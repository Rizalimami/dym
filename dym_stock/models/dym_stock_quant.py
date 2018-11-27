# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2014-now Noviat nv/sa (www.noviat.com).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm, osv
from datetime import datetime
# from openerp.addons.report_xls.utils import _render
# from openerp.tools.translate import _


class dym_stock_quant(orm.Model):
    _inherit = 'stock.quant'
    
    def _check_location(self, cr, uid, location, context=None):
        result = super(dym_stock_quant, self)._check_location(cr, uid, location, context=context)
        if location.usage == 'internal' :
            cr.execute("""
            SELECT
                sum(qty) as quantity
            FROM
                stock_quant
            WHERE
                location_id = %s
            """,([location.id]))
            current_qty = cr.fetchall()[0][0]
            if location.maximum_qty != -1 and current_qty > location.maximum_qty :
                raise osv.except_osv(('Perhatian !'), ("Quantity produk melebihi jumlah maksimum lokasi '%s' !" %location.name))
            if datetime.strptime(location.start_date, "%Y-%m-%d").date() > datetime.today().date() or datetime.strptime(location.end_date, "%Y-%m-%d").date() < datetime.today().date() :
                raise osv.except_osv(('Perhatian !'), ("Effective Date utk lokasi '%s' sudah habis !" %location.name))
        return result

    def quants_get(self, cr, uid, location, product, qty, domain=None, restrict_lot_id=False, restrict_partner_id=False, context=None):
        if context is None:
            context = {}
        if domain is None:
            domain = []
        if product.categ_id.isParentName('Extras') :
            return super(dym_stock_quant, self).quants_get(cr, uid, location, product, qty, domain, restrict_lot_id, restrict_partner_id, context)
        else :
            if 'bypass_consolidate' not in context:
                domain += [('consolidated_date', '!=', False)]
        return super(dym_stock_quant, self).quants_get(cr, uid, location, product, qty, domain, restrict_lot_id, restrict_partner_id, context)
