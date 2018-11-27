from openerp.osv import osv, fields

class consolidate_invoice_line(osv.osv):
    _inherit = 'consolidate.invoice.line' 

    def _get_purchase_line_id(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.consolidate_id.asset == False:
                res[line.id] = line.move_id.purchase_line_id.id
            else:
                res[line.id] = line.receive_line_id.purchase_line_id.id
        return res

    def _get_subtotal(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            obj_inv_line = self.pool.get('account.invoice.line')
            id_inv_line = obj_inv_line.search(cr, uid, [('purchase_line_id','=',line.purchase_line_id.id),('invoice_id','=',line.consolidate_id.invoice_id.id)])
            if not id_inv_line:
                res[line.id] = line.price_unit * line.move_qty
            else:
                inv_line_id = obj_inv_line.browse(cr, uid, id_inv_line)[0]
                price = (inv_line_id.price_unit * inv_line_id.quantity) - (inv_line_id.discount_amount + inv_line_id.discount_cash + inv_line_id.discount_lain + inv_line_id.discount_program)
                taxes = inv_line_id.invoice_line_tax_id.compute_all(price, 1, product=inv_line_id.product_id, partner=inv_line_id.invoice_id.partner_id)
                final_unit_price = taxes['total'] / inv_line_id.quantity
                subtotal = round(final_unit_price*line.product_qty,2)
                res[line.id] = subtotal
        return res

    _columns = {
        'purchase_line_id': fields.function(_get_purchase_line_id, string='PO Line', type='many2one', method=True, relation='purchase.order.line',), 
        'price_subtotal': fields.function(_get_subtotal, string='Subtotal', type='float', method=True), 
    }
