from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api

class account_voucher(models.Model):
    _inherit = "account.voucher"


    @api.multi
    def get_journal_balance(self, branch_id=None, journal_id=None):
        if not journal_id or not branch_id:
            return 0
        journal = self.env['account.journal'].browse([journal_id])
        aa_obj = self.env['account.analytic.account']
        start_date = fields.Date.context_today(self)
        sql_query = ''
        analytic_branch = aa_obj.search([('segmen','=',3),('branch_id','=',branch_id),('type','=','normal'),('state','not in',('close','cancelled'))])
        analytic_cc = aa_obj.search([('segmen','=',4),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',analytic_branch.ids)])
        sql_query = ' AND l.analytic_account_id in %s' % str(tuple(analytic_cc.ids)).replace(',)', ')')
        bank_balance = journal.default_credit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=True,sql_query=sql_query).balance or journal.default_debit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=True,sql_query=sql_query).balance
        today_balance = journal.default_credit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=False,sql_query=sql_query).balance or journal.default_debit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=False,sql_query=sql_query).balance
        return bank_balance + today_balance

    @api.multi
    @api.depends('journal_id')
    def _get_balance(self):
        aa_obj = self.env['account.analytic.account']
        start_date = fields.Date.context_today(self)
        for rec in self:
            bank_balance = 0
            today_balance = 0
            branch_id = rec.branch_id
            if rec.journal_id:            
                sql_query = ''
                if branch_id:
                    analytic_branch = aa_obj.search([('segmen','=',3),('branch_id','=',branch_id.id),('type','=','normal'),('state','not in',('close','cancelled'))])
                    analytic_cc = aa_obj.search([('segmen','=',4),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',analytic_branch.ids)])
                    sql_query = ' AND l.analytic_account_id in %s' % str(tuple(analytic_cc.ids)).replace(',)', ')')
                bank_balance = rec.journal_id.default_credit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=True,sql_query=sql_query).balance or rec.journal_id.default_debit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=True,sql_query=sql_query).balance
                today_balance = rec.journal_id.default_credit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=False,sql_query=sql_query).balance or rec.journal_id.default_debit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=False,sql_query=sql_query).balance
            rec.balance = bank_balance + today_balance

    current_balance = fields.Float(compute=_get_balance, string='Balance', readonly=True) 

    @api.onchange('account_id')
    def onchange_to_get_analytic(self):
        aa_obj = self.env['account.analytic.account']
        af_obj = self.env['analytic.account.filter']
        if self.inter_branch_id and self.inter_branch_division and self.account_id:
            analytic_filter = af_obj.search([('account_id','=',self.account_id.id),('branch_type','=',self.inter_branch_id.branch_type)])
            if analytic_filter:
                analytic_1, analytic_2, analytic_3, analytic_4 = aa_obj.get_analytical(self.inter_branch_id.id, analytic_filter.bisnis_unit.name, False, 4, analytic_filter.cost_center)
            else:
                analytic_1, analytic_2, analytic_3, analytic_4 = aa_obj.get_analytical(self.inter_branch_id.id, self.inter_branch_division, False, 4, 'General')
            self.analytic_1 = analytic_1
            self.analytic_2 = analytic_2
            self.analytic_3 = analytic_3
            self.analytic_4 = analytic_4
