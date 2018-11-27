from datetime import datetime
from openerp import models, fields, api, _

class AccountVoucher(models.Model):
    _inherit = "account.voucher"

    clearing_id = fields.Many2one('dym.clearing.giro', string='Clearing ID')

    @api.multi
    def _check_auto_debit(self):
        AutoClearing = self.env['auto.clearing']
        ClearingGiro = self.env['dym.clearing.giro']
        now = datetime.now().strftime('%Y-%m-%d')
        for voucher in self.search([('payment_method','=','auto_debit'),('state','=','approved'),('auto_debit_date','<=',now)]):
            voucher.clearing_bank = False
            try:
                voucher.signal_workflow('confirm_payment')
            except:
                pass