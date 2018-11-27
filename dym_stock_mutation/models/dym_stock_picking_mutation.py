from openerp.osv import osv, fields
class dym_stock_picking_mutation(osv.osv):
    _inherit = 'stock.picking'
    
    def transfer(self, cr, uid, picking, context=None):
        res = super(dym_stock_picking_mutation, self).transfer(cr, uid, picking, context=context)
        for move in picking.move_lines :
            if move.product_id.categ_id.isParentName('Extras') :
                return res
            
        if picking.picking_type_id.code == 'interbranch_in' and picking.model_id.model == 'dym.mutation.order' :
            obj_order = self.pool.get('dym.mutation.order').browse(cr, uid, picking.transaction_id)
            qty = {}
            qty2 = {}
            qty3 = {}
            for x in picking.move_lines :
                qty[x.product_id] = qty.get(x.product_id,0) + x.product_uom_qty
                qty2[x.product_id] = qty2.get(x.product_id,0) + x.product_uom_qty
                qty3[x.product_id] = qty3.get(x.product_id,0) + x.product_uom_qty
            
            for x in obj_order.sudo().order_line :
                qty[x.product_id] = qty.get(x.product_id,0) + x.supply_qty
                x.write({'supply_qty':qty[x.product_id]})
            for x in obj_order.sudo().distribution_id.distribution_line :
                qty2[x.product_id] = qty2.get(x.product_id,0) + x.supply_qty
                x.write({'supply_qty':qty2[x.product_id]})
            for x in obj_order.sudo().distribution_id.sudo().request_id.request_line :
                qty3[x.product_id] = qty3.get(x.product_id,0) + x.supply_qty
                x.write({'supply_qty':qty3[x.product_id]})
            obj_order.sudo().is_done()

        #work_order
        if picking.picking_type_id.code == 'outgoing' and picking.model_id.model == 'dym.work.order' :
            obj_order = self.pool.get('dym.work.order').browse(cr, uid, picking.transaction_id)
            qty = {}
            for x in picking.move_lines :
                for y in obj_order.work_lines :
                    if x.work_order_line_id.id == y.id:
                        if not y.product_id.product_tmpl_id.is_bundle:
                            supplied_qty = y.supply_qty + x.product_uom_qty
                            y.write({'supply_qty':supplied_qty})
                            continue
                        if y.product_id.product_tmpl_id.is_bundle:
                            for z in y.bundle_line:
                                if z.product_id.id == x.product_id.id:
                                    supplied_qty = z.supply_qty + x.product_uom_qty
                                    z.write({'supply_qty':supplied_qty})
                                    continue
        if picking.picking_type_id.code == 'incoming' and picking.model_id.model == 'dym.work.order' :
            obj_order = self.pool.get('dym.work.order').browse(cr, uid, picking.transaction_id)
            qty = {}
            for x in picking.move_lines :
                for y in obj_order.work_lines :
                    if x.work_order_line_id.id == y.id:
                        if not y.product_id.product_tmpl_id.is_bundle:
                            supplied_qty = y.supply_qty - x.product_uom_qty
                            y.write({'supply_qty':supplied_qty})
                            continue
                        if y.product_id.product_tmpl_id.is_bundle:
                            for z in y.bundle_line:
                                if z.product_id.id == x.product_id.id:
                                    supplied_qty = z.supply_qty - x.product_uom_qty
                                    z.write({'supply_qty':supplied_qty})
                                    continue

        #dealer_sale_order
        if picking.picking_type_id.code == 'outgoing' and picking.model_id.model == 'dealer.sale.order' :
            obj_order = self.pool.get('dealer.sale.order').browse(cr, uid, picking.transaction_id)
            qty = {}
            for x in picking.move_lines :
                qty[x.product_id] = qty.get(x.product_id,0) + x.product_uom_qty
            for x in obj_order.dealer_sale_order_line :
                qty[x.product_id] = qty.get(x.product_id,0) + x.product_qty
                x.write({'supply_qty':qty[x.product_id]})
        if picking.picking_type_id.code == 'incoming' and picking.model_id.model == 'dealer.sale.order' :
            obj_order = self.pool.get('dealer.sale.order').browse(cr, uid, picking.transaction_id)
            qty = {}
            for x in picking.move_lines :
                qty[x.product_id] = qty.get(x.product_id,0) + x.product_uom_qty
            for x in obj_order.dealer_sale_order_line :
                qty[x.product_id] =-(qty.get(x.product_id,0)) + x.product_qty
                x.write({'supply_qty':qty[x.product_id]})

        #purchase_order
        if picking.picking_type_id.code == 'incoming' and picking.model_id.model == 'purchase.order' :
            obj_order = self.pool.get('purchase.order').browse(cr, uid, picking.transaction_id)
            qty = {}
            for x in picking.move_lines :
                qty[x.product_id] = qty.get(x.product_id,0) + x.product_uom_qty
            for x in obj_order.order_line :
                qty[x.product_id] = qty.get(x.product_id,0) + x.received
                x.write({'received':qty[x.product_id]})
        elif picking.picking_type_id.code == 'outgoing' and picking.model_id.model == 'purchase.order' :
            obj_order = self.pool.get('purchase.order').browse(cr, uid, picking.transaction_id)
            if obj_order.state not in ['cancel','done','close'] :
                qty = {}
                for x in picking.move_lines :
                    qty[x.product_id] = qty.get(x.product_id,0) + x.product_uom_qty
                for x in obj_order.order_line :
                    qty[x.product_id] = -(qty.get(x.product_id,0)) + x.received
                    x.write({'received':qty[x.product_id]})
        elif picking.picking_type_id.code == 'incoming' and picking.location_id.usage == 'supplier' and not picking.transaction_id :
            for move in picking.move_lines :
                if move.purchase_line_id :
                    received = move.purchase_line_id.received
                    move.purchase_line_id.received = received + move.product_uom_qty
        elif picking.picking_type_id.code == 'outgoing' and picking.location_dest_id.usage == 'supplier' and not picking.transaction_id :
            for move in picking.move_lines :
                if move.purchase_line_id :
                    received = move.purchase_line_id.received
                    move.purchase_line_id.received = received - move.product_uom_qty
        return res
    