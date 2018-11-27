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
]

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')

class wiz_retur_beli_line(orm.TransientModel):
    _name = 'wiz.retur.beli.line'
    _description = "Retur Beli Wizard Line"
    _columns = {
        'wizard_retur_beli_id': fields.many2one('wiz.retur.beli', 'Wizard ID'),
        'check_process':fields.boolean('Process?'),
        'product_id': fields.many2one('product.product', 'Product'),
        'product_qty': fields.integer('Quantity', required=True),
        'engine_number': fields.many2one('stock.production.lot', 'Engine Number'),
        'move_id': fields.many2one('stock.move', 'Move'),
        'beli_line_id': fields.many2one('dym.retur.beli.line', 'Beli Line ID'),
    }

    def onchange_engine(self, cr, uid, ids, invoice_id, product_id, engine_number):
        value = {}
        domain = {}
        warning = {}
        return  {'value':value, 'domain':domain, 'warning':warning}

    def quantity_change(self, cr, uid, ids, quantity, id_product, beli_line_id, context=None):
        value = {}
        warning = {}
        product_id = self.pool.get('product.product').browse(cr, uid, id_product)
        value['check_process'] = True
        if product_id.categ_id.isParentName('Unit') :
            value['product_qty'] = 1
            return {'value':value}
        beli_line = self.pool.get('dym.retur.beli.line').browse(cr, uid, beli_line_id)
        po_ids = self.pool.get('purchase.order').search(cr, uid, [('invoice_ids', 'in', [beli_line.retur_id.invoice_id.id])])
        for po in self.pool.get('purchase.order').browse(cr, uid, po_ids):
            picking_ids = []
            picking_ids += [picking.id for picking in po.picking_ids]
        move_obj = self.pool.get('stock.move')
        move_search = move_obj.search(cr, uid, [('picking_id', 'in', picking_ids), ('product_id', '=', id_product), ('state', '=', 'done')])
        received_qty = 0
        for move in self.pool.get('stock.move').browse(cr, uid, move_search):
            search_return_history = move_obj.search(cr, uid, [('origin_returned_move_id', '=', move.id), ('state', 'not in', ('draft','cancel'))])
            return_history_qty = 0
            for return_history in self.pool.get('stock.move').browse(cr, uid, search_return_history):
                return_history_qty += return_history.product_uom_qty
            received_qty += move.product_uom_qty - return_history_qty
        barang_line_ids = self.pool.get('dym.retur.barang.line').search(cr, uid, [('beli_line_id','=',beli_line_id)])
        barang_line_brw = self.pool.get('dym.retur.barang.line').browse(cr, uid, barang_line_ids)
        barang_line_qty = 0
        for barang_line in barang_line_brw:
            barang_line_qty += barang_line.product_qty
        received_qty -= barang_line_qty
        if received_qty > beli_line.product_qty:
            received_qty = beli_line.product_qty
        if quantity <= 0 :
            value['product_qty'] = received_qty
            return {'value':value,'warning':{'title':'Perhatian !', 'message':'Quantity tidak boleh kurang dari 1'}}
        if quantity > received_qty:
            value['product_qty'] = received_qty
            return {'value':value,'warning':{'title':'Perhatian !', 'message':'Maximal quantity yang bisa di retur adalah '+str(received_qty)}}
        return {'value':value}

class wiz_retur_beli(orm.TransientModel):
    _name = 'wiz.retur.beli'
    _description = "Retur Beli Wizard"

    _columns = {
        'retur_id' : fields.many2one('dym.retur.beli','Retur Pembelian'),
        'invoice_id' : fields.many2one('account.invoice','Invoice'),
        'line_ids': fields.one2many('wiz.retur.beli.line', 'wizard_retur_beli_id'),
    }

    _defaults = {
        'retur_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False,
        'invoice_id': lambda self, cr, uid, ctx: ctx and ctx.get('invoice_id', False) or False,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("Data Error, please try to refresh page or contact your administrator!"))
        res = super(wiz_retur_beli, self).default_get(cr, uid, fields, context=context)
        proses_id = context and context.get('active_id', False) or False
        val = self.pool.get('dym.retur.beli').browse(cr, uid, proses_id, context=context)
        move_obj = self.pool.get('stock.move')
        result1 = []     
        for beli_line in val.retur_beli_line:
            if beli_line.product_id.categ_id.isParentName('Unit'):
                packing_line_obj = self.pool.get('dym.stock.packing.line')
                po_ids = self.pool.get('purchase.order').search(cr, uid, [('invoice_ids', 'in', [val.invoice_id.id])])
                serial_number_ids = []
                packing_line = []
                for po in self.pool.get('purchase.order').browse(cr, uid, po_ids):
                    picking_ids = []
                    picking_ids += [picking.id for picking in po.picking_ids]
                    packing_line_ids = packing_line_obj.search(cr, uid, [('packing_id.picking_id','in',picking_ids),('product_id','=',beli_line.product_id.id),('packing_id.state','=','posted')])
                    for line in packing_line_obj.browse(cr, uid, packing_line_ids):
                        barang_lot_ids = self.pool.get('dym.retur.barang.line').search(cr, uid, ['|','&',('retur_id','=',val.id),('beli_line_id','=',beli_line.id),'&',('retur_id.invoice_id','=',val.invoice_id.id),('retur_id.state','not in',('draft','cancel')),('engine_number','=',line.serial_number_id.id)])
                        if line.serial_number_id.id not in serial_number_ids and not barang_lot_ids and line.serial_number_id.state in ['intransit','stock']:
                            serial_number_ids.append(line.serial_number_id.id)
                            packing_line.append(line)
                for quantity in range(int(len(serial_number_ids))):
                    move_obj = self.pool.get('stock.move')
                    move_search = move_obj.search(cr, uid, [('picking_id', '=', packing_line[quantity].packing_id.picking_id.id), ('product_id', '=', beli_line.product_id.id), ('state', '=', 'done')])
                    result1.append([0,0,{'retur_id': val.id, 'product_qty': 1, 'product_id': beli_line.product_id.id, 'beli_line_id': beli_line.id, 'engine_number':serial_number_ids[quantity], 'move_id':move_search[0]}])
            else :
                po_ids = self.pool.get('purchase.order').search(cr, uid, [('invoice_ids', 'in', [val.invoice_id.id])])
                picking_ids = []
                for po in self.pool.get('purchase.order').browse(cr, uid, po_ids):
                    picking_ids += [picking.id for picking in po.picking_ids]
                move_obj = self.pool.get('stock.move')
                move_search = move_obj.search(cr, uid, [('picking_id', 'in', picking_ids), ('product_id', '=', beli_line.product_id.id), ('state', '=', 'done')])
                received_qty = 0
                for move in self.pool.get('stock.move').browse(cr, uid, move_search):
                    search_return_history = move_obj.search(cr, uid, [('origin_returned_move_id', '=', move.id), ('state', 'not in', ('draft','cancel'))])
                    return_history_qty = 0
                    for return_history in self.pool.get('stock.move').browse(cr, uid, search_return_history):
                        return_history_qty += return_history.product_uom_qty
                    received_qty += move.product_uom_qty - return_history_qty
                barang_line_ids = self.pool.get('dym.retur.barang.line').search(cr, uid, [('beli_line_id','=',beli_line.id)])
                barang_line_brw = self.pool.get('dym.retur.barang.line').browse(cr, uid, barang_line_ids)
                barang_line_qty = 0
                for barang_line in barang_line_brw:
                    barang_line_qty += barang_line.product_qty
                received_qty -= barang_line_qty
                if received_qty > beli_line.product_qty:
                    received_qty = beli_line.product_qty
                if received_qty > 0:
                    if move_search:
                        result1.append([0,0,{'retur_id': val.id, 'product_qty': received_qty, 'product_id': beli_line.product_id.id, 'beli_line_id': beli_line.id, 'move_id':move_search[0]}])
        res['line_ids'] = result1
        return res

    def generate_retur_barang(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for data in self.browse(cr, uid, ids, context=context):
            result1 = []
            for line in data.line_ids:
                if line.check_process:
                    result1.append({'retur_id': data.retur_id.id, 'product_qty': line.product_qty, 'product_id': line.product_id.id, 'beli_line_id': line.beli_line_id.id, 'engine_number':line.engine_number.id, 'move_id':line.move_id.id})
            for res in result1:
                self.pool.get('dym.retur.barang.line').create(cr, uid, res)
        return {}

class stock_move(osv.osv):
    _inherit = 'stock.move'

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(stock_move, self).write(cr, uid, ids, vals, context=context)
        if vals.get('state') in ['done', 'cancel']:
            for move in self.browse(cr, uid, ids, context=context):
                if move.picking_id.origin and (move.picking_id.origin[:3] == 'RB/' or move.picking_id.origin[:3] == 'RBE'):
                    retur_id = self.pool.get('dym.retur.beli').search(cr, uid, [('name','=',move.picking_id.origin)])
                    if self.test_moves_retur_done(cr, uid, retur_id[0], context=context):
                        lot = move.restrict_lot_id
                        workflow.trg_validate(uid, 'dym.retur.beli', retur_id[0], 'picking_done', cr)
                    if self.test_moves_retur_except(cr, uid, move.picking_id, context=context):
                        workflow.trg_validate(uid, 'dym.retur.beli', retur_id[0], 'picking_cancel', cr)
        return res

    def test_moves_retur_done(self, cr, uid, retur_id, context=None):
        retur_brw = self.pool.get('dym.retur.beli').browse(cr, uid, [retur_id])
        obj_picking = self.pool.get('stock.picking')
        pick_ids = obj_picking.search(cr,uid,[('origin','ilike',retur_brw.name)])
        pick_brw = obj_picking.browse(cr, uid, pick_ids)
        for pick in pick_brw:
            if pick.state != 'done' and pick.state != 'cancel' :
                return False
        return True

    def test_moves_retur_except(self, cr, uid, picking, context=None):
        at_least_one_canceled = False
        alldoneorcancel = True
        if picking.state == 'cancel':
            at_least_one_canceled = True
        if picking.state not in ['done', 'cancel']:
            alldoneorcancel = False
        return at_least_one_canceled and alldoneorcancel

class dym_retur_beli(osv.osv):
    _name = "dym.retur.beli"
    _description = "Retur Pembelian"
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_retur_pembelian_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_id',\
            'division',\
            'number',\
            'date', \
            'invoice_retur', \
            'retur_type',\
            'supplier_invoice_number',\
            'document_date',\
            'supplier',\
            'invoice_beli_number',\
            'coa',\
            'kode',\
            'deskripsi',\
            'warna',\
            'engine_number',\
            'chassis_number',\
            'price_unit',\
            'discount_amount',\
            'product_qty',\
            'jumlah',\
            'dpp',\
            'ppn',\
            'hutang',\
            'nilai_persediaan',\
            'oos_number',\
            'payment_number',\
            'payment_date',\
            'payment_reallocation',\
            'saldo', \

            ]
 
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_retur_pembelian_non_unit_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_id',\
            'division',\
            'number',\
            'date', \
            'invoice_retur', \
            'retur_type',\
            'supplier_invoice_number',\
            'document_date',\
            'supplier',\
            'coa',\
            'kode',\
            'deskripsi',\
            'price_unit',\
            'discount_amount',\
            'product_qty',\
            'jumlah',\
            'dpp',\
            'ppn',\
            'oos_number',\
            'payment_number',\
            'payment_date',\
            'payment_reallocation',\
            'saldo', \

            ]

    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_arap_details_fields(self, cr, uid, context=None):
        return [
            'document', 'date', 'date_maturity', 'account', 'description',
            'rec_or_rec_part', 'debit', 'credit', 'balance',
            # 'partner_id',
        ]
 
    # Change/Add Template entries
    def _report_xls_arap_overview_template(self, cr, uid, context=None):
        """
        Template updates, e.g.
 
        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Move Line ID')],
                'lines': [1, 0, 'text', _render("p['ids_aml']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
 
    # Change/Add Template entries
    def _report_xls_arap_details_template(self, cr, uid, context=None):
        return {}

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('confirmed', 'Waiting Approval'),
        ('approved','Process Confirmed'),
        ('except_picking', 'Shipping Exception'),
        ('except_invoice', 'Invoice Exception'),
        ('done','Done'),
        ('cancel','Cancelled')
    ] 

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for val in self.browse(cr, uid, ids, context=context):
            res[val.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            amount_untaxed = amount_tax = amount_total = amount_tax = 0.0
           
            for line in val.retur_beli_line:
                amount_untaxed += line.price_subtotal
                price = (line.price_unit * line.product_qty) - line.discount_amount
                for c in self.pool.get('account.tax').compute_all(cr,uid, line.taxes_id, price,1, line.product_id, val.partner_id)['taxes']:
                    amount_tax += c.get('amount',0.0)
            res[val.id]['amount_untaxed'] = amount_untaxed
            res[val.id]['amount_tax'] = amount_tax
            res[val.id]['amount_total'] = amount_untaxed + amount_tax
        return res
    
    def _get_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('dym.retur.beli.line').browse(cr, uid, ids, context=context):
            result[line.retur_id.id] = True
        return result.keys()

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')         
        user = user_obj.browse(cr,uid,uid)
        return user.get_default_branch()

    def _count_picking(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for retur in self.browse(cr, uid, ids, context=context):
            res[retur.id] = len(retur.retur_beli_line)
        return res

    _columns = {
        'branch_id': fields.many2one('dym.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division', change_default=True, select=True),
        'name': fields.char('Retur Beli Ref.', readonly=True),
        'date': fields.date('Retur Date'),
        'date_due': fields.date('Due Date'),
        'retur_type':fields.selection(RETUR_TYPE, 'Return Type', change_default=True, select=True),
        'state': fields.selection(STATE_SELECTION, 'State', readonly=True),
        'retur_beli_line': fields.one2many('dym.retur.beli.line','retur_id',string="Retur Line"), 
        'partner_id':fields.many2one('res.partner','Supplier'),
        'partner_cabang': fields.many2one('dym.cabang.partner',string='Cabang Supplier'),
        'invoice_id': fields.related('consolidate_id', 'invoice_id', relation='account.invoice', type='many2one', string='Supplier Invoice Ref.'),
        'consolidate_id':fields.many2one('consolidate.invoice','Consolidate Invoice',domain="[('branch_id','=',branch_id),('division','=',division),('partner_id','=',partner_id),('asset','=',False),('state','=','done')]"),
        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tax Base',
            store={
                'dym.retur.beli': (lambda self, cr, uid, ids, c={}: ids, ['retur_beli_line'], 10),
                'dym.retur.beli.line': (_get_line, ['product_qty'], 10),
            },
            multi='sums', help="The amount without tax and discount.", track_visibility='always'),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'dym.retur.beli': (lambda self, cr, uid, ids, c={}: ids, ['retur_beli_line'], 10),
                'dym.retur.beli.line': (_get_line, ['product_qty'], 10),
            },
            multi='sums', help="Grand Total."),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tax Amount',
            store={
                'dym.retur.beli': (lambda self, cr, uid, ids, c={}: ids, ['retur_beli_line'], 10),
                'dym.retur.beli.line': (_get_line, ['product_qty'], 10),
            },
            multi='sums', help="The tax amount."),
        'invoiced': fields.boolean('Invoiced', readonly=True, copy=False),
        'invoice_method': fields.selection([('order','Based on generated draft invoice')], 'Invoicing Control', required=True,
            readonly=True),
        'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
        'confirm_date':fields.datetime('Confirmed on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),  
        'payment_term':fields.many2one('account.payment.term',string="Payment Terms"),
        'picking_count': fields.function(_count_picking, type='integer', string='Picking'),
        # 'reason': fields.text('Alasan Retur', required=True),
    }
    _defaults = {
        'date': fields.date.context_today,
        'state':'draft',
        'invoice_method':'order',
        'invoiced': 0,
        'branch_id': _get_default_branch,
     }
    
    def create(self, cr, uid, vals, context=None):
        if not vals['retur_beli_line']:
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail retur beli. Data tidak bisa di save."))
        retur_beli = []
        proses_pool = self.pool.get('dym.retur.beli.line')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'RBE', division=vals['division'])
        vals['date'] = time.strftime('%Y-%m-%d'),
        proses_id = super(dym_retur_beli, self).create(cr, uid, vals, context=context) 
        return proses_id
    
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Retur pembelian sudah di proses ! tidak bisa didelete !"))
        return super(dym_retur_beli, self).unlink(cr, uid, ids, context=context)
    
    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def wkf_confirm_retur(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot')
        move_pool = self.pool.get('stock.move')
        self.write(cr, uid, ids, {'state': 'approved','confirm_uid':uid,'confirm_date':datetime.now()})
        return True
   
    def wkf_action_cancel(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)  
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        return True

    def wkf_approve_retur(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'approved'})
        return True
    
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        collect = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot')
        line_pool = self.pool.get('dym.retur.beli.line')
        return super(dym_retur_beli, self).write(cr, uid, ids, vals, context=context)
    
    def wkf_set_to_draft(self,cr,uid,ids):
        return self.write({'state':'draft'})       
    
    def refund_cleanup_lines(self, cr, uid, ids, lines, retur_beli_line=False, journal=False, context=None):
        result = []
        if retur_beli_line:
            for retur_line in retur_beli_line:
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
                values['discount_amount'] = retur_line.discount_amount
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
        return result

    def prepare_refund(self, cr, uid, ids, invoice, retur_beli_line, payment_term, date=None, period_id=None, description=None, journal_id=None, origin=None, context=None):
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
        elif invoice['type'] == 'in_invoice':
            journal_src = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'purchase_refund')], limit=1)
            journal = self.pool.get('account.journal').browse(cr, uid, journal_src)
        else:
            journal_src = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale_refund')], limit=1)
            journal = self.pool.get('account.journal').browse(cr, uid, journal_src)
        values['journal_id'] = journal.id
        values['invoice_line'] = self.refund_cleanup_lines(cr, uid, ids, invoice.invoice_line, retur_beli_line, journal)
        tax_lines = filter(lambda l: l.manual, invoice.tax_line)
        values['tax_line'] = self.refund_cleanup_lines(cr, uid, ids, tax_lines)
        values['type'] = TYPE2REFUND[invoice['type']]
        values['supplier_invoice_number'] = invoice.supplier_invoice_number
        values['document_date'] = invoice.document_date
        values['date_invoice'] = date
        values['state'] = 'draft'
        values['number'] = False
        values['origin'] = origin
        values['payment_term'] = payment_term
        values['account_id'] = journal.default_debit_account_id.id
        values['analytic_1'] = invoice.analytic_1.id
        values['analytic_2'] = invoice.analytic_2.id
        values['analytic_3'] = invoice.analytic_3.id
        values['analytic_4'] = invoice.analytic_4.id
        if period_id:
            values['period_id'] = period_id
        if description:
            values['name'] = description
        return values

    def action_invoice_create(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        obj_inv = self.pool.get('account.invoice')
        invoice_line = []
        config = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',val.branch_id.id)])
        if config :
            config_browse = self.pool.get('dym.branch.config').browse(cr,uid,config)
            retur_debit_account_id = config_browse.retur_beli_journal_id.default_debit_account_id.id 
            retur_credit_account_id = config_browse.retur_beli_journal_id.default_credit_account_id.id  
            journal_retur = config_browse.retur_beli_journal_id.id
            if not journal_retur :
                raise osv.except_osv(_('Attention!'),
                    _('Jurnal Retur Pembelian belum diisi, harap isi terlebih dahulu didalam branch config')) 
            if not config_browse.retur_beli_journal_id.default_debit_account_id.id:
                raise osv.except_osv(_('Attention!'),
                        _('Mohon lengkapi data default debit account di journal %s') % (config_browse.retur_beli_journal_id.name))   
            if config_browse.retur_beli_journal_id.default_debit_account_id.type != 'receivable':
                raise osv.except_osv(_('Attention!'),
                        _('Data internal type untuk account retur %s - %s harus Receivable') % (config_browse.retur_beli_journal_id.default_debit_account_id.code, config_browse.retur_beli_journal_id.default_debit_account_id.name)) 

        elif not config:
            raise osv.except_osv(_('Error!'),
                _('Please define Journal in Setup Division for this branch: "%s".') % \
                (val.branch_id.name))
                              
        if val.amount_total < 1: 
            raise osv.except_osv(_('Attention!'),
                _('Mohon periksa kembali detail retur.')) 

        values = self.prepare_refund(cr, uid, ids, val.invoice_id, val.retur_beli_line, val.payment_term.id, date=datetime.today(), period_id=False, description=False, journal_id=journal_retur, origin=val.name, context=context)
        inv_refund_id = obj_inv.create(cr, uid, values)    
        obj_inv.button_compute(cr, uid, inv_refund_id)
        return inv_refund_id 

    def _get_default_location_delivery_sales(self,cr,uid,ids,context=None):
        default_location_id = {}
        obj_picking_type = self.pool.get('stock.picking.type')
        for val in self.browse(cr,uid,ids):
            picking_type_id = obj_picking_type.search(cr,uid,[
                ('branch_id','=',val.branch_id.id),
                ('code','=','incoming')
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
        location_dest_id = location['destination']
        if default_location_search:
            default_location_brw = self.pool.get('dym.product.location').browse(cr, uid, default_location_search)
            location_dest_id = default_location_brw.location_id.id
        move_template = {
            'branch_id': retur.branch_id.id,
            'division': retur.division,
            'name': line.product_id.name_get().pop()[1] or '',
            'product_id': line.product_id.id,
            'product_uom': line.product_uom.id,
            'product_uom_qty': line.product_qty,
            'location_id': location['source'],
            'location_dest_id': location_dest_id, ##check
            'picking_id': picking_id,
            'price_unit': line.consolidate_line_id.price_unit,
            'invoice_state': 'none',
            'retur_beli_line_id': line.id,
        }
        res.append(move_template)
        return res

    def _create_returns(self, cr, uid, ids, context=None):
        retur_brw = self.browse(cr, uid, ids)[0]
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        uom_obj = self.pool.get('product.uom')
        data_obj = self.pool.get('stock.return.picking.line')
        picking_type_obj = self.pool.get('stock.picking.type')
        returned_lines = 0

        # Cancel assignment of existing chained assigned moves
        # moves_to_unreserve = []
        # for line in retur_brw.retur_beli_line:
        #     if line.consolidate_line_id.move_id:
        #         move = line.consolidate_line_id
        #         if move.move_id.move_dest_id:
        #             to_check_moves = [move.move_id.move_dest_id]
        #             while to_check_moves:
        #                 current_move = to_check_moves.pop()
        #                 if current_move.state not in ('done', 'cancel') and current_move.reserved_quant_ids:
        #                     moves_to_unreserve.append(current_move.id)
        #                 split_move_ids = move_obj.search(cr, uid, [('split_from', '=', current_move.id)], context=context)
        #                 if split_move_ids:
        #                     to_check_moves += move_obj.browse(cr, uid, split_move_ids, context=context)
        picking_type_id = picking_type_obj.search(cr,uid,[
            ('branch_id','=',retur_brw.branch_id.id),
            ('code','=','incoming')
        ])
        picking_type = False
        if picking_type_id:
            picking_type = picking_type_obj.browse(cr,uid,picking_type_id[0])
        if not picking_type or not picking_type.return_picking_type_id:
            raise osv.except_osv(_('Warning !'), _("Picking Type untuk branch %s belum lengkap")%(retur_brw.branch_id.name))

               
        # if moves_to_unreserve:
        #     move_obj.do_unreserve(cr, uid, moves_to_unreserve, context=context)
        #     #break the link between moves in order to be able to fix them later if needed
        #     move_obj.write(cr, uid, moves_to_unreserve, {'move_orig_ids': False}, context=context)

        #Create new picking for returned products
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

        if retur_brw.retur_type == 'Admin':
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

        location = self._get_default_location_delivery_sales(cr,uid,ids)
        for line in retur_brw.retur_beli_line:
            new_qty = line.product_qty
            # default_location_search = self.pool.get('dym.product.location').search(cr, uid, [
            #                                                             ('branch_id','=',retur_brw.branch_id.id),
            #                                                             ('product_id','=',line.product_id.id)
            #                                                             ], order='id desc', limit=1)
            # locatian_search_id = location['destination']
            # if default_location_search:
            #     default_location_brw = self.pool.get('dym.product.location').browse(cr, uid, default_location_search)
            #     locatian_search_id = default_location_brw.location_id.id
            location_search_id = False
            id_quant = False
            if line.consolidate_line_id.name.id:
                id_quant = self.pool.get('stock.quant').search(cr, SUPERUSER_ID, [('lot_id','=',line.consolidate_line_id.name.id),('product_id','=',line.product_id.id),('location_id.usage','=','nrfs'),('qty','>',0)])
                if id_quant:
                    location_search_id = self.pool.get('stock.quant').browse(cr, uid, id_quant)[0].location_id.id
                else:
                    raise osv.except_osv(_('Attention!'),
                    _('Nomor Engine %s tidak ditemukan / tidak termasuk stock not ready for sale!')%(line.consolidate_line_id.name.name))
            else:
                locatian_search_ids = self.pool.get('dym.stock.packing.line').get_stock_location(cr, SUPERUSER_ID, [], line.product_id.id, retur_brw.branch_id.id, [], usage=['nrfs'], lot_state=['returned'], context=context)
                if not locatian_search_ids:
                    raise osv.except_osv(('Invalid action !'), ('Tidak ditemukan stock not ready for sale di branch %s') % (retur_brw.branch_id.name,))
                location_search_id = locatian_search_ids[0]
            if new_qty:
                move_retur_id = move_obj.create(cr, uid, {
                    'branch_id': retur_brw.branch_id.id,
                    'division': retur_brw.division,
                    'product_id': line.product_id.id,
                    'name': line.product_id.name_get().pop()[1] or '',
                    'product_uom_qty': new_qty,
                    'picking_id': new_picking,
                    'location_id': location_search_id,
                    'location_dest_id': picking_type.default_location_src_id.id,
                    'invoice_state': 'none',
                    'product_uom': line.product_uom.id,
                    'restrict_lot_id': line.consolidate_line_id.name.id,
                    # 'origin_returned_move_id': line.consolidate_line_id.move_id.id,
                    'price_unit': line.consolidate_line_id.price_unit,
                    'retur_beli_line_id': line.id,
                })
                if line.consolidate_line_id.name.id and id_quant:
                    self.pool.get('stock.quant').write(cr, SUPERUSER_ID, [id_quant[0]], {'reservation_id':move_retur_id})
                assign_move = []
                extras = {}
                for x in line.product_id.extras_line:
                    if x.product_id in extras:
                        extras[x.product_id] = {'qty':extras[x.product_id]['qty']+(new_qty*x.quantity),'line':move_retur_id}
                    else:
                        extras[x.product_id] = {'qty':new_qty*x.quantity,'line':move_retur_id}
                if extras and retur_brw.retur_type == 'Uang':
                    for key, value in extras.items():
                        default_location_search = self.pool.get('dym.product.location').search(cr, SUPERUSER_ID, [
                                                                                    ('branch_id','=',retur_brw.branch_id.id),
                                                                                    ('product_id','=',key.id)
                                                                                    ], order='id desc', limit=1)
                        if default_location_search:
                            default_location_brw = self.pool.get('dym.product.location').browse(cr, SUPERUSER_ID, default_location_search)
                            location_search_id = default_location_brw.location_id.id
                        # location_search_ids = self.pool.get('dym.stock.packing.line').get_stock_location(cr, SUPERUSER_ID, [], key.id, retur_brw.branch_id.id, [0], where_query=" and q.qty >= " + str(value['qty']), context=context)
                        # if not location_search_ids:
                        #     raise osv.except_osv(('Invalid action !'), ('Tidak ditemukan stock product ksu %s di branch %s') % (key.name, retur_brw.branch_id.name,))
                        # elif not location_search_id or location_search_id not in location_search_ids:
                        #     location_search_id = location_search_ids[0]
                        move_retur_id = move_obj.create(cr, uid, {
                            'branch_id': retur_brw.branch_id.id,
                            'division': retur_brw.division,
                            'product_id': key.id,
                            'name': key.name_get().pop()[1] or '',
                            'product_uom_qty': value['qty'],
                            'picking_id': new_picking,
                            'location_id': location_search_id,
                            'location_dest_id': picking_type.default_location_src_id.id,
                            'invoice_state': 'none',
                            'product_uom': key.uom_id.id,
                            # 'restrict_lot_id': moves.restrict_lot_id.id,
                            # 'origin_returned_move_id': moves.id,
                            'price_unit': 0,
                            'retur_beli_line_id': line.id,
                        })
                        assign_move.append(move_retur_id)
                # moves_ksu_barang_bonus = []
                # if line.consolidate_line_id.move_id and retur_brw.retur_type == 'Uang':
                #     moves_ksu_barang_bonus = move_obj.search(cr, uid, [('move_line_id_extra','=',line.consolidate_line_id.move_id.id),('id','!=',line.consolidate_line_id.move_id.id)])
                # for moves in move_obj.browse(cr, uid, moves_ksu_barang_bonus):
                #     move_retur_id = move_obj.create(cr, uid, {
                #         'branch_id': retur_brw.branch_id.id,
                #         'division': retur_brw.division,
                #         'product_id': moves.product_id.id,
                #         'name': moves.product_id.name_get().pop()[1] or '',
                #         'product_uom_qty': moves.product_uom_qty,
                #         'picking_id': new_picking,
                #         'location_id': moves.location_dest_id.id,
                #         'location_dest_id': moves.location_id.id,
                #         'invoice_state': 'none',
                #         'product_uom': moves.product_uom.id,
                #         'restrict_lot_id': moves.restrict_lot_id.id,
                #         'origin_returned_move_id': moves.id,
                #         'price_unit': moves.price_unit,
                #     })
                #     assign_move.append(move_retur_id)
                assign_move = move_obj.action_confirm(cr, uid, assign_move)
                move_obj.action_assign(cr, uid, assign_move)
            if retur_brw.retur_type == 'Admin':
                if not line.product_id:
                    continue
                if line.product_id.type in ('product', 'consu'):
                    for vals in self._prepare_order_line_move(cr, uid, ids, retur_brw, line, picking_id, location, context=context):
                        move = move_obj.create(cr, uid, vals, context=context)
                        todo_moves.append(move)
        
        pick_obj.action_confirm(cr, uid, [new_picking], context=context)
        pick_obj.action_assign(cr, uid, [new_picking], context=context)

        # if retur_brw.retur_type == 'Admin':
            # todo_moves = move_obj.action_confirm(cr, uid, todo_moves)
            # move_obj.force_assign(cr, uid, todo_moves)
        return True

    def action_picking_create(self, cr, uid, ids, context=None):
        for retur in self.browse(cr, uid, ids):
            new_picking_id = self._create_returns(cr, uid, ids)
        return True

    def wkf_retur_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def picking_done(self, cr, uid, ids, context=None):
        # move_obj = self.pool.get('stock.move')
        # for retur in self.browse(cr, uid, ids):
        #     if not retur.retur_barang_line:
        #         for beli_line in retur.retur_beli_line:
        #             obj_retur_barang_ids = self.pool.get('dym.retur.barang.line').search(cr, uid, [('retur_id','=',retur.id),('beli_line_id','=',beli_line.id)])
        #             qty_barang_line = 0
        #             if obj_retur_barang_ids:
        #                 retur_barang_line_browse = self.pool.get('dym.retur.barang.line').browse(cr, uid, obj_retur_barang_ids)
        #                 for barang_line in retur_barang_line_browse:
        #                     qty_barang_line += barang_line.product_qty
        #             po_ids = self.pool.get('purchase.order').search(cr, uid, [('invoice_ids', 'in', [retur.invoice_id.id])])
        #             packing_line = []
        #             for po in self.pool.get('purchase.order').browse(cr, uid, po_ids):
        #                 picking_ids = []
        #                 picking_ids += [picking.id for picking in po.picking_ids]
        #             move_search = move_obj.search(cr, uid, [('picking_id', '=', picking_ids), ('product_id', '=', beli_line.product_id.id), ('state', 'not in', ('done','cancel'))])
        #             move_brw = move_obj.browse(cr, uid, move_search)
        #             cancel_move_qty = beli_line.product_qty - qty_barang_line
        #             for move in move_brw:
        #                 if cancel_move_qty > 0:
        #                     minus_cancel = 0
        #                     if move.product_uom_qty > cancel_move_qty:
        #                         new_move = move_obj.split(cr, uid, move, cancel_move_qty)
        #                         move_obj.action_cancel(cr, uid, [new_move])
        #                         minus_cancel = cancel_move_qty
        #                     else:
        #                         move_obj.action_cancel(cr, uid, [move.id])
        #                         minus_cancel = move.product_uom_qty
        #                     cancel_move_qty  -= minus_cancel
        self.write(cr, uid, ids, {'state':'approved'}, context=context)
        return True

    def invoice_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'approved','invoiced':True}, context=context)
        return True
    
    def view_invoice(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree4')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
        result['views'] = [(res and res[1] or False, 'form')]
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        obj = obj_inv.search(cr,uid,[('origin','ilike',val.name),
                                     ('type','=','in_refund')
                                    ])
        result['res_id'] = obj[0] 
        return result

    def view_picking(self,cr,uid,ids,context=None):
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

    def retur_change(self,cr,uid,ids,branch_id,division,partner_id,context=None):
        val = {}
        dom = {}
        val['invoice_id'] = False
        val['retur_beli_line'] = False
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if not user.branch_id:
            raise osv.except_osv(('Perhatian !'), ("User %s tidak memiliki default branch. Silahkan hubungi system administrator untuk melanjutkan.")%(user.login))
        if not user.branch_ids:
            raise osv.except_osv(('Perhatian !'), ("User %s tidak memiliki akses ke cabang manapun. Silahkan hubungi system administrator untuk melanjutkan.")%(user.login))
        if user.branch_type != 'HO':
            dom['branch_id'] = [('id','=',user.branch_id.id)]
        else:
            dom['branch_id'] = [('id','in',user.branch_ids.ids)]
        return {'value':val,'domain':dom}

    def purchase_change(self,cr,uid,ids,consolidate_id,retur_type,division,context=None):
        value = {}
        print "==purchase_change=="
        return {'value':value}
      
    def consolidate_change(self,cr,uid,ids,consolidate_id,retur_type,division,context=None):
        value = {}
        consolidate = self.pool.get('consolidate.invoice').browse(cr,uid,[consolidate_id])
        move_obj = self.pool.get('stock.move')
        invoice_line_obj = self.pool.get('account.invoice.line')
        retur_beli_line = []
        if consolidate:
            for x in consolidate.consolidate_line:
                if x.name and (x.name.state != 'stock' or x.name.location_id.usage != 'nrfs'):
                    continue
                invoice_line_ids = invoice_line_obj.search(cr, uid, [('purchase_line_id','=',x.purchase_line_id.id),('invoice_id','=',consolidate.invoice_id.id)])
                if invoice_line_ids:
                    invoice_line = self.pool.get('account.invoice.line').browse(cr,uid,invoice_line_ids[0])
                    taxes_ids = []
                    for tax_id in invoice_line.invoice_line_tax_id:
                        taxes_ids.append(tax_id.id)
                    qty = x.product_qty
                    obj_retur_ids = self.pool.get('dym.retur.beli.line').search(cr, uid, [('retur_id.state','not in',('draft','cancel')),('consolidate_line_id','=',x.id),('retur_id','not in',ids)])
                    retur_line_browse = self.pool.get('dym.retur.beli.line').browse(cr, uid, obj_retur_ids)
                    for retur_line in retur_line_browse:                    
                        qty -= retur_line.product_qty
                    if qty > 0:
                        retur_beli_line.append([0,0,{
                            'lot_id':x.name.id,
                            'name':invoice_line.name,                               
                            'consolidate_line_id':x.id,
                            'invoice_line_id':invoice_line.id,
                            'product_qty':qty,
                            'discount_amount': (invoice_line.discount_amount + invoice_line.discount_program + invoice_line.discount_cash + invoice_line.discount_lain) / invoice_line.quantity,
                            'taxes_id':[(6, 0, taxes_ids)],
                            'product_uom':x.product_uom.id,
                            'product_id':x.product_id.id,                               
                            'price_unit':invoice_line.price_unit,
                            'consolidate_price':x.price_unit,
                            'template_id':x.product_id.product_tmpl_id.id,
                        }])
        value['retur_beli_line'] = retur_beli_line
        # value['retur_barang_line'] = False
        return {'value':value}

    def has_retur_good(self, cr, uid, ids, *args):
        for retur in self.browse(cr, uid, ids):
            if not retur.retur_beli_line:
                return False
        return True

class dym_retur_beli_line(osv.osv):
    _name = "dym.retur.beli.line"
    
    def _amount_line(self, cr, uid, ids, prop, arg, context=None):
        res = {}
        tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            price = (line.price_unit * line.product_qty) - line.discount_amount
            taxes = tax_obj.compute_all(cr, uid, line.taxes_id, price, 1, line.product_id, line.retur_id.partner_id)
            res[line.id] = taxes['total']
        return res

    _columns = {
        'retur_id' : fields.many2one('dym.retur.beli','Retur Pembelian'),
        'lot_id': fields.related('consolidate_line_id', 'name', relation='stock.production.lot', type='many2one', string='Engine Number'),
        'consolidate_line_id': fields.many2one('consolidate.invoice.line', 'Consolidate Line'),
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line'),
        'name': fields.text('Description', required=True),
        'product_qty': fields.integer('Quantity', required=True),
        'discount_amount': fields.float(string='Discount Amount'),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', type='float', digits_compute= dp.get_precision('Account')),
        'taxes_id': fields.related('invoice_line_id', 'invoice_line_tax_id', relation='account.tax', type='many2many', string='Taxes'),
        'product_uom': fields.related('invoice_line_id', 'uos_id', relation='product.uom', type='many2one', string='UOM'),
        'product_id': fields.related('invoice_line_id', 'product_id', relation='product.product', type='many2one', string='Variant'),
        'price_unit': fields.float(string='Unit Price'),
        'template_id': fields.related('product_id', 'product_tmpl_id', relation='product.template', type='many2one', string='Type'),
    }

    def quantity_change(self, cr, uid, ids, quantity, id_product, consolidate_line_id, context=None):
        value = {}
        warning = {}
        product_id = self.pool.get('product.product').browse(cr, uid, id_product)
        consolidate_line = self.pool.get('consolidate.invoice.line').browse(cr, uid, consolidate_line_id)
        max_qty = consolidate_line.product_qty
        obj_retur_ids = self.pool.get('dym.retur.beli.line').search(cr, uid, [('retur_id.state','not in',('draft','cancel')),('consolidate_line_id','=',consolidate_line_id),('id','not in',ids)])
        retur_line_browse = self.pool.get('dym.retur.beli.line').browse(cr, uid, obj_retur_ids)
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
    _name = "dym.retur.barang.line"
    _columns = {
        'retur_id' : fields.many2one('dym.retur.beli','Retur Pembelian'),
        'product_id': fields.many2one('product.product', 'Product'),
        'product_qty': fields.integer('Quantity', required=True),
        'engine_number': fields.many2one('stock.production.lot', 'Engine Number'),
        'move_id': fields.many2one('stock.move', 'Move'),
        'beli_line_id': fields.many2one('dym.retur.beli.line', 'Beli Line ID'),
    }

class dym_stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'retur_beli_line_id':fields.many2one('dym.retur.beli.line',string="Retur Beli Line"),
    }
