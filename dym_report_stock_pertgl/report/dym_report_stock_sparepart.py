# -*- coding: utf-8 -*-

from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
from openerp import SUPERUSER_ID

import logging
import locale
_logger = logging.getLogger(__name__)


class dym_stock_sparepart_report_pertgl_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_stock_sparepart_report_pertgl_print, self).__init__(
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
        date = data['date']
        
        title_prefix = ''
        title_short_prefix = ''
     
        report_stock_sparepart = {
            'date': date,
            'type': 'receivable',
            'title': title_prefix + _(''),
            'title_short': title_short_prefix + ', ' + _('Stock Sparepart Per Tanggal')}

        query_start = " select q.id as q_id, "\
            "b.name as branch_name, "\
            "t.name as product_name,  "\
            "t.description as product_desc,  "\
            "rm.name as ranking,  "\
            "c1.name as categ_parent_name, "\
            "c.name as categ_name,  "\
            "l.name as location_name, "\
            "p.default_code as p_default_code, "\
            "c.id as categ_id "\
            "from stock_quant q "\
            "INNER JOIN stock_location l ON q.location_id = l.id "\
            "LEFT JOIN (select a.quant_id, max(a.move_id) as move_id from stock_quant_move_rel a  "\
            "inner join stock_move b on a.move_id = b.id where b.state = 'done' group by a.quant_id) qm ON q.id = qm.quant_id "\
            "LEFT JOIN dym_branch b ON l.branch_id = b.id "\
            "LEFT JOIN stock_move m ON qm.move_id = m.id "\
            "LEFT JOIN stock_picking sp ON m.picking_id = sp.id "\
            "LEFT JOIN dym_stock_packing pack ON pack.picking_id = sp.id and pack.state = 'posted' "\
            "LEFT JOIN product_product p ON q.product_id = p.id "\
            "LEFT JOIN product_template t ON p.product_tmpl_id = t.id "\
            "LEFT JOIN product_category c ON t.categ_id = c.id  "\
            "LEFT JOIN product_category c1 ON c.parent_id = c1.id  "\
            "LEFT JOIN stock_warehouse w ON l.warehouse_id = w.id  "\
            "LEFT JOIN (select rx.branch_id, max(rx.id) as rank_id from dym_ranking rx group by rx.branch_id) r ON b.id = r.branch_id "\
            "LEFT JOIN dym_ranking_line rl ON rl.rank_id = r.rank_id and rl.product_id = p.id "\
            "LEFT JOIN dym_ranking_master rm ON rl.master_rank_id = rm.id "\
            "WHERE 1=1 and q.in_date <= '"+str(date)+" 23:59:59' "
            
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'Sparepart')  
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
        reports = [report_stock_sparepart]
        
        query_group=" group by c.id, q.id, t.name, product_desc, categ_name, categ_parent_name, location_name, branch_name, p.default_code, ranking"
        query_order=" order by branch_name, t.name, location_name "
        
        for report in reports:
            
            cr.execute(query_start + query_end+query_group+query_order)
            all_lines = cr.dictfetchall()
            quants = []
            if not all_lines:
                raise osv.except_osv(_('Error!'), _('Data not found.'))

            if all_lines:
                p_map = map(
                    lambda x: {
                        'q_id': x['q_id'],
                        'branch_name': str(x['branch_name']),
                        'parent_category': 'Sparepart',
                        'product_name': str(x['product_name']),
                        # 'product_desc': str(x['product_desc'].encode('ascii','ignore').decode('ascii') if x['product_desc'].encode('ascii','ignore').decode('ascii') != None else x['p_default_code'].encode('ascii','ignore').decode('ascii') if x['p_default_code'].encode('ascii','ignore').decode('ascii') != None else ''),
                        'product_desc': str(x['product_desc'] if x['product_desc'] != None else x['p_default_code'] if x['p_default_code'] != None else ''),
                        'ranking': str(x['ranking']) if x['ranking'] != None else '',
                        'categ_parent_name': str(x['categ_parent_name']),
                        'categ_name': str(x['categ_name']),
                        'location_name': str(x['location_name']),
                        },
                    all_lines)

                date_time = str(date) + ' 23:59:59'
                product_code = ''
                for p in p_map:
                     if p['q_id'] not in map(
                            lambda x: x.get('q_id', None), quants):
                        quant_lines = filter(
                            lambda x: x['q_id'] == p['q_id'], all_lines)
                        p.update({'lines': quant_lines})
                        intransit = 0
                        rfs = 0
                        nrfs = 0
                        reserved = 0
                        undelivered = 0
                        quant = self.pool.get('stock.quant').browse(cr, SUPERUSER_ID, quant_lines[0]['q_id'])
                        location = quant.location_id
                        filtered_history_quant_before = quant.history_ids.filtered(lambda r: r.date <= date_time).sorted(key=lambda r: r.date, reverse=True)
                        filtered_history_quant_after = quant.history_ids.filtered(lambda r: r.date > date_time).sorted(key=lambda r: r.date)
                        if filtered_history_quant_before and filtered_history_quant_before[0].location_dest_id.usage not in ('internal','nrfs'):
                            continue
                        elif quant.in_date <= date_time and ((quant.consolidated_date and quant.consolidated_date > date_time) or not quant.consolidated_date):
                            intransit = quant.qty
                            location = quant.history_ids.filtered(lambda r: r.date <= date_time).sorted(key=lambda r: r.date)[0].location_dest_id
                        elif (filtered_history_quant_after and filtered_history_quant_after[0].create_date <= date_time and filtered_history_quant_after.date > date_time and filtered_history_quant_after[0].location_dest_id.usage == 'customer') or quant.reservation_id :
                            undelivered = quant.qty
                            location = filtered_history_quant_after[0].location_id if filtered_history_quant_after else location
                        elif filtered_history_quant_before and filtered_history_quant_before[0].location_dest_id.usage == 'internal':
                            rfs = quant.qty
                            location = filtered_history_quant_before[0].location_dest_id
                        elif filtered_history_quant_before and filtered_history_quant_before[0].location_dest_id.usage == 'nrfs':
                            nrfs = quant.qty
                            location = filtered_history_quant_before[0].location_dest_id
                        p.update({
                                'location_name': location.name,
                                'intransit': intransit,
                                'rfs': rfs,
                                'nrfs': nrfs,
                                'reserved': reserved,
                                'undelivered': undelivered
                                })
                        if nrfs > 0 or rfs > 0 or intransit > 0 or reserved > 0 or undelivered > 0:
                            total_stock = nrfs + rfs + intransit + reserved + undelivered
                            if product_code == quant_lines[0]['branch_name']+quant_lines[0]['product_name']+quant_lines[0]['location_name']:
                                quants[len(quants)-1]['intransit'] += intransit
                                quants[len(quants)-1]['rfs'] += rfs
                                quants[len(quants)-1]['nrfs'] += nrfs
                                quants[len(quants)-1]['reserved'] += reserved
                                quants[len(quants)-1]['undelivered'] += undelivered
                                quants[len(quants)-1]['total_stock'] += total_stock
                                continue
                            category = self.pool.get('product.category').browse(cr, uid, [quant_lines[0]['categ_id']])
                            parent_category = 'Sparepart'
                            if category.isParentName('ACCESSORIES'):
                                parent_category = 'Aksesoris'
                            location_obj = location
                            location_parent = location_obj.name
                            while (location_obj.location_id.location_id):
                                location_obj = location_obj.location_id
                                location_parent = location_obj.name
                            p.update({
                                'parent_category': parent_category,
                                'location_parent': location_parent,
                                'total_stock': total_stock,
                                })
                            product_code = quant_lines[0]['branch_name']+quant_lines[0]['product_name']+quant_lines[0]['location_name']
                            quants.append(p)
                report.update({'quants': quants})

        reports = filter(lambda x: x.get('quants'), reports)
        if not reports:
            reports = [{
            'type': 'receivable',
            'title': title_prefix + _(''),
            'title_short': title_short_prefix + ', ' + _('Stock Sparepart') ,
                        'quants':
                            [ {
                        'branch_name': 'NO DATA FOUND',
                        'product_name': 'NO DATA FOUND',
                        'product_desc': 'NO DATA FOUND',
                        'parent_category': 'NO DATA FOUND',
                        'categ_parent_name': 'NO DATA FOUND',
                        'categ_name': 'NO DATA FOUND',
                        'ranking':'NO DATA FOUND',
                        'location_parent': 'NO DATA FOUND',
                        'location_name': 'NO DATA FOUND',
                        'intransit':0,
                        'rfs': 0,
                        'nrfs': 0,
                        'reserved': 0,
                        'undelivered': 0,
                        'total_stock': 0,
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
        super(dym_stock_sparepart_report_pertgl_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_stock_sparepart_report_pertgl_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_stock_pertgl.report_stock_sparepart_pertgl'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_stock_pertgl.report_stock_sparepart_pertgl'
    _wrapped_report_class = dym_stock_sparepart_report_pertgl_print
