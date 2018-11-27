from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp

class dym_branch_config(models.Model):
    _inherit = 'dym.branch.config'
   
    dym_payment_request_account_id = fields.Many2one('account.journal', string='Journal Payment Request',help='Journal Untuk Payment Request')
    dym_other_receivable_account_id = fields.Many2one('account.journal', string='Journal Other Receivable',help='Journal Untuk Other Receivable')

    max_writeoff_payable = fields.Float('Maximum Writeoff Payable', digits=dp.get_precision('Account'))
    writeoff_payable_account_id = fields.Many2one('account.account', string='Writeoff Payable Account')
    max_writeoff_receivable = fields.Float('Maximum Writeoff Receivable', digits=dp.get_precision('Account'))
    writeoff_receivable_account_id = fields.Many2one('account.account', string='Writeoff Receivable Account')
   
      