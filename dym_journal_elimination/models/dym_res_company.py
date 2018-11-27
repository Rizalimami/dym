import time
from datetime import datetime
from openerp import models, fields, api

class res_company(models.Model):
    _inherit = "res.company"
    
    journal_consolidate_multi_company_id = fields.Many2one('account.journal',string="Journal Consolidate Multi Company",domain="[('type','!=','view')]",help="Journal ini dibutuhkan dalam transaksi journal konsolidasi")
    journal_eliminate_multi_company_id = fields.Many2one('account.journal',string="Journal Eliminate Multi Company",domain="[('type','!=','view')]",help="Journal ini dibutuhkan dalam transaksi journal eliminasi")

    account_elimination_line = fields.One2many('dym.account.elimination.line','company_id','Account Elimination Filter')
    account_fields_report_line = fields.One2many('dym.account.fields.report.line','company_id','Account Elimination Fields Report')
    account_report_intercom_line = fields.One2many('dym.account.report.intercom.line','company_id','Account Intercom. Report')
    account_elimination_diff_id = fields.Many2one('account.account','Account Elimination Diff')

class dym_account_elimination_line(models.Model):
    _name = 'dym.account.elimination.line'

    company_id = fields.Many2one('res.company','Company ID')
    account_id = fields.Many2one('account.account','Account')

    @api.model
    def create(self,vals):
        account = self.env['account.account'].browse(vals['account_id'])
        account.is_intercom = True
        return super(dym_account_elimination_line, self).create(vals)
        
    @api.multi
    def write(self,vals):
        self.account_id.is_intercom = False
        account = self.env['account.account'].browse(vals['account_id'])
        account.is_intercom = True
        return super(dym_account_elimination_line, self).write(vals)

    @api.multi
    def unlink(self):
        self.account_id.is_intercom = False
        return super(dym_account_elimination_line, self).unlink()

class dym_account_fields_report_line(models.Model):
    _name = 'dym.account.fields.report.line'

    company_id = fields.Many2one('res.company','Company ID')
    account_id = fields.Many2one('account.account','Account')
    credit = fields.Boolean('Credit')

class dym_account_intercom_report_line(models.Model):
    _name = 'dym.account.report.intercom.line'

    company_id = fields.Many2one('res.company','Company ID')
    account_left_id = fields.Many2one('account.account','Account Left')
    account_right_id = fields.Many2one('account.account','Account Right')
  
class account_account(models.Model):
    _inherit = 'account.account'

    is_intercom = fields.Boolean("Is Intercom")
