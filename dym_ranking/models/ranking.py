from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import math

class dym_ranking_master(models.Model):
    _name = "dym.ranking.master"
    _order = "percentage asc"

    name = fields.Char('Rank Name', required=True)
    operator = fields.Selection([('<','<'),('<=','<=')],'Operator', required=True)
    percentage = fields.Float('%', required=True)
    order_min = fields.Float('Min. Stock (%)', required=True)
    order_max = fields.Float('Max. Stock (%)', required=True)
    order_qty = fields.Float('Buffer Stock (%)')

    @api.constrains('percentage')
    def _percentage_constraint(self):
        search_uniq = self.env['dym.ranking.master'].search([('percentage','=',self.percentage),('id','!=',self.id)])
        if search_uniq:
            raise ValidationError("Persentase sudah terdaftar!")
    
    @api.constrains('name')
    def _name_constraint(self):
        name_uniq = self.env['dym.ranking.master'].search([('name','=',self.name),('id','!=',self.id)])
        if name_uniq:
            raise ValidationError("Nama ranking sudah terdaftar!")

    @api.constrains('order_min','order_max','order_qty')
    def _order_min_max_constraint(self):
        name_uniq = self.env['dym.ranking.master'].search([('name','=',self.name),('id','!=',self.id)])
        if self.order_min > self.order_max:
            raise ValidationError("Minimal stock harus lebih kecil dari maksimal stock!")
        if self.order_qty and (self.order_qty < self.order_min) or (self.order_qty > self.order_max):
            raise ValidationError("Buffer stock harus diantara minimal stock dan maksimal stock!")

class dym_ranking(models.Model):
    _name = "dym.ranking"
    _description = "Pinjaman 2 Arah"
    
    @api.model
    def _get_default_date(self):
        return self.env['dym.branch'].get_default_date_model()
        
    # date = fields.Date('Date', required=True)
    name = fields.Char('Analisa')
    month = fields.Selection([(1,'Januari'),(2,'Februari'),(3,'Maret'),(4,'April'),(5,'Mei'),(6,'Juni'),(7,'Juli'),(8,'Agustus'),(9,'September'),(10,'Oktober'),(11,'November'),(12,'Desember')], 'Start Month', required=True)
    year = fields.Selection([(num, str(num)) for num in range(2015, (datetime.now().year)+1 )], 'Start Year', required=True)
    branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division', required=True)
    part_aksesoris = fields.Selection([('Sparepart','Part'),('ACCESSORIES','Aksesoris')], 'Part / Aksesoris')
    periode = fields.Selection([('3','3 Bulan'),('6','6 Bulan')], 'Periode', required=True)
    m6_koefisien = fields.Float('m-6 Koefisien (%)')
    m5_koefisien = fields.Float('m-5 Koefisien (%)')
    m4_koefisien = fields.Float('m-4 Koefisien (%)')
    m3_koefisien = fields.Float('m-3 Koefisien (%)')
    m2_koefisien = fields.Float('m-2 Koefisien (%)')
    m1_koefisien = fields.Float('m-1 Koefisien (%)')
    total_koefisien = fields.Float('Total Koefisien')
    rank_line = fields.One2many('dym.ranking.line', 'rank_id', 'Detail Ranking')
    product_ids = fields.Many2many('product.product', 'dym_ranking_product_rel', 'dym_ranking_id', 'product_id', 'Products', domain=[('sale_ok','=',True)])
    purchase_id = fields.Many2one('purchase.order', 'Purchase', copy=False)
        
    _defaults={
               # 'date' : _get_default_date,
               }

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'ARA', division=vals['division'])
        return super(dym_ranking, self).create(cr, uid, vals, context=context)

    @api.onchange('branch_id','division','month','year','periode','m6_koefisien','m5_koefisien','m4_koefisien','m3_koefisien','m2_koefisien','m1_koefisien','product_ids')
    def branch_change(self):
        # self.rank_line = False
        if self.periode == '3':
            self.m4_koefisien = 0
            self.m5_koefisien = 0
            self.m6_koefisien = 0

    def _get_categ_ids(self, cr, uid, categ_name, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, categ_name)
        if categ_name == 'Sparepart':
            categ_sparepart = []
            aksesoris_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, 'ACCESSORIES')
            for cat in categ_ids:
                if cat not in aksesoris_ids:
                    categ_sparepart.append(cat)
            categ_ids = categ_sparepart
        return categ_ids

    @api.onchange('division','part_aksesoris')
    def onchange_division(self):
        value = {}
        domain = {}
        warning = {}
        value['product_ids'] = False
        if self.division:
            if self.division == 'Sparepart':
                if self.part_aksesoris:
                    categ_ids = self._get_categ_ids(self.part_aksesoris)
                else:
                    domain['product_ids'] = [('id','=',0)]
                    return  {'value':value, 'domain':domain, 'warning':warning}
            else:
                categ_ids = self._get_categ_ids(self.division)
            domain['product_ids'] = [('categ_id','in',categ_ids),('sale_ok','=',True)]
        else:
            domain['product_ids'] = [('id','=',0)]
        return  {'value':value, 'domain':domain, 'warning':warning}

    @api.multi
    def get_qty_order(self, first_date, last_date, product_id, branch_id):
        domain_lost_order = [('date', '>=', datetime.strftime(first_date, '%Y-%m-%d')),
                            ('date', '<=', datetime.strftime(last_date, '%Y-%m-%d')),
                            ('product_id', '=', product_id.id),
                            ('branch_id', '=', branch_id)]
        lost_order_brw = self.env['dym.lost.order'].search(domain_lost_order)
        lost_order_qty = 0
        for lost_order in lost_order_brw:
            lost_order_qty += lost_order.lost_order_qty

        domain_hotline_order = [('order_id.date_order', '>=', datetime.strftime(first_date, '%Y-%m-%d')),
                                ('order_id.date_order', '<=', datetime.strftime(last_date, '%Y-%m-%d')),
                                ('product_id', '=', product_id.id),
                                ('order_id.branch_id', '=', branch_id),
                                ('order_id.state', 'in', ('approved','done')),
                                ('order_id.purchase_order_type_id.name', '=', 'Hotline')]
                    
        po_line_brw = self.env['purchase.order.line'].search(domain_hotline_order)
        po_line_qty = 0
        for po_line in po_line_brw:
            po_line_qty += po_line.product_qty

        sales_qty = 0
        if product_id.categ_id.isParentName('Unit'):
            domain_sales_unit = [('dealer_sale_order_line_id.date_order', '>=', datetime.strftime(first_date, '%Y-%m-%d')),
                                ('dealer_sale_order_line_id.date_order', '<=', datetime.strftime(last_date, '%Y-%m-%d')),
                                ('product_id', '=', product_id.id),
                                ('dealer_sale_order_line_id.branch_id', '=', branch_id),
                                ('dealer_sale_order_line_id.state', 'in', ('approved','progress','done'))]
            dso_line_brw = self.env['dealer.sale.order.line'].search(domain_sales_unit)
            for dso_line in dso_line_brw:
                sales_qty += dso_line.product_qty

        if product_id.categ_id.isParentName('Sparepart'):
            domain_sales_wo = [('work_order_id.date', '>=', datetime.strftime(first_date, '%Y-%m-%d')),
                                ('work_order_id.date', '<=', datetime.strftime(last_date, '%Y-%m-%d')),
                                ('product_id', '=', product_id.id),
                                ('work_order_id.branch_id', '=', branch_id),
                                ('work_order_id.state', 'in', ('approved','finished','open','done'))]
            wo_line_brw = self.env['dym.work.order.line'].search(domain_sales_wo)
            for wo_line in wo_line_brw:
                sales_qty += wo_line.product_qty

            domain_sales_so = [('order_id.date_order', '>=', datetime.strftime(first_date, '%Y-%m-%d')),
                                ('order_id.date_order', '<=', datetime.strftime(last_date, '%Y-%m-%d')),
                                ('product_id', '=', product_id.id),
                                ('order_id.branch_id', '=', branch_id),
                                ('order_id.state', 'in', ('progress','done')),
                                ('order_id.division','=','Sparepart')]
            so_line_brw = self.env['sale.order.line'].search(domain_sales_so)
            for so_line in so_line_brw:
                sales_qty += so_line.product_uom_qty
        return lost_order_qty + po_line_qty + sales_qty

    @api.multi
    def generate_line(self):
        if self.periode == '3':
            if self.m1_koefisien + self.m2_koefisien + self.m3_koefisien != 100:
                raise osv.except_osv(('Invalid action !'), ('Jumlah persentase koefisien pre 1-3 month bukan 100%!'))
        if self.periode == '6':
            if self.m1_koefisien + self.m2_koefisien + self.m3_koefisien + self.m4_koefisien + self.m5_koefisien + self.m6_koefisien != 100:
                raise osv.except_osv(('Invalid action !'), ('Jumlah persentase koefisien pre 1-6 month bukan 100%!'))
        self.rank_line.unlink()
        rank_line_obj = self.env['dym.ranking.line']
        res = []
        # product_ids = self.product_ids
        # if not self.product_ids:
        if self.division == 'Sparepart':
            categ_ids = self._get_categ_ids(self.part_aksesoris)
        else:
            categ_ids = self._get_categ_ids(self.division)
        product_ids = self.env['product.product'].search([('categ_id','in',categ_ids),('sale_ok','=',True)])
        periode = 3
        if self.periode == '6':
            periode = 6
        interval_days = []
        first_day = date(self.year, self.month, 1)
        query_from = ""
        query_select = ""
        query_total_demand = ""
        query_total_madk = ""
        query_move = ""
        for month in range(periode):
            month = month + 1
            last_day =  first_day - timedelta(days=1)
            first_day =  last_day.replace(day=1)
            query_from += ("LEFT JOIN (SELECT lodx.product_id, SUM(lodx.lost_order_qty) as product_qty FROM dym_lost_order lodx WHERE lodx.branch_id = %s and lodx.date >= '%s' and lodx.date <= '%s' GROUP BY lodx.product_id) lod%s on p.id = lod%s.product_id ") % (str(self.branch_id.id), str(first_day), str(last_day), str(month), str(month))
            query_from += ("LEFT JOIN (SELECT polx.product_id, SUM(polx.product_qty) as product_qty FROM purchase_order_line polx, purchase_order pox, dym_purchase_order_type potx WHERE polx.order_id = pox.id and pox.branch_id = %s and pox.state in ('approved','done') and pox.date_order >= '%s' and pox.date_order <= '%s' and potx.name = 'Hotline' and potx.id = pox.purchase_order_type_id GROUP BY polx.product_id) po%s on p.id = po%s.product_id ") % (str(self.branch_id.id), str(first_day), str(last_day), str(month), str(month))
            if month == 1:
                koefisien = self.m1_koefisien
            if month == 2:
                koefisien = self.m2_koefisien
            if month == 3:
                koefisien = self.m3_koefisien
            if month == 4:
                koefisien = self.m4_koefisien
            if month == 5:
                koefisien = self.m5_koefisien
            if month == 6:
                koefisien = self.m6_koefisien
            if self.division == 'Unit':
                query_select += ("COALESCE(lod%s.product_qty,0) + COALESCE(po%s.product_qty,0) + COALESCE(dso%s.product_qty,0) + COALESCE(so%s.product_qty,0) as m%s, ") % (str(month), str(month), str(month), str(month), str(month))
                query_total_demand += ("COALESCE(lod%s.product_qty,0) + COALESCE(po%s.product_qty,0) + COALESCE(dso%s.product_qty,0) + COALESCE(so%s.product_qty,0) + ") % (str(month), str(month), str(month), str(month))
                query_total_madk += ("(%s * (COALESCE(lod%s.product_qty,0) + COALESCE(po%s.product_qty,0) + COALESCE(dso%s.product_qty,0) + COALESCE(so%s.product_qty,0)) / 100) + ") % (koefisien,str(month),str(month),str(month),str(month))
                query_from += ("LEFT JOIN (SELECT dsolx.product_id, SUM(dsolx.product_qty) as product_qty FROM dealer_sale_order_line dsolx, dealer_sale_order dsox WHERE dsolx.dealer_sale_order_line_id = dsox.id and dsox.branch_id = %s and dsox.state in ('approved','progress','done') and dsox.date_order >= '%s' and dsox.date_order <= '%s' GROUP BY dsolx.product_id) dso%s on p.id = dso%s.product_id ") % (str(self.branch_id.id), str(first_day), str(last_day), str(month), str(month))
                query_from += ("LEFT JOIN (SELECT solx.product_id, SUM(solx.product_uom_qty) as product_qty FROM sale_order_line solx, sale_order sox WHERE solx.order_id = sox.id and sox.branch_id = %s and sox.state in ('progress','done') and sox.date_order >= '%s' and sox.date_order <= '%s' and sox.division = 'Unit' GROUP BY solx.product_id) so%s on p.id = so%s.product_id ") % (str(self.branch_id.id), str(first_day), str(last_day), str(month), str(month))
            else:
                query_select += ("COALESCE(lod%s.product_qty,0) + COALESCE(po%s.product_qty,0) + COALESCE(wo%s.product_qty,0) + COALESCE(sos%s.product_qty,0) as m%s, ") % (str(month), str(month), str(month), str(month), str(month))
                query_total_demand += ("COALESCE(lod%s.product_qty,0) + COALESCE(po%s.product_qty,0) + COALESCE(wo%s.product_qty,0) + COALESCE(sos%s.product_qty,0) + ") % (str(month), str(month), str(month), str(month))
                query_total_madk += ("(%s * (COALESCE(lod%s.product_qty,0) + COALESCE(po%s.product_qty,0) + COALESCE(wo%s.product_qty,0) + COALESCE(sos%s.product_qty,0)) / 100) + ") % (koefisien,str(month),str(month),str(month),str(month))
                query_from += ("LEFT JOIN (SELECT solsx.product_id, SUM(solsx.product_uom_qty) as product_qty FROM sale_order_line solsx, sale_order sosx WHERE solsx.order_id = sosx.id and sosx.branch_id = %s and sosx.state in ('progress','done') and sosx.date_order >= '%s' and sosx.date_order <= '%s' and sosx.division = 'Sparepart' GROUP BY solsx.product_id) sos%s on p.id = sos%s.product_id ") % (str(self.branch_id.id), str(first_day), str(last_day), str(month), str(month))
                query_from += ("LEFT JOIN (SELECT wolx.product_id, SUM(wolx.product_qty) as product_qty FROM dym_work_order_line wolx, dym_work_order wox WHERE wolx.work_order_id = wox.id and wox.branch_id = %s and wox.state in ('approved','finished','open','done') and wox.date >= '%s' and wox.date <= '%s' GROUP BY wolx.product_id) wo%s on p.id = wo%s.product_id ") % (str(self.branch_id.id), str(first_day), str(last_day), str(month), str(month))
        # query_move = ("(SELECT CASE WHEN sldx.usage in ('internal','nrfs','kpb') and (sldx.branch_id = smx.branch_id or sldx.branch_id = spx.branch_id or sldx.branch_id = six.branch_id) THEN COALESCE(smx.total_stock_destination,0) WHEN slsx.usage in ('internal','nrfs','kpb') and (slsx.branch_id = smx.branch_id or slsx.branch_id = spx.branch_id or slsx.branch_id = six.branch_id) THEN COALESCE(smx.total_stock_source,0) ELSE 0 END as saldo_stock_awal FROM stock_move smx LEFT JOIN stock_location slsx on slsx.id = smx.location_id LEFT JOIN stock_location sldx on sldx.id = smx.location_dest_id LEFT JOIN stock_picking spx on spx.id = smx.picking_id LEFT JOIN stock_inventory six on six.id = smx.inventory_id WHERE (smx.branch_id = %s or spx.branch_id = %s or six.branch_id = %s) and smx.state = 'done' and smx.date < '%s' and (slsx.usage = 'internal' or sldx.usage = 'internal') and smx.product_id = p.id order by smx.date desc limit 1) ") % (str(self.branch_id.id), str(self.branch_id.id), str(self.branch_id.id), str(datetime.strftime(date(self.year, self.month, 1), '%Y-%m-%d')))
        query_move = ("(SELECT sum(sqx.qty) as saldo_stock_awal FROM stock_quant sqx LEFT JOIN stock_location slsx on slsx.id = sqx.location_id LEFT JOIN stock_production_lot splx on splx.id = sqx.lot_id WHERE slsx.branch_id = %s and slsx.usage in ('internal','nrfs','kpb') and sqx.reservation_id is null and sqx.consolidated_date is not null and (splx.state = 'stock' or sqx.consolidated_date is not null) and sqx.product_id = p.id) ") % (str(self.branch_id.id))
        # query_move = "COALESCE(sm.saldo_stock_awal,0) as saldo_stock_awal, sm.move_id as move_id"
        query_total_demand = query_total_demand[:-2]
        query_total_madk = query_total_madk[:-2]
        # query_move = query_move[:-2]
        query_start = ("SELECT %s p.id as product_id, (%s)/%s as mad, COALESCE(%s,0) as mad_koefisien, %s as saldo_stock_awal FROM product_product p %s where p.id in %s order by mad_koefisien desc") % (query_select, query_total_demand, periode, query_total_madk, query_move, query_from, str(tuple(product_ids.ids)).replace(',)', ')'))

        self._cr.execute(query_start)
        all_lines = self._cr.dictfetchall()

        total_koefisien = sum(line['mad_koefisien'] for line in all_lines)
        self.write({'total_koefisien':total_koefisien})
        kumulatif = 0
        master_rank_brw = self.env['dym.ranking.master'].search([], order='percentage asc')
        new_res = sorted(all_lines, key=lambda k: k['mad_koefisien'], reverse=True)
        cur_month_day = datetime.today()
        cur_month_last_day = date(cur_month_day.year, cur_month_day.month, 1) + relativedelta(months=1) - timedelta(days=1)
        cur_month_factor = float(cur_month_last_day.day - cur_month_day.day) / float(cur_month_last_day.day)
        for line in new_res:
            line['mad_kumulatif'] = line['mad_koefisien'] + kumulatif
            mad_percentage = 0
            if total_koefisien > 0:
                mad_percentage = (line['mad_kumulatif'] / total_koefisien) * 100
            line['mad_percentage'] = mad_percentage
            rank = False
            rank_filtered = master_rank_brw.filtered(lambda r: r.percentage == mad_percentage and r.operator == '<=')
            if not rank_filtered:
                rank_filtered = master_rank_brw.filtered(lambda r: r.percentage > mad_percentage)
            if not rank_filtered:
                raise osv.except_osv(('Invalid action !'), ('Persentase %s tidak ditemukan di master ranking!')%(mad_percentage))
            rank = rank_filtered[0]
            line['master_rank_id'] = rank.id
            order_min = line['mad_koefisien'] * rank.order_min / 100
            line['order_min'] = order_min
            order_qty = line['mad_koefisien'] * (rank.order_qty or rank.order_min) / 100
            line['order_qty'] = order_qty
            order_max = line['mad_koefisien'] * rank.order_max / 100
            line['order_max'] = order_max
            line['saldo_stock_awal'] = math.ceil(line['saldo_stock_awal'] or 0)
            line['cur_month_factor'] = cur_month_factor
            sugor = math.ceil(order_qty + (line['mad_koefisien']*cur_month_factor) - line['saldo_stock_awal'])
            line['suggestion_order'] = sugor if sugor > 0 else 0
            line['adjust_qty'] = 0
            line['suggestion_order_final'] = sugor if sugor > 0 else 0
            line['saldo_stock_akhir'] = line['suggestion_order_final'] + line['saldo_stock_awal'] - (line['mad_koefisien']*cur_month_factor)
            if line['mad_koefisien'] > 0:
                line['stock_level_akhir'] = line['saldo_stock_akhir'] / line['mad_koefisien']
            else:
                line['stock_level_akhir'] = 0
            line['rank_id'] = self.id
            kumulatif += line['mad_koefisien']
            if not self.product_ids or line['product_id'] in self.product_ids.ids:
                rank_line_obj.create(line)
        return True

    @api.multi
    def create_po(self):
        if not self.rank_line:
            raise osv.except_osv(('Invalid action !'), ('Mohon generate ranking terlebih dahulu!'))

        purchase_obj = self.env['purchase.order']
        if self.division == 'Unit' :
            if not self.branch_id.pricelist_unit_purchase_id :
                raise osv.except_osv(_('Perhatian !'), _('Silahkan setting Pricelist Beli Unit di Branch terlebih dahulu !'))
            else :
                pricelist = self.branch_id.pricelist_unit_purchase_id.id
        else :
            if not self.branch_id.pricelist_part_purchase_id :
                raise osv.except_osv(_('Perhatian !'), _('Silahkan setting Pricelist Beli Sparepart di Branch terlebih dahulu !'))
            else :
                pricelist = self.branch_id.pricelist_part_purchase_id.id
        picking_type_in = purchase_obj._get_picking_in()
        onchange_picking_type_vals = purchase_obj.onchange_picking_type_id(self.branch_id.id, False)
        supplier = False
        if 'partner_id' in onchange_picking_type_vals['value']:
            supplier = self.env['res.partner'].browse(onchange_picking_type_vals['value']['partner_id'])
        if 'picking_type_id' in onchange_picking_type_vals['value']:
            picking_type_in = onchange_picking_type_vals['value']['picking_type_id']
        location_id = self.env['stock.picking.type'].browse([picking_type_in]).default_location_dest_id.id
        if not location_id:
            location_id = False
        payment_term = False
        purchase = {
                    'origin': self.name,
                    'date_order': datetime.today(),
                    'partner_id': supplier.id,
                    'pricelist_id': pricelist,
                    'location_id': location_id,
                    'company_id': self.branch_id.company_id.id,
                    'picking_type_id': picking_type_in,
                    'branch_id': self.branch_id.id,
                    'division' : self.division,
                    'payment_term_id' : payment_term,
                    'sugor_ids': [(6, 0, [self.id])],
                    }
        if supplier:
            if supplier.property_supplier_payment_term:
                purchase.update({'payment_term_id': supplier.property_supplier_payment_term.id})
            purchase.update({'fiscal_position': supplier.property_account_position and supplier.property_account_position.id or False})
        purchase_id = purchase_obj.create(purchase)
        # purchase_obj.message_post([purchase_id.id], body=_("RFQ created"))
        self.write({'purchase_id': purchase_id.id})
        purchase_line = []
        vals = {}
        categ = self.env['product.category'].search([('name','=',self.division),('parent_id','=',False)], order='id asc')[0]
        for line in self.rank_line.filtered(lambda r: r.check_order == True and r.suggestion_order_final > 0):
            if line.check_order == False:
                continue
            po_line_obj = self.env['purchase.order.line']
            product_uom = self.env['product.uom']
            product = line.product_id
            default_uom_po_id = product.uom_po_id.id
            date_order = datetime.strftime(datetime.today(), "%Y-%m-%d %H:%M:%S")
            qty = product_uom._compute_qty(line.product_id.uom_id.id, line.suggestion_order_final, default_uom_po_id)
            if self.division == 'Unit' :
                if not self.branch_id.pricelist_unit_purchase_id :
                    raise osv.except_osv(_('Perhatian !'), _('Silahkan setting Pricelist Beli Unit di Branch terlebih dahulu !'))
                else :
                    pricelist = self.branch_id.pricelist_unit_purchase_id.id
            elif self.division == 'Sparepart' : 
                if not self.branch_id.pricelist_part_purchase_id :
                    raise osv.except_osv(_('Perhatian !'), _('Silahkan setting Pricelist Beli Sparepart di Branch terlebih dahulu !'))
                else :
                    pricelist = self.branch_id.pricelist_part_purchase_id.id
            else :
                # if supplier and not supplier.property_product_pricelist_purchase :
                #     raise osv.except_osv(_('Perhatian !'), _('Silahkan setting Purchase Pricelist Beli dalam supplier %s !')%(supplier.name))
                # elif supplier :
                pricelist = supplier.property_product_pricelist_purchase.id
            if supplier:    
                vals = po_line_obj.onchange_product_id(pricelist, product.id, qty, default_uom_po_id,
                    supplier.id, date_order=date_order,
                    fiscal_position_id=supplier.property_account_position,
                    date_planned=date_order,
                    name=False, price_unit=False, state='draft')['value']
            else:
                vals = po_line_obj.onchange_product_id(pricelist, product.id, qty, default_uom_po_id,
                    False, date_order=date_order,
                    fiscal_position_id=supplier.property_account_position,
                    date_planned=date_order,
                    name=False, price_unit=False, state='draft')['value']

            vals.update({
                'order_id': purchase_id.id,
                'template_id': product.product_tmpl_id.id,
                'product_id': product.id,
                'division_dummy': 'Umum' if self.division == 'Umum' else '',
                'categ_id': categ.id,
                # 'account_analytic_id': requisition_line.account_analytic_id.id,
                'taxes_id': [(6, 0, vals['taxes_id'])],
                'state': 'draft'
            })
            purchase_line_id = po_line_obj.create(vals)
        if not vals:
            raise osv.except_osv(('Invalid action !'), ('Mohon check product yang mau di order!'))
        return True

    @api.cr_uid_ids_context
    def view_po(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        val = self.browse(cr, uid, ids)
        if val.division == 'Unit':
            result = mod_obj.get_object_reference(cr, uid, 'dym_purchase_order', 'purchase_form_action_showroom')
            id = result and result[1] or False
            result = act_obj.read(cr, uid, [id], context=context)[0]
            res = mod_obj.get_object_reference(cr, uid, 'purchase', 'purchase_order_form')
        elif val.division == 'Sparepart':
            result = mod_obj.get_object_reference(cr, uid, 'dym_purchase_order', 'purchase_form_action_workshop')
            id = result and result[1] or False
            result = act_obj.read(cr, uid, [id], context=context)[0]
            res = mod_obj.get_object_reference(cr, uid, 'purchase', 'purchase_order_form')
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = val.purchase_id.id
        return result

class dym_ranking_line(models.Model):
    _name = "dym.ranking.line"

    @api.one
    @api.depends('order_qty','mad_koefisien','saldo_stock_awal','adjust_qty','cur_month_factor')
    def _compute_suggestion(self):
        sugor = math.ceil(self.order_qty + (self.mad_koefisien*self.cur_month_factor) - self.saldo_stock_awal)
        self.suggestion_order = sugor if sugor > 0 else 0
        self.suggestion_order_final = self.suggestion_order + self.adjust_qty
        self.saldo_stock_akhir = self.suggestion_order_final + self.saldo_stock_awal - (self.mad_koefisien*self.cur_month_factor)
        if self.mad_koefisien > 0:
            self.stock_level_akhir = self.saldo_stock_akhir / self.mad_koefisien
        else:
            self.stock_level_akhir = 0
        # self.suggestion_order = sugor
    #     mad_percentage = 0
    #     if self.rank_id.total_koefisien > 0:
    #         mad_percentage = (self.mad_kumulatif / self.rank_id.total_koefisien) * 100
    #     self.mad_percentage = mad_percentage
    #     master_rank_brw = self.env['dym.ranking.master'].search([('percentage','>=',mad_percentage)], order='percentage asc')
    #     rank = False
    #     for ranking in master_rank_brw:
    #         if ranking.percentage > mad_percentage:
    #             rank = ranking
    #             break
    #         elif ranking.percentage == mad_percentage and ranking.operator == '<=':
    #             rank = ranking
    #             break
    #     if not rank:
    #         raise osv.except_osv(('Invalid action !'), ('Persentase %s tidak ditemukan di master ranking!')%(mad_percentage))
    #     self.master_rank_id = rank.id
    #     order_min = self.mad_koefisien * rank.order_min / 100
    #     self.order_min = order_min
    #     order_max = self.mad_koefisien * rank.order_max / 100
    #     self.order_max = order_max
    #     self.order_qty = order_min
    #     first_day = date(self.rank_id.year, self.rank_id.month, 1)
    #     domain = [('product_id', '=', self.product_id.id),
    #                 ('branch_id', '=', self.rank_id.branch_id.id),
    #                 ('date', '<', datetime.strftime(first_day, '%Y-%m-%d')),
    #                 ('state','=','done'),'|',
    #                 ('location_id.usage','=','internal'),
    #                 ('location_dest_id.usage','=','internal')]
    #     moves_brw = self.env['stock.move'].search(domain, order='date desc, id desc', limit=1)
    #     saldo_stock_awal = 0
    #     if moves_brw:
    #         if moves_brw.location_dest_id.usage in ['internal','nrfs','kpb'] and moves_brw.location_dest_id.branch_id.id == moves_brw.branch_id.id:
    #             saldo_stock_awal = moves_brw.total_stock_destination
    #         elif moves_brw.location_id.usage in ['internal','nrfs','kpb'] and moves_brw.location_id.branch_id.id == moves_brw.branch_id.id:
    #             saldo_stock_awal = moves_brw.total_stock_source
    #     self.saldo_stock_awal = saldo_stock_awal
    #     self.suggestion_order = round(order_min + self.mad_koefisien - saldo_stock_awal, 0)

    rank_id = fields.Many2one('dym.ranking', 'Ranking')
    product_id = fields.Many2one('product.product', 'Product')
    m6 = fields.Integer('m-6')
    m5 = fields.Integer('m-5')
    m4 = fields.Integer('m-4')
    m3 = fields.Integer('m-3')
    m2 = fields.Integer('m-2')
    m1 = fields.Integer('m-1')
    mad = fields.Float('MAD')
    mad_koefisien = fields.Float('MAD Koef')
    mad_kumulatif = fields.Float('MAD Cum')
    mad_percentage = fields.Float('% MAD Cum')
    master_rank_id = fields.Many2one('dym.ranking.master', 'Rank')
    order_min = fields.Float('Min. Stock')
    order_max = fields.Float('Max. Stock')
    order_qty = fields.Float('Buffer Stock')
    saldo_stock_awal = fields.Integer('Current Stock')
    cur_month_factor = fields.Float('Current Month Factor')
    suggestion_order = fields.Integer('Suggest Order', compute='_compute_suggestion', store=True)
    adjust_qty = fields.Integer('Adjust Order')
    suggestion_order_final = fields.Integer('Fix Order', compute='_compute_suggestion', store=True)
    saldo_stock_akhir = fields.Float('End Stock', compute='_compute_suggestion', store=True)
    stock_level_akhir = fields.Float('End Stock Level', compute='_compute_suggestion', store=True)
    check_order = fields.Boolean('Order?')

    @api.onchange('order_qty','adjust_qty')
    def order_qty_change(self):        
        if self.order_qty < self.order_min:
            self.order_qty = self.order_min
        elif self.order_qty > self.order_max:
            self.order_qty = self.order_max
        suggestion_order = math.ceil(self.order_qty + (self.mad_koefisien*self.cur_month_factor) - self.saldo_stock_awal)
        if suggestion_order > 0:
            self.suggestion_order = suggestion_order
        else:
            self.suggestion_order = 0
        if self.adjust_qty > self.suggestion_order:
            self.adjust_qty = self.suggestion_order
        self.suggestion_order_final = self.suggestion_order + self.adjust_qty
        if self.suggestion_order_final <= 0:
            self.check_order = False
        self.saldo_stock_akhir = self.suggestion_order_final + self.saldo_stock_awal - (self.mad_koefisien*self.cur_month_factor)
        if self.mad_koefisien > 0:
            self.stock_level_akhir = self.saldo_stock_akhir / self.mad_koefisien
        else:
            self.stock_level_akhir = 0