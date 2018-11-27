from datetime import datetime
from openerp import models, fields, api, _

class AccountVoucher(models.Model):
    _inherit = "account.voucher"

    clearing_id = fields.Many2one('dym.clearing.giro', string='Clearing ID')

    def _check_auto_debit(self, cr, uid, ids=False, context=None):
        return self.check_auto_debit(cr, uid, ids, context=context)

    @api.multi
    def check_auto_debit(self):
        AutoClearing = self.env['auto.clearing']
        ClearingGiro = self.env['dym.clearing.giro']
        now = datetime.now().strftime('%Y-%m-%d')
        for voucher in self.search([('payment_method','=','auto_debit'),('state','in',['approved']),('auto_debit_date','<=',now)]):
            voucher.clearing_bank = False
            try:
                voucher.signal_workflow('confirm_payment')
            except:
                pass

        clearing_search = ClearingGiro.search([('state','=','draft'),('move_id','!=',False)])
        clearing_ids = [c.id for c in clearing_search if c.move_id.model=='account.voucher' and c.move_id.transaction_id]
        # for clearing_id in ClearingGiro.search([('state','=','draft'),('move_id','!=',False)]):
        for clearing_id in ClearingGiro.browse(clearing_ids):
            move_id = clearing_id.move_id
            # if not move_id.model=='account.voucher' or not move_id.transaction_id:
            #     continue
            # voucher_id = self.env['account.voucher'].browse(move_id.transaction_id)
            voucher_id = self.env['account.voucher'].search([('id','=',move_id.transaction_id),('payment_method','=','auto_debit')])
            if not voucher_id:
                continue
            try:
                clearing_id.confirm_clearing()
                # if voucher_id.payment_method=='auto_debit':
                #     clearing_id.confirm_clearing()
            except:
                pass