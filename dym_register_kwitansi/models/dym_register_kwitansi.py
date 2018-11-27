import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class dym_account_move_line(models.Model):
    _inherit = "account.move.line"
    
    kwitansi_id = fields.Many2one('dym.register.kwitansi.line',string='No Kwitansi')
    
class dym_register_kwitansi(models.Model):
    
    _name = "dym.register.kwitansi"
    _description = "Register Kwitansi Dealer"
    _order = "id asc"

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    name = fields.Char(string='Register Kwitansi')
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
    register_kwitansi_ids = fields.One2many('dym.register.kwitansi.line','register_kwitansi_id',readonly=True,ondelete='cascade')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')

    @api.multi
    def get_sequence(self,branch_id,context=None):
        doc_code = self.env['dym.branch'].browse(branch_id).doc_code
        seq_name = 'REG/KWT/{0}'.format(doc_code)
        seq = self.env['ir.sequence']
        ids = seq.sudo().search([('name','=',seq_name)])
        if not ids:
            prefix = '/%(y)s/%(month)s/'
            prefix = seq_name + prefix
            ids = seq.create({'name':seq_name,
                                 'implementation':'no_gap',
                                 'prefix':prefix,
                                 'padding':5})
        
        return seq.get_id(ids.id)
    
    @api.model
    def create(self,values,context=None):
        vals = []
        values['name'] = self.get_sequence(values['branch_id'],context)
        values['date'] = datetime.today()
        dym_register_kwit = super(dym_register_kwitansi,self).create(values)
        
        return dym_register_kwit
    
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
            
        self.write({'date':datetime.today(),'register_kwitansi_ids': vals,'state':'posted','confirm_uid':self._uid,'confirm_date':datetime.now()})
        
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
            self.prefix=self.prefix=self.branch_id.doc_code+"/KWT/"
          
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Register Kwitansi sudah diproses, data tidak bisa didelete !"))
        return super(dym_register_kwitansi, self).unlink(cr, uid, ids, context=context) 
            
class dealer_register_spk_line(models.Model):
    
    _name = 'dym.register.kwitansi.line'
    #_inherit = ['mail.thread']
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    register_kwitansi_id = fields.Many2one('dym.register.kwitansi')
    name = fields.Char(string='No. Register')
    branch_id = fields.Many2one('dym.branch',string='Branch', default=_get_default_branch)
    payment_id = fields.Many2one('account.voucher',string = 'Payment No.')
    state = fields.Selection([
                              ('open','Open'),
                              ('printed','Printed'),
                              ('cancel','Canceled'),
                              ('rusak','Rusak'),
                              ('hilang','Hilang'),
                              ],default='draft')
    state_register = fields.Selection(related='state',string='State')
    reason = fields.Char('Reason')
    
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