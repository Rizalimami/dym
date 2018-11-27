from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import openerp.addons.decimal_precision as dp
from openerp import workflow, SUPERUSER_ID
import uuid
from lxml import etree

class dym_purchase_order(osv.osv):
    _inherit = 'purchase.order'

    def action_cancel_draft(self, cr, uid, ids, context=None):
        res = super(dym_purchase_order, self).action_cancel_draft(cr, uid, ids, context=context)
        so = self.browse(cr, uid, ids, context=context)[0]
        newname = datetime.now().strftime('%Y%m%d%H%M%S')
        new_id = self.copy(cr, uid, ids[0], context=context)
        self.write(cr, uid, [new_id], {
            'set2draft': False, 
            'state':'cancel', 
            'name':'%s (cancel)' % so.name
        })
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        default = dict(context or {})
        so = self.browse(cr, uid, id, context=context)
        default.update(
            sequence_id=_(False),
            name=_("%s (canceled)") % (so['name'] or ''))
        return super(dym_purchase_order, self).copy(cr, uid, id, default, context=context)

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_purchase_order, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        for field in res['fields']:
            if field == 'division':
                if 'menu' in context and context['menu'] == 'showroom':
                    res['fields'][field]['selection'] = [('Unit','Showroom'), ('Umum','General')]

                if 'menu' in context and context['menu'] == 'workshop':
                    res['fields'][field]['selection'] = [('Sparepart','Workshop'), ('Umum','General')]

                if 'menu' in context and context['menu'] == 'general_affair':
                    res['fields'][field]['selection'] = [('Unit','Showroom'), ('Sparepart','Workshop'), ('Umum','General')]

            # if field == 'order_line':
            #     doc = etree.XML(res['arch'])      
            #     nodes_unit_price = doc.xpath("//field[@name='order_line']/tree/field[@name='price_unit']")
            #     for node in nodes_unit_price:
            #         node.set('readonly', '0')
            #     res['arch'] = etree.tostring(doc)
        return res

    def _get_backorders(self, cr, uid, ids, res):
        re_fetch = False
        picking_ids = []
        for key, value in res.items():
            picking_ids = picking_ids + value

        if picking_ids :
            query = """
            SELECT a.id, b.id FROM stock_picking a JOIN stock_picking b ON b.backorder_id = a.id
                WHERE a.id in %s
                GROUP BY a.id, b.id
                   
            """
            cr.execute(query, (tuple(picking_ids), ))
            picks = cr.fetchall()

            for pick_id, backorder_id in picks:
                for key, value in res.items():
                    if pick_id in value and backorder_id not in value :
                        res[key].append(backorder_id)
                        re_fetch = True
            if re_fetch :
                res = self._get_backorders(cr, uid, ids, res)
        return res
    
    def _get_picking_ids(self, cr, uid, ids, field_names, args, context=None):
        res = super(dym_purchase_order,self)._get_picking_ids(cr, uid, ids, field_names, args, context=context)
        res = self._get_backorders(cr, uid, ids, res)
        return res
    
    def _get_picking_type_ids(self, cr, uid, context=None):
        obj_user = self.pool.get('res.users').browse(cr, uid, uid)
        branch_ids = []
        for x in obj_user.area_id.branch_ids :
            branch_ids.append(x.id)
        if branch_ids :
            if len(branch_ids) > 1 :
                return False
            else :
                picking_type_id = self.pool.get('stock.picking.type').search(cr, uid, [
                                                                            ('branch_id','=',branch_ids[0]),
                                                                            ('code','=','incoming'),
                                                                            ])
                if not picking_type_id:
                    raise osv.except_osv(('Error'), ("Tidak ditemukan picking type untuk branch %s")%(obj_user.area_id.branch_ids[0].name))
                return picking_type_id[0]
        return False
    
    def _get_default_branch(self,cr,uid,context=None):
        user_browse = self.pool.get('res.users').browse(cr,uid,uid)
        branch_ids = self.pool.get('dym.branch').search(cr,uid,[('company_id','=',user_browse.company_id.id)],context=context)
        user_branch_ids = user_browse.branch_ids 
        for branch in user_branch_ids:
            if branch.id in branch_ids and branch.branch_type!='HO':
                return branch.id
        return False

    def _get_analytic_company(self,cr,uid,context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        if 'active_model' in context and context['active_model'] == 'purchase.requisition' and 'active_id' in context:
            pr = self.pool.get('purchase.requisition').browse(cr, uid, context['active_id'])
            if pr.proposal_id.analytic_1.company_id.id == company.id:
                return pr.proposal_id.analytic_1.id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_purchase_order-3] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    def _get_analytic_bisnis_unit_proposal(self,cr,uid,context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        if 'active_model' in context and context['active_model'] == 'purchase.requisition' and 'active_id' in context:
            pr = self.pool.get('purchase.requisition').browse(cr, uid, context['active_id'])
            if pr.proposal_id.analytic_1.company_id.id == company.id:
                return pr.proposal_id.analytic_2.id
        return False

    def _get_analytic_branch_proposal(self,cr,uid,context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        if 'active_model' in context and context['active_model'] == 'purchase.requisition' and 'active_id' in context:
            pr = self.pool.get('purchase.requisition').browse(cr, uid, context['active_id'])
            if pr.proposal_id.analytic_1.company_id.id == company.id:
                return pr.proposal_id.analytic_3.id
        return False

    def _get_analytic_cost_center_proposal(self,cr,uid,context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        if 'active_model' in context and context['active_model'] == 'purchase.requisition' and 'active_id' in context:
            pr = self.pool.get('purchase.requisition').browse(cr, uid, context['active_id'])
            if pr.proposal_id.analytic_1.company_id.id == company.id:
                return pr.proposal_id.analytic_4.id
        return False

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
               val1 += line.price_subtotal
               for c in self.pool.get('account.tax').compute_all(cr, uid, line.taxes_id, line.price_unit, line.product_qty, line.product_id, order.partner_id)['taxes']:
                    val += c.get('amount', 0.0)
            amount_tax = val
            amount_untaxed = val1
            if cur:
                amount_tax = cur_obj.round(cr, uid, cur, val)
                amount_untaxed = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_tax']=amount_tax
            res[order.id]['amount_untaxed']=amount_untaxed
            res[order.id]['amount_total']=res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res

    def _set_minimum_planned_date(self, cr, uid, ids, name, value, arg, context=None):
        if not value: return False
        if type(ids)!=type([]):
            ids=[ids]
        pol_obj = self.pool.get('purchase.order.line')
        for po in self.browse(cr, uid, ids, context=context):
            if po.order_line:
                pol_ids = pol_obj.search(cr, uid, [
                    ('order_id', '=', po.id), '|', ('date_planned', '=', po.minimum_planned_date), ('date_planned', '<', value)
                ], context=context)
                pol_obj.write(cr, uid, pol_ids, {'date_planned': value}, context=context)
        self.invalidate_cache(cr, uid, context=context)
        return True

    def _minimum_planned_date(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        purchase_obj=self.browse(cr, uid, ids, context=context)
        for purchase in purchase_obj:
            res[purchase.id] = False
            if purchase.order_line:
                min_date=purchase.order_line[0].date_planned
                for line in purchase.order_line:
                    if line.state == 'cancel':
                        continue
                    if line.date_planned < min_date:
                        min_date=line.date_planned
                res[purchase.id]=min_date
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('purchase.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    def _get_create_invoice(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = False
            cancelled_invoice = 0
            for invoice in order.invoice_ids:
                if invoice.state == 'cancel':
                    cancelled_invoice += 1
            if order.invoice_count - cancelled_invoice <= 0:
                res[order.id] = True
        return res

    def _get_purchase_order(self, cr, uid, ids, context=None):
        result = {}
        for order in self.browse(cr, uid, ids, context=context):
            result[order.id] = True
        return result.keys()
        
    _columns = {
        'minimum_planned_date':fields.function(_minimum_planned_date, fnct_inv=_set_minimum_planned_date, string='Expired Date', type='date', select=True, help="This is computed as the minimum scheduled date of all purchase order lines' products.",
            store = {
                'purchase.order.line': (_get_order, ['date_planned'], 10),
                'purchase.order': (_get_purchase_order, ['order_line'], 10),
            }
        ),
        'name': fields.char('PO Ref.', required=True, select=True, copy=False,
                    help="Unique number of the purchase order, "
                         "computed automatically when the purchase order is created."),
        'branch_id':fields.many2one('dym.branch','Branch', required=True, domain="[('company_id','=',company_id)]"),

        'asset': fields.boolean('Asset', readonly=True, states={'draft': [('readonly', False)]}),
        'prepaid': fields.boolean('Prepaid', readonly=True, states={'draft': [('readonly', False)]}),

        # 'division': fields.selection(_get_division, string="Division", store=True, change_default=True, select=True, required=True),
        'division':fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division', change_default=True, select=True, required=True),
        'purchase_order_type_id':fields.many2one('dym.purchase.order.type','PO Type'),
        'editable_price': fields.boolean(string='Editable Price'),
        'start_date':fields.date('Start Date'),
        'end_date':fields.date('End Date'),
        'po_ref':fields.char('PO Ref'),
        'dealer_id':fields.many2one('res.partner','Dealer'),
        'back_order':fields.char('Back Order'),
        'salesman_id':fields.many2one('res.users','Salesman'),
        'no_claim':fields.char('No. Claim'),
        'ship_to':fields.char('Ship To'),
        'delivery_date':fields.date('Delivery Date'),
        'customer_id':fields.many2one('res.partner','Customer'),
        'post_code':fields.char('Post Code'),
        'type_motor_id':fields.many2one('product.product','Type Motor'),
        'assembling':fields.char('Year of Assembling'),
        'of_the_road':fields.selection([('y','Y'),('n','N')],'Vehicle of The Road'),
        'return_service':fields.selection([('y','Y'),('n','N')],'Job Return Service'),
        'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
        'confirm_date':fields.datetime('Confirmed on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),      
        'date_order':fields.datetime('PO Date'),
        'picking_ids': fields.function(_get_picking_ids, method=True, type='one2many', relation='stock.picking', string='Picking List', help="This is the list of receipts that have been generated for this purchase order."),
        'partner_type':fields.many2one('dym.partner.type',string="Partner Type",domain="[('division','like',division)]"),
        'partner_cabang': fields.many2one('dym.cabang.partner','Cabang Supplier'),
        'analytic_1': fields.many2one('account.analytic.account','Account Analytic Company'),
        'analytic_2': fields.many2one('account.analytic.account','Account Analytic Bisnis Unit'),
        'analytic_3': fields.many2one('account.analytic.account','Account Analytic Branch'),
        'analytic_4': fields.many2one('account.analytic.account','Account Analytic Cost Center'),
        'create_invoice': fields.function(_get_create_invoice, type="boolean", string='Create Invoice',
            store={
                'purchase.order': (lambda self, cr, uid, ids, c={}: ids, ['invoice_ids'], 10),
            }, help="Create Invoice"),
        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tax Base',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The amount without tax", track_visibility='always'),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The tax amount"),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total (Rp)',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The total amount"),
        # 'wo_ids': fields.many2many('dym.work.order','po_wo_rel','po_id','wo_id', 'Work Order Reference'),
        # 'so_ids': fields.many2many('sale.order','po_so_rel','po_id','so_id', 'Sales Memo Reference'),
        'wo_id': fields.many2one('dym.work.order', 'Work Order Reference'),
        'so_id': fields.many2one('sale.order', 'Sales Memo Reference'),
        'hutang_lain_id': fields.many2one('account.voucher', 'Customer Deposit Reference'),
        'dealer_spk_id': fields.many2one('dealer.spk', 'Dealer Memo Reference'),
        'mandatory_so_wo' : fields.related('purchase_order_type_id','mandatory_so_wo',type='boolean',string="Mandatory SO/WO"),
        'mandatory_hutang_lain' : fields.related('purchase_order_type_id','mandatory_hutang_lain',type='boolean',string="Mandatory Customer Deposit"),
        'sugor_ids': fields.many2many('dym.ranking','po_sugor_rel','po_id','sugor_id', 'Suggestion Order'),
        'set2draft': fields.boolean('Set to Draft OK?', default=True),
    }
    
    _defaults = {
        'name': '/',
        'branch_id': _get_default_branch,
        'salesman_id': lambda obj, cr, uid, context:uid,
        'journal_id': False,
        'date_order': fields.datetime.now,
        'analytic_1':_get_analytic_company,
        'analytic_2':_get_analytic_bisnis_unit_proposal,
        'analytic_3':_get_analytic_branch_proposal,
        'analytic_4':_get_analytic_cost_center_proposal,
        'invoice_method': 'manual',
    }
    
    def create(self, cr, uid, vals, context=None):
        if 'order_line' in vals and vals['division'] == 'Unit':
            no_ksu = []
            for item in vals['order_line']:
                prod = self.pool.get('product.product').browse(cr, uid, item[2]['product_id'])
                if not prod.extras_line:
                    no_ksu.append(prod.product_tmpl_id.name + ' (%s)' % prod.attribute_value_ids[0].name)
            if no_ksu:
                raise osv.except_osv(('Perhatian !'), ("Produk %s tidak memiliki KSU, silahkan cek terlebih dahulu !" % ' ,'.join(no_ksu)))

        temporary_name = str(uuid.uuid4())
        vals['name'] = temporary_name
        vals['date_order'] = datetime.today()
        res = super(dym_purchase_order, self).create(cr, uid, vals, context=context)
        return res
    
    def has_stockable_product(self, cr, uid, ids, *args):
        res = super(dym_purchase_order,self).has_stockable_product(cr,uid,ids,*args)
        for order in self.browse(cr, uid, ids):
            if not order.asset and not order.prepaid:
                for order_line in order.order_line:
                    if order_line.product_id and order_line.product_id.type in ('product', 'consu'):
                        return True
        return False

    def change_sugor_ref(self,cr,uid,ids,sugor_ids,division,partner_id,branch_id,context=None):
        dom={}        
        val={}
        po_line_obj = self.pool.get('purchase.order.line')
        if sugor_ids:
            date_order = datetime.strftime(datetime.today(), "%Y-%m-%d %H:%M:%S")
            branch = self.pool.get('dym.branch').browse(cr, uid, branch_id)
            sugor_ids = self.resolve_2many_commands(cr, uid, 'sugor_ids', sugor_ids, ['id'], context)
            ar_ids = []
            for l in sugor_ids:
                if isinstance(l, dict):
                    ar_ids += [l['id']]
            if (not division or not branch_id) and ar_ids:
                warning = {'title':'Perhatian','message':'Mohon lengkapi division dan branch terlebih dahulu !'}
                return {'value':val, 'warning':warning}
            supplier = self.pool.get('res.partner').browse(cr, uid, partner_id)
            lines = []
            mapped_product = self.pool.get('dym.ranking').browse(cr, uid, ar_ids).mapped('rank_line').filtered(lambda r: r.check_order == True and r.suggestion_order_final > 0)
            for rank_line in mapped_product:                
                pricelist = False
                if division == 'Unit':
                    if not branch.pricelist_unit_purchase_id :
                        warning = {'title':'Perhatian','message':'Silahkan setting Pricelist Beli Unit di Branch terlebih dahulu !'}
                        return {'value':val, 'warning':warning}
                    else :
                        pricelist = branch.pricelist_unit_purchase_id.id
                elif division == 'Sparepart' : 
                    if not branch.pricelist_part_purchase_id :
                        warning = {'title':'Perhatian','message':'Silahkan setting Pricelist Beli Sparepart di Branch terlebih dahulu !'}
                        return {'value':val, 'warning':warning}
                    else :
                        pricelist = branch.pricelist_part_purchase_id.id
                else :
                    pricelist = supplier.property_product_pricelist_purchase.id
                if supplier:
                    vals = po_line_obj.onchange_product_id(cr, uid, ids, pricelist, rank_line.product_id.id, rank_line.suggestion_order_final, rank_line.product_id.uom_po_id.id,
                        supplier.id, date_order=date_order,
                        fiscal_position_id=supplier.property_account_position,
                        date_planned=date_order,
                        name=False, price_unit=False, state='draft')['value']
                else:
                    vals = po_line_obj.onchange_product_id(cr, uid, ids, pricelist, rank_line.product_id.id, rank_line.suggestion_order_final, rank_line.product_id.uom_po_id.id,
                        False, date_order=date_order,
                        fiscal_position_id=supplier.property_account_position,
                        date_planned=date_order,
                        name=False, price_unit=False, state='draft')['value']
                categ = rank_line.product_id.categ_id
                while categ.parent_id:
                    categ = categ.parent_id
                vals.update({
                    'template_id': rank_line.product_id.product_tmpl_id.id,
                    'product_id': rank_line.product_id.id,
                    # 'division_dummy': 'Umum' if division in ['Umum','Sparepart'] else '',
                    'division_dummy': division in ['Umum','Sparepart'] and division or '',
                    'categ_id': categ.id,
                    # 'account_analytic_id': requisition_line.account_analytic_id.id,
                    'taxes_id': [(6, 0, vals['taxes_id'])],
                    'state': 'draft'
                })
                lines.append([0,0,vals])
            val['order_line'] = lines
        return {'domain':dom,'value':val}

    def change_so_ref(self,cr,uid,ids,so_id,division,partner_id,context=None):
        dom={}        
        val={}
        po_line_obj = self.pool.get('purchase.order.line')
        if so_id and division == 'Sparepart':
            date_order = datetime.strftime(datetime.today(), "%Y-%m-%d %H:%M:%S")
            so = self.pool.get('sale.order').browse(cr, uid, so_id)
            supplier = self.pool.get('res.partner').browse(cr, uid, partner_id)
            lines = []
            for line in so.order_line:
                pricelist = False
                if so.division == 'Unit':
                    if not so.branch_id.pricelist_unit_purchase_id :
                        warning = {'title':'Perhatian','message':'Silahkan setting Pricelist Beli Unit di Branch terlebih dahulu !'}
                        return {'value':val, 'warning':warning}
                    else :
                        pricelist = so.branch_id.pricelist_unit_purchase_id.id
                elif so.division == 'Sparepart' : 
                    if not so.branch_id.pricelist_part_purchase_id :
                        warning = {'title':'Perhatian','message':'Silahkan setting Pricelist Beli Sparepart di Branch terlebih dahulu !'}
                        return {'value':val, 'warning':warning}
                    else :
                        pricelist = so.branch_id.pricelist_part_purchase_id.id
                else :
                    pricelist = supplier.property_product_pricelist_purchase.id
                if supplier:
                    vals = po_line_obj.onchange_product_id(cr, uid, ids, pricelist, line.product_id.id, line.product_uom_qty, line.product_id.uom_po_id.id,
                        supplier.id, date_order=date_order,
                        fiscal_position_id=supplier.property_account_position,
                        date_planned=date_order,
                        name=False, price_unit=False, state='draft')['value']
                else:
                    vals = po_line_obj.onchange_product_id(cr, uid, ids, pricelist, line.product_id.id, line.product_uom_qty, line.product_id.uom_po_id.id,
                        False, date_order=date_order,
                        fiscal_position_id=supplier.property_account_position,
                        date_planned=date_order,
                        name=False, price_unit=False, state='draft')['value']
                categ = line.product_id.categ_id
                while categ.parent_id:
                    categ = categ.parent_id
                vals.update({
                    'template_id': line.product_id.product_tmpl_id.id,
                    'product_id': line.product_id.id,
                    'division_dummy': division in ['Umum','Sparepart'] and division or '',
                    'categ_id': categ.id,
                    'taxes_id': [(6, 0, vals['taxes_id'])],
                    'state': 'draft'
                })
                lines.append([0,0,vals])
            val['order_line'] = lines
        return {'domain':dom,'value':val}

    def onchange_partner_type(self,cr,uid,ids,partner_type,branch_id,context=None):
        dom = {}        
        val = {}
        journal_ids = []
        if partner_type:
            domain_search = [('branch_id','in',[branch_id,False])]
            obj_partner_type = self.pool.get('dym.partner.type').browse(cr, uid, [partner_type])
            if obj_partner_type.field_type == 'boolean':
                domain_search += [(obj_partner_type.name,'!=',False)]
            elif obj_partner_type.field_type == 'selection':
                domain_search += [(obj_partner_type.selection_name,'=',obj_partner_type.name)]
            dom['partner_id'] = domain_search
            if branch_id:
                branch = self.pool.get('dym.branch').browse(cr, uid, branch_id)
                if branch.branch_status == 'H1':
                    dom['partner_id'] += [('id','!=',branch.default_supplier_workshop_id.id)]
                if branch.branch_status == 'H23':
                    dom['partner_id'] += [('id','!=',branch.default_supplier_id.id)]
                # if branch.company_id and branch.company_id.partner_id:
                #     dom['partner_id'] += [('id','!=',branch.company_id.partner_id.id)]
            domain = [
                ('type','in',['purchase','purchase_refund']),
                ('company_id','=',branch.company_id.id),
            ]
            res1, dom1 = self.get_branch_purchase_default_journal(cr, uid, ids, branch_id, context=context)
        val['partner_id']=False
        return {'domain':dom,'value':val}

    def onchange_division(self, cr, uid, ids, branch_id, division, partner_id, context=None):
        if not context:
            context = {}
        dom={}
        res={}
        war={}
        res['purchase_order_type_id']=False
        if branch_id :
            branch_obj = self.pool.get('dym.branch').browse(cr, uid, branch_id)
            if not partner_id:
                if branch_obj.branch_status in ['H1','H123']:
                    res['partner_id']=branch_obj.default_supplier_id.id
                if branch_obj.branch_status in ['H23']:
                    res['partner_id']=branch_obj.default_supplier_workshop_id.id
            partner_type_id = self.pool.get('dym.partner.type').search(cr, uid, [('name','=','principle')])
            dom['partner_type'] = "['|',('division','like',division),('id','=',"+str(partner_type_id[0])+")]"
            res['partner_type']= int(partner_type_id[0])
            journal_config = self._get_branch_journal_config(cr, uid, branch_id)
            if division == 'Unit':
                res['pricelist_id']=branch_obj.pricelist_unit_purchase_id
                res['journal_id']=journal_config['dym_po_journal_unit_id'].id
            elif division == 'Sparepart':
                res['pricelist_id']=branch_obj.pricelist_part_purchase_id
                res['journal_id']=journal_config['dym_po_journal_sparepart_id'].id
            elif partner_id and division == 'Umum':
                partner_obj = self.pool.get('res.partner').browse(cr, uid, partner_id)
                res['pricelist_id'] = partner_obj.property_product_pricelist_purchase
                # if not res.get('pricelist_id',True):
                #     war = {'title': _('Perhatian !'), 'message': _('Pricelist beli cabang belum ada, silahkan ditambahkan di Supplier.')}
            if division == 'Umum':
                res['journal_id']=journal_config['dym_po_journal_umum_id'].id
            if not res.get('pricelist_id',True) and division not in ['Umum',False]:
                war = {'title': _('Perhatian !'), 'message': _('Pricelist beli cabang belum ada, silahkan ditambahkan di Branch Configuration.')}
        else :
            res['pricelist_id']=False

        partnertype = False
        if 'partner_type' in res and res['partner_type']:
            partnertype = self.pool.get('dym.partner.type').browse(cr, uid, [res['partner_type']], context=context)[0]
            if partnertype.name in ['Konsolidasi','Afiliasi']:
                journal_id = self.pool.get('account.journal').search(cr, uid, [
                    ('is_intercompany','=',True),
                    ('type','in',['purchase','purchase_refund']),
                    ('company_id','=',branch_obj.company_id.id)
                    ], context=context)
                res['journal_id'] = journal_id and journal_id[0] or None
        return {'domain':dom, 'value':res,'warning':war}

    def get_branch_purchase_default_journal(self, cr, uid, ids, branch_id=None, context=None):
        dom = {}
        res = {}
        if not branch_id:
            return (res,dom)
        branch_config_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
        if not branch_config_id:
            raise osv.except_osv(
                        _('Perhatian'),
                        _('Konfigurasi Cabang ini tidak ditemukan di Branch Config, silahkan setting dulu.'))
        branch_config = self.pool.get('dym.branch.config').browse(cr,uid,branch_config_id[0])
        this = self.browse(cr, uid, ids, context=context)

        if this.asset and branch_config.dym_po_journal_asset_id:
            res['journal_id'] = branch_config.dym_po_journal_asset_id.id
        elif this.prepaid and branch_config.dym_po_journal_prepaid_id:
            res['journal_id'] = branch_config.dym_po_journal_prepaid_id.id
        else:
            pass

        if this.partner_type.name in ['Afiliasi','Konsolidasi'] and branch_config.dym_po_journal_intercompany_id:
            res['journal_id'] = branch_config.dym_po_journal_intercompany_id.id
        else:
            for jnl in branch_config.dym_po_type_journal_ids:

                if this.purchase_order_type_id and jnl.po_type_id.id == this.purchase_order_type_id.id and jnl.category == this.division and jnl.journal_id:
                    res['journal_id'] = jnl.journal_id.id
                    dom['journal_id'] = [('id','=',jnl.journal_id.id)]
                    break
                else:
                    dom['journal_id'] = []
        return (res,dom)

    def purchase_order_type_id_change(self, cr, uid, ids, division, partner_type_id, purchase_order_type_id, id_branch=False,asset=False, prepaid=False, order_line=False, context=None):
        if not id_branch:
            return False
        this = self.browse(cr, uid, ids, context=context)
        po_type = self.pool.get('dym.purchase.order.type').browse(cr, uid, purchase_order_type_id)
        partner_type = self.pool.get('dym.partner.type').browse(cr,uid,partner_type_id,context=context)
        res = {}
        res['editable_price']=True
        # res['editable_price']=po_type.editable_price
        res['start_date']=False
        res['end_date']=False
        res['invoice_method']='manual'
        res['mandatory_so_wo']=False
        res['mandatory_hutang_lain']=False
        if po_type:
            res['start_date'] = po_type.get_date(po_type.date_start)
            res['end_date'] = po_type.get_date(po_type.date_end)
            res['invoice_method'] = po_type.invoice_method if po_type.invoice_method else 'manual'
            res['mandatory_so_wo'] = po_type.mandatory_so_wo
            res['mandatory_hutang_lain'] = po_type.mandatory_hutang_lain
        if id_branch:
            analytic_1, analytic_2, analytic_3, analytic_4 = self.get_analytic_combi(cr, uid, id_branch, asset, prepaid, order_line,purchase_order_type_id)
            if analytic_1:
                res['analytic_1'] = analytic_1
            res['analytic_2'] = analytic_2
            res['analytic_3'] = analytic_3
            res['analytic_4'] = analytic_4
        res1, dom = self.get_branch_purchase_default_journal(cr, uid, ids, id_branch, context=context)
        branch_config_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',id_branch)])
        if not branch_config_id:
            raise osv.except_osv(
                        _('Perhatian'),
                        _('Konfigurasi Cabang ini tidak ditemukan di Branch Config, silahkan setting dulu.'))
        branch_config = self.pool.get('dym.branch.config').browse(cr,uid,branch_config_id[0])
        if asset and branch_config.dym_po_journal_asset_id:
            res['journal_id'] = branch_config.dym_po_journal_asset_id.id
        elif prepaid and branch_config.dym_po_journal_prepaid_id:
            res['journal_id'] = branch_config.dym_po_journal_prepaid_id.id
        elif partner_type.name in ['Konsolidasi'] and branch_config.dym_po_journal_intercompany_id:
            res['journal_id'] = branch_config.dym_po_journal_intercompany_id.id
        else:
            for jnl in branch_config.dym_po_type_journal_ids:
                if jnl.po_type_id.id == purchase_order_type_id and jnl.category == division and jnl.journal_id:
                    res['journal_id'] = jnl.journal_id.id
                    dom['journal_id'] = [('id','=',jnl.journal_id.id)]
                    break
        partner_type = partner_type_id
        if partner_type:
            domain_search = [('branch_id','in',[id_branch,False])]
            obj_partner_type = self.pool.get('dym.partner.type').browse(cr, uid, [partner_type])
            if obj_partner_type.field_type == 'boolean':
                domain_search += [(obj_partner_type.name,'!=',False)]
            elif obj_partner_type.field_type == 'selection':
                domain_search += [(obj_partner_type.selection_name,'=',obj_partner_type.name)]
            dom['partner_id'] = domain_search
            if id_branch:
                branch = self.pool.get('dym.branch').browse(cr, uid, id_branch)
                if branch.branch_status == 'H1':
                    dom['partner_id'] += [('id','!=',branch.default_supplier_workshop_id.id)]
                if branch.branch_status == 'H23':
                    dom['partner_id'] += [('id','!=',branch.default_supplier_id.id)]
                # if branch.company_id and branch.company_id.partner_id:
                #     dom['partner_id'] += [('id','!=',branch.company_id.partner_id.id)]
            domain = [
                ('type','in',['purchase','purchase_refund']),
                ('company_id','=',branch.company_id.id),
            ]
            res1, dom1 = self.get_branch_purchase_default_journal(cr, uid, ids, id_branch, context=context)
        return {
            'value':res,
            'domain':dom,
        }
    
    def _get_branch_journal_config(self,cr,uid,branch_id):
        result = {}
        branch_journal_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
        if not branch_journal_id:
            raise osv.except_osv(
                        _('Perhatian'),
                        _('Jurnal pembelian cabang belum dibuat, silahkan setting dulu.'))
            
        branch_journal = self.pool.get('dym.branch.config').browse(cr,uid,branch_journal_id[0])
        result.update({
            'dym_po_journal_unit_id':branch_journal.dym_po_journal_unit_id,
            'dym_po_journal_sparepart_id':branch_journal.dym_po_journal_sparepart_id,
            'dym_po_journal_umum_id':branch_journal.dym_po_journal_umum_id,
            'dym_po_journal_blind_bonus_beli_id':branch_journal.dym_po_journal_blind_bonus_beli_id,
            'dym_po_account_blind_bonus_beli_dr_id':branch_journal.dym_po_account_blind_bonus_beli_dr_id,
            'dym_po_account_blind_bonus_beli_cr_id':branch_journal.dym_po_account_blind_bonus_beli_cr_id,
        })
        
        return result
    
    def _prepare_invoice(self, cr, uid, order, line_ids, context=None):
        result = super(dym_purchase_order, self)._prepare_invoice(cr, uid, order, line_ids, context)
        
        result['journal_id'] = False
        result['account_id'] = False
        if order.division == 'Unit':
            result['journal_id'] = order.journal_id.id
            result['account_id'] = order.journal_id.default_credit_account_id.id
            # adi [constraint error if account_id is False]
        elif order.division == 'Sparepart':
            result['journal_id'] = order.journal_id.id
            result['account_id'] = order.journal_id.default_credit_account_id.id
            # adi [constraint error if account_id is False]
        elif order.division == 'Umum':
            result['journal_id'] = order.journal_id.id 
            result['account_id'] = order.journal_id.default_credit_account_id.id
            # adi [constraint error if account_id is False]
        if not result['journal_id']:
            raise osv.except_osv(
                _('Perhatian'),
                _('Journal di %s belum diisi!.') % (order.name))
        if not result['account_id']:
            raise osv.except_osv(
                _('Perhatian'),
                _('Default Credit Account untuk jurnal %s belum dibuat, silahkan dibuat terlebih dahulu.') % (order.journal_id.name))
        result['branch_id'] = order.branch_id.id
        result['division'] = order.division
        result['tipe'] = 'purchase'
        result['asset'] = True if order.asset or order.prepaid else False
        result['partner_type'] = order.partner_type.id
        result['analytic_1'] = order.analytic_1.id
        result['analytic_2'] = order.analytic_2.id
        result['analytic_3'] = order.analytic_3.id
        result['analytic_4'] = order.analytic_4.id
        return result
    
    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):
        ''' prepare the stock move data from the PO line. This function returns a list of dictionary ready to be used in stock.move's create()'''
        product_uom = self.pool.get('product.uom')
        price_unit = order_line.price_unit
        if order_line.product_uom.id != order_line.product_id.uom_id.id:
            price_unit *= order_line.product_uom.factor / order_line.product_id.uom_id.factor
        if order.currency_id.id != order.company_id.currency_id.id:
            #we don't round the price_unit, as we may want to store the standard price with more digits than allowed by the currency
            price_unit = self.pool.get('res.currency').compute(cr, uid, order.currency_id.id, order.company_id.currency_id.id, price_unit, round=False, context=context)
        res = []
        default_location_search = self.pool.get('dym.product.location').search(cr, uid, [
                                                                                    ('branch_id','=',order.branch_id.id),
                                                                                    ('product_id','=',order_line.product_id.id)
                                                                                    ], order='id desc', limit=1)
        if default_location_search:
            default_location_brw = self.pool.get('dym.product.location').browse(cr, uid, default_location_search)
            location_dest_id = default_location_brw.location_id.id
        else:
            location_dest_id = order.location_id.id

        move_template = {
            'branch_id': order.branch_id.id,
            'categ_id': order_line.product_id.categ_id.id,
            'name': order_line.name or '',
            'product_id': order_line.product_id.id,
            'product_uom': order_line.product_uom.id,
            'product_uos': order_line.product_uom.id,
            'date': order.date_order,
            'date_expected': order.end_date,
            'location_id': order.picking_type_id.default_location_src_id.id,
            'location_dest_id': location_dest_id,
            'picking_id': picking_id,
            'partner_id': order.dest_address_id.id or order.partner_id.id,
            'move_dest_id': False,
            'state': 'draft',
            'purchase_line_id': order_line.id,
            'company_id': order.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': order.picking_type_id.id,
            'group_id': group_id,
            'procurement_id': False,
            'origin': order.name,
            'route_ids': order.picking_type_id.warehouse_id and [(6, 0, [x.id for x in order.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id':order.picking_type_id.warehouse_id.id,
            'invoice_state': order.invoice_method == 'picking' and '2binvoiced' or 'none',
        }

        diff_quantity = order_line.product_qty
        for procurement in order_line.procurement_ids:
            procurement_qty = product_uom._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, to_uom_id=order_line.product_uom.id)
            tmp = move_template.copy()
            tmp.update({
                'product_uom_qty': min(procurement_qty, diff_quantity),
                'product_uos_qty': min(procurement_qty, diff_quantity),
                'move_dest_id': procurement.move_dest_id.id,  #move destination is same as procurement destination
                'group_id': procurement.group_id.id or group_id,  #move group is same as group of procurements if it exists, otherwise take another group
                'procurement_id': procurement.id,
                'invoice_state': procurement.rule_id.invoice_state or (procurement.location_id and procurement.location_id.usage == 'customer' and procurement.invoice_state=='picking' and '2binvoiced') or (order.invoice_method == 'picking' and '2binvoiced') or 'none', #dropship case takes from sale
                'propagate': procurement.rule_id.propagate,
            })
            diff_quantity -= min(procurement_qty, diff_quantity)
            res.append(tmp)
        #if the order line has a bigger quantity than the procurement it was for (manually changed or minimal quantity), then
        #split the future stock move in two because the route followed may be different.
        if diff_quantity > 0:
            move_template['product_uom_qty'] = diff_quantity
            move_template['product_uos_qty'] = diff_quantity
            res.append(move_template)
        return res
    
    def action_picking_create(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids):
            if order.division is not 'Umum' and not order.asset and not order.prepaid:
                picking_vals = {
                    'picking_type_id': order.picking_type_id.id,
                    'partner_id': order.dest_address_id.id or order.partner_id.id,
                    'date': order.date_order,
                    'start_date': order.start_date,
                    'end_date': order.end_date,
                    'origin': order.name,
                    'branch_id': order.branch_id.id,
                    'division': order.division,
                    'transaction_id': order.id,
                    'model_id': self.pool.get('ir.model').search(cr,uid,[('model','=',order.__class__.__name__)])[0],
                }
                print "=====picking_vals====",picking_vals

                picking_id = self.pool.get('stock.picking').create(cr, uid, picking_vals, context=context)
                print "=picking_idpicking_idpicking_id====>",picking_id
                print "~~~~~~~~~~",order, order.order_line, picking_id

                self._create_stock_moves(cr, uid, order, order.order_line, picking_id, context=context)
    
    def effective_date_change(self, cr, uid, ids, start_date, end_date, context=None):
        value = {}
        warning = {}
        if start_date and datetime.strptime(start_date, "%Y-%m-%d").date() < datetime.today().date() :
            warning = {'title':'Perhatian','message':'Tanggal tidak boleh kurang dari tanggal hari ini !'}
            value['start_date'] = False
        elif start_date and end_date and datetime.strptime(start_date, "%Y-%m-%d").date() > datetime.strptime(end_date, "%Y-%m-%d").date() :
            warning = {'title':'Perhatian','message':'End Date tidak boleh sama atau kurang dari Start Date !'}
            value['end_date'] = False
        if end_date and not warning :
            value['minimum_planned_date'] = end_date
        return {'value':value, 'warning':warning}
    
    def onchange_partner_id(self, cr, uid, ids, branch_id, division, partner_id, context=None):
        result = super(dym_purchase_order,self).onchange_partner_id(cr, uid, ids, partner_id, context=context)
        if result.get('value',False):
            if context.get('division') != 'Umum' and 'pricelist_id' in result['value']:
                result['value'].pop('pricelist_id', None)
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
            payment_term_id = partner.property_supplier_payment_term.id
            if 'value' not in result:
                result['value'] = {}
            result['value']['payment_term_id'] = payment_term_id
            self.purchase_order_type_id_change(division, partner.partner_type, purchase_order_type_id, id_branch=False,asset=False, prepaid=False, order_line=False, context=context)
        return result
    
    def default_get(self, cr, uid, fields, context=None):
         context = context or {}
         res = super(dym_purchase_order, self).default_get(cr, uid, fields, context=context)
         if 'picking_type_id' in fields:
             res.update({'picking_type_id': self._get_picking_type_ids(cr, uid)})
         return res
    

    def change_reset(self, cr, uid, ids, field, context=None):
        res = {}
        # if field == 'analytic_2':
        #     res['analytic_3'] = False
        #     res['analytic_4'] = False
        # if field == 'analytic_3':
        #     res['analytic_4'] = False
        result = {}
        result['value'] = res
        return result

    def get_analytic_combi(self,cr, uid, id_branch, asset, prepaid, order_line, purchase_order_type_id, product_id=False):
        branch_id = self.pool.get('dym.branch').browse(cr, uid, id_branch)
        if product_id == False:
            lines = self.resolve_2many_commands(cr, uid, 'order_line', order_line, ['product_id'])
            if lines:
                product_id = lines[0]['product_id']
        if prepaid == True or asset == True:
            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_id, 'Umum', False, 4, 'General')
            return analytic_1, analytic_2, analytic_3, analytic_4
        elif product_id and purchase_order_type_id:
            product_id = tuple==type(product_id) and product_id[0] or product_id
            product = self.pool.get('product.product').browse(cr, uid, product_id)
            po_type = self.pool.get('dym.purchase.order.type').browse(cr, uid, purchase_order_type_id)
            cost_center = ''
            po_type_name = po_type.name.lower()
            if product.categ_id.get_root_name() != 'Umum':
                analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_id, '', product.categ_id, 4, 'General')
            elif po_type_name == 'jp3':
                analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_id, 'Service', False, 4, 'General')
            else:
                analytic_1, analytic_2, analytic_3, analytic_4 = False, False, False, False
            return analytic_1, analytic_2, analytic_3, analytic_4
        analytic_1, analytic_2, analytic_3, analytic_4 = False, False, False, False
        return analytic_1, analytic_2, analytic_3, analytic_4

    def onchange_picking_type_id(self, cr, uid, ids, id_branch, id_picking_type, change_branch=False, asset=False, prepaid=False, order_line=False, purchase_order_type_id=False, context=None):
        value = {}
        warning = {}
        dom = {}
        value['picking_type_id'] = False
        branch_id = self.pool.get('dym.branch').browse(cr, uid, id_branch)
        obj_picking_type = self.pool.get('stock.picking.type')
        picking_type_ids = obj_picking_type.search(cr, uid, [
                                                            ('code','=','incoming'),
                                                            ('branch_id','=',id_branch)
                                                            ])        
        if change_branch == True and id_branch:
            analytic_1, analytic_2, analytic_3, analytic_4 = self.get_analytic_combi(cr, uid, id_branch, asset, prepaid, order_line, purchase_order_type_id)
            if analytic_1:
                value['analytic_1'] = analytic_1
            value['analytic_2'] = analytic_2
            value['analytic_3'] = analytic_3
            value['analytic_4'] = analytic_4
        id_picking_type = False
        if picking_type_ids :
        	id_picking_type = picking_type_ids[0]
        if id_branch :
            if branch_id.branch_status in ['H1','H123']:
                value['partner_id']=branch_id.default_supplier_id.id
            if branch_id.branch_status in ['H23']:
                value['partner_id']=branch_id.default_supplier_workshop_id.id
            partner_type_id = self.pool.get('dym.partner.type').search(cr, uid, [('name','=','principle')])
            dom['partner_type'] = "['|',('division','like',division),('id','=',"+str(partner_type_id[0])+")]"
            value['partner_type']= int(partner_type_id[0])
            if id_picking_type :
                value['picking_type_id'] = id_picking_type
            else :
                warning = {"title":"Perhatian", "message":"Tidak ditemukan type picking 'Receipts' untuk '%s'\nsilahkan buat di menu Warehouse > Type Of Operation" %branch_id.name}
                value['picking_type_id'] = False
                value['branch_id'] = False
        if id_picking_type :
            picktype = self.pool.get("stock.picking.type").browse(cr, uid, [id_picking_type])
            if picktype.default_location_dest_id :
                value.update({'location_id': picktype.default_location_dest_id.id})
            value.update({'related_location_id': picktype.default_location_dest_id and picktype.default_location_dest_id.id or False})
        return {'value': value, 'warning':warning, 'domain':dom}
    
    def refresh_po(self, cr, uid, ids, context=None):
        if not self.check_access_rights(cr, uid, 'read', raise_exception=False):
            user_id = SUPERUSER_ID
        else:
            user_id = uid
        for order in self.browse(cr, uid, ids, context=context):
            workflow.trg_write(user_id, 'purchase.order', order.id, cr)
        return True

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        vals = super(dym_purchase_order,self).wkf_confirm_order(cr,uid,ids,context=context)
        self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now(),'date_order':datetime.now()})
        return vals
    
    def _prepare_inv_line(self, cr, uid, account_id, order_line, context=None):
        res = super(dym_purchase_order,self)._prepare_inv_line(cr, uid, account_id, order_line,context=context)
        if order_line.order_id.asset == True or order_line.order_id.prepaid == True:
            branch_config_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',order_line.order_id.branch_id.id)])
            if not branch_config_id:
                raise osv.except_osv(
                            _('Perhatian'),
                            _('Config Branch, silahkan setting dulu.'))
            branch_config = self.pool.get('dym.branch.config').browse(cr,uid,branch_config_id[0])
            as_pr_account_id = False
            if order_line.order_id.asset == True:
                if not(branch_config.journal_register_asset and branch_config.journal_register_asset.default_debit_account_id):
                    raise osv.except_osv(
                                _('Perhatian'),
                                _('Jurnal register asset cabang belum lengkap, silahkan setting dulu.'))
                as_pr_account_id = branch_config.journal_register_asset.default_debit_account_id.id
            if order_line.order_id.prepaid == True:
                if not(branch_config.journal_register_prepaid and branch_config.journal_register_prepaid.default_debit_account_id):
                    raise osv.except_osv(
                                _('Perhatian'),
                                _('Jurnal register prepaid cabang belum lengkap, silahkan setting dulu.'))
                as_pr_account_id = branch_config.journal_register_prepaid.default_debit_account_id.id
            res['account_id'] = as_pr_account_id
        po_type_name = order_line.order_id.purchase_order_type_id.name.lower()
        if order_line.order_id.prepaid == True or order_line.order_id.asset == True:
            res['analytic_1'] = order_line.order_id.analytic_1.id
            res['analytic_2'] = order_line.order_id.analytic_2.id
            res['analytic_3'] = order_line.order_id.analytic_3.id
            res['account_analytic_id'] = False
        elif order_line.order_id.division != 'Umum':
            res['analytic_1'] = order_line.order_id.analytic_1.id
            res['analytic_2'] = order_line.order_id.analytic_2.id
            res['analytic_3'] = order_line.order_id.analytic_3.id
            res['account_analytic_id'] = order_line.order_id.analytic_4.id
        elif po_type_name == 'jp3':
            res['analytic_1'] = order_line.order_id.analytic_1.id
            res['analytic_2'] = order_line.order_id.analytic_2.id
            res['analytic_3'] = order_line.order_id.analytic_3.id
            service_analytic = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',4),('cost_center','=','Service'),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',order_line.order_id.analytic_3.ids)])
            if not service_analytic:
                raise osv.except_osv(('Perhatian !'), ("Analytic service tidak ditemukan"))
            res['account_analytic_id'] = service_analytic[0]
        else:
            res['analytic_1'] = order_line.order_id.analytic_1.id
            res['analytic_2'] = order_line.order_id.analytic_2.id
            res['analytic_3'] = order_line.order_id.analytic_3.id
            res['account_analytic_id'] = False
        if order_line.order_id.partner_id.pkp == False:
            res['invoice_line_tax_id'] = False
        return res

    def action_cancel(self, cr, uid, ids, context=None):
        vals = super(dym_purchase_order,self).action_cancel(cr,uid,ids,context=context)
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})
        purchase = self.browse(cr,uid,ids)
        # if purchase.asset :
            # asset_obj = self.pool.get('account.asset.asset')
            # receipt_obj = self.pool.get('dym.transfer.asset') 
        receive_obj = self.pool.get('dym.transfer.asset') 
        receive_ids = receive_obj.search(cr,uid,[
                                                ('purchase_id','=',purchase.id)
                                                ])           
        if receive_ids :
            receive_browse = receive_obj.browse(cr,uid,receive_ids)
            for x in receive_obj :
                if x.state != 'cancel'  :
                    x.write({'cancel_uid':uid,
                            'cancel_date':datetime.now(),
                            'state':'cancel'
                              }) 
            # asset_search = asset_obj.search(cr,uid,[
            #                                         ('purchase_id','=',purchase.id)
            #                                         ])           
            # if asset_search :
            #     asset_brw = asset_obj.browse(cr,uid,asset_search)
            #     for x in asset_brw :
            #         if x.receive_id :
            #                 x.receive_id.write({'cancel_uid':uid,
            #                                     'cancel_date':datetime.now(),
            #                                     'state':'cancel'
            #                                       }) 
            #                 x.receive_id.receive_id.write({'cancel_uid':uid,
            #         x.write({'purchase_id':False,'receive_id':False,'received':False})
                    
        return vals        
    
    def write(self, cr, uid, ids, vals, context=None):
        vals.get('order_line', []).sort(reverse=True)
        return super(dym_purchase_order, self).write(cr, uid, ids, vals, context=context)
    
    def test_moves_done(self, cr, uid, ids, context=None):
        '''PO is done at the delivery side if all the incoming shipments are done'''
        for purchase in self.browse(cr, uid, ids, context=context):
            for picking in purchase.picking_ids:
                if not all(move.product_id.categ_id.isParentName('Extras') for move in picking.move_lines) and picking.state != 'done':
                    return False
        return True
    
    def test_moves_except(self, cr, uid, ids, context=None):
        ''' PO is in exception at the delivery side if one of the picking is canceled
            and the other pickings are completed (done or canceled)
        '''
        at_least_one_canceled = False
        alldoneorcancel = True
        for purchase in self.browse(cr, uid, ids, context=context):
            for picking in purchase.picking_ids:
                if picking.state == 'cancel':
                    at_least_one_canceled = True
                if picking.state not in ['done', 'cancel'] and not all(move.product_id.categ_id.isParentName('Extras') for move in picking.move_lines):
                    alldoneorcancel = False
        return at_least_one_canceled and alldoneorcancel

class dym_purchase_order_line(osv.osv):
    _inherit = "purchase.order.line"
    
    def _get_price(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for purchase_order_line in self.browse(cr, uid, ids, context=context):
            price_unit_show=purchase_order_line.price_unit
            
            res[purchase_order_line.id]=price_unit_show
        return res
    
    def _amount_line(self, cr, uid, ids, prop, arg, context=None):
        res = {}
        cur_obj=self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            taxes = tax_obj.compute_all(cr, uid, line.taxes_id, line.price_unit, line.product_qty, line.product_id, line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            price_subtotal = taxes['total']
            if cur:
                price_subtotal = cur_obj.round(cr, uid, cur, taxes['total'])
            res[line.id] = price_subtotal
        return res

    def _get_consolidated_qty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            consol_src = self.pool.get('consolidate.invoice.line').search(cr, uid, ['|',('move_id.purchase_line_id','=',line.id),('receive_line_id.purchase_line_id','=',line.id),('consolidate_id.state','=','done')])
            consol_brw = self.pool.get('consolidate.invoice.line').browse(cr, uid, consol_src)
            consol_qty = sum(consol.product_qty for consol in consol_brw)
            res[line.id] = consol_qty
        return res

    _columns = {
        'name':fields.text('Description',required=False),
        'editable_price': fields.boolean('Editable Price'),
        'date_planned': fields.date('Scheduled Date', select=True),
        'received':fields.float('Received', digits=(16,0)),
        'categ_id':fields.many2one('product.category','Category',required=True),
        'template_id':fields.many2one('product.template','Tipe'),
        'product_id':fields.many2one('product.product','Variant'),
        'price_unit_show':fields.function(_get_price,string='Unit Price'),
        'taxes_id_show': fields.many2many('account.tax', 'purchase_order_taxe', 'ord_id', 'tax_id', 'Taxes'),
        'qty_invoiced': fields.float('Invoiced', digits=(16,0)),
        'division_dummy': fields.char('Division'),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
        'branch_id' : fields.related('order_id','branch_id',type='many2one',relation="dym.branch",string="Branch"),
        'asset' : fields.related('order_id','asset',type='boolean',string="Asset"),
        'prepaid' : fields.related('order_id','prepaid',type='boolean',string="Prepaid"),
        'qty_consolidated':fields.function(_get_consolidated_qty,string='Consolidated', digits=(16,0)),
    }
    
    _sql_constraints = [('product_id_unique', 'unique(order_id,product_id)', 'Tidak boleh ada product yg sama dalam satu transaksi .1.!')]

    def change_tax(self,cr,uid,ids,tax_id,context=None):
        return {'value':{'taxes_id_show':tax_id}}
        
    def category_change(self, cr, uid, ids, categ_id, branch_id, division, pricelist_id, is_asset, is_prepaid, template_id=False, editable_price=None):
        if not branch_id or not division :
            raise osv.except_osv(('No Branch or Division Defined!'), ('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        if division in ('Unit', 'Sparepart') and not pricelist_id :
            raise osv.except_osv(('No Purchase Pricelist Defined!'), ('Sebelum menambah detil transaksi,\n harap set pricelist terlebih dahulu di Branch Configuration.'))
        dom = {}
        val = {}
        val['editable_price'] = editable_price
        val['editable_price'] = True
        val['product_id'] = False 
        if categ_id:
            categ_ids = self.pool.get('product.category').get_child_by_ids(cr,uid,categ_id)
            if division == 'Umum':
                categ_ids += self.pool.get('product.category').get_child_ids(cr,uid,[],'Service')
            dom['template_id']=[('categ_id','in',categ_ids),('purchase_ok','=',True),('is_asset','=',is_asset),('is_prepaid','=',is_prepaid)]
            if template_id:
                dom['product_id']=[('product_tmpl_id','=',template_id),('categ_id','in',categ_ids),('purchase_ok','=',True),('is_asset','=',is_asset),('is_prepaid','=',is_prepaid)]
                template = self.pool.get('product.template').browse(cr, uid, [template_id])
                if len(template.product_variant_ids) == 1:
                    val['product_id'] = template.product_variant_ids.id
            else:
                dom['product_id']=[('id','=',0)]
            categ_name = self.pool.get('product.category').browse(cr,uid,categ_id).name
            if categ_name in ['Umum','Sparepart']:
                val['division_dummy']=categ_name
            else:
                val['division_dummy']=""
        else:
            categ = self.pool.get('product.category').search(cr, uid, [('name','=',division)])
            if categ:
                val['categ_id'] = categ[0]
                categ_ids = self.pool.get('product.category').get_child_by_ids(cr,uid,categ[0])
                if division == 'Umum':
                    categ_ids += self.pool.get('product.category').get_child_ids(cr,uid,[],'Service')
                dom['template_id']=[('categ_id','in',categ_ids),('purchase_ok','=',True),('is_asset','=',is_asset)]
                if template_id:
                    dom['product_id']=[('product_tmpl_id','=',template_id),('categ_id','in',categ_ids),('purchase_ok','=',True),('is_asset','=',is_asset)]
                    template = self.pool.get('product.template').browse(cr, uid, [template_id])
                    if len(template.product_variant_ids) == 1:
                        val['product_id'] = template.product_variant_ids.id
                else:
                    dom['product_id']=[('id','=',0)]
                # dom['product_id']=[('categ_id','in',categ_ids),('purchase_ok','=',True),('is_asset','=',is_asset)]
            if division in ['Umum','Sparepart']:
                val['division_dummy']=division
            else:
                val['division_dummy']=""
        return {'domain':dom,'value':val}
    
    def price_unit_change(self, cr, uid, ids, price_unit):
        value = {}
        if not price_unit:
           value['price_unit_show'] = 0
           value['price_unit'] = 0
        else:
           value['price_unit_show'] = price_unit
           value['price_unit'] = price_unit
        return {'value':value}
    
    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft', context=None):
        res = super(dym_purchase_order_line, self).onchange_product_id(cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=date_order, fiscal_position_id=fiscal_position_id, date_planned=date_planned,
            name=name, price_unit=price_unit, state='draft', context=context)
        pricelist = self.pool.get('product.pricelist').browse(cr,uid,pricelist_id)
        product = self.pool.get('product.product').browse(cr, uid, product_id)
        if product.uom_id:
            res['value'].update({'product_uom': product.uom_id.id})
        res['value'].update({'name': product.description or product.default_code or product.name})
        if ('price_unit' not in res['value'] or res['value']['price_unit'] < 1) and product_id and product.categ_id.get_root_name() not in ('Umum','Service'):
            raise osv.except_osv(('Perhatian !'), ("xUnit Price Product '%s' tidak boleh '%s'" %(product.name,(res['value']['price_unit'] or 0.0))))
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if partner.pkp == False:
                res['value'].update({'taxes_id': []})
        return res
    
class dym_purchase_line_invoice(osv.osv_memory):
    _inherit = 'purchase.order.line_invoice'
    
    def makeInvoices(self, cr, uid, ids, context=None):
        """
             To get Purchase Order line and create Invoice
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : retrun view of Invoice
        """

        if context is None:
            context={}

        record_ids =  context.get('active_ids',[])
        if record_ids:
            res = False
            invoices = {}
            invoice_obj = self.pool.get('account.invoice')
            purchase_obj = self.pool.get('purchase.order')
            purchase_line_obj = self.pool.get('purchase.order.line')
            invoice_line_obj = self.pool.get('account.invoice.line')
            account_jrnl_obj = self.pool.get('account.journal')

            def multiple_order_invoice_notes(orders):
                branch_id = False
                division = False
                partner_id = False
                notes = ""
                for order in orders:
                    notes += "%s \n" % order.notes
                    if branch_id != False and branch_id != order.branch_id.id :
                        raise osv.except_osv(('Perhatian !'), ("Branch harus sama, silahkan cek kembali"))
                    if division != False and division != order.division :
                        raise osv.except_osv(('Perhatian !'), ("Division harus sama, silahkan cek kembali"))
                    if partner_id != False and partner_id != order.partner_id.id :
                        raise osv.except_osv(('Perhatian !'), ("Supplier harus sama, silahkan cek kembali"))
                    branch_id = order.branch_id.id
                    division = order.division
                    partner_id = order.partner_id.id
                    
                return notes

            def make_invoice_by_partner(partner, orders, lines_ids):
                """
                    create a new invoice for one supplier
                    @param partner : The object partner
                    @param orders : The set of orders to add in the invoice
                    @param lines : The list of line's id
                """
                name = orders and orders[0].name or ''                
                journal_id = False
                account_id = False
                if orders[0].division == 'Unit' :
                    journal_id = orders[0].journal_id
                    account_id = orders[0].journal_id.default_credit_account_id
                elif orders[0].division == 'Sparepart' :
                    journal_id = orders[0].journal_id
                    account_id = orders[0].journal_id.default_credit_account_id
                else :
                    journal_id = orders[0].journal_id
                    account_id = orders[0].journal_id.default_credit_account_id

                if not journal_id:
                    raise osv.except_osv(
                        _('Perhatian'),
                        _('Journal di %s belum diisi!.') % (orders[0].name))
                if not account_id:
                    raise osv.except_osv(
                        _('Perhatian'),
                        _('Default Credit Account untuk jurnal %s belum dibuat, silahkan dibuat terlebih dahulu.') % (orders[0].journal_id.name))
                
                inv = {
                    'branch_id': orders[0].branch_id.id,
                    'division': orders[0].division,
                    'name': name,
                    'origin': name,
                    'type': 'in_invoice',
                    'tipe': 'purchase',
                    'journal_id':journal_id.id,
                    'reference' : partner.ref,
                    'account_id': account_id.id,
                    'partner_id': partner.id,
                    'invoice_line': [(6,0,lines_ids)],
                    'currency_id' : orders[0].currency_id.id,
                    'comment': multiple_order_invoice_notes(orders),
                    'payment_term': orders[0].payment_term_id.id,
                    'fiscal_position': partner.property_account_position.id,
                    'analytic_1': orders[0].analytic_1.id,
                    'analytic_2': orders[0].analytic_2.id,
                    'analytic_3': orders[0].analytic_3.id,
                    'analytic_4': orders[0].analytic_4.id,
                    'partner_type' : orders[0].partner_type.id,
                    'asset': True if orders[0].asset or orders[0].prepaid else False,
                }
                
                inv_id = invoice_obj.create(cr, uid, inv)
                for order in orders:
                    order.write({'invoice_ids': [(4, inv_id)]})
                
                return inv_id

            for line in purchase_line_obj.browse(cr, uid, record_ids, context=context):
                if (not line.invoiced) and (line.state not in ('draft', 'cancel')):
                    if not line.partner_id.id in invoices:
                        invoices[line.partner_id.id] = []
                    acc_id = purchase_obj._choose_account_from_po_line(cr, uid, line, context=context)
                    inv_line_data = purchase_obj._prepare_inv_line(cr, uid, acc_id, line, context=context)
                    inv_line_data.update({'origin': line.order_id.name, 'quantity': line.product_qty-line.qty_invoiced})
                    inv_id = invoice_line_obj.create(cr, uid, inv_line_data, context=context)
                    purchase_line_obj.write(cr, uid, [line.id], {'invoice_lines': [(4, inv_id)]})
                    invoices[line.partner_id.id].append((line,inv_id))
            
            order_id = False
            partner_id = False
            for key, value in invoices.items():
                if partner_id != False and partner_id != key :
                    raise osv.except_osv(('Perhatian !'), ("Supplier harus sama, silahkan cek kembali"))
                partner_id = key
                for inv_id in value :
                    if order_id != False and order_id != inv_id[0].order_id.id :
                        raise osv.except_osv(('Perhatian !'), ("Satu invoice hanya bisa satu PO, silahkan cek kembali"))
                    order_id = inv_id[0].order_id.id
            
            res = []
            for result in invoices.values():
                il = map(lambda x: x[1], result)
                orders = list(set(map(lambda x : x[0].order_id, result)))
                
                # Supplier, Branch, Division harus sama
                branch_id = False
                division = False
                journal = False
                for order in orders:
                    if branch_id != False and branch_id != order.branch_id.id :
                        raise osv.except_osv(('Perhatian !'), ("Branch harus sama, silahkan cek kembali"))
                    if division != False and division != order.division :
                        raise osv.except_osv(('Perhatian !'), ("Division harus sama, silahkan cek kembali"))
                    if journal != False and journal != order.journal_id.id :
                        raise osv.except_osv(('Perhatian !'), ("Journal harus sama, silahkan cek kembali"))
                    branch_id = order.branch_id.id
                    division = order.division
                    journal = order.journal_id.id
                
                res.append(make_invoice_by_partner(orders[0].partner_id, orders, il))

            # compute the invoice
            invoice_obj.button_compute(cr, uid, res, context=context, set_total=True)
            
        return {
            'domain': "[('id','in', ["+','.join(map(str,res))+"])]",
            'name': _('Supplier Invoices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'context': "{'type':'in_invoice', 'journal_type': 'purchase'}",
            'type': 'ir.actions.act_window'
        }
