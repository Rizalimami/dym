import time
from lxml import etree
import pytz
from openerp import SUPERUSER_ID, models, api, _
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from openerp import workflow
from openerp import netsvc
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import calendar
from openerp.exceptions import except_orm, Warning, RedirectWarning
import re
from openerp.addons.dym_work_order.report import fungsi_terbilang

import pdb

class dym_work_order_discount_line(osv.osv):
    _inherit = 'dealer.sale.order.line.discount.line'       

    _columns = {
        'work_order_line_discount_line_id': fields.many2one('dym.work.order.line',ondelete='cascade'),
    }

class dym_product_template_category(osv.osv):
    _inherit = 'product.template'
    _columns = {
        'service_category_ids': fields.many2many('dym.category.product', 'service_category_rel', 'service_id', 'category_id', 'Category Service', copy=False),
    }

class dym_work_order(osv.osv):
    _name = "dym.work.order"
    _description = "Work Order"
    _order = 'date desc, id desc'

    def _amount_line_tax(self,cr , uid, line, context=None):
        val=0.0
        if context is None:
            context = {} 
        discount_program = 0
        for program_line in line.discount_line:
            if program_line.tipe_diskon == 'percentage':
                discount_program += (line.price_unit * program_line.discount_pelanggan / 100)
            else:
                discount_program += program_line.discount_pelanggan 
        discount_program = discount_program * line.product_qty
        price = (line.price_unit*line.product_qty) - line.discount - discount_program  - line.discount_bundle
        for c in self.pool.get('account.tax').compute_all(cr,uid, line.tax_id, price, 1, line.product_id)['taxes']:
            val +=c.get('amount',0.0)
        return val
    
    
    def _get_order(self, cr, uid, ids, context=None):
        wo = self.pool.get('dym.work.order.line').browse(cr, uid, ids).mapped('work_order_id')
        return list(set(wo.ids))
    
    
    def _max_warranty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'warranty': 0.0,
            }
            nilai_max = 0.0
            
            for line in order.work_lines:
                if nilai_max < line.warranty:
                    nilai_max = line.warranty
            res[order.id]['warranty'] = nilai_max
        return res

    def _get_days(self, cr, uid, context=None):
        x = []
        return x
    
    def get_location_ids(self,cr,uid,ids,context=None):
        quants_ids = self.pool.get('stock.quant').search(cr,uid,['&',('product_id','in',ids),('qty','>',0.0),('reservation_id','=',False)])
        loc_ids = self.pool.get('stock.quant').read(cr, uid, quants_ids, ['location_id'])
        return [x['location_id'][0] for x in loc_ids]

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting Approval'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
        ('finished', 'Finished'),
        ('open', 'Open'),
        ('except_picking', 'Shipping Exception'),
        ('except_invoice', 'Invoice Exception'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ]
    
    def _invoiced(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for purchase in self.browse(cursor, user, ids, context=context):
            res[purchase.id] = all(line.invoiced for line in purchase.work_lines)
        return res
    
    def _get_picking_in(self, cr, uid, context=None):
        obj_data = self.pool.get('ir.model.data')
        return obj_data.get_object_reference(cr, uid, 'stock','picking_type_in') and obj_data.get_object_reference(cr, uid, 'stock','picking_type_in')[1] or False

    def _get_picking_ids(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for po_id in ids:
            res[po_id] = []
        query = """
        SELECT picking_id, po.id 
        FROM stock_picking p,
         stock_move m, 
         dym_work_order_line pol, 
         dym_work_order po
            WHERE  po.id in %s
            and po.id = pol.work_order_id
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
        for wo in self.browse(cr, uid, ids, context=context):
            for picking in wo.picking_ids:
                if picking.state != 'done' and picking.state != 'cancel' :
                    return False
        return True
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False  
        return branch_ids 

    def _check_invoice(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'sparepart_invoice_cancel': False,
                'service_invoice_cancel': False,
            }
            obj_inv = self.pool.get('account.invoice')
            invoice_ids = obj_inv.search(cr,uid,[
                ('origin','ilike',order.name),
                ('type','=','out_invoice')
            ])
            for inv in obj_inv.browse(cr, uid, invoice_ids):
                for line in inv.invoice_line:
                    if line.product_id.categ_id.isParentName('Sparepart'):
                        res[order.id]['sparepart_invoice_cancel'] = True if inv.state == 'cancel' else False
                        break
                    elif line.product_id.categ_id.isParentName('Service'):
                        res[order.id]['service_invoice_cancel'] = True if inv.state == 'cancel' else False
                        break
        return res

    def _get_tipe_konsumen(self,cr,uid,ids,context=None):
        tipe_id = False
        tipe_ids = self.pool.get('tipe.konsumen').search(cr, uid, [('default','=',True),('wo','=',True)], limit=1)
        if tipe_ids:
            tipe_id = self.pool.get('tipe.konsumen').browse(cr, uid, tipe_ids)
        return tipe_id

    def _get_days_func(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for wo in self.browse(cr, uid, ids, context=context):
            a = datetime.strptime(wo.date,"%Y-%m-%d %H:%M:%S").date()
            b = datetime.strptime(wo.tanggal_pembelian,"%Y-%m-%d").date()
            timedelta = a -b
            diff = timedelta.days
            res[wo.id] = diff
        return res

    _columns = {
        'tipe_konsumen': fields.many2one('tipe.konsumen','Tipe Konsumen'),
        'sparepart_invoice_cancel': fields.function(_check_invoice, string='Sparepart Invoice Cancel', type='boolean', copy=False, multi='sums'),
        'service_invoice_cancel': fields.function(_check_invoice, string='Service Invoice Cancel', type='boolean', copy=False, multi='sums'),
        'name': fields.char('Work Order', size=64, required=True),
        'date' : fields.datetime('Order Date', required=True),
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True, select=True, copy=False),
        'branch_id':fields.many2one('dym.branch','Branch',required=True,default=lambda self: self.env.user.branch_id),
        'division':fields.selection([('Sparepart','Workshop')],'Division', change_default=True,select=True,required=True),
        'customer_id':fields.many2one('res.partner','Customer'),
        'customer_cabang': fields.many2one('dym.cabang.partner','Cabang Customer'),
        'customer_transaksi':fields.many2one('res.partner','Customer Transaksi'),
        'customer_name':fields.related('customer_id','name',type='char', required=True,readonly=True, string='Customer Name',),
        'type':fields.selection([('KPB','KPB'),('REG','Regular'),('WAR','Job Return'),('CLA','Claim')],'Type', change_default=True, select=True, readonly=True, required=True),
        'kpb_ke':fields.selection([('1','1'),('2','2'),('3','3'),('4','4')],'KPB Ke',change_default=True,select=True),
        'no_pol':fields.char('No Polisi',size=12,select=True),
        'prev_work_order_id':fields.many2one('dym.work.order','WO Sebelumnya',domain="[('state','=','done')]"), # domain: state = done dan type = REG atau WAR dan date tidak melebihi waktu garansi
        'mekanik_id':fields.many2one('hr.employee','Mechanic'),
        'product_id':fields.many2one('product.product','Product'),
        'km':fields.integer('Km'),
        'work_lines': fields.one2many('dym.work.order.line', 'work_order_id', 'Order lines'),
        'work_lines2': fields.one2many('dym.work.order.line', 'work_order_id', 'Order lines'),
        'note': fields.text('Keluhan'),
        'payment_term':fields.many2one('account.payment.term','Payment Terms',required=True),
        'lama_garansi':fields.float('Lama Garansi'),
        'start':fields.datetime('Start',readonly=True),
        'date_break':fields.datetime('Break',readonly=True),
        'end_break':fields.datetime('End Break',readonly=True),
        'finish':fields.datetime('Finish',readonly=True),
        'bensin':fields.selection([('0','0'),('25','25'),('50','50'),('75','75'),('100','100')],'Bensin',change_default=True,select=True),
        'type_motorcycle':fields.char('Type Motorcycle'),
        'member':fields.related('customer_transaksi','member',type='char',string='Member Number'),
        'kode_buku':fields.char('Kode Buku'),
        'nama_buku':fields.char('Nomor Buku'),
        'shipped':fields.boolean('Received', readonly=True, select=True, copy=False,help="It indicates that a picking has been done"),  
        'tanggal_pembelian':fields.date('Tanggal Pembelian'),
        'lot_id':fields.many2one('stock.production.lot','Engine No'),
        'chassis_no':fields.related('lot_id','chassis_no',type='char',string='Chassis Number'),
        'warranty':fields.function(_max_warranty, digits_compute=dp.get_precision('Account'), string='Warranty',
            store={
                'dym.work.order': (lambda self, cr, uid, ids, c={}: ids, ['work_lines'], 10),
                'dym.work.order.line': (_get_order, ['product_id'], 10),
            },
            multi='sumsa', help="Warranty"),
        'tipe_buku':fields.char('Tipe Buku Service'),
        'jenis_oli': fields.selection([('MPX', 'MPX'), ('SPX','SPX')], 'Jenis Oli'),
        'dealer_penjual':fields.char('Dealer Penjual'),
        'stampel_ahass': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Stampel Ahass'),
        'stampel_dealer_depan': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Stampel Dealer Depan'),
        'stampel_dealer_belakang': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Stampel Dealer Belakang'),
        'tt_pemilik': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'TTD'),
        'km_cek': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'KM Cek'),
        'tgl_beli_cek': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Cek Tanggal Beli'),
        'tgl_service_cek': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Cek Tanggal Service'),
        'chassis_no_cek': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Cek No Chassis'),
        'engine_no_cek': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Cek No Engine'),
        'no_buk_cek': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Cek No Buku'),
        'kpb_collected':fields.selection([('belum', 'Belum'), ('ok','OK'), ('not','Not Ok'), ('collected','Collected')], 'KPB Collected'),
        'kpb_collected_date':fields.datetime('KPB Collected Date'),
        'collecting_id':fields.many2one('dym.collecting.kpb',string="Collecting KPB ID"),
        'mobile': fields.char('Mobile'),
        'days':fields.function(_get_days_func,string='Hari', type='integer'),
        'type_wo':fields.boolean('Type WO', readonly=True, select=True, copy=False),  
        'date_confirm':fields.datetime('Confirmation date', readonly=1),
        'invoiced': fields.function(_invoiced, string='Invoice Received', type='boolean', copy=False), 
        'invoice_method': fields.selection([('manual','Based on Purchase Order lines'),('order','Based on generated draft invoice'),('picking','Based on incoming shipments')], 'Invoicing Control', required=True,
            readonly=True, states={'draft':[('readonly',False)], 'sent':[('readonly',False)]},
            help="Based on Purchase Order lines: place individual lines in 'Invoice Control / On Purchase Order lines' from where you can selectively create an invoice.\n" \
                "Based on generated invoice: create a draft invoice you can validate later.\n" \
                "Based on incoming shipments: let you create an invoice when receipts are validated."
        ), 
        'invoice_ids': fields.many2many('account.invoice', 'purchase_invoice_rel', 'purchase_id',
                                        'invoice_id', 'Invoices', copy=False),
        'picking_ids': fields.function(_get_picking_ids, method=True, type='one2many', relation='stock.picking', string='Picking List', help="This is the list of receipts that have been generated for this purchase order."),
        'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
        'confirm_date':fields.datetime('Confirmed on'),    
        'pajak_gunggung':fields.boolean('Tanpa Faktur Pajak',copy=False),   
        'pajak_gabungan':fields.boolean('Faktur Pajak Gabungan',copy=False),   
        'pajak_generate':fields.boolean('Faktur Pajak Satuan',copy=False),   
        'faktur_pajak_id':fields.many2one('dym.faktur.pajak.out',string='No Faktur Pajak',copy=False),
        'finco_id': fields.many2one('res.partner','Finco',domain=[('finance_company','=',True)]),
        'pit_id':fields.many2one('dym.pit','Pit'),
        'sa_id':fields.many2one('hr.employee','Service Advisor'),
        'check_service_id':fields.many2one('dym.check.service','Check Setvice', readonly=True, invisible=True),
        'is_pedagang_eceran': fields.related('branch_id', 'is_pedagang_eceran', relation='dym.branch',type='boolean',string='Pedagang Eceran',store=False),
    }
    
    _defaults = {
        'tipe_konsumen': _get_tipe_konsumen,
        'name': '/',
        'km':False,
        'state': 'draft',
        'date': fields.datetime.now,
        'division':'Sparepart',
        'kpb_collected':'belum',
        'kpb_collected_date':False,
        'stampel_ahass':'tidak',
        'stampel_dealer_depan':'tidak',
        'stampel_dealer_belakang':'tidak',
        'tt_pemilik':'tidak',
        'km_cek':'tidak',
        'tgl_beli_cek':'tidak',
        'tgl_service_cek':'tidak',
        'chassis_no_cek':'tidak',
        'engine_no_cek':'tidak',
        'no_buk_cek':'tidak',
        'tanggal_pembelian':fields.date.context_today,
        'days':_get_days,
        'invoice_method': 'manual',
        'shipped': 0,
        'state':'draft',
        'type_wo':0,
        'warranty':0.0,
        'branch_id': _get_default_branch,
    }
    
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Nama WO harus unik !'),
    ]
    
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
        val = self.browse(cr,uid,ids)
        if val.customer_transaksi.tipe_faktur_pajak:
            if val.customer_transaksi.tipe_faktur_pajak == 'satuan':
                value['pajak_generate'] = True
                value['pajak_gunggung'] = False
                value['pajak_gabungan'] = False
            elif val.customer_transaksi.tipe_faktur_pajak == 'gabungan':
                value['pajak_generate'] = False
                value['pajak_gunggung'] = False
                value['pajak_gabungan'] = True
            else:
                value['pajak_generate'] = False
                value['pajak_gunggung'] = True
                value['pajak_gabungan'] = False
        return {'value':value}
    
    def chassis_onchange(self, cr, uid, ids,chassis_no):
        if chassis_no :
            chassis_no = chassis_no.replace(' ', '').upper()
            return {'value' : {'chassis_no':chassis_no}}

    def no_pol_onchange(self, cr, uid, ids,no_pol):
        warning = {}
        value = {}
        result = {}
        if no_pol:
            formatted_no_polisi = ''
            no_polisi_normalize = no_pol.replace(' ', '').upper()
            splitted_no_polisi = re.findall(r'[A-Za-z]+|\d+', no_polisi_normalize)
            if len(splitted_no_polisi) == 3:
              if splitted_no_polisi[0].isalpha() == True and splitted_no_polisi[1].isdigit() == True and splitted_no_polisi[2].isalpha() == True:
                for word in splitted_no_polisi:
                  formatted_no_polisi += word + ' '
                formatted_no_polisi = formatted_no_polisi[:-1]
                return {'value':{'no_pol':formatted_no_polisi}}              
            warning = {
                'title': ('Perhatian !'),
                'message': (('Format nomor polisi salah, mohon isi nomor polisi dengan format yang benar! (ex. A 1234 BB)')),
            }
            value['no_pol'] = self.browse(cr, uid, ids).no_pol
            result['warning'] = warning
            result['value'] = value
            return result
    
    def kode_buku_onchange(self, cr, uid, ids,kode_buku):
        if kode_buku :
            kode_buku = kode_buku.replace(' ', '').upper()
            return {'value' : {'kode_buku':kode_buku}}
        
    def nama_buku_onchange(self, cr, uid, ids,nama_buku):
        if nama_buku :
            nama_buku = nama_buku.replace(' ', '').upper()
            return {'value' : {'nama_buku':nama_buku}}
        
    def onchange_type(self, cr, uid, ids, service_type):
        dom = {}
        if service_type:
            return {'value':{'payment_term':False,'kpb_ke':False,'prev_work_order_id':False}}
        cr.execute('''
               select  id as work_order
               from dym_work_order where 
               CAST(date AS DATE) + cast(warranty as int)>current_date-1
               ''')
        item_ids = [x[0] for x in cr.fetchall()]
        dom['prev_work_order_id']=[('id','in',item_ids)]
        return {'domain':dom}


    def onchange_prev_work_order_id(self, cr, uid, ids, prev_work_order_id):
        dom = {}
        if prev_work_order_id:
            prev_work_order = self.pool.get('dym.work.order').browse(cr, uid, prev_work_order_id)
            if prev_work_order:

                dom.update({'tipe_konsumen':[('id','=',prev_work_order.tipe_konsumen.id)]})
                lines = []
                for line in prev_work_order.work_lines:
                    discount_lines = []
                    for disc_line in line.discount_line:
                        discount_lines.append([0,0,{
                            'program_subsidi': disc_line.program_subsidi.id,
                            'discount': disc_line.discount,
                            'discount_pelanggan': disc_line.discount_pelanggan,
                            'tipe_subsidi': disc_line.tipe_subsidi,
                            'ps_md': disc_line.ps_md,
                            'ps_ahm': disc_line.ps_ahm,
                            'ps_finco': disc_line.ps_finco,
                            'ps_dealer': disc_line.ps_dealer,
                            'ps_others': disc_line.ps_others,
                            'tipe_diskon': disc_line.tipe_diskon,
                            'tipe_diskon_copy': disc_line.tipe_diskon_copy,
                            'ps_persen': disc_line.ps_persen,
                        }])
                    bundle_lines = []
                    for bund_line in line.bundle_line:
                        bundle_lines.append([0,0,{
                            'type': bund_line.type,
                            'item_id': bund_line.item_id.id,
                            'product_id': bund_line.product_id.id,
                            'product_uom_qty': bund_line.product_uom_qty,
                            'product_uom': bund_line.product_uom.id,
                            'location_id': bund_line.location_id.id,
                            'diskon': bund_line.diskon,
                            'supply_qty': bund_line.supply_qty,
                            'price_bundle': bund_line.price_bundle,
                        }])
                    barang_bonus_lines = []
                    for brgbns_line in line.barang_bonus_line:
                        barang_bonus_lines.append([0,0,{
                            'barang_subsidi_id': brgbns_line.barang_subsidi_id.id,
                            'product_subsidi_id': brgbns_line.product_subsidi_id.id,
                            'barang_qty': brgbns_line.barang_qty,
                            'price_barang': brgbns_line.price_barang,
                            'bb_md': brgbns_line.bb_md,
                            'bb_ahm': brgbns_line.bb_ahm,
                            'bb_finco': brgbns_line.bb_finco,
                            'bb_dealer': brgbns_line.bb_dealer,
                            'bb_others': brgbns_line.bb_others,
                            'force_cogs': brgbns_line.force_cogs,
                        }])
                    vals = {
                        'name': line.name,
                        'categ_id': line.categ_id,
                        'categ_id_2': line.categ_id_2.id,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_qty,
                        'product_uom': line.product_uom.id,
                        'supply_qty': line.supply_qty,
                        'discount_persen': line.discount_persen,
                        'discount': line.discount,
                        'price_unit': line.price_unit,
                        'tax_id': [(6, 0, line.tax_id.ids)],
                        'warranty': 0,
                        'invoiced': False,
                        'state': 'draft',
                        'tax_id_show': [(6, 0, line.tax_id.ids)],
                        'discount_line': discount_lines,
                        'branch_dummy': False,
                        'insentif_finco': line.insentif_finco,
                        'is_bundle': line.is_bundle,
                        'bundle_line': bundle_lines,
                        'barang_bonus_line': barang_bonus_lines,
                    }
                    if line.location_id:
                        vals.update({'location_id':line.location_id.id})
                    lines.append([0,0,vals])
                return {'value':{
                            'lot_id':prev_work_order.lot_id.id, 'tipe_konsumen':prev_work_order.tipe_konsumen.id, 'pit_id':prev_work_order.pit_id.id, 'mekanik_id':prev_work_order.mekanik_id.id, 'sa_id':prev_work_order.sa_id.id, 'work_lines2':lines,
                        },
                        'domain': dom,
                    }
            return {'value':{'lot_id':False,'work_lines2':False}}
        return True
    
    def onchange_tanggal(self,cr,uid,ids,tanggal_pembelian,date):
        a=datetime.strptime(date[:10],"%Y-%m-%d")
        b=datetime.strptime(tanggal_pembelian[:10],"%Y-%m-%d")
        timedelta = a -b
        diff=timedelta.days
        return {
            'value':{
                'days':diff
                }
            }
    
    def onchange_branch_id(self, cr, uid, branch_id, product_id, pit_id, context=None):
        dom = {} 
        product_ids = self.pool.get('product.category').get_child_ids(cr,uid,branch_id,'Unit')
        dom['product_id']=[('categ_id','in',product_ids)]

        if branch_id:
            pit_ids = self.pool.get('dym.pit').search(cr, uid, [('branch_id','=',branch_id),('active','=',True)])
            if pit_ids:
                employee_ids = []
                for pit in self.pool.get('dym.pit').browse(cr, uid, pit_ids):
                    employee_ids+=pit.mekanik_ids.ids
            dom['mekanik_id']=[('id','in',employee_ids)]
            dom['pit_id']=[('id','in',pit_ids)]

        value = {}
        if branch_id:
            branch = self.pool.get('dym.branch').browse(cr,uid,branch_id)
            value['is_pedagang_eceran'] = branch.is_pedagang_eceran
        return {'domain':dom, 'value':value}
        
    def onchange_pit_id(self, cr, uid, ids, pit_id, mekanik_id, branch_id, context=None):
        dom = {} 
        mekanik_ids = []
        value = {}
        employee_ids = []
        employee_obj = self.pool.get('hr.employee')
        if pit_id:
            pit_ids = self.pool.get('dym.pit').search(cr, uid, [('id','=',pit_id)])
            employee_ids = self.pool.get('dym.pit').browse(cr, uid, pit_ids).mekanik_ids.ids
        else:
            if branch_id:
                pit_ids = self.pool.get('dym.pit').search(cr, uid, [('branch_id','=',branch_id),('active','=',True)])
                if pit_ids:
                    dom['pit_id']=[('id','in',pit_ids)]
                    employee_ids = []
                    for pit in self.pool.get('dym.pit').browse(cr, uid, pit_ids):
                        employee_ids += pit.mekanik_ids.ids
        if not mekanik_id:
            value['mekanik_id'] = False                          
            dom['mekanik_id']=[('id','in',employee_ids)]

        if len(employee_ids)==1:
            value['mekanik_id']=employee_ids[0]
            advisor_ids = self.pool.get('hr.employee').search(cr, uid, [('job_id.name','=','SERVICE ADVISOR'),('branch_id','=',branch_id)])
            if advisor_ids:
                if len(advisor_ids)==1:
                    value['sa_id'] = advisor_ids[0]
        return {'domain':dom, 'value':value}

    def onchange_mekanik_id(self, cr, uid, ids, mekanik_id, pit_id, branch_id, context=None):
        dom = {}
        value = {}
        if not pit_id and mekanik_id:
            pit_id = self.pool.get('dym.pit').search(cr, uid, [('mekanik_ids','in',[mekanik_id])], context=context)
            if pit_id:
                dom['pit_id'] = [('id','in',pit_id)]
                value['pit_id'] = pit_id[0]
        return {'domain':dom, 'value':value}

    def onchange_lot_id(self, cr, uid, ids, lot_id):
        lot = self.pool.get('stock.production.lot').browse(cr, uid, lot_id) 
        if lot:
            tanggal_beli = lot.work_order_ids.mapped('tanggal_pembelian')[0] if lot.work_order_ids.mapped('tanggal_pembelian') else lot.invoice_date 
            values = {
                'customer_id':lot.customer_stnk.id,
                'customer_transaksi':lot.customer_stnk.id,
                'product_id':lot.product_id.id,
                'kode_buku':lot.kode_buku,
                'nama_buku':lot.nama_buku,
                'tanggal_pembelian':tanggal_beli,
                'no_pol':lot.no_polisi,
                'chassis_no':lot.chassis_no,
            }
            return {'value':values}
        return {'value':{
                'customer_id':False,
                'customer_transaksi':False,
                'product_id':False,
                'kode_buku':False,
                'nama_buku':False,
                'tanggal_pembelian':False,
                'no_pol':False,
                'chassis_no':False,
            }
        }

    def onchange_customer_id(self, cr, uid, ids, customer_id,type,branch_id):
        mobile = []
        payment_term = []
        if customer_id:
            obj_customer = self.pool.get("res.partner").browse(cr,uid,customer_id)
            mobile = obj_customer.mobile
            if type == 'SLS' or type == 'REG' :
                payment_term = obj_customer.property_payment_term.id
            elif type == 'KPB' or type == 'CLA' : 
                obj_payment_term=self.pool.get("dym.branch").browse(cr,uid,branch_id)
                payment_term = obj_payment_term.default_supplier_workshop_id.property_payment_term.id
            if not payment_term :
                 payment_term =1
            member = obj_customer.member
        else:
            member = False
            mobile = False
        return {'value':{'mobile' : mobile,'payment_term': payment_term,'member': member}}

    def onchange_customer_transaksi(self, cr, uid, ids, customer_transaksi):
        mobile = []
        payment_term = []
        if customer_transaksi:
            obj_customer = self.pool.get("res.partner").browse(cr,uid,customer_transaksi)
            member = obj_customer.member
        else:
            member = False
        return {'value':{'member': member}}

    def dym_outstanding_kpb_wizard(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dym.outstanding.kpb.wizard.form'), ("model", "=", 'dym.work.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Work Order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dym.work.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
        } 

    def dym_outstanding_claim_wizard(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dym.outstanding.claim.wizard.form'), ("model", "=", 'dym.work.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Work Order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dym.work.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
        } 
        
    def start_stop_wo(self, cr, uid, ids, context=None):
        obj_claim_kpb = self.pool.get("ir.ui.view")
        obj_ir_view = obj_claim_kpb.search(cr,uid, [("name", "=", 'dym.start.stop.wo.form'),("model", "=", 'dym.start.stop.wo'),])
        view_id = obj_claim_kpb.browse(cr,uid,obj_ir_view)
        work_order_browse = self.browse(cr, uid, ids[0], context=context)
        return {
            'name':_("Start / Stop Work Order"),
            'view_mode': 'form',
            'view_id': view_id.id,
            'view_type': 'form',
            'res_model': 'dym.start.stop.wo',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'branch_id': work_order_browse.branch_id.id,
                'work_order_id': work_order_browse.id,
                'mekanik_id': work_order_browse.mekanik_id.id,
                'pit_id': work_order_browse.pit_id.id,
            }
        }

    def view_picking(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        pick_ids = []
        for po in self.browse(cr, uid, ids, context=context):
            pick_ids += [picking.id for picking in po.picking_ids]
        action['context'] = {}
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = pick_ids and pick_ids[0] or False 
        return action
    
    def view_picking_slip(self,cr,uid,ids,context=None): 
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        pick_ids = []
        for po in self.browse(cr, uid, ids, context=context):
            pick_ids += [picking.id for picking in po.picking_ids]
        action['context'] = {}
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = pick_ids and pick_ids[0] or False 
        return action
    
    
    def _get_jornal_id(self, cr, uid, ids, branch_id,type,context=None):
        obj_account = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',branch_id),])
        set_account_journal = {}
        jornal=self.pool.get('dym.branch.config').browse(cr,uid,obj_account)
        if obj_account:
            if type == 'KPB' :
                journal_id=self.pool.get('dym.branch.config').browse(cr,uid,obj_account).wo_kpb_journal_id.id
                account_id=self.pool.get('dym.branch.config').browse(cr,uid,obj_account).wo_kpb_journal_id.default_debit_account_id.id
                if not journal_id:
                     raise osv.except_osv(('Warning !'), ("Journal WO KPB Belum di Setting"))
                if not account_id :
                     raise osv.except_osv(('Warning !'), ("Debit Account WO KPB di Branch Config Belum di Setting"))
                
            if type == 'CLA' :
                journal_id=self.pool.get('dym.branch.config').browse(cr,uid,obj_account).wo_claim_journal_id.id
                account_id=self.pool.get('dym.branch.config').browse(cr,uid,obj_account).wo_claim_journal_id.default_debit_account_id.id
                if not journal_id:
                     raise osv.except_osv(('Warning !'), ("Journal WO Claim Belum di Setting"))
                if not account_id :
                     raise osv.except_osv(('Warning !'), ("Debit Account WO Claim di Branch Config Belum di Setting"))
            if type == 'SLS' or type == 'REG' : 
                journal_id=self.pool.get('dym.branch.config').browse(cr,uid,obj_account).wo_reg_journal_id.id
                account_id=self.pool.get('dym.branch.config').browse(cr,uid,obj_account).wo_reg_journal_id.default_debit_account_id.id
                if not journal_id:
                     raise osv.except_osv(('Warning !'), ("Journal WO Regular dan Part Sales Belum di Setting"))
                if not account_id :
                     raise osv.except_osv(('Warning !'), ("Debit Account WO Regular dan Part Sales di Branch Config Belum di Setting"))
            if type == 'WAR' : 
                journal_id=self.pool.get('dym.branch.config').browse(cr,uid,obj_account).wo_war_journal_id.id
                account_id=self.pool.get('dym.branch.config').browse(cr,uid,obj_account).wo_war_journal_id.default_debit_account_id.id  
                if not journal_id:
                     raise osv.except_osv(('Warning !'), ("Journal  WO Parts Sales & Job Return Belum di Setting"))
                if not account_id :
                     raise osv.except_osv(('Warning !'), ("Debit Account WO Parts Sales & Job Return di Branch Config Belum di Setting"))
            set_account_journal.update({'journal_id':journal_id,'account_id': account_id, })
            return set_account_journal

    def _get_account_id(self, cr, uid, ids, product_id,context=None):
        obj_account = self.pool.get('product.product').search(cr,uid,[('id','=',product_id),])
        if obj_account:
            account_line=self.pool.get('product.product').browse(cr,uid,obj_account).property_account_income.id
            if not account_line :
                account_line=self.pool.get('product.product').browse(cr,uid,obj_account).categ_id.property_account_income_categ.id
                if not account_line :
                    account_line=self.pool.get('product.product').browse(cr,uid,obj_account).categ_id.parent_id.property_account_income_categ.id
                if not account_line :
                    raise osv.except_osv(('Warning !'), ("Account Untuk Product Belum di Setting"))
            return account_line

    def _get_customer_id(self, cr, uid, ids, type, customer_id, branch_id, context=None):
        if type == 'KPB' or type == 'CLA' :
            obj_customer_wo = self.pool.get('dym.branch').browse(cr, uid,branch_id)
            customer_id_wo=obj_customer_wo.default_supplier_workshop_id.id
            if not obj_customer_wo.default_supplier_workshop_id.id :
                raise osv.except_osv(('Perhatian !'), ("Principle di Branch Belum di Setting"))
        else :
            customer_id_wo=customer_id
        return customer_id_wo
      
    def _get_dest_location_wo(self,cr,uid,ids,context=None):
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
     
    
    def _get_wo(self, cr, uid, ids, type,date,tanggal_pembelian,lot_id,kpb_ke,km,context=None):
        if type == 'KPB' :
            tanggal_wo=date
            tanggal_pembelian=tanggal_pembelian
            tanggal_wo_format=datetime.strptime(tanggal_wo,"%Y-%m-%d %H:%M:%S")
            tanggal_pembelian_format=datetime.strptime(tanggal_pembelian,"%Y-%m-%d")
            pengurangan_hari=tanggal_wo_format-tanggal_pembelian_format
            pengurangan_hari_format=abs((pengurangan_hari).days)
            
            obj_engine = self.pool.get('dym.kpb.expired')
            lot = self.pool.get('stock.production.lot').browse(cr, uid, lot_id)
            vit = obj_engine.search(cr,uid, [("name", "in", [lot.name[:5],False]), ("service", "=", kpb_ke)], order='name desc')
            if not vit:
                vit = obj_engine.search(cr,uid, [("name", "in", [lot.name[:4],False]), ("service", "=", kpb_ke)], order='name desc')
                if not vit:
                    raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ada Di Database KPB"))
            data = obj_engine.browse(cr, uid, vit[0])
            if km>data.km:
                raise osv.except_osv(('Perhatian !'), ("Kilometer telah lewat batas KPB"))
            elif km==0:
                raise osv.except_osv(('Perhatian !'), ("Kilometer tidak boleh nol"))
            # if pengurangan_hari_format > data.hari:
            #      raise osv.except_osv(('Perhatian !'), ("Tanggal KPB sudah lewat batas KPB"))
        elif type != 'SLS' :
            if km==0:
                raise osv.except_osv(('Perhatian !'), ("Kilometer tidak boleh nol"))
        return True

    def create(self, cr, uid, vals, context=None):
        if not vals['work_lines'] and vals['type'] != 'WAR':
            raise osv.except_osv(('Perhatian !'), ("Detail Transaksi Belum di Isi"))
        vals['date'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self._get_wo(cr, uid, vals['branch_id'], vals ['type'],vals['date'],vals['tanggal_pembelian'],vals['lot_id'],vals['kpb_ke'],vals['km'])       
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'WOR', division=vals['division'])
        # Otomatis pilih tipe Faktur Pajak
        obj_partner = self.pool.get('res.partner')
        if 'customer_transaksi' in vals:
            customer_transaksi = obj_partner.browse(cr,uid,vals['customer_transaksi'])
            if 'customer_transaksi' in vals:
                if customer_transaksi.npwp and not customer_transaksi.tipe_faktur_pajak:
                    raise osv.except_osv(('Perhatian !'), ("Tipe Faktur Pajak di master Customer belum dilengkapi"))
                elif not customer_transaksi.npwp and customer_transaksi.tipe_faktur_pajak != 'tanpa_fp':
                    raise osv.except_osv(('Perhatian !'), ("Nomor NPWP atau Tipe Faktur Pajak di master Customer belum dilengkapi"))
                # elif customer_transaksi.npwp and customer_transaksi.tipe_faktur_pajak == 'tanpa_fp':
                #     raise osv.except_osv(('Perhatian !'), ("Tipe Faktur Pajak tidak boleh diisi 'Tanpa Faktur Pajak' di master Customer jika ada NPWP")) 
                elif not customer_transaksi.npwp and not customer_transaksi.tipe_faktur_pajak:
                    raise osv.except_osv(('Perhatian !'), ("Tipe Faktur Pajak di master Customer belum dilengkapi"))    

                if customer_transaksi.tipe_faktur_pajak == 'tanpa_fp':
                    vals['pajak_gunggung']=True
                    vals['pajak_generate']=False
                    vals['pajak_gabungan']=False
                elif customer_transaksi.tipe_faktur_pajak == 'satuan':
                    vals['pajak_gunggung']=False
                    vals['pajak_generate']=True
                    vals['pajak_gabungan']=False
                elif customer_transaksi.tipe_faktur_pajak == 'gabungan':
                    vals['pajak_gunggung']=False
                    vals['pajak_generate']=False
                    vals['pajak_gabungan']=True
        work_order = super(dym_work_order, self).create(cr, uid, vals, context=context)
        if work_order:
            wo = self.browse(cr, uid, work_order)
            if wo.amount_total < 0:
                 raise osv.except_osv(('Perhatian !'), ("Total Amount tidak boleh minus! harap cek kembali data anda!"))
            if not wo.work_lines.filtered(lambda r: r.categ_id == 'Service') and wo.work_lines:
                raise osv.except_osv(('Perhatian !'), ("WO Tidak memiliki service"))
            if vals['work_lines'] and vals['type'] == 'KPB':
                if wo.work_lines.filtered(lambda r: r.categ_id == 'Service') and wo.work_lines:
                    categ_id_srv_check = []
                    for wo_line in wo.work_lines:
                        if wo_line.categ_id in categ_id_srv_check:
                            raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada dua kategori yang sama dalam satu WO KPB!"))
                        else:
                            categ_id_srv_check.append(wo_line.categ_id)

            # Cek Double Product
            double_prod = []
            single_prod = []
            for item in wo.work_lines:
                key = str(item.product_id.name)
                if key not in single_prod:
                    single_prod.append(key)
                else:
                    double_prod.append(item.product_id.name)
            if double_prod:
                raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada produk Saprepart/Accessories/Service yang sama dalam satu WO ! Silahkan cek ulang pada produk : %s" % ', '.join(double_prod)))

            obj_lot = self.pool.get('stock.production.lot')
            lot_update_reserve = obj_lot.write(cr,uid,vals['lot_id'],{'kode_buku': vals['kode_buku'],'nama_buku':vals['nama_buku'],'no_polisi':vals['no_pol'],'chassis_no':vals['chassis_no'],'product_id':vals['product_id']})       
        return work_order

    def check_procurement_needed(self, cr, uid, product_id, context=None):
        prod_obj = self.pool.get('product.product')
        res = False
        if product_id.product_tmpl_id.is_bundle:
            for item in product_id.product_tmpl_id.item_ids:
                if item.product_id.type != 'service':
                    res = True
        elif product_id.type != 'service':
                res = True
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        context = context or {}
        tgl_break = time.strftime('%Y-%m-%d %H:%M:%S')
        val = self.browse(cr, uid, ids, context={})[0]
        res=super(dym_work_order, self).write(cr, uid, ids, vals, context=context)
        s=self.pool.get('dym.work.order.line').search(cr,uid,[('work_order_id','=',val.id),('state','=','draft')])
        if s :
            for x in self.pool.get('dym.work.order.line').browse(cr,uid,s) :
                if x.state == 'draft': 
                    netsvc.LocalService("workflow").trg_delete(uid, 'dym.work.order', val.id, cr) 
                    netsvc.LocalService("workflow").trg_create(uid, 'dym.work.order', val.id, cr)

                    if (x.categ_id == 'Sparepart' and x.state == 'draft' and val.state_wo == 'in_progress') or (x.categ_id == 'Service' and x.state == 'draft' and val.state_wo == 'in_progress'):
                        super(dym_work_order, self).write(cr, uid, ids, {'state': 'draft','shipped':0,'type_wo':0,'state_wo':'break','date_break':tgl_break}, context=context)
                        # elif x.categ_id == 'Sparepart' and x.state == 'draft':
                    elif self.check_procurement_needed(cr, uid, x.product_id, context=context) and x.state == 'draft':
                        super(dym_work_order, self).write(cr, uid, ids, {'state': 'draft','shipped':0,'type_wo':0}, context=context)
                    else :
                        super(dym_work_order, self).write(cr, uid, ids, {'state': 'draft'}, context=context)
                        netsvc.LocalService("workflow").trg_validate(uid, 'dym.work.order', val.id, 'break_wo', cr)
        for wo in self.browse(cr, uid, ids):
            for line in wo.work_lines:
                if line.price_subtotal < 0:
                    raise osv.except_osv(('Perhatian !'), ("Sub Total Amount pada baris %s tidak boleh minus! harap cek kembali data anda!" % (line.name_show,) ))
            if wo.amount_total < 0:
                 raise osv.except_osv(('Perhatian !'), ("Total Amount tidak boleh minus! harap cek kembali data anda!"))
            if not wo.work_lines.filtered(lambda r: r.categ_id == 'Service') and wo.work_lines:
                raise osv.except_osv(('Perhatian !'), ("WO %s Tidak memiliki service")%(wo.name))
            if wo.work_lines and wo.type == 'KPB':
                if wo.work_lines.filtered(lambda r: r.categ_id == 'Service') and wo.work_lines:
                    categ_id_srv_check = []
                    for wo_line in wo.work_lines:
                        if wo_line.categ_id in categ_id_srv_check:
                            raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada dua kategori yang sama dalam satu WO KPB!"))
                        else:
                            categ_id_srv_check.append(wo_line.categ_id)

            # Cek Double Product
            double_prod = []
            single_prod = []
            for item in wo.work_lines:
                key = str(item.product_id.name)
                if key not in single_prod:
                    single_prod.append(key)
                else:
                    double_prod.append(item.product_id.name)
            if double_prod:
                raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada produk Saprepart/Accessories/Service yang sama dalam satu WO ! Silahkan cek ulang pada produk : %s" % ', '.join(double_prod)))
            
            self._get_wo(cr, uid, [wo.id], wo.type, wo.date, wo.tanggal_pembelian, wo.lot_id.id, wo.kpb_ke, wo.km)       
        return res
  
    def button_dummy(self, cr, uid, ids, context=None):
        return True
    
    def wkf_approve_order(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'approved', 'date_approve': fields.date.context_today(self,cr,uid,context=context)})
       
        return True
        
    def invoice_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return True
    
    def wkf_po_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        
    def wo_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'})

    def start2(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state_wo':False})
    
    def start_wo(self, cr, uid, ids, context=None):
        self.signal_workflow(cr, uid, ids, 'in_progress')
    
    def break_wo(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state_wo':'break'})
    
    def end_break_wo(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state_wo':'in_progress'})
    
    def end_wo(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state_wo':'finish'})
    
    def finished(self, cr, uid, ids, context=None):        
        return self.write(cr, uid, ids, {'state':'finished'})
    
    def invoice_create_wo(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        # for move in val.picking_ids.move_lines:
        #     move.write({'state': 'assigned'})
        self.signal_workflow(cr, uid, ids, 'invoice_create')
        return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        for wo in self.browse(cr, uid, ids):
            if wo.state_wo:
                raise osv.except_osv(('Perhatian !'), ("WO %s sudah di proses, tidak bisa di cancel")%(wo.name))
            for line in wo.work_lines:
                if line.supply_qty > 0:
                    raise osv.except_osv(('Perhatian !'), ("WO %s sudah di proses, tidak bisa di cancel")%(wo.name))
            wo.picking_ids.action_cancel()
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        cr.execute('UPDATE dym_work_order '\
                   'SET state=%s '\
                   'WHERE id IN %s', ('cancel', tuple(ids),))
        return True

    def wkf_action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True
        
    def dym_collected_ok(self, cr, uid, ids, context=None):
        kpb_state = self.browse(cr, uid , ids).collected_ok_not
        self.write(cr, uid, ids, {'kpb_collected':kpb_state}, context=context)    
        self.write(cr, uid, ids, {'kpb_collected_date':datetime.today()}, context=context)                                                 
        return True
    
    def _get_branch_journal_config(self,cr,uid,branch_id):
        result = {}
        obj_branch_config_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
        if not obj_branch_config_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak Ditemukan konfigurasi jurnal Cabang, Silahkan konfigurasi dulu"))
        else:
            
            obj_branch_config = self.pool.get('dym.branch.config').browse(cr,uid,obj_branch_config_id[0])
            if not(obj_branch_config.wo_account_potongan_langsung_id.id and obj_branch_config.wo_journal_psmd_id.id and obj_branch_config.wo_account_sisa_subsidi_id.id and obj_branch_config.wo_account_potongan_subsidi_id.id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi jurnal penjualan cabang belum lengkap, silahkan setting dulu"))
        return obj_branch_config

    def invoice_create(self, cr, uid, ids, context=None):
        invoice_id = self.action_invoice_create(cr, uid, ids, category='Service', context=context)
        return invoice_id

    def invoice_sparepart_create(self, cr, uid, ids, context=None):
        invoice_id = self.action_invoice_create(cr, uid, ids, category='Sparepart', context=context)
        return invoice_id

    def action_invoice_create(self, cr, uid, ids, category=False, context=None):
        force_cogs = 0.0   
        val = self.browse(cr, uid, ids, context={})[0]
        self.write(cr, uid, ids, {'date':datetime.today()})
        customer = self._get_customer_id(cr, uid, ids,val.type,val.customer_id.id,val.branch_id.id)
        account_and_journal = self._get_jornal_id(cr, uid, ids,val.branch_id.id,val.type) 
             
        obj_inv = self.pool.get('account.invoice') 
        obj_inv_line = self.pool.get('account.invoice.line') 
         
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr,uid,[ ('model','=',self.__class__.__name__) ])
        
        invoice_pelunasan = {}
        invoice_pelunasan_line = []

        invoice_insentif_finco = {}
        invoice_insentif_finco_line = []

        obj_branch_config = self._get_branch_journal_config(cr,uid,val.branch_id.id)
        cc_string = 'Service'
        if category == 'Sparepart':
            cc_string = 'Sparepart_Accesories'
        analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, category, False, 4, cc_string)
        analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, category, False, 4, 'General')
        finco = False
        invoice_pelunasan = {
            'name':val.name,
            'origin': val.name,
            'branch_id':val.branch_id.id,
            'division':val.division,
            'partner_id':customer,
            'date_invoice':val.date,
            'reference_type':'none',
            'type': 'out_invoice', 
            'tipe': 'customer',
            'journal_id':account_and_journal['journal_id'],
            'account_id':account_and_journal['account_id'],
            'transaction_id':val.id,
            'model_id':obj_model_id[0],
            'comment':val.note,
            'analytic_1': analytic_1_general,
            'analytic_2': analytic_2_general,
            'analytic_3': analytic_3_general,
            'analytic_4': analytic_4_general,
        }

        per_product = {}
        per_potongan = {}
        per_barang_bonus = {}
        per_invoice = []

        obj_line = self.pool.get('account.invoice.line') 
        work_id_lines = []
        
        per_barang_bonus = {}
        for line in val.work_lines:
            if line.product_id.product_tmpl_id.is_bundle:
                has_category = False
                for bundle_line in line.bundle_line:
                    if bundle_line.product_id.categ_id.get_root_name() == category and (bundle_line.supply_qty > 0 or category == 'Service'):
                        has_category = True
                if has_category == False:
                    continue
            if line.categ_id != category and not line.product_id.product_tmpl_id.is_bundle:
                continue
            if line.categ_id == "Service" or line.product_id.product_tmpl_id.is_bundle:
                qty=line.product_qty
            elif line.categ_id == "Sparepart" :
                qty=line.supply_qty
                if qty <=0:
                    continue

            if not line.product_id.product_tmpl_id.is_bundle:
                if not per_product.get(line.product_id.id,False):
                    per_product[line.product_id.id] = {}
                per_product[line.product_id.id]['price_unit'] = line.price_unit
                per_product[line.product_id.id]['product_qty'] = per_product[line.product_id.id].get('product_qty',0)+qty
                per_product[line.product_id.id]['categ_id'] = line.categ_id
                per_product[line.product_id.id]['tax_id'] = [(6, 0, [y.id for y in line.tax_id])]
                per_product[line.product_id.id]['discount'] = line.discount

            else:
                for bundle_line in line.bundle_line:
                    if bundle_line.product_id.categ_id.get_root_name() != category or bundle_line.price_bundle <= 0 or (bundle_line.supply_qty <= 0 and bundle_line.product_id.categ_id.isParentName('Sparepart')):
                        continue
                    if not per_product.get(bundle_line.product_id.id,False):
                        per_product[bundle_line.product_id.id] = {}
                    per_product[bundle_line.product_id.id]['price_unit'] = bundle_line.price_bundle
                    if bundle_line.product_id.categ_id.isParentName('Sparepart'):
                        per_product[bundle_line.product_id.id]['product_qty'] = per_product[bundle_line.product_id.id].get('product_qty',0)+bundle_line.supply_qty
                    else:
                        per_product[bundle_line.product_id.id]['product_qty'] = per_product[bundle_line.product_id.id].get('product_qty',0)+bundle_line.product_uom_qty
                    per_product[bundle_line.product_id.id]['categ_id'] = category
                    per_product[bundle_line.product_id.id]['tax_id'] = [(6, 0, [y.id for y in line.tax_id])]
                    per_product[bundle_line.product_id.id]['discount'] = bundle_line.diskon

                    if not line.categ_id_2.bisnis_unit:
                        per_potongan['discount_bundle'] = per_potongan.get('discount_bundle',0)+bundle_line.diskon
                    else:
                        per_potongan['discount_bundle_acc'] = per_potongan.get('discount_bundle_acc',0)+bundle_line.diskon
            per_potongan['tax_id'] = [(6, 0, [y.id for y in line.tax_id])]
            if line.categ_id != category:
                continue

            # Disabled by Iman
            if line.categ_id == "Service":
                per_potongan['discount'] = per_potongan.get('discount',0)+line.discount
            if line.categ_id == "Sparepart":
                if not line.categ_id_2.bisnis_unit:
                    per_potongan['discount'] = per_potongan.get('discount',0)+(line.discount_pcs*line.supply_qty)
                else:
                    per_potongan['discount_acc'] = per_potongan.get('discount_acc',0)+(line.discount_pcs*line.supply_qty)
                    analytic_acc_1, analytic_acc_2, analytic_acc_3, analytic_acc_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, category, line.categ_id_2, 4, cc_string)

            date_due_default = datetime.now().strftime('%Y-%m-%d')
            if val.branch_id.default_supplier_workshop_id.property_payment_term:
                pterm_list = val.branch_id.default_supplier_workshop_id.property_payment_term.compute(value=1, date_ref=date_due_default)[0]
                if pterm_list:
                    date_due_default = max(line_2[0] for line_2 in pterm_list)

            for disc in line.discount_line:
                invoice_ps_finco = {}
                invoice_ps_finco_line = []

                if disc.tipe_diskon == 'percentage':
                    total_diskon = disc.discount_pelanggan
                    if disc.tipe_diskon == 'percentage':
                        total_diskon = line.price_unit * disc.discount_pelanggan / 100
                    if not line.categ_id_2.bisnis_unit:                 
                        per_potongan['discount_pelanggan'] = per_potongan.get('discount_pelanggan',0)+(total_diskon*qty)
                    else:
                        per_potongan['discount_pelanggan_acc'] = per_potongan.get('discount_pelanggan_acc',0)+(total_diskon*qty)
                else:
                    total_claim_discount = disc.ps_ahm + disc.ps_md + disc.ps_finco + disc.ps_others + disc.ps_dealer
                    total_diskon_pelanggan = 0 if total_claim_discount - disc.discount_pelanggan >= disc.ps_dealer else disc.ps_dealer - (total_claim_discount - disc.discount_pelanggan)
                    total_diskon_external = disc.discount_pelanggan - total_diskon_pelanggan
                    if not line.categ_id_2.bisnis_unit:                 
                        per_potongan['discount_external'] = per_potongan.get('discount_external',0)+(total_diskon_external*qty)
                        per_potongan['discount_pelanggan'] = per_potongan.get('discount_pelanggan',0)+(total_diskon_pelanggan*qty)
                    else:
                        per_potongan['discount_external_acc'] = per_potongan.get('discount_external_acc',0)+(total_diskon_external*qty)
                        per_potongan['discount_pelanggan_acc'] = per_potongan.get('discount_pelanggan_acc',0)+(total_diskon_pelanggan*qty)

                if disc.tipe_diskon == 'percentage':
                    continue
                discount_gap = 0.0
                discount_md = 0.0
                discount_finco = 0.0
                discount_oi = 0.0
                sisa_ke_finco = False
                
                if disc.discount_pelanggan != disc.discount:
                     discount_gap =  disc.discount - disc.discount_pelanggan
                     print discount_gap
                
                if (disc.ps_ahm > 0 or disc.ps_md > 0):
                    invoice_md = {}
                    invoice_md_line = []
        
                    if not (obj_branch_config.wo_journal_psmd_id.default_credit_account_id.id and obj_branch_config.wo_journal_psmd_id.default_debit_account_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal PS MD belum lengkap!"))
                    if not val.branch_id.default_supplier_workshop_id.id:
                        raise osv.except_osv(('Perhatian !'), ("Principle workshop di branch belum diisi, silahkan setting dulu!"))
                    invoice_md = {
                        'branch_id':val.branch_id.id,
                        'division':val.division,
                        'partner_id':val.branch_id.default_supplier_workshop_id.id,
                        'date':datetime.now().strftime('%Y-%m-%d'), 
                        'date_due': date_due_default, 
                        'reference': val.name, #
                        'name':val.name,
                        'user_id': val.confirm_uid.id or val.write_uid.id or val.create_uid.id,
                        'journal_id': obj_branch_config.wo_journal_psmd_id.id,
                        'account_id': obj_branch_config.wo_journal_psmd_id.default_debit_account_id.id,
                        'type': 'sale',
                        'analytic_1': analytic_1_general,
                        'analytic_2': analytic_2_general,
                        'analytic_3': analytic_3_general,
                        'analytic_4': analytic_4_general,      
                    }
                    
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
                                'account_id': obj_branch_config.wo_journal_psmd_id.default_credit_account_id.id,
                                'type': 'cr',
                                'analytic_1': analytic_1,
                                'analytic_2': analytic_2,
                                'analytic_3': analytic_3,
                                'account_analytic_id': analytic_4,    
                            }])
                        
                        if discount_oi>0:
                            invoice_md_line.append([0,False,{
                                'name': 'Sisa subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                'amount': discount_gap,
                                'account_id': obj_branch_config.wo_account_sisa_subsidi_id.id,
                                'type': 'cr',
                                'analytic_1': analytic_1,
                                'analytic_2': analytic_2,
                                'analytic_3': analytic_3,
                                'account_analytic_id': analytic_4,    
                            }])
                    else:
                        invoice_md_line.append([0,False,{
                            'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                            'amount': disc.ps_ahm+disc.ps_md,
                            'account_id': obj_branch_config.wo_journal_psmd_id.default_credit_account_id.id,
                            'type': 'cr',
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id': analytic_4,    
                        }])
                            
                    invoice_md['line_cr_ids'] = invoice_md_line
                    
                    per_invoice.append(invoice_md)

            for barang_bonus in line.barang_bonus_line:
                if not per_barang_bonus.get(barang_bonus.product_subsidi_id.id,False):
                    per_barang_bonus[barang_bonus.product_subsidi_id.id] = {}
                per_barang_bonus[barang_bonus.product_subsidi_id.id]['product_qty'] = per_barang_bonus[barang_bonus.product_subsidi_id.id].get('product_qty',0)+ barang_bonus.barang_qty
                per_barang_bonus[barang_bonus.product_subsidi_id.id]['force_cogs'] = per_barang_bonus[barang_bonus.product_subsidi_id.id].get('force_cogs',0)+barang_bonus.price_barang
                if barang_bonus.bb_md > 0 or barang_bonus.bb_ahm > 0:
                    invoice_bb_md = {}
                    invoice_bb_md_line = []
                    
                    if not (obj_branch_config.wo_journal_bbmd_id.default_credit_account_id.id and obj_branch_config.wo_journal_bbmd_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal Barang Subsidi belum lengkap!"))
                    invoice_bb_md = {
                        'branch_id':val.branch_id.id,
                        'division':val.division,
                        'partner_id':val.branch_id.default_supplier_id.id,
                        'date':datetime.now().strftime('%Y-%m-%d'), 
                        'date_due': date_due_default, 
                        'reference': val.name,
                        'name':val.name,
                        'user_id': val.confirm_uid.id or val.write_uid.id or val.create_uid.id,
                        'journal_id': obj_branch_config.wo_journal_bbmd_id.id,
                        'account_id': obj_branch_config.wo_journal_bbmd_id.default_debit_account_id.id,
                        'type': 'sale',
                        'analytic_1': analytic_1_general,
                        'analytic_2': analytic_2_general,
                        'analytic_3': analytic_3_general,
                        'analytic_4': analytic_4_general,      
                    }
                    invoice_bb_md_line = [[0,False,{
                        'name': 'Subsidi '+barang_bonus.barang_subsidi_id.name+' '+line.product_id.name,
                        'amount': barang_bonus.bb_ahm+barang_bonus.bb_md,
                        'account_id': obj_branch_config.wo_journal_bbmd_id.default_credit_account_id.id,
                        'type': 'cr',
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id': analytic_4,    
                    }]]
                    invoice_bb_md['line_cr_ids'] = invoice_bb_md_line
                    per_invoice.append(invoice_bb_md)

        for key, value in per_product.items():
            if value['price_unit'] > 0:
                product_id = self.pool.get('product.product').browse(cr,uid,key)
                fake_line_ids = []
                list_product_bundle = ''
                if product_id.product_tmpl_id.is_bundle:
                    fake_line_ids = product_id.product_tmpl_id.item_ids
                    for fake_line in fake_line_ids:
                        if fake_line.product_id.type != 'service':
                            force_cogs += self._get_moved_price(cr,uid,val.picking_ids,fake_line.product_id)
                else:
                    if value['categ_id']=='Sparepart':
                        force_cogs = self._get_moved_price(cr,uid,val.picking_ids,product_id)

                analytic_prod_1, analytic_prod_2, analytic_prod_3, analytic_prod_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, category, product_id.categ_id, 4, cc_string)
                invoice_pelunasan_line.append([0,False,{
                        'name':product_id.name + list_product_bundle,
                        'product_id':product_id.id,
                        'quantity':value['product_qty'],
                        'origin':val.name,
                        'price_unit':value['price_unit'],
                        'invoice_line_tax_id': value['tax_id'],
                        'account_id': self.pool.get('product.product')._get_account_id(cr,uid,ids,product_id.id),
                        'force_cogs': force_cogs,
                        'analytic_1': analytic_prod_1,
                        'analytic_2': analytic_prod_2,
                        'analytic_3': analytic_prod_3,
                        'account_analytic_id':analytic_prod_4,  
                   }])

        for key, value in per_potongan.items():
            if value > 0:
                price_unit = -1*value
                tax = per_potongan['tax_id']
                if key=='discount':
                    invoice_pelunasan_line.append([0,False,{
                            'name': 'Diskon Reguler',
                            'quantity':1,
                            'origin':val.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': obj_branch_config.wo_account_potongan_langsung_id.id,
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])
                
                if key=='discount_pelanggan':
                    invoice_pelunasan_line.append([0,False,{
                            'name': 'Diskon Dealer',
                            'quantity':1,
                            'origin':val.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': obj_branch_config.wo_account_potongan_subsidi_id.id,
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])

                if key=='discount_external':
                    # invoice_pelunasan['discount_program'] = value
                    if not obj_branch_config.wo_account_potongan_subsidi_external_id:
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan subsidi external di branch config belum ada!"))
                    invoice_pelunasan_line.append([0,False,{
                            'name': 'Diskon External',
                            'quantity':1,
                            'origin':val.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': obj_branch_config.wo_account_potongan_subsidi_external_id.id,
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])

                if key=='discount_bundle':
                    if not obj_branch_config.wo_account_potongan_bundle_id:
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon bundle cabang belum lengkap, silahkan setting dulu"))
                    invoice_pelunasan_line.append([0,False,{
                            'name': 'Diskon Bundle',
                            'quantity':1,
                            'origin':val.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': obj_branch_config.wo_account_potongan_bundle_id.id,
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])

                if key=='discount_acc':
                    invoice_pelunasan_line.append([0,False,{
                            'name': 'Diskon Reguler Acc',
                            'quantity':1,
                            'origin':val.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': obj_branch_config.wo_account_potongan_langsung_id.id,
                            'analytic_1': analytic_acc_1,
                            'analytic_2': analytic_acc_2,
                            'analytic_3': analytic_acc_3,
                            'account_analytic_id':analytic_acc_4,  
                        }])

                if key=='discount_pelanggan_acc':
                    invoice_pelunasan_line.append([0,False,{
                            'name': 'Diskon Dealer Acc',
                            'quantity':1,
                            'origin':val.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': obj_branch_config.wo_account_potongan_subsidi_id.id,
                            'analytic_1': analytic_acc_1,
                            'analytic_2': analytic_acc_2,
                            'analytic_3': analytic_acc_3,
                            'account_analytic_id':analytic_acc_4,  
                        }])


                if key=='discount_external_acc':
                    # invoice_pelunasan['discount_program'] = value
                    if not obj_branch_config.wo_account_potongan_subsidi_external_id:
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan subsidi external di branch config belum ada!"))
                    invoice_pelunasan_line.append([0,False,{
                            'name': 'Diskon External Acc',
                            'quantity':1,
                            'origin':val.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': obj_branch_config.wo_account_potongan_subsidi_external_id.id,
                            'analytic_1': analytic_acc_1,
                            'analytic_2': analytic_acc_2,
                            'analytic_3': analytic_acc_3,
                            'account_analytic_id':analytic_acc_4,  
                        }])


                if key=='discount_bundle_acc':
                    if not obj_branch_config.wo_account_potongan_bundle_id:
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon bundle cabang belum lengkap, silahkan setting dulu"))
                    invoice_pelunasan_line.append([0,False,{
                            'name': 'Diskon Bundle Acc',
                            'quantity':1,
                            'origin':val.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': obj_branch_config.wo_account_potongan_bundle_id.id,
                            'analytic_1': analytic_acc_1,
                            'analytic_2': analytic_acc_2,
                            'analytic_3': analytic_acc_3,
                            'account_analytic_id':analytic_acc_4,  
                        }])

        for value in per_invoice:
            create_ar = self.pool.get('account.voucher').create(cr,uid,value,context=context)
        invoice_pelunasan['invoice_line'] = invoice_pelunasan_line
        move=obj_inv.create(cr,uid,invoice_pelunasan)
        obj_inv.button_reset_taxes(cr,uid,move)
        netsvc.LocalService("workflow").trg_validate(uid, 'account.invoice', move, 'invoice_open', cr) 
        self.write(cr, uid, ids, {'state': 'open'})
        # packing = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id', '=', val.picking_ids.id),('state','not in',('draft','cancelled'))])
        # print packing,'------------Packing ID'
        # packing_id = self.pool.get('dym.stock.packing').browse(cr,uid,packing).id
        # print packing_id,'packing_id---------\n'
        # post = self.pool.get('dym.stock.packing').post(cr, uid, packing_id, context)
        if not val.faktur_pajak_id:
            if val.amount_tax and not val.pajak_gabungan and not val.pajak_gunggung :
                self.pool.get('dym.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'dym.work.order',context=context) 
            if val.amount_tax and val.pajak_gunggung == True :   
                self.pool.get('dym.faktur.pajak.out').create_pajak_gunggung(cr,uid,ids,'dym.work.order',context=context) 
        return move

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        todo = []
        for po in self.browse(cr, uid, ids, context=context):
            if not po.work_lines:
                raise osv.except_osv(_('Error!'),_('You cannot confirm a work order without any work oder order line.'))
            for line in po.work_lines:
                if po.type=='WAR' and not line.job_redo:
                    continue
                if line.categ_id == 'Sparepart' and line.is_bundle == False:
                    if not line.location_id:
                        raise osv.except_osv(_('Error!'),_('Mohon isi lokasi untuk produk %s.')%(line.product_id.product_tmpl_id.name))
                    if line.qty_available <= 0 or line.qty_available < line.product_qty:
                        raise osv.except_osv(_('Error!'),_('Stock product %s tidak cukup')%(line.product_id.product_tmpl_id.name))
                for barang_bonus in line.barang_bonus_line:
                    barang_bonus.write({'force_cogs':barang_bonus.price_barang})
        for id in ids:
            self.write(cr, uid, [id], {'state' : 'confirmed'})
        return True

    def has_sparepart(self, cr, uid, ids, invoice=False, *args):
        for order in self.browse(cr, uid, ids):
            if order.type == 'WAR':
                return False
            for work_lines in order.work_lines:
                if work_lines.product_id.product_tmpl_id.is_bundle:
                    for bundle_line in work_lines.bundle_line:
                        if bundle_line.product_id.categ_id.isParentName('Sparepart') and (not invoice or (invoice and bundle_line.price_bundle > 0 and bundle_line.supply_qty > 0)):
                            return True
                elif work_lines.product_id and work_lines.categ_id == "Sparepart" and (not invoice or (work_lines.price_unit > 0 and invoice and work_lines.supply_qty > 0)):
                    return True
                else:
                    if work_lines.barang_bonus_line and not invoice:
                        for barang_bonus in work_lines.barang_bonus_line:
                            if barang_bonus.product_subsidi_id.type != 'service':
                                return True
        return False
    
    def test_moves_except(self, cr, uid, ids, context=None):
        at_least_one_canceled = False
        alldoneorcancel = True
        for purchase in self.browse(cr, uid, ids, context=context):
            for picking in purchase.picking_ids:
                if picking.state == 'cancel':
                    at_least_one_canceled = True
                if picking.state not in ['done', 'cancel']:
                    alldoneorcancel = False
        return at_least_one_canceled and alldoneorcancel
    

    def _prepare_order_line_move(self, cr, uid, order, work_lines, picking_id, context=None):
        res = []
        fake_line_ids = []
        if work_lines.product_id.product_tmpl_id.is_bundle:
            fake_line_ids = work_lines.bundle_line
        else:
            fake_line_ids.append(work_lines)
        location = self._get_dest_location_wo(cr,uid,order.id)
        for fake_line in fake_line_ids:
            location_destination = location['destination']
            if order.branch_id.kpb_ganti_oli_barang == True and order.kpb_ke == '1' and order.type == 'KPB' and fake_line.product_id.is_oli == True:
                location_dest_search = self.pool.get('stock.location').search(cr, uid, [('usage','=','kpb'),('branch_id','=',order.branch_id.id)])
                if not location_dest_search:
                    raise osv.except_osv(('Invalid action !'), ('Tidak ditemukan lokasi kpb di branch %s') % (order.branch_id.name,))
                location_destination = location_dest_search[0]
            if work_lines.product_id.product_tmpl_id.is_bundle:
                product_qty = fake_line.product_uom_qty
            else:
                product_qty = fake_line.product_qty
            if fake_line.product_id.type != 'service':
                average_price = self.pool.get('product.price.branch')._get_price(cr, uid, work_lines.location_id.warehouse_id.id, fake_line.product_id.id)
                move_template = {
                            'name': work_lines.name or '',
                            'categ_id': fake_line.product_id.categ_id.id,
                            'product_uom': fake_line.product_id.uom_id.id,
                            'product_uos': fake_line.product_id.uom_id.id,
                            'picking_id': picking_id,
                            'picking_type_id':location['picking_type_id'], 
                            'work_order_line_id':work_lines.id,
                            'product_id': fake_line.product_id.id,
                            'product_uos_qty': product_qty,
                            'product_uom_qty': product_qty,
                            'state': 'draft',
                            'location_id': fake_line.location_id.id,
                            'location_dest_id': location_destination,
                            'branch_id': work_lines.work_order_id.branch_id.id,
                            'price_unit': average_price,
                            'origin': work_lines.work_order_id.name
                }
                res.append(move_template)
        return res
        
    def _create_stock_moves(self, cr, uid, order, order_lines, picking_id=False, context=None):
        stock_move = self.pool.get('stock.move')
        todo_moves = []
        barang_bonuses = {}
        for work_lines in order_lines:
            if not work_lines.product_id:
                continue
            if self.pool.get('stock.move').search(cr, uid, [('work_order_line_id','=',work_lines.id)]):
                continue
            # if work_lines.categ_id == "Sparepart" and work_lines.state == "confirmed": 
            if self.check_procurement_needed(cr, uid, work_lines.product_id, context=context) and work_lines.state == "confirmed":
                for vals in self._prepare_order_line_move(cr, uid, order, work_lines, picking_id, context=context):
                    self.pool.get('dym.work.order.line').write(cr,uid,work_lines.id,{'state': 'open'}, context=context)
                    move = stock_move.create(cr, uid, vals, context=context)
                    todo_moves.append(move)

            if work_lines.barang_bonus_line:
                for barang_bonus in work_lines.barang_bonus_line:
                    if not barang_bonuses.get(barang_bonus.product_subsidi_id.id,False):
                        barang_bonuses[barang_bonus.product_subsidi_id.id] = {}
                    barang_bonuses[barang_bonus.product_subsidi_id.id]['qty'] = barang_bonuses[barang_bonus.product_subsidi_id.id].get('qty',0) + barang_bonus.barang_qty
                    barang_bonuses[barang_bonus.product_subsidi_id.id]['price_barang'] = barang_bonuses[barang_bonus.product_subsidi_id.id].get('price_barang',0) + barang_bonus.price_barang
                    barang_bonuses[barang_bonus.product_subsidi_id.id]['line'] = work_lines
        location = self._get_dest_location_wo(cr,uid,order.id)
        for key, value in barang_bonuses.items():
            product_id = self.pool.get('product.product').browse(cr,uid,key)
            vals = {
                    'name': product_id.partner_ref,
                    'categ_id': product_id.categ_id.id,
                    'product_id': product_id.id,
                    'product_uom_qty': value.get('qty',0),
                    'location_id': location['source'],
                    'invoice_state': 'invoiced',
                    'product_uom': product_id.uom_id.id,#key.uom_id,
                    'location_dest_id': location['destination'],
                    'branch_id': order.branch_id.id,
                    'division': order.division,
                    'origin': order.name,
                    'undelivered_value': value.get('price_barang',0),
                    'picking_id': picking_id,
                    'work_order_line_id':value['line'].id or False,
                    'state': 'draft',
                    }
            move = stock_move.create(cr, uid, vals, context=context)
            todo_moves.append(move)
        todo_moves = stock_move.action_confirm(cr, uid, todo_moves)
        stock_move.action_assign(cr, uid, todo_moves)
    

    def action_picking_create(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids):
            obj_model = self.pool.get('ir.model')
            obj_model_id = obj_model.search(cr,uid,[ ('model','=',order.__class__.__name__) ])
            obj_model_id_model = obj_model.browse(cr,uid,obj_model_id).id
            location = self._get_dest_location_wo(cr,uid,order.id)
            picking_vals = {
                'picking_type_id': location['picking_type_id'],
                'division':'Sparepart',
                'move_type': 'direct',
                'branch_id': order.branch_id.id,
                'partner_id': order.customer_id.id,
                'invoice_state': 'none',
                'transaction_id': order.id,
                'model_id': obj_model_id_model,
                'origin': order.name
            }
            picking_id = self.pool.get('stock.picking').create(cr, uid, picking_vals, context=context)
            self._create_stock_moves(cr, uid, order, order.work_lines, picking_id, context=context)

    def picking_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'shipped':1}, context=context)
        return True   
    
    def has_service(self, cr, uid, ids, invoice=False, *args):
        for order in self.browse(cr, uid, ids):
            if order.type == 'WAR' and invoice == True:
                return False
            for work_lines in order.work_lines:
                if work_lines.product_id.product_tmpl_id.is_bundle and not invoice:
                    for bundle_line in work_lines.bundle_line:
                        if bundle_line.product_id and bundle_line.product_id.type == 'service':
                            return True
                else:
                    if work_lines.product_id and work_lines.categ_id == "Service":
                        return True
        return False

    def view_invoice(self,cr,uid,ids,context=None):
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
        
        if len(obj)>0:
            result['domain'] = "[('id','in',["+','.join(map(str, obj))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = obj[0] 
        return result

    def get_uang_muka(self,cr,uid,ids,wo_name,context=None):
        obj_inv = self.pool.get('account.invoice')
        invoice_ids = obj_inv.search(cr, uid, [('origin','ilike',wo_name),('type','=','out_invoice')])
        uang_muka = 0
        for inv in obj_inv.browse(cr, uid, invoice_ids):
            for payment in inv.payment_ids:
                if payment.date <= inv.date_invoice:
                    uang_muka += payment.credit
        if invoice_ids:
            import locale
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
            return inv.currency_id.symbol + ' ' + locale.format("%d", uang_muka, grouping=True)
        else:
            return 'Rp 0'

    def get_terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil

    def get_no_kuitansi(self,cr,uid,ids,wo_name,categ=False,context=None):
        obj_inv = self.pool.get('account.invoice')
        invoice_ids = obj_inv.search(cr, uid, [('origin','ilike',wo_name),('type','=','out_invoice')])
        payments = []
        for inv in obj_inv.browse(cr, uid, invoice_ids):
            for paym in inv.payment_ids:
                if not paym.move_id.name in payments:
                    payments.append(paym.move_id.name)
        if not payments:
            return '-'
        else:
            return ', '.join(payments)
    
    def get_no_invoice(self,cr,uid,ids,wo_name,categ=False,context=None):
        obj_inv = self.pool.get('account.invoice')
        invoice_ids = obj_inv.search(cr, uid, [('origin','ilike',wo_name),('type','=','out_invoice')])
        for inv in obj_inv.browse(cr, uid, invoice_ids):
            if categ:
                for line in inv.invoice_line:
                    if line.product_id.categ_id.isParentName(categ):
                        return inv.number
            else:
                return ', '.join(inv.mapped('number'))
        return '-'

    def get_tanggal_invoice(self,cr,uid,ids,wo_name,context=None):
        obj_inv = self.pool.get('account.invoice')
        invoice_ids = obj_inv.search(cr, uid, [('origin','ilike',wo_name),('type','=','out_invoice')])
        for inv in obj_inv.browse(cr, uid, invoice_ids):
            return inv.date_invoice and datetime.strptime(inv.date_invoice, '%Y-%m-%d').strftime("%d-%m-%Y") or None
        return '-'

    def action_view_picking(self,cr,uid,ids,context=None):  
        val = self.browse(cr, uid, ids, context={})[0]
        obj_inv = self.pool.get('stock.picking')
        obj = obj_inv.search(cr,uid,[('transaction_id','=',val.id),('model_id','=',self.__class__.__name__)])
        return {
            'name': 'Picking Slip',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': obj[0]
            } 
        
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Cannot delete a work order which is in state \'%s\'!') % (val.state,))
        return super(dym_work_order, self).unlink(cr, uid, ids, context=context) 
    
    def _get_moved_price(self,cr,uid,picking_ids,product_id):
        move_price = 0.0
        for picking in picking_ids:
            for move in picking.move_lines:
                if move.product_id.id == product_id.id and move.state=='done':
                    move_price += move.price_unit*move.product_qty
        return move_price



class dym_work_order_line(osv.osv):
    _name = "dym.work.order.line"

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

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            discount_program = 0
            for program_line in line.discount_line:
                if program_line.tipe_diskon == 'percentage':
                    discount_program += (line.price_unit * program_line.discount_pelanggan / 100)
                else:
                    discount_program += program_line.discount_pelanggan 
            discount_program = discount_program * line.product_qty
            price = (line.price_unit*line.product_qty) - line.discount - discount_program - line.discount_bundle
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, 1, line.product_id)
            res[line.id]=taxes['total']
        return res

    def create_price(self, cr, uid, ids,price_unit):
        value = {}
        
        if not price_unit:
           value ={'price_unit_show':0,'discount_persen':0}
        else:
            value={'price_unit_show':price_unit,'discount_persen':0}
        return {'value':value}
    

    def create_qty_available(self, cr, uid, ids,qty_available):
        value = {}
        if not qty_available:
           value ={'qty_available_show':0}
        else:
            value={'qty_available_show':qty_available}
        return {'value':value}
    
    def create_supply_qty(self, cr, uid, ids,supply_qty):
        value = {}
        if not supply_qty:
           value ={'supply_qty_show':0}
        else:
            value={'supply_qty_show':supply_qty}
        return {'value':value}

    def onchange_job_redo(self, cr, uid, ids, job_redo):
        return True

    def product_qty_change(self, cr, uid, ids, product_qty, qty_available, discount_persen, discount_pcs, discount, price_unit, field, disc_persen=False, disc_amount=False, disc_sum=False):
        value = {}
        warning = {}
        if product_qty <= 0:
           value['product_qty'] = 1
           warning = {'title': 'perhatian!', 'message':'Quantity minimal 1!'}
        if product_qty > qty_available:
            lost_order_qty = product_qty - qty_available
            value['lost_order_qty'] = lost_order_qty
            if qty_available > 0:
                value['product_qty'] = qty_available
        else:
            value['lost_order_qty'] = 0
        qty = product_qty
        if 'product_qty' in value:
            qty = value['product_qty']
        fill_discount = self.change_discount_persen(cr, uid, ids, discount_persen, discount_pcs, discount, price_unit, qty, field, disc_persen=disc_persen, disc_amount=disc_amount, disc_sum=disc_sum)
        value.update(fill_discount['value'])
        return {'value':value,'warning':warning}
        
    def create_warranty(self, cr, uid, ids,warranty):
        value = {}
        if not warranty:
           value ={'warranty_show':0}
        else:
            value={'warranty_show':warranty}
        return {'value':value}
    
    def create_name(self, cr, uid, ids,name):
        value = {}
        if not name:
           value ={'name_show':' '}
        else:
            value={'name_show':name}
        return {'value':value}
    
    def _get_price(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.browse(cr, uid, ids, context=context):
            price_unit_show=price.price_unit
            res[price.id]=price_unit_show
        return res
    
    
    
    def _get_supply_qty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for supply in self.browse(cr, uid, ids, context=context):
            supply_qty_show=supply.supply_qty
            res[supply.id]=supply_qty_show
        return res
    
    def _get_qty_available(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for qty in self.browse(cr, uid, ids, context=context):
            qty_available_show=qty.qty_available
            res[qty.id]=qty_available_show
        return res
    
    def _get_warranty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for warranty in self.browse(cr, uid, ids, context=context):
            warranty_show=warranty.warranty
            res[warranty.id]=warranty_show
        return res
    

    def _get_name(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            # name_show=line.name
            name_show=line.product_id.default_code
            res[line.id]=name_show
        return res
    
    def _get_harga_jasa(self, cr, uid, ids, product_id,branch_id,product_unit_id,context=None):
        categori_workshop =self.pool.get('dym.branch').browse(cr,uid,branch_id).workshop_category.id
        product_unit =self.pool.get('product.product').browse(cr,uid,product_unit_id).category_product_id.id
        harga_jasa_id=self.pool.get('dym.harga.jasa').search(cr,uid,[('product_id_jasa','=',product_id),('workshop_category','=',categori_workshop),('category_product_id','=',product_unit)])
        harga_jasa=self.pool.get('dym.harga.jasa').browse(cr,uid,harga_jasa_id).price
        return harga_jasa
    
    def _get_price_list(self, cr, uid, ids,branch_id,context=None):
        branch_price =self.pool.get('dym.branch').browse(cr,uid,branch_id).pricelist_part_sales_id.id
        return branch_price
    
    def _get_product(self,cr, uid, ids, categ_id,type,kpb_ke,context=None):
            categ_ids = self.pool.get('product.category').get_child_by_ids(cr,uid,[categ_id])
            return categ_ids   
        
    def _get_branch(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for wo in self.browse(cr, uid, ids):
            res[wo.id] = {
                'branch_dummy': 0,
                'division_dummy': '',
                'customer_dummy': 0,
                
            }
            for work_order in self.pool.get('dym.work.order').browse(cr,uid,wo.work_order_id.id):
                res[wo.id]['branch_dummy'] = work_order.branch_id.id
                res[wo.id]['division_dummy'] = work_order.division
                res[wo.id]['customer_dummy'] = work_order.customer_id.id
                
        return res

    def _get_discount(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('dealer.sale.order.line.discount.line').browse(cr, uid, ids, context=context):
            result[line.dealer_sale_order_line_discount_line_id.id] = True
        return result.keys()

    def _amount_discount_program(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for wo_line in self.browse(cr, uid, ids, context=context):
            res[wo_line.id] = {
                'discount_program': 0.0,
            }
            val = 0
            for line in wo_line.discount_line:
                if line.tipe_diskon == 'percentage':
                    val += (wo_line.price_unit * line.discount_pelanggan / 100)
                else:
                    val += line.discount_pelanggan 
            res[wo_line.id]['discount_program'] = val * wo_line.product_qty
           
        return res   

    def _amount_discount_bundle(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for wo_line in self.browse(cr, uid, ids, context=context):
            res[wo_line.id] = {
                'discount_bundle': 0.0,
            }
            val = 0
            for line in wo_line.bundle_line:
                val += line.diskon
            res[wo_line.id]['discount_bundle'] = val * wo_line.product_qty
           
        return res   

    def _count_wo(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for wol in self.browse(cr, uid, ids, context=context):
            res[wol.id] = {
                'count_wo': 0,
            }            
            if wol.id == wol.work_order_id.work_lines.sorted(key=lambda r: r.id)[0].id:
                res[wol.id]['count_wo'] = 1
            else:
                res[wol.id]['count_wo'] = 0
        return res

    def _get_wo(self, cr, uid, ids, context=None):
        wo_ids = self.pool.get('dym.work.order.line').search(cr, uid, [('work_order_id', 'in', ids)])
        return list(set(wo_ids))

    _columns = {
        'count_wo': fields.function(_count_wo, string='Count WO', type="integer", digits_compute= dp.get_precision('Account'),
              store={
                    'dym.work.order': (_get_wo, ['work_lines'], 10),
                     },multi='sumsb', help="Discount Program."),
        'name': fields.text('Description'),
        'name_show':fields.function(_get_name,string='Description', type='char'),
        'work_order_id': fields.many2one('dym.work.order', 'Work Order', ondelete='cascade'),
        'categ_id': fields.selection([('Sparepart','Sparepart'),('Service','Service')], 'Category', required=True),
        'categ_id_2': fields.many2one('product.category', 'Category 2'),
        'product_id': fields.many2one('product.product','Product',required=True),
        'product_qty': fields.float('Qty', digits_compute=dp.get_precision('Product UoM')),
        'product_uom': fields.many2one('product.uom', 'UoM'),
        'supply_qty':fields.float('Spl Qty'),
        'supply_qty_show':fields.function(_get_supply_qty,string='Spl Qty'),
        'location_id': fields.many2one('stock.location','Location'),
        'discount_persen':fields.float('Disc (Persen)'),
        'discount_pcs':fields.float('Disc Pcs (Amount)'),
        'discount':fields.float('Disc Sum (Amount)'),
        'discount_2': fields.related('discount',type='float',readonly=True),
        'discount_pcs_2': fields.related('discount_pcs',type='float',readonly=True),
        'discount_persen_2': fields.related('discount_persen',type='float',readonly=True),
        'price_unit_show':fields.function(_get_price,string='Unit Price'),
        'price_unit': fields.float('Unit Price', required=True ),#digits_compute= dp.get_precision('Product Price') , states={'draft': [('readonly', False)]}),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account'), help="Price Subtotal."),
        'tax_id': fields.many2many('account.tax', 'work_order_tax', 'order_line_id', 'tax_id', 'Taxes'),#states={'draft': [('readonly', False)]}),
        'warranty':fields.float('Warranty'),
        'warranty_show':fields.function(_get_warranty,string='Warranty'),
        'invoiced': fields.boolean('Invoiced', readonly=True, copy=False),
        'qty_available':fields.float('Qty Avb'),
        'qty_available_show':fields.function(_get_qty_available,string='Qty Avb'),
        'state':fields.selection([('cancel','Cancelled'),('draft','Draft'),('confirmed','Confirmed'),('open','Open'),('done','Done')],required=True,readonly=True,copy=False),
        'tax_id_show': fields.many2many('account.tax', 'work_order_tax', 'order_line_id', 'tax_id', 'Taxes'),#states={'draft': [('readonly', False)]}),
        'discount_line': fields.one2many('dealer.sale.order.line.discount.line','work_order_line_discount_line_id','Discount Line',),
        'branch_dummy': fields.function(_get_branch,type='integer',multi=True),
        'division_dummy': fields.function(_get_branch,type='char',multi=True),
        'customer_dummy': fields.function(_get_branch,type='integer',multi=True),
        'discount_program': fields.function(_amount_discount_program, string='Disc Program', digits_compute= dp.get_precision('Account'),
              store={
                    'dym.work.order.line': (lambda self, cr, uid, ids, c={}: ids, ['price_unit','discount_line','product_qty'], 10),
                     },multi='sumsc', help="Discount Program."),
        'discount_bundle': fields.function(_amount_discount_bundle, string='Disc Bundle', digits_compute= dp.get_precision('Account'),multi='sumsd', help="Discount Bundle."),
        'insentif_finco': fields.float(),
        'bundle_line': fields.one2many('dym.work.order.bundle', 'wo_line_id', 'Bundle List'),
        'is_bundle': fields.boolean('Bundle'),
        'barang_bonus_line': fields.one2many('dealer.sale.order.line.brgbonus.line','work_order_line_brgbonus_line_id', 'Barang Bonus Line'),
        'lost_order_qty': fields.float('Lost Order QTY'),
        'job_redo': fields.boolean('Redo'),
        'save_lost_order': fields.boolean('Save Lost Order'),
        'disc_persen': fields.boolean('Discount Persen'),
        'disc_amount': fields.boolean('Discount Amount'),
        'disc_sum': fields.boolean('Discount Sum'),
    }
    
    _defaults = {
        'product_qty': 1,
        'supply_qty':0,
        'warranty':0.0,
        'state':'draft',
        'insentif_finco':0
    }
    
    def change_tax(self,cr,uid,ids,tax_id,context=None):
        return {'value':{'tax_id_show':tax_id}}
    
    def change_check(self, cr, uid, ids, field_state, enable_check_field, disable_check_field=[], discount_fields=[]):
        value = {}
        if disable_check_field and field_state == True:
            for field in disable_check_field:
                value[field] = False
        if discount_fields and field_state == False:
            for field in discount_fields:
                value[field] = 0
        return {'value':value}

    def change_discount_persen(self, cr, uid, ids, discount_persen, discount_pcs, discount, price_unit, product_qty, field, disc_persen=False, disc_amount=False, disc_sum=False, context=None):
        value = {}
        if disc_persen == True:
            if discount_persen > 100:
                discount_persen = 0
                warning = {
                    'title': 'perhatian!',
                    'message': 'maksimal discount 100%'
                }
            elif discount_persen < 0:
                discount_persen = 0
                warning = {
                    'title': 'perhatian!',
                    'message': 'tidak boleh input nilai negatif'
                }
            if discount_persen > 0:
                discount_pcs = (price_unit * 1 * discount_persen)/100
                discount = discount_pcs * product_qty
            else:
                discount_persen = 0
                discount_pcs = 0
                discount = 0
        if disc_amount == True:
            if discount_pcs > 0:
                discount = product_qty*discount_pcs
            else:
                discount = 0
                discount_pcs = 0
                discount = 0
        if disc_sum == True:
            if discount > 0 and product_qty > 0:
                discount_pcs = discount/product_qty
            else:
                discount = 0
                discount_pcs = 0
                discount = 0
        value['discount'] = discount
        value['discount_pcs'] = discount_pcs
        value['discount_persen'] = discount_persen
        value['discount_2'] = discount
        value['discount_pcs_2'] = discount_pcs
        value['discount_persen_2'] = discount_persen
        return {'value':value}

    def action_view_picking(self,cr,uid,ids,context=None):  
        val = self.browse(cr, uid, ids, context={})[0]
        obj_inv = self.pool.get('stock.picking')
        obj = obj_inv.search(cr,uid,[('transaction_id','=',val.id),('model_id','=',self.__class__.__name__)])
        return {
            'name': 'Picking Slip',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': obj[0]
            }

    def change_save_lost_order(self, cr, uid, ids, branch_dummy, product_id, lost_order_qty, qty_available, product_qty, price_unit,customer_id, context=None):
        value = {}
        if lost_order_qty > 0 and branch_dummy and product_id and lost_order_qty:
            res = {'date':datetime.now().strftime('%Y-%m-%d'), 'branch_id': branch_dummy, 'product_id': product_id, 'lost_order_qty': lost_order_qty , 'tipe_dok': 'WO', 'no_dok': '', 'pemenuhan_qty': qty_available, 'het': price_unit,'customer_id':customer_id, 'rec_id': 0, 'rec_model':'dym.work.order.line'}
            self.pool.get('dym.lost.order').create(cr, uid, res)
            if qty_available > 0:
                value['product_qty'] = qty_available
            value['lost_order_qty'] = 0
            value['save_lost_order'] = False
            value['qty_available_show'] = qty_available
            value['qty_available'] = qty_available
        return {'value':value}

    def location_change(self, cr, uid, ids, location_id,product_id,categ_id,product_qty):
        qty=0.00
        res2={}
        obj_product = self.pool.get('product.product').browse(cr, uid, [product_id])
        if categ_id == 'Sparepart' and not obj_product.product_tmpl_id.is_bundle:
            object_loc=self.pool.get('stock.quant').search(cr,uid,[('location_id','=',location_id),('product_id','=',product_id),('reservation_id','=',False),('consolidated_date','!=',False)])
            if object_loc :
                quant = self.pool.get('stock.quant').browse(cr,uid,object_loc)
                for line in quant :
                    qty +=line.qty
            res2 = {'qty_available':qty }    
            if product_qty > qty:
                lost_order_qty = product_qty - qty
                res2['lost_order_qty'] = lost_order_qty
                if qty > 0:
                    res2['product_qty'] = qty
            else:
                res2['lost_order_qty'] = 0
        return  {'value': res2}  

    def get_bundle_diskon(self, cr, uid, ids, template, product, branch, context=None):
        diskon = 0
        diskon_src = self.pool.get('dym.bundle.diskon').search(cr, uid, [('template_id', '=', template.id),('branch_id', '=', branch.id),('product_tmpl_id', '=', product.product_tmpl_id.id)], limit=1, order='id desc')
        if diskon_src:
            diskon_obj = self.pool.get('dym.bundle.diskon').browse(cr, uid, diskon_src)
            diskon = diskon_obj.diskon
        return diskon
    
    def get_frt_price(self, cr, uid, ids, product_id, branch_id, product_unit_id):
        obj_product = self.pool.get('product.product').browse(cr, uid, [product_id])
        rate = self.pool.get('dym.branch').browse(cr,uid,branch_id).rate
        category_product_id = self.pool.get('product.product').browse(cr,uid,product_unit_id).category_product_id.id
        obj_frt_src = self.pool.get('dym.frt').search(cr,uid,[('product_id_jasa','=',obj_product.product_tmpl_id.id),('category_product_id','=',category_product_id)])
        if obj_frt_src:
            obj_frt = self.pool.get('dym.frt').browse(cr,uid,obj_frt_src)

            obj_frt_history_adjust_ids = self.pool.get('dym.frt.history').search(cr,uid,[('frt_id','=',obj_frt.id),('branch_id','=',branch_id),('price','>',0)], order="date desc, id desc", limit=1)
            obj_frt_history_adjust = self.pool.get('dym.frt.history').browse(cr, uid, obj_frt_history_adjust_ids)
            
            obj_frt_lastest_change_ids = self.pool.get('dym.frt.history').search(cr,uid,['|','&',('frt_id','=',obj_frt.id),('time','>',0),'&',('branch_id','=',branch_id),('rate','>',0)], order="date desc, id desc", limit=1)        
            obj_frt_lastest_change = self.pool.get('dym.frt.history').browse(cr, uid, obj_frt_lastest_change_ids)

            if obj_frt_history_adjust and obj_frt_lastest_change and obj_frt_history_adjust.date >= obj_frt_lastest_change.date and obj_frt_history_adjust.id >= obj_frt_lastest_change.id:
                return obj_frt_history_adjust.price
            return obj_frt.time * rate
        else:
            return 0

    def product_change(self, cr, uid, ids, product_id, categ_id,branch_id, product_unit_id,kpb_ke,type,division,customer_id):
        obj_product = self.pool.get('product.product').browse(cr, uid, [product_id])
        obj_product_motor=self.pool.get('product.product').browse(cr, uid, product_unit_id)
        branch = self.pool.get('dym.branch').browse(cr,uid,branch_id)
        warning = ''
        warranty = 0
        harga_final = 0
        is_bundle = False
        bundles = []
        discount_bundle = 0
        if product_id and categ_id == "Service" and not obj_product.product_tmpl_id.is_bundle:
            warranty = obj_product.warranty
            harga_unit = 0
            if not (branch.kpb_ganti_oli_barang == True and kpb_ke == '1' and  type == 'KPB' and obj_product.is_oli == True):
                if obj_product.use_frt == True:
                    harga_unit = self.get_frt_price(cr, uid, ids, product_id,branch_id, product_unit_id)
                else:
                    harga_unit = self._get_harga_jasa(cr, uid, ids,product_id,branch_id,product_unit_id)
                if harga_unit <= 0 :
                    warning = 'Harga jasa / FRT tidak ditemukan'
            harga_final = harga_unit
        elif product_id and not obj_product.product_tmpl_id.is_bundle:
            warranty = 0.0
            price=0
            if not (branch.kpb_ganti_oli_barang == True and kpb_ke == '1' and type == 'KPB' and obj_product.is_oli == True):  
                pricelist = branch.pricelist_part_sales_id.id
                if obj_product :
                    if type == 'KPB' and kpb_ke == '1' :
                        obj_categ_service1=self.pool.get('dym.category.product.service').search(cr,uid,[('category_product_id','=',obj_product_motor.category_product_id.id),('product_id','=',obj_product.id)])
                        price=self.pool.get('dym.category.product.service').browse(cr,uid,obj_categ_service1).price
                        if price <= 0:
                            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], obj_product.id, 1,0)[pricelist]
                    else :
                        price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], obj_product.id, 1,0)[pricelist]
                if price <=0:
                    warning = 'Harga Produk tidak ditemukan di pricelist'
            harga_final = price
        elif obj_product.product_tmpl_id.is_bundle:
            is_bundle = True
            for bundle_line in obj_product.product_tmpl_id.item_ids:
                if not bundle_line.product_id or bundle_line.product_uom_qty <= 0:
                    warning = 'Settingan product bundle tidak lengkap!'
                diskon_bundle = 0
                harga_unit = 0
                location_ids = []
                if bundle_line.product_id and bundle_line.product_id.categ_id.isParentName('Service'):
                    if bundle_line.product_id.warranty > warranty:
                        warranty = bundle_line.product_id.warranty
                    if not (branch.kpb_ganti_oli_barang == True and kpb_ke == '1' and type == 'KPB' and bundle_line.product_id.is_oli == True):
                        diskon_bundle = self.get_bundle_diskon(cr, uid, ids, obj_product.product_tmpl_id, bundle_line.product_id, branch)
                        if bundle_line.product_id.use_frt == True:
                            harga_unit = self.get_frt_price(cr, uid, ids, bundle_line.product_id.id, branch_id, product_unit_id)
                            if harga_unit <=0:
                                warning = 'Harga FRT tidak ditemukan untuk produk ' + bundle_line.product_id.name
                            harga_final += harga_unit
                        else:
                            harga_unit = self._get_harga_jasa(cr, uid, ids, bundle_line.product_id.id, branch_id, product_unit_id)
                            if harga_unit <=0:
                                warning = 'Harga jasa tidak ditemukan untuk produk ' + bundle_line.product_id.name
                            harga_final += harga_unit
                elif bundle_line.product_id:
                    if not (branch.kpb_ganti_oli_barang == True and kpb_ke == '1' and type == 'KPB' and bundle_line.product_id.is_oli == True):
                        diskon_bundle = self.get_bundle_diskon(cr, uid, ids, obj_product.product_tmpl_id, bundle_line.product_id, branch)
                        pricelist = branch.pricelist_part_sales_id.id
                        if bundle_line.product_id:
                            harga_unit = 0
                            if type == 'KPB' and kpb_ke == '1':
                                obj_categ_service1=self.pool.get('dym.category.product.service').search(cr,uid,[('category_product_id','=',obj_product_motor.category_product_id.id),('product_id','=',bundle_line.product_id.id)])
                                harga_unit=self.pool.get('dym.category.product.service').browse(cr,uid,obj_categ_service1).price
                                if harga_unit <= 0:
                                    harga_unit = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], bundle_line.product_id.id, 1,0)[pricelist]
                            else :
                                harga_unit = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], bundle_line.product_id.id, 1,0)[pricelist]
                            if harga_unit <=0:
                                warning = 'Harga Produk ' + bundle_line.product_id.name + ' tidak ditemukan di pricelist'
                            harga_final += harga_unit
                    loc_ids = bundle_line.product_id.get_location_ids()
                    location_ids = self.pool.get('stock.location').search(cr, uid, [('id','in',loc_ids),('branch_id','=',branch_id),('usage','=','internal')])
                bundles.append([0,0,{
                    'diskon': diskon_bundle,
                    'type': bundle_line.product_id.type,
                    'product_id': bundle_line.product_id.id,
                    'product_uom_qty': bundle_line.product_uom_qty,
                    'product_uom': bundle_line.product_uom.id,
                    'item_id': bundle_line.id,
                    'price_bundle': harga_unit,
                    'src_loc_domain': location_ids and [(6, 0, location_ids)] or [],
                }])
                discount_bundle += diskon_bundle
        else:
            return {'value':{'name': False, 
                'product_uom': False,
                'price_unit': False,
                'warranty': False,
                'tax_id': False,
                'tax_id_show': False,
                'product_id': False,
                'location_id': False,
                'product_qty': 1,
                'discount': False,
                'discount_line': False,
                'is_bundle': False,
                'barang_bonus_line':False,
                'bundle_line':False,
                'discount_bundle':False,
            }}
        if warning:
            return {'value':{'name': False, 
                'product_uom': False,
                'price_unit': False,
                'warranty': False,
                'tax_id': False,
                'tax_id_show': False,
                'product_id': False,
                'location_id': False,
                'product_qty': 1,
                'discount': False,
                'discount_line': False,
                'is_bundle': False,
                'barang_bonus_line':False,
                'bundle_line':False,
                'discount_bundle':False,
                },
                'warning':{'title':'Perhatian!','message':warning}
            }
        res = {
            'name': obj_product.description,
            'product_uom': obj_product.uom_id.id,
            'price_unit': harga_final,
            'warranty': warranty,
            'tax_id': obj_product.taxes_id,
            'tax_id_show': obj_product.taxes_id,
            'branch_dummy': branch_id,
            'division_dummy': division,
            'customer_dummy': customer_id,
            'discount_line': False,
            'barang_bonus_line':False,
            'bundle_line': bundles,
            'is_bundle': is_bundle,
            'location_id': False,
            'discount_bundle':discount_bundle,
            'product_qty': 1,
        }
        domain = {'location_id': "[('id','in',"+str(obj_product.get_location_ids())+"),('branch_id','=',"+str(branch_id)+"),('usage','=','internal')]"  }   
        return  {'value': res, 'domain': domain}

    def category_change(self, cr, uid, ids, categ_id,type,kpb_ke,branch_id,division,product_unit_id,categ_id_2):
        if not branch_id or not division:
            raise osv.except_osv(_('No Branch Defined!'), _('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        if not type or not product_unit_id:
            if type != "SLS":
                raise osv.except_osv(_('Warning!'), _('Sebelum menambah detil transaksi,\n harap isi type dan Product .'))
        kategory_workshop = self.pool.get('dym.branch').browse(cr, uid, branch_id)
        check_kategory_branch=kategory_workshop.workshop_category.id
        if not check_kategory_branch:
            raise osv.except_osv(('Warning !'), ("Cabang tersebut belum dipilih Kategori Workshopnya, Silahkan setting di branch"))
        price_list= self._get_price_list(cr, uid, ids,branch_id)
        if not price_list :
            raise osv.except_osv(('No Sale Pricelist Defined !'), ("Sebelum menambah detil transaksi,\n harap set pricelist terlebih dahulu di Branch Configuration."))
        dom = {}
        product_obj = self.pool.get('product.product')
        product_id = product_obj.browse(cr, uid, product_unit_id)
        val = {}
        val['product_id'] = False
        categ_ids = []
        categ_2_ids = []
        domain_product_jasa = []
        if type == 'KPB':
            val['categ_id'] = 'Service'
        if not categ_id:
            val['categ_id_2'] = False
            dom['categ_id_2']=[('id','in',[])]
        else:
            categ_src = self.pool.get('product.category').search(cr, uid, [('name','=',categ_id),('parent_id','=',False)])
            categ_ids= self._get_product(cr, uid, ids, categ_src, type, kpb_ke)
            domain = [('id','in',categ_ids),('parent_id','=',categ_id)]
            if type != 'KPB':
                domain += [('name','!=','ASS')]
            categ_2_ids = self.pool.get('product.category').search(cr, uid, domain) 
            if categ_2_ids and type == 'KPB':
                catg2 = self.pool.get('product.category').search(cr, uid, [('id','in',categ_2_ids),('name','=','ASS')]) 
                if catg2:
                    val['categ_id_2'] = catg2[0]
                    categ_id = 'Service'
                    categ_id_2 = categ_2_ids[0]
            dom['categ_id_2']=[('id','in',categ_2_ids)]
            if categ_id_2:
                if self.pool.get('product.category').isParentName(cr, uid, [categ_id_2], categ_id) == False:
                    val['categ_id_2'] = False
                else:
                    categ_ids= self._get_product(cr, uid, ids, categ_id_2,type,kpb_ke)
                if categ_id == 'Service':
                    product_ids = []
                    if kpb_ke=='1':
                        product_ids += self.pool.get('product.product').search(cr,uid,[('service_category_ids','=',product_id.category_product_id.id),('type','=','service'),('is_bundle','=',True)])
                    elif kpb_ke=='2':
                        prod_id = self.pool.get('product.product').search(cr,uid,[('name','=','ASS2')])
                        product_ids += prod_id
                    elif kpb_ke=='3':
                        prod_id = self.pool.get('product.product').search(cr,uid,[('name','=','ASS3')])
                        product_ids += prod_id
                    elif kpb_ke=='4':
                        prod_id = self.pool.get('product.product').search(cr,uid,[('name','=','ASS4')])
                        product_ids += prod_id
                    else:
                        product_ids += self.pool.get('product.product').search(cr,uid,['|',('service_category_ids','=',product_id.category_product_id.id),('service_category_ids','=',False),('type','=','service')])
                    if kpb_ke in ['2','3','4'] and prod_id:
                        val['product_id'] = prod_id[0]
                    domain_product_jasa = [('id','in',product_ids)]

        dom['product_id'] = [('categ_id','in',categ_ids)] + domain_product_jasa
        return {'domain':dom, 'value':val}
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state not in ['draft']:
                raise osv.except_osv(_('Invalid Action!'), _('Cannot delete a record which is in state \'%s\'.') %(rec.state,))
        return super(dym_work_order_line, self).unlink(cr, uid, ids, context=context)

class dym_work_order_bundle(osv.osv):
    _name = "dym.work.order.bundle"

    def _get_qty_available(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for bundle_line in self.browse(cr, uid, ids, context=context):
            qty=0.00
            if bundle_line.product_id and bundle_line.location_id:
                if bundle_line.product_id.categ_id.isParentName('Sparepart'):
                    object_loc = self.pool.get('stock.quant').search(cr,uid,[('location_id','=',bundle_line.location_id.id),('product_id','=',bundle_line.product_id.id),('reservation_id','=',False),('consolidated_date','!=',False)])
                    if object_loc :
                        quant = self.pool.get('stock.quant').browse(cr,uid,object_loc)
                        for line in quant:
                            qty += line.qty
            res[bundle_line.id] = qty
        return res

    _columns = {
        'src_loc_domain': fields.many2many('stock.location', 'bundle_location_rel', 'bundle_id', 'location_id', 'Source Location Domain', copy=False),
        'wo_line_id': fields.many2one('dym.work.order.line', 'Work Order Line'),
        'type':    fields.char('Bundle Type'),
        'item_id':    fields.many2one('product.item', 'Product Item', readonly=True),
        'product_id':    fields.many2one('product.product', 'Product', readonly=True),
        'product_uom_qty':    fields.integer('Quantity', readonly=True),
        'product_uom':     fields.many2one('product.uom', 'UoM', readonly=True),
        'location_id': fields.many2one('stock.location','Location'),
        'qty_available':fields.function(_get_qty_available,string='Qty Avb'),
        'diskon':    fields.float('Diskon'),
        'diskon_show': fields.related('diskon', type='float',string='Diskon'),
        'supply_qty':fields.float('Spl Qty'),
        'price_bundle':fields.float('Unit Price'),
        'search_location': fields.boolean('Fill Location'),
    }

    _defaults = {
        'supply_qty':0,
    }

    def change_search_location(self, cr, uid, ids, product_id, branch_id, location_id):
        value = {}
        domain = {}
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id)
            location_ids = product.get_location_ids()
            if location_id and location_id not in location_ids:
                value['location_id'] = False
            domain = {'location_id': "[('id','in',"+str(location_ids)+"),('branch_id','=',"+str(branch_id)+"),('usage','=','internal')]"}
        return {'value':value, 'domain': domain}

    def onchange_location_id(self, cr, uid, ids, product_id, branch_id, location_id):
        domain = {}
        value = {}
        warning = {}
        qty = 0.00
        product = self.pool.get('product.product').browse(cr, uid, product_id)
        if product_id and product.categ_id.isParentName('Sparepart'):
            if location_id:
                object_loc = self.pool.get('stock.quant').search(cr,uid,[('location_id','=',location_id),('product_id','=',product_id),('reservation_id','=',False),('consolidated_date','!=',False)])
                if object_loc :
                    quant = self.pool.get('stock.quant').browse(cr,uid,object_loc)
                    for line in quant :
                        qty += line.qty
                location = self.pool.get('stock.location').browse(cr, uid, location_id)
                if qty <= 0:
                    value['location_id'] = False
                    warning['title']=_('Perhatian!')
                    warning['message']=_('Qty stock %s di lokasi %s = 0')%(product.name,location.name)
            value['qty_available'] = qty
            domain = {'location_id': "[('id','in',"+str(product.get_location_ids())+"),('branch_id','=',"+str(branch_id)+"),('usage','=','internal')]"}
        return  {'domain': domain, 'value':value, 'warning':warning}

    
class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'work_order_line_id': fields.many2one('dym.work.order.line',
            'Work Order Order Line', ondelete='set null', select=True,
            readonly=True),
    }

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(stock_move, self).write(cr, uid, ids, vals, context=context)
        from openerp import workflow
        for move in self.browse(cr, uid, ids, context=context):
                if move.work_order_line_id and move.work_order_line_id.work_order_id: 
                    work_order_id = move.work_order_line_id.work_order_id.id 
                    if self.pool.get('dym.work.order').test_moves_done(cr, uid, [work_order_id], context=context):
                        workflow.trg_validate(uid, 'dym.work.order', work_order_id, 'picking_done', cr)
                        self.pool.get('dym.work.order').write(cr, uid,work_order_id, {'type_wo': 2}, context=context)
                        self.pool.get('dym.work.order.line').write(cr, uid,move.work_order_line_id.id, {'state': 'done'}, context=context)
                    if self.pool.get('dym.work.order').test_moves_except(cr, uid, [work_order_id], context=context):
                       workflow.trg_validate(uid, 'dym.work.order', work_order_id, 'picking_cancel', cr)
        return res
    
class dym_stock_picking_wo(osv.osv):
    _inherit = 'stock.picking'
    
class dym_account_invoice(models.Model):
    _inherit = 'account.invoice'
            
    @api.multi
    def action_cancel(self):
        cancel = super(dym_account_invoice,self).action_cancel()
        if self.model_id.model == 'dym.work.order' and self.transaction_id:
            for line in self.invoice_line:
                if line.product_id.categ_id.isParentName('Sparepart'):
                    workflow.trg_validate(self._uid, 'dym.work.order', self.transaction_id, 'invoice_sparepart_cancel', self._cr)
                    break
        return cancel

    @api.multi
    def confirm_paid(self):
        paid = super(dym_account_invoice,self).confirm_paid()
        if self.model_id.model == 'dym.work.order' and self.transaction_id:
            for line in self.invoice_line:
                if line.product_id.categ_id.isParentName('Sparepart'):
                    workflow.trg_validate(self._uid, 'dym.work.order', self.transaction_id, 'invoice_sparepart_paid', self._cr)
                    break
        return paid

    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        move_lines = super(dym_account_invoice,self).finalize_invoice_move_lines(move_lines)
        return move_lines

    @api.multi
    def action_move_create(self):
        precision = self.env['decimal.precision'].precision_get('Account')
        res = super(dym_account_invoice,self).action_move_create()
        ar_acc=0;ppn_acc=0;analytic_4_acc=False;diskon_ar=0;diskon_ppn=0;part_list=[];accessories_list=[]
        obj_move_line=self.env['account.move.line']
        analytic_4 = False

        if 'WOR' in self.origin or 'SOR' in self.origin:
            #Get Accessories Amount
            for line in self.move_id.line_id:
                if line.analytic_2.code == '230':
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(line.branch_id.id, 'Sparepart', line.product_id.categ_id, 4, 'General')
                    if line.product_id and line.account_id.id != line.product_id.categ_id.property_stock_valuation_account_id.id:
                        ar_acc += line.credit
                        ppn_acc += line.credit / 11
                    elif not line.product_id and line.name != self.origin:
                        diskon_ar += line.debit
                        diskon_ppn += line.debit / 11
                    accessories_list.append(line.id)
                if line.analytic_2.code == '220' and line.product_id:
                    part_list.append(line.analytic_2.id)
            if accessories_list and not part_list:
                line.move_id.button_cancel()
                for line in self.move_id.line_id:
                    if line.name == self.origin:
                        line.write({'analytic_account_id': analytic_4})
                    elif 'PPN' in line.account_id.name:
                        line.write({'analytic_account_id': analytic_4})
                    line.move_id.post()
            if part_list and accessories_list:
                #Write Move Line and Add Move Line Accessories
                ar_acc = round(ar_acc,precision)
                ppn_acc = round(ppn_acc,precision)
                diskon_ar = round(diskon_ar,precision)
                diskon_ppn = round(diskon_ppn,precision)

                if ar_acc and ppn_acc:
                    amount_ar = (ar_acc-diskon_ar)*1.1
                    amount_ppn = (ppn_acc-diskon_ppn)*1.1

                    amount_ar = round(amount_ar,precision)
                    amount_ppn = round(amount_ppn,precision)

                    debit = 0
                    credit = 0
                    line.move_id.button_cancel()    
                    for line in self.move_id.line_id:
                        if line.name == self.origin:
                            line.write({'debit':line.debit - amount_ar})
                            new_line = line.copy()
                            new_line.write({'debit':amount_ar,'analytic_account_id': analytic_4})
                            debit+=new_line.debit
                        elif 'PPN' in line.account_id.name:
                            line.write({'credit':line.credit - amount_ppn})
                            new_line = line.copy()
                            new_line.write({'credit':amount_ppn,'analytic_account_id': analytic_4,'tax_amount':ar_acc-diskon_ar})
                            credit+=new_line.credit
                        debit+=line.debit
                        credit+=line.credit
                    line.move_id.post()
                else:
                    for line in self.move_id.line_id:
                        if line.analytic_2.code != '210' and analytic_4:
                            line.write({'analytic_account_id': analytic_4})
        return res

class dealer_sale_order_brgbonus_line(osv.osv):
    _inherit = 'dealer.sale.order.line.brgbonus.line'       
    _columns = {
        'work_order_line_brgbonus_line_id': fields.many2one('dym.work.order.line',ondelete='cascade'),
    }
