import time
from datetime import datetime,timedelta
from openerp import workflow
from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import fields, osv, orm
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
from lxml import etree
from openerp.osv.orm import setup_modifiers

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Supplier Invoice
    'out_refund': 'out_invoice',        # Customer Refund
    'in_refund': 'in_invoice',          # Supplier Refund
}

RETUR_TYPE = [
    ('Uang','Uang'),
    ('Admin','Admin'),
    # ('Barang','Barang'),
]

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')

class wiz_retur_jual_line(orm.TransientModel):
    _name = 'wiz.retur.jual.line'
    _description = "Retur Jual Wizard Line"
    _columns = {
        'wizard_retur_jual_id': fields.many2one('wiz.retur.jual', 'Wizard ID'),
        'check_process':fields.boolean('Process?'),
        'product_id': fields.many2one('product.product', 'Product'),
        'product_qty': fields.integer('Quantity', required=True),
        'engine_number': fields.many2one('stock.production.lot', 'Engine Number'),
        'move_id': fields.many2one('stock.move', 'Move'),
        'jual_line_id': fields.many2one('dym.retur.jual.line', 'Jual Line ID'),
        'engine_number_retur': fields.many2one('stock.production.lot', 'Engine Number Retur', domain="[('state','=','stock'),('product_id','=',product_id),('location_id.branch_id','=',parent.branch_id),('location_id.usage','=','internal')]"),
    }

    def onchange_engine(self, cr, uid, ids, invoice_id, product_id, engine_number):
        value = {}
        domain = {}
        warning = {}
        # if not invoice_id or not partner_id:
        #     value['engine_number'] = False
        #     return {'value':value,'warning':{'title':'Perhatian !', 'message':'Sebelum menambah detil transaksi,\n harap isi invoice, dan supplier terlebih dahulu.'}}
        # id_product = self.pool.get('product.product').browse(cr, uid, product_id)
        # if not id_product.categ_id.isParentName('Unit') :
        #     value['engine_number'] = False
        #     return {'value':value,'warning':{'title':'Perhatian !', 'message':'Field nomor engine hanya berlaku untuk produk unit'}}
        # packing_line_obj = self.pool.get('dym.stock.packing.line')
        # val = self.pool.get('account.invoice').search(cr, uid, [('id', '=', [invoice_id])])
        # serial_number_ids = []
        # packing_line_ids = packing_line_obj.search(cr, uid, [('packing_id.picking_id.origin','=',val.name),('product_id','=',product_id),('packing_id.state','=','posted')])
        # for line in packing_line_obj.browse(cr, uid, packing_line_ids):
        #     if engine_number and line.serial_number_id.id == engine_number:
        #         move_obj = self.pool.get('stock.move')
        #         move_search = move_obj.search(cr, uid, [('picking_id', '=', line.packing_id.picking_id.id), ('product_id', '=', product_id), ('state', '=', 'done')])
        #         value['move_id'] = move_search[0]
        #     if line.serial_number_id.id not in serial_number_ids:
        #         serial_number_ids.append(line.serial_number_id.id)
        # domain['engine_number'] = [('id','in',serial_number_ids)]
        # value['product_qty'] = 1
        return  {'value':value, 'domain':domain, 'warning':warning}

    def quantity_change(self, cr, uid, ids, quantity, id_product, jual_line_id, context=None):
        value = {}
        warning = {}
        product_id = self.pool.get('product.product').browse(cr, uid, id_product)
        value['check_process'] = True
        if product_id.categ_id.isParentName('Unit') :
            value['product_qty'] = 1
            return {'value':value}
        jual_line = self.pool.get('dym.retur.jual.line').browse(cr, uid, jual_line_id)
        move_obj = self.pool.get('stock.move')
        move_search = move_obj.search(cr, uid, [('picking_id.origin', 'ilike', jual_line.retur_id.invoice_id.origin), ('product_id', '=', id_product), ('state', '=', 'done')])
        received_qty = 0
        for move in self.pool.get('stock.move').browse(cr, uid, move_search):
            search_return_history = move_obj.search(cr, uid, [('origin_returned_move_id', '=', move.id), ('state', 'not in', ('draft','cancel'))])
            return_history_qty = 0
            for return_history in self.pool.get('stock.move').browse(cr, uid, search_return_history):
                return_history_qty += return_history.product_uom_qty
            received_qty += move.product_uom_qty - return_history_qty
        barang_line_ids = self.pool.get('dym.retur.barang.jual.line').search(cr, uid, [('jual_line_id','=',jual_line_id)])
        barang_line_brw = self.pool.get('dym.retur.barang.jual.line').browse(cr, uid, barang_line_ids)
        barang_line_qty = 0
        for barang_line in barang_line_brw:
            barang_line_qty += barang_line.product_qty
        received_qty -= barang_line_qty
        if received_qty > jual_line.product_qty:
            received_qty = jual_line.product_qty

        if quantity <= 0 :
            value['product_qty'] = received_qty
            return {'value':value,'warning':{'title':'Perhatian !', 'message':'Quantity tidak boleh kurang dari 1'}}
        if quantity > received_qty:
            value['product_qty'] = received_qty
            return {'value':value,'warning':{'title':'Perhatian !', 'message':'Maximal quantity yang bisa di retur adalah '+str(received_qty)}}
        return {'value':value}

class wiz_retur_jual(orm.TransientModel):
    _name = 'wiz.retur.jual'
    _description = "Retur Jual Wizard"

    _columns = {
        'retur_id' : fields.many2one('dym.retur.jual','Retur Penjualan'),
        'branch_id' : fields.many2one('dym.branch','Branch'),
        'invoice_id' : fields.many2one('account.invoice','Invoice'),
        'line_ids': fields.one2many('wiz.retur.jual.line', 'wizard_retur_jual_id'),
    }
    _defaults = {
        'retur_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False,
        'invoice_id': lambda self, cr, uid, ctx: ctx and ctx.get('invoice_id', False) or False,
        'branch_id': lambda self, cr, uid, ctx: ctx and ctx.get('branch_id', False) or False,
    }

    def _get_obj_transaksi(self, cr, uid, invoice, context=None):
        header = False
        lines = False
        model = ''
        search = self.pool.get('dealer.sale.order').search(cr, uid, [('name','ilike',invoice.origin)])
        if search:
            model = 'dealer.sale.order'
            header = self.pool.get(model).browse(cr, uid, search)
            lines = header.dealer_sale_order_line
            return header, lines, model
        search = self.pool.get('sale.order').search(cr, uid, [('name','ilike',invoice.origin)])
        if search:
            model = 'sale.order'
            header = self.pool.get(model).browse(cr, uid, search)
            lines = header.order_line
            return header, lines, model
        search = self.pool.get('sale.order').search(cr, uid, [('name','ilike',invoice.origin)])
        if search:
            model = 'dym.work.order'
            header = self.pool.get(model).browse(cr, uid, search)
            lines = header.work_lines
            return header, lines, model
        return False, False, ''

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("Data Error, please try to refresh page or contact your administrator!"))
        res = super(wiz_retur_jual, self).default_get(cr, uid, fields, context=context)
        proses_id = context and context.get('active_id', False) or False
        val = self.pool.get('dym.retur.jual').browse(cr, uid, proses_id, context=context)
        move_obj = self.pool.get('stock.move')
        result1 = []     
        header, lines, model = self._get_obj_transaksi(cr, uid, val.invoice_id, context=context)
        main_invoice_ids = []
        packing_line_obj = self.pool.get('dym.stock.packing.line')
        if header and lines and model:
            # if model == 'dealer.sale.order':
            #     if header.finco_id:
            #         main_invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('origin','ilike',header.name),('partner_id','=',header.finco_id.id),('tipe','=','finco')])
            #     else:
            #         main_invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('origin','ilike',header.name),('partner_id','=',header.partner_id.id),('tipe','=','customer')])                    
            # elif model == 'sale.order':
            #     main_invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('origin','ilike',header.name),('partner_id','=',header.partner_id.id)])
            # elif model == 'dym.work.order':
            #     main_invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('origin','ilike',header.name),('partner_id','=',header.customer_id.id)])
            # if main_invoice_ids:
            #     main_invoice = self.pool.get('account.invoice').browse(cr, uid, main_invoice_ids)[0]
            serial_number_ids = []
            packing_line = []
            if model == 'dealer.sale.order':
                packing_line_ids = packing_line_obj.search(cr, uid, [('packing_id.picking_id.origin','ilike',header.name),('packing_id.state','=','posted')])
                for line in packing_line_obj.browse(cr, uid, packing_line_ids):
                    barang_lot_ids = self.pool.get('dym.retur.barang.jual.line').search(cr, uid, ['|',('retur_id','=',val.id),'&',('retur_id.invoice_id','=',val.invoice_id.id),('retur_id.state','not in',('draft','cancel')),('engine_number','=',line.serial_number_id.id)])
                    if line.serial_number_id.id not in serial_number_ids and not barang_lot_ids and line.serial_number_id.state not in ['intransit','titipan','stock','returned'] and not line.serial_number_id.proses_stnk_id and ((line.product_id.categ_id.isParentName('Unit') and val.retur_type == 'Barang') or val.retur_type in ['Uang','Admin']):
                        serial_number_ids.append(line.serial_number_id.id)
                        packing_line.append(line)
                for quantity in range(int(len(serial_number_ids))):
                    move_obj = self.pool.get('stock.move')
                    move_search = move_obj.search(cr, uid, [('picking_id', '=', packing_line[quantity].packing_id.picking_id.id), ('product_id', '=', packing_line[quantity].product_id.id), ('state', '=', 'done')])
                    result1.append([0,0,{'retur_id': val.id, 'product_qty': packing_line[quantity].quantity, 'product_id': packing_line[quantity].product_id.id, 'jual_line_id': False, 'engine_number':serial_number_ids[quantity], 'move_id':move_search[0]}])
            else :
                for jual_line in val.retur_jual_line:
                    move_obj = self.pool.get('stock.move')
                    move_search = move_obj.search(cr, uid, [('picking_id.origin', 'ilike', header.name), ('product_id', '=', jual_line.product_id.id), ('state', '=', 'done')])
                    received_qty = 0
                    for move in self.pool.get('stock.move').browse(cr, uid, move_search):
                        search_return_history = move_obj.search(cr, uid, [('origin_returned_move_id', '=', move.id), ('state', 'not in', ('draft','cancel'))])
                        return_history_qty = 0
                        for return_history in self.pool.get('stock.move').browse(cr, uid, search_return_history):
                            return_history_qty += return_history.product_uom_qty
                        received_qty += move.product_uom_qty - return_history_qty
                    barang_line_ids = self.pool.get('dym.retur.barang.jual.line').search(cr, uid, [('jual_line_id','=',jual_line.id)])
                    barang_line_brw = self.pool.get('dym.retur.barang.jual.line').browse(cr, uid, barang_line_ids)
                    barang_line_qty = 0
                    for barang_line in barang_line_brw:
                        barang_line_qty += barang_line.product_qty
                    received_qty -= barang_line_qty
                    if received_qty > jual_line.product_qty:
                        received_qty = jual_line.product_qty
                    if received_qty > 0:
                        if move_search:
                            result1.append([0,0,{'retur_id': val.id, 'product_qty': received_qty, 'product_id': jual_line.product_id.id, 'jual_line_id': jual_line.id, 'move_id':move_search[0]}])
        # for jual_line in val.retur_jual_line:
            # if jual_line.product_id.categ_id.isParentName('Unit'):
            #     packing_line_obj = self.pool.get('dym.stock.packing.line')
            #     serial_number_ids = []
            #     packing_line = []
            #     packing_line_ids = packing_line_obj.search(cr, uid, [('packing_id.picking_id.origin','=',val.invoice_id.name),('product_id','=',jual_line.product_id.id),('packing_id.state','=','posted')])
            #     for line in packing_line_obj.browse(cr, uid, packing_line_ids):
            #         barang_lot_ids = self.pool.get('dym.retur.barang.jual.line').search(cr, uid, ['|','&',('retur_id','=',val.id),('jual_line_id','=',jual_line.id),'&',('retur_id.invoice_id','=',val.invoice_id.id),('retur_id.state','not in',('draft','cancel')),('engine_number','=',line.serial_number_id.id)])
            #         if line.serial_number_id.id not in serial_number_ids and not barang_lot_ids and line.serial_number_id.state not in ['intransit','titipan','stock','returned'] and not line.serial_number_id.proses_stnk_id:
            #             serial_number_ids.append(line.serial_number_id.id)
            #             packing_line.append(line)
            #     for quantity in range(int(len(serial_number_ids))):
            #         move_obj = self.pool.get('stock.move')
            #         move_search = move_obj.search(cr, uid, [('picking_id', '=', packing_line[quantity].packing_id.picking_id.id), ('product_id', '=', jual_line.product_id.id), ('state', '=', 'done')])
            #         result1.append([0,0,{'retur_id': val.id, 'product_qty': 1, 'product_id': jual_line.product_id.id, 'jual_line_id': jual_line.id, 'engine_number':serial_number_ids[quantity], 'move_id':move_search[0]}])
            # else :
                # move_obj = self.pool.get('stock.move')
                # move_search = move_obj.search(cr, uid, [('picking_id.origin', '=', val.invoice_id.name), ('product_id', '=', jual_line.product_id.id), ('state', '=', 'done')])
                # received_qty = 0
                # for move in self.pool.get('stock.move').browse(cr, uid, move_search):
                #     search_return_history = move_obj.search(cr, uid, [('origin_returned_move_id', '=', move.id), ('state', 'not in', ('draft','cancel'))])
                #     return_history_qty = 0
                #     for return_history in self.pool.get('stock.move').browse(cr, uid, search_return_history):
                #         return_history_qty += return_history.product_uom_qty
                #     received_qty += move.product_uom_qty - return_history_qty
                # barang_line_ids = self.pool.get('dym.retur.barang.jual.line').search(cr, uid, [('jual_line_id','=',jual_line.id)])
                # barang_line_brw = self.pool.get('dym.retur.barang.jual.line').browse(cr, uid, barang_line_ids)
                # barang_line_qty = 0
                # for barang_line in barang_line_brw:
                #     barang_line_qty += barang_line.product_qty
                # received_qty -= barang_line_qty
                # if received_qty > jual_line.product_qty:
                #     received_qty = jual_line.product_qty
                # if received_qty > 0:
                #     if move_search:
                #         result1.append([0,0,{'retur_id': val.id, 'product_qty': received_qty, 'product_id': jual_line.product_id.id, 'jual_line_id': jual_line.id, 'move_id':move_search[0]}])
        res['line_ids'] = result1
        return res

    def generate_retur_barang(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for data in self.browse(cr, uid, ids, context=context):
            result1 = []
            for line in data.line_ids:
                if line.product_id.categ_id.isParentName('Unit') and not line.engine_number_retur and data.retur_id.retur_type == 'Barang':
                    raise osv.except_osv(('Perhatian !'), ("Untuk tipe retur barang, mohon isi normor engine yang akan pengganti."))
                if line.check_process:
                    result1.append({'retur_id': data.retur_id.id, 'product_qty': line.product_qty, 'product_id': line.product_id.id, 'jual_line_id': line.jual_line_id.id, 'engine_number':line.engine_number.id, 'move_id':line.move_id.id, 'engine_number_retur':line.engine_number_retur.id})
            for res in result1:
                self.pool.get('dym.retur.barang.jual.line').create(cr, uid, res)
        return {}

class stock_move(osv.osv):
    _inherit = 'stock.move'

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(stock_move, self).write(cr, uid, ids, vals, context=context)
        if vals.get('state') in ['done', 'cancel']:
            for move in self.browse(cr, uid, ids, context=context):
                if move.picking_id.origin and (move.picking_id.origin[:3] == 'RJ/' or move.picking_id.origin[:3] == 'RJU'):
                    retur_id = self.pool.get('dym.retur.jual').search(cr, uid, [('name','=',move.picking_id.origin)])
                    if self.test_moves_retur_jual_done(cr, uid, retur_id[0], context=context):
                        workflow.trg_validate(uid, 'dym.retur.jual', retur_id[0], 'picking_done', cr)
                    if self.test_moves_retur_jual_except(cr, uid, move.picking_id, context=context):
                        workflow.trg_validate(uid, 'dym.retur.jual', retur_id[0], 'picking_cancel', cr)
        return res

    def test_moves_retur_jual_done(self, cr, uid, retur_id, context=None):
        retur_brw = self.pool.get('dym.retur.jual').browse(cr, uid, [retur_id])
        obj_picking = self.pool.get('stock.picking')
        pick_ids = obj_picking.search(cr,uid,[('origin','ilike',retur_brw.name)])
        pick_brw = obj_picking.browse(cr, uid, pick_ids)
        for pick in pick_brw:
            if pick.state != 'done' and pick.state != 'cancel' :
                return False
        return True

    def test_moves_retur_jual_except(self, cr, uid, picking, context=None):
        at_least_one_canceled = False
        alldoneorcancel = True
        if picking.state == 'cancel':
            at_least_one_canceled = True
        if picking.state not in ['done', 'cancel']:
            alldoneorcancel = False
        return at_least_one_canceled and alldoneorcancel

class dym_retur_jual(osv.osv):
    _name = "dym.retur.jual"
    _description = "Retur Penjualan"
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_retur_penjualan_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_id',\
            'division',\
            'number',\
            'date',\
            'invoice_retur_number',\
            'invoice_retur_date',\
            'invoice_jual_number',\
            'invoice_jual_date',\
            'customer',\
            'kode',\
            'deskripsi',\
            'warna',\
            'engine_number',\
            'chassis_number',\
            'price_unit',\
            'price_bbn',\
            'discount_total',\
            'discount_konsumen',\
            'discount_dealer',\
            'discount_finco',\
            'discount_md',\
            'discount_ahm',\
            'biaya_retur',\
            'product_qty',\
            'dpp',\
            'ppn',\
            'sales',\
            'jumlah',\
            'nilai_hpp',\
            'type',\
            'keterangan',\
            'ois_number',\
            'payment_number',\
            'payment_date',\
            'payment_allocation',\
            'saldo',\
            'aging',\
        ]
 
    def _report_xls_retur_penjualan_non_unit_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_id',\
            'division',\
            'number',\
            'date',\
            'invoice_retur_number',\
            'invoice_retur_date',\
            'invoice_jual_number',\
            'invoice_jual_date',\
            'customer',\
            'kode',\
            'deskripsi',\
            'price_unit',\
            'discount_total',\
            'biaya_retur',\
            'product_qty',\
            'dpp',\
            'ppn',\
            'sales',\
            'jumlah',\
            'type',\
            'keterangan',\
            'ois_number',\
            'payment_number',\
            'payment_date',\
            'payment_allocation',\
            'saldo',\
            'aging',\
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
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('confirmed', 'Waiting Approval'),
        ('approved','Confirmed'),
        ('except_picking', 'Shipping Exception'),
        ('except_invoice', 'Invoice Exception'),
        ('done','Done'),
        ('cancel','Cancelled')
    ] 

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_retur_jual, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        for field in res['fields']:
            if field == 'division':
                if 'menu' in context and context['menu'] == 'showroom':
                    res['fields'][field]['selection'] = [('Unit','Showroom')]
                if 'menu' in context and context['menu'] == 'workshop':
                    res['fields'][field]['selection'] = [('Sparepart','Workshop')]
        return res
        
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for val in self.browse(cr, uid, ids, context=context):
            res[val.id] = {
                'amount_bbn': 0.0,
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            amount_untaxed = amount_tax = amount_total = amount_bbn = 0.0
            for line in val.retur_jual_line:
                amount_bbn += line.price_bbn
                amount_untaxed += line.price_subtotal
                price = (line.price_unit * line.product_qty) - line.discount_total
                for c in self.pool.get('account.tax').compute_all(cr,uid, line.taxes_id, price,1, line.product_id, val.partner_id)['taxes']:
                    amount_tax += c.get('amount',0.0)
            if val.retur_jual_line:
                biaya_taxes = self.pool.get('account.tax').compute_all(cr,uid, line[0].taxes_id, val.biaya_retur*-1,1, line[0].product_id, val.partner_id)
                amount_untaxed += biaya_taxes['total']
                for a in biaya_taxes['taxes']:
                    amount_tax += a.get('amount',0.0)
            res[val.id]['amount_bbn'] = amount_bbn
            res[val.id]['amount_untaxed'] = amount_untaxed
            res[val.id]['amount_tax'] = amount_tax
            res[val.id]['amount_total'] = amount_untaxed + amount_tax + amount_bbn
        return res
    
    def _get_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('dym.retur.jual.line').browse(cr, uid, ids, context=context):
            result[line.retur_id.id] = True
        return result.keys()

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')         
        user = user_obj.browse(cr,uid,uid)
        return user.get_default_branch()

    def _count_picking(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for retur in self.browse(cr, uid, ids, context=context):
            res[retur.id] = len(retur.retur_jual_line)
        return res

    def _count_return_picking(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        obj_picking = self.pool.get('stock.picking')
        for retur in self.browse(cr, uid, ids, context=context):
            pick_ids = []
            if retur.dso_id:
                pick_ids = obj_picking.search(cr,uid,[('origin','ilike',retur.dso_id.name)])
            elif retur.so_id:
                pick_ids = obj_picking.search(cr,uid,[('origin','ilike',retur.so_id.name)])
            res[retur.id] = len(pick_ids)
        return res

    def _get_oos_state(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        obj_picking = self.pool.get('stock.picking')
        for retur in self.browse(cr, uid, ids, context=context):
            pick_ids = []
            if retur.dso_id:
                pick_ids = obj_picking.search(cr,uid,[('origin','ilike',retur.dso_id.name)])
            elif retur.so_id:
                pick_ids = obj_picking.search(cr,uid,[('origin','ilike',retur.so_id.name)])
            
            pick_states = [picking.state for picking in obj_picking.browse(cr, uid, pick_ids, context=context)]
            if pick_states.count('done'):
                if pick_states.count('done') != len(pick_states):
                    res[retur.id] = 'transferred partial'
                else:
                    res[retur.id] = 'done'
            else:
                res[retur.id] = 'not yet'
        return res

    def _get_ois_state(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        obj_picking = self.pool.get('stock.picking')
        for retur in self.browse(cr, uid, ids, context=context):
            pick_ids = obj_picking.search(cr,uid,[('origin','ilike',retur.name)])
            for picking in obj_picking.browse(cr, uid, pick_ids, context=context):
                res[retur.id] = picking.state
                if not picking.state:
                    res[retur.id] = 'not yet'
        return res

    _columns = {
        'branch_id': fields.many2one('dym.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division', change_default=True, select=True),
        'name': fields.char('Retur Ref.', readonly=True),
        'ket': fields.text('Keterangan'),
        'date': fields.date('Retur Date'),
        'retur_type':fields.selection(RETUR_TYPE, 'Tipe Retur', change_default=True, select=True),
        'state': fields.selection(STATE_SELECTION, 'State', readonly=True),
        'retur_jual_line': fields.one2many('dym.retur.jual.line','retur_id',string="Retur Line"), 
        'partner_id':fields.many2one('res.partner','Customer', 
            help=' Syarat Retur Jual: \
                \n* Sudah kirim unit + KSU. \
                \n* Sudah ada pembayaran JP / Full \
                \n* Belum proses STNK \
                \n* Belum ada pembayaran leasing'),
        'partner_cabang': fields.many2one('dym.cabang.partner',string='Cabang Customer'),
        'invoice_id':fields.many2one('account.invoice','Invoice Number'),
        'dso_id':fields.many2one('dealer.sale.order','Sales Reference', 
            help=' Syarat Retur Jual: \
                \n* Sudah kirim unit + KSU. \
                \n* Sudah ada pembayaran JP / Full \
                \n* Belum proses STNK \
                \n* Belum ada pembayaran leasing'),
        'so_id':fields.many2one('sale.order','Sales Reference',
            help=' Syarat Retur Jual: \
                \n* Sudah kirim barang. \
                \n* Sudah lunas'),
        'biaya_retur': fields.float(string='Biaya Adm. Retur'),
        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tax Base',
            store={
                'dym.retur.jual': (lambda self, cr, uid, ids, c={}: ids, ['retur_jual_line','biaya_retur'], 10),
                'dym.retur.jual.line': (_get_line, ['product_qty'], 10),
            },
            multi='sums', help="The amount without tax and discount.", track_visibility='always'),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'dym.retur.jual': (lambda self, cr, uid, ids, c={}: ids, ['retur_jual_line','biaya_retur'], 10),
                'dym.retur.jual.line': (_get_line, ['product_qty'], 10),
            },
            multi='sums', help="Grand Total."),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tax Amount',
            store={
                'dym.retur.jual': (lambda self, cr, uid, ids, c={}: ids, ['retur_jual_line','biaya_retur'], 10),
                'dym.retur.jual.line': (_get_line, ['product_qty'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_bbn': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Non Tax / BBN',
            store={
                'dym.retur.jual': (lambda self, cr, uid, ids, c={}: ids, ['retur_jual_line','biaya_retur'], 10),
                'dym.retur.jual.line': (_get_line, ['price_bbn'], 10),
            },
            multi='sums', help="The total amount of BBN."),
        'invoiced': fields.boolean('Invoiced', readonly=True, copy=False),
        'invoice_method': fields.selection([('order','Based on generated draft invoice')], 'Invoicing Control', required=True,
            readonly=True),
        'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
        'confirm_date':fields.datetime('Confirmed on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),  
        'payment_term':fields.many2one('account.payment.term',string="Payment Term"),
        'picking_count': fields.function(_count_picking, type='integer', string='Picking'),
        'return_picking_count': fields.function(_count_return_picking, type='integer', string='Return Picking'),
        'lot_state': fields.char(string='Lot State'),
        'oos_state': fields.function(_get_oos_state, type='char', string='OOS State'),
        'ois_state': fields.function(_get_ois_state, type='char', string='OIS State'),
        'is_pic': fields.boolean(string='Is PIC'),
        'help_type': fields.selection([('showroom','Showroom'),('workshop','Workshop')], string='Help type'),
    }
    _defaults = {
        'date': fields.date.context_today,
        'state':'draft',
        'invoice_method':'order',
        'invoiced': 0,
        'branch_id': _get_default_branch,
        'lot_state': 'not_returned',
        'help_type': 'showroom',
     }
    
    def create(self, cr, uid, vals, context=None):
        if not vals['retur_jual_line']:
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail retur jual. Data tidak bisa di save."))
        retur_jual = []
        proses_pool = self.pool.get('dym.retur.jual.line')

        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'RJU', division=vals['division'])
        vals['date'] = time.strftime('%Y-%m-%d'),
        proses_id = super(dym_retur_jual, self).create(cr, uid, vals, context=context) 
        return proses_id
    
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Retur penjualan sudah di proses ! tidak bisa didelete !"))
        return super(dym_retur_jual, self).unlink(cr, uid, ids, context=context)
    
    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def wkf_confirm_retur(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot')
        move_pool = self.pool.get('stock.move')
        picking_pool = self.pool.get('stock.picking')
        packing_pool = self.pool.get('dym.stock.packing')
        if val.dso_id:
            val.dso_id.write({'is_returned':True,'return_id':val.id})
            picking_ids = picking_pool.search(cr, uid, [('origin','=',val.dso_id.name)], order='create_date')
            for picking in picking_pool.browse(cr, uid, picking_ids, context=context):
                picking.write({'is_returned':True,'return_id':val.id})
                packing_ids = packing_pool.search(cr, uid, [('picking_id','=',picking.id)], order='create_date')
                for packing in packing_pool.browse(cr, uid, packing_ids, context=context):
                    packing.write({'is_returned':True,'return_id':val.id})
                    returned_engine_numbers = [l.lot_id.id for l in val.retur_jual_line if l.lot_id]
                    packing_engine_numbers = [l.serial_number_id.id for l in packing.packing_line2 if l.serial_number_id]
                    partial_return = True
                    if len(returned_engine_numbers)==len(packing_engine_numbers):
                        partial_return = False
                    if partial_return:
                        for line in packing.packing_line2:
                            if line.serial_number_id.id in returned_engine_numbers:
                                line.write({'is_returned':True,'return_id':val.id})
                        for return_line in val.retur_jual_line:
                            for packing_line in packing.packing_line2:
                                for ksu_line in return_line.product_id.extras_line:
                                    if packing_line.product_id.id == ksu_line.product_id.id:
                                        packing_line.write({'quantity':packing_line.quantity - 1})

        self.write(cr, uid, ids, {'state': 'approved','confirm_uid':uid,'confirm_date':datetime.now()})
        return True
   
    def wkf_action_cancel(self, cr, uid, ids, context=None):
        print "===wkf_action_cancel==="
        val = self.browse(cr,uid,ids)  
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        return True

    def wkf_approve_retur(self, cr, uid, ids, context=None):
        print "===wkf_approve_retur==="
        self.write(cr, uid, ids, {'state': 'approved'})
        return True
    
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        collect = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot')
        line_pool = self.pool.get('dym.retur.jual.line')
        return super(dym_retur_jual, self).write(cr, uid, ids, vals, context=context)
    
    def wkf_set_to_draft(self,cr,uid,ids):
        print "===wkf_set_to_draft==="
        return self.write({'state':'draft'})       
    
    def refund_cleanup_lines(self, cr, uid, ids, lines, retur_jual_line=False, journal=False, context=None):
        print "===refund_cleanup_lines==="
        result = []
        if retur_jual_line:
            per_product = {}
            per_potongan = {}
            bbn = False
            for retur_line in retur_jual_line:
                line = retur_line.invoice_line_id
                values = {}
                for name, field in line._fields.iteritems():
                    if name in MAGIC_COLUMNS:
                        continue
                    elif field.type == 'many2one':
                        values[name] = line[name].id
                    elif field.type not in ['many2many', 'one2many']:
                        values[name] = line[name]
                    elif name == 'invoice_line_tax_id':
                        values[name] = [(6, 0, line[name].ids)]
                values['name'] = retur_line.name
                values['consolidated_qty'] = 0
                values['quantity'] = retur_line.product_qty
                values['quantity_show'] = retur_line.product_qty
                values['discount'] = 0
                values['discount_amount'] = 0
                values['discount_cash'] = 0
                values['discount_program'] = 0
                values['discount_lain'] = 0
                values['price_unit'] = retur_line.price_unit
                values['price_unit_show'] = retur_line.price_unit
                values['price_subtotal'] = retur_line.price_subtotal
                if retur_line.product_id:
                    accounts = self.pool.get('product.template').get_product_accounts(cr, uid, retur_line.product_id.product_tmpl_id.id, context)
                    acc_valuation = accounts.get('property_stock_valuation_account_id', False)
                    if not acc_valuation:
                        raise osv.except_osv(_('Attention!'),
                                _('Mohon lengkapi data stock valuation account untuk produk %s') % (retur_line.product_id.name))   
                    values['account_id'] = acc_valuation
                result.append((0, 0, values))
                per_potongan['discount_amount'] = per_potongan.get('discount_amount',0)+retur_line.discount_amount
                per_potongan['discount_lain'] = per_potongan.get('discount_lain',0)+retur_line.discount_lain
                per_potongan['discount_cash'] = per_potongan.get('discount_cash',0)+retur_line.discount_cash
                per_potongan['discount_dealer'] = per_potongan.get('discount_dealer',0)+retur_line.discount_dealer
                per_potongan['discount_external'] = per_potongan.get('discount_external',0)+retur_line.discount_external
                per_potongan['tax_id'] = [(6, 0, retur_line.taxes_id.ids)]
            retur = retur_jual_line[0].retur_id
            config = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',retur.branch_id.id)])
            obj_branch_config = self.pool.get('dym.branch.config').browse(cr,uid,config)
            if retur.division=='Unit':
                analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, retur.branch_id, 'Unit', False, 4, 'Sales')
            elif retur.division=='Sparepart':
                analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, retur.branch_id, '', retur_jual_line[0].product_id.categ_id, 4, 'Sparepart_Accesories')
            if retur.biaya_retur != 0:
                if not obj_branch_config.retur_jual_biaya_tambahan_retur_account_id:
                    raise osv.except_osv(('Perhatian !'), ("Konfigurasi account retur biaya di branch config belum ada!"))
                account_id = obj_branch_config.retur_jual_biaya_tambahan_retur_account_id.id
                result.append([0,False,{
                    'name': 'Biaya / Diskon Tambahan',
                    'quantity':1,
                    'origin':retur.name,
                    'price_unit':retur.biaya_retur*-1,
                    'invoice_line_tax_id':per_potongan['tax_id'],
                    'account_id': account_id,
                    'analytic_1': analytic_1,
                    'analytic_2': analytic_2,
                    'analytic_3': analytic_3,
                    'account_analytic_id':analytic_4,  
                }])
            for key, value in per_potongan.items():
                if value > 0:
                    price_unit = -1*value
                    tax = per_potongan['tax_id']
                    if key=='discount_amount':
                        account_id = False
                        if retur_jual_line[0].dso_line_id:
                            if not obj_branch_config.dealer_so_account_potongan_langsung_id:
                                raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan langsung di branch config belum ada!"))
                            account_id = obj_branch_config.dealer_so_account_potongan_langsung_id.id
                        else:
                            if not obj_branch_config.so_account_potongan_langsung_id:
                                raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan langsung di branch config belum ada!"))
                            account_id = obj_branch_config.so_account_potongan_langsung_id.id
                        result.append([0,False,{
                            'name': 'Diskon Reguler',
                            'quantity':1,
                            'origin':retur.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': account_id,
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])
                    
                    if key=='discount_dealer':
                        # invoice_pelunasan['discount_program'] = value
                        account_id = False
                        if retur_jual_line[0].dso_line_id:
                            if not obj_branch_config.dealer_so_account_potongan_subsidi_id:
                                raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan subsidi di branch config belum ada!"))
                            account_id = obj_branch_config.dealer_so_account_potongan_subsidi_id.id
                        else:
                            if not obj_branch_config.dym_so_account_discount_program_id:
                                raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan subsidi di branch config belum ada!"))
                            account_id = obj_branch_config.dym_so_account_discount_program_id.id
                        result.append([0,False,{
                            'name': 'Diskon Dealer',
                            'quantity':1,
                            'origin':retur.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': account_id,
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])
                    if key=='discount_external':
                        # invoice_pelunasan['discount_program'] = value
                        account_id = False
                        if retur_jual_line[0].dso_line_id:
                            if not obj_branch_config.dealer_so_account_potongan_subsidi_external_id:
                                raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan subsidi external di branch config belum ada!"))
                            account_id = obj_branch_config.dealer_so_account_potongan_subsidi_external_id.id
                        else:
                            if not obj_branch_config.dym_so_account_discount_program_external_id:
                                raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan subsidi external di branch config belum ada!"))
                            account_id = obj_branch_config.dym_so_account_discount_program_external_id.id
                        result.append([0,False,{
                            'name': 'Diskon External',
                            'quantity':1,
                            'origin':retur.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': account_id,
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])
                    if key=='discount_cash':
                        # invoice_pelunasan['discount_program'] = value
                        account_id = False
                        if not obj_branch_config.dym_so_account_discount_cash_id:
                            raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan cash di branch config belum ada!"))
                        account_id = obj_branch_config.dym_so_account_discount_cash_id.id
                        result.append([0,False,{
                            'name': 'Diskon Cash',
                            'quantity':1,
                            'origin':retur.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': account_id,
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])
                    if key=='discount_lain':
                        # invoice_pelunasan['discount_program'] = value
                        account_id = False
                        if not obj_branch_config.dym_so_account_discount_lainnya_id:
                            raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan lain di branch config belum ada!"))
                        account_id = obj_branch_config.dym_so_account_discount_lainnya_id.id
                        result.append([0,False,{
                            'name': 'Diskon Lainnya',
                            'quantity':1,
                            'origin':retur.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': account_id,
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])
        else:
            for line in lines:
                values = {}
                for name, field in line._fields.iteritems():
                    if name in MAGIC_COLUMNS:
                        continue
                    elif field.type == 'many2one':
                        values[name] = line[name].id
                    elif field.type not in ['many2many', 'one2many']:
                        values[name] = line[name]
                    elif name == 'invoice_line_tax_id':
                        values[name] = [(6, 0, line[name].ids)]
                result.append((0, 0, values))
        return result

    def prepare_refund(self, cr, uid, ids, invoice, retur_jual_line, payment_term, date=None, period_id=None, description=None, journal_id=None, origin=None, context=None):
        print "===prepare_refund==="
        values = {}
        for field in ['name', 'reference', 'comment', 'date_due', 'partner_id', 'company_id',
                'account_id', 'currency_id', 'payment_term', 'user_id', 'fiscal_position',
                'branch_id', 'division','asset']:
            if invoice._fields[field].type == 'many2one':
                values[field] = invoice[field].id
            else:
                values[field] = invoice[field] or False
        if journal_id:
            journal = self.pool.get('account.journal').browse(cr, uid, [journal_id])
        elif invoice['type'] == 'out_invoice':
            journal_src = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale_refund')], limit=1)
            journal = self.pool.get('account.journal').browse(cr, uid, journal_src)
        else:
            journal_src = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'purchase_refund')], limit=1)
            journal = self.pool.get('account.journal').browse(cr, uid, journal_src)
        values['journal_id'] = journal.id
        values['invoice_line'] = self.refund_cleanup_lines(cr, uid, ids, invoice.invoice_line, retur_jual_line, journal)
        tax_lines = filter(lambda l: l.manual, invoice.tax_line)
        values['tax_line'] = self.refund_cleanup_lines(cr, uid, ids, tax_lines)
        if retur_jual_line and retur_jual_line[0].retur_id.amount_bbn > 0:
            config = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',retur_jual_line[0].retur_id.branch_id.id)])
            config_browse = self.pool.get('dym.branch.config').browse(cr,uid,config)
            if not config_browse.dealer_so_account_bbn_jual_id:
                raise osv.except_osv(_('Attention!'),
                    _('Account BBN Jual di branch config dealer sale order belum di set!')) 
            values['amount_bbn'] = retur_jual_line[0].retur_id.amount_bbn
            values['account_bbn'] = config_browse.dealer_so_account_bbn_jual_id.id
        values['type'] = TYPE2REFUND[invoice['type']]
        values['date_invoice'] = date
        values['state'] = 'draft'
        values['number'] = False
        values['origin'] = origin
        values['payment_term'] = payment_term
        values['qq_id'] = invoice.qq_id.id
        values['account_id'] = journal.default_credit_account_id.id or journal.default_debit_account_id.id
        values['analytic_1'] = invoice.analytic_1.id
        values['analytic_2'] = invoice.analytic_2.id
        values['analytic_3'] = invoice.analytic_3.id
        values['analytic_4'] = invoice.analytic_4.id
        if period_id:
            values['period_id'] = period_id
        if description:
            values['name'] = description
        return values

    def reverse_account_move(self, cr, uid, ids, move, context=None):
        print "===reverse_account_move==="
        period_ids = self.pool.get('account.period').find()
        journal_copy = move.copy({
            'line_id':[],
            'name': move.name + ' - Retur',
            'ref':move.name + ' - Retur',
            'date': datetime.now(),
            'period_id':period_ids.id,
            'reverse_from_id':move.id,
            })
        for move_line in move.line_id:
            if move_line.debit > 0:
                move_line.copy({
                    'name': move_line.name + ' - Retur',
                    'ref': move_line.name + ' - Retur',
                    'credit':move_line.debit,
                    'debit':0,
                    'period_id': period_ids.id,
                    'date': datetime.now(),
                    'move_id':journal_copy,
                })
            if move_line.credit > 0:
                move_line.copy({
                    'name': move_line.name + ' - Retur',
                    'ref': move_line.name + ' - Retur',
                    'debit':move_line.credit,
                    'credit':0,
                    'period_id': period_ids.id,
                    'date': datetime.now(),
                    'move_id':journal_copy,
                })
        journal_copy.post()
        return journal_copy

    def action_invoice_create(self, cr, uid, ids, context=None):
        print "===action_invoice_create==="
        val = self.browse(cr, uid, ids, context={})[0]
        obj_inv = self.pool.get('account.invoice')
        invoice_line = []
        config = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',val.branch_id.id)])
        if config :
            config_browse = self.pool.get('dym.branch.config').browse(cr,uid,config)
            if val.division == 'Unit':
                retur_account_id = config_browse.retur_jual_dso_journal_id.default_debit_account_id or config_browse.retur_jual_dso_journal_id.default_credit_account_id
                journal_retur = config_browse.retur_jual_dso_journal_id
            elif val.division == 'Sparepart':
                retur_account_id = config_browse.retur_jual_so_journal_id.default_debit_account_id or config_browse.retur_jual_so_journal_id.default_credit_account_id
                journal_retur = config_browse.retur_jual_so_journal_id
            if not journal_retur.id :
                raise osv.except_osv(_('Attention!'),
                    _('Jurnal Retur Penjualan belum diisi, harap isi terlebih dahulu didalam branch config')) 
            if not retur_account_id.id:
                raise osv.except_osv(_('Attention!'),
                    _('Mohon lengkapi data default credit account di journal %s') % (journal_retur.name))   
                             
            #if retur_account_id.type != 'payable':
                #raise osv.except_osv(_('Attention!'),
                    #_('Data internal type untuk account retur %s - %s harus Payable') % (retur_account_id.code, retur_account_id.name)) 

        elif not config :
            raise osv.except_osv(_('Error!'),
                _('Please define Journal in Setup Division for this branch: "%s".') % \
                (val.branch_id.name))
                              
        if val.amount_total < 1: 
            raise osv.except_osv(_('Attention!'),
                _('Mohon periksa kembali detail retur.')) 

        values = self.prepare_refund(cr, uid, ids, val.invoice_id, val.retur_jual_line, val.payment_term.id, date=datetime.today(), period_id=False, description=False, journal_id=journal_retur.id, origin=val.name, context=context)
        if val.retur_type == 'Admin':
            values['sale_return_type'] = 'admin'
        elif val.retur_type == 'Uang':
            values['sale_return_type'] = 'uang'
        elif val.retur_type == 'Barang':
            values['sale_return_type'] = 'barang'
        else:
            values['sale_return_type'] = 'none'

        inv_refund_id = obj_inv.create(cr, uid, values)    
        obj_inv.button_compute(cr, uid, inv_refund_id)
        return inv_refund_id 

    def _get_default_location_delivery_sales(self,cr,uid,ids,context=None):
        print "===_get_default_location_delivery_sales==="
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
                         raise osv.except_osv(('Perhatian !'), ("Location destination Belum di Setting di picking type"))
                    if not pick_type.default_location_src_id.id :
                         raise osv.except_osv(('Perhatian !'), ("Location source Belum di Setting di picking type"))
                    default_location_id.update({
                        'picking_type_id':pick_type.id,
                        'source':pick_type.default_location_src_id.id,
                        'destination': pick_type.default_location_dest_id.id,
                    })
            else:
               raise osv.except_osv(('Error !'), ('Tidak ditemukan default lokasi barang masuk di konfigurasi cabang \'%s\'!') % (val.branch_id.name,)) 
        return default_location_id

    def _prepare_order_line_move(self, cr, uid, ids, retur, line, picking_id, location, context=None):
        print "===_prepare_order_line_move==="
        if line.product_uom:
            product_uom = line.product_uom
        else:
            product_uom = line.product_id.uom_id
        price_unit = line.price_unit
        if product_uom.id != line.product_id.uom_id.id:
            price_unit *= product_uom.factor / line.product_id.uom_id.factor
        res = []
        uom_obj = self.pool.get('product.uom')
        obj_picking_type = self.pool.get('stock.picking.type')
        pick_type = obj_picking_type.browse(cr,uid,location['picking_type_id'])
        default_location_search = self.pool.get('dym.product.location').search(cr, uid, [
            ('branch_id','=',retur.branch_id.id),
            ('product_id','=',line.product_id.id)
        ], order='id desc', limit=1)
        locatian_search_id = location['source']
        if default_location_search:
            default_location_brw = self.pool.get('dym.product.location').browse(cr, uid, default_location_search)
            locatian_search_id = default_location_brw.location_id.id        

        move_template = {
            'branch_id': retur.branch_id.id,
            'division': retur.division,
            'name': line.retur_product_id.name_get().pop()[1] if line.retur_product_id else line.product_id.name_get().pop()[1] or '',
            'product_id': line.retur_product_id.id if line.retur_product_id else line.product_id.id,
            'product_uom': line.retur_product_id.uom_id.id if line.retur_product_id else line.product_id.uom_id.id,
            'product_uom_qty': line.product_qty,
            'location_id': line.retur_location_id.id if line.retur_location_id else locatian_search_id,
            'location_dest_id': location['destination'], ##check
            'picking_id': picking_id,
            'price_unit': price_unit,
            'invoice_state': 'none',
            'restrict_lot_id': line.retur_lot_id.id,
            'retur_jual_line_id': line.id,
        }
        res.append(move_template)
        return res

    def _create_returns(self, cr, uid, ids, context=None):
        print "===_create_returns==="
        retur_brw = self.browse(cr, uid, ids)[0]
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        uom_obj = self.pool.get('product.uom')
        data_obj = self.pool.get('stock.return.picking.line')
        picking_type_obj = self.pool.get('stock.picking.type')
        picking_type_id = picking_type_obj.search(cr,uid,[
            ('branch_id','=',retur_brw.branch_id.id),
            ('code','=','outgoing')
        ])
        picking_type = False
        if picking_type_id:
            picking_type = picking_type_obj.browse(cr,uid,picking_type_id[0])
        if not picking_type or not picking_type.return_picking_type_id:
            raise osv.except_osv(_('Warning !'), _("Picking Type untuk branch %s belum lengkap")%(retur_brw.branch_id.name))

        # pick_type_id = pick.picking_type_id.return_picking_type_id and pick.picking_type_id.return_picking_type_id.id or pick.picking_type_id.id
        new_picking = pick_obj.create(cr, uid, {
            'name': '/',
            'picking_type_id': picking_type.return_picking_type_id.id ,
            'partner_id': retur_brw.partner_id.id,
            'date': datetime.now(),
            # 'start_date': order.start_date, ##check
            # 'end_date': order.end_date,  ##check
            'move_type': 'direct',
            'invoice_state': 'none',
            'priority': '0',
            'origin': retur_brw.name,
            'branch_id': retur_brw.branch_id.id,
            'division': retur_brw.division,
            # 'transaction_id': retur_brw.id,
            'model_id': self.pool.get('ir.model').search(cr,uid,[('model','=',retur_brw.__class__.__name__)])[0],

        }, context=context)

        if retur_brw.retur_type == 'Barang':
            picking_vals = {
                'name': '/',
                'picking_type_id': picking_type.id,
                'partner_id': retur_brw.partner_id.id,
                'date': datetime.now(),
                # 'start_date': order.start_date, ##check
                # 'end_date': order.end_date,  ##check
                'move_type': 'direct',
                'invoice_state': 'none',
                'priority': '0',
                'origin': retur_brw.name,
                'branch_id': retur_brw.branch_id.id,
                'division': retur_brw.division,
                # 'transaction_id': retur_brw.id,
                'model_id': self.pool.get('ir.model').search(cr,uid,[('model','=',retur_brw.__class__.__name__)])[0],
                'retur': True,
            }
            picking_id = self.pool.get('stock.picking').create(cr, uid, picking_vals, context=context)
            todo_moves = []

        trans = False
        if retur_brw.division == 'Unit':
            trans = retur_brw.dso_id
        if retur_brw.division == 'Sparepart':
            trans = retur_brw.so_id
        location = self._get_default_location_delivery_sales(cr,uid,ids)
        for line in retur_brw.retur_jual_line:
            domain = []
            if retur_brw.division == 'Unit':
                domain = [('restrict_lot_id','=',line.lot_id.id)]
            move_search = move_obj.search(cr, uid, [('picking_id.origin', 'ilike', trans.name), ('product_id', '=', line.product_id.id),('state', '=', 'done')] + domain, limit=1)
            move = move_obj.browse(cr, uid, move_search)
            new_qty = line.product_qty
            default_location_search = self.pool.get('dym.product.location').search(cr, uid, [
                ('branch_id','=',retur_brw.branch_id.id),
                ('product_id','=',line.product_id.id)
            ], order='id desc', limit=1)
            locatian_search_id = location['source']
            if default_location_search:
                default_location_brw = self.pool.get('dym.product.location').browse(cr, uid, default_location_search)
                locatian_search_id = default_location_brw.location_id.id
            price = 0
            account_move_line_ids = self.pool.get('account.move.line').search(cr, uid, [
                ('move_id','=',line.invoice_line_id.invoice_id.move_id.id),
                ('product_cost_id','=',line.product_id.id)
            ], order='id desc', limit=1)
            if account_move_line_ids:
                account_move_line = self.pool.get('account.move.line').browse(cr, uid, account_move_line_ids)
                price = account_move_line.product_cost_price
            else:
                accounts = self.pool.get('product.template').get_product_accounts(cr, uid, line.product_id.product_tmpl_id.id, context)
                acc_valuation = accounts.get('property_stock_valuation_account_id', False)
                if not acc_valuation:
                    raise osv.except_osv(_('Attention!'),
                        _('Mohon lengkapi data stock valuation account untuk produk %s') % (line.product_id.name))   
                account_move_line_ids = self.pool.get('account.move.line').search(cr, uid, [
                    ('move_id','=',line.invoice_line_id.invoice_id.move_id.id),
                    ('product_id','=',line.product_id.id),
                    ('account_id','=',acc_valuation)
                ], order='id desc', limit=1)
                if account_move_line_ids:
                    account_move_line = self.pool.get('account.move.line').browse(cr, uid, account_move_line_ids)
                    price = account_move_line.debit or account_move_line.credit
            if new_qty:
                move_retur_id = move_obj.create(cr, uid, {
                    'branch_id': retur_brw.branch_id.id,
                    'division': retur_brw.division,
                    'product_id': line.product_id.id,
                    'name': line.product_id.name_get().pop()[1] or '',
                    'product_uom_qty': new_qty,
                    'picking_id': new_picking,
                    'location_id': picking_type.default_location_dest_id.id,
                    'location_dest_id': locatian_search_id,
                    'invoice_state': 'none',
                    'product_uom': line.product_id.uom_id.id,
                    'restrict_lot_id': line.lot_id.id,
                    'origin_returned_move_id': move.id,
                    'price_unit': price,
                    'retur_jual_line_id': line.id,
                })
                assign_move = []
                moves_ksu_barang_bonus = []
                if line.dso_line_id and retur_brw.retur_type in ['Uang','Admin']:
                    moves_ksu_barang_bonus = move_obj.search(cr, uid, [('dealer_sale_order_line_id','=',line.dso_line_id.id),('product_id','!=',line.dso_line_id.product_id.id)])
                if line.so_line_id and retur_brw.retur_type in ['Uang','Admin']:
                    moves_ksu_barang_bonus = move_obj.search(cr, uid, [('sale_order_line_id','=',line.so_line_id.id),('product_id','!=',line.so_line_id.product_id.id)])
                for moves in move_obj.browse(cr, uid, moves_ksu_barang_bonus):
                    move_retur_id = move_obj.create(cr, uid, {
                        'branch_id': retur_brw.branch_id.id,
                        'division': retur_brw.division,
                        'product_id': moves.product_id.id,
                        'name': moves.product_id.name_get().pop()[1] or '',
                        'product_uom_qty': moves.product_uom_qty,
                        'picking_id': new_picking,
                        'location_id': moves.location_dest_id.id,
                        'location_dest_id': moves.location_id.id,
                        'invoice_state': 'none',
                        'product_uom': moves.product_uom.id,
                        'restrict_lot_id': False,
                        'origin_returned_move_id': moves.id,
                        'price_unit': moves.price_unit,
                        'retur_jual_line_id': line.id,
                    })
                    assign_move.append(move_retur_id)
                assign_move = move_obj.action_confirm(cr, uid, assign_move)
                move_obj.action_assign(cr, uid, assign_move)
            if retur_brw.retur_type == 'Barang':
                if not line.product_id:
                    continue
                if line.product_id.type in ('product', 'consu'):
                    for vals in self._prepare_order_line_move(cr, uid, ids, retur_brw, line, picking_id, location, context=context):
                        move_create = move_obj.create(cr, uid, vals, context=context)
                        if line.retur_lot_id.id and retur_brw.retur_type == 'Barang':
                            id_quant = self.pool.get('stock.quant').search(cr, SUPERUSER_ID, [('lot_id','=',line.retur_lot_id.id),('product_id','=',line.retur_product_id.id),('location_id','=',line.retur_location_id.id),('qty','>',0)])
                            self.pool.get('stock.quant').write(cr, SUPERUSER_ID, id_quant, {'reservation_id':move_create})
                        todo_moves.append(move_create)                      
                        # dso_line_search = self.pool.get('dealer.sale.order.line').search(cr, uid, [('dealer_sale_order_line_id.name','ilike',retur_brw.invoice_id.origin),('lot_id','=',data_get.engine_number.id)])
                        # line = self.pool.get('dealer.sale.order.line').browse(cr, uid, dso_line_search)
                        # if retur_brw.division == 'Unit' and move.dealer_sale_order_line_id:
                        #     move.dealer_sale_order_line_id.write({'lot_id':line.lot_id.id})

        pick_obj.action_confirm(cr, uid, [new_picking], context=context)
        pick_obj.action_assign(cr, uid, [new_picking], context=context)

        if retur_brw.retur_type == 'Barang':
            todo_moves = move_obj.action_confirm(cr, uid, todo_moves)
            move_obj.force_assign(cr, uid, todo_moves)
            # for assign_move_retur in stock_move.browse(cr, uid, todo_moves):
            #     if assign_move_retur.state not in ('draft', 'cancel', 'done'):
            #         if assign_move_retur.product_id.categ_id.isParentName('Unit'):
            #             self.pool.get('stock.move').action_assign(cr, uid, todo_moves, context=context)       
        return True

    def action_picking_create(self, cr, uid, ids, context=None):
        print "===action_picking_create _create_returns==="
        for retur in self.browse(cr, uid, ids):
            if retur.return_picking_count:
                new_picking_id = self._create_returns(cr, uid, ids)
                print "~~~~~~~~~~new_picking_id~~~~~~~~~~~",new_picking_id
        return True

    def wkf_retur_done(self, cr, uid, ids, context=None):
        print "===wkf_retur_done==="
        self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def picking_done(self, cr, uid, ids, context=None):
        print "===picking_done==="
        # move_obj = self.pool.get('stock.move')
        # for retur in self.browse(cr, uid, ids):
        #     if not retur.retur_barang_line:
        #         for jual_line in retur.retur_jual_line:
        #             obj_retur_barang_ids = self.pool.get('dym.retur.barang.jual.line').search(cr, uid, [('retur_id','=',retur.id),('jual_line_id','=',jual_line.id)])
        #             qty_barang_line = 0
        #             if obj_retur_barang_ids:
        #                 retur_barang_line_browse = self.pool.get('dym.retur.barang.jual.line').browse(cr, uid, obj_retur_barang_ids)
        #                 for barang_line in retur_barang_line_browse:
        #                     qty_barang_line += barang_line.product_qty
        #             move_search = move_obj.search(cr, uid, [('picking_id.origin', '=', retur.invoice_id.origin), ('product_id', '=', jual_line.product_id.id), ('state', 'not in', ('done','cancel'))])
        #             move_brw = move_obj.browse(cr, uid, move_search)
        #             cancel_move_qty = jual_line.product_qty - qty_barang_line
        #             for move in move_brw:
        #                 if cancel_move_qty > 0:
        #                     minus_cancel = 0
        #                     if move.product_uom_qty > cancel_move_qty:
        #                         new_move = move_obj.split(cr, uid, move, cancel_move_qty)
        #                         move_obj.action_cancel(cr, uid, [new_move])
        #                         minus_cancel = cancel_move_qty
        #                     else:
        #                         move_obj.action_cancel(cr, uid, [move.id])
        #                         if move.dealer_sale_order_line_id and move.restrict_lot_id:
        #                             if move.restrict_lot_id:
        #                                 clean_lot_id = move.restrict_lot_id
        #                             else:
        #                                 clean_lot_id = move.dealer_sale_order_line_id.lot_id
        #                             clean_lot_id.write({
        #                                             'state':'stock',
        #                                             'sale_order_reserved':False,
        #                                             'customer_reserved':False,
        #                                             'customer_reserved':False,
        #                                             'dealer_sale_order_id': False,
        #                                             'invoice_date': False,
        #                                             'customer_id': False,
        #                                             'customer_stnk': False,
        #                                             'dp': 0,
        #                                             'tenor': 0,
        #                                             'cicilan': 0,
        #                                             'jenis_penjualan':'',
        #                                             'finco_id':False,
        #                                             'biro_jasa_id': False,
        #                                             'invoice_bbn': False,
        #                                             'total_jasa':0,
        #                                             'cddb_id':False,
        #                                             'move_lines_invoice_bbn_id':False,
        #                                             'pengurusan_stnk_bpkb_id':False,
        #                                             'state_stnk':False,
        #                                             'tgl_pengurusan_stnk_bpkb' : False,
        #                                             'inv_pengurusan_stnk_bpkb_id': False,
        #                                             'invoice_bbn':False,
        #                                             'total_jasa':0,
        #                                             'pengurusan_stnk_bpkb_id':False,
        #                                             'tgl_faktur':False,
        #                                             'permohonan_faktur_id':False,
        #                                             'tgl_terima':False,
        #                                             'penerimaan_faktur_id':False,
        #                                             'faktur_stnk':False,
        #                                             'tgl_cetak_faktur':False,
        #                                             'tgl_penyerahan_faktur':False,
        #                                             'penyerahan_faktur_id':False,
        #                                             'lot_status_cddb':'not',
        #                                             'proses_biro_jasa_id': False,
        #                                             'tgl_proses_birojasa':False,
        #                                             'no_notice_copy':False,
        #                                             'tgl_notice_copy':False,
        #                                             'proses_stnk_id':False,
        #                                             'tgl_proses_stnk':False,
        #                                             })
        #                         minus_cancel = move.product_uom_qty
        #                     cancel_move_qty  -= minus_cancel
        self.write(cr, uid, ids, {'state':'approved'}, context=context)
        return True

    def invoice_done(self, cr, uid, ids, context=None):
        print "===invoice_done==="
        self.write(cr, uid, ids, {'state': 'approved','invoiced':True}, context=context)
        return True

    def view_lot_number(self,cr,uid,ids,context=None):
        print "===view_lot_number==="
        result = {}
        val = self.browse(cr, uid, ids)
        lot_ids = []
        for line in val.retur_jual_line:
            if line.lot_state=='ok':
                lot_ids.append(line.lot_id.id)

                line.lot_id.write({
                    'state':'stock',
                    'sale_order_reserved':False,
                    'customer_reserved':False,
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
                })
                # val.lot_state = 'stock'

        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'dym_retur_jual', 'action_report_dealer_sale_order_wizard')
        view_id = result and result[1] or False
        result = act_obj.read(cr, uid, [view_id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'dym_retur_jual', 'view_back_to_ready_for_sale_wizard')
        result['views'] = [(res and res[1] or False, 'form')]
        return result
    
    def view_invoice(self,cr,uid,ids,context=None):
        print "===view_invoice==="
        val = self.browse(cr, uid, ids)
        if val.retur_type=='Admin':
            if val.oos_state=='done':
                if val.ois_state != 'done':
                    raise osv.except_osv(_('Warning!'), _("Invoice tidak boleh dilihat sebelum status OIS Retur = Transfered via Klik Delivery Order."))
            else:
                if val.lot_state != 'stock':
                    raise osv.except_osv(_('Warning!'), _("Invoice tidak boleh dilihat sebelum status produk = Stok (Ready for Sale) via klik Back to RFS"))

        if val.retur_type=='Uang':
            obj_picking = self.pool.get('stock.picking')
            pick_ids = obj_picking.search(cr,uid,[('origin','ilike',val.name)])
            for picking in obj_picking.browse(cr, uid, pick_ids, context=context):
                if picking.state != 'done':
                    raise osv.except_osv(_('Warning!'), _("Invoice tidak boleh dilihat sebelum status Delivery Order adalah Transfered."))

        lot_ids = []
        for line in val.retur_jual_line:
            if line.lot_state=='ok':
                lot_ids.append(line.lot_id.id)

        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree3')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        result['views'] = [(res and res[1] or False, 'form')]
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        obj = obj_inv.search(cr,uid,[('origin','ilike',val.name),
            ('type','=','out_refund')
        ])
        result['res_id'] = obj[0] 
        return result

    def view_picking(self,cr,uid,ids,context=None):
        print "===view_picking==="
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)

        val = self.browse(cr, uid, ids)
        obj_picking = self.pool.get('stock.picking')
        pick_ids = obj_picking.search(cr,uid,[('origin','ilike',val.name)
                                    ])
        action['context'] = {}
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = pick_ids and pick_ids[0] or False
        return action

    def retur_change(self,cr,uid,ids,branch_id,division,partner_id,retur_type,partner_cabang,context=None):
        domain = {}
        value = {}
        value['invoice_id'] = False
        value['retur_jual_line'] = False
        dso_ids = []
        menu_access = context.get('menu',False)
        value['help_type'] = menu_access
        if branch_id:
            user_obj = self.pool.get('res.users')         
            user = user_obj.browse(cr,uid,uid)
            if user.branch_type!='HO':
                if not user.branch_id:
                    raise osv.except_osv(_('Warning!'), _('User %s tidak memiliki default branch !' % user.login))
                domain['branch_id'] = [('id','=',branch_id)]
                if not division:
                    if menu_access=='showroom':
                        value['division'] = 'Unit'
                    if menu_access=='workshop':
                        value['division'] = 'Sparepart'
            else:
                raise osv.except_osv(_('Warning!'), _('User %s tidak diperbolehkan untuk melakukan transaksi retur jual !' % user.login))
            if partner_id:
                partner = self.pool.get('res.partner').browse(cr, uid, [partner_id], context=context)
                if partner.partner_type in ['Afiliasi','Konsolidasi']:
                    value['is_pic'] = True
                else:
                    value['is_pic'] = False
                if retur_type and retur_type=='Admin':
                    domain_dso=[('branch_id','=',branch_id),('division','=',division),('partner_id','=',partner_id),('state','in',['progress','done'])]
                else:
                    domain_dso=[('branch_id','=',branch_id),('division','=',division),('partner_id','=',partner_id),('state','=','done')]
                if partner_cabang:
                    domain_dso += [('partner_cabang','=',partner_cabang)]
                
                dso_search = self.pool.get('dealer.sale.order').search(cr,uid,domain_dso)
                if dso_search:
                    dso_brw = self.pool.get('dealer.sale.order').browse(cr,uid,dso_search)
                    for dso in dso_brw:
                        flag = False
                        if dso.finco_id and dso.is_credit:
                            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('origin','ilike',dso.name),('type','=','out_invoice'),('tipe','=','finco'),('partner_id','in',[dso.partner_id.id,dso.finco_id.id])])
                        else:
                            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('origin','ilike',dso.name),('type','=','out_invoice'),('tipe','=','customer'),('partner_id','=',dso.partner_id.id)])
                        if invoice_ids:
                            invoice = self.pool.get('account.invoice').browse(cr,uid,invoice_ids[0])
                            if dso.is_credit and dso.finco_id and invoice.amount_total - invoice.residual > invoice.amount_dp:
                                continue
                        for line in dso.dealer_sale_order_line:
                            if line.lot_id and line.lot_id.state not in ['intransit','titipan','stock','returned','reserved'] and line.lot_id.proses_stnk_id:
                                continue
                            obj_retur_ids = self.pool.get('dym.retur.jual.line').search(cr, uid, [('retur_id.state','not in',('draft','cancel')),('retur_id','not in',ids),('dso_line_id','=',line.id)])
                            retur_line_browse = self.pool.get('dym.retur.jual.line').browse(cr, uid, obj_retur_ids)
                            qty = line.product_qty
                            for retur_line in retur_line_browse:                    
                                qty -= retur_line.product_qty
                            if qty > 0:
                                flag = True
                        if flag == True:
                            dso_ids.append(dso.id)
                    domain['dso_id'] = [('id','in',dso_ids)]
                else:
                    so_search = self.pool.get('sale.order').search(cr,uid,domain_dso)
                    dso_brw = self.pool.get('sale.order').browse(cr,uid,so_search)
                    for dso in dso_brw:
                        invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('origin','ilike',dso.name),('type','=','out_invoice'),('tipe','=','customer'),('partner_id','=',dso.partner_id.id)])
                        if invoice_ids:
                            invoice = self.pool.get('account.invoice').browse(cr,uid,invoice_ids[0])
                        for line in dso.order_line:
                            obj_retur_ids = self.pool.get('dym.retur.jual.line').search(cr, uid, [('retur_id.state','not in',('draft','cancel')),('retur_id','not in',ids),('dso_line_id','=',line.id)])
                            retur_line_browse = self.pool.get('dym.retur.jual.line').browse(cr, uid, obj_retur_ids)
                            qty = line.product_uom_qty
                            for retur_line in retur_line_browse:                    
                                qty -= retur_line.product_uom_qty
                            if qty > 0:
                                flag = True
                        if flag == True:
                            dso_ids.append(dso.id)
                    domain['so_id'] = [('id','in',dso_ids)]
        return {'value':value,'domain':domain}

    def so_dso_change(self,cr,uid,ids,trans_id,retur_type,division,trans_type,context=None):
        print "===so_dso_change==="
        value = {}
        if not trans_id:
            value['retur_jual_line'] = False
            return {'value':value}
        invoice_line_obj = self.pool.get('account.invoice.line')
        origin = False
        if trans_type == 'DSO':
            so = self.pool.get('dealer.sale.order').browse(cr,uid,[trans_id])
            order_lines = so.dealer_sale_order_line
        if trans_type == 'SO':
            so = self.pool.get('sale.order').browse(cr,uid,[trans_id])
            order_lines = so.order_line
        retur_jual_line = []
        invoice_line = False
        if so:
            for line in order_lines:
                if trans_type == 'DSO' and line.lot_id and line.lot_id.state not in ['intransit','titipan','stock','returned','reserved'] and line.lot_id.proses_stnk_id:
                    continue
                invoice_line_ids = False
                qty = 0
                lot_id = False
                so_line_id = False
                dso_line_id = False
                price_bbn = 0
                if trans_type == 'DSO':
                    price_bbn = line.price_bbn
                    dso_line_id = line.id
                    lot_id = line.lot_id.id
                    qty = line.product_qty
                    if so.finco_id and so.is_credit:
                        invoice_line_ids = invoice_line_obj.search(cr, uid, [('invoice_id.origin','ilike',so.name),('invoice_id.type','=','out_invoice'),('product_id','=',line.product_id.id),('invoice_id.tipe','=','finco'),('invoice_id.partner_id','in',[so.partner_id.id,so.finco_id.id])])
                    else:
                        invoice_line_ids = invoice_line_obj.search(cr, uid, [('invoice_id.origin','ilike',so.name),('invoice_id.type','=','out_invoice'),('product_id','=',line.product_id.id),('invoice_id.tipe','=','customer'),('invoice_id.partner_id','=',so.partner_id.id)])
                if trans_type == 'SO':
                    so_line_id = line.id
                    qty = line.product_uom_qty
                    invoice_line_ids = invoice_line_obj.search(cr, uid, [('invoice_id.origin','ilike',so.name),('invoice_id.type','=','out_invoice'),('product_id','=',line.product_id.id),('invoice_id.tipe','in',['md_sale_unit', 'md_sale_sparepart'])])
                taxes_ids = []
                if invoice_line_ids:
                    invoice_line = self.pool.get('account.invoice.line').browse(cr,uid,invoice_line_ids[0])
                    if trans_type == 'DSO':
                        if invoice_line.invoice_id.amount_total - invoice_line.invoice_id.residual > invoice_line.invoice_id.amount_dp and so.is_credit and so.finco_id:
                            raise osv.except_osv(_('Warning!'), _("Finance company %s sudah melakukan pembayaran untuk transaksi %s!")%(so.finco_id.name, so.name))
                    for tax_id in invoice_line.invoice_line_tax_id:
                        taxes_ids.append(tax_id.id)
                    obj_retur_ids = self.pool.get('dym.retur.jual.line').search(cr, uid, [('retur_id.state','not in',('draft','cancel')),('retur_id','not in',ids),('dso_line_id','=',dso_line_id),('so_line_id','=',so_line_id)])
                    retur_line_browse = self.pool.get('dym.retur.jual.line').browse(cr, uid, obj_retur_ids)
                    for retur_line in retur_line_browse:                    
                        qty -= retur_line.product_qty
                    if qty > 0:
                        if so_line_id:
                            discounts = self.pool.get('dym.retur.jual.line').get_discount_line(cr, uid, ids, invoice_line.price_unit, qty, invoice_line.invoice_line_tax_id, line.product_id, invoice_line.invoice_id.partner_id, dso_line_id=False, so_line_id=line, context=context)
                        if dso_line_id:
                            discounts = self.pool.get('dym.retur.jual.line').get_discount_line(cr, uid, ids, invoice_line.price_unit, qty, invoice_line.invoice_line_tax_id, line.product_id, invoice_line.invoice_id.partner_id, dso_line_id=line, so_line_id=False, context=context)
                        if trans_type == 'DSO': 
                            retur_jual_line.append([0,0,{
                                'lot_id':lot_id,
                                'name':invoice_line.name,
                                'invoice_line_id':invoice_line.id,
                                'product_qty':qty,
                                'taxes_id':[(6, 0, taxes_ids)],
                                'product_uom':line.product_id.uom_id.id,
                                'product_id':line.product_id.id,                               
                                'price_unit':invoice_line.price_unit,
                                'dso_line_id':dso_line_id,
                                'so_line_id':so_line_id,
                                'product_tmpl_id':line.product_id.product_tmpl_id.id,
                                'price_bbn':price_bbn,
                                'discount_amount': discounts['discount_amount'],
                                'discount_dealer': discounts['discount_dealer'],
                                'discount_external': discounts['discount_external'],
                                'discount_cash': discounts['discount_cash'],
                                'discount_lain': discounts['discount_lain'],
                                'discount_total': discounts['discount_total'],
                                'price_subtotal': discounts['price_subtotal'],
                            }])
                        if trans_type == 'SO': 
                            retur_jual_line.append([0,0,{
                                'name':invoice_line.name,
                                'invoice_line_id':invoice_line.id,
                                'product_qty':qty,
                                'taxes_id':[(6, 0, taxes_ids)],
                                'product_uom':line.product_id.uom_id.id,
                                'product_id':line.product_id.id,                               
                                'price_unit':invoice_line.price_unit,
                                'dso_line_id':dso_line_id,
                                'so_line_id':so_line_id,
                                'product_tmpl_id':line.product_id.product_tmpl_id.id,
                                'price_bbn':price_bbn,
                                'discount_amount': discounts['discount_amount'],
                                'discount_dealer': discounts['discount_dealer'],
                                'discount_external': discounts['discount_external'],
                                'discount_cash': discounts['discount_cash'],
                                'discount_lain': discounts['discount_lain'],
                                'discount_total': discounts['discount_total'],
                                'price_subtotal': discounts['price_subtotal'],
                            }])        
        if not retur_jual_line:
            if trans_type == 'DSO':
                raise osv.except_osv(_('Warning!'), _("Produk tidak ditemukan! produk yang dijual sudah diproses STNKnya atau sudah pernah diretur!"))
            if trans_type == 'SO':
                raise osv.except_osv(_('Warning!'), _("Produk tidak ditemukan! produk yang dijual sudah pernah diretur!"))
        if invoice_line:
            value['retur_jual_line'] = retur_jual_line
            value['invoice_id'] = invoice_line.invoice_id
        else:
            value['retur_jual_line'] = False
            value['invoice_id'] = False
        return {'value':value}

    def has_retur_good(self, cr, uid, ids, *args):
        print "===has_retur_good==="
        for retur in self.browse(cr, uid, ids):
            if not retur.retur_jual_line:
                return False
        return True

class dym_retur_jual_line(osv.osv):
    _name = "dym.retur.jual.line"
    
    # def _amount_line(self, cr, uid, ids, prop, arg, context=None):
    #     res = {}
    #     tax_obj = self.pool.get('account.tax')
    #     for line in self.browse(cr, uid, ids, context=context):
    #         price = (line.price_unit * line.product_qty) - line.discount_amount
    #         taxes = tax_obj.compute_all(cr, uid, line.taxes_id, price, 1, line.product_id, line.retur_id.partner_id)
    #         res[line.id] = taxes['total']
    #     return res

    def get_discount_line(self, cr, uid, ids, price_unit, product_qty, taxes_id, product_id, partner_id, dso_line_id=False, so_line_id=False, context=None):
        res = {
            'discount_amount': 0.0,
            'discount_dealer': 0.0,
            'discount_external': 0.0,
            'discount_cash': 0.0,
            'discount_lain': 0.0,
            'discount_total': 0.0,
            'price_subtotal': 0.0,
        }
        discount_amount = discount_dealer = discount_external = discount_cash = discount_lain = discount_total = 0.0
        if dso_line_id:
            line = dso_line_id
            discount_amount = line.discount_po
            for disc in line.discount_line:
                if disc.include_invoice == False:
                    continue
                if disc.tipe_diskon == 'percentage':
                    total_diskon = disc.discount_pelanggan
                    if disc.tipe_diskon == 'percentage':
                        total_diskon = line.price_unit * disc.discount_pelanggan / 100
                    discount_dealer = discount_dealer+(total_diskon*line.product_qty)
                else:
                    total_claim_discount = disc.ps_ahm + disc.ps_md + disc.ps_finco + disc.ps_others + disc.ps_dealer
                    total_diskon_pelanggan = 0 if total_claim_discount - disc.discount_pelanggan >= disc.ps_dealer else disc.ps_dealer - (total_claim_discount - disc.discount_pelanggan)
                    total_diskon_external = disc.discount_pelanggan - total_diskon_pelanggan
                    discount_external = discount_external+(total_diskon_external*line.product_qty)
                    discount_dealer = discount_dealer+(total_diskon_pelanggan*line.product_qty)
        if so_line_id:
            line = so_line_id
            discount_cash = line.discount_cash
            discount_lain = line.discount_lain
            discount_amount = line.discount_show
            for disc in line.discount_line:
                if disc.tipe_diskon == 'percentage':
                    total_diskon = disc.discount_pelanggan
                    if disc.tipe_diskon == 'percentage':
                        total_diskon = line.price_unit * disc.discount_pelanggan / 100
                    discount_dealer = discount_dealer+(total_diskon*line.product_qty)
                else:                        
                    total_claim_discount = disc.ps_ahm + disc.ps_md + disc.ps_finco + disc.ps_others + disc.ps_dealer
                    total_diskon_pelanggan = 0 if total_claim_discount - disc.discount_pelanggan >= disc.ps_dealer else disc.ps_dealer - (total_claim_discount - disc.discount_pelanggan)
                    total_diskon_external = disc.discount_pelanggan - total_diskon_pelanggan
                    discount_external = discount_external+(total_diskon_external*line.product_qty)
                    discount_dealer = discount_dealer+(total_diskon_pelanggan*line.product_qty)
        res['discount_amount'] = discount_amount
        res['discount_dealer'] = discount_dealer
        res['discount_external'] = discount_external
        res['discount_cash'] = discount_cash
        res['discount_lain'] = discount_lain
        discount_total = discount_amount + discount_dealer + discount_external + discount_cash + discount_lain
        res['discount_total'] = discount_total
        price = (price_unit * product_qty) - discount_total
        taxes = taxes_id.compute_all(price, 1, product_id, partner_id)
        res['price_subtotal'] = taxes['total']
        return res

    def _get_discount(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for val in self.browse(cr, uid, ids, context=context):
            discounts = val.get_discount_line(val.price_unit, val.product_qty, val.taxes_id, val.product_id, val.retur_id.partner_id, dso_line_id=val.dso_line_id, so_line_id=val.so_line_id, context=context)
            res[val.id] = {
                'discount_amount': discounts['discount_amount'],
                'discount_dealer': discounts['discount_dealer'],
                'discount_external': discounts['discount_external'],
                'discount_cash': discounts['discount_cash'],
                'discount_lain': discounts['discount_lain'],
                'discount_total': discounts['discount_total'],
                'price_subtotal': discounts['price_subtotal'],
            }            
        return res

    _columns = {
        'retur_id' : fields.many2one('dym.retur.jual','Retur Penjualan'),
        'lot_id': fields.related('dso_line_id', 'lot_id', relation='stock.production.lot', type='many2one', string='Engine Number'),
        'price_bbn': fields.related('dso_line_id', 'price_bbn', type='float', string='Price BBN'),
        'retur_location_id': fields.many2one('stock.location', 'Lokasi Barang Retur'),
        'retur_product_id': fields.many2one('product.product', 'Product Retur'),
        'retur_lot_id': fields.many2one('stock.production.lot', 'Engine Number Retur'),
        'dso_line_id': fields.many2one('dealer.sale.order.line', 'Dealer Sale Order Line'),
        'so_line_id': fields.many2one('sale.order.line', 'Sale Order Line'),
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line'),
        'name': fields.text('Description', required=True),
        'product_qty': fields.integer('Quantity', required=True),
        # 'discount_amount': fields.float(string='Discount Amount'),
        'discount_amount': fields.function(_get_discount, digits_compute=dp.get_precision('Account'), string='Discount Pelanggan',
            store={
                'dym.retur.jual.line': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line_id','dso_line_id','so_line_id'], 10),
            }, multi='discount', track_visibility='always'),
        'discount_dealer': fields.function(_get_discount, digits_compute=dp.get_precision('Account'), string='Discount Program Dealer',
            store={
                'dym.retur.jual.line': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line_id','dso_line_id','so_line_id'], 10),
            }, multi='discount', track_visibility='always'),
        'discount_external': fields.function(_get_discount, digits_compute=dp.get_precision('Account'), string='Discount Program External',
            store={
                'dym.retur.jual.line': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line_id','dso_line_id','so_line_id'], 10),
            }, multi='discount', track_visibility='always'),
        'discount_cash': fields.function(_get_discount, digits_compute=dp.get_precision('Account'), string='Discount Cash',
            store={
                'dym.retur.jual.line': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line_id','dso_line_id','so_line_id'], 10),
            }, multi='discount', track_visibility='always'),
        'discount_lain': fields.function(_get_discount, digits_compute=dp.get_precision('Account'), string='Discount Lain',
            store={
                'dym.retur.jual.line': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line_id','dso_line_id','so_line_id'], 10),
            }, multi='discount', track_visibility='always'),
        'discount_total': fields.function(_get_discount, digits_compute=dp.get_precision('Account'), string='Discount Total',
            store={
                'dym.retur.jual.line': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line_id','dso_line_id','so_line_id'], 10),
            }, multi='discount', track_visibility='always'),
        'price_subtotal': fields.function(_get_discount, digits_compute=dp.get_precision('Account'), string='Subtotal',
            store={
                'dym.retur.jual.line': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line_id','dso_line_id','so_line_id'], 10),
            }, multi='discount', track_visibility='always'),
        # 'price_subtotal': fields.function(_amount_line, string='Subtotal', type='float', digits_compute= dp.get_precision('Account')),
        'taxes_id': fields.related('invoice_line_id', 'invoice_line_tax_id', relation='account.tax', type='many2many', string='Taxes'),
        'product_uom': fields.related('product_id', 'uom_id', relation='product.uom', type='many2one', string='Unit of Measure'),
        'product_id': fields.related('invoice_line_id', 'product_id', relation='product.product', type='many2one', string='Variant'),
        'price_unit': fields.float(string='Unit Price'),
        'product_tmpl_id': fields.related('product_id', 'product_tmpl_id', relation='product.template', type='many2one', string='Product Template'),
        'lot_state': fields.char(string='State', default='ok'),
    }

    def change_retur_location(self, cr, uid, ids, retur_location_id, product_id, context=None):
        value = {}
        warning = {}
        domain = {}
        ids_serial_number = []
        if retur_location_id and product_id:
            ids_serial_number = self.pool.get('dym.stock.packing.line').get_lot_available_dealer(cr, uid, ids, product_id, retur_location_id)
        domain['retur_lot_id'] = [('id','in',ids_serial_number)]
        value['retur_lot_id'] = False
        return {'domain':domain,'value':value}

    def quantity_change(self, cr, uid, ids, quantity, id_product, dso_line_id, so_line_id, division, context=None):
        value = {}
        warning = {}
        product_id = self.pool.get('product.product').browse(cr, uid, id_product)
        max_qty = 0
        if division == 'Unit':
            max_qty = self.pool.get('dealer.sale.order.line').browse(cr, uid, dso_line_id).product_qty
        if division == 'Sparepart':
            max_qty = self.pool.get('sale.order.line').browse(cr, uid, so_line_id).product_uom_qty
        obj_retur_ids = self.pool.get('dym.retur.jual.line').search(cr, uid, [('retur_id.state','not in',('draft','cancel')),('retur_id','not in',ids),('dso_line_id','=',dso_line_id),('so_line_id','=',so_line_id)])
        retur_line_browse = self.pool.get('dym.retur.jual.line').browse(cr, uid, obj_retur_ids)
        for retur_line in retur_line_browse:                    
            max_qty -= retur_line.product_qty
        if quantity <= 0 :
            value['product_qty'] = max_qty
            return {'value':value,'warning':{'title':'Perhatian !', 'message':'Quantity tidak boleh kurang dari 1'}}
        if quantity > max_qty:
            value['product_qty'] = max_qty
            return {'value':value,'warning':{'title':'Perhatian !', 'message':'Maximal quantity yang bisa di retur adalah '+str(max_qty)}}
        return {'value':value}

class dym_retur_barang_line(osv.osv):
    _name = "dym.retur.barang.jual.line"
    
    _columns = {
        'retur_id' : fields.many2one('dym.retur.jual','Retur Penjualan'),
        'product_id': fields.many2one('product.product', 'Product'),
        'product_qty': fields.integer('Quantity', required=True),
        'engine_number': fields.many2one('stock.production.lot', 'Engine Number'),
        'move_id': fields.many2one('stock.move', 'Move'),
        'jual_line_id': fields.many2one('dym.retur.jual.line', 'Jual Line ID'),
        'engine_number_retur': fields.many2one('stock.production.lot', 'Engine Number Retur'),
    }

class dym_stock_move(osv.osv):
    _inherit = 'stock.move'

    _columns = {
        'retur_jual_line_id':fields.many2one('dym.retur.jual.line',string="Retur Jual Line"),
    }

