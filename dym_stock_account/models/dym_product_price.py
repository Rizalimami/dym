##############################################################################
#
#    Sipo Cloud Service
#    Copyright (C) 2015.
#
##############################################################################

from openerp.osv import osv
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import models,fields, exceptions, api, _
from datetime import datetime


class dym_product_price_branch(models.Model):
    _name = 'product.price.branch'
    _rec_name = 'product_id'
    _order = "warehouse_id asc, product_id asc"

    cost =  fields.Float(string='Cost')
    product_id = fields.Many2one('product.product','Product', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    category_id = fields.Many2one(related='product_id.categ_id', string='Product Category', store=True)

    def create(self, cr, uid, vals, context=None):
        new_id = super(dym_product_price_branch, self).create(cr, uid, vals, context=context)
        product_id = self.pool.get('product.product').browse(cr, uid, [vals.get('product_id')], context=context)[0].id
        self.pool.get('product.product').write(cr, uid, product_id, {'cost_id': new_id})
        history_id = self.pool.get('product.price.history').search(cr, uid, [('model_name','=',context.get('model_name')),('trans_id','=',context.get('trans_id')),('warehouse_id','=',vals.get('warehouse_id')),('product_id','=',vals.get('product_id'))])
        if not history_id:
            self.pool.get('product.price.history').create(cr, uid, {
                'warehouse_id': vals.get('warehouse_id'),
                'product_id': vals.get('product_id'),
                'cost': vals.get('cost'),
                'product_template_id': context.get('product_template_id'),
                'stock_qty': context.get('stock_qty'),
                'old_cost_price': context.get('old_cost_price'),
                'trans_qty': context.get('trans_qty'),
                'trans_price': context.get('trans_price'),
                'origin': context.get('origin'),
                'transaction_type': context.get('transaction_type'),
                'model_name': context.get('model_name'),
                'trans_id': context.get('trans_id'),
            },context=context)
        else:
            history = self.pool.get('product.price.history').browse(cr, uid, history_id)
            new_cost_price = ((history.old_cost_price * history.stock_qty) + (history.trans_price * (history.trans_qty + context.get('trans_qty')))) / (history.stock_qty + history.trans_qty + context.get('trans_qty'))
            history.write({'trans_qty': history.trans_qty + context.get('trans_qty'), 'cost': new_cost_price})
            vals['cost'] = new_cost_price
        return True
                

    def write(self, cr, uid, ids, vals, context=None):
        res = super(dym_product_price_branch, self).write(cr, uid, ids, vals, context=context)
        if 'cost' in vals and 'warehouse_id' in vals and 'product_id' in vals:
            product_price = self.browse(cr, uid, ids)
            history_id = self.pool.get('product.price.history').search(cr, uid, [('model_name','=',context.get('model_name')),('trans_id','=',context.get('trans_id')),('warehouse_id','=',vals.get('warehouse_id')),('product_id','=',vals.get('product_id'))])
            if not history_id:
                self.pool.get('product.price.history').create(cr, uid, {
                    'warehouse_id': vals.get('warehouse_id'),
                    'product_id': vals.get('product_id'),
                    'cost': vals.get('cost'),
                    'product_template_id': context.get('product_template_id'),
                    'stock_qty': context.get('stock_qty'),
                    'old_cost_price': context.get('old_cost_price'),
                    'trans_qty': context.get('trans_qty'),
                    'trans_price': context.get('trans_price'),
                    'origin': context.get('origin'),
                    'transaction_type': context.get('transaction_type'),
                    'model_name': context.get('model_name'),
                    'trans_id': context.get('trans_id'),
                }, context=context)
            else:
                history = self.pool.get('product.price.history').browse(cr, uid, history_id)
                new_cost_price = ((history.old_cost_price * history.stock_qty) + (history.trans_price * (history.trans_qty + context.get('trans_qty')))) / (history.stock_qty + history.trans_qty + context.get('trans_qty'))
                history.write({'trans_qty': history.trans_qty + context.get('trans_qty'), 'cost': new_cost_price})
                vals['cost'] = new_cost_price
        return res
    
    def _get_price(self, cr, uid, warehouse_id, product_id):
        cost = 0.0
        price_id = self.search(cr, uid, [('warehouse_id','=', warehouse_id), ('product_id','=', product_id)])
        if price_id:
            price_obj = self.browse(cr, uid, price_id[0])
            if price_obj:
                cost = price_obj.cost
        return cost

class dym_product_price_history(models.Model):
    """
    Keep track of the ``product.product`` cost prices as they are changed.
    """

    _inherit = 'product.price.history'
    _order = 'date desc,warehouse_id asc'


    def _get_default_branch(self, cr, uid, context=None):
        user_browse = self.pool['res.users'].browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids

    @api.one
    @api.depends('trans_qty','stock_qty')
    def _compute_new_qty(self):
        self.new_qty = self.stock_qty + self.trans_qty

    date = fields.Datetime(string='Date', required=False, readonly=True)
    origin = fields.Char(string='Source Document')
    trans_price = fields.Float(string='Trans Cost Price', required=True)
    old_cost_price = fields.Float(string='Beginning Cost Price', required=True)
    cost = fields.Float(string='Ending Cost Price', required=True)
    trans_qty = fields.Float(string='Trans Unit qty', required=True)
    stock_qty = fields.Float(string='Beginning qty', required=True)
    new_qty = fields.Float(string='Ending qty', compute=_compute_new_qty, store=True)
    warehouse_id = fields.Many2one('stock.warehouse', required=False)
    product_id = fields.Many2one('product.product', 'Product', required=False)
    product_template_id = fields.Many2one(related='product_id.product_tmpl_id', string='Product Template', required=False, readonly=True, store=False)
    transaction_type = fields.Selection([('in','In'),('out','Out')],'Transaction Type')
    model_name = fields.Char('Model Name')
    trans_id = fields.Integer('Transaction Id')

    def _report_xls_cost_price_history_fields(self, cr, uid, context=None):
        return [

            'no',\
            'cabang_code',\
            'cabang_nama',\
            'category',\
            'product_code',\
            'product_name',\
            'lokasi',\
            'origin',\
            'document_movement',\
            'status',\
            'qty_awal',\
            'cost_awal',\
            'qty_trans',\
            'cost_trans',\
            'qty_akhir',\
            'cost_akhir',\
        ]

    @api.model
    def create(self,vals,context=None):
        vals['date'] = datetime.now() 
        res =  super(dym_product_price_history, self).create(vals)  
        return res

class ProductProduct(models.Model):
    _inherit = 'product.product'

    cost_id = fields.Many2one('product.price.branch')
    standard_price = fields.Float(related='cost_id.cost', string='Cost Price', store=False)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _set_standard_price(self, cr, uid, product_tmpl_id, value, context=None):
        # FUNGSI BAWAAN ODOO INI TIDAK DIGUNAKAN LAGI KARENA KONSEP COSTING YANG BERBEDA  (HZ)
        pass

class ProductCostAdjustment(models.Model):
    _name = 'product.cost.adjustment'


    name = fields.Char('Name')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division')
    cost_history_id = fields.Many2one('product.price.history')
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    cost_price = fields.Float(string='Cost Price', required=True)
    current_cost_price = fields.Float(related='cost_history_id.old_cost_price', string='Current Cost Price')
    state = fields.Selection([('draft','Draft'), ('waiting_for_approval', 'Waiting for Approval'), ('approved','Approved'), ('done','Done'), ('rejected', 'Rejected')], 'State', default='draft')
    date = fields.Date(string='Date', readonly=True)
    account_move_id = fields.Many2one('account.move',string='Journal Entries', readonly=True)
    approved_date = fields.Datetime(string='Approved Date')
    approval_ids = fields.One2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    approval_state = fields.Selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True, default='b')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')

    @api.model
    def create(self,vals,context=None):
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'COSTADJ', division=False) 
        vals['date'] = datetime.now() 
        res =  super(ProductCostAdjustment, self).create(vals)  
        return res

    def confirm(self, cr, uid, ids, context=None):
        product_adj = self.browse(cr, uid, ids, context=None)
        price_branch_id = self.pool.get('product.price.branch').search(cr, uid, [('product_id', '=', product_adj.product_id.id), ('warehouse_id', '=', product_adj.warehouse_id.id)], context=None)
        product_avail = self.pool.get('stock.quant')._get_stock_product_branch(cr, uid, product_adj.warehouse_id.id, product_adj.product_id.id)

        # if len(price_branch_id) == 0 and product_avail <= 0:
        #     raise osv.except_osv(_('Warning !'), _("Anda tidak dapat melakukan update cost price, karena stock untuk barang ini tidak ada."))
        current_cost_price = self.pool.get('product.price.branch').browse(cr, uid, price_branch_id, context=None).cost

        branch = product_adj.branch_id.id
        branch_config_ids = self.pool.get('dym.branch.config').search(cr, uid, [('branch_id','=',branch)], context=None)
        branch_config = self.pool.get('dym.branch.config').browse(cr, uid, branch_config_ids, context=None)
        amount = (product_adj.cost_price - current_cost_price) * product_avail
        if amount < 0:
            amount = amount * -1
        date = product_adj.date
        root_product_category = self.pool.get('product.category').get_root_name(cr, uid, [product_adj.product_id.categ_id.id])
        journal_id = branch_config.cost_adjustment_journal_id
        period_id = self.pool.get('account.period').find(cr, uid, dt=product_adj.date, context=None)
        if root_product_category == 'Unit':
            division = 'Unit'
        elif root_product_category == 'Sparepart':
            division = 'Sparepart'
        else:
            division = 'Umum'
        context = {
                'stock_qty': product_avail,
                'old_cost_price': current_cost_price,
                'trans_qty': 0,
                'trans_price': product_adj.cost_price,
                'origin': '/',
                'product_template_id': product_adj.product_id.product_tmpl_id.id,
            }
        vals = {
            'warehouse_id': product_adj.warehouse_id.id,
            'product_id': product_adj.product_id.id,
            'cost': product_adj.cost_price
        }
        if product_avail > 0:
            account_move = self.pool.get('account.move').create(cr, uid, {
                'name': product_adj.name or '/',
                'journal_id': journal_id.id,
                'date': date,
                'period_id': period_id[0],
                'transaction_id': product_adj.id,
                'model': product_adj.__class__.__name__,
            })
            cost_center = ''
            if product_adj.product_id.categ_id.get_root_name() in ('Unit','Extras'):
                cost_center = 'Sales'
            elif product_adj.product_id.categ_id.get_root_name() == 'Sparepart':
                cost_center = 'Sparepart_Accesories'
            elif product_adj.product_id.categ_id.get_root_name() =='Umum':
                cost_center = 'General'
            elif product_adj.product_id.categ_id.get_root_name() =='Service':
                cost_center = 'Service'
            else:
                raise osv.except_osv(('Attention!'),('Analytic Account tidak ditemukan mohon hubungi sistem administrator anda. %s!') % (product_adj.product_id.name))
            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, product_adj.branch_id, '', product_adj.product_id.categ_id, 4, cost_center)
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, product_adj.branch_id, '', product_adj.product_id.categ_id, 4, 'General')
            if product_adj.cost_price > current_cost_price:
                # LOOPING 2 KALI UNTUK MEMBUAT JOURNAL ENTRIES LINE {DEBIT & CREDIT} (HZ)
                x = 0
                while x < 2:
                    if x == 0:
                        self.pool.get('account.move.line').create(cr, uid, {
                            'branch': branch,
                            'division': division,
                            'name': product_adj.name or '/',
                            'debit': amount,
                            'credit': 0.0,
                            'account_id': product_adj.product_id.categ_id.property_stock_valuation_account_id.id,
                            'move_id': account_move,
                            'journal_id': journal_id.id,
                            'period_id': period_id[0],
                            'date': date,
                            'analytic_account_id' : analytic_4_general,
                            })
                        x +=1
                    else:
                        self.pool.get('account.move.line').create(cr, uid, {
                            'branch': branch,
                            'division': division,
                            'name': product_adj.name or '/',
                            'debit': 0.0,
                            'credit': amount,
                            'account_id': journal_id.default_credit_account_id.id,
                            'move_id': account_move,
                            'journal_id': journal_id.id,
                            'period_id': period_id[0],
                            'date': date,
                            'analytic_account_id' : analytic_4_general,
                            })
                        x +=1
            else:
                x = 0
                while x < 2:
                    if x == 0:
                        self.pool.get('account.move.line').create(cr, uid, {
                            'branch': branch,
                            'division': division,
                            'name': product_adj.name or '/',
                            'debit': 0.0,
                            'credit': amount,
                            'account_id': product_adj.product_id.categ_id.property_stock_valuation_account_id.id,
                            'move_id': account_move,
                            'journal_id': journal_id.id,
                            'period_id': period_id[0],
                            'date': date,
                            'analytic_account_id' : analytic_4_general,
                            })
                        x +=1
                    else:
                        self.pool.get('account.move.line').create(cr, uid, {
                            'branch': branch,
                            'division': division,
                            'name': product_adj.name or '/',
                            'debit': amount,
                            'credit': 0.0,
                            'account_id': journal_id.default_debit_account_id.id,
                            'move_id': account_move,
                            'journal_id': journal_id.id,
                            'period_id': period_id[0],
                            'date': date,
                            'analytic_account_id' : analytic_4_general,
                            })
                        x +=1
            
            self.pool.get('stock.move').update_price_branch(cr, uid, vals, context=context)
            self.write(cr, uid, ids, {'state': 'done','account_move_id':account_move, 'date': datetime.now(),'confirm_uid':uid,'confirm_date':datetime.now()}, context=None)
            return True
        else:
            self.write(cr, uid, ids, {'state': 'done','date': datetime.now(),'confirm_uid':uid,'confirm_date':datetime.now()}, context=None)
            self.pool.get('stock.move').update_price_branch(cr, uid, vals, context=context)
            return True

    def confirm_all(self, cr, uid, ids, context=None):
        # all_id = self.search(cr, uid, [], context=None)
        # for x in self.browse(cr, uid, all_id, context=None):
        #     self.confirm(cr, uid, [x.id], context=None)
        # product_template_obj = self.pool.get('product.template')
        # ids = product_template_obj.search(cr, uid, [('type','=','product'),('cost_method','=','standard')])
        # product_template_obj.write(cr, uid, ids, {'cost_method':'average'})
        return True

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        if not self.warehouse_id and not self.product_id and not self.branch_id:
            pass
        else:
            return {'domain': {'warehouse_id': [('branch_id', '=', self.branch_id.id)]}}

    @api.onchange('division')
    def onchange_division(self):
        value = {}
        domain = {}
        obj_categ = self.env['product.category']
        categ_ids = obj_categ.get_child_ids(self.division)
        domain['product_id'] = [('categ_id','in',categ_ids)]
        value['product_id'] = False
        return  {'domain':domain,'value':value}

    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.warehouse_id and not self.product_id:
            pass
        elif not self.warehouse_id:
            return {'warning': {'title': 'Warning Message', 'message': 'Please choose your warehouse first.'}}
        else:
            current_cost_price = self.env['product.price.branch'].search([('warehouse_id', '=', self.warehouse_id.id),('product_id', '=', self.product_id.id)], limit=1).cost
            self.cost_price = current_cost_price

    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        if not self.warehouse_id and not self.product_id:
            pass
        elif not self.product_id:
            pass
        else:
            current_cost_price = self.env['product.price.branch'].search([('warehouse_id', '=', self.warehouse_id.id),('product_id', '=', self.product_id.id)], limit=1).cost
            self.cost_price = self.current_cost_price

    @api.multi
    def wkf_request_approval(self):
        obj_matrix = self.env["dym.approval.matrixbiaya"]
        if self.cost_price <= 0:
            raise osv.except_osv(('Perhatian !'), ("Cost Price harus lebih dari 0"))
        config = self.env['dym.branch.config'].search([
                                                       ('branch_id','=',self.branch_id.id)
                                                       ])   
        # if config :
        #     config_browse = config
        #     for x in config_browse :
        #         if not x.cost_adjustment_journal_id or not x.cost_adjustment_journal_id.default_debit_account_id or not x.cost_adjustment_journal_id.default_credit_account_id:
        #             raise exceptions.ValidationError(("Data jurnal cost adjusment di config branch %s belum lengkap")%(self.branch_id.name))
        obj_matrix.request_by_value(self, self.cost_price)
        self.write({'state': 'waiting_for_approval','approval_state':'rf'})
        return True
    
    @api.multi       
    def wkf_approval(self):
        if self.cost_price <= 0:
            raise osv.except_osv(('Perhatian !'), ("Cost Price harus lebih dari 0"))
        approval_sts = self.env["dym.approval.matrixbiaya"].approve(self)
        if approval_sts == 1:
            self.write({'approval_state':'a','approved_date':datetime.now(),'state':'approved'})
        elif approval_sts == 0:
            raise exceptions.ValidationError(("User tidak termasuk group approval"))
        return True

    @api.multi
    def has_approved(self):
        if self.approval_state == 'a':
            return True
        return False
    
    @api.multi
    def has_rejected(self):
        if self.approval_state == 'r':
            self.write({'state':'draft'})
            return True
        return False
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})