from openerp import api, SUPERUSER_ID, exceptions
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.osv.orm import browse_record_list, browse_record, browse_null
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import time
from datetime import datetime
import code

class dym_stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    @profile
    def create_packing(self, cr, uid, ids, context=None):
        picking_id = self.browse(cr, uid, ids, context=context)
        if picking_id.retur == True:
            for move_line in picking_id.move_lines:
                code = False
                field = False
                retur_line_id = False
                if move_line.retur_beli_line_id.retur_id.retur_type == 'Barang':
                    code = 'outgoing'
                    field = 'retur_beli_line_id'
                    retur_line_id = move_line.retur_beli_line_id.id
                    warning1 = "Pengembalian barang ke supplier belum lengkap"
                elif move_line.retur_jual_line_id.retur_id.retur_type == 'Barang':
                    code = 'incoming'
                    field = 'retur_jual_line_id'
                    retur_line_id = move_line.retur_jual_line_id.id
                    warning1 = "Pengembalian barang dari customer belum lengkap"
                if code and field and retur_line_id:
                    move_search = move_line.search([(field,'=',retur_line_id),('picking_id.picking_type_id.code','=',code),('state','!=','done')])
                    if move_search:
                        raise osv.except_osv(('Perhatian !'), (warning1))
                    else:
                        move_search = move_line.search([('picking_id.origin','=',picking_id.origin),('picking_id.picking_type_id.code','=',code),('state','!=','done'),('retur_beli_line_id','=',False),('retur_jual_line_id','=',False)])
                        if move_search:
                            raise osv.except_osv(('Perhatian !'), (warning1))

        if picking_id.branch_id.branch_type == 'MD' and picking_id.division == 'Unit' and picking_id.picking_type_code == 'incoming' and not picking_id.is_reverse and picking_id.state != 'done' :
            raise osv.except_osv(('Perhatian !'), ("Untuk penerimaan Unit MD silahkan create di menu Showroom > Good Receipt Note MD"))
        packing_draft = self.pool.get('dym.stock.packing').search(cr, uid, [
            ('picking_id','=',picking_id.id),
            ('state','=','draft')
        ])
        if picking_id.state == 'done' or packing_draft :
            return self.view_packing(cr,uid,ids,context)
        
        obj_packing = self.pool.get('dym.stock.packing')
        obj_packing_line = self.pool.get('dym.stock.packing.line')
        branch_sender_id = False
        
        if picking_id.picking_type_code == 'interbranch_in' :
            branch_sender_id = picking_id.location_id.branch_id.id
        packing_vals = {
			'picking_id': picking_id.id,
			'branch_sender_id': branch_sender_id,
            'picking_type_id': picking_id.picking_type_id.id,
            # 'division':picking_id.division,
		}
        id_packing = obj_packing.create(cr, uid, packing_vals, context=context)        
        
        if (picking_id.picking_type_code == 'outgoing' and picking_id.rel_branch_type == 'DL') or picking_id.division == 'Umum' or picking_id.is_reverse :
            ids_move = self.get_ids_move(cr, uid, ids, context)
            for move in picking_id.move_lines:
                if move.state not in ['draft','cancel']:
                    if picking_id.picking_type_code == 'incoming' and not picking_id.is_reverse :
                        current_reserved = 0
                        stock_available = self.get_seharusnya(cr, uid, ids, context)[move.product_id]
                    elif picking_id.is_reverse :
                        current_reserved = self.get_current_reserved(cr, uid, ids, move.product_id.id, move.location_id.id, ids_move, context)
                        if picking_id.picking_type_code in ('outgoing','interbranch_out'):
                            stock_available = self.get_stock_available(cr, uid, ids, move.product_id.id, move.location_id.id, context)
                        else:
                            stock_available = 0
                    elif move.product_id.categ_id.isParentName('Extras') :
                        current_reserved = self.get_current_reserved(cr, uid, ids, move.product_id.id, move.location_id.id, ids_move, context)
                        stock_available = self.get_stock_available_extras(cr, uid, ids, move.product_id.id, move.location_id.id, context)
                    else :
                        current_reserved = self.get_current_reserved(cr, uid, ids, move.product_id.id, move.location_id.id, ids_move, context)
                        stock_available = self.get_stock_available(cr, uid, ids, move.product_id.id, move.location_id.id, context)
                    seharusnya = self.get_seharusnya(cr, uid, ids, context)[move.product_id]
                    packing_line_vals = {
                        'packing_id': id_packing,
                        'template_id': move.product_tmpl_id.id,
                        'product_id': move.product_id.id,
                        # 'quantity': self.get_qty(cr, uid, ids, picking_id, move.product_id, move.product_uom_qty, context),
                        'quantity': seharusnya,
                        'seharusnya': seharusnya,
                        'serial_number_id': move.restrict_lot_id.id,
                        'engine_number': move.restrict_lot_id.name,
                        'chassis_number': move.restrict_lot_id.chassis_no,
                        'source_location_id': move.restrict_lot_id.location_id.id if move.restrict_lot_id and move.picking_id.picking_type_code in ('outgoing','interbranch_out','internal') else move.location_id.id,
                        'destination_location_id': move.location_dest_id.id,
                        'tahun_pembuatan': move.restrict_lot_id.tahun,
                        'ready_for_sale': self.convert_rfs(cr, uid, ids, move.restrict_lot_id.ready_for_sale, context),
                        'current_reserved': current_reserved,
                        'stock_available': stock_available,
                        'purchase_line_id': move.purchase_line_id.id,
                        'move_id': move.id,
                    }
                    obj_packing_line.create(cr, uid, packing_line_vals)
        return self.view_packing(cr, uid, ids, context)