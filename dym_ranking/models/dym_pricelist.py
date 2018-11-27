from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError


class dym_pricelist(models.Model):
    _inherit = "purchase.order"

    @api.one
    def _get_suggestion_id(self):
        suggestion_brw = self.env['dym.ranking'].search([('purchase_id','=',self.id)])
        if suggestion_brw:
            self.suggestion_id = suggestion_brw[0].id
        else:
            self.suggestion_id = False

    suggestion_id = fields.Many2one('dym.ranking', 'Suggestion', readonly=True, compute='_get_suggestion_id')

class dym_lost_order(models.Model):
    _name = "dym.lost.order"

    date = fields.Datetime(string='Order Date',default=fields.Datetime.now)
    rec_id = fields.Integer('Record ID')
    rec_model = fields.Char('Record Model')
    branch_id = fields.Many2one('dym.branch', 'Branch')
    product_id = fields.Many2one('product.product', 'Product')
    tipe_dok = fields.Char('Tipe Dokumen')
    no_dok = fields.Char('Dokumen')
    lost_order_qty = fields.Float('Lost Order QTY')
    pemenuhan_qty = fields.Float('Qty Pemenuhan')
    het = fields.Float('HET')
    customer_id = fields.Many2one('res.partner', 'Customer')

class dym_pricelist(models.Model):
    _inherit = "dym.pricelist"

    order_qty = fields.Float('Customer Order')
    lost_order_qty = fields.Float('Lost Order QTY')
    lost_order_qty_show = fields.Float('Lost Order QTY')


    @api.onchange('order_qty')
    def order_qty_change(self):
        if self.product_id and self.branch_id and self.order_qty > 0 and self.stock_available < self.order_qty:
            lost_order_qty = self.order_qty - self.stock_available
            self.lost_order_qty = lost_order_qty
            self.lost_order_qty_show = lost_order_qty
        else:
            self.lost_order_qty = 0
            self.lost_order_qty_show = 0

    def create(self, cr, uid, vals, context=None):
        if 'lost_order_qty' in vals and 'product_id' in vals and vals['product_id'] and 'branch_id' in vals and vals['branch_id']:
            if vals['lost_order_qty'] <= 0:
                return {'warning':{'title':'Invalid action!','message':'Tidak bisa simpan lost order karena product tersedia!'}}
            elif vals['lost_order_qty'] > 0 and vals['product_id'] and vals['branch_id'] and vals['lost_order_qty']:
                res = {'branch_id': vals['branch_id'], 'product_id': vals['product_id'], 'lost_order_qty': vals['lost_order_qty'], 'tipe_dok': 'Check Price', 'no_dok': '', 'pemenuhan_qty': 0, 'het': vals['harga_jual']}
                self.pool.get('dym.lost.order').create(cr, uid, res)
        else:
            raise osv.except_osv(('Perhatian !'), ("Tidak bisa disimpan, form ini hanya untuk Pengecekan"))
        return False

    @api.multi
    def save_lost_order(self):
        return False

