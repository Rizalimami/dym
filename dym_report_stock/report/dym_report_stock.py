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


class dym_stock_unit_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_stock_unit_report_print, self).__init__(
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
     
        report_stock_unit = {
            'show_valuation': show_valuation,
            'type': 'receivable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Report Stock Unit')}


        query_start = "select a.id as p_id, " \
            "c.name as nama_branch,  " \
            "c.code as code_branch,  " \
            "c.profit_centre as profit_centre,  " \
            "c.name as p_name , " \
            "e.name_template as p_kode_product,  " \
            "b.complete_name as p_nama_lokasi,  " \
            "b.usage as usage,  " \
            "d.receive_date as p_tanggal,  " \
            "p.name as p_grn_no, " \
            "d.name as p_mesin,  " \
            "d.chassis_no as p_rangka,  " \
            "d.tahun as p_tahun,  " \
            "a.qty as p_qty,  " \
            " ppb.current_valuation / coalesce(nullif(current_stock,0),1) as p_cost, " \
            "a.reservation_id as reservation_id,  " \
            "h.name as p_categ_name,  " \
            "g.code as p_warna,  " \
            "date_part('days', now() - d.receive_date) as p_umur, "\
            "0 as p_umur_mutasi, "\
            "AGE(CURRENT_DATE, d.receive_date) as umur,  " \
            "d.state as p_state,  " \
            "x.description as p_default_code,  " \
            "e.id as p_product_id,  " \
            "w.id as p_warehouse_id,  " \
            "c.warehouse_id as p_branch_warehouse,  " \
            "COALESCE(bs.name, '') as branch_source,  " \
            "r.origin as p_origin " \
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
            "LEFT JOIN dym_stock_packing p ON r.id = p.picking_id " \
            "LEFT JOIN dym_branch bs ON p.branch_sender_id = bs.id " \
            "LEFT JOIN product_price_branch ppb on ppb.warehouse_id=b.warehouse_id and ppb.product_id=a.product_id " \
            "where b.usage in ('internal','nrfs','kpb') "
            
        
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
        
        query_order="order by nama_branch,code_branch,profit_centre,p_nama_lokasi,p_kode_product,p_warna,p_tanggal "
        # print query_start + query_end + query_order
        
        for report in reports:
            cr.execute(query_start + query_end+query_order)
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
                # product_category = self.product_id.categ_id.get_root_name()
                p_map = map(
                    lambda x: {
                        'p_id': x['p_id'],
                        'p_name': x['p_name'],
                        'p_code': x['code_branch'],
                        # 'p_profit_centre': str(x['profit_centre']),
                        'p_parent_category': 'Unit',
                        'p_categ_name': str(x['p_categ_name']),
                        'p_branch_name': x['p_name'],
                        'p_kode_product': x['p_kode_product'],
                        'p_warna': x['p_warna'],
                        'p_umur': str(x['p_umur']) if x['p_umur'] != None else str(x['p_umur_mutasi']),
                        'branch_source': str(x['branch_source']) if x['branch_source'] != None else '',
                        'p_umur_mutasi': str(x['p_umur_mutasi']),
                        'p_nama_lokasi': x['p_nama_lokasi'],
                        'p_tanggal': x['p_tanggal'],
                        'p_grn_no' : str(x['p_grn_no']),
                        'p_qty': str(x['p_qty']),
                        'p_cost':  x['p_cost'],
                        'p_mesin': x['p_mesin'],
                        'p_tahun': x['p_tahun'],
                        'p_rangka': x['p_rangka'],
                        'p_state': x['p_state'],
                        'p_origin': x['p_origin'],
                        'p_default_code': x['p_default_code'],
                        'state_stock': 'intransit' if x['p_state'] == 'intransit' and x['usage'] in ['internal','nrfs','kpb'] else 'Ready for Sale' if x['p_state'] == 'stock' and x['usage'] == 'internal' and not x['reservation_id'] else 'Not Ready for Sale' if x['p_state'] == 'stock' and x['usage'] in ['nrfs','kpb'] and not x['reservation_id'] else 'Undelivered' if x['p_state'] in ['sold','sold_offtr','paid','paid_offtr'] and x['usage'] in ['internal','nrfs','kpb'] else 'Transferred' if x['p_state'] in ['sold','sold_offtr','paid','paid_offtr'] and x['usage'] == 'customer' else 'Reserved' if (x['p_state'] == 'reserved' or x['reservation_id']) and x['usage'] in ['internal','nrfs','kpb']  else 'Purchase Return' if x['p_state'] == 'returned' and x['usage'] in ['internal','nrfs','kpb'] else 'Transferred' if x['p_state'] == 'returned' and x['usage'] == 'supplier' else 'Asset' if x['p_state'] == 'asset' else ''},
                    all_lines)
                for p in p_map:
                    if p['p_id'] not in map(
                            lambda x: x.get('p_id', None), partners):
                        partners.append(p)
                        partner_lines = filter(
                            lambda x: x['p_id'] == p['p_id'], all_lines)
                        p.update({'lines': partner_lines})
                        p.update(
                            {'d': 1,
                             'c': 2,
                             'b': 3})
                        cost = 0
                        warehouse_id = partner_lines[0]['p_branch_warehouse'] or partner_lines[0]['p_warehouse_id']
                        if warehouse_id:
                            price_id = self.pool.get('product.price.branch').search(cr, uid, [('warehouse_id','=', warehouse_id), ('product_id','=', partner_lines[0]['p_product_id'])])
                            # if price_id:
                            #    cost = self.pool.get('product.price.branch').browse(cr, uid, price_id[0]).cost
                            #    cost =  locale.format("%d", cost, grouping=False)
                            if p['state_stock'] != 'intransit':
                                cost = p['p_cost']
                        quant = self.pool.get('stock.quant').browse(cr, uid, partner_lines[0]['p_id'])
                        if quant.product_id.categ_id:
                            category = quant.product_id.categ_id
                            while (category.parent_id and category.parent_id.bisnis_unit == False):
                                category = category.parent_id
                            p.update({'p_categ_name': category.name,
                                      'p_cost' : cost})

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
        super(dym_stock_unit_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_stock_unit_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_stock.report_stock_unit'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_stock.report_stock_unit'
    _wrapped_report_class = dym_stock_unit_report_print
