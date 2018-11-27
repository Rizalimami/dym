from openerp import models, fields, api, _

class dym_branch_config(models.Model):
    _inherit = 'dym.branch.config'
   
    dym_advance_payment_account_id = fields.Many2one('account.account', string='Account Advance Payment',help='Account Piutang untuk Advance Payment')
    advance_payment_hutang_lain = fields.Many2one('account.account', string="Account Advance Payment Hutang Lain")
