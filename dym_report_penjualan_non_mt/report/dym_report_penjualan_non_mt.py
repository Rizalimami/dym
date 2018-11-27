from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_penjualan_non_mt_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_penjualan_non_mt_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        
        branch_ids = data['branch_ids']
        start_date = data['start_date']
        end_date = data['end_date']

        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " b.id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " dsm.date_order >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " dsm.date_order <= '%s'" % str(end_date)

        
        query_penjualan_non_mt = """
            select dsml.id as dsml_id,
                b.name as cabang,
                dsm.name as faktur,
                dsm.date_order as date,
                cust.name as customer,
                p.name_template as motor,
                spl.name as no_mesin,
                sls.name as salesman,
                dsm.division as division,
                dsml.discount_po as disc_konsumen,
                dsml.amount_hutang_komisi as broker,
                dsm.amount_total as total,
                date(aml.date) - date(dsm.date_order) as ar_days,
                aml.date as lunas
                from dealer_sale_order dsm
                left join dym_branch b on dsm.branch_id = b.id
                left join res_partner cust on dsm.partner_id = cust.id
                left join dealer_sale_order_line dsml on dsm.id = dsml.dealer_sale_order_line_id
                left join product_product p on p.id = dsml.product_id
                left join product_template pt on pt.id = p.product_tmpl_id
                left join stock_production_lot spl ON spl.id = dsml.lot_id
                left join hr_employee empl ON empl.id = dsm.employee_id
                left join res_partner sls ON sls.id = empl.partner_id
                left join account_move_line aml on aml.ref = dsm.name
        """
        query_where = "WHERE sls.default_code not like 'MT-%' AND " + where_start_date + " AND " + where_end_date + " AND " + where_branch_ids
        sql_query = query_penjualan_non_mt + query_where
        self.cr.execute(sql_query)
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                'no': 0,
                'dsml_id': x['dsml_id'],
                'cabang': str(x['cabang'].encode('ascii','ignore').decode('ascii')) if x['cabang'] != None else '',
                'faktur': str(x['faktur'].encode('ascii','ignore').decode('ascii')) if x['faktur'] != None else '',
                'date': str(x['date'].encode('ascii','ignore').decode('ascii')) if x['date'] != None else '',
                'customer': str(x['customer'].encode('ascii','ignore').decode('ascii')) if x['customer'] != None else '',
                'motor': str(x['motor'].encode('ascii','ignore').decode('ascii')) if x['motor'] != None else '',
                'no_mesin': str(x['no_mesin'].encode('ascii','ignore').decode('ascii')) if x['no_mesin'] != None else '',
                'salesman': str(x['salesman'].encode('ascii','ignore').decode('ascii')) if x['salesman'] != None else '',
                'division': str(x['division'].encode('ascii','ignore').decode('ascii')) if x['division'] != None else '',
                'disc_konsumen': x['disc_konsumen'] if x['disc_konsumen'] > 0 else 0.0,
                'disc_intern': 0,
                'disc_extern': 0,
                'broker': x['broker'] if x['broker'] > 0 else 0.0,
                'total': x['total'] if x['total'] > 0 else 0.0,
                'ar_days': x['ar_days'] if x['ar_days'] > 0 else 0,
                'lunas': str(x['lunas'].encode('ascii','ignore').decode('ascii')) if x['lunas'] != None else '',
                }, all_lines)

            for data in datas:

                dsml = self.pool.get('dealer.sale.order.line').browse(cr, uid, data['dsml_id'])
                for diskon in dsml.discount_line:
                    if diskon.discount_pelanggan - diskon.ps_dealer_copy == 0:
                        data['disc_intern'] = data['disc_intern'] + diskon.ps_dealer_copy
                    elif diskon.discount_pelanggan - diskon.ps_dealer_copy > 0:
                        data['disc_intern'] = data['disc_intern'] + diskon.ps_dealer_copy
                        data['disc_extern'] = data['disc_extern'] + (diskon.discount_pelanggan - diskon.ps_dealer_copy)
                    elif diskon.discount_pelanggan - diskon.ps_dealer_copy < 0:
                        data['disc_extern'] = data['disc_extern'] + diskon.discount_pelanggan

            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            reports = [{'datas': [{
                'no': 'NO DATA FOUND',
                'cabang': 'NO DATA FOUND',
                'faktur': 'NO DATA FOUND',
                'date': 'NO DATA FOUND',
                'customer': 'NO DATA FOUND',
                'motor': 'NO DATA FOUND',
                'no_mesin': 'NO DATA FOUND',
                'division': 'NO DATA FOUND',
                'salesman': 'NO DATA FOUND',
                'disc_konsumen': 0,
                'disc_intern': 0,
                'disc_extern': 0,
                'broker': 0,
                'total': 0,
                'ar_days': 0,
                'lunas': 'Belum Lunas',
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(dym_report_penjualan_non_mt_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_penjualan_non_mt_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_penjualan_non_mt.report_penjualan_non_mt'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_penjualan_non_mt.report_penjualan_non_mt'
    _wrapped_report_class = dym_report_penjualan_non_mt_print
    