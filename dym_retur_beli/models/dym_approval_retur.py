import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc

class dym_retur_beli_approval(osv.osv):
    _inherit = "dym.retur.beli"
      
    _columns = {
        'approval_ids': fields.one2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
        'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),
    }
    
    _defaults ={
        'approval_state':'b'
    }
    
    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_rb = self.browse(cr, uid, ids, context=context)
        for line in obj_rb.retur_beli_line:
            # if line.product_qty > line.available_qty:
            if line.lot_id and obj_rb.division == 'Unit':
                id_quant = self.pool.get('stock.quant').search(cr, uid, [('lot_id','=',line.lot_id.id),('lot_id.state','=','stock'),'|',('reservation_id','=',False),('location_id.usage','!=','nrfs')])
                if not id_quant:
                    raise osv.except_osv(('Perhatian !'),('Nomor Engine %s tidak ditemukan / sedang di reserve / tidak termasuk stock not ready for sale!')%(line.lot_id.name))
                line.lot_id.write({'state': 'returned'})
            obj_retur_ids = self.pool.get('dym.retur.beli.line').search(cr, uid, [('retur_id.state','not in',('draft','cancel')),('consolidate_line_id','=',line.consolidate_line_id.id),('id','!=',line.id)])
            total_returned = 0
            if obj_retur_ids:
                retur_line_browse = self.pool.get('dym.retur.beli.line').browse(cr, uid, obj_retur_ids)
                for retur_line in retur_line_browse:
                    total_returned += retur_line.product_qty
            if total_returned + line.product_qty > line.consolidate_line_id.product_qty:
                raise osv.except_osv(('Perhatian !'),('Jumlah retur line product %s  tidak boleh melebihi %s!') % (line.product_id.name, (line.consolidate_line_id.product_qty - total_returned)))
            # obj_retur_barang_ids = self.pool.get('dym.retur.barang.line').search(cr, uid, [('retur_id','=',obj_rb.id),('beli_line_id','=',line.id)])
            # qty_barang_line = 0
            # if obj_retur_barang_ids:
            #     retur_barang_line_browse = self.pool.get('dym.retur.barang.line').browse(cr, uid, obj_retur_barang_ids)
            #     for barang_line in retur_barang_line_browse:
            #         qty_barang_line += barang_line.product_qty
            # if qty_barang_line > line.product_qty:
            #     raise osv.except_osv(('Perhatian !'),('Jumlah retur barang product %s  tidak boleh melebihi %s!') % (line.product_id.name, line.product_qty))
            # if qty_barang_line < line.product_qty:
            #     packing_line_obj = self.pool.get('dym.stock.packing.line')
            #     po_ids = self.pool.get('purchase.order').search(cr, uid, [('invoice_ids', 'in', [obj_rb.invoice_id.id])])
            #     packing_line = []
            #     for po in self.pool.get('purchase.order').browse(cr, uid, po_ids):
            #         picking_ids = []
            #         picking_ids += [picking.id for picking in po.picking_ids]
            #     move_obj = self.pool.get('stock.move')
            #     move_search = move_obj.search(cr, uid, [('picking_id', '=', picking_ids), ('product_id', '=', line.product_id.id), ('state', 'not in', ('done','cancel'))])
            #     move_brw = move_obj.browse(cr, uid, move_search)
            #     qty_progress = 0
            #     for move in move_brw:
            #         qty_progress += move.product_uom_qty
            #     if line.product_qty - qty_barang_line > qty_progress:
            #         raise osv.except_osv(('Perhatian !'),('total move product %s yang akan dicancel (%s) lebih besar dari total move yang sedang dalam proses picking (%s)!') % (line.product_id.name, line.product_qty - qty_barang_line, qty_progress))
        obj_matrix = self.pool.get("dym.approval.matrixbiaya")
        if not obj_rb.retur_beli_line:
            raise osv.except_osv(('Perhatian !'), ("Retur belum diisi"))
        obj_matrix.request(cr, uid, ids, obj_rb, 'amount_total')
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True
           
    def wkf_approval(self, cr, uid, ids, context=None):
        obj_rb = self.browse(cr, uid, ids, context=context)
        if not obj_rb.retur_beli_line:
            raise osv.except_osv(('Perhatian !'), ("Retur belum diisi"))
        approval_sts = self.pool.get("dym.approval.matrixbiaya").approve(cr, uid, ids, obj_rb)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
   
        return True

    def has_approved(self, cr, uid, ids, *args):
        obj_rb = self.browse(cr, uid, ids)
        return obj_rb.approval_state == 'a'

    def has_rejected(self, cr, uid, ids, *args):
        obj_rb = self.browse(cr, uid, ids)
        if obj_rb.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
        obj_rb = self.browse(cr, uid, ids, context=context)
        for line in obj_rb.retur_beli_line:
            if line.lot_id and obj_rb.division == 'Unit':
                line.lot_id.write({'state': 'stock'})

    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})  
        obj_rb = self.browse(cr, uid, ids, context=context)
        for line in obj_rb.retur_beli_line:
            if line.lot_id and obj_rb.division == 'Unit':
                line.lot_id.write({'state': 'stock'})