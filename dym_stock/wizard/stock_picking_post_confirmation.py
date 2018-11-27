# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import fields, osv

class stock_picking_post_button(osv.osv_memory):
    """
        Account move line select
    """
    _name = "stock.picking.post.button"
    _description = "Account move line select"

    _columns = {
        'msg': fields.text(string="Message")
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        if context is None:
            context={}
        res = super(stock_picking_post_button, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        return res

    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_picking_post_button, self).default_get(
            cr, uid, fields, context=context)
        return res

    def post_it(self, cr, uid, ids, context=None):
        packing_ids = context.get('active_id',[])
        for packing in self.pool.get('dym.stock.packing').browse(cr, uid, packing_ids, context=context):
            packing.with_context(okey=True).post()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
