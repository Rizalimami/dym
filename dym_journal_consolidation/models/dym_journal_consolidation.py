from openerp import models, fields, api, _, SUPERUSER_ID
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp.osv import orm, fields, osv
import logging
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)
from lxml import etree

class account_move_consol(osv.osv):
    _name = "account.move.consol"
    _description = "Journal Entry Consolidation"
    _order = "id desc"

    def _amount_compute(self, cr, uid, ids, name, args, context, where =''):
        if not ids: return {}
        cr.execute( 'SELECT move_id, SUM(debit) '\
                    'FROM account_move_line_consol '\
                    'WHERE move_id IN %s '\
                    'GROUP BY move_id', (tuple(ids),))
        result = dict(cr.fetchall())
        for id in ids:
            result.setdefault(id, 0.0)
        return result

    def _search_amount(self, cr, uid, obj, name, args, context):
        ids = set()
        for cond in args:
            amount = cond[2]
            if isinstance(cond[2],(list,tuple)):
                if cond[1] in ['in','not in']:
                    amount = tuple(cond[2])
                else:
                    continue
            else:
                if cond[1] in ['=like', 'like', 'not like', 'ilike', 'not ilike', 'in', 'not in', 'child_of']:
                    continue

            cr.execute("select move_id from account_move_line_consol group by move_id having sum(debit) %s %%s" % (cond[1]),(amount,))
            res_ids = set(id[0] for id in cr.fetchall())
            ids = ids and (ids & res_ids) or res_ids
        if ids:
            return [('id', 'in', tuple(ids))]
        return [('id', '=', '0')]

    def _get_move_from_lines(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('account.move.line.consol')
        return [line.move_id.id for line in line_obj.browse(cr, uid, ids, context=context)]

    def _get_period(self, cr, uid, context=None):
        ctx = dict(context or {})
        period_ids = self.pool.get('account.period').find(cr, uid, context=ctx)
        return period_ids[0]

    _columns = {
        'name': fields.char('Number', required=True, copy=False),
        'ref': fields.char('Reference', copy=False),
        'period_id': fields.many2one('account.period', 'Period', required=True, states={'posted':[('readonly',True)]}),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, states={'posted':[('readonly',True)]}),
        'state': fields.selection(
              [('draft','Unposted'), ('posted','Posted')], 'Status',
              required=True, readonly=True, copy=False,
              help='All manually created new journal entries are usually in the status \'Unposted\', '
                   'but you can set the option to skip that status on the related journal. '
                   'In that case, they will behave as journal entries automatically created by the '
                   'system on document validation (invoices, bank statements...) and will be created '
                   'in \'Posted\' status.'),
        'line_id': fields.one2many('account.move.line.consol', 'move_id', 'Entries',
                                   states={'posted':[('readonly',True)]},
                                   copy=True),
        'partner_id': fields.related('line_id', 'partner_id', type="many2one", relation="res.partner", string="Partner", store={
            _name: (lambda self, cr,uid,ids,c: ids, ['line_id'], 10),
            'account.move.line.consol': (_get_move_from_lines, ['partner_id'],10)
            }),
        'amount': fields.function(_amount_compute, string='Amount', digits_compute=dp.get_precision('Account'), type='float', fnct_search=_search_amount),
        'date': fields.date('Date', required=True, states={'posted':[('readonly',True)]}, select=True),
        'narration':fields.text('Internal Note'),
        'company_id': fields.related('journal_id','company_id',type='many2one',relation='res.company',string='Company', store=True, readonly=True),
        'balance': fields.float('balance', digits_compute=dp.get_precision('Account'), help="This is a field only used for internal purpose and shouldn't be displayed"),
        'cancel_uid' : fields.many2one('res.users',string="Cancelled by"),
        'confirm_uid' : fields.many2one('res.users',string="Posted by"),
        'cancel_date' : fields.datetime('Cancelled on'),
        'confirm_date' : fields.datetime('Posted on'),
    }

    _defaults = {
        'name': '/',
        'state': 'draft',
        'period_id': _get_period,
        'date': fields.date.context_today,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

    def _check_centralisation(self, cursor, user, ids, context=None):
        for move in self.browse(cursor, user, ids, context=context):
            if move.journal_id.centralisation:
                move_ids = self.search(cursor, user, [
                    ('period_id', '=', move.period_id.id),
                    ('journal_id', '=', move.journal_id.id),
                    ])
                if len(move_ids) > 1:
                    return False
        return True

    _constraints = [
        (_check_centralisation,
            'You cannot create more than one move per period on a centralized journal.',
            ['journal_id']),
    ]

    def post(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoice = context.get('invoice', False)
        valid_moves = self.validate(cr, uid, ids, context)

        if not valid_moves:
            raise osv.except_osv(_('Error!'), _('You cannot validate a non-balanced entry.\nMake sure you have configured payment terms properly.\nThe latest payment term line should be of the "Balance" type.'))
        obj_sequence = self.pool.get('ir.sequence')
        for move in self.browse(cr, uid, valid_moves, context=context):
            if move.name =='/':
                new_name = False
                journal = move.journal_id

                if invoice and invoice.internal_number:
                    new_name = invoice.internal_number
                else:
                    if journal.sequence_id:
                        c = {'fiscalyear_id': move.period_id.fiscalyear_id.id}
                        new_name = obj_sequence.next_by_id(cr, uid, journal.sequence_id.id, c)
                    else:
                        raise osv.except_osv(_('Error!'), _('Please define a sequence on the journal.'))

                if new_name:
                    self.write(cr, uid, [move.id], {'name':new_name})

        aml_ids = self.browse(cr, uid, valid_moves).mapped('line_id.consolidation_move_line_id').ids
        if aml_ids:
            cr.execute('SELECT lc.id from account_move_line_consol lc left join account_move_consol mc on mc.id = lc.move_id where lc.consolidation_move_line_id in %s and mc.state = %s and mc.id not in %s', (tuple(aml_ids),'posted',tuple(valid_moves),))
            rows = cr.dictfetchall()
            if rows:
                raise osv.except_osv(_('Error!'), _('Terdapat journal item konsolidasi yang sudah dipost!.'))

        amlc_ids = self.browse(cr, uid, valid_moves).mapped('line_id.elimination_move_line_id').ids
        if amlc_ids:
            cr.execute('SELECT lc.id from account_move_line_consol lc left join account_move_consol mc on mc.id = lc.move_id where lc.elimination_move_line_id in %s and mc.state = %s and mc.id not in %s', (tuple(amlc_ids),'posted',tuple(valid_moves),))
            rows = cr.dictfetchall()
            if rows:
                raise osv.except_osv(_('Error!'), _('Terdapat journal item eliminasi yang sudah dipost!.'))

        cr.execute('UPDATE account_move_consol '\
                   'SET state=%s,confirm_uid=%s,confirm_date=%s '\
                   'WHERE id IN %s',
                   ('posted', uid, time.strftime('%Y-%m-%d %H:%M:%S'), tuple(valid_moves),))
        if aml_ids:
            cr.execute('UPDATE account_move_line '\
                       'SET consolidate_posted=%s '\
                       'WHERE id IN %s',
                       ('t',tuple(aml_ids),))
        if amlc_ids:
            cr.execute('UPDATE account_move_line_consol '\
                       'SET eliminate_posted=%s '\
                       'WHERE id IN %s',
                       ('t',tuple(amlc_ids),))
            posted_consol = self.browse(cr, uid, valid_moves).mapped('line_id.elimination_move_line_id.move_id').filtered(lambda r: r.state == 'draft')
            if posted_consol:
                raise osv.except_osv(_('Error!'), _('Journal entry konsolidasi belum di post!.'))
        self.invalidate_cache(cr, uid, context=context)
        return True

    def button_validate(self, cursor, user, ids, context=None):
        for move in self.browse(cursor, user, ids, context=context):
            # check that all accounts have the same topmost ancestor
            top_common = None
            for line in move.line_id:
                account = line.account_id
                top_account = account
                while top_account.parent_id:
                    top_account = top_account.parent_id
                if not top_common:
                    top_common = top_account
                elif top_account.id != top_common.id:
                    raise osv.except_osv(_('Error!'),
                                         _('You cannot validate this journal entry because account "%s" does not belong to chart of accounts "%s".') % (account.name, top_common.name))
        return self.post(cursor, user, ids, context=context)

    def button_cancel(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if not line.journal_id.update_posted:
                raise osv.except_osv(_('Error!'), _('You cannot modify a posted entry of this journal.\nFirst you should set the journal to allow cancelling entries.'))
        if ids:
            cr.execute('UPDATE account_move_consol '\
                       'SET state=%s '\
                       'WHERE id IN %s', ('draft', tuple(ids),))
            self.invalidate_cache(cr, uid, context=context)
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':time.strftime('%Y-%m-%d %H:%M:%S')})
        aml_ids = self.browse(cr, uid, ids).mapped('line_id.consolidation_move_line_id').ids
        if aml_ids:
            cr.execute('UPDATE account_move_line '\
                   'SET consolidate_posted=%s '\
                   'WHERE id IN %s',
                   ('f',tuple(aml_ids),))
        posted_elim = self.browse(cr, uid, ids).mapped('line_id').filtered(lambda r: r.eliminate_posted == True)
        if posted_elim:
            raise osv.except_osv(_('Error!'), _('Journal entry sudah dieliminasi!.'))
        amlc_ids = self.browse(cr, uid, ids).mapped('line_id.elimination_move_line_id').ids
        if amlc_ids:
            cr.execute('UPDATE account_move_line_consol '\
                       'SET eliminate_posted=%s '\
                       'WHERE id IN %s',
                       ('f',tuple(amlc_ids),))
        return True

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        c = context.copy()
        c['novalidate'] = True
        result = super(account_move_consol, self).write(cr, uid, ids, vals, c)
        self.validate(cr, uid, ids, context=context)
        return result

    def create(self, cr, uid, vals, context=None):
        context = dict(context or {})
        if vals.get('line_id'):
            if vals.get('journal_id'):
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['journal_id'] = vals['journal_id']
                context['journal_id'] = vals['journal_id']
            if 'period_id' in vals:
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['period_id'] = vals['period_id']
                context['period_id'] = vals['period_id']
            else:
                default_period = self._get_period(cr, uid, context)
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['period_id'] = default_period
                context['period_id'] = default_period

            c = context.copy()
            c['novalidate'] = True
            c['period_id'] = vals['period_id'] if 'period_id' in vals else self._get_period(cr, uid, context)
            c['journal_id'] = vals['journal_id']
            if 'date' in vals: c['date'] = vals['date']
            result = super(account_move_consol, self).create(cr, uid, vals, c)
            tmp = self.validate(cr, uid, [result], context)
            journal = self.pool.get('account.journal').browse(cr, uid, vals['journal_id'], context)
            if journal.entry_posted and tmp:
                self.button_validate(cr,uid, [result], context)
        else:
            result = super(account_move_consol, self).create(cr, uid, vals, context)
        return result

    def unlink(self, cr, uid, ids, context=None, check=True):
        context = dict(context or {})
        if isinstance(ids, (int, long)):
            ids = [ids]
        toremove = []
        obj_move_line = self.pool.get('account.move.line.consol')
        for move in self.browse(cr, uid, ids, context=context):
            if move['state'] != 'draft':
                raise osv.except_osv(_('User Error!'),
                        _('You cannot delete a posted journal entry "%s".') % \
                                move['name'])
            line_ids = map(lambda x: x.id, move.line_id)
            context['journal_id'] = move.journal_id.id
            context['period_id'] = move.period_id.id
            obj_move_line._update_check(cr, uid, line_ids, context)
            obj_move_line.unlink(cr, uid, line_ids, context=context)
            toremove.append(move.id)
        result = super(account_move_consol, self).unlink(cr, uid, toremove, context)
        return result

    def _compute_balance(self, cr, uid, id, context=None):
        move = self.browse(cr, uid, id, context=context)
        amount = 0
        for line in move.line_id:
            amount+= (line.debit - line.credit)
        return amount

    def _centralise(self, cr, uid, move, mode, context=None):
        assert mode in ('debit', 'credit'), 'Invalid Mode' #to prevent sql injection
        currency_obj = self.pool.get('res.currency')
        account_move_line_obj = self.pool.get('account.move.line.consol')
        context = dict(context or {})

        if mode=='credit':
            account_id = move.journal_id.default_debit_account_id.id
            mode2 = 'debit'
            if not account_id:
                raise osv.except_osv(_('User Error!'),
                        _('There is no default debit account defined \n' \
                                'on journal "%s".') % move.journal_id.name)
        else:
            account_id = move.journal_id.default_credit_account_id.id
            mode2 = 'credit'
            if not account_id:
                raise osv.except_osv(_('User Error!'),
                        _('There is no default credit account defined \n' \
                                'on journal "%s".') % move.journal_id.name)

        # find the first line of this move with the current mode
        # or create it if it doesn't exist
        cr.execute('select id from account_move_line_consol where move_id=%s and centralisation=%s limit 1', (move.id, mode))
        res = cr.fetchone()
        if res:
            line_id = res[0]
        else:
            context.update({'journal_id': move.journal_id.id, 'period_id': move.period_id.id})
            line_id = account_move_line_obj.create(cr, uid, {
                'name': _(mode.capitalize()+' Centralisation'),
                'centralisation': mode,
                'partner_id': False,
                'account_id': account_id,
                'move_id': move.id,
                'journal_id': move.journal_id.id,
                'period_id': move.period_id.id,
                'date': move.period_id.date_stop,
                'debit': 0.0,
                'credit': 0.0,
            }, context)

        # find the first line of this move with the other mode
        # so that we can exclude it from our calculation
        cr.execute('select id from account_move_line_consol where move_id=%s and centralisation=%s limit 1', (move.id, mode2))
        res = cr.fetchone()
        if res:
            line_id2 = res[0]
        else:
            line_id2 = 0

        cr.execute('SELECT SUM(%s) FROM account_move_line_consol WHERE move_id=%%s AND id!=%%s' % (mode,), (move.id, line_id2))
        result = cr.fetchone()[0] or 0.0
        cr.execute('update account_move_line_consol set '+mode2+'=%s where id=%s', (result, line_id))
        account_move_line_obj.invalidate_cache(cr, uid, [mode2], [line_id], context=context)

        #adjust also the amount in currency if needed
        cr.execute("select currency_id, sum(amount_currency) as amount_currency from account_move_line_consol where move_id = %s and currency_id is not null group by currency_id", (move.id,))
        for row in cr.dictfetchall():
            currency_id = currency_obj.browse(cr, uid, row['currency_id'], context=context)
            if not currency_obj.is_zero(cr, uid, currency_id, row['amount_currency']):
                amount_currency = row['amount_currency'] * -1
                account_id = amount_currency > 0 and move.journal_id.default_debit_account_id.id or move.journal_id.default_credit_account_id.id
                cr.execute('select id from account_move_line_consol where move_id=%s and centralisation=\'currency\' and currency_id = %slimit 1', (move.id, row['currency_id']))
                res = cr.fetchone()
                if res:
                    cr.execute('update account_move_line_consol set amount_currency=%s , account_id=%s where id=%s', (amount_currency, account_id, res[0]))
                    account_move_line_obj.invalidate_cache(cr, uid, ['amount_currency', 'account_id'], [res[0]], context=context)
                else:
                    context.update({'journal_id': move.journal_id.id, 'period_id': move.period_id.id})
                    line_id = account_move_line_obj.create(cr, uid, {
                        'name': _('Currency Adjustment'),
                        'centralisation': 'currency',
                        'partner_id': False,
                        'account_id': account_id,
                        'move_id': move.id,
                        'journal_id': move.journal_id.id,
                        'period_id': move.period_id.id,
                        'date': move.period_id.date_stop,
                        'debit': 0.0,
                        'credit': 0.0,
                        'currency_id': row['currency_id'],
                        'amount_currency': amount_currency,
                    }, context)

        return True

    #
    # Validate a balanced move. If it is a centralised journal, create a move.
    #
    def validate(self, cr, uid, ids, context=None):
        if context and ('__last_update' in context):
            del context['__last_update']

        valid_moves = [] #Maintains a list of moves which can be responsible to create analytic entries
        obj_move_line = self.pool.get('account.move.line.consol')
        obj_precision = self.pool.get('decimal.precision')
        prec = obj_precision.precision_get(cr, uid, 'Account')
        for move in self.browse(cr, uid, ids, context):
            journal = move.journal_id
            amount = 0
            line_ids = []
            line_draft_ids = []
            company_id = None
            # makes sure we don't use outdated period
            obj_move_line._update_journal_check(cr, uid, journal.id, move.period_id.id, context=context)
            for line in move.line_id:
                amount += line.debit - line.credit
                line_ids.append(line.id)
                if line.state=='draft':
                    line_draft_ids.append(line.id)

                if not company_id:
                    company_id = line.account_id.company_id.id
                if not company_id == line.account_id.company_id.id:
                    raise osv.except_osv(_('Error!'), _("Cannot create moves for different companies."))

                if line.account_id.currency_id and line.currency_id:
                    if line.account_id.currency_id.id != line.currency_id.id and (line.account_id.currency_id.id != line.account_id.company_id.currency_id.id):
                        raise osv.except_osv(_('Error!'), _("""Cannot create move with currency different from ..""") % (line.account_id.code, line.account_id.name))

            if round(abs(amount), prec) < 10 ** (-max(5, prec)):
                # If the move is balanced
                # Add to the list of valid moves
                # (analytic lines will be created later for valid moves)
                valid_moves.append(move)

                # Check whether the move lines are confirmed

                if not line_draft_ids:
                    continue
                # Update the move lines (set them as valid)

                obj_move_line.write(cr, uid, line_draft_ids, {
                    'state': 'valid'
                }, context, check=False)

                account = {}
                account2 = {}

                if journal.type in ('purchase','sale'):
                    for line in move.line_id:
                        code = amount = 0
                        key = (line.account_id.id, line.tax_code_id.id)
                        if key in account2:
                            code = account2[key][0]
                            amount = account2[key][1] * (line.debit + line.credit)
                        elif line.account_id.id in account:
                            code = account[line.account_id.id][0]
                            amount = account[line.account_id.id][1] * (line.debit + line.credit)
                        if (code or amount) and not (line.tax_code_id or line.tax_amount):
                            obj_move_line.write(cr, uid, [line.id], {
                                'tax_code_id': code,
                                'tax_amount': amount
                            }, context, check=False)
            elif journal.centralisation:
                # If the move is not balanced, it must be centralised...

                # Add to the list of valid moves
                # (analytic lines will be created later for valid moves)
                valid_moves.append(move)

                #
                # Update the move lines (set them as valid)
                #
                self._centralise(cr, uid, move, 'debit', context=context)
                self._centralise(cr, uid, move, 'credit', context=context)
                obj_move_line.write(cr, uid, line_draft_ids, {
                    'state': 'valid'
                }, context, check=False)
            else:
                # We can't validate it (it's unbalanced)
                # Setting the lines as draft
                not_draft_line_ids = list(set(line_ids) - set(line_draft_ids))
                if not_draft_line_ids:
                    obj_move_line.write(cr, uid, not_draft_line_ids, {
                        'state': 'draft'
                    }, context, check=False)

        valid_moves = [move.id for move in valid_moves]
        return len(valid_moves) > 0 and valid_moves or False


class account_move_line_consol(osv.osv):
    _name = "account.move.line.consol"
    _description = "Journal Items Consolidation"

    def _query_get(self, cr, uid, obj='l', context=None):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalperiod_obj = self.pool.get('account.period')
        account_obj = self.pool.get('account.account')
        fiscalyear_ids = []
        context = dict(context or {})
        initial_bal = context.get('initial_bal', False)
        company_clause = " "
        query = ''
        query_params = {}
        if context.get('company_id'):
            company_clause = " AND " +obj+".company_id = %(company_id)s"
            query_params['company_id'] = context['company_id']
        if not context.get('fiscalyear'):
            if context.get('all_fiscalyear'):
                #this option is needed by the aged balance report because otherwise, if we search only the draft ones, an open invoice of a closed fiscalyear won't be displayed
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [])
            else:
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [('state', '=', 'draft')])
        else:
            #for initial balance as well as for normal query, we check only the selected FY because the best practice is to generate the FY opening entries
            fiscalyear_ids = context['fiscalyear']
            if isinstance(context['fiscalyear'], (int, long)):
                fiscalyear_ids = [fiscalyear_ids]

        query_params['fiscalyear_ids'] = tuple(fiscalyear_ids) or (0,)
        state = context.get('state', False)
        where_move_state = ''
        where_move_lines_by_date = ''

        if context.get('date_from') and context.get('date_to'):
            query_params['date_from'] = context['date_from']
            query_params['date_to'] = context['date_to']
            if initial_bal:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM account_move_consol WHERE date < %(date_from)s)"
            else:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM account_move_consol WHERE date >= %(date_from)s AND date <= %(date_to)s)"

        if state:
            if state.lower() not in ['all']:
                query_params['state'] = state
                where_move_state= " AND "+obj+".move_id IN (SELECT id FROM account_move_consol WHERE account_move_consol.state = %(state)s)"
        if context.get('period_from') and context.get('period_to') and not context.get('periods'):
            if initial_bal:
                period_company_id = fiscalperiod_obj.browse(cr, uid, context['period_from'], context=context).company_id.id
                first_period = fiscalperiod_obj.search(cr, uid, [('company_id', '=', period_company_id)], order='date_start', limit=1)[0]
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, first_period, context['period_from'])
            else:
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, context['period_from'], context['period_to'])
        if context.get('periods'):
            query_params['period_ids'] = tuple(context['periods'])
            if initial_bal:
                query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s)" + where_move_state + where_move_lines_by_date
                period_ids = fiscalperiod_obj.search(cr, uid, [('id', 'in', context['periods'])], order='date_start', limit=1)
                if period_ids and period_ids[0]:
                    first_period = fiscalperiod_obj.browse(cr, uid, period_ids[0], context=context)
                    query_params['date_start'] = first_period.date_start
                    query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s AND date_start <= %(date_start)s AND id NOT IN %(period_ids)s)" + where_move_state + where_move_lines_by_date
            else:
                query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s AND id IN %(period_ids)s)" + where_move_state + where_move_lines_by_date
        else:
            query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s)" + where_move_state + where_move_lines_by_date

        if initial_bal and not context.get('periods') and not where_move_lines_by_date:
            #we didn't pass any filter in the context, and the initial balance can't be computed using only the fiscalyear otherwise entries will be summed twice
            #so we have to invalidate this query
            raise osv.except_osv(_('Warning!'),_("You have not supplied enough arguments to compute the initial balance, please select a period and a journal in the context."))

        if context.get('journal_ids'):
            query_params['journal_ids'] = tuple(context['journal_ids'])
            query += ' AND '+obj+'.journal_id IN %(journal_ids)s'

        if context.get('account_ids'):
            query_params['account_ids'] = tuple(context['account_ids'])
            query += ' AND '+obj+'.account_id IN %(account_ids)s'

        if context.get('analytic_ids'):
            query_params['analytic_ids'] = tuple(context['analytic_ids'])
            query += ' AND '+obj+'.analytic_account_id IN %(analytic_ids)s'

        if context.get('chart_account_id'):
            child_ids = account_obj._get_children_and_consol(cr, uid, [context['chart_account_id']], context=context)
            query_params['child_ids'] = tuple(child_ids)
            query += ' AND '+obj+'.account_id IN %(child_ids)s'

        if context.get('sql_query'):
            query += context['sql_query']

        if context.get('analytic_co_dari'):
            if context.get('analytic_co_dari'):
                query_params['analytic_co_dari'] = int(context['analytic_co_dari'])
                query += " AND cast(coalesce(a1.code, '-1') as integer) >= %(analytic_co_dari)s"

        if context.get('analytic_co_sampai'):
            if context.get('analytic_co_sampai').isdigit():
                query_params['analytic_co_sampai'] = int(context['analytic_co_sampai'])
                query += " AND cast(coalesce(a1.code, '9999999999') as integer) <= %(analytic_co_sampai)s"

        if context.get('analytic_bb_dari'):
            if context.get('analytic_bb_dari'):
                query_params['analytic_bb_dari'] = int(context['analytic_bb_dari'])
                query += " AND cast(coalesce(a2.code, '-1') as integer) >= %(analytic_bb_dari)s"

        if context.get('analytic_bb_sampai'):
            if context.get('analytic_bb_sampai').isdigit():
                query_params['analytic_bb_sampai'] = int(context['analytic_bb_sampai'])
                query += " AND cast(coalesce(a2.code, '9999999999') as integer) <= %(analytic_bb_sampai)s"

        if context.get('analytic_br_dari'):
            if context.get('analytic_br_dari'):
                query_params['analytic_br_dari'] = int(context['analytic_br_dari'])
                query += " AND cast(coalesce(a3.code, '-1') as integer) >= %(analytic_br_dari)s"

        if context.get('analytic_br_sampai'):
            if context.get('analytic_br_sampai').isdigit():
                query_params['analytic_br_sampai'] = int(context['analytic_br_sampai'])
                query += " AND cast(coalesce(a3.code, '9999999999') as integer) <= %(analytic_br_sampai)s"

        if context.get('analytic_cc_dari'):
            if context.get('analytic_cc_dari'):
                query_params['analytic_cc_dari'] = int(context['analytic_cc_dari'])
                query += " AND cast(coalesce(a4.code, '-1') as integer) >= %(analytic_cc_dari)s"

        if context.get('analytic_cc_sampai'):
            if context.get('analytic_cc_sampai').isdigit():
                query_params['analytic_cc_sampai'] = int(context['analytic_cc_sampai'])
                query += " AND cast(coalesce(a4.code, '9999999999') as integer) <= %(analytic_cc_sampai)s"

        query += company_clause
        return cr.mogrify(query, query_params)

    def _get_move_lines(self, cr, uid, ids, context=None):
        result = []
        for move in self.pool.get('account.move.consol').browse(cr, uid, ids, context=context):
            for line in move.line_id:
                result.append(line.id)
        return result

    def _balance(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        c = context.copy()
        c['initital_bal'] = True
        sql = """SELECT l1.id, COALESCE(SUM(l2.debit-l2.credit), 0)
                    FROM account_move_line_consol l1 LEFT JOIN account_move_line_consol l2
                    ON (l1.account_id = l2.account_id
                      AND l2.id <= l1.id
                      AND """ + \
                self._query_get(cr, uid, obj='l2', context=c) + \
                ") WHERE l1.id IN %s GROUP BY l1.id"

        cr.execute(sql, [tuple(ids)])
        return dict(cr.fetchall())

    def _get_analytic(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id] = {
                'analytic_1': False,
                'analytic_2': False,
                'analytic_3': False,
                'analytic_4': False,
            }
            analytic_1 = analytic_2 = analytic_3 = analytic_4 = False
            analytic = line.analytic_account_id
            if analytic.type == 'normal':
                if analytic.segmen == 1:
                    analytic_1 = analytic.id
                if analytic.segmen == 2:
                    analytic_2 = analytic.id
                if analytic.segmen == 3:
                    analytic_3 = analytic.id
                if analytic.segmen == 4:
                    analytic_4 = analytic.id
            while (analytic.parent_id):
                analytic = analytic.parent_id
                if analytic.type == 'normal':
                    if analytic.segmen == 1:
                        analytic_1 = analytic.id
                    if analytic.segmen == 2:
                        analytic_2 = analytic.id
                    if analytic.segmen == 3:
                        analytic_3 = analytic.id
                    if analytic.segmen == 4:
                        analytic_4 = analytic.id
            res[line.id] = {
                'analytic_1': analytic_1,
                'analytic_2': analytic_2,
                'analytic_3': analytic_3,
                'analytic_4': analytic_4,
            }
        return res

       
    def _balance_search(self, cursor, user, obj, name, args, domain=None, context=None):
        if context is None:
            context = {}
        if not args:
            return []
        where = ' AND '.join(map(lambda x: '(abs(sum(debit-credit))'+x[1]+str(x[2])+')',args))
        cursor.execute('SELECT id, SUM(debit-credit) FROM account_move_line_consol \
                     GROUP BY id, debit, credit having '+where)
        res = cursor.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]

    _columns = {
        'consolidation_move_line_id' : fields.many2one('account.move.line', string='Consolidate Move Line', copy=False),
        'branch_id' : fields.many2one('dym.branch', string='Branch'),
        'division' : fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', change_default=True, select=False),
        'balance': fields.function(_balance, fnct_search=_balance_search, string='Balance'),
        'analytic_1' : fields.function(_get_analytic, type='many2one', relation='account.analytic.account', string='Account Analytic Company', multi='sums', store=True),
        'analytic_2' : fields.function(_get_analytic, type='many2one', relation='account.analytic.account', string='Account Analytic Bisnis Unit', multi='sums', store=True),
        'analytic_3' : fields.function(_get_analytic, type='many2one', relation='account.analytic.account', string='Account Analytic Branch', multi='sums', store=True),
        'analytic_4' : fields.function(_get_analytic, type='many2one', relation='account.analytic.account', string='Account Analytic Cost Center', multi='sums', store=True),
        'name': fields.char('Name', required=True),
        'quantity': fields.float('Quantity', digits=(16,2), help="The optional quantity expressed by this line, eg: number of product sold. The quantity is not a legal requirement but is very useful for some reports."),
        'product_uom_id': fields.many2one('product.uom', 'Unit of Measure'),
        'product_id': fields.many2one('product.product', 'Product'),
        'debit': fields.float('Debit', digits_compute=dp.get_precision('Account')),
        'credit': fields.float('Credit', digits_compute=dp.get_precision('Account')),
        'account_id': fields.many2one('account.account', 'Account', required=True, ondelete="cascade", domain=[('type','<>','view'), ('type', '<>', 'closed')], select=2),
        'move_id': fields.many2one('account.move.consol', 'Journal Entry', ondelete="cascade", help="The move of this entry line.", select=2, required=True, auto_join=True),
        'narration': fields.related('move_id','narration', type='text', relation='account.move.consol', string='Internal Note'),
        'ref': fields.related('move_id', 'ref', string='Reference', type='char', store=True),
        'amount_currency': fields.float('Amount Currency', help="The amount expressed in an optional other currency if it is a multi-currency entry.", digits_compute=dp.get_precision('Account')),
        'currency_id': fields.many2one('res.currency', 'Currency', help="The optional other currency if it is a multi-currency entry."),
        'journal_id': fields.related('move_id', 'journal_id', string='Journal', type='many2one', relation='account.journal', required=True, select=True,
                                store = {
                                    'account.move.consol': (_get_move_lines, ['journal_id'], 20)
                                }),
        'period_id': fields.related('move_id', 'period_id', string='Period', type='many2one', relation='account.period', required=True, select=True,
                                store = {
                                    'account.move.consol': (_get_move_lines, ['period_id'], 20)
                                }),
        'partner_id': fields.many2one('res.partner', 'Partner', select=1, ondelete='restrict'),
        'date': fields.related('move_id','date', string='Effective date', type='date', required=True, select=True,
                                store = {
                                    'account.move.consol': (_get_move_lines, ['date'], 20)
                                }),
        'date_created': fields.date('Creation date', select=True),
        'centralisation': fields.selection([('normal','Normal'),('credit','Credit Centralisation'),('debit','Debit Centralisation'),('currency','Currency Adjustment')], 'Centralisation', size=8),
        'balance': fields.function(_balance, fnct_search=_balance_search, string='Balance'),
        'state': fields.selection([('draft','Unbalanced'), ('valid','Balanced')], 'Status', readonly=True, copy=False),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Account', help="The Account can either be a base tax code or a tax code account."),
        'tax_amount': fields.float('Tax/Base Amount', digits_compute=dp.get_precision('Account'), select=True, help="If the Tax account is a tax code account, this field will contain the taxed amount.If the tax account is base tax code, "\
                    "this field will contain the basic amount(without tax)."),
        'account_tax_id':fields.many2one('account.tax', 'Tax', copy=False),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'company_id': fields.related('account_id', 'company_id', type='many2one', relation='res.company',
                            string='Company', store=True, readonly=True)
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        result = []

        for line in self.browse(cr, uid, ids, context=context):
            if line.name != '/':  
                result.append((line.id, (line.move_id.name or '')+' ('+line.name+')'))
            else:
                result.append((line.id, line.move_id.name))
        return result

    def _get_date(self, cr, uid, context=None):
        if context is None:
            context or {}
        period_obj = self.pool.get('account.period')
        dt = time.strftime('%Y-%m-%d')
        if context.get('journal_id') and context.get('period_id'):
            cr.execute('SELECT date FROM account_move_line_consol ' \
                    'WHERE journal_id = %s AND period_id = %s ' \
                    'ORDER BY id DESC limit 1',
                    (context['journal_id'], context['period_id']))
            res = cr.fetchone()
            if res:
                dt = res[0]
            else:
                period = period_obj.browse(cr, uid, context['period_id'], context=context)
                dt = period.date_start
        return dt

    def _get_currency(self, cr, uid, context=None):
        if context is None:
            context = {}
        if not context.get('journal_id', False):
            return False
        cur = self.pool.get('account.journal').browse(cr, uid, context['journal_id']).currency
        return cur and cur.id or False

    def _get_period(self, cr, uid, context=None):
        """
        Return  default account period value
        """
        context = context or {}
        if context.get('period_id', False):
            return context['period_id']
        account_period_obj = self.pool.get('account.period')
        ids = account_period_obj.find(cr, uid, context=context)
        period_id = False
        if ids:
            period_id = ids[0]
        return period_id

    def _get_journal(self, cr, uid, context=None):
        """
        Return journal based on the journal type
        """
        context = context or {}
        if context.get('journal_id', False):
            return context['journal_id']
        journal_id = False

        journal_pool = self.pool.get('account.journal')
        if context.get('journal_type', False):
            jids = journal_pool.search(cr, uid, [('type','=', context.get('journal_type'))])
            if not jids:
                model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'account', 'action_account_journal_form')
                msg = _("""Cannot find any account journal of "%s" type for this company, You should create one.\n Please go to Journal Configuration""") % context.get('journal_type').replace('_', ' ').title()
                raise openerp.exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
            journal_id = jids[0]
        return journal_id

    _defaults = {
        'centralisation': 'normal',
        'date': _get_date,
        'date_created': fields.date.context_today,
        'state': 'draft',
        'currency_id': _get_currency,
        'journal_id': _get_journal,
        'credit': 0.0,
        'debit': 0.0,
        'amount_currency': 0.0,
        'account_id': lambda self, cr, uid, c: c.get('account_id', False),
        'period_id': _get_period,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.move.line.consol', context=c)
    }

    def _check_no_view(self, cr, uid, ids, context=None):
        lines = self.browse(cr, uid, ids, context=context)
        for l in lines:
            if l.account_id.type in ('view', 'consolidation'):
                return False
        return True

    def _check_no_closed(self, cr, uid, ids, context=None):
        lines = self.browse(cr, uid, ids, context=context)
        for l in lines:
            if l.account_id.type == 'closed':
                raise osv.except_osv(_('Error!'), _('You cannot create journal items on a closed account %s %s.') % (l.account_id.code, l.account_id.name))
        return True

    def _check_company_id(self, cr, uid, ids, context=None):
        lines = self.browse(cr, uid, ids, context=context)
        for l in lines:
            if l.account_id.company_id != l.period_id.company_id:
                return False
        return True

    def _check_date(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if l.journal_id.allow_date:
                if not time.strptime(l.date[:10],'%Y-%m-%d') >= time.strptime(l.period_id.date_start, '%Y-%m-%d') or not time.strptime(l.date[:10], '%Y-%m-%d') <= time.strptime(l.period_id.date_stop, '%Y-%m-%d'):
                    return False
        return True

    def _check_currency(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if l.account_id.currency_id:
                if not l.currency_id or not l.currency_id.id == l.account_id.currency_id.id:
                    return False
        return True

    def _check_currency_and_amount(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if (l.amount_currency and not l.currency_id):
                return False
        return True

    def _check_currency_amount(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if l.amount_currency:
                if (l.amount_currency > 0.0 and l.credit > 0.0) or (l.amount_currency < 0.0 and l.debit > 0.0):
                    return False
        return True

    def _check_currency_company(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if l.currency_id.id == l.company_id.currency_id.id:
                return False
        return True

    _constraints = [
        (_check_no_view, 'You cannot create journal items on an account of type view or consolidation.', ['account_id']),
        (_check_no_closed, 'You cannot create journal items on closed account.', ['account_id']),
        (_check_company_id, 'Account and Period must belong to the same company.', ['company_id']),
        (_check_date, 'The date of your Journal Entry is not in the defined period! You should change the date or remove this constraint from the journal.', ['date']),
        (_check_currency, 'The selected account of your Journal Entry forces to provide a secondary currency. You should remove the secondary currency on the account or select a multi-currency view on the journal.', ['currency_id']),
        (_check_currency_and_amount, "You cannot create journal items with a secondary currency without recording both 'currency' and 'amount currency' field.", ['currency_id','amount_currency']),
        (_check_currency_amount, 'The amount expressed in the secondary currency must be positive when account is debited and negative when account is credited.', ['amount_currency']),
        (_check_currency_company, "You cannot provide a secondary currency if it is the same than the company one." , ['currency_id']),
    ]

    #TODO: ONCHANGE_ACCOUNT_ID: set account_tax_id
    def onchange_currency(self, cr, uid, ids, account_id, amount, currency_id, date=False, journal=False, context=None):
        if context is None:
            context = {}
        account_obj = self.pool.get('account.account')
        journal_obj = self.pool.get('account.journal')
        currency_obj = self.pool.get('res.currency')
        if (not currency_id) or (not account_id):
            return {}
        result = {}
        acc = account_obj.browse(cr, uid, account_id, context=context)
        if (amount>0) and journal:
            x = journal_obj.browse(cr, uid, journal).default_credit_account_id
            if x: acc = x
        context = dict(context)
        context.update({
                'date': date,
                'res.currency.compute.account': acc,
            })
        v = currency_obj.compute(cr, uid, currency_id, acc.company_id.currency_id.id, amount, context=context)
        result['value'] = {
            'debit': v > 0 and v or 0.0,
            'credit': v < 0 and -v or 0.0
        }
        return result

    def onchange_partner_id(self, cr, uid, ids, move_id, partner_id, account_id=None, debit=0, credit=0, date=False, journal=False, context=None):
        partner_obj = self.pool.get('res.partner')
        payment_term_obj = self.pool.get('account.payment.term')
        journal_obj = self.pool.get('account.journal')
        fiscal_pos_obj = self.pool.get('account.fiscal.position')
        val = {}
        val['date_maturity'] = False

        if not partner_id:
            return {'value':val}
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        jt = False
        if journal:
            jt = journal_obj.browse(cr, uid, journal, context=context).type
        part = partner_obj.browse(cr, uid, partner_id, context=context)

        payment_term_id = False
        if jt and jt in ('purchase', 'purchase_refund') and part.property_supplier_payment_term:
            payment_term_id = part.property_supplier_payment_term.id
        elif jt and part.property_payment_term:
            payment_term_id = part.property_payment_term.id
        if payment_term_id:
            res = payment_term_obj.compute(cr, uid, payment_term_id, 100, date)
            if res:
                val['date_maturity'] = res[0][0]
        if not account_id:
            id1 = part.property_account_payable.id
            id2 =  part.property_account_receivable.id
            if jt:
                if jt in ('sale', 'purchase_refund'):
                    val['account_id'] = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, id2)
                elif jt in ('purchase', 'sale_refund'):
                    val['account_id'] = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, id1)
                elif jt in ('general', 'bank', 'cash'):
                    if part.customer:
                        val['account_id'] = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, id2)
                    elif part.supplier:
                        val['account_id'] = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, id1)
                if val.get('account_id', False):
                    d = self.onchange_account_id(cr, uid, ids, account_id=val['account_id'], partner_id=part.id, context=context)
                    val.update(d['value'])
        return {'value':val}

    def onchange_account_id(self, cr, uid, ids, account_id=False, partner_id=False, context=None):
        account_obj = self.pool.get('account.account')
        partner_obj = self.pool.get('res.partner')
        fiscal_pos_obj = self.pool.get('account.fiscal.position')
        val = {}
        if account_id:
            res = account_obj.browse(cr, uid, account_id, context=context)
            tax_ids = res.tax_ids
            if tax_ids and partner_id:
                part = partner_obj.browse(cr, uid, partner_id, context=context)
                tax_id = fiscal_pos_obj.map_tax(cr, uid, part and part.property_account_position or False, tax_ids)[0]
            else:
                tax_id = tax_ids and tax_ids[0].id or False
            val['account_tax_id'] = tax_id
        return {'value': val}

    def _update_journal_check(self, cr, uid, journal_id, period_id, context=None):
        if context is None:
            context = {}
        if 'bypass_check' not in context:
            journal_obj = self.pool.get('account.journal')
            period_obj = self.pool.get('account.period')
            jour_period_obj = self.pool.get('account.journal.period')
            cr.execute('SELECT state FROM account_journal_period WHERE journal_id = %s AND period_id = %s', (journal_id, period_id))
            result = cr.fetchall()
            journal = journal_obj.browse(cr, uid, journal_id, context=context)
            period = period_obj.browse(cr, uid, period_id, context=context)
            for (state,) in result:
                if state == 'done':
                    raise osv.except_osv(_('Error!'), _('You can not add/modify entries in a closed period %s of journal %s.') % (period.name, journal.name))
            if not result:
                jour_period_obj.create(cr, uid, {
                    'name': (journal.code or journal.name)+':'+(period.name or ''),
                    'journal_id': journal.id,
                    'period_id': period.id
                })
        return True

    def _update_check(self, cr, uid, ids, context=None):
        done = {}
        for line in self.browse(cr, uid, ids, context=context):
            err_msg = _('Move name (id): %s (%s)') % (line.move_id.name, str(line.move_id.id))
            if line.move_id.state <> 'draft' and (not line.journal_id.entry_posted):
                raise osv.except_osv(_('Error!'), _('You cannot do this modification on a confirmed entry. You can just change some non legal fields or you must unconfirm the journal entry first.\n%s.') % err_msg)
            t = (line.journal_id.id, line.period_id.id)
            if t not in done:
                self._update_journal_check(cr, uid, line.journal_id.id, line.period_id.id, context)
                done[t] = True
        return True

    def onchange_date(self, cr, user, ids, date, context=None):
        """
        Returns a dict that contains new values and context
        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        res = {}
        if context is None:
            context = {}
        period_pool = self.pool.get('account.period')
        pids = period_pool.find(cr, user, date, context=context)
        if pids:
            res.update({'period_id':pids[0]})
            context = dict(context, period_id=pids[0])
        return {
            'value':res,
            'context':context,
        }

    def _check_moves(self, cr, uid, context=None):
        # use the first move ever created for this journal and period
        if context is None:
            context = {}
        cr.execute('SELECT id, state, name FROM account_move_consol WHERE journal_id = %s AND period_id = %s ORDER BY id limit 1', (context['journal_id'],context['period_id']))
        res = cr.fetchone()
        if res:
            if res[1] != 'draft':
                raise osv.except_osv(_('User Error!'),
                       _('The account move (%s) for centralisation ' \
                                'has been confirmed.') % res[2])
        return res

    def unlink(self, cr, uid, ids, context=None, check=True):
        if context is None:
            context = {}
        move_obj = self.pool.get('account.move.consol')
        self._update_check(cr, uid, ids, context)
        result = False
        move_ids = set()
        for line in self.browse(cr, uid, ids, context=context):
            move_ids.add(line.move_id.id)
            localcontext = dict(context)
            localcontext['journal_id'] = line.journal_id.id
            localcontext['period_id'] = line.period_id.id
            result = super(account_move_line_consol, self).unlink(cr, uid, [line.id], context=localcontext)
        move_ids = list(move_ids)
        if check and move_ids:
            move_obj.validate(cr, uid, move_ids, context=context)
        return result

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        if context is None:
            context={}
        move_obj = self.pool.get('account.move.consol')
        account_obj = self.pool.get('account.account')
        journal_obj = self.pool.get('account.journal')
        if isinstance(ids, (int, long)):
            ids = [ids]
        if vals.get('account_tax_id', False):
            raise osv.except_osv(_('Unable to change tax!'), _('You cannot change the tax, you should remove and recreate lines.'))
        if ('account_id' in vals) and not account_obj.read(cr, uid, vals['account_id'], ['active'])['active']:
            raise osv.except_osv(_('Bad Account!'), _('You cannot use an inactive account.'))

        affects_move = any(f in vals for f in ('account_id', 'journal_id', 'period_id', 'move_id', 'debit', 'credit', 'date'))

        if update_check and affects_move:
            self._update_check(cr, uid, ids, context)

        todo_date = None
        if vals.get('date', False):
            todo_date = vals['date']
            del vals['date']

        for line in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            if not ctx.get('journal_id'):
                if line.move_id:
                   ctx['journal_id'] = line.move_id.journal_id.id
                else:
                    ctx['journal_id'] = line.journal_id.id
            if not ctx.get('period_id'):
                if line.move_id:
                    ctx['period_id'] = line.move_id.period_id.id
                else:
                    ctx['period_id'] = line.period_id.id
            #Check for centralisation
            journal = journal_obj.browse(cr, uid, ctx['journal_id'], context=ctx)
            if journal.centralisation:
                self._check_moves(cr, uid, context=ctx)
        result = super(account_move_line_consol, self).write(cr, uid, ids, vals, context)

        if affects_move and check and not context.get('novalidate'):
            done = []
            for line in self.browse(cr, uid, ids):
                if line.move_id.id not in done:
                    done.append(line.move_id.id)
                    move_obj.validate(cr, uid, [line.move_id.id], context)
                    if todo_date:
                        move_obj.write(cr, uid, [line.move_id.id], {'date': todo_date}, context=context)
        return result

    def create(self, cr, uid, vals, context=None, check=True):
        account_obj = self.pool.get('account.account')
        tax_obj = self.pool.get('account.tax')
        move_obj = self.pool.get('account.move.consol')
        cur_obj = self.pool.get('res.currency')
        journal_obj = self.pool.get('account.journal')
        context = dict(context or {})
        if vals.get('move_id', False):
            move = self.pool.get('account.move.consol').browse(cr, uid, vals['move_id'], context=context)
            if move.company_id:
                vals['company_id'] = move.company_id.id
            if move.date and not vals.get('date'):
                vals['date'] = move.date
        if ('account_id' in vals) and not account_obj.read(cr, uid, [vals['account_id']], ['active'])[0]['active']:
            raise osv.except_osv(_('Bad Account!'), _('You cannot use an inactive account.'))
        if 'journal_id' in vals and vals['journal_id']:
            context['journal_id'] = vals['journal_id']
        if 'period_id' in vals and vals['period_id']:
            context['period_id'] = vals['period_id']
        if ('journal_id' not in context) and ('move_id' in vals) and vals['move_id']:
            m = move_obj.browse(cr, uid, vals['move_id'])
            context['journal_id'] = m.journal_id.id
            context['period_id'] = m.period_id.id
        #we need to treat the case where a value is given in the context for period_id as a string
        if 'period_id' in context and not isinstance(context.get('period_id', ''), (int, long)):
            period_candidate_ids = self.pool.get('account.period').name_search(cr, uid, name=context.get('period_id',''))
            if len(period_candidate_ids) != 1:
                raise osv.except_osv(_('Error!'), _('No period found or more than one period found for the given date.'))
            context['period_id'] = period_candidate_ids[0][0]
        if not context.get('journal_id', False) and context.get('search_default_journal_id', False):
            context['journal_id'] = context.get('search_default_journal_id')
        self._update_journal_check(cr, uid, context['journal_id'], context['period_id'], context)
        move_id = vals.get('move_id', False)
        journal = journal_obj.browse(cr, uid, context['journal_id'], context=context)
        vals['journal_id'] = vals.get('journal_id') or context.get('journal_id')
        vals['period_id'] = vals.get('period_id') or context.get('period_id')
        vals['date'] = vals.get('date') or context.get('date')
        if not move_id:
            if journal.centralisation:
                #Check for centralisation
                res = self._check_moves(cr, uid, context)
                if res:
                    vals['move_id'] = res[0]
            if not vals.get('move_id', False):
                if journal.sequence_id:
                    #name = self.pool.get('ir.sequence').next_by_id(cr, uid, journal.sequence_id.id)
                    v = {
                        'date': vals.get('date', time.strftime('%Y-%m-%d')),
                        'period_id': context['period_id'],
                        'journal_id': context['journal_id']
                    }
                    if vals.get('ref', ''):
                        v.update({'ref': vals['ref']})
                    move_id = move_obj.create(cr, uid, v, context)
                    vals['move_id'] = move_id
                else:
                    raise osv.except_osv(_('No Piece Number!'), _('Cannot create an automatic sequence for this piece.\nPut a sequence in the journal definition for automatic numbering or create a sequence manually for this piece.'))
        ok = not (journal.type_control_ids or journal.account_control_ids)
        if ('account_id' in vals):
            account = account_obj.browse(cr, uid, vals['account_id'], context=context)
            if journal.type_control_ids:
                type = account.user_type
                for t in journal.type_control_ids:
                    if type.code == t.code:
                        ok = True
                        break
            if journal.account_control_ids and not ok:
                for a in journal.account_control_ids:
                    if a.id == vals['account_id']:
                        ok = True
                        break
            # Automatically convert in the account's secondary currency if there is one and
            # the provided values were not already multi-currency
            if account.currency_id and 'amount_currency' not in vals and account.currency_id.id != account.company_id.currency_id.id:
                vals['currency_id'] = account.currency_id.id
                ctx = {}
                if 'date' in vals:
                    ctx['date'] = vals['date']
                vals['amount_currency'] = cur_obj.compute(cr, uid, account.company_id.currency_id.id,
                    account.currency_id.id, vals.get('debit', 0.0)-vals.get('credit', 0.0), context=ctx)
        if not ok:
            raise osv.except_osv(_('Bad Account!'), _('You cannot use this general account in this journal, check the tab \'Entry Controls\' on the related journal.'))

        result = super(account_move_line_consol, self).create(cr, uid, vals, context=context)
        # CREATE Taxes
        if vals.get('account_tax_id', False):
            del vals['account_tax_id']

        recompute = journal.env.recompute and context.get('recompute', True)
        if check and not context.get('novalidate') and (recompute or journal.entry_posted):
            tmp = move_obj.validate(cr, uid, [vals['move_id']], context)
            if journal.entry_posted and tmp:
                move_obj.button_validate(cr,uid, [vals['move_id']], context)
        return result

    def list_periods(self, cr, uid, context=None):
        ids = self.pool.get('account.period').search(cr,uid,[])
        return self.pool.get('account.period').name_get(cr, uid, ids, context=context)

    def list_journals(self, cr, uid, context=None):
        ng = dict(self.pool.get('account.journal').name_search(cr,uid,'',[]))
        ids = ng.keys()
        result = []
        for journal in self.pool.get('account.journal').browse(cr, uid, ids, context=context):
            result.append((journal.id,ng[journal.id],journal.type,
                bool(journal.currency),bool(journal.analytic_journal_id)))
        return result

class dym_journal_consolidation(orm.TransientModel):
    _name = 'dym.journal.consolidation'
    _description = 'Journal Consolidation '
 
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context:
            context = {}
        res = super(dym_journal_consolidation, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids = self._get_branch_ids(cr, uid, context)
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'branch_ids': fields.many2many('dym.branch', 'dym_journal_consolidation_branch_rel', 'dym_journal_consolidation_wizard_id', 'branch_id', 'Branches', required=True),
        'period_id': fields.many2one('account.period', 'Consolidation Period', required=True),
    }
    
    def get_group_company(self,cr,uid, ids, context=None):
        user_obj = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid)
        company = user_obj.company_id
        while company.parent_id:
            company = company.parent_id
        return company

    def transfer(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        period_obj = self.pool.get('account.period')
        data = self.read(cr, SUPERUSER_ID, ids)[0]
        branch_ids = data['branch_ids']
        period_id = data['period_id'][0]
        company = self.get_group_company(cr, uid, ids, context=context)
        journal_id = company.journal_consolidate_multi_company_id.id 
        if not company.journal_consolidate_multi_company_id:
            raise osv.except_osv(('Perhatian !'), ("Journal konsolidasi multi company belum diisi di %s!")%(company.name)) 
        period = period_obj.browse(cr, SUPERUSER_ID, period_id)
        branch = self.pool.get('dym.branch').browse(cr, SUPERUSER_ID, branch_ids)
        if period.company_id != company:
            raise osv.except_osv(('Perhatian !'), ("Period yang diisi harus periode grup company")) 
        date_start = datetime.strptime(period.date_start, DEFAULT_SERVER_DATE_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_stop = datetime.strptime(period.date_stop, DEFAULT_SERVER_DATE_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)  
        branch_period_ids = period_obj.search(cr, SUPERUSER_ID, [('company_id','in',branch.mapped('company_id').ids),('date_start','=',period.date_start),('date_stop','=',period.date_stop)])
        branch_period = period_obj.browse(cr, SUPERUSER_ID, branch_period_ids).filtered(lambda r: r.state == 'draft')
        if branch_period:
            raise osv.except_osv(('Perhatian !'), ("Period: %s company: %s belum di close")%(period.name,', '.join(branch_period.mapped('company_id.name'))))  
        name = ('Transfer jurnal entries branch %s periode %s - %s')%(', '.join(branch.mapped('name')),str(date_start),str(date_stop))
        date = time.strftime('%Y-%m-%d %H:%M:%S')

        move = {
            'name': '/',
            'ref': name,
            'journal_id': journal_id,
            'date': date,
            'period_id':period.id,
        }

        move_id = self.pool.get('account.move.consol').create(cr, SUPERUSER_ID, move, context=None)
        request = ("INSERT INTO account_move_line_consol (move_id,name,ref,account_id,credit,debit,branch_id,division,currency_id,product_id,product_uom_id,amount_currency,quantity,partner_id,tax_code_id,tax_amount,consolidation_move_line_id,eliminate_posted,journal_id,period_id,company_id,date,state,consol_entry) (SELECT %s as move_id, l.name as name, l.ref as ref, ac.group_account as account_id, l.credit as credit, l.debit as debit, l.branch_id as branch_id, l.division as division, l.currency_id as currency_id, l.product_id as product_id, l.product_uom_id as product_uom_id, l.amount_currency as amount_currency, l.quantity as quantity, l.partner_id as partner_id, l.tax_code_id as tax_code_id, l.tax_amount as tax_amount, l.id as consolidation_move_line_id, 'f' as eliminate_posted, %s as journal_id, %s as period_id, %s as company_id, %s as date, 'draft' as state, m.id as consol_entry FROM account_move_line l left join account_move m on l.move_id = m.id left join account_account_consol_rel ac_rel on ac_rel.parent_id = l.account_id left join account_account ac on ac.id = ac_rel.child_id and ac.type = 'consolidation' left join analytic_konsolidasi_analytic_rel anc_rel on anc_rel.analytic2_id = l.analytic_account_id left join account_analytic_account ang on ang.id = anc_rel.analytic_id and ang.company_id = %s WHERE (l.consolidate_posted = 'f' or  l.consolidate_posted is null) and m.id in (SELECT mx.id as move_ids FROM account_move_line lx left join account_move mx on lx.move_id = mx.id left join account_period ax on mx.period_id = ax.id WHERE ax.id in %s and lx.branch_id in %s and (lx.consolidate_posted = 'f' or  lx.consolidate_posted is null) and mx.state = 'posted' group by mx.id))")
        params = (move_id,journal_id,period.id,company.id,date,company.id,tuple(branch_period_ids),tuple(branch.ids))
        


        sql = """SELECT 
            %s as move_id, 
            l.name as name, 
            l.ref as ref, 
            ac.group_account as account_id, 
            l.credit as credit, 
            l.debit as debit, 
            l.branch_id as branch_id, 
            l.division as division, 
            l.currency_id as currency_id, 
            l.product_id as product_id, 
            l.product_uom_id as product_uom_id, 
            l.amount_currency as amount_currency, 
            l.quantity as quantity, 
            l.partner_id as partner_id, 
            l.tax_code_id as tax_code_id, 
            l.tax_amount as tax_amount, 
            l.id as consolidation_move_line_id, 
            'f' as eliminate_posted, 
            %s as journal_id, 
            %s as period_id, 
            %s as company_id, 
            %s as date, 
            'draft' as state, 
            m.id as consol_entry 
        FROM 
            account_move_line l 
            left join account_move m on l.move_id = m.id 
            left join account_account_consol_rel ac_rel on ac_rel.parent_id = l.account_id 
            left join account_account ac on ac.id = ac_rel.child_id and ac.type = 'consolidation' 
            left join analytic_konsolidasi_analytic_rel anc_rel on anc_rel.analytic2_id = l.analytic_account_id 
            left join account_analytic_account ang on ang.id = anc_rel.analytic_id and ang.company_id = %s 
        WHERE 
            (l.consolidate_posted = 'f' or  l.consolidate_posted is null) 
            and m.id in (
                SELECT mx.id as move_ids 
                FROM account_move_line lx 
                left join account_move mx on lx.move_id = mx.id 
                left join account_period ax on mx.period_id = ax.id 
                WHERE 
                ax.id in %s and 
                lx.branch_id in %s and 
                (lx.consolidate_posted = 'f' or  lx.consolidate_posted is null) 
                and mx.state = 'posted' 
                group by mx.id
            )"""


        cr.execute(sql, params)

        cr.execute(request, params)
        request = ("SELECT l.id as id, l.consolidation_move_line_id as consolidation_move_line_id FROM account_move_line_consol l WHERE l.move_id = %s group by id, consolidation_move_line_id")
        params = (move_id,)
        cr.execute(request,params)
        rows = cr.dictfetchall()
        if not rows:
            raise osv.except_osv(('Perhatian !'), ("Computer tidak menemukan baris jurnal konsolidasi yang dapat ditransfer, mohon diperiksa kembali mungkin data jurnal konsolidasi untuk period: '%s' di company '%s' sudah di transfer sebelumnya, atau memang tidak ada data jurnal pada periode tersebut yang dapat ditransfer (tidak ada transaksi).")%(period.name,', '.join(branch_period.mapped('company_id.name'))))
        consolidate_move_line_ids = []
        line_ids = []
        for row in rows:
            consolidate_move_line_ids.append(row['consolidation_move_line_id'])
            line = self.pool.get('account.move.line').browse(cr, uid, row['consolidation_move_line_id'])
            analytic_name = line.analytic_account_id.analytic_combination
            group_analytic_search = self.pool.get('account.analytic.account').search(cr, SUPERUSER_ID, [('analytic_combination','=',analytic_name),('company_id.parent_id','=',False)], limit=1)
            group_analytic = self.pool.get('account.analytic.account').browse(cr, SUPERUSER_ID, group_analytic_search)
            if not group_analytic:
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan analytic konsolidasi untuk analytic %s-%s!")%(line.analytic_account_id.analytic_combination, line.analytic_account_id.name))  
            self.pool.get('account.move.line.consol').write(cr, SUPERUSER_ID, row['id'], {'analytic_account_id':group_analytic.id}, context=context)
            line_ids.append(row['id'])
        context['bypass_check'] = True
        self.pool.get('account.move.line').write(cr, SUPERUSER_ID, consolidate_move_line_ids, {'consolidated':True}, context=context)
        self.pool.get('account.move.line.consol').write(cr, SUPERUSER_ID, line_ids, {'move_id':move_id}, context=context)
        del context['bypass_check']
        if company.journal_consolidate_multi_company_id.entry_posted:
            posted = self.pool.get('account.move.consol').post(cr, SUPERUSER_ID, [move_id], context=None)
        return True

class account_move_line(osv.osv):
    _inherit = "dym.branch"
    
    def _get_consolidate_status(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        branch = self.browse(cr, uid, ids, context=context)
        if 'period' in context and context['period']:
            period_obj = self.pool.get('account.period')
            period = period_obj.browse(cr, uid, context['period'])
            date_start = datetime.strptime(period.date_start, DEFAULT_SERVER_DATE_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_stop = datetime.strptime(period.date_stop, DEFAULT_SERVER_DATE_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)  
            branch_period_ids = period_obj.search(cr, SUPERUSER_ID, [('company_id','in',branch.mapped('company_id').ids),('date_start','=',period.date_start),('date_stop','=',period.date_stop),('state','=','done')])
            branch_unconsolidated = []
            if branch_period_ids:
                request = ("SELECT lx.branch_id as branch_id FROM account_move_line lx left join account_move mx on lx.move_id = mx.id left join account_period ax on mx.period_id = ax.id WHERE ax.id in %s and lx.branch_id in %s and (lx.consolidate_posted = 'f' or  lx.consolidate_posted is null) and mx.state = 'posted' group by lx.branch_id")

                params = (tuple(branch_period_ids),tuple(ids))
                cr.execute(request, params)
                rows = cr.dictfetchall()
                branch_unconsolidated = [row['branch_id'] for row in rows]
            company_period_draft_ids = period_obj.search(cr, SUPERUSER_ID, [('company_id','=',branch.mapped('company_id').ids),('date_start','=',period.date_start),('date_stop','=',period.date_stop),('state','=','draft')])
            company_period_draft = period_obj.browse(cr, SUPERUSER_ID, company_period_draft_ids).mapped('company_id').ids
            for br in branch:
                if br.company_id.id in company_period_draft:
                    res[br.id] = ('Period %s %s Belum di Close') % (period.name,br.company_id.name)
                elif br.id in branch_unconsolidated:
                    res[br.id] = 'Belum di Consolidate'
                else:
                    res[br.id] = 'Sudah di Consolidate'
        else:
            return {}
        return res

    _columns = {
        'consolidation_status': fields.function(_get_consolidate_status, string='Status', type='char')
    }

class account_move_line(osv.osv):
    _inherit = "account.move.line"
        
    _columns = {
        'consolidated' : fields.boolean(string='Consolidated', copy=False),
        'consolidate_posted' : fields.boolean(string='Consolidate Posted', copy=False)
    }

    def _update_journal_check(self, cr, uid, journal_id, period_id, context=None):
        if context is None:
            context = {}
        if 'bypass_check' not in context:
            journal_obj = self.pool.get('account.journal')
            period_obj = self.pool.get('account.period')
            jour_period_obj = self.pool.get('account.journal.period')
            cr.execute('SELECT state FROM account_journal_period WHERE journal_id = %s AND period_id = %s', (journal_id, period_id))
            result = cr.fetchall()
            journal = journal_obj.browse(cr, uid, journal_id, context=context)
            period = period_obj.browse(cr, uid, period_id, context=context)
            for (state,) in result:
                if state == 'done':
                    raise osv.except_osv(_('Error!'), _('You can not add/modify entries in a closed period %s of journal %s.') % (period.name, journal.name))
            if not result:
                jour_period_obj.create(cr, uid, {
                    'name': (journal.code or journal.name)+':'+(period.name or ''),
                    'journal_id': journal.id,
                    'period_id': period.id
                })
        return True