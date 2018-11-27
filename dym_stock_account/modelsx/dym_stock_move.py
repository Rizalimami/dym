from openerp.osv import fields, osv

class dym_stock_move(osv.osv):
    _inherit = "stock.move"

    def get_price_unit(self, cr, uid, move, context=None):
        price_unit = super(dym_stock_move, self).get_price_unit(cr, uid, move, context=context)
        if (move.purchase_line_id or (move.picking_id.is_reverse and move.location_id.usage == 'internal' and move.location_dest_id.usage == 'supplier')) and move.branch_id.branch_type == 'DL':
            return 0.01
        return move.price_unit/1.1 or move.product_id.standard_price
    