from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_registerpraso_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_registerpraso_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        
        
        query_registerpraso = """
            select  '' as region,
                    area.code as area,
                    '[' || b.code || '] ' || b.name as branch,
                    COALESCE(b.branch_status,'') as branch_status, 
                    COALESCE(b.code,'') as branch_code,
                    COALESCE(b.name,'') as branch_name,
                    COALESCE(dso.name,'') as name, 
                    CASE WHEN dso.state = 'progress' THEN 'Sales Memo' WHEN dso.state = 'done' THEN 'Done' WHEN dso.state IS NULL THEN '' ELSE dso.state END as state, 
                    COALESCE(ai.number,'') as invoice_number, 
                    ai.date_invoice as invoice_date, 
                    extract (year from ai.date_invoice) as invoice_date_year, 
                    extract (MONTH from ai.date_invoice) as chosen_month,
                    COALESCE(finco.name,'Cash') as finco_code,
                    case    when finco.name = 'PT. ADIRA DINAMIKA MULTI FINANCE TBK.' then 'AF-' || cust.name 
                        when finco.name = 'PT. CENTRAL SENTOSA FINANCE' then 'CSF-' || cust.name 
                        when finco.name = 'PT. FEDERAL INTERNATIONAL FINANCE' then 'FIF-' || cust.name 
                        when finco.name = 'PT. INDOMOBIL FINANCE INDONESIA' then 'IFI-' || cust.name 
                        when finco.name = 'PT. MANDALA MULTIFINANCE TBK.' then 'MMF-' || cust.name 
                        when finco.name = 'PT. MANDIRI UTAMA FINANCE' then 'MUF-' || cust.name 
                        when finco.name = 'PT. MEGA CENTRAL FINANCE ' then 'MCF-' || cust.name 
                        when finco.name = 'PT. MITRA PINASTHIKA MUSTIKA FINANCE' then 'MPMF-' || cust.name 
                        when finco.name = 'PT. RADANA BHASKARA FINANCE, TBK' then 'RBF-' || cust.name 
                        when finco.name = 'PT. SUMMIT OTTO FINANCE' then 'SOF-' || cust.name 
                        when finco.name = 'PT. WAHANA OTTOMITRA MULTIARTHA' then 'WOM-' || cust.name 
                    else 'CASH-' || cust.name end as cust_name,
                    case when dso.is_credit = 't' then 'Credit' else 'Cash' end as sls_pay,
                    'Marketing' as marketing,
                    COALESCE(prod.name_template,'') as product_name,
                    COALESCE(prod_tmpl.default_code,'') as product_desc,
                    COALESCE(lot.name,'') as lot_name, 
                    COALESCE(lot.chassis_no,'') as lot_chassis,
                    COALESCE(dsol.price_unit,0) as price_unit,
                    COALESCE(dsol.price_bbn,0) as price_bbn,
                    COALESCE(dsol.discount_po/1.1,0)+COALESCE(dsol_disc.discount_pelanggan/1.1,0) as disc_total,
                    case    when finco.name = 'PT. ADIRA DINAMIKA MULTI FINANCE TBK.' then 'AF-' || cust.name 
                        when finco.name = 'PT. CENTRAL SENTOSA FINANCE' then 'CSF-' || cust.name 
                        when finco.name = 'PT. FEDERAL INTERNATIONAL FINANCE' then 'FIF-' || cust.name 
                        when finco.name = 'PT. INDOMOBIL FINANCE INDONESIA' then 'IFI-' || cust.name 
                        when finco.name = 'PT. MANDALA MULTIFINANCE TBK.' then 'MMF-' || cust.name 
                        when finco.name = 'PT. MANDIRI UTAMA FINANCE' then 'MUF-' || cust.name 
                        when finco.name = 'PT. MEGA CENTRAL FINANCE ' then 'MCF-' || cust.name 
                        when finco.name = 'PT. MITRA PINASTHIKA MUSTIKA FINANCE' then 'MPMF-' || cust.name 
                        when finco.name = 'PT. RADANA BHASKARA FINANCE, TBK' then 'RBF-' || cust.name 
                        when finco.name = 'PT. SUMMIT OTTO FINANCE' then 'SOF-' || cust.name 
                        when finco.name = 'PT. WAHANA OTTOMITRA MULTIARTHA' then 'WOM-' || cust.name 
                    else 'CASH-' || cust.name end as cust_name_2,
                    cust.street || ' RT' || cust.rt || '/RW' || cust.rw || ' Kel. ' || cust.kelurahan || ' Kec. ' || cust.kecamatan || ' ' || city.name || ' ' || state.name as alamat_cust_name,
                    city_branch.name as kota_cabang,
                    COALESCE(dsol.amount_hutang_komisi,0) as amount_hutang_komisi,
                    COALESCE(dsol.product_qty,0) as product_qty,
                    case when rj.qty_retur = 1 then rj.qty_retur else 0 end as qty_retur,
                    case when rj.qty_retur = 1 then COALESCE(dsol.product_qty,0) - rj.qty_retur else COALESCE(dsol.product_qty,0) - 0 end as net_sales,
                    extract (DAY from ai.date_invoice) as invoice_date_date,
                    COALESCE(dcp_partner.name,'') as cabang_partner,
                    dso.tanda_jadi as tanda_jadi,
                    dsol.finco_no_po as no_po,
                    dsol.finco_tgl_po as tgl_po,
                    dso.dp_po as jp_po,
                    COALESCE(dsol.discount_po,0) as discount_po,
                    city_stnk.name as kota_cust_stnk_name,
                    cust_stnk.street || ' RT' || cust_stnk.rt || '/RW' || cust_stnk.rw || ' Kel. ' || cust_stnk.kelurahan || ' Kec. ' || cust_stnk.kecamatan || ' ' || city_stnk.name || ' ' || state_stnk.name as alamat_cust_stnk_name,
                    cust_stnk.kecamatan as kec_cust_stnk_name,
                    cust_stnk.kelurahan as kel_cust_stnk_name,
                    CASE WHEN left(city_stnk.name,3) = 'KAB' then 'Kabupaten' else case when city_stnk.name is null then ' ' else 'Kotamadya' end end as jns_kota_cust_stnk_name,
                    employee_koord.nip as nik_sales_koor_name,
                    employee_koord.name_related as sales_koor_name,
                    COALESCE(job.name,'') as job_name,
                    employee_koord.tgl_masuk as mkt_join_date,
                    (DATE_PART('year', now()::date) - DATE_PART('year', employee_koord.tgl_masuk::date)) * 12 + (DATE_PART('month', now()::date) - DATE_PART('month', employee_koord.tgl_masuk::date)) || ' months' as lama_kerja,
                    crm_spv.name as spv_nik,
                    employee_spv.name_related as spv_name,
                    employee.nip as nik_sales_name,
                    COALESCE(res_res.name,'') as sales_name, 
                    disc_ext_int.disc_extern as discount_extern_ps, 
                    disc_ext_int.disc_intern as discount_intern_ps,
                    case when dso.is_pic = TRUE then 1 else 0 end as "Is PIC",
                    case when rj.qty_retur = 1 then 1 else 0 end as "Is Retur",
                    case when dso.is_credit = 't' then finco.name else 'Direct Customer' end as "Bill To",
                    COALESCE(pav.name,'') as "Warna",
                    0 as tambahan_bbn,
                    'nama_pendek' as nama_pendek,
                    COALESCE(dsol.finco_tenor,0) as tenor
                from    dealer_sale_order dso 
                left join dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id = dso.id 
                left join account_invoice ai on ai.origin = dso.name and left(ai.number,3) in ('NDE')
                left join dym_branch b ON dso.branch_id = b.id 
                left join dym_area_cabang_rel dacr on dacr.branch_id = b.id and dacr.area_id in (532,533,534,535,536,537,538,539)
                left join dym_area area on area.id = dacr.area_id and area.id in (532,533,534,535,536,537,538,539)
                left join product_product prod ON dsol.product_id = prod.id 
                left join product_attribute_value_product_product_rel pavppr ON dsol.product_id = pavppr.prod_id 
                left join product_attribute_value pav ON pav.id = pavppr.att_id
                left join stock_production_lot lot ON dsol.lot_id = lot.id 
                left join res_partner finco ON dso.finco_id = finco.id 
                left join res_partner cust ON dso.partner_id = cust.id 
                left join dym_city city ON city.id = cust.city_id
                left join dym_city city_branch ON city_branch.id = b.city_id
                left join res_country_state state ON state.id = cust.state_id
                left join res_partner cust_stnk ON dsol.partner_stnk_id = cust_stnk.id 
                left join dym_city city_stnk ON city_stnk.id = cust_stnk.city_id
                left join res_country_state state_stnk ON state_stnk.id = cust_stnk.state_id
                left join ( select  dealer_sale_order_line_discount_line_id, 
                            sum(ps_finco) as ps_finco, 
                            sum(ps_ahm) as ps_ahm, 
                            sum(ps_md) as ps_md, 
                            sum(ps_dealer) as ps_dealer, 
                            sum(ps_others) as ps_others, 
                            sum(discount) as discount, 
                            sum(discount_pelanggan) as discount_pelanggan,
                            sum(ps_ahm) + sum(ps_md) + sum(ps_finco) + sum(ps_others) as disc_extern_all,
                            sum(discount_pelanggan) - (sum(ps_ahm) + sum(ps_md) + sum(ps_finco) + sum(ps_others)) as check_disc
                        from    dealer_sale_order_line_discount_line group by dealer_sale_order_line_discount_line_id ) dsol_disc ON dsol_disc.dealer_sale_order_line_discount_line_id = dsol.id 
                left join ( select dso.name as dso_name, count(*) as qty_retur from dym_retur_jual drj 
                        left join dealer_sale_order dso on dso.id = drj.dso_id group by dso.name) rj on rj.dso_name = dso.name
                left join dealer_spk spk on spk.dealer_sale_order_id = dso.id --and spk.state in ('done','so')
                left join dym_cabang_partner dcp ON dcp.id = spk.partner_cabang 
                left join dym_cabang_partner dcp_partner ON dcp_partner.id = dso.partner_cabang 
                left join dym_cabang_partner dcp_finco ON dcp_finco.id = dso.finco_cabang 
                left join hr_employee employee ON dso.employee_id = employee.id 
                left join resource_resource res_res ON employee.resource_id = res_res.id 
                left join hr_job job ON employee.job_id = job.id 
                left join crm_case_section crm ON dso.section_id = crm.id 
                left join hr_employee employee_koord ON employee_koord.id = crm.employee_id 
                left join crm_case_section crm_spv ON crm.parent_id = crm_spv.id 
                left join hr_employee employee_spv ON employee_spv.id = crm_spv.employee_id
                left join ( select  b.dsoldli as "dsol_id",
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
                                from    dealer_sale_order_line_discount_line )a )b
                        group by b.dsoldli) disc_ext_int on disc_ext_int.dsol_id = dsol.id
                left join ( select  distinct prod.product_tmpl_id, prod.name_template, prod.default_code
                            from    product_product prod
                            left join product_template prod_tmpl on prod.product_tmpl_id = prod_tmpl.id
                            where   prod.default_code is not null and prod_tmpl.kd_mesin is not null) prod_tmpl on prod_tmpl.product_tmpl_id = prod.product_tmpl_id
                --WHERE   dso.state in ('progress','done') and spk.state not in ('draft','cancelled')
                    --and dso.name in ('DSM-S/KAR01/1805/00456')
                    --and rj.qty_retur = 1
                    --and dso.is_pic = False
        """

        query_where = " WHERE dso.state in ('progress','done') and spk.state not in ('draft','cancelled') "
        if data['start_date']:
            query_where += " and dso.date_order >= '%s'" % str(data['start_date'])
        if data['end_date']:
            query_where += " and dso.date_order <= '%s'" % str(data['end_date'])
        if data['branch_ids']:
            query_where += " and dso.branch_id in %s" % str(tuple(data['branch_ids'])).replace(',)', ')')

        self.cr.execute(query_registerpraso + query_where)
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                # 'id_dso': x['id_dso'],
                'no': 0,
                'region' : x['region'],
                'area' : x['area'],
                'branch_status': x['branch_status'],
                'branch_code': x['branch_code'],
                'branch_name': x['branch_name'],
                'name': x['name'],
                'state': x['state'],
                'invoice_number': x['invoice_number'],
                'invoice_date': x['invoice_date'],
                'invoice_date_year': x['invoice_date_year'],
                'chosen_month': x['chosen_month'],
                'finco_code': x['finco_code'],
                'cust_name': x['cust_name'],
                'sls_pay' : x['sls_pay'],
                'marketing': x['marketing'],
                'product_name': x['product_name'],
                'product_desc': x['product_desc'],
                'lot_name': x['lot_name'],
                'lot_chassis': x['lot_chassis'],
                'price_unit': x['price_unit'],
                'price_bbn': x['price_bbn'],
                'disc_total': x['disc_total'],
                'cust_name_2': x['cust_name_2'],
                'alamat_cust_name' : x['alamat_cust_name'],
                'kota_cabang': x['kota_cabang'],
                'amount_hutang_komisi': x['amount_hutang_komisi'],
                'product_qty': x['product_qty'],
                'qty_retur' : x['qty_retur'],
                'net_sales' : x['net_sales'],
                'invoice_date_date': x['invoice_date_date'],
                'cabang_partner': x['cabang_partner'],
                'tanda_jadi': x['tanda_jadi'],
                'no_po': x['no_po'],
                'tgl_po': x['tgl_po'],
                'tenor': x['tenor'],
                'jp_po' : x['jp_po'],
                'discount_po': x['discount_po'],
                'kota_cust_stnk_name' : x['kota_cust_stnk_name'],
                'alamat_cust_stnk_name' : x['alamat_cust_stnk_name'],
                'kec_cust_stnk_name' : x['kec_cust_stnk_name'],
                'kel_cust_stnk_name' : x['kel_cust_stnk_name'],
                'jns_kota_cust_stnk_name' : x['jns_kota_cust_stnk_name'],
                'nik_sales_koor_name' : x['nik_sales_koor_name'],
                'sales_koor_name': x['sales_koor_name'],
                'job_name': x['job_name'],
                'mkt_join_date': x['mkt_join_date'],
                'lama_kerja': x['lama_kerja'],
                'spv_nik': x['spv_nik'],
                'spv_name': x['spv_name'],
                'sales_name': x['sales_name'],
                'discount_extern_ps' : x['discount_extern_ps'],
                'discount_intern_ps' : x['discount_intern_ps'],                
                'nik_sales_name' : x['nik_sales_name'],
                'tambahan_bbn' : x['tambahan_bbn'],
                # 'state_ksu': 'Undelivered' if x['state_picking'] == None else 'Delivered',
                # 'state_picking': x['state_picking'],
                # 'oos_number': x['oos_number'],
                # 'no_registrasi': x['no_registrasi']no_registrasi,
                # 'md_code': x['md_code']md_code,
                # 'spk_name': x['spk_name']spk_name,
                # 'date_order': x['date_order']) if x['date_order'] != None else False,
                # 'is_cod': x['is_cod']is_cod,
                # 'cust_code': x['cust_code']cust_code,
                # 'cust_stnk_code' : x['cust_stnk_code'],
                # 'cust_stnk_name': x['cust_stnk_name']cust_stnk_name,
                # 'pkp': x['pkp']pkp'] != None else 'Non PKP',
                # 'pav_code': x['pav_code']pav_code,
                # 'ps_dealer': x['ps_dealer'],
                # 'ps_ahm': x['ps_ahm'],
                # 'ps_md': x['ps_md'],
                # 'ps_finco': x['ps_finco'],
                # 'ps_total': x['ps_total'],
                # 'sales': x['sales'] if x['sales'] != 0 else 0,
                # 'disc_reg': x['disc_reg'] if x['disc_reg'] != 0 else 0,
                # 'disc_quo': x['disc_quo'] if x['disc_quo'] != 0 else 0,
                # 'disc_quo_incl_tax': x['disc_quo_incl_tax'] if x['disc_quo_incl_tax'] != 0 else 0,
                # 'price_subtotal': x['price_subtotal'],
                # 'piutang_dp': x['piutang_dp'],
                # 'piutang': x['piutang'],
                # 'piutang_total': x['piutang_total'],
                # 'PPN': x['ppn'],
                # 'total': x['total'],
                # 'force_cogs': x['force_cogs'],
                # 'gp_dpp_minus_hpp': x['gp_dpp_minus_hpp'],
                # 'gp_unit': x['gp_unit'],
                # 'dpp_insentif_finco': x['dpp_insentif_finco'] if x['dpp_insentif_finco'] != 0 else 0,
                # 'price_bbn_beli': x['price_bbn_beli'],
                # 'pph_komisi': x['amount_hutang_komisi'] * 3 / 100,
                # 'gp_bbn': x['gp_bbn'],
                # 'gp_total': x['gp_total'],
                # 'beban_cabang': x['beban_cabang'],
                # 'categ_name': x['categ_name']categ_name,
                # 'categ2_name': x['categ2_name']categ2_name,
                # 'prod_series': x['prod_series']prod_series,
                # 'faktur_pajak': x['faktur_pajak']faktur_pajak,
                # 'partner_komisi_id': x['partner_komisi_id'],
                # 'hutang_komisi_id': x['hutang_komisi_id'],
                # 'proposal_id': x['proposal_id'],
                # 'no_hp_cust_beli' : x['no_hp_cust_beli'],
                # 'no_hp_cust_stnk' : x['no_hp_cust_stnk'],
                # 'tahun_rakit' : x['tahun_rakit'],
                # 'disc_quo_incl_tax_no': x['disc_quo_incl_tax_no'],
                # 'tax_type' : x['tax_type'],
                # 'dso_amount': x['dso_amount'],
                # 'ps_other' : x['ps_other'],
                # 'cust_corp' : x['cust_corp'],
                # 'qty_pic' : x['qty_pic'],
                # 'finco_branch' : x['finco_branch'],
                # 'kota_cust_name' : x['kota_cust_name'],
                # 'vchannel' : x['vchannel'],
                # 'pmd_reff' : x['pmd_reff'],
                # 'proposal_address' : x['proposal_address'],
                # 'trans' : x['trans'],
                # 'npwp_cust' : x['npwp_cust'],
                # 'vcust_id': x['vcust_id'],
                'nama_pendek': x['nama_pendek']
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            reports = [{'datas': [{
                'no': '0',
                'region' : 'NO DATA FOUND',
                'area' : 'NO DATA FOUND',
                'branch_status': 'NO DATA FOUND',
                'branch_code': 'NO DATA FOUND',
                'branch_name': 'NO DATA FOUND',
                'name': 'NO DATA FOUND',
                'state': 'NO DATA FOUND',
                'invoice_number': 'NO DATA FOUND',
                'invoice_date': 'NO DATA FOUND',
                'invoice_date_year': 0,
                'chosen_month': 0,
                'finco_code': 'NO DATA FOUND',
                'cust_name': 'NO DATA FOUND',
                'sls_pay' : 'NO DATA FOUND',
                'marketing' : 'NO DATA FOUND',
                'product_name': 'NO DATA FOUND',
                'product_desc': 'NO DATA FOUND',
                'lot_name': 'NO DATA FOUND',
                'lot_chassis': 'NO DATA FOUND',
                'price_unit': 0,
                'price_bbn': 0,
                'disc_total': 0,
                'cust_name_2': 'NO DATA FOUND',
                'alamat_cust_name':'NO DATA FOUND',
                'kota_cabang' : 'NO DATA FOUND',
                'amount_hutang_komisi': 0,
                'product_qty': 0,
                'qty_retur' : 0,
                'net_sales' : 0,
                'invoice_date_date': 0,
                'cabang_partner': 'NO DATA FOUND',
                'tanda_jadi': 0,
                'no_po': 'NO DATA FOUND',
                'tgl_po': 'NO DATA FOUND',  
                'tenor': 0,
                'jp_po' : 0,
                'discount_po': 0,
                'kota_cust_stnk_name' : 'NO DATA FOUND',
                'alamat_cust_stnk_name' : 'NO DATA FOUND',
                'kec_cust_stnk_name' : 'NO DATA FOUND',
                'kel_cust_stnk_name' : 'NO DATA FOUND',
                'jns_kota_cust_stnk_name' : 'NO DATA FOUND',
                'nik_sales_koor_name' : 'NO DATA FOUND',
                'sales_koor_name': 'NO DATA FOUND',
                'job_name': 'NO DATA FOUND',
                'mkt_join_date': 'NO DATA FOUND',
                'lama_kerja': 'NO DATA FOUND',
                'spv_nik': 'NO DATA FOUND',
                'spv_name': 'NO DATA FOUND',
                'sales_name': 'NO DATA FOUND',
                'discount_extern_ps' : 0,
                'discount_intern_ps' : 0,
                'nik_sales_name' : 'NO DATA FOUND',
                'tambahan_bbn' : 0,
                # 'effective_date': 'NO DATA FOUND',
                # 'proposal_id': 'NO DATA FOUND',
                # 'or_name': 'NO DATA FOUND',
                # 'pav_code': 'NO DATA FOUND',
                # 'tgl_lunas': 'NO DATA FOUND',
                # 'ar_days': '0',
                # 'tahun_rakit': 'NO DATA FOUND',
                # 'invoice_status': 'NO DATA FOUND',
                # 'last_update_time' : 'NO DATA FOUND',
                # 'analytic_1': 'NO DATA FOUND',
                # 'analytic_2': 'NO DATA FOUND',
                # 'analytic_3': 'NO DATA FOUND',
                # 'analytic_4': 'NO DATA FOUND',
                # 'analytic_combination': 'NO DATA FOUND',
                # 'gp_dpp_minus_hpp': 0,
                # 'gp_unit': 0,
                # 'dpp_insentif_finco': 0,
                # 'price_bbn_beli': 0,
                # 'gp_bbn': 0,
                # 'gp_total': 0,
                # 'beban_cabang': 0,
                # 'pph_komisi': 0,
                # 'categ_name': 'NO DATA FOUND',
                # 'pkp': 'NO DATA FOUND',
                # 'categ2_name': 'NO DATA FOUND',
                # 'prod_series': 'NO DATA FOUND',
                # 'no_hp_cust_beli': 'NO DATA FOUND',
                # 'no_hp_cust_stnk': 'NO DATA FOUND',
                # 'finco_branch' : 'NO DATA FOUND',
                # 'ps_other' : 0,
                # 'kota_cust_name' : 'NO DATA FOUND',
                # 'tax_type' : 'NO DATA FOUND',
                # 'cust_corp' : 'NO DATA FOUND',
                # 'qty_pic' : 0,
                # 'date_order': 'NO DATA FOUND',
                # 'state_ksu': 'NO DATA FOUND',
                # 'state_picking' : 'NO DATA FOUND',
                # 'oos_number' : 'NO DATA FOUND',
                # 'no_registrasi' : 'NO DATA FOUND',
                # 'md_code': 'NO DATA FOUND',
                # 'spk_name': 'NO DATA FOUND',
                # 'is_cod': 'NO DATA FOUND',
                # 'cust_code': 'NO DATA FOUND',
                # 'cust_stnk_code' : 'NO DATA FOUND',
                # 'cust_stnk_name' : 'NO DATA FOUND',
                # 'hutang_komisi_id': 'NO DATA FOUND',
                # 'partner_komisi_id': 'NO DATA FOUND',
                # 'or_amount': 0,
                # 'ps_dealer': 0,
                # 'ps_ahm': 0,
                # 'ps_md': 0,
                # 'ps_finco': 0,
                # 'ps_total': 0,
                # 'sales': 0,
                # 'piutang_dp': 0,
                # 'piutang': 0,
                # 'piutang_total': 0,
                # 'total': 0,
                # 'disc_reg': 0,
                # 'disc_quo': 0,
                # 'disc_quo_incl_tax': 0,
                # 'price_subtotal': 0,
                # 'PPN': 0,
                # 'force_cogs': 0,
                # 'vchannel' : 'NO DATA FOUND',
                # 'pmd_reff' : 'NO DATA FOUND',
                # 'proposal_address' : 'NO DATA FOUND',
                # 'trans' : 'NO DATA FOUND',
                # 'npwp_cust' : 'NO DATA FOUND',
                'nama_pendek' : 'NO DATA FOUND'
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(dym_report_registerpraso_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_registerpraso_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_registerpraso.report_registerpraso'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_registerpraso.report_registerpraso'
    _wrapped_report_class = dym_report_registerpraso_print
    