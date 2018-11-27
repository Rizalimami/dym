from datetime import datetime, date
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_penjualansum_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_penjualansum_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        branch_status = data['branch_status']

        # title_short_prefix = ''

        # report_penjualansum = {
        #     'type': '',
        #     'title': '',
        #     'title_short': title_short_prefix + ', ' + _('Laporan Penjualan Sum')}
        
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " dso.date_order >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " dso.date_order <= '%s'" % str(end_date)
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " dso.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        
        query_penjualansum = """select  
                b.branch_code as branch_code, 
                b.branch_status as branch_status, 
                b.branch_name as branch_name, 
                sum(b.cash) - sum(b.retur_cash) - sum(b.jual_pic) as cash, 
                --sum(b.cash) - sum(b.jual_pic) as cash, 
                sum(b.retur_cash) as retur_cash, 
                sum(b.cash) - sum(b.jual_pic) - sum(b.retur_cash) - sum(b.retur_cash) as net_cash, 
                --sum(b.cash) - sum(b.jual_pic) - sum(b.retur_cash) as net_cash, 
                sum(b.adira) - sum(b.retur_adira) as adira,
                sum(b.retur_adira) as retur_adira,
                sum(b.adira) - sum(b.retur_adira) - sum(b.retur_adira) as net_adira,
                sum(b.astra_buana) - sum(b.retur_astra_buana) as astra_buana,
                sum(b.retur_astra_buana) as retur_astra_buana,
                sum(b.astra_buana) - sum(b.retur_astra_buana) - sum(b.retur_astra_buana) as net_astra_buana,
                sum(b.csf) - sum(b.retur_csf) as csf,
                sum(b.retur_csf) as retur_csf,
                sum(b.csf) - sum(b.retur_csf) - sum(b.retur_csf) as net_csf,
                sum(b.fif) - sum(b.retur_fif) as fif,
                sum(b.retur_fif) as retur_fif,
                sum(b.fif) - sum(b.retur_fif) - sum(b.retur_fif) as net_fif,
                sum(b.ifi) - sum(b.retur_ifi) as ifi,
                sum(b.retur_ifi) as retur_ifi,
                sum(b.ifi) - sum(b.retur_ifi) - sum(b.retur_ifi) as net_ifi,
                sum(b.mandala) - sum(b.retur_mandala) as mandala,
                sum(b.retur_mandala) as retur_mandala,
                sum(b.mandala) - sum(b.retur_mandala) - sum(b.retur_mandala) as net_mandala,
                sum(b.mandiri_tunas) - sum(b.retur_mandiri_tunas) as mandiri_tunas,
                sum(b.retur_mandiri_tunas) as retur_mandiri_tunas,
                sum(b.mandiri_tunas) - sum(b.retur_mandiri_tunas) - sum(b.retur_mandiri_tunas) as net_mandiri_tunas,
                sum(b.mandiri_utama) - sum(b.retur_mandiri_utama) as mandiri_utama,
                sum(b.retur_mandiri_utama) as retur_mandiri_utama,
                sum(b.mandiri_utama) - sum(b.retur_mandiri_utama) - sum(b.retur_mandiri_utama) as net_mandiri_utama,
                sum(b.mcf) - sum(b.retur_mcf) as mcf,
                sum(b.retur_mcf) as retur_mcf,
                sum(b.mcf) - sum(b.retur_mcf) - sum(b.retur_mcf) as net_mcf,
                sum(b.mpmf) - sum(b.retur_mpmf) as mpmf,
                sum(b.retur_mpmf) as retur_mpmf,
                sum(b.mpmf) - sum(b.retur_mpmf) - sum(b.retur_mpmf) as net_mpmf,
                sum(b.rbf) - sum(b.retur_rbf) as rbf,
                sum(b.retur_rbf) as retur_rbf,
                sum(b.rbf) - sum(b.retur_rbf) - sum(b.retur_rbf) as net_rbf,
                sum(b.sof) - sum(b.retur_sof) as sof,
                sum(b.retur_sof) as retur_sof,
                sum(b.sof) - sum(b.retur_sof) - sum(b.retur_sof) as net_sof,
                sum(b.wom) - sum(b.retur_wom) as wom,
                sum(b.retur_wom) as retur_wom,
                sum(b.wom) - sum(b.retur_wom) - sum(b.retur_wom) as net_wom,
                sum(b.jual_pic) - sum(b.retur_jual_pic) as jual_pic,
                sum(b.retur_jual_pic) as retur_jual_pic,
                sum(b.jual_pic) - sum(b.retur_jual_pic) - sum(b.retur_jual_pic) as net_jual_pic,
                (sum(b.adira) - 1 * (sum(b.retur_adira))) + (sum(b.fif) - 1 * (sum(b.retur_fif))) + (sum(b.ifi) - 1 * (sum(b.retur_ifi))) + 
                        (sum(b.sof) - 1 * (sum(b.retur_sof))) + (sum(b.csf) - 1 * (sum(b.retur_csf))) +
                        (sum(b.mpmf) - 1 * (sum(b.retur_mpmf))) + (sum(b.wom) - 1 * (sum(b.retur_wom))) +
                        (sum(b.rbf) - 1 * (sum(b.retur_rbf))) + (sum(b.mcf) - 1 * (sum(b.retur_mcf))) +
                        (sum(b.mandiri_utama) - 1 * (sum(b.retur_mandiri_utama))) + (sum(b.mandiri_tunas) - 1 * (sum(b.retur_mandiri_tunas))) +
                        (sum(b.mandala) - 1 * (sum(b.retur_mandala))) + (sum(b.astra_buana) - 1 * (sum(b.retur_astra_buana)))
                as total_credit,
                sum(b.retur_adira) + sum(b.retur_fif) + sum(b.retur_ifi) +
                        sum(b.retur_sof) + sum(b.retur_csf) +
                        sum(b.retur_mpmf) + sum(b.retur_wom) +
                        sum(b.retur_rbf) + sum(b.retur_mcf) +
                        sum(b.retur_mandiri_utama) + sum(b.retur_mandiri_tunas) +
                        sum(b.retur_mandala) + sum(b.retur_astra_buana)
                as retur_credit,
                (sum(b.adira) - 2 * (sum(b.retur_adira))) + (sum(b.fif) - 2 * (sum(b.retur_fif))) + (sum(b.ifi) - 2 * (sum(b.retur_ifi))) +
                        (sum(b.sof) - 2 * (sum(b.retur_sof))) + (sum(b.csf) - 2 * (sum(b.retur_csf))) +
                        (sum(b.mpmf) - 2 * (sum(b.retur_mpmf))) + (sum(b.wom) - 2 * (sum(b.retur_wom))) +
                        (sum(b.rbf) - 2 * (sum(b.retur_rbf))) + (sum(b.mcf) - 2 * (sum(b.retur_mcf))) +
                        (sum(b.mandiri_utama) - 2 * (sum(b.retur_mandiri_utama))) + (sum(b.mandiri_tunas) - 2 * (sum(b.retur_mandiri_tunas))) +
                        (sum(b.mandala) - 2 * (sum(b.retur_mandala))) + (sum(b.astra_buana) - 2 * (sum(b.retur_astra_buana)))
                as net_credit,
                ((sum(b.adira) - sum(b.retur_adira)) + (sum(b.fif) - sum(b.retur_fif)) + (sum(b.ifi) - sum(b.retur_ifi)) +
                            (sum(b.sof) - sum(b.retur_sof)) + (sum(b.csf) - sum(b.retur_csf)) +
                            (sum(b.mpmf) - sum(b.retur_mpmf)) + (sum(b.wom) - sum(b.retur_wom)) +
                            (sum(b.rbf) - sum(b.retur_rbf)) + (sum(b.mcf) - sum(b.retur_mcf)) +
                            (sum(b.mandiri_utama) - sum(b.retur_mandiri_utama)) + (sum(b.mandiri_tunas) - sum(b.retur_mandiri_tunas)) +
                            (sum(b.mandala) - sum(b.retur_mandala)) + (sum(b.astra_buana) - sum(b.retur_astra_buana))) +
                --(sum(b.cash) - sum(b.jual_pic) - sum(b.retur_cash))
                --(sum(b.cash) - sum(b.jual_pic))
                (sum(b.cash) - sum(b.retur_cash))
                as penjualan_bruto,
                ((sum(b.retur_adira)) + (sum(b.retur_fif)) + (sum(b.retur_ifi)) + (sum(b.retur_sof)) + (sum(b.retur_csf)) + (sum(b.retur_mpmf)) + (sum(b.retur_wom)) + (sum(b.retur_rbf)) +
                            (sum(b.retur_mcf)) + (sum(b.retur_mandiri_utama)) + (sum(b.retur_mandiri_tunas)) + (sum(b.retur_mandala)) + (sum(b.retur_astra_buana))) +
                (sum(b.retur_cash))
                as retur_penjualan,
                (((sum(b.adira) - sum(b.retur_adira)) + (sum(b.fif) - sum(b.retur_fif)) + (sum(b.ifi) - sum(b.retur_ifi)) +
                            (sum(b.sof) - sum(b.retur_sof)) + (sum(b.csf) - sum(b.retur_csf)) +
                            (sum(b.mpmf) - sum(b.retur_mpmf)) + (sum(b.wom) - sum(b.retur_wom)) +
                            (sum(b.rbf) - sum(b.retur_rbf)) + (sum(b.mcf) - sum(b.retur_mcf)) +
                            (sum(b.mandiri_utama) - sum(b.retur_mandiri_utama)) + (sum(b.mandiri_tunas) - sum(b.retur_mandiri_tunas)) +
                            (sum(b.mandala) - sum(b.retur_mandala)) + (sum(b.astra_buana) - sum(b.retur_astra_buana))) +
                --(sum(b.cash) - sum(b.jual_pic) - sum(b.retur_cash))) -
                --(sum(b.cash) - sum(b.jual_pic) )) -
                (sum(b.cash) - sum(b.retur_cash) )) -
                (((sum(b.retur_adira)) + (sum(b.retur_fif)) + (sum(b.retur_ifi)) + (sum(b.retur_sof)) + (sum(b.retur_csf)) + (sum(b.retur_mpmf)) + (sum(b.retur_wom)) + (sum(b.retur_rbf)) +
                            (sum(b.retur_mcf)) + (sum(b.retur_mandiri_utama)) + (sum(b.retur_mandiri_tunas)) + (sum(b.retur_mandala)) + (sum(b.retur_astra_buana))) +
                (sum(b.retur_cash)))
                as net_penjualan
                from
                (select a.name, a.branch_code, a.branch_status, a.branch_name, a.cust_name, a.finco_code,
                    case when a.finco_code = 'Cash' then count(a.finco_code) else 0 end as cash,
                    case when a.finco_code = 'Cash' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_cash,
                    case when a.finco_code = 'PT. ADIRA DINAMIKA MULTI FINANCE TBK.' then count(a.finco_code) else 0 end as adira,
                    case when a.finco_code = 'PT. ADIRA DINAMIKA MULTI FINANCE TBK.' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_adira,
                    case when a.finco_code = 'PT. ASURANSI ASTRA BUANA' then count(a.finco_code) else 0 end as astra_buana,
                    case when a.finco_code = 'PT. ASURANSI ASTRA BUANA' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_astra_buana,
                    case when a.finco_code = 'PT. CENTRAL SENTOSA FINANCE' then count(a.finco_code) else 0 end as csf,
                    case when a.finco_code = 'PT. CENTRAL SENTOSA FINANCE' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_csf,
                    case when a.finco_code = 'PT. FEDERAL INTERNATIONAL FINANCE' then count(a.finco_code) else 0 end as fif,
                    case when a.finco_code = 'PT. FEDERAL INTERNATIONAL FINANCE' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_fif,
                    case when a.finco_code = 'PT. INDOMOBIL FINANCE INDONESIA' then count(a.finco_code) else 0 end as ifi,
                    case when a.finco_code = 'PT. INDOMOBIL FINANCE INDONESIA' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_ifi,
                    case when a.finco_code = 'PT. MANDALA MULTIFINANCE TBK.' then count(a.finco_code) else 0 end as mandala,
                    case when a.finco_code = 'PT. MANDALA MULTIFINANCE TBK.' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_mandala,
                    case when a.finco_code = 'PT. MANDIRI TUNAS FINANCE' then count(a.finco_code) else 0 end as mandiri_tunas,
                    case when a.finco_code = 'PT. MANDIRI TUNAS FINANCE' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_mandiri_tunas,
                    case when a.finco_code = 'PT. MANDIRI UTAMA FINANCE' then count(a.finco_code) else 0 end as mandiri_utama,
                    case when a.finco_code = 'PT. MANDIRI UTAMA FINANCE' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_mandiri_utama,
                    case when a.finco_code = 'PT. MEGA CENTRAL FINANCE ' then count(a.finco_code) else 0 end as mcf,
                    case when a.finco_code = 'PT. MEGA CENTRAL FINANCE ' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_mcf,
                    case when a.finco_code = 'PT. MITRA PINASTHIKA MUSTIKA FINANCE' then count(a.finco_code) else 0 end as mpmf,
                    case when a.finco_code = 'PT. MITRA PINASTHIKA MUSTIKA FINANCE' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_mpmf,
                    case when a.finco_code = 'PT. RADANA BHASKARA FINANCE, TBK' then count(a.finco_code) else 0 end as rbf,
                    case when a.finco_code = 'PT. RADANA BHASKARA FINANCE, TBK' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_rbf,
                    case when a.finco_code = 'PT. SUMMIT OTO FINANCE' then count(a.finco_code) else 0 end as sof,
                    case when a.finco_code = 'PT. SUMMIT OTO FINANCE' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_sof,
                    case when a.finco_code = 'PT. WAHANA OTTOMITRA MULTIARTHA' then count(a.finco_code) else 0 end as wom,
                    case when a.finco_code = 'PT. WAHANA OTTOMITRA MULTIARTHA' and a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_wom,
                    case when a.finco_code != 'Cash' and a.finco_code != '' then count(a.finco_code) else 0 end as credit,
                    count(a.finco_code) as all,
                    case when a.no_retur <> ' ' then count(a.no_retur) else 0 end as retur_jual,
                    case when a.no_retur <> ' ' and a.finco_code = 'Cash' and (a.cust_name = 'PT. Daya Anugrah Mandiri' or a.cust_name = 'PT. Solusi Tulus Mitra' or a.cust_name = 'PT. Rina Mitra Raharja' or a.cust_name = 'PT. Daya Alvita Mandiri' or a.cust_name = 'PT. Cakra Laksana Sakti') then count(a.no_retur) else 0 end as retur_jual_pic,
                    case when a.finco_code = 'Cash' and (a.cust_name = 'PT. Daya Anugrah Mandiri' or a.cust_name = 'PT. Solusi Tulus Mitra' or a.cust_name = 'PT. Rina Mitra Raharja' or a.cust_name = 'PT. Daya Alvita Mandiri' or a.cust_name = 'PT. Cakra Laksana Sakti') then count(a.finco_code) else 0 end as jual_pic
                    from (select dso.id as id_dso, COALESCE(b.branch_status,'') as branch_status, COALESCE(b.code,'') as branch_code,
                            COALESCE(b.name,'') as branch_name, COALESCE(dso.name,'') as name,
                            CASE WHEN dso.state = 'progress' THEN 'Sales Memo' WHEN dso.state = 'done' THEN 'Done' WHEN dso.state IS NULL THEN '' ELSE dso.state END as state,
                            dso.date_order as date_order, COALESCE(finco.name,'Cash') as finco_code,
                            COALESCE(case when cust.is_company = 't' and cust.name = 'PT. Daya Anugrah Mandiri' then 'PT. Daya Anugrah Mandiri'
                                     else case when cust.is_company = 't' and cust.name = 'PT. Cakra Laksana Sakti' then 'PT. Cakra Laksana Sakti'
                                     else case when cust.is_company = 't' and cust.name = 'PT. Daya Alvita Mandiri' then 'PT. Daya Alvita Mandiri'
                                     else case when cust.is_company = 't' and cust.name = 'PT. Rina Mitra Raharja' then 'PT. Rina Mitra Raharja'
                                     else case when cust.is_company = 't' and cust.name = 'PT. Solusi Tulus Mitra' then 'PT. Solusi Tulus Mitra'
                                     else cust.name end end end end end,'') as cust_name,
                            lot.name as lot_name,
                            ' ' as no_retur
                        from    dealer_sale_order dso
                        inner join dealer_spk spk on spk.dealer_sale_order_id = dso.id
                        inner join dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id = dso.id
                        left join (select max(sp.id) as id, sp.origin from stock_picking sp group by sp.origin) sp on sp.origin = dso.name
                        left join stock_picking sp1 on sp1.id = sp.id
                        left join dym_hutang_komisi hk ON dsol.hutang_komisi_id = hk.id
                        left join res_partner rhk ON hk.name = rhk.name
                        left join res_partner medi ON dso.partner_komisi_id = medi.id
                        left join dym_proposal_event pro ON dso.proposal_id = pro.id
                        left join dym_branch b ON dso.branch_id = b.id
                        left join res_partner md ON b.default_supplier_id = md.id
                        left join res_partner finco ON dso.finco_id = finco.id
                        left join hr_employee employee ON dso.employee_id = employee.id
                        left join resource_resource res_res ON employee.resource_id = res_res.id
                        left join hr_job job ON employee.job_id = job.id
                        left join crm_case_section crm ON dso.section_id = crm.id
                        left join hr_employee employee_koord ON employee_koord.id = crm.employee_id
                        left join res_partner cust ON dso.partner_id = cust.id
                        left join res_partner cust_stnk ON dsol.partner_stnk_id = cust_stnk.id
                        left join product_product product ON dsol.product_id = product.id
                        left join product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id
                        left join product_attribute_value pav ON pavpp.att_id = pav.id
                        left join product_template prod_template ON product.product_tmpl_id = prod_template.id
                        left join product_category prod_category ON prod_template.categ_id = prod_category.id
                        left join product_category prod_category2 ON prod_category.parent_id = prod_category2.id
                        left join stock_production_lot lot ON dsol.lot_id = lot.id
                        left join dym_faktur_pajak_out fp ON dso.faktur_pajak_id = fp.id
                        left join dym_cabang_partner dcp ON dcp.id = spk.partner_cabang
                        left join ( select  dealer_sale_order_line_discount_line_id, sum(ps_finco) as ps_finco, case when sum(ps_finco) = sum(discount_pelanggan) then sum(ps_finco) else case when sum(ps_finco) = 0 then sum(ps_finco) else sum(discount_pelanggan) end end as ps_finco_real, sum(ps_ahm) as ps_ahm, sum(ps_md) as ps_md, sum(ps_dealer) as ps_dealer,
                                    sum(ps_others) as ps_others, case when sum(ps_finco) = sum(discount_pelanggan) then sum(ps_finco) else sum(discount_pelanggan) end as discount_real, sum(discount) as discount, sum(discount_pelanggan) as discount_pelanggan
                                from    dealer_sale_order_line_discount_line group by dealer_sale_order_line_discount_line_id ) dsol_disc ON dsol_disc.dealer_sale_order_line_discount_line_id = dsol.id
                        left join (     select  dealer_sale_order_line_discount_line_id, sum(discount_pelanggan) as discount_pelanggan
                                from    dealer_sale_order_line_discount_line where include_invoice = 'f'
                                group by dealer_sale_order_line_discount_line_id ) dsol_disc_not ON dsol_disc_not.dealer_sale_order_line_discount_line_id = dsol.id
                        left join (     select  dealer_sale_order_line_discount_line_id, sum(discount_pelanggan) as discount_pelanggan
                                from    dealer_sale_order_line_discount_line where include_invoice = 't'
                                group by dealer_sale_order_line_discount_line_id ) dsol_disc_yes ON dsol_disc_yes.dealer_sale_order_line_discount_line_id = dsol.id
                        --left join sale_member_empl_rel smer ON smer.id = empl_id.register_spk_id
                        left join (select max(dspl.id) as id, dspl.engine_number from dym_stock_packing_line dspl group by dspl.engine_number) dspl on dspl.engine_number = lot.name
                        left join dym_stock_packing_line dspl1 ON dspl1.id = dspl.id
                        left join dealer_register_spk_line drsl ON drsl.id = dso.register_spk_id """ \
                    "WHERE dso.state in ('done','progress') and " + where_start_date + " AND " + where_end_date + " AND " + where_branch_ids + " " \
                    "union " \
                    """select dso.id as id_dso, COALESCE(b.branch_status,'') as branch_status, COALESCE(b.code,'') as branch_code,
                            COALESCE(b.name,'') as branch_name, COALESCE(dso.name,'') as name,
                            CASE WHEN dso.state = 'progress' THEN 'Sales Memo' WHEN dso.state = 'done' THEN 'Done' WHEN dso.state IS NULL THEN '' ELSE dso.state END as state,
                            dso.date_order as date_order, COALESCE(finco.name,'Cash') as finco_code,
                            COALESCE(case when cust.is_company = 't' and cust.name = 'PT. Daya Anugrah Mandiri' then 'PT. Daya Anugrah Mandiri'
                                     else case when cust.is_company = 't' and cust.name = 'PT. Cakra Laksana Sakti' then 'PT. Cakra Laksana Sakti'
                                     else case when cust.is_company = 't' and cust.name = 'PT. Daya Alvita Mandiri' then 'PT. Daya Alvita Mandiri'
                                     else case when cust.is_company = 't' and cust.name = 'PT. Rina Mitra Raharja' then 'PT. Rina Mitra Raharja'
                                     else case when cust.is_company = 't' and cust.name = 'PT. Solusi Tulus Mitra' then 'PT. Solusi Tulus Mitra'
                                     else cust.name end end end end end,'') as cust_name,
                            lot.name as lot_name,
                            drj.name as no_retur
                         from dym_retur_jual drj
                         left join dealer_sale_order dso ON drj.dso_id = dso.id
                         left join dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dso.id
                         left join stock_production_lot lot ON dsol.lot_id = lot.id
                         left join dym_branch b ON dso.branch_id = b.id
                         left join res_partner finco ON dso.finco_id = finco.id
                         left join res_partner cust ON dso.partner_id = cust.id """ \
                        "WHERE dso.state in ('done','progress') and drj.state in ('done','approved') and " + where_start_date + " AND " + where_end_date + " AND " + where_branch_ids + " " \
                        """order by name) a group by a.name, a.branch_status, a.branch_code, a.branch_name, a.finco_code, a.cust_name, a.no_retur)
                    b group by b.branch_status, b.branch_code, b.branch_name"""
            
        self.cr.execute(query_penjualansum)
        # print query_penjualansum   
        all_lines = self.cr.dictfetchall()
        # print "---------------",all_lines
        
        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                'no': 0,
                'branch_status': str(x['branch_status'].encode('ascii','ignore').decode('ascii')) if x['branch_status'] != None else '',
                'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                'cash': x['cash'],
                'retur_cash': x['retur_cash'],
                'net_cash': x['net_cash'],
                'adira': x['adira'],
                'retur_adira': x['retur_adira'],
                'net_adira': x['net_adira'],
                'astra_buana': x['astra_buana'],
                'retur_astra_buana': x['retur_astra_buana'],
                'net_astra_buana': x['net_astra_buana'],
                'csf': x['csf'],
                'retur_csf': x['retur_csf'],
                'net_csf': x['net_csf'],
                'fif': x['fif'],
                'retur_fif': x['retur_fif'],
                'net_fif': x['net_fif'],
                'ifi': x['ifi'],
                'retur_ifi': x['retur_ifi'],
                'net_ifi': x['net_ifi'],
                'mandala': x['mandala'],
                'retur_mandala': x['retur_mandala'],
                'net_mandala': x['net_mandala'],
                'mandiri_tunas': x['mandiri_tunas'],
                'retur_mandiri_tunas': x['retur_mandiri_tunas'],
                'net_mandiri_tunas': x['net_mandiri_tunas'],
                'mandiri_utama': x['mandiri_utama'],
                'retur_mandiri_utama': x['retur_mandiri_utama'],
                'net_mandiri_utama': x['net_mandiri_utama'],
                'mcf': x['mcf'],
                'retur_mcf': x['retur_mcf'],
                'net_mcf': x['net_mcf'],
                'mpmf': x['mpmf'],
                'retur_mpmf': x['retur_mpmf'],
                'net_mpmf': x['net_mpmf'],
                'rbf': x['rbf'],
                'retur_rbf': x['retur_rbf'],
                'net_rbf': x['net_rbf'],
                'sof': x['sof'],
                'retur_sof': x['retur_sof'],
                'net_sof': x['net_sof'],
                'wom': x['wom'],
                'retur_wom': x['retur_wom'],
                'net_wom': x['net_wom'],
                'jual_pic': x['jual_pic'],
                'retur_jual_pic': x['retur_jual_pic'],
                'net_jual_pic': x['net_jual_pic'],
                'total_credit': x['total_credit'],
                'retur_credit': x['retur_credit'],
                'net_credit': x['net_credit'],
                'penjualan_bruto': x['penjualan_bruto'],
                'retur_penjualan': x['retur_penjualan'],
                'net_penjualan': x['net_penjualan']
            }, all_lines)
            reports = filter(lambda x : datas, [{'datas':datas}])
        else :
            reports = [{'datas': [{
                'no' : 0,
                'branch_status' : 'NO DATA FOUND',
                'branch_code' : 'NO DATA FOUND',
                'branch_name' : 'NO DATA FOUND',
                'cash': 'NO DATA FOUND',
                'retur_cash': 'NO DATA FOUND',
                'net_cash': 'NO DATA FOUND',
                'adira': 'NO DATA FOUND',
                'retur_adira': 'NO DATA FOUND',
                'net_adira': 'NO DATA FOUND',
                'astra_buana': 'NO DATA FOUND',
                'retur_astra_buana': 'NO DATA FOUND',
                'net_astra_buana': 'NO DATA FOUND',
                'csf': 'NO DATA FOUND',
                'retur_csf': 'NO DATA FOUND',
                'net_csf': 'NO DATA FOUND',
                'fif': 'NO DATA FOUND',
                'retur_fif': 'NO DATA FOUND',
                'net_fif': 'NO DATA FOUND',
                'ifi': 'NO DATA FOUND',
                'retur_ifi': 'NO DATA FOUND',
                'net_ifi': 'NO DATA FOUND',
                'mandala': 'NO DATA FOUND',
                'retur_mandala': 'NO DATA FOUND',
                'net_mandala': 'NO DATA FOUND',
                'mandiri_tunas': 'NO DATA FOUND',
                'retur_mandiri_tunas': 'NO DATA FOUND',
                'net_mandiri_tunas': 'NO DATA FOUND',
                'mandiri_utama': 'NO DATA FOUND',
                'retur_mandiri_utama': 'NO DATA FOUND',
                'net_mandiri_utama': 'NO DATA FOUND',
                'mcf': 'NO DATA FOUND',
                'retur_mcf': 'NO DATA FOUND',
                'net_mcf': 'NO DATA FOUND',
                'mpmf': 'NO DATA FOUND',
                'retur_mpmf': 'NO DATA FOUND',
                'net_mpmf': 'NO DATA FOUND',
                'rbf': 'NO DATA FOUND',
                'retur_rbf': 'NO DATA FOUND',
                'net_rbf': 'NO DATA FOUND',
                'sof': 'NO DATA FOUND',
                'retur_sof': 'NO DATA FOUND',
                'net_sof': 'NO DATA FOUND',
                'wom': 'NO DATA FOUND',
                'retur_wom': 'NO DATA FOUND',
                'net_wom': 'NO DATA FOUND',
                'jual_pic': 'NO DATA FOUND',
                'retur_jual_pic': 'NO DATA FOUND',
                'net_jual_pic': 'NO DATA FOUND',
                'total_credit': 'NO DATA FOUND',
                'retur_credit': 'NO DATA FOUND',
                'net_credit': 'NO DATA FOUND',
                'penjualan_bruto': 'NO DATA FOUND',
                'retur_penjualan': 'NO DATA FOUND',
                'net_penjualan': 'NO DATA FOUND'}]
                }]

        self.localcontext.update({'reports':reports})
        super(dym_report_penjualansum_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_penjualansum_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_penjualansum.report_penjualansum'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_penjualansum.report_penjualansum'
    _wrapped_report_class = dym_report_penjualansum_print
