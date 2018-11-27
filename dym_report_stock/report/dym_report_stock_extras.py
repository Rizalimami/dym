from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv

import logging
import locale
_logger = logging.getLogger(__name__)


class dym_stock_extras_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_stock_extras_report_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        cr = self.cr
        uid = self.uid
        context = self.context
        branch_ids = data['branch_ids']
        product_ids = data['product_ids']
        location_ids = data['location_ids']
        
        title_prefix = ''
        title_short_prefix = ''
     
        report_stock_extras = {
            'type': 'receivable',
            'title': title_prefix + _(''),
            'title_short': title_short_prefix + ', ' + _('Stock KSU')}
       


        query_start = """ select q.id as q_id, sum(q.qty) as quantity, q.in_date as date, q.consolidated_date as consolidated_date, 
            q.reservation_id as reservation_id, m.id as move_id, 
            m.origin as move_origin, sp.name as picking_name, 
            t.name as product_name, t.description as product_desc, c.name as categ_name, c.id as categ_id, 
            date_part('days', now() - MIN(q.in_date) ) as aging, 
            q.cost / sum(q.qty) as harga_satuan,
            q.cost as total_harga,
            l.name as location_name, b.code as branch_code, b.name as branch_name, b.profit_centre as branch_profit_center,
            p.default_code as p_default_code,
            p.id as p_product_id,
            w.id as p_warehouse_id,
            b.warehouse_id as p_branch_warehouse,
            l.usage as usage,
            q.location_id as location_id,
            sp.id as picking_id
            from stock_quant q
            INNER JOIN stock_location l ON q.location_id = l.id AND l.usage  in ('internal','nrfs','kpb')
            LEFT JOIN (select a.quant_id, max(a.move_id) as move_id from stock_quant_move_rel a 
            inner join stock_move b on a.move_id = b.id where b.state = 'done' group by a.quant_id) qm ON q.id = qm.quant_id
            LEFT JOIN dym_branch b ON l.branch_id = b.id
            LEFT JOIN stock_move m ON qm.move_id = m.id
            LEFT JOIN stock_picking sp ON m.picking_id = sp.id
            LEFT JOIN product_product p ON q.product_id = p.id
            LEFT JOIN product_template t ON p.product_tmpl_id = t.id
            LEFT JOIN product_category c ON t.categ_id = c.id 
            LEFT JOIN stock_warehouse w ON l.warehouse_id = w.id 
            WHERE 1=1 and q.qty > 0 """
            
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'Extras')  
        query_start +=" and t.categ_id in %s " % str(
            tuple(categ_ids)).replace(',)', ')')
    

        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        query_end=""
        if branch_ids :
            query_end +=" AND  b.id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
        if product_ids :
            query_end+=" AND  q.product_id  in %s " % str(
                tuple(product_ids)).replace(',)', ')')
        if location_ids :
            query_end+=" AND  q.location_id  in %s " % str(
                tuple(location_ids)).replace(',)', ')')
        reports = [report_stock_extras]
        
        query_group=" group by c.id, q.id, q.in_date, consolidated_date, q.reservation_id, m.id, move_origin, picking_name ,t.name, product_desc, categ_name, location_name, branch_code, branch_name,profit_centre, p.default_code, p.id, w.id, b.warehouse_id, l.usage, q.location_id, sp.id"
        query_order=" order by branch_code,t.name,location_name "
        
        for report in reports:
            
            cr.execute(query_start + query_end+query_group+query_order)
            all_lines = cr.dictfetchall()
            quants = []

            if all_lines:

                p_map = map(
                    lambda x: {
                        'location_id': x['location_id'],
                        'q_id': x['q_id'],
                        'branch_code': str(x['branch_code']),
                        'branch_name': str(x['branch_name']),
                        'parent_category': 'Extras',
                        'product_desc': str(x['product_desc']),
                        'categ_name': str(x['categ_name']),
                        'product_name': str(x['product_name']),
                        'move_origin': str(x['move_origin']),
                        'picking_name': str(x['picking_name']),
                        'location_name': str(x['location_name']),
                        'aging': str(x['aging']),
                        'quantity':x['quantity'],
                        # 'harga_satuan': x['harga_satuan'],
                        # 'total_harga': x['total_harga'],
                        'default_code': x['p_default_code'],
                        'status': 'Ready for Sale' if x['usage'] == 'internal' and not x['reservation_id'] else 'Not Ready for Sale' if x['usage'] in ['nrfs','kpb'] and not x['reservation_id'] else 'Undelivered' if x['reservation_id'] and x['usage'] in ['internal','nrfs','kpb'] else 'Transferred' if not x['reservation_id'] and x['usage'] == 'customer' else 'n/a'
                        },
                    all_lines)

                current_cost = {}
                for p in p_map:
                     if p['q_id'] not in map(
                            lambda x: x.get('q_id', None), quants):
                        quants.append(p)
                        quant_lines = filter(
                            lambda x: x['q_id'] == p['q_id'], all_lines)                        
                        p.update({'lines': quant_lines})
                        unit_grn = ''
                        picking_id = quant_lines[0]['picking_id']
                        if picking_id:
                            picking = self.pool.get('stock.picking').browse(cr, uid, picking_id)
                            if picking.division == 'Unit':
                                packing_id = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id','=',picking.id),('state','=','posted')])
                                if packing_id:
                                    packing = self.pool.get('dym.stock.packing').browse(cr, uid, packing_id)
                                    unit_grn = ', '.join(packing.mapped('name'))
                            else:
                                while (picking.backorder_id and picking.division != 'Unit'):
                                    picking = picking.backorder_id
                                    if picking.division == 'Unit':
                                        packing_id = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id','=',picking.id),('state','=','posted')])
                                        if packing_id:
                                            packing = self.pool.get('dym.stock.packing').browse(cr, uid, packing_id)
                                            unit_grn = ', '.join(packing.mapped('name'))
                            if not unit_grn:
                                extras_ids = self.pool.get('dym.barang.extras').search(cr, uid, [('product_id','=',quant_lines[0]['p_product_id'])])
                                product_units = self.pool.get('dym.barang.extras').browse(cr, uid, extras_ids).mapped('barang_extras_id').ids
                                src_picking = self.pool.get('stock.move').search(cr, uid, ['|',('picking_id.origin','ilike',picking.origin),('origin','ilike',picking.origin),'|',('picking_id.picking_type_id','=',picking.picking_type_id.id),('picking_type_id','=',picking.picking_type_id.id),('picking_id.division','=','Unit'),('product_id','in',product_units)])
                                picking = self.pool.get('stock.move').browse(cr, uid, src_picking).mapped('picking_id')
                                packing_id = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id','in',picking.ids),('state','=','posted')])
                                if packing_id:
                                    packing = self.pool.get('dym.stock.packing').browse(cr, uid, packing_id)
                                    unit_grn = ', '.join(packing.mapped('name'))
                        cost = 0
                        warehouse_id = quant_lines[0]['p_branch_warehouse'] or quant_lines[0]['p_warehouse_id']
                        if warehouse_id:
                            price_id = self.pool.get('product.price.branch').search(cr, uid, [('warehouse_id','=', warehouse_id), ('product_id','=', quant_lines[0]['p_product_id'])])
                            if price_id:
                                cost = self.pool.get('product.price.branch').browse(cr, uid, price_id[0]).cost
                        category = self.pool.get('product.category').browse(cr, uid, [quant_lines[0]['categ_id']])
                        parent_category = 'Extras'
                        if category.isParentName('ACCESSORIES'):
                            parent_category = 'Aksesoris'
                        # total_harga = locale.format("%d", cost*quant_lines[0]['quantity'], grouping=True)
                        # harga_satuan = locale.format("%d", cost, grouping=True)

                        # cari parent location
                        location_id = quant_lines[0]['location_id']
                        location_obj = self.pool.get('stock.location').browse(cr, uid, location_id)
                        location_parent = location_obj.name
                        while (location_obj.location_id.location_id):
                            location_obj = location_obj.location_id
                            location_parent = location_obj.name
                        p.update({
                            'parent_category': parent_category,
                            'harga_satuan': cost,
                            'total_harga': cost*quant_lines[0]['quantity'],
                            'location_parent': location_parent,
                            'unit_grn': unit_grn,
                            })
                        # quant = self.pool.get('stock.quant').browse(cr, uid, quant_lines[0]['q_id'])
                        # if quant.product_id.categ_id:
                        #     category = quant.product_id.categ_id
                        #     while (category.parent_id and category.parent_id.bisnis_unit == False):
                        #         category = category.parent_id
                        #     p.update({'categ_name': category.name})
                report.update({'quants': quants})

        reports = filter(lambda x: x.get('quants'), reports)
       
        if not reports:
            reports = [{
            'type': 'receivable',
            'title': title_prefix + _(''),
            'title_short': title_short_prefix + ', ' + _('Stock KSU') ,
                        'quants':
                            [ {
                        'branch_code':'NO DATA FOUND',
                        'branch_name': 'NO DATA FOUND',
                        'parent_category': 'NO DATA FOUND',
                        'product_desc': 'NO DATA FOUND',
                        'categ_name': 'NO DATA FOUND',
                        'product_name': 'NO DATA FOUND',
                        'move_origin':'NO DATA FOUND',
                        'picking_name': 'NO DATA FOUND',
                        'location_name': 'NO DATA FOUND',
                        'status' : 'NO DATA FOUND',
                        'aging': 'NO DATA FOUND',
                        'quantity':0,
                        'harga_satuan': 0,
                        'total_harga': 0,
                        'default_code': 'NO DATA FOUND',
                        'location_parent': 'NO DATA FOUND',
                        'unit_grn': 'NO DATA FOUND',
                        }], 
                        
            }]        
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        objects = False
        super(dym_stock_extras_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_stock_extras_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_tock.report_stock_extras'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_tock.report_stock_extras'
    _wrapped_report_class = dym_stock_extras_report_print
