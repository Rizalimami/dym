import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import date, datetime, timedelta
from openerp import SUPERUSER_ID
class stock_production_lot(osv.osv):
    _inherit = 'stock.production.lot'
    _columns = {
        'hpp': fields.float('HPP', readonly=True, digits_compute=dp.get_precision('Product Price')),
        'performance_hpp': fields.float('Performance HPP', readonly=True, digits_compute=dp.get_precision('Product Price')),
        'consolidate_id': fields.many2one('consolidate.invoice', 'Consolidate Invoice', readonly=True),
    }

class dym_hpp_account_invoice(osv.osv):
    _inherit = 'account.invoice'
    
    def _consolidated(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for invoice in self.browse(cursor, user, ids, context=context):
            qty = {}
            for x in invoice.invoice_line :
                qty[x.product_id] = qty.get(x.product_id,0) + x.quantity - x.consolidated_qty
        res[invoice.id] = all(x[1] == 0 for x in qty.items())
        return res
    
    _columns = {
        'consolidated': fields.boolean('Invoice Consolidated')
    }

class dym_hpp_account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    _columns = {
        'consolidated_qty': fields.float('Cnsldted Qty', digits=(5,0)),
    }
    
class dym_hpp_stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    def _consolidated(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for picking in self.browse(cursor, user, ids, context=context):
            qty = {}
            for x in picking.move_lines :
                qty[x.product_id] = qty.get(x.product_id,0) + x.quantity - x.consolidated_qty
        res[picking.id] = all(x[1] == 0 for x in qty.items())
        return res
    
    _columns = {
        'consolidated': fields.boolean('Picking Consolidated')
    }
    
class dym_hpp_stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'consolidated_qty': fields.integer('Cnsldted Qty'),
    }
    
class consolidate_invoice(osv.osv):
    _name = "consolidate.invoice"
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(consolidate_invoice, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        for field in res['fields']:
            if field == 'division':
                if 'menu' in context and context['menu'] == 'showroom':
                    res['fields'][field]['selection'] = [('Unit','Showroom'), ('Umum','General')]

                if 'menu' in context and context['menu'] == 'workshop':
                    res['fields'][field]['selection'] = [('Sparepart','Workshop'), ('Umum','General')]

                if 'menu' in context and context['menu'] == 'general_affair':
                    res['fields'][field]['selection'] = [('Unit','Showroom'), ('Sparepart','Workshop'), ('Umum','General')]
        return res
        
    def get_sjno(self,cr,uid,ids, picking_id, context=None):
        packing_id = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id', '=', picking_id)], limit=1)
        packing = self.pool.get('dym.stock.packing').browse(cr, uid, packing_id)
        return packing.sj_no


    def get_sjdate(self,cr,uid,ids, picking_id, context=None):
        packing_id = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id', '=', picking_id)], limit=1)
        packing = self.pool.get('dym.stock.packing').browse(cr, uid, packing_id)
        return packing.sj_date[8:10]+ "-" + packing.sj_date[5:7] + "-" + packing.sj_date[:4]


    def get_grnno(self,cr,uid,ids, picking_id, context=None):
        packing_id = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id', '=', picking_id)], limit=1)
        packing = self.pool.get('dym.stock.packing').browse(cr, uid, packing_id)
        return packing.name

    def get_grndate(self,cr,uid,ids, picking_id, context=None):
        packing_id = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id', '=', picking_id)], limit=1)
        packing = self.pool.get('dym.stock.packing').browse(cr, uid, packing_id)
        return packing.date[8:10]+ "-" + packing.date[5:7] + "-" + packing.date[:4]

    def get_acc(self,cr,uid,ids, partner_id, context=None):
        partner_id = self.pool.get('res.partner.bank').search(cr, uid, [('partner_id', '=', partner_id)], limit=1)
        partner = self.pool.get('res.partner.bank').browse(cr, uid, partner_id)
        return partner.acc_number

    def get_bank(self,cr,uid,ids, partner_id, context=None):
        partner_id = self.pool.get('res.partner.bank').search(cr, uid, [('partner_id', '=', partner_id)], limit=1)
        partner = self.pool.get('res.partner.bank').browse(cr, uid, partner_id)
        return partner.bank_name

    def get_an(self,cr,uid,ids, partner_id, context=None):
        partner_id = self.pool.get('res.partner.bank').search(cr, uid, [('partner_id', '=', partner_id)], limit=1)
        partner = self.pool.get('res.partner.bank').browse(cr, uid, partner_id)
        return partner.owner_name

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    _columns = {
        'branch_id':fields.many2one('dym.branch','Branch', required=True),
        'division':fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division', change_default=True, select=True, required=True),
        'name': fields.char('Consolidate Invoice Ref.', size=64, required=True, readonly=True, select=True, states={'draft': [('readonly', False)]}),
        'invoice_id': fields.many2one('account.invoice', 'Supplier Invoice', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'picking_id': fields.many2one('stock.picking', 'Incoming Shipment', readonly=True, states={'draft': [('readonly', False)]}),
        'receive_id': fields.many2one('dym2.receive.asset', 'Receive Asset / Prepaid', readonly=True, states={'draft': [('readonly', False)]}),
        'date': fields.date('Date', readonly=True, select=True, states={'draft': [('readonly', False)]}),
        'state': fields.selection([('draft', 'Draft'), ('done', 'Done'), ('cancel', 'Cancel')], 'State', readonly=True, select=True),
        'consolidate_line': fields.one2many('consolidate.invoice.line', 'consolidate_id', 'Consolidate Lines', readonly=True, required=True, states={'draft': [('readonly', False)]}),
        'partner_id': fields.many2one('res.partner', 'Supplier'),
        'confirm_uid':fields.many2one('res.users',string="Approved by"),
        'confirm_date':fields.datetime('Approved on'),      
        'asset': fields.related('invoice_id', 'asset', type='boolean', string="Asset"),

    }
    
    _defaults = {
        'name': '/',
        'date': fields.date.context_today,
        'state':'draft',
        'branch_id': _get_default_branch,
    }

    _order = 'name desc'


    def update_price_branch(self, cr, uid, vals, context=None):
        obj_product_price = self.pool.get('product.price.branch')
        product_price_id = obj_product_price.search(cr, uid, [('warehouse_id','=', vals.get('warehouse_id')),('product_id','=',vals.get('product_id'))])
        if product_price_id:
            obj_product_price.write(cr, uid, product_price_id, vals, context=context)
        else:
            obj_product_price.create(cr, uid, vals, context=context)
        return True

    def name_get(self, cr, uid, ids, context=None):
        result = []
        for consolidate in self.browse(cr, uid , ids):
            receipt_name = False
            if consolidate.asset == False and consolidate.picking_id:
                packing_id = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id', '=', consolidate.picking_id.id),('state', '=', 'posted')], limit=1)
                packing = self.pool.get('dym.stock.packing').browse(cr, uid, packing_id)
                receipt_name = packing.name
            if consolidate.asset == True and consolidate.receive_id:
                receipt_name = consolidate.receive_id.name
            supp_invoice = ''
            if consolidate.invoice_id.supplier_invoice_number:
                supp_invoice = ' [' + consolidate.invoice_id.supplier_invoice_number + ']'            
            if receipt_name:
                receipt_name = ' [' + receipt_name + ']'
            result.append((consolidate.id, "%s%s%s" % (consolidate.name, supp_invoice or '', receipt_name or '')))
        return result

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []        
        if name and len(name) >= 3:
            ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('invoice_id.supplier_invoice_number', operator, name)] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('receive_id.name', operator, name)] + args, limit=limit, context=context or {})
            if not ids:
                packing_ids = self.pool.get('dym.stock.packing').search(cr, uid, [('name', operator, name),('state', '=', 'posted')])
                picking_ids = []
                for packing in self.pool.get('dym.stock.packing').browse(cr, uid, packing_ids):
                    if packing.picking_id.id not in picking_ids:
                        picking_ids.append(packing.picking_id.id)
                ids = self.search(cr, uid, [('picking_id.id', 'in', picking_ids)] + args, limit=limit, context=context or {})
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context or {})
        return self.name_get(cr, uid, ids, context or {})

    def consolidate_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'draft'})
    
    def consolidate_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'})
    
    def create_move(self, cr, uid, ids, branch_id, consolidate_line):
        move_obj = self.pool.get('account.move')
        cur_obj = self.pool.get('res.currency')
        obj_inv_line = self.pool.get('account.invoice.line')
        stock_move_obj = self.pool.get('stock.move')
        create_journal = False
        if consolidate_line.consolidate_id.asset == False:
            if not consolidate_line.product_id.categ_id.property_stock_account_input_categ or not consolidate_line.product_id.categ_id.property_stock_valuation_account_id or not consolidate_line.product_id.categ_id.property_stock_journal:
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi jurnal/account product belum lengkap!"))
            
            branch =  self.pool.get('dym.branch').browse(cr, uid, branch_id)
            analytic_4 = False
            if branch:
                cost_center = 'General'
                # if consolidate_line.product_id.categ_id.get_root_name() in ('Unit','Extras'):
                #     cost_center = 'Sales'
                # elif consolidate_line.product_id.categ_id.get_root_name() == 'Sparepart':
                #     cost_center = 'Sparepart_Accesories'
                # elif consolidate_line.product_id.categ_id.get_root_name() =='Umum':
                #     cost_center = 'General'
                # elif consolidate_line.product_id.categ_id.get_root_name() =='Service':
                #     cost_center = 'Service'
                if cost_center:
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, '', consolidate_line.product_id.categ_id, 4, cost_center)

            debit_account = consolidate_line.product_id.categ_id.property_stock_valuation_account_id.id
            # if consolidate_line.consolidate_id.asset == True:
            #     asset_prepaid = consolidate_line.consolidate_id.receive_id.asset_prepaid
            #     branch_config_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
            #     if not branch_config_id:
            #         raise osv.except_osv(
            #                     _('Perhatian'),
            #                     _('Config Branch, silahkan setting dulu.'))
            #     branch_config = self.pool.get('dym.branch.config').browse(cr,uid,branch_config_id[0])
            #     if not(branch_config.journal_register_asset and branch_config.journal_register_asset.default_debit_account_id and asset_prepaid == 'asset') and not(branch_config.journal_register_prepaid and branch_config.journal_register_prepaid.default_debit_account_id and asset_prepaid == 'prepaid'):
            #         raise osv.except_osv(
            #                     _('Perhatian'),
            #                     _('Jurnal register asset/prepaid cabang belum lengkap, silahkan setting dulu.'))
            #     debit_account = branch_config.journal_register_asset.default_debit_account_id.id if asset_prepaid == 'asset' else branch_config.journal_register_prepaid.default_debit_account_id.id
            id_inv_line = obj_inv_line.search(cr, uid, [('purchase_line_id','=',consolidate_line.purchase_line_id.id),('invoice_id','=',consolidate_line.consolidate_id.invoice_id.id)])
            inv_line_id = obj_inv_line.browse(cr, uid, id_inv_line)[0]
            price = (inv_line_id.price_unit * inv_line_id.quantity) - (inv_line_id.discount_amount + inv_line_id.discount_cash + inv_line_id.discount_lain + inv_line_id.discount_program)
            taxes = inv_line_id.invoice_line_tax_id.compute_all(price, 1, product=inv_line_id.product_id, partner=inv_line_id.invoice_id.partner_id)
            new_cost_price = taxes['total'] / inv_line_id.quantity
            consolidate_line.write({'price_unit':new_cost_price})
            move_journal = {
                'name': consolidate_line.consolidate_id.name,
                'ref': consolidate_line.consolidate_id.invoice_id.number,
                'journal_id': consolidate_line.product_id.categ_id.property_stock_journal.id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'transaction_id':consolidate_line.consolidate_id.id,
                'model':consolidate_line.consolidate_id.__class__.__name__,
            }
            
            move_line = [[0,False,{
                'name': [str(name) for id, name in consolidate_line.product_id.name_get()][0],
                'account_id': consolidate_line.product_id.categ_id.property_stock_account_input_categ.id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'debit': 0.0,
                'credit': round(new_cost_price*consolidate_line.product_qty,2),
                'branch_id': branch_id,
                'division': consolidate_line.consolidate_id.division,
                'analytic_account_id' : analytic_4,
                'product_id' : consolidate_line.product_id.id
            }]]
            
            move_line.append([0,False,{
                'name': [name for id, name in consolidate_line.product_id.name_get()][0],
                'account_id': debit_account,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'debit': round(new_cost_price*consolidate_line.product_qty,2),
                'credit': 0.0,
                'branch_id': branch_id,
                'division': consolidate_line.consolidate_id.division,
                'analytic_account_id' : analytic_4,
                'product_id' : consolidate_line.product_id.id
            }])
            
            move_journal['line_id'] = move_line
            create_journal = move_obj.create(cr, uid, move_journal)
            if consolidate_line.product_id.categ_id.property_stock_journal.entry_posted :
                post_journal = move_obj.post(cr, uid, create_journal)

        # UPDATE COST PRICE BERDASARKAN PRODUCT YANG SUDAH DI CONSOLIDATE AGAR BALANCE DENGAN CATATAN ACCOUNTING (HZ)
        context = {}
        vals = {}
        for line in consolidate_line.sorted(key=lambda r: r.product_id.id):
            move = line.move_id
            obj_product_price = self.pool.get('product.price.branch')
            cur = consolidate_line.consolidate_id.invoice_id.company_id.currency_id
            id_inv_line = obj_inv_line.search(cr, uid, [('purchase_line_id','=',line.purchase_line_id.id),('invoice_id','=',consolidate_line.consolidate_id.invoice_id.id)])
            inv_line_id = obj_inv_line.browse(cr, uid, id_inv_line)[0]
            tax_include = inv_line_id.invoice_line_tax_id[0].price_include if inv_line_id.invoice_line_tax_id else False
            if (line.move_id.location_id.usage == 'supplier') and (line.move_id.product_id.cost_method == 'average'):
                product_avail = self.pool.get('stock.quant')._get_stock_product_branch(cr, uid, line.move_id.location_dest_id.warehouse_id.id, line.product_id.id)
                if product_avail <= 0:
                    if line.move_id.location_id.usage == 'transit' or line.move_id.location_id.usage in ('internal','nrfs','kpb'):
                        old_cost_price = obj_product_price._get_price(cr, uid, line.move_id.location_dest_id.warehouse_id.id, line.product_id.id)
                        new_cost_price = obj_product_price._get_price(cr, uid, line.move_id.location_id.warehouse_id.id, line.product_id.id)
                        # old_cost_price = cur_obj.round(cr, uid, cur, old_cost_price)
                        # new_cost_price = cur_obj.round(cr, uid, cur, new_cost_price)
                        consolidate_line.write({'price_unit':new_cost_price})
                        context = {
                            'stock_qty': 0.0,
                            'old_cost_price': old_cost_price,
                            'trans_qty': line.product_qty,
                            'trans_price': new_cost_price,
                            'origin': line.move_id.picking_id.origin,
                            'product_template_id': line.product_id.product_tmpl_id.id,
                            'transaction_type': 'in',
                            'model_name': 'consolidate.invoice',
                            'trans_id': consolidate_line.consolidate_id.id,
                        }
                        vals = {
                            'cost': new_cost_price,
                            'warehouse_id': line.move_id.location_dest_id.warehouse_id.id,
                            'product_id': line.product_id.id,
                        }
                        self.update_price_branch(cr, uid, vals, context=context)
                    elif line.move_id.location_id.usage == 'supplier':
                        old_cost_price = obj_product_price._get_price(cr, uid, line.move_id.location_dest_id.warehouse_id.id, line.product_id.id)
                        old_cost_price = cur_obj.round(cr, uid, cur, old_cost_price)
                        # TRANS PRICE DIBAGI 1.1 KARENA UNTUK MENGAMBIL HARGA DPP TERGANTUNG APAKAH HARGA SUDAH TERMASUK PAJAK
                        price = (inv_line_id.price_unit * inv_line_id.quantity) - (inv_line_id.discount_amount + inv_line_id.discount_cash + inv_line_id.discount_lain + inv_line_id.discount_program)
                        taxes = inv_line_id.invoice_line_tax_id.compute_all(price, 1, product=inv_line_id.product_id, partner=inv_line_id.invoice_id.partner_id)
                        new_cost_price = taxes['total'] / inv_line_id.quantity
                        # new_cost_price = cur_obj.round(cr, uid, cur, trans_price)
                        context = {
                            'stock_qty': 0.0,
                            'old_cost_price': old_cost_price,
                            'trans_qty': line.product_qty,
                            'trans_price': new_cost_price,
                            'origin': move.picking_id.origin,
                            'product_template_id': move.product_id.product_tmpl_id.id,
                            'transaction_type': 'in',
                            'model_name': 'consolidate.invoice',
                            'trans_id': consolidate_line.consolidate_id.id,
                        }
                        vals = {
                            'warehouse_id': move.location_dest_id.warehouse_id.id,
                            'product_id': move.product_id.id,
                            'cost': new_cost_price
                        }
                        self.update_price_branch(cr, uid, vals, context=context)
                else:
                    if line.move_id.location_id.usage == 'transit' or line.move_id.location_id.usage in ('internal','nrfs','kpb'):
                        trans_price = obj_product_price._get_price(cr, uid, line.move_id.location_id.warehouse_id.id, line.product_id.id)
                        old_cost_price = obj_product_price._get_price(cr, uid, line.move_id.location_dest_id.warehouse_id.id, line.product_id.id)
                        new_cost_price = ((old_cost_price * product_avail) + (trans_price * line.product_qty)) / (product_avail + line.product_qty)
                        # new_cost_price = cur_obj.round(cr, uid, cur, new_cost_price)
                        consolidate_line.write({'price_unit':trans_price})
                        context = {
                            'stock_qty': product_avail,
                            'old_cost_price': old_cost_price,
                            'trans_qty': line.product_qty,
                            'trans_price': trans_price,
                            'origin': line.move_id.picking_id.origin,
                            'product_template_id': line.product_id.product_tmpl_id.id,
                            'transaction_type': 'in',
                            'model_name': 'consolidate.invoice',
                            'trans_id': consolidate_line.consolidate_id.id,
                        }
                        vals = {
                            'warehouse_id': line.move_id.location_dest_id.warehouse_id.id,
                            'product_id': line.product_id.id,
                            'cost': new_cost_price
                        }
                        self.update_price_branch(cr, uid, vals, context=context)
                    elif line.move_id.location_id.usage == 'supplier':
                        old_cost_price = obj_product_price._get_price(cr, uid, line.move_id.location_dest_id.warehouse_id.id, line.product_id.id)
                        # TRANS PRICE DIBAGI 1.1 KARENA UNTUK MENGAMBIL HARGA DPP TERGANTUNG APAKAH HARGA SUDAH TERMASUK PAJAK
                        price = (inv_line_id.price_unit * inv_line_id.quantity) - (inv_line_id.discount_amount + inv_line_id.discount_cash + inv_line_id.discount_lain + inv_line_id.discount_program)
                        taxes = inv_line_id.invoice_line_tax_id.compute_all(price, 1, product=inv_line_id.product_id, partner=inv_line_id.invoice_id.partner_id)
                        trans_price = taxes['total'] / inv_line_id.quantity
                        # if tax_include:
                        #     trans_price = (inv_line_id.price_subtotal / inv_line_id.quantity) / 1.1 
                        # else:
                        #     trans_price = inv_line_id.price_subtotal / inv_line_id.quantity
                        new_cost_price = ((old_cost_price * product_avail) + (trans_price * line.product_qty)) / (product_avail + line.product_qty)
                        # new_cost_price = cur_obj.round(cr, uid, cur, new_cost_price)
                        context = {
                            'stock_qty': product_avail,
                            'old_cost_price': old_cost_price,
                            'trans_qty': line.product_qty,
                            'trans_price': trans_price,
                            'origin': line.move_id.picking_id.origin,
                            'product_template_id': line.product_id.product_tmpl_id.id,
                            'transaction_type': 'in',
                            'model_name': 'consolidate.invoice',
                            'trans_id': consolidate_line.consolidate_id.id,
                        }
                        vals = {
                            'warehouse_id': line.move_id.location_dest_id.warehouse_id.id,
                            'product_id': line.product_id.id,
                            'cost': new_cost_price
                        }
                        self.update_price_branch(cr, uid, vals, context=context)
        return create_journal
    
    def write_invoice_line(self, cr, uid, ids, id_invoice, purchase_line_id, qty, context=None):
        consolidate_id = self.browse(cr, uid, ids, context)
        obj_inv_line = self.pool.get('account.invoice.line')


        id_inv_line = obj_inv_line.search(cr, uid, [('purchase_line_id','=',purchase_line_id.id),('invoice_id','=',id_invoice)])
        if not id_inv_line :
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan product '%s' untuk receipt '%s' di invoice yang dipilih\nPastikan Anda memilih invoice dan receipt untuk PO yang sama !" %(purchase_line_id.product_id.name,consolidate_id.invoice_id.number)))
        inv_line_id = obj_inv_line.browse(cr, uid, id_inv_line)[0]
        qty_before = inv_line_id.consolidated_qty
	inv_line_qty = 0
        for inv_line_id in obj_inv_line.browse(cr, uid, id_inv_line):
	    #print "Invoice id ='%s' dengan purchase line id ='%s' consolidate qty ='%s' %(id_invoice,purchase_line_id,inv_line_id.consolidated_qty)   
            inv_line_qty += inv_line_id.quantity
	#print qty_before + qty
	#print inv_line_qty
	#print inv_line_id
        if qty_before + qty <= inv_line_qty :
            inv_line_id.write({'consolidated_qty': qty_before + qty})
        else :
            raise osv.except_osv(('Perhatian !'), ("Quantity product '%s' melebihi qty invoice untuk PO '%s'" %(inv_line_id.product_id.name,purchase_line_id.order_id.name)))
        
    def write_move_line(self, cr, uid, ids, id_picking, purchase_line_id, qty, context=None):
        consolidate_id = self.browse(cr, uid, ids, context)
        obj_move = self.pool.get('stock.move')
        id_move = obj_move.search(cr, uid, [('purchase_line_id','=',purchase_line_id.id),('picking_id','=',id_picking),('state','not in',['draft','cancel'])])
        move_id = obj_move.browse(cr, uid, id_move)
        qty_before = move_id.consolidated_qty
        if qty_before + qty <= move_id.product_uom_qty :
            move_id.write({'consolidated_qty': qty_before + qty})
        else :
            raise osv.except_osv(('Perhatian !'), ("Quantity product '%s' melebihi qty receipt untuk PO '%s' !" %(move_id.product_id.name,purchase_line_id.order_id.name)))
    
    def write_receive_line(self, cr, uid, ids, id_receive, purchase_line_id, qty, context=None):
        consolidate_id = self.browse(cr, uid, ids, context)
        obj_receive_line = self.pool.get('dym2.receive.asset.line')
        id_receive_line = obj_receive_line.search(cr, uid, [('purchase_line_id','=',purchase_line_id.id),('receive_id','=',id_receive)])
        receive_line_id = obj_receive_line.browse(cr, uid, id_receive_line)
        qty_before = receive_line_id.consolidated_qty
        if qty_before + qty <= receive_line_id.quantity :
            receive_line_id.write({'consolidated_qty': qty_before + qty})
        else :
            raise osv.except_osv(('Perhatian !'), ("Quantity product '%s' melebihi qty receipt untuk PO '%s' !" %(receive_line_id.product_id.name,purchase_line_id.order_id.name)))

    def is_consolidated(self, cr, uid, ids, id_invoice, id_picking, id_receive, context=None):
        obj_invoice = self.pool.get('account.invoice')
        obj_picking = self.pool.get('stock.picking')
        obj_receive = self.pool.get('dym2.receive.asset')
        invoice_id = obj_invoice.browse(cr, uid, id_invoice)
        if all(line.quantity == line.consolidated_qty or line.product_id.type == 'service' for line in invoice_id.invoice_line) :
            invoice_id.write({'consolidated': True})
        else :
            invoice_id.write({'consolidated': False})
        
        if id_picking:
            picking_id = obj_picking.browse(cr, uid, id_picking)
            if all(line.product_uom_qty == line.consolidated_qty for line in picking_id.move_lines) :
                picking_id.write({'consolidated': True})
            else :
                picking_id.write({'consolidated': False})
        
        if id_receive:
            receive_id = obj_receive.browse(cr, uid, id_receive)
            if all(line.quantity == line.consolidated_qty or line.product_id.type == 'service' for line in receive_id.receive_line_ids) :
                receive_id.write({'consolidated': True})
            else :
                receive_id.write({'consolidated': False})

    def consolidate_confirm(self, cr, uid, ids, context=None):
        consolidate_id = self.browse(cr, uid, ids, context)
        obj_invoice_line = self.pool.get('account.invoice.line')
        obj_lot = self.pool.get('stock.production.lot')
        obj_quant = self.pool.get('stock.quant')
        product_price_obj = self.pool.get('product.price.branch')
        # if consolidate_id.asset == False:
        for line in consolidate_id.consolidate_line :
            create_move = self.create_move(cr, uid, ids, consolidate_id.branch_id.id, line)
            line.write({'account_move_id': create_move})
                # new_std_price = 0
                # if line.product_id.cost_method=='average':
                #     product_avail = self.pool.get('stock.quant')._get_stock_product_branch(cr, uid, line.move_id.location_dest_id.warehouse_id.id, line.product_id.id)
                #     average_price = product_price_obj._get_price(cr, uid, line.move_id.location_dest_id.warehouse_id.id, line.product_id.id)
                #     if product_avail <=0:
                #         new_std_price = line.price_unit
                #     else:
                #         new_std_price = ((average_price * product_avail) + (line.price_unit * line.product_qty)) / (product_avail + line.product_qty)
                    # self.pool.get('stock.move').update_price_branch(cr, uid, line.move_id.location_dest_id.warehouse_id.id, line.product_id.id, new_std_price)
                    # self.update_price_branch(cr, uid, {'warehouse_id':line.move_id.location_dest_id.warehouse_id.id, 'product_id':line.product_id.id, 'new_std_price':new_std_price})

        if consolidate_id.division == 'Unit' :
            for line in consolidate_id.consolidate_line :
                if not line.name :
                    raise osv.except_osv(('Perhatian !'), ("Lot tidak boleh kosong, silahkan cek kembali data Anda !"))
                obj_lot.write(cr, uid, [line.name.id], {'hpp': line.price_unit, 'state': 'stock', 'consolidate_id': consolidate_id.id})
                id_quant = obj_quant.search(cr, SUPERUSER_ID, [('lot_id','=',line.name.id)])
                obj_quant.write(cr, SUPERUSER_ID, id_quant, {'cost':line.price_unit, 'consolidated_date': datetime.now()})
                self.write_invoice_line(cr, uid, ids, consolidate_id.invoice_id.id, line.purchase_line_id, line.product_qty)
                self.write_move_line(cr, uid, ids, consolidate_id.picking_id.id, line.purchase_line_id, line.product_qty)
        elif consolidate_id.division in ('Sparepart','Umum') and consolidate_id.asset == False:
            for line in consolidate_id.consolidate_line:
                id_quant = obj_quant.search(cr, SUPERUSER_ID, [('product_id','=',line.product_id.id),('history_ids','in',line.move_id.id),('consolidated_date','=',False)])
                for quant in obj_quant.browse(cr, SUPERUSER_ID, id_quant) :
                    if line.product_qty < quant.qty :
                        obj_quant._quant_split(cr, uid, quant, line.product_qty)
                    quant.write({'cost':line.price_unit * quant.qty, 'consolidated_date':datetime.now()})
                self.write_invoice_line(cr, uid, ids, consolidate_id.invoice_id.id, line.purchase_line_id, line.product_qty)
                self.write_move_line(cr, uid, ids, consolidate_id.picking_id.id, line.purchase_line_id, line.product_qty)
        elif consolidate_id.division == 'Umum' and consolidate_id.asset == True:
            for line in consolidate_id.consolidate_line:
                self.write_invoice_line(cr, uid, ids, consolidate_id.invoice_id.id, line.purchase_line_id, line.product_qty)
                self.write_receive_line(cr, uid, ids, consolidate_id.receive_id.id, line.purchase_line_id, line.product_qty)
        
        if consolidate_id.asset == False:
            self.is_consolidated(cr, uid, ids, consolidate_id.invoice_id.id, consolidate_id.picking_id.id, False)
        else:
            self.is_consolidated(cr, uid, ids, consolidate_id.invoice_id.id, False, consolidate_id.receive_id.id)
        self.write(cr, uid, ids, {'date':datetime.today(), 'state':'done', 'confirm_uid':uid, 'confirm_date':datetime.now()})
    
    def create(self, cr, uid, vals, context=None):
        if not vals['consolidate_line'] :
            raise osv.except_osv(('Tidak bisa disimpan !'), ("Silahkan isi detil consolidate terlebih dahulu"))
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'CIN', division=vals['division'])
        return super(consolidate_invoice, self).create(cr, uid, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Consolidate sudah di proses, data tidak bisa dihapus !"))
        return super(consolidate_invoice, self).unlink(cr, uid, ids, context=context)    
    
    def picking_id_change(self, cr, uid, ids, picking_id, receive_id, asset, branch_id, division, invoice_id, partner_id, context=None):
        value = {}
        line_vals = []
        if asset == False and picking_id: 
            packing_ids = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id','=',picking_id),('state','=','posted')])
            if packing_ids:
                for packing in self.pool.get('dym.stock.packing').browse(cr, uid, packing_ids):
                    for line in packing.packing_line:
                        lot_change_vals = self.pool.get('consolidate.invoice.line').lot_change(cr, uid, ids, branch_id, division, line.serial_number_id.id, line.product_id.id, invoice_id, partner_id, picking_id, receive_id)
                        if 'warning' in lot_change_vals or (line.serial_number_id and (line.serial_number_id.state != 'intransit' or line.serial_number_id.consolidate_id)):
                            continue
                        res = {}
                        res['price_unit'] = lot_change_vals['value']['price_unit']
                        res['product_qty'] = lot_change_vals['value']['product_qty']
                        res['move_qty'] = lot_change_vals['value']['move_qty']
                        res['move_qty_show'] = lot_change_vals['value']['move_qty_show']
                        res['product_uom'] = lot_change_vals['value']['product_uom']
                        res['receive_line_id'] = lot_change_vals['value']['receive_line_id'] if 'receive_line_id' in lot_change_vals['value'] else False
                        res['move_id'] = lot_change_vals['value']['move_id'] if 'move_id' in lot_change_vals['value'] else False

                        res['product_id'] = line.product_id.id
                        res['template_id'] = line.product_id.product_tmpl_id.id
                        if line.serial_number_id:
                            res['name'] = line.serial_number_id.id
                        line_vals.append([0, 0, res])
        
        if asset == True and receive_id:
            receive_ids = self.pool.get('dym2.receive.asset').search(cr,uid,[('id','=',receive_id),('state','=','done')])
            if receive_ids:
                for receive in self.pool.get('dym2.receive.asset').browse(cr, uid, receive_ids):
                    for line in receive.receive_line_ids:
                        lot_change_vals = self.pool.get('consolidate.invoice.line').lot_change(cr, uid, ids, branch_id, division, False, line.product_id.id, invoice_id, partner_id, picking_id, receive_id)
                        if 'warning' in lot_change_vals:
                            continue
                        res = {}
                        res['price_unit'] = lot_change_vals['value']['price_unit']
                        res['product_qty'] = lot_change_vals['value']['product_qty']
                        res['move_qty'] = lot_change_vals['value']['move_qty']
                        res['move_qty_show'] = lot_change_vals['value']['move_qty_show']
                        res['product_uom'] = lot_change_vals['value']['product_uom']
                        res['receive_line_id'] = lot_change_vals['value']['receive_line_id'] if 'receive_line_id' in lot_change_vals['value'] else False
                        res['move_id'] = lot_change_vals['value']['move_id'] if 'move_id' in lot_change_vals['value'] else False
                        res['product_id'] = line.product_id.id
                        res['template_id'] = line.product_id.product_tmpl_id.id
                        line_vals.append((0, 0, res))
        value['consolidate_line'] = line_vals or False
        return {'value':value}

    def invoice_id_change(self, cr, uid, ids, id_invoice, id_partner, id_branch, division, context=None):
        value = {}
        domain = {}
        
        obj_invoice = self.pool.get('account.invoice')
        obj_invoice_line = self.pool.get('account.invoice.line')
        obj_lot = self.pool.get('stock.production.lot')
        obj_quant = self.pool.get('stock.quant')
        obj_picking = self.pool.get('stock.picking')
        obj_move = self.pool.get('stock.move')
        obj_receive = self.pool.get('dym2.receive.asset')
        obj_receive_line = self.pool.get('dym2.receive.asset.line')

        invoice_id = obj_invoice.browse(cr, uid, id_invoice)
        if invoice_id.asset == False:
            picking_ids = obj_picking.search(cr, uid, [('picking_type_code','=','incoming'),('branch_id','=',id_branch),('division','=',division),('state','=','done'),('partner_id','=',id_partner),('consolidated','=',False)])
            picking_domain = []
            for line in invoice_id.invoice_line:
                move_ids = obj_move.search(cr,uid,[('product_id','=',line.product_id.id),('state','=','done'),('picking_id','in',picking_ids),('purchase_line_id','=',line.purchase_line_id.id)])
                for move in obj_move.browse(cr, uid, move_ids):
                    if move.picking_id.id not in picking_domain:
                        picking_domain.append(move.picking_id.id)
            domain = {'picking_id':  [('id', 'in', picking_domain)]}
            value['picking_id'] = False       
            value['receive_id'] = False  
            value['asset'] = False     
        else:
            receive_ids = obj_receive.search(cr, uid, [('purchase_id.branch_id','=',id_branch),('purchase_id.division','=',division),('state','=','done'),('purchase_id.partner_id','=',id_partner),('consolidated','=',False)])
            receive_domain = []
            for line in invoice_id.invoice_line:
                receive_line_ids = obj_receive_line.search(cr,uid,[('product_id','=',line.product_id.id),('receive_id.state','=','done'),('receive_id','in',receive_ids),('purchase_line_id','=',line.purchase_line_id.id)])
                for receive_line in obj_receive_line.browse(cr, uid, receive_line_ids):
                    if receive_line.receive_id.id not in receive_domain:
                        receive_domain.append(receive_line.receive_id.id)
            domain = {'receive_id':  [('id', 'in', receive_domain)]}
            value['picking_id'] = False       
            value['receive_id'] = False  
            value['asset'] = True
        return {'value': value,'domain':domain}
    
class consolidate_invoice_line(osv.osv):
    _name = 'consolidate.invoice.line' 

    def _get_purchase_line_id(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.consolidate_id.asset == False:
                res[line.id] = line.move_id.purchase_line_id.id
            else:
                res[line.id] = line.receive_line_id.purchase_line_id.id
        return res

    def _get_subtotal(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            obj_inv_line = self.pool.get('account.invoice.line')
            id_inv_line = obj_inv_line.search(cr, uid, [('purchase_line_id','=',line.purchase_line_id.id),('invoice_id','=',line.consolidate_id.invoice_id.id)])
            inv_line_id = obj_inv_line.browse(cr, uid, id_inv_line)[0]
            price = (inv_line_id.price_unit * inv_line_id.quantity) - (inv_line_id.discount_amount + inv_line_id.discount_cash + inv_line_id.discount_lain + inv_line_id.discount_program)
            taxes = inv_line_id.invoice_line_tax_id.compute_all(price, 1, product=inv_line_id.product_id, partner=inv_line_id.invoice_id.partner_id)
            final_unit_price = taxes['total'] / inv_line_id.quantity
            subtotal = round(final_unit_price*line.product_qty,2)
            res[line.id] = subtotal
        return res

    _columns = {
        'consolidate_id': fields.many2one('consolidate.invoice', 'Consolidate Invoice', required=True, ondelete='cascade'),
        'name': fields.many2one('stock.production.lot', 'Lot (NOSIN)'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.integer('Invoice Qty'),
        'move_qty': fields.integer('GRN Qty'),
        'move_qty_show': fields.related('move_qty',string='GRN Qty'),
        'consolidated_qty': fields.integer('Consolidated Qty'),
        'move_id': fields.many2one('stock.move', 'Stock Move'),
        'receive_line_id': fields.many2one('dym2.receive.asset.line', 'Receive Line'),
        'purchase_line_id': fields.function(_get_purchase_line_id, string='PO Line', type='many2one', method=True, relation='purchase.order.line',), 
        'product_uom': fields.many2one('product.uom', 'UoM', required=True),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price')),
        'price_subtotal': fields.function(_get_subtotal, string='Subtotal', type='float', method=True), 
        'account_move_id': fields.many2one('account.move', 'Account Move'),
        'template_id':fields.many2one('product.template', 'Tipe'),
    }
    
    _sql_constraints = [
        ('unique_product_id', 'unique(consolidate_id,product_id,name)', 'Ditemukan Lot/Product duplicate, silahkan cek kembali'),
    ]
    
    def _auto_init(self,cr,context=None):
        result = super(consolidate_invoice_line,self)._auto_init(cr,context=context)
        cr.execute("""
            DROP INDEX IF EXISTS consolidate_invoice_line_unique_product_id_action_index;
            CREATE UNIQUE INDEX consolidate_invoice_line_unique_product_id_action_index on consolidate_invoice_line (consolidate_id,product_id)
            WHERE name IS NULL;
        """)
        return result
    
    def create(self, cr, uid, vals, context=None):
        if vals['product_qty'] <= 0 or vals['price_unit'] < 0 :
            raise osv.except_osv(('Tidak bisa disimpan !'), ("Product Qty dan Price Unit tidak boleh 0"))
        return super(consolidate_invoice_line, self).create(cr, uid, vals, context=context)
        
    def lot_change(self, cr, uid, ids, id_branch, division, id_lot, id_product, id_invoice, id_partner, id_picking, id_receive, template_id=False):
        if not id_branch or not division or not id_invoice or not id_partner and (not id_picking or not id_receive):
            raise osv.except_osv(('Warning'),('Silahkan lengkapi data header terlebih dahulu'))
        res = {}
        domain = {}
        products = []
        obj_invoice = self.pool.get('account.invoice')
        obj_invoice_line = self.pool.get('account.invoice.line')
        obj_lot = self.pool.get('stock.production.lot')
        obj_quant = self.pool.get('stock.quant')
        obj_picking = self.pool.get('stock.picking')
        obj_move = self.pool.get('stock.move')
        obj_receive = self.pool.get('dym2.receive.asset')
        obj_receive_line = self.pool.get('dym2.receive.asset.line')
        invoice_id = obj_invoice.browse(cr, uid, id_invoice)
        if id_lot :
            lot_id = obj_lot.browse(cr, uid, id_lot)
            id_move = obj_move.search(cr,uid,[('product_id','=',lot_id.product_id.id),('picking_id','=',id_picking),('state','=','done')])
            move_id = obj_move.browse(cr, uid, id_move)

            res['product_id'] = lot_id.product_id.id
            res['template_id'] = lot_id.product_id.product_tmpl_id.id
            res['product_uom'] = lot_id.product_id.uom_id.id
            res['product_qty'] = 1
            res['move_qty'] = 1
            res['move_qty_show'] = 1
            res['move_id'] = move_id.id
            
            id_inv_line = obj_invoice_line.search(cr, uid,
                [('purchase_line_id','=',move_id.purchase_line_id.id),
                ('invoice_id','=',id_invoice),
                ])
            if id_inv_line :
                inv_line_id = obj_invoice_line.browse(cr, uid, id_inv_line)[0]
                price = (inv_line_id.price_unit * inv_line_id.quantity) - (inv_line_id.discount_amount + inv_line_id.discount_cash + inv_line_id.discount_lain + inv_line_id.discount_program)
                taxes = inv_line_id.invoice_line_tax_id.compute_all(price, 1, product=inv_line_id.product_id, partner=inv_line_id.invoice_id.partner_id)
                new_cost_price = taxes['total'] / inv_line_id.quantity
                res['price_unit'] = new_cost_price
            else :
                return {'value':{'price_unit':False}, 'warning':{'title':'Attention!','message':"Tidak ditemukan product '%s' warna '%s' di invoice '%s' untuk receipt yang dipilih,\nPastikan Anda memilih invoice dan receipt untuk PO yang sama !" %(lot_id.product_id.name,lot_id.product_id.attribute_value_ids.name,invoice_id.number)}}
        elif id_product :
            if invoice_id.asset == False:
                id_move = obj_move.search(cr,uid,[('product_id','=',id_product),('picking_id','=',id_picking),('state','=','done')])
                move_id = obj_move.browse(cr, uid, id_move)
                if not move_id:
                    return {'value':{'product_id':False},'101 warning':{'title':'Attention!','message':'Tidak ditemukan product yg dipilih dalam receipt !'}}
                
                id_quant = obj_quant.search(cr,SUPERUSER_ID,[('product_id','=',id_product),('history_ids','in',id_move),('consolidated_date','=',False)])
                
                if not id_quant:
                    return {'value':{'product_id':False},'102 warning':{'title':'Attention!','message':'Tidak ditemukan product yg dipilih dalam receipt'}}
                quant_id = obj_quant.browse(cr,uid,id_quant[0])
                
                id_inv_line = self.pool.get('account.invoice.line').search(cr, uid,
                    [('purchase_line_id','=',move_id.purchase_line_id.id),
                    ('invoice_id','=',id_invoice),
                    ])
                if id_inv_line :
                    # search_return_history = move_obj.search(cr, uid, [('origin_returned_move_id', '=', move_id.id), ('state', 'not in', ('draft','cancel'))])
                    # return_history_qty = 0
                    # for return_history in obj_move.browse(cr, uid, search_return_history):
                    #     return_history_qty += return_history.product_uom_qty
                    inv_line_id = obj_invoice_line.browse(cr, uid, id_inv_line)[0]
                    price = (inv_line_id.price_unit * inv_line_id.quantity) - (inv_line_id.discount_amount + inv_line_id.discount_cash + inv_line_id.discount_lain + inv_line_id.discount_program)
                    taxes = inv_line_id.invoice_line_tax_id.compute_all(price, 1, product=inv_line_id.product_id, partner=inv_line_id.invoice_id.partner_id)
                    new_cost_price = taxes['total'] / inv_line_id.quantity
                    res['price_unit'] = new_cost_price
                    res['product_qty'] = move_id.product_qty - move_id.consolidated_qty
                    res['move_qty'] = move_id.product_qty - move_id.consolidated_qty
                    res['move_qty_show'] = move_id.product_qty - move_id.consolidated_qty
                    res['product_uom'] = move_id.product_uom.id
                    res['move_id'] = id_move[0]
                else :
                    product_id = self.pool.get('product.product').browse(cr, uid, id_product)
                    return {'value':{'price_unit':False}, 'warning':{'title':'Attention!','message':"Tidak ditemukan product '%s' di invoice '%s' untuk receipt yang dipilih,\nPastikan Anda memilih invoice dan receipt untuk PO yang sama !" %(product_id.name,invoice_id.number)}}
            else:
                id_receive_line = obj_receive_line.search(cr,uid,[('product_id','=',id_product),('receive_id','=',id_receive),('receive_id.state','=','done')])
                receive_line_id = obj_receive_line.browse(cr, uid, id_receive_line)
                if not receive_line_id:
                    return {'value':{'product_id':False},'103 warning':{'title':'Attention!','message':'Tidak ditemukan product yg dipilih dalam receipt !'}}
                
                id_inv_line = self.pool.get('account.invoice.line').search(cr, uid,
                    [('purchase_line_id','=',receive_line_id.purchase_line_id.id),
                    ('invoice_id','=',id_invoice),
                    ])
                if id_inv_line :
                    inv_line_id = obj_invoice_line.browse(cr, uid, id_inv_line)[0]
                    price = (inv_line_id.price_unit * inv_line_id.quantity) - (inv_line_id.discount_amount + inv_line_id.discount_cash + inv_line_id.discount_lain + inv_line_id.discount_program)
                    taxes = inv_line_id.invoice_line_tax_id.compute_all(price, 1, product=inv_line_id.product_id, partner=inv_line_id.invoice_id.partner_id)
                    new_cost_price = taxes['total'] / inv_line_id.quantity
                    res['price_unit'] = new_cost_price
                    res['product_qty'] = receive_line_id.quantity - receive_line_id.consolidated_qty
                    res['move_qty'] = receive_line_id.quantity - receive_line_id.consolidated_qty
                    res['move_qty_show'] = receive_line_id.quantity - receive_line_id.consolidated_qty
                    res['product_uom'] = receive_line_id.product_id.uom_id.id
                    res['receive_line_id'] = id_receive_line[0]
                else :
                    product_id = self.pool.get('product.product').browse(cr, uid, id_product)
                    return {'value':{'price_unit':False}, 'warning':{'title':'Attention!','message':"Tidak ditemukan product '%s' di invoice '%s' untuk receipt yang dipilih,\nPastikan Anda memilih invoice dan receipt untuk PO yang sama !" %(product_id.name,invoice_id.number)}}
        templates = []
        if invoice_id.asset == False:
            picking_id = obj_picking.browse(cr, uid, id_picking)
            for move in picking_id.move_lines :
                products.append(move.product_id.id)
                templates.append(move.product_id.product_tmpl_id.id)
            domain['product_id']=[('id','in',products),('product_tmpl_id','=',template_id)]
            domain['template_id']=[('id','in',templates)]
        else:
            receive_id = obj_receive.browse(cr, uid, id_receive)
            for receive_line in receive_id.receive_line_ids :
                products.append(receive_line.product_id.id)
                templates.append(receive_line.product_id.product_tmpl_id.id)
            domain['product_id']=[('id','in',products),('product_tmpl_id','=',template_id)]
            domain['template_id']=[('id','in',templates)]
        if template_id:
            template = self.pool.get('product.template').browse(cr, uid, [template_id])
            if len(template.product_variant_ids) == 1:
                res['product_id'] = template.product_variant_ids.id
            if id_product and id_product not in template.product_variant_ids.ids:
                res['product_id'] = False
        return {'value': res,'domain':domain}
    
    def product_qty_change(self, cr, uid, ids, product_qty, move_qty):
        if product_qty and move_qty :
            if product_qty < 0:
                return {'value':{'product_qty':move_qty},'warning':{'title':'Attention!','message':'Product Qty tidak boleh negatif'}}
            if product_qty > move_qty:
                return {'value':{'product_qty':move_qty},'warning':{'title':'Attention!','message':'Product Qty tidak boleh melebihi move qty'}}
        return True

class stock_quant(osv.osv):
    
    _inherit = 'stock.quant'

    def _get_state(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):            
            state = ''
            if line.product_category == 'Unit':
                state = 'intransit' if line.lot_id.state == 'intransit' and line.location_id.usage in ['internal','nrfs','kpb'] else 'Ready for Sale' if line.lot_id.state == 'stock' and line.location_id.usage == 'internal' and not line.reservation_id else 'Not Ready for Sale' if line.lot_id.state == 'stock' and line.location_id.usage in ['nrfs','kpb'] and not line.reservation_id else 'Undelivered' if line.lot_id.state in ['sold','sold_offtr','paid','paid_offtr'] and line.location_id.usage in ['internal','nrfs','kpb'] else 'Transferred' if line.lot_id.state in ['sold','sold_offtr','paid','paid_offtr'] and line.location_id.usage == 'customer' else 'Reserved' if (line.lot_id.state == 'reserved' or line.reservation_id) and line.location_id.usage in ['internal','nrfs','kpb']  else 'Purchase Return' if line.lot_id.state == 'returned' and line.location_id.usage in ['internal','nrfs','kpb'] else 'Transferred' if line.lot_id.state == 'returned' and line.location_id.usage == 'supplier' else 'Asset' if line.lot_id.state == 'asset' else ''
            elif line.product_category == 'Extras':
                state = 'Ready for Sale' if line.location_id.usage == 'internal' and not line.reservation_id else 'Not Ready for Sale' if line.location_id.usage in ['nrfs','kpb'] and not line.reservation_id else 'Undelivered' if line.reservation_id and line.location_id.usage in ['internal','nrfs','kpb'] else 'Transferred' if not line.reservation_id and line.location_id.usage == 'customer' else ''
            else:
                state = 'intransit' if not line.consolidated_date and line.location_id.usage in ['internal','nrfs','kpb'] else 'Ready for Sale' if line.consolidated_date and line.location_id.usage == 'internal' and not line.reservation_id else 'Not Ready for Sale' if line.consolidated_date and line.location_id.usage in ['nrfs','kpb'] and not line.reservation_id else 'Undelivered' if line.reservation_id and line.location_id.usage in ['internal','nrfs','kpb'] else 'Transferred' if not line.reservation_id and line.location_id.usage == 'customer' else ''
            res[line.id] = state
        return res

    _columns = {
        'consolidated_date' :fields.datetime('Consolidated Date'),
        'warehouse_id': fields.related('location_id', 'warehouse_id', relation='stock.warehouse', type='many2one', string="Warehouse"),
        'state': fields.function(_get_state, string='Status', type='char', method=True), 
    }
