from openerp import models, fields, api
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import netsvc

class dym_clearing_giro_approval(models.Model):
    _inherit = 'dym.clearing.giro'
    
    approval_ids = fields.One2many('dym.approval.line', 'transaction_id', string="Table Approval", domain=[('form_id','=',_inherit)])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Reject')
    ], 'Approval State', readonly=True, default='b')
    approve_uid = fields.Many2one('res.users',string="Approved by")
    approve_date = fields.Datetime('Approved on')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')    
        
    @api.multi
    def wkf_request_approval(self):
        total_loan = 0
        if not self.move_line_ids:
            raise exceptions.ValidationError(("Silahkan isi detail journal terlebih dahulu"))
        obj_matrix = self.env['dym.approval.matrixbiaya']
        obj_matrix.request_by_value(self,self.total_giro)
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
        return True
    
    @api.multi
    def wkf_approval(self):
        approval_sts = self.env['dym.approval.matrixbiaya'].approve(self)
        if approval_sts == 1 :
            self.write({'approval_state':'a', 'state':'approved','approve_uid':self._uid,'approve_date':datetime.now()})
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