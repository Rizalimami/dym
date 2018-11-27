from openerp import models, fields, api, _, SUPERUSER_ID
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError, RedirectWarning

class dym_reimbursed(models.Model):
    _inherit = "dym.reimbursed"

    voucher_reimbursed_ids = fields.One2many('voucher.reimbursed.line', 'reimbursed_id', string='Voucher Reimburse')

class VoucherReimburseLine(models.Model):
    _name = 'voucher.reimbursed.line'

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('request', 'Requested'),
        ('approved', 'Approved'),
        ('req2ho', 'Requested to HO'), #Saat dipanggil oleh tranfer request
        ('hoapproved', 'HO Approved'), #Saat orang HO pencet oleh tranfer request
        ('horejected', 'HO Rejected'), #Saat orang HO pencet oleh tranfer request
        ('paid', 'HO Paid'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ]   

    reimbursed_id = fields.Many2one('dym.reimbursed', string='Reimburse ID', domain="[('state','=','horejected'),('voucher_reimbursed_ids','=',False)]")
    voucher_id = fields.Many2one('account.voucher', string='Voucher ID')
    state = fields.Selection(STATE_SELECTION, related="reimbursed_id.state", string='State', readonly=True,default='draft')
    date_request = fields.Date(string="Date Requested", related="reimbursed_id.date_request", required=True,readonly=True,default=fields.Date.context_today)
    amount_total = fields.Float(string='Total Amount', related="reimbursed_id.amount_total", digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    date_horejected = fields.Date(string="Date HO Rejected", related="reimbursed_id.date_horejected", )

    # @api.onchange('reimbursed_id')
    # def onchange_reimbursed_id(self):
    #     if self.reimbursed_id:
    #         line_values = {}
    #         for rl in self.reimbursed_id.line_ids:
    #             if not rl.account_id.id in line_values:
    #                 line_values[rl.account_id.id] = rl.amount
    #             else:
    #                 line_values[rl.account_id.id] += rl.amount
    #             print "--->",rl.account_id.id,rl.amount

    #         print line_values


