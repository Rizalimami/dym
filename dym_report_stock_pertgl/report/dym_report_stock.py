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


class dym_stock_unit_report_pertgl_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_stock_unit_report_pertgl_print, self).__init__(
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
     
        report_stock_unit = {
            'date': date,
            'type': 'receivable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Report Stock Unit Per Tanggal')}

        query_start = "select a.id as p_id, " \
            "c.name as p_name , " \
            "e.name_template as p_kode_product,  " \
            "x.description as p_default_code,  " \
            "g.code as p_warna,  " \
            "d.name as p_mesin,  " \
            "d.chassis_no as p_rangka,  " \
            "a.lot_id as lot_id,  " \
            "'"+str(date)+"' - d.receive_date as p_umur, "\
            "date_part('days', '"+str(date)+" 23:59:59' - MIN(a.in_date) ) as p_umur_quant, "\
            "d.tahun as p_tahun,  " \
            "d.state as p_state,  " \
            "b.name as p_nama_lokasi  " \
            "From  " \
            "stock_quant a " \
            "LEFT JOIN stock_location b ON b.id = a.location_id " \
            "LEFT JOIN dym_branch c ON c.id = b.branch_id " \
            "LEFT JOIN stock_production_lot d ON d.id = a.lot_id " \
            "LEFT JOIN product_product e ON e.id = a.product_id " \
            "LEFT JOIN product_template x ON x.id = e.product_tmpl_id " \
            "LEFT JOIN product_attribute_value_product_product_rel f ON f.prod_id = a.product_id " \
            "LEFT JOIN product_attribute_value g ON g.id = f.att_id " \
            "LEFT JOIN product_category h ON h.id = x.categ_id " \
            "LEFT JOIN stock_warehouse w ON b.warehouse_id = w.id " \
            "LEFT JOIN stock_picking r ON r.id = d.picking_id " \
            "LEFT JOIN dym_stock_packing p ON r.id = p.picking_id and p.branch_sender_id is not null " \
            "LEFT JOIN dym_branch bs ON p.branch_sender_id = bs.id " \
            "where a.lot_id is not null and a.in_date <= '"+str(date)+" 23:59:59' "
            
        
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'Unit')  
        query_start +="and h.id in %s" % str(
            tuple(categ_ids)).replace(',)', ')')

        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        query_end=""
        if branch_ids :
            query_end +=" AND  b.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if product_ids :
            query_end+="AND  a.product_id  in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        if location_ids :
            query_end+="AND  a.location_id  in %s" % str(
                tuple(location_ids)).replace(',)', ')')
        reports = [report_stock_unit]
        
        query_group=" group by a.id,p_name,p_kode_product,p_default_code,p_warna,p_mesin,p_rangka,lot_id,p_umur,p_tahun,p_state,p_nama_lokasi "
        query_order="order by p_kode_product "
        
        for report in reports:
            cr.execute(query_start + query_end+query_group+query_order)
            all_lines = cr.dictfetchall()
            partners = []
            if all_lines:
                def lines_map(x):
                        x.update({'docname': x['p_name']})
                map(lines_map, all_lines)
                for cnt in range(len(all_lines)-1):
                    if all_lines[cnt]['p_id'] != all_lines[cnt+1]['p_id']:
                        all_lines[cnt]['draw_line'] = 1
                    else:
                        all_lines[cnt]['draw_line'] = 0
                all_lines[-1]['draw_line'] = 1
                p_map = map(
                    lambda x: {
                        'p_id': x['p_id'],
                        'lot_id': x['lot_id'],
                        'p_name': x['p_name'],
                        'p_parent_category': 'Unit',
                        'p_branch_name': x['p_name'],
                        'p_kode_product': x['p_kode_product'],
                        'p_warna': x['p_warna'],
                        'p_umur': str(x['p_umur']) if x['p_umur'] != None and x['p_umur'] >= 0 else str(x['p_umur_quant']).split('.')[0] if x['p_umur_quant'] != None else '',
                        'p_nama_lokasi': x['p_nama_lokasi'],
                        'p_mesin': x['p_mesin'],
                        'p_tahun': x['p_tahun'],
                        'p_rangka': x['p_rangka'],
                        'p_default_code': x['p_default_code'],},
                    all_lines)

                date_time = str(date) + ' 23:59:59'
                lot_ids = []
                product_code = ''
                total_intransit = 0
                total_reserved = 0
                total_undelivered = 0
                total_rfs = 0
                total_nrfs = 0
                grand_total_intransit = 0
                grand_total_reserved = 0
                grand_total_undelivered = 0
                grand_total_rfs = 0
                grand_total_nrfs = 0
                for p in p_map:
                    if p['p_id'] not in map(
                            lambda x: x.get('p_id', None), partners):
                        partner_lines = filter(
                            lambda x: x['p_id'] == p['p_id'], all_lines)
                        quant = self.pool.get('stock.quant').browse(cr, SUPERUSER_ID, partner_lines[0]['p_id'])
                        filtered_history_quant_before = quant.history_ids.filtered(lambda r: r.date <= date_time).sorted(key=lambda r: r.date, reverse=True)
                        if filtered_history_quant_before and filtered_history_quant_before[0].location_dest_id.usage not in ('internal','nrfs'):
                            continue
                        elif partner_lines[0]['lot_id'] in lot_ids:
                            continue
                        if product_code not in ('',partner_lines[0]['p_kode_product']) and (total_nrfs > 0 or total_rfs > 0 or total_intransit > 0 or total_reserved > 0 or total_undelivered > 0):
                            partners.append({
                                        'p_id': '',
                                        'lot_id': '',
                                        'p_name': '',
                                        'p_parent_category': '',
                                        'p_branch_name': '',
                                        'p_kode_product': '',
                                        'p_warna': '',
                                        'p_umur': '',
                                        'p_nama_lokasi': '',
                                        'p_mesin': '',
                                        'p_tahun': 'Sub Total',
                                        'p_rangka': '',
                                        'p_default_code': '',
                                        'lines': partner_lines,
                                        'intransit': total_intransit,
                                        'rfs': total_rfs,
                                        'nrfs': total_nrfs,
                                        'reserved': total_reserved,
                                        'undelivered': total_undelivered
                                        })
                            total_intransit = 0
                            total_reserved = 0
                            total_undelivered = 0
                            total_rfs = 0
                            total_nrfs = 0
                            product_code = partner_lines[0]['p_kode_product']
                        if product_code == '':
                            product_code = partner_lines[0]['p_kode_product']
                        p.update({'lines': partner_lines})
                        intransit = 0
                        rfs = 0
                        nrfs = 0
                        reserved = 0
                        undelivered = 0
                        location = partner_lines[0]['p_nama_lokasi']
                        if quant.in_date <= date_time and ((quant.consolidated_date and quant.consolidated_date > date_time) or not quant.consolidated_date):
                            intransit = 1
                            location = quant.history_ids.filtered(lambda r: r.date <= date_time).sorted(key=lambda r: r.date)[0].location_dest_id.name
                        elif filtered_history_quant_before and quant.lot_id.dealer_sale_order_id and quant.lot_id.dealer_sale_order_id.confirm_date and quant.lot_id.dealer_sale_order_id.confirm_date <= date_time and filtered_history_quant_before[0].location_dest_id.usage != 'customer':
                            undelivered = 1
                            location = quant.lot_id.dealer_sale_order_id.dealer_sale_order_line.filtered(lambda r: r.lot_id == quant.lot_id).location_id.name
                        elif quant.lot_id.dealer_sale_order_id and quant.lot_id.dealer_sale_order_id.create_date <= date_time and ((quant.lot_id.dealer_sale_order_id.confirm_date and quant.lot_id.dealer_sale_order_id.confirm_date > date_time) or not quant.lot_id.dealer_sale_order_id.confirm_date):
                            reserved = 1
                            location = quant.lot_id.dealer_sale_order_id.dealer_sale_order_line.filtered(lambda r: r.lot_id == quant.lot_id).location_id.name
                        elif filtered_history_quant_before and filtered_history_quant_before[0].location_dest_id.usage == 'internal':
                            rfs = 1
                            location = filtered_history_quant_before[0].location_dest_id.name
                        elif filtered_history_quant_before and filtered_history_quant_before[0].location_dest_id.usage == 'nrfs':
                            nrfs = 1
                            location = filtered_history_quant_before[0].location_dest_id.name
                        p.update({
                                'p_nama_lokasi': location,
                                'intransit': intransit,
                                'rfs': rfs,
                                'nrfs': nrfs,
                                'reserved': reserved,
                                'undelivered': undelivered
                                })
                        total_intransit += intransit
                        total_rfs += rfs
                        total_nrfs += nrfs
                        total_reserved += reserved
                        total_undelivered += undelivered
                        if nrfs > 0 or rfs > 0 or intransit > 0 or reserved > 0 or undelivered > 0:
                            lot_ids.append(partner_lines[0]['lot_id'])
                            partners.append(p)
                if partners and (total_nrfs > 0 or total_rfs > 0 or total_intransit > 0 or total_reserved > 0 or total_undelivered > 0):
                    partners.append({
                                'p_id': '',
                                'lot_id': '',
                                'p_name': '',
                                'p_parent_category': '',
                                'p_branch_name': '',
                                'p_kode_product': '',
                                'p_warna': '',
                                'p_umur': '',
                                'p_nama_lokasi': '',
                                'p_mesin': '',
                                'p_tahun': 'Sub Total',
                                'p_rangka': '',
                                'p_default_code': '',
                                'lines': partner_lines,
                                'intransit': total_intransit,
                                'rfs': total_rfs,
                                'nrfs': total_nrfs,
                                'reserved': total_reserved,
                                'undelivered': total_undelivered
                                })
                report.update({'partners': partners})

                

        reports = filter(lambda x: x.get('partners'), reports)
        if not reports:
            raise orm.except_orm(
                _('No Data Available'),
                _('No records found for your selection!'))

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        objects = False
        super(dym_stock_unit_report_pertgl_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_stock_unit_report_pertgl_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_stock_pertgl.report_stock_unit_pertgl'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_stock_pertgl.report_stock_unit_pertgl'
    _wrapped_report_class = dym_stock_unit_report_pertgl_print
