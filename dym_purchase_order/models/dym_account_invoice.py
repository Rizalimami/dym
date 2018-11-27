import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _, workflow, SUPERUSER_ID
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.osv import osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class dym_account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_account_invoice, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        for field in res['fields']:
            if field == 'division':
                if 'menu' in context and context['menu'] == 'showroom':
                    res['fields'][field]['selection'] = [('Unit','Showroom'), ('Umum','General')]

                if 'menu' in context and context['menu'] == 'workshop':
                    res['fields'][field]['selection'] = [('Sparepart','Workshop'), ('Umum','General')]

                if 'menu' in context and context['menu'] == 'general_affair':
                    res['fields'][field]['selection'] = [('Unit','Showroom'), ('Sparepart','Workshop'), ('Umum','General')]
        return res
        
    def _register_hook(self, cr):
        selection = self._columns['tipe'].selection
        if ('purchase', 'purchase') not in selection:
            self._columns['tipe'].selection.append(
                    ('purchase', 'purchase'))
        return super(dym_account_invoice, self)._register_hook(cr)
    
    @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount','discount_cash','discount_program','discount_lain')
    def _compute_amount(self):
        super(dym_account_invoice, self)._compute_amount()
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line)
        self.amount_tax = sum(line.amount for line in self.tax_line)
        self.discount_cash = sum(line.discount_cash for line in self.invoice_line)
        self.discount_program = sum(line.discount_program for line in self.invoice_line)
        self.discount_lain = sum(line.discount_lain for line in self.invoice_line)
        self.amount_total = self.amount_untaxed + self.amount_tax + self.amount_bbn

    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_purchase_order-1] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line.price_subtotal',
        'move_id.state',
        'move_id.line_id.account_id.type',
        'move_id.line_id.amount_residual',
        'move_id.line_id.reconcile_id',
        'move_id.line_id.amount_residual_currency',
        'move_id.line_id.currency_id',
        'move_id.line_id.reconcile_partial_id.line_partial_ids.invoice.type',
    )

    def _compute_residual(self):
        self.residual = 0.0
        partial_reconciliations_done = []
        for line in self.sudo().move_id.line_id:
            if (line.account_id.type != 'receivable' and self.type in ['out_invoice']) or (line.account_id.type != 'payable' and self.type in ['in_invoice','in_refund']) or (line.debit > 0 and self.type in ['in_invoice']) or (line.credit > 0 and self.type in ['out_invoice','in_refund']):
                continue
            if line.reconcile_partial_id and line.reconcile_partial_id.id in partial_reconciliations_done:
                continue
            if line.currency_id == self.currency_id:
                line_amount = line.amount_residual_currency if line.currency_id else line.amount_residual
            else:
                from_currency = line.company_id.currency_id.with_context(date=line.date)
                line_amount = from_currency.compute(line.amount_residual, self.currency_id)
            if line.reconcile_partial_id:
                partial_reconciliation_invoices = set()
                for pline in line.reconcile_partial_id.line_partial_ids:
                    if pline.invoice and self.type == pline.invoice.type and ((pline.debit > 0 and self.type in ['out_invoice','in_refund']) or (pline.credit > 0 and self.type in ['in_invoice','out_refund'])):
                        partial_reconciliation_invoices.update([pline.invoice.id])
                line_amount = self.currency_id.round(line_amount / len(partial_reconciliation_invoices))
                partial_reconciliations_done.append(line.reconcile_partial_id.id)
            
            self.residual += line_amount
        self.residual = max(self.residual, 0.0)

    residual = fields.Float(string='Balance', digits=dp.get_precision('Account'), compute='_compute_residual', store=False, help="Remaining amount due.")
    discount_cash = fields.Float(string='Diskon Cash',digits= dp.get_precision('Discount Cash'), compute='_compute_amount', readonly=True)
    discount_program = fields.Float(string='Diskon Program',digits= dp.get_precision('Discount Cash'), compute='_compute_amount', readonly=True)
    discount_lain = fields.Float(string='Diskon Lain',digits= dp.get_precision('Discount Cash'), compute='_compute_amount', readonly=True)
    amount_dp = fields.Float(string='JP Nett',digits= dp.get_precision('Amount JP'), readonly=True)
    account_dp = fields.Many2one('account.account', string='Account JP')
    amount_bbn = fields.Float(string='BBN',digits= dp.get_precision('BBN'), readonly=True)
    account_bbn = fields.Many2one('account.account', string='Account BBN')
    analytic_1 = fields.Many2one('account.analytic.account', string='Account Analytic Company')
    analytic_2 = fields.Many2one('account.analytic.account', string='Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', string='Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', string='Account Analytic Cost Center')
    biro_jasa = fields.Boolean(related='partner_id.biro_jasa', string='Biro Jasa')
    state = fields.Selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('proforma2','Pro-forma'),
            ('open','Validated'),
            ('paid','Paid'),
            ('cancel','Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' when invoice is in Pro-forma status,invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user create invoice,a invoice number is generated.Its in open status till user does not pay invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    amount_untaxed = fields.Float(string='Tax Base', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Tax Amount', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')
    
    _defaults = {
        'analytic_1': _get_analytic_company,
    }


    @api.multi
    def compute_residual(self):
        return self.compute_residual_inv(invoice=self)

    @api.multi
    def compute_residual_all(self):
        return self.compute_residual_inv()

    @api.multi
    def compute_residual_inv(self, end_date=False, invoice=False):
        if invoice:
            invs = invoice
        else:
            invs = self.search([('id','!=',0)])
        for inv in invs:
            residual = 0.0
            partial_reconciliations_done = []
            reconciliations_done = []
            for line in inv.sudo().move_id.line_id:
                if (line.account_id.type != 'receivable' and inv.type in ['out_invoice','out_refund']) or (line.account_id.type != 'payable' and inv.type in ['in_invoice','in_refund']) or (line.debit > 0 and inv.type in ['in_invoice','out_refund']) or (line.credit > 0 and inv.type in ['out_invoice','in_refund']):
                    continue
                if line.reconcile_partial_id and line.reconcile_partial_id.id in partial_reconciliations_done:
                    continue
                if line.reconcile_id and line.reconcile_id.id in reconciliations_done:
                    continue
                if end_date:
                    line_amount = 0
                else:
                    if line.currency_id == inv.currency_id:
                        line_amount = line.amount_residual_currency if line.currency_id else line.amount_residual
                    else:
                        from_currency = line.company_id.currency_id.with_context(date=line.date)
                        line_amount = from_currency.compute(line.amount_residual, inv.currency_id)
                if line.reconcile_partial_id:
                    partial_reconciliation_invoices = set()
                    if end_date:
                        line_amount += line.get_residual_date_based(line.id, end_date)
                    for pline in line.reconcile_partial_id.line_partial_ids:
                        if pline.invoice and inv.type == pline.invoice.type and ((pline.debit > 0 and inv.type in ['out_invoice','in_refund']) or (pline.credit > 0 and inv.type in ['in_invoice','out_refund'])):
                            partial_reconciliation_invoices.update([pline.invoice.id])
                    line_amount = inv.currency_id.round(line_amount / len(partial_reconciliation_invoices))
                    partial_reconciliations_done.append(line.reconcile_partial_id.id)
                if line.reconcile_id and invoice:
                    reconciliation_invoices = set()
                    if end_date:
                        line_amount += line.get_residual_date_based(line.id, end_date)
                    for pline in line.reconcile_id.line_id:
                        if pline.invoice and inv.type == pline.invoice.type and ((pline.debit > 0 and inv.type in ['out_invoice','in_refund']) or (pline.credit > 0 and inv.type in ['in_invoice','out_refund'])):                            
                            reconciliation_invoices.update([pline.invoice.id])
                    line_amount = inv.currency_id.round(line_amount / len(reconciliation_invoices))
                    reconciliations_done.append(line.reconcile_id.id)
                if not line.reconcile_id and not line.reconcile_partial_id:
                    line_amount = line.debit + line.credit
                residual += line_amount
            residual = max(residual, 0.0)
            if inv.residual != residual and not end_date:
                inv.write({'residual':residual})
            if invoice:
                return residual
        return True

    def _get_pricelist(self):
        if self.division == 'Unit' :
            current_pricelist = self.branch_id.pricelist_unit_purchase_id.id
        elif self.division == 'Sparepart' :
            current_pricelist = self.branch_id.pricelist_part_purchase_id.id
        else :
            current_pricelist = self.partner_id.property_product_pricelist_purchase.id
        return current_pricelist
    
    def purchase_unit(self, cr, uid, ids, contex=None):
        invoice_id = self.browse(cr, uid, ids)
        if invoice_id.division == 'Unit' and invoice_id.branch_id.default_supplier_id == invoice_id.partner_id and all(line.purchase_line_id.id <> False for line in invoice_id.invoice_line) :
            return True
        return False
    
    def action_invoice_bb_create(self, cr, uid, ids, contex=None):
        invoice_id = self.browse(cr, uid, ids)
        if invoice_id.purchase_unit() :
            if invoice_id.branch_id.blind_bonus_beli <= 0 :
                raise osv.except_osv(('Perhatian'), ('Amount Blind Bonus cabang tidak boleh 0, silahkan konfigurasi ulang'))
            
            obj_branch_config = self.pool.get('purchase.order')._get_branch_journal_config(cr, uid, invoice_id.branch_id.id)
            if not (obj_branch_config['dym_po_journal_blind_bonus_beli_id'] or obj_branch_config['dym_po_account_blind_bonus_beli_dr_id'].id or obj_branch_config['dym_po_account_blind_bonus_beli_cr_id'].id):
                raise osv.except_osv(('Perhatian'), ('Account Blind Bonus Belum diisi atau belum lengkap, silahkan konfigurasi ulang'))
            
            total_qty = 0
            for line in invoice_id.invoice_line :
                total_qty += line.quantity
                
            inv_bb_line_vals = [(0, 0, {
                'name': 'Blind Bonus Beli',
                'quantity': total_qty,
                'origin': invoice_id.origin,
                'price_unit': invoice_id.branch_id.blind_bonus_beli,
                'account_id': obj_branch_config['dym_po_account_blind_bonus_beli_cr_id'].id
                })]
            
            inv_bb_vals = {
                'name': invoice_id.number,
                'origin': invoice_id.origin,
                'branch_id': invoice_id.branch_id.id,
                'division': invoice_id.division,
                'partner_id': invoice_id.partner_id.id,
                'date_invoice': invoice_id.date_invoice,
                'document_date': datetime.now(),
                'reference_type': 'none',
                'type': 'out_invoice',
                'tipe': 'blind_bonus_beli',
                'journal_id': obj_branch_config['dym_po_journal_blind_bonus_beli_id'].id,
                'account_id': obj_branch_config['dym_po_account_blind_bonus_beli_dr_id'].id,
                'invoice_line': inv_bb_line_vals,
                }
            
            id_inv_bb = self.create(cr, uid, inv_bb_vals)
            workflow.trg_validate(uid, 'account.invoice', id_inv_bb, 'invoice_open', cr)
            return id_inv_bb
        return False

    def invoice_validate(self, cr, uid, ids, context=None):
        invoice_id = self.browse(cr, uid, ids, context=context)
        if invoice_id.state == 'open':
            return True
        res = super(dym_account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        if invoice_id.type == "in_invoice" and invoice_id.tipe == 'purchase' and invoice_id.state == 'open':
            product_over_qty = []
            for invoice_line in invoice_id.invoice_line :
                if invoice_line.purchase_line_id :
                    purchase_line_id = invoice_line.purchase_line_id
                    current_invoiced = purchase_line_id.qty_invoiced
                    a = purchase_line_id.id
                    obj_inv_line = self.pool.get('account.invoice.line')

                    inv_line_ids = obj_inv_line.search(cr, uid, [('purchase_line_id', '=', a),
                                                                 ('invoice_id.state', '=', 'is_refund')])

                    for line in inv_line_ids:
                        inv_line = obj_inv_line.browse(cr, uid, line)
                        invoice_refund += inv_line.quantity
                        if invoice_refund:
                            new_invoiced = invoice_line.quantity + current_invoiced - invoice_refund
                        else :
                            new_invoiced = invoice_line.quantity + current_invoiced
               	        if new_invoiced > purchase_line_id.product_qty :
                            raise Warning(("Quantity product '%s' melebihi quantity PO !\nQty invoice: '%s', Qty PO: '%s'" %(purchase_line_id.product_id.name, int(new_invoiced), int(purchase_line_id.product_qty))))
                        elif new_invoiced < purchase_line_id.product_qty :
                            purchase_line_id.write({'qty_invoiced':new_invoiced, 'invoiced':False})
                        else :
                            purchase_line_id.write({'qty_invoiced':new_invoiced, 'invoiced':True})

        purchase_order_obj = self.pool.get('purchase.order')
        po_ids = purchase_order_obj.search(cr, uid, [('invoice_ids', 'in', ids)], context=context)
        if not purchase_order_obj.check_access_rights(cr, uid, 'read', raise_exception=False):
            user_id = SUPERUSER_ID
        else:
            user_id = uid
        for order in purchase_order_obj.browse(cr, uid, po_ids, context=context):
            for line in order.order_line:
                if line.qty_invoiced < line.product_qty and line.invoiced == True:
                    line.write({'invoiced':False})
            workflow.trg_write(user_id, 'purchase.order', order.id, cr)
        return res


    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        move_lines = super(dym_account_invoice,self).finalize_invoice_move_lines(move_lines)
        obj_branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if not obj_branch_config:
            raise osv.except_osv(('Perhatian !'), ("Tidak Ditemukan konfigurasi jurnal Cabang, Silahkan konfigurasi dulu"))
        name = self.supplier_invoice_number or self.name or '/'
        for line in move_lines :
            if line[2]['account_id'] == obj_branch_config.dealer_so_account_bbn_jual_id.id:
                line[2]['partner_id'] = self.qq_id.id or self.partner_id.id or line[2]['partner_id']
            if self.type in ('in_invoice', 'out_refund'):
                if line[2]['credit'] == self.amount_total - self.amount_bbn and line[2]['name'] == name[:64]:
                    line[2]['analytic_account_id'] = self.analytic_4.id
            else:
                if line[2]['debit'] == self.amount_total - self.amount_bbn and line[2]['name'] == name[:64]:
                    line[2]['analytic_account_id'] = self.analytic_4.id
            if 'force_partner_id' in line[2] and line[2]['force_partner_id']:
                line[2]['partner_id'] = line[2]['force_partner_id']
        if self.type=='in_invoice': ## DEALER & MAIN DEALER ##
            if self.discount_cash>0 or self.discount_lain>0 or self.discount_program>0:
                date = datetime.now().strftime('%Y-%m-%d')
                for line in move_lines :
                    if line[2]['credit'] > 0:
                        date = line[2]['date']
                        line[2]['credit'] = self.amount_total
                        break
                        
        if self.amount_bbn > 0:
            debit = 0
            credit = 0
            for line in move_lines :
                if line[2]['debit'] == self.amount_total - self.amount_bbn and line[2]['name'] == name[:64]:
                    line[2]['debit'] = self.amount_total
                    credit = self.amount_bbn
                    break
                elif line[2]['credit'] == self.amount_total - self.amount_bbn and line[2]['name'] == name[:64]:
                    line[2]['credit'] = self.amount_total
                    debit = self.amount_bbn
                    break
            account_bbn = self.account_bbn
            if not self.account_bbn:
                if not obj_branch_config.dealer_so_account_bbn_jual_id.id:
                    raise osv.except_osv(('Perhatian !'), ("Konfigurasi account BBN cabang belum lengkap, silahkan setting dulu"))
                account_bbn = obj_branch_config.dealer_so_account_bbn_jual_id
                self.write({'account_bbn':account_bbn.id})
            move_lines.append((0,0,{
                'name': 'BBN '+ self.name,
                'ref' : 'BBN '+ self.name, 
                'partner_id': self.qq_id.id or self.partner_id.id,
                'account_id': account_bbn.id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'debit': debit,
                'credit': credit,
                'branch_id': self.branch_id.id,
                'division': self.division,
                'analytic_account_id':self.analytic_4.id,  
            }))
        for x in move_lines:
            v1,v2,v3 = x
            account_name = self.env['account.account'].browse(v3['account_id'])[0].name
        return move_lines
    
    @api.onchange('discount_cash','discount_program','discount_lain')
    def onchange_discount(self):
        if self.discount_cash < 0  or self.discount_lain<0 or self.discount_program<0:
            self.discount_cash = 0
            self.discount_lain = 0 
            self.discount_program = 0
            return {'warning':{'title':'Perhatian !','message':'Discount tidak boleh negatif'}}
        
    @api.multi
    def renew_price(self):
        po_id = self.env['purchase.order'].search([('name','=',self.origin)])
        if self.state != 'draft':
            raise osv.except_osv(('Perhatian !'), ("Update price hanya boleh ketika statusnya draft saja!"))
        pricelist_id = False
        if po_id:
            pricelist_id = po_id.pricelist_id
        elif str(self.origin).split('-')[0] == 'POR':
            if self.division == 'Unit':
                pricelist_id = self.branch_id.pricelist_unit_purchase_id
            elif self.division == 'Sparepart':
                pricelist_id = self.branch_id.pricelist_part_purchase_id
        if pricelist_id:
            for line in self.invoice_line:
                price_unit = pricelist_id.price_get(line.product_id.id,line.quantity)[pricelist_id.id]
                if line.price_unit != price_unit:
                    line.price_unit = price_unit

        self.button_reset_taxes()
        return True
    # supplier_invoice_number = fields.Char(copy=False)
    @api.one
    @api.constrains('supplier_invoice_number')
    def _check_unique_supplier_invoice_number_insensitive(self):
        print 'test*********'
        if (
                    self.supplier_invoice_number and
                        self.type in ('in_invoice', 'in_refund')):
            same_supplier_inv_num = self.search([
                ('commercial_partner_id', '=', self.commercial_partner_id.id),
                ('type', 'in', ('in_invoice', 'in_refund')),
                ('supplier_invoice_number',
                 '=ilike',
                 self.supplier_invoice_number),
                ('id', '!=', self.id),
            ])
            if same_supplier_inv_num:
                raise osv.except_osv(('Perhatian !'), ("The invoice/refund with supplier invoice number '%s'already exists in Odoo" %same_supplier_inv_num[0].supplier_invoice_number))
                # raise ValidationError(
                #     _("The invoice/refund with supplier invoice number '%s' "
                #       "already exists in Odoo under the number '%s' "
                #       "for supplier '%s'.") % (
                #         same_supplier_inv_num[0].supplier_invoice_number,
                #         same_supplier_inv_num[0].number or '-',
                #         same_supplier_inv_num[0].partner_id.display_name))

class dym_account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'
    
    def _get_pricelist(self, partner_id, branch_id, division, type):
        current_pricelist = False
        if division == 'Unit' and branch_id:
            branch = self.env['dym.branch'].browse(branch_id)
            if type in ('in_invoice','in_refund'):
                current_pricelist = branch.pricelist_unit_purchase_id.id
            elif type in ('out_invoice','out_refund'):
                current_pricelist = branch.pricelist_unit_sales_id.id
        elif division == 'Sparepart' and branch_id:
            branch = self.env['dym.branch'].browse(branch_id)
            if type in ('in_invoice','in_refund'):
                current_pricelist = branch.pricelist_part_purchase_id.id
            elif type in ('out_invoice','out_refund'):
                current_pricelist = branch.pricelist_part_sales_id.id
        else :
            if type in ('in_invoice','in_refund'):
                partner = self.env['res.partner'].browse(partner_id)
                current_pricelist = partner.property_product_pricelist_purchase.id
        return current_pricelist

    def price_unit_change(self, cr, uid, ids, price_unit, create_manual_invoice):
        value = {}
        value['create_manual_dummy'] = create_manual_invoice
        if not price_unit:
           value['price_unit_show'] = 0
           value['price_unit'] = 0
        else:
           value['price_unit_show'] = price_unit
           value['price_unit'] = price_unit
        return {'value':value}

    @api.multi
    def product_id_change(self, product, uom_id, qty=0, name='', type='out_invoice',
            partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
            company_id=None):
        res = super(dym_account_invoice_line, self).product_id_change(product, uom_id, qty=qty, name=name, type=type,
            partner_id=partner_id, fposition_id=fposition_id, price_unit=price_unit, currency_id=currency_id,
            company_id=company_id)
        if product and 'branch_id' in self._context and 'division' in self._context:
            current_pricelist = self._get_pricelist(partner_id, self._context['branch_id'], self._context['division'], type)
            if current_pricelist:
                current_price = self.pool.get('product.pricelist').price_get(self._cr,self._uid,[current_pricelist], product, 1)[current_pricelist]
                res['value'].update({'price_unit': current_price})
        return res

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_id', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id','discount_amount','discount_cash','discount_program','discount_lain')
    def _compute_price(self):
        # price = (self.price_unit * self.quantity) * (1 - (self.discount or 0.0) / 100.0) - self.discount_amount - self.discount_cash - self.discount_lain - self.discount_program
        price = (self.price_unit * self.quantity) - self.discount_amount - self.discount_cash - self.discount_lain - self.discount_program
        taxes = self.invoice_line_tax_id.compute_all(price, 1, product=self.product_id, partner=self.invoice_id.partner_id)


        # def compute_all(self, cr, uid, taxes, price_unit, quantity, product=None, partner=None, force_excluded=False):

        self.price_subtotal = taxes['total']
        if self.invoice_id:
            self.price_subtotal = self.invoice_id.currency_id.round(self.price_subtotal)
    
    @api.model
    def _default_price_unit(self):
        if not self._context.get('check_total'):
            return 0
        total = self._context['check_total']
        for l in self._context.get('invoice_line', []):
            if isinstance(l, (list, tuple)) and len(l) >= 3 and l[2]:
                vals = l[2]
                # price = (vals.get('price_unit', 0)*vals.get('quantity')) * (1 - vals.get('discount', 0) / 100.0) - vals.get('discount_amount', 0) - vals.get('discount_cash', 0) - vals.get('discount_lain', 0) - vals.get('discount_program', 0)
                price = (vals.get('price_unit', 0)*vals.get('quantity')) - vals.get('discount_amount', 0) - vals.get('discount_cash', 0) - vals.get('discount_lain', 0) - vals.get('discount_program', 0)
                total = total - price
                taxes = vals.get('invoice_line_tax_id')
                if taxes and len(taxes[0]) >= 3 and taxes[0][2]:
                    taxes = self.env['account.tax'].browse(taxes[0][2])
                    tax_res = taxes.compute_all(price, 1,
                        product=vals.get('product_id'), partner=self._context.get('partner_id'))
                    for tax in tax_res['taxes']:
                        total = total - tax['amount']
        return total
        
    @api.one
    @api.depends('product_id')
    def _get_product_category(self):
        product_category = self.product_id.categ_id.get_root_name()
        self.product_category = product_category

    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_purchase_order-2] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    @api.one
    @api.depends('product_id')
    def _get_product_template(self):
        self.template_id = self.product_id.product_tmpl_id

    product_category = fields.Char('Product Category', compute="_get_product_category")
    discount_amount = fields.Float(string='Diskon',digits= dp.get_precision('Discount'),default=0.0)
    price_unit_show = fields.Float(related='price_unit', string='Unit Price')
    quantity_show = fields.Float(related='quantity', string='Quantity')
    discount_cash = fields.Float(string='Diskon Cash',digits= dp.get_precision('Discount Cash'),default=0.0)
    discount_program = fields.Float(string='Diskon Program',digits= dp.get_precision('Discount Cash'),default=0.0)
    discount_lain = fields.Float(string='Diskon Lain',digits= dp.get_precision('Discount Cash'),default=0.0)
    analytic_1 = fields.Many2one('account.analytic.account', string='AA-Company')
    analytic_2 = fields.Many2one('account.analytic.account', 'AA-Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'AA-Branch')
    force_partner_id = fields.Many2one('res.partner', 'Force Partner')
    create_manual_dummy = fields.Boolean('Create Manual')
    template_id = fields.Many2one('product.template', 'Tipe', compute="_get_product_template", store=True)
    product_id = fields.Many2one('product.product', 'Product')
    uos_id = fields.Many2one('product.uom', string='UOM', ondelete='set null', index=True)
    discount = fields.Float(string='Diskon (%)', digits= dp.get_precision('Discount'), default=0.0)
    biro_jasa = fields.Boolean(related='invoice_id.biro_jasa', string='Biro Jasa')
    division = fields.Selection(related='invoice_id.division', string='Division')

    _defaults = {
        'analytic_1': _get_analytic_company,
    }

    @api.onchange('discount_amount')
    def onchange_discount_amount(self):
        if self.discount >= 0:
            price = (self.price_unit * self.quantity)
            discount_amount = (price*self.discount)/100
            if self.discount_amount != discount_amount:
                self.discount = 0

    @api.onchange('discount')
    def onchange_discount_persen(self):
        if self.discount > 100:
            self.discount = 0
            self.discount_amount = 0
            return {'warning': {'title': 'perhatian!', 'message':'maksimal discount cash 100%'}}
        elif self.discount < 0:
            self.discount = 0
            self.discount_amount = 0
            return {'warning': {'title': 'perhatian!', 'message': 'tidak boleh input nilai negatif'}}
        elif self.discount > 0:
            price = (self.price_unit * self.quantity)
            self.discount_amount = (price*self.discount)/100

    @api.onchange('discount_amount','discount','discount_cash','discount_lain','discount_program')
    def onchange_discount(self):
        total_discount = sum([
            self.discount_amount,
            self.price_unit_show and (self.discount * self.price_unit_show / 100.0) or 0.0,
            self.discount_cash,
            self.discount_lain,
            self.discount_program
        ])
        if total_discount > self.price_unit_show:
            return {
                'warning':{
                    'title':'Perhatian !',
                    'message':'Total Discount tidak boleh melebihi total harga'
                },
                'value':{
                    'discount_amount':0.0,
                    'discount_cash':0.0,
                    'discount_lain':0.0,
                    'discount_program':0.0,
                }
            }

        if self.discount_amount < 0  or self.discount<0 or self.discount_cash < 0  or self.discount_lain<0 or self.discount_program<0:
            self.discount_amount = 0
            self.discount = 0 
            self.discount_cash = 0
            self.discount_lain = 0 
            self.discount_program = 0
            return {'warning':{'title':'Perhatian !','message':'Discount tidak boleh negatif'}}
    
    @api.model
    def move_line_get(self, invoice_id):
        inv = self.env['account.invoice'].browse(invoice_id)
        currency = inv.currency_id.with_context(date=inv.date_invoice)
        company_currency = inv.company_id.currency_id
        res = []
        for line in inv.invoice_line:
            mres = self.move_line_get_item(line)
            mres['invl_id'] = line.id
            res.append(mres)
            tax_code_found = False
            price = (line.price_unit * line.quantity) - line.discount_amount - line.discount_cash - line.discount_lain - line.discount_program
            taxes = line.invoice_line_tax_id.compute_all(
                price,
                1, line.product_id, inv.partner_id)['taxes']
            for tax in taxes:
                if inv.type in ('out_invoice', 'in_invoice'):
                    tax_code_id = tax['base_code_id']
                    tax_amount = tax['price_unit'] * 1 * tax['base_sign']
                else:
                    tax_code_id = tax['ref_base_code_id']
                    tax_amount = tax['price_unit'] * 1 * tax['ref_base_sign']

                if tax_code_found:
                    if not tax_code_id:
                        continue
                    res.append(dict(mres))
                    res[-1]['price'] = 0.0
                    res[-1]['account_analytic_id'] = False
                elif not tax_code_id:
                    continue
                tax_code_found = True

                res[-1]['tax_code_id'] = tax_code_id
                res[-1]['tax_amount'] = currency.compute(tax_amount, company_currency)
        return res
        
class dym_account_invoice_tax(models.Model):
    _inherit = "account.invoice.tax"
    
    base = fields.Float(string='Tax Base', digits=dp.get_precision('Account'))
    amount = fields.Float(string='Tax Amount', digits=dp.get_precision('Account'))

    @api.model
    def move_line_get(self, invoice_id):
        res = super(dym_account_invoice_tax, self).move_line_get(invoice_id)
        for line in res:
            line['account_analytic_id'] = line['account_analytic_id'] or self.env['account.invoice'].browse(invoice_id).analytic_4.id
        return res

    @api.v8
    def compute(self, invoice):
        tax_grouped = {}
        currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.context_today(invoice))
        company_currency = invoice.company_id.currency_id
        analytic_4 = invoice.analytic_4.id
        for line in invoice.invoice_line:
            price = (line.price_unit * line.quantity) - line.discount_amount - line.discount_cash - line.discount_lain - line.discount_program
            taxes = line.invoice_line_tax_id.compute_all(
                price,
                1, line.product_id, invoice.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'invoice_id': invoice.id,
                    'name': tax['name'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'base': currency.round(tax['price_unit'] * 1),
                }
                if invoice.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = analytic_4
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['ref_base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['ref_tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = analytic_4

                if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = analytic_4

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])
            t['tax_amount'] = currency.round(t['tax_amount'])
        return tax_grouped

    
    
