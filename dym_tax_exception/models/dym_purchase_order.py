import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.osv import osv 

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.multi
    def button_dummy(self):
        res = super(PurchaseOrder, self).button_dummy()
        for line in self.order_line:
            branch_config_id = self.env['dym.branch.config'].search([('branch_id','=',line.branch_id.id)])
            if branch_config_id.free_tax:
                line.taxes_id = False
                line.taxes_show_id = False
        return res

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
 
    @api.multi
    @api.onchange('product_id')
    def onchange_product_id(self, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft', context=None):
        res = super(PurchaseOrderLine, self).onchange_product_id(pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=date_order, fiscal_position_id=fiscal_position_id, date_planned=date_planned,
            name=name, price_unit=price_unit, state='draft')

        branch_id = self._context.get('branch_id', False)
        branch_config_id = self.env['dym.branch.config'].search([('branch_id','=',branch_id)])
        if branch_config_id.free_tax:
            res["value"].update({'taxes_id': False, 'taxes_id_view': False})
        return res
