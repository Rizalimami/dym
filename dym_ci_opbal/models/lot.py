from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    opbal = fields.Boolean('Opbal', default=False)
