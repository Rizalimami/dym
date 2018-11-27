# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#    Author: Yannick Gouin <yannick.gouin@elico-corp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, fields, orm
from openerp import netsvc

class product_item(osv.osv):
    _name = "product.item"
    _description = "Product Item for Bundle products"
        
    def _get_variant(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = item.product_tmpl_id.product_variant_ids[0].id 
        return res

    _columns = {
        # 'sequence':   fields.integer('Sequence'),
        'template_id': fields.many2one('product.template', 'Parent ID', required=True),
        'product_tmpl_id': fields.many2one('product.template', 'Product', required=True),
        'product_id': fields.function(_get_variant, relation='product.product', type='many2one', string='Variant'),
        'product_uom':     fields.many2one('product.uom', 'UoM', required=True),
        'product_uom_qty':    fields.integer('Quantity', required=True),
        # 'revenue':    fields.float('Revenue repartition (%)', help="Define when you sell a Bundle product, how many percent of the sale price is applied to this item."),
        # 'editable':   fields.boolean('Allow changes in DO ?', help="Allow the user to change this item (quantity or item itself) in the Delivery Orders."),
    }
    _defaults = {
        'editable': lambda *a: True,
    }
    
    
    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        context = context or {}
        domain = {}
        result = {}

        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            if product:
                result.update({'product_uom': product.uom_id.id})
                domain = {'product_uom': [('category_id', '=', product.uom_id.category_id.id)]}
                
        return {'value': result, 'domain': domain}
    

# class product_product(osv.osv):
#     _inherit = "product.product"
    
#     _columns = {
#         'item_ids': fields.one2many('product.item', 'product_id', 'Item sets'),
#     }
# product_product()


class product_template(osv.osv):
    _inherit = "product.template"

    _columns = {
        'item_ids': fields.one2many('product.item', 'template_id', 'Item sets'),
        'is_bundle': fields.boolean('Bundle'),
    }

    def onchange_bundle(self, cr, uid, ids, is_bundle, context=None):
        context = context or {}
        domain = {}
        result = {}
        
        if is_bundle:
            result.update({'type':'service'})
        else:
            result.update({'type':False})

        return {'value': result, 'domain': domain}

product_template()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
