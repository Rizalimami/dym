import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import netsvc

class dym_platform(models.Model):
    _inherit = "dym.request.platform"      
    
    approval_ids = fields.One2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)])
    approval_state =  fields.Selection([
                                        ('b','Belum Request'),
                                        ('rf','Request For Approval'),
                                        ('a','Approved'),
                                        ('r','Reject')
                                        ],'Approval State', readonly=True,default='b')
    
    @api.multi
    def wkf_request_approval(self):
        #obj_po = self.e(cr, uid, ids, context=context)
        obj_matrix = self.env['dym.approval.matrixbiaya'] 
        obj_matrix.request(self, 'approval_field')
        self.write({'state': 'waiting_for_approval','approval_state':'rf'})
        return True
    
    @api.multi      
    def wkf_approval(self):
        
        approval_sts = self.env['dym.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            partner = self.env['res.partner'].search([('id','=',self.partner_id.id)])
            if self.division == 'Unit' :
                partner.write({'credit_limit_unit':self.partner_id.credit_limit_unit + self.limit})  
            elif self.division == 'Sparepart' :
                partner.write({'credit_limit_sparepart':self.partner_id.credit_limit_sparepart + self.limit})                          
            self.write({'date':datetime.today(),'approval_state':'a','state':'approved','confirm_uid':self._uid,'confirm_date':datetime.now()})
            
        elif approval_sts == 0:
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
    
    @api.one
    def wkf_set_to_draft(self):
        self.write({'state':'draft','approval_state':'r'})