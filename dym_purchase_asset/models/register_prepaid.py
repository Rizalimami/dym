import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _
import pdb
from lxml import etree

class dym_branch_config(models.Model):
    _inherit = 'dym.branch.config'

    journal_register_asset = fields.Many2one('account.journal', string='Journal Register Asset',help='Journal Register Asset')
    journal_register_prepaid = fields.Many2one('account.journal', string='Journal Register Prepaid',help='Journal Register Prepaid')

class dym2_register_prepaid(models.Model):
    _name = 'dym2.register.prepaid'
    _desctiption = 'Transfer Asset'
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('done','Posted'),
        ('cancel','Cancelled')
    ]
        
    name = fields.Char(string="Register Prepaid No", default="#")
    register_type = fields.Selection([('receive', 'Receive Asset/Prepaid'),('payment_request','Payment Request')], string='Prepaid Source', default='receive')
    payment_request_id = fields.Many2one('account.voucher',string="Payment Request")
    prepaid_branch_id = fields.Many2one(related="payment_request_id.branch_id",string='Branch')
    purchase_id = fields.Many2one(related="receive_id.purchase_id",string="Reference")
    receive_id = fields.Many2one('dym2.receive.asset',string="Reference")
    date = fields.Date(string="Date",default=fields.Date.context_today)
    transfer_ids = fields.One2many('dym2.register.prepaid.line','transfer_id')
    prepaid_ids = fields.One2many('account.asset.asset','register_prepaid_id')    
    state = fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    branch_id = fields.Many2one(related="payment_request_id.branch_id",string='Branch')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')            

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(dym2_register_prepaid, self).default_get(cr, uid, fields, context=context)
        receive_ids = context.get('active_ids', [])
        active_model = context.get('active_model')
        if not receive_ids or len(receive_ids) != 1:
            return res
        assert active_model in ('dym2.receive.asset'), 'Bad context propagation'
        receive_id = receive_ids
        receive = self.pool.get('dym2.receive.asset').browse(cr, uid, receive_id, context=context)
        # if receive.consolidated == False:
        #     raise osv.except_osv(('Perhatian !'), ("Receive Asset %s belum di consolidate!")%(receive.name))
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

    @api.multi
    def create_prepaid(self) :
        prepaid_obj = self.env['account.asset.asset'] 
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        invoice = False
        order = self.purchase_id
        invoice_ids = False
      
        if order.invoiced :
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
                    _('Jurnal register prepaid cabang belum dibuat, silahkan setting dulu.'))
            if not branch_config.journal_register_prepaid or not branch_config.journal_register_prepaid.default_credit_account_id:
                raise osv.except_osv(
                    _('Perhatian'),
                    _('Jurnal register prepaid cabang belum lengkap, silahkan setting dulu.'))
            i += 1
            if x.pr_line_id.prepaid_id and self.register_type == 'payment_request':
                raise osv.except_osv(('Perhatian !'), ("Prepaid %s sudah di register !")%(x.description + ' # ' + (order.name or self.payment_request_id.number or '')))
            register_account_id = branch_config.journal_register_prepaid.default_credit_account_id.id
            if self.register_type == 'payment_request':
                register_account_id = x.pr_line_id.account_id.id
            method_end = False
            if x.method_end != '(None.None,)':
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
            prefix = 'PREPAID/%s' % x.asset_owner.doc_code
            if not x.prepaid_id :
                prepaid_id = prepaid_obj.create({
                   'analytic_1' : x.analytic_1.id,
                   'analytic_2' : x.analytic_2.id,
                   'analytic_3' : x.analytic_3.id,
                   'analytic_4' : x.analytic_4.id,
                   'branch_id' : x.branch_id.id,
                   'code' : self.env['ir.sequence'].get_sequence_asset_category(prefix),
                   'division' : 'Umum',
                   'name': x.description + ' # ' + (order.name or self.payment_request_id.number or ''),
                   'partner_id': order.partner_id.id if order else self.payment_request_id.partner_id.id,
                   'category_id': x.asset_categ_id.id,
                   'purchase_date': x.document_date,
                   'purchase_value': x.price_unit,
                   'method': x.method,
                   'method_time': x.method_time or 'number',
                   'method_number': x.method_number,
                   'method_period': x.method_period, 
                   'prorata' : x.prorata,
                   'method_progress_factor': x.method_progress_factor,
                   'method_end': method_end,
                   'purchase_id':order.id if order else False,
                   'payment_request_id':self.payment_request_id.id,
                   'first_day_of_month':x.first_day_of_month,
                   'received' : True,
                   'register_prepaid_id' : self.id,
                   'responsible_id' : x.responsible_id.id if x.responsible_id else False,
                   'asset_user' : x.asset_user.id,
                   'asset_owner' : x.asset_owner.id,
                   'invoice_id':invoice_ref
                   })
                prepaid_id.compute_depreciation_board()
                if x.open_asset:
                    prepaid_id.validate()        
                x.write({'prepaid_id':prepaid_id.id})
                if x.pr_line_id and self.register_type == 'payment_request':
                    x.pr_line_id.write({'prepaid_id': prepaid_id.id})
            elif x.prepaid_id :
                x.prepaid_id.write({
                   'analytic_1' : x.analytic_1.id,
                   'analytic_2' : x.analytic_2.id,
                   'analytic_3' : x.analytic_3.id,
                   'analytic_4' : x.analytic_4.id,
                   'branch_id' : x.branch_id.id,
                   'division' : 'Umum',
                   'name': x.description + ' # ' + (order.name or self.payment_request_id.number or ''),
                   'partner_id': order.partner_id.id if order else self.payment_request_id.partner_id.id,
                   'category_id': x.asset_categ_id.id,
                   'purchase_date': x.document_date,
                   'purchase_value': x.price_unit,
                   'method': x.method,
                   'method_time': x.method_time or 'number',
                   'method_number': x.method_number,
                   'method_period': x.method_period, 
                   'prorata' : x.prorata,
                   'method_progress_factor': x.method_progress_factor,
                   'method_end': method_end,
                   'purchase_id':order.id if order else False,
                   'payment_request_id':self.payment_request_id.id,
                   'first_day_of_month':x.first_day_of_month,
                   'received' : True,
                   'register_prepaid_id' : self.id,
                   'responsible_id' : x.responsible_id.id if x.responsible_id else False,
                   'asset_user' : x.asset_user.id,
                   'asset_owner' : x.asset_owner.id,
                   'invoice_id':invoice_ref
                   })
                x.prepaid_id.compute_depreciation_board()   
                if x.prepaid_id.state == 'draft' and x.open_asset:
                    x.prepaid_id.validate() 
                if x.pr_line_id and self.register_type == 'payment_request':
                    x.pr_line_id.write({'prepaid_id': x.prepaid_id.id})
                                   
            if self.register_type == 'receive':                    
                available_register_qty = x.receive_line_id.quantity - x.receive_line_id.asset_receive_qty
                if available_register_qty < x.quantity :
                    raise osv.except_osv(('Perhatian !'), ("Prepaid %s yang bisa di register tidak boleh lebih dari %s !")%(x.receive_line_id.product_id.name, available_register_qty))
                if x.receive_line_id.id :
                    asset_receive_qty = x.receive_line_id.asset_receive_qty + 1
                    x.receive_line_id.write({'asset_receive_qty':asset_receive_qty})
                if x.receive_line_id.asset_receive_qty == x.receive_line_id.quantity :
                    x.receive_line_id.write({'asset_receive':True})
            
            '''
            DO NOT CREATE MOVE ON REGISTERING PREPAID
            #create_move
            move_obj = self.env['account.move']
            if not x.asset_categ_id.account_asset_id:
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi Asset Account di master asset kategori %s belum lengkap!")%(x.asset_categ_id.name))
            move_journal = {
                'name': x.transfer_id.name,
                'ref': invoice_number or order.name or self.payment_request_id.number,
                'journal_id': branch_config.journal_register_prepaid.id,
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
            if self.register_type == 'payment_request':
                branch_order = self.prepaid_branch_id.id
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
            if branch_config.journal_register_prepaid.entry_posted:
                post_journal = create_journal.post()
            '''

        if self.register_type == 'receive':
            receive = self.receive_id
            # if receive.consolidated == False:
            #     raise osv.except_osv(('Perhatian !'), ("Receive Asset/Prepaid %s belum di consolidate!")%(receive.name))
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
        # values['name'] = self.env['ir.sequence'].get_sequence('REGA')     
        reg_prepaid = super(dym2_register_prepaid,self).create(values)
        if reg_prepaid.register_type == 'receive':
            branch = reg_prepaid.receive_id.purchase_id.branch_id
        elif reg_prepaid.register_type == 'payment_request':
            branch = reg_prepaid.prepaid_branch_id
        name = self.env['ir.sequence'].get_per_branch(branch.id, 'RPR', division='Umum') 
        reg_prepaid.write({'name':name})
        return reg_prepaid

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
                res['value']['asset_ids'] = False
                return res
            rekap_asset = {}
            company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
            level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
            if not level_1_ids:
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan data analytic untuk company %s")%(company.name))
            for op in receive.receive_line_ids:
                for qty in range(int(op.asset_receive_qty),int(op.quantity)) :
                    items.append([0,0,{
                        'receive_line_id': op.id,
                        'product_id': op.product_id.id,
                        'price_unit': op.price_unit,
                        'quantity': 1,
                        'description': op.description,
                        'analytic_1': level_1_ids[0],
                        'register_type': self.register_type,
                    }])
            return {'value':{'transfer_ids': items}}

    @api.multi
    def onchange_payment_request(self,payment_request_id):
        if payment_request_id :
            items = []
            pr = self.env['account.voucher'].browse([payment_request_id])
            company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
            level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
            if not level_1_ids:
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan data analytic untuk company %s")%(company.name))
            for line in pr.line_dr_ids:
                if not line.prepaid_id:
                    items.append([0,0,{
                        'pr_line_id': line.id,
                        'price_unit': line.amount,
                        'quantity': 1,
                        'description': line.name,
                        'analytic_1': line.analytic_1.id or level_1_ids[0],
                        'analytic_2': line.analytic_2.id,
                        'analytic_3': line.analytic_3.id,
                        'analytic_4': line.account_analytic_id.id,
                        'register_type': self.register_type,
                    }])
            return {'value':{'transfer_ids': items}}
            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Register prepaid %s tidak bisa dihapus dalam status 'Posted' atau 'Cancel' !")%(item.name))
        return super(dym2_register_prepaid, self).unlink(cr, uid, ids, context=context)     

    @api.multi
    def onchange_register_type(self):
        value = {}
        value['transfer_ids'] = False
        value['transfer_ids2'] = False
        value['transfer_ids3'] = False
        value['transfer_ids4'] = False
        value['receive_id'] = False
        value['invoice_id'] = False
        value['stock_branch_id'] = False
        value['payment_request_id'] = False
        value['cip_branch_id'] = False
        return {'value':value}

class dym_transfer_asset_line(models.Model):
    _name = 'dym2.register.prepaid.line'
    _rec_name = 'description'
    
    @api.depends('price_unit')
    def get_price_unit(self):
        for line in self:
            line.price_unit_show = line.price_unit 
        
    def get_prorata(self):
        for line in self:
            line.prorata = line.asset_categ_id.prorata

    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    register_type = fields.Selection(related='transfer_id.register_type', string='Register Type')
    receive_line_id = fields.Many2one('dym2.receive.asset.line') 
    transfer_id = fields.Many2one('dym2.register.prepaid',string="Transfer No")
    product_id = fields.Many2one('product.product',string="Product")
    prepaid_id = fields.Many2one('account.asset.asset',string="Prepaid",domain="[('categ_type','=','prepaid'),('received','=',False),('register_prepaid_id','=',False)]")
    description = fields.Char(string='Description')
    asset_categ_id = fields.Many2one('account.asset.category', 'Prepaid Category', domain = [('type','=','prepaid')])
    branch_id = fields.Many2one('dym.branch',string="User Branch")
    document_date = fields.Date(strinig="Document Date")
    prorata = fields.Boolean(string="Prorata",compute=get_prorata,store=1)
    open_asset = fields.Boolean(string="Skip Draft")
    first_day_of_month = fields.Boolean(string='First Day of Month',help="First Day of Month ?",default=True)
    method_number = fields.Integer(string='Number of Depreciations',help="Jumlah depresiasi")
    method_period = fields.Integer(string='Period Length',help="Per berapa bulan ?",default=1)
    pr_line_id = fields.Many2one('account.voucher.line') 
    quantity = fields.Integer(string="Qty",default=1)
    price_unit = fields.Float('Cost Price Before PPN')
    method = fields.Selection([('linear','Linear'),('degressive','Degressive')])
    method_time = fields.Char('Time Method')
    method_progress_factor = fields.Float('Degressive Factor')
    method_end = fields.Date('Ending Date')
    price_unit_show = fields.Float('Cost Price Before PPN',compute=get_price_unit,readonly=1,store=1)
    responsible_id = fields.Many2one('hr.employee',string="Responsible")
    analytic_1 = fields.Many2one('account.analytic.account', string='Account Analytic Company', default=_get_analytic_company)
    analytic_2 = fields.Many2one('account.analytic.account', 'Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center')
    asset_owner = fields.Many2one('dym.branch', 'Asset Owner')
    asset_user = fields.Many2one('hr.employee', 'User PIC')

    _sql_constraints = [('unique_transfer_asset_line', 'unique(transfer_id,prepaid_id)', 'Nomor Asset tidak boleh duplikat,silahkan periksa kembali data anda !'),]  
    
    @api.onchange('asset_categ_id')
    def onchange_categ(self):
        if self.asset_categ_id :
            self.method = self.asset_categ_id.method
            self.method_number = self.asset_categ_id.method_number
            self.method_time = self.asset_categ_id.method_time
            self.method_period = self.asset_categ_id.method_period
            self.method_progress_factor = self.asset_categ_id.method_progress_factor
            self.method_end = self.asset_categ_id.method_end
            self.first_day_of_month = self.asset_categ_id.first_day_of_month

    @api.onchange('prepaid_id')
    def onchange_asset(self):
        if self.prepaid_id :
            self.asset_categ_id = self.prepaid_id.category_id.id  
            self.onchange_categ()                        
            self.branch_id = self.prepaid_id.branch_id.id 
            self.document_date = self.prepaid_id.purchase_date
