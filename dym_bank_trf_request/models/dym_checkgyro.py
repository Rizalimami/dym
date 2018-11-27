import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError, RedirectWarning

class dym_checkgyro_line(models.Model):
    _inherit = "dym.checkgyro.line"
    _description = "Cheque or Giro Book Pages"

    advice_id = fields.Many2one('bank.trf.advice', string="Bank Transfer Advice")
