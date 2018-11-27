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


class dym_stock_sparepart_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_stock_sparepart_report_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        # locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        cr = self.cr
        uid = self.uid
        context = self.context
        branch_ids = data['branch_ids']
        product_ids = data['product_ids']
        location_ids = data['location_ids']
        show_valuation = data['show_valuation']
        
        title_prefix = ''
        title_short_prefix = ''
     
        report_stock_sparepart = {
            'show_valuation': show_valuation,
            'type': 'receivable',
            'title': title_prefix + _(''),
            'title_short': title_short_prefix + ', ' + _('Stock Sparepart')}
       
        query_end = ""
        if branch_ids:
            query_end += " AND  b.id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
        if product_ids:
            query_end += " AND  q.product_id  in %s " % str(
                tuple(product_ids)).replace(',)', ')')
        if location_ids:
            query_end += " AND  q.location_id  in %s " % str(
                tuple(location_ids)).replace(',)', ')')
        # if date:
        #    query_end += " and q.in_date <= '" +str(date)+ "23:59:59'"

        categ_ids = self.pool.get('product.category').get_child_ids(cr, uid, ids, 'Sparepart')

        query_start = """ select * from
                    (select q.id as q_id, 
                    case when sum(q.qty) < 0 
                        then -1 * (sum(q.qty))
                        else sum(q.qty)
                    end as quantity, 
                    q.in_date as date, q.consolidated_date as consolidated_date,
                    q.reservation_id as reservation_id, m.id as move_id,
                    case when (reservation_id is not null and l.usage in ('internal','nrfs','kpb')) or (reservation_id is null and pack.name is null and l.usage='customer')
                           then orig.origin
                           else m.origin 
                    end as move_origin, sp.name as picking_name,
                    t.name as product_name, 
                    t.id as product_name_tmpl_id, 
                    t.description as product_desc, 
                    c.id as category_id, 
                    c.name as categ_name, 
                    c1.name as categ_parent_name, c.id as categ_id,
                    date_part('days', now() - MIN(q.in_date) ) as aging,
                    q.cost / case when sum(q.qty) = 0
                        then 1
                        else sum(q.qty)
                    end as harga_satuan,
                    q.cost as total_harga,
                    l.name as location_name, 
                    l.id as loc_id, 
                    b.id as branch_id, 
                    b.code as branch_code, b.name as branch_name, b.profit_centre as branch_profit_center,
                    p.default_code as p_default_code,
                    p.id as p_product_id,
                    w.id as p_warehouse_id,
                    b.warehouse_id as p_branch_warehouse,
                    l.usage as usage,
                    pack.name as pack_name,
                    pack.date as pack_date,
                    rm.name as ranking,
                    q.location_id as location_id,
                    orig.origin as orig_origin,
                    qm.state m_state,
                    case
                        when consolidated_date is null and l.usage in ('internal','nrfs','kpb') and qm.state = 'done'
                            then 'intransit'
                        when consolidated_date is not null and l.usage in ('nrfs','kpb') and reservation_id is null
                            then 'Not Ready for Sale'
                        when (reservation_id is not null and l.usage in ('internal','nrfs','kpb')) or (reservation_id is null and pack.name is null and l.usage='customer' and substring(m.origin,1,5) ='WOR-W')
                            then 'Reserved'
                        when consolidated_date is not null and l.usage ='internal' and reservation_id is null
                            then 'Ready for Sale'
                        when (reservation_id is not null and l.usage in ('internal','nrfs','kpb')) or (l.usage in ('internal','customer') and qm.state = 'assigned')
                            then 'Undelivered'
                        else 'Transfered'
                    end state
                    from stock_quant q
                    INNER JOIN stock_location l ON q.location_id = l.id
                    LEFT JOIN (select a.quant_id, max(a.move_id) as move_id, b.state from stock_quant_move_rel a
                    inner join stock_move b on a.move_id = b.id where b.state in ('done','assigned') group by a.quant_id,b.state) qm ON q.id = qm.quant_id
                    LEFT JOIN dym_branch b ON l.branch_id = b.id
                    LEFT JOIN stock_move m ON qm.move_id = m.id
                    LEFT JOIN stock_picking sp ON m.picking_id = sp.id
                    LEFT JOIN dym_stock_packing pack ON pack.picking_id = sp.id and pack.state = 'posted'
                    LEFT JOIN product_product p ON q.product_id = p.id
                    LEFT JOIN product_template t ON p.product_tmpl_id = t.id
                    LEFT JOIN product_category c ON t.categ_id = c.id
                    LEFT JOIN product_category c1 ON c.parent_id = c1.id
                    LEFT JOIN stock_warehouse w ON l.warehouse_id = w.id
                    LEFT JOIN (select rx.branch_id, max(rx.id) as rank_id from dym_ranking rx group by rx.branch_id) r ON b.id = r.branch_id
                    LEFT JOIN dym_ranking_line rl ON rl.rank_id = r.rank_id and rl.product_id = p.id
                    LEFT JOIN dym_ranking_master rm ON rl.master_rank_id = rm.id
                    LEFT JOIN stock_move orig ON orig.id=q.reservation_id 
                    WHERE 1=1 """ + query_end + """and t.categ_id in %s """ % str(
                    tuple(categ_ids)).replace(',)', ')') + """
                    group by c.id, q.id, q.in_date, consolidated_date, q.reservation_id, m.id, move_origin, picking_name ,t.name, t.id, product_desc, categ_name, category_id, categ_parent_name, location_name, loc_id, b.id, branch_code, branch_name,profit_centre, p.default_code, p.id, w.id, b.warehouse_id, l.usage, q.location_id, pack_name, pack_date, ranking, orig.origin, qm.state
                    order by branch_code,t.name,location_name) a
                    where state != 'Transfered' """
            
        # categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'Sparepart')  
        # query_start +=" and t.categ_id in %s " % str(
        #     tuple(categ_ids)).replace(',)', ')')
    

        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        # query_end=""
        # if branch_ids :
        #     query_end +=" AND  b.id in %s " % str(
        #         tuple(branch_ids)).replace(',)', ')')
        # if product_ids :
        #     query_end+=" AND  q.product_id  in %s " % str(
        #         tuple(product_ids)).replace(',)', ')')
        # if location_ids :
        #     query_end+=" AND  q.location_id  in %s " % str(
        #         tuple(location_ids)).replace(',)', ')')
        reports = [report_stock_sparepart]
        
        # query_group=" group by c.id, q.id, q.in_date, consolidated_date, q.reservation_id, m.id, move_origin, picking_name ,t.name, product_desc, categ_name, categ_parent_name, location_name, branch_code, branch_name,profit_centre, p.default_code, p.id, w.id, b.warehouse_id, l.usage, q.location_id, pack_name, pack_date, ranking, orig.origin "
        # query_order=" order by branch_code,t.name,location_name "
        
        for report in reports:
            
            # cr.execute(query_start + query_end+query_group+query_order)
            cr.execute(query_start)
            all_lines = cr.dictfetchall()
            quants = []

            if all_lines:
                p_map = map(
                    lambda x: {
                        'location_id': x['location_id'],
                        'q_id': x['q_id'],
                        'branch_id': str(x['branch_id']),
                        'branch_code': str(x['branch_code']),
                        'branch_name': str(x['branch_name']),
                        'parent_category': 'Sparepart',
                        'product_desc': str(x['product_desc']),
                        'pack_name': x['pack_name'].encode('utf-8') if x['pack_name'] != None else '',
                        'pack_date': str(x['pack_date']) if x['pack_date'] != None else '',
                        'ranking': str(x['ranking']) if x['ranking'] != None else '',
                        'category_id': str(x['category_id']),
                        'categ_name': str(x['categ_name']),
                        'categ_parent_name': str(x['categ_parent_name']),
                        'product_name_tmpl_id': str(x['product_name_tmpl_id']),
                        'product_name': str(x['product_name']),
                        'p_product_id': str(x['p_product_id']),
                        'move_origin': str(x['move_origin']),
                        'picking_name': str(x['picking_name']),
                        'location_name': str(x['location_name']),
                        'loc_id': str(x['loc_id']),
                        'aging': str(x['aging']),
                        'quantity':x['quantity'],
                        'default_code': x['p_default_code'],
                        # 'status': 'intransit' if not x['consolidated_date'] and x['usage'] in ['internal','nrfs','kpb'] else 'Ready for Sale' if x['consolidated_date'] and x['usage'] == 'internal' and not x['reservation_id'] else 'Not Ready for Sale' if x['consolidated_date'] and x['usage'] in ['nrfs','kpb'] and not x['reservation_id'] else 'Reserved' if x['reservation_id'] and x['usage'] in ['internal','nrfs','kpb']  and x['orig_origin'] and 'WOR-W' in x['orig_origin'] else 'Undelivered' if x['reservation_id'] and x['usage'] in ['internal','nrfs','kpb'] else 'Transferred' if not x['reservation_id'] and x['usage'] == 'customer' else 'n/a'                    },
                        'status':str(x['state'])},
                    all_lines)

                current_cost = {}
                for p in p_map:
                     if p['q_id'] not in map(
                            lambda x: x.get('q_id', None), quants):
                        quants.append(p)
                        quant_lines = filter(
                            lambda x: x['q_id'] == p['q_id'], all_lines)
                        p.update({'lines': quant_lines})
                        cost = 0
                        warehouse_id = quant_lines[0]['p_branch_warehouse'] or quant_lines[0]['p_warehouse_id']
                        if warehouse_id:
                            price_id = self.pool.get('product.price.branch').search(cr, uid, [('warehouse_id','=', warehouse_id), ('product_id','=', quant_lines[0]['p_product_id'])])
                            if price_id:
                                if p['status'] != 'intransit':
                                    cost = self.pool.get('product.price.branch').browse(cr, uid, price_id[0]).cost
                        category = self.pool.get('product.category').browse(cr, uid, [quant_lines[0]['categ_id']])
                        parent_category = 'Sparepart'
                        if category.isParentName('ACCESSORIES'):
                            parent_category = 'Aksesoris'
                        location_id = quant_lines[0]['location_id']
                        location_obj = self.pool.get('stock.location').browse(cr, uid, location_id)
                        location_parent = location_obj.name
                        while (location_obj.location_id.location_id):
                            location_obj = location_obj.location_id
                            location_parent = location_obj.name
                        p.update({
                            'parent_category': parent_category,
                            'harga_satuan': cost ,
                            'total_harga': cost*quant_lines[0]['quantity'],
                            'location_parent': location_parent,
                        })
                report.update({'quants': quants})

        reports = filter(lambda x: x.get('quants'), reports)
       
        if not reports:
            reports = [{
            'type': 'receivable',
            'title': title_prefix + _(''),
            'title_short': title_short_prefix + ', ' + _('Stock Sparepart') ,
                'quants':[{
                    'pack_name':'NO DATA FOUND',
                    'pack_date':'NO DATA FOUND',
                    'ranking':'NO DATA FOUND',
                    'branch_id':'NO DATA FOUND',
                    'branch_code':'NO DATA FOUND',
                    'branch_name': 'NO DATA FOUND',
                    'parent_category': 'NO DATA FOUND',
                    'product_desc': 'NO DATA FOUND',
                    'p_product_id': 'NO DATA FOUND',
                    'category_id': 'NO DATA FOUND',
                    'categ_name': 'NO DATA FOUND',
                    'categ_parent_name': 'NO DATA FOUND',
                    'product_name_tmpl_id': 'NO DATA FOUND',
                    'product_name': 'NO DATA FOUND',
                    'move_origin':'NO DATA FOUND',
                    'picking_name': 'NO DATA FOUND',
                    'location_name': 'NO DATA FOUND',
                    'loc_id': 'NO DATA FOUND',
                    'status' : 'NO DATA FOUND',
                    'aging': 'NO DATA FOUND',
                    'quantity':0,
                    'harga_satuan': 0,
                    'total_harga': 0,
                    'default_code': 'NO DATA FOUND',
                    'location_parent': 'NO DATA FOUND',
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
        super(dym_stock_sparepart_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_stock_sparepart_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_tock.report_stock_sparepart'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_tock.report_stock_sparepart'
    _wrapped_report_class = dym_stock_sparepart_report_print
