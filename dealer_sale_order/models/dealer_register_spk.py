import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class dealer_register_spk(models.Model):
    
    _name = "dealer.register.spk"
    _description = "Register Memo Dealer"
    _order = "id asc"

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    name = fields.Char(string='Register Memo')
    date = fields.Date(string='Date',required=True,default=fields.Date.context_today)
    branch_id = fields.Many2one('dym.branch', string ='Branch',required=True, default=_get_default_branch)
    prefix = fields.Char(string='Prefix',required=True)
    nomor_awal = fields.Char(string ='Nomor Awal',required=True,default=1)
    nomor_akhir = fields.Char(string ='Nomor akhir',required=True,default=2)
    padding = fields.Char(string='Padding',required=True,default=8)
    state = fields.Selection([
        ('draft','Draft'),
        ('posted','Posted'),
    ],default='draft')
    register_spk_ids = fields.One2many('dealer.register.spk.line','register_spk_id',readonly=True,ondelete='cascade')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')    
    
    @api.model
    def create(self,values,context=None):
        vals = {}
        values['name'] = self.env['ir.sequence'].get_per_branch(values['branch_id'], 'REG/MEMO', division='Unit')
        values['date'] = datetime.today()
        dealer_register_spks = super(dealer_register_spk,self).create(values)
        return dealer_register_spks
    
    @api.multi
    def action_post(self):
        vals = []
        padding ="{0:0"+str(self.padding)+"d}"
        for number in range(int(self.nomor_awal),int(self.nomor_akhir)+1):
            vals.append([0,0,{
                'name': self.prefix+padding.format(number),
                'state': 'open',
                'branch_id': self.branch_id.id
            }])
        self.write({'date':datetime.today(),'register_spk_ids': vals,'state':'posted','confirm_uid':self._uid,'confirm_date':datetime.now()})
        return True
   
    @api.onchange('nomor_awal','nomor_akhir','branch_id','padding')
    def nomor_awal_change(self):
        if int(self.nomor_awal) <= 0:
            self.nomor_awal = 1
            self.nomor_akhir = int(self.nomor_awal)+1
            return {'warning':{'title':'Attention!','message':'Nomor awal harus > 0'}}
        if int(self.nomor_akhir) <= int(self.nomor_awal):
            self.nomor_akhir = int(self.nomor_awal)+1
        if int(self.padding) <=0:
            self.padding = 8
            return {'warning':{'title':'Attention!','message':'Padding harus > 0'}}
        if self.branch_id:
            self.prefix=self.prefix=self.branch_id.doc_code+"/MEMO/"
            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Dealer Register Memo sudah diproses, data tidak bisa didelete !"))
        return super(dealer_register_spk, self).unlink(cr, uid, ids, context=context)           
        
class dealer_register_spk_line(models.Model):
    
    _name = 'dealer.register.spk.line'
    #_inherit = ['mail.thread']
    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    register_spk_id = fields.Many2one('dealer.register.spk')
    name = fields.Char(string='No. Register')
    branch_id = fields.Many2one('dym.branch',string='Branch', default=_get_default_branch)
    state = fields.Selection([
        ('draft','Draft'),
        ('open','Open'),
        ('reserved','Reserved'),
        ('spk','Memo'),
        ('so','SO'),
        ('cancelled','Cancelled'),
        ('rusak','Rusak'),
        ('hilang','Hilang'),
    ], default='draft')
    state_register = fields.Selection(related='state',string='State')
    tanggal_distribusi= fields.Date(string='Tanggal Distribusi')
    tanggal_kembali = fields.Date(string='Tanggal Kembali')
    sales_id = fields.Many2one('hr.employee',string='Salesman')
    spk_id = fields.Many2one('dealer.spk',string ='Memo')
    dealer_sale_order_id = fields.Many2one('dealer.sale.order',string='Dealer Sales Memo')
    dealer_spk_line = fields.One2many('dealer.spk','register_spk_id', 'Dealer Memo Line')
    reason_kembali = fields.Text('Reason Pengembalian Memo')
    

    _sql_constraints = [
        ('unique_nomor_register', 'unique(name)', 'Nomor register sudah pernah dibuat !'),
    ]

    @api.multi
    def set_rusak(self):
        self.write({'state':'rusak'})
        return True

    @api.multi
    def set_hilang(self):
        self.write({'state':'hilang'})
        return True

    @api.multi
    def kembalikan_distribusi(self):
        self.write({'state':'open','sales_id':False,'tanggal_distribusi':False})
        return True
