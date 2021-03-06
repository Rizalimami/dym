# -*- coding: utf-8 -*-

import time
import pytz 
import openerp.addons.decimal_precision as dp

from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import workflow, api
from openerp.addons.dealer_sale_order.report import fungsi_terbilang
from openerp.addons.dym_base import DIVISION_SELECTION

class dealer_sale_order(osv.osv):
    _name = 'dealer.sale.order'
    _description = "Dealer Sales Memo"
    _order = 'date_order desc, id desc'

    def get_no_invoice(self,cr,uid,ids,dso,context=None):
        obj_inv_line = self.pool.get('account.invoice.line')
        invoice_line_ids = obj_inv_line.search(cr, uid, [('invoice_id.origin','ilike',dso.name),('invoice_id.type','=','out_invoice'),('product_id','=',dso.dealer_sale_order_line[0].product_id.id)])
        for inv_line in obj_inv_line.browse(cr, uid, invoice_line_ids):
            return inv_line.invoice_id.number
        return '-'

    def get_invoice_qq(self,cr,uid,ids,dso,context=None):
        obj_inv_line = self.pool.get('account.invoice.line')
        dso_line = self.pool.get('dealer.sale.order.line')
        order_line = dso_line.search(cr, uid, [('dealer_sale_order_line_id','=', dso.id)])
        invoice_line_ids = obj_inv_line.search(cr, uid, [('invoice_id.origin','ilike',dso.name),('invoice_id.type','=','out_invoice'),('product_id','=',dso.dealer_sale_order_line[0].product_id.id)])
        # counter = 1
        line = dso_line.browse(cr, uid, dso.id)
        # print len(order_line),'line--------------------\n'
        if (len(order_line) > 1 ):
            return 'Silakan Buka Lampiran !'
        else :
            inv_line = obj_inv_line.browse(cr, uid, invoice_line_ids)
            return inv_line.invoice_id.qq2_id.display_name
        return '-'

    def get_adh(self,cr,uid,branch_id):
        obj_employee = self.pool.get('hr.employee')
        adh_ids = obj_employee.search(cr, uid, [('branch_id','=',branch_id),('job_id','=',125)])
        adh = obj_employee.browse(cr, uid, adh_ids)
        return adh.name

    def get_tanggal_invoice(self,cr,uid,ids,dso,context=None):
        obj_inv_line = self.pool.get('account.invoice.line')
        invoice_line_ids = obj_inv_line.search(cr, uid, [('invoice_id.origin','ilike',dso.name),('invoice_id.type','=','out_invoice'),('product_id','=',dso.dealer_sale_order_line[0].product_id.id)])
        for inv_line in obj_inv_line.browse(cr, uid, invoice_line_ids):
            return inv_line.invoice_id.date_invoice
        return '-'

    def get_terbilang(self,cr, uid, ids, amount, print_subsidi_tax=False):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id', print_subsidi_tax=print_subsidi_tax)
        return hasil
     
    def _report_xls_dealer_sale_order_fields(self, cr, uid, context=None):
        return [
            'branch_id','order_name', 'order_date','default_code','konsumen','sales','finco','dp_net','sales_source','cicilan','location_id','product_id',
            'warna','mesin','rangka','tenor','is_bbn','nama_stnk','uang_muka','pot_pelanggan','harga','total_discount'
            ,'harga_bbn','state'
        ]
    
    def _report_xls_stock_sparepart_fields(self, cr, uid, context=None):
        return [
            'cabang', 'kode_product','location_id','tanggal','jumlah'
        ]

    def _report_xls_arap_details_fields(self, cr, uid, context=None):
        return [
            'document', 'date', 'date_maturity', 'account', 'description',
            'rec_or_rec_part', 'debit', 'credit', 'balance',
        ]

    def _report_xls_arap_overview_template(self, cr, uid, context=None):
        return {}

    def _report_xls_arap_details_template(self, cr, uid, context=None):
        return {}
        
    def _amount_line_tax(self,cr , uid, line, context=None):
        val=val1=disc_total=subtotal=0.0
        for detail in line:
            for disc in detail.discount_line:
                if disc.include_invoice == False:
                    continue
                if disc.tipe_diskon == 'percentage':
                    disc_total += (detail.price_unit * disc.discount_pelanggan / 100)
                else:
                    disc_total += disc.discount_pelanggan 
            subtotal+=detail.price_unit-(disc_total+detail.discount_po)
                
            val1 += line.price_unit-(disc_total+line.discount_po)
        for c in self.pool.get('account.tax').compute_all(cr,uid, line.tax_id, subtotal,line.product_qty, line.product_id)['taxes']:
            val +=c.get('amount',0.0)
        return val
    
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_bbn': 0.0,
                'amount_total': 0.0,
                'amount_hpp':0.0,
                'amount_ps':0.0,
                'amount_pot':0.0,
                'amount_total_disc':0.0,
                'amount_piutang':0.0,
                'amount_gp_unit':0.0,
                'amount_gp_bbn':0.0,
                'amount_hc':0.0,
                'amount_beban_dealer':0.0,
                'dp_po':0.0,
                'diskon_dp':0.0,
                'diskon_dp_2':0.0,
                'tanda_jadi':0.0,
                'tanda_jadi2':0.0,
                'customer_dp':0.0,
            }
            val = val1 = ps_total = subtotal = valbbn = val_hc = val_um = val_harga_jual = disc_total = val_pot = val_beli_unit = val_barang_subsidi = val_ps_dealer = val_bb_dealer = valbbn_beli = tanda_jadi = tanda_jadi2 = diskon_dp = diskon_dp_2 = 0.0
           
            for line in order.dealer_sale_order_line:
                disc_total = 0
                for disc in line.discount_line:
                    if disc.include_invoice == False:
                        continue
                    if disc.tipe_diskon == 'percentage':
                        disc_total += (line.price_unit * disc.discount_pelanggan / 100)
                    else:
                        disc_total += disc.discount_pelanggan 
                        val_ps_dealer += disc.ps_dealer
                for bb in line.barang_bonus_line:
                    val_barang_subsidi += bb.price_barang
                    val_bb_dealer+= bb.bb_dealer
                
                taxes = tax_obj.compute_all(cr, uid, line.tax_id, (line.price_unit-(disc_total+line.discount_po)), line.product_qty, line.product_id)
                val1 += taxes['total']
                val += self._amount_line_tax(cr, uid, line, context=context)
                ps_total+=disc_total
                valbbn += line.price_bbn
                val_um += line.uang_muka
                val_harga_jual += tax_obj.compute_all(cr, uid, line.tax_id, line.price_unit, line.product_qty, line.product_id)['total']
                val_pot += line.discount_po
                val_beli_unit+=line.price_unit_beli
                valbbn_beli = line.price_bbn_beli
                val_hc += line.amount_hutang_komisi
                diskon_dp += line.diskon_dp
                diskon_dp_2 += line.diskon_dp_2
                tanda_jadi += line.tanda_jadi
                tanda_jadi2 += line.tanda_jadi2
            
            res[order.id]['amount_tax'] = val
            res[order.id]['amount_harga_jual'] = val_harga_jual
            res[order.id]['amount_ps'] = ps_total
            res[order.id]['amount_pot'] = val_pot
            res[order.id]['amount_untaxed'] =val1
            res[order.id]['amount_bbn'] = valbbn
            res[order.id]['amount_hc'] = val_hc
            res[order.id]['dp_po'] = val_um
            res[order.id]['diskon_dp'] = diskon_dp
            res[order.id]['diskon_dp_2'] = diskon_dp_2
            res[order.id]['tanda_jadi'] = tanda_jadi
            res[order.id]['tanda_jadi2'] = tanda_jadi2
            # res[order.id]['customer_dp'] = val_um - diskon_dp - diskon_dp_2 - tanda_jadi2
            res[order.id]['customer_dp'] = val_um - diskon_dp - diskon_dp_2
            res[order.id]['amount_gp_bbn'] = valbbn - valbbn_beli
            res[order.id]['amount_beban_dealer'] = val_ps_dealer + val_bb_dealer + val_pot
            res[order.id]['amount_total_disc'] = res[order.id]['amount_ps'] + res[order.id]['amount_pot']
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']+res[order.id]['amount_bbn']
            res[order.id]['amount_gp_unit'] = res[order.id]['amount_harga_jual'] - val_beli_unit - res[order.id]['amount_beban_dealer'] - res[order.id]['amount_hc']
            res[order.id]['amount_piutang'] = res[order.id]['amount_total'] - res[order.id]['customer_dp']
        return res
    
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('dealer.sale.order.line').browse(cr, uid, ids, context=context):
            result[line.dealer_sale_order_line_id.id] = True
        return result.keys()
    
    def _get_picking_ids(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for po_id in ids:
            res[po_id] = []
        query = """
        SELECT picking_id, po.id 
        FROM stock_picking p,
         stock_move m, 
         dealer_sale_order_line pol, 
         dealer_sale_order po
            WHERE  po.id in %s
            and po.id = pol.dealer_sale_order_line_id
            and p.origin=po.name
            and m.picking_id = p.id
            GROUP BY picking_id, po.id
        """
        cr.execute(query, (tuple(ids), ))
        picks = cr.fetchall()
        for pick_id, po_id in picks:
            res[po_id].append(pick_id)
       
        return res
    
    def test_moves_done(self, cr, uid, ids, context=None):
        for purchase in self.browse(cr, uid, ids, context=context):
            if not purchase.picking_ids :
                return False
            for picking in purchase.picking_ids:
                if picking.state != 'done' and picking.state != 'cancel':
                    return False
        return True

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        

    def _check_repeat(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            repeat_order = 'Tidak'
            if self.search(cr, uid, [('state','=','done'),('partner_id','=',order.partner_id.id),('id','<',order.id),('date_order','<=',order.date_order)]):
                repeat_order = 'Ya'
            res[order.id] = repeat_order
        return res

    def _get_user_id(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            emp_id = order.employee_id.user_id.id
            emp_src = self.pool.get('res.users').search(cr, uid, [('employee_id','=',order.employee_id.id)], limit=1)
            if emp_src:
                emp_id = emp_src[0]
            res[order.id] = emp_id
        return res

    def _get_payable_receivable(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = order.partner_id.debit
        return res

    _columns = {
        'origin': fields.char('Source Document', help="Reference of the document that generated this sales order request."),
        'payable_receivable': fields.function(_get_payable_receivable, digits_compute=dp.get_precision('Account'), string='Payable Balance',
            store={
                'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['partner_id'], 10),
            }, help="Payable Balance", track_visibility='always'),
        'repeat_order': fields.function(_check_repeat, type="char", string='Repeat Order'),
        'name' : fields.char('Sales Memo'),
        'untuk_pembayaran':fields.char('Untuk Pembayaran'),
        'untuk_pembayaran_2':fields.char('Untuk Pembayaran'),
        'amount_cod_print':fields.float('Total'),
        'untuk_pembayaran_3':fields.char('Untuk Pembayaran'),
        'untuk_pembayaran_4':fields.char('Untuk Pembayaran'),
        'untuk_pembayaran_5':fields.char('Untuk Pembayaran'),
        'branch_id': fields.many2one('dym.branch','Branch',required=True),
        'division': fields.selection([('Unit','Showroom')],required=True,string='Division'),
        'date_order': fields.date('Memo Date',required=True),
        'payment_term': fields.many2one('account.payment.term','Payment Term'),
        'partner_id': fields.many2one('res.partner','Customer',domain=[('customer','=',True)],required=True),
        'partner_komisi_id': fields.many2one('res.partner','Mediator'),
        'finco_id': fields.many2one('res.partner','Finco',domain=[('finance_company','=',True)]),
        'finco_cabang': fields.many2one('dym.cabang.partner','Cabang Finco'),
        'user_id': fields.function(_get_user_id, string='Responsible', type="many2one", relation="res.users", store={
                'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['employee_id'], 10),
            }),
        'pricelist_id': fields.related('dealer_spk_id', 'pricelist_id', relation='product.pricelist', type='many2one', string='Pricelist', store=True, readonly=True),
        'employee_id': fields.related('dealer_spk_id', 'employee_id', relation='hr.employee', type='many2one', string='Sales Person', store=True, readonly=True),
        'section_id': fields.related('dealer_spk_id', 'section_id', relation='crm.case.section', type='many2one', string='Sales Team', store=True, readonly=True),
        'sales_source': fields.related('dealer_spk_id', 'sales_source', relation='sales.source', type='many2one', string='Sales Source', store=True, readonly=True),
        'dealer_sale_order_line': fields.one2many('dealer.sale.order.line','dealer_sale_order_line_id','Sales Memo Line',states={'draft': [('readonly', False)],'progress': [('readonly', True)],'invoiced': [('readonly', True)],'done': [('readonly', True)]}),
        'state': fields.selection([
            ('cancel', 'Cancelled'),
            ('draft', 'Draft Quotation'),
            ('waiting_for_approval','Waiting Approval'),
            ('approved','Approved'),                                
            ('progress', 'Sales Memo'),
            ('done', 'Done'),
        ], 'Status',),
        'date_confirm': fields.date('Confirmation Date', readonly=True, select=True, help="Date on which sales order is confirmed.", copy=False),
        'dp_po': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='JP PO',
            store={
                'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['dealer_sale_order_line'], 10),
                'dealer.sale.order.line': (_get_order, ['uang_muka'], 10)
            },
            multi='sums', help="JP PO", track_visibility='always'),
        'diskon_dp': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Diskon JP 1',
            store={
                'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['dealer_sale_order_line'], 10),
                'dealer.sale.order.line': (_get_order, ['diskon_dp'], 10)
            },
            multi='sums', help="Diskon JP 1", track_visibility='always'),
        'diskon_dp_2': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Diskon JP 2',
            store={
                'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['dealer_sale_order_line'], 10),
                'dealer.sale.order.line': (_get_order, ['diskon_dp_2'], 10)
            },
            multi='sums', help="Diskon JP 2", track_visibility='always'),
        'tanda_jadi': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tanda Jadi',
            store={
                'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['tanda_jadi','dealer_sale_order_line'], 10),
                'dealer.sale.order.line': (_get_order, ['tanda_jadi'], 10)
            },
            multi='sums', help="Tanda Jadi", track_visibility='always'),
        'tanda_jadi2': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tanda Jadi',
            store={
                'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['tanda_jadi2','dealer_sale_order_line'], 10),
                'dealer.sale.order.line': (_get_order, ['tanda_jadi2'], 10)
            },
            multi='sums', help="Tanda Jadi", track_visibility='always'),
        'customer_dp': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='JP Nett',
            store={
                'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['customer_dp','diskon_dp','diskon_dp_2','dealer_sale_order_line'], 10),
                'dealer.sale.order.line': (_get_order, ['uang_muka'], 10)
            },
            multi='sums', help="Customer JP", track_visibility='always'),
        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tax Base',
            store={
                'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['dealer_sale_order_line'], 10),
                'dealer.sale.order.line': (_get_order, ['price_unit', 'tax_id', 'product_qty'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'),
        
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['dealer_sale_order_line'], 10),
                'dealer.sale.order.line': (_get_order, ['price_unit', 'tax_id',  'product_qty'], 10),
            },
            multi='sums', help="The tax amount."),
        
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['dealer_sale_order_line'], 10),
                'dealer.sale.order.line': (_get_order, ['price_unit', 'tax_id', 'product_qty'], 10),
            },
            multi='sums', help="The total amount."),
        
        'amount_bbn': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Non Tax / BBN',
            store={
                'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['dealer_sale_order_line'], 10),
                'dealer.sale.order.line': (_get_order, ['price_bbn'], 10),
            },
            multi='sums', help="The total amount."),
        'amount_harga_jual': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Harga Jual',                   
            multi='sums', help="The total HPP."),
        'amount_pot': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Potongan',                   
            multi='sums', help="Total Potongan."),
        'amount_ps': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total PS',                   
            multi='sums', help="Total PS."),
        'amount_total_disc': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Disc',                   
            multi='sums', help="Total Disc."),
        'amount_gp_unit': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='GP Unit',                   
            multi='sums', help="Total GP Unit."),
        'amount_gp_bbn': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='GP BBN',                   
            multi='sums', help="Total GP BBN."),
        'amount_piutang': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Sisa Piutang',                   
            multi='sums', help="Total Piutang."),
        'amount_hc': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Hutang Komisi',                   
            multi='sums', help="Total Hutang Komisi."),
        'amount_beban_dealer': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Beban Dealer',                   
            multi='sums', help="Total Beban Dealer."),
        'qq': fields.char('qq'),
        'alamat_kirim': fields.text('Alamat Kirim'),
        'amount_tax_info':fields.related('amount_tax',string='Total Tax',readonly=True),
        'amount_bbn_info':fields.related('amount_bbn',string='Total BBN',readonly=True),
        'amount_dp_info':fields.related('customer_dp',string='Total JP',readonly=True),
        'picking_ids': fields.function(_get_picking_ids, method=True, type='one2many', relation='stock.picking', string='Picking List', help="This is the list of receipts that have been generated for this sale order."),
        'picking_dummy': fields.related('picking_ids',type='boolean'),
        'summary_diskon_ids': fields.one2many('dealer.sale.order.summary.diskon','dealer_sale_order_id'),
        'dealer_spk_id': fields.many2one('dealer.spk'),
        'partner_cabang': fields.many2one('dym.cabang.partner', string='Partner Cabang'),
        'register_spk_id': fields.many2one('dealer.register.spk.line', type='many2one', string='Register No'),
        'cddb_id': fields.many2many('dym.cddb','dso_cddb_rel','dso_id','cddb_id',string='CDDB',required=False),
        'is_cod':fields.boolean('Is COD'),
        'confirm_uid':fields.many2one('res.users',string="Approved by"),
        'confirm_date':fields.datetime('Approved on'),       
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),                   
        'payment_term_dummy': fields.related('payment_term',relation='account.payment.term',type='many2one',string='Payment Term',store=False),
        'pajak_gunggung':fields.boolean('Tanpa Faktur Pajak',copy=False),   
        'pajak_gabungan':fields.boolean('Faktur Pajak Gabungan',copy=False),   
        'pajak_generate':fields.boolean('Faktur Pajak Satuan',copy=False),   
        'faktur_pajak_id':fields.many2one('dym.faktur.pajak.out',string='No Faktur Pajak',copy=False)  ,
        'journal_id':fields.many2one('account.journal', 'Payment Method'),
        'is_credit':fields.boolean('Credit'),
        'is_pic': fields.related('dealer_spk_id', 'is_pic', type='boolean', string='Is PIC', store=True, readonly=True),
        'is_asset': fields.related('dealer_spk_id', 'is_asset', type='boolean', string='Is Asset', store=True, readonly=True),
        'po_id': fields.many2one('purchase.order', string='Intercompany PO#', help='Purchase Order number that issued by intercompany partner'),
        'is_pedagang_eceran': fields.related('branch_id', 'is_pedagang_eceran', relation='dym.branch', type='boolean',string='Pedagang Eceran',store=False),
        'print_subsidi_tax':fields.boolean('Print subsidi with tax'),
        'bill_date': fields.date('Bill Date'),
        'mt_khusus': fields.related('employee_id','mt_khusus',type='boolean',string="Is MT Khusus",store=True)
    }

    _defaults = {
        'state': 'draft',
        'division': 'Unit',
        'date_order': fields.date.context_today,
        'branch_id' : _get_default_branch,
        'is_credit': lambda self, cr, uid, ctx: ctx and ctx.get('is_credit', False) or False,
    }

    def onchange_gabungan_gunggung(self,cr,uid,ids,gabungan_gunggung,pajak_gabungan,pajak_gunggung,pajak_generate,context=None):
        value = {}
        if gabungan_gunggung == 'pajak_gabungan' and pajak_gabungan == True:
            value['pajak_gunggung'] = False
            value['pajak_generate'] = False
        if gabungan_gunggung == 'pajak_gunggung' and pajak_gunggung == True:
            value['pajak_gabungan'] = False
            value['pajak_generate'] = False
        if gabungan_gunggung == 'pajak_generate' and pajak_generate == True:
            value['pajak_gunggung'] = False
            value['pajak_gabungan'] = False
        return {'value':value}

    def dealer_spk_id_change(self, cr, uid, ids, dealer_spk_id):
        value = {}
        if dealer_spk_id:
            dealer_spk_id = self.pool.get('dealer.spk').browse(cr, uid, dealer_spk_id, context=context)[0]
            value['register_spk_id'] = dealer_spk_id.register_spk_id.id
        return {'value':value}

    def onchange_credit(self,cr,uid,ids,is_credit):
        value = {}
        if is_credit == False:
            value['finco_id'] = False
        return {'value':value}

    def onchange_po(self,cr,uid,ids,po_id):
        value = {}
        return {'value':value}

    def onchange_is_pic(self,cr,uid,ids,is_pic):
        value = {}
        return {'value':value}

    def _get_approval_diskon(self,cr,uid,data):
        per_product = {}
        hasil = []
        update = False
        for line in data:
            if line[0] == 0: 
                if not per_product.get(line[2]['product_id'],False):
                    per_product[line[2]['product_id']] = {}
                
                per_product[line[2]['product_id']]['product_qty'] = per_product[line[2]['product_id']].get('product_qty',0)+line[2].get('product_qty',0)
                per_product[line[2]['product_id']]['beban_po'] = per_product[line[2]['product_id']].get('beban_po',0)+line[2].get('discount_po',0)
                per_product[line[2]['product_id']]['beban_hc'] = per_product[line[2]['product_id']].get('beban_hc',0)+line[2].get('amount_hutang_komisi',0)
                 
                for disc in line[2]['discount_line']:
                    if disc[2].get('tipe_diskon',0) != 'percentage':
                        per_product[line[2]['product_id']]['beban_ps'] = per_product[line[2]['product_id']].get('beban_ps',0)+disc[2].get('ps_dealer',0)
                 
                for bb in line[2]['barang_bonus_line']:
                    per_product[line[2]['product_id']]['beban_bb'] = per_product[line[2]['product_id']].get('beban_bb',0)+disc[2].get('discount_dealer',0)
                
        if update == False:
            for key, value in per_product.items():
                hasil.append([0,False,{
                    'product_id': key,
                    'product_qty':value.get('product_qty',0),
                    'beban_po':value.get('beban_po',0),
                    'beban_hc':value.get('beban_hc',0),
                    'beban_ps':value.get('beban_ps',0),
                    'beban_bb':value.get('beban_bb',0),
                    'amount_average':(value.get('beban_po',0)+value.get('beban_hc',0)+value.get('beban_ps',0)+value.get('beban_bb',0))/value.get('product_qty',0),                    
                   }])
        else:
            for key, value in per_product.items():
                hasil.append([0,False,{
                    'product_id': key,
                    'product_qty':value.get('product_qty_old',0)-value.get('product_qty',0),
                    'beban_po':value.get('beban_po_old',0)-value.get('beban_po',0),
                    'beban_hc':value.get('beban_hc_old',0)-value.get('beban_hc',0),
                    'beban_ps':value.get('beban_ps_old',0)-value.get('beban_ps',0),
                    'beban_bb':value.get('beban_bb_old',0),
                    'amount_average':(value.get('amount_average_old',0)
                                      -(value.get('beban_po',0)+value.get('beban_hc',0)+value.get('beban_ps',0)+value.get('beban_bb',0)))
                                      /(value.get('product_qty_old',0)-value.get('product_qty',0)),
                                       }])
        return hasil

    def _set_bill_date(self, cr, uid, dsm_id=None, context=None):
        if dsm_id:
            dsm = self.browse(cr, uid, dsm_id)
            if not dsm.bill_date and dsm.is_credit:
                self.write(cr, uid, dsm_id, {
                    'bill_date': time.strftime("%Y-%m-%d")
                    }, context=context)
        return True
    
    def _set_diskon_summary(self,cr,uid,ids,data):
        per_product = {}
        hasil = []
        update = False
        for line in data:
            if not per_product.get(line.product_id.id,False):
                per_product[line.product_id.id] = {}
            per_product[line.product_id.id]['product_qty'] = per_product[line.product_id.id].get('product_qty',0)+line.product_qty
            per_product[line.product_id.id]['beban_po'] = per_product[line.product_id.id].get('beban_po',0)+line.discount_po
            per_product[line.product_id.id]['beban_hc'] = per_product[line.product_id.id].get('beban_hc',0)+line.amount_hutang_komisi
            for disc in line['discount_line']:
                if disc.tipe_diskon != 'percentage':
                    per_product[line.product_id.id]['beban_ps'] = per_product[line.product_id.id].get('beban_ps',0)+disc.ps_dealer
            for bb in line['barang_bonus_line']:
                per_product[line.product_id.id]['beban_bb'] = per_product[line.product_id.id].get('beban_bb',0)+bb.bb_dealer
        
        for key, value in per_product.items():
            average = (value.get('beban_po',0)+value.get('beban_hc',0)+value.get('beban_ps',0)+value.get('beban_bb',0))/value.get('product_qty',0)
            hasil.append([0,False,{
                'product_id': key,
                'product_qty':value.get('product_qty',0),
                'beban_po':value.get('beban_po',0),
                'beban_hc':value.get('beban_hc',0),
                'beban_ps':value.get('beban_ps',0),
                'beban_bb':value.get('beban_bb',0),
                'amount_average':average,
            }])
        check_old_summary = self.pool.get('dealer.sale.order.summary.diskon').search(cr,uid,[('dealer_sale_order_id','in',ids)])
        if check_old_summary:
            delete_summary = self.pool.get('dealer.sale.order.summary.diskon').unlink(cr,uid,check_old_summary)
        insert_summary = self.write(cr,uid,ids,{'summary_diskon_ids':hasil})
        return per_product
    
    def print_wizard(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.wizard.print'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Print SM',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
        } 
        
        
    def print_wizard_kuitansi_pembalik(self,cr,uid,ids,context=None):  
        val = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.kuitansi.pembalik.print'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        untuk_pembayaran_3 = val.untuk_pembayaran_3
        tipe_motor = ''
        tipe_list = []
        if not untuk_pembayaran_3:
            for line in val.dealer_sale_order_line:
                if line.product_id.product_tmpl_id.name not in tipe_list:
                    tipe_list.append(line.product_id.product_tmpl_id.name)
                    tipe_motor += line.product_id.product_tmpl_id.name + ', '
            if tipe_motor:
                tipe_motor = tipe_motor[:-2]
            untuk_pembayaran_3 = ("DISC PEMBELIAN UNTUK %s (%s) UNIT SEPEDA MOTOR HONDA TYPE %s")%(str(len(val.dealer_sale_order_line)), val.get_terbilang(len(val.dealer_sale_order_line), print_subsidi_tax=True).upper(), tipe_motor)
        val.write({'untuk_pembayaran_3':untuk_pembayaran_3})
        return {
            'name': 'Print SM',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': val.id,
        }

    def print_wizard_kuitansi_cod(self,cr,uid,ids,context=None):  
        is_kasir_h1 = self.pool.get("res.users").has_group(cr, uid, 'dym_base_security.group_dym_kasir_h1')
        is_kasir_h123 = self.pool.get("res.users").has_group(cr, uid, 'dym_base_security.group_dym_kasir_h123')
        is_kasir_h23 = self.pool.get("res.users").has_group(cr, uid, 'dym_base_security.group_dym_kasir_h23')
        if not (is_kasir_h1 or is_kasir_h123 or is_kasir_h23):
            raise osv.except_osv(('Warning !'), ("Tombol Penagihan COD hanya bisa dilakukan oleh Kasir"))
    	val = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.kuitansi.cod.print'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        untuk_pembayaran_2 = val.untuk_pembayaran_2
        amount_cod_print = val.amount_cod_print
        tipe_motor = ''
        tipe_list = []
        if not untuk_pembayaran_2:
            for line in val.dealer_sale_order_line:
                if line.product_id.product_tmpl_id.name not in tipe_list:
                    tipe_list.append(line.product_id.product_tmpl_id.name)
                    tipe_motor += line.product_id.product_tmpl_id.name + ', '
            if tipe_motor:
                tipe_motor = tipe_motor[:-2]
            if val.dealer_sale_order_line[0].partner_stnk_id != val.partner_id:
                untuk_pembayaran_2 = ('PEMBELIAN A/N %s QQ "%s" UNTUK %s (%s) UNIT SEPEDA MOTOR HONDA TYPE %s')%(str(val.partner_id.name).upper(), str(val.dealer_sale_order_line[0].partner_stnk_id.name).upper() ,str(len(val.dealer_sale_order_line)), val.get_terbilang(len(val.dealer_sale_order_line), print_subsidi_tax=True).upper(), tipe_motor)
            else:
                untuk_pembayaran_2 = ('PEMBELIAN A/N %s UNTUK %s (%s) UNIT SEPEDA MOTOR HONDA TYPE %s')%(str(val.partner_id.name).upper(), str(len(val.dealer_sale_order_line)), val.get_terbilang(len(val.dealer_sale_order_line), print_subsidi_tax=True).upper(), tipe_motor)
        val.write({'untuk_pembayaran_2':untuk_pembayaran_2})
        if not amount_cod_print:
            amount_cod_print = val.customer_dp if val.is_credit == True else val.amount_total
        val.write({'amount_cod_print':amount_cod_print})
        return {
            'name': 'Print SM',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': val.id,
        }

    def print_wizard_kuitansi_pelunasan_leasing(self,cr,uid,ids,context=None):  
        val = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.kuitansi.pelunasan.leasing'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        untuk_pembayaran_4 = val.untuk_pembayaran_4
        tipe_motor = ''
        tipe_list = []
        if not untuk_pembayaran_4:
            for line in val.dealer_sale_order_line:
                if line.product_id.product_tmpl_id.name not in tipe_list:
                    tipe_list.append(line.product_id.product_tmpl_id.name)
                    tipe_motor += line.product_id.product_tmpl_id.name + ', '
            if tipe_motor:
                tipe_motor = tipe_motor[:-2]
            untuk_pembayaran_4 = ("%s (%s) UNIT SEPEDA MOTOR HONDA TYPE %s + BIAYA PENGURUSAN STNK DAN BPKB")%(str(len(val.dealer_sale_order_line)), val.get_terbilang(len(val.dealer_sale_order_line), print_subsidi_tax=True).upper(), tipe_motor)
        val.write({'untuk_pembayaran_4':untuk_pembayaran_4})
        return {
            'name': 'Print SM',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': val.id,
        } 

    def get_amount_subsidi(self,cr, uid, ids, dso):
        total_ps_finco = 0
        for line in dso.dealer_sale_order_line:
            for disc in line.discount_line:
                total_ps_finco += disc.ps_finco
        if dso.print_subsidi_tax == True:
            total_ps_finco = round((total_ps_finco/0.98) + ((total_ps_finco/0.98) * 0.1), 0)
        return total_ps_finco

    def print_wizard_subsidi_leasing(self,cr,uid,ids,context=None):  
        val = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.subsidi.leasing.print'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        untuk_pembayaran = val.untuk_pembayaran
        val.write({'print_subsidi_tax':False})
        if 'print_subsidi_tax' in context:
            val.write({'print_subsidi_tax':True})
        tipe_motor = ''
        tipe_list = []
        if not untuk_pembayaran:
            for line in val.dealer_sale_order_line:
                if line.product_id.product_tmpl_id.name not in tipe_list:
                    tipe_list.append(line.product_id.product_tmpl_id.name)
                    tipe_motor += line.product_id.product_tmpl_id.name + ', '
            if tipe_motor:
                tipe_motor = tipe_motor[:-2]
            untuk_pembayaran = ("JASA PERANTARA %s (%s) UNIT SEPEDA MOTOR HONDA TYPE %s")%(str(len(val.dealer_sale_order_line)), val.get_terbilang(len(val.dealer_sale_order_line), print_subsidi_tax=True).upper(), tipe_motor)
        val.write({'untuk_pembayaran':untuk_pembayaran})
        return {
            'name': 'Print SM',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': val.id,
        } 
    
    def print_wizard_pelunasan_leasing(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.pelunasan.leasing.print'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Print Pelunasan Leasing',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
        } 

    def print_wizard_kuitansi_mediator(self,cr,uid,ids,context=None):  
        is_kasir_h1 = self.pool.get("res.users").has_group(cr, uid, 'dym_base_security.group_dym_kasir_h1')
        is_kasir_h123 = self.pool.get("res.users").has_group(cr, uid, 'dym_base_security.group_dym_kasir_h123')
        is_kasir_h23 = self.pool.get("res.users").has_group(cr, uid, 'dym_base_security.group_dym_kasir_h23')
        if not (is_kasir_h1 or is_kasir_h123 or is_kasir_h23):
            raise osv.except_osv(('Warning !'), ("Tombol Kuitansi Mediator hanya bisa dilakukan oleh Kasir"))
            
        val = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        # obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.kuitansi.pembalik.print'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.kuitansi.mediator.print'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        untuk_pembayaran_5 = val.untuk_pembayaran_5
        tipe_motor = ''
        tipe_list = []
        if not untuk_pembayaran_5:
            for line in val.dealer_sale_order_line:
                if line.product_id.product_tmpl_id.name not in tipe_list:
                    tipe_list.append(line.product_id.product_tmpl_id.name)
                    tipe_motor += line.product_id.product_tmpl_id.name + ', '
            if tipe_motor:
                tipe_motor = tipe_motor[:-2]
            untuk_pembayaran_5 = ("JASA PERANTARA UNTUK %s (%s) UNIT SEPEDA MOTOR HONDA TYPE %s")%(str(len(val.dealer_sale_order_line)), val.get_terbilang(len(val.dealer_sale_order_line), print_subsidi_tax=True).upper(), tipe_motor)
        val.write({'untuk_pembayaran_5':untuk_pembayaran_5})
        return {
            'name': 'Print Kwitansi Mediator',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': val.id,
        }

    def print_wizard_invoice_mediator(self,cr,uid,ids,context=None):  
        val = self.browse(cr,uid,ids)
        invoice_obj = self.pool.get("account.invoice")
        invoice_ids = invoice_obj.search(cr, uid, [('origin','=',val.name),('type','=','in_invoice')], limit=1, context=context)
        invoice = invoice_obj.browse(cr, uid, invoice_ids, context=context)
        if not invoice:
            raise osv.except_osv(('Waduh !'), ("Maaf ya, saya tidak menemukan invoice mediator."))
        return invoice.invoice_print()
        
    def subsidi_leasing(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.subsidi.wizard'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Subsidi QQ',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
        }
                
    def create(self,cr,uid,vals,context=None):
        if not vals['dealer_sale_order_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail Sales. Data tidak bisa di save."))
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'DSM', division='Unit', context=context)
        import json
        dealer_sales_order = super(dealer_sale_order, self).create(cr, uid, vals, context=context)
        if dealer_sales_order:
            obj_lot = self.pool.get('stock.production.lot')
            for line in vals['dealer_sale_order_line']: 
                if line[2]['is_bbn']=='T' and 'finco_id' in vals and vals['finco_id']:
                    raise osv.except_osv(('Perhatian !'), ("Penjualan credit harus harus menggunakan BBN!"))
                lot_update_reserve = obj_lot.write(cr,uid,line[2]['lot_id'],{'state': 'reserved','sale_order_reserved':dealer_sales_order,'customer_reserved':vals['partner_id']})
            obj_branch_config = self._get_branch_journal_config(cr, uid, vals['branch_id'])
        return dealer_sales_order
    
    def _get_branch_journal_config(self,cr,uid,branch_id):
        result = {}
        obj_branch_config_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
        if not obj_branch_config_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak Ditemukan konfigurasi jurnal Cabang, Silahkan konfigurasi dulu"))
        else:
            obj_branch_config = self.pool.get('dym.branch.config').browse(cr,uid,obj_branch_config_id[0])
            if not(obj_branch_config.dealer_so_journal_pic_id.id and obj_branch_config.dealer_so_journal_pelunasan_id.id and obj_branch_config.dealer_so_journal_psmd_id.id and obj_branch_config.dealer_so_journal_psfinco_id.id and obj_branch_config.dealer_so_account_bbn_jual_id.id and obj_branch_config.dealer_so_account_sisa_subsidi_id.id and obj_branch_config.dealer_so_journal_hc_id.id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi jurnal penjualan cabang belum lengkap, silahkan setting dulu"))
        return obj_branch_config
   
    def _get_cost_quant_per_lot(self,cr,uid,lot_id):
        cost_quant = 0.0
        obj_quant = self.pool.get('stock.quant')
        quant_id = obj_quant.search(cr,uid,[('lot_id','=',lot_id.id)])
        if quant_id:
            cost_quant = obj_quant.browse(cr,uid,quant_id[0])['cost']
        return cost_quant

    def action_button_cancel_sale(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        for o in self.browse(cr, uid, ids):
            for line in o.dealer_sale_order_line:
                update_lot = self.update_serial_number(cr,uid,{
                    'state':'stock',
                    'sale_order_reserved':False,
                    'customer_reserved':False,
                    'dealer_sale_order_id': False,
                    'invoice_date': False,
                    'customer_id': False,
                    'customer_stnk': False,
                    'dp': 0,
                    'tenor': 0,
                    'cicilan': 0,
                    'jenis_penjualan':'',
                    'finco_id':False,
                    'biro_jasa_id': False,
                    'invoice_bbn': False,
                    'total_jasa':0,
                    'cddb_id':False,
                    'move_lines_invoice_bbn_id':False,
                    'pengurusan_stnk_bpkb_id':False,
                    'state_stnk':False,
                    'tgl_pengurusan_stnk_bpkb' : False,
                    'inv_pengurusan_stnk_bpkb_id': False,
                    'invoice_bbn':False,
                    'total_jasa':0,
                    'pengurusan_stnk_bpkb_id':False,
                    'tgl_faktur':False,
                    'permohonan_faktur_id':False,
                    'tgl_terima':False,
                    'penerimaan_faktur_id':False,
                    'faktur_stnk':False,
                    'tgl_cetak_faktur':False,
                    'tgl_penyerahan_faktur':False,
                    'penyerahan_faktur_id':False,
                    'lot_status_cddb':'not',
                    'proses_biro_jasa_id': False,
                    'tgl_proses_birojasa':False,
                    'no_notice_copy':False,
                    'tgl_notice_copy':False,
                    'proses_stnk_id':False,
                    'tgl_proses_stnk':False,
                    'no_faktur':'',
                },line.lot_id.id)
            o.picking_ids.action_cancel()
            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('origin','ilike',o.name)])
            invoices = self.pool.get('account.invoice').browse(cr, uid, invoice_ids)
            invoices.signal_workflow('invoice_cancel') 
            voucher_ids = self.pool.get('account.voucher').search(cr, uid, [('name','ilike',o.name)])
            vouchers = self.pool.get('account.voucher').browse(cr, uid, voucher_ids)
            vouchers.cancel_voucher()
            o.delete_workflow()
            o.create_workflow()
            self.signal_workflow(cr, uid, ids, 'draft_cancel')
        return True

    def action_button_confirm(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        
        for o in self.browse(cr, uid, ids):
            
            if not o.dealer_sale_order_line:
                raise osv.except_osv(_('Attention!'),_('Tidak ada detail Sales. Data tidak bisa di confirm.'))
            else:
                self.write(cr, uid, ids, {'state': 'progress', 'date_confirm': fields.date.context_today(self, cr, uid, context=context)})
            
            for line in o.dealer_sale_order_line:
                cost_quant = 0.0
                price_id = self.pool.get('product.price.branch').search(cr, uid, [('warehouse_id','=', o.branch_id.warehouse_id.id), ('product_id','=', line.product_id.id)])
                if price_id:
                    cost_quant = self.pool.get('product.price.branch').browse(cr, uid, price_id[0]).cost
                line.write({'force_cogs': cost_quant})
                for barang_bonus in line.barang_bonus_line:
                    barang_bonus.write({'force_cogs':barang_bonus.price_barang})
            self.signal_workflow(cr, uid, ids, 'order_confirm')

            jenis_penjualan = '1'
            finco_id = False
            finco_cabang = False
            inv_bbn_jual_id = False
            total_jasa = 0
            obj_inv = self.pool.get('account.invoice')
            if o.finco_id:
                jenis_penjualan = '2'
                finco_id = o.finco_id.id
                finco_cabang = o.finco_cabang.id
        
                inv_id = obj_inv.search(cr,uid,[
                    ('origin','ilike',o.name),
                    ('partner_id','in',[o.partner_id.id,o.finco_id.id]),
                    ('tipe','=','finco')
                    ])
                inv_id_dp = obj_inv.search(cr,uid,[
                    ('origin','ilike',o.name),
                    ('partner_id','=',o.partner_id.id),
                    ('tipe','=','customer')
                    ])

            else:
                inv_id = obj_inv.search(cr,uid,[
                    ('origin','ilike',o.name),
                    ('partner_id','=',o.partner_id.id),
                    ('tipe','=','customer')
                    ])

            for line in o.dealer_sale_order_line:
                move_line_bbn_ids = False

                state = line.lot_id.state
                if line.lot_id.state not in ('paid','paid_offtr'):
                    if line.is_bbn == 'Y':
                        state = 'sold'
                    else:
                        state = 'sold_offtr'
                cddb_id = None
                if line.partner_stnk_id:
                    cddb_id = line.partner_stnk_id.id

                values = {
                   'dealer_sale_order_id': o.id,
                   'invoice_date': datetime.now().strftime('%Y-%m-%d'),
                   'customer_id': o.partner_id.id,
                   'customer_stnk': line.partner_stnk_id.id,
                   'dp': line.uang_muka,
                   'tenor': line.finco_tenor,
                   'cicilan': line.cicilan,
                   'jenis_penjualan':jenis_penjualan,
                   'finco_id':finco_id,
                   'finco_cabang':finco_cabang,
                   'state': state,
                   'biro_jasa_id': line.biro_jasa_id.id,
                   'invoice_bbn': inv_bbn_jual_id,
                   'total_jasa':total_jasa,
                   'cddb_id':cddb_id,
                   'move_lines_invoice_bbn_id':move_line_bbn_ids,
                   'plat':line.plat,
                }
                
                update_lot = self.update_serial_number(cr,uid,values,line.lot_id.id)
        self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now(),'date_order':datetime.today()})
        return True
    
    def get_move_line_bbn(self,cr,uid,ids,move_line_bbn_ids,line_ids,context=None):
        for x in line_ids :
            if x.credit > 0.0 :
                move_line_bbn_ids = x.id                              
        return move_line_bbn_ids
    
    def button_dummy(self, cr, uid, ids, context=None):
        return True
    
    def _get_product_template_id(self, cr, uid , product_id, context=None):
        product_template_obj = self.pool.get('product.product').browse(cr,uid,product_id)
        product_template_id = product_template_obj.product_tmpl_id.id
        
        return product_template_id
    
    def onchange_sales(self,cr,uid,ids,sales_id):
        value = {}
        if sales_id:            
            partner = self.pool.get('hr.employee').browse(cr,uid,sales_id)
            section = self.pool.get('crm.case.section').search(cr,uid,['|',('user_id','=',sales_id),('member_ids','=',sales_id)], limit=1)
            value['partner_komisi_id'] = partner.partner_id.id
            if section:
                value['section_id'] = section[0]
            return {'value':value}
        return False
        
    
    def action_invoice_create(self, cr, uid, ids, context=None):
        sale_order = self.browse(cr, uid, ids, context)
        if not sale_order or not sale_order.ensure_one():
            raise osv.except_osv(_('Error!'),
                _('action_invoice_create() method only for single object.'))
        elif not sale_order.dealer_sale_order_line:
            raise osv.except_osv(_('Error!'),
                _('Harap isi detil sale order terlebih dahulu.'))

        obj_inv = self.pool.get('account.invoice') 
        account_id = False
        ar_branch_id = False
        ap_branch_id = False
        default_supplier = False
        invoice_customer = {}
        invoice_customer_line = []
        invoice_finco = {}
        invoice_finco_line = []
        invoice_pelunasan = {}
        invoice_pelunasan_line = []
        invoice_bbn = {}
        invoice_bbn_line = []
        invoice_insentif_finco = {}
        invoice_insentif_finco_line = []
        invoice_hc = {}
        invoice_hc_line = []
        analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, sale_order.branch_id, 'Unit', False, 4, 'Sales')
        analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, sale_order.branch_id, 'Unit', False, 4, 'General')
        obj_bbn = self.pool.get('dym.harga.bbn.line')

        obj_branch_config = self._get_branch_journal_config(cr,uid,sale_order.branch_id.id)
        finco = False
        if not obj_branch_config.dealer_so_journal_pic_id.default_debit_account_id.id and not obj_branch_config.dealer_so_journal_pelunasan_id.default_debit_account_id.id and not sale_order.partner_id.property_account_receivable.id:
            raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet jurnal pelunasan penjualan regular atau intercompany dan account receivable di customer belum lengkap!"))
        
        qq2_ids = []
        for l in sale_order.dealer_sale_order_line:
            if l.partner_stnk_id:
                qq2_ids.append(l.partner_stnk_id.id)
        if qq2_ids:
            qq2_ids = [(6,0,qq2_ids)]

        if sale_order.is_pic:
            journal_id = obj_branch_config.dealer_so_journal_pic_id.id
            account_id = obj_branch_config.dealer_so_journal_pic_id.default_debit_account_id.id or sale_order.partner_id.property_account_receivable.id,
        else:
            journal_id = obj_branch_config.dealer_so_journal_pelunasan_id.id
            account_id = obj_branch_config.dealer_so_journal_pelunasan_id.default_debit_account_id.id or sale_order.partner_id.property_account_receivable.id,

        if sale_order.finco_id:
            finco = sale_order.finco_id.id
            invoice_pelunasan = {
                'name':sale_order.name,
                'origin': sale_order.name,
                'branch_id':sale_order.branch_id.id,
                'division':sale_order.division,
                'partner_id':sale_order.partner_id.id,
                'date_invoice':sale_order.date_order,
                'reference_type':'none',
                'type': 'out_invoice', 
                'tipe': 'finco',
                'qq_id': sale_order.partner_id.id,
                'qq2_id': qq2_ids,
                'journal_id': journal_id,
                'account_id': account_id,
                'payment_term': sale_order.payment_term.id,
                'section_id':sale_order.section_id.id,
                'analytic_1': analytic_1_general,
                'analytic_2': analytic_2_general,
                'analytic_3': analytic_3_general,
                'analytic_4': analytic_4_general,
            }
            invoice_insentif_finco = {
                'name':sale_order.name,
                'origin': sale_order.name,
                'branch_id':sale_order.branch_id.id,
                'division':sale_order.division,
                'partner_id':sale_order.finco_id.id,
                'date_invoice':sale_order.date_order,
                'reference_type':'none',
                'type': 'out_invoice', 
                'tipe': 'insentif',
                'qq_id': sale_order.partner_id.id,
                'qq2_id': qq2_ids,
                'journal_id': obj_branch_config.dealer_so_journal_insentive_finco_id.id,
                'account_id': obj_branch_config.dealer_so_journal_insentive_finco_id.default_debit_account_id.id,
                'analytic_1': analytic_1_general,
                'analytic_2': analytic_2_general,
                'analytic_3': analytic_3_general,
                'analytic_4': analytic_4_general,
            }
        else:
             invoice_pelunasan = {
                'name':sale_order.name,
                'origin': sale_order.name,
                'branch_id':sale_order.branch_id.id,
                'division':sale_order.division,
                'partner_id':sale_order.partner_id.id,
                'date_invoice':sale_order.date_order,
                'reference_type':'none',
                'type': 'out_invoice', 
                'tipe': 'customer',
                'journal_id': journal_id,
                'account_id': account_id,
                'payment_term': sale_order.payment_term.id,
                'section_id':sale_order.section_id.id,   
                'analytic_1': analytic_1_general,
                'analytic_2': analytic_2_general,
                'analytic_3': analytic_3_general,
                'analytic_4': analytic_4_general,               
            }
        
        if sale_order.partner_komisi_id:
            if not (obj_branch_config.dealer_so_journal_hc_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_hc_id.default_debit_account_id.id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal HC belum lengkap!"))
            invoice_hc = {
                'name':sale_order.name,
                'origin': sale_order.name,
                'branch_id':sale_order.branch_id.id,
                'division':sale_order.division,
                'partner_id':sale_order.partner_komisi_id.id,
                'date_invoice':sale_order.date_order,
                'reference_type':'none',
                'type': 'in_invoice', 
                'tipe': 'hc',
                'journal_id': obj_branch_config.dealer_so_journal_hc_id.id,
                'account_id': obj_branch_config.dealer_so_journal_hc_id.default_credit_account_id.id,
                'analytic_1': analytic_1_general,
                'analytic_2': analytic_2_general,
                'analytic_3': analytic_3_general,
                'analytic_4': analytic_4_general,
            }

        per_product = {}
        per_potongan = {}
        per_barang_bonus = {}
        per_invoice = []
        per_ar = []
        for line in sale_order.dealer_sale_order_line:
            
            if not per_product.get(line.product_id.id,False):
                per_product[line.product_id.id] = {}
                
            per_product[line.product_id.id]['product_qty'] = per_product[line.product_id.id].get('product_qty',0)+line.product_qty
            per_product[line.product_id.id]['price_unit'] = per_product[line.product_id.id].get('price_unit',0)+line.price_unit
            per_product[line.product_id.id]['force_cogs'] = per_product[line.product_id.id].get('force_cogs',0)+line.force_cogs
            per_product[line.product_id.id]['tax_id'] = [(6, 0, [y.id for y in line.tax_id])]
            
            if line.is_bbn == 'Y':
                per_product[line.product_id.id]['price_bbn'] = per_product[line.product_id.id].get('price_bbn',0)+line.price_bbn
                per_product[line.product_id.id]['product_qty_bbn'] = per_product[line.product_id.id].get('product_qty_bbn',0)+line.product_qty
            if line.hutang_komisi_id and line.amount_hutang_komisi:
                per_product[line.product_id.id]['amount_hutang_komisi'] = per_product[line.product_id.id].get('amount_hutang_komisi',0)+line.amount_hutang_komisi
            
            per_product[line.product_id.id]['customer_dp'] = per_product[line.product_id.id].get('customer_dp',0)+line.uang_muka
            insentif_finco = line._get_insentif_finco_value(finco,sale_order.branch_id.id)
            self.write(cr, uid, line.id, {'insentif_finco':insentif_finco})
            per_product[line.product_id.id]['insentif_finco'] = per_product[line.product_id.id].get('insentif_finco',0)+insentif_finco
            per_potongan['discount_po'] = per_potongan.get('discount_po',0)+line.discount_po
            per_potongan['tax_id'] = [(6, 0, [y.id for y in line.tax_id])]
            
            date_due_default = datetime.now().strftime('%Y-%m-%d')
            date_due_finco = datetime.now().strftime('%Y-%m-%d')
            if sale_order.finco_id.property_payment_term:
                pterm_list = sale_order.finco_id.property_payment_term.compute(value=1, date_ref=date_due_finco)[0]
                if pterm_list:
                    date_due_finco = max(line[0] for line in pterm_list)
            if sale_order.branch_id.default_supplier_id.property_payment_term:
                pterm_list = sale_order.branch_id.default_supplier_id.property_payment_term.compute(value=1, date_ref=date_due_default)[0]
                if pterm_list:
                    date_due_default = max(line[0] for line in pterm_list)

            for disc in line.discount_line:
                invoice_ps_finco = {}
                invoice_ps_finco_line = []
                
                if disc.include_invoice == False:
                    continue

                if disc.tipe_diskon == 'percentage':
                    total_diskon = disc.discount_pelanggan
                    if disc.tipe_diskon == 'percentage':
                        total_diskon = line.price_unit * disc.discount_pelanggan / 100
                    per_potongan['discount_pelanggan'] = per_potongan.get('discount_pelanggan',0)+(total_diskon*line.product_qty)
                else:
                    total_claim_discount = disc.ps_ahm + disc.ps_md + disc.ps_finco + disc.ps_others + disc.ps_dealer
                    total_diskon_pelanggan = 0 if total_claim_discount - disc.discount_pelanggan >= disc.ps_dealer else disc.ps_dealer - (total_claim_discount - disc.discount_pelanggan)
                    total_diskon_external = disc.discount_pelanggan - total_diskon_pelanggan
                    per_potongan['discount_external'] = per_potongan.get('discount_external',0)+(total_diskon_external*line.product_qty)
                    per_potongan['discount_pelanggan'] = per_potongan.get('discount_pelanggan',0)+(total_diskon_pelanggan*line.product_qty)
                if disc.tipe_diskon == 'percentage':
                    continue
                discount_gap = 0.0
                discount_md = 0.0
                discount_finco = 0.0
                discount_oi = 0.0
                sisa_ke_finco = False
                
                if disc.discount_pelanggan != disc.discount:
                     discount_gap =  disc.discount - disc.discount_pelanggan
                taxes = [(6, 0, [y.id for y in line.tax_id])]
                
                if disc.ps_finco > 0:
                    if not (obj_branch_config.dealer_so_journal_psfinco_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_psfinco_id.default_debit_account_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal PS Finco belum lengkap!"))
                    if not sale_order.finco_id.id:
                        raise osv.except_osv(('Perhatian !'), ("Financial company perlu didefinisikan untuk program subsidi " + disc.program_subsidi.name + "!"))
                    invoice_ps_finco = {
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.finco_id.id,
                        'date':datetime.now().strftime('%Y-%m-%d'), 
                        'date_due': date_due_finco, 
                        'reference': sale_order.name, #
                        'name':sale_order.name,
                        'user_id': sale_order.user_id.id,
                        'journal_id': obj_branch_config.dealer_so_journal_psfinco_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_psfinco_id.default_debit_account_id.id,
                        'type': 'sale',
                        'analytic_1': analytic_1_general,
                        'analytic_2': analytic_2_general,
                        'analytic_3': analytic_3_general,
                        'analytic_4': analytic_4_general,
                    }
                    
                    if discount_gap >0:
                        if disc.ps_finco > discount_gap: 
                            discount_finco = disc.ps_finco - discount_gap
                            discount_oi = discount_gap
                            sisa_ke_finco = True
                        elif disc.ps_finco == discount_gap:
                            discount_finco = disc.ps_finco
                        else:
                            discount_oi = discount_gap - disc.ps_finco
                            discount_finco = disc.ps_finco - discount_oi
                            discount_gap = discount_gap - discount_oi
                        
                        if discount_finco > 0:   
                            invoice_ps_finco_line.append([0,False,{
                                'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                'amount': discount_finco,
                                'account_id': obj_branch_config.dealer_so_journal_psfinco_id.default_credit_account_id.id,
                                'type': 'cr',
                                'analytic_1': analytic_1,
                                'analytic_2': analytic_2,
                                'analytic_3': analytic_3,
                                'account_analytic_id':analytic_4,  
                            }])
                        
                        if discount_oi>0:
                            invoice_ps_finco_line.append([0,False,{
                                'name': 'Sisa subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                'amount':discount_oi,
                                'account_id': obj_branch_config.dealer_so_account_sisa_subsidi_id.id,
                                'type': 'cr',
                                'analytic_1': analytic_1,
                                'analytic_2': analytic_2,
                                'analytic_3': analytic_3,
                                'account_analytic_id':analytic_4,  
                            }])
                        
                    else:
                        invoice_ps_finco_line.append([0,False,{
                            'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                            'amount':disc.ps_finco,
                            'account_id': obj_branch_config.dealer_so_journal_psfinco_id.default_credit_account_id.id,
                            'type': 'cr',
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])
                        sisa_ke_finco = True
                        
                    invoice_ps_finco['line_cr_ids'] = invoice_ps_finco_line
                    per_ar.append(invoice_ps_finco)
                
                if (disc.ps_ahm > 0 or disc.ps_md > 0):
                    invoice_md = {}
                    invoice_md_line = []
        
                    if not (obj_branch_config.dealer_so_journal_psmd_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_psmd_id.default_debit_account_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal PS MD belum lengkap!"))
                    if not sale_order.branch_id.default_supplier_id.id:
                        raise osv.except_osv(('Perhatian !'), ("Principle di branch belum diisi, silahkan setting dulu!"))
                    invoice_md = {
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.branch_id.default_supplier_id.id,
                        'date':datetime.now().strftime('%Y-%m-%d'), 
                        'date_due': date_due_default, 
                        'reference': sale_order.name, #
                        'name':sale_order.name,
                        'user_id': sale_order.user_id.id,
                        'journal_id': obj_branch_config.dealer_so_journal_psmd_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_psmd_id.default_debit_account_id.id,
                        'type': 'sale',
                        'analytic_1': analytic_1_general,
                        'analytic_2': analytic_2_general,
                        'analytic_3': analytic_3_general,
                        'analytic_4': analytic_4_general,
                    }
                    
                    if sisa_ke_finco == False:
                        if discount_gap >0:
                            if (disc.ps_md+disc.ps_ahm) >= discount_gap:
                                discount_md = disc.ps_md+disc.ps_ahm-discount_gap
                                discount_oi = discount_gap
                            else:
                                discount_md = discount_gap - disc.ps_md- disc.ps_ahm
                            
                            if discount_md>0:  
                                invoice_md_line.append([0,False,{
                                    'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                    'amount': discount_md,
                                    'account_id': obj_branch_config.dealer_so_journal_psmd_id.default_credit_account_id.id,
                                    'type': 'cr',
                                    'analytic_1': analytic_1,
                                    'analytic_2': analytic_2,
                                    'analytic_3': analytic_3,
                                    'account_analytic_id':analytic_4,  
                                }])
                            
                            if discount_oi>0:
                                invoice_md_line.append([0,False,{
                                    'name': 'Sisa subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                    'amount': discount_gap,
                                    'account_id': obj_branch_config.dealer_so_account_sisa_subsidi_id.id,
                                    'type': 'cr',
                                    'analytic_1': analytic_1,
                                    'analytic_2': analytic_2,
                                    'analytic_3': analytic_3,
                                    'account_analytic_id':analytic_4,  
                                }])
                        else:
                            invoice_md_line.append([0,False,{
                                'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                'amount': disc.ps_ahm+disc.ps_md,
                                'account_id': obj_branch_config.dealer_so_journal_psmd_id.default_credit_account_id.id,
                                'type': 'cr',
                                'analytic_1': analytic_1,
                                'analytic_2': analytic_2,
                                'analytic_3': analytic_3,
                                'account_analytic_id':analytic_4,  
                            }])
                        
                    else:
                        invoice_md_line.append([0,False,{
                            'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                            'amount': disc.ps_ahm+disc.ps_md,
                            'account_id': obj_branch_config.dealer_so_journal_psmd_id.default_credit_account_id.id,
                            'type': 'cr',
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])
                            
                    invoice_md['line_cr_ids'] = invoice_md_line
                    
                    per_ar.append(invoice_md)

            for barang_bonus in line.barang_bonus_line:
                if not per_barang_bonus.get(barang_bonus.product_subsidi_id.id,False):
                    per_barang_bonus[barang_bonus.product_subsidi_id.id] = {}
                per_barang_bonus[barang_bonus.product_subsidi_id.id]['product_qty'] = per_barang_bonus[barang_bonus.product_subsidi_id.id].get('product_qty',0)+ barang_bonus.barang_qty
                per_barang_bonus[barang_bonus.product_subsidi_id.id]['force_cogs'] = per_barang_bonus[barang_bonus.product_subsidi_id.id].get('force_cogs',0)+barang_bonus.price_barang
                if barang_bonus.bb_md > 0 or barang_bonus.bb_ahm > 0:
                    invoice_bb_md = {}
                    invoice_bb_md_line = []
                    
                    if not (obj_branch_config.dealer_so_journal_bbmd_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_bbmd_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal Barang Subsidi belum lengkap!"))
                    invoice_bb_md = {
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.branch_id.default_supplier_id.id,
                        'date':datetime.now().strftime('%Y-%m-%d'), 
                        'date_due': date_due_default, 
                        'reference': sale_order.name, #
                        'name':sale_order.name,
                        'user_id': sale_order.user_id.id,
                        'journal_id': obj_branch_config.dealer_so_journal_bbmd_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_bbmd_id.default_debit_account_id.id,
                        'type': 'sale',
                        'analytic_1': analytic_1_general,
                        'analytic_2': analytic_2_general,
                        'analytic_3': analytic_3_general,
                        'analytic_4': analytic_4_general,
                    }
                    invoice_bb_md_line = [[0,False,{
                        'name': 'Subsidi '+barang_bonus.barang_subsidi_id.name+' '+line.product_id.name,
                        'amount': barang_bonus.bb_ahm+barang_bonus.bb_md,
                        'account_id': obj_branch_config.dealer_so_journal_bbmd_id.default_credit_account_id.id,
                        'type': 'cr',
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id':analytic_4,  
                    }]]
                    invoice_bb_md['line_cr_ids'] = invoice_bb_md_line
                    per_ar.append(invoice_bb_md)
                if barang_bonus.bb_finco > 0:
                    invoice_bb_finco = {}
                    invoice_bb_finco_line = []
                    if not (obj_branch_config.dealer_so_journal_bbfinco_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_bbfinco_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal Barang Subsidi Finco belum lengkap!"))
                    invoice_bb_finco = {
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.finco_id.id,
                        'date':datetime.now().strftime('%Y-%m-%d'), 
                        'date_due': date_due_finco, 
                        'reference': sale_order.name, #
                        'name':sale_order.name,
                        'user_id': sale_order.user_id.id,
                        'journal_id': obj_branch_config.dealer_so_journal_bbfinco_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_bbfinco_id.default_debit_account_id.id,
                        'type': 'sale',
                        'analytic_1': analytic_1_general,
                        'analytic_2': analytic_2_general,
                        'analytic_3': analytic_3_general,
                        'analytic_4': analytic_4_general,
                    }
                    invoice_bb_finco_line = [[0,False,{
                        'name': 'Subsidi '+barang_bonus.barang_subsidi_id.name+' '+line.product_id.name,
                        'amount': barang_bonus.bb_finco,
                        'account_id': obj_branch_config.dealer_so_journal_bbfinco_id.default_credit_account_id.id,
                        'type': 'cr',
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id':analytic_4,  
                    }]]
                    invoice_bb_finco['line_cr_ids'] = invoice_bb_finco_line
                    per_ar.append(invoice_bb_finco)

        if sale_order.customer_dp > 0:
            invoice_pelunasan['amount_dp'] = sale_order.customer_dp
            invoice_pelunasan['account_dp'] = obj_branch_config.dealer_so_account_dp.id
        
        invoice_pelunasan['tanda_jadi'] = sale_order.tanda_jadi
            
        if sale_order.amount_bbn > 0:
            invoice_pelunasan['amount_bbn'] = sale_order.amount_bbn
            invoice_pelunasan['account_bbn'] = obj_branch_config.dealer_so_account_bbn_jual_id.id

        for key, value in per_product.items():            
            product_id = self.pool.get('product.product').browse(cr,uid,key)
            product_income_account_id = self.pool.get('product.product')._get_account_id(cr,uid,ids,product_id.id)
            if not product_income_account_id:
                raise osv.except_osv(_('Error!'),
                    _('Income account untuk produk %s belum diisi!') % \
                    (product_id.name))
            sale_account_id = self.pool.get('product.product')._get_account_id(cr,uid,ids,product_id.id)
            if sale_order.is_pic:
                sale_account_id = obj_branch_config.dealer_so_account_penjualan_pic_id.id
                if not sale_account_id:                
                    raise osv.except_osv(_('Error!'),
                        _('Konfigurasi akun penjualan inter-company di Branch Config belum tidak ada!'))

            invoice_pelunasan_line.append([0,False,{
                'name': 'HMK' + product_id.name,
                'product_id':product_id.id,
                'quantity':value['product_qty'],
                'origin':sale_order.name,
                'price_unit':((value['price_unit'])/value['product_qty']),
                'invoice_line_tax_id': value['tax_id'],
                'account_id': sale_account_id,
                'force_cogs': value.get('force_cogs',0),
                'analytic_1': analytic_1,
                'analytic_2': analytic_2,
                'analytic_3': analytic_3,
                'account_analytic_id':analytic_4,  
            }])
            if value.get('insentif_finco',0) > 0:
                invoice_insentif_finco_line.append([0,False,{
                    'name': 'Insentif '+str(product_id.name),
                    'quantity': value['product_qty'],
                    'origin': sale_order.name,
                    'price_unit':value['insentif_finco']/value['product_qty'],
                    'invoice_line_tax_id': [(6,0,[2])],
                    'account_id': obj_branch_config.dealer_so_journal_insentive_finco_id.default_credit_account_id.id,
                    'analytic_1': analytic_1,
                    'analytic_2': analytic_2,
                    'analytic_3': analytic_3,
                    'account_analytic_id':analytic_4,  
                }])
                
            if value.get('amount_hutang_komisi') > 0:
                invoice_hc_line.append([0,False,{
                    'name': 'Hutang Komisi '+str(product_id.name),
                    'quantity': value['product_qty'],
                    'origin': sale_order.name,
                    'price_unit':value['amount_hutang_komisi']/value['product_qty'],
                    'account_id': obj_branch_config.dealer_so_journal_hc_id.default_debit_account_id.id,
                    'analytic_1': analytic_1,
                    'analytic_2': analytic_2,
                    'analytic_3': analytic_3,
                    'account_analytic_id':analytic_4,  
                }])
        for key, value in per_potongan.items():
            if value > 0:
                price_unit = -1*value
                tax = per_potongan['tax_id']
                if key=='discount_po':
                    if not obj_branch_config.dealer_so_account_potongan_langsung_id:
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan langsung di branch config belum ada!"))                    
                    account_discount_id = obj_branch_config.dealer_so_account_potongan_langsung_id
                    if sale_order.is_pic:
                        account_discount_id = obj_branch_config.dealer_so_account_potongan_pic_id
                        if not account_discount_id:
                            raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan inter company di branch config belum ada!"))
                    invoice_pelunasan_line.append([0,False,{
                        'name': 'Diskon Reguler',
                        'quantity':1,
                        'origin':sale_order.name,
                        'price_unit':price_unit,
                        'invoice_line_tax_id':tax,
                        'account_id': account_discount_id.id,
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id':analytic_4,  
                    }])
                
                if key=='discount_pelanggan':
                    # invoice_pelunasan['discount_program'] = value
                    if not obj_branch_config.dealer_so_account_potongan_subsidi_id:
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan subsidi di branch config belum ada!"))                    
                    account_discount_id = obj_branch_config.dealer_so_account_potongan_subsidi_id
                    if sale_order.is_pic:
                        account_discount_id = obj_branch_config.dealer_so_account_potongan_pic_id
                        if not account_discount_id:
                            raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan inter company di branch config belum ada!"))
                    invoice_pelunasan_line.append([0,False,{
                        'name': 'Diskon Dealer',
                        'quantity':1,
                        'origin':sale_order.name,
                        'price_unit':price_unit,
                        'invoice_line_tax_id':tax,
                        'account_id': account_discount_id.id,
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id':analytic_4,  
                    }])
                if key=='discount_external':
                    # invoice_pelunasan['discount_program'] = value
                    if not obj_branch_config.dealer_so_account_potongan_subsidi_external_id:
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan subsidi external di branch config belum ada!"))
                    account_discount_id = obj_branch_config.dealer_so_account_potongan_subsidi_external_id
                    if sale_order.is_pic:
                        account_discount_id = obj_branch_config.dealer_so_account_potongan_pic_id
                        if not account_discount_id:
                            raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan inter company di branch config belum ada!"))
                    invoice_pelunasan_line.append([0,False,{
                        'name': 'Diskon External',
                        'quantity':1,
                        'origin':sale_order.name,
                        'price_unit':price_unit,
                        'invoice_line_tax_id':tax,
                        'account_id': account_discount_id.id,
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id':analytic_4,  
                    }])
        if invoice_hc_line:
            invoice_hc['invoice_line']=invoice_hc_line
            create_invoice_hc = obj_inv.create(cr,uid,invoice_hc)
            obj_inv.button_reset_taxes(cr,uid,create_invoice_hc)
            workflow.trg_validate(uid, 'account.invoice', create_invoice_hc, 'invoice_open', cr)
            
        for value in per_invoice:
            create_invoice = obj_inv.create(cr,uid,value)
            obj_inv.button_reset_taxes(cr,uid,create_invoice)
            workflow.trg_validate(uid, 'account.invoice', create_invoice, 'invoice_open', cr)

        for value in per_ar:
            create_ar = self.pool.get('account.voucher').create(cr,uid,value,context=context)

        invoice_pelunasan['invoice_line']= invoice_pelunasan_line
        create_invoice_pelunasan = obj_inv.create(cr,uid,invoice_pelunasan)
        obj_inv.button_reset_taxes(cr,uid,create_invoice_pelunasan)
        workflow.trg_validate(uid, 'account.invoice', create_invoice_pelunasan, 'invoice_open', cr)
        if sale_order.amount_tax and not sale_order.pajak_gabungan and not sale_order.pajak_gunggung :   
            self.pool.get('dym.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'dealer.sale.order',context=context) 
        if sale_order.amount_tax and sale_order.pajak_gunggung == True :   
            self.pool.get('dym.faktur.pajak.out').create_pajak_gunggung(cr,uid,ids,'dealer.sale.order',context=context)
        return create_invoice_pelunasan 

    def action_invoice_dp_create(self,cr,uid,ids,context=None):
        invoice_customer = {}
        invoice_customer_line = []
        obj_inv = self.pool.get('account.invoice')
        for line in self.browse(cr, uid, ids, context=context): 
            obj_branch_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',line.branch_id.id)])
            if not obj_branch_id:
                raise osv.except_osv(_('Error!'),
                    _('Jurnal tidak ditemukan silahkan configurasi dulu: "%s" .') % \
                    (line.branch_id.name))
            
            obj_branch_config = self.pool.get('dym.branch.config').browse(cr,uid,obj_branch_id[0])
            if not (obj_branch_config.dealer_so_journal_dp_id.default_debit_account_id.id and obj_branch_config.dealer_so_journal_dp_id.default_credit_account_id.id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal JP belum lengkap!"))
            if line.dealer_sale_order_line:
                if line.finco_id:
                    invoice_customer = {
                        'name':line.name,
                        'origin': line.name,
                        'branch_id':line.branch_id.id,
                        'division':line.division,
                        'partner_id':line.partner_id.id,
                        'date_invoice':line.date_order,
                        'reference_type':'none',
                        'type': 'out_invoice',                                    
                        #'payment_term':val.payment_term,
                        'tipe': 'customer',
                        'journal_id': obj_branch_config.dealer_so_journal_dp_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_dp_id.default_debit_account_id.id
                    }
                    invoice_customer_line.append([0,False,{
                        'name': 'Customer JP',
                        'quantity': 1,
                        'origin': line.name,
                        'price_unit':line.customer_dp,
                        'account_id': obj_branch_config.dealer_so_journal_dp_id.default_credit_account_id.id
                    }])
                invoice_customer['invoice_line'] = invoice_customer_line
                
                invoice_dp_create = obj_inv.create(cr,uid,invoice_customer)
                workflow.trg_validate(uid, 'account.invoice', invoice_dp_create, 'invoice_open', cr)
        return invoice_dp_create
    
    def _get_status_inv(self,cr,uid,ids,origin):
        obj_inv = self.pool.get('account.invoice')
        
        obj = obj_inv.search(cr,uid,[
                                     ('origin','ilike',origin),
                                     ('type','=','out_invoice'),
                                     ('tipe','=','customer')
                                     ])
        if obj:
            invoice = obj_inv.browse(cr,uid,obj[0])
            if invoice.state == 'paid':
                return True
        return False
    
    def action_create_do2(self,cr,uid,ids,context=None):
        sales_obj = self.browse(cr,uid,ids)
        if sales_obj.picking_ids:
            return True
        elif self._get_status_inv(cr,uid,ids,sales_obj.name):
            self.action_create_picking(cr, uid, ids)
        elif sales_obj.is_cod:
            self.action_create_picking(cr, uid, ids)
            
        return True
    
    def action_create_do(self,cr,uid,ids,contex=None):
        do_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        quant_obj = self.pool.get('stock.quant')
        #location_cust_id = self.pool.get('stock.location')
        quants_lot = []
        sales_obj = self.browse(cr,uid,ids)
        picking_id = do_obj.search(cr,uid,[('origin','ilike',sales_obj.name)])
        if picking_id:
            return {
                'name': 'Picking Slip',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'current',
                'res_id': picking_id and picking_id[0] or False
            }
        if not (sales_obj.is_cod or sales_obj.is_pic) and self.check_customer_payment(cr, uid, ids) == False:
            raise osv.except_osv(_('Attention!'),_('Pelunasan unit belum dipenuhi!'))
            
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr,uid,[ ('model','=',sales_obj.__class__.__name__) ])
        obj_model_id_model = obj_model.browse(cr,uid,obj_model_id).id
        
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        
        location = self._get_default_location_delivery_sales(cr,uid,ids)
        transfer_header = {
            'branch_id': sales_obj.branch_id.id,
            'division': sales_obj.division,
            'origin': sales_obj.name,
            'move_type': 'direct',
            'partner_id': sales_obj.partner_id.id,
            'invoice_state': 'invoiced',
            'priority': '0',
            'min_date': tomorrow,
            'picking_type_id': location['picking_type_id'],
            'model_id': obj_model_id_model,
        }
        transfer_line = []
        barang_bonuses = {}
        extras = {}
        for lines in sales_obj['dealer_sale_order_line']:
            transfer_line.append([0,False,{
                'product_id': lines.product_id.id,
                'product_uom_qty': lines.product_qty,
                'name': lines.product_id.partner_ref,
                'location_id':lines.location_id.id,
                'invoice_state': 'invoiced',
                'product_uom': lines.product_id.uom_id.id,
                'restrict_lot_id': lines.lot_id.id,
                'origin': sales_obj.name,
                'location_dest_id':location['destination'],
                'undelivered_value': lines.force_cogs,
                'dealer_sale_order_line_id':lines.id,
                'branch_id': sales_obj.branch_id.id,
            }])
            quant_id = quant_obj.search(cr,uid,[('lot_id','=',lines.lot_id.id)])
            if quant_id:
                quants = quant_obj.browse(cr,uid,quant_id[0])
                quants_lot.append((quants,lines.product_qty))
            else:
                raise osv.except_osv(_('Attention!'),_('Tidak Ditemukan stok untuk no engine sales order!'))
            
            if lines.barang_bonus_line:
                for barang_bonus in lines.barang_bonus_line:
                    if not barang_bonuses.get(barang_bonus.product_subsidi_id.id,False):
                        barang_bonuses[barang_bonus.product_subsidi_id.id] = {}
                    barang_bonuses[barang_bonus.product_subsidi_id.id]['qty'] = barang_bonuses[barang_bonus.product_subsidi_id.id].get('qty',0) + barang_bonus.barang_qty
                    barang_bonuses[barang_bonus.product_subsidi_id.id]['price_barang'] = barang_bonuses[barang_bonus.product_subsidi_id.id].get('price_barang',0) + barang_bonus.price_barang
                    barang_bonuses[barang_bonus.product_subsidi_id.id]['line_id'] = lines.id

            if lines.product_id.categ_id.isParentName('Unit'):
                for x in lines.product_id.extras_line:
                    if not extras.get(x.product_id,False):
                        extras[x.product_id] = {}
                    extras[x.product_id]['product_qty'] = extras[x.product_id].get('product_qty',0)+x.quantity
                    ksu_location_id = self.pool.get('stock.location').search(cr, uid, [('branch_id', '=', sales_obj.branch_id.id),
                                                                                    ('name', '=', 'KSU')])
                    blocation = self.pool.get('stock.location').browse(cr, uid, ksu_location_id, )
                    extras[x.product_id]['location'] = blocation.id
                    # extras[x.product_id]['location'] = lines.location_id.id
                    extras[x.product_id]['line_id'] = lines.id
    
        ##TODO: append bonus to transfer_line
        for key, value in extras.items():
            transfer_line.append([0,False,{
                    'product_id':key.id,
                    'product_uom_qty':value.get('product_qty',0),
                    'name':key.partner_ref,
                    'location_id':value.get('location',False) or location['source'],
                    'invoice_state':'none',
                    'product_uom':key.uom_id.id,#key.uom_id,
                    'location_dest_id':location['destination'],
                    'dealer_sale_order_line_id':value.get('line_id',False),
                    'branch_id': sales_obj.branch_id.id,
                    'origin': sales_obj.name,
                }])

        ##TODO: append extras to transfer_line
        for key, value in barang_bonuses.items():
            product_id = self.pool.get('product.product').browse(cr,uid,key)
            transfer_line.append([0,False,{
                          'product_id': product_id.id,
                          'product_uom_qty': value.get('qty',0),
                          'name': product_id.partner_ref,
                          'location_id': location['source'],
                          'invoice_state': 'invoiced',
                          'product_uom': product_id.uom_id.id,#key.uom_id,
                          'location_dest_id': location['destination'],
                          'dealer_sale_order_line_id':value.get('line_id',False),
                          'branch_id': sales_obj.branch_id.id,
                          'origin': sales_obj.name,
                          'undelivered_value': value.get('price_barang',0),
                          }])

        #appaend move lines
        transfer_header['move_lines'] = transfer_line
        create_do = do_obj.create(cr,uid,transfer_header)
        if create_do:
            do_obj.action_confirm(cr, uid, [create_do])
            for pick in do_obj.browse(cr,uid,create_do):
                if pick.move_lines:
                    count_quants = 0
                    for move in pick.move_lines:
                        if move.state not in ('draft', 'cancel', 'done'):
                            if move.product_id.categ_id.isParentName('Unit'):
                                assign = move_obj.action_assign(cr,uid,move.id)
                                count_quants+=1
        
            
        return True
    
    def waktu_local(self,cr,uid,ids,context=None):
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(cr, uid, uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)        
        return start
    
    def update_serial_number(self,cr,uid,vals,lot_id):
        obj_lot = self.pool.get('stock.production.lot')
        update_lot = obj_lot.write(cr,uid,lot_id,vals)
        return True
    
    def action_view_invoice_cust(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        result['views'] = [(res and res[1] or False, 'form')]
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        obj = obj_inv.search(cr,uid,[
            ('origin','ilike',val.name),
            ('tipe','=','customer')
        ])
        result['res_id'] = obj[0] 
        return result
    
    def action_view_invoices(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        obj = obj_inv.search(cr,uid,[
            ('origin','ilike',val.name),
            ('type','=','out_invoice')
        ])
        if not obj:
            obj = [self.action_invoice_create(cr, uid, ids)]
        if len(obj)>0:
            result['domain'] = "[('id','in',["+','.join(map(str, obj))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = obj[0] 
        return result

        
    def action_view_invoice_finco(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        result['views'] = [(res and res[1] or False, 'form')]
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        obj = obj_inv.search(cr,uid,[
            ('origin','ilike',val.name),
            ('tipe','=','finco')
        ])        
        result['res_id'] = obj[0]   
        return result
    
    def action_view_do(self,cr,uid,ids,context=None):  
        val = self.browse(cr, uid, ids)
        obj_picking = self.pool.get('stock.picking')
        picking_id = obj_picking.search(cr,uid,[
            ('origin','ilike',val.name)
        ])        
        return {
            'name': 'Picking Slip',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': picking_id and picking_id[0] or False
        }
        
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Cannot delete a Sales Memo which is in state \'%s\'!') % (val.state,))
        if val.dealer_spk_id:
            self.pool.get('dealer.spk').write(cr,uid,val.dealer_spk_id.id,{'state':'progress','dealer_sale_order_id':False})
        if val.dealer_sale_order_line:
            for line in val.dealer_sale_order_line:
                update_lot = self.update_serial_number(cr,uid,{'state': 'stock','sale_order_reserved':False,'customer_reserved':False},line.lot_id.id)
        return super(dealer_sale_order, self).unlink(cr, uid, ids, context=context)
    
    def write(self,cr,uid,ids,vals,context=None):
        line_obj = self.pool.get('dealer.sale.order.line')
        if vals.get('partner_id',False):
            line_ids = line_obj.search(cr,uid,[('dealer_sale_order_line_id','=',ids[0])])
            for detail in line_obj.browse(cr,uid,line_ids):
                update_lot = self.update_serial_number(cr,uid,{'customer_reserved':vals['partner_id']},detail.lot_id.id)
        
        if vals.get('partner_komisi_id')==False:
            if self.browse(cr,uid,ids).dealer_sale_order_line:
                line_ids = line_obj.search(cr,uid,[('dealer_sale_order_line_id','=',ids[0])])
                update_hc = self.pool.get('dealer.sale.order.line').write(cr,uid,line_ids,{'hutang_komisi_id':False,'hutang_komisi_amount':0.0,'amount_hutang_komisi':0.0,'tipe_komisi':False})
        
        if vals.get('dealer_sale_order_line',False):
            header = self.read(cr,uid,ids,['partner_id'])
            for line in vals['dealer_sale_order_line']:
                if line[1] == False:
                    if line[2]['lot_id']:                    
                        update_lot = self.update_serial_number(cr,uid,{'state':'reserved','sale_order_reserved':ids[0],'customer_reserved':header[0]['partner_id'][0]},line[2]['lot_id'])
        
        return super(dealer_sale_order, self).write(cr, uid, ids, vals, context=context)
    
    def _get_branch_setting(self,cr,uid,branch_id,context=None):
        branch = self.pool.get('dym.branch')
        branch_obj = branch.browse(cr,uid,branch_id)
        return branch_obj
    
    def transferred(self, cr, uid, ids, *args):
        val = self.browse(cr, uid, ids)
        obj_picking = self.pool.get('stock.picking')          
        picking_id = obj_picking.search(cr,uid,[
            ('origin','ilike',val.name)
        ])       
        status_picking = obj_picking.read(cr,uid,picking_id,['state'])
        if status_picking[0]['state'] == 'done':
            return True         
        return False
    
    def check_customer_payment(self, cr, uid, ids, *args):
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        if val.finco_id and val.is_credit == True:
            if val.customer_dp <= 0:
                return True
            inv_id = obj_inv.search(cr,uid,[
                ('origin','ilike',val.name),
                ('partner_id','in',[val.partner_id.id,val.finco_id.id]),
                ('tipe','=','finco'),
                ('state','!=','cancel')
            ])
            inv_status = obj_inv.browse(cr,uid,inv_id)
            amount_dp = inv_status.amount_total
            if inv_status.amount_dp > 0:
                amount_dp = inv_status.amount_dp            
            for line in inv_status.move_id.line_id:
                if line.partner_id.id in [inv_status.partner_id.id or inv_status.qq_id.id] and line.debit == inv_status.amount_total and (line.reconcile_id or line.reconcile_partial_id) and line.amount_residual <= inv_status.amount_total - amount_dp:
                    return True
                elif line.account_id.id == inv_status.account_dp.id and line.reconcile_id and line.debit == amount_dp:
                    return True
        else:
            inv_id = obj_inv.search(cr,uid,[
                ('origin','ilike',val.name),
                ('partner_id','=',val.partner_id.id),
                ('tipe','=','customer'),
                ('state','!=','cancel')
            ])
            inv_status = obj_inv.browse(cr,uid,inv_id)
            if inv_status.state == 'paid' or inv_status.residual == 0:
                return True
        return False

    def paid(self, cr, uid, ids, *args):
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        
        if val.finco_id:
            inv_id = obj_inv.search(cr,uid,[
                ('origin','ilike',val.name),
                ('partner_id','in',[val.partner_id.id,val.finco_id.id]),
                ('tipe','=','finco')
            ])
        else:
            inv_id = obj_inv.search(cr,uid,[
                ('origin','ilike',val.name),
                ('partner_id','=',val.partner_id.id),
                ('tipe','=','customer')
            ])
        inv_status = obj_inv.read(cr,uid,inv_id,['state'])
        if inv_status[0]['state'] == 'paid':
            return True
        return False
    
    def _get_invoice_ids(self, cr, uid, ids, context=None):
        dso_id = self.browse(cr, uid, ids, context=context)
        obj_inv = self.pool.get('account.invoice')
        obj_model = self.pool.get('ir.model')
        id_model = obj_model.search(cr, uid, [('model','=','dealer.sale.order')])[0]
        ids_inv = obj_inv.search(cr, uid, [
            ('model_id','=',id_model),
            ('transaction_id','=',dso_id.id),
            ('state','!=','cancel')
            ])
        inv_ids = obj_inv.browse(cr, uid, ids_inv)
        return inv_ids

    def _get_ids_picking(self, cr, uid, ids, context=None):
        dso_id = self.browse(cr, uid, ids, context=context)
        obj_picking = self.pool.get('stock.picking')
        obj_model = self.pool.get('ir.model')
        id_model = obj_model.search(cr, uid, [('model','=','dealer.sale.order')])[0]
        ids_picking = obj_picking.search(cr, uid, [
            ('model_id','=',id_model),
            ('transaction_id','=',dso_id.id),
            ('state','!=','cancel')
            ])
        return ids_picking
    
    def reverse(self, cr, uid, ids, context=None):
        ids_picking = self._get_ids_picking(cr, uid, ids, context)
        ids_move = self.pool.get('stock.move').search(cr, uid, [
            ('picking_id','in',ids_picking),
            ('origin_returned_move_id','!=',False),
            ('state','!=','cancel')
            ])
        if ids_move :
            return True
        return False
        
    def action_paid(self, cr, uid, ids, *args):
        context = {}
        sale_order = self.browse(cr,uid,ids)
        if sale_order.finco_id and sale_order.is_credit == True and sale_order.customer_dp <= 0:
            invoice_id = self.action_invoice_create(cr, uid, ids)
        if not sale_order.is_cod:
            self.signal_workflow(cr, uid, ids, 'has_been_paid')
        tanda_jadi = sale_order.tanda_jadi
        customer_dp = sale_order.customer_dp
        total_harus_bayar = tanda_jadi + customer_dp
        for line in sale_order.dealer_sale_order_line:
            if line.is_bbn == 'Y':
                update_lot = self.update_serial_number(cr,uid,{'state':'paid'},line.lot_id.id)
            else:
                update_lot = self.update_serial_number(cr,uid,{'state':'paid_offtr'},line.lot_id.id)
        return True
    
    def dp_paid(self, cr, uid, ids, *args):
        val = self.browse(cr, uid, ids)
        if val.customer_dp <= 0:
            return True
        obj_inv = self.pool.get('account.invoice')
        inv_id = obj_inv.search(cr,uid,[
            ('origin','ilike',val.name),
            ('partner_id','in',[val.partner_id.id,val.finco_id.id]),
            ('tipe','=','finco')
        ])
        inv_status = obj_inv.browse(cr,uid,inv_id)
        amount_dp = inv_status.amount_total
        if inv_status.amount_dp > 0:
            amount_dp = inv_status.amount_dp
        for line in inv_status.move_id.line_id:
            if line.partner_id.id in [inv_status.partner_id.id or inv_status.qq_id.id] and line.debit == inv_status.amount_total and (line.reconcile_id or line.reconcile_partial_id) and line.amount_residual <= inv_status.amount_total - amount_dp:
                return True
            elif line.account_id.id == inv_status.account_dp.id and line.reconcile_id and line.debit == amount_dp:
                return True
        return False
    
    def credit(self,cr,uid,ids,*args):
        for order in self.browse(cr,uid,ids):
            if order.finco_id:
                return True
        return False

    def _get_default_location_delivery_sales(self,cr,uid,ids,context=None):
        default_location_id = {}
        obj_picking_type = self.pool.get('stock.picking.type')
        for val in self.browse(cr,uid,ids):
            picking_type_id = obj_picking_type.search(cr,uid,[
                ('branch_id','=',val.branch_id.id),
                ('code','=','outgoing')
            ])
            if picking_type_id:
                for pick_type in obj_picking_type.browse(cr,uid,picking_type_id[0]):
                    if not pick_type.default_location_dest_id.id :
                         raise osv.except_osv(('Perhatian !'), ("Location destination Belum di Setting"))
                    default_location_id.update({
                        'picking_type_id':pick_type.id,
                        'source':pick_type.default_location_src_id.id,
                        'destination': pick_type.default_location_dest_id.id,
                    })
            else:
               raise osv.except_osv(('Error !'), ('Tidak ditemukan default lokasi untuk penjualan di konfigurasi cabang \'%s\'!') % (val.branch_id.name,)) 
        return default_location_id
    
    def wkf_dealer_sale_order_done(self,cr,uid,ids):
        sale_order = self.browse(cr,uid,ids)
        if sale_order.dealer_spk_id:
            self.pool.get('dealer.spk').write(cr,uid,sale_order.dealer_spk_id.id,{'state':'done'})
        self.write(cr, uid, ids, {'state': 'done'})
        return True
    
    def validate_npwp(self, npwp=None):
        if not npwp:
            return False
        if len(npwp) != 20:
            return False
        if not npwp.replace('.','').replace('-','').isdigit():
            return False
        if not npwp[2:3]=='.':
            return False
        if not npwp[6:7]=='.':
            return False
        if not npwp[10:11]=='.':
            return False
        if not npwp[12:13]=='-':
            return False
        if not npwp[16:17]=='.':
            return False
        return True

    def partner_id_change(self,cr,uid,ids,partner_id,finco_id):
        value = {}
        warning = {}
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
        valid_npwp = self.validate_npwp(partner.npwp)
        value['pajak_generate'] = valid_npwp
        if not valid_npwp and partner.is_company:
            warning = {'title':'Perhatian !','message':'Mohon lengkapi nomor NPWP untuk customer %s.' % partner.name}

        if finco_id and partner_id:
            partner = self.pool.get('res.partner').browse(cr,uid,finco_id)
            if not partner.property_payment_term.id:
                return {'value':{'finco_id':False,'payment_term':False,'payment_term_dummy':False},'warning':{'title':'Perhatian !','message':'Tidak ditemukan default payment term finco !'}}
            else:
                value = {'payment_term':partner.property_payment_term.id,'payment_term_dummy':partner.property_payment_term.id}
                value['payable_receivable'] = partner.debit
                return {'value':value}
                  
        elif partner_id:
            partner = self.pool.get('res.partner').browse(cr,uid,partner_id) 
            if not partner.property_payment_term.id:
                return {'value':{'partner_id':False,'payment_term':False,'payment_term_dummy':False},'warning':{'title':'Perhatian !','message':'Tidak ditemukan default payment term customer !'}}
            else:
                value = {'payment_term':partner.property_payment_term.id,'payment_term_dummy':partner.property_payment_term.id}  
                value['payable_receivable'] = partner.debit
                return {'value':value}

        return {'warning':warning}
    
    def cod(self,cr,uid,ids):
        for sale_order in self.browse(cr,uid,ids):
            if sale_order.is_cod:
                return True
        return False
    
    def branch_change(self,cr,uid,ids,branch_id):
        value =  {}
        if branch_id:
            branch = self.pool.get('dym.branch').browse(cr,uid,branch_id)
            if branch.is_mandatory_spk:
                return {'value':{'branch_id':False},'warning':{'title':'Perhatian','message':'Tidak boleh create so langsung, harus dari pra-SO!'}}
            value['pricelist_id'] = branch.pricelist_unit_sales_id.id
        return {'value':value}
    
class dealer_sale_order_line(osv.osv):
    _name = 'dealer.sale.order.line'
    
    def discount_line_change(self, cr, uid, ids, discount_line, discount_po, finco_id, price_unit, uang_muka, diskon_dp_2, tanda_jadi2):  
        value = {}

        if not (6, 0, []) in discount_line:
            return {'value':value}

        if finco_id:
            lines = self.resolve_2many_commands(cr, uid, 'discount_line', discount_line, ['include_invoice','discount_pelanggan','tipe_diskon'])
            diskon_dp = discount_po
            diskon_dp_2 = 0
            for disc in lines:
                if disc['include_invoice'] == True:
                    diskon_dp += disc['discount_pelanggan'] if disc['tipe_diskon'] != 'percentage' else (price_unit*disc['discount_pelanggan']/100)
                else:
                    diskon_dp_2 += disc['discount_pelanggan'] if disc['tipe_diskon'] != 'percentage' else (price_unit*disc['discount_pelanggan']/100)
            # customer_dp = uang_muka - diskon_dp - diskon_dp_2 - tanda_jadi2 
            customer_dp = uang_muka - diskon_dp - diskon_dp_2
            value['diskon_dp'] = diskon_dp
            value['diskon_dp_2'] = diskon_dp_2
            value['customer_dp'] = customer_dp
        return {'value':value}

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        res = {}
        disc_total = 0
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            for detail in line.discount_line:
                if detail.include_invoice == False:
                    continue
                if detail.tipe_diskon == 'percentage':
                    disc_total += (line.price_unit * detail.discount_pelanggan / 100)
                else:
                    disc_total += detail.discount_pelanggan 
            price = line.price_unit - (disc_total+line.discount_po)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_qty, line.product_id)
            res[line.id]=taxes['total']
        return res

    def _amount_dp(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            dp_nett = line.uang_muka - line.diskon_dp - line.diskon_dp_2           
            # dp_nett = line.uang_muka - line.diskon_dp - line.diskon_dp_2 - line.tanda_jadi2           
            res[line.id] = dp_nett
        return res
    
    def _amount_total_discount(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for discount in self.browse(cr, uid, ids, context=context):
            res[discount.id] = {
                'discount_total': 0.0,
            }
            val = discount.discount_po
            for line in discount.discount_line:
                if line.include_invoice == False:
                    continue
                if line.tipe_diskon == 'percentage':
                    val += (discount.price_unit * line.discount_pelanggan / 100)
                else:
                    val += line.discount_pelanggan 
            res[discount.id]['discount_total'] = val
           
        return res

    def partner_stnk_id_change(self, cr, uid, ids, partner_stnk_id):
        if not partner_stnk_id:
            return {'value':{'city_id':False}}
        partner_stnk_id = self.pool.get('res.partner').browse(cr,uid,partner_stnk_id)
        if partner_stnk_id:
            if partner_stnk_id.sama == True:
                return {'value':{'city_id':partner_stnk_id.city_id}}
            else:
                return {'value':{'city_id':partner_stnk_id.city_tab_id}}
        return {'value':{'city_id':False}}
    
    def biro_jasa_id_change(self, cr, uid, ids, product_id, branch_id, plat, biro_jasa_id, city_id):
        result = {}
        return { 'value' : result}
    
    def lot_id_change(self, cr, uid, ids, lot_id):
        result = {}
        if not lot_id:
            return {'value':{'price_unit_beli':False}}
        lot_obj = self.pool.get('stock.production.lot').browse(cr,uid,lot_id)
        if lot_obj:
            result.update({'price_unit_beli': lot_obj.hpp})
            result['chassis_no'] = lot_obj.chassis_no
        return {'value':result}
    
    def _get_discount(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('dealer.sale.order.line.discount.line').browse(cr, uid, ids, context=context):
            result[line.dealer_sale_order_line_discount_line_id.id] = True
        return result.keys()
    
    def _get_branch(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for dso in self.browse(cr, uid, ids):
            res[dso.id] = {
                'branch_dummy': 0,
                'finco_dummy': 0,
                'komisi_dummy': 0,
                'division_dummy': '',
                'customer_dummy': 0,
            }
            for sale_order in self.pool.get('dealer.sale.order').browse(cr,uid,dso.dealer_sale_order_line_id.id):
                res[dso.id]['branch_dummy'] = sale_order.branch_id.id
                res[dso.id]['finco_dummy'] = sale_order.finco_id.id
                res[dso.id]['komisi_dummy'] = sale_order.partner_komisi_id.id
                res[dso.id]['division_dummy'] = sale_order.division
                res[dso.id]['customer_dummy'] = sale_order.partner_id.id
                
        return res
    
    def category_change(self, cr, uid, ids, categ_id,branch_id, finco_id,komisi_id,division,customer_id, template_id=False):
        dom = {}
        value = {}
        tampung = []
        value['product_id'] = False 
        if categ_id:
            categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,categ_id)
            dom['template_id']=[('categ_id','in',categ_ids),('sale_ok','=',True)]
            if template_id:
                dom['product_id']=[('product_tmpl_id','=',template_id),('categ_id','in',categ_ids),('sale_ok','=',True)]
                template = self.pool.get('product.template').browse(cr, uid, [template_id])
                if len(template.product_variant_ids) == 1:
                    value['product_id'] = template.product_variant_ids.id
            else:
                dom['product_id']=[('id','=',0)]
        value['branch_dummy'] = branch_id 
        value['finco_dummy'] = finco_id 
        value['komisi_dummy'] = komisi_id 
        value['division_dummy'] = division 
        value['customer_dummy'] = customer_id 
        return {'value':value,'domain':dom}
    
    def location_change(self, cr, uid, ids, location_id,product_id):
        obj_product_location = self.pool.get('product.product').browse(cr, uid, product_id)      
        dom = {}
        
        obj_stock2 = self.pool.get('stock.quant').search(cr, uid, [('location_id','=',location_id),('product_id','=',product_id),('reservation_id','=',False),('lot_id','!=',False)])
        if obj_stock2:
            lots = self.pool.get('stock.quant').read(cr, uid,obj_stock2,['lot_id'])
            if lots:
                dom['lot_id']=[('id','in',[x['lot_id'][0] for x in lots]),('state','=','stock')]
            else:
                return {'value':{'product_id':False,'location_id':False,'price_unit':0},'warning':{'title':'Perhatian !','message':'Stock tidak ditemukan'}}
        else :
            dom['lot_id']=[('id','in',[]),('state','=','stock')] 

        return  {'domain': dom}
    
    def onchange_price(self,cr,uid,ids,price_unit):
        value = {'price_unit_show':0}
        if price_unit:
            value.update({'price_unit_show':price_unit})       
        return {'value':value}

    def _get_price_unit(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.read(cr, uid, ids, ['price_unit']):
            price_unit_show = price['price_unit']
            res[price['id']] = price_unit_show
        return res
    
    def onchange_price_bbn(self,cr,uid,ids,price_bbn):
        value = {'price_bbn_show':0}
        if price_bbn:
            value.update({'price_bbn_show':price_bbn})       
        return {'value':value}
    
    def onchange_hutang_komisi(self,cr,uid,ids,product_id,hutang_komisi,partner_komisi_id):
        result = {'hutang_komisi_id':False,'hutang_komisi_amount': 0}
        
         
        if not hutang_komisi:
            return {'value':{'hutang_komisi_id':False,'hutang_komisi_amount': 0,'amount_hutang_komisi': 0}}
        
        if not product_id:
#             return result
            return {'value':{'hutang_komisi_id':False,'hutang_komisi_amount': 0,'amount_hutang_komisi': 0,},
                    'warning':{'title':'Perhatian !','message':'Pilih produk terlebih dahulu'}}
        else:
            product_template_obj = self.pool.get('product.product').browse(cr,uid,product_id)
            product_template_id = product_template_obj.product_tmpl_id.id
        
        if not partner_komisi_id:
            return {'value':{'hutang_komisi_id':False,'hutang_komisi_amount': 0,'amount_hutang_komisi': 0,},
                    'warning':{'title':'Perhatian !','message':'Hutang Komisi jika partner komisi terisi'}}
        
        hc = self.pool.get('dym.hutang.komisi').browse(cr, uid, hutang_komisi)

        if hc.date_start > datetime.now().strftime('%Y-%m-%d') or hc.date_end < datetime.now().strftime('%Y-%m-%d'):# or not ps.active:
            return {'value':{'hutang_komisi_id':False,'hutang_komisi_amount': 0,'amount_hutang_komisi': 0,},
                    'warning':{'title':'Perhatian !','message':'Hutang komisi sudah tidak aktif.'}}
            
        if not hc.hutang_komisi_line:
            return {'value':{'hutang_komisi_id':False,'hutang_komisi_amount': 0,'amount_hutang_komisi': 0},
                    'warning':{'title':'Perhatian !','message':'Detail hutang komisi tidak ditemukan.'}}
        
        hc_line_id = hc.hutang_komisi_line      
       
        hc_line_obj = self.pool.get('dym.hutang.komisi.line').search(cr, uid,[('product_template_id','=',product_template_id),('hutang_komisi_id','=',hutang_komisi)])
        
        if not hc_line_obj:
            return {'value':{'hutang_komisi_id':False,'hutang_komisi_amount': 0,'amount_hutang_komisi': 0},
                    'warning':{'title':'Perhatian !','message':'Detail hutang komisi tidak ditemukan.'}}
        else:
            hc_obj = self.pool.get('dym.hutang.komisi.line').browse(cr, uid,hc_line_obj)
            
            result.update({
                           'hutang_komisi_id': hutang_komisi,
                           'tipe_komisi': hc.tipe_komisi,
                           'hutang_komisi_amount': hc_obj.amount,
                           'amount_hutang_komisi': hc_obj.amount,
                           })
        return {'value':result}
    
    def onchange_amount_hc(self,cr,uid,ids,product_id,hutang_komisi,tipe_komisi,amount_hutang_komisi,partner_komisi_id,hutang_komisi_amount):
        if not hutang_komisi and not product_id:
            return {'value':{'hutang_komisi_id':False,'amount_hutang_komisi': 0}}
        if tipe_komisi == 'fix':
            return {'value':{'amount_hutang_komisi':hutang_komisi_amount}}
        elif tipe_komisi=='non':
            if amount_hutang_komisi < 0 or amount_hutang_komisi > hutang_komisi_amount:
                return {'value':{'amount_hutang_komisi':hutang_komisi_amount},'warning':{'title':'Perhatian !','message':'Amount Hutang Komisi Tidak Boleh nilai negatif atau lebih dari master hutang komisi.'}}

        return True
        

    def _get_price_bbn(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.read(cr, uid, ids, ['price_bbn']):
            price_bbn_show = price['price_bbn']
            res[price['id']] = price_bbn_show
        return res

    def _get_tanda_jadi2(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.read(cr, uid, ids, ['tanda_jadi']):
            tanda_jadi_show = price['tanda_jadi']
            res[price['id']] = tanda_jadi_show
        return res

    def _get_diskon_dp(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.read(cr, uid, ids, ['diskon_dp']):
            diskon_dp_show = price['diskon_dp']
            res[price['id']] = diskon_dp_show
        return res
    
    def _get_order_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = True
        return result.keys()

    def _get_harga_bbn_detail(self, cr, uid, ids, birojasa_id, plat, city_id, product_template_id):   
        if not birojasa_id:
            return False

        pricelist_harga_bbn = self.pool.get('dym.harga.bbn.line').search(cr,uid,[
                ('partner_id','=',birojasa_id),
                ('tipe_plat','=',plat),
                ('active','=',True),
                ('start_date','<=',datetime.now().strftime('%Y-%m-%d')),
                ('end_date','>=',datetime.now().strftime('%Y-%m-%d')),
            ])

        if not pricelist_harga_bbn:
            return False

        for pricelist_bbn in pricelist_harga_bbn:
            bbn_detail = self.pool.get('dym.harga.bbn.line.detail').search(cr,uid,[
                    ('harga_bbn_line_id','=',pricelist_bbn),
                    ('product_template_id','=',product_template_id),
                    ('city_id','=',city_id)
                ])
            if bbn_detail:
                return self.pool.get('dym.harga.bbn.line.detail').browse(cr,uid,bbn_detail)

        return False
   
    def _get_insentif_finco_value(self, cr, uid, ids, finco_id, branch_id):
        if not finco_id or not branch_id:
            return 0
        pricelist_incentives = self.pool.get('dym.incentive.finco.line').search(cr,uid,[
                ('partner_id','=',finco_id),
                ('active','=',True),
                ('start_date','<=',datetime.now().strftime('%Y-%m-%d')),
                ('end_date','>=',datetime.now().strftime('%Y-%m-%d')),
            ])
        if not pricelist_incentives:
            return 0

        incentive_value = self.pool.get('dym.incentive.finco.line.detail').search(cr, uid,[
                ('incentive_finco_line_id','=',pricelist_incentives[0]),
                ('branch_id','=',branch_id),
            ])
        
        if incentive_value:
            incentive = self.pool.get('dym.incentive.finco.line.detail').browse(cr,uid,incentive_value[0])
            return incentive['incentive']
        return 0
    
    def _get_insentif_finco(self,cr,uid,ids,finco_id,branch_id):
        return {'value': {'insentif_finco':_get_insentif_finco_value(cr,uid,ids,finco_id,branch_id)}}

    def _get_chassis_no(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for dsm in self.browse(cr, uid, ids):
            res[dsm.id] = dsm.lot_id.chassis_no
        return res
    
    _columns = {
        'dealer_sale_order_line_id': fields.many2one('dealer.sale.order','Sales Memo Line',ondelete='cascade'),
        'partner_id': fields.related('dealer_sale_order_line_id', 'partner_id', relation='res.partner', type='many2one', string='Customer', store=True, readonly=True),
        'categ_id':fields.selection([('Unit','Unit')],'Category',required=True),
        'template_id':fields.many2one('product.template', 'Tipe'),
        'product_id': fields.many2one('product.product','Produk',required=True,domain="[('sale_ok','=',True)]"),
        'price_unit': fields.float(required=True,string='Unit Price'),
        'price_unit_beli': fields.float(string='Unit Price Beli'),
        'price_unit_show': fields.function(_get_price_unit,string='Unit Price'),
        'product_qty': fields.integer('Qty',required=True),
        'location_id': fields.many2one('stock.location','Location',domain=[('location_id','=','dealer.sale.order.branch_id')],required=True),
        'lot_id': fields.many2one('stock.production.lot','No. Engine',required=True),
        'chassis_no': fields.function(_get_chassis_no, string='Chassis Number', type='char', readonly=True),
        'is_bbn': fields.selection([('Y','Y'),('T','T')],'BBN',required=True),
        'plat': fields.selection([('H','H'),('M','M')],'Plat'),
        'partner_stnk_id': fields.many2one('res.partner','Nama STNK',domain=[('customer','=',True)]),
        'city_id': fields.many2one('dym.city','City'),
        'biro_jasa_id': fields.many2one('res.partner','Biro Jasa',domain=[('biro_jasa','=',True)]),
        'price_bbn': fields.float('Price BBN',),
        'price_bbn_show': fields.function(_get_price_bbn,string='Price BBN'),
        'tax_id': fields.many2many('account.tax', 'dealer_sale_order_tax', 'dealer_sale_order_line_id', 'tax_id', 'Taxes'),                    
        'tanda_jadi': fields.float('Tanda Jadi'),
        'tanda_jadi2': fields.float('Tanda Jadi'),
        'tanda_jadi2_show': fields.function(_get_tanda_jadi2,string='Tanda Jadi'),
        'uang_muka': fields.float('Jaminan Pembelian PO'),
        'diskon_dp': fields.float('Diskon JP 1', digits_compute=dp.get_precision('Account')),
        'diskon_dp_2': fields.float('Diskon JP 2', digits_compute=dp.get_precision('Account')),
        'diskon_dp_2_copy':fields.related('diskon_dp_2', type='float', string='Diskon JP 2',readonly=True),
        'diskon_dp_show': fields.function(_get_diskon_dp,string='Diskon JP 1'),
        'customer_dp': fields.function(_amount_dp, digits_compute=dp.get_precision('Account'), type='float', string='JP Nett'),
        'discount_po':fields.float('Potongan Pelanggan'),
        'discount_line': fields.one2many('dealer.sale.order.line.discount.line','dealer_sale_order_line_discount_line_id','Discount Line',),
        'discount_total': fields.function(_amount_total_discount, string='Disc Total', digits_compute= dp.get_precision('Account'),
            store={
                'dealer.sale.order.line': (lambda self, cr, uid, ids, c={}: ids, ['price_unit','discount_line','discount_po'], 10),
                'dealer.sale.order.line.discount.line': (_get_discount, ['discount'], 10),
            }, multi='sums', help="The total Discount."),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account'),
            store = {
               'dealer.sale.order.line': (lambda self, cr, uid, ids, c={}: ids, ['price_unit','discount_line','discount_po'], 10),
                'dealer.sale.order.line.discount.line': (_get_discount, ['discount'], 10),
            }),
        'price_bbn_beli': fields.float(),
        'price_bbn_notice': fields.float(),
        'price_bbn_proses': fields.float(),
        'price_bbn_jasa': fields.float(),
        'price_bbn_jasa_area': fields.float(),
        'price_bbn_fee_pusat': fields.float(), 
        'insentif_finco': fields.float(),
        'finco_tgl_po': fields.date('Tanggal PO'),
        'finco_no_po': fields.char('No. PO'),
        'finco_tenor': fields.integer('Tenor'),
        'barang_bonus_line': fields.one2many('dealer.sale.order.line.brgbonus.line','dealer_sale_order_line_brgbonus_line_id', 'Barang Bonus Line'),
        'customer_deposit_ids': fields.one2many('account.voucher', 'dso_id', string='Voucher CDE',required=False),
        'customer_deposit_total': fields.float(string='Total CDE'),
        'cicilan': fields.integer('Cicilan'),
        'hutang_komisi_id':fields.many2one('dym.hutang.komisi','Hutang Komisi'),
        'hutang_komisi_amount':fields.float('Hutang Komisi Amount (from master data)'),
        'amount_hutang_komisi': fields.float('Amount'),
        'tipe_komisi':fields.char('Tipe Komisi'),
        'branch_dummy': fields.function(_get_branch,type='integer',multi=True),
        'finco_dummy': fields.function(_get_branch, type='integer',multi=True),
        'komisi_dummy': fields.function(_get_branch, type='integer',multi=True),
        'division_dummy': fields.function(_get_branch,type='char',multi=True),
        'customer_dummy': fields.function(_get_branch,type='integer',multi=True),
        'force_cogs': fields.float()
    }

    _defaults = {
        'product_qty' : 1,
        'is_bbn': 'Y',
        'categ_id':'Unit',
        'price_bbn_beli': 0,
        'insentif_finco':0
    }
    
    _sql_constraints = [('lot_id_unique', 'unique(dealer_sale_order_line_id,lot_id)', 'No Engine sudah pernah diinput!')]
    

    def onchange_discount_pelanggan(self, cr, uid, ids, diskon_dp, context=None):
        print "diskon_dp===========>",diskon_dp
        return {'value':{'diskon_dp':diskon_dp}}

    def unlink(self, cr, uid, ids, context=None):
        header_obj = self.pool.get('dealer.sale.order')
        for val in self.browse(cr, uid, ids, context={}):
            
            header = header_obj.browse(cr,uid,val.dealer_sale_order_line_id.id)
            for data in header:            
                if data.state != 'draft':
                    raise osv.except_osv(('Invalid action !'), ('Cannot delete a Sales Memo Line which is in state \'%s\'!') % (data.state,))
            update_lot = header_obj.update_serial_number(cr,uid,{'state': 'stock','sale_order_reserved':False,'customer_reserved':False},val.lot_id.id)
        return super(dealer_sale_order_line, self).unlink(cr, uid, ids, context=context) 
    
    def write(self,cr,uid,ids,vals,context=None):
        header_obj = self.pool.get('dealer.sale.order')      
        sale_order_id = self.read(cr,uid,ids[0],['dealer_sale_order_line_id'])
        header_id = sale_order_id['dealer_sale_order_line_id'][0]
        tanda_jadi = float(vals.get('tanda_jadi',0.0))
        tanda_jadi2 = float(vals.get('tanda_jadi2',0.0))
        customer_deposit_total = float(vals.get('customer_deposit_total',False))

        if tanda_jadi and customer_deposit_total:
            if customer_deposit_total != tanda_jadi:
                raise osv.except_osv(('Perhatian !'), ("Total Tanda Jadi tidak sama dengan Total Voucher CDE!"))

        if tanda_jadi and not customer_deposit_total:
            data = self.read(cr,uid,ids,['customer_deposit_total'])
            customer_deposit_total = data and float(data[0]['customer_deposit_total']) or 0.0
            if customer_deposit_total != tanda_jadi:
                raise osv.except_osv(('Perhatian !'), ("Total Tanda Jadi tidak sama dengan Total Voucher CDE!"))

        if not tanda_jadi and customer_deposit_total:
            data = self.read(cr,uid,ids,['tanda_jadi'])
            tanda_jadi = data and float(data[0]['tanda_jadi']) or 0.0
            if customer_deposit_total != tanda_jadi:
                raise osv.except_osv(('Perhatian !'), ("Total Tanda Jadi tidak sama dengan Total Voucher CDE!"))

        if vals.get('lot_id',False):    
            lot_lawas = self.read(cr,uid,ids[0],['lot_id'])
            lot_lawas_id =  lot_lawas['lot_id'][0]
            update_lot = header_obj.update_serial_number(cr,uid,{'state':'stock','sale_order_reserved':False,'customer_reserved':False},lot_lawas_id)
            for header in header_obj.browse(cr,uid,header_id):
                update_lot = header_obj.update_serial_number(cr,uid,{'state':'reserved','sale_order_reserved':header_id,'customer_reserved':header.partner_id.id},vals['lot_id'])
        
        if vals.get('is_bbn',False):   
            for header in header_obj.browse(cr,uid,header_id):
                if vals['is_bbn']=='T' and header.finco_id:
                    raise osv.except_osv(('Perhatian !'), ("Penjualan credit harus  menggunakan BBN!"))
                
                elif vals['is_bbn']=='T' and not header.finco_id:
                    self.write(cr,uid,ids,{'partner_stnk_id':False,'plat':False,'biro_jasa_id':False,'price_bbn':0.0})

        save_change = super(dealer_sale_order_line, self).write(cr, uid, ids, vals, context=context)
        return save_change

    def onchange_customer_deposit(self,cr,uid,ids,customer_deposit_ids,uang_muka,diskon_dp,diskon_dp_2,context=None):
        if not context:
            context = {}
        result = {}

        cde_ids = []
        if customer_deposit_ids:
            v1,v2,cde_ids = customer_deposit_ids[0]

        customer_deposits = self.pool.get('account.voucher').browse(cr, uid, cde_ids, context=context)
        total_cde = 0.0
        for cde in customer_deposits:
            total_cde += cde.paid_amount
        customer_dp = uang_muka - diskon_dp - diskon_dp_2
        result.update({
            'value':{
                'customer_deposit_total':total_cde,
                'customer_dp': customer_dp,
                'tanda_jadi2': total_cde,
                'tanda_jadi2_show': total_cde,
            }
        })
        return result


    def onchange_uang_muka(self,cr,uid,ids,uang_muka,finco_id,tanda_jadi,discount_line,discount_po,price_unit,diskon_dp,diskon_dp_2,tanda_jadi2):
        result = {}
        if uang_muka < 0:
            result = {'value':{'uang_muka':0},'warning':{'title':'Perhatian !','message':'Tidak boleh memasukkan nilai negatif!'}}
        if not finco_id and uang_muka > 0:
            result = {'value':{'uang_muka':0},'warning':{'title':'Perhatian !','message':'Jaminan Pembelian hanya diisi untuk penjualan kredit!'}}
        customer_dp = uang_muka - diskon_dp - diskon_dp_2 
        if not 'value' in result:
            result.update({'value':{}})
        result['value'].update({'customer_dp':customer_dp})
        return result

    def onchange_diskon_dp(self,cr,uid,ids,diskon_dp,finco_id=None,discount_line=None,discount_po=None,price_unit=None,uang_muka=None,tanda_jadi2=None):
        result = {}
        if diskon_dp < 0:
            result = {'value':{'diskon_dp':0},'warning':{'title':'Perhatian !','message':'Tidak boleh memasukkan nilai negatif!'}}
        if not finco_id and diskon_dp > 0:
            result = {'value':{'diskon_dp':0},'warning':{'title':'Perhatian !','message':'Diskon JP 1 hanya diisi untuk penjualan kredit!'}}
        res = self.onchange_discount_po(cr, uid, ids, discount_po, discount_line, finco_id, price_unit,uang_muka,tanda_jadi2)
        if diskon_dp != res['value'].get('diskon_dp',0) and not result:
            result = {'value':{'diskon_dp':diskon_dp},'warning':{'title':'Perhatian !','message':'Diskon JP 1 TIDAK SAMA DENGAN total potongan pelanggan tambah discount_program!'}}
        return result

    def onchange_diskon_dp_2(self,cr,uid,ids,diskon_dp_2,finco_id,discount_line,discount_po,price_unit,uang_muka,tanda_jadi2):
        result = {}
        if diskon_dp_2 < 0:
            result = {'value':{'diskon_dp_2':0},'warning':{'title':'Perhatian !','message':'Tidak boleh memasukkan nilai negatif!'}}
        if not finco_id and diskon_dp_2 > 0:
            result = {'value':{'diskon_dp_2':0},'warning':{'title':'Perhatian !','message':'Diskon JP 2 hanya diisi untuk penjualan kredit!'}}
        if not result:
            result = {'value':{'diskon_dp_2_copy':diskon_dp_2}}
        res = self.onchange_discount_po(cr, uid, ids, discount_po, discount_line, finco_id, price_unit,uang_muka,tanda_jadi2)
        if diskon_dp_2 != res['value'].get('diskon_dp_2',0) and not result:
            result = {'value':{'diskon_dp_2':diskon_dp_2},'warning':{'title':'Perhatian !','message':'Diskon JP 2 TIDAK SAMA DENGAN total discount_program!'}}
        
        diskon_dp = res['value'].get('diskon_dp',0.0)
        # customer_dp = uang_muka - diskon_dp - diskon_dp_2 - tanda_jadi2 
        customer_dp = uang_muka - diskon_dp - diskon_dp_2 
        result['value'].update({'customer_dp':customer_dp})

        return result

    def onchange_is_bbn(self,cr,uid,ids,is_bbn,branch_id):
        result = {}
        birojasa = []
        birojasa_srch = self.pool.get('dym.harga.birojasa').search(cr,uid,[
                                                                      ('branch_id','=',branch_id)
                                                                      ])
        if birojasa_srch :
            birojasa_brw = self.pool.get('dym.harga.birojasa').browse(cr,uid,birojasa_srch)
            for x in birojasa_brw :
                birojasa.append(x.birojasa_id.id)
                        
        if not is_bbn:
            result = {'value':{'is_bbn':'Y'},'domain':{'biro_jasa_id':[('id','in',birojasa)]}}
        if is_bbn == 'T':
            result = {'value':{'plat':False,'partner_stnk_id':False,'biro_jasa_id':False},'domain':{'biro_jasa_id':[('id','in',birojasa)]}}
        elif is_bbn == 'Y':
            result = {'value':{},'domain':{'biro_jasa_id':[('id','in',birojasa)]}}
        return result
    
    def onchange_plat(self,cr,uid,ids,plat,branch_id,product_id):
        if branch_id:
            branch = self.pool.get('dym.branch').browse(cr,uid,branch_id)
        else:
            return {'value':{'price_bbn':0},'warning':{'title':'Perhatian !','message':'Pilih Cabang Terlebih Dahulu.'}}
        result = {}

        if not product_id:            
            return {'value':{'price_bbn':0}}

        if not plat:
            return {'value':{'price_bbn':0}}
        elif plat=='H':
            if not branch.pricelist_bbn_hitam_id:
                return {'value':{'price_bbn':0},'warning':{'title':'Perhatian !','message':'Data Pricelist tidak ditemukan, silahkan konfigurasi data cabang dulu.'}}
            else :
                pricelist = branch.pricelist_bbn_hitam_id.id
        else:
            if not branch.pricelist_bbn_merah_id:
                return {'value':{'price_bbn':0},'warning':{'title':'Perhatian !','message':'Data Pricelist tidak ditemukan, silahkan konfigurasi data cabang dulu.'}}
            else :
                pricelist = branch.pricelist_bbn_merah_id.id
        price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], product_id, 1,0)[pricelist]
        if price is False:
            return {'value':{'price_bbn':0},'warning':{'title':'Perhatian !','message':'Data Pricelist BBN tidak ditemukan untuk produk ini, silahkan konfigurasi data cabang dulu.'}}
        else:
            result = {'value':{'price_bbn':price}}
        return result

    def onchange_tanda_jadi(self,cr,uid,ids,tanda_jadi,context=None):
        if not context:
            context = {}
        result = {}
        if tanda_jadi < 0:
            result = {'value':{'tanda_jadi':0},'warning':{'title':'Perhatian !','message':'Tidak boleh memasukkan nilai negatif!'}}
        return result

    def onchange_discount_po(self,cr,uid,ids,discount_po,discount_line,finco_id,price_unit,uang_muka,tanda_jadi2):
        value = {}
        warning = {}
        diskon_dp = discount_po
        diskon_dp_2 = 0
        if discount_po < 0:
            diskon_dp = 0
            value['discount_po'] = 0
            warning['title'] = 'Perhatian !'
            warning['message'] = 'Tidak boleh memasukkan nilai negatif!'
        if finco_id:
            lines = self.resolve_2many_commands(cr, uid, 'discount_line', discount_line, ['include_invoice','discount_pelanggan','tipe_diskon'])
            for disc in lines:
                if disc['include_invoice'] == True:
                    diskon_dp += disc['discount_pelanggan'] if disc['tipe_diskon'] != 'percentage' else (price_unit*disc['discount_pelanggan']/100)
                else:
                    diskon_dp_2 += disc['discount_pelanggan'] if disc['tipe_diskon'] != 'percentage' else (price_unit*disc['discount_pelanggan']/100)

            customer_dp = uang_muka - diskon_dp - diskon_dp_2 

            value['diskon_dp'] = diskon_dp
            value['diskon_dp_2'] = diskon_dp_2
            value['customer_dp'] = customer_dp

        return {'value':value,'warning':warning}

class dealer_sale_order_discount_line(osv.osv):
    _name = 'dealer.sale.order.line.discount.line'       

    _columns = {
        'dealer_sale_order_line_discount_line_id': fields.many2one('dealer.sale.order.line',ondelete='cascade'),
        'sale_order_line_discount_line_id': fields.many2one('sale.order.line',ondelete='cascade'),
        'program_subsidi': fields.many2one('dym.program.subsidi','Program Subsidi',required=True),
        'discount': fields.float('Total Subsidi',required=True),
        'discount_copy':fields.related('discount', type='float', string='Total Subsidi',readonly=True),
        'discount_pelanggan': fields.float('Discount',required=True),
        'tipe_subsidi': fields.char(),
        'include_invoice': fields.boolean('Discount include di invoice', help="jika dicentang maka diskon subsidi akan dimasukkan ke invoice dan di jurnal sebagai diskon quotation"),
        'include_invoice_copy':fields.related('include_invoice', type='boolean', string='Discount include di invoice',readonly=True, help="jika dicentang maka diskon subsidi akan dimasukkan ke invoice dan di jurnal sebagai diskon quotation"),
        'ps_md':fields.float(),
        'ps_ahm':fields.float(),
        'ps_finco':fields.float(),
        'ps_dealer':fields.float(),
        'ps_others':fields.float(),
        'ps_md_copy':fields.related('ps_md', type='float', string='Diskon MD',readonly=True),
        'ps_ahm_copy':fields.related('ps_ahm', type='float', string='Diskon AHM',readonly=True),
        'ps_finco_copy':fields.related('ps_finco', type='float', string='Diskon Finco',readonly=True),
        'ps_dealer_copy':fields.related('ps_dealer', type='float', string='Diskon Dealer',readonly=True),
        'ps_others_copy':fields.related('ps_others', type='float', string='Diskon Others',readonly=True),
        'tipe_diskon':fields.selection([('amount','Amount'),('percentage','Percentage')], 'Tipe Diskon'),
        'tipe_diskon_copy':fields.related('tipe_diskon', type='selection', selection=[('amount','Amount'),('percentage','Percentage')], string='Tipe Diskon',readonly=True),
        'ps_persen':fields.float(),
    }

    _default = {
        'ps_md':0,
        'ps_ahm':0,
        'ps_finco':0,
        'ps_dealer':0,
        'ps_others':0,
        'tipe_potongan':'piu',
        'ps_persen':0,
        'include_invoice':True,
        'include_invoice_copy':True,
    }

    def write(self,cr,uid,ids,vals,context=None):
        save_change = super(dealer_sale_order_discount_line, self).write(cr, uid, ids, vals, context=context)
        header_obj = self.pool.get('dealer.sale.order.line.discount.line')
        header_id = self.read(cr,uid,ids[0], ['id'])['id']
        is_exclusive = []
        product = ''
        if header_obj.browse(cr,uid,header_id).dealer_sale_order_line_discount_line_id.id:
            order_id = header_obj.browse(cr,uid,header_id).dealer_sale_order_line_discount_line_id.id
            order_obj = self.pool.get('dealer.sale.order.line')
            product = header_obj.browse(cr,uid,header_id).dealer_sale_order_line_discount_line_id.product_id
        elif header_obj.browse(cr,uid,header_id).work_order_line_discount_line_id.id:
            order_id = header_obj.browse(cr,uid,header_id).work_order_line_discount_line_id.id
            order_obj = self.pool.get('dym.work.order.line')
            product = header_obj.browse(cr,uid,header_id).work_order_line_discount_line_id.product_id
        elif header_obj.browse(cr,uid,header_id).sale_order_line_discount_line_id.id:
            order_id = header_obj.browse(cr,uid,header_id).sale_order_line_discount_line_id.id
            order_obj = self.pool.get('sale.order.line')
            product = header_obj.browse(cr,uid,header_id).sale_order_line_discount_line_id.product_id

        for line in order_obj.browse(cr,uid,order_id).discount_line:
            if line.program_subsidi.is_exclusive == 1:
                is_exclusive.append(line.program_subsidi.name)

        if is_exclusive and len(order_obj.browse(cr,uid,order_id).discount_line) > 1:
            warn_exclusive = ''
            for prog_name in is_exclusive:
                warn_exclusive += '\n - ' + prog_name

            product_name = product.name
            if product.attribute_value_ids:
                product_name = product_name + ' ('
            for attribute in product.attribute_value_ids:
                product_name += attribute.name + ', '
            if product.attribute_value_ids:
                product_name = product_name[:-2]
                product_name = product_name + ')'

            raise osv.except_osv(('Perhatian !'), ('Program exclusive tidak bisa digabungkan dengan program lain \n program exclusive yang terdaftar: ' + warn_exclusive + '\n\n Product: ' + product_name))

        return save_change
    
    def create(self,cr,uid,vals,context=None):    
        dealer_sales_order_line_discount_line = super(dealer_sale_order_discount_line, self).create(cr, uid, vals, context=context)
        
        header_obj = self.pool.get('dealer.sale.order.line.discount.line')
        is_exclusive = []
        product = ''
        if header_obj.browse(cr,uid,dealer_sales_order_line_discount_line).dealer_sale_order_line_discount_line_id.id:
            order_id = header_obj.browse(cr,uid,dealer_sales_order_line_discount_line).dealer_sale_order_line_discount_line_id.id
            order_obj = self.pool.get('dealer.sale.order.line')
            product = header_obj.browse(cr,uid,dealer_sales_order_line_discount_line).dealer_sale_order_line_discount_line_id.product_id
        elif header_obj.browse(cr,uid,dealer_sales_order_line_discount_line).work_order_line_discount_line_id.id:
            order_id = header_obj.browse(cr,uid,dealer_sales_order_line_discount_line).work_order_line_discount_line_id.id
            order_obj = self.pool.get('dym.work.order.line')
            product = header_obj.browse(cr,uid,dealer_sales_order_line_discount_line).work_order_line_discount_line_id.product_id
        elif header_obj.browse(cr,uid,dealer_sales_order_line_discount_line).sale_order_line_discount_line_id.id:
            order_id = header_obj.browse(cr,uid,dealer_sales_order_line_discount_line).sale_order_line_discount_line_id.id
            order_obj = self.pool.get('sale.order.line')
            product = header_obj.browse(cr,uid,dealer_sales_order_line_discount_line).sale_order_line_discount_line_id.product_id

        for line in order_obj.browse(cr,uid,order_id).discount_line:
            if line.program_subsidi.is_exclusive == 1:
                is_exclusive.append(line.program_subsidi.name)

        if is_exclusive and len(order_obj.browse(cr,uid,order_id).discount_line) > 1:
            warn_exclusive = ''
            for prog_name in is_exclusive:
                warn_exclusive += '\n - ' + prog_name

            product_name = product.name
            if product.attribute_value_ids:
                product_name = product_name + ' ('
            for attribute in product.attribute_value_ids:
                product_name += attribute.name + ', '
            if product.attribute_value_ids:
                product_name = product_name[:-2]
                product_name = product_name + ')'

            raise osv.except_osv(('Perhatian !'), ('Program exclusive tidak bisa digabungkan dengan program lain \n program exclusive yang terdaftar: ' + warn_exclusive + '\n\n Product: ' + product_name))
        
        return dealer_sales_order_line_discount_line

    def program_subsidi_change(self, cr, uid, ids, product_id, program_subsidi, uang_muka, finco_dummy, branch_dummy, division_dummy, sale_order_form=False, member=False, finco_tenor=None, context=None):
        result = {}
        domain = {}
        if not product_id:
            raise osv.except_osv(('Perhatian !'), ("Pilih Produk Terlebih Dahulu"))
        else:
            product_template_obj = self.pool.get('product.product').browse(cr,uid,product_id)

        is_member_only = ''
        is_member_only2 = []
        if not member:
            raise osv.except_osv(('Perhatian !'), ("Pilih Customer Terlebih Dahulu"))
        else:
            customer_obj = self.pool.get('res.partner').browse(cr,uid,member)
            if not customer_obj.member:
                is_member_only = ",('is_member_only','=',False)"
                is_member_only2 = [('is_member_only','=',False)]
        is_program_depo = False
        if sale_order_form == True and division_dummy == 'Sparepart':
            is_program_depo = True
        if finco_dummy==0:
            finco_dummy = False
        ps_domain = [
            ('product_ids','=',product_id),
            ('area_id.branch_ids','in',branch_dummy),
            ('division','=',division_dummy),
            ('date_end','>=',datetime.now().strftime('%Y-%m-%d')),
            ('date_start','<=',datetime.now().strftime('%Y-%m-%d')),
            ('state','=','approved'),
            ('active','=',True),
            ('instansi_id','=',finco_dummy),
            ('is_program_depo','=',is_program_depo)
        ] + is_member_only2
        ps_domain1 = ps_domain
        if finco_tenor:
            ps_domain1 = ps_domain + [('tenor_start','<=',finco_tenor),('tenor_end','>=',finco_tenor)]
        program_subsidi_ids1 = self.pool.get('dym.program.subsidi').search(cr, uid, ps_domain1, order='tenor')
        ps_domain2 = ps_domain + [('tenor_start','<=',0),('tenor_end','>=',0)]
        program_subsidi_ids2 = self.pool.get('dym.program.subsidi').search(cr, uid, ps_domain2, order='tenor')
        program_subsidi_ids = list(set(program_subsidi_ids1 + program_subsidi_ids2))

        if finco_dummy>0:
            domain['program_subsidi'] = [('id','in',program_subsidi_ids)]
        else:
            domain = {'program_subsidi': "[('product_ids','=',"+str(product_id)+"),('area_id.branch_ids','in',"+str(branch_dummy)+"),('division','=','"+str(division_dummy)+"'),('date_end','>=','"+datetime.now().strftime('%Y-%m-%d')+"'),('date_start','<=','"+datetime.now().strftime('%Y-%m-%d')+"'),('state','=','approved'),('active','=',True),('instansi_id','=',False),('is_program_depo','=',"+str(is_program_depo)+")"+is_member_only+"]"}
        product_template_id = product_template_obj.product_tmpl_id.id
        if not program_subsidi:
            return {'domain':domain,'value':{'discount': 0,'tipe_potongan':False,'discount_pelanggan':0,'ps_ahm':0,'ps_md':0,'ps_finco':0,'ps_dealer':0,'ps_others':0,'ps_persen':0,'tipe_diskon':False},}
        ps = self.pool.get('dym.program.subsidi').browse(cr, uid, program_subsidi)            
        if not ps.program_subsidi_line:
            return {'value':{'discount': 0,'tipe_potongan':False,'discount_pelanggan':0,'ps_ahm':0,'ps_md':0,'ps_finco':0,'ps_dealer':0,'ps_others':0,'ps_persen':0,'tipe_diskon':False},
                    'warning':{'title':'Perhatian !','message':'Detail program subsidi tidak ditemukan.'}}
        ps_line_id = ps.program_subsidi_line      
        ps_line_obj = self.pool.get('dym.program.subsidi.line').search(cr, uid,[('product_template_id','=',product_template_id),('program_subsidi_id','=',program_subsidi)])
        if not ps_line_obj:
            return {'value':{'discount': 0,'tipe_potongan':False,'discount_pelanggan':0,'ps_ahm':0,'ps_md':0,'ps_finco':0,'ps_dealer':0,'ps_others':0,'ps_persen':0,'tipe_diskon':False},
                    'warning':{'title':'Perhatian !','message':'Detail produk program subsidi tidak ditemukan.'}}
        else:
            dis_obj = self.pool.get('dym.program.subsidi.line').browse(cr, uid,ps_line_obj)
            #Pengecekan DP berdasarkan tipe dp di Program subsidi
            if dis_obj.tipe_dp == 'min':
                if uang_muka < dis_obj.amount_dp:
                    return {'value':{'discount': 0,'tipe_potongan':False,'discount_pelanggan':0,'ps_ahm':0,'ps_md':0,'ps_finco':0,'ps_dealer':0,'ps_others':0,'ps_persen':0,'tipe_diskon':False},
                            'warning':{'title':'Perhatian !','message':'JP konsumen tidak memenuhi nilai minimum untuk mendapatkan PS.'}}
            
            elif dis_obj.tipe_dp == 'max':
                if uang_muka > dis_obj.amount_dp:
                    return {'value':{'discount': 0,'tipe_potongan':False,'discount_pelanggan':0,'ps_ahm':0,'ps_md':0,'ps_finco':0,'ps_dealer':0,'ps_others':0,'ps_persen':0,'tipe_diskon':False},
                            'warning':{'title':'Perhatian !','message':'JP konsumen melebihi nilai maksimum untuk mendapatkan PS.'}}
            result.update({
                'discount': dis_obj.total_diskon,
                'discount_copy': dis_obj.total_diskon,
                'discount_pelanggan': dis_obj.total_diskon,
                'ps_ahm': dis_obj.diskon_ahm,
                'ps_md': dis_obj.diskon_md,
                'ps_finco':dis_obj.diskon_finco,
                'ps_dealer':dis_obj.diskon_dealer,
                'ps_others':dis_obj.diskon_others,
                'tipe_subsidi':ps.tipe_subsidi,
                'tipe_potongan':'piu',
                'tipe_diskon_copy':dis_obj.tipe_diskon,
                'tipe_diskon':dis_obj.tipe_diskon,
                'ps_persen':dis_obj.diskon_persen,
                'include_invoice': ps.include_invoice,
                'include_invoice_copy':ps.include_invoice,
            })
        return {'domain':domain,'value':result}
    
    def onchange_discount_pelanggan(self,cr,uid,ids,program_subsidi,tipe_subsidi,discount,discount_pelanggan,context=None):
        if not context:
            context = {}
        result = {}

        parent = context.get('parent',False)
        if ids and parent:
            dso_line_id = parent.get('dealer_sale_order_line',False)
            if dso_line_id:
                dso_line_id = dso_line_id[0][1]
                if dso_line_id:
                    dso_line = self.pool.get('dealer.sale.order.line').browse(cr, uid, [dso_line_id], context=context)[0]
                    diskon_dp = dso_line.discount_po + discount_pelanggan
                    vals = {
                        'diskon_dp': diskon_dp,
                        'customer_dp': dso_line.uang_muka - diskon_dp,
                    }
                    self.pool.get('dealer.sale.order.line').onchange_discount_pelanggan(cr, uid, [dso_line_id], diskon_dp)
                    self.pool.get('dealer.sale.order.line').write(cr, uid, [dso_line_id], vals, context=context)

        if discount_pelanggan < 0:
            return {'value':{'discount_pelanggan':0},
                    'warning':{'title':'Perhatian !','message':'Tidak boleh memasukkan nilai negatif!'}}
        if tipe_subsidi=='fix':
            result.update({'discount_pelanggan':discount})  
        else:
            if discount_pelanggan > discount:
                return {'value':{'discount_pelanggan':discount},
                        'warning':{'title':'Perhatian !','message':'Discount tidak boleh lebih dari total subsidi!'}}

        return {'value':result}

    def onchange_tipe_diskon(self,cr,uid,ids,tipe_diskon):
        value = {'tipe_diskon_copy':'amount'}
        if tipe_diskon == 'percentage':
            value.update({'tipe_diskon_copy':'percentage'})       
        return {'value':value}

    def onchange_include_invoice(self,cr,uid,ids,include_invoice):
        value = {'include_invoice_copy':include_invoice}
        return {'value':value}

    def onchange_harga_ps(self,cr,uid,ids,ps_ahm,ps_md,ps_finco,ps_dealer,ps_others):
        value = {
            'ps_ahm_copy':ps_ahm,
            'ps_md_copy':ps_md,
            'ps_finco_copy':ps_finco,
            'ps_dealer_copy':ps_dealer,
            'ps_others_copy':ps_others,
        }
        return {'value':value}


class dealer_sale_order_brgbonus_line(osv.osv):
    _name = 'dealer.sale.order.line.brgbonus.line'       
    _columns = {
        'dealer_sale_order_line_brgbonus_line_id': fields.many2one('dealer.sale.order.line',ondelete='cascade'),
        'sale_order_line_brgbonus_line_id': fields.many2one('sale.order.line',ondelete='cascade'),
        'barang_subsidi_id': fields.many2one('dym.subsidi.barang','Kode Barang Subsidi',required=True,domain="[('state','=','approved')]"),
        'product_subsidi_id': fields.many2one('product.product','Barang Subsidi',required=True),
        'barang_qty': fields.integer('Qty',required=True),
        'price_barang': fields.float('Harga',required=True),
        'bb_md':fields.float(),
        'bb_ahm':fields.float(),
        'bb_finco':fields.float(),
        'bb_dealer':fields.float(),
        'bb_others':fields.float(),
        'force_cogs':fields.float(),
    }
    _default = {
        'bb_md': 0,
        'bb_ahm': 0,
        'bb_finco': 0,
        'bb_dealer': 0,
        'bb_others': 0,
    }

    def barang_bonus_change(self, cr, uid, ids, product_id, barang_subsidi):
        result = {}
        domain = {}
        if not product_id:
            raise osv.except_osv(('Perhatian !'), ("Pilih Produk Terlebih Dahulu"))            
        else:
            product_template_obj = self.pool.get('product.product').browse(cr,uid,product_id)

        product_template_id = product_template_obj.product_tmpl_id.id

        if not barang_subsidi:
            return {'value':{'barang_subsidi_id':False,'price_barang': 0,'product_subsidi_id':False,'barang_qty':0,'bb_md':0,'bb_ahm':0,'bb_finco':0,'bb_dealer':0,'bb_others':0},}
        else:
            domain = {'barang_subsidi_id': "[('date_end','<=','"+datetime.now().strftime('%Y-%m-%d')+"')]"} 

        ps = self.pool.get('dym.subsidi.barang').browse(cr, uid, barang_subsidi)

        if ps.date_start > datetime.now().strftime('%Y-%m-%d') or ps.date_end < datetime.now().strftime('%Y-%m-%d'):# or not ps.active:
            return {'value':{'barang_subsidi_id':False,'price_barang': 0,'product_subsidi_id':False,'barang_qty':0,'bb_md':0,'bb_ahm':0,'bb_finco':0,'bb_dealer':0,'bb_others':0},
                    'warning':{'title':'Perhatian !','message':'Barang subsidi sudah tidak aktif.'}}
            
        if not ps.subsidi_barang_line:
            return {'value':{'barang_subsidi_id':False,'price_barang': 0,'product_subsidi_id':False,'barang_qty':0,'bb_md':0,'bb_ahm':0,'bb_finco':0,'bb_dealer':0,'bb_others':0},
                    'warning':{'title':'Perhatian !','message':'Detail barang subsidi tidak ditemukan.'}}
        
        ps_line_id = ps.subsidi_barang_line      
       
        ps_line_obj = self.pool.get('dym.subsidi.barang.line').search(cr, uid,[('product_id','=',product_template_id),('subsidi_barang_id','=',barang_subsidi)])
        
        if not ps_line_obj:
            return {'value':{'barang_subsidi_id':False,'price_barang': 0,'product_subsidi_id':False,'barang_qty':0,'bb_md':0,'bb_ahm':0,'bb_finco':0,'bb_dealer':0,'bb_others':0},
                    'warning':{'title':'Perhatian !','message':'Detail produk barang subsidi tidak ditemukan.'}}
        else:
            dis_obj = self.pool.get('dym.subsidi.barang.line').browse(cr, uid,ps_line_obj)
            result.update({'product_subsidi_id':  ps.product_template_id.product_variant_ids[0].id,
                            'barang_qty': dis_obj.qty,
                            'price_barang': dis_obj.total_diskon,
                            'bb_md':dis_obj.diskon_md,
                            'bb_ahm':dis_obj.diskon_ahm,
                            'bb_finco':dis_obj.diskon_finco,
                            'bb_dealer':dis_obj.diskon_dealer,
                            'bb_others':dis_obj.diskon_others,
                           })
            domain = {'product_subsidi_id': "[('id','=',"+str(ps.product_template_id.product_variant_ids[0].id)+")]"}
        return {'value':result,'domain':domain}

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'dealer_sale_order_line_id': fields.many2one('dealer.sale.order.line',
            'Dealer Sales Memo Line', ondelete='set null', select=True,
            readonly=True),
    }

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(stock_move, self).write(cr, uid, ids, vals, context=context)
        for move in self.browse(cr, uid, ids, context=context):
                if move.dealer_sale_order_line_id: 
                    dealer_sale_order_id = move.dealer_sale_order_line_id.dealer_sale_order_line_id.id 
                    if self.pool.get('dealer.sale.order').test_moves_done(cr, uid, [dealer_sale_order_id], context=context):
                        workflow.trg_validate(uid, 'dealer.sale.order', dealer_sale_order_id, 'picking_done', cr)
                        dso = move.dealer_sale_order_line_id.dealer_sale_order_line_id                        
                        if dso.state != 'done' and dso.check_customer_payment() == True:
                            cr.execute('UPDATE dealer_sale_order SET state = %s WHERE id = %s',('done',dso.id,))
        return res
        
class sales_source(osv.osv):
    _name = 'sales.source'
    _order = 'sequence'
    
    _columns = {
        'sequence': fields.integer(string='Sequence'),
        'name' : fields.char('Name', required=True),
        'code' : fields.char('Code'),
        'default_pic' : fields.boolean('Default PIC', help='If this is selected, this source will become default on Inter Company Sale/Purchase (PIC)'),
    }

    _default = {
        'default_pic': False,
    }

    _sql_constraints = [
        ('unique_source_name', 'unique(name)', 'Sales source sudah ada!'),
    ]


class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _is_mediator(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context == None:
            context = {}
        for partner in self.browse(cr, uid, ids, context=context):
            is_mediator = False            
            if 'branch_id' in context and self.pool.get('dym.hutang.komisi').search(cr, uid, [('area_id.branch_ids','in',context['branch_id']),('state','=','approved'),('date_start','<=',time.strftime('%Y-%m-%d %H:%M:%S')),('date_end','>=',time.strftime('%Y-%m-%d %H:%M:%S')),('partner_komisi_ids','=',partner.id)]):
                is_mediator = True
            res[partner.id] = is_mediator
        return res

    def _get_hutang_komisi(self, cr, uid, ids, context=None):
        hc = self.pool.get('dym.hutang.komisi').browse(cr, uid, ids).mapped('partner_komisi_ids')
        return list(set(hc.ids))

    _columns = {
        'is_mediator' : fields.function(_is_mediator, type="boolean", string="Is Mediator",
            store={
                'dym.hutang.komisi': (_get_hutang_komisi, ['partner_komisi_ids'], 10),
            }),
    }


class dym_proses_stnk(osv.osv):
    _inherit = 'dym.proses.stnk'
    _columns = {
        'dso_ids': fields.related('serial_number_ids', 'dealer_sale_order_id', type='many2one', relation='dealer.sale.order', string='Dealer Sales Memo'),
    }

