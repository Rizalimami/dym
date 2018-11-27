from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm
from openerp import SUPERUSER_ID

class dym_report_kartu_stock_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_kartu_stock_print, self).__init__(cr, uid, name, context=context)
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
        branch_id = data['branch_id']
        product_id = data['product_id']
        lot_id = data['lot_id']
        kode_produk = ''
        deskripsi = ''
        warna = ''
        if product_id:
            product = self.pool.get('product.product').browse(cr, SUPERUSER_ID, product_id[0])
            kode_produk = product.product_tmpl_id.name
            deskripsi = product.product_tmpl_id.description or product.default_code
            warna = self.pool.get('dym.branch').get_attribute_name(cr, SUPERUSER_ID, [], product)
        nosin = lot_id[1] if lot_id else ''
        cabang = branch_id[1] if branch_id else ''
        title_short_prefix = ''
        
        report_kartu_stock = {
            'type': 'receivable',
            'title': '',
            'division':division,
            'title_short': title_short_prefix + '' + _('Laporan Kartu Stock')}
        where_division = where_division2 = " 1=1 "
        if division:
            where_division = " spick.division = '%s'" % str(division)
            where_division2 = " (spick.division = '%s' or spack.division = '%s')" % (str(division),str(division))
        where_picking_type_code = " 1=1 "
        where_date_start_date = where_date_start_date2 = " 1=1 "
        # if date_start_date:
        #     where_date_start_date = " date(spick.date) >= '%s'" % str(date_start_date)
        #     where_date_start_date2 = " date(spl.date) >= '%s'" % str(date_start_date)
        where_state = where_state2 = " 1=1 "
        where_state = " spack.state = 'posted' "
        where_state2 = " spl.state = 'done' "
        where_date_end_date = where_date_end_date2 = " 1=1 "
        if date_end_date:
            where_date_end_date = " date(spick.date) <= '%s'" % str(date_end_date)
            where_date_end_date2 = " date(spl.date) <= '%s'" % str(date_end_date)
        where_min_date_start_date = where_min_date_start_date2 = " 1=1 "
        where_min_date_end_date = where_min_date_end_date2 = " 1=1 "
        where_date_done_start_date = where_date_done_start_date2 = " 1=1 "
        where_date_done_end_date = where_date_done_end_date2 = " 1=1 "
        where_branch_ids = where_branch_ids2 = " 1=1 "
        if branch_id and division == 'Sparepart':
            where_branch_ids = " spick.branch_id = %s" % branch_id[0]
            where_branch_ids2 = " (spl.branch_id = %s or spack.branch_id = %s or spick.branch_id = %s)" % (branch_id[0],branch_id[0],branch_id[0])
        where_product_ids = " 1=1 "
        if product_id :
            where_product_ids = " product.id = %s " % product_id[0]
        where_partner_ids = where_partner_ids2 = " 1=1 "
        if lot_id :
            where_partner_ids = " spl.serial_number_id = %s" % lot_id[0]
            where_partner_ids2 = " lot.id = %s" % lot_id[0]
        where_categ_ids = " 1=1 "

        query_kartu_stock = "SELECT CONCAT(cast(spl.id as text),'-dym_stock_packing_line') as id_ai, spick.id as id_picking, 'pack' as object, spl.id as pack_line_id, prod_tmpl.categ_id as categ_id, " \
            "b.code as branch_code, b.name as branch_name, spick.division, spt.name as picking_type_name, spack.name as packing_name, spack.date as packing_date, " \
            "partner.default_code as partner_code, partner.name as partner_name, expedisi.default_code as ekspedisi_code, expedisi.name as ekspedisi_name, " \
            "product.name_template as prod_tmpl, pav.code as color, spl.engine_number as engine, spl.chassis_number as chassis, " \
            "spl.tahun_pembuatan as tahun, " \
            "CASE WHEN source_sloc.usage not in ('internal','kpb','nrfs') and sloc.usage in ('internal','kpb','nrfs') THEN spl.quantity " \
            "    ELSE 0 " \
            "END as qty, " \
            "CASE WHEN source_sloc.usage in ('internal','kpb','nrfs') and sloc.usage not in ('internal','kpb','nrfs') THEN spl.quantity " \
            "    ELSE 0 " \
            "END as qty_out, " \
            "spack.state as packing_state, spick.origin as picking_origin, prod_categ.name as categ_name, prod_tmpl.name as internal_ref, " \
            "COALESCE(spick2.origin,'') as backorder, sloc.name as location, case when spl.ready_for_sale = true then 'RFS' else 'NRFS' end as status_rfs, COALESCE(bs.name, '') as branch_source, parent_sloc.name as parent_location, source_sloc.name as location_source, parent_source_sloc.name as parent_location_source " \
            "FROM " \
            "dym_stock_packing spack " \
            "inner join dym_stock_packing_line spl ON spack.id = spl.packing_id " \
            "left join stock_picking spick ON spick.id = spack.picking_id " \
            "left join stock_picking spick2 ON spick2.id = spick.backorder_id " \
            "left join dym_branch b on b.id = spick.branch_id " \
            "left join res_partner partner on partner.id = spick.partner_id " \
            "left join res_partner expedisi on expedisi.id = spack.expedition_id " \
            "left join product_product product on product.id = spl.product_id " \
            "left join product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id " \
            "left join product_attribute_value pav ON pavpp.att_id = pav.id " \
            "left join stock_picking_type spt ON spt.id = spick.picking_type_id " \
            "left join product_template prod_tmpl ON prod_tmpl.id = product.product_tmpl_id " \
            "left join product_category prod_categ ON prod_categ.id = prod_tmpl.categ_id " \
            "left join stock_location sloc ON sloc.id = spl.destination_location_id " \
            "left join stock_location parent_sloc ON parent_sloc.id = sloc.location_id " \
            "left join stock_location source_sloc ON source_sloc.id = spl.source_location_id " \
            "left join stock_location parent_source_sloc ON parent_source_sloc.id = source_sloc.location_id " \
            "left join dym_branch bs ON spack.branch_sender_id = bs.id " \
            "where ((spl.engine_number is not null and spick.division = 'Unit') or spick.division != 'Unit') and spl.quantity > 0 and " + where_state + " AND " + where_division + " AND " + where_picking_type_code + " AND " + where_date_start_date + " AND " + where_date_end_date + " AND " + where_min_date_start_date + " AND " + where_min_date_end_date + " AND " + where_date_done_start_date + " AND " + where_date_done_end_date + " AND " + where_branch_ids + " AND " + where_categ_ids + " AND " + where_product_ids + " AND " + where_partner_ids + " " \
            " UNION ALL " \
            "SELECT CONCAT(cast(spl.id as text),'-stock_move') as id_ai, spick.id as id_picking, 'move' as object, spl.id as pack_line_id, prod_tmpl.categ_id as categ_id, " \
            "b.code as branch_code, b.name as branch_name, " \
            "CASE WHEN spack.id is not null THEN spack.division " \
            "    WHEN spick.id is not null THEN spick.division " \
            "    ELSE '' " \
            "END as division, " \
            "CASE WHEN spack.id is not null and sloc.usage = 'inventory' THEN 'Delivery Orders' " \
            "    WHEN spack.id is not null and source_sloc.usage = 'inventory' THEN 'Receipts' " \
            "    ELSE spt.name " \
            "END as picking_type_name, " \
            "CASE WHEN spack.id is not null THEN spack.name " \
            "    WHEN spick.id is not null THEN spick.name " \
            "    ELSE '' " \
            "END as packing_name, " \
            "date(spl.date) as packing_date, " \
            "partner.default_code as partner_code, partner.name as partner_name, '' as ekspedisi_code, '' as ekspedisi_name, " \
            "product.name_template as prod_tmpl, pav.code as color, lot.name as engine, CONCAT(lot.chassis_code, lot.chassis_no) as chassis, " \
            "lot.tahun as tahun,  " \
            "CASE WHEN source_sloc.usage not in ('internal','kpb','nrfs') and sloc.usage in ('internal','kpb','nrfs') THEN spl.product_uom_qty " \
            "    ELSE 0 " \
            "END as qty, " \
            "CASE WHEN source_sloc.usage in ('internal','kpb','nrfs') and sloc.usage not in ('internal','kpb','nrfs') THEN spl.product_uom_qty " \
            "    ELSE 0 " \
            "END as qty_out, " \
            "CASE WHEN spack.id is not null THEN spack.state " \
            "    WHEN spick.id is not null THEN spick.state " \
            "    ELSE '' " \
            "END as packing_state, " \
            "spick.origin as picking_origin, prod_categ.name as categ_name, product.default_code as internal_ref, " \
            "COALESCE(spick2.origin,'') as backorder, sloc.name as location, case when sloc.usage = 'internal' then 'RFS' when sloc.usage in ('kpb','nrfs') then 'NRFS' else '' end as status_rfs, '' as branch_source, parent_sloc.name as parent_location, source_sloc.name as location_source, parent_source_sloc.name as parent_location_source " \
            "FROM " \
            "stock_move spl " \
            "left join stock_inventory spack ON spack.id = spl.inventory_id " \
            "left join stock_production_lot lot ON lot.id = spl.restrict_lot_id " \
            "left join stock_picking spick ON spick.id = spl.picking_id " \
            "left join stock_picking spick2 ON spick2.id = spick.backorder_id " \
            "left join dym_branch b on b.id = spl.branch_id " \
            "left join res_partner partner on partner.id = spick.partner_id " \
            "left join dym_stock_packing packing on spick.id = packing.picking_id " \
            "left join product_product product on product.id = spl.product_id " \
            "left join product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id " \
            "left join product_attribute_value pav ON pavpp.att_id = pav.id " \
            "left join stock_picking_type spt ON spt.id = spl.picking_type_id " \
            "left join product_template prod_tmpl ON prod_tmpl.id = product.product_tmpl_id " \
            "left join product_category prod_categ ON prod_categ.id = prod_tmpl.categ_id " \
            "left join stock_location sloc ON sloc.id = spl.location_dest_id " \
            "left join stock_location parent_sloc ON parent_sloc.id = sloc.location_id " \
            "left join stock_location source_sloc ON source_sloc.id = spl.location_id " \
            "left join stock_location parent_source_sloc ON parent_source_sloc.id = source_sloc.location_id " \
            "where ((lot.id is not null and (spack.division = 'Unit' or spick.division = 'Unit')) or (spack.division != 'Unit' or spick.division != 'Unit')) and spl.product_uom_qty > 0 and " + where_state2 + " AND " + where_division2 + " AND " + where_picking_type_code + " AND " + where_date_start_date2 + " AND " + where_date_end_date2 + " AND " + where_min_date_start_date2 + " AND " + where_min_date_end_date2 + " AND " + where_date_done_start_date2 + " AND " + where_date_done_end_date2 + " AND " + where_branch_ids2 + " AND " + where_categ_ids + " AND " + where_product_ids + " AND " + where_partner_ids2 + " and packing.id is null " \
            " ORDER BY packing_date asc " \
        
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        reports = [report_kartu_stock]
        
        for report in reports:
            cr.execute(query_kartu_stock)
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
                for p in p_map:
                    if p['id_ai'] not in map(
                            lambda x: x.get('id_ai', None), picking_ids):
                        packing_line = filter(
                            lambda x: x['id_ai'] == p['id_ai'], all_lines)
                        if packing_line[0]['packing_date'] < str(date_start_date) and date_start_date:
                            stock_awal += packing_line[0]['qty']
                            stock_awal -= packing_line[0]['qty_out']
                        else:
                            total_stock += packing_line[0]['qty']
                            total_stock -= packing_line[0]['qty_out']
                            p.update({'lines': packing_line})
                            picking_ids.append(p)
                stock_akhir = stock_awal + total_stock
                report.update({'kode_produk': kode_produk})
                report.update({'deskripsi': deskripsi})
                report.update({'warna': warna})
                report.update({'nosin': nosin})
                report.update({'cabang': cabang})
                report.update({'stock_awal': stock_awal})
                report.update({'stock_akhir': stock_akhir})
                report.update({'picking_ids': picking_ids})

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
                        'qty_out': 0,
                        'packing_state': 'NO DATA FOUND',
                        'picking_origin': 'NO DATA FOUND',
                        'backorder': 'NO DATA FOUND',}], 'title_short': 'Laporan Kartu Stock', 'type': 'receivable', 'title': '', 'division':division, 'stock_awal': 0, 'stock_akhir': 0, 'kode_produk': kode_produk, 'deskripsi': deskripsi, 'warna': warna, 'nosin': nosin, 'cabang': cabang}]
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_kartu_stock_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_kartu_stock_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_kartu_stock.report_kartu_stock'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_kartu_stock.report_kartu_stock'
    _wrapped_report_class = dym_report_kartu_stock_print
