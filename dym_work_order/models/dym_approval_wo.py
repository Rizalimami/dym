import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc
import pdb
class dym_work_order(osv.osv):
    _inherit = "dym.work.order"      
    _columns = {
                'approval_ids': fields.one2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
                'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),  
    }
    
    _defaults ={
                'approval_state':'b'
                }

    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_po = self.browse(cr, uid, ids, context=context)
        obj_matrix = self.pool.get("dym.approval.matrixbiaya")
        if not obj_po.work_lines:
            raise osv.except_osv(('Perhatian !'), ("Produk belum diisi"))
        discount=0.0
        for line in obj_po.work_lines:
            if line.categ_id=='Sparepart' and not line.location_id:
                raise osv.except_osv(('Perhatian !'), ("Lokasi item belum diisi"))
            self.pool.get('dym.work.order.line').write(cr,uid,line.id,{'state': 'confirmed'})
            if obj_po.type == 'KPB' and obj_po.kpb_ke == '1':
                discount += line.discount + line.discount_program
            else:
                discount += line.discount + line.discount_program + line.discount_bundle
        if discount > 0.0 and not obj_po.customer_id.member:
            obj_matrix.request_by_value(cr, uid, ids, obj_po, discount)
            self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        if discount > 0.0 and obj_po.customer_id.member:
            return False
        return True

    def wkf_approval(self, cr, uid, ids, context=None):           
        obj_po = self.browse(cr, uid, ids, context=context)
        if not obj_po.work_lines:
            raise osv.except_osv(('Perhatian !'), ("produk belum diisi"))
        discount=0.0
        for line in obj_po.work_lines:
            if obj_po.type == 'KPB' and obj_po.kpb_ke == '1':
                discount += line.discount + line.discount_program
            else:
                discount += line.discount + line.discount_program + line.discount_bundle
        if discount > 0.0:
            approval_sts = self.pool.get("dym.approval.matrixbiaya").approve(cr, uid, ids, obj_po)
            if approval_sts == 1:
                self.write(cr, uid, ids, {'date':datetime.today(),'approval_state':'a','confirm_uid':uid,'confirm_date':datetime.now()})
            elif approval_sts == 0:
                raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
        else:
            self.write(cr, uid, ids, {'date':datetime.today(),'approval_state':'a','confirm_uid':uid,'confirm_date':datetime.now()})
        return True

    def discount_is_zero(self, cr, uid, ids, *args):        
        obj_po = self.browse(cr, uid, ids)
        if obj_po.type == 'WAR':
            return True
        discount=0.0
        for line in obj_po.work_lines:
            if obj_po.type == 'KPB' and obj_po.kpb_ke == '1':
                discount += line.discount + line.discount_program
            else:
                discount += line.discount + line.discount_program + line.discount_bundle
        if discount == 0.0:
            # self.write(cr, uid, ids, {'date':datetime.today(),'approval_state':'a','confirm_uid':uid,'confirm_date':datetime.now()})
            return True
        if discount > 0.0 and obj_po.customer_id.member:
            return True
        return False

    def has_approved(self, cr, uid, ids, *args):
        obj_po = self.browse(cr, uid, ids)
        return obj_po.approval_state == 'a'

    def has_rejected(self, cr, uid, ids, *args):
        obj_po = self.browse(cr, uid, ids)
        if obj_po.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
	cr.execute('UPDATE dym_work_order_line SET state=%s WHERE work_order_id in %s', ('draft', tuple(ids)))
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
    
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
	cr.execute('UPDATE dym_work_order_line SET state=%s WHERE work_order_id in %s', ('draft', tuple(ids)))
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})
        
class dym_reason_reject_approval(osv.osv_memory):
    _name = "dym.reason.reject.approval.wo"
    _columns = {
                'reason':fields.text('Reason')
                }
    
    def dym_reject_approval(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context=context)
        user = self.pool.get("res.users").browse(cr, uid, uid)['groups_id']
        
        po_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
        
        line = self.pool.get("dym.work.order").browse(cr,uid,po_id,context=context)
        objek = False
        for x in line.approval_ids :
            for y in user:
                    if y == x.group_id :
                        objek = True
                        for z in line.approval_ids :
                            if z.reason == False :
                                z.write({
                                        'reason':val.reason,
                                        'value':line.amount_total,
                                        'sts':'3',
                                        'pelaksana_id':uid,
                                        'tanggal':datetime.today()
                                        }) 
        
                                self.pool.get("dym.work.order").write(cr, uid, po_id, {'state':'draft','approval_state':'r'})
        if objek == False :
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
                                                      
        return True    