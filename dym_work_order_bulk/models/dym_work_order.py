#!/usr/bin/python

import time
from openerp import netsvc, workflow
from openerp import SUPERUSER_ID, models, api, _
from openerp.osv import fields, osv

import logging
_logger = logging.getLogger(__name__)


class dym_stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def create_packing_bulk(self, cr, uid, ids, context=None):
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
            return packing_draft
        
        obj_packing = self.pool.get('dym.stock.packing')
        obj_packing_line = self.pool.get('dym.stock.packing.line')
        branch_sender_id = False
        
        if picking_id.picking_type_code == 'interbranch_in' :
            branch_sender_id = picking_id.location_id.branch_id.id
        packing_vals = {
            'picking_id': picking_id.id,
            'branch_sender_id': branch_sender_id,
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
        return id_packing

class dym_start_stop_wo(osv.osv):
    _inherit = "dym.start.stop.wo"

    def btn_start_bulk(self, cr, uid, ids, context=None):
        tgl_start = time.strftime('%Y-%m-%d %H:%M:%S')
        a = self.browse(cr,uid,ids)
        obj_wo_a = self.pool.get('dym.work.order')
        obj_id_a = obj_wo_a.search(cr,uid,[('id','=',a.work_order_id.id)])
        obj_strt = obj_wo_a.browse(cr,uid,obj_id_a)
        inv = self.browse(cr, uid, ids[0], context=context)
        if obj_strt :
            obj_wo_a.write(cr, uid, obj_id_a, {'state_wo':'in_progress','start':tgl_start,'mekanik_id':inv.mekanik_id.id, 'pit_id':inv.pit_id.id}, context=context)
            self.write(cr, uid, ids, {'state_wo':'in_progress','start':tgl_start,'date_break':a.work_order_id.date_break,'end_break':a.work_order_id.end_break,'finish':a.work_order_id.finish}, context=context)
            workflow.trg_validate(uid, 'dym.work.order', obj_strt.id, 'start_wo', cr)
            obj_wo_time_line = self.pool.get('dym.start.stop.wo.time.line')
            time_line_values = {
                'start_stop_wo_id': obj_id_a[0],
                'state_time_line': 'start',
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            }  
            create_time_line = obj_wo_time_line.create(cr, uid, time_line_values)
        return True

    def btn_finish_bulk(self, cr, uid, ids, context=None):
        tgl_finish = time.strftime('%Y-%m-%d %H:%M:%S')
        d = self.browse(cr,uid,ids)
        obj_wo_d = self.pool.get('dym.work.order')
        obj_id_d = obj_wo_d.search(cr,uid,[('id','=',d.work_order_id.id)])
        obj_fns = obj_wo_d.browse(cr,uid,obj_id_d)
        
        if obj_fns :
            obj_wo_d.write(cr, uid, obj_id_d, {'state_wo':'finish','finish':tgl_finish}, context=context)
            self.write(cr, uid, ids, {'state_wo':'finish','finish':tgl_finish,'start':d.work_order_id.start,'date_break':d.work_order_id.date_break,'end_break':d.work_order_id.end_break}, context=context)
            workflow.trg_validate(uid, 'dym.work.order', obj_fns.id, 'end_wo', cr)

            obj_wo_time_line = self.pool.get('dym.start.stop.wo.time.line')
            time_line_values = {
                'start_stop_wo_id': obj_id_d[0],
                'state_time_line': 'finish',
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            }  
            create_time_line = obj_wo_time_line.create(cr, uid, time_line_values)  
        return True

class dym_work_order(osv.osv):
    _inherit = "dym.work.order"

    _columns = {
        'bulk_notes': fields.char('Bulk Notes')
    }

    def view_cpa_bulk(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')        
        result = mod_obj.get_object_reference(cr, uid, 'dealer_sale_order', 'action_vendor_receipt_workshop')
        
        id = result and result[1] or False        
        result = act_obj.read(cr, uid, [id], context=context)[0]
        
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        Voucher = self.pool.get('account.voucher')
        VoucherLine = self.pool.get('account.voucher.line')
        inv_ids = obj_inv.search(cr,uid,[
            ('origin','ilike',val.name),
            ('type','=','out_invoice')
        ])

        if not inv_ids:
            raise osv.except_osv(('Perhatian !'), ("Belum ada invoice"))

        ar_ids = []

        analytic_1 = False
        analytic_2 = False
        analytic_3 = False
        analytic_4 = False
        for inv in obj_inv.browse(cr, uid, inv_ids, context=context):
            analytic_1 = inv.analytic_1
            analytic_2 = inv.analytic_2
            analytic_3 = inv.analytic_3
            analytic_4 = inv.analytic_4
            if inv.move_id:
                move_line_ar = inv.move_id.line_id.filtered(lambda x:x.account_id.type=='receivable') or False
                if move_line_ar:
                    for ml_ar in move_line_ar:
                        ar_ids.append(ml_ar.id)
                else:
                    raise osv.except_osv(('Perhatian !'), ("Invoice belum divalidasi... (1)"))
            else:
                raise osv.except_osv(('Perhatian !'), ("Invoice belum divalidasi... (2)"))

        cpa_ids = []
        if ar_ids:
            voucher_line_ids = VoucherLine.search(cr, uid, [('move_line_id','in',ar_ids)], context=context)
            if voucher_line_ids:
                for voucher_line_id in VoucherLine.browse(cr, uid, voucher_line_ids, context=context):
                    if not voucher_line_id.voucher_id.id in cpa_ids:
                        cpa_ids.append(voucher_line_id.voucher_id.id)

        if not cpa_ids:
            if ar_ids:
                cpa_id = self.create_cpa(cr, uid, ids, ar_ids, analytic_1, analytic_2, analytic_3, analytic_4, context=context)
                cpa_ids.append(cpa_id)
        return cpa_ids

    def get_picking_bulk(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        pick_ids = []
        for po in self.browse(cr, uid, ids, context=context):
            pick_ids += [picking.id for picking in po.picking_ids]
        action['context'] = {}
        for picking in self.pool.get('stock.picking').browse(cr, uid, pick_ids, context=context):
            if picking.state=='assigned':
                packing_id = picking.create_packing_bulk()
                packing = self.pool.get('dym.stock.packing').browse(cr, uid, packing_id, context=context)
                if packing.state=='draft':
                    packing.post()
        return True

    def _work_order_bulk_validate(self, cr, uid, context=None):
        return self.work_order_bulk_validate(cr, uid, [], automatic=True, context=context)

    def work_order_bulk_validate(self, cr, uid, ids, automatic=False, context=None):
        context = context or {}
        invoice_ids = []
        WO = self.pool.get('dym.work.order')
        SSWO = self.pool.get('dym.start.stop.wo')
        domain =  [
            ('x_bulkid','!=',False),
            ('state','in',['draft','approved','finished'])
        ]
        draft_wos = WO.search(cr, uid, domain, context=context)
        for dwo in WO.browse(cr, uid, draft_wos, context=context):# Approve
            if dwo.state=='waiting_for_approval':
                print('-- Approve')
                client.exec_workflow('dym.work.order', 'approval_approve', dwo.id)
            if dwo.state=='approved' and dwo.state_wo != 'finish':
                sswo_id = SSWO.search(cr, uid, [('work_order_id','=',dwo.id)], context=context)
                if not sswo_id:
                    sswo_id = SSWO.create(cr, uid, {
                        'branch_id': dwo.branch_id.id,
                        'work_order_id': dwo.id,
                        'mekanik_id': dwo.mekanik_id.id,
                        'pit_id': dwo.pit_id.id,
                    }, context=context)
                sswo = SSWO.browse(cr, uid, sswo_id, context=context)
                sswo.btn_start_bulk()
                sswo.btn_finish_bulk()
            if dwo.shipped != True:
                self.get_picking_bulk(cr, uid, [dwo.id],context=context)
            if dwo.state=='finished':
                dwo.invoice_create_wo()




    
        