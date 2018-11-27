from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm
from openerp import SUPERUSER_ID

class dym_report_stock_outstanding_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_stock_outstanding_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        division = data['division']
        date_start_date = data['date_start_date']
        date_end_date = data['date_end_date']
        branch_ids = data['branch_ids']
        product_ids = data['product_ids']
        
        title_short_prefix = ''
        report_stock_outstanding = {
            'type': 'receivable',
            'title': '',
            'division':division,
            'title_short': title_short_prefix + '' + _('Laporan Stock Outstanding')}
        where_division = " 1=1 "
        if division:
            where_division = " spack.division = '%s'" % str(division)
        where_picking_type_code = " 1=1 "
        where_date_start_date = " 1=1 "
        if date_start_date:
            where_date_start_date = " date(spack.date) >= '%s'" % str(date_start_date)
        where_state = " 1=1 "
        where_date_end_date = " 1=1 "
        where_ois_date = " 1=1 "
        if date_end_date:
            where_date_end_date = " date(spack.date) <= '%s'" % str(date_end_date)
            where_ois_date = " date(spick.date_done) <= '%s'" % str(date_end_date)
        where_min_date_start_date = " 1=1 "
        where_min_date_end_date = " 1=1 "
        where_date_done_start_date = " 1=1 "
        where_date_done_end_date = " 1=1 "
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " spack.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        where_product_ids = " 1=1 "
        if product_ids :
            where_product_ids = " product.id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        where_partner_ids = " 1=1 "
        where_categ_ids = " 1=1 "

        query_stock_outstanding = "SELECT CONCAT(cast(spl.id as text),'-dym_stock_packing_line') as id_ai, spick.id as id_picking, 'pack' as object, spl.id as pack_line_id, prod_tmpl.categ_id as categ_id, " \
            "b.code as branch_code, b.name as branch_name, spick.division, spt.name as picking_type_name, spack.name as packing_name, spack.date as packing_date, " \
            "mo.date as partner_code, mo.name as partner_name, date(spick.date) as ekspedisi_code, spick.name as ekspedisi_name, " \
            "product.name_template as prod_tmpl, pav.code as color, spl.engine_number as engine, spl.chassis_number as chassis, " \
            "spl.tahun_pembuatan as tahun, " \
            "spl.quantity  as qty, " \
            "0 as qty_out, " \
            "spack.state as packing_state, spick.origin as picking_origin, prod_categ.name as categ_name, product.default_code as internal_ref, " \
            "'' as backorder, sloc.name as location, case when spl.ready_for_sale = true then 'RFS' else 'NRFS' end as status_rfs, '' as branch_source, parent_sloc.name as parent_location, source_sloc.name as location_source, parent_source_sloc.name as parent_location_source " \
            "FROM " \
            "dym_mutation_request spack " \
            "left join dym_stock_distribution dist ON dist.request_id = spack.id " \
            "left join dym_mutation_order mo ON mo.distribution_id = dist.id " \
            "left join stock_picking spick ON spick.origin = mo.name and spick.state = 'done' and " + where_ois_date +" " \
            "left join stock_picking spick2 ON spick2.origin = mo.name " \
            "left join dym_stock_packing packing ON packing.picking_id = spick2.id " \
            "left join dym_stock_packing_line spl ON packing.id = spl.packing_id " \
            "left join dym_branch b on b.id = spack.branch_id " \
            "left join product_product product on product.id = spl.product_id " \
            "left join product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id " \
            "left join product_attribute_value pav ON pavpp.att_id = pav.id " \
            "left join stock_picking_type spt ON spt.id = spick.picking_type_id " \
            "left join stock_picking_type spt2 ON spt2.id = spick2.picking_type_id " \
            "left join product_template prod_tmpl ON prod_tmpl.id = product.product_tmpl_id " \
            "left join product_category prod_categ ON prod_categ.id = prod_tmpl.categ_id " \
            "left join stock_location sloc ON sloc.id = spl.destination_location_id " \
            "left join stock_location parent_sloc ON parent_sloc.id = sloc.location_id " \
            "left join stock_location source_sloc ON source_sloc.id = spl.source_location_id " \
            "left join stock_location parent_source_sloc ON parent_source_sloc.id = source_sloc.location_id " \
            "where ((spl.engine_number is not null and spack.division = 'Unit') or spack.division != 'Unit') and spl.quantity > 0 and " + where_state + " AND " + where_division + " AND " + where_picking_type_code + " AND " + where_date_start_date + " AND " + where_date_end_date + " AND " + where_min_date_start_date + " AND " + where_min_date_end_date + " AND " + where_date_done_start_date + " AND " + where_date_done_end_date + " AND " + where_branch_ids + " AND " + where_categ_ids + " AND " + where_product_ids + " AND " + where_partner_ids + " and spick2.id is not null and spt2.code = 'interbranch_out' and spt.code != 'interbranch_out' " \
            " ORDER BY packing_date asc " \
        
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        reports = [report_stock_outstanding]
        
        for report in reports:
            cr.execute(query_stock_outstanding)
            all_lines = cr.dictfetchall()
            picking_ids = []

            if all_lines:
                def lines_map(x):
                        x.update({'docname': x['branch_code']})
                map(lines_map, all_lines)
                for cnt in range(len(all_lines)-1):
                    if all_lines[cnt]['id_picking'] != all_lines[cnt+1]['id_picking']:
                        all_lines[cnt]['draw_line'] = 1
                    else:
                        all_lines[cnt]['draw_line'] = 0
                all_lines[-1]['draw_line'] = 1

                p_map = map(
                    lambda x: {
                        'no': 0,
                        'id_picking': str(x['id_picking']),
                        'id_ai': str(x['id_ai']),
                        'object': str(x['object']),
                        'pack_line_id': x['pack_line_id'],
                        'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                        'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                        'branch_source': str(x['branch_source'].encode('ascii','ignore').decode('ascii')) if x['branch_source'] != None else '',
                        'division': str(x['division'].encode('ascii','ignore').decode('ascii')) if x['division'] != None else '',
                        'picking_type_name': str(x['picking_type_name'].encode('ascii','ignore').decode('ascii')) if x['picking_type_name'] != None else '',
                        'internal_ref': str(x['internal_ref'].encode('ascii','ignore').decode('ascii')) if x['internal_ref'] != None else '',
                        'categ_name': str(x['categ_name'].encode('ascii','ignore').decode('ascii')) if x['categ_name'] != None else '',
                        'packing_name': str(x['packing_name'].encode('ascii','ignore').decode('ascii')) if x['packing_name'] != None else '',
                        'packing_date': str(x['packing_date'].encode('ascii','ignore').decode('ascii')) if x['packing_date'] != None else '',
                        'partner_code': str(x['partner_code'].encode('ascii','ignore').decode('ascii')) if x['partner_code'] != None else '',
                        'partner_name': str(x['partner_name'].encode('ascii','ignore').decode('ascii')) if x['partner_name'] != None else '',
                        'ekspedisi_code': str(x['ekspedisi_code'].encode('ascii','ignore').decode('ascii')) if x['ekspedisi_code'] != None else '',
                        'ekspedisi_name': str(x['ekspedisi_name'].encode('ascii','ignore').decode('ascii')) if x['ekspedisi_name'] != None else '',
                        'prod_tmpl': str(x['prod_tmpl'].encode('ascii','ignore').decode('ascii')) if x['prod_tmpl'] != None else '',
                        'color': str(x['color'].encode('ascii','ignore').decode('ascii')) if x['color'] != None else '',
                        'engine': str(x['engine'].encode('ascii','ignore').decode('ascii')) if x['engine'] != None else '',
                        'chassis': str(x['chassis'].encode('ascii','ignore').decode('ascii')) if x['chassis'] != None else '',
                        'tahun': str(x['tahun'].encode('ascii','ignore').decode('ascii')) if x['tahun'] != None else '',
                        'qty': x['qty'],
                        'qty_out': x['qty_out'],
                        'packing_state': str(x['packing_state'].encode('ascii','ignore').decode('ascii')) if x['packing_state'] != None else '',
                        'picking_origin': str(x['picking_origin'].encode('ascii','ignore').decode('ascii')) if x['picking_origin'] != None else '',
                        'backorder': str(x['backorder'].encode('ascii','ignore').decode('ascii')) if x['backorder'] != None else '',
                        'location': str(x['location'].encode('ascii','ignore').decode('ascii')) if x['location'] != None else '',
                        'parent_location': str(x['parent_location'].encode('ascii','ignore').decode('ascii')) if x['parent_location'] != None else '',
                        'location_source': str(x['location_source'].encode('ascii','ignore').decode('ascii')) if x['location_source'] != None else '',
                        'parent_location_source': str(x['parent_location_source'].encode('ascii','ignore').decode('ascii')) if x['parent_location_source'] != None else '',
                        'status_rfs': str(x['status_rfs'].encode('ascii','ignore').decode('ascii')) if x['status_rfs'] != None else '',
                    },
                    
                    all_lines)
                stock_awal = 0
                total_stock = 0
                # for p in p_map:
                #     if p['id_ai'] not in map(
                #             lambda x: x.get('id_ai', None), picking_ids):
                #         packing_line = filter(
                #             lambda x: x['id_ai'] == p['id_ai'], all_lines)
                #         if packing_line[0]['packing_date'] < str(date_start_date) and date_start_date:
                #             stock_awal += packing_line[0]['qty']
                #             stock_awal -= packing_line[0]['qty_out']
                #         else:
                #             total_stock += packing_line[0]['qty']
                #             total_stock -= packing_line[0]['qty_out']
                #             p.update({'lines': packing_line})
                #             picking_ids.append(p)
                stock_akhir = stock_awal + total_stock
                # report.update({'kode_produk': kode_produk})
                # report.update({'deskripsi': deskripsi})
                # report.update({'warna': warna})
                # report.update({'nosin': nosin})
                # report.update({'cabang': cabang})
                # report.update({'stock_awal': stock_awal})
                # report.update({'stock_akhir': stock_akhir})
                # report.update({'picking_ids': picking_ids})
                report.update({'picking_ids': p_map})

        reports = filter(lambda x: x.get('picking_ids'), reports)
        
        if not reports :
            reports = [{'picking_ids': [{
                        'no': 0,
                        'branch_code': 'NO DATA FOUND',
                        'branch_name': 'NO DATA FOUND',
                        'branch_source': 'NO DATA FOUND',
                        'division': 'NO DATA FOUND',
                        'categ_name': 'NO DATA FOUND',
                        'internal_ref': 'NO DATA FOUND',
                        'picking_type_name': 'NO DATA FOUND',
                        'packing_name': 'NO DATA FOUND',
                        'packing_date': 'NO DATA FOUND',
                        'partner_code': 'NO DATA FOUND',
                        'partner_name': 'NO DATA FOUND',
                        'ekspedisi_code': 'NO DATA FOUND',
                        'ekspedisi_name': 'NO DATA FOUND',
                        'prod_tmpl': 'NO DATA FOUND',
                        'color': 'NO DATA FOUND',
                        'engine': 'NO DATA FOUND',
                        'chassis': 'NO DATA FOUND',
                        'tahun': 'NO DATA FOUND',
                        'location': 'NO DATA FOUND',
                        'parent_location': 'NO DATA FOUND',
                        'location_source': 'NO DATA FOUND',
                        'parent_location_source': 'NO DATA FOUND',
                        'status_rfs': 'NO DATA FOUND',
                        'qty': 0,
                        'packing_state': 'NO DATA FOUND',
                        'picking_origin': 'NO DATA FOUND',
                        'backorder': 'NO DATA FOUND',}], 'title_short': 'Laporan Stock Outstanding', 'type': 'receivable', 'title': '', 'division':division}]
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_stock_outstanding_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_stock_outstanding_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_stock_outstanding.report_stock_outstanding'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_stock_outstanding.report_stock_outstanding'
    _wrapped_report_class = dym_report_stock_outstanding_print
