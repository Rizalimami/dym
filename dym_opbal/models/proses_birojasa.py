# -*- coding: utf-8 -*-
import time
from datetime import datetime
from openerp import workflow
from openerp.osv import fields, osv, orm
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
from lxml import etree
from openerp.osv.orm import setup_modifiers

class dym_proses_birojasa(osv.osv):
    _inherit = "dym.proses.birojasa"

    _columns = {
	    'is_opbal': fields.boolean(string='Opbal'),
	}

    def action_invoice_create(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        engine_obj = self.pool.get('stock.production.lot')
        obj_inv = self.pool.get('account.invoice')
        total_jasa = 0.00
        total_notice = 0.00
        estimasi = 0.00
        invoice_id = {}
        move_line_obj = self.pool.get('account.move.line')
        #ACCOUNT 
        config = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',val.branch_id.id),])
        invoice_bbn = {}

        if config :
            config_browse = self.pool.get('dym.branch.config').browse(cr,uid,config)
            progressive_debit_account = config_browse.tagihan_birojasa_progressive_journal_id.default_debit_account_id.id  
            progressive_credit_account = config_browse.tagihan_birojasa_progressive_account_id.id
            bbn_debit_account_id = config_browse.tagihan_birojasa_bbn_account_id.id 
            bbn_credit_account_id = config_browse.tagihan_birojasa_bbn_journal_id.default_credit_account_id.id  
            bbn_jual_id = config_browse.dealer_so_account_bbn_jual_id.id  
            journal_birojasa = config_browse.tagihan_birojasa_bbn_journal_id.id
            journal_progressive = config_browse.tagihan_birojasa_progressive_journal_id.id,
            if not journal_birojasa or not journal_progressive or not progressive_credit_account or not progressive_debit_account or not bbn_debit_account_id or not bbn_credit_account_id  or not bbn_jual_id:
                raise osv.except_osv(_('Attention!'),
                    _('Jurnal Pajak Progressive atau Jurnal BBN Beli belum lengkap, harap isi terlebih dahulu didalam branch config'))   
                             
        elif not config :
            raise osv.except_osv(_('Error!'),
                _('Please define Journal in Setup Division for this branch: "%s".') % \
                (val.branch_id.name))
                              
        move_list = []
        if val.amount_total < 1: 
            raise osv.except_osv(_('Attention!'),
                _('Mohon periksa kembali detail tagihan birojasa.')) 
        analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, 'Unit', False, 4, 'Sales')
        analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, 'Unit', False, 4, 'General')
        birojasa_id = obj_inv.create(cr,uid, {
            'name':val.name,
            'origin': val.name,
            'branch_id':val.branch_id.id,
            'division':val.division,
            'partner_id':val.partner_id.id,
            'date_invoice':val.tanggal,
            'reference_type':'none',
            'account_id':bbn_credit_account_id,
            'comment':val.note,
            'type': 'in_invoice',
            'supplier_invoice_number' : val.no_dok,
            'journal_id' : journal_birojasa,
            'document_date' : val.tgl_dok,
            'analytic_1': analytic_1_general,
            'analytic_2': analytic_2_general,
            'analytic_3': analytic_3_general,
            'analytic_4': analytic_4_general,
        })   
        obj_line = self.pool.get('account.invoice.line') 
        invoice_bbn_ids = []
        total_titipan = 0
        move_bbn_partner = {}
        move_bbn_ids = []
        move_ids = []
        for x in val.proses_birojasa_line :
            pajak_progressive_id = False
            if x.pajak_progressive > 0.00 :
                customer_name = str(x.name.customer_id.name)       
                engine_no = str(x.name.name)                     
                string = "Pajak Progresif a/n \'%s\', No Engine \'%s\' !" % (customer_name,engine_no)
                inv_pajak_progressive_id = obj_inv.create(cr,uid, {
                    'name':string,
                    'qq_id':x.name.customer_stnk.id,
                    'origin': val.name,
                    'branch_id':val.branch_id.id,
                    'division':val.division,
                    'partner_id':x.name.customer_id.id,
                    'date_invoice':val.tanggal,
                    'reference_type':'none',
                    'account_id':progressive_debit_account,
                    'type': 'out_invoice',
                    'supplier_invoice_number' : val.no_dok,
                    'journal_id':journal_progressive,
                    'document_date' : val.tgl_dok,
                    'analytic_1': analytic_1_general,
                    'analytic_2': analytic_2_general,
                    'analytic_3': analytic_3_general,
                    'analytic_4': analytic_4_general,
                    'invoice_line':[[0,False,{
                        'account_id':progressive_credit_account,
                        'partner_id':x.name.customer_id.id,
                        'name': string,
                        'quantity': 1,
                        'origin': val.name,
                        'price_unit':x.pajak_progressive  or 0.00,
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id': analytic_4,
                    }]]
                })       
                obj_inv.signal_workflow(cr, uid, [inv_pajak_progressive_id], 'invoice_open' ) 
                pajak_progressive_id = inv_pajak_progressive_id
                
            engine_obj.write(cr,uid,[x.name.id],{'inv_pajak_progressive_id':pajak_progressive_id,'inv_proses_birojasa':birojasa_id})

            inv_line_id = False
            if x.name.dealer_sale_order_id.finco_id and x.name.dealer_sale_order_id.is_credit == True:
                inv_line_id = obj_line.search(cr,uid,[
                    ('invoice_id.origin', 'ilike', x.name.dealer_sale_order_id.name),
                    ('invoice_id.partner_id', 'in', [x.name.dealer_sale_order_id.partner_id.id,x.name.dealer_sale_order_id.finco_id.id]),
                    ('invoice_id.tipe','=','finco'),
                    '|',('account_id', '=', bbn_jual_id),('invoice_id.account_bbn', '=', bbn_jual_id),
                    ], limit=1)
            else:
                inv_line_id = obj_line.search(cr,uid,[
                    ('invoice_id.origin', 'ilike', x.name.dealer_sale_order_id.name),
                    ('invoice_id.partner_id', '=', x.name.dealer_sale_order_id.partner_id.id),
                    ('invoice_id.tipe','=','customer'),
                    '|',('account_id', '=', bbn_jual_id),('invoice_id.account_bbn', '=', bbn_jual_id),
                    ], limit=1)
            invoice_line = obj_line.browse(cr, uid, inv_line_id)
            if invoice_line:
                obj_line.create(cr,uid, {
                    'invoice_id':birojasa_id,
                    'account_id':bbn_jual_id,
                    'partner_id':x.name.customer_id.id,
                    'name': 'Total Titipan ' + x.name.customer_id.name + ' ' + x.name.name,
                    'quantity': 1,
                    'origin': val.name,
                    'price_unit': x.titipan,
                    'analytic_1': analytic_1_general,
                    'analytic_2': analytic_2_general,
                    'analytic_3': analytic_3_general,
                    'account_analytic_id': analytic_4_general,
                    'tagihan_birojasa': x.total_tagihan,
                    'force_partner_id': x.name.customer_id.id,
                })
                if invoice_line.invoice_id.move_id.id not in move_ids:
                    move_bbn_id = self.pool.get('account.move.line').search(cr, uid, [('account_id','=',bbn_jual_id),('move_id','=',invoice_line.invoice_id.move_id.id),('credit','>',0)])
                    self.pool.get('account.move.line').write(cr, uid, move_bbn_id, {'partner_id':x.name.customer_id.id})
                    move_ids.append(invoice_line.invoice_id.move_id.id)
                    if x.name.customer_id not in move_bbn_partner:
                        move_bbn_partner[x.name.customer_id] = []
                    move_bbn_partner[x.name.customer_id] += move_bbn_id
                bbn_res = {}
                bbn_res['lot_id'] = x.name
                bbn_res['partner_id'] = x.name.customer_id
                bbn_res['amount'] = x.titipan
                invoice_bbn_ids.append(bbn_res)
                total_titipan += x.titipan
                total_jasa += x.total_jasa

            if x.is_opbal:
                obj_line.create(cr,uid, {
                    'invoice_id':birojasa_id,
                    'account_id':bbn_jual_id,
                    'partner_id':x.name.customer_id.id,
                    'name': 'Total Titipan ' + x.name.customer_id.name + ' ' + x.name.name,
                    'quantity': 1,
                    'origin': val.name,
                    'price_unit': x.titipan,
                    'analytic_1': analytic_1_general,
                    'analytic_2': analytic_2_general,
                    'analytic_3': analytic_3_general,
                    'account_analytic_id': analytic_4_general,
                    'tagihan_birojasa': x.total_tagihan,
                    'force_partner_id': x.name.customer_id.id,
                })
                total_titipan += x.titipan
                total_jasa += x.total_jasa

        obj_line.create(cr,uid, {
            'invoice_id':birojasa_id,
            'account_id':bbn_debit_account_id,
            'partner_id':val.partner_id.id,
            'name': 'Total Pendapatan STNK',
            'quantity': 1,
            'origin': val.name,
            'price_unit': (val.amount_total - total_titipan - total_jasa) or 0.00,
            'analytic_1': analytic_1,
            'analytic_2': analytic_2,
            'analytic_3': analytic_3,
            'account_analytic_id': analytic_4,
            }) 

        if total_jasa:
            jasa_stnk_account_id = config_browse.biaya_jasa_pengurusan_stnk_account_id.id
            if not jasa_stnk_account_id:
                raise osv.except_osv(_('Attention!'),
                    _('Account biaya jasa pengurusan STNK belum di set, harap isi terlebih dahulu didalam branch config'))
            obj_line.create(cr,uid, {
                'invoice_id':birojasa_id,
                'account_id':jasa_stnk_account_id,
                'partner_id':val.partner_id.id,
                'name': 'Biaya Jasa Perantara Pengurusan STNK',
                'quantity': 1,
                'origin': val.name,
                'price_unit': (total_jasa) or 0.00,
                'analytic_1': analytic_1,
                'analytic_2': analytic_2,
                'analytic_3': analytic_3,
                'account_analytic_id': analytic_4,
                })
           
        obj_inv.signal_workflow(cr, uid, [birojasa_id], 'invoice_open' ) 
        birojasa_inv = obj_inv.browse(cr, uid, [birojasa_id])
        move_line_ids = []
        for bbn in invoice_bbn_ids:
            move_line_ids = move_line_obj.search(cr,uid,[
                ('name','=','Total Titipan ' + bbn['partner_id'].name + ' ' + bbn['lot_id'].name),
                ('invoice','=',birojasa_id),
                ('account_id','=',bbn_jual_id),
                ('move_id','=',birojasa_inv.move_id.id),
                ('partner_id','=',bbn['partner_id'].id),
                ('debit','=',bbn['amount']),
                ], limit=1)
            move_line_obj.write(cr, uid, move_line_ids, {'partner_id':bbn['partner_id'].id})
            if move_line_ids and bbn['partner_id'] in move_bbn_partner:
                reconcile_id = move_line_obj.reconcile_partial(cr, uid, move_line_ids + move_bbn_partner[bbn['partner_id']], 'auto')

        return birojasa_id 