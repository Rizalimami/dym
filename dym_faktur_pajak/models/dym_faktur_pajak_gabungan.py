import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv
import time

class dym_faktur_pajak_gabungan(models.Model):
    _name = "dym.faktur.pajak.gabungan"
    _description = "Faktur Pajak Gabungan"

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancel','Cancelled')
    ]
            
    name = fields.Char(string="Name",readonly=True,default='')
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, default=_get_default_branch)
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date = fields.Date(string="Date",required=True,readonly=True,default=fields.Date.context_today)
    pajak_gabungan_line = fields.One2many('dym.faktur.pajak.gabungan.line','pajak_gabungan_id')
    company_id = fields.Many2one('res.company',string="Company")
    faktur_pajak_id = fields.Many2one('dym.faktur.pajak.out', 'No Faktur Pajak',domain="[('state','=','open'),('company_id','=',company_id)]")
    start_date = fields.Date(string="Transaction Date")
    end_date = fields.Date(string="End Date")
    customer_id = fields.Many2one('res.partner',string="Partner",domain="['|','|','|','|',('principle','!=',False),('biro_jasa','!=',False),('forwarder','!=',False),('supplier','!=',False),('customer','!=',False)]")
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], string='Division',default='Unit', required=True,change_default=True, select=True)
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    remark = fields.Char('Remark')
    faktur_pajak_tgl = fields.Date(string='Tgl Faktur Pajak',
                               related='faktur_pajak_id.date')
    in_out = fields.Selection([
                              ('in','In'),
                              ('out','Out'),
                              ], default='out', required=True, string='Faktur Type')
    no_faktur_pajak = fields.Char(string="No Faktur Pajak")
    tgl_faktur_pajak = fields.Date(string="Tgl Faktur Pajak")

    def faktur_pajak_change(self,cr,uid,ids,no_faktur_pajak,context=None):   
        value = {}
        warning = {}
        if no_faktur_pajak :
            cek = no_faktur_pajak.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Nomor Faktur Pajak Hanya Boleh Angka ! ')),
                }
                value = {
                         'no_faktur_pajak':False
                         }     
        return {'warning':warning,'value':value} 

    @api.onchange('in_out')
    def onchange_in_out(self):
        if self.in_out == 'in':
            self.faktur_pajak_id = False
        if self.in_out == 'out':
            self.no_faktur_pajak = False
            self.tgl_faktur_pajak = False

    @api.onchange('branch_id')
    def onchange_branch(self):
        self.company_id = self.branch_id.company_id

    @api.onchange('end_date')
    def onchange_date(self):
        warning = {}
        if self.end_date and self.start_date :
            if self.start_date > self.end_date :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (("End Date tidak boleh kurang dari Start Date")),
                }   
                self.end_date = False
        return {'warning':warning}

    
    @api.multi
    def action_generate(self):
        work_order = self.env['dym.work.order']
        other_receivable = self.env['account.voucher'] #type Sales
        sales_order = self.env['dealer.sale.order']
        sales_order_md = self.env['sale.order']
        asset_disposal = self.env['dym.asset.disposal']
        account_invoice = self.env['account.invoice']
        pajak_line = self.env['dym.faktur.pajak.gabungan.line']
        rekap = {}
        
        if self.in_out == 'out':
            so_data = sales_order.search([
                                         ('branch_id','=',self.branch_id.id),
                                         ('state','in',('approved','progress','done')),
                                         ('pajak_gabungan','=',True),
                                         ('faktur_pajak_id','=',False),
                                         ('partner_id','=',self.customer_id.id),
                                         ('division','=',self.division),
                                         ('date_order','>=',self.start_date),
                                         ('date_order','<=',self.end_date),
                                         ])

            wo_data = work_order.search([
                                         ('branch_id','=',self.branch_id.id),
                                         ('state','in',('confirmed','approved','finished','open','done')),
                                         ('pajak_gabungan','=',True),
                                         ('faktur_pajak_id','=',False),
                                         ('customer_id','=',self.customer_id.id),
                                         ('division','=',self.division),
                                         ('date','>=',self.start_date),
                                         ('date','<=',self.end_date),
                                         ]) 
            
            or_data = other_receivable.search([
                                         ('branch_id','=',self.branch_id.id),
                                         ('state','in',('proforma','posted')),
                                         ('pajak_gabungan','!=',False),
                                         ('type','=','sale'),
                                         ('faktur_pajak_id','=',False),
                                        ('partner_id','=',self.customer_id.id),
                                        ('division','=',self.division),
                                        ('date','>=',self.start_date),
                                        ('date','<=',self.end_date),
                                         ])  
            
            so_md_data = sales_order_md.search([
                                         ('branch_id','=',self.branch_id.id),
                                         ('state','in',('progress','manual','done')),
                                         ('pajak_gabungan','=',True),
                                         ('faktur_pajak_id','=',False),
                                         ('partner_id','=',self.customer_id.id),
                                         ('division','=',self.division),
                                         ('date_order','>=',self.start_date),
                                         ('date_order','<=',self.end_date),
                                         ])
                    
            ad_data = asset_disposal.search([
                                         ('branch_id','=',self.branch_id.id),
                                         ('state','in',('approved','confirmed','done','except_invoice')),
                                         ('pajak_gabungan','=',True),
                                         ('faktur_pajak_id','=',False),
                                         ('partner_id','=',self.customer_id.id),
                                         ('division','=',self.division),
                                         ('date','>=',self.start_date),
                                         ('date','<=',self.end_date),
                                         ])

            av_data = account_invoice.search([
                                         ('branch_id','=',self.branch_id.id),
                                         ('state','in',('open','paid')),
                                         ('pajak_gabungan','=',True),
                                         ('faktur_pajak_id','=',False),
                                         ('partner_id','=',self.customer_id.id),
                                         ('division','=',self.division),
                                         ('date_invoice','>=',self.start_date),
                                         ('date_invoice','<=',self.end_date),
                                         ('type','in',('out_invoice','in_refund')),
                                         ])

            if av_data :
                for x in av_data :
                    if not rekap.get(str(x.number)) :
                        rekap[str(x.number)] = {}                
                        rekap[str(x.number)]['date'] = x.date_invoice
                        rekap[str(x.number)]['total_amount'] = x.amount_total
                        rekap[str(x.number)]['untaxed_amount'] = x.amount_untaxed
                        rekap[str(x.number)]['tax_amount'] = x.amount_tax
                        rekap[str(x.number)]['model'] = 'account.invoice'

            if so_data :
                for x in so_data :
                    if not rekap.get(str(x.name)) :
                        rekap[str(x.name)] = {}                
                        rekap[str(x.name)]['date'] = x.date_order
                        rekap[str(x.name)]['total_amount'] = x.amount_total
                        rekap[str(x.name)]['untaxed_amount'] = x.amount_untaxed
                        rekap[str(x.name)]['tax_amount'] = x.amount_tax
                        rekap[str(x.name)]['model'] = 'dealer.sale.order'
            
            if wo_data :
                for x in wo_data :
                    if not rekap.get(str(x.name)) :
                        rekap[str(x.name)] = {}      
                        rekap[str(x.name)]['date'] = x.date
                        rekap[str(x.name)]['total_amount'] = x.amount_total
                        rekap[str(x.name)]['untaxed_amount'] = x.amount_untaxed
                        rekap[str(x.name)]['tax_amount'] = x.amount_tax   
                        rekap[str(x.name)]['model'] = 'dym.work.order' 
            
            if or_data :
                for x in or_data :
                    if not rekap.get(str(x.number)) :
                        rekap[str(x.number)] = {}                
                        rekap[str(x.number)]['date'] = x.date
                        rekap[str(x.number)]['total_amount'] = x.amount
                        rekap[str(x.number)]['untaxed_amount'] = x.amount - x.tax_amount
                        rekap[str(x.number)]['tax_amount'] = x.tax_amount   
                        rekap[str(x.number)]['model'] = 'account.voucher' 
            
            if so_md_data :
                for x in so_md_data :
                    if not rekap.get(str(x.name)) :
                        rekap[str(x.name)] = {}                
                        rekap[str(x.name)]['date'] = x.date_order
                        rekap[str(x.name)]['total_amount'] = x.amount_total
                        rekap[str(x.name)]['untaxed_amount'] = x.amount_untaxed
                        rekap[str(x.name)]['tax_amount'] = x.amount_tax
                        rekap[str(x.name)]['model'] = 'sale.order'
        
            if ad_data :
                for x in ad_data :
                    if not rekap.get(str(x.name)) :
                        rekap[str(x.name)] = {}                
                        rekap[str(x.name)]['date'] = x.date
                        rekap[str(x.name)]['total_amount'] = x.amount_total
                        rekap[str(x.name)]['untaxed_amount'] = x.amount_net_price
                        rekap[str(x.name)]['tax_amount'] = x.amount_tax
                        rekap[str(x.name)]['model'] = 'dym.asset.disposal'

        if self.in_out == 'in':
            inv_data = self.env['account.invoice'].search([
                                         ('branch_id','=',self.branch_id.id),
                                         ('state','in',('open','paid')),
                                         ('pajak_gabungan','=',True),
                                         ('faktur_pajak_id','=',False),
                                         ('partner_id','=',self.customer_id.id),
                                         ('division','=',self.division),
                                         ('date_invoice','>=',self.start_date),
                                         ('date_invoice','<=',self.end_date),
                                         ('type','in',('in_invoice','out_refund')),
                                         ])

            pr_data = self.env['account.voucher'].search([
                                         ('branch_id','=',self.branch_id.id),
                                         ('state','in',('approved','posted')),
                                         ('pajak_gabungan','!=',False),
                                         ('type','=','purchase'),
                                         ('faktur_pajak_id','=',False),
                                        ('partner_id','=',self.customer_id.id),
                                        ('division','=',self.division),
                                        ('date','>=',self.start_date),
                                        ('date','<=',self.end_date),
                                         ])  
                    
            if inv_data :
                for x in inv_data :
                    if not rekap.get(str(x.number)) :
                        rekap[str(x.number)] = {}                
                        rekap[str(x.number)]['date'] = x.date_invoice
                        rekap[str(x.number)]['total_amount'] = x.amount_total
                        rekap[str(x.number)]['untaxed_amount'] = x.amount_untaxed
                        rekap[str(x.number)]['tax_amount'] = x.amount_tax
                        rekap[str(x.number)]['model'] = 'account.invoice'

            if pr_data :
                for x in pr_data :
                    if not rekap.get(str(x.number)) :
                        rekap[str(x.number)] = {}                
                        rekap[str(x.number)]['date'] = x.date
                        rekap[str(x.number)]['total_amount'] = x.amount
                        rekap[str(x.number)]['untaxed_amount'] = x.amount - x.tax_amount
                        rekap[str(x.number)]['tax_amount'] = x.tax_amount   
                        rekap[str(x.number)]['model'] = 'account.voucher' 

        if rekap :
            for x,y in rekap.items() :
                pajak_line.create({
                                   'name':x,
                                   'model':y['model'],
                                   'pajak_gabungan_id':self.id,
                                   'date':y['date'],
                                   'total_amount':y['total_amount'],
                                   'untaxed_amount':y['untaxed_amount'],
                                   'tax_amount':y['tax_amount'],
                                   'model':y['model'],
                                   })
        if not rekap :
            raise osv.except_osv(('Perhatian !'), ('Data tidak ditemukan !'))  
                
    @api.multi
    def action_confirmed(self):
        if not self.pajak_gabungan_line :
            raise osv.except_osv(('Perhatian !'), ('Silahkan Generate data terlebih dahulu !'))   
        find_similar = self.search([
                                    ('id','!=',self.id),
                                    ('faktur_pajak_id','=',self.faktur_pajak_id.id),
                                    ('in_out','=','out'),
                                    ('state','!=','draft')
                                    ])
        if find_similar :
            raise osv.except_osv(('Perhatian !'), ('Nomor faktur pajak telah digunakan oleh no %s !')%(find_similar.name)) 
        
        work_order = self.env['dym.work.order']
        other_receivable = self.env['account.voucher'] #type Sales
        sales_order = self.env['dealer.sale.order'] 
        sales_order_md = self.env['sale.order'] 
        asset_disposal = self.env['dym.asset.disposal'] 
        account_invoice = self.env['account.invoice'] 
        pajak_out = self.env['dym.faktur.pajak.out'] 
        tax_amount = 0.0
        untaxed_amount = 0.0
        total_amount = 0.0
        vals = self.browse(self.id)
        
        model = self.env['ir.model'].search([
                                             ('model','=',vals.__class__.__name__)
                                             ])
        for x in self.pajak_gabungan_line :
            tax_amount += x.tax_amount
            untaxed_amount += x.untaxed_amount
            total_amount += x.total_amount
        if vals.in_out == 'out' and self.faktur_pajak_id.id:
            if self.faktur_pajak_id.state != 'open':
                raise osv.except_osv(('Perhatian !'), ("Faktur pajak %s sudah digunakan!")%(self.faktur_pajak_id.name))
            pajak_id = pajak_out.browse(self.faktur_pajak_id.id)
            pajak_id.write({
                            'state':'close',
                            'model_id':model.id,
                            'partner_id':self.customer_id.id,
                            'transaction_id':self.id,
                            'date':datetime.today(),
                            'untaxed_amount':untaxed_amount,
                            'amount_total':total_amount,
                            'tax_amount':tax_amount,
                            'pajak_gabungan':True,
                            'in_out':'out',
                            })
        elif vals.in_out == 'in':
            faktur_pajak_id = pajak_out.create({
                'name': self.no_faktur_pajak,
                'state': 'close',
                'thn_penggunaan' : int(self.tgl_faktur_pajak[:4]),
                'tgl_terbit' : self.tgl_faktur_pajak,
                'model_id':model.id,
                'amount_total':total_amount,
                'untaxed_amount':untaxed_amount,
                'tax_amount':tax_amount,
                'transaction_id':self.id,
                'date':datetime.today(),
                'partner_id':self.customer_id.id,
                'pajak_gabungan':True,
                'in_out':'in',
            })
            self.write({'faktur_pajak_id':faktur_pajak_id.id})

        for x in self.pajak_gabungan_line :
            if x.model == 'dym.work.order' :
                wo_data = work_order.search([
                                             ('name','=',x.name),
                                             ('faktur_pajak_id','=',False)
                                             ])
                if wo_data :
                    wo_data.write({
                                   'faktur_pajak_id':self.faktur_pajak_id.id
                                   })
                else :
                    raise osv.except_osv(('Perhatian !'), ('Detil dari pajak gabungan (%s) sudah diproses sebelumnya.')%(x.name))  
            elif x.model == 'dealer.sale.order' :
                so_data = sales_order.search([
                                             ('name','=',x.name),
                                             ('faktur_pajak_id','=',False)
                                             ])
                if so_data :
                    so_data.write({
                                   'faktur_pajak_id':self.faktur_pajak_id.id
                                   })  
                else :
                    raise osv.except_osv(('Perhatian !'), ('Detil dari pajak gabungan (%s) sudah diproses sebelumnya.')%(x.name))                     
            elif x.model == 'account.voucher' :
                or_data = other_receivable.search([
                                             ('number','=',x.name),
                                             ('faktur_pajak_id','=',False)
                                             ])
                if or_data :
                    if self.in_out == 'out':
                        or_data.write({
                                       'faktur_pajak_id':self.faktur_pajak_id.id
                                       })  
                    if self.in_out == 'in':
                        or_data.write({
                                       'faktur_pajak_id':faktur_pajak_id.id
                                       })  
                else :
                    raise osv.except_osv(('Perhatian !'), ('Detil dari pajak gabungan (%s) sudah diproses sebelumnya.')%(x.name))
            elif x.model == 'sale.order' :
                so_md_data = sales_order_md.search([
                                             ('name','=',x.name),
                                             ('faktur_pajak_id','=',False)
                                             ])
                if so_md_data :
                    so_md_data.write({
                                   'faktur_pajak_id':self.faktur_pajak_id.id
                                   })  
                else :
                    raise osv.except_osv(('Perhatian !'), ('Detil dari pajak gabungan (%s) sudah diproses sebelumnya.')%(x.name))
            elif x.model == 'dym.asset.disposal' :
                ad_data = asset_disposal.search([
                                             ('name','=',x.name),
                                             ('faktur_pajak_id','=',False)
                                             ])
                if ad_data :
                    ad_data.write({
                                   'faktur_pajak_id':self.faktur_pajak_id.id
                                   })  
                else :
                    raise osv.except_osv(('Perhatian !'), ('Detil dari pajak gabungan (%s) sudah diproses sebelumnya.')%(x.name))
            elif x.model == 'account.invoice' :
                acc_inv_data = self.env['account.invoice'].search([
                                             ('number','=',x.name),
                                             ('faktur_pajak_id','=',False)
                                             ])
                if acc_inv_data :
                    acc_inv_data.write({
                                   'faktur_pajak_id':faktur_pajak_id.id
                                   })  
                else :
                    raise osv.except_osv(('Perhatian !'), ('Detil dari pajak gabungan (%s) sudah diproses sebelumnya.')%(x.name))

        self.state = 'confirmed'    
        self.confirm_uid = self._uid
        self.confirm_date = datetime.now() 
        self.date = datetime.today()
                               
    @api.model
    def create(self,vals,context=None):  
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'FPG', division="Umum")     
        vals['date'] = time.strftime('%Y-%m-%d')                         
        pajak_gab = super(dym_faktur_pajak_gabungan, self).create(vals)
        return pajak_gab 
    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Faktur Pajak Gabungan sudah diproses, data tidak bisa didelete !"))
        return super(dym_faktur_pajak_gabungan, self).unlink(cr, uid, ids, context=context)     
            
class dym_faktur_pajak_gabungan_line(models.Model):
    _name = "dym.faktur.pajak.gabungan.line"
    _description = "Faktur Pajak Gabungan Line"
    
    pajak_gabungan_id = fields.Many2one('dym.faktur.pajak.gabungan')
    model = fields.Char(string='Object Name')
    name = fields.Char(string="Transaction No")
    date = fields.Date(string='Date')
    total_amount = fields.Float(string="Total Amount")
    untaxed_amount = fields.Float(string="Untaxed Amount")
    tax_amount = fields.Float(string="Tax Amount")