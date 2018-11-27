from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_kinerja_wo_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_kinerja_wo_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        section_id = data['section_id']
        user_id = data['user_id']
        product_ids = data['product_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        state = data['state']
        branch_ids = data['branch_ids']

        title_short_prefix = ''
        
        report_kinerja_wo = {
            'type': '',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Kinerja Mekanik')}
        
        where_section_id = " 1=1 "
        if section_id :
            where_section_id = " kw.section_id = '%s'" % str(section_id)
        where_user_id = " 1=1 "
        if user_id :
            where_user_id = " kw.employee_id = '%s'" % str(user_id)
        where_product_ids = " 1=1 "
        if product_ids :
            where_product_ids = " kwl.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " kw.tanggal_pembelian >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " kw.tanggal_pembelian <= '%s 23:59:59'" % str(end_date)
        where_state = " 1=1 "
        if state in ['progress','done'] :
            where_state = " kw.state = '%s'" % str(state)
        else :
            where_state = " kw.state in ('progress','done')"
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " kw.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        query_kinerja_wo = "select " \
            "COALESCE(b.branch_status,'') as branch_status, " \
            "COALESCE(b.code,'') as branch_code, " \
            "COALESCE(b.name,'') as branch_name, " \
            "COALESCE(kw.name,'') as wo_name, " \
            "COALESCE(collect.name,'') as collecting_id, " \
            "kw.tanggal_pembelian as date_order, " \
            "proposal_id as proposal_id, " \
            "COALESCE(mekan.name_related,'') as mekanik_id, " \
            "COALESCE(sa.name_related,'') as sa_id, " \
            "COALESCE(kwl.price_unit,0) as price_unit, " \
            "SUM(COALESCE(kwl.supply_qty,0)) as supply_qty, " \
            "SUM(COALESCE(kwl.product_qty,0)*COALESCE(kwl.price_unit,0)-COALESCE(kwl.discount_program,0)-COALESCE(spl_db.discount_bundle,0)-COALESCE(kwl.discount,0)) as price_subtotal, " \
            "COALESCE(product.name_template,'') as product_name, " \
            "SUM(COALESCE(kwl.discount_program,0)) as discount_program, " \
            "SUM(COALESCE(spl_db.discount_bundle,0)) as discount_persen, " \
            "0 as amount_tax, " \
            "SUM(COALESCE(kwl.discount,0)) as discount, " \
            "SUM(COALESCE(kwl.product_qty,0)) as product_qty, " \
            "COALESCE(prod_category.name,'') as categ_name, " \
            "COALESCE(fp.name,'') as faktur_pajak " \
            "from dym_work_order kw " \
            "inner join dym_work_order_line kwl on kwl.work_order_id = kw.id " \
            "left join dym_branch b ON kw.branch_id = b.id " \
            "left join dym_collecting_kpb collect ON collect.id = kw.collecting_id and collect.state in ('open','done') " \
            "left join res_partner cust ON kw.customer_id = cust.id " \
            "left join hr_employee mekan ON kw.mekanik_id = mekan.id " \
            "left join hr_employee sa ON kw.sa_id = sa.id " \
            "left join product_product product ON kwl.product_id = product.id " \
            "left join product_template prod_template ON product.product_tmpl_id = prod_template.id " \
            "left join product_category prod_category ON prod_template.categ_id = prod_category.id " \
            "left join dym_faktur_pajak_out fp ON kw.faktur_pajak_id = fp.id " \
            "left join ( " \
            "select db.wo_line_id, sum(db.diskon) as discount_bundle " \
            "from dym_work_order_bundle db " \
            "group by db.wo_line_id " \
            ") spl_db ON spl_db.wo_line_id = kwl.id " \
            "WHERE " + where_section_id + " AND " + where_user_id + " AND " + where_product_ids + " AND " + where_start_date + " AND " + where_end_date + " AND " + where_state + " AND " + where_branch_ids + " AND " + "kwl.categ_id in ('Service') " \
            "group by kw.id, branch_status, b.code,mekanik_id, collect.name, b.name, kw.name, mekan.name_related, sa.name_related, price_unit, kwl.id, cust.name, product.name_template, prod_category.name, fp.name " \
            "order by mekanik_id "
        
        move_selection = ""
        report_info = _('')
        move_selection += ""
        reports = [report_kinerja_wo]
        
        for report in reports:
            cr.execute(query_kinerja_wo)
            all_lines = cr.dictfetchall()
            kw_ids = []

            if all_lines:

                p_map = map(
                    lambda x: {
                        'no': 0,
                        'branch_status': str(x['branch_status'].encode('ascii','ignore').decode('ascii')) if x['branch_status'] != None else '',
                        'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                        'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                        'collecting_id': str(x['collecting_id'].encode('ascii','ignore').decode('ascii')) if x['collecting_id'] != None else '',
                        'sa_id': str(x['sa_id'].encode('ascii','ignore').decode('ascii')) if x['sa_id'] != None else '',
                        'wo_name': str(x['wo_name'].encode('ascii','ignore').decode('ascii')) if x['wo_name'] != None else '',
                        'date_order': str(x['date_order']) if x['date_order'] != None else False,
                        'product_name': str(x['product_name'].encode('ascii','ignore').decode('ascii')) if x['product_name'] != None else '',
                        'product_qty': x['product_qty'],
                        'supply_qty':x['supply_qty'],
                        'price_unit': x['price_unit'],
                        'discount': x['discount'],
                        'discount_program': x['discount_program'],
                        'discount_persen': x['discount_persen'],
                        'mekanik_id': x['mekanik_id'],
                          'price_subtotal': x['price_subtotal'],
                         'amount_tax': x['amount_tax'],
                        'categ_name': str(x['categ_name'].encode('ascii','ignore').decode('ascii')) if x['categ_name'] != None else '',
                        'faktur_pajak': str(x['faktur_pajak'].encode('ascii','ignore').decode('ascii')) if x['faktur_pajak'] != None else '',
                        'proposal_id': x['proposal_id']
                    },
                    
                    all_lines)
                report.update({'kw_ids': p_map})

        reports = filter(lambda x: x.get('kw_ids'), reports)
        
        if not reports :
            reports = [{'kw_ids': [{
            'no': 'NO DATA FOUND',
            'branch_status': 'NO DATA FOUND',
            'branch_code': 'NO DATA FOUND',
            'branch_name': 'NO DATA FOUND',
            'wo_name': 'NO DATA FOUND',
            'sa_id': 'NO DATA FOUND',
            'collecting_id': 'NO DATA FOUND',
            'analytic_1': 'NO DATA FOUND',
            'analytic_2': 'NO DATA FOUND',
            'analytic_3': 'NO DATA FOUND',
            'analytic_4': 'NO DATA FOUND',
            'analytic_combination': 'NO DATA FOUND',
            'name': 'NO DATA FOUND',
            'state': 'NO DATA FOUND',
            'date_order': 'NO DATA FOUND',
            'product_name': 'NO DATA FOUND',
            'price_unit': 0,
            'discount': 0,
            'discount_program': 0,
            'discount_persen': 0,
            'product_qty':0,
            'amount_tax':0,
            'price_subtotal': 0,
            'categ_name': 'NO DATA FOUND',
            'mekanik_id': 'NO DATA FOUND',
            'faktur_pajak': 'NO DATA FOUND'}], 'title_short': 'Laporan Penjualan Sparepart', 'type': '', 'title': ''}]
        
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_kinerja_wo_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_kinerja_wo_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_kinerja_wo.report_kinerja_wo'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_kinerja_wo.report_kinerja_wo'
    _wrapped_report_class = dym_report_kinerja_wo_print
