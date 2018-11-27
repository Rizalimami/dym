from openerp import models, fields, api
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import netsvc


class dym2_transfer_asset_approval(models.Model):
    _inherit = 'dym2.transfer.asset'
    
    approval_ids = fields.One2many('dym.approval.line', 'transaction_id', string="Table Approval", domain=[('form_id','=',_inherit)])
    approval_state = fields.Selection([
                                       ('b','Belum Request'),
                                       ('rf','Request For Approval'),
                                       ('a','Approved'),
                                       ('r','Reject')
                                       ], 'Approval State', readonly=True, default='b')
    confirm_uid = fields.Many2one('res.users',string="Approved by")
    confirm_date = fields.Datetime('Approved on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')    
        
    @api.multi
    def wkf_request_approval(self):
        for asset in self.transfer_line:
            obj_transfer_line = self.env['dym2.transfer.asset.line'].search([('transfer_id.state','in',('waiting_for_approval','approved')),('asset_id','=',asset.asset_id.id)])
            if obj_transfer_line:
                raise exceptions.ValidationError(('Asset [%s] %s sedang di proses oleh %s!') % (asset.asset_id.code, asset.asset_id.name, obj_transfer_line.transfer_id.name))

            if asset.asset_id.branch_id != self.branch_id:
                raise exceptions.ValidationError(('Lokasi asset [%s] %s ada di %s!') % (asset.asset_id.code, asset.asset_id.name, asset.asset_id.branch_id.name))
        obj_matrix = self.env['dym.approval.matrixbiaya']
        obj_matrix.request_by_value(self,0.00)
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
        return True
    
    @api.multi
    def wkf_approval(self):
        approval_sts = self.env['dym.approval.matrixbiaya'].approve(self)
        if approval_sts == 1 :
            self.write({'rel_date':datetime.today(),'approval_state':'a', 'state':'approved','confirm_uid':self._uid,'confirm_date':datetime.now()})
        elif approval_sts == 0 :
            raise exceptions.ValidationError( ("User tidak termasuk group approval"))
        return True
    
    @api.multi
    def has_approved(self):
        if self.approval_state == 'a':
            return True
        return False
    
    @api.multi
    def has_rejected(self):
        if self.approval_state == 'r':
            self.write({'state':'draft'})
            return True
        return False
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})