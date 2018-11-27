from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_jualbysalesman_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_jualbysalesman_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def format_tanggal(self, tanggal):            
        return datetime.strptime(str(tanggal),'%Y-%m-%d').strftime('%d-%m-%Y')

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        
        query_jualbysalesman = """
            select dsol.id dsol_id,
            b.name cabang,
            hr.name_related member,
            hrjob.name jobid,
            hrsls.name_related leader,
            case
            when hrjob.name='SALES TEAM TRAINEE' then hrsls.name_related
            else hr.name_related
            end as salesman,
            dso.name faktur, 
            date_order date, 
            ai.number invoice_no,
            case
            when ai.date_invoice is null then ai.create_date::timestamp::date
            else ai.date_invoice::timestamp::date
            end as invoice_date,
            upper(r.name) customer, 
            pp.name_template motor, 
            lot.name no_mesin, 
            dsol.price_unit harga_unit,
            dsol.discount_po disc_konsumen,
            amount_hutang_komisi broker,
            COALESCE(finco.name,'Cash') as finco_code, 
            dcp_finco.name as finco_branch,
            COALESCE(dsol.product_qty,0) as product_qty, 
            employee_spv.name_related as spv_name,
	    CASE WHEN dso.is_cod = TRUE THEN 'COD' 
		else case when dso.is_pic = 't' then 'PIC'
	    ELSE 'Reguler' END END as is_cod, 
            dso.amount_total total
            from dealer_sale_order dso
            left join dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id = dso.id
            left join hr_employee hr on hr.id = dso.employee_id
            left join res_partner r on r.id = dso.partner_id
            left join res_partner finco ON dso.finco_id = finco.id 
            left join dym_cabang_partner dcp_finco ON dcp_finco.id = dso.finco_cabang 
            left join crm_case_section crm ON dso.section_id = crm.id 
            left join hr_employee employee_koord ON employee_koord.id = crm.employee_id
            left join crm_case_section crm_spv ON crm.parent_id = crm_spv.id 
            left join hr_employee employee_spv ON employee_spv.id = crm_spv.employee_id 
            left join product_product pp on pp.id = dsol.product_id
            left join stock_production_lot lot on lot.id = dsol.lot_id
            left join dym_branch b on b.id = dso.branch_id
            left join sale_member_empl_rel rel on rel.member_id=hr.id
            left join crm_case_section sls on sls.id=rel.section_id
            left join hr_job hrjob on hr.job_id=hrjob.id
            left join hr_employee hrsls on hrsls.id=sls.employee_id
            left join account_invoice ai on ai.origin=dso.name
        """

        query_where = " where dso.state in ('progress','done') and ai.number like 'NDE-%' "
        if data['start_date']:
            query_where += " and dso.date_order >= '%s'" % str(data['start_date'])
        if data['end_date']:
            query_where += " and dso.date_order <= '%s'" % str(data['end_date'])
        if data['branch_ids']:
            query_where += " and dso.branch_id in %s" % str(tuple(data['branch_ids'])).replace(',)', ')')

        order_by = " order by b.name asc, salesman asc"

        self.cr.execute(query_jualbysalesman + query_where + order_by)
        all_lines = self.cr.dictfetchall()

        if all_lines :
            datas = map(lambda x : {
                'no': 0,
                'dsol_id': x['dsol_id'],
                'cabang':x['cabang'],
                'salesman':x['salesman'],
                'faktur':x['faktur'],
                'date':self.format_tanggal(x['date']),
                'customer':x['customer'],
                'motor':x['motor'],
                'no_mesin':x['no_mesin'],
                'harga_unit':x['harga_unit'],
                'disc_konsumen':x['disc_konsumen'],
                'finco_code':x['finco_code'],
                'finco_branch':x['finco_branch'],
                'product_qty':x['product_qty'],
                'spv_name':x['spv_name'],
                'disc_intern':0,
                'disc_extern':0,
                'broker':x['broker'],
                'total':x['total'],
                'ar_days':0,
                'lunas':'',
                'is_cod':x['is_cod'],
                'invoice_no': x['invoice_no'],
                'invoice_date': self.format_tanggal(x['invoice_date']) if x['invoice_date'] != None else x['invoice_date']
                }, all_lines)
            
            
            for data in datas:

                now = datetime.now()
                date_today = now.strftime("%d-%m-%Y")
                
                # Diskon Intern Extern
                dsol = self.pool.get('dealer.sale.order.line').browse(cr, uid, data['dsol_id'])
                for diskon in dsol.discount_line:
                    disc_extern_all = diskon.ps_ahm_copy + diskon.ps_md_copy + diskon.ps_finco_copy + diskon.ps_others_copy
                    if diskon.discount_pelanggan - disc_extern_all <= 0:
                        data['disc_extern'] = data['disc_extern'] + diskon.discount_pelanggan
                        data['disc_intern'] = 0
                    else:
                        data['disc_extern'] = data['disc_extern'] + disc_extern_all
                        data['disc_intern'] = data['disc_intern'] + (diskon.discount_pelanggan - disc_extern_all)
                                    
                # AR Days
                invoice_ids = self.pool.get('account.invoice').search(cr, uid,[('origin','=',data['faktur'])])
                invoice = self.pool.get('account.invoice').browse(cr, uid, invoice_ids[0])
                payment_dates = []
                if invoice.payment_ids:
                    for payment in invoice.payment_ids:
                        payment_dates.append(payment.date)
                    order_date = datetime.strptime(dsol.dealer_sale_order_line_id.date_order, '%Y-%m-%d')
                    payment_date = datetime.strptime(max(payment_dates), '%Y-%m-%d')
                    # data['ar_days'] = abs((payment_date-order_date).days) + 1
                    
                    if invoice.state == 'paid':
                        # Lunas
                        data['lunas'] = self.format_tanggal(max(payment_dates))
                        # data['ar_days'] = abs((payment_date-order_date).days) + 1
                        data['ar_days'] = abs((payment_date-datetime.strptime(data['invoice_date'],'%d-%m-%Y')).days) + 1
                    else:
                        data['lunas'] = None
                        data['ar_days'] = abs((datetime.strptime(date_today,'%d-%m-%Y')-datetime.strptime(data['invoice_date'],'%d-%m-%Y')).days) + 1
                else:
                    data['ar_days'] = abs((datetime.strptime(date_today,'%d-%m-%Y')-datetime.strptime(data['invoice_date'],'%d-%m-%Y')).days) + 1
                
                # # Lunas
                # if payment_dates:
                #     data['lunas'] = self.format_tanggal(max(payment_dates))

            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            raise osv.except_osv(('Warning'), ('Data Report Tidak Ditemukan!'))
        
        self.localcontext.update({'reports': reports})
        super(dym_report_jualbysalesman_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_jualbysalesman_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_jualbysalesman.report_jualbysalesman'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_jualbysalesman.report_jualbysalesman'
    _wrapped_report_class = dym_report_jualbysalesman_print
    