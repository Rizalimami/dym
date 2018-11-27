# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class FiscalYearClose(models.TransientModel):
    _inherit = "account.fiscalyear.close"

    @api.multi
    def data_save(self):
        """
        This function close account fiscalyear and create entries in new fiscalyear
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Account fiscalyear close state’s IDs

        """
        def _reconcile_fy_closing():
            """
            This private function manually do the reconciliation on the account_move_line given as `ids´, and directly
            through psql. It's necessary to do it this way because the usual `reconcile()´ function on account.move.line
            object is really resource greedy (not supposed to work on reconciliation between thousands of records) and
            it does a lot of different computation that are useless in this particular case.
            """
            #check that the reconcilation concern journal entries from only one company
            self.env.cr.execute('select distinct(company_id) from account_move_line where id in %s',(tuple(ids),))
            if len(cr.fetchall()) > 1:
                raise osv.except_osv(_('Warning!'), _('The entries to reconcile should belong to the same company.'))
            r_id = self.env['account.move.reconcile'].create({'type': 'auto', 'opening_reconciliation': True})
            self.env.cr.execute('update account_move_line set reconcile_id = %s where id in %s',(r_id, tuple(ids),))
            # reconcile_ref deptends from reconcile_id but was not recomputed
            MoveLine._store_set_values(['reconcile_ref'])
            MoveLine.invalidate_cache(['reconcile_id'], ids)
            return r_id

        self.ensure_one()

        Period = self.env['account.period']
        FiscalYear = self.env['account.fiscalyear']
        Journal = self.env['account.journal']
        Move = self.env['account.move']
        MoveLine = self.env['account.move.line']
        Account = self.env['account.account']
        JournalPeriod = self.env['account.journal.period']
        Currency = self.env['res.currency']

        fy_id = self.fy_id.id

        self.env.cr.execute("SELECT id FROM account_period WHERE date_stop < (SELECT date_start FROM account_fiscalyear WHERE id = %s)", (str(self.fy2_id.id),))
        fy_period_set = ','.join(map(lambda id: str(self.id), self.env.cr.fetchall()))
        self.env.cr.execute("SELECT id FROM account_period WHERE date_start > (SELECT date_stop FROM account_fiscalyear WHERE id = %s)", (str(fy_id),))
        fy2_period_set = ','.join(map(lambda id: str(self.id), self.env.cr.fetchall()))

        if not fy_period_set or not fy2_period_set:
            raise osv.except_osv(_('User Error!'), _('The periods to generate opening entries cannot be found.'))

        period = self.period_id
        new_fyear = self.fy2_id
        old_fyear = self.fy_id

        new_journal = self.journal_id
        company_id = new_journal.company_id.id

        if not new_journal.default_credit_account_id or not new_journal.default_debit_account_id:
            raise osv.except_osv(_('User Error!'),
                    _('The journal must have default credit and debit account.'))
        if (not new_journal.centralisation) or new_journal.entry_posted:
            raise osv.except_osv(_('User Error!'),
                    _('The journal must have centralized counterpart without the Skipping draft state option checked.'))

        #delete existing move and move lines if any
        move_ids = Move.search([('journal_id', '=', new_journal.id), ('period_id', '=', period.id)])
        print "move_ids======>",move_ids
        if move_ids:
            move_line_ids = MoveLine.search([('move_id', 'in', move_ids.ids)])
            MoveLine._remove_move_reconcile(move_line_ids.ids, opening_reconciliation=True)
            MoveLine.unlink()
            move_ids.unlink()

            # MoveLine._remove_move_reconcile(move_line_ids, opening_reconciliation=True)
            # MoveLine.unlink(move_line_ids)
            # Move.unlink(move_ids)

        self.env.cr.execute("SELECT id FROM account_fiscalyear WHERE date_stop < %s", (str(new_fyear.date_start),))
        result = self.env.cr.dictfetchall()
        fy_ids = [x['id'] for x in result]
        query_line = MoveLine._query_get(obj='account_move_line', context={'fiscalyear':fy_ids})
        #create the opening move

        move_id = Move.search([('period_id','=',period.id),('date','=',period.date_start),('journal_id','=',new_journal.id)])
        if not move_id:
            vals = {
                'name': '/',
                'ref': '',
                'period_id': period.id,
                'date': period.date_start,
                'journal_id': new_journal.id,
            }
            move_id = Move.create(vals)

        print "move_id===>",move_id

        #1. report of the accounts with defferal method == 'unreconciled'
        self.env.cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type = t.id)
            WHERE a.active
              AND a.type not in ('view', 'consolidation')
              AND a.company_id = %s
              AND t.close_method = %s''', (company_id, 'unreconciled', ))
        account_ids = map(lambda x: x[0], self.env.cr.fetchall())

        # print "account_ids===>",account_ids
        # SQL = """
        #     INSERT INTO account_move_line (
        #         name, create_uid, create_date, write_uid, write_date,
        #         statement_id, journal_id, currency_id, date_maturity,
        #         partner_id, blocked, credit, state, debit,
        #         ref, account_id, period_id, date, move_id, amount_currency,
        #         quantity, product_id, company_id, analytic_4, analytic_2, analytic_3, analytic_1)
        #     (SELECT 
        #         name, create_uid, create_date, write_uid, write_date,
        #         statement_id, %s,currency_id, date_maturity, partner_id,
        #         blocked, credit, 'draft', debit, ref, account_id,
        #         %s, (%s) AS date, %s, amount_currency, quantity, product_id, company_id,
        #         analytic_4, analytic_2, analytic_3, analytic_1 
        #     FROM 
        #         account_move_line
        #     WHERE 
        #         account_id IN %s AND """ + query_line + """ AND 
        #         reconcile_id IS NULL)"""
        # self.env.cr.execute(SQL,(new_journal.id, period.id, period.date_start, move_id.id, tuple(account_ids),))

        if account_ids:
            self.env.cr.execute('''
                INSERT INTO account_move_line (
                     name, create_uid, create_date, write_uid, write_date,
                     statement_id, journal_id, currency_id, date_maturity,
                     partner_id, blocked, credit, state, debit,
                     ref, account_id, period_id, date, move_id, amount_currency,
                     quantity, product_id, company_id, 
                     analytic_4, analytic_2, analytic_3, analytic_1)
                  (SELECT name, create_uid, create_date, write_uid, write_date,
                     statement_id, %s,currency_id, date_maturity, partner_id,
                     blocked, credit, 'draft', debit, ref, account_id,
                     %s, (%s) AS date, %s, amount_currency, quantity, product_id, company_id, 
                     analytic_4, analytic_2, analytic_3, analytic_1
                   FROM account_move_line
                   WHERE account_id IN %s
                     AND ''' + query_line + '''
                     AND reconcile_id IS NULL)''', (new_journal.id, period.id, period.date_start, move_id.id, tuple(account_ids),))

            #We have also to consider all move_lines that were reconciled
            #on another fiscal year, and report them too
            self.env.cr.execute('''
                INSERT INTO account_move_line (
                     name, create_uid, create_date, write_uid, write_date,
                     statement_id, journal_id, currency_id, date_maturity,
                     partner_id, blocked, credit, state, debit,
                     ref, account_id, period_id, date, move_id, amount_currency,
                     quantity, product_id, company_id, 
                     analytic_4, analytic_2, analytic_3, analytic_1)
                  (SELECT
                     b.name, b.create_uid, b.create_date, b.write_uid, b.write_date,
                     b.statement_id, %s, b.currency_id, b.date_maturity,
                     b.partner_id, b.blocked, b.credit, 'draft', b.debit,
                     b.ref, b.account_id, %s, (%s) AS date, %s, b.amount_currency,
                     b.quantity, b.product_id, b.company_id, 
                     b.analytic_4, b.analytic_2, b.analytic_3, b.analytic_1
                     FROM account_move_line b
                     WHERE b.account_id IN %s
                       AND b.reconcile_id IS NOT NULL
                       AND b.period_id IN ('''+fy_period_set+''')
                       AND b.reconcile_id IN (SELECT DISTINCT(reconcile_id)
                                          FROM account_move_line a
                                          WHERE a.period_id IN ('''+fy2_period_set+''')))''', (new_journal.id, period.id, period.date_start, move_id.id, tuple(account_ids),))
            self.invalidate_cache()

        #2. report of the accounts with defferal method == 'detail'
        self.env.cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type = t.id)
            WHERE a.active
              AND a.type not in ('view', 'consolidation')
              AND a.company_id = %s
              AND t.close_method = %s''', (company_id, 'detail', ))
        account_ids = map(lambda x: x[0], self.env.cr.fetchall())

        if account_ids:
            self.env.cr.execute('''
                INSERT INTO account_move_line (
                     name, create_uid, create_date, write_uid, write_date,
                     statement_id, journal_id, currency_id, date_maturity,
                     partner_id, blocked, credit, state, debit,
                     ref, account_id, period_id, date, move_id, amount_currency,
                     quantity, product_id, company_id,
                     analytic_4, analytic_2, analytic_3, analytic_1)
                  (SELECT name, create_uid, create_date, write_uid, write_date,
                     statement_id, %s,currency_id, date_maturity, partner_id,
                     blocked, credit, 'draft', debit, ref, account_id,
                     %s, (%s) AS date, %s, amount_currency, quantity, product_id, company_id,
                     analytic_4, analytic_2, analytic_3, analytic_1
                   FROM account_move_line
                   WHERE account_id IN %s
                     AND ''' + query_line + ''')
                     ''', (new_journal.id, period.id, period.date_start, move_id.id, tuple(account_ids),))
            self.invalidate_cache()

        #3. report of the accounts with defferal method == 'balance'
        self.env.cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type = t.id)
            WHERE a.active
              AND a.type not in ('view', 'consolidation')
              AND a.company_id = %s
              AND t.close_method = %s''', (company_id, 'balance', ))
        account_ids = map(lambda x: x[0], self.env.cr.fetchall())

        query_1st_part = """
                INSERT INTO account_move_line (
                     debit, credit, name, date, move_id, journal_id, period_id,
                     account_id, currency_id, amount_currency, company_id, analytic_4, analytic_2, analytic_3, analytic_1, state) VALUES
        """
        query_2nd_part = ""
        query_2nd_part_args = []
        ctx = dict(self.env.context or {})
        ctx.update({
            'fiscalyear':fy_id
        })
        for account in Account.with_context(ctx).browse(account_ids):
            company_currency_id = self.env.user.company_id.currency_id
            if not Currency.is_zero(abs(account.balance)):
                if query_2nd_part:
                    query_2nd_part += ','
                query_2nd_part += "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                query_2nd_part_args += (account.balance > 0 and account.balance or 0.0,
                       account.balance < 0 and -account.balance or 0.0,
                       self.report_name,
                       period.date_start,
                       move_id.id,
                       new_journal.id,
                       period.id,
                       account.id,
                       account.currency_id and account.currency_id.id or None,
                       account.foreign_balance if account.currency_id else 0.0,
                       account.company_id.id,
                       'draft')
        if query_2nd_part:

            print "query_1st_part======>",query_1st_part
            print "query_2nd_part======>",query_2nd_part
            print "query_2nd_part_args=>",query_2nd_part_args

            self.env.cr.execute(query_1st_part + query_2nd_part, tuple(query_2nd_part_args))
            self.invalidate_cache()

        #validate and centralize the opening move
        Move.validate([move_id])

        #reconcile all the move.line of the opening move
        ids = MoveLine.search([('journal_id', '=', new_journal.id),
            ('period_id.fiscalyear_id','=',new_fyear.id)])
        if ids:
            reconcile_id = _reconcile_fy_closing()
            #set the creation date of the reconcilation at the first day of the new fiscalyear, in order to have good figures in the aged trial balance
            self.env['account.move.reconcile'].write([reconcile_id], {'create_date': new_fyear.date_start})

        #create the journal.period object and link it to the old fiscalyear
        new_period = self.period_id.id
        ids = JournalPeriod.search([('journal_id', '=', new_journal.id), ('period_id', '=', new_period)])
        if not ids:
            ids = [JournalPeriod.create({
                   'name': (new_journal.name or '') + ':' + (period.code or ''),
                   'journal_id': new_journal.id,
                   'period_id': period.id
               })]
        self.env.cr.execute('UPDATE account_fiscalyear ' \
                    'SET end_journal_period_id = %s ' \
                    'WHERE id = %s', (ids[0], old_fyear.id))
        # FiscalYear.invalidate_cache(['end_journal_period_id'], [old_fyear.id])
        FiscalYear.invalidate_cache()

        return {'type': 'ir.actions.act_window_close'}

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
