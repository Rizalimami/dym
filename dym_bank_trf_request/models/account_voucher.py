from openerp import models, fields, api

class account_voucher(models.Model):
    _inherit = 'account.voucher'
    _description = 'Account Voucher'

    @api.multi
    @api.depends('fully_paid','state')
    def _is_fully_paid(self):
        for voucher in self:
            if voucher.state == 'draft' or voucher.fully_paid==True:
                continue

            avls = self.env['account.voucher.line'].search_read([('move_line_id','=',voucher.number)],['amount_unreconciled','amount_original','amount','voucher_id'])
            tot_amount_unreconciled = 0.0
            tot_amount_original = 0.0
            tot_amount = 0.0
            for avl in avls:
                if tot_amount_unreconciled != avl['amount_unreconciled']:
                    tot_amount_unreconciled = avl['amount_unreconciled']
                if tot_amount_original != avl['amount_original']:
                    tot_amount_original = avl['amount_original']
                tot_amount += avl['amount']
            if tot_amount > 0 and tot_amount_unreconciled == tot_amount:
                voucher.fully_paid = True
            else:
                voucher.fully_paid = False

    fully_paid = fields.Boolean(compute='_is_fully_paid', string='Fully Paid', store=False, track_visibility='always')
    transfer_request_id = fields.Many2one('bank.trf.request')