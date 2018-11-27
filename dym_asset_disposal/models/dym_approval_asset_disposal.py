import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc

class dym_asset_disposal_approval(osv.osv):
    _inherit = "dym.asset.disposal"
      
    _columns = {
                'approval_ids': fields.one2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
                'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),
    }
    
    _defaults ={
                'approval_state':'b'
                }
    
    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_bj = self.browse(cr, uid, ids, context=context)
        for asset in obj_bj.asset_disposal_line:
            obj_dispose_line = self.pool.get('dym.asset.disposal.line').search(cr, uid, [('dispose_id.state','not in',('draft','cancel')),('asset_id','=',asset.asset_id.id)])
            if obj_dispose_line:
                raise exceptions.ValidationError(('Asset [%s] %s sedang di proses oleh %s!') % (asset.asset_id.code, asset.asset_id.name, obj_dispose_line.dispose_id.name))
        obj_matrix = self.pool.get("dym.approval.matrixbiaya")
        if not obj_bj.asset_disposal_line:
            raise osv.except_osv(('Perhatian !'), ("Asset belum diisi"))
        obj_matrix.request(cr, uid, ids, obj_bj, 'amount_total')
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True
           
    def wkf_approval(self, cr, uid, ids, context=None):
        obj_bj = self.browse(cr, uid, ids, context=context)
        if not obj_bj.asset_disposal_line:
            raise osv.except_osv(('Perhatian !'), ("Asset belum diisi"))
        approval_sts = self.pool.get("dym.approval.matrixbiaya").approve(cr, uid, ids, obj_bj)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
   
        return True

    def has_approved(self, cr, uid, ids, *args):
        obj_bj = self.browse(cr, uid, ids)
        return obj_bj.approval_state == 'a'

    def has_rejected(self, cr, uid, ids, *args):
        obj_bj = self.browse(cr, uid, ids)
        if obj_bj.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})

    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})  