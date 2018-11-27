import time
from openerp import models, fields, api
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class dym_sale_order_update_price(models.TransientModel):
    _name = 'dym.sale.order.update.price'

    so_id = fields.Many2one('dealer.sale.order', string="Sales Memo")
    so_line_id = fields.Many2one('dealer.sale.order.line', string="Sales Memo Line")

    template_id = fields.Many2one('product.template', string="Tipe")
    product_id = fields.Many2one('product.product', string="Warna")
    sale_price = fields.Float(string="Sale Price")
    sale_price_new = fields.Float(string="Sale Price New")
    diff_price = fields.Float(string="Different Price")
    bbn_price = fields.Float(string="BBN Price")
    bbn_price_new = fields.Float(string="BBN Price New")
    diff_price_bbn = fields.Float(string="Different Price")

    @api.model
    def default_get(self, fields):
        active_id = self._context.get('active_id', None)
        active_ids = self._context.get('active_ids', None)
        res = super(dym_sale_order_update_price, self).default_get(fields)
        order_line_id = self.env['dealer.sale.order.line'].browse(active_ids)
        branch_id = order_line_id.dealer_sale_order_line_id.branch_id
        pricelist_unit_sales_id = branch_id.pricelist_unit_sales_id
        pricelist_bbn_id = branch_id.pricelist_bbn_hitam_id
        if order_line_id.plat == 'M':
            pricelist_bbn_id = branch_id.pricelist_bbn_merah_id
        price = self._get_price_unit(pricelist_unit_sales_id.id, order_line_id.product_id.id)
        price_bbn = self._get_price_unit(pricelist_bbn_id.id, order_line_id.product_id.id)
        res['so_id'] = self.env.context.get('dealer_sale_order_line_id',False)
        res['so_line_id'] = active_id
        res['template_id'] = order_line_id.template_id.id
        res['product_id'] = order_line_id.product_id.id
        res['sale_price'] = order_line_id.price_unit_show
        res['sale_price_new'] = price
        res['diff_price'] = price - order_line_id.price_unit_show

        if order_line_id.is_bbn == 'Y':
            res['bbn_price'] = order_line_id.price_bbn_show
            res['bbn_price_new'] = price_bbn
            res['diff_price_bbn'] = price_bbn - order_line_id.price_bbn_show
        else:
            res['bbn_price'] = 0.0
            res['bbn_price_new'] = 0.0
            res['diff_price_bbn'] = 0.0

        return res

    @api.multi
    def action_update_price(self):
        active_model = self.env.context.get('active_model',False)
        active_ids = self.env.context.get('active_ids',False)
        if active_model and active_model == 'dealer.sale.order.line' and active_ids:
            so_line_obj = self.env[active_model].browse(active_ids)
            so_id = so_line_obj.dealer_sale_order_line_id
            if so_line_obj.dealer_sale_order_line_id.state == 'draft':
                so_line_obj.write({
                    'price_unit':self.sale_price_new,
                    'price_unit_show':self.sale_price_new,
                    'price_bbn': self.bbn_price_new,
                    'price_bbn_show': self.bbn_price_new,
                })

    def _get_price_unit(self,cr,uid,pricelist,product_id):
        price_unit = self.pool.get('product.pricelist').price_get(cr,uid,[pricelist],product_id,1)[pricelist]
        return price_unit  

