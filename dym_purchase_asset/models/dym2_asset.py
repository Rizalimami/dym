from openerp.osv import osv
import pdb
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import models,fields, exceptions, api, _
from datetime import datetime

class ProductCostAdjustment(models.Model):
    _inherit = 'account.asset.asset'

    approved_uid = fields.Many2one('res.users',string="Approved By")
    approved_date = fields.Datetime(string='Approved Date')
    approval_ids = fields.One2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)])
    approval_state = fields.Selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True, default='b')
    confirm_close_uid = fields.Many2one('res.users',string="Confirm close by")
    confirm_close_date = fields.Datetime('Confirm close on')

    @api.multi
    def confirm(self):
        self.write({'confirm_close_uid':self._uid,'confirm_close_date':datetime.now()})
        self.set_to_close()
        return True

    @api.multi
    def wkf_request_approval(self):
        obj_matrix = self.env["dym.approval.matrixbiaya"]
        obj_matrix.request_by_value(self, self.real_value_residual)
        self.write({'state': 'waiting_for_approval','approval_state':'rf'})
        return True
    
    @api.multi       
    def wkf_approval(self):
        approval_sts = self.env["dym.approval.matrixbiaya"].approve(self)
        if approval_sts == 1:
            self.write({'approval_state':'a','approved_date':datetime.now(),'approved_uid':self._uid,'state':'approved'})
        elif approval_sts == 0:
            raise exceptions.ValidationError(("User tidak termasuk group approval"))
        return True

    @api.multi
    def has_approved(self):
        if self.approval_state == 'a':
            return True
        return False
    
    @api.multi
    def has_rejected(self):
        if self.approval_state == 'r':
            self.write({'state':'open'})
            return True
        return False
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'open','approval_state':'r'})
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'open','approval_state':'b'})