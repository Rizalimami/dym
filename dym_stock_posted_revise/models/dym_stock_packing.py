from openerp import models, fields, api, _, SUPERUSER_ID
import time
from datetime import datetime
from openerp.osv import osv
import string
import openerp.addons.decimal_precision as dp

class dym_stock_packing(models.Model):
    _inherit = "dym.stock.packing"
    _description = "Stock Packing"

    revision_note = fields.Text('Revision Notes')
