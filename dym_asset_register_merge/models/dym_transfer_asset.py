import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _
import pdb
from lxml import etree

class dym_transfer_asset(models.Model):
    _inherit = 'dym.transfer.asset'
    _desctiption = 'Transfer Asset'

    merge_asset = fields.Boolean('Merge Asset?')
    merged_asset_id = fields.Many2one('account.asset.asset',string="Asset",domain="[('categ_type','=','fixed'),('received','=',False),('receive_id','=',False)]")

    def do_create_asset(self):
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
                'Service': 'SV'
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

    @api.model
    def do_create_merge_asset(self):

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

        created_asset = False
        values = False
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
                'Service': 'SV'
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
            code_ownership = ownership[x.analytic_4.name]
            get_acccateg = x.asset_categ_id.account_asset_id.name
            code_acccateg = acccateg[get_acccateg[-(len(get_acccateg)-4):]]
            prefix += '/%s/%s' % (code_ownership,code_acccateg)

            if not created_asset:
                if not x.asset_id:
                    created_asset_id = asset_obj.create({
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
                        'purchase_value': sum([z.price_unit for z in self.transfer_ids]),
                        'real_purchase_value': sum([z.price_unit for z in self.transfer_ids]),
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
                    created_asset_id.compute_depreciation_board()
                    if x.open_asset:
                        created_asset_id.validate()
                    created_asset = created_asset_id
                else:
                    x.asset_id.category_id = x.asset_categ_id.id
                    created_asset = x.asset_id
            else:
                if not x.asset_id:
                    x.asset_id = created_asset.id
                else:
                    x.asset_id.category_id = x.asset_categ_id.id

            total_value = sum([z.price_unit for z in self.transfer_ids])
            if created_asset.real_purchase_value != total_value:
                created_asset.real_purchase_value = total_value

            if x.pr_line_id and self.register_type == 'payment_request':
                x.pr_line_id.write({'prepaid_id': created_asset.id})
               
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
                    
        if not self.asset_ids and created_asset:
            self.asset_ids = [created_asset.id]

    @api.multi
    def create_asset(self) :
        if self.merge_asset:
            self.do_create_merge_asset()
        else:
            self.do_create_asset()

        if self.register_type == 'receive':
            receive = self.receive_id
            if receive.consolidated == False:
                raise osv.except_osv(('Perhatian !'), ("Receive Asset/Prepaid %s belum di consolidate!")%(receive.name))
            asset_receive_qty =  receive.asset_receive_qty
            receive.write({'asset_receive_qty':asset_receive_qty})
            if receive.asset_receive_qty == receive.qty_asset :
                receive.write({'asset_receive':True})

        self.write({'date':datetime.today(),'state':'done','confirm_uid':self._uid,'confirm_date':datetime.now()})

        return True