import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID

class dym_cancel_kwitansi(models.Model):
    _name = "dym.cancel.kwitansi"
    _description ="Cancel Kwitansi"

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('validate','Posted'),
        ('cancel','Cancelled')
    ]
    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
            
    name = fields.Char(string="Name",readonly=True,default='')
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, default=_get_default_branch)
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date = fields.Date(string="Date",required=True,readonly=True,default=fields.Date.context_today)
    reason = fields.Char(string="Reason")
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], string='Division',default='Unit', required=True,change_default=True, select=True)    
    voucher_id = fields.Many2one(related='kwitansi_id.payment_id',string='Payment No')
    kwitansi_id = fields.Many2one('dym.register.kwitansi.line',string="Kwitansi No",domain="[('state','=','cancel'),('branch_id','=',branch_id),('payment_id','!=',False)]")
    confirm_uid = fields.Many2one('res.users',string="Validated by")
    confirm_date = fields.Datetime('Validated on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')    
    voucher_id_show = fields.Many2one('account.voucher',string="Payment No")
    
    @api.onchange('voucher_id')
    def changekwitansi(self):
        self.voucher_id_show  = self.voucher_id.id
 
    @api.model
    def create(self,vals,context=None):
     
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'CKW', division=vals['division'])     
        vals['date'] = time.strftime('%Y-%m-%d')                        
        kwitansi_id = super(dym_cancel_kwitansi, self).create(vals)

        return kwitansi_id

    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Form Cancel Kwitansi tidak bisa didelete karena sudah di validate !"))
        return super(dym_cancel_kwitansi, self).unlink(cr, uid, ids, context=context)         
        
                   
    @api.multi
    def validate_kwitansi(self):
        voucher = self.env['account.voucher']
        kwitansi = self.env['dym.register.kwitansi.line']
        
        kwitansi_id = kwitansi.search([
                                       ('id','=',self.kwitansi_id.id)
                                       ])
        if not kwitansi_id :
            raise osv.except_osv(('Perhatian !'), ("Nomor Kwitansi sudah dihapus !"))
                
        kwitansi_id.write({'state':'open','payment_id':False,'reason':False})
        self.state = 'validate'
        self.confirm_uid = self._uid
        self.confirm_date = datetime.now()
        self.voucher_id_show = self.voucher_id.id
        self.date = datetime.today()
        
