from openerp import models, fields, api

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    _description = 'Account Invoice'

    transfer_request_id = fields.Many2one('bank.trf.request')