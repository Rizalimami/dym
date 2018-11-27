import time
from datetime import datetime
import string 
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api
from openerp.osv.expression import get_unaccent_wrapper
from openerp import workflow
import openerp.addons.decimal_precision as dp
import pdb

class dealer_sale_order_line(osv.osv):
    _inherit = 'dealer.sale.order.line'

    def action_so_update_price(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        for o in self.browse(cr, uid, ids):
            state = o.dealer_sale_order_line_id.state
            if not state == 'draft':
                raise osv.except_osv(('Perhatian !'), ("Edit harga hanya boleh ketika status Delaer Sales Memo masih Draft!"))


            form_id  = 'Sales Memo Update Price'
            view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                ("name", "=", form_id), 
                ("model", "=", 'dym.sale.order.update.price'),
            ])

            return {
                'name': _('Update Price'),
                'view_type': 'form',
                'view_id' : view_id,
                'view_mode': 'form',
                # 'res_id': ids[0],
                'res_model': 'dym.sale.order.update.price',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'nodestroy': True,
                'context': context
            }


            # view = self.env.ref('dym_sale_order_update_price.view_dym_sale_order_update_price')
            # return {
            #     'name': _('Update Price'),
            #     'type': 'ir.actions.act_window',
            #     'view_type': 'form',
            #     'view_mode': 'form',
            #     'res_model': 'dym.sale.order.update.price',
            #     'views': [(view.id, 'form')],
            #     'view_id': view.id,
            #     'target': 'new',
            #     'res_id': self.ids[0],
            #     'context': self.env.context,
            # }


class tipe_konsumen(osv.osv):
    _name = 'tipe.konsumen'
    _order = 'sequence, name'
    _columns = {
        'name' : fields.char('Name', required=True),
        'sequence': fields.integer('Sequence', help="Determine the display order in the report sales order"),
        'default': fields.boolean('Set Default'),
        'so': fields.boolean('Sales Memo'),
        'wo': fields.boolean('Work Order'),
    }

    _sql_constraints = [
    ('unique_source_name', 'unique(name)', 'Sales source sudah ada!'),
    ]


class account_invoice_line_sale_order(osv.osv):
    _inherit = 'account.invoice.line'

    def _get_amount_sale_line(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            sale_line_ids = self.pool.get('sale.order.line').search(cr, uid, [('invoice_lines','in',[line.id])])
            sale_lines = self.pool.get('sale.order.line').browse(cr, uid, sale_line_ids)
            sale_discount = 0
            sale_amount = 0
            for sale_line in sale_lines:
                sale_discount += sale_line.discount_show + sale_line.discount_cash + sale_line.discount_lain + (sale_line.discount_program/sale_line.product_uom_qty)
            price = (line.price_unit * line.quantity) - sale_discount
            product = line.product_id
            partner = line.invoice_id.partner_id
            taxes = line.invoice_line_tax_id.compute_all(price, 1, product, partner)
            sale_amount = taxes['total']

            res[line.id] = {
                'sale_discount': sale_discount,
                'sale_amount': sale_amount,
            }
        return res

    _columns = {
        'sale_discount':fields.function(_get_amount_sale_line, type='float', string='Total Discount', multi='sums'),
        'sale_amount':fields.function(_get_amount_sale_line, type='float', string='Amount', multi='sums'),
    }


class dym_sale_order(osv.osv):
    
    _inherit = 'sale.order'
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_sale_order, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        for field in res['fields']:
            if field == 'division':
                if 'menu' in context and context['menu'] == 'showroom':
                    res['fields'][field]['selection'] = [('Unit','Showroom')]
                if 'menu' in context and context['menu'] == 'workshop':
                    res['fields'][field]['selection'] = [('Sparepart','Workshop')]
        return res

    def _amount_all_wrapper(self, cr, uid, ids, field_name, arg, context=None):
        """ Wrapper because of direct method passing as parameter for function fields """
        return self._amount_all(cr, uid, ids, field_name, arg, context=context)

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    def _amount_line_tax(self, cr, uid, line, context=None):
        val = 0.0
        discount_program = 0
        for program_line in line.discount_line:
            if program_line.tipe_diskon == 'percentage':
                discount_program += (line.price_unit * program_line.discount_pelanggan / 100)
            else:
                discount_program += program_line.discount_pelanggan 
        discount_program = discount_program * line.product_uom_qty
        price = (line.price_unit * line.product_uom_qty) - line.discount_show - discount_program - line.discount_cash - line.discount_lain
        for c in self.pool.get('account.tax').compute_all(cr, uid, line.tax_id, price, 1, line.product_id, line.order_id.partner_id)['taxes']:
            val += c.get('amount', 0.0)
        return val

    # def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
    #     res = super(dym_sale_order,self)._amount_all(cr, uid, ids, field_name, arg, context=context)
    #     amount_untaxed = amount_taxed = amount_total = 0.0
    #     for sale_order in self.browse(cr,uid,ids):                
    #         amount_untaxed = res[sale_order.id].get('amount_untaxed',0)
    #         amount_taxed = amount_untaxed*0.1
    #         amount_total = amount_untaxed+amount_taxed-total_discount
    #         res[sale_order.id].update({'amount_tax':amount_taxed,'amount_total':amount_total})
    #     return res
    
    def _get_discount(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'discount_cash': 0.0,
                'discount_program': 0.0,
                'discount_lain': 0.0,
            }
            discount_total = 0
            for line in order.order_line:
                discount_program = 0
                for program_line in line.discount_line:
                    if program_line.tipe_diskon == 'percentage':
                        discount_program += (line.price_unit * program_line.discount_pelanggan / 100)
                    else:
                        discount_program += program_line.discount_pelanggan 
                discount_program = discount_program * line.product_uom_qty
                discount_total += discount_program
            res[order.id]['discount_cash'] = sum(line.discount_cash for line in order.order_line) 
            res[order.id]['discount_program'] = discount_total
            res[order.id]['discount_lain'] = sum(line.discount_lain for line in order.order_line) 
        return res
    
    def _get_total_inv(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for inv in self.read(cr, uid, ids, ['total_invoiced']):
            total_invoiced = inv['total_invoiced']
            res[inv['id']] = total_invoiced
        return res

    def _get_employee_id(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)             
        return user_browse.employee_id

    def _get_tipe_konsumen(self,cr,uid,ids,context=None):
        tipe_id = False
        tipe_ids = self.pool.get('tipe.konsumen').search(cr, uid, [('default','=',True),('so','=',True)], limit=1)
        if tipe_ids:
            tipe_id = self.pool.get('tipe.konsumen').browse(cr, uid, tipe_ids)
        return tipe_id

    _columns = {
        'tipe_transaksi':fields.selection([('reguler', 'Reguler'),('hotline', 'Hotline'),('pic', 'PIC')],'Tipe Transaksi'),
        'tipe_konsumen': fields.many2one('tipe.konsumen','Tipe Konsumen'),
        'partner_cabang': fields.many2one('dym.cabang.partner','Cabang Customer'),
        'employee_id': fields.many2one('hr.employee','Sales Person'),
        'branch_id': fields.many2one('dym.branch','Branch',required=True),
        'division':fields.selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division', change_default=True, select=True, required=True),
        'credit_limit_unit': fields.related('partner_id','credit_limit_unit',relation='res.partner',string='Credit Limit Unit'),
        'credit_limit_sparepart': fields.related('partner_id','credit_limit_sparepart',relation='res.partner',string='Credit Limit Sparepart'),
        'total_invoiced_show': fields.function(_get_total_inv, string='Total Invoiced'),
        'total_invoiced': fields.float(),
        # 'discount_cash_persen': fields.float('Discount Cash (%)'),
        'discount_cash': fields.function(_get_discount, string='Discount Cash', multi='sums'),
        'discount_program': fields.function(_get_discount, string='Discount Cash', multi='sums'),
        'discount_lain': fields.function(_get_discount, string='Discount Cash', multi='sums'),
        # 'discount_cash_show': fields.function(_get_discount_cash, string='Discount Cash'),
        # 'discount_program': fields.float('Discount Program'),
        # 'discount_lain': fields.float('Discount Lain',),
        # iman 'distribution_id': fields.many2one('dym.stock.distribution','Stock Distribution'),
        'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
        'confirm_date':fields.datetime('Confirmed on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),     
        'partner_id': fields.many2one('res.partner', 'Customer', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, domain=['|','|',('direct_customer','=',True),('customer','=',True),('is_customer_depo','=',True)], required=True, change_default=True, select=True, track_visibility='always'),
        'pajak_gunggung':fields.boolean('Tanpa Faktur Pajak',copy=False),   
        'pajak_gabungan':fields.boolean('Faktur Pajak Gabungan',copy=False),   
        'pajak_generate':fields.boolean('Faktur Pajak Satuan',copy=False),   
        'faktur_pajak_id':fields.many2one('dym.faktur.pajak.out',string='No Faktur Pajak',copy=False),

        'mobile': fields.char('Mobile'),

        # 'discount_program': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Discount Program',
        #     store={
        #         'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line','discount_cash','discount_lain'], 10),
        #         'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty','discount_line'], 10),
        #     },
        #     multi='sums', help="The amount of discount program.", track_visibility='always'),

        'amount_untaxed': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount','discount_cash','discount_lain', 'product_uom_qty','discount_line'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'),
        'amount_tax': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount','discount_cash','discount_lain', 'product_uom_qty','discount_line'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount','discount_cash','discount_lain', 'product_uom_qty','discount_line'], 10),
            },
            multi='sums', help="The total amount."),
        'is_pedagang_eceran': fields.related('branch_id', 'is_pedagang_eceran', relation='dym.branch',type='boolean',string='Pedagang Eceran',store=False),
        'member':fields.related('partner_id','member',type='char',string='Member Number'),
    }

    _defaults = {
        'warehouse_id': False,
        'division': 'Sparepart',
        'employee_id': _get_employee_id,
        'tipe_konsumen': _get_tipe_konsumen,
        'tipe_transaksi': 'reguler',
    }

    def onchange_sales(self,cr,uid,ids,sales_id):
        value = {}
        if sales_id:            
            section = self.pool.get('crm.case.section').search(cr,uid,['|',('user_id','=',sales_id),('member_ids','=',sales_id)], limit=1)
            if section:
                value['section_id'] = section[0]
            return {'value':value}
        return False

    def onchange_gabungan_gunggung(self,cr,uid,ids,gabungan_gunggung,pajak_gabungan,pajak_gunggung,pajak_generate,tipe_transaksi,context=None):
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
        if tipe_transaksi == 'pic':
            value['pajak_generate']=True
            value['pajak_gunggung'] = False
            value['pajak_gabungan'] = False
        val = self.browse(cr,uid,ids)
        if val.partner_id.tipe_faktur_pajak:
            if val.partner_id.tipe_faktur_pajak == 'satuan':
                value['pajak_generate'] = True
                value['pajak_gunggung'] = False
                value['pajak_gabungan'] = False
            elif val.partner_id.tipe_faktur_pajak == 'gabungan':
                value['pajak_generate'] = False
                value['pajak_gunggung'] = False
                value['pajak_gabungan'] = True
            else:
                value['pajak_generate'] = False
                value['pajak_gunggung'] = True
                value['pajak_gabungan'] = False
        return {'value':value}

    def onchange_branch(self,cr,uid,ids,branch_id,context=None):
        if not context:
            context = {}
        value = {}
        warehouse_ids = self.pool.get('stock.warehouse').search(cr, uid, [('branch_id', '=', branch_id)])
        if warehouse_ids:
            value['warehouse_id'] = warehouse_ids[0]
            value['partner_id'] = False
        if branch_id:
            branch = self.pool.get('dym.branch').browse(cr,uid,branch_id)
            value['is_pedagang_eceran'] = branch.is_pedagang_eceran
            value['pricelist_id'] = branch.pricelist_unit_sales_id.id
        return {'value':value}
    
    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'SOR', division=vals['division'])
        sale_order = super(dym_sale_order, self).create(cr, uid, vals, context=context)
        res = self.browse(cr,uid,sale_order) 
        if res.amount_total < 0:
             raise osv.except_osv(('Perhatian !'), ("Total Amount tidak boleh minus! harap cek kembali data anda!"))
        for line in res.order_line:
            if res.tipe_transaksi == 'hotline' and line.qty_available > 0:
             raise osv.except_osv(('Perhatian !'), ("SO Hotline hanya untuk produk yang available 0"))
        return sale_order
    
    def write(self, cr, uid, ids, vals, context=None):
        res = super(dym_sale_order, self).write(cr, uid, ids, vals, context=context)
        for order in self.browse(cr,uid,ids):
            if order.amount_total < 0:
                 raise osv.except_osv(('Perhatian !'), ("Total Amount tidak boleh minus! harap cek kembali data anda!"))
        return res

    # PT IMan
    # def write(self, cr, uid, ids, vals, context=None):
    #     context = context or {}
    #     tgl_break = time.strftime('%Y-%m-%d %H:%M:%S')
    #     val = self.browse(cr, uid, ids, context={})[0]
    #     res=super(dym_sale_order, self).write(cr, uid, ids, vals, context=context)
    #     for order in self.browse(cr,uid,ids):
    #         if order.amount_total < 0:
    #              raise osv.except_osv(('Perhatian !'), ("Total Amount tidak boleh minus! harap cek kembali data anda!"))
    #     s=self.pool.get('sale.order.line').search(cr,uid,[('order_id','=',val.id),('state','=','draft')])
    #     if s :
    #         for x in self.pool.get('sale.order.line').browse(cr,uid,s) :
    #             if x.state == 'draft': 
    #                 netsvc.LocalService("workflow").trg_delete(uid, 'sale.order', val.id, cr) 
    #                 netsvc.LocalService("workflow").trg_create(uid, 'sale.order', val.id, cr)
    #                 super(dym_sale_order, self).write(cr, uid, ids, {'state': 'draft'}, context=context)
    #                 netsvc.LocalService("workflow").trg_validate(uid, 'sale.order', val.id, 'break_wo', cr)
    #     for wo in self.browse(cr, uid, ids):
    #         if wo.amount_total < 0:
    #              raise osv.except_osv(('Perhatian !'), ("Total Amount tidak boleh minus! harap cek kembali data anda!"))
    #         if not wo.work_lines.filtered(lambda r: r.categ_id == 'Service') and wo.work_lines:
    #             raise osv.except_osv(('Perhatian !'), ("WO %s Tidak memiliki service")%(wo.name))
    #         self._get_wo(cr, uid, [wo.id], wo.type, wo.date, wo.tanggal_pembelian, wo.lot_id.id, wo.kpb_ke, wo.km)       
    #     return res

    def _invoice_total(self, cr, uid, ids, partner_id, division, context=None):
        invoice_total = 0.0
        sale_order = self.browse(cr,uid,ids)
        obj_inv = self.pool.get('account.invoice')
        
        if division=='Unit':
            tipe = 'md_sale_unit'
        elif division=='Sparepart':
            tipe='md_sale_sparepart'
            
        domain = [('partner_id', 'child_of', partner_id),('division','=',division),('state','=','open'),('tipe','=',tipe)]
        invoice_ids = obj_inv.search(cr, uid, domain, context=context)
        invoices = obj_inv.browse(cr, uid, invoice_ids, context=context)
        invoice_total = sum(inv.residual for inv in invoices)
        return invoice_total
    
    def onchange_tipe_konsumen(self, cr, uid, ids, partner_id, tipe_konsumen, context=None):
        partner = self.pool.get('res.partner').browse(cr,uid,partner_id)
        if not tipe_konsumen or not partner_id:
            return {}
        if partner.partner_type in ['Afiliasi','Konsolidasi']:
            tipe_konsumen_id = self.pool.get('tipe.konsumen').search(cr,uid,[('name','=','Workshop Customer')],context=context)
            if tipe_konsumen_id and tipe_konsumen != tipe_konsumen_id[0]:
                return {
                    'warning': {'title': _('Warning'),'message': _('Tipe konsumen untuk partner Afiliasi dan Konsolidasi hanya boleh "Workshop Customer" saja.')},
                    'value': {
                        'tipe_konsumen': tipe_konsumen_id[0],
                    }
                }

    def onchange_tipe_transaksi(self, cr, uid, ids, partner_id, tipe_transaksi, context=None):
        dom={}
        partner_ids = []
        # if not tipe_transaksi or not partner_id:
        #     return {}
        partner = self.pool.get('res.partner').browse(cr,uid,partner_id)
        if tipe_transaksi == 'pic' and not partner_id:
            partner_ids = self.pool.get('res.partner').search(cr,uid,[('partner_type','in',['Afiliasi','Konsolidasi'])])
            partner_brw = self.pool.get('res.partner').browse(cr,uid,partner_ids)
            if partner_brw:
                for x in partner_brw:
                    partner_ids.append(x.id)
            dom['partner_id']=[('id','in',partner_ids)]
            return {'domain':dom }
        elif tipe_transaksi != 'pic' and not partner_id:
            dom['partner_id']=[('partner_type','not in',['Afiliasi','Konsolidasi'])]
            return {'domain':dom }
        elif tipe_transaksi != 'pic' and partner.partner_type in ['Afiliasi','Konsolidasi']:
                return {
                    'warning': {'title': _('Warning'),'message': _('Tipe transaksi untuk partner Afiliasi dan Konsolidasi hanya boleh tipe "PIC" saja.')},
                    'value':{
                        'tipe_transaksi':'pic',
                    }
                }
        elif tipe_transaksi == 'pic' and partner.partner_type not in ['Afiliasi','Konsolidasi']:
                return {
                    'warning': {'title': _('Warning'),'message': _('Tipe transaksi "PIC" hanya untuk partner Afiliasi dan Konsolidasi saja.')},
                    'value':{
                        'tipe_transaksi': 'reguler',
                    }
                }
        return {}

    def onchange_partner_id_new(self, cr, uid, ids, part, division, branch_id, context=None):
        mobile = []
        res = self.onchange_partner_id(cr, uid, ids, part, context)
        partner_obj = self.pool.get('res.partner').browse(cr,uid,part)
        if not (part and division and branch_id):
            return {'value': {'pricelist_id':False,'partner_invoice_id': False, 'partner_shipping_id': False,  'payment_term': False, 'fiscal_position': False,'member':partner_obj.member,'mobile':partner_obj.mobile}}
        if partner_obj:
            total_inv = self._invoice_total(cr,uid,ids,part,division)
            res['value'].update({'total_invoiced':total_inv,'total_invoiced_show':total_inv,'credit_limit_unit':partner_obj.credit_limit_unit,'credit_limit_sparepart':partner_obj.credit_limit_sparepart,'member':partner_obj.member,'mobile':partner_obj.mobile})
            if partner_obj.partner_type in ['Afiliasi','Konsolidasi']:
                res['value'].update({
                    'tipe_transaksi':'pic',
                    'pajak_generate':True,
                })
                tipe_konsumen_id = self.pool.get('tipe.konsumen').search(cr,uid,[('name','=','Workshop Customer')],context=context)
                if tipe_konsumen_id:
                    res['value'].update({
                        'tipe_konsumen':tipe_konsumen_id[0],
                    })
        
        if not (res['value'].get('pricelist_id',False)):
            # md_id = self.pool.get('dym.branch').search(cr,uid,[('code','=','MML'),('branch_type','=','MD')])
            if not branch_id:
                res.update({'value':{'pricelist_id':False,'partner_id':False},'warning':{'title':'Perhatian','message':'Tidak ditemukan pricelist jual!'}})
            else:
                if division == 'Unit':
                    pricelist_md = self.pool.get('dym.branch').browse(cr,uid,branch_id)['pricelist_unit_sales_id']
                elif division == 'Sparepart':
                    pricelist_md = self.pool.get('dym.branch').browse(cr,uid,branch_id)['pricelist_part_sales_id']
                print pricelist_md,"pricelist_md"
                if pricelist_md and pricelist_md.id:
                    res['value'].update({'pricelist_id':pricelist_md.id})
                else:
                    res.update({'value':{'pricelist_id':False,'partner_id':False},'warning':{'title':'Perhatian','message':'Tidak ditemukan pricelist jual!'}})
        return res
    
   
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
    
    def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
        vals = super(dym_sale_order, self)._prepare_order_line_procurement(cr, uid, order, line, group_id=group_id, context=context)
        location = self._get_default_location_delivery_sales(cr,uid,order.id)
        procurement_rule_id = self.pool.get('procurement.rule').search(cr, uid, [
            ('warehouse_id','=',order.warehouse_id.id),
            ('picking_type_id','=', location['picking_type_id'])
        ])
        
        if procurement_rule_id:
            vals['rule_id'] = procurement_rule_id[0]
        vals['location_id'] = location['destination']
        return vals
    
    def _get_branch_journal_config(self,cr,uid,branch_id):
        result = {}
        branch_journal_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
        if not branch_journal_id:
            raise osv.except_osv(
                        _('Perhatian'),
                        _('Jurnal penjualan cabang belum dibuat, silahkan setting dulu.'))
            
        branch_journal = self.pool.get('dym.branch.config').browse(cr,uid,branch_journal_id[0])
        if not(branch_journal.dym_so_journal_sparepart_id):
            raise osv.except_osv(
                        _('Perhatian'),
                        _('Jurnal penjualan cabang belum lengkap, silahkan setting dulu.'))
        if not(branch_journal.dym_so_journal_sparepart_id.default_debit_account_id):
            raise osv.except_osv(
                        _('Perhatian'),
                        _('Account debit di Jurnal penjualan cabang belum lengkap, silahkan setting dulu.'))
        result.update({
                  'dym_so_journal_unit_id':branch_journal.dym_so_journal_unit_id,
                  'dym_so_journal_sparepart_id':branch_journal.dym_so_journal_sparepart_id,
                  })
        
        return result
    
    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr,uid,[ ('model','=',self.__class__.__name__) ])
        journal_config = self._get_branch_journal_config(cr, uid, order.branch_id.id)
        invoice = super(dym_sale_order,self)._prepare_invoice(cr, uid, order, lines, context=context)
        if order.division=='Unit':
            tipe = 'md_sale_unit'
            # analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, order.branch_id, 'Unit', False, 4, 'Sales')
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, order.branch_id, 'Unit', False, 4, 'General')
        elif order.division=='Sparepart':
            if not order.order_line:
                raise osv.except_osv(
                            _('Perhatian'),
                            _('Mohon isi detail penjualan.'))
            tipe='md_sale_sparepart'
            # analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, order.branch_id, '', order.order_line[0].product_id.categ_id, 4, 'Sparepart_Accesories')
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, order.branch_id, '', order.order_line[0].product_id.categ_id, 4, 'General')
        invoice.update({
                'branch_id':order.branch_id.id,
                'division':order.division,
                'name':order.name,
                'tipe': tipe,
                'model_id': obj_model_id[0],
                'transaction_id':order.id,
                'analytic_1':analytic_1_general or False,
                'analytic_2':analytic_2_general or False,
                'analytic_3':analytic_3_general or False,
                'analytic_4':analytic_4_general or False,
                })
        
        if order.division == 'Unit':
            invoice['journal_id'] = journal_config['dym_so_journal_unit_id'].id
            invoice['account_id'] = journal_config['dym_so_journal_unit_id'].default_debit_account_id.id
        elif order.division == 'Sparepart':
            # Jika Tipe Transaksi PIC
            if order.tipe_transaksi=='pic':
                obj_branch_config = self._get_branch_journal_config_so(cr,uid,order.branch_id.id)
                if not obj_branch_config.dym_so_journal_pic_id:
                    raise osv.except_osv(('Perhatian !'), ("Konfigurasi Journal penjualan PIC di branch config belum diset!"))            
                invoice['journal_id'] = obj_branch_config.dym_so_journal_pic_id.id
                invoice['account_id'] = obj_branch_config.dym_so_journal_pic_id.default_debit_account_id.id
                
                if not obj_branch_config.dym_so_account_penjualan_pic_id:
                    raise osv.except_osv(('Perhatian !'), ("Konfigurasi Account penjualan intercompany di branch config belum diset!"))            
                # Replace Account Penjualan Reguler ke intercompany
                inv_line=self.pool.get('account.invoice.line').browse(cr,uid,lines)
                for line in inv_line:
                   line.write({'account_id':obj_branch_config.dym_so_account_penjualan_pic_id.id})
            else:
                invoice['journal_id'] = journal_config['dym_so_journal_sparepart_id'].id
                invoice['account_id'] = journal_config['dym_so_journal_sparepart_id'].default_debit_account_id.id
        
        # discount_program = 0.0
        # for line in order.order_line:
        #     for disc in line.discount_line:
        #         discount_program += (disc.discount_pelanggan*line.product_uom_qty)    
        # if order.discount_cash>0 or discount_program>0 or order.discount_lain>0:
        #     invoice.update({
        #                     'discount_cash':order.discount_cash,
        #                     'discount_program':discount_program,
        #                     'discount_lain':order.discount_lain
        #                     })
        
       
        return invoice
    
    def _get_branch_journal_config_so(self,cr,uid,branch_id):
        result = {}
        obj_branch_config_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
        if not obj_branch_config_id:
            raise osv.except_osv(('Perhatian !'), ("Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu"))
        else:
            
            obj_branch_config = self.pool.get('dym.branch.config').browse(cr,uid,obj_branch_config_id[0])
            if not(obj_branch_config.so_account_potongan_langsung_id and obj_branch_config.dym_so_account_discount_cash_id and obj_branch_config.dym_so_account_discount_program_id and obj_branch_config.dym_so_account_discount_lainnya_id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi cabang jurnal Diskon belum dibuat, silahkan setting dulu"))
            
        return obj_branch_config

    # def _make_invoice(self, cr, uid, order, lines, context=None):
    #     inv_id = super(dym_sale_order,self)._make_invoice(cr, uid, order, lines, context=context)
    #     per_ar = []
    #     per_potongan = {}
    #     for line in order.order_line:
    #         for disc in line.discount_line:
    #             if disc.tipe_diskon == 'percentage':
    #                 total_diskon = disc.discount_pelanggan
    #                 if disc.tipe_diskon == 'percentage':
    #                     total_diskon = line.price_unit * disc.discount_pelanggan / 100
    #                 per_potongan['discount_pelanggan'] = per_potongan.get('discount_pelanggan',0)+(total_diskon*line.product_uom_qty)
    #             else:
    #                 total_claim_discount = disc.ps_ahm + disc.ps_md + disc.ps_finco + disc.ps_others + disc.ps_dealer
    #                 total_diskon_pelanggan = 0 if total_claim_discount - disc.discount_pelanggan >= disc.ps_dealer else disc.ps_dealer - (total_claim_discount - disc.discount_pelanggan)
    #                 total_diskon_external = disc.discount_pelanggan - total_diskon_pelanggan
    #                 # if disc.tipe_diskon == 'percentage':
    #                 #     total_diskon_dealer = line.price_unit * disc.discount_pelanggan / 100
    #                 #     total_diskon_pelanggan = 0
    #                 per_potongan['discount_external'] = per_potongan.get('discount_external',0)+(total_diskon_external*line.product_uom_qty)
    #                 per_potongan['discount_pelanggan'] = per_potongan.get('discount_pelanggan',0)+(total_diskon_pelanggan*line.product_uom_qty)
    #     # per_potongan['discount_program'] = order.discount_program
    #     per_potongan['discount_cash'] = order.discount_cash
    #     per_potongan['discount_lain'] = order.discount_lain
    #     per_potongan['discount'] = sum(line.discount_show for line in order.order_line) 
    #     per_potongan['tax_id'] = [(6, 0, [y.id for y in order.order_line[0].tax_id])]
    #     invoice_lines = []
    #     obj_branch_config = self._get_branch_journal_config_so(cr,uid,order.branch_id.id)
    #     if order.division=='Unit':
    #         analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, order.branch_id, 'Unit', False, 4, 'Sales')
    #         analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, order.branch_id, 'Unit', False, 4, 'General')
    #     elif order.division=='Sparepart':
    #         if not order.order_line:
    #             raise osv.except_osv(
    #                         _('Perhatian'),
    #                         _('Mohon isi detail penjualan.'))
    #         analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, order.branch_id, '', order.order_line[0].product_id.categ_id, 4, 'Sparepart_Accesories')
    #         analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, order.branch_id, '', order.order_line[0].product_id.categ_id, 4, 'General')
    #     # if order.division=='Unit':
    #     #     analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, order.branch_id, 'Unit', False, 4, 'Sales')
    #     # elif order.division=='Sparepart':
    #     #     analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, order.branch_id, 'Sparepart', False, 4, 'Sparepart_Accesories')
    #     for key, value in per_potongan.items():
    #         if value > 0:
    #             price_unit = -1*value
    #             tax = per_potongan['tax_id']
    #             if key=='discount':
    #                 invoice_lines.append({
    #                         'name': 'Diskon Reguler',
    #                         'quantity':1,
    #                         'origin':order.name,
    #                         'price_unit':price_unit,
    #                         'invoice_line_tax_id':tax,
    #                         'account_id': obj_branch_config.so_account_potongan_langsung_id.id,
    #                         'invoice_id': inv_id,
    #                         'analytic_1':analytic_1 or False,
    #                         'analytic_2':analytic_2 or False,
    #                         'analytic_3':analytic_3 or False,
    #                         'account_analytic_id':analytic_4 or False,
    #                     })
    #             if key=='discount_pelanggan':
    #                 invoice_lines.append({
    #                         'name': 'Diskon Dealer',
    #                         'quantity':1,
    #                         'origin':order.name,
    #                         'price_unit':price_unit,
    #                         'invoice_line_tax_id':tax,
    #                         'account_id': obj_branch_config.dym_so_account_discount_program_id.id,
    #                         'invoice_id': inv_id,
    #                         'analytic_1':analytic_1 or False,
    #                         'analytic_2':analytic_2 or False,
    #                         'analytic_3':analytic_3 or False,
    #                         'account_analytic_id':analytic_4 or False,
    #                     })
    #             if key=='discount_external':
    #                 # invoice_pelunasan['discount_program'] = value
    #                 if not obj_branch_config.dym_so_account_discount_program_external_id:
    #                     raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan subsidi external di branch config belum ada!"))
    #                 invoice_pelunasan_line.append([0,False,{
    #                         'name': 'Diskon External',
    #                         'quantity':1,
    #                         'origin':order.name,
    #                         'price_unit':price_unit,
    #                         'invoice_line_tax_id':tax,
    #                         'account_id': obj_branch_config.dym_so_account_discount_program_external_id.id,
    #                         'invoice_id': inv_id,
    #                         'analytic_1': analytic_1 or False,
    #                         'analytic_2': analytic_2 or False,
    #                         'analytic_3': analytic_3 or False,
    #                         'account_analytic_id': analytic_4 or False,
    #                     }])
    #             if key=='discount_cash':
    #                 invoice_lines.append({
    #                         'name': 'Diskon Cash',
    #                         'quantity':1,
    #                         'origin':order.name,
    #                         'price_unit':price_unit,
    #                         'invoice_line_tax_id':tax,
    #                         'account_id': obj_branch_config.dym_so_account_discount_cash_id.id,
    #                         'invoice_id': inv_id,
    #                         'analytic_1':analytic_1 or False,
    #                         'analytic_2':analytic_2 or False,
    #                         'analytic_3':analytic_3 or False,
    #                         'account_analytic_id':analytic_4 or False,
    #                     })
    #             if key=='discount_lain':
    #                 invoice_lines.append({
    #                         'name': 'Diskon Lainnya',
    #                         'quantity':1,
    #                         'origin':order.name,
    #                         'price_unit':price_unit,
    #                         'invoice_line_tax_id':tax,
    #                         'account_id': obj_branch_config.dym_so_account_discount_lainnya_id.id,
    #                         'invoice_id': inv_id,
    #                         'analytic_1':analytic_1 or False,
    #                         'analytic_2':analytic_2 or False,
    #                         'analytic_3':analytic_3 or False,
    #                         'account_analytic_id':analytic_4 or False,
    #                     })
    #     for line in invoice_lines:
    #         line_id = self.pool.get('account.invoice.line').create(cr, uid, line, context=context)
    #     self.pool.get('account.invoice').button_reset_taxes(cr,uid,inv_id)
    #     workflow.trg_validate(uid, 'account.invoice', inv_id, 'invoice_open', cr)

    #     date_due_default = datetime.now().strftime('%Y-%m-%d')
    #     if order.branch_id.default_supplier_workshop_id.property_payment_term:
    #         pterm_list = order.branch_id.default_supplier_workshop_id.property_payment_term.compute(value=1, date_ref=date_due_default)[0]
    #         if pterm_list:
    #             date_due_default = max(line[0] for line in pterm_list)
    #     per_barang_bonus = {}
    #     for line in order.order_line:
    #         # if order.division=='Unit':
    #         #     analytic_1_line, analytic_2_line, analytic_3_line, analytic_4_line = self.pool.get('account.analytic.account').get_analytical(cr, uid, order.branch_id, '', line.product_id.categ_id, 4, 'Sales')
    #         # elif order.division=='Sparepart':
    #         #     analytic_1_line, analytic_2_line, analytic_3_line, analytic_4_line = self.pool.get('account.analytic.account').get_analytical(cr, uid, order.branch_id, '', line.product_id.categ_id, 4, 'Sparepart_Accesories')
    #         for disc in line.discount_line:
    #             if disc.tipe_diskon == 'percentage':
    #                 continue
    #             discount_gap = 0.0
    #             discount_md = 0.0
    #             discount_finco = 0.0
    #             discount_oi = 0.0
    #             sisa_ke_finco = False
                
    #             if disc.discount_pelanggan != disc.discount:
    #                  discount_gap =  disc.discount - disc.discount_pelanggan
    #                  print discount_gap
    #             taxes = [(6, 0, [y.id for y in line.tax_id])]
    #             if (disc.ps_ahm > 0 or disc.ps_md > 0):
    #                 #invoice ps_ahm
    #                 invoice_md = {}
    #                 invoice_md_line = []
        
    #                 if not (obj_branch_config.dym_so_journal_psmd_id.default_credit_account_id.id and obj_branch_config.dym_so_journal_psmd_id.default_debit_account_id.id):
    #                     raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal PS MD belum lengkap!"))
    #                 if not order.branch_id.default_supplier_workshop_id.id:
    #                     raise osv.except_osv(('Perhatian !'), ("Principle workshop di branch belum diisi, silahkan setting dulu!"))
    #                 invoice_md = {
    #                     'branch_id':order.branch_id.id,
    #                     'division':order.division,
    #                     'partner_id':order.branch_id.default_supplier_workshop_id.id,
    #                     'date':datetime.now().strftime('%Y-%m-%d'), 
    #                     'date_due': date_due_default, 
    #                     'reference': order.name,
    #                     'name':order.name,
    #                     'journal_id': obj_branch_config.dym_so_journal_psmd_id.id,
    #                     'account_id': obj_branch_config.dym_so_journal_psmd_id.default_debit_account_id.id,
    #                     'type': 'sale',
    #                     'analytic_1':analytic_1_general or False,
    #                     'analytic_2':analytic_2_general or False,
    #                     'analytic_3':analytic_3_general or False,
    #                     'analytic_4':analytic_4_general or False,
    #                 }
                    
    #                 if discount_gap >0:
    #                     if (disc.ps_md+disc.ps_ahm) >= discount_gap:
    #                         discount_md = disc.ps_md+disc.ps_ahm-discount_gap
    #                         discount_oi = discount_gap
    #                     else:
    #                         discount_md = discount_gap - disc.ps_md- disc.ps_ahm
                        
    #                     if discount_md>0:  
    #                         invoice_md_line.append([0,False,{
    #                             'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
    #                             'amount': discount_md,
    #                             'account_id': obj_branch_config.dym_so_journal_psmd_id.default_credit_account_id.id,
    #                             'type': 'cr',
    #                             'analytic_1':analytic_1 or False,
    #                             'analytic_2':analytic_2 or False,
    #                             'analytic_3':analytic_3 or False,
    #                             'account_analytic_id':analytic_4 or False,
    #                         }])
                        
    #                     if discount_oi>0:
    #                         invoice_md_line.append([0,False,{
    #                             'name': 'Sisa subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
    #                             'amount': discount_gap,
    #                             'account_id': obj_branch_config.dym_so_account_sisa_subsidi_id.id,
    #                             'type': 'cr',
    #                             'analytic_1':analytic_1 or False,
    #                             'analytic_2':analytic_2 or False,
    #                             'analytic_3':analytic_3 or False,
    #                             'account_analytic_id':analytic_4 or False,
    #                         }])
                        
    #                 else:
    #                     invoice_md_line.append([0,False,{
    #                         'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
    #                         'amount': disc.ps_ahm+disc.ps_md,
    #                         'account_id': obj_branch_config.dym_so_journal_psmd_id.default_credit_account_id.id,
    #                         'type': 'cr',
    #                         'analytic_1':analytic_1 or False,
    #                         'analytic_2':analytic_2 or False,
    #                         'analytic_3':analytic_3 or False,
    #                         'account_analytic_id':analytic_4 or False,
    #                     }])
    #                 invoice_md['line_cr_ids'] = invoice_md_line
    #                 per_ar.append(invoice_md)
    #         for barang_bonus in line.barang_bonus_line:
    #             if not per_barang_bonus.get(barang_bonus.product_subsidi_id.id,False):
    #                 per_barang_bonus[barang_bonus.product_subsidi_id.id] = {}
    #             per_barang_bonus[barang_bonus.product_subsidi_id.id]['product_qty'] = per_barang_bonus[barang_bonus.product_subsidi_id.id].get('product_qty',0)+ barang_bonus.barang_qty
    #             per_barang_bonus[barang_bonus.product_subsidi_id.id]['force_cogs'] = per_barang_bonus[barang_bonus.product_subsidi_id.id].get('force_cogs',0)+barang_bonus.price_barang
    #             if barang_bonus.bb_md > 0 or barang_bonus.bb_ahm > 0:
    #                 invoice_bb_md = {}
    #                 invoice_bb_md_line = []
                    
    #                 if not (obj_branch_config.so_journal_bbmd_id.default_credit_account_id.id and obj_branch_config.so_journal_bbmd_id.id):
    #                     raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal Barang Subsidi belum lengkap!"))
    #                 invoice_bb_md = {
    #                     # 'name':sale_order.name,
    #                     # 'origin': sale_order.name,
    #                     # 'branch_id':sale_order.branch_id.id,
    #                     # 'division':sale_order.division,
    #                     # 'partner_id':sale_order.branch_id.default_supplier_id.id,#default_suplier['default_supplier_id']['id'],
    #                     # 'date_invoice':datetime.now().strftime('%Y-%m-%d'),
    #                     # 'reference_type':'none',
    #                     # 'type': 'out_invoice', 
    #                     # 'tipe': 'bb_md',
    #                     # 'qq_id': sale_order.partner_id.id,
    #                     # 'journal_id': obj_branch_config.so_journal_bbmd_id.id,
    #                     # 'account_id': obj_branch_config.so_journal_bbmd_id.default_debit_account_id.id 

    #                     'branch_id':order.branch_id.id,
    #                     'division':order.division,
    #                     'partner_id':order.branch_id.default_supplier_id.id,
    #                     'date':datetime.now().strftime('%Y-%m-%d'), 
    #                     # 'amount': 0, 
    #                     'date_due': date_due_default, 
    #                     'reference': order.name, #
    #                     'name':order.name,
    #                     'user_id': order.user_id.id,
    #                     'journal_id': obj_branch_config.so_journal_bbmd_id.id,
    #                     'account_id': obj_branch_config.so_journal_bbmd_id.default_debit_account_id.id,
    #                     'type': 'sale',
    #                     'analytic_1':analytic_1_general or False,
    #                     'analytic_2':analytic_2_general or False,
    #                     'analytic_3':analytic_3_general or False,
    #                     'analytic_4':analytic_4_general or False,
    #                 }
    #                 invoice_bb_md_line = [[0,False,{
    #                     # 'name': 'Subsidi '+barang_bonus.barang_subsidi_id.name+' '+line.product_id.name,
    #                     # 'quantity': 1,
    #                     # 'origin': sale_order.name,
    #                     # 'price_unit':barang_bonus.bb_ahm+barang_bonus.bb_md ,
    #                     # 'account_id': obj_branch_config.so_journal_bbmd_id.default_credit_account_id.id

    #                     'name': 'Subsidi '+barang_bonus.barang_subsidi_id.name+' '+line.product_id.name,
    #                     'amount': barang_bonus.bb_ahm+barang_bonus.bb_md,
    #                     'account_id': obj_branch_config.so_journal_bbmd_id.default_credit_account_id.id,
    #                     'type': 'cr',
    #                     'analytic_1':analytic_1 or False,
    #                     'analytic_2':analytic_2 or False,
    #                     'analytic_3':analytic_3 or False,
    #                     'account_analytic_id':analytic_4 or False,
    #                 }]]
    #                 invoice_bb_md['line_cr_ids'] = invoice_bb_md_line
    #                 per_ar.append(invoice_bb_md)
    #             # if barang_bonus.bb_finco > 0:
    #             #     invoice_bb_finco = {}
    #             #     invoice_bb_finco_line = []
    #             #     if not (obj_branch_config.dealer_so_journal_bbfinco_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_bbfinco_id.id):
    #             #         raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal Barang Subsidi Finco belum lengkap!"))
    #             #     invoice_bb_finco = {
    #             #         # 'name':sale_order.name,
    #             #         # 'origin': sale_order.name,
    #             #         # 'branch_id':sale_order.branch_id.id,
    #             #         # 'division':sale_order.division,
    #             #         # 'partner_id':sale_order.finco_id.id,
    #             #         # 'date_invoice':datetime.now().strftime('%Y-%m-%d'),
    #             #         # 'reference_type':'none',
    #             #         # 'type': 'out_invoice', 
    #             #         # 'tipe': 'bb_finco',
    #             #         # 'qq_id': sale_order.partner_id.id,
    #             #         # 'journal_id': obj_branch_config.dealer_so_journal_bbfinco_id.id,
    #             #         # 'account_id': obj_branch_config.dealer_so_journal_bbfinco_id.default_debit_account_id.id 

    #             #         'branch_id':sale_order.branch_id.id,
    #             #         'division':sale_order.division,
    #             #         'partner_id':sale_order.finco_id.id,
    #             #         'date':datetime.now().strftime('%Y-%m-%d'), 
    #             #         # 'amount': 0, 
    #             #         'date_due': date_due_finco, 
    #             #         'reference': sale_order.name, #
    #             #         'name':sale_order.name,
    #             #         'user_id': sale_order.user_id.id,
    #             #         'journal_id': obj_branch_config.dealer_so_journal_bbfinco_id.id,
    #             #         'account_id': obj_branch_config.dealer_so_journal_bbfinco_id.default_debit_account_id.id,
    #             #         'type': 'sale'
    #             #     }
    #             #     invoice_bb_finco_line = [[0,False,{
    #             #         # 'name': 'Subsidi '+barang_bonus.barang_subsidi_id.name+' '+line.product_id.name,
    #             #         # 'quantity': 1,
    #             #         # 'origin': sale_order.name,
    #             #         # 'price_unit':barang_bonus.bb_finco ,
    #             #         # 'account_id': obj_branch_config.dealer_so_journal_bbfinco_id.default_credit_account_id.id

    #             #         'name': 'Subsidi '+barang_bonus.barang_subsidi_id.name+' '+line.product_id.name,
    #             #         'amount': barang_bonus.bb_finco,
    #             #         'account_id': obj_branch_config.dealer_so_journal_bbfinco_id.default_credit_account_id.id,
    #             #         'type': 'cr',
    #             #     }]]
    #             #     invoice_bb_finco['line_cr_ids'] = invoice_bb_finco_line
    #             #     per_ar.append(invoice_bb_finco)
    #     for value in per_ar:
    #         create_ar = self.pool.get('account.voucher').create(cr,uid,value,context=context)
    #     return inv_id

    def action_ship_create(self, cr, uid, ids, context=None):
        res = super(dym_sale_order,self).action_ship_create(cr, uid, ids, context=context)
        self.signal_workflow(cr, uid, ids, 'manual_invoice')
        stock_move = self.pool.get('stock.move')
        todo_moves = []
        for order in self.browse(cr,uid,ids):
            if not order.picking_ids:
                continue
            location = self._get_default_location_delivery_sales(cr,uid,order.id)
            barang_bonuses = {}
            for lines in order.order_line:
                if lines.barang_bonus_line:
                    for barang_bonus in lines.barang_bonus_line:
                        if not barang_bonuses.get(barang_bonus.product_subsidi_id.id,False):
                            barang_bonuses[barang_bonus.product_subsidi_id.id] = {}
                        barang_bonuses[barang_bonus.product_subsidi_id.id]['qty'] = barang_bonuses[barang_bonus.product_subsidi_id.id].get('qty',0) + barang_bonus.barang_qty
                        barang_bonuses[barang_bonus.product_subsidi_id.id]['price_barang'] = barang_bonuses[barang_bonus.product_subsidi_id.id].get('price_barang',0) + barang_bonus.price_barang
                        barang_bonuses[barang_bonus.product_subsidi_id.id]['line'] = lines
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
                        'sale_order_line_id': value['line'].id or False,
                        'group_id': order.picking_ids[0].group_id.id,
                        'picking_id': order.picking_ids[0].id,
                        'state': 'draft',
                        }
                move = stock_move.create(cr, uid, vals, context=context)
                todo_moves.append(move)
        todo_moves = stock_move.action_confirm(cr, uid, todo_moves)
        stock_move.action_assign(cr, uid, todo_moves)
        return res
    
    def action_button_confirm(self, cr, uid, ids, context=None):
        obj_picking = self.pool.get('stock.picking')
        order = self.browse(cr,uid,ids)
        
        qty = {}
        approved_qty = {}
        for line in order.order_line:
            for barang_bonus in line.barang_bonus_line:
                barang_bonus.write({'force_cogs':barang_bonus.price_barang})
            # if line.discount_cash_persen > 0:
            #     price = (line.price_unit * line.product_uom_qty) * (1 - (line.discount or 0.0) / 100.0) - line.discount_program - line.discount_lain
            #     discount_cash = (price*line.discount_cash_persen)/100
            #     if discount_cash != line.discount_cash:
            #         raise osv.except_osv(('Amount discount cash tidak sama dengan hasil perhitungan dari %s!') % str(line.discount_cash_persen)+'%', ('Klik Renew Price untuk update discount cash atau ubah discount cash (%) menjadi 0 jika ingin menggunakan amount saja'))
        if order.state == 'draft' :
            for x in order.order_line :
                qty[x.product_id] = qty.get(x.product_id,0) + x.product_uom_qty
            if order.distribution_id:
                for x in order.distribution_id.distribution_line :
                    qty[x.product_id] = qty.get(x.product_id,0) + x.qty
                    approved_qty[x.product_id] = approved_qty.get(x.product_id,0) + x.approved_qty
                    if (approved_qty[x.product_id] - qty[x.product_id]) >= 0 :
                        x.write({'qty':qty[x.product_id]})
                    else :
                        raise osv.except_osv(('Perhatian !'), ("Quantity Product '%s' melebihi Approved Qty"%x.product_id.name_template))
        
        if all(x.approved_qty - x.qty == 0 for x in order.distribution_id.distribution_line) and order.distribution_id:
            order.distribution_id.state = 'done'
        if not order.payment_term:
            payment_term = order.payment_term.line_ids.search([('days','=',0),('days2','=',0),('value','=','balance')]).mapped('payment_id').filtered(lambda r: len(r.line_ids) == 1)
            if payment_term:
                order.write({'payment_term':payment_term[0].id})
        invoice_total = self._invoice_total(cr, uid, ids, order.partner_id.id,order.division) + order.amount_total
        if not(order.payment_term and len(order.payment_term.line_ids.ids) == 1 and order.payment_term.line_ids.days == 0 and order.payment_term.line_ids.days2 == 0 and order.payment_term.line_ids.value == 'balance'):
            if order.division == 'Unit':
                if round(invoice_total,2) > round(order.partner_id.credit_limit_unit,2):
                    raise osv.except_osv(('Tidak bisa confirm!'), ('Total order melebihi batas limit plafond\nLimit Plafond = %d sedangkan total invoiced+order sekarang = %d') % (order.partner_id.credit_limit_unit,invoice_total))
            elif order.division == 'Sparepart' :
                if (round(invoice_total,2) > round(order.partner_id.credit_limit_sparepart,2)) and order.partner_id.credit_limit_sparepart != 0:
                    raise osv.except_osv(('Tidak bisa confirm!'), ('Total order melebihi batas limit plafond\nLimit Plafond = %d sedangkan total invoiced+order sekarang = %d') % (order.partner_id.credit_limit_sparepart,invoice_total))
        
        if order.division == 'Sparepart':
            for line in order.order_line:
                if line.product_id.product_tmpl_id.is_bundle:
                    for fake_line in line.product_id.product_tmpl_id.item_ids:
                        obj_picking.compare_sale_stock(cr,uid,order.branch_id.id,order.division,fake_line.product_id.id,fake_line.product_uom_qty*line.product_uom_qty)
                else:
                    obj_picking.compare_sale_stock(cr,uid,order.branch_id.id,order.division,line.product_id.id,line.product_uom_qty)
        res = super(dym_sale_order,self).action_button_confirm(cr,uid,ids,context=context)
        self.write(cr, uid, ids, {'date_order':datetime.now(),'confirm_uid':uid,'confirm_date':datetime.now()})
        # if order.amount_tax and not order.pajak_gabungan and not order.pajak_gunggung:
        #     self.pool.get('dym.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'sale.order',context=context)     
        # if order.amount_tax and order.pajak_gunggung == True :   
        #     self.pool.get('dym.faktur.pajak.out').create_pajak_gunggung(cr,uid,ids,'sale.order',context=context)                            
        return res
    
    def _get_pricelist(self, cr, uid, ids):
        sale_order = self.browse(cr, uid, ids)
        if sale_order.pricelist_id:
            current_pricelist = sale_order.pricelist_id.id
        elif sale_order.division == 'Unit' :
            current_pricelist = sale_order.branch_id.pricelist_unit_sales_id.id
        elif sale_order.division == 'Sparepart' :
            current_pricelist = sale_order.branch_id.pricelist_part_sales_id.id
        else :
            current_pricelist = sale_order.partner_id.property_product_pricelist.id
        sale_order.write({'pricelist_id':current_pricelist})
        return current_pricelist
    
    def renew_price(self, cr, uid, ids, context=None):
        for sale_order in self.browse(cr, uid, ids):
            for lines in sale_order.order_line:
                if lines.product_id :
                    current_pricelist = self._get_pricelist(cr, uid, ids)
    
                    if not current_pricelist:
                        raise osv.except_osv( ('Perhatian!'), ("Tidak ditemukan konfigurasi pricelist beli cabang sekarang, konfigurasi dulu!"))
                    
                    current_price = self.pool.get('product.pricelist').price_get(cr, uid, [current_pricelist], lines.product_id.id, 1)[current_pricelist]
                     
                    if not current_price:
                        raise osv.except_osv( ('Perhatian!'), ("Tidak ditemukan harga produk %s di pricelist yg aktif!") % lines.product_id.name)
                    
                    lines.write({'price_unit':current_price})
                # if lines.discount_cash_persen > 0:
                #     price = (lines.price_unit * lines.product_uom_qty) * (1 - (lines.discount or 0.0) / 100.0) - lines.discount_program - lines.discount_lain
                #     discount_cash = (price*lines.discount_cash_persen)/100
                #     lines.write({'discount_cash':discount_cash})
        return True

    
class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'

    def _get_pricelist(self, cr, uid,  partner_id, branch_id, division, pricelist):
        current_pricelist = False
        if pricelist:
            current_pricelist = pricelist
        elif division == 'Unit' and branch_id:
            branch = self.pool.get('dym.branch').browse(cr, uid, branch_id)
            current_pricelist = branch.pricelist_unit_sales_id.id
        elif division == 'Sparepart' and branch_id:
            branch = self.pool.get('dym.branch').browse(cr, uid, branch_id)
            current_pricelist = branch.pricelist_part_sales_id.id
#         elif self.division == 'Umum' :
#             current_pricelist = self.branch_id.pricelist_umum_purchase_id.id            
        else :
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
            current_pricelist = partner.property_product_pricelist_purchase.id
        return current_pricelist

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, tax_id=[(6, 0, [])], discount_show=0, discount_line=[(6, 0, [])], discount_lain=0, discount_cash=0, discount_cash_persen=0, tipe_transaksi='', discount=0, discount_pcs=0, discount_lain_pcs=0, discount_cash_pcs=0, disc_persen=False, disc_amount=False, disc_sum=False, cash_persen=False, cash_amount=False, cash_sum=False, lain_amount=False, lain_sum=False, context=None):
        
        res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)
        
        if product and 'division' in context and 'branch_id' in context:
            qty_in_picking = self.pool.get('stock.picking')._get_qty_picking(cr,uid, context['branch_id'], context['division'], product)
            qty_in_quant = self.pool.get('stock.picking')._get_qty_quant(cr, uid, context['branch_id'], product)
            qty_available = qty_in_quant - qty_in_picking
            res['value'].update({'qty_available': qty_available})
            if 'quantity' in context and context['quantity'] > qty_available:
                lost_order_qty = context['quantity'] - qty_available
                res['value'].update({'lost_order_qty': lost_order_qty})
                if qty_available > 0:
                    res['value'].update({'product_uom_qty': qty_available})
            else:
                res['value'].update({'lost_order_qty': 0})
            current_pricelist = self._get_pricelist(cr, uid, partner_id, context['branch_id'], context['division'], pricelist)
            if current_pricelist:
                current_price = self.pool.get('product.pricelist').price_get(cr, uid,[current_pricelist], product, 1)[current_pricelist]
                if current_price > 0:
                    fill_subtotal = self.calculate_sub_total(cr, uid, ids, partner_id, product, qty, current_price, tax_id, discount, discount_pcs, discount_show, discount_lain_pcs, discount_lain, discount_cash_persen, discount_cash_pcs, discount_cash, discount_line,  disc_persen=disc_persen, disc_amount=disc_amount, disc_sum=disc_sum, cash_persen=cash_persen, cash_amount=cash_amount, cash_sum=cash_sum, lain_amount=lain_amount, lain_sum=lain_sum)
        
                    res['value'].update(fill_subtotal['value'])
                    res['value'].update({'product_uom_show': uom,'price_unit_show': current_price,'price_unit': current_price,'discount_line':False,'barang_bonus_line':False})
                else:        
                    return {'value':{'product_id':False,'price_unit':0,'discount_line':False,'barang_bonus_line':False},'warning':{'title':'Perhatian !','message':'Data Pricelist tidak ditemukan untuk produk "%s", silahkan konfigurasi data cabang dulu.' % (self.pool.get('product.product').browse(cr,uid,product).name)}}
            else:
                return {'value':{'product_id':False,'price_unit':0,'discount_line':False,'barang_bonus_line':False},'warning':{'title':'Perhatian !','message':'Data Pricelist tidak ditemukan, silahkan konfigurasi data cabang dulu.'}}
        else:
            return {'value':{'price_unit':0,'discount_line':False,'barang_bonus_line':False}}

        prod = self.pool.get('product.product').browse(cr, uid, [product], context=context)
        if prod.default_code and prod.default_code != prod.name:
            res['value']['name'] = '%s [%s]' % (prod.name,prod.default_code)
        else:
            res['value']['name'] = prod.name
        return res


    def _get_branch(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for so in self.browse(cr, uid, ids):
            res[so.id] = {
                'branch_dummy': 0,
                'division_dummy': '',
                'customer_dummy': 0,
                'tipe_transaksi_dummy': 'hotline',
            }
            for sale_order in self.pool.get('sale.order').browse(cr,uid,so.order_id.id):
                res[so.id]['branch_dummy'] = sale_order.branch_id.id
                res[so.id]['division_dummy'] = sale_order.division
                res[so.id]['customer_dummy'] = sale_order.partner_id.id
                res[so.id]['tipe_transaksi_dummy'] = sale_order.tipe_transaksi
        return res

    def _get_discount(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('dealer.sale.order.line.discount.line').browse(cr, uid, ids, context=context):
            result[line.dealer_sale_order_line_discount_line_id.id] = True
        return result.keys()

    def _amount_discount_program(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for discount in self.browse(cr, uid, ids, context=context):
            res[discount.id] = {
                'discount_program': 0.0,
            }
            val = 0
            for line in discount.discount_line:
                if line.tipe_diskon == 'percentage':
                    val += (discount.price_unit * line.discount_pelanggan / 100)
                else:
                    val += line.discount_pelanggan 
            res[discount.id]['discount_program'] = val * discount.product_uom_qty
        return res  

    # def _amount_discount_cash(self, cr, uid, ids, field_name, arg, context=None):
    #     res = {}
    #     for line in self.browse(cr, uid, ids, context=context):
    #         res[line.id] = {
    #             'discount_cash': 0.0,
    #         }
    #         discount_cash = 0.0
    #         price = (line.price_unit * line.product_uom_qty) * (1 - (line.discount or 0.0) / 100.0) - line.discount_program - line.discount_lain
    #         discount_cash = (price*line.discount_cash_persen)/100
    #         res[line.id]['discount_cash'] = discount_cash
    #     return res  

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
            discount_program = discount_program * line.product_uom_qty
            price = (line.price_unit * line.product_uom_qty) - line.discount_show - discount_program - line.discount_cash - line.discount_lain
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, 1, line.product_id, line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res

    def _get_qty_available(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for qty in self.browse(cr, uid, ids, context=context):
            qty_available_show=qty.qty_available
            res[qty.id]=qty_available_show
        return res

    def _get_discount_approval(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            discount_show = line.discount_show
            discount_dealer = 0
            for program_line in line.discount_line:
                if program_line.tipe_diskon == 'percentage':
                    discount_dealer += (line.price_unit * program_line.discount_pelanggan / 100)
                else:
                    discount_dealer += program_line.ps_dealer 
            discount_dealer = discount_dealer * line.product_uom_qty
            res[line.id] = {
                'discount_show': discount_show,
                'discount_dealer': discount_dealer,
            }
        return res

    _columns = {
        'categ_id':fields.many2one('product.category','Category',required=True),
        'force_cogs': fields.float('Force COGS'),
        'discount_line': fields.one2many('dealer.sale.order.line.discount.line','sale_order_line_discount_line_id','Discount Line',),
        'barang_bonus_line': fields.one2many('dealer.sale.order.line.brgbonus.line','sale_order_line_brgbonus_line_id', 'Barang Bonus Line'),
        'branch_dummy': fields.function(_get_branch,type='integer',multi=True),
        'division_dummy': fields.function(_get_branch,type='char',multi=True),
        'customer_dummy': fields.function(_get_branch,type='integer',multi=True),
        'tipe_transaksi_dummy': fields.function(_get_branch,type='char',multi=True),
        'discount_program': fields.function(_amount_discount_program, string='Disc Program', digits_compute= dp.get_precision('Account'),store={
                    'sale.order.line': (lambda self, cr, uid, ids, c={}: ids, ['discount_line'], 10),
                     },multi='sums', help="Discount Program."),
        # 'discount_cash': fields.function(_amount_discount_cash, string='Disc Cash', digits_compute= dp.get_precision('Account'),
        #       store={
        #             'sale.order.line': (lambda self, cr, uid, ids, c={}: ids, ['categ_id','tax_id','product_id','price_unit','discount_cash_persen','discount_lain','discount_program','product_uom_qty','discount'], 10),
        #              },multi='sums', help="Discount Program."),
        'discount_cash': fields.float(string='Discount Cash', digits_compute= dp.get_precision('Account')),
        'discount_lain': fields.float(string='Discount Lain', digits_compute= dp.get_precision('Account'), help="Discount Lain.", copy=False),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account'), help="Price Subtotal."),
        # 'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account'), store= {'dym.sale.order.line': (lambda self, cr, uid, ids, c={}: ids, ['price_unit','product_qty','discount','discount_lain','discount_line','discount_program','tax_id','discount_cash'], 10),
        'discount_cash_persen': fields.float('Discount Cash (%)', copy=False),
        'lost_order_qty': fields.float('Lost Order QTY'),
        'qty_available':fields.float('Qty Avb'),
        'qty_available_show':fields.function(_get_qty_available,string='Qty Avb'),
        'save_lost_order': fields.boolean('Save Lost Order'),
        'product_uom_show': fields.related('product_uom',relation='product.uom',type='many2one',string='Unit of Measure',readonly=True),
        'price_unit_show':fields.related('price_unit',string='Unit Price',readonly=True),
        'discount_show': fields.float(string='Discount Sum', digits_compute= dp.get_precision('Account')),
        'discount_cash_pcs': fields.float(string='Discount Cash Pcs', digits_compute= dp.get_precision('Account')),
        'discount_lain_pcs': fields.float(string='Discount Lain Pcs', digits_compute= dp.get_precision('Account')),
        'discount_pcs': fields.float(string='Discount Pcs', digits_compute= dp.get_precision('Account')),
        'discount_dealer':fields.function(_get_discount_approval, string='Discount Dealer', multi='sumsa'),
        'disc_persen': fields.boolean('Discount Persen'),
        'disc_amount': fields.boolean('Discount Amount'),
        'disc_sum': fields.boolean('Discount Sum'),
        'cash_persen': fields.boolean('Cash Persen'),
        'cash_amount': fields.boolean('Cash Amount'),
        'cash_sum': fields.boolean('Cash Sum'),
        'lain_amount': fields.boolean('Lain Amount'),
        'lain_sum': fields.boolean('Lain Sum'),
        'discount_2': fields.related('discount',type='float',readonly=True),
        'discount_pcs_2': fields.related('discount_pcs',type='float',readonly=True),
        'discount_show_2': fields.related('discount_show',type='float',readonly=True),
        'discount_lain_pcs_2': fields.related('discount_lain_pcs',type='float',readonly=True),
        'discount_lain_2': fields.related('discount_lain',type='float',readonly=True),
        'discount_cash_persen_2': fields.related('discount_cash_persen',type='float',readonly=True),
        'discount_cash_pcs_2': fields.related('discount_cash_pcs',type='float',readonly=True),
        'discount_cash_2': fields.related('discount_cash',type='float',readonly=True),
    }

    _defaults = {
        'discount_lain': 0.0,
    }

    def create_qty_available(self, cr, uid, ids,qty_available):
        value = {}
        if not qty_available:
           value ={'qty_available_show':0}
        else:
            value={'qty_available_show':qty_available}
        return {'value':value}

    def change_save_lost_order(self, cr, uid, ids, branch_dummy, product_id, lost_order_qty, qty_available, product_uom_qty, price_unit, context=None):
        value = {}
        value['lost_order_qty'] = 0
        '''
        Deactivated as Pica request #211
        if lost_order_qty > 0 and branch_dummy and product_id and lost_order_qty:
            res = {'date':datetime.now().strftime('%Y-%m-%d'), 'branch_id': branch_dummy, 'product_id': product_id, 'lost_order_qty': lost_order_qty , 'tipe_dok': 'SO', 'no_dok': '', 'pemenuhan_qty': product_uom_qty, 'het': price_unit, 'rec_id': 0, 'rec_model':'sale.order.line'}
            self.pool.get('dym.lost.order').create(cr, uid, res)
            if qty_available > 0:
                value['product_uom_qty'] = qty_available
            value['lost_order_qty'] = 0
            value['save_lost_order'] = False
            value['qty_available_show'] = qty_available
            value['qty_available'] = qty_available
        '''
        return {'value':value}

    def fill_show_field(self, cr, uid, ids, field, value, context=None):
        value = {}
        value[field] = value
        return {'value':value}

    def change_check(self, cr, uid, ids, field_state, enable_check_field, disable_check_field=[], discount_fields=[]):
        value = {}
        if disable_check_field and field_state == True:
            for field in disable_check_field:
                value[field] = False
        if discount_fields and field_state == False:
            for field in discount_fields:
                value[field] = 0
        return {'value':value}


    def calculate_sub_total(self, cr, uid, ids, partner_id, product_id, product_uom_qty, price_unit, tax_id, discount, discount_pcs, discount_show, discount_lain_pcs, discount_lain, discount_cash_persen, discount_cash_pcs, discount_cash, discount_line,  disc_persen=False, disc_amount=False, disc_sum=False, cash_persen=False, cash_amount=False, cash_sum=False, lain_amount=False, lain_sum=False):
        tax_obj = self.pool.get('account.tax')
        value = {}
        warning = {}
        if lain_amount == True:
            if discount_lain_pcs > 0:
                discount_lain = product_uom_qty*discount_lain_pcs
            else:
                discount_lain_pcs = 0
                discount_lain = 0
        if lain_sum == True:
            if discount_lain > 0 and product_uom_qty > 0:
                discount_lain_pcs = discount_lain/product_uom_qty
            else:
                discount_lain_pcs = 0
                discount_lain = 0
        if disc_persen == True:
            if discount > 100:
                discount = 0
                warning = {
                    'title': 'perhatian!',
                    'message': 'maksimal discount 100%'
                }
            elif discount < 0:
                discount = 0
                warning = {
                    'title': 'perhatian!',
                    'message': 'tidak boleh input nilai negatif'
                }
            if discount > 0:
                discount_pcs = (price_unit * 1 * discount)/100
                discount_show = discount_pcs * product_uom_qty
            else:
                discount = 0
                discount_pcs = 0
                discount_show = 0
        if disc_amount == True:
            if discount_pcs > 0:
                discount_show = product_uom_qty*discount_pcs
            else:
                discount = 0
                discount_pcs = 0
                discount_show = 0
        if disc_sum == True:
            if discount_show > 0 and product_uom_qty > 0:
                discount_pcs = discount_show/product_uom_qty
            else:
                discount = 0
                discount_pcs = 0
                discount_show = 0
        discount_program = 0
        discount_dealer = 0
        lines = self.resolve_2many_commands(cr, uid, 'discount_line', discount_line, ['discount_pelanggan','tipe_diskon','ps_dealer'])
        for disc in lines:
            discount_program += disc['discount_pelanggan'] if disc['tipe_diskon'] != 'percentage' else (price_unit*disc['discount_pelanggan']/100)
            discount_dealer += disc['ps_dealer'] if disc['tipe_diskon'] != 'percentage' else (price_unit*disc['ps_dealer']/100)
        discount_program = discount_program * product_uom_qty
        discount_dealer = discount_dealer * product_uom_qty
        if cash_persen == True:
            if discount_cash_persen > 100:
                discount_cash_persen = 0
                warning = {
                    'title': 'perhatian!',
                    'message': 'maksimal discount cash 100%'
                }
            elif discount_cash_persen < 0:
                discount_cash_persen = 0
                warning = {
                    'title': 'perhatian!',
                    'message': 'tidak boleh input nilai negatif'
                }
            if discount_cash_persen > 0 and product_uom_qty > 0:
                price_pcs = (price_unit * 1) - discount_pcs - (discount_program/product_uom_qty) - discount_lain_pcs
                discount_cash_pcs = (price_pcs * discount_cash_persen)/100
                discount_cash = product_uom_qty*discount_cash_pcs
            else:
                discount_cash_persen = 0
                discount_cash_pcs = 0
                discount_cash = 0
        if cash_amount == True:
            if discount_cash_pcs > 0 and product_uom_qty > 0:
                discount_cash = product_uom_qty*discount_cash_pcs
            else:
                discount = 0
                discount_cash_pcs = 0
                discount_cash = 0
        if cash_sum == True:
            if discount_cash > 0 and product_uom_qty > 0:
                discount_cash_pcs = discount_cash/product_uom_qty
            else:
                discount = 0
                discount_cash_pcs = 0
                discount_cash = 0
        price = (price_unit * product_uom_qty) - discount_show - discount_program - discount_lain - discount_cash
        tax_lines = self.resolve_2many_commands(cr, uid, 'tax_id', tax_id, ['id'])
        tax_ids = []
        for tax in tax_lines:
            tax_ids.append(tax['id'])
        taxes_obj = tax_obj.browse(cr, uid, tax_ids)
        product = self.pool.get('product.product').browse(cr, uid, product_id)
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
        taxes = tax_obj.compute_all(cr, uid, taxes_obj, price, 1, product, partner)
        price_subtotal = taxes['total']
        value['discount'] = discount
        value['discount_pcs'] = discount_pcs
        value['discount_show'] = discount_show
        value['discount_lain_pcs'] = discount_lain_pcs
        value['discount_lain'] = discount_lain
        value['discount_cash_pcs'] = discount_cash_pcs
        value['discount_cash_persen'] = discount_cash_persen
        value['discount_cash'] = discount_cash
        value['discount_program'] = discount_program
        value['discount_dealer'] = discount_dealer
        value['price_subtotal'] = price_subtotal
        value['discount_2'] = discount
        value['discount_pcs_2'] = discount_pcs
        value['discount_show_2'] = discount_show
        value['discount_lain_pcs_2'] = discount_lain_pcs
        value['discount_lain_2'] = discount_lain
        value['discount_cash_pcs_2'] = discount_cash_pcs
        value['discount_cash_persen_2'] = discount_cash_persen
        value['discount_cash_2'] = discount_cash
        return {'value':value,'warning':warning}
        
    def category_change(self, cr, uid, ids, categ_id, branch_id, division, pricelist_id, customer_id, tipe_transaksi, product_id):
        if not branch_id or not division :
            raise osv.except_osv(('No Branch or Division Defined!'), ('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        if division in ('Unit', 'Sparepart') and not pricelist_id :
            raise osv.except_osv(('No Purchase Pricelist Defined!'), ('Sebelum menambah detil transaksi,\n harap set pricelist terlebih dahulu di Branch Configuration.'))
        product_obj = self.pool.get('product.product')
        product_id = product_obj.browse(cr, uid, product_id)
        dom = {}
        val = {}
        val['product_id'] = False
        if categ_id:
            categ_ids = self.pool.get('product.category').get_child_by_ids(cr,uid,categ_id)
            dom['product_id']=[('categ_id','in',categ_ids),('sale_ok','=',True),('product_tmpl_id.is_bundle','=',False)]
        else:
            print "False", categ_id, product_id
            val['product_id'] = False
            dom['product_id']=[('id','in',[])]
        return {
            'value':{
                'branch_dummy':branch_id,
                'division_dummy':division,
                'customer_dummy':customer_id,
                'tipe_transaksi_dummy': tipe_transaksi,
                'product_id' : False,
            },
            'domain':dom
        }
    
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        res = super(sale_order_line,self)._prepare_order_line_invoice_line(cr, uid, line, account_id=account_id, context=context)
        res.update({'discount':0})
        branch_config_ids = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',line.order_id.branch_id.id)])
        # if line.discount != 0:
        #     discount_amount = ((line.price_unit * line.product_uom_qty) * (line.discount or 0.0)) / 100.0
        #     res.update({'discount_amount':discount_amount})
        if not branch_config_ids:
            raise osv.except_osv(('Perhatian !'), ("Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu"))
        else:
            branch_config = self.pool.get('dym.branch.config').browse(cr,uid,branch_config_ids[0])
            cc_string = 'Sparepart_Accesories'
            if line.product_id.categ_id.isParentName('Unit'):
                cc_string = 'Sales'
            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, line.order_id.branch_id, '', line.order_id.order_line[0].product_id.categ_id, 4, cc_string)
            res.update({
                'analytic_1':analytic_1 or False,
                'analytic_2':analytic_2 or False,
                'analytic_3':analytic_3 or False,
                'account_analytic_id':analytic_4 or False,
                })
        if line.product_id:
            if line.product_id.product_tmpl_id.cost_method == 'real':
                pricelist_beli_md = line.order_id.branch_id.pricelist_unit_purchase_id.id
                if not pricelist_beli_md:
                    raise osv.except_osv(('No Sale Pricelist Defined!'), ('Tidak bisa confirm'))
                purchase_price = round(self.pool.get('product.pricelist').price_get(cr, uid, [pricelist_beli_md], line.product_id.id, 1,0)[pricelist_beli_md]/1.1,2)
                force_cogs = purchase_price*line.product_uom_qty
                res.update({'force_cogs':force_cogs})
                line.update({'force_cogs':force_cogs})
            elif line.product_id.product_tmpl_id.cost_method == 'average':
                product_price_branch_obj = self.pool.get('product.price.branch')
                product_price_avg_id = product_price_branch_obj._get_price(cr, uid, line.order_id.warehouse_id.id, line.product_id.id)
                line.update({'force_cogs':product_price_avg_id})

            list_product_bundle = ''
            if line.product_id.product_tmpl_id.is_bundle:
                list_product_bundle += ' ['
                for fake_line in line.product_id.product_tmpl_id.item_ids:
                    list_product_bundle += fake_line.product_id.name + ', '
                list_product_bundle = list_product_bundle[:-2]
                list_product_bundle += ']'
            res.update({'name':line.product_id.name + list_product_bundle})
        return res
    
    def button_confirm(self, cr, uid, ids, context=None):
        res = super(sale_order_line,self).button_confirm(cr, uid, ids, context=context)
        for line in self.browse(cr, uid, ids):
            if line.order_id.pricelist_id:
                current_pricelist = line.order_id.pricelist_id.id
            elif line.order_id.division == 'Unit' :
                current_pricelist = line.order_id.branch_id.pricelist_unit_sales_id.id
            elif line.order_id.division == 'Sparepart' :
                current_pricelist = line.order_id.branch_id.pricelist_part_sales_id.id
            price_unit = round(line.price_unit,2) 
            current_price = round(self.pool.get('product.pricelist').price_get(cr, uid, [current_pricelist], line.product_id.id, 1,0)[current_pricelist],2)
            if price_unit != current_price:
                raise osv.except_osv(('Price unit %s tidak sama dengan pricelist!') % line.product_id.name, ('Klik Renew Price untuk update harga'))
        return res