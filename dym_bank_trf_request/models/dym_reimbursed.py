from openerp.tools.translate import _
from openerp import models, fields, api

class dym_reimbursed(models.Model):
    _inherit = "dym.reimbursed"

    transfer_request_id = fields.Many2one('bank.trf.request')
    date_hoapprove = fields.Date(string="Date HO Approved")
    date_horejected = fields.Date(string="Date HO Rejected")