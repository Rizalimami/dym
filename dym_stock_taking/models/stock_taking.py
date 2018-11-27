from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp import models, exceptions, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import string

class wiz_stock_opname_count_line(models.TransientModel):
    _name = 'wiz.stock.opname.count.line'
    _description = "Stock Opname Count Line Wizard"
    
    @api.one
    @api.depends('qty_count','current_count')
    def _get_total_count(self):
        self.total_count = self.current_count + self.qty_count

    wizard_stock_opname_id = fields.Many2one('wiz.stock.opname.count', 'Wizard ID')
    location_id = fields.Many2one('stock.location','Location')
    product_id = fields.Many2one('product.product','Product')
    real_qty = fields.Float('Quantity On Hand')
    current_count = fields.Float('Current Count')
    qty_count = fields.Float('Qty Count')
    total_count = fields.Float('Total Count', compute="_get_total_count")
    lot_id = fields.Many2one('stock.production.lot','Engine Number')
    standard_line_id = fields.Many2one('dym.opname.line', 'Standard Line')
    blank_line_id = fields.Many2one('dym.opname.line.blank', 'Blank Line')
    no_tag = fields.Many2one('dym.inventory.tag', 'Nomor Tag')

class wiz_stock_opname_count(models.TransientModel):
    _name = 'wiz.stock.opname.count'
    _description = "Stock Opname Count Wizard"
        
    opname_id = fields.Many2one('dym.stock.opname','Stock Opname')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division')
    warehouse_id = fields.Many2one('stock.warehouse','Warehouse')
    location_id = fields.Many2one('stock.location','Location')
    product_id = fields.Many2one('product.product','Product')
    lot_id = fields.Many2one('stock.production.lot','Engine Number')
    count = fields.Char('Count')
    line_ids = fields.One2many('wiz.stock.opname.count.line', 'wizard_stock_opname_id')

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("Data Error, please try to refresh page or contact your administrator!"))
        res = super(wiz_stock_opname_count, self).default_get(cr, uid, fields, context=context)
        count = context and context.get('count', False) or False
        warehouse_id = context and context.get('warehouse_id', False) or False
        opname_id = context and context.get('active_id', False) or False
        opname = self.pool.get('dym.stock.opname').browse(cr, uid, opname_id, context=context)
        res.update(opname_id=opname_id)
        res.update(warehouse_id=warehouse_id)
        res.update(count=count)
        res.update(division=opname.division)
        return res

    @api.onchange('product_id')
    def change_product(self):
        warning = {}
        res = []
        self.lot_id = False
        if self.product_id:
            if not self.location_id:
                self.product_id = False
                warning = {'title':'Perhatian !','message':"mohon lengkapi data lokasi terlebih dahulu"}
                return {'warning':warning}
            if not self.product_id.categ_id.isParentName('Unit'):
                standard_search = self.env['dym.opname.line'].search([('product_id','=',self.product_id.id),('location_id','=',self.location_id.id),('opname_id','=',self.opname_id.id)])
                for standard in standard_search:
                    current_count = 0
                    if self.count == "count_1":
                        current_count = standard.count_1
                    elif self.count == "count_2":
                        current_count = standard.count_2
                    elif self.count == "count_3":
                        current_count = standard.count_3
                    res.append([0,0,{
                         'location_id':standard.location_id.id,
                         'product_id':standard.product_id.id,
                         'real_qty':standard.qty,
                         'current_count':current_count,
                         'qty_count':1,
                         'lot_id':False,
                         'standard_line_id':standard.id,
                         'blank_line_id':False,
                    }])
                blank_search = self.env['dym.opname.line.blank'].search([('product_id','=',self.product_id.id),('location_id','=',self.location_id.id),('opname_id','=',self.opname_id.id)])
                for blank in blank_search:
                    current_count = 0
                    if self.count == "count_1":
                        current_count = blank.count_1
                    elif self.count == "count_2":
                        current_count = blank.count_2
                    elif self.count == "count_3":
                        current_count = blank.count_3
                    res.append([0,0,{
                         'location_id':blank.location_id.id,
                         'product_id':blank.product_id.id,
                         'real_qty':blank.qty,
                         'current_count':current_count,
                         'qty_count':1,
                         'lot_id':False,
                         'standard_line_id':False,
                         'blank_line_id':blank.id,
                    }])
                if not blank_search and not standard_search:
                    res.append([0,0,{
                         'location_id':self.location_id.id,
                         'product_id':self.product_id.id,
                         'real_qty':0,
                         'current_count':0,
                         'qty_count':1,
                         'lot_id':False,
                         'standard_line_id':False,
                         'blank_line_id':False,
                    }])
        if res:
            val_conv =  self._convert_to_cache({'line_ids': res}, validate=False)
            val_conv['line_ids'] = val_conv['line_ids'] + self.line_ids
            self.update(val_conv)
        self.product_id = False

    @api.onchange('lot_id')
    def change_lot(self):
        warning = {}
        res = []
        if self.lot_id:
            if not self.location_id:
                self.lot_id = False
                warning = {'title':'Perhatian !','message':"mohon lengkapi data lokasi terlebih dahulu"}
                return {'warning':warning}
            standard_search = self.env['dym.opname.line'].search([('location_id','=',self.location_id.id),('opname_id','=',self.opname_id.id),('lot_id','=',self.lot_id.id)])
            for standard in standard_search:
                current_count = 0
                if self.count == "count_1":
                    current_count = standard.count_1
                elif self.count == "count_2":
                    current_count = standard.count_2
                elif self.count == "count_3":
                    current_count = standard.count_3
                res.append([0,0,{
                     'location_id':standard.location_id.id,
                     'product_id':standard.lot_id.product_id.id,
                     'real_qty':standard.qty,
                     'current_count':current_count,
                     'qty_count':1,
                     'lot_id':standard.lot_id.id,
                     'standard_line_id':standard.id,
                     'blank_line_id':False,
                }])
            blank_search = self.env['dym.opname.line.blank'].search([('location_id','=',self.location_id.id),('opname_id','=',self.opname_id.id),('engine_number','=',self.lot_id.name)])
            for blank in blank_search:
                current_count = 0
                if self.count == "count_1":
                    current_count = blank.count_1
                elif self.count == "count_2":
                    current_count = blank.count_2
                elif self.count == "count_3":
                    current_count = blank.count_3
                res.append([0,0,{
                     'location_id':blank.location_id.id,
                     'product_id':self.lot_id.product_id.id,
                     'real_qty':blank.qty,
                     'current_count':current_count,
                     'qty_count':1,
                     'lot_id':self.lot_id.id,
                     'standard_line_id':False,
                     'blank_line_id':blank.id,
                }])
            if not blank_search and not standard_search:
                res.append([0,0,{
                     'location_id':self.location_id.id,
                     'product_id':self.lot_id.product_id.id,
                     'real_qty':0,
                     'current_count':0,
                     'qty_count':1,
                     'lot_id':self.lot_id,
                     'standard_line_id':False,
                     'blank_line_id':False,
                }])
        if res:
            val_conv =  self._convert_to_cache({'line_ids': res}, validate=False)
            val_conv['line_ids'] = val_conv['line_ids'] + self.line_ids
            self.update(val_conv)
        self.lot_id = False

    @api.one
    def save_count(self):
        for data in self:
            result = []
            for line in data.line_ids:
                res = {}
                if not line.standard_line_id and not line.blank_line_id:
                    res['opname_id'] = self.opname_id.id
                    res['no_tag'] = line.no_tag.id
                    res['product_id'] = line.product_id.id
                    res['location_id'] = line.location_id.id
                    res['engine_number'] = line.lot_id.name
                    res['chassis_number'] = (line.lot_id.chassis_code if line.lot_id.chassis_code else '') + (line.lot_id.chassis_no if line.lot_id.chassis_no else '')
                    if self.count == "count_1":
                        res['count_1'] = line.total_count
                    elif self.count == "count_2":
                        res['count_2'] = line.total_count
                    elif self.count == "count_3":
                        res['count_3'] = line.total_count
                    line.blank_line_id.create(res)
                if line.standard_line_id:
                    if self.count == "count_1":
                        line.standard_line_id.write({'count_1':line.total_count})
                    elif self.count == "count_2":
                        line.standard_line_id.write({'count_2':line.total_count})
                    elif self.count == "count_3":
                        line.standard_line_id.write({'count_3':line.total_count})
                if line.blank_line_id:
                    if self.count == "count_1":
                        line.blank_line_id.write({'count_1':line.total_count})
                    elif self.count == "count_2":
                        line.blank_line_id.write({'count_2':line.total_count})
                    elif self.count == "count_3":
                        line.blank_line_id.write({'count_3':line.total_count})
        return True
class AccountFilter(models.Model):
    _inherit = "dym.account.filter"

    def _register_hook(self, cr):
        selection = self._columns['name'].selection
        if ('loss_account_inventory_adjustment','Loss Account Inventory Adjustment') not in selection: 
            self._columns['name'].selection.append(
                ('loss_account_inventory_adjustment', 'Loss Account Inventory Adjustment')
                )
            self._columns['name'].selection.append(
                ('income_account_inventory_adjustment', 'Income Account Inventory Adjustment')
                )

        return super(AccountFilter, self)._register_hook(cr)  

class onedStockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    @api.onchange('adjustment_qty')
    def _onchange_adjustment_qty(self):
        self.product_qty = self.theoretical_qty + self.adjustment_qty

    @api.onchange('product_id','location_id')
    def _onchange_product_location(self):
        self.cost_price = self.env['product.price.branch'].search([('warehouse_id','=', self.location_id.warehouse_id.id), ('product_id','=', self.product_id.id)]).cost or self.cost_price

    adjustment_qty = fields.Float(string='Adjustment Quantity', required=True, digits_compute=dp.get_precision('Product Unit of Measure'))
    cost_price = fields.Float(string='Cost Price', required=True, digits_compute=dp.get_precision('Account'))

    def _resolve_inventory_line(self, cr, uid, ids, context=None):
        move_id = super(onedStockInventoryLine, self)._resolve_inventory_line(cr, uid, ids, context=None)
        stock_move = self.pool.get('stock.move').browse(cr, uid, [move_id], context=None)
        self.pool.get('stock.move').write(cr, uid, [move_id], {'price_unit':ids.cost_price,'branch_id': ids.inventory_id.warehouse_id.branch_id.id,'categ_id':stock_move.product_id.categ_id.id})
        return move_id

class dym_stock_inventory(models.Model):
    _inherit = "stock.inventory"

    @api.model
    def _getLossAcccountDomain(self):
        dom2={}
        edi_doc_list2 = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.env['dym.account.filter'].get_domain_account('loss_account_inventory_adjustment')
        edi_doc_list2.extend(dict)      
        dom2['account_id'] = edi_doc_list2
        dom2['account_id'][2] = ('type','=','other')
        return dom2

    @api.model
    def _getIncomeAcccountDomain(self):
        dom2={}
        edi_doc_list2 = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.env['dym.account.filter'].get_domain_account('income_account_inventory_adjustment')
        edi_doc_list2.extend(dict)      
        dom2['account_id'] = edi_doc_list2
        dom2['account_id'][2] = ('type','=','other')
        return dom2

    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_stock_taking] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]
        
    @api.one
    @api.depends('warehouse_id','location_id')
    def _get_branch(self):
        self.branch_id = self.warehouse_id.branch_id or self.location_id.branch_id

    @api.model
    @api.depends('branch_id')
    def _get_branch_destination_id(self):
        if self.branch_id:
            self.branch_destination_id = self.branch_id or False

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    loss_account = fields.Many2one('account.account', string='Loss Account', domain=_getLossAcccountDomain)
    income_account = fields.Many2one('account.account', string='Income Account', domain=_getIncomeAcccountDomain)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division', required=True)
    analytic_1 = fields.Many2one('account.analytic.account', string='Account Analytic Company')
    analytic_2 = fields.Many2one('account.analytic.account', string='Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', string='Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', string='Account Analytic Cost Center')

    branch_id = fields.Many2one('dym.branch', string='Branch', compute='_get_branch', store=True)
    state = fields.Selection([('draft','Draft'), ('cancel', 'Cancelled'), ('confirm', 'In Progress'), ('waiting_for_approval', 'Waiting for Approval'), ('approved','Approved'), ('done','Validated'), ('rejected', 'Rejected')], 'Status', readonly=True, select=True, copy=False, default='draft')
    approval_ids = fields.One2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)])
    approval_state = fields.Selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True, default='b')
    branch_destination_id =  fields.Many2one('dym.branch', string='Branch Destination', required=True, default=_get_branch_destination_id)

    _defaults = {
        'analytic_1':_get_analytic_company,
    }

    @api.onchange('warehouse_id','location_id')
    def change_warehouse_number(self):
        self.branch_id = self.warehouse_id.branch_id or self.location_id.branch_id

    @api.model
    def _get_default_date(self):
        # return datetime.now()
        return self.env['dym.branch'].get_default_date_model()

    # @api.multi
    # def _get_harga_pricelist(self, line, pricelist):
    #     date_order_str = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
    #     product_qty = line.theoretical_qty - line.product_qty
    #     if product_qty < 0:
    #         product_qty = -product_qty        
    #     price = pricelist.price_get(line.product_id.id, product_qty, context={'date': date_order_str})[pricelist.id]
    #     if price != False:
    #         return price
    #     else:
    #         return 0

    #Overide Without Super to Pass Negative Qty in Inventory Adjustment 
    def action_done(self, cr, uid, ids, context=None):
        """ Finish the inventory
        @return: True
        """
        for inv in self.browse(cr, uid, ids, context=context):
            # for inventory_line in inv.line_ids:
            #     if inventory_line.product_qty < 0 and inventory_line.product_qty != inventory_line.theoretical_qty:
            #         raise osv.except_osv(_('Warning'), _('You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s' % (inventory_line.product_id.name, inventory_line.product_qty)))
            self.action_check(cr, uid, [inv.id], context=context)
            self.write(cr, uid, [inv.id], {'state': 'done'}, context=context)
            self.post_inventory(cr, uid, inv, context=context)
        return True

    def post_inventory(self, cr, uid, inv, context=None):
        if context is None:
            context = {}
        context['inventory'] = inv
        res = super(dym_stock_inventory, self).post_inventory(cr, uid, inv, context=context)
        for line in inv.line_ids:
            if line.product_id.categ_id.isParentName('Unit'):
                    # price = self._get_harga_pricelist(cr, uid, line, line.location_id.branch_id.pricelist_unit_purchase_id)
                    quant_id = self.pool.get('stock.quant').search(cr, uid, [('lot_id','=',line.prod_lot_id.id)], order='id desc',limit=1)
                    quant = self.pool.get('stock.quant').browse(cr, uid, quant_id)
                    quant.write({'consolidated_date':self._get_default_date(cr,uid), 'cost':line.cost_price * quant.qty})
                    write_res = {'hpp':line.cost_price * quant.qty,'product_id':line.product_id.id, 'branch_id': line.location_id.branch_id.id or inv.warehouse_id.branch_id.id or inv.location_id.branch_id.id, 'division':'Unit','location_id':quant.location_id.id}
                    if line.adjustment_qty < 0:
                        write_res['state'] = 'loss'
                    else:
                        write_res['state'] = 'stock'
                    if not quant.lot_id.receive_date:
                        write_res['receive_date'] = datetime.today()
                    quant.lot_id.write(write_res)
            elif not line.product_id.categ_id.isParentName('Unit'):
                product_qty = line.theoretical_qty - line.product_qty
                if product_qty < 0:
                    product_qty = -product_qty
                    quant_ids = self.pool.get('stock.quant').search(cr, uid, [
                        ('product_id','=',line.product_id.id),
                        ('qty','=',product_qty),
                        ('location_id','=',line.location_id.id),
                        ], order='id desc', limit=1)
                    for quant in self.pool.get('stock.quant').browse(cr, uid, quant_ids):
                        quant.write({'consolidated_date':self._get_default_date(cr,uid), 'cost':line.cost_price * quant.qty})
        return res

    @api.multi
    def wkf_request_approval(self):
        obj_matrix = self.env["dym.approval.matrixbiaya"]
        obj_matrix.request_by_value(self, 0)
        for line in self.line_ids:
            if line.product_qty != line.theoretical_qty + line.adjustment_qty:
                product_qty = line.theoretical_qty + line.adjustment_qty
                if product_qty < 0:
                    product_qty = 0
                line.write({'product_qty': product_qty})
            if line.product_id.categ_id.isParentName('Unit') and not line.prod_lot_id:
                raise exceptions.ValidationError(("Mohon lengkapi serial number untuk produk unit!"))
        self.write({'state': 'waiting_for_approval','approval_state':'rf'})
        return True
    
    @api.multi       
    def wkf_approval(self):
        approval_sts = self.env["dym.approval.matrixbiaya"].approve(self)
        if approval_sts == 1:
            self.write({'approval_state':'a','state':'approved'})
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
            self.write({'state':'confirm'})
            return True
        return False
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'confirm','approval_state':'r'})
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'confirm','approval_state':'b'})

class dym_stock_quant_rel_product_name(models.Model):
    _inherit = "stock.quant"

    @api.one
    @api.depends('product_id')
    def _get_product_name(self):
        self.product_name = self.product_id.product_tmpl_id.name
        self.product_category = self.product_id.categ_id.get_root_name()

    product_name = fields.Char(string='Product Name', compute='_get_product_name', store=True)
    product_category = fields.Char(string='Product Category', compute='_get_product_name', store=True)

class dym_inventory_tag(models.Model):
    _name = "dym.inventory.tag"
    _description = "Inventory Blank Tag"

    @api.one
    @api.depends('summary_id.opname_id.line_blank_ids.no_tag')
    def _get_line_blank_id(self):
        line_blank = self.env['dym.opname.line.blank'].search([('no_tag','=',self.id)])
        self.line_blank_id = line_blank.id

    name = fields.Char('Tag')
    summary_id = fields.Many2one('dym.inventory.summary', 'Summary')
    line_blank_id = fields.Many2one('dym.opname.line.blank', 'Line Blank ID', compute='_get_line_blank_id', store=True)

class dym_stock_opname(models.Model):
    _name = "dym.stock.opname"
    _description = "Stock Opname"

    @api.one
    @api.depends('line_ids','line_blank_ids')
    def _get_summary(self):
        total_qty_on_hand = float(0)
        total_count_1 = float(0)
        total_count_2 = float(0)
        total_count_3 = float(0)
        total_variance = float(0)
        total_amount = float(0)
        total_minus = float(0)
        total_plus = float(0)
        total_amount_minus = float(0)
        total_amount_plus = float(0)
        for standard in self.line_ids:
            total_qty_on_hand += standard.qty
            total_count_1 += standard.count_1
            total_count_2 += standard.count_2
            total_count_3 += standard.count_3
            total_variance += standard.variance
            total_amount += standard.amount
            if standard.variance < 0:
                total_minus += standard.variance                
            if standard.amount < 0:
                total_amount_minus += standard.amount
            if standard.variance > 0:
                total_plus += standard.variance                
            if standard.amount > 0:
                total_amount_plus += standard.amount
        for blank in self.line_blank_ids:
            total_qty_on_hand += blank.qty
            total_count_1 += blank.count_1
            total_count_2 += blank.count_2
            total_count_3 += blank.count_3
            total_variance += blank.variance
            total_amount += blank.amount
            if blank.variance < 0:
                total_minus += blank.variance                
            if blank.amount < 0:
                total_amount_minus += blank.amount
            if blank.variance > 0:
                total_plus += blank.variance                
            if blank.amount > 0:
                total_amount_plus += blank.amount
        self.total_qty_on_hand = total_qty_on_hand
        self.total_count_1 = total_count_1
        self.total_count_2 = total_count_2
        self.total_count_3 = total_count_3
        self.total_variance = total_variance
        self.total_amount = total_amount
        self.total_minus = total_minus
        self.total_plus = total_plus
        self.total_amount_minus = total_amount_minus
        self.total_amount_plus = total_amount_plus

    name = fields.Char('Name')
    summary_id = fields.Many2one('dym.inventory.summary', 'Summary')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division', readonly=True)
    date = fields.Datetime('Date', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    branch_id = fields.Many2one('dym.branch', 'Branch', readonly=True)
    line_ids = fields.One2many('dym.opname.line', 'opname_id', 'Detail Stock Opname', copy=False)
    line_blank_ids = fields.One2many('dym.opname.line.blank', 'opname_id', 'Detail Stock Opname', copy=False)
    total_qty_on_hand = fields.Float(string='Total QTY On Hand', compute='_get_summary')
    total_count_1 = fields.Float(string='Total Count 1', compute='_get_summary')
    total_count_2 = fields.Float(string='Total Count 2', compute='_get_summary')
    total_count_3 = fields.Float(string='Total Count 3', compute='_get_summary')
    total_variance = fields.Float(string='Total Variance', compute='_get_summary')
    total_amount = fields.Float(string='Total Amount', compute='_get_summary')
    total_minus = fields.Float(string='Total Variance Minus', compute='_get_summary')
    total_plus = fields.Float(string='Total Variance Plus', compute='_get_summary')
    total_amount_minus = fields.Float(string='Total Amount Variance Minus', compute='_get_summary')
    total_amount_plus = fields.Float(string='Total Amount Variance Plus', compute='_get_summary')
    state = fields.Selection([
                              ('draft','Draft'),
                              ('waiting_for_approval','Waiting For Approval'),
                              ('approved','Approved'),
                              ('done','Done'),
                              ('cancel','Cancelled'),
                              ('reject','Rejected'),
                              ], 'State', default='draft')
    adjustment_id = fields.Many2one('stock.inventory', 'Inventory Adjustment', readonly=True)
    count_1 = fields.Boolean('Count-1')
    count_2 = fields.Boolean('Count-2')
    count_3 = fields.Boolean('Count-3')
    
    _defaults={
               'date' : fields.Datetime.now,
               }

    def create(self, cr, uid, vals, context=None):
        branch_id = self.pool.get('stock.warehouse').browse(cr, uid, [vals['warehouse_id']]).branch_id.id
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, branch_id, 'SOP', division=False)
        vals['branch_id'] = branch_id
        return super(dym_stock_opname, self).create(cr, uid, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        return super(dym_stock_opname, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def wkf_action_cancel(self):
        self.write({'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})


    @api.model
    def _get_default_date(self):
        # return datetime.now()
        return self.env['dym.branch'].get_default_date_model()

    @api.multi
    def create_new_lot(self, line):
        if line.chassis_number :
            if len(line.chassis_number) == 14:
                chassis_number = line.chassis_number
                chassis_code = False
            elif len(line.chassis_number) == 17:
                chassis_number = line.chassis_number[3:18]
                chassis_code = line.chassis_number[:3]
        lot = self.env['stock.production.lot'].create({
                                 'name':line.engine_number,
                                 'chassis_no':chassis_number,
                                 'chassis_code':chassis_code,
                                 'product_id':line.product_id.id,
                                 'branch_id':line.opname_id.branch_id.id,
                                 'division':line.opname_id.division,
                                 'purchase_order_id':False,
                                 'po_date':False,
                                 'receive_date':self._get_default_date(),
                                 'supplier_id':False,
                                 'expedisi_id':False,
                                 'receipt_id':False,
                                 'picking_id':False,
                                 'state':'stock',
                                 'location_id': line.location_id.id,
                                 'tahun': self._get_default_date().strftime('%Y'),
                                 'ready_for_sale': 'good'
                                 })
        return lot.id

    @api.multi
    def create_adjustment(self):
        adjustment_obj = self.env['stock.inventory']
        res = {}
        for line in self.line_ids:
            if line.variance == 0:
                continue
            location = line.location_id
            while (location.location_id):
                location = location.location_id                
            key = location.id
            if key not in res:
                per_location = {}
                per_location['name'] = self.name
                per_location['warehouse_id'] = self.warehouse_id.id
                per_location['location_id'] = key
                per_location['filter'] = 'partial'
                per_location['division'] = self.division
                per_location['line_ids'] = []
                res[key] = per_location
            per_product = {}
            per_product['product_id'] = line.product_id.id
            per_product['product_uom_id'] = line.product_id.uom_id.id
            per_product['location_id'] = line.location_id.id
            per_product['adjustment_qty'] = line.variance
            per_product['product_qty'] = line.qty + line.variance
            per_product['prod_lot_id'] = line.lot_id.id
            per_product['cost_price'] = line.inventory_value
            res[key]['line_ids'] += [(0, 0, per_product)]

        for line in self.line_blank_ids:
            if line.variance == 0:
                continue
            location = line.location_id
            while (location.location_id):
                location = location.location_id                
            key = location.id
            if key not in res:
                per_location = {}
                per_location['name'] = self.name
                per_location['warehouse_id'] = self.warehouse_id.id
                per_location['location_id'] = key
                per_location['filter'] = 'partial'
                per_location['division'] = self.division
                per_location['line_ids'] = []
                res[key] = per_location
            per_product = {}
            per_product['product_id'] = line.product_id.id
            per_product['product_uom_id'] = line.product_id.uom_id.id
            per_product['location_id'] = line.location_id.id
            per_product['adjustment_qty'] = line.variance
            per_product['product_qty'] = line.qty + line.variance
            per_product['cost_price'] = line.inventory_value
            lot_search = self.env['stock.production.lot'].search([('name','=',line.engine_number)])
            if lot_search:
                lot_id = lot_search[0]
            else:
                lot_id = self.create_new_lot(line)
            per_product['prod_lot_id'] = lot_id
            res[key]['line_ids'] += [(0, 0, per_product)]
        if res:
            for x in res:
                adjustment_id = adjustment_obj.create(res[x])
                self.write({'adjustment_id':adjustment_id.id,'state':'done'})
        return True

    @api.multi
    def close_count_1(self):
        self.write({'count_1':True})

    @api.multi
    def close_count_2(self):
        self.write({'count_2':True})

    @api.multi
    def close_count_3(self):
        self.write({'count_3':True})

    @api.cr_uid_ids_context
    def view_adjustment(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        val = self.browse(cr, uid, ids)
        result = mod_obj.get_object_reference(cr, uid, 'stock', 'action_inventory_form')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_inventory_form')
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = val.adjustment_id.id
        return result

class dym_opname_line(models.Model):
    _name = "dym.opname.line"
    _order = "no_tag asc"
    
    @api.one
    @api.depends('count_1','count_2','count_3')
    def _get_variance(self):
        if self.count_3 > 0:
            self.variance = self.count_3 - self.qty
        elif self.count_2 > 0:
            self.variance = self.count_2 - self.qty
        else:
            self.variance = self.count_1 - self.qty

    @api.one
    @api.depends('variance')
    def _get_status(self):
        if self.variance == 0:
            self.status = 'OK'
        else:
            self.status = 'Not OK'

    @api.one
    @api.depends('product_id','opname_id.warehouse_id')
    def _get_amount_inventory(self):
        self.inventory_value = self.env['product.price.branch'].search([('warehouse_id','=', self.opname_id.warehouse_id.id), ('product_id','=', self.product_id.id)]).cost or 0

    @api.one
    @api.depends('variance')
    def _get_amount_variance(self):
        self.amount = self.variance * self.inventory_value

    opname_id = fields.Many2one('dym.stock.opname', 'Stock Opname')
    no_tag = fields.Char('Nomor Tag', readonly=True)
    inventory_line_id = fields.Many2one('dym.inventory.line', 'Inventory Line')
    inventory_line_second_id = fields.Many2one('dym.inventory.line.second', 'Inventory Line')
    product_id = fields.Many2one('product.product', 'Item', readonly=True)
    attribute_value_ids = fields.Many2many(related='product_id.attribute_value_ids', string='Variant', readonly=True)
    inventory_value = fields.Float(string='Inventory Value', readonly=True, compute='_get_amount_inventory')
    location_id = fields.Many2one('stock.location', 'Lokasi', readonly=True)
    lot_id = fields.Many2one('stock.production.lot', 'Engine Number', readonly=True)
    qty = fields.Float(string='Quantity On Hand', readonly=True)
    blank_tag = fields.Boolean(string='Blank Tag', default=False, readonly=True)
    count_1 = fields.Float(string='Count-1')
    count_2 = fields.Float(string='Count-2')
    count_3 = fields.Float(string='Count-3')
    parent_count_1 = fields.Boolean(related="opname_id.count_1", string='Parent Count-1')
    parent_count_2 = fields.Boolean(related="opname_id.count_2", string='Parent Count-2')
    parent_count_3 = fields.Boolean(related="opname_id.count_3", string='Parent Count-3')
    variance = fields.Float(string='Variance', compute='_get_variance')
    status = fields.Char(string='status', compute='_get_status')
    amount = fields.Float(string='Amount Variance', compute='_get_amount_variance')

class dym_opname_line_blank(models.Model):
    _name = "dym.opname.line.blank"
    _order = "no_tag asc"

    @api.one
    @api.depends('count_1','count_2','count_3')
    def _get_variance(self):
        if self.count_3 > 0:
            self.variance = self.count_3 - self.qty
        elif self.count_2 > 0:
            self.variance = self.count_2 - self.qty
        else:
            self.variance = self.count_1 - self.qty

    @api.one
    @api.depends('variance')
    def _get_status(self):
        if self.variance == 0:
            self.status = 'OK'
        else:
            self.status = 'Not OK'

    @api.one
    @api.depends('variance')
    def _get_amount_variance(self):
        self.amount = self.variance * self.inventory_value

    @api.one
    @api.depends('product_id','opname_id.warehouse_id')
    def _get_amount_inventory(self):
        self.inventory_value = self.env['product.price.branch'].search([('warehouse_id','=', self.opname_id.warehouse_id.id), ('product_id','=', self.product_id.id)]).cost or 0

    opname_id = fields.Many2one('dym.stock.opname', 'Stock Opname')
    inventory_line_second_id = fields.Many2one('dym.inventory.line.second', 'Inventory Line')
    division = fields.Selection(related="opname_id.division", string='Division')
    no_tag = fields.Many2one('dym.inventory.tag', 'Nomor Tag', required=True)
    product_id = fields.Many2one('product.product', 'Item', required=True)
    inventory_value = fields.Float(string='Inventory Value', readonly=True, compute='_get_amount_inventory')
    attribute_value_ids = fields.Many2many(related='product_id.attribute_value_ids', string='Variant')
    engine_number = fields.Char(string='Engine Number')
    chassis_number = fields.Char(string='Chassis Number')
    location_id = fields.Many2one('stock.location', 'Lokasi', required=True)
    qty = fields.Float(string='Quantity On Hand', readonly=True)
    blank_tag = fields.Boolean(string='Blank Tag', default=True, readonly=True)
    count_1 = fields.Float(string='Count-1')
    count_2 = fields.Float(string='Count-2')
    count_3 = fields.Float(string='Count-3')
    parent_count_1 = fields.Boolean(related="opname_id.count_1", string='Parent Count-1')
    parent_count_2 = fields.Boolean(related="opname_id.count_2", string='Parent Count-2')
    parent_count_3 = fields.Boolean(related="opname_id.count_3", string='Parent Count-3')
    variance = fields.Float(string='Variance', compute='_get_variance')
    status = fields.Char(string='status', compute='_get_status')
    amount = fields.Float(string='Amount Variance', compute='_get_amount_variance')

    @api.multi
    def is_punctuation(self, words):
        for n in range(len(words)) :
            if words[n] in string.punctuation :
                return True
        return False

    @api.onchange('engine_number')
    def change_engine_number(self):
        warning={}
        if self.engine_number:
            if not (self.product_id and self.location_id):
                self.engine_number = False
                warning = {'title':'Perhatian !','message':"mohon lengkapi data produk dan lokasi terlebih dahulu"}
                return {'warning':warning}
            if not self.product_id:
                self.engine_number = False
                warning = {'title':'Perhatian !','message':"Produk tidak boleh kosong"}
                return {'warning':warning}
            self.engine_number = self.engine_number.replace(" ", "")
            self.engine_number = self.engine_number.upper()
            if len(self.engine_number) != 12 :
                self.engine_number = False
                warning = {'title':'Engine Number Salah !','message':"Silahkan periksa kembali Engine Number yang Anda input"}
                return {'warning':warning}
            
            if self.is_punctuation(self.engine_number) :
                warning = {'title':'Perhatian !','message':"Engine Number hanya boleh huruf dan angka"}
                return {'warning':warning}
            
            if self.product_id:
                product_id = self.env['product.template'].search([('name','=',self.product_id.name)])
                if product_id.kd_mesin :
                    pjg = len(product_id.kd_mesin)
                    if product_id.kd_mesin != self.engine_number[:pjg] :
                        self.engine_number = False
                        warning = {'title':'Perhatian !','message':"Engine Number tidak sama dengan kode mesin di Produk"}
                        return {'warning':warning}
                else :
                    self.engine_number = False
                    warning = {'title':'Perhatian !','message':"Silahkan isi kode mesin '%s' di master product terlebih dahulu" %self.product_id.description}
                    return {'warning':warning}
                engine_search = self.env['stock.quant'].search([('lot_id.name','=',self.engine_number),('location_id','=',self.location_id.id),('qty','>','0'),('lot_id.state','not in',['returned','loss'])])
                if engine_search:
                    self.engine_number=False
                    warning = {'title':'Perhatian !','message':"Nomor engine sudah ada"}
                    return {'warning':warning}

    @api.onchange('chassis_number')
    def change_chassis_number(self):
        warning = {}
        if self.chassis_number :
            self.chassis_number = self.chassis_number.replace(" ", "")
            self.chassis_number = self.chassis_number.upper()
            if len(self.chassis_number) == 14 or (len(self.chassis_number) == 17 and self.chassis_number[:2] == 'MH') :
                self.chassis_number = self.chassis_number
            else :
                self.chassis_number = False
                warning = {'title':'Chassis Number Salah !','message':"Silahkan periksa kembali Chassis Number yang Anda input"}
                return {'warning':warning}
            
            if self.is_punctuation(self.chassis_number) :
                self.chassis_number = False
                warning = {'title':'Perhatian','message':"Chassis Number hanya boleh huruf dan angka"}
                return {'warning':warning}
            chassis_exist = self.env['stock.quant'].search([('lot_id.chassis_no','=',self.chassis_number),('location_id','=',self.location_id.id),('qty','>','0'),('lot_id.state','not in',['returned','loss'])])
            if chassis_exist:
                self.chassis_number=False
                warning = {'title':'Perhatian !','message':"Chassis Number sudah ada"}
                return {'warning':warning}

    @api.constrains('engine_number','chassis_number')
    def _uniq_engine_chassis(self):
        if self.division == 'Unit':
            engine_search = self.search([('engine_number','=',self.engine_number),('opname_id','=',self.opname_id.id),('id','!=',self.id)])
            if engine_search:
                raise ValidationError("Ditemukan engine number duplicate, silahkan cek kembali!")
            chassis_search = self.search([('chassis_number','=',self.chassis_number),('opname_id','=',self.opname_id.id),('id','!=',self.id)])
            if chassis_search:
                raise ValidationError("Ditemukan chassis number duplicate, silahkan cek kembali!")

    @api.constrains('product_id','location_id')
    def _uniq_location_product(self):
        standard_search =  self.env['dym.opname.line'].search([('product_id','=',self.product_id.id),('location_id','=',self.location_id.id),('opname_id','=',self.opname_id.id),('lot_id.name','=',self.engine_number)])
        if standard_search:
            raise ValidationError("Kombinasi product-lokasi sudah ada di inventory line (standard)!")
        blank_search = self.search([('product_id','=',self.product_id.id),('location_id','=',self.location_id.id),('id','!=',self.id),('opname_id','=',self.opname_id.id),('engine_number','=',self.engine_number)])
        if blank_search:
            raise ValidationError("Kombinasi product-lokasi sudah ada di inventory line (blank)!")

    @api.constrains('no_tag')
    def _uniq_no_tag(self):
        blank_search = self.search([('no_tag','=',self.no_tag.id),('id','!=',self.id)])
        if blank_search:
            raise ValidationError("Nomor tag " + self.no_tag.name + " sudah digunakan untuk product " + self.product_id.name + " di lokasi " + self.location_id.name + "!")

class dym_inventory_summary(models.Model):
    _name = "dym.inventory.summary"
    _description = "Inventory Summary"

    @api.one
    @api.depends('snapshot_id')
    def _get_snapshot_ids(self):
        if self.snapshot_id:
            snapshot_ids = self.env['dym.inventory.line.second'].search([('snapshot_id','=',self.snapshot_id.id)])
            self.line_ids_second = snapshot_ids

    name = fields.Char('Name')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division')
    cutoff_date = fields.Datetime('Cut-Off Date', required=True)
    snapshot_id = fields.Many2one('dym.inventory.snapshot', 'Snapshot Date')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    line_ids = fields.One2many('dym.inventory.line', 'summary_id', 'Detail Summary', copy=False)
    line_ids_second = fields.One2many('dym.inventory.line.second', 'summary_id', 'Detail Summary', copy=False, compute='_get_snapshot_ids')
    opname_id = fields.Many2one('dym.stock.opname', 'Stock Opname', copy=False)
    snapshot_first = fields.Boolean('Snapshot')
    total_generated = fields.Integer('Total Generated')
    amount_generate = fields.Integer('Amount Generate')
    tag_ids = fields.One2many('dym.inventory.tag', 'summary_id', 'Tags', copy=False)
    
    _defaults={
               'cutoff_date' : fields.Datetime.now,
               }

    def create(self, cr, uid, vals, context=None):
        branch_id = self.pool.get('stock.warehouse').browse(cr, uid, [vals['warehouse_id']]).branch_id.id
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, branch_id, 'ISU', division=False)
        return super(dym_inventory_summary, self).create(cr, uid, vals, context=context)

    
    @api.onchange('warehouse_id','division')
    def warehouse_change(self):
        self.line_ids = False
    
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        return super(dym_inventory_summary, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def generate_inventory(self):
        self.line_ids.unlink()
        line_obj = self.env['dym.inventory.line']
        res = []
        grouped_quants = {}
        locations = self.env['stock.location'].search([('warehouse_id','=',self.warehouse_id.id),('usage','=','internal')])
        domain = [('location_id','in',locations.ids)]
        if self.division == 'Unit':
            domain += [('product_category','=','Unit'),('lot_id.state','not in',['returned','loss'])]
        else:
            domain += [('product_category','=','Sparepart')]
        quants = self.env['stock.quant'].search(domain, order='product_name asc')
        for quant in quants:
            key = str(quant.location_id.id) + '_' + quant.product_name + '_' + str(quant.product_id.id) + '_' + str(quant.lot_id.id)
            if key not in grouped_quants:
                grouped_quants[key] = {'product_id':quant.product_id.id,'location_id':quant.location_id.id,'qty':quant.qty,'lot_id':quant.lot_id.id}
            else:
                grouped_quants[key]['qty'] += quant.qty
        for item in sorted(grouped_quants):
            if grouped_quants[item]['qty'] > 0:
                res.append({'summary_id':self.id, 'product_id': grouped_quants[item]['product_id'], 'location_id': grouped_quants[item]['location_id'], 'qty': grouped_quants[item]['qty'],'lot_id':grouped_quants[item]['lot_id']})
        count = 0
        for line in res:
            count += 1
            index = self.name.find('/')
            line['no_tag'] = self.name[:index] + 'S' + self.name[index:] + '-' + str("%05d" % (count,))
            line_obj.create(line)
        return True

    @api.multi
    def set_snapshot(self):
        self.write({'snapshot_first':True,'cutoff_date':datetime.today()})
        return True

    @api.multi
    def generate_snapshot(self):
        res = []
        line_second_obj = self.env['dym.inventory.line.second']
        current_date = datetime.today()
        snapshot_id = self.env['dym.inventory.snapshot'].create({'name':current_date,'summary_id':self.id})
        grouped_quants = {}
        locations = self.env['stock.location'].search([('warehouse_id','=',self.warehouse_id.id),('usage','=','internal')])
        domain = [('location_id','in',locations.ids)]
        if self.division == 'Unit':
            domain += [('product_category','=','Unit'),('lot_id.state','not in',['returned','loss'])]
        else:
            domain += [('product_category','=','Sparepart')]
        quants = self.env['stock.quant'].search(domain, order='product_name asc')
        for quant in quants:
            key = str(quant.location_id.id) + '_' + quant.product_name + '_' + str(quant.product_id.id) + '_' + str(quant.lot_id.id)
            if key not in grouped_quants:
                grouped_quants[key] = {'product_id':quant.product_id.id,'location_id':quant.location_id.id,'qty':quant.qty,'lot_id':quant.lot_id.id}
            else:
                grouped_quants[key]['qty'] += quant.qty
        for item in sorted(grouped_quants):
            if grouped_quants[item]['qty'] > 0:
                res.append({'summary_id':self.id, 'product_id': grouped_quants[item]['product_id'], 'location_id': grouped_quants[item]['location_id'], 'qty': grouped_quants[item]['qty'], 'snapshot_id': snapshot_id.id,'lot_id':grouped_quants[item]['lot_id']}) 
        for line in res:
            line_second_obj.create(line)
        self.snapshot_id = snapshot_id.id
        return True

    @api.multi
    def generate_tag(self):
        if self.amount_generate <= 0:
            raise osv.except_osv(('Invalid action !'), ('Jumlah tag yang mau di generate harus lebih dari 0!'))
        tag_obj = self.env['dym.inventory.tag']
        count = self.total_generated
        for i in range(self.amount_generate):
            count += 1
            index = self.name.find('/')
            tag = {}
            tag['summary_id'] = self.id
            tag['name'] = self.name[:index] + 'B' + self.name[index:] + '-' + str("%05d" % (count,))
            tag_obj.create(tag)
        self.total_generated += self.amount_generate
        self.amount_generate = 1
        return True

    @api.multi
    def start_opname(self):
        opname_obj = self.env['dym.stock.opname']
        opname_line = []
        opname_line_blank = []
        second_Line_ids = self.env['dym.inventory.snapshot'].search([], order="id desc", limit=1).second_line_ids
        for line in second_Line_ids:
            inv_line = self.env['dym.inventory.line'].search([('location_id','=',line.location_id.id),('summary_id','=',line.summary_id.id),('product_id','=',line.product_id.id),('lot_id','=',line.lot_id.id)])
            if inv_line:
                opname_line.append((0, 0, {
                'inventory_line_id': inv_line.id,
                'inventory_line_second_id': line.id,
                'product_id': line.product_id.id,
                'lot_id': line.lot_id.id,
                'location_id': line.location_id.id,
                'qty': line.qty,
                'blank_tag': False,
                'no_tag': inv_line.no_tag
                }))
            else:
                opname_line_blank.append((0, 0, {
                'inventory_line_second_id': line.id,
                'no_tag': False,
                'product_id': line.product_id.id,
                'location_id': line.location_id.id,
                'engine_number': line.lot_id.name,
                'chassis_number': (line.lot_id.chassis_code if line.lot_id.chassis_code else '') + (line.lot_id.chassis_no if line.lot_id.chassis_no else ''),
                'qty': line.qty,
                'blank_tag': True,
                }))
        if opname_line_blank:
            if len(opname_line_blank) < len(self.tag_ids):
                tags = self.env['dym.inventory.tag'].search([], order="id asc")
                index = 0
                for line_blank in opname_line_blank:
                    line_blank[2]['no_tag'] = tags[index]
                    index += 1
            else:
                raise osv.except_osv(('Invalid action !'), ('Jumlah blank tag yang dibutuhkan (%s) lebih kecil dari blank tag yang di generate (%s)!')%(len(opname_line_blank),len(self.tag_ids)))
        opname = {
            'warehouse_id': self.warehouse_id.id,
            'summary_id': self.id,
            'division': self.division,
            'line_ids': opname_line,
            'line_blank_ids': opname_line_blank
        }
        opname_id = opname_obj.create(opname)
        self.write({'opname_id':opname_id.id})
        return True

    @api.cr_uid_ids_context
    def view_opname(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        val = self.browse(cr, uid, ids)
        result = mod_obj.get_object_reference(cr, uid, 'dym_stock_taking', 'dym_stock_opname_action')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'dym_stock_taking', 'dym_stock_opname_form_view')
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = val.opname_id.id
        return result

class dym_inventory_line(models.Model):
    _name = "dym.inventory.line"
    _order = "no_tag asc"

    summary_id = fields.Many2one('dym.inventory.summary', 'Summary')
    no_tag = fields.Char('Nomor Tag')
    product_id = fields.Many2one('product.product', 'Item', readonly=True)
    attribute_value_ids = fields.Many2many(related='product_id.attribute_value_ids', string='Variant', readonly=True)
    location_id = fields.Many2one('stock.location', 'Lokasi', readonly=True)
    qty = fields.Float(string='Quantity', readonly=True)
    lot_id = fields.Many2one('stock.production.lot', string='Engine Number', readonly=True)


class dym_inventory_line_second(models.Model):
    _name = "dym.inventory.line.second"

    summary_id = fields.Many2one('dym.inventory.summary', 'Summary')
    snapshot_id = fields.Many2one('dym.inventory.snapshot', 'Snapshot 2')
    product_id = fields.Many2one('product.product', 'Item', readonly=True)
    attribute_value_ids = fields.Many2many(related='product_id.attribute_value_ids', string='Variant', readonly=True)
    location_id = fields.Many2one('stock.location', 'Lokasi', readonly=True)
    qty = fields.Float(string='Quantity', readonly=True)
    lot_id = fields.Many2one('stock.production.lot', string='Engine Number', readonly=True)

class dym_inventory_snapshot(models.Model):
    _name = "dym.inventory.snapshot"

    second_line_ids = fields.One2many('dym.inventory.line.second', 'snapshot_id', 'Second Line')
    name = fields.Datetime('Snapshot Date')
    summary_id = fields.Many2one('dym.inventory.summary', 'Summary')