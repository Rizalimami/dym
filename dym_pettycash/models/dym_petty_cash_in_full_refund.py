import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.osv import orm
from openerp.addons.dym_base import DIVISION_SELECTION

class dym_pettycash_in_full_refund_reason(models.Model):
    _name = "dym.pettycash.in.full.refund.reason"
    _description ="Petty cash in full refund reasons"
    _order = "sequence"
    
    name = fields.Char('Reason')
    notes = fields.Text('Description')
    sequence = fields.Integer(string='Sequence', default=0,
        help="Gives the sequence of this line when displaying the invoice.")
