from openerp import models, fields, api
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import netsvc
from openerp.osv import osv
import pdb

class dym_sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.multi
    @api.depends('approval_ids') 
    def _cek_approval_line(self):
        for rec in self:
            so = False
            pic = False
            if rec.approval_ids.filtered(lambda s: s.sts == '1').mapped('approval_config_id').filtered(lambda r: r.code == ' ' and r.type == 'biaya'):
                so = True
            if rec.approval_ids.filtered(lambda s: s.sts == '1').mapped('approval_config_id').filtered(lambda r: r.code == 'pic' and r.type == 'biaya'):
                pic = True
            rec.approval_line_so = so
            rec.approval_line_pic = pic

    approval_ids = fields.One2many('dym.approval.line', 'transaction_id', string="Table Approval", domain=[('form_id','=',_inherit)])
    approval_state = fields.Selection([
                                       ('b','Belum Request'),
                                       ('rf','Request For Approval'),
                                       ('a','Approved'),
                                       ('r','Reject')
                                       ], 'Approval State', readonly=True, default='b')
    state = fields.Selection([
                                ('draft', 'Draft Quotation'),
                                ('waiting_for_approval','Waiting Approval'),
                                ('approved', 'Order Confirmed'),
                                ('sent', 'Quotation Sent'),
                                ('cancel', 'Cancelled'),
                                ('waiting_date', 'Waiting Schedule'),
                                ('progress', 'Sales Memo'),
                                ('manual', 'Sale to Invoice'),
                                ('shipping_except', 'Shipping Exception'),
                                ('invoice_except', 'Invoice Exception'),
                                ('done', 'Done'),
                            ], 'Status', default='draft', readonly=True, select=True, copy=False, help="Gives the status of the quotation or sales order.\
                              \nThe exception status is automatically set when a cancel operation occurs \
                              in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception).\nThe 'Waiting Schedule' status is set when the invoice is confirmed\
                               but waiting for the scheduler to run on the order date.")
    approve_uid = fields.Many2one('res.users',string="Approved by")
    approve_date = fields.Datetime('Approved on')
    approve_so = fields.Selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'SO Approved')
    approval_line_so = fields.Boolean(compute='_cek_approval_line', string="SO")
    approve_pic = fields.Selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'PIC Approved')
    approval_line_pic = fields.Boolean(compute='_cek_approval_line', string="PIC")
        
    @api.multi
    def wkf_request_approval(self):
        obj_matrix = self.env['dym.approval.matrixbiaya']
        if not self.order_line:
            raise osv.except_osv(('Perhatian !'), ("Produk belum diisi"))
                
        if len(self.payment_term.line_ids.ids) == 1 and self.payment_term.line_ids.days == 0:
            self.write({'order_policy':'prepaid'})
        discount_dealer = 0
        discount_show = 0
        for line in self.order_line:
            discount_dealer += line.discount_dealer
            discount_show += line.discount_show
            if line.price_unit < 1:
                raise osv.except_osv(('Perhatian !'), ("Unit Price Product '%s' tidak boleh '%s'" %(line.product_id.name,line.price_unit)))
            if line.product_uom_qty < 1:
                raise osv.except_osv(('Perhatian !'), ("QTY Product '%s' harus lebih dari %s" %(line.product_id.name,0)))
        total_diskon = self.discount_cash + discount_dealer + self.discount_lain + discount_show
        res_write = {'state':'waiting_for_approval', 'approval_state':'rf', 'approve_pic':'a'} 
        if total_diskon > 0:
            obj_matrix.request_by_value(self,total_diskon)
            # self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
        # else:
            # self.write({'approval_state':'a', 'state':'approved'})
        if self.tipe_transaksi == 'pic':
            obj_matrix.request_by_value(self, self.amount_total, code='pic')
            res_write['approve_pic'] = 'rf'
        if not total_diskon and self.tipe_transaksi != 'pic':
            res_write['approval_state'] = 'a'
            res_write['state'] = 'approved'
        self.write(res_write)
        return True
    

    @api.multi
    def wkf_to_draft(self):
        self.write({'approval_state':'b', 'state':'draft'})
        return True
    
    @api.multi
    def wkf_approval(self):
        approval_sts = self.env['dym.approval.matrixbiaya'].approve(self, code=' ')
        if (approval_sts == 1) and (self.approve_pic == 'a' or not self.approval_line_pic):
            self.write({'approval_state':'a', 'state':'approved','approve_uid':self._uid,'approve_date':datetime.now()})
        elif approval_sts == 1 :
            self.write({'approval_state':'a','approve_uid':self._uid,'approve_date':datetime.now()})
        elif approval_sts == 0 :
            raise exceptions.ValidationError( ("User tidak termasuk group approval"))
        return True

    @api.multi
    def wkf_approval_pic(self):
        approval_pic_sts = self.env['dym.approval.matrixbiaya'].approve(self, code='pic')
        if approval_pic_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval PIC"))
        elif (self.approve_so == 'a' or not self.approval_line_so) and (self.approve_pic == 'a' or not self.approval_line_pic):
            self.write({'approve_pic':'a', 'state':'approved'})
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