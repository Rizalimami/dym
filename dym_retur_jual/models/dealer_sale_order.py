import time
from datetime import datetime
from openerp import fields, models

class DealerSaleOrder(models.Model):
    _inherit = "dealer.sale.order"      

    is_returned = fields.Boolean(string='Is Returned', default=False)
    return_id = fields.Many2one("dym.retur.jual", string="Return ID")
    return_oos = fields.Char(string='Return OOS State', related="return_id.oos_state", store=True)
