from openerp import models, fields, api
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import netsvc
from openerp.osv import osv

# class dym_alokasi_titipan_approval(models.Model):
#     _inherit = 'dym.alokasi.titipan'
    
#     approval_ids = fields.One2many('dym.approval.line', 'transaction_id', string="Table Approval", domain=[('form_id','=',_inherit)])
#     approval_state = fields.Selection([
#                                        ('b','Belum Request'),
#                                        ('rf','Request For Approval'),
#                                        ('a','Approved'),
#                                        ('r','Reject')
#                                        ], 'Approval State', readonly=True, default='b')
#     approve_uid = fields.Many2one('res.users',string="Approved by")
#     approve_date = fields.Datetime('Approved on')
#     confirm_uid = fields.Many2one('res.users',string="Confirmed by")
#     confirm_date = fields.Datetime('Confirmed on')
#     cancel_uid = fields.Many2one('res.users',string="Cancelled by")
#     cancel_date = fields.Datetime('Cancelled on')    
        
#     @api.multi
#     def wkf_request_approval(self):
#         titipan_line_list = []
#         titipan_line_dict = {}
#         for line in self.line_ids:
#             if line.titipan_line_id not in titipan_line_list:
#                 titipan_line_list.append(line.titipan_line_id)
#                 titipan_line_dict[line.titipan_line_id] = {'amount':0}
#             titipan_line_dict[line.titipan_line_id]['amount'] += line.amount
#         for titipan_line in titipan_line_list:
#             allocated_amount = titipan_line_dict[titipan_line]['amount']
#             if allocated_amount > titipan_line.fake_balance:
#                 raise osv.except_osv(('Tidak bisa request approval!'), ("Total Customer Deposit [%s] untuk titipan %s lebih besar dari balance yang bisa dialokasikan [%s]")%(allocated_amount, titipan_line.name, titipan_line.fake_balance))
#         obj_matrix = self.env['dym.approval.matrixbiaya']
#         obj_matrix.request_by_value(self,self.total_alokasi)
#         self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
#         return True
    

#     @api.multi
#     def wkf_approval(self):
#         titipan_line_list = []
#         titipan_line_dict = {}
#         for line in self.line_ids:
#             if line.titipan_line_id not in titipan_line_list:
#                 titipan_line_list.append(line.titipan_line_id)
#                 titipan_line_dict[line.titipan_line_id] = {'amount':0}
#             titipan_line_dict[line.titipan_line_id]['amount'] += line.amount
#         for titipan_line in titipan_line_list:
#             allocated_amount = titipan_line_dict[titipan_line]['amount']
#             if allocated_amount > titipan_line.fake_balance:
#                 raise osv.except_osv(('Tidak bisa approve!'), ("Total Customer Deposit [%s] untuk titipan %s lebih besar dari balance yang bisa dialokasikan [%s]")%(allocated_amount, titipan_line.name, titipan_line.fake_balance))
#         approval_sts = self.env['dym.approval.matrixbiaya'].approve(self)
#         if approval_sts == 1 :
#             self.write({'approval_state':'a', 'state':'approved','approve_uid':self._uid,'approve_date':datetime.now()})
#         elif approval_sts == 0 :
#             raise exceptions.ValidationError( ("User tidak termasuk group approval"))
#         return True

#     @api.multi
#     def has_approved(self):
#         if self.approval_state == 'a':
#             return True
#         return False
    
#     @api.multi
#     def has_rejected(self):
#         if self.approval_state == 'r':
#             self.write({'state':'draft'})
#             return True
#         return False
    
#     @api.cr_uid_ids_context
#     def wkf_set_to_draft(self, cr, uid, ids, context=None):
#         self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
    
#     @api.cr_uid_ids_context
#     def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
#         self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})