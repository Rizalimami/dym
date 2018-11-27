from datetime import datetime, timedelta
from openerp.osv import osv, fields
from openerp.tools.translate import _

class bank_statement(osv.osv):
    _inherit = 'account.bank.statement'
    
    _columns = {
        'confirm_uid':fields.many2one('res.users',string="Closed by"),
        'confirm_date':fields.datetime('Closed on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),     
        'branch_id' : fields.many2one('dym.branch', 'Branch', required=True),
        'division':fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=True),   
    }

    def create(self,cr,uid,vals,context=None):
        vals['date'] = datetime.today()
        res = super(bank_statement,self).create(cr,uid,vals,context=None)
        return res
    
    def button_cancel(self, cr, uid, ids, context=None):
        vals = super(bank_statement,self).button_cancel(cr,uid,ids,context=None)
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})
        return vals  
      
    def button_confirm_cash(self, cr, uid, ids, context=None): 
        vals = super(bank_statement,self).button_confirm_cash(cr,uid,ids,context=None)
        self.write(cr,uid,ids,{'date':datetime.today(),'confirm_uid':uid,'confirm_date':datetime.now()})
        return vals            

    def _prepare_move(self, cr, uid, st_line, st_line_number, context=None):
        res = super(bank_statement,self)._prepare_move(cr, uid, st_line, st_line_number, context=context)
        res['transaction_id'] = st_line.statement_id.id
        res['model'] = st_line.statement_id.__class__.__name__
        return res

    def _prepare_move_line_vals(self, cr, uid, st_line, move_id, debit, credit, currency_id=False,
                amount_currency=False, account_id=False, partner_id=False, context=None):
        res = super(bank_statement,self)._prepare_move_line_vals(cr, uid, st_line, move_id, debit, credit, currency_id=currency_id, amount_currency=amount_currency, account_id=account_id, partner_id=partner_id, context=context)
        res['analytic_account_id'] = st_line.analytic_4.id
        return res

    def button_confirm_bank(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                continue

            self.balance_check(cr, uid, st.id, journal_type=j_type, context=context)
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error!'), _('Please verify that an account is defined in the journal.'))
            for line in st.move_line_ids:
                if line.state != 'valid':
                    raise osv.except_osv(_('Error!'), _('The account entries lines are not in valid state.'))
            move_ids = []
            for st_line in st.line_ids:
                if not st_line.amount:
                    continue
                if st_line.account_id and not st_line.journal_entry_id.id:
                    vals = {
                        'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                        'credit': st_line.amount > 0 and st_line.amount or 0.0,
                        'account_id': st_line.account_id.id,
                        'name': st_line.name,
                        'analytic_account_id': st_line.analytic_4.id,
                        'branch_id': st.branch_id.id,
                        'division': st.division,
                    }
                    self.pool.get('account.bank.statement.line').process_reconciliation(cr, uid, st_line.id, [vals], context=context)
                elif not st_line.journal_entry_id.id:
                    raise osv.except_osv(_('Error!'), _('All the account entries lines must be processed in order to close the statement.'))
                move_ids.append(st_line.journal_entry_id.id)
            if move_ids:
                self.pool.get('account.move').post(cr, uid, move_ids, context=context)
            self.message_post(cr, uid, [st.id], body=_('Statement %s confirmed, journal items were created.') % (st.name,), context=context)
        self.link_bank_to_partner(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state': 'confirm', 'closing_date': time.strftime("%Y-%m-%d %H:%M:%S"), 'date':datetime.today(), 'confirm_uid':uid, 'confirm_date':datetime.now()}, context=context)

class bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'

    def _get_analytic_company(self,cr,uid,context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_bank_transfer-1] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    _columns = {
        'analytic_1': fields.many2one('account.analytic.account','Account Analytic Company'),
        'analytic_2': fields.many2one('account.analytic.account','Account Analytic Bisnis Unit'),
        'analytic_3': fields.many2one('account.analytic.account','Account Analytic Branch'),
        'analytic_4': fields.many2one('account.analytic.account','Account Analytic Cost Center'),           
    }

    _defaults = {
        'analytic_1':_get_analytic_company,
    }

    def get_currency_rate_line(self, cr, uid, st_line, currency_diff, move_id, context=None):
        res = super(bank_statement_line,self).get_currency_rate_line(cr, uid, st_line, currency_diff, move_id, context=context)
        res['branch_id'] = st_line.statement_id.branch_id.id
        res['division'] = st_line.statement_id.division
        res['analytic_account_id'] = st_line.analytic_4.id
        return res

    def _get_exchange_lines(self, cr, uid, st_line, mv_line, currency_diff, currency_id, move_id, context=None):
        res = super(bank_statement_line,self)._get_exchange_lines(cr, uid, st_line, mv_line, currency_diff, currency_id, move_id, context=context)
        res[0]['analytic_account_id'] = mv_line.analytic_account_id.id
        res[0]['branch_id'] = mv_line.branch_id.id
        res[0]['division'] = mv_line.division
        res[1]['analytic_account_id'] = st_line.analytic_4.id
        res[1]['branch_id'] = st_line.statement_id.branch_id.id
        res[1]['division'] = st_line.statement_id.division
        return res
