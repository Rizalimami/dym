from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_rjualsdb_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_rjualsdb_print, self).__init__(cr, uid, name, context=context)
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
        
        query_rjualsdb = """
            select  --dso.id as id_dso, 
                    --dsol.id as id_dsol, 
                    COALESCE(b.branch_status,'') as branch_status, 
                    area.code as area,
                    COALESCE(b.code,'') as branch_code,
                    COALESCE(b.name,'') as branch_name,
                    COALESCE(ai.number,'') as invoice_number, 
                    --ai.date_invoice as invoice_date,
                    to_char(ai.date_invoice, 'DD-MM-YYYY') as invoice_date,
                    ai.write_date as last_update_time,
                    case when ai.state = 'draft' then 'Draft'
                    else case when ai.state = 'open' then 'Open'
                    else case when ai.state = 'cancel' then 'Cancelled'
                    else case when ai.state = 'paid' then 'Paid'
                    end end end end as invoice_status, 
                    COALESCE(drsl.name, '') as no_registrasi,
                    COALESCE(spk.name,'') as spk_name, 
                    COALESCE(dso.name,'') as name, 
                    --dso.date_order as date_order, 
                    to_char(dso.date_order, 'DD-MM-YYYY') as date_order, 
                    CASE WHEN dso.state = 'progress' THEN 'Sales Memo' WHEN dso.state = 'done' THEN 'Done' WHEN dso.state IS NULL THEN '' ELSE dso.state END as state, 
                    case when sp.state is null then 'Undelivered' else 'Delivered' end as state_ksu,
                    CASE WHEN sp.state = 'draft' THEN 'Draft' 
                        WHEN sp.state = 'cancel' THEN 'Cancelled'
                        WHEN sp.state = 'waiting' THEN 'Waiting Another Operation' 
                        WHEN sp.state = 'confirmed' THEN 'Waiting Availability' 
                        WHEN sp.state = 'partially_available' THEN 'Partially Available' 
                        WHEN sp.state = 'assigned' THEN 'Ready to Transfer' 
                        WHEN sp.state = 'done' THEN 'Transferred' 
                    ELSE sp.state END as state_picking, 
                    sp.name as oos_number,
                    CASE WHEN dso.is_cod = TRUE THEN 'COD' 
                        else case when dso.is_pic = 't' then 'PIC'
                    ELSE 'Reguler' END END as is_cod, 
                    case when dso.is_credit = 't' then 'Credit' else 'Cash' end as sls_pay,
                    coalesce(finco.default_code,'') as vcust_id,
                    COALESCE(finco.name,'Cash') as finco_code, 
                    dcp_finco.name as finco_branch,
                    dsol.finco_no_po as no_po,
                    --dsol.finco_tgl_po as tgl_po,
                    to_char(dsol.finco_tgl_po, 'DD-MM-YYYY') as tgl_po,
                    dsol.finco_tenor as tenor,
                    dso.dp_po as jp_po,
                    COALESCE(cust.default_code,'') as cust_code, 
                    COALESCE(cust.name,'') as cust_name, 
                    COALESCE(dcp_partner.name,'') as cabang_partner, 
                    coalesce(cust.street,'') || ' RT' || coalesce(cust.rt,'') || '/RW' || coalesce(cust.rw,'') || ' Kel. ' || coalesce(cust.kelurahan,'') || ' Kec. ' || coalesce(cust.kecamatan,'') || ' ' || coalesce(city.name,'') || ' ' || coalesce(state.name,'') as alamat_cust_name,
                    city.name as kota_cust_name,
                    cust.mobile as no_hp_cust_beli, 
                    COALESCE(cust_stnk.default_code,'') as cust_stnk_code, 
                    COALESCE(cust_stnk.name,'') as cust_stnk_name, 
                    coalesce(cust_stnk.street,'') || ' RT' || coalesce(cust_stnk.rt,'') || '/RW' || coalesce(cust_stnk.rw,'') || ' Kel. ' || coalesce(cust_stnk.kelurahan,'') || ' Kec. ' || coalesce(cust_stnk.kecamatan,'') || ' ' || coalesce(city_stnk.name,'') || ' ' || coalesce(state_stnk.name,'') as alamat_cust_stnk_name,
                    city_stnk.name as kota_cust_stnk_name,
                    CASE WHEN left(city_stnk.name,3) = 'KAB' then 'Kabupaten' else case when city_stnk.name is null then ' ' else 'Kotamadya' end end as jns_kota_cust_stnk_name,
                    cust_stnk.kecamatan as kec_cust_stnk_name,
                    cust_stnk.kelurahan as kel_cust_stnk_name,
                    cust_stnk.mobile as no_hp_cust_stnk,
                    ' ' as cust_corp,
                    employee.nip as nik_sales_name,
                    COALESCE(res_res.name,'') as sales_name, 
                    COALESCE(job.name,'') as job_name, 
                    employee_koord.nip as nik_sales_koor_name,
                    employee_koord.name_related as sales_koor_name, 
                    employee_spv.nip as spv_nik,
                    employee_spv.name_related as spv_name,
                    COALESCE(medi.default_code,'') as partner_komisi_id,
                    COALESCE(medi.name,'') as partner_komisi_name, 
                    COALESCE(hk.name,'') as hutang_komisi_id, 
                    COALESCE(dsol.amount_hutang_komisi,0) as amount_hutang_komisi, 
                    COALESCE((dsol.amount_hutang_komisi * 3)/100,0) as pph_komisi, 
                    COALESCE(lot.name,'') as lot_name, 
                    COALESCE(lot.chassis_no,'') as lot_chassis, 
                    COALESCE(product.name_template,'') as product_name,
                    COALESCE(product1.default_code,'') as product_desc,
                    COALESCE(pav.code,'') as pav_code, 
                    COALESCE(prod_category.name,'') as categ_name, 
                    COALESCE(prod_category2.name,'') as categ2_name, 
                    COALESCE(prod_template.series,'') as prod_series, 
                    lot.tahun as tahun_rakit,
                    COALESCE(dsol_disc.ps_ahm,0) as ps_ahm, 
                    COALESCE(dsol_disc.ps_md,0) as ps_md, 
                    COALESCE(dsol_disc.ps_finco,0) as ps_finco, 
                    COALESCE(dsol_disc.ps_dealer,0) as ps_dealer, 
                    0 as ps_other,
                    COALESCE(dsol_disc.ps_dealer,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0) as ps_total, 
                    COALESCE(dsol.price_unit,0) as price_unit, 
                    COALESCE(dsol.price_unit/1.1,0) as sales, 
                    COALESCE(dsol.discount_po,0)+COALESCE(dsol_disc.discount_pelanggan,0) as disc_total, 
                    COALESCE(dsol.discount_po,0) as discount_po, 
                    disc_ext_int.disc_extern as discount_extern_ps, 
                    disc_ext_int.disc_intern as discount_intern_ps,
                    COALESCE(dsol_disc_not.discount_pelanggan,0) as disc_quo_incl_tax_no, 
                    COALESCE(dsol.price_bbn,0) as price_bbn, 
                    round(COALESCE(dsol.price_subtotal,0) + round(dsol.price_subtotal*0.1,2) + COALESCE(dsol.price_bbn,0)) as piutang_total, 
                    dsb.name as dsb_name,
                    dsbl.diskon_ahm as dsbl_diskon_ahm, 
                    dsbl.diskon_md as dsbl_diskon_md, 
                    dsbl.diskon_dealer as dsbl_diskon_dealer, 
                    dsbl.diskon_finco as dsbl_diskon_finco, 
                    dsbl.diskon_others as dsbl_diskon_others, 
                    dsbl.total_diskon as dsbl_total_diskon, 
                    COALESCE(dsol.discount_po,0)+COALESCE(dsol_disc.ps_dealer,0)+COALESCE(amount_hutang_komisi,0) as beban_cabang, 
                    COALESCE(dsol.price_subtotal,0) as price_subtotal,
                    round(dsol.price_subtotal*0.1,2) as ppn,
                    round(COALESCE(dsol.price_subtotal,0) + round(dsol.price_subtotal*0.1,2)) as total, 
                    COALESCE(dsol.force_cogs,0) as force_cogs, 
                    COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0) as gp_dpp_minus_hpp, 
                    COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0) as gp_unit, 
                    COALESCE(dsol.price_bbn_beli,0) as price_bbn_beli, 
                    COALESCE(dsol.price_bbn,0)-COALESCE(dsol.price_bbn_beli,0) as gp_bbn, 
                    (COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0))+(COALESCE(dsol.price_bbn,0)-COALESCE(dsol.price_bbn_beli,0)) as gp_total, 
                    insentif_finco as dpp_insentif_finco, 
                    0 as tambahan_bbn,
                    COALESCE(dsol.product_qty,0) as product_qty, 
                    case when dso.is_pic = 't' then 1 else 0 end as qty_pic,
                    case when rj.qty_retur = 1 then rj.qty_retur else 0 end as qty_retur,
                    case when rj.qty_retur = 1 then COALESCE(dsol.product_qty,0) - rj.qty_retur else COALESCE(dsol.product_qty,0) - 0 end as net_sales,
                    CONCAT(pro.number, ' ', pro.name) as proposal_id, 
                    pro.street as proposal_address,
                    cust.npwp as npwp_cust,
                    COALESCE(cust.npwp,'Non PKP') as pkp, 
                    ' ' as tax_type,
                    COALESCE(fp.name,'') as faktur_pajak, 
                    av_nde.number as or_name,
                    case when ar_days.date_cpa is not null then (ar_days.date_cpa::date - ai.date_invoice::date) + 1 else (now()::date - ai.date_invoice::date) + 1 end as ar_days,
                    --case when ar_days.date_cpa is not null then ar_days.date_cpa else null end AS tgl_lunas,
                    case when to_char(ar_days.date_cpa, 'DD-MM-YYYY') is not null then to_char(ar_days.date_cpa, 'DD-MM-YYYY') else null end AS tgl_lunas,
                    COALESCE(md.default_code || '-' || md.name,'') as md_code,
                    case when dso.is_pic = TRUE then 1 else 0 end as is_pic,
                    case when rj.qty_retur = 1 then 1 else 0 end as is_retur
                from    dealer_sale_order dso 
                left join dealer_spk spk on spk.dealer_sale_order_id = dso.id 
                left join dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id = dso.id 
                left join account_invoice ai on ai.origin = dso.name and left(ai.number,3) in ('NDE')
                --left join stock_picking sp on sp.origin = dso.name and sp.name not like '%KSU%'
                left join ( select sp.name as name, sp.origin as origin, sp.state as state, sm.product_id as product_id
                    from stock_picking sp
                    left join stock_move sm on sm.picking_id = sp.id
                    where sm.restrict_lot_id is not null) sp on sp.origin = dso.name and sp.product_id = dsol.product_id and sp.name not like '%KSU%'
                --left join stock_move sm ON sm.dealer_sale_order_line_id = dsol.id and sm.state not in ('done','cancel','draft') and sm.product_id != dsol.product_id 
                left join dym_hutang_komisi hk ON dsol.hutang_komisi_id = hk.id 
                --left join res_partner rhk ON hk.name = rhk.name
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
                left join ( select dealer_sale_order_line_discount_line_id, sum(ps_finco) as ps_finco, sum(ps_ahm) as ps_ahm, sum(ps_md) as ps_md, sum(ps_dealer) as ps_dealer, 
                        sum(ps_others) as ps_others, sum(discount) as discount, sum(discount_pelanggan) as discount_pelanggan 
                        from dealer_sale_order_line_discount_line group by dealer_sale_order_line_discount_line_id ) dsol_disc ON dsol_disc.dealer_sale_order_line_discount_line_id = dsol.id 
                left join ( select dealer_sale_order_line_discount_line_id, sum(discount_pelanggan) as discount_pelanggan 
                        from dealer_sale_order_line_discount_line where include_invoice = 'f'
                        group by dealer_sale_order_line_discount_line_id ) dsol_disc_not ON dsol_disc_not.dealer_sale_order_line_discount_line_id = dsol.id 
                left join ( select dealer_sale_order_line_discount_line_id, sum(discount_pelanggan) as discount_pelanggan 
                        from dealer_sale_order_line_discount_line where include_invoice = 't' 
                        group by dealer_sale_order_line_discount_line_id ) dsol_disc_yes ON dsol_disc_yes.dealer_sale_order_line_discount_line_id = dsol.id 
                --left join sale_member_empl_rel smer ON smer.id = empl_id.register_spk_id 
                --left join dym_stock_packing_line dspl ON dspl.engine_number = lot.name
                left join dealer_register_spk_line drsl ON drsl.id = dso.register_spk_id 
                left join dym_area_cabang_rel dacr on dacr.branch_id = b.id and dacr.area_id in (532,533,534,535,536,537,538,539)
                left join dym_area area on area.id = dacr.area_id and area.id in (532,533,534,535,536,537,538,539)
                --left join dym_retur_jual drj on drj.dso_id = dso.id
                left join (select dso.name as dso_name, count(*) as qty_retur from dym_retur_jual drj left join dealer_sale_order dso on dso.id = drj.dso_id where drj.state in ('approved','done') group by dso.name) rj on rj.dso_name = dso.name
                left join dealer_sale_order_line_brgbonus_line dsolbl on dsolbl.dealer_sale_order_line_brgbonus_line_id = dsol.id
                left join dym_subsidi_barang dsb on dsb.id = dsolbl.barang_subsidi_id
                left join dym_subsidi_barang_line dsbl on dsbl.subsidi_barang_id = dsb.id and dsbl.product_id = dsol.template_id
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
                left join ( select string_agg(distinct(number), ', ') as number, reference as reference 
                            from account_voucher 
                            group by reference) av_nde on av_nde.reference = dso.name
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

        query_where = " WHERE dso.state in ('progress','done') and spk.state not in ('draft','cancelled') "
        if data['start_date']:
            query_where += " and dso.date_order >= '%s'" % str(data['start_date'])
        if data['end_date']:
            query_where += " and dso.date_order <= '%s'" % str(data['end_date'])
        if data['branch_ids']:
            query_where += " and dso.branch_id in %s" % str(tuple(data['branch_ids'])).replace(',)', ')')
        query_group = """   group by dso.id, drsl.name, dsol.price_subtotal, dsol.price_bbn, b.branch_status, b.code, spk.name, dcp.name, b.name, md.default_code, finco.name, employee_koord.name_related,
                            res_res.name, job.name, cust.default_code, cust.name, cust_stnk.name, cust.npwp, product.name_template, pav.code, dsol.product_qty, lot.name, lot.chassis_no, dsol.price_unit,
                            dsol.discount_po, dsol_disc.ps_dealer, dsol_disc.ps_ahm, dsol_disc.ps_md, dsol_disc.ps_finco, dsol_disc_yes.discount_pelanggan, dsol_disc_not.discount_pelanggan, dsol_disc.discount_pelanggan,
                            dsol.force_cogs, dsol.price_bbn_beli, dsol.amount_hutang_komisi, dsol.insentif_finco, prod_category.name, prod_category2.name, prod_template.series, fp.name, hk.name, pro.number, 
                            pro.name, sp.state, sp.name, cust.mobile, cust_stnk.mobile, dsol.finco_no_po, dsol.finco_tgl_po, dsol.id, dcp_partner.name,
                            cust_stnk.default_code, md.name, product1.default_code, medi.default_code, medi.name, area.code, dcp_finco.name, cust.street, cust.rt, cust.rw, cust.kelurahan,
                            cust.kecamatan, city.name, state.name, cust_stnk.street, cust_stnk.rt, cust_stnk.rw, cust_stnk.kelurahan, cust_stnk.kecamatan, city_stnk.name, state_stnk.name,
                            finco.default_code, employee_koord.nip, employee.nip, rj.qty_retur, pro.street, employee_spv.nip, employee_spv.name_related, dsb.name, dsbl.diskon_ahm, dsbl.diskon_md, ar_days.date_cpa, ai.write_date,
                            dsbl.diskon_dealer, dsol.finco_tenor, dsbl.diskon_finco, dsbl.diskon_others, dsbl.total_diskon, lot.tahun, disc_ext_int.disc_extern, disc_ext_int.disc_intern, ai.number, ai.date_invoice, ai.state, av_nde.number
                        """
        query_order = " order by b.name, ai.number"

        self.cr.execute(query_rjualsdb + query_where + query_group + query_order)
        # raise osv.except_osv(('Perhatian !'), ("No \'%s\' ...")%(query_rjualsdb + query_where + query_group + query_order))
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                # 'id_dso': x['id_dso'],
                'no': 0,
                # 'id_dso': x['id_dso'],
                # 'id_dsol': x['id_dsol'],
                'state_ksu': x['state_picking'],
                'state_picking': x['state_picking'],
                'oos_number': x['oos_number'],
                'no_registrasi': x['no_registrasi'],
                'branch_status': x['branch_status'],
                'branch_code': x['branch_code'],
                'branch_name': x['branch_name'],
                'invoice_number': x['invoice_number'],
                'invoice_date': x['invoice_date'],
                'invoice_status': x['invoice_status'],
                'md_code': x['md_code'],
                'spk_name': x['spk_name'],
                'name': x['name'],
                'state': x['state'],
                'date_order': x['date_order'],
                'finco_code': x['finco_code'],
                'is_cod': x['is_cod'],
                'sales_koor_name': x['sales_koor_name'],
                'sales_name': x['sales_name'],
                'job_name': x['job_name'],
                'cust_code': x['cust_code'],
                'cust_stnk_code' : x['cust_stnk_code'],
                'cust_name': x['cust_name'],
                'cust_stnk_name': x['cust_stnk_name'],
                'pkp': x['pkp'],
                'product_name': x['product_name'],
                'product_desc': x['product_desc'],
                'pav_code': x['pav_code'],
                'product_qty': x['product_qty'],
                'lot_name': x['lot_name'],
                'lot_chassis': x['lot_chassis'],
                'price_unit': x['price_unit'],
                'discount_po': x['discount_po'],
                'ps_dealer': x['ps_dealer'],
                'ps_ahm': x['ps_ahm'],
                'ps_md': x['ps_md'],
                'cabang_partner': x['cabang_partner'],
                'ps_finco': x['ps_finco'],
                'ps_total': x['ps_total'],
                'sales': x['sales'],
                # 'disc_reg': x['disc_reg'],
                # 'disc_quo': x['disc_quo'],
                # 'disc_quo_incl_tax': x['disc_quo_incl_tax'],
                'disc_total': x['disc_total'],
                'price_subtotal': x['price_subtotal'],
                # 'piutang_dp': x['piutang_dp'],
                # 'piutang': x['piutang'],
                'piutang_total': x['piutang_total'],
                'PPN': x['ppn'],
                'total': x['total'],
                'force_cogs': x['force_cogs'],
                'gp_dpp_minus_hpp': x['gp_dpp_minus_hpp'],
                'gp_unit': x['gp_unit'],
                'amount_hutang_komisi': x['amount_hutang_komisi'],
                'dpp_insentif_finco': x['dpp_insentif_finco'],
                'price_bbn': x['price_bbn'],
                'price_bbn_beli': x['price_bbn_beli'],
                'pph_komisi': x['pph_komisi'],
                'gp_bbn': x['gp_bbn'],
                'gp_total': x['gp_total'],
                'beban_cabang': x['beban_cabang'],
                'categ_name': x['categ_name'],
                'categ2_name': x['categ2_name'],
                'prod_series': x['prod_series'],
                'faktur_pajak': x['faktur_pajak'],
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
                'tenor': x['tenor'],
                # 'dso_amount': x['dso_amount'],
                'area' : x['area'],
                # 'region' : x['region'],
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
                # 'vchannel' : x['vchannel'],
                # 'pmd_reff' : x['pmd_reff'],
                'proposal_address' : x['proposal_address'],
                # 'trans' : x['trans'],
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
                'last_update_time':x['last_update_time'],
                'or_name':x['or_name'],
                'ar_days':x['ar_days'],
                'tgl_lunas':x['tgl_lunas'],
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            reports = [{'datas': [{
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
                # 'piutang_dp': 0,
                # 'piutang': 0,
                'piutang_total': 0,
                'total': 0,
                # 'disc_reg': 0,
                # 'disc_quo': 0,
                # 'disc_quo_incl_tax': 0,
                'disc_quo_incl_tax_no': 0,
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
                'tenor': 0,
                'no_po': 'NO DATA FOUND',
                'area' : 'NO DATA FOUND',
                # 'region' : 'NO DATA FOUND',
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
                # 'vchannel' : 'NO DATA FOUND',
                # 'pmd_reff' : 'NO DATA FOUND',
                'proposal_address' : 'NO DATA FOUND',
                # 'trans' : 'NO DATA FOUND',
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
                'faktur_pajak': 'NO DATA FOUND'
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(dym_report_rjualsdb_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_rjualsdb_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_rjualsdb.report_rjualsdb'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_rjualsdb.report_rjualsdb'
    _wrapped_report_class = dym_report_rjualsdb_print
    