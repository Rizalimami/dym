from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_rjualbymt_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_rjualbymt_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']

        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " dso.date_order >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " dso.date_order <= '%s'" % str(end_date)
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " dso.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        
        query_rjualbymt = """
            select  dsol.id dsol_id,
                    b.name cabang,
                    case when hrjob.name='SALES TEAM TRAINEE' then hr.name_related
                        else 'NON MARKETING TRAINEE'
                    end as mt,
                    dso.name faktur, 
                    date_order date, 
                    COALESCE(ai.number,'') invoice_no, 
                    case when ai.date_invoice is null then ai.create_date::timestamp::date
                        else ai.date_invoice::timestamp::date
                    end as invoice_date,
                    COALESCE(finco.name,'Cash') as finco_code, 
                    COALESCE(finco.name,'Cash') as finco_code, 
                    dcp_finco.name as finco_branch,
                    CASE WHEN dso.is_cod = TRUE THEN 'COD' 
                        else case when dso.is_pic = 't' then 'PIC'
                    ELSE 'Reguler' END END as is_cod, 
                    upper(r.name) customer, 
                    pp.name_template motor, 
                    lot.name no_mesin, 
                    employee_koord.name_related as leader,
                    employee_spv.name_related as spv_name,
                    COALESCE(dsol.product_qty,0) as product_qty, 
                    dsol.price_unit harga_unit,
                    dsol.discount_po disc_konsumen,
                    disc_ext_int.disc_intern disc_intern,
                    disc_ext_int.disc_extern disc_extern, 
                    amount_hutang_komisi broker,
                    dso.amount_total total,
                    case when ar_days.date_cpa is not null then (ar_days.date_cpa::date - ai.date_invoice::date) + 1 else (now()::date - ai.date_invoice::date) + 1 end ar_days,
                    case when ar_days.date_cpa is not null then ar_days.date_cpa else null end lunas
                    

                    --hr.name_related member,
                    --hrjob.name jobid
                    --case when hrsls.name_related is null then hr.name_related else hrsls.name_related end as leader,
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
                --left join sale_member_empl_rel rel on rel.member_id=hr.id
                --left join crm_case_section sls on sls.id=rel.section_id
                left join hr_job hrjob on hr.job_id=hrjob.id
                --left join hr_employee hrsls on hrsls.id=sls.employee_id
                left join account_invoice ai on ai.origin = dso.name and left(ai.number,3) in ('NDE')
                /*left join (   select  b.dsoldli as "dsol_id",
                            sum(b.disc_extern) as "disc_extern",
                            sum(b.disc_intern) as "disc_intern"
                        From    (select a.dsoldli,
                            case when a.check_disc <= 0 then a.disc_extern_all
                            else a.disc_extern_all end as "disc_extern",
                            case when a.check_disc <= 0 then 0
                            else a.check_disc end as "disc_intern"
                            from    (select dealer_sale_order_line_discount_line_id as dsoldli, 
                                    ps_finco as ps_finco, 
                                    ps_ahm as ps_ahm, 
                                    ps_md as ps_md, 
                                    ps_dealer as ps_dealer, 
                                    ps_others as ps_others, 
                                    discount as discount, 
                                    discount_pelanggan as discount_pelanggan,
                                    ps_ahm + ps_md + ps_finco + ps_others as disc_extern_all,
                                    discount_pelanggan - (ps_ahm + ps_md + ps_finco + ps_others) as check_disc
                                from    dealer_sale_order_line_discount_line
                                where   dealer_sale_order_line_discount_line_id in (40266,38921)
                                 )a )b
                        where b.dsoldli in (40266,38921)
                        group by b.dsoldli) disc_ext_int on disc_ext_int.dsol_id = dsol.id*/
                left join (select   c.dsol_id as "dsol_id",
                            sum(c.disc_extern) as "disc_extern",
                            sum(c.disc_intern) as "disc_intern"
                        from    (select b.dsoldli as "dsol_id",
                            case when b.discount_pelanggan - (b.disc_extern + b.disc_intern) != 0 then sum(b.discount_pelanggan) 
                                else sum(b.disc_extern) end as "disc_extern",
                            sum(b.disc_intern) as "disc_intern"
                        From    (select a.dsoldli,
                            a.discount_pelanggan,
                            case when a.check_disc <= 0 then a.disc_extern_all
                            else a.disc_extern_all end as "disc_extern",
                            case when a.check_disc <= 0 then 0
                            else a.check_disc end as "disc_intern"
                            from    (select dealer_sale_order_line_discount_line_id as dsoldli, 
                                    ps_finco as ps_finco, 
                                    ps_ahm as ps_ahm, 
                                    ps_md as ps_md, 
                                    ps_dealer as ps_dealer, 
                                    ps_others as ps_others, 
                                    discount as discount, 
                                    discount_pelanggan as discount_pelanggan,
                                    ps_ahm + ps_md + ps_finco + ps_others as disc_extern_all,
                                    discount_pelanggan - (ps_ahm + ps_md + ps_finco + ps_others) as check_disc
                                from    dealer_sale_order_line_discount_line
                                 )a )b
                        group by b.dsoldli, b.discount_pelanggan, b.disc_extern, b.disc_intern) c
                        group by c.dsol_id ) disc_ext_int on disc_ext_int.dsol_id = dsol.id
                left join ( select  am.name as nde, 
                            aml.name as dsm, 
                            max(am_cpa.date) as date_cpa, 
                            sum(aml_cpa.credit) as credit_cpa, 
                            dso.amount_total as total_dsm,
                            sum(aml_cpa.credit) - dso.amount_total as selisih
                    from    account_move am
                    left join account_move_line aml on aml.move_id = am.id
                    left join account_move_line aml_cpa on aml_cpa.reconcile_id = aml.reconcile_id
                    left join account_move am_cpa on aml_cpa.move_id = am_cpa.id
                    left join dealer_sale_order dso on dso.name = aml.name
                    where   left(am.name,5) = 'NDE-S'
                            and left(aml.name,3) = 'DSM'
                            and left(am_cpa.name,3) = 'CPA' """ \
                "and dso.state in ('progress','done') AND " + where_start_date + " AND " + where_end_date + " AND " + where_branch_ids + " " \
        """
                    group by am.name, aml.name, dso.amount_total ) ar_days on ar_days.dsm = dso.name
        """

        query_where = " WHERE dso.state in ('progress','done') "
        if data['start_date']:
            query_where += " and dso.date_order >= '%s'" % str(data['start_date'])
        if data['end_date']:
            query_where += " and dso.date_order <= '%s'" % str(data['end_date'])
        if data['branch_ids']:
            query_where += " and dso.branch_id in %s" % str(tuple(data['branch_ids'])).replace(',)', ')')
        # query_group = """   group by dso.id, drsl.name, dsol.price_subtotal, dsol.price_bbn, b.branch_status, b.code, spk.name, dcp.name, b.name, md.default_code, finco.name, employee_koord.name_related,
        #                     res_res.name, job.name, cust.default_code, cust.name, cust_stnk.name, cust.npwp, product.name_template, pav.code, dsol.product_qty, lot.name, lot.chassis_no, dsol.price_unit,
        #                     dsol.discount_po, dsol_disc.ps_dealer, dsol_disc.ps_ahm, dsol_disc.ps_md, dsol_disc.ps_finco, dsol_disc_yes.discount_pelanggan, dsol_disc_not.discount_pelanggan, dsol_disc.discount_pelanggan,
        #                     dsol.force_cogs, dsol.price_bbn_beli, dsol.amount_hutang_komisi, dsol.insentif_finco, prod_category.name, prod_category2.name, prod_template.series, fp.name, hk.name, pro.number, pro.name, 
        #                     sp.state, sp.name, cust.mobile, cust_stnk.mobile, dsol.finco_no_po, dsol.finco_tgl_po,employee_spv.name_related, lot.tahun, ai.number, ai.date_invoice, ai.state, ar_days.date_cpa, av_nde.number
        #                 """
        query_order = " order by b.name asc, mt asc"

        self.cr.execute(query_rjualbymt + query_where + query_order)
        # raise osv.except_osv(('Perhatian !'), ("No \'%s\' ...")%(query_rjualbymt + query_where + query_group + query_order))
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                'no': 0,
                'dsol_id': x['dsol_id'],
                'cabang':x['cabang'],
                'mt':x['mt'],
                'faktur':x['faktur'],
                'date':x['date'],
                'customer':x['customer'],
                'motor':x['motor'],
                'no_mesin':x['no_mesin'],
                'harga_unit':x['harga_unit'],
                'disc_konsumen':x['disc_konsumen'],
                'finco_code':x['finco_code'],
                'finco_branch':x['finco_branch'],
                'product_qty':x['product_qty'],
                'spv_name':x['spv_name'],
                'disc_intern':x['disc_intern'],
                'disc_extern':x['disc_extern'],
                'broker':x['broker'],
                'is_cod':x['is_cod'],
                'total':x['total'],
                'ar_days':x['ar_days'],
                'lunas':x['lunas'],
                'leader': x['leader'],
                'invoice_no': x['invoice_no'],
                'invoice_date': x['invoice_date'],
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            reports = [{'datas': [{
                'no': 0,
                'dsol_id': 'NO DATA FOUND',
                'cabang':'NO DATA FOUND',
                'mt':'NO DATA FOUND',
                'faktur':'NO DATA FOUND',
                'date':'NO DATA FOUND',
                'customer':'NO DATA FOUND',
                'motor':'NO DATA FOUND',
                'no_mesin':'NO DATA FOUND',
                'harga_unit':0,
                'disc_konsumen':0,
                'finco_code':'NO DATA FOUND',
                'finco_branch':'NO DATA FOUND',
                'product_qty':0,
                'spv_name':'NO DATA FOUND',
                'disc_intern':0,
                'disc_extern':0,
                'broker':'NO DATA FOUND',
                'is_cod':'NO DATA FOUND',
                'total':0,
                'ar_days':0,
                'lunas':'NO DATA FOUND',
                'leader': 'NO DATA FOUND',
                'invoice_no': 'NO DATA FOUND',
                'invoice_date': 'NO DATA FOUND'
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(dym_report_rjualbymt_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_rjualbymt_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_rjualbymt.report_rjualbymt'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_rjualbymt.report_rjualbymt'
    _wrapped_report_class = dym_report_rjualbymt_print
    