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

#
# Please note that these reports are not multi-currency !!!
#

from openerp.osv import fields,osv
from openerp import tools

class purchase_report(osv.osv):
    _inherit = "purchase.report"
    _columns = {
        'date': fields.datetime('Order Date', readonly=True, help="Date on which this document has been created"),  # TDE FIXME master: rename into date_order
        'state': fields.selection([('draft', 'Request for Quotation'),
                                     ('confirmed', 'Waiting Supplier Ack'),
                                      ('approved', 'Approved'),
                                      ('except_picking', 'Shipping Exception'),
                                      ('except_invoice', 'Invoice Exception'),
                                      ('done', 'Done'),
                                      ('cancel', 'Cancelled')],'Order Status', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'picking_type_id': fields.many2one('stock.warehouse', 'Warehouse', readonly=True),
        'location_id': fields.many2one('stock.location', 'Destination', readonly=True),
        'partner_id':fields.many2one('res.partner', 'Supplier', readonly=True),
        'pricelist_id':fields.many2one('product.pricelist', 'Pricelist', readonly=True),
        'date_approve':fields.date('Date Approved', readonly=True),
        'expected_date':fields.date('Expected Date', readonly=True),
        'move_date':fields.datetime('GRN Date', readonly=True),
        'validator' : fields.many2one('res.users', 'Validated By', readonly=True),
        'product_uom' : fields.many2one('product.uom', 'Reference Unit of Measure', required=True),
        'company_id':fields.many2one('res.company', 'Company', readonly=True),
        'user_id':fields.many2one('res.users', 'Responsible', readonly=True),
        'delay':fields.float('Days to Validate', digits=(16,2), readonly=True),
        'delay_pass':fields.float('Days to Deliver', digits=(16,2), readonly=True),
        'quantity': fields.integer('Unit Quantity', readonly=True),  # TDE FIXME master: rename into unit_quantity
        'move_qty': fields.integer('Distributed Quantity', readonly=True),  # TDE FIXME master: rename into unit_quantity
        'price_total': fields.float('Total Price', readonly=True),
        'price_average': fields.float('Average Price', readonly=True, group_operator="avg"),
        'negociation': fields.float('Purchase-Standard Price', readonly=True, group_operator="avg"),
        'price_standard': fields.float('Products Value', readonly=True, group_operator="sum"),
        'nbr': fields.integer('# of Lines', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'po_name': fields.char('Purchase Order', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'pot_name': fields.char('PO Type', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'division': fields.char('Division', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'category_id': fields.many2one('product.category', 'Category', readonly=True)

    }
    _order = 'date desc, price_total desc'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'purchase_report')
        cr.execute("""
            create or replace view purchase_report as (
                WITH currency_rate (currency_id, rate, date_start, date_end) AS (
                    SELECT r.currency_id, r.rate, r.name AS date_start,
                        (SELECT name FROM res_currency_rate r2
                        WHERE r2.name > r.name AND
                            r2.currency_id = r.currency_id
                         ORDER BY r2.name ASC
                         LIMIT 1) AS date_end
                    FROM res_currency_rate r
                )
                select
                    min(l.id) as id,
                    s.date_order as date,
                    l.state,
                    s.date_approve,
                    s.minimum_planned_date as expected_date,
                    s.dest_address_id,
                    s.pricelist_id,
                    s.validator,
                    spt.warehouse_id as picking_type_id,
                    s.division as division,
                    s.partner_id as partner_id,
                    s.create_uid as user_id,
                    s.company_id as company_id,
                    l.product_id,
                    t.categ_id as category_id,
                    s.name as po_name,
                    pot.name as pot_name,
                    t.uom_id as product_uom,
                    s.location_id as location_id,
                    mv.date as move_date, 
                    sum(mv.product_uom_qty/u.factor*u2.factor) as move_qty,
                    sum(l.product_qty/u.factor*u2.factor) as quantity,
                    extract(epoch from age(s.date_approve,s.date_order))/(24*60*60)::decimal(16,2) as delay,
                    extract(epoch from age(l.date_planned,s.date_order))/(24*60*60)::decimal(16,2) as delay_pass,
                    count(*) as nbr,
                    sum(l.price_unit*cr.rate*l.product_qty)::decimal(16,2) as price_total,
                    avg(100.0 * (l.price_unit*cr.rate*l.product_qty) / NULLIF(ip.value_float*l.product_qty/u.factor*u2.factor, 0.0))::decimal(16,2) as negociation,
                    sum(ip.value_float*l.product_qty/u.factor*u2.factor)::decimal(16,2) as price_standard,
                    (sum(l.product_qty*cr.rate*l.price_unit)/NULLIF(sum(l.product_qty/u.factor*u2.factor),0.0))::decimal(16,2) as price_average
                from purchase_order_line l
                    join purchase_order s on (l.order_id=s.id)
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                            LEFT JOIN ir_property ip ON (ip.name='standard_price' AND ip.res_id=CONCAT('product.template,',t.id) AND ip.company_id=s.company_id)
                    left join stock_move mv on mv.purchase_line_id = l.id and mv.state = 'done'
                    left join dym_purchase_order_type pot on pot.id = s.purchase_order_type_id
                    left join product_uom u on (u.id=l.product_uom)
                    left join product_uom u2 on (u2.id=t.uom_id)
                    left join stock_picking_type spt on (spt.id=s.picking_type_id)
                    join currency_rate cr on (cr.currency_id = s.currency_id and
                        cr.date_start <= coalesce(s.date_order, now()) and
                        (cr.date_end is null or cr.date_end > coalesce(s.date_order, now())))
                group by
                    s.company_id,
                    s.create_uid,
                    s.partner_id,
                    u.factor,
                    s.location_id,
                    l.price_unit,
                    s.date_approve,
                    pot.name,
                    l.date_planned,
                    mv.date,
                    mv.product_uom_qty,
                    l.product_uom,
                    s.name,
                    s.division,
                    s.minimum_planned_date,
                    s.pricelist_id,
                    s.validator,
                    s.dest_address_id,
                    l.product_id,
                    t.categ_id,
                    s.date_order,
                    l.state,
                    spt.warehouse_id,
                    u.uom_type,
                    u.category_id,
                    t.uom_id,
                    u.id,
                    u2.factor
            )
        """)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
