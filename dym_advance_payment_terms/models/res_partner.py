import time
from datetime import datetime
from openerp import models, fields, api

class Partner(models.Model):
    _inherit = "res.partner"

    advanced_payment_terms = fields.Boolean('Advanced Payment Terms', help='Check if the amount due is due on holiday, the due date of the debt is advanced.')
