from openerp import models, fields, api, SUPERUSER_ID
from openerp.osv import osv
from openerp.tools.translate import _

class StockMove(models.Model):
    _inherit = "stock.move"



    @api.model
    def _get_parent_name(self):
    	for rec in self:
	    	if rec.picking_id and rec.picking_id.name:
	    		rec.parent_name = rec.picking_id.name[:4]
	    	else:
	    		rec.parent_name = 'N/A'

    parent_name = fields.Char('Parent Name', compute='_get_parent_name')

