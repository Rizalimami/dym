from datetime import datetime, date
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm
from openerp import SUPERUSER_ID

class dym_report_penjualansdb_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_penjualansdb_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def format_tanggal(self, tanggal):
        return datetime.strptime(str(tanggal),'%Y-%m-%d').strftime('%d-%m-%Y')

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        
        title_short_prefix = ''
        
        user_brw = self.pool.get('res.users').browse(cr, uid, uid)
        user_branch_type = user_brw.branch_type

        report_penjualansdb = {
            'type': '',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan SDB New')} 

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
        
        query_sdb = """
            select  dso.id as id_dso, 
                    dsol.id as id_dsol, 
                    COALESCE(b.branch_status,'') as branch_status, 
                    COALESCE(b.code,'') as branch_code,
                    COALESCE(b.name,'') as branch_name,
                    COALESCE(dso.name,'') as name, 
                    COALESCE(dcp_partner.name,'') as cabang_partner, 
                    COALESCE(spk.name,'') as spk_name, 
                    COALESCE(drsl.name, '') as no_registrasi, 
                    COALESCE(cust_stnk.default_code,'') as cust_stnk_code, 
                    COALESCE(md.default_code || '-' || md.name,'') as md_code,                     
                    CASE WHEN dso.state = 'progress' THEN 'Sales Memo' WHEN dso.state = 'done' THEN 'Done' WHEN dso.state IS NULL THEN '' ELSE dso.state END as state, 
                    dso.date_order as date_order, 
                    COALESCE(finco.name,'Cash') as finco_code, 
                    CASE WHEN dso.is_cod = TRUE THEN 'COD' 
			else case when dso.is_pic = 't' then 'PIC'
		    ELSE 'Reguler' END END as is_cod, 
                    --sm.id as stock_move_non_unit_id, 
                    employee_koord.name_related as sales_koor_name, 
                    COALESCE(res_res.name,'') as sales_name, 
                    COALESCE(job.name,'') as job_name, 
                    COALESCE(cust.default_code,'') as cust_code, 
                    COALESCE(cust.name,'') as cust_name, 
                    COALESCE(cust_stnk.name,'') as cust_stnk_name, 
                    COALESCE(cust.npwp,'Non PKP') as pkp, 
                    COALESCE(product.name_template,'') as product_name,
                    COALESCE(product1.default_code,'') as product_desc,
                    COALESCE(pav.code,'') as pav_code, 
                    COALESCE(dsol.product_qty,0) as product_qty, 
                    COALESCE(lot.name,'') as lot_name, 
                    COALESCE(lot.chassis_no,'') as lot_chassis, 
                    COALESCE(dsol.price_unit,0) as price_unit, 
                    COALESCE(dsol.discount_po,0) as discount_po, 
                    COALESCE(dsol_disc.ps_dealer,0) as ps_dealer, 
                    COALESCE(dsol_disc.ps_ahm,0) as ps_ahm, 
                    COALESCE(dsol_disc.ps_md,0) as ps_md, 
                    COALESCE(dsol_disc.ps_finco,0) as ps_finco, 
                    COALESCE(dsol_disc.ps_dealer,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0) as ps_total, 
                    COALESCE(dsol.price_unit/1.1,0) as sales, 
                    COALESCE(dsol.discount_po/1.1,0) as disc_reg, 
                    COALESCE(dsol_disc_yes.discount_pelanggan/1.1,0) as disc_quo, 
                    COALESCE(dsol_disc_yes.discount_pelanggan) as disc_quo_incl_tax, 
                    COALESCE(dsol_disc_not.discount_pelanggan) as disc_quo_incl_tax_no, 
                    COALESCE(dsol.discount_po,0)+COALESCE(dsol_disc.discount_pelanggan,0) as disc_total, 
                    COALESCE(dsol.price_subtotal,0) as price_subtotal, 
                    round(COALESCE(dsol.price_subtotal,0) + round(dsol.price_subtotal*0.1,2) + COALESCE(dsol.price_bbn,0)) as piutang_total, 
                    round(COALESCE(dsol.price_subtotal,0) + round(dsol.price_subtotal*0.1,2)) as total, 
                    round(dsol.price_subtotal*0.1,2) as PPN, 
                    COALESCE(dsol.force_cogs,0) as force_cogs, 
                    COALESCE(dso.customer_dp,0) as piutang_dp, 
                    round(COALESCE(dsol.price_subtotal,0) + round(dsol.price_subtotal*0.1,2) + COALESCE(dsol.price_bbn,0)) - COALESCE(dso.customer_dp,0) as piutang,
                    --CASE    WHEN finco.name = 'PT. ADIRA DINAMIKA MULTI FINANCE TBK.' THEN round((COALESCE(dsol.price_unit,0) + COALESCE(dsol.price_bbn,0) - COALESCE(dsol.discount_po,0))) - COALESCE(dso.customer_dp,0)      
                    --    ELSE round(COALESCE(dsol.price_unit,0) + COALESCE(dsol.price_bbn,0) - COALESCE(dsol.discount_po,0) - COALESCE(dsol_disc.discount_pelanggan,0)) - COALESCE(dso.customer_dp,0) END as piutang, 
                    COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0) as gp_dpp_minus_hpp, 
                    COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0) as gp_unit, 
                    COALESCE(dsol.price_bbn,0) as price_bbn, 
                    COALESCE(dsol.price_bbn_beli,0) as price_bbn_beli, 
                    COALESCE(dsol.price_bbn,0)-COALESCE(dsol.price_bbn_beli,0) as gp_bbn, 
                    (COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0))+(COALESCE(dsol.price_bbn,0)-COALESCE(dsol.price_bbn_beli,0)) as gp_total, 
                    0 as pph_komisi, 
                    COALESCE(dsol.amount_hutang_komisi,0) as amount_hutang_komisi, 
                    COALESCE(dsol.insentif_finco/1.1,0) as insentif_finco, 
                    insentif_finco as dpp_insentif_finco, 
                    COALESCE(dsol.discount_po,0)+COALESCE(dsol_disc.ps_dealer,0)+COALESCE(amount_hutang_komisi,0) as beban_cabang, 
                    COALESCE(prod_category.name,'') as categ_name, 
                    COALESCE(prod_category2.name,'') as categ2_name, 
                    COALESCE(prod_template.series,'') as prod_series, 
                    COALESCE(fp.name,'') as faktur_pajak, 
                    COALESCE(medi.default_code,'') as partner_komisi_id,
                    COALESCE(medi.name,'') as partner_komisi_name, 
                    COALESCE(hk.name,'') as hutang_komisi_id, 
                    CONCAT(pro.number, ' ', pro.name) as proposal_id, 
                    CASE    WHEN sp.state = 'draft' THEN 'Draft' 
                        WHEN sp.state = 'cancel' THEN 'Cancelled'
                        WHEN sp.state = 'waiting' THEN 'Waiting Another Operation'      
                        WHEN sp.state = 'confirmed' THEN 'Waiting Availability'      
                        WHEN sp.state = 'partially_available' THEN 'Partially Available'      
                        WHEN sp.state = 'assigned' THEN 'Ready to Transfer'      
                        WHEN sp.state = 'done' THEN 'Transferred'      
                        ELSE sp.state END as state_picking, 
                    sp.name as oos_number,
                    cust.mobile as no_hp_cust_beli, 
                    cust_stnk.mobile as no_hp_cust_stnk,
                    dspl.tahun_pembuatan as tahun_rakit,
                    dso.amount_total as dso_amount,
                    dsol.finco_no_po as no_po,
                    dsol.finco_tgl_po as tgl_po,
                    case when dso.is_credit = 't' then 'Credit' else 'Cash' end as sls_pay,
                    case when dso.is_credit = 't' then finco.name else 'Direct Customer' end as Bill_to,
                    case    when finco.name = 'PT. ADIRA DINAMIKA MULTI FINANCE TBK.' then 'AF-' || cust.name 
                        when finco.name = 'PT. CENTRAL SENTOSA FINANCE' then 'CSF-' || cust.name 
                        when finco.name = 'PT. FEDERAL INTERNATIONAL FINANCE' then 'FIF-' || cust.name 
                        when finco.name = 'PT. INDOMOBIL FINANCE INDONESIA' then 'IFI-' || cust.name 
                        when finco.name = 'PT. MANDALA MULTIFINANCE TBK.' then 'MMF-' || cust.name 
                        when finco.name = 'PT. MANDIRI UTAMA FINANCE' then 'MUF-' || cust.name 
                        when finco.name = 'PT. MEGA CENTRAL FINANCE ' then 'MCF-' || cust.name 
                        when finco.name = 'PT. MITRA PINASTHIKA MUSTIKA FINANCE' then 'MPMF-' || cust.name 
                        when finco.name = 'PT. RADANA BHASKARA FINANCE, TBK' then 'RBF-' || cust.name 
                        when finco.name = 'PT. SUMMIT OTO FINANCE' then 'SOF-' || cust.name 
                        when finco.name = 'PT. WAHANA OTTOMITRA MULTIARTHA' then 'WOM-' || cust.name 
                    else 'CASH-' || cust.name end as cust_name,
                    'region' as region,
                    area.code as area,
                    0 as ps_other,
                    dso.dp_po as jp_po,
                    0 as discount_extern_ps,
                    0 as discount_intern_ps,
                    dcp_finco.name as finco_branch,
                    coalesce(cust.street,'') || ' RT' || coalesce(cust.rt,'') || '/RW' || coalesce(cust.rw,'') || ' Kel. ' || coalesce(cust.kelurahan,'') || ' Kec. ' || coalesce(cust.kecamatan,'') || ' ' || coalesce(city.name,'') || ' ' || coalesce(state.name,'') as alamat_cust_name,
                    city.name as kota_cust_name,
                    coalesce(cust_stnk.street,'') || ' RT' || coalesce(cust_stnk.rt,'') || '/RW' || coalesce(cust_stnk.rw,'') || ' Kel. ' || coalesce(cust_stnk.kelurahan,'') || ' Kec. ' || coalesce(cust_stnk.kecamatan,'') || ' ' || coalesce(city_stnk.name,'') || ' ' || coalesce(state_stnk.name,'') as alamat_cust_stnk_name,
                    city_stnk.name as kota_cust_stnk_name,
                    CASE WHEN left(city_stnk.name,3) = 'KAB' then 'Kabupaten' else case when city_stnk.name is null then ' ' else 'Kotamadya' end end as jns_kota_cust_stnk_name,
                    cust_stnk.kecamatan as kec_cust_stnk_name,
                    cust_stnk.kelurahan as kel_cust_stnk_name,
                    coalesce(finco.default_code,'') as vcust_id,
                    employee_koord.nip as nik_sales_koor_name,
                    employee.nip as nik_sales_name,
                    ' ' as tax_type,
                    0 as tambahan_bbn,
                    ' ' as cust_corp,
                    case when dso.is_pic = 't' then 1 else 0 end as qty_pic,
                    case when rj.qty_retur = 1 then rj.qty_retur else 0 end as qty_retur,
                    case when rj.qty_retur = 1 then COALESCE(dsol.product_qty,0) - rj.qty_retur else COALESCE(dsol.product_qty,0) - 0 end as net_sales,
                    ' ' as vchannel,
                    ' ' as pmd_reff,
                    pro.street as proposal_address,
                    ' ' as trans,
                    cust.npwp as npwp_cust,
                    employee_spv.nip as spv_nik,
                    employee_spv.name_related as spv_name,
                    dsb.name as dsb_name,
                    dsbl.diskon_ahm as dsbl_diskon_ahm, 
                    dsbl.diskon_md as dsbl_diskon_md, 
                    dsbl.diskon_dealer as dsbl_diskon_dealer, 
                    dsbl.diskon_finco as dsbl_diskon_finco, 
                    dsbl.diskon_others as dsbl_diskon_others, 
                    dsbl.total_diskon as dsbl_total_diskon 
                from    dealer_sale_order dso 
                inner join dealer_spk spk on spk.dealer_sale_order_id = dso.id 
                inner join dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id = dso.id 
                left join stock_picking sp on sp.origin = dso.name 
                left join stock_move sm ON sm.dealer_sale_order_line_id = dsol.id and sm.state not in ('done','cancel','draft') and sm.product_id != dsol.product_id 
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
                left join crm_case_section crm_spv ON crm.parent_id = crm_spv.id 
                left join hr_employee employee_spv ON employee_spv.id = crm_spv.employee_id 
                left join res_partner cust ON dso.partner_id = cust.id 
                left join dym_city city ON city.id = cust.city_id
                left join res_country_state state ON state.id = cust.state_id
                left join res_partner cust_stnk ON dsol.partner_stnk_id = cust_stnk.id 
                left join dym_city city_stnk ON city_stnk.id = cust_stnk.city_id
                left join res_country_state state_stnk ON state_stnk.id = cust_stnk.state_id
                left join product_product product ON dsol.product_id = product.id 
                left join product_product product1 ON product.name_template = product1.name_template and product1.default_code is not null
                left join product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id 
                left join product_attribute_value pav ON pavpp.att_id = pav.id 
                left join product_template prod_template ON product.product_tmpl_id = prod_template.id 
                left join product_category prod_category ON prod_template.categ_id = prod_category.id 
                left join product_category prod_category2 ON prod_category.parent_id = prod_category2.id 
                left join stock_production_lot lot ON dsol.lot_id = lot.id 
                left join dym_faktur_pajak_out fp ON dso.faktur_pajak_id = fp.id 
                left join dym_cabang_partner dcp ON dcp.id = spk.partner_cabang 
                left join dym_cabang_partner dcp_partner ON dcp_partner.id = dso.partner_cabang 
                left join dym_cabang_partner dcp_finco ON dcp_finco.id = dso.finco_cabang 
                left join ( select  dealer_sale_order_line_discount_line_id, sum(ps_finco) as ps_finco, sum(ps_ahm) as ps_ahm, sum(ps_md) as ps_md, sum(ps_dealer) as ps_dealer, 
                            sum(ps_others) as ps_others, sum(discount) as discount, sum(discount_pelanggan) as discount_pelanggan 
                        from    dealer_sale_order_line_discount_line group by dealer_sale_order_line_discount_line_id ) dsol_disc ON dsol_disc.dealer_sale_order_line_discount_line_id = dsol.id 
                left join (     select  dealer_sale_order_line_discount_line_id, sum(discount_pelanggan) as discount_pelanggan 
                        from    dealer_sale_order_line_discount_line where include_invoice = 'f'
                        group by dealer_sale_order_line_discount_line_id ) dsol_disc_not ON dsol_disc_not.dealer_sale_order_line_discount_line_id = dsol.id 
                left join (     select  dealer_sale_order_line_discount_line_id, sum(discount_pelanggan) as discount_pelanggan 
                        from    dealer_sale_order_line_discount_line where include_invoice = 't' 
                        group by dealer_sale_order_line_discount_line_id ) dsol_disc_yes ON dsol_disc_yes.dealer_sale_order_line_discount_line_id = dsol.id 
                --left join sale_member_empl_rel smer ON smer.id = empl_id.register_spk_id 
                left join dym_stock_packing_line dspl ON dspl.engine_number = lot.name
                left join dealer_register_spk_line drsl ON drsl.id = dso.register_spk_id 
                left join dym_area_cabang_rel dacr on dacr.branch_id = b.id and dacr.area_id in (532,533,534,535,536,537,538,539)
                left join dym_area area on area.id = dacr.area_id and area.id in (532,533,534,535,536,537,538,539)
                --left join dym_retur_jual drj on drj.dso_id = dso.id
                left join (select dso.name as dso_name, count(*) as qty_retur from dym_retur_jual drj left join dealer_sale_order dso on dso.id = drj.dso_id where drj.state in ('approved','done') group by dso.name) rj on rj.dso_name = dso.name
                left join dealer_sale_order_line_brgbonus_line dsolbl on dsolbl.dealer_sale_order_line_brgbonus_line_id = dsol.id
                left join dym_subsidi_barang dsb on dsb.id = dsolbl.barang_subsidi_id
                left join dym_subsidi_barang_line dsbl on dsbl.subsidi_barang_id = dsb.id and dsbl.product_id = dsol.template_id
                 """ \
            "WHERE dso.state in ('progress','done') AND " + where_start_date + " AND " + where_end_date + " AND " + where_branch_ids + " " \
            """group by        dso.id, drsl.name, dsol.price_subtotal, dsol.price_bbn, b.branch_status, b.code, spk.name, dcp.name, b.name, md.default_code, finco.name, employee_koord.name_related,
                                res_res.name, job.name, cust.default_code, cust.name, cust_stnk.name, cust.npwp, product.name_template, pav.code, dsol.product_qty, lot.name, lot.chassis_no, dsol.price_unit,
                                dsol.discount_po, dsol_disc.ps_dealer, dsol_disc.ps_ahm, dsol_disc.ps_md, dsol_disc.ps_finco, dsol_disc_yes.discount_pelanggan, dsol_disc_not.discount_pelanggan, dsol_disc.discount_pelanggan,
                                dsol.force_cogs, dsol.price_bbn_beli, dsol.amount_hutang_komisi, dsol.insentif_finco, prod_category.name, prod_category2.name, prod_template.series, fp.name, rhk.default_code,
                                hk.name, pro.number, pro.name, sp.state, sp.name, cust.mobile, cust_stnk.mobile, dspl.tahun_pembuatan, dsol.finco_no_po, dsol.finco_tgl_po, dsol.id, dcp_partner.name,
                                cust_stnk.default_code, md.name, product1.default_code, medi.default_code, medi.name, area.code, dcp_finco.name, cust.street, cust.rt, cust.rw, cust.kelurahan,
                                cust.kecamatan, city.name, state.name, cust_stnk.street, cust_stnk.rt, cust_stnk.rw, cust_stnk.kelurahan, cust_stnk.kecamatan, city_stnk.name, state_stnk.name,
                                finco.default_code, employee_koord.nip, employee.nip, rj.qty_retur, pro.street, employee_spv.nip, employee_spv.name_related, dsb.name, dsbl.diskon_ahm, dsbl.diskon_md,
                                dsbl.diskon_dealer, dsbl.diskon_finco, dsbl.diskon_others, dsbl.total_diskon """
            # "order by b.code, dso.date_order"


        move_selection = ""
        report_info = _('')
        move_selection += ""
                
        reports = [report_penjualansdb]
        for report in reports:
            cr.execute(query_sdb)
            print query_sdb
            all_lines = cr.dictfetchall()
            dso_ids = []

            if all_lines:
                def lines_map(x):
                        x.update({'docname': x['branch_code']})
                map(lines_map, all_lines)
                for cnt in range(len(all_lines)-1):
                    if all_lines[cnt]['id_dso'] != all_lines[cnt+1]['id_dso']:
                        all_lines[cnt]['draw_line'] = 1
                    else:
                        all_lines[cnt]['draw_line'] = 0
                all_lines[-1]['draw_line'] = 1

                p_map = map(
                    lambda x: {
                        'no': 0,
                        'id_dso': x['id_dso'],
                        'id_dsol': x['id_dsol'],
                        'state_ksu': 'Undelivered' if x['state_picking'] == None else 'Delivered',
                        'state_picking': x['state_picking'],
                        'oos_number': x['oos_number'],
                        'no_registrasi': str(x['no_registrasi'].encode('ascii','ignore').decode('ascii')) if x['no_registrasi'] != None else '',
                        'branch_status': str(x['branch_status'].encode('ascii','ignore').decode('ascii')) if x['branch_status'] != None else '',
                        'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                        'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                        'md_code': str(x['md_code'].encode('ascii','ignore').decode('ascii')) if x['md_code'] != None else '',
                        'spk_name': str(x['spk_name'].encode('ascii','ignore').decode('ascii')) if x['spk_name'] != None else '',
                        'name': str(x['name'].encode('ascii','ignore').decode('ascii')) if x['name'] != None else '',
                        'state': str(x['state'].encode('ascii','ignore').decode('ascii')) if x['state'] != None else '',
                        'date_order': str(x['date_order']) if x['date_order'] != None else False,
                        'finco_code': str(x['finco_code'].encode('ascii','ignore').decode('ascii')) if x['finco_code'] != None else '',
                        'is_cod': str(x['is_cod'].encode('ascii','ignore').decode('ascii')) if x['is_cod'] != None else '',
                        'sales_koor_name': str(x['sales_koor_name'].encode('ascii','ignore').decode('ascii')) if x['sales_koor_name'] != None else '',
                        'sales_name': str(x['sales_name'].encode('ascii','ignore').decode('ascii')) if x['sales_name'] != None else '',
                        'job_name': str(x['job_name'].encode('ascii','ignore').decode('ascii')) if x['job_name'] != None else '',
                        'cust_code': str(x['cust_code'].encode('ascii','ignore').decode('ascii')) if x['cust_code'] != None else '',
                        'cust_stnk_code' : x['cust_stnk_code'],
                        'cust_name': str(x['cust_name'].encode('ascii','ignore').decode('ascii')) if x['cust_name'] != None else '',
                        'cust_stnk_name': str(x['cust_stnk_name'].encode('ascii','ignore').decode('ascii')) if x['cust_stnk_name'] != None else '',
                        'pkp': str(x['pkp'].encode('ascii','ignore').decode('ascii')) if x['pkp'] != None else 'Non PKP',
                        'product_name': str(x['product_name'].encode('ascii','ignore').decode('ascii')) if x['product_name'] != None else '',
                        'product_desc': x['product_desc'],
                        'pav_code': str(x['pav_code'].encode('ascii','ignore').decode('ascii')) if x['pav_code'] != None else '',
                        'product_qty': x['product_qty'],
                        'lot_name': str(x['lot_name'].encode('ascii','ignore').decode('ascii')) if x['lot_name'] != None else '',
                        'lot_chassis': str(x['lot_chassis'].encode('ascii','ignore').decode('ascii')) if x['lot_chassis'] != None else '',
                        'price_unit': x['price_unit'],
                        'discount_po': x['discount_po'],
                        'ps_dealer': x['ps_dealer'],
                        'ps_ahm': x['ps_ahm'],
                        'ps_md': x['ps_md'],
                        'cabang_partner': x['cabang_partner'],
                        'ps_finco': x['ps_finco'],
                        'ps_total': x['ps_total'],
                        'sales': x['sales'] if x['sales'] != 0 else 0,
                        'disc_reg': x['disc_reg'] if x['disc_reg'] != 0 else 0,
                        'disc_quo': x['disc_quo'] if x['disc_quo'] != 0 else 0,
                        'disc_quo_incl_tax': x['disc_quo_incl_tax'] if x['disc_quo_incl_tax'] != 0 else 0,
                        'disc_total': x['disc_total'] if x['disc_total'] != 0 else 0,
                        'price_subtotal': x['price_subtotal'],
                        'piutang_dp': x['piutang_dp'],
                        'piutang': x['piutang'],
                        'piutang_total': x['piutang_total'],
                        'PPN': x['ppn'],
                        'total': x['total'],
                        'force_cogs': x['force_cogs'],
                        'gp_dpp_minus_hpp': x['gp_dpp_minus_hpp'],
                        'gp_unit': x['gp_unit'],
                        'amount_hutang_komisi': x['amount_hutang_komisi'],
                        'dpp_insentif_finco': x['dpp_insentif_finco'] if x['dpp_insentif_finco'] != 0 else 0,
                        'price_bbn': x['price_bbn'],
                        'price_bbn_beli': x['price_bbn_beli'],
                        'pph_komisi': x['amount_hutang_komisi'] * 3 / 100,
                        'gp_bbn': x['gp_bbn'],
                        'gp_total': x['gp_total'],
                        'beban_cabang': x['beban_cabang'],
                        'categ_name': str(x['categ_name'].encode('ascii','ignore').decode('ascii')) if x['categ_name'] != None else '',
                        'categ2_name': str(x['categ2_name'].encode('ascii','ignore').decode('ascii')) if x['categ2_name'] != None else '',
                        'prod_series': str(x['prod_series'].encode('ascii','ignore').decode('ascii')) if x['prod_series'] != None else '',
                        'faktur_pajak': str(x['faktur_pajak'].encode('ascii','ignore').decode('ascii')) if x['faktur_pajak'] != None else '',
                        'partner_komisi_id': x['partner_komisi_id'],
                        'partner_komisi_name': x['partner_komisi_name'],
                        'hutang_komisi_id': x['hutang_komisi_id'],
                        'proposal_id': x['proposal_id'],
                        'no_hp_cust_beli' : x['no_hp_cust_beli'],
                        'no_hp_cust_stnk' : x['no_hp_cust_stnk'],
                        'tahun_rakit' : x['tahun_rakit'],
                        'disc_quo_incl_tax_no': x['disc_quo_incl_tax_no'],
                        'no_po': x['no_po'],
                        'tgl_po': x['tgl_po'],
                        'dso_amount': x['dso_amount'],
                        'area' : x['area'],
                        'region' : x['region'],
                        'ps_other' : x['ps_other'],
                        'jp_po' : x['jp_po'],
                        'discount_extern_ps' : x['discount_extern_ps'],
                        'discount_intern_ps' : x['discount_intern_ps'],
                        'finco_branch' : x['finco_branch'],
                        'alamat_cust_name' : x['alamat_cust_name'],
                        'kota_cust_name' : x['kota_cust_name'],
                        'alamat_cust_stnk_name' : x['alamat_cust_stnk_name'],
                        'kota_cust_stnk_name' : x['kota_cust_stnk_name'],
                        'jns_kota_cust_stnk_name' : x['jns_kota_cust_stnk_name'],
                        'kec_cust_stnk_name' : x['kec_cust_stnk_name'],
                        'kel_cust_stnk_name' : x['kel_cust_stnk_name'],
                        'nik_sales_koor_name' : x['nik_sales_koor_name'],
                        'nik_sales_name' : x['nik_sales_name'],
                        'tax_type' : x['tax_type'],
                        'tambahan_bbn' : x['tambahan_bbn'],
                        'cust_corp' : x['cust_corp'],
                        'qty_pic' : x['qty_pic'],
                        'qty_retur' : x['qty_retur'],
                        'net_sales' : x['net_sales'],
                        'vchannel' : x['vchannel'],
                        'pmd_reff' : x['pmd_reff'],
                        'proposal_address' : x['proposal_address'],
                        'trans' : x['trans'],
                        'npwp_cust' : x['npwp_cust'],
                        'sls_pay' : x['sls_pay'],
                        'vcust_id': x['vcust_id'],
                        'spv_nik': x['spv_nik'],
                        'spv_name': x['spv_name'],
                        'dsb_name':x['dsb_name'],
                        'dsbl_diskon_ahm':x['dsbl_diskon_ahm'],
                        'dsbl_diskon_md':x['dsbl_diskon_md'],
                        'dsbl_diskon_dealer':x['dsbl_diskon_dealer'],
                        'dsbl_diskon_finco':x['dsbl_diskon_finco'],
                        'dsbl_diskon_others':x['dsbl_diskon_others'],
                        'dsbl_total_diskon':x['dsbl_total_diskon'],
                    },
                    
                    all_lines)
                for p in p_map:
                    if p['id_dso'] not in map(lambda x: x.get('id_dso', None), dso_ids):
                        records = filter(lambda x: x['id_dso'] == p['id_dso'], all_lines)
                        dso = self.pool.get('dealer.sale.order').browse(cr, uid, records[0]['id_dso'])
                        if user_branch_type == 'HO':
                            analytic_1_id, analytic_2_id, analytic_3_id, analytic_4_id = self.pool.get('account.analytic.account').get_analytical(cr, SUPERUSER_ID, dso.branch_id, 'Unit', False, 4, 'Sales')
                            analytic_1_name = self.pool.get('account.analytic.account').browse(cr, SUPERUSER_ID, analytic_1_id).name or ''
                            analytic_1 = self.pool.get('account.analytic.account').browse(cr, SUPERUSER_ID, analytic_1_id).code or ''

                            analytic_2_name = self.pool.get('account.analytic.account').browse(cr, SUPERUSER_ID, analytic_2_id).name or ''
                            analytic_2 = self.pool.get('account.analytic.account').browse(cr, SUPERUSER_ID, analytic_2_id).code or ''

                            analytic_3_name = self.pool.get('account.analytic.account').browse(cr, SUPERUSER_ID, analytic_3_id).name or ''
                            analytic_3 = self.pool.get('account.analytic.account').browse(cr, SUPERUSER_ID, analytic_3_id).code or ''
                            
                            analytic_4_name = self.pool.get('account.analytic.account').browse(cr, SUPERUSER_ID, analytic_4_id).name or ''
                            analytic_4 = self.pool.get('account.analytic.account').browse(cr, SUPERUSER_ID, analytic_4_id).code or ''
                        else:
                            analytic_1_id, analytic_2_id, analytic_3_id, analytic_4_id = self.pool.get('account.analytic.account').get_analytical(cr, uid, dso.branch_id, 'Unit', False, 4, 'Sales')
                            analytic_1_name = self.pool.get('account.analytic.account').browse(cr, uid, analytic_1_id).name or ''
                            analytic_1 = self.pool.get('account.analytic.account').browse(cr, uid, analytic_1_id).code or ''

                            analytic_2_name = self.pool.get('account.analytic.account').browse(cr, uid, analytic_2_id).name or ''
                            analytic_2 = self.pool.get('account.analytic.account').browse(cr, uid, analytic_2_id).code or ''

                            analytic_3_name = self.pool.get('account.analytic.account').browse(cr, uid, analytic_3_id).name or ''
                            analytic_3 = self.pool.get('account.analytic.account').browse(cr, uid, analytic_3_id).code or ''
                            
                            analytic_4_name = self.pool.get('account.analytic.account').browse(cr, uid, analytic_4_id).name or ''
                            analytic_4 = self.pool.get('account.analytic.account').browse(cr, uid, analytic_4_id).code or ''

                        branch = dso.branch_id
                        branch_name = dso.branch_id.name
                        branch_status_1 = dso.branch_id.branch_status
                        branch_id = dso.branch_id.id

                        if (branch and branch_ids and branch.id not in branch_ids):
                            continue
                        analytic_2_branch = analytic_2
                        if analytic_2 in ['210','220','230']:
                            analytic_2_branch = analytic_2
                        analytic_combination = analytic_1 + '/' + analytic_2_branch + '/' + analytic_3 + '/' + analytic_4
                        p.update({'lines': records})
                        p.update({'analytic_1': analytic_1_name})
                        p.update({'analytic_2': analytic_2_name})
                        p.update({'analytic_3': analytic_3_name})
                        p.update({'analytic_4': analytic_4_name})
                        p.update({'branch_id': branch_id})
                        p.update({'branch_status': branch_status_1})
                        p.update({'branch_name': branch_name})
                        p.update({'analytic_combination': analytic_combination})
                        p.update({'or_name': ''})
                        #p.update({'or_amount': '0'})
                        p.update({'invoice_number': ''})
                        p.update({'invoice_date': ''})
                        p.update({'effective_date': ''})
                        p.update({'invoice_status': ''})
                        p.update({'ar_days': '0'})
                        p.update({'tgl_lunas': ''})
                        p.update({'last_update_time': ''})

                        now = datetime.now()
                        date_today = now.strftime("%d-%m-%Y")

                        # Diskon Intern Extern
                        dsol = self.pool.get('dealer.sale.order.line').browse(cr, uid, p['id_dsol'])
                        try:
                            for diskon in dsol.discount_line:
                                if diskon:
                                    disc_extern_all = diskon.ps_ahm_copy + diskon.ps_md_copy + diskon.ps_finco_copy + diskon.ps_others_copy
                                    if diskon.discount_pelanggan - disc_extern_all <= 0:
                                        p['discount_extern_ps'] = p['discount_extern_ps'] + diskon.discount_pelanggan
                                        p['discount_intern_ps'] = 0
                                        p({'discount_extern_ps':p['discount_extern_ps']})
                                        p({'discount_intern_ps':p['discount_intern_ps']})
                                    else:
                                        p['discount_extern_ps'] = p['discount_extern_ps'] + disc_extern_all
                                        p['discount_intern_ps'] = p['discount_intern_ps'] + (diskon.discount_pelanggan - disc_extern_all)
                                        p({'discount_extern_ps':p['discount_extern_ps']})
                                        p({'discount_intern_ps':p['discount_intern_ps']})
                        except Exception as e:
                            pass
                        

                        if user_branch_type == 'HO':
                            moves_ids = self.pool.get('account.move').search(cr, SUPERUSER_ID, [('ref','ilike',dso.name),('state','=','posted')], limit=1)
                        else:
                            moves_ids = self.pool.get('account.move').search(cr, uid, [('ref','ilike',dso.name),('state','=','posted')], limit=1)
                        if moves_ids:
                            if user_branch_type == 'HO':
                                moves = self.pool.get('account.move').browse(cr, SUPERUSER_ID, moves_ids)
                            else:
                                moves = self.pool.get('account.move').browse(cr, uid, moves_ids)
                            p.update({'tgl_lunas': moves.date and ', '.join(moves.mapped('date')) or None})
                        if user_branch_type == 'HO':
                            voucher_ids = self.pool.get('account.voucher').search(cr, SUPERUSER_ID, ['|',('name','ilike',dso.name),('reference','ilike',dso.name)])
                        else:
                            voucher_ids = self.pool.get('account.voucher').search(cr, uid, ['|',('name','ilike',dso.name),('reference','ilike',dso.name)])
                        if voucher_ids:
                            if user_branch_type == 'HO':
                                vouchers = self.pool.get('account.voucher').browse(cr, SUPERUSER_ID, voucher_ids)
                            else:
                                vouchers = self.pool.get('account.voucher').browse(cr, uid, voucher_ids)
                            p.update({'or_name': ', '.join(vouchers.mapped('number'))})
                            #p.update({'or_amount': ', '.join([str(i) for i in vouchers.mapped('amount')])})
                        if user_branch_type == 'HO':
                            invoice_ids = self.pool.get('account.invoice').search(cr, SUPERUSER_ID, [('origin','ilike',dso.name),('type','=','out_invoice')], limit=1)
                        else:
                            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('origin','ilike',dso.name),('type','=','out_invoice')], limit=1)
                        if invoice_ids:
                            if user_branch_type == 'HO':
                                invoices = self.pool.get('account.invoice').browse(cr, SUPERUSER_ID, invoice_ids)
                            else:
                                invoices = self.pool.get('account.invoice').browse(cr, uid, invoice_ids)
                            payment_dates = [x.date for x in invoices.payment_ids]
                            payment_credits = [x.credit for x in invoices.payment_ids]
                            payment_debits = [x.debit for x in invoices.payment_ids]
                            # print invoices.write_date
                            # p.update({'last_update_time' : write_date})
                            if payment_dates:
                                payment_dates = max(payment_dates)
                            else:
                                payment_dates = None
                            if p['dso_amount'] - sum(payment_credits) + sum(payment_debits) == 0:
                                p.update({'tgl_lunas': payment_dates})
                            else:
                                p.update({'tgl_lunas': None})
                            p.update({'invoice_number': ', '.join(invoices.mapped('internal_number'))})
                            if invoices.date_invoice:
                                p.update({'invoice_date': invoices.date_invoice})
                                p.update({'last_update_time': datetime.strptime(invoices.write_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')})
                            else:
                                p.update({'invoice_date': datetime.strptime(invoices.confirm_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')})
                                p.update({'last_update_time': datetime.strptime(invoices.write_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')})
                            p.update({'invoice_status': invoices.state})
                            if invoices.state == 'cancel':
                                p.update({'product_qty': 0,
                                        'price_unit': 0,
                                        'discount_po': 0,
                                        'ps_dealer': 0,
                                        'ps_ahm': 0,
                                        'ps_md': 0,
                                        'ps_finco': 0,
                                        'ps_total': 0,
                                        'sales': 0,
                                        'disc_reg': 0,
                                        'disc_quo': 0,
                                        'disc_quo_incl_tax': 0,
                                        'disc_total': 0,
                                        'piutang_dp': 0,
                                        'piutang': 0,
                                        'piutang_total': 0,
                                        'total': 0,
                                        'price_subtotal': 0,
                                        'PPN': 0,
                                        'force_cogs': 0,
                                        'gp_dpp_minus_hpp': 0,
                                        'gp_unit': 0,
                                        'amount_hutang_komisi': 0,
                                        'dpp_insentif_finco': 0,
                                        'price_bbn': 0,
                                        'price_bbn_beli': 0,
                                        'gp_bbn': 0,
                                        'gp_total': 0,
                                        'beban_cabang': 0,
                                        'pph_komisi': 0,
                                        })
                            # ar = date_effective - date_inv
                            # print "asdasdasd", ar
                            # print "date_effective : ", date_effective
                            # print "date_inv : ", date_inv
                            # print date_effective - date_inv
                            # p.update({'ar_days': str(ar)})
                            # inv_cust = invoices
                            # if len(invoices) > 1:
                            #     inv_cust = invoices.filtered(lambda r: r.tipe == 'customer')
                            # if inv_cust and inv_cust[0].state == 'paid' and inv_cust[0].payment_ids:
                            #     paid_date = inv_cust[0].payment_ids.sorted(key=lambda r: r.date)[len(inv_cust[0].payment_ids) - 1].date
                            #     paid_date = datetime.strptime(paid_date, '%Y-%m-%d')
                            #     paid_date = datetime.date(paid_date)
                            #     str_paid_date = paid_date.strftime('%Y-%m-%d')
                            #     print "------",inv_cust
                            # else:
                            #     paid_date = date.today()
                            #     str_paid_date = ''
                            # inv_date = inv_cust[0].date_invoice
                            # if inv_date:
                            #     inv_date = datetime.strptime(inv_date, '%Y-%m-%d')
                            #     inv_date = datetime.date(inv_date)
                            #     date_diff = int((paid_date-inv_date).days)
                            #     p.update({'ar_days': str(date_diff)})
                            #     p.update({'tgl_lunas': str_paid_date})
                            # else:
                            #     p.update({'ar_days': None})
                            #     p.update({'tgl_lunas': None})
                        dso_ids.append(p)
                dso_ids = sorted(dso_ids, key=lambda k: k['invoice_number'])
                report.update({'dso_ids': dso_ids})

        for x in reports[0]['dso_ids']:
            if x['last_update_time']:
                x['last_update_time'] = self.format_tanggal(x['last_update_time'])
            if x['tgl_po']:
                x['tgl_po'] = self.format_tanggal(x['tgl_po'])
            if x['invoice_date']:
                x['invoice_date'] = self.format_tanggal(x['invoice_date'])
            if x['tgl_lunas']:
                x['tgl_lunas'] = self.format_tanggal(x['tgl_lunas'])
                # x['ar_days'] = abs((datetime.strptime(x['tgl_lunas'],'%d-%m-%Y') - datetime.strptime(x['invoice_date'],'%d-%m-%Y')).days) + 1
                x['ar_days'] = abs((datetime.strptime(x['tgl_lunas'],'%d-%m-%Y') - datetime.strptime(x['invoice_date'],'%d-%m-%Y')).days) + 1
            else:
                x['tgl_lunas'] = None
                x['ar_days'] = abs((datetime.strptime(date_today,'%d-%m-%Y') - datetime.strptime(x['invoice_date'],'%d-%m-%Y')).days) + 1
            x['date_order'] = self.format_tanggal(x['date_order'])
            # x['ar_days'] = abs(((datetime.strftime("%d-%m-%Y")) - datetime.strptime(x['invoice_date'],'%d-%m-%Y')).days) + 1
        reports = filter(lambda x: x.get('dso_ids'), reports)

        #print reports[0]['dso_ids'][0]
        
        tampung = []
        for x in reports:
            for y in x['dso_ids']:
                if len(y['lines']) == 1:
                    tampung.append(y)
                else:
                    temp_str = ''
                    temp = y
                    for z in y['lines']:
                        if z['lot_name'] != temp_str:
                            temp_str = z['lot_name']
                            test_tampung = {
                                'discount_po' : z['discount_po'],
                                'no_registrasi' : temp['no_registrasi'],
                                'pkp' : temp['pkp'],
                                'price_unit' : z['price_unit'],
                                'ps_md' : temp['ps_md'],
                                'id_dso' : temp['id_dso'],
                                'id_dsol': temp['id_dsol'],
                                'cabang_partner' : z['cabang_partner'],
                                'product_qty' : temp['product_qty'],
                                'piutang_total' : z['piutang_total'],
                                'state_picking' : temp['state_picking'],
                                'oos_number' : temp['oos_number'],
                                'total' : z['total'],
                                'tgl_lunas' : temp['tgl_lunas'],
                                'branch_id' : temp['branch_id'],
                                'analytic_4' : temp['analytic_4'],
                                'analytic_2' : temp['analytic_2'],
                                'analytic_3' : temp['analytic_3'],
                                'analytic_1' : temp['analytic_1'],
                                'piutang_dp' : temp['piutang_dp'],
                                'job_name' : temp['job_name'],
                                'disc_quo' : z['disc_quo'],
                                'cust_code' : temp['cust_code'],
                                'cust_stnk_code' : z['cust_stnk_code'],
                                'hutang_komisi_id' : temp['hutang_komisi_id'],
                                'ps_total' : z['ps_total'],
                                'sales' : z['sales'],
                                'branch_name' : temp['branch_name'],
                                'gp_bbn' : z['gp_bbn'],
                                'invoice_number' : temp['invoice_number'],
                                'name' : temp['name'],
                                'pph_komisi' : z['pph_komisi'],
                                'disc_total' : z['disc_total'],
                                'faktur_pajak' : temp['faktur_pajak'],
                                'cust_name' : temp['cust_name'],
                                'cust_stnk_name' : temp['cust_stnk_name'],
                                'piutang' : z['piutang'],
                                'prod_series' : temp['prod_series'],
                                'disc_quo_incl_tax' : temp['disc_quo_incl_tax'],
                                'sales_name' : temp['sales_name'],
                                'pav_code' : z['pav_code'],
                                'sales_koor_name' : temp['sales_koor_name'],
                                'branch_status' : temp['branch_status'],
                                'md_code' : temp['md_code'],
                                'is_cod' : temp['is_cod'],
                                'ps_finco' : z['ps_finco'],
                                'state_ksu' : temp['state_ksu'],
                                'lines' : temp['lines'],
                                'price_subtotal' : z['price_subtotal'],
                                'finco_code' : temp['finco_code'],
                                'beban_cabang' : z['beban_cabang'],
                                'ar_days' : temp['ar_days'],
                                'date_order' : temp['date_order'],
                                'disc_reg' : z['disc_reg'],
                                'price_bbn' : z['price_bbn'],
                                'no' : temp['no'],
                                'PPN' : temp['PPN'],
                                'branch_code' : temp['branch_code'],
                                'state' : temp['state'],
                                'ps_dealer' : temp['ps_dealer'],
                                'amount_hutang_komisi' : temp['amount_hutang_komisi'],
                                'proposal_id' : temp['proposal_id'],
                                'product_name' : z['product_name'],
                                'product_desc' : temp['product_desc'],
                                'analytic_combination' : temp['analytic_combination'],
                                'gp_total' : z['gp_total'],
                                'price_bbn_beli' : z['price_bbn_beli'],
                                'ps_ahm' : z['ps_ahm'],
                                'invoice_date' : temp['invoice_date'],
                                'effective_date' : temp['effective_date'],
                                'tahun_rakit' : temp['tahun_rakit'],
                                'force_cogs' : z['force_cogs'],
                                'categ2_name' : z['categ2_name'],
                                'lot_chassis' : z['lot_chassis'],
                                'invoice_status' : temp['invoice_status'],
                                'partner_komisi_id' : temp['partner_komisi_id'],
                                'partner_komisi_name': temp['partner_komisi_name'],
                                'lot_name' : z['lot_name'],
                                'dpp_insentif_finco' : z['dpp_insentif_finco'],
                                'categ_name' : z['categ_name'],
                                'gp_unit' : z['gp_unit'],
                                'or_name' : temp['or_name'],
                                'no_hp_cust_beli' : temp['no_hp_cust_beli'],
                                'no_hp_cust_stnk' : temp['no_hp_cust_stnk'],
                                # 'or_amount' : str(temp['or_amount']),
                                'spk_name' : z['spk_name'],
                                'gp_dpp_minus_hpp' : z['gp_dpp_minus_hpp'],
                                'no_po' : z['no_po'],
                                'tgl_po' : z['tgl_po'],
                                'area' : z['area'],
                                'region' : z['region'],
                                'last_update_time' : temp['last_update_time'],
                                'ps_other' : z['ps_other'],
                                'jp_po' : z['jp_po'],
                                'discount_extern_ps' : temp['discount_extern_ps'],
                                'discount_intern_ps' : temp['discount_intern_ps'],
                                'finco_branch' : z['finco_branch'],
                                'kota_cust_name' : z['kota_cust_name'],
                                'alamat_cust_name' : z['alamat_cust_name'],
                                'alamat_cust_stnk_name' : z['alamat_cust_stnk_name'],
                                'kota_cust_stnk_name' : z['kota_cust_stnk_name'],
                                'jns_kota_cust_stnk_name' : z['jns_kota_cust_stnk_name'],
                                'kec_cust_stnk_name' : z['kec_cust_stnk_name'],
                                'kel_cust_stnk_name' : z['kel_cust_stnk_name'],
                                'nik_sales_koor_name' : z['nik_sales_koor_name'],
                                'nik_sales_name' : z['nik_sales_name'],
                                'tax_type' : z['tax_type'],
                                'tambahan_bbn' : z['tambahan_bbn'],
                                'cust_corp' : z['cust_corp'],
                                'qty_pic' : z['qty_pic'],
                                'qty_retur' : z['qty_retur'],
                                'net_sales' : z['net_sales'],
                                'vchannel' : z['vchannel'],
                                'pmd_reff' : z['pmd_reff'],
                                'proposal_address' : z['proposal_address'],
                                'trans' : z['trans'],
                                'npwp_cust' : z['npwp_cust'],
                                'sls_pay' : z['sls_pay'],
                                'vcust_id' : z['vcust_id'],
                                'spv_nik':temp['spv_nik'],
                                'spv_name':temp['spv_name'],
                                'dsb_name':temp['dsb_name'],
                                'dsbl_diskon_ahm':temp['dsbl_diskon_ahm'],
                                'dsbl_diskon_md':temp['dsbl_diskon_md'],
                                'dsbl_diskon_dealer':temp['dsbl_diskon_dealer'],
                                'dsbl_diskon_finco':temp['dsbl_diskon_finco'],
                                'dsbl_diskon_others':temp['dsbl_diskon_others'],
                                'dsbl_total_diskon':temp['dsbl_total_diskon'],
                                }
                            tampung.append(test_tampung)
        del reports[0]['dso_ids']
        report.update({'dso_ids': tampung})
        
        
        if not reports :
            reports = [{'dso_ids': [{
            'no': 'NO DATA FOUND',
            'state_ksu': 'NO DATA FOUND',
            'invoice_number': 'NO DATA FOUND',
            'invoice_status': 'NO DATA FOUND',
            'invoice_date': 'NO DATA FOUND',
            'effective_date': 'NO DATA FOUND',
            'state_ksu': 'NO DATA FOUND',
            'state_picking' : 'NO DATA FOUND',
            'oos_number' : 'NO DATA FOUND',
            'branch_status': 'NO DATA FOUND',
            'no_registrasi' : 'NO DATA FOUND',
            'branch_code': 'NO DATA FOUND',
            'branch_name': 'NO DATA FOUND',
            'analytic_1': 'NO DATA FOUND',
            'analytic_2': 'NO DATA FOUND',
            'analytic_3': 'NO DATA FOUND',
            'analytic_4': 'NO DATA FOUND',
            'analytic_combination': 'NO DATA FOUND',
            'md_code': 'NO DATA FOUND',
            'spk_name': 'NO DATA FOUND',
            'name': 'NO DATA FOUND',
            'state': 'NO DATA FOUND',
            'date_order': 'NO DATA FOUND',
            'finco_code': 'NO DATA FOUND',
            'is_cod': 'NO DATA FOUND',
            'sales_koor_name': 'NO DATA FOUND',
            'sales_name': 'NO DATA FOUND',
            'job_name': 'NO DATA FOUND',
            'cust_code': 'NO DATA FOUND',
            'cust_name': 'NO DATA FOUND',
            'cust_stnk_code' : 'NO DATA FOUND',
            'cust_stnk_name' : 'NO DATA FOUND',
            'proposal_id': 'NO DATA FOUND',
            'hutang_komisi_id': 'NO DATA FOUND',
            'partner_komisi_id': 'NO DATA FOUND',
            'partner_komisi_name': 'NO DATA FOUND',
            'or_name': 'NO DATA FOUND',
            # 'or_amount': 0,
            'product_name': 'NO DATA FOUND',
            'product_desc': 'NO DATA FOUND',
            'pav_code': 'NO DATA FOUND',
            'product_qty': 0,
            'cabang_partner': 'NO DATA FOUND',
            'lot_name': 'NO DATA FOUND',
            'lot_chassis': 'NO DATA FOUND',
            'tgl_lunas': 'NO DATA FOUND',
            'ar_days': '0',
            'price_unit': 0,
            'discount_po': 0,
            'ps_dealer': 0,
            'ps_ahm': 0,
            'ps_md': 0,
            'ps_finco': 0,
            'ps_total': 0,
            'sales': 0,
            'piutang_dp': 0,
            'piutang': 0,
            'piutang_total': 0,
            'total': 0,
            'disc_reg': 0,
            'disc_quo': 0,
            'disc_quo_incl_tax': 0,
            'disc_total': 0,
            'price_subtotal': 0,
            'PPN': 0,
            'force_cogs': 0,
            'tahun_rakit': 'NO DATA FOUND',
            'gp_dpp_minus_hpp': 0,
            'gp_unit': 0,
            'amount_hutang_komisi': 0,
            'dpp_insentif_finco': 0,
            'price_bbn': 0,
            'price_bbn_beli': 0,
            'gp_bbn': 0,
            'gp_total': 0,
            'beban_cabang': 0,
            'pph_komisi': 0,
            'categ_name': 'NO DATA FOUND',
            'pkp': 'NO DATA FOUND',
            'categ2_name': 'NO DATA FOUND',
            'prod_series': 'NO DATA FOUND',
            'no_hp_cust_beli': 'NO DATA FOUND',
            'no_hp_cust_stnk': 'NO DATA FOUND',
            'tgl_po': 'NO DATA FOUND',
            'no_po': 'NO DATA FOUND',
            'area' : 'NO DATA FOUND',
            'region' : 'NO DATA FOUND',
            'last_update_time' : 'NO DATA FOUND',
            'ps_other' : 0,
            'jp_po' : 0,
            'discount_extern_ps' : 0,
            'discount_intern_ps' : 0,
            'finco_branch' : 'NO DATA FOUND',
            'alamat_cust_name':'NO DATA FOUND',
            'kota_cust_name' : 'NO DATA FOUND',
            'alamat_cust_stnk_name' : 'NO DATA FOUND',
            'kota_cust_stnk_name' : 'NO DATA FOUND',
            'jns_kota_cust_stnk_name' : 'NO DATA FOUND',
            'kec_cust_stnk_name' : 'NO DATA FOUND',
            'kel_cust_stnk_name' : 'NO DATA FOUND',
            'nik_sales_koor_name' : 'NO DATA FOUND',
            'nik_sales_name' : 'NO DATA FOUND',
            'tax_type' : 'NO DATA FOUND',
            'tambahan_bbn' : 0,
            'cust_corp' : 'NO DATA FOUND',
            'qty_pic' : 0,
            'qty_retur' : 0,
            'net_sales' : 0,
            'vchannel' : 'NO DATA FOUND',
            'pmd_reff' : 'NO DATA FOUND',
            'proposal_address' : 'NO DATA FOUND',
            'trans' : 'NO DATA FOUND',
            'npwp_cust' : 'NO DATA FOUND',
            'sls_pay' : 'NO DATA FOUND',
            'vcust_id' : 'NO DATA FOUND',
            'spv_name' : 'NO DATA FOUND',
            'spv_nik' : 'NO DATA FOUND',
            'dsb_name': 'NO DATA FOUND',
            'dsbl_diskon_ahm': 0,
            'dsbl_diskon_md': 0,
            'dsbl_diskon_dealer': 0,
            'dsbl_diskon_finco': 0,
            'dsbl_diskon_others': 0,
            'dsbl_total_diskon': 0,
            'faktur_pajak': 'NO DATA FOUND'}], 'title_short': 'Laporan SDB New', 'type': '', 'title': ''}]
        
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        objects=False
        super(dym_report_penjualansdb_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_penjualansdb_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

#register report
class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_penjualansdb.report_penjualansdb'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_penjualansdb.report_penjualansdb'
    _wrapped_report_class = dym_report_penjualansdb_print
