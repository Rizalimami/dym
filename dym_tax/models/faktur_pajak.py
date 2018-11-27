import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class dym_faktur_pajak(models.Model):
    
    _inherit = "dym.faktur.pajak"
         
    jenis_npwp = fields.Selection([('terpusat','Terpusat'),('percabang','Per Cabang')], string='Jenis NPWP', related="company_id.jenis_npwp")
    

class dym_faktur_pajak_out(models.Model):
    
    _inherit = 'dym.faktur.pajak.out'

    branch_id = fields.Many2one('dym.branch', string='Branch', related="faktur_pajak_id.branch_id", store=True)    

    def get_no_faktur_pajak(self,cr,uid,ids,object,context=None):
        vals = self.pool.get(object).browse(cr,uid,ids)
        branch_id = context.get('npwp_branch_id',vals.branch_id.id)
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
            branch_id = vals.inter_branch_id.id
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
            domain += [('branch_id','=',branch_id)]
        domain += [
            ('state','=','open'),
            ('thn_penggunaan','=',thn_penggunaan),
            ('tgl_terbit','<=',tgl_terbit),
            ('company_id','=',vals.branch_id.company_id.id)
        ]
        no_fp = faktur_pajak.search(cr, uid, domain, limit=1, order='id')        
        if not no_fp :
            raise osv.except_osv(('Perhatian !'), ("xNomor faktur pajak tidak ditemukan, silahkan Generate terlebih dahulu !"))
        
        vals.write({'faktur_pajak_id':no_fp[0]})
        model = self.pool.get('ir.model').search(cr,uid,[
            ('model','=',vals.__class__.__name__)
        ])
        if object == 'dealer.sale.order':
            faktur_pajak.write(cr,uid,no_fp,{
                'model_id':model[0],
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
            faktur_pajak.write(cr,uid,no_fp,{
                'model_id':model[0],
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
            faktur_pajak.write(cr,uid,no_fp,{
                'model_id':model[0],
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
            faktur_pajak.write(cr,uid,no_fp,{
                'model_id':model[0],
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
            faktur_pajak.write(cr,uid,no_fp,{
                'model_id':model[0],
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
            faktur_pajak.write(cr,uid,no_fp,{
                'model_id':model[0],
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
