from openerp import models, fields, api
from openerp.exceptions import Warning as UserError, RedirectWarning

class dym_bank_transfer(models.Model):
    _inherit = 'dym.bank.transfer'

    bank_trf_advice_id = fields.Many2one('bank.trf.advice',string="Transfer Advice")
    bank_trf_request_ids = fields.One2many('bank.trf.request', 'transfer_id')
