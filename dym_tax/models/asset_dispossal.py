import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

import json

class AssetDisposal(models.Model):
    _inherit = "dym.asset.disposal"

    jenis_npwp = fields.Selection([('terpusat','Terpusat'),('percabang','Per Cabang')], string='Jenis NPWP', related="branch_id.company_id.jenis_npwp")
    npwp_branch_id = fields.Many2one('dym.branch', string='Asset Location', help="The branch where asset is located")

    def dispose_change(self,cr,uid,ids,branch_id,birojasa_id,context=None):
        res = super(AssetDisposal, self).dispose_change(cr,uid,ids,branch_id,birojasa_id,context=context)
        domain = {}
        value = {}
        if branch_id:
            branch = self.pool.get('dym.branch').browse(cr, uid, [branch_id], context=context)
            branches = self.pool.get('dym.branch').search(cr, uid, [('company_id','=',branch.company_id.id)], context=context)
            domain['loc_branch_id'] = [('id','in',branches)]

            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, 'Umum', False, 4, 'General')
            value['analytic_1'] = analytic_1_general
            value['analytic_2'] = analytic_2_general
            value['analytic_3'] = analytic_3_general
            value['analytic_4'] = analytic_4_general

        return {'domain':domain,'value':value}

    def action_invoice_create(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        asset_obj = self.pool.get('account.asset.asset')
        obj_inv = self.pool.get('account.invoice')
        invoice_line = []
        move_line_obj = self.pool.get('account.move.line')
        config = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',val.branch_id.id)])
        config_browse = self.pool.get('dym.branch.config').browse(cr,uid,config)
        if config :
            disposal_debit_account_id = config_browse.asset_disposal_journal_id.default_debit_account_id.id 
            disposal_credit_account_id = config_browse.asset_disposal_journal_id.default_credit_account_id.id  
            journal_asset_disposal = config_browse.asset_disposal_journal_id.id
            if not journal_asset_disposal or not disposal_debit_account_id or not disposal_credit_account_id:
                raise osv.except_osv(_('Attention!'),
                    _('Jurnal Asset Disposal belum diisi, harap isi terlebih dahulu didalam branch config'))                                
        elif not config :
            raise osv.except_osv(_('Error!'),
                _('Please define Journal in Setup Division for this branch: "%s".') % \
                (val.branch_id.name))
        if val.amount_total < 1: 
            raise osv.except_osv(_('Attention!'),
                _('Mohon periksa kembali detail asset disposal.')) 
        for x in val.asset_disposal_line:
            if not x.asset_id.analytic_4.id:
                raise osv.except_osv(_('Attention!'),
                    _('data analytic untuk asset %s belum lengkap') % \
                    (x.asset_id.name))
            if not x.asset_id.account_depreciation_id or not x.asset_id.account_asset_id:
                raise osv.except_osv(_('Attention!'),
                    _('Data Account di kategori asset %s belum lengkap')%(x.asset_id.category_id.name))   
            invoice_line.append([0,False,{
                'account_id':x.asset_id.account_depreciation_id.id,
                'partner_id':val.partner_id.id,
                'name': 'Accumulated Depreciation ' + x.asset_id.name,
                'quantity': 1,
                'origin': val.name,
                'price_unit':(x.depreciated*-1) or 0.00,
                'analytic_2': x.asset_id.analytic_2.id,
                'analytic_3': x.asset_id.analytic_3.id,
                'account_analytic_id':x.asset_id.analytic_4.id,
            }])
            invoice_line.append([0,False,{
                'account_id':x.asset_id.account_asset_id.id,
                'partner_id':val.partner_id.id,
                'name': 'Cost ' + x.asset_id.name,
                'quantity': 1,
                'origin': val.name,
                'price_unit':x.purchase_value  or 0.00,
                'analytic_2': x.asset_id.analytic_2.id,
                'analytic_3': x.asset_id.analytic_3.id,
                'account_analytic_id':x.asset_id.analytic_4.id,
            }])
            invoice_line.append([0,False,{
                'account_id':disposal_credit_account_id,
                'partner_id':val.partner_id.id,
                'name': 'Laba / Rugi ' + x.asset_id.name,
                'quantity': 1,
                'origin': val.name,
                'price_unit':x.gain_loss  or 0.00,
                'analytic_2': x.asset_id.analytic_2.id,
                'analytic_3': x.asset_id.analytic_3.id,
                'account_analytic_id':x.asset_id.analytic_4.id,
            }])
        tax_line =[]
        for tax_id in val.taxes_ids:
            amount_tax = float(0)
            for c in self.pool.get('account.tax').compute_all(cr,uid, tax_id, (val.amount_untaxed-val.discount),1)['taxes']:
                amount_tax +=c.get('amount',0.0)
            tax_line.append([0,False,{
                'name':tax_id.name,
                'account_id':tax_id.account_collected_id.id,
                'base':(val.amount_untaxed-val.discount),               
                'amount':amount_tax,               
            }])
        if val.discount != 0:
            invoice_line.append([0,False,{
                'account_id':disposal_credit_account_id,
                'partner_id':val.partner_id.id,
                'name': 'Diskon ' + val.name,
                'quantity': 1,
                'origin': val.name,
                'price_unit': (val.discount*-1) or 0.00,
                'analytic_2': x.asset_id.analytic_2.id,
                'analytic_3': x.asset_id.analytic_3.id,
                'account_analytic_id':x.asset_id.analytic_4.id,
            }])
        inv_dispose_asset_id = obj_inv.create(cr,uid, {
            'name':val.name,
            'origin': val.name,
            'branch_id':val.branch_id.id,
            'division':val.division,
            'partner_id':val.partner_id.id,
            'date_invoice':val.date,
            'reference_type':'none',
            'account_id':disposal_debit_account_id,
            'comment':val.memo,
            'type': 'out_invoice',
            'journal_id' : journal_asset_disposal,
            'discount_lain' : val.discount,                        
            'tipe': 'customer',                
            'payment_term': val.payment_term.id,
            'tax_line':tax_line,
            'invoice_line':invoice_line,
            'analytic_1': val.analytic_1.id,
            'analytic_2': val.analytic_2.id,
            'analytic_3': val.analytic_3.id,
            'analytic_4': val.analytic_4.id,
        })   
        obj_line = self.pool.get('account.invoice.line') 
        for dispose_line in val.asset_disposal_line :
            asset_obj.write(cr,uid,[dispose_line.asset_id.id],{'inv_dispose_asset':inv_dispose_asset_id})
            update_vals = {'inv_dispose_asset':inv_dispose_asset_id,}
        obj_inv.signal_workflow(cr, uid, [inv_dispose_asset_id], 'invoice_open' )
        if val.amount_tax and not val.pajak_gabungan and not val.pajak_gunggung :
            ctx = context.copy()
            ctx['npwp_branch_id'] = val.npwp_branch_id.id
            self.pool.get('dym.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'dym.asset.disposal',context=ctx)   
        if val.amount_tax and val.pajak_gunggung == True :   
            self.pool.get('dym.faktur.pajak.out').create_pajak_gunggung(cr,uid,ids,'dym.asset.disposal',context=context)  
        return inv_dispose_asset_id 