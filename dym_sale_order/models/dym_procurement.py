from openerp.osv import fields, osv
from openerp.tools.translate import _

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
from dateutil.relativedelta import relativedelta
from datetime import datetime


class procurement_order(osv.osv):
    _inherit = "procurement.order"
    
    def _get_default_location_delivery_sales(self,cr,uid,branch_id):
        default_location_id = {}
        obj_picking_type = self.pool.get('stock.picking.type')
        picking_type_id = obj_picking_type.search(cr,uid,[
                                                  ('branch_id','=',branch_id),
                                                  ('code','=','outgoing')
                                                  ])
        if picking_type_id:
            for pick_type in obj_picking_type.browse(cr,uid,picking_type_id[0]):
                if not pick_type.default_location_dest_id.id :
                     raise osv.except_osv(('Perhatian !'), ("Location destination Belum di Setting"))
                default_location_id.update({
                    'picking_type_id':pick_type.id,
                    'source':pick_type.default_location_src_id.id,
                    'destination': pick_type.default_location_dest_id.id,
                })
        else:
           raise osv.except_osv(('Error !'), ('Tidak ditemukan default lokasi untuk penjualan di konfigurasi cabang \'%s\'!') % (val.branch_id.name,)) 
        return default_location_id
    
    def _run_move_create(self, cr, uid, procurement, context=None):
        vals = super(procurement_order,self)._run_move_create(cr, uid, procurement, context=context)
        undelivered_value = 0
        if procurement.sale_line_id and procurement.sale_line_id.id:
            branch_id = procurement.sale_line_id.order_id.branch_id.id
            if procurement.product_id.product_tmpl_id.cost_method == 'real':
                pricelist_beli_md = procurement.sale_line_id.order_id.branch_id.pricelist_unit_purchase_id.id
                if not pricelist_beli_md:
                    raise osv.except_osv(('No Purchase Pricelist Defined!'), ('Tidak bisa confirm'))
                undelivered_value = round(self.pool.get('product.pricelist').price_get(cr, uid, [pricelist_beli_md], procurement.product_id.id, 1,0)[pricelist_beli_md]/1.1,2)
            elif procurement.product_id.product_tmpl_id.cost_method == 'average':
                product_price_branch_obj = self.pool.get('product.price.branch')
                undelivered_value = product_price_branch_obj._get_price(cr, uid, procurement.sale_line_id.order_id.warehouse_id.id, procurement.product_id.id)    
            
            location = self._get_default_location_delivery_sales(cr,uid,branch_id)
            
            vals.update({'branch_id':branch_id,'undelivered_value':undelivered_value,'picking_type_id': location['picking_type_id'],'location_dest_id': location['destination']})
        
        return vals
    
class stock_move(osv.osv):
    _inherit = "stock.move"
    
    _columns = {
                'sale_order_line_id': fields.many2one('sale.order.line', 'Sales Memo Line'),
                }

    
    def get_stock_location(self, cr, uid, product_id, branch_id, move_id, usage=['internal'], where_query="", warn_kosong=False, lot_state=['stock'], context=None):
        if not context:
            context = {}
        if 'usage' in context:
            usage = context.get('usage','')
        if 'lot_state' in context:
            lot_state = context.get('lot_state','')
        move_query = ""
        if move_id:
            move_query = ("or q.reservation_id in %s") % (str(
                tuple(move_id)).replace(',)', ')'),)
        ids_location = []
        cr.execute("""
        SELECT
            q.location_id,
            l.name
        FROM
            stock_location l, stock_quant q
        LEFT JOIN
            stock_production_lot lot on lot.id = q.lot_id
        WHERE
            q.product_id = %s and l.branch_id = %s and (q.reservation_id is Null """ + move_query + """)
            and (q.lot_id is Null or lot.state in %s) and q.location_id = l.id and l.usage in %s """ + where_query + """
        GROUP BY
            q.location_id, l.name
        """,(product_id, branch_id, tuple(lot_state), tuple(usage)))
        for location in cr.fetchall() :
            ids_location.append(location[0])
        if warn_kosong == True and len(ids_location) == 0:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            branch = self.pool.get('dym.branch').browse(cr, uid, branch_id, context=context)
            raise osv.except_osv(('Perhatian !'), ("Produk %s %s tidak ditemukan di branch %s, Mohon periksa stock!")%(product.name, product.description or product.default_code, branch.name))
        return ids_location

    def _picking_assign(self, cr, uid, move_ids, procurement_group, location_from, location_to, context=None):
        pick_obj = self.pool.get("stock.picking")
        move = self.browse(cr,uid,move_ids[0])

        if move.branch_id:
            move_vals = {}
            source_locations = self.get_stock_location(cr, uid, product_id=move.product_id.id, branch_id=move.branch_id.id, move_id=[move.id])
            if source_locations:
                location_from = source_locations[0]
                move_vals.update({
                    'location_id': location_from
                })

            values = {
                'origin': move.origin,
                'company_id': move.company_id and move.company_id.id or False,
                'move_type': move.group_id and move.group_id.move_type or 'direct',
                'partner_id': move.partner_id.id or False,
                'picking_type_id': move.picking_type_id and move.picking_type_id.id or False,
                'group_id': procurement_group,
                'location_id':location_from,
                'location_dest_id': location_to,
                'branch_id': move.branch_id.id,
                'division': move.procurement_id.sale_line_id.order_id.division,
                'state': 'draft',
            }
            pick = pick_obj.create(cr, uid, values, context=context)
            move_vals.update({
                'picking_id': pick
            })
            self.write(cr, uid, move_ids, move_vals, context=context)            
        res = super(stock_move,self)._picking_assign(cr, uid, move_ids, procurement_group, location_from, location_to, context=context)
        pick_obj.force_assign(cr,uid,pick)
        return res 