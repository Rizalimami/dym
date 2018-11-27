import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import openerp.addons.decimal_precision as dp
from openerp.osv import osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF

class dym_faktur_pajak(models.Model):

    _name = "dym.faktur.pajak"
    _description = "Faktur Pajak"
    _order = "id asc"


    @api.model
    def _get_default_year(self):
        year = datetime.now().year
        return year

    @api.model
    def _get_default_company(self):
        return self.env.user.company_id.id

    name = fields.Char(string='Faktur Pajak')
    date = fields.Date(string='Date',required=True,default=fields.Date.context_today)
    prefix = fields.Char(string='Prefix',required=True)
    counter_start = fields.Integer(string ='Counter Start',required=True,default=1)
    counter_end = fields.Integer(string ='Counter End',required=True,default=2)
    padding = fields.Integer(string='Padding',required=True,default=8)
    state = fields.Selection([
        ('draft','Draft'),
        ('cancel','Cancel'),
        ('posted','Posted'),
    ], default='draft')
    faktur_pajak_ids = fields.One2many('dym.faktur.pajak.out','faktur_pajak_id',readonly=True)
    company_id = fields.Many2one('res.company',string="Company", default=_get_default_company)
    branch_id = fields.Many2one('dym.branch', string='Branch')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    thn_penggunaan = fields.Integer(string="Tahun Penggunaan", default=_get_default_year)
    tgl_terbit = fields.Date(string="Tgl Terbit")
    no_document = fields.Char('No Document')
    
    @api.model
    def create(self,values,context=None):
        vals = []
        values['name'] = self.env['ir.sequence'].get_sequence('GFP', division='Umum')     
        values['date'] = datetime.today()
        if len(str(values.get('thn_penggunaan','1'))) < 4 or len(str(values.get('thn_penggunaan','1'))) > 4 :
            raise osv.except_osv(('Perhatian !'), ("Tahun Pembuatan harus 4 digit !"))
        faktur_pajak = super(dym_faktur_pajak,self).create(values)       
        return faktur_pajak
    
    @api.onchange('company_id')
    def onchange_company_id(self):
        if self.company_id and self.jenis_npwp=='percabang':
            branch_ids = self.env['dym.branch'].search([('company_id','=',self.company_id.id)])
            branch_ids = [b.id for b in branch_ids if not b.name.startswith('HO ')]
            return {
                'domain': {
                    'branch_id': [('id','in',branch_ids)]
                }
            }

    @api.onchange('thn_penggunaan')
    def onchange_tahun_penggunaan(self):
        warning = {}        
        if self.thn_penggunaan :
            tahun = len(str(self.thn_penggunaan))
            if tahun > 4 or tahun < 4 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Tahun hanya boleh 4 digit ! ')),
                }
                self.thn_penggunaan = False                
        return {'warning':warning} 

    @api.multi
    def action_post(self):
        vals = []
        padding ="{0:0"+str(self.padding)+"d}"
        numbers = []
        existing_numbers = [x.name for x in self.faktur_pajak_ids]
        if existing_numbers:
            pass
        else:
            for number in range(self.counter_start,self.counter_end+1):
                vals.append([0,0,{
                    'name': self.prefix+padding.format(number),
                    'state': 'open',
                    'thn_penggunaan' : self.thn_penggunaan,
                    'tgl_terbit' : self.tgl_terbit,
                    'in_out':'out',
                    'company_id':self.company_id.id,
                }])
            values = {
                'date':datetime.today(),
                'faktur_pajak_ids': vals,
                'state':'posted',
                'confirm_uid':self._uid,
                'confirm_date':datetime.now()
            }
            self.write(values)
        return True

    @api.one
    def action_cancel(self):
        self.state = 'cancel'
        
    @api.one
    def action_reset(self):
        self.state = 'draft'
   
    @api.onchange('counter_start','counter_end')
    def counter_start_change(self):
        if self.counter_start <= 0:
            self.counter_start = 1
            self.counter_end = self.counter_start
            return {'warning':{'title':'Attention!','message':'Counter Start harus > 0'}}
        
        if self.counter_end <= self.counter_start:
            self.counter_end = self.counter_start
        
        if self.padding <=0:
            return {'warning':{'title':'Attention!','message':'Padding harus > 0'}}
    
          
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Generate Faktur Pajak sudah diproses, data tidak bisa didelete !"))
        return super(dym_faktur_pajak, self).unlink(cr, uid, ids, context=context) 
            
class dym_faktur_pajak_out(models.Model):
    _name = 'dym.faktur.pajak.out'
    _order = 'masa desc, date desc'

    @api.cr_uid_ids_context
    def _get_default_company(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.company').search(cr,uid,[]) 
        browse =   self.pool.get('res.company').browse(cr,uid,user_obj)     
        return browse[0].id or False

    @api.model
    @api.depends('date')
    def _get_masa(self):
        if self.date:
            return datetime.strptime(self.date,DSDF).strftime('%Y/%s')
            
    @api.one
    @api.depends('date')
    def _get_masa_pajak(self):
	if self.date:
		self.masa = datetime.strptime(self.date,DSDF).strftime('%Y/%s')

    faktur_pajak_id = fields.Many2one('dym.faktur.pajak')
    branch_ids = fields.Many2many('dym.branch','dym_bank_account_cabang_rel','bank_account_id','branch_id', 'Branchs')
    name = fields.Char(string='Faktur Pajak')
    transaction_id = fields.Integer('Transaction ID')
    export_efaktur = fields.Boolean('Export EF')
    state = fields.Selection([
        ('open','Open'),
        ('close','Closed'),
        ('print','Printed'),
        ('cancel','Canceled'),
    ],default='open')
    untaxed_amount = fields.Float('Untaxed Amount')
    tax_amount = fields.Float('Tax Amount')
    amount_total = fields.Float('Total Amount')
    date = fields.Date('Date')
    masa = fields.Char(string='Masa Pajak', compute=_get_masa_pajak, default=_get_masa, store=True)
    partner_id = fields.Many2one('res.partner',string='Partner')
    npwp = fields.Char(related="partner_id.npwp")
    model_id = fields.Many2one('ir.model',string='Model')
    state_register = fields.Selection(related='state',string='State')
    pajak_gabungan = fields.Boolean('Pajak Gabungan')
    pajak_gunggung = fields.Boolean('Pajak Gunggung')
    signature_id = fields.Many2one('dym.signature',string='Signature By')
    cetak_ke = fields.Integer('Cetak ke')
    company_id = fields.Many2one('res.company',string='Company')
    thn_penggunaan = fields.Integer(string="Tahun Penggunaan")
    tgl_terbit = fields.Date(string="Tgl Terbit")
    keterangan = fields.Text(string="Keterangan")
    kode_transaksi = fields.Char(string="Kode Transaksi")
    in_out = fields.Selection([
        ('in','In'),
        ('out','Out'),
    ])

    @api.multi
    def view_transaction(self):
        print "====== view_transaction ======="
        print "--->",self.transaction_id, self.model_id

        return {
            'name': 'View Transaction',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.model_id.model,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': self.transaction_id
        }


    @api.constrains('name','in_out')
    def _unique_nomor_faktur_pajak(self):
        if self.in_out == 'out' and self.name:
            fp_data = self.search([('in_out','=','out'),('name','=',self.name),('id','!=',self.id)])
            if fp_data:
                raise ValidationError("Nomor Faktur Pajak sudah pernah dibuat !")

    def get_no_faktur_pajak(self,cr,uid,ids,object,context=None):
        vals = self.pool.get(object).browse(cr,uid,ids)
        faktur_pajak = self.pool.get('dym.faktur.pajak.out')
        if object == 'dealer.sale.order' :
            thn_penggunaan = int(vals.date_order[:4])
            tgl_terbit = vals.date_order
        elif object == 'dym.work.order' :
            thn_penggunaan = int(vals.date[:4])
            tgl_terbit = vals.date
        elif object == 'account.voucher' :
            thn_penggunaan = int(vals.date[:4])
            tgl_terbit = vals.date
        elif object == 'sale.order' :
            thn_penggunaan = int(vals.date_order[:4])
            tgl_terbit = vals.date_order            
        elif object == 'dym.asset.disposal' :
            thn_penggunaan = int(vals.date[:4])
            tgl_terbit = vals.date         
        elif object == 'account.invoice' :
            thn_penggunaan = int(vals.date_invoice[:4])
            tgl_terbit = vals.date_invoice             

        domain = []        
        if vals.branch_id.company_id.jenis_npwp == 'percabang':
            domain += [('branch_id','=',vals.branch_id.id)]
        domain += [
            ('state','=','open'),
            ('thn_penggunaan','=',thn_penggunaan),
            ('tgl_terbit','<=',tgl_terbit),
            ('company_id','=',vals.branch_id.company_id.id)
        ]
        no_fp = faktur_pajak.search(cr, uid, domain, limit=1, order='id')
        
        if not no_fp :
            raise osv.except_osv(('Perhatian !'), ("Nomor faktur pajak tidak ditemukan, silahkan Generate terlebih dahulu !"))
        
        vals.write({'faktur_pajak_id':no_fp[0]})
        model = self.pool.get('ir.model').search(cr,uid,[
                                                         ('model','=',vals.__class__.__name__)
                                                         ])
        if object == 'dealer.sale.order' :
            faktur_pajak.write(cr,uid,no_fp,{'model_id':model[0],
                                            'amount_total':vals.amount_total,
                                            'untaxed_amount':vals.amount_untaxed,
                                            'tax_amount':vals.amount_tax,                                                    
                                            'state':'close',
                                            'transaction_id':vals.id,
                                            'date':vals.date_order,
                                            'partner_id':vals.partner_id.id,
                                            'in_out':'out',
                                                    })   
        elif object == 'dym.work.order' :
            faktur_pajak.write(cr,uid,no_fp,{'model_id':model[0],
                                            'amount_total':vals.amount_total,
                                            'untaxed_amount':vals.amount_untaxed,
                                            'tax_amount':vals.amount_tax,                                                    
                                            'state':'close',
                                            'transaction_id':vals.id,
                                            'date':vals.date,
                                            'partner_id':vals.customer_id.id,
                                            'in_out':'out',
                                                })    
        
        elif object == 'account.voucher' :
            total = 0.0
            for x in vals.line_cr_ids :
                total += x.amount
            tax = vals.amount - total
            faktur_pajak.write(cr,uid,no_fp,{'model_id':model[0],
                                            'amount_total':vals.amount,
                                            'untaxed_amount':total ,
                                            'tax_amount':tax,
                                            'state':'close',
                                            'transaction_id':vals.id,
                                            'date':vals.date,
                                            'partner_id':vals.partner_id.id,
                                            'in_out':'out',
                                                    }) 
        elif object == 'sale.order' :
            faktur_pajak.write(cr,uid,no_fp,{'model_id':model[0],
                                            'amount_total':vals.amount_total,
                                            'untaxed_amount':vals.amount_untaxed,
                                            'tax_amount':vals.amount_tax,                                                    
                                            'state':'close',
                                            'transaction_id':vals.id,
                                            'date':vals.date_order,
                                            'partner_id':vals.partner_id.id,
                                            'in_out':'out',
                                                })      
        elif object == 'dym.asset.disposal' :
            faktur_pajak.write(cr,uid,no_fp,{'model_id':model[0],
                                            'amount_total':vals.amount_total,
                                            'untaxed_amount':vals.amount_net_price,
                                            'tax_amount':vals.amount_tax,                                                    
                                            'state':'close',
                                            'transaction_id':vals.id,
                                            'date':vals.date,
                                            'partner_id':vals.partner_id.id,
                                            'in_out':'out',
                                                })    
        elif object == 'account.invoice' :
            faktur_pajak.write(cr,uid,no_fp,{'model_id':model[0],
                                            'amount_total':vals.amount_total,
                                            'untaxed_amount':vals.amount_untaxed,
                                            'tax_amount':vals.amount_tax,
                                            'state':'close',
                                            'transaction_id':vals.id,
                                            'date':vals.date_invoice,
                                            'partner_id':vals.partner_id.id,
                                            'in_out':'out',
                                                    })       
        return no_fp
        

    def create_pajak_gunggung(self,cr,uid,ids,object,context=None):
        vals = self.pool.get(object).browse(cr,uid,ids)
        faktur_pajak = self.pool.get('dym.faktur.pajak.out')
        if object == 'dealer.sale.order' :
            thn_penggunaan = int(vals.date_order[:4])
            tgl_terbit = vals.date_order
        elif object == 'dym.work.order' :
            thn_penggunaan = int(vals.date[:4])
            tgl_terbit = vals.date
        elif object == 'account.voucher' :
            thn_penggunaan = int(vals.date[:4])
            tgl_terbit = vals.date
        elif object == 'sale.order' :
            thn_penggunaan = int(vals.date_order[:4])
            tgl_terbit = vals.date_order            
        elif object == 'dym.asset.disposal' :
            thn_penggunaan = int(vals.date[:4])
            tgl_terbit = vals.date         
        elif object == 'account.invoice' :
            thn_penggunaan = int(vals.date_invoice[:4])
            tgl_terbit = vals.date_invoice             

        model = self.pool.get('ir.model').search(cr,uid,[
                                                         ('model','=',vals.__class__.__name__)
                                                         ])
        no_fp = False
        if object == 'dealer.sale.order' :
            no_fp = faktur_pajak.create(cr,uid,{'model_id':model[0],
                                                'amount_total':vals.amount_total,
                                                'untaxed_amount':vals.amount_untaxed,
                                                'tax_amount':vals.amount_tax,                                                    
                                                'state':'close',
                                                'transaction_id':vals.id,
                                                'date':vals.date_order,
                                                'partner_id':vals.partner_id.id,
                                                'company_id':vals.branch_id.company_id.id,
                                                'in_out':'out',
                                                'pajak_gunggung':True,
                                                })   
        elif object == 'dym.work.order' :
            no_fp = faktur_pajak.create(cr,uid,{'model_id':model[0],
                                                'amount_total':vals.amount_total,
                                                'untaxed_amount':vals.amount_untaxed,
                                                'tax_amount':vals.amount_tax,                                                    
                                                'state':'close',
                                                'transaction_id':vals.id,
                                                'date':vals.date,
                                                'partner_id':vals.customer_id.id,
                                                'company_id':vals.branch_id.company_id.id,
                                                'in_out':'out',
                                                'pajak_gunggung':True,
                                                })    
        
        elif object == 'account.voucher' :
            total = 0.0
            for x in vals.line_cr_ids :
                total += x.amount
            tax = vals.amount - total
            no_fp = faktur_pajak.create(cr,uid,{'model_id':model[0],
                                                'amount_total':vals.amount,
                                                'untaxed_amount':total ,
                                                'tax_amount':tax,
                                                'state':'close',
                                                'transaction_id':vals.id,
                                                'date':vals.date,
                                                'partner_id':vals.partner_id.id,
                                                'company_id':vals.branch_id.company_id.id,
                                                'in_out':'out',
                                                'pajak_gunggung':True,
                                                }) 
        elif object == 'sale.order' :
            no_fp = faktur_pajak.create(cr,uid,{'model_id':model[0],
                                                'amount_total':vals.amount_total,
                                                'untaxed_amount':vals.amount_untaxed,
                                                'tax_amount':vals.amount_tax,                                                    
                                                'state':'close',
                                                'transaction_id':vals.id,
                                                'date':vals.date_order,
                                                'partner_id':vals.partner_id.id,
                                                'company_id':vals.branch_id.company_id.id,
                                                'in_out':'out',
                                                'pajak_gunggung':True,
                                                })      
        elif object == 'dym.asset.disposal' :
            no_fp = faktur_pajak.create(cr,uid,{'model_id':model[0],
                                                'amount_total':vals.amount_total,
                                                'untaxed_amount':vals.amount_net_price,
                                                'tax_amount':vals.amount_tax,                                                    
                                                'state':'close',
                                                'transaction_id':vals.id,
                                                'date':vals.date,
                                                'partner_id':vals.partner_id.id,
                                                'company_id':vals.branch_id.company_id.id,
                                                'in_out':'out',
                                                'pajak_gunggung':True,
                                                })    
        elif object == 'account.invoice' :
            no_fp = faktur_pajak.create(cr,uid,{'model_id':model[0],
                                                'amount_total':vals.amount_total,
                                                'untaxed_amount':vals.amount_untaxed,
                                                'tax_amount':vals.amount_tax,
                                                'state':'close',
                                                'transaction_id':vals.id,
                                                'date':vals.date_invoice,
                                                'partner_id':vals.partner_id.id,
                                                'company_id':vals.branch_id.company_id.id,
                                                'in_out':'out',
                                                'pajak_gunggung':True,
                                                })       
        return no_fp

    @api.cr_uid_ids_context
    def signature_change(self,cr,uid,ids,signature,context=None):
        vals = self.browse(cr,uid,ids)
        # company  = self.pool.get('res.company')._company_default_get(cr,uid,ids,'dym.faktur.pajak.out') or 1
        # vals.write({'company_id':company})
        
    def print_faktur_pajak(self,cr,uid,ids,context=None):  
        res = self.browse(cr,uid,ids)

        if not res.partner_id.pkp :
                raise osv.except_osv(('Perhatian !'), ("Customer non PKP !"))
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dym.faktur.pajak.out.wizard'), ("model", "=", 'dym.faktur.pajak.out')])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
            
        return {
            'name': 'Faktur Pajak',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dym.faktur.pajak.out',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'target': 'new',
            'nodestroy': True,
            'res_id': res.id,
            'context': context
            }    


class res_company(models.Model):
    _inherit = 'res.company'

    is_pedagang_eceran = fields.Boolean(string='Pedagang Eceran')
    vat = fields.Char(related='partner_id.npwp', string='Tax ID/NPWP', readonly=True)
    
class dym_branch(models.Model):
    _inherit = 'dym.branch'

    is_pedagang_eceran = fields.Boolean(string='Pedagang Eceran',
                               related='company_id.is_pedagang_eceran')
    