from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_kinerja_so_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_kinerja_so_print, self).__init__(cr, uid, name, context=context)
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
        
        report_kinerja_so = {
            'type': '',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Kinerja Mekanik')}
        
        where_section_id = " 1=1 "
        if section_id :
            where_section_id = " ks.section_id = '%s'" % str(section_id)
        where_user_id = " 1=1 "
        if user_id :
            where_user_id = " ks.employee_id = '%s'" % str(user_id)
        where_product_ids = " 1=1 "
        if product_ids :
            where_product_ids = " ksl.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " ks.date_order >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " ks.date_order <= '%s'" % str(end_date)
        where_state = " 1=1 "
        if state in ['progress','done'] :
            where_state = " ks.state = '%s'" % str(state)
        else :
            where_state = " ks.state in ('progress','done')"
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " ks.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        query_kinerja_so = "select " \
            "COALESCE(b.branch_status,'') as branch_status, " \
            "COALESCE(b.code,'') as branch_code, " \
            "COALESCE(b.name,'') as branch_name, " \
            "ks.name as so_name, " \
            "ks.date_order as date_order, " \
            "proposal_id as proposal_id, " \
            "COALESCE(sales.name_related,'') as mekanik_id, " \
            "COALESCE(ksl.price_unit,0) as price_unit, " \
            "SUM(COALESCE(ksl.price_unit,0)*COALESCE(ksl.product_uom_qty,0)-COALESCE(ksl.discount_cash,0)-COALESCE(ksl.discount_lain,0)-COALESCE(ksl.discount_program,0)-COALESCE(ksl.discount,0)) as price_subtotal, " \
            "COALESCE(product.name_template,'') as product_name, " \
            "SUM(COALESCE(ksl.discount_program,0)) as discount_program, " \
            "SUM(COALESCE(ksl.discount_lain,0)) as discount_persen, " \
            "SUM(COALESCE(ksl.discount_cash,0)) as discount_cash, " \
            "SUM(COALESCE(ks.amount_tax,0)) as amount_tax, " \
            "SUM(COALESCE(ksl.discount,0)) as discount, " \
            "SUM(COALESCE(ksl.product_uom_qty,0)) as product_qty, " \
            "COALESCE(prod_category.name,'') as categ_name, " \
            "COALESCE(fp.name,'') as faktur_pajak " \
            "from sale_order ks " \
            "inner join sale_order_line ksl on ksl.order_id = ks.id " \
            "left join dym_branch b ON ks.branch_id = b.id " \
            "left join res_partner cust ON ks.partner_id = cust.id " \
            "left join hr_employee sales ON ks.employee_id = sales.id " \
            "left join product_product product ON ksl.product_id = product.id " \
            "left join product_template prod_template ON product.product_tmpl_id = prod_template.id " \
            "left join product_category prod_category ON prod_template.categ_id = prod_category.id " \
            "left join dym_faktur_pajak_out fp ON ks.faktur_pajak_id = fp.id " \
            "WHERE " + where_section_id + " AND " + where_user_id + " AND " + where_product_ids + " AND " + where_start_date + " AND " + where_end_date + " AND " + where_state + " AND " + where_branch_ids + " " \
            "group by ks.date_order,branch_status, b.code,mekanik_id, ks.name, b.name, sales.name_related, price_unit, ksl.id, cust.name, product.name_template, prod_category.name, fp.name, proposal_id " \
            "order by mekanik_id "
        
        move_selection = ""
        report_info = _('')
        move_selection += ""
        reports = [report_kinerja_so]
        
        for report in reports:
            cr.execute(query_kinerja_so)
            all_lines = cr.dictfetchall()
            ks_ids = []

            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': 0,
                        'branch_status': str(x['branch_status'].encode('ascii','ignore').decode('ascii')) if x['branch_status'] != None else '',
                        'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                        'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                        'so_name': str(x['so_name'].encode('ascii','ignore').decode('ascii')) if x['so_name'] != None else '',
                        'date_order': str(x['date_order']) if x['date_order'] != None else False,
                        'product_name': str(x['product_name'].encode('ascii','ignore').decode('ascii')) if x['product_name'] != None else '',
                        'product_qty': x['product_qty'],
                        'price_unit': x['price_unit'],
                        'discount': x['discount'],
                        'discount_program': x['discount_program'],
                        'discount_persen': x['discount_persen'],
                        'discount_cash': x['discount_cash'],
                        'mekanik_id': x['mekanik_id'],
                        'price_subtotal': x['price_subtotal'],
                        'amount_tax': x['amount_tax'],
                        'categ_name': str(x['categ_name'].encode('ascii','ignore').decode('ascii')) if x['categ_name'] != None else '',
                        'faktur_pajak': str(x['faktur_pajak'].encode('ascii','ignore').decode('ascii')) if x['faktur_pajak'] != None else '',
                        'proposal_id': x['proposal_id']
                    },
                    
                    all_lines)
                report.update({'ks_ids': p_map})

        reports = filter(lambda x: x.get('ks_ids'), reports)
        
        if not reports :
            reports = [{'ks_ids': [{
            'no': 'NO DATA FOUND',
            'branch_status': 'NO DATA FOUND',
            'branch_code': 'NO DATA FOUND',
            'branch_name': 'NO DATA FOUND',
            'so_name': 'NO DATA FOUND',
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
            'discount_cash': 0,
            'amount_tax':0,
            'product_qty':0,
            'price_subtotal': 0,
            'mekanik_id': 'NO DATA FOUND',
            'categ_name': 'NO DATA FOUND',
            'faktur_pajak': 'NO DATA FOUND'}], 'title_short': 'Laporan Penjualan Sparepart', 'type': '', 'title': ''}]
        
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_kinerja_so_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_kinerja_so_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_kinerja_so.report_kinerja_so'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_kinerja_so.report_kinerja_so'
    _wrapped_report_class = dym_report_kinerja_so_print
