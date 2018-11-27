##############################################################################
#
#    Sipo Cloud Service
#    Copyright (C) 2015.
#
##############################################################################

import openerp.addons.decimal_precision as dp
from openerp import api, fields, models, _

class SipoProductCostWarehouse(models.Model):
	_name = 'product.cost.warehouse'
	_description = 'Product Cost Per Warehouse'

	_rec_name = 'product_id'

	product_id = fields.Many2one('product.product', 'Product', require=True, select=True)
	warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', require=True)
	standard_price = fields.Float('Cost', digits_compute=dp.get_precision('Product Price'), help='Cost of the product')

	_defaults = {
		'standard_price': 0.0
	}

	_order = 'product_id, warehouse_id'

class StockWarehouse(models.Model):
	_inherit = 'stock.warehouse'

	cost_method = fields.Selection([('standard', 'Standard Price'), ('average', 'Average Price'), ('real', 'Real Price')],
            help="""Standard Price: The cost price is manually updated at the end of a specific period (usually every year).
                    Average Price: The cost price is recomputed at each incoming shipment and used for the product valuation.
                    Real Price: The cost price displayed is the price of the last outgoing product (will be use in case of inventory loss for example).""",
            string="Costing Method", required=True, copy=True)

# class ProductProduct(models.Model):
#     _inherit = 'product.product'

#     cost_method = fields.Selection(related='stock.'),