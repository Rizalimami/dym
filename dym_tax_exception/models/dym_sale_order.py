import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self, pricelist, product, qty=0, uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, tax_id=[(6, 0, [])], 
            discount_show=0, discount_line=[(6, 0, [])], discount_lain=0, discount_cash=0, discount_cash_persen=0, tipe_transaksi='', 
            discount=0, discount_pcs=0, discount_lain_pcs=0, discount_cash_pcs=0, disc_persen=False, disc_amount=False, disc_sum=False, 
            cash_persen=False, cash_amount=False, cash_sum=False, lain_amount=False, lain_sum=False, context=None):

        res = super(SaleOrderLine, self).product_id_change(pricelist, product, qty=qty, uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id, 
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag)

        branch_config_id = self.env['dym.branch.config'].search([('branch_id','=',self._context.get('branch_id'))])
        if branch_config_id.free_tax:
            res['value']['tax_id'] = False
            res['value']['tax_id_view'] = False
        return res
        
class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def button_dummy(self):
        res = super(SaleOrder, self).button_dummy()
        for line in self.order_line:
            branch_config_id = self.env['dym.branch.config'].search([('branch_id','=',line.branch_dummy)])

            if branch_config_id.free_tax:
                line.tax_id = False
        return res