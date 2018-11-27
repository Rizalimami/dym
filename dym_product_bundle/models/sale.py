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

from openerp.osv import fields, osv
from openerp import netsvc
from openerp.tools.translate import _

class sale_order(osv.osv):
    _inherit = "sale.order"
    
    def action_ship_create(self, cr, uid, ids, context=None):
        """Create the required procurements to supply sales order lines, also connecting
        the procurements to appropriate stock moves in order to bring the goods to the
        sales order's requested location.

        :return: True
        """
        context = context or {}
        context['lang'] = self.pool['res.users'].browse(cr, uid, uid).lang
        procurement_obj = self.pool.get('procurement.order')
        sale_line_obj = self.pool.get('sale.order.line')
        for order in self.browse(cr, uid, ids, context=context):
            proc_ids = []
            vals = self._prepare_procurement_group(cr, uid, order, context=context)
            if not order.procurement_group_id:
                group_id = self.pool.get("procurement.group").create(cr, uid, vals, context=context)
                order.write({'procurement_group_id': group_id})

            for line in order.order_line:
                if line.state == 'cancel':
                    continue
                #Try to fix exception procurement (possible when after a shipping exception the user choose to recreate)
                if line.procurement_ids:
                    #first check them to see if they are in exception or not (one of the related moves is cancelled)
                    procurement_obj.check(cr, uid, [x.id for x in line.procurement_ids if x.state not in ['cancel', 'done']])
                    line.refresh()
                    #run again procurement that are in exception in order to trigger another move
                    except_proc_ids = [x.id for x in line.procurement_ids if x.state in ('exception', 'cancel')]
                    procurement_obj.reset_to_confirmed(cr, uid, except_proc_ids, context=context)
                    proc_ids += except_proc_ids
                else:
                    fake_line_ids = []
                    if line.product_id.product_tmpl_id.is_bundle:
                        fake_line_ids = line.product_id.product_tmpl_id.item_ids
                    else:
                        fake_line_ids = line
                    for fake_line in fake_line_ids:
                        prod_obj = self.pool.get('product.product')
                        if prod_obj.need_procurement(cr, uid, [fake_line.product_id.id], context=context):
                            if line.state == 'done':
                                continue
                            context['line'] = line
                            vals = self._prepare_order_line_procurement(cr, uid, order, fake_line, group_id=order.procurement_group_id.id, context=context)
                            del context['line']
                            ctx = context.copy()
                            ctx['procurement_autorun_defer'] = True
                            proc_id = procurement_obj.create(cr, uid, vals, context=ctx)
                            proc_ids.append(proc_id)
            #Confirm procurement order such that rules will be applied on it
            #note that the workflow normally ensure proc_ids isn't an empty list
            procurement_obj.run(cr, uid, proc_ids, context=context)

            #if shipping was in exception and the user choose to recreate the delivery order, write the new status of SO
            if order.state == 'shipping_except':
                val = {'state': 'progress', 'shipped': False}

                if (order.order_policy == 'manual'):
                    for line in order.order_line:
                        if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                            val['state'] = 'manual'
                            break
                order.write(val)
        return True

    def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
        date_planned = self._get_date_planned(cr, uid, order, context['line'], order.date_order, context=context)
        if context['line'].product_id.product_tmpl_id.is_bundle:            
            return  {
                'name': line.product_id.name  + ' [' + context['line'].name + ']',
                'origin': order.name,
                'date_planned': date_planned,
                'product_id': line.product_id.id,
                'product_qty': line.product_uom_qty*context['line'].product_uom_qty,
                'product_uom': line.product_uom.id,
                'product_uos_qty': line.product_uom_qty*context['line'].product_uom_qty,
                'product_uos': line.product_uom.id,
                'company_id': order.company_id.id,
                'group_id': group_id,
                'invoice_state': (order.order_policy == 'picking') and '2binvoiced' or 'none',
                'sale_line_id': context['line'].id or False
            }
        return {
            'name': line.name,
            'origin': order.name,
            'date_planned': date_planned,
            'product_id': line.product_id.id,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id) or line.product_uom.id,
            'company_id': order.company_id.id,
            'group_id': group_id,
            'invoice_state': (order.order_policy == 'picking') and '2binvoiced' or 'none',
            'sale_line_id': line.id
        }

    def procurement_needed(self, cr, uid, ids, context=None):
        #when sale is installed only, there is no need to create procurements, that's only
        #further installed modules (sale_service, sale_stock) that will change this.
        sale_line_obj = self.pool.get('sale.order.line')
        prod_obj = self.pool.get('product.product')
        res = []
        for order in self.browse(cr, uid, ids, context=context):
            for line in order.order_line:
                fake_line_ids = []
                if line.product_id.product_tmpl_id.is_bundle:
                    fake_line_ids = line.product_id.product_tmpl_id.item_ids
                else:
                    fake_line_ids.append(line)
                res.append(prod_obj.need_procurement(cr, uid, [fake_line.product_id.id for fake_line in fake_line_ids if line.state != 'cancel'], context=context))
        return any(res)
sale_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: