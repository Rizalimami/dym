import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _
import pdb
from lxml import etree

class dym_purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    def _count_shipment(self):
        shipment_count = 0
        if self.asset == False and self.prepaid == False:
            shipment_count = len(self.picking_ids)
        self.shipment_count = shipment_count

    @api.depends('order_line.product_qty')
    def get_qty_asset(self):
        qty = 0
        for x in self.order_line :
            qty += x.product_qty
        self.qty_asset = qty
    
    @api.depends('order_line')
    def get_qty_receive(self):
        receive_ids = []
        if (self.asset == True or self.prepaid == True) and self.order_line:
            receive_ids = self.env['dym2.receive.asset'].search([('purchase_id','=',self.id)])
        self.receive_count = len(receive_ids)

    asset = fields.Boolean('Asset', readonly=True, states={'draft': [('readonly', False)]})
    prepaid = fields.Boolean('Prepaid', readonly=True, states={'draft': [('readonly', False)]})
    asset_receive = fields.Boolean('Asset Receive')
    asset_receive_qty = fields.Integer('QTY Asset')
    qty_asset = fields.Integer('Purchase Asset Qty',compute=get_qty_asset)
    receive_count = fields.Integer('Receiving Assets',compute=get_qty_receive)
    shipment_count = fields.Integer('Incoming Shipments',compute=_count_shipment)
            
    @api.cr_uid_ids_context
    def view_asset(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'dym_purchase_asset', 'receive_asset_action'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        obj_receive = self.pool.get('dym2.receive.asset')
        val = self.browse(cr, uid, ids)
        receive_ids = obj_receive.search(cr,uid,[('purchase_id','=',val.id)])
        action['context'] = {}
        if len(receive_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, receive_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'dym_purchase_asset', 'dym2_receive_asset_form_view')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = receive_ids and receive_ids[0] or False 
        return action


    @api.onchange('order_line')
    def change_order_line(self):
        if self.branch_id and len(self.order_line) > 0 and self.order_line[0].product_id:
            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('purchase.order').get_analytic_combi(self._cr, self._uid, self.branch_id.id, self.asset, self.prepaid, self.order_line, self.purchase_order_type_id.id, self.order_line[0].product_id.id)
            if analytic_1:
                self.analytic_1 = analytic_1
            self.analytic_2 = analytic_2
            self.analytic_3 = analytic_3
            self.analytic_4 = analytic_4

    @api.cr_uid_ids_context
    def onchange_asset_prepaid(self,cr,uid,ids,asset_prepaid,asset,prepaid,id_branch=False, order_line=False, purchase_order_type_id=False, context=None):
        value = {}

        if not id_branch:
            return False

        branch_config_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',id_branch)])
        if not branch_config_id:
            raise osv.except_osv(
                        _('Perhatian'),
                        _('Konfigurasi Cabang ini tidak ditemukan di Branch Config, silahkan setting dulu.'))
        branch_config = self.pool.get('dym.branch.config').browse(cr,uid,branch_config_id[0])

        if asset and branch_config.dym_po_journal_asset_id:
            value['journal_id'] = branch_config.dym_po_journal_asset_id.id
        if prepaid and branch_config.dym_po_journal_prepaid_id:
            value['journal_id'] = branch_config.dym_po_journal_prepaid_id.id

        if asset_prepaid == 'asset' and asset == True:
            value['prepaid'] = False
        if asset_prepaid == 'prepaid' and prepaid == True:
            value['asset'] = False
        if id_branch:
            analytic_1, analytic_2, analytic_3, analytic_4 = self.get_analytic_combi(cr, uid, id_branch, asset, prepaid, order_line, purchase_order_type_id)
            if analytic_1:
                value['analytic_1'] = analytic_1
            value['analytic_2'] = analytic_2
            value['analytic_3'] = analytic_3
            value['analytic_4'] = analytic_4
        return {'value':value}

class dym_purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'
    
    asset_receive = fields.Boolean('Asset Receive')
    asset_receive_qty = fields.Integer('QTY Asset',default=0)

class dym2_receive_asset(models.Model):
    _name = 'dym2.receive.asset'
    _description = 'Receive Asset'

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('done','Posted'),
        ('cancel','Cancelled')
    ]
        
    @api.depends('receive_line_ids.quantity')
    def get_qty_asset(self):
        qty = 0
        for x in self.receive_line_ids :
            qty += x.quantity
        self.qty_asset = qty

    name = fields.Char(string="Receive Asset No", default="#")
    purchase_id = fields.Many2one('purchase.order',string="Reference")
    date = fields.Date(string="Date",default=fields.Date.context_today)
    receive_line_ids = fields.One2many('dym2.receive.asset.line','receive_id')
    register_ids = fields.One2many('dym.transfer.asset','receive_id')    
    state = fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    branch_id = fields.Many2one(related="purchase_id.branch_id",string='Branch')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')     
    asset_receive = fields.Boolean('Asset Register')
    asset_receive_qty = fields.Integer('QTY Asset')
    qty_asset = fields.Integer('Receive Asset Qty',compute=get_qty_asset)
    consolidated = fields.Boolean('Receive Consolidated') 
    asset_prepaid = fields.Selection([('asset', 'Asset'),('prepaid','Prepaid')], string='Asset / Prepaid')
      
  
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(dym2_receive_asset, self).default_get(cr, uid, fields, context=context)
        purchase_ids = context.get('active_ids', [])
        active_model = context.get('active_model')
        if not purchase_ids or len(purchase_ids) != 1 or not context.get('active_model') or 'purchase.order' not in context.get('active_model'):
            return res
        assert active_model in ('purchase.order'), 'Bad context propagation'
        purchase_id = purchase_ids
        purchase = self.pool.get('purchase.order').browse(cr, uid, purchase_id, context=context)
        items = []
        for op in purchase.order_line:
            if int(op.product_qty) - int(op.asset_receive_qty) > 0:
                item = {
                    'purchase_line_id': op.id,
                    'product_id': op.product_id.id,
                    'price_unit': op.price_subtotal / op.product_qty,
                    'quantity': int(op.product_qty) - int(op.asset_receive_qty),
                    'description': op.name,
                }
                if op.name:
                    items.append(item)
        if purchase.asset == True:
            asset_prepaid = 'asset'
        if purchase.prepaid == True:
            asset_prepaid = 'prepaid'
        res.update(receive_line_ids=items)
        res.update(purchase_id=purchase.id)
        res.update(asset_prepaid=asset_prepaid)
        return res

    @api.multi
    def receive(self) :
        i = 0   
        order = self.purchase_id
        for x in self.receive_line_ids : 
            i += x.quantity
            available_receive_qty = x.purchase_line_id.product_qty - x.purchase_line_id.asset_receive_qty
            if available_receive_qty < x.quantity or x.quantity < 1 :
                raise osv.except_osv(('Perhatian !'), ("Asset/Prepaid %s yang bisa di receive tidak boleh lebih dari %s !")%(x.purchase_line_id.product_id.name, available_receive_qty))
            if x.purchase_line_id:
                asset_receive_qty = x.purchase_line_id.asset_receive_qty + x.quantity
                x.purchase_line_id.write({'asset_receive_qty':asset_receive_qty})
            if x.purchase_line_id.asset_receive_qty == x.purchase_line_id.product_qty :
                x.purchase_line_id.write({'asset_receive':True})                 
                        
        asset_receive_qty =  order.asset_receive_qty + i 
        order.write({'asset_receive_qty':asset_receive_qty})    
        if order.asset_receive_qty == order.qty_asset :
            order.write({'asset_receive':True})
            receiving_cancel = self.search([('purchase_id','=',order.id),('state','=','draft')])
            receiving_cancel.write({'state':'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})

        self.write({'date':datetime.today(),'state':'done','confirm_uid':self._uid,'confirm_date':datetime.now()})
        return True
    
    @api.model
    def create(self,values,context=None):
        vals = []
        values['name'] = '/'    
        receive_asset = super(dym2_receive_asset,self).create(values)    
        name = self.env['ir.sequence'].get_per_branch(receive_asset.purchase_id.branch_id.id, 'RAP', division='Umum') 
        receive_asset.write({'name':name})   
        return receive_asset
    
    @api.multi
    def onchange_asset_prepaid(self):
        value = {}
        value['purchase_id'] = False
        value['receive_line_ids'] = False
        return {'value':value}

    @api.multi
    def onchange_purchase(self,purchase_id):
        if purchase_id :
            items = []
            purchase_order = self.env['purchase.order'].browse([purchase_id])
            rekap_asset = {}
            for op in purchase_order.order_line :
                if int(op.product_qty) - int(op.asset_receive_qty) > 0:
                    items.append([0,0,{
                        'purchase_line_id': op.id,
                        'product_id': op.product_id.id,
                        'price_unit': op.price_subtotal / op.product_qty,
                        'quantity': int(op.product_qty) - int(op.asset_receive_qty),
                        'description': op.name,
                    }])
            return {'value':{'receive_line_ids': items}}
            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Receive Asset/Prepaid %s tidak bisa dihapus dalam status 'Posted' atau 'Cancel' !")%(item.name))
        return super(dym2_receive_asset, self).unlink(cr, uid, ids, context=context)     

    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()}, context=context)
        return True

class dym_transfer_asset_line(models.Model):
    _name = 'dym2.receive.asset.line'
    _rec_name = 'description'
    
    @api.depends('price_unit')
    def get_price_unit(self):
        for line in self:
            line.price_unit_show = line.price_unit 
        
    receive_id = fields.Many2one('dym2.receive.asset',string="Transfer No")
    product_id = fields.Many2one('product.product',string="Product")
    description = fields.Char(string='Description')
    purchase_line_id = fields.Many2one('purchase.order.line')
    quantity = fields.Integer(string="Qty",default=1)
    price_unit = fields.Float('Cost Price Before PPN')
    price_unit_show = fields.Float('Cost Price Before PPN',compute=get_price_unit,readonly=1,store=1)
    asset_receive = fields.Boolean('Asset Register')
    asset_receive_qty = fields.Integer('QTY Asset',default=0)
    consolidated_qty = fields.Integer(string="Cnsldted Qty")
            

class dym_transfer_asset(models.Model):
    _name = 'dym.transfer.asset'
    _description = 'Register Asset'
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('done','Posted'),
        ('cancel','Cancelled')
    ]
        
    name = fields.Char(string="Receipt Asset No", default="#")
    register_type = fields.Selection([('receive', 'Receive Asset/Prepaid'),('stock','Stock'),('payment_request','Payment Request'),('supplier_invoice','Supplier Invoice'),('cip','CIP')], string='Asset Source', default='receive')
    cip_branch_id = fields.Many2one('dym.branch',string="Branch")
    prepaid_branch_id = fields.Many2one(related="payment_request_id.branch_id",string='Branch')
    stock_branch_id = fields.Many2one('dym.branch',string="Branch")
    purchase_id = fields.Many2one(related="receive_id.purchase_id",string="Reference")
    receive_id = fields.Many2one('dym2.receive.asset',string="Reference")
    date = fields.Date(string="Date",default=fields.Date.context_today)
    transfer_ids = fields.One2many('dym.transfer.asset.line','transfer_id')
    transfer_ids2 = fields.One2many('dym.transfer.asset.line','transfer_id')
    transfer_ids3 = fields.One2many('dym.transfer.asset.line','transfer_id')
    transfer_ids4 = fields.One2many('dym.transfer.asset.line','transfer_id')
    asset_ids = fields.One2many('account.asset.asset','receive_id')    
    state = fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    branch_id = fields.Many2one(related="purchase_id.branch_id",string='Branch')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')            
    payment_request_id = fields.Many2one('account.voucher',string="Payment Request")
    invoice_id = fields.Many2one('account.invoice',string="Supplier Invoice")
                
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(dym_transfer_asset, self).default_get(cr, uid, fields, context=context)
        receive_ids = context.get('active_ids', [])
        active_model = context.get('active_model')
        if not receive_ids or len(receive_ids) != 1:
            return res
        assert active_model in ('dym2.receive.asset'), 'Bad context propagation'
        receive_id = receive_ids
        receive = self.pool.get('dym2.receive.asset').browse(cr, uid, receive_id, context=context)
        if receive.consolidated == False:
            raise osv.except_osv(('Perhatian !'), ("Receive Asset %s belum di consolidate!")%(receive.name))
        items = []
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan data analytic untuk company %s")%(company.name))
        for op in receive.receive_line_ids:
            for qty in range(int(op.asset_receive_qty),int(op.quantity)) :
                item = {
                    'receive_line_id': op.id,
                    'product_id': op.product_id.id,
                    'price_unit': op.price_unit,
                    'quantity': 1,
                    'description': op.description,
                    'analytic_1': level_1_ids[0],
                }
                items.append(item)
        res.update(transfer_ids=items)
        res.update(register_type='receive')
        res.update(receive_id=receive_id[0])
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        transfer_id = self.browse(cr, uid, ids, context=context)
        # <!-- 1 Register by receipt asset -->
        if transfer_id.register_type == 'receive':
            vals.pop('transfer_ids2',None)
            vals.pop('transfer_ids3',None)
            vals.pop('transfer_ids4',None)
        #<!-- 2 Register by stock -->
        elif transfer_id.register_type == 'stock':
            vals.pop('transfer_ids',None)
            vals.pop('transfer_ids3',None)
            vals.pop('transfer_ids4',None)
        #<!-- 2 Register by payment_request -->
        elif transfer_id.register_type == 'payment_request' or transfer_id.register_type == 'supplier_invoice':
            vals.pop('transfer_ids',None)
            vals.pop('transfer_ids2',None)
            vals.pop('transfer_ids4',None)
        #<!-- 2 Register by cip -->
        elif transfer_id.register_type == 'cip':
            vals.pop('transfer_ids',None)
            vals.pop('transfer_ids2',None)
            vals.pop('transfer_ids3',None)
        return super(dym_transfer_asset, self).write(cr, uid, ids, vals, context=context)

    @api.multi
    def create_asset(self) :
        asset_obj = self.env['account.asset.asset'] 
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        invoice = False
        order = self.purchase_id
        invoice_ids = False
        
        if self.register_type == 'supplier_invoice' and self.invoice_id:
            invoice_ids = self.invoice_id
        elif order.invoiced :
            invoice_ids = invoice_obj.search([
                ('origin','ilike',order.name)
            ])[0]
        i = 0   
        received_qty = {}
        for x in self.transfer_ids : 
            branch_config = self.env['dym.branch.config'].search([('branch_id','=',x.branch_id.id)])
            if not branch_config:
                raise osv.except_osv(
                    _('Perhatian'),
                    _('Jurnal register asset cabang belum dibuat, silahkan setting dulu.'))
                
            if not branch_config.journal_register_asset or not branch_config.journal_register_asset.default_credit_account_id:
                raise osv.except_osv(
                    _('Perhatian'),
                    _('Jurnal register asset cabang belum lengkap, silahkan setting dulu.'))
            if x.pr_line_id.prepaid_id and self.register_type == 'payment_request':
                raise osv.except_osv(('Perhatian !'), ("Asset %s sudah di register !")%(x.description + ' # ' + (order.name or self.payment_request_id.number or ''),))
            register_account_id = branch_config.journal_register_asset.default_credit_account_id.id
            if self.register_type == 'payment_request':
                register_account_id = x.pr_line_id.account_id.id
            elif self.register_type == 'supplier_invoice':
                register_account_id = x.invoice_line_id.account_id.id
            elif self.register_type == 'stock':
                register_account_id = x.product_id.categ_id.property_stock_valuation_account_id.id
            elif self.register_type == 'cip':
                register_account_id = x.asset_id.category_id.account_asset_id.id
            if self.register_type == 'stock':
                if x.product_id.categ_id.get_root_name() == 'Unit' and not x.stock_lot_id:
                    raise osv.except_osv(
                        _('Perhatian'),
                        _('Engine Number untuk produk unit %s harus diisi.')%(x.product_id.name))
                location_dest_search = self.env['stock.location'].search([('usage','=','internal'),('branch_id','=',self.stock_branch_id.id)])
                if not location_dest_search:
                    raise osv.except_osv(('Invalid action !'), ('Tidak ditemukan lokasi asset clearing di branch %s') % (self.stock_branch_id.name,))
                location_destination = location_dest_search[0]
                move_template = {
                    'name': x.product_id.name or '',
                    'categ_id': x.product_id.categ_id.id,
                    'product_uom': x.product_id.uom_id.id,
                    'product_id': x.product_id.id,
                    'product_uom_qty': 1,
                    'state': 'draft',
                    'location_id': x.stock_location_id.id,
                    'location_dest_id': location_destination.id,
                    'branch_id': self.stock_branch_id.id,
                    'price_unit': x.price_unit,
                    'origin': self.name
                }
                move = self.env['stock.move'].create(move_template)
                move.action_done()
                x.stock_lot_id.write({
                    'state':'asset',
                    'location_id':location_destination.id,
                    'branch_id':self.stock_branch_id.id,
                })
            i += 1
            method_end = False
            if x.method_end != '(None.None,)' :
                method_end = False
            if invoice_ids :
                invoice_ref = invoice_ids.id
                invoice_number = invoice_ids.number
                invoice_line_ids = invoice_line_obj.search([
                    ('invoice_id','=',invoice_ids.id),
                    ('product_id','=',x.product_id.id)
                ]) 
                if invoice_line_ids :
                    price = invoice_line_ids.price_subtotal / invoice_line_ids.quantity
            else :
                price = x.price_unit
                invoice_ref = False
                invoice_number = ''

            # Get Sequence
            ownership = {
                'HRGA' : 'GA',
                'IT' : 'IT',
                'Service': 'SV',
                'Sparepart & Accesories' : 'SV',
                'Sparepart & Accessories' : 'SV'
            }

            acccateg = {
                'Tanah' : '01',
                'Bangunan' : '02',
                'Bangunan Dalam Pelaksanaan' : '02',
                'Kendaraan' : '03',
                'Peralatan Kantor' : '04',
                'Peralatan Bengkel' : '05',
                'Instalasi Bengkel' : '06',
                'Perangkat Lunak' : '07',
            }

            prefix = 'ASSET/%s' % x.asset_owner.doc_code
            if not x.analytic_4.name in ownership:
                raise osv.except_osv(('Invalid action !'), ('Analytic name %s tidak terdaftar, hanya boleh HRGA/IT/Service saja!') % (x.analytic_4.name,))
            code_ownership = ownership[x.analytic_4.name]
            get_acccateg = x.asset_categ_id.account_asset_id.name
            code_acccateg = acccateg[get_acccateg[-(len(get_acccateg)-4):]]
            prefix += '/%s/%s' % (code_ownership,code_acccateg)

            if not x.asset_id :       
                asset_id = asset_obj.create({
                    'analytic_1' : x.analytic_1.id,
                    'analytic_2' : x.analytic_2.id,
                    'analytic_3' : x.analytic_3.id,
                    'analytic_4' : x.analytic_4.id,
                    'location_id' : x.location_id.id,
                    'branch_id' : x.branch_id.id,
                    'code' : self.env['ir.sequence'].get_sequence_asset_category(prefix),
                    'division' : 'Umum',
                    'product_id' : x.product_id.id,
                    'name': x.description + ' # ' + (order.name or self.payment_request_id.number or ''),
                    'partner_id': order.partner_id.id if order else self.payment_request_id.partner_id.id,
                    'category_id': x.asset_categ_id.id,
                    'purchase_date': x.document_date,
                    'purchase_value': x.price_unit,
                    'method': x.method,
                    'method_time': x.method_time or 'number',
                    'method_number': x.method_number,
                    'method_period': x.method_period, 
                    'prorata' : x.asset_categ_id.prorata,
                    'method_progress_factor': x.method_progress_factor,
                    'method_end': method_end,
                    'purchase_id':order.id if order else False,
                    'payment_request_id':self.payment_request_id.id,
                    'first_day_of_month':x.first_day_of_month,
                    'received' : True,
                    'receive_id' : self.id,
                    'responsible_id' : x.responsible_id.id if x.responsible_id else False,
                    'asset_user' : x.asset_user.id,
                    'asset_owner' : x.asset_owner.id,
                    'invoice_id':invoice_ref
                }) 
                asset_id.compute_depreciation_board()
                if x.open_asset:
                    asset_id.validate()        
                x.write({'asset_id':asset_id.id})
                if x.pr_line_id and self.register_type == 'payment_request':
                    x.pr_line_id.write({'prepaid_id': asset_id.id})
            elif x.asset_id :
                x.asset_id.write({
                    'analytic_1' : x.analytic_1.id,
                    'analytic_2' : x.analytic_2.id,
                    'analytic_3' : x.analytic_3.id,
                    'analytic_4' : x.analytic_4.id,
                    'location_id' : x.location_id.id,
                    'branch_id' : x.branch_id.id,
                    'division' : 'Umum',
                    'product_id' : x.product_id.id,
                    'name': x.description + ' # ' + (order.name or self.payment_request_id.number or ''),
                    'partner_id': order.partner_id.id if order else self.payment_request_id.partner_id.id,
                    'category_id': x.asset_categ_id.id,
                    'purchase_date': x.document_date,
                    'purchase_value': x.price_unit,
                    'method': x.method,
                    'method_time': x.method_time or 'number',
                    'method_number': x.method_number,
                    'method_period': x.method_period, 
                    'prorata' : x.asset_categ_id.prorata,
                    'method_progress_factor': x.method_progress_factor,
                    'method_end': method_end,
                    'purchase_id':order.id if order else False,
                    'payment_request_id':self.payment_request_id.id,
                    'first_day_of_month':x.first_day_of_month,
                    'received' : True,
                    'receive_id' : self.id,
                    'responsible_id' : x.responsible_id.id if x.responsible_id else False,
                    'asset_user' : x.asset_user.id,
                    'asset_owner' : x.asset_owner.id,
                    'invoice_id':invoice_ref
                }) 
                x.asset_id.compute_depreciation_board()   
                if x.asset_id.state == 'draft' and x.open_asset:
                    x.asset_id.validate() 
                if x.pr_line_id and self.register_type == 'payment_request':
                    x.pr_line_id.write({'prepaid_id': x.asset_id.id})
               
            if self.register_type == 'receive':                    
                available_register_qty = x.receive_line_id.quantity - x.receive_line_id.asset_receive_qty
                if available_register_qty < x.quantity :
                    raise osv.except_osv(('Perhatian !'), ("Asset %s yang bisa di register tidak boleh lebih dari %s !")%(x.receive_line_id.product_id.name, available_register_qty))
                if x.receive_line_id.id :
                    asset_receive_qty = x.receive_line_id.asset_receive_qty + 1               
                    x.receive_line_id.write({'asset_receive_qty':asset_receive_qty})
                if x.receive_line_id.asset_receive_qty == x.receive_line_id.quantity :
                    x.receive_line_id.write({'asset_receive':True})
            if self.register_type == 'supplier_invoice':                    
                available_register_qty = x.invoice_line_id.quantity - x.invoice_line_id.cip_count
                if available_register_qty < x.quantity :
                    raise osv.except_osv(('Perhatian !'), ("Asset %s yang bisa di register tidak boleh lebih dari %s !")%(x.invoice_line_id.product_id.name, available_register_qty))
                if x.invoice_line_id.id :
                    cip_count = x.invoice_line_id.cip_count + 1               
                    x.invoice_line_id.write({'cip_count':cip_count})

            '''
            DO NOT CREATE MOVE ON REGISTERING ASSET
            #create_move
            move_obj = self.env['account.move']
            
            if not x.asset_categ_id.account_asset_id:
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi Asset Account di master asset kategori %s belum lengkap!")%(x.asset_categ_id.name))

            move_journal = {
                'name': x.transfer_id.name,
                'ref': invoice_number or order.name or self.payment_request_id.number,
                'journal_id': branch_config.journal_register_asset.id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'transaction_id':self.id,
                'model':self.__class__.__name__,
            }
            
            move_line = [[0,False,{
                'name': x.description + ' # ' + (order.name or self.payment_request_id.number or ''),
                'account_id': x.asset_categ_id.account_asset_id.id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'debit': x.price_unit,
                'credit': 0.0,
                'branch_id': x.branch_id.id,
                'division': 'Umum',
                'partner_id': order.partner_id.id if order else self.payment_request_id.partner_id.id,
                'analytic_account_id' : x.analytic_4.id,
            }]]
            
            branch_order = order.branch_id.id if order else False
            if self.register_type == 'stock':
                branch_order = self.stock_branch_id.id
            elif self.register_type == 'payment_request':
                branch_order = self.prepaid_branch_id.id
            elif self.register_type == 'cip':
                branch_order = self.cip_branch_id.id
            elif self.register_type == 'supplier_invoice':
                branch_order = self.invoice_id.branch_id.id
            move_line.append([0,False,{
                'name': x.description + ' # ' + (order.name or self.payment_request_id.number or ''),
                'account_id': register_account_id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'debit': 0.0,
                'credit': x.price_unit,
                'branch_id': branch_order,
                'partner_id': order.partner_id.id if order else self.payment_request_id.partner_id.id,
                'division': 'Umum',
                'analytic_account_id' : x.analytic_4.id,
            }])
            move_journal['line_id'] = move_line
            create_journal = move_obj.create(move_journal)
            if branch_config.journal_register_asset.entry_posted:
                post_journal = create_journal.post()
        '''

        if self.register_type == 'receive':
            receive = self.receive_id
            if receive.consolidated == False:
                raise osv.except_osv(('Perhatian !'), ("Receive Asset/Prepaid %s belum di consolidate!")%(receive.name))
            asset_receive_qty =  receive.asset_receive_qty + i
            receive.write({'asset_receive_qty':asset_receive_qty})
            if receive.asset_receive_qty == receive.qty_asset :
                receive.write({'asset_receive':True})

        self.write({'date':datetime.today(),'state':'done','confirm_uid':self._uid,'confirm_date':datetime.now()})

        return True
        
    @api.model
    def create(self,values,context=None):
        vals = []
        values['name'] = '/' 
        receipt_asset = super(dym_transfer_asset,self).create(values)
        if receipt_asset.register_type == 'receive':
            branch = receipt_asset.receive_id.purchase_id.branch_id
        elif receipt_asset.register_type == 'stock':
            branch = receipt_asset.stock_branch_id
        elif receipt_asset.register_type == 'payment_request':
            branch = receipt_asset.prepaid_branch_id
        elif receipt_asset.register_type == 'supplier_invoice':
            branch = receipt_asset.invoice_id.branch_id
        elif receipt_asset.register_type == 'cip':
            branch = receipt_asset.cip_branch_id
        name = self.env['ir.sequence'].get_per_branch(branch.id, 'RAS', division='Umum')
        receipt_asset.write({'name':name})
        return receipt_asset
        
    @api.multi
    def onchange_receive(self,receive_id):
        if receive_id :
            items = []
            receive = self.env['dym2.receive.asset'].browse([receive_id])
            if receive.consolidated == False:
                Warning = {
                    'title': ('Perhatian !'),
                    'message': ("Receive Asset %s belum di consolidate !")%(receive.name),
                }
                res = {}
                res['warning'] = Warning
                res['value'] = {}
                res['value']['transfer_ids'] = False
                res['value']['transfer_ids2'] = False
                res['value']['transfer_ids3'] = False
                res['value']['transfer_ids4'] = False
                res['value']['asset_ids'] = False
                return res
            rekap_asset = {}
            branch = receive.purchase_id.branch_id
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(self._cr, self._uid, branch, 'Umum', False, 3, 'General')
            for op in receive.receive_line_ids:
                for qty in range(int(op.asset_receive_qty),int(op.quantity)) :
                    items.append([0,0,{
                        'receive_line_id': op.id,
                        'product_id': op.product_id.id,
                        'price_unit': op.price_unit,
                        'quantity': 1,
                        'description': op.description,
                        'analytic_1': analytic_1_general,
                        'analytic_2': analytic_2_general,
                        'analytic_3': analytic_3_general,
                        'register_type': self.register_type,
                    }])
            return {'value':{'transfer_ids': items}}

    @api.multi
    def onchange_payment_request(self,payment_request_id):
        if payment_request_id :
            items = []
            pr = self.env['account.voucher'].browse([payment_request_id])
            branch = pr.branch_id
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(self._cr, self._uid, branch, 'Umum', False, 3, 'General')
            for line in pr.line_dr_ids:
                if not line.prepaid_id:
                    items.append([0,0,{
                        'pr_line_id': line.id,
                        'price_unit': line.amount,
                        'quantity': 1,
                        'description': line.name,
                        'analytic_1': analytic_1_general,
                        'analytic_2': analytic_2_general,
                        'analytic_3': analytic_3_general,
                        'register_type': self.register_type,
                    }])
            return {'value':{'transfer_ids3': items}}

    @api.multi
    def onchange_supplier_invoice(self,invoice_id):
        if invoice_id :
            items = []
            inv = self.env['account.invoice'].browse([invoice_id])
            branch = inv.branch_id
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(self._cr, self._uid, branch, 'Umum', False, 3, 'General')
            for line in inv.invoice_line:
                if line.quantity > line.cip_count:
                    for qty in range(int(line.cip_count),int(line.quantity)) :
                        items.append([0,0,{
                            'invoice_line_id': line.id,
                            'price_unit': line.price_subtotal / line.quantity,
                            'quantity': 1,
                            'description': line.name,
                            'analytic_1': analytic_1_general,
                            'analytic_2': analytic_2_general,
                            'analytic_3': analytic_3_general,
                            'register_type': self.register_type,
                        }])
            return {'value':{'transfer_ids3': items}}

    @api.multi
    def onchange_cip_branch(self,cip_branch_id):
        if cip_branch_id :
            items = []
            return {'value':{'transfer_ids4': items}}

    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Receipt Asset %s tidak bisa dihapus dalam status 'Posted' atau 'Cancel' !")%(item.name))
        return super(dym_transfer_asset, self).unlink(cr, uid, ids, context=context)     

    @api.multi
    def onchange_register_type(self):
        value = {}
        value['transfer_ids'] = False
        value['transfer_ids2'] = False
        value['transfer_ids3'] = False
        value['transfer_ids4'] = False
        value['receive_id'] = False
        value['stock_branch_id'] = False
        value['payment_request_id'] = False
        value['cip_branch_id'] = False
        value['invoice_id'] = False
        return {'value':value}
            
class dym_transfer_asset_line(models.Model):
    _name = 'dym.transfer.asset.line'
    _rec_name = 'description'
    
    @api.depends('price_unit')
    def get_price_unit(self):
        for line in self:
            line.price_unit_show = line.price_unit 
        
    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    register_type = fields.Selection(related='transfer_id.register_type', string='Register Type')
    invoice_line_id = fields.Many2one('account.invoice.line',string="Invoice Line")
    stock_location_id = fields.Many2one('stock.location',string="Product Location")
    stock_lot_id = fields.Many2one('stock.production.lot',string="Engine Number")
    transfer_id = fields.Many2one('dym.transfer.asset',string="Transfer No")
    product_id = fields.Many2one('product.product',string="Product")
    asset_id = fields.Many2one('account.asset.asset',string="Asset",domain="[('categ_type','=','fixed'),('received','=',False),('receive_id','=',False)]")
    description = fields.Char(string='Description')
    asset_categ_id = fields.Many2one('account.asset.category', 'Asset Category', domain = [('type','=','fixed')])
    branch_id = fields.Many2one('dym.branch',string="User Branch")
    document_date = fields.Date(strinig="Document Date")
    prorata = fields.Boolean(string="Prorata", default=True)
    open_asset = fields.Boolean(string="Skip Draft")
    first_day_of_month = fields.Boolean(string='First Day of Month',help="First Day of Month ?",default=True)
    method_number = fields.Integer(string='Number of Depreciations',help="Jumlah depresiasi")
    method_period = fields.Integer(string='Period Length',help="Per berapa bulan ?",default=1)
    receive_line_id = fields.Many2one('dym2.receive.asset.line') 
    quantity = fields.Integer(string="Qty",default=1)
    price_unit = fields.Float('Cost Price Before PPN')
    method = fields.Selection([('linear','Linear'),('degressive','Degressive')])
    method_time = fields.Char('Time Method')
    method_progress_factor = fields.Float('Degressive Factor')
    method_end = fields.Date('Ending Date')
    price_unit_show = fields.Float('Cost Price Before PPN',compute=get_price_unit,readonly=1,store=1)
    responsible_id = fields.Many2one('hr.employee',string="Responsible")    
    location_id = fields.Many2one('stock.location',string="Asset Location",domain="[('branch_id','!=',False),('branch_id','=',branch_id),('usage','=','internal')]", required=True)
    analytic_1 = fields.Many2one('account.analytic.account', string='Account Analytic Company', default=_get_analytic_company)
    analytic_2 = fields.Many2one('account.analytic.account', 'Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center')
    asset_owner = fields.Many2one('dym.branch', 'Asset Owner')
    asset_user = fields.Many2one('hr.employee', 'User PIC')
    pr_line_id = fields.Many2one('account.voucher.line') 

    _sql_constraints = [('unique_transfer_asset_line', 'unique(transfer_id,asset_id)', 'Nomor Asset tidak boleh duplikat,silahkan periksa kembali data anda !'),]  

    @api.onchange('stock_location_id')
    def get_location_change(self):
        value = {}
        warning = {}
        domain = {}
        self.product_id = False
        self.stock_lot_id = False
        self.price_unit = 0
        self.price_unit_show = 0
        self.description = ''
        return {'domain':domain,'value':value}

    @api.onchange('stock_location_id','product_id')
    def get_domain_lot(self):
        value = {}
        warning = {}
        domain = {}
        if not self.stock_location_id:
            self.product_id = False
            self.stock_lot_id = False
            domain['product_id'] = [('id','=',0)]
            domain['stock_lot_id'] = [('id','=',0)]
            self.price_unit = 0
            self.price_unit_show = 0
            self.description = ''
            return {'domain':domain,'value':value}

        product_ids = []
        domain_search = [('qty', '>', 0.0),('location_id','=',self.stock_location_id.id),('reservation_id','=',False),('consolidated_date','!=',False),'|',('lot_id.state','=','stock'),'&',('lot_id','=',False),('product_category','!=','Unit')]
        quants = self.env['stock.quant'].search(domain_search)
        product_ids = [quant.product_id.id for quant in quants if quant.product_id.id not in product_ids]
        domain['product_id'] = [('id','in',product_ids)]
        if not self.product_id:
            self.stock_lot_id = False
            domain['stock_lot_id'] = [('id','=',0)]
            self.price_unit = 0
            self.price_unit_show = 0
            self.description = ''
            return {'domain':domain,'value':value}

        if self.transfer_id.register_type == 'stock':
            branch = self.stock_location_id.branch_id or self.stock_location_id.warehouse_id.branch_id
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(self._cr, self._uid, branch, 'Umum', False, 3, 'General')
            self.analytic_1 = analytic_1_general
            self.analytic_2 = analytic_2_general
            self.analytic_3 = analytic_3_general
        average_price = self.env['product.price.branch']._get_price(self.stock_location_id.warehouse_id.id, self.product_id.id)
        self.price_unit = average_price
        self.price_unit_show = average_price
        ids_serial_number = []
        if self.stock_location_id and self.product_id and self.product_id.categ_id.get_root_name() == 'Unit':
            ids_serial_number = self.env['dym.stock.packing.line'].get_lot_available_dealer(self.product_id.id, self.stock_location_id.id)
        domain['stock_lot_id'] = [('id','in',ids_serial_number)]
        self.stock_lot_id = False
        self.description = self.product_id.default_code or self.product_id.description or self.product_id.name
        return {'domain':domain,'value':value}

    @api.onchange('asset_categ_id')
    def onchange_categ(self):
        if self.asset_categ_id :
            self.method = self.asset_categ_id.method
            self.method_number = self.asset_categ_id.method_number
            self.method_time = self.asset_categ_id.method_time
            self.method_period = self.asset_categ_id.method_period
            self.method_progress_factor = self.asset_categ_id.method_progress_factor
            self.method_end = self.asset_categ_id.method_end
            self.prorata = self.asset_categ_id.prorata
            self.first_day_of_month = self.asset_categ_id.first_day_of_month

    @api.onchange('asset_id')
    def onchange_asset(self):
        if self.asset_id:
            if self.transfer_id.register_type != 'cip':
                self.asset_categ_id = self.asset_id.category_id.id 
            else:
                self.asset_categ_id = False
                self.method = False
                self.method_time = False
                self.method_number = False
                self.method_period = False 
                self.prorata = False
                self.method_progress_factor = False
                self.method_end = False
                self.first_day_of_month = False
                self.purchase_id = False
                self.pr_line_id = False
            self.onchange_categ()                        
            self.branch_id = self.asset_id.branch_id.id 
            self.location_id = self.asset_id.location_id.id 
            self.document_date = self.asset_id.purchase_date
            self.quantity = 1
            self.description = self.asset_id.name
            self.analytic_1 = self.asset_id.analytic_1.id or self._get_analytic_company()
            self.analytic_2 = self.asset_id.analytic_2.id
            self.analytic_3 = self.asset_id.analytic_3.id
            self.analytic_4 = self.asset_id.analytic_4.id
            self.product_id = self.asset_id.product_id.id
            self.price_unit = self.asset_id.purchase_value
            self.price_unit_show = self.asset_id.purchase_value
            self.responsible_id = self.asset_id.responsible_id.id
            self.asset_user = self.asset_id.asset_user.id,
            self.asset_owner = self.asset_id.asset_owner.id,

    @api.onchange('branch_id')
    def onchange_branch(self):
        self.register_type = self.transfer_id.register_type
        self.location_id = False