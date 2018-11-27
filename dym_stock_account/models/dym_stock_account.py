from openerp.osv import osv, fields
from openerp import SUPERUSER_ID, api
from openerp import tools
    
class stock_history(osv.osv):
    _inherit = 'stock.history'

    def _get_inventory_value(self, cr, uid, ids, name, attr, context=None):
        if context is None:
            context = {}
        date = context.get('history_date')
        product_tmpl_obj = self.pool.get("product.template")
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.product_id.cost_method == 'real':
                res[line.id] = line.quantity * line.price_unit_on_quant
            elif line.product_id.cost_method == 'average':
                product_price_obj = self.pool.get('product.price.branch')
                unit_price = product_price_obj._get_price(cr, uid, line.location_id.warehouse_id.id, line.product_id.id)
                res[line.id] = line.quantity * unit_price
            else:
                res[line.id] = line.quantity * product_tmpl_obj.get_history_price(cr, uid, line.product_id.product_tmpl_id.id, line.company_id.id, date=date, context=context)
        return res

    _columns = {
        'inventory_value': fields.function(_get_inventory_value, string="Inventory Value", type='float', readonly=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'stock_history')
        cr.execute("""
            CREATE OR REPLACE VIEW stock_history AS (
              SELECT MIN(id) as id,
                move_id,
                location_id,
                company_id,
                product_id,
                product_categ_id,
                SUM(quantity) as quantity,
                date,
                price_unit_on_quant,
                source
                FROM
                ((SELECT
                    stock_move.id::text || '-' || quant.id::text AS id,
                    quant.id AS quant_id,
                    stock_move.id AS move_id,
                    dest_location.id AS location_id,
                    dest_location.company_id AS company_id,
                    stock_move.product_id AS product_id,
                    product_template.categ_id AS product_categ_id,
                    quant.qty AS quantity,
                    stock_move.date AS date,
                    quant.cost as price_unit_on_quant,
                    stock_move.origin AS source
                FROM
                    stock_quant as quant, stock_quant_move_rel, stock_move
                LEFT JOIN
                   stock_location dest_location ON stock_move.location_dest_id = dest_location.id
                LEFT JOIN
                    stock_location source_location ON stock_move.location_id = source_location.id
                LEFT JOIN
                    product_product ON product_product.id = stock_move.product_id
                LEFT JOIN
                    product_template ON product_template.id = product_product.product_tmpl_id
                WHERE quant.qty>0 AND stock_move.state = 'done' AND dest_location.usage in ('internal','nrfs','kpb') AND stock_quant_move_rel.quant_id = quant.id
                AND stock_quant_move_rel.move_id = stock_move.id AND (
                    (source_location.company_id is null and dest_location.company_id is not null) or
                    (source_location.company_id is not null and dest_location.company_id is null) or
                    source_location.company_id != dest_location.company_id or
                    source_location.usage not in ('internal','nrfs','kpb'))
                ) UNION
                (SELECT
                    '-' || stock_move.id::text || '-' || quant.id::text AS id,
                    quant.id AS quant_id,
                    stock_move.id AS move_id,
                    source_location.id AS location_id,
                    source_location.company_id AS company_id,
                    stock_move.product_id AS product_id,
                    product_template.categ_id AS product_categ_id,
                    - quant.qty AS quantity,
                    stock_move.date AS date,
                    quant.cost as price_unit_on_quant,
                    stock_move.origin AS source
                FROM
                    stock_quant as quant, stock_quant_move_rel, stock_move
                LEFT JOIN
                    stock_location source_location ON stock_move.location_id = source_location.id
                LEFT JOIN
                    stock_location dest_location ON stock_move.location_dest_id = dest_location.id
                LEFT JOIN
                    product_product ON product_product.id = stock_move.product_id
                LEFT JOIN
                    product_template ON product_template.id = product_product.product_tmpl_id
                WHERE quant.qty>0 AND stock_move.state = 'done' AND source_location.usage in ('internal','nrfs','kpb') AND stock_quant_move_rel.quant_id = quant.id
                AND stock_quant_move_rel.move_id = stock_move.id AND (
                    (dest_location.company_id is null and source_location.company_id is not null) or
                    (dest_location.company_id is not null and source_location.company_id is null) or
                    dest_location.company_id != source_location.company_id or
                    dest_location.usage not in ('internal','nrfs','kpb'))
                ))
                AS foo
                GROUP BY move_id, location_id, company_id, product_id, product_categ_id, date, price_unit_on_quant, source
            )""")

class stock_location(osv.osv):
    _inherit = "stock.location"

    def _location_owner(self, cr, uid, location, context=None):
        ''' Return the company owning the location if any '''
        return location and (location.usage in ('internal','nrfs','kpb')) and location.company_id or False

class stock_quant(osv.osv):
    _inherit = "stock.quant"
    
    def _get_stock_product_branch(self, cr, uid, warehouse_id, product_id, move_id=False):
        stock = 0
        product = self.pool.get('product.product').browse(cr, uid, product_id)
        if  product.categ_id.get_root_name() == 'Unit':
            quant_domain = [('location_id.warehouse_id','=',warehouse_id),('location_id.usage','in',['nrfs','kpb','internal']),('product_id','=',product_id),'|','&',('lot_id.state','=','stock'),('reservation_id','=',False),'|',('lot_id.state','=','reserved'),'&',('reservation_id','!=',False),('lot_id.state','not in',['sold','sold_offtr','paid','paid_offtr'])]
            if move_id:
                quant_domain = [('location_id.warehouse_id','=',warehouse_id),('location_id.usage','in',['nrfs','kpb','internal']),('product_id','=',product_id),'|','|','&',('lot_id.state','=','stock'),('reservation_id','=',False),'|',('lot_id.state','=','reserved'),'&',('reservation_id','!=',False),('lot_id.state','not in',['sold','sold_offtr','paid','paid_offtr']),'&',('reservation_id','=',move_id),('lot_id.state','in',['stock','reserved','sold','sold_offtr','paid','paid_offtr'])]
        else:
            quant_domain = [('location_id.warehouse_id','=',warehouse_id),('location_id.usage','in',['nrfs','kpb','internal']),('product_id','=',product_id),('consolidated_date','!=',False),'|',('reservation_id','=',False),('reservation_id','=',move_id)]
        quant_obj = self.pool.get('stock.quant')
        quant_ids = quant_obj.search(cr, uid, quant_domain)
        if quant_ids:
            for quants in self.pool.get('stock.quant').browse(cr, uid, quant_ids):
                stock += quants.qty
        history_id = self.pool.get('product.price.history').search(cr, uid, [('warehouse_id','=',warehouse_id),('product_id','=',product_id)], order='date desc', limit=1)
        if history_id:
            history = self.pool.get('product.price.history').browse(cr, uid, history_id)
            if stock != history.new_qty:
                stock = history.new_qty
        return stock

    def _account_entry_move(self, cr, uid, quants, move, context=None):
        """
        Accounting Valuation Entries

        quants: browse record list of Quants to create accounting valuation entries for. Unempty and all quants are supposed to have the same location id (thay already moved in)
        move: Move to use. browse record
        """
        if context is None:
            context = {}
        location_obj = self.pool.get('stock.location')
        location_from = move.location_id
        location_to = quants[0].location_id
        company_from = location_obj._location_owner(cr, uid, location_from, context=context)
        company_to = location_obj._location_owner(cr, uid, location_to, context=context)
        if move.product_id.valuation != 'real_time':
            return False
        for q in quants:
            if q.owner_id:
                #if the quant isn't owned by the company, we don't make any valuation entry
                return False
            if q.qty <= 0:
                #we don't make any stock valuation for negative quants because the valuation is already made for the counterpart.
                #At that time the valuation will be made at the product cost price and afterward there will be new accounting entries
                #to make the adjustments when we know the real cost price.
                return False
        #in case of routes making the link between several warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        # Create Journal Entry for products arriving in the company
        if company_to and (move.location_id.usage not in ('internal','nrfs','kpb','transit') and move.location_dest_id.usage in ('internal','nrfs','kpb') or company_from != company_to):
            ctx = context.copy()
            ctx['force_company'] = company_to.id
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, move, context=ctx)
            if location_from and location_from.usage == 'customer':
                if move.retur_jual_line_id.retur_id.retur_type != 'Barang':
                    #goods returned from customer
                    self._create_account_move_line(cr, uid, quants, move, acc_dest, acc_valuation, journal_id, context=ctx)
            else:
                if (location_from and location_from.usage != 'supplier') or (location_from and location_from.usage == 'supplier' and not move.purchase_line_id and move.retur_beli_line_id.retur_id.retur_type != 'Barang'):
                    self._create_account_move_line(cr, uid, quants, move, acc_src, acc_valuation, journal_id, context=ctx)

        # Create Journal Entry for products leaving the company
        if company_from and (move.location_id.usage in ('internal','nrfs','kpb') and move.location_dest_id.usage not in ('internal','nrfs','kpb','transit') or company_from != company_to):
            ctx = context.copy()
            ctx['force_company'] = company_from.id
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, move, context=ctx)
            if location_to and location_to.usage == 'supplier':
                if (move.picking_id.create_manual == True or not move.picking_id) and move.retur_beli_line_id.retur_id.retur_type != 'Barang':
                    #goods returned to supplier
                    self._create_account_move_line(cr, uid, quants, move, acc_valuation, acc_src, journal_id, context=ctx)
            else:
                if (move.picking_id.create_manual == True or move.inventory_id or not move.picking_id or location_to.usage != 'customer') and move.retur_jual_line_id.retur_id.retur_type != 'Barang':
                    if location_to.usage == 'transit':
                        self._create_account_move_line(cr, uid, quants, move, acc_valuation, acc_src, journal_id, context=ctx)
                    else:
                        self._create_account_move_line(cr, uid, quants, move, acc_valuation, acc_dest, journal_id, context=ctx)            

    def _create_account_move_line(self, cr, uid, quants, move, credit_account_id, debit_account_id, journal_id, context=None):
        #group quants by cost
        quant_cost_qty = {}
        for quant in quants:
            if quant_cost_qty.get(quant.cost):
                quant_cost_qty[quant.cost] += quant.qty
            else:
                quant_cost_qty[quant.cost] = quant.qty
        move_obj = self.pool.get('account.move')
        for cost, qty in quant_cost_qty.items():
            move_lines = self._prepare_account_move_line(cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=context)
            period_id = context.get('force_period', self.pool.get('account.period').find(cr, uid, context=context)[0])
            move_obj.create(cr, uid, {'journal_id': journal_id,
                                      'line_id': move_lines,
                                      'period_id': period_id,
                                      'date': fields.date.context_today(self, cr, uid, context=context),
                                      'ref': move.picking_id.name,
                                      'transaction_id': move.picking_id.id if move.picking_id else move.inventory_id.id if move.inventory_id else 0,
                                      'model': move.picking_id.__class__.__name__ if move.picking_id else move.inventory_id.__class__.__name__ if move.inventory_id else ''}, context=context)

    def _prepare_account_move_line(self, cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=None):
        if context is None:
            context = {}
        product_price_obj = self.pool.get('product.price.branch')
        # if move.price_unit <= 0.01:
        #     warehouse_id = move.location_id.warehouse_id.id
        #     if not move.location_id.warehouse_id:
        #         warehouse_id = move.location_dest_id.warehouse_id.id
        #     average_price = product_price_obj._get_price(cr, uid, warehouse_id, move.product_id.id)
        #     move.write({'price_unit':average_price})
        res = super(stock_quant, self)._prepare_account_move_line(cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=context)
        if context.get('force_valuation_amount'):
            valuation_amount = context.get('force_valuation_amount')
        else:
            if move.product_id.cost_method == 'average':
                valuation_amount = move.price_unit
            else:
                valuation_amount = cost if move.product_id.cost_method == 'real' else move.product_id.standard_price
        res[0][2].update({
                        'debit': valuation_amount * qty if res[0][2]['debit'] > 0 else 0,
                        'credit': valuation_amount * qty if res[0][2]['credit'] > 0 else 0,
                        })
        res[1][2].update({
                        'debit': valuation_amount * qty if res[1][2]['debit'] > 0 else 0,
                        'credit': valuation_amount * qty if res[1][2]['credit'] > 0 else 0,
                        })
        analytic_4 = False
        branch =  move.picking_id.branch_id or move.inventory_id.warehouse_id.branch_id or move.inventory_id.location_id.branch_id or move.branch_id
        if context != None and 'inventory' in context:
            inv = context['inventory']
            branch = move.picking_id.branch_id or inv.warehouse_id.branch_id or inv.location_id.branch_id or move.branch_id 
            res[0][2]['branch_id'] = branch.id
            res[1][2]['branch_id'] = branch.id
            res[0][2]['analytic_account_id'] = move.inventory_id.analytic_4.id
            res[1][2]['analytic_account_id'] = move.inventory_id.analytic_4.id
            del context['inventory']
        if branch and ('analytic_account_id' not in res[0][2] or not res[0][2]['analytic_account_id']):
            cost_center = ''
            category = ''
            if move.product_id.categ_id.get_root_name() in ('Unit','Extras'):
                cost_center = 'Sales'
                # category = 'Unit'
            elif move.product_id.categ_id.get_root_name() == 'Sparepart':
                cost_center = 'Sparepart_Accesories'
                # category = 'Sparepart'
            elif move.product_id.categ_id.get_root_name() =='Umum':
                cost_center = 'General'
                # category = 'Umum'
            elif move.product_id.categ_id.get_root_name() =='Service':
                cost_center = 'Service'
                # category = 'Service'
            else:
                raise osv.except_osv(('Attention!'),('Analytic Account tidak ditemukan mohon hubungi sistem administrator anda. %s!') % (move.product_id.name))
            if cost_center:
                categ_obj = move.product_id.categ_id
                category = ''
                if move.product_id.categ_id.get_root_name() == 'Extras':
                    categ_obj = False
                    category = 'Unit'
                analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, category, categ_obj, 4, cost_center)
                analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, category, categ_obj, 4, 'General')
                journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, move, context=context)
                res[0][2]['analytic_account_id'] = analytic_4_general if res[0][2]['account_id'] == acc_valuation else analytic_4
                res[1][2]['analytic_account_id'] = analytic_4_general if res[1][2]['account_id'] == acc_valuation else analytic_4
                res[0][2]['branch_id'] = branch.id
                res[1][2]['branch_id'] = branch.id
                if move.location_id.sudo().branch_id and branch != move.location_id.sudo().branch_id and move.location_id.usage == 'transit':
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, move.location_id.sudo().branch_id, category, categ_obj, 4, cost_center)
                    res[1][2]['analytic_account_id'] = analytic_4
                    res[1][2]['branch_id'] = move.location_id.sudo().branch_id.id
        new_valuation_amount = 0.0
        for item in res:
            item[2].update({
                        # 'branch_id': branch.id,
                        'division': move.picking_id.division or move.inventory_id.division,
                            })
        currency_obj = self.pool.get('res.currency')
        if move.product_id.cost_method == 'average':
            # if move.location_id.usage == 'transit' or move.location_id.usage == 'internal' or move.location_id.usage == 'inventory':
            #     warehouse_id = move.location_dest_id.warehouse_id.id
            #     if not move.location_dest_id.warehouse_id:
            #         warehouse_id = move.location_id.warehouse_id.id
            #     new_valuation_amount = product_price_obj._get_price(cr, uid, warehouse_id, move.product_id.id) * qty
            #     move.update({'real_hpp':new_valuation_amount})

            # elif move.location_id.usage == 'supplier':
            #     new_valuation_amount = (move.price_unit/1.1) * qty

            if move.location_dest_id.usage == 'inventory' and move.location_id.usage in ('internal','nrfs','kpb'):
                debit_account_id = move.inventory_id.loss_account.id
                res[0][2].update({
                            'debit': move.price_unit * qty,
                            'account_id': debit_account_id
                            })
                res[1][2].update({
                                'credit': move.price_unit * qty,
                                })
            elif move.location_dest_id.usage in ('internal','nrfs','kpb') and move.location_id.usage == 'inventory':
                credit_account_id = move.inventory_id.income_account.id
                res[0][2].update({
                            'debit': move.price_unit * qty,
                            })
                res[1][2].update({
                                'credit': move.price_unit * qty,
                                'account_id': credit_account_id
                                })
            valuation_amount = move.price_unit * qty
                
        else:
            if move.location_dest_id.usage == 'inventory' and move.location_id.usage in ('internal','nrfs','kpb'):
                debit_account_id = move.inventory_id.loss_account.id
                res[0][2].update({
                            'debit': move.price_unit * qty,
                            'account_id': debit_account_id
                            })
                res[1][2].update({
                                'credit': move.price_unit * qty,
                                })
            elif move.location_dest_id.usage in ('internal','nrfs','kpb') and move.location_id.usage == 'inventory':
                credit_account_id = move.inventory_id.income_account.id
                res[0][2].update({
                            'debit': move.price_unit * qty,
                            })
                res[1][2].update({
                                'credit': move.price_unit * qty,
                                'account_id': credit_account_id
                                })
            valuation_amount = move.price_unit * qty
            move.update({'real_hpp':valuation_amount})
        #the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        #the company currency... so we need to use round() before creating the accounting entries.
        valuation_amount = currency_obj.round(cr, uid, move.company_id.currency_id, valuation_amount * qty)
        partner_id = (move.picking_id.partner_id and self.pool.get('res.partner')._find_accounting_partner(move.picking_id.partner_id).id) or False
        price_diff = 0.0
        
        #get force_cogs value from account invoice line, the value has been multiplied with product_qty
        cogs_inv = currency_obj.round(cr, uid, move.company_id.currency_id, move.undelivered_value * qty)
        
        # if cogs_inv >0:
        #     if currency_obj.round(cr, uid, move.company_id.currency_id, cogs_inv) != valuation_amount:
        #         pricediff_acc = move.product_id.property_account_creditor_price_difference and move.product_id.property_account_creditor_price_difference.id
        #         if not pricediff_acc:
        #             pricediff_acc = move.product_id.categ_id.property_account_creditor_price_difference_categ and move.product_id.categ_id.property_account_creditor_price_difference_categ.id
                
        #         output_acc = move.product_id.property_stock_account_output and move.product_id.property_stock_account_output_categ.id
        #         if not output_acc:
        #             output_acc = move.product_id.categ_id.property_stock_account_output_categ and move.product_id.categ_id.property_stock_account_output_categ.id    
                
        #         if not (pricediff_acc and output_acc):
        #             raise osv.except_osv(('Attention!'),('Tidak Ditemukan account price different product %s!') % (move.product_id.name))
        #         price_diff = round(cogs_inv - valuation_amount,2)
        #         if price_diff != 0:
        #             debit_diff_vals = {
        #                 'name': move.name,
        #                 'product_id': move.product_id.id,
        #                 'quantity': qty,
        #                 'product_uom_id': move.product_id.uom_id.id,
        #                 'ref': move.picking_id and move.picking_id.name or False,
        #                 'date': move.date,
        #                 'partner_id': partner_id,
        #                 'debit': price_diff > 0 and price_diff or 0,
        #                 'credit': price_diff < 0 and -price_diff or 0,
        #                 'account_id': output_acc,
        #                 'branch_id': branch.id,
        #                 'division': move.picking_id.division,
        #                 'analytic_account_id' : analytic_4
        #                 }
        #             res.append((0,0,debit_diff_vals))
        #             credit_diff_vals = {
        #                 'name': 'Price Different '+move.name,
        #                 'product_id': move.product_id.id,
        #                 'quantity': qty,
        #                 'product_uom_id': move.product_id.uom_id.id,
        #                 'ref': move.picking_id and move.picking_id.name or False,
        #                 'date': move.date,
        #                 'partner_id': partner_id,
        #                 'debit': price_diff < 0 and -price_diff or 0,
        #                 'credit': price_diff > 0 and price_diff or 0,
        #                 'account_id': pricediff_acc,
        #                 'branch_id': branch.id,
        #                 'division': move.picking_id.division,
        #                 'analytic_account_id' : analytic_4
        #                 }
        #             res.append((0,0,credit_diff_vals))
        return res

class stock_picking(osv.osv):
    _inherit = "stock.picking"
   
    _columns = {    
        'create_manual': fields.boolean('Manual Created'),
   }

    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
        res = super(stock_picking, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)
        if move.purchase_line_id:
            res['analytic_1'] = move.purchase_line_id.order_id.analytic_1.id
            res['analytic_2'] = move.purchase_line_id.order_id.analytic_2.id
            res['analytic_3'] = move.purchase_line_id.order_id.analytic_3.id
            res['analytic_4'] = move.purchase_line_id.order_id.analytic_4.id
            res['origin'] = move.purchase_line_id.order_id.name
            res['payment_term'] = move.purchase_line_id.order_id.payment_term_id.id
            res['tipe'] = 'purchase'
            res['partner_type'] = move.purchase_line_id.order_id.partner_type.id
        journal = self.pool.get('account.journal').browse(cr, uid, journal_id)
        if not journal.sudo().default_credit_account_id.id:
            raise osv.except_osv(
                _('Perhatian'),
                _('Default Credit Account untuk jurnal %s belum dibuat, silahkan dibuat terlebih dahulu.') % (journal.sudo().name))
        res['account_id'] = journal.sudo().default_credit_account_id.id
        res['division'] = move.picking_id.division or move.purchase_line_id.order_id.division
        res['branch_id'] = move.picking_id.branch_id.id or move.purchase_line_id.order_id.branch_id.id or move.branch_id.id
        return res

    def change_create_manual(self,cr,uid,ids,create_manual,context=None):
        val = {}
        val['create_manual'] = True
        return {'value':val}

class stock_move(osv.osv):
    _inherit = "stock.move"

    def _get_price_unit_invoice(self, cr, uid, move_line, type, context=None):
        res = super(stock_move, self)._get_price_unit_invoice(cr, uid, move_line, type, context=context)
        if move_line.purchase_line_id.price_unit > 0:
            res = move_line.purchase_line_id.price_unit
        return res

    def _create_invoice_line_from_vals(self, cr, uid, move, invoice_line_vals, context=None):
        if move.purchase_line_id:
            invoice_line_vals['analytic_1'] = move.purchase_line_id.order_id.analytic_1.id
            invoice_line_vals['analytic_2'] = move.purchase_line_id.order_id.analytic_2.id
            invoice_line_vals['analytic_3'] = move.purchase_line_id.order_id.analytic_3.id
            invoice_line_vals['account_analytic_id'] = move.purchase_line_id.order_id.analytic_4.id
        invoice_line_id = super(stock_move, self)._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
        if move.purchase_line_id:
            vals = {}
            vals['account_analytic_id'] = move.purchase_line_id.order_id.analytic_4.id
            if move.purchase_line_id.order_id.partner_id.pkp == False:
                vals['invoice_line_tax_id'] = False
            self.pool.get('account.invoice.line').write(cr, uid, invoice_line_id, vals)
        return invoice_line_id

    # TIMING UPDATE PRODUCT COST PRICE DIGANTI SAAT CONSOLIDATE PERHITUNGAN INI HANYA UNTUK INVENTORY_ADJUSTMENT IN DAN MUTATION ORDER
    def product_price_update_before_done(self, cr, uid, ids, context=None):
        obj_product_price = self.pool.get('product.price.branch')
        product_obj = self.pool.get('product.product')
        cur_obj = self.pool.get('res.currency')
        for move in self.browse(cr, uid, ids, context=context):
            # if move.price_unit <= 0.01:
            #     warehouse_id = move.location_id.warehouse_id.id
            #     if not move.location_id.warehouse_id:
            #         warehouse_id = move.location_dest_id.warehouse_id.id
            #     average_price = obj_product_price._get_price(cr, uid, warehouse_id, move.product_id.id)
            #     move.write({'price_unit':average_price})
            if (move.location_id.usage in ('internal','nrfs','kpb') and (move.location_dest_id.usage == 'customer' or move.location_dest_id.usage == 'supplier') and move.retur_beli_line_id.retur_id.retur_type != 'Barang' and move.retur_jual_line_id.retur_id.retur_type != 'Barang' and not (move.origin_returned_move_id and not move.retur_beli_line_id and move.location_dest_id.usage == 'supplier')):
                warehouse_id = move.location_id.warehouse_id.id
                product_avail = self.pool.get('stock.quant')._get_stock_product_branch(cr, uid, warehouse_id, move.product_id.id, move.id)
                old_cost_price = obj_product_price._get_price(cr, uid, warehouse_id, move.product_id.id)
                new_cost_price = 0
                history_id = self.pool.get('product.price.history').search(cr, uid, [('model_name','=','stock.picking'),('trans_id','=',move.picking_id.id),('warehouse_id','=',warehouse_id),('product_id','=',move.product_id.id)])
                move.write({'price_unit':old_cost_price})
                if not history_id:
                    self.pool.get('product.price.history').create(cr, uid, {
                        'warehouse_id': warehouse_id,
                        'product_id': move.product_id.id,
                        'cost': old_cost_price,
                        'product_template_id': move.product_id.product_tmpl_id.id,
                        'stock_qty': product_avail,
                        'old_cost_price': old_cost_price,
                        'trans_qty': move.product_uom_qty * -1,
                        'trans_price': new_cost_price,
                        'transaction_type': 'out',
                        'origin': move.picking_id.origin or move.inventory_id.name,
                        'model_name': 'stock.picking',
                        'trans_id': move.picking_id.id,
                    }, context=None)
                else:
                    history = self.pool.get('product.price.history').browse(cr, uid, history_id)
                    history.write({'trans_qty': (move.product_uom_qty*-1) + history.trans_qty})
            elif ((move.location_id.usage == 'supplier' and move.retur_beli_line_id.retur_id.retur_type != 'Barang' and move.retur_beli_line_id) or move.location_id.usage == 'transit' or move.location_dest_id.usage == 'transit' or move.location_id.warehouse_id != move.location_dest_id.warehouse_id or (move.location_id.usage == 'customer' and move.retur_jual_line_id.retur_id.retur_type != 'Barang')) and (move.product_id.cost_method == 'average'):
                product = move.product_id
                cur = cur_obj.search(cr,uid,[('name','=','IDR')])
                cur = cur_obj.browse(cr, uid, cur[0])
                product_avail = self.pool.get('stock.quant')._get_stock_product_branch(cr, uid, move.location_dest_id.warehouse_id.id, move.product_id.id, move.id)
                model_name = 'stock.picking'
                trans_id = move.picking_id.id
                if move.inventory_id:
                    model_name = 'stock.inventory'
                    trans_id = move.inventory_id.id
                transaction_type = 'in'
                if move.location_id.usage in ('internal','nrfs','kpb') and move.location_dest_id.usage == 'transit':
                    transaction_type = 'out'
                if product_avail <= 0:
                    if (move.location_dest_id.usage in ('internal','nrfs','kpb') and move.location_id.usage == 'inventory') or (move.location_id.usage in ('internal','nrfs','kpb') and move.location_dest_id.usage in ('internal','nrfs','kpb') and move.location_id.warehouse_id.id != move.location_dest_id.warehouse_id.id) or (move.location_id.usage in ('internal','nrfs','kpb') and move.location_dest_id.usage == 'transit') or (move.location_id.usage == 'transit' and move.location_dest_id.usage in ('internal','nrfs','kpb')) or (move.location_id.usage == 'customer' and move.retur_jual_line_id.retur_id.retur_type != 'Barang') or (move.location_id.usage == 'supplier' and move.retur_beli_line_id.retur_id.retur_type != 'Barang' and move.retur_beli_line_id):
                        old_cost_price = obj_product_price._get_price(cr, uid, move.location_dest_id.warehouse_id.id, move.product_id.id)
                        new_cost_price = move.price_unit
                        old_cost_price = cur_obj.round(cr, uid, cur, old_cost_price)
                        new_cost_price = cur_obj.round(cr, uid, cur, new_cost_price)
                        context = {
                            'stock_qty': 0.0,
                            'old_cost_price': old_cost_price,
                            'trans_qty': move.product_qty if transaction_type == 'in' else move.product_qty * -1,
                            'trans_price': new_cost_price,
                            'origin': move.picking_id.origin or move.inventory_id.name,
                            'product_template_id': move.product_id.product_tmpl_id.id,
                            'transaction_type': transaction_type,
                            'model_name': model_name,
                            'trans_id': trans_id,
                        }
                        vals = {
                            'cost': new_cost_price,
                            'warehouse_id': move.location_dest_id.warehouse_id.id,
                            'product_id': move.product_id.id,
                        }
                        self.update_price_branch(cr, uid, vals, context=context)
                    
                else:
                    if (move.location_dest_id.usage in ('internal','nrfs','kpb') and move.location_id.usage == 'inventory') or (move.location_id.usage in ('internal','nrfs','kpb') and move.location_dest_id.usage in ('internal','nrfs','kpb') and move.location_id.warehouse_id.id != move.location_dest_id.warehouse_id.id) or (move.location_id.usage in ('internal','nrfs','kpb') and move.location_dest_id.usage == 'transit') or (move.location_id.usage == 'transit' and move.location_dest_id.usage in ('internal','nrfs','kpb')) or (move.location_id.usage == 'customer' and move.retur_jual_line_id.retur_id.retur_type != 'Barang') or (move.location_id.usage == 'supplier' and move.retur_beli_line_id.retur_id.retur_type != 'Barang' and move.retur_beli_line_id):
                        old_cost_price = obj_product_price._get_price(cr, uid, move.location_dest_id.warehouse_id.id, move.product_id.id)
                        transaction_price = move.price_unit
                        new_cost_price = ((old_cost_price * product_avail) + (transaction_price * move.product_qty)) / (product_avail + move.product_qty)
                        new_cost_price = cur_obj.round(cr, uid, cur, new_cost_price)
                        context = {
                            'stock_qty': product_avail,
                            'old_cost_price': old_cost_price,
                            'trans_qty': move.product_qty if transaction_type == 'in' else move.product_qty * -1,
                            'trans_price': transaction_price,
                            'origin': move.picking_id.origin or move.inventory_id.name,
                            'product_template_id': move.product_id.product_tmpl_id.id,
                            'transaction_type': transaction_type,
                            'model_name': model_name,
                            'trans_id': trans_id,
                        }
                        vals = {
                            'warehouse_id': move.location_dest_id.warehouse_id.id,
                            'product_id': move.product_id.id,
                            'cost': new_cost_price
                        }
                        self.update_price_branch(cr, uid, vals, context=context)
                
    def update_price_branch(self, cr, uid, vals, context=None):
        obj_product_price = self.pool.get('product.price.branch')
        product_price_id = obj_product_price.search(cr, uid, [('warehouse_id','=', vals.get('warehouse_id')),('product_id','=',vals.get('product_id'))])
        if product_price_id:
            obj_product_price.write(cr, uid, product_price_id, vals, context=context)
        else:
            obj_product_price.create(cr, uid, vals, context=context)
        return True
    
    # FUNGSI BAWAAN ODOO INI TIDAK DIGUNAKAN LAGI KARENA KONSEP COSTING YANG BERBEDA
    def _store_average_cost_price(self, cr, uid, move, context=None):
        pass
