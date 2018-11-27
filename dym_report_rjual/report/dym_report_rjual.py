from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_rjual_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_rjual_print, self).__init__(cr, uid, name, context=context)
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
        
        query_rjual = """
            select  dso.id as id_dso, 
                    COALESCE(drsl.name, '') as no_registrasi, 
                    round(COALESCE(dsol.price_subtotal,0) + round(dsol.price_subtotal*0.1,2) + COALESCE(dsol.price_bbn,0)) as piutang_total, 
                    round(COALESCE(dsol.price_subtotal,0) + round(dsol.price_subtotal*0.1,2)) as total, 
                    COALESCE(b.branch_status,'') as branch_status, COALESCE(b.code,'') as branch_code,
                    COALESCE(spk.name,'') as spk_name, 
                    COALESCE(dcp.name,'') as cabang_partner, 
                    COALESCE(ai.number,'') as invoice_number, 
                    COALESCE(ai.date_invoice,null) as invoice_date, 
                    COALESCE(ai.state,'') as invoice_status, 
                    COALESCE(b.name,'') as branch_name, 
                    COALESCE(md.default_code,'') as md_code, 
                    COALESCE(dso.name,'') as name, 
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
                    case when dso.is_pic <> 't' then COALESCE(cust_stnk.name,'') else '' end as cust_stnk_name, 
                    COALESCE(cust.npwp,'Non PKP') as pkp, 
                    COALESCE(product.name_template,'') as product_name, 
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
                    COALESCE(dsol.discount_po/1.1,0)+COALESCE(dsol_disc.discount_pelanggan/1.1,0) as disc_total, 
                    COALESCE(dsol.price_subtotal,0) as price_subtotal, 
                    round(dsol.price_subtotal*0.1,2) as PPN, 
                    COALESCE(dsol.force_cogs,0) as force_cogs, 
                    COALESCE(dso.customer_dp,0) as piutang_dp, 
                    round(COALESCE(dsol.price_subtotal,0) + round(dsol.price_subtotal*0.1,2) + COALESCE(dsol.price_bbn,0)) - COALESCE(dso.customer_dp,0) as piutang,
                    --CASE WHEN finco.name = 'PT. ADIRA DINAMIKA MULTI FINANCE TBK.' THEN round((COALESCE(dsol.price_unit,0) + COALESCE(dsol.price_bbn,0) - COALESCE(dsol.discount_po,0))) - COALESCE(dso.customer_dp,0) 
                    -- ELSE round(COALESCE(dsol.price_unit,0) + COALESCE(dsol.price_bbn,0) - COALESCE(dsol.discount_po,0) - COALESCE(dsol_disc.discount_pelanggan,0)) - COALESCE(dso.customer_dp,0) END as piutang, 
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
                    COALESCE(dsol.discount_po/1.1,0)+COALESCE(dsol_disc.ps_dealer/1.1,0)+COALESCE(amount_hutang_komisi,0) as beban_cabang, 
                    COALESCE(prod_category.name,'') as categ_name, 
                    COALESCE(prod_category2.name,'') as categ2_name, 
                    COALESCE(prod_template.series,'') as prod_series, 
                    COALESCE(fp.name,'') as faktur_pajak, 
                    --COALESCE(rhk.default_code,'') as partner_komisi_id, 
                    '' as partner_komisi_id, 
                    COALESCE(hk.name,'') as hutang_komisi_id, 
                    CONCAT(pro.number, ' ', pro.name) as proposal_id, 
                    CASE WHEN sp.state = 'draft' THEN 'Draft' 
                        WHEN sp.state = 'cancel' THEN 'Cancelled'
                        WHEN sp.state = 'waiting' THEN 'Waiting Another Operation' 
                        WHEN sp.state = 'confirmed' THEN 'Waiting Availability' 
                        WHEN sp.state = 'partially_available' THEN 'Partially Available' 
                        WHEN sp.state = 'assigned' THEN 'Ready to Transfer' 
                        WHEN sp.state = 'done' THEN 'Transferred' 
                    ELSE sp.state END as state_picking, 
                    case when sp.state is null then 'Undelivered' else 'Delivered' end as state_ksu,
                    sp.name as oos_number,
                    employee_spv.name_related as spv_name,
                    cust.mobile as no_hp_cust_beli, 
                    cust_stnk.mobile as no_hp_cust_stnk,
                    --dspl.tahun_pembuatan as tahun_rakit,
                    lot.tahun as tahun_rakit,
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
                        when finco.name = 'PT. SUMMIT OTTO FINANCE' then 'SOF-' || cust.name 
                        when finco.name = 'PT. WAHANA OTTOMITRA MULTIARTHA' then 'WOM-' || cust.name 
                    else 'CASH-' || cust.name end as "Customer",
                    av_nde.number as or_name,
                    case when ar_days.date_cpa is not null then (ar_days.date_cpa::date - ai.date_invoice::date) + 1 else (now()::date - ai.date_invoice::date) + 1 end as ar_days,
                    case when ar_days.date_cpa is not null then ar_days.date_cpa else null end AS tgl_lunas
                from    dealer_sale_order dso 
                left join dealer_spk spk on spk.dealer_sale_order_id = dso.id 
                left join dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id = dso.id 
                left join account_invoice ai on ai.origin = dso.name and left(ai.number,3) in ('NDE')
                --left join stock_picking sp on sp.origin = dso.name 
                left join ( select sp.name as name, sp.origin as origin, sp.state as state, sm.product_id as product_id
                        from stock_picking sp
                        left join stock_move sm on sm.picking_id = sp.id
                        where sm.restrict_lot_id is not null) sp on sp.origin = dso.name and sp.product_id = dsol.product_id and sp.name not like 'KSU%'
                --left join stock_move sm ON sm.dealer_sale_order_line_id = dsol.id and sm.state not in ('done','cancel','draft') and sm.product_id != dsol.product_id 
                left join dym_hutang_komisi hk ON dsol.hutang_komisi_id = hk.id 
                --left join res_partner rhk ON hk.name = rhk.name
                left join res_partner medi ON dso.partner_komisi_id = medi.id 
                left join dym_proposal_event pro ON dso.proposal_id = pro.id 
                left join dym_branch b ON dso.branch_id = b.id 
                left join res_partner md ON b.default_supplier_id = md.id 
                left join res_partner finco ON dso.finco_id = finco.id 
                left join hr_employee employee ON dso.employee_id = employee.id 
                left join dealer_register_spk_line drsl ON drsl.id = dso.register_spk_id 
                left join resource_resource res_res ON employee.resource_id = res_res.id 
                left join hr_job job ON employee.job_id = job.id 
                left join crm_case_section crm ON dso.section_id = crm.id 
                left join hr_employee employee_koord ON employee_koord.id = crm.employee_id 
                left join res_partner cust ON dso.partner_id = cust.id 
                left join res_partner cust_stnk ON dsol.partner_stnk_id = cust_stnk.id 
                left join crm_case_section crm_spv ON crm.parent_id = crm_spv.id 
                left join hr_employee employee_spv ON employee_spv.id = crm_spv.employee_id 
                left join product_product product ON dsol.product_id = product.id 
                left join product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id 
                left join product_attribute_value pav ON pavpp.att_id = pav.id 
                left join product_template prod_template ON product.product_tmpl_id = prod_template.id 
                left join product_category prod_category ON prod_template.categ_id = prod_category.id 
                left join product_category prod_category2 ON prod_category.parent_id = prod_category2.id 
                left join stock_production_lot lot ON dsol.lot_id = lot.id 
                left join dym_faktur_pajak_out fp ON dso.faktur_pajak_id = fp.id 
                left join dym_cabang_partner dcp ON dcp.id = spk.partner_cabang 
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
                            dsol.force_cogs, dsol.price_bbn_beli, dsol.amount_hutang_komisi, dsol.insentif_finco, prod_category.name, prod_category2.name, prod_template.series, fp.name, hk.name, pro.number, pro.name, 
                            sp.state, sp.name, cust.mobile, cust_stnk.mobile, dsol.finco_no_po, dsol.finco_tgl_po,employee_spv.name_related, lot.tahun, ai.number, ai.date_invoice, ai.state, ar_days.date_cpa, av_nde.number
                        """
        query_order = " order by 6,11"

        self.cr.execute(query_rjual + query_where + query_group + query_order)
        # raise osv.except_osv(('Perhatian !'), ("No \'%s\' ...")%(query_rjual + query_where + query_group + query_order))
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                # 'id_dso': x['id_dso'],
                'no': 0,
                'branch_status': x['branch_status'],
                'branch_code': x['branch_code'],
                'branch_name': x['branch_name'],
                'no_registrasi': x['no_registrasi'],
                'spk_name': x['spk_name'],
                'name': x['name'],
                'date_order': x['date_order'],
                'state': x['state'],
                'state_ksu': x['state_ksu'],
                'state_picking': x['state_picking'],
                'oos_number': x['oos_number'],
                'invoice_number': x['invoice_number'],
                'invoice_date': x['invoice_date'],
                'invoice_status': x['invoice_status'],
                'finco_code': x['finco_code'],
                'is_cod': x['is_cod'],
                'cust_code': x['cust_code'],
                'cust_name': x['cust_name'],
                'cabang_partner': x['cabang_partner'],
                'cust_stnk_name': x['cust_stnk_name'],
                'product_name': x['product_name'],
                'pav_code': x['pav_code'],
                'product_qty': x['product_qty'],
                'lot_name': x['lot_name'],
                'lot_chassis': x['lot_chassis'],
                'price_unit': x['price_unit'],
                'discount_po': x['discount_po'],
                'ps_dealer': x['ps_dealer'],
                'ps_ahm': x['ps_ahm'],
                'ps_md': x['ps_md'],    
                'ps_finco': x['ps_finco'],
                'ps_total': x['ps_total'],
                'sales': x['sales'],
                'disc_quo_incl_tax_no': x['disc_quo_incl_tax_no'],
                'disc_quo_incl_tax': x['disc_quo_incl_tax'],
                'disc_reg': x['disc_reg'],
                'disc_quo': x['disc_quo'],
                'disc_total': x['disc_total'],
                'price_subtotal': x['price_subtotal'],
                'PPN': x['ppn'],
                'total': x['total'],
                'force_cogs': x['force_cogs'],
                'piutang_dp': x['piutang_dp'],
                'piutang': x['piutang'],
                'piutang_total': x['piutang_total'],
                'gp_dpp_minus_hpp': x['gp_dpp_minus_hpp'],
                'gp_unit': x['gp_unit'],
                'price_bbn': x['price_bbn'],
                'price_bbn_beli': x['price_bbn_beli'],
                'gp_bbn': x['gp_bbn'],
                'gp_total': x['gp_total'],
                'partner_komisi_id': x['partner_komisi_id'],
                'hutang_komisi_id': x['hutang_komisi_id'],
                'amount_hutang_komisi': x['amount_hutang_komisi'],
                'pph_komisi': x['pph_komisi'],
                'dpp_insentif_finco': x['dpp_insentif_finco'],
                'beban_cabang': x['beban_cabang'],
                'ar_days':x['ar_days'],
                'tgl_lunas':x['tgl_lunas'],
                'categ_name': x['categ_name'],
                'categ2_name': x['categ2_name'],
                'prod_series': x['prod_series'],
                'faktur_pajak': x['faktur_pajak'],
                'pkp': x['pkp'],
                'proposal_id': x['proposal_id'],
                'or_name':x['or_name'],
                'sales_name': x['sales_name'],
                'job_name': x['job_name'],
                'sales_koor_name': x['sales_koor_name'],
                'spv_name': x['spv_name'],
                'md_code': x['md_code'],
                'no_hp_cust_beli' : x['no_hp_cust_beli'],
                'no_hp_cust_stnk' : x['no_hp_cust_stnk'],
                'tahun_rakit' : x['tahun_rakit'],
                'no_po': x['no_po'],
                'tgl_po': x['tgl_po'],
                # 'cust_stnk_code' : x['cust_stnk_code'],
                # 'product_desc': x['product_desc'],
                # 'partner_komisi_name': x['partner_komisi_name'],
                # 'tenor': x['tenor'],
                # # 'dso_amount': x['dso_amount'],
                # 'area' : x['area'],
                # # 'region' : x['region'],
                # 'ps_other' : x['ps_other'],
                # 'jp_po' : x['jp_po'],
                # 'discount_extern_ps' : x['discount_extern_ps'],
                # 'discount_intern_ps' : x['discount_intern_ps'],
                # 'finco_branch' : x['finco_branch'],
                # 'alamat_cust_name' : x['alamat_cust_name'],
                # 'kota_cust_name' : x['kota_cust_name'],
                # 'alamat_cust_stnk_name' : x['alamat_cust_stnk_name'],
                # 'kota_cust_stnk_name' : x['kota_cust_stnk_name'],
                # 'jns_kota_cust_stnk_name' : x['jns_kota_cust_stnk_name'],
                # 'kec_cust_stnk_name' : x['kec_cust_stnk_name'],
                # 'kel_cust_stnk_name' : x['kel_cust_stnk_name'],
                # 'nik_sales_koor_name' : x['nik_sales_koor_name'],
                # 'nik_sales_name' : x['nik_sales_name'],
                # 'tax_type' : x['tax_type'],
                # 'tambahan_bbn' : x['tambahan_bbn'],
                # 'cust_corp' : x['cust_corp'],
                # 'qty_pic' : x['qty_pic'],
                # 'qty_retur' : x['qty_retur'],
                # 'net_sales' : x['net_sales'],
                # # 'vchannel' : x['vchannel'],
                # # 'pmd_reff' : x['pmd_reff'],
                # 'proposal_address' : x['proposal_address'],
                # # 'trans' : x['trans'],
                # 'npwp_cust' : x['npwp_cust'],
                # 'sls_pay' : x['sls_pay'],
                # 'vcust_id': x['vcust_id'],
                # 'spv_nik': x['spv_nik'],
                # 'dsb_name':x['dsb_name'],
                # 'dsbl_diskon_ahm':x['dsbl_diskon_ahm'],
                # 'dsbl_diskon_md':x['dsbl_diskon_md'],
                # 'dsbl_diskon_dealer':x['dsbl_diskon_dealer'],
                # 'dsbl_diskon_finco':x['dsbl_diskon_finco'],
                # 'dsbl_diskon_others':x['dsbl_diskon_others'],
                # 'dsbl_total_diskon':x['dsbl_total_diskon'],
                # 'last_update_time':x['last_update_time'],
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            reports = [{'datas': [{
                'no': 'NO DATA FOUND',
                'branch_status': 'NO DATA FOUND',
                'branch_code': 'NO DATA FOUND',
                'branch_name': 'NO DATA FOUND',
                'no_registrasi': 'NO DATA FOUND',
                'spk_name': 'NO DATA FOUND',
                'name': 'NO DATA FOUND',
                'date_order': 'NO DATA FOUND',
                'state': 'NO DATA FOUND',
                'state_ksu': 'NO DATA FOUND',
                'state_picking': 'NO DATA FOUND',
                'oos_number': 'NO DATA FOUND',
                'invoice_number': 'NO DATA FOUND',
                'invoice_date': 'NO DATA FOUND',
                'invoice_status': 'NO DATA FOUND',
                'finco_code': 'NO DATA FOUND',
                'is_cod': 'NO DATA FOUND',
                'cust_code': 'NO DATA FOUND',
                'cust_name': 'NO DATA FOUND',
                'cabang_partner': 'NO DATA FOUND',
                'cust_stnk_name': 'NO DATA FOUND',
                'product_name': 'NO DATA FOUND',
                'pav_code': 'NO DATA FOUND',
                'product_qty': 0,
                'lot_name': 'NO DATA FOUND',
                'lot_chassis': 'NO DATA FOUND',
                'price_unit': 0,
                'discount_po': 0,
                'ps_dealer': 0,
                'ps_ahm': 0,
                'ps_md': 0,
                'ps_finco': 0,
                'ps_total': 0,
                'sales': 0,
                'disc_quo_incl_tax_no': 0,
                'disc_quo_incl_tax': 0,
                'disc_reg': 0,
                'disc_quo': 0,
                'disc_total': 0,
                'price_subtotal': 0,
                'PPN': 0,
                'total': 0,
                'force_cogs': 0,
                'piutang_dp': 0,
                'piutang': 0,
                'piutang_total': 0,
                'gp_dpp_minus_hpp': 0,
                'gp_unit': 0,
                'price_bbn': 0,
                'price_bbn_beli': 0,
                'gp_bbn': 0,
                'gp_total': 0,
                'partner_komisi_id': 'NO DATA FOUND',
                'hutang_komisi_id': 'NO DATA FOUND',
                'amount_hutang_komisi': 0,
                'pph_komisi': 0,
                'dpp_insentif_finco': 0,
                'beban_cabang': 0,
                'ar_days': 0,
                'tgl_lunas': 'NO DATA FOUND',
                'categ_name': 'NO DATA FOUND',
                'categ2_name': 'NO DATA FOUND',
                'prod_series': 'NO DATA FOUND',
                'faktur_pajak': 'NO DATA FOUND',
                'pkp': 'NO DATA FOUND',
                'proposal_id': 'NO DATA FOUND',
                'or_name': 'NO DATA FOUND',
                'sales_name': 'NO DATA FOUND',
                'job_name': 'NO DATA FOUND',
                'sales_koor_name': 'NO DATA FOUND',
                'spv_name': 'NO DATA FOUND',
                'md_code': 'NO DATA FOUND',
                'no_hp_cust_beli' : 'NO DATA FOUND',
                'no_hp_cust_stnk' : 'NO DATA FOUND',
                'tahun_rakit' : 'NO DATA FOUND',
                'no_po': 'NO DATA FOUND',
                'tgl_po': 'NO DATA FOUND'

                # 'no': 'NO DATA FOUND',
                # 'state_ksu': 'NO DATA FOUND',
                # 'invoice_number': 'NO DATA FOUND',
                # 'invoice_status': 'NO DATA FOUND',
                # 'invoice_date': 'NO DATA FOUND',
                # 'effective_date': 'NO DATA FOUND',
                # 'state_ksu': 'NO DATA FOUND',
                # 'state_picking' : 'NO DATA FOUND',
                # 'oos_number' : 'NO DATA FOUND',
                # 'branch_status': 'NO DATA FOUND',
                # 'no_registrasi' : 'NO DATA FOUND',
                # 'branch_code': 'NO DATA FOUND',
                # 'branch_name': 'NO DATA FOUND',
                # 'analytic_1': 'NO DATA FOUND',
                # 'analytic_2': 'NO DATA FOUND',
                # 'analytic_3': 'NO DATA FOUND',
                # 'analytic_4': 'NO DATA FOUND',
                # 'analytic_combination': 'NO DATA FOUND',
                # 'md_code': 'NO DATA FOUND',
                # 'spk_name': 'NO DATA FOUND',
                # 'name': 'NO DATA FOUND',
                # 'state': 'NO DATA FOUND',
                # 'date_order': 'NO DATA FOUND',
                # 'finco_code': 'NO DATA FOUND',
                # 'is_cod': 'NO DATA FOUND',
                # 'sales_koor_name': 'NO DATA FOUND',
                # 'sales_name': 'NO DATA FOUND',
                # 'job_name': 'NO DATA FOUND',
                # 'cust_code': 'NO DATA FOUND',
                # 'cust_name': 'NO DATA FOUND',
                # 'cust_stnk_code' : 'NO DATA FOUND',
                # 'cust_stnk_name' : 'NO DATA FOUND',
                # 'proposal_id': 'NO DATA FOUND',
                # 'hutang_komisi_id': 'NO DATA FOUND',
                # 'partner_komisi_id': 'NO DATA FOUND',
                # 'partner_komisi_name': 'NO DATA FOUND',
                # 'or_name': 'NO DATA FOUND',
                # # 'or_amount': 0,
                # 'product_name': 'NO DATA FOUND',
                # 'product_desc': 'NO DATA FOUND',
                # 'pav_code': 'NO DATA FOUND',
                # 'product_qty': 0,
                # 'cabang_partner': 'NO DATA FOUND',
                # 'lot_name': 'NO DATA FOUND',
                # 'lot_chassis': 'NO DATA FOUND',
                # 'tgl_lunas': 'NO DATA FOUND',
                # 'ar_days': '0',
                # 'price_unit': 0,
                # 'discount_po': 0,
                # 'ps_dealer': 0,
                # 'ps_ahm': 0,
                # 'ps_md': 0,
                # 'ps_finco': 0,
                # 'ps_total': 0,
                # 'sales': 0,
                # # 'piutang_dp': 0,
                # # 'piutang': 0,
                # 'piutang_total': 0,
                # 'total': 0,
                # # 'disc_reg': 0,
                # # 'disc_quo': 0,
                # # 'disc_quo_incl_tax': 0,
                # 'disc_total': 0,
                # 'price_subtotal': 0,
                # 'PPN': 0,
                # 'force_cogs': 0,
                # 'tahun_rakit': 'NO DATA FOUND',
                # 'gp_dpp_minus_hpp': 0,
                # 'gp_unit': 0,
                # 'amount_hutang_komisi': 0,
                # 'dpp_insentif_finco': 0,
                # 'price_bbn': 0,
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
                # 'tgl_po': 'NO DATA FOUND',
                # 'tenor': 0,
                # 'no_po': 'NO DATA FOUND',
                # 'area' : 'NO DATA FOUND',
                # # 'region' : 'NO DATA FOUND',
                # 'last_update_time' : 'NO DATA FOUND',
                # 'ps_other' : 0,
                # 'jp_po' : 0,
                # 'discount_extern_ps' : 0,
                # 'discount_intern_ps' : 0,
                # 'finco_branch' : 'NO DATA FOUND',
                # 'alamat_cust_name':'NO DATA FOUND',
                # 'kota_cust_name' : 'NO DATA FOUND',
                # 'alamat_cust_stnk_name' : 'NO DATA FOUND',
                # 'kota_cust_stnk_name' : 'NO DATA FOUND',
                # 'jns_kota_cust_stnk_name' : 'NO DATA FOUND',
                # 'kec_cust_stnk_name' : 'NO DATA FOUND',
                # 'kel_cust_stnk_name' : 'NO DATA FOUND',
                # 'nik_sales_koor_name' : 'NO DATA FOUND',
                # 'nik_sales_name' : 'NO DATA FOUND',
                # 'tax_type' : 'NO DATA FOUND',
                # 'tambahan_bbn' : 0,
                # 'cust_corp' : 'NO DATA FOUND',
                # 'qty_pic' : 0,
                # 'qty_retur' : 0,
                # 'net_sales' : 0,
                # # 'vchannel' : 'NO DATA FOUND',
                # # 'pmd_reff' : 'NO DATA FOUND',
                # 'proposal_address' : 'NO DATA FOUND',
                # # 'trans' : 'NO DATA FOUND',
                # 'npwp_cust' : 'NO DATA FOUND',
                # 'sls_pay' : 'NO DATA FOUND',
                # 'vcust_id' : 'NO DATA FOUND',
                # 'spv_name' : 'NO DATA FOUND',
                # 'spv_nik' : 'NO DATA FOUND',
                # 'dsb_name': 'NO DATA FOUND',
                # 'dsbl_diskon_ahm': 0,
                # 'dsbl_diskon_md': 0,
                # 'dsbl_diskon_dealer': 0,
                # 'dsbl_diskon_finco': 0,
                # 'dsbl_diskon_others': 0,
                # 'dsbl_total_diskon': 0,
                # 'faktur_pajak': 'NO DATA FOUND'
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(dym_report_rjual_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_rjual_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_rjual.report_rjual'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_rjual.report_rjual'
    _wrapped_report_class = dym_report_rjual_print
    