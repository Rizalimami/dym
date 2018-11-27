import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp import SUPERUSER_ID
from lxml import etree

class dym_bundle_diskon(models.Model):
    _name = 'dym.bundle.diskon'

    @api.one
    def _get_variant(self):
        self.product_id = self.product_tmpl_id.product_variant_ids[0].id

    branch_id = fields.Many2one('dym.branch', string='Branch', required=True)
    template_id = fields.Many2one('product.template', string='Bundle', required=True)
    product_tmpl_id =  fields.Many2one('product.template', 'Product', required=True)
    product_id = fields.Many2one('product.product', string='Variant', compute=_get_variant)
    diskon = fields.Float(string='Diskon', required=True)

    @api.constrains('branch_id','template_id','product_tmpl_id')
    def product_constraint(self):
        record = self.search([('branch_id','=', self.branch_id.id),('template_id','=', self.template_id.id),('product_tmpl_id','=', self.product_tmpl_id.id),('id','!=', self.id)])
        if record:
            raise ValidationError("Data tidak boleh duplicate!")


    @api.onchange('template_id')
    def template_change(self):
        domain = {}
        item_ids = self.env['product.item'].search([('template_id','=', self.template_id.id)])
        product_ids = [item.product_tmpl_id.id for item in item_ids]
        domain['product_tmpl_id'] = [('id','in',product_ids)]
        return {'domain':domain}
