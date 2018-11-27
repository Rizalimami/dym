import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc

class dym_retur_jual_approval(osv.osv):
    _inherit = "dym.retur.jual"
      
    _columns = {
        'approval_ids': fields.one2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
        'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),
    }
    
    _defaults ={
        'approval_state':'b'
    }
    
    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_rj = self.browse(cr, uid, ids, context=context)
        for line in obj_rj.retur_jual_line:
            obj_retur_ids = self.pool.get('dym.retur.jual.line').search(cr, uid, [('retur_id.state','not in',('draft','cancel')),('dso_line_id','=',line.dso_line_id.id),('so_line_id','=',line.so_line_id.id),('id','!=',line.id)])
            total_returned = 0
            if obj_retur_ids:
                retur_line_browse = self.pool.get('dym.retur.jual.line').browse(cr, uid, obj_retur_ids)
                for retur_line in retur_line_browse:
                    total_returned += retur_line.product_qty
            qty = 0
            if obj_rj.division == 'Unit':
                if not line.retur_lot_id and obj_rj.retur_type == 'Barang':
                    raise osv.except_osv(('Perhatian !'),('Untuk tipe retur barang, engine number retur harus diisi!'))
                if line.retur_lot_id and obj_rj.retur_type == 'Barang':
                    id_quant = self.pool.get('stock.quant').search(cr, uid, [('lot_id','=',line.retur_lot_id.id),('location_id','=',line.retur_location_id.id),('product_id','=',line.retur_product_id.id),('lot_id.state','=','stock'),('reservation_id','=',False),('consolidated_date','!=',False)])
                    if not id_quant:
                        raise osv.except_osv(('Perhatian !'),('Nomor Engine retur tidak ditemukan, mohon pilih nomor engine retur lain'))
                    line.retur_lot_id.write({'state': 'reserved', 'customer_reserved': obj_rj.dso_id.partner_id.id})
                qty = line.dso_line_id.product_qty
            else:
                qty = line.so_line_id.product_uom_qty
            if total_returned + line.product_qty > qty and line.product_id:
                raise osv.except_osv(('Perhatian !'),('Jumlah retur line product %s  tidak boleh melebihi %s!') % (line.product_id.name, (qty - total_returned)))
        obj_matrix = self.pool.get("dym.approval.matrixbiaya")
        if not obj_rj.retur_jual_line:
            raise osv.except_osv(('Perhatian !'), ("Retur belum diisi"))
        obj_matrix.request(cr, uid, ids, obj_rj, 'amount_total')
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True
           
    def wkf_approval(self, cr, uid, ids, context=None):
        obj_rj = self.browse(cr, uid, ids, context=context)
        if not obj_rj.retur_jual_line:
            raise osv.except_osv(('Perhatian !'), ("Retur belum diisi"))
        approval_sts = self.pool.get("dym.approval.matrixbiaya").approve(cr, uid, ids, obj_rj)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
        return True

    def has_approved(self, cr, uid, ids, *args):
        obj_rj = self.browse(cr, uid, ids)
        return obj_rj.approval_state == 'a'

    def has_rejected(self, cr, uid, ids, *args):
        obj_rj = self.browse(cr, uid, ids)
        if obj_rj.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
        obj_rj = self.browse(cr, uid, ids, context=context)
        for line in obj_rj.retur_jual_line:
            if line.retur_lot_id and obj_rj.retur_type == 'Barang' and obj_rj.division == 'Unit':
                line.retur_lot_id.write({'state': 'stock', 'customer_reserved': False})

    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})  
        obj_rj = self.browse(cr, uid, ids, context=context)
        for line in obj_rj.retur_jual_line:
            if line.retur_lot_id and obj_rj.retur_type == 'Barang' and obj_rj.division == 'Unit':
                line.retur_lot_id.write({'state': 'stock', 'customer_reserved': False})