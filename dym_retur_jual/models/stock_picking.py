import time
from datetime import datetime
from openerp import fields, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_returned = fields.Boolean(string='Is Returned')
    return_id = fields.Many2one("dym.retur.jual", string="Return ID")
    return_oos = fields.Char(string='Return OOS State', related="return_id.oos_state", store=True)
