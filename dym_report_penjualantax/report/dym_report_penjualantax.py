from datetime import datetime, date
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_penjualantax_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_penjualantax_print, self).__init__(cr, uid, name, context=context)
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
        partner_komisi_id = data['partner_komisi_id']
        proposal_id = data['proposal_id']
        hutang_komisi_id = data['hutang_komisi_id']
        state = data['state']
        branch_ids = data['branch_ids']
        finco_ids = data['finco_ids']
        segmen = data['segmen']
        branch_status = data['branch_status']

        title_short_prefix = ''
        
        report_penjualantax = {
            'type': '',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Penjualan Tax')}
        
        where_section_id = " 1=1 "
        if section_id :
            where_section_id = " dso.section_id = '%s'" % str(section_id)
        where_user_id = " 1=1 "
        if user_id :
            where_user_id = " dso.employee_id = '%s'" % str(user_id)
        where_partner_komisi_id = " 1=1 "
        if partner_komisi_id :
            where_partner_komisi_id = " dso.partner_komisi_id = '%s'" % str(partner_komisi_id)
        where_hutang_komisi_id = " 1=1 "
        if hutang_komisi_id :
            where_hutang_komisi_id = " dso.hutang_komisi_id = '%s'" % str(hutang_komisi_id)
        where_proposal_id = " 1=1 "
        if proposal_id :
            where_proposal_id_id = " dso.proposal_id = '%s'" % str(proposal_id)
        where_product_ids = " 1=1 "
        if product_ids :
            where_product_ids = " dsol.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " dso.date_order >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " dso.date_order <= '%s'" % str(end_date)
        where_state = " 1=1 "
        if state in ['progress','done'] :
            where_state = " dso.state = '%s'" % str(state)
        else :
            where_state = " dso.state in ('progress','done')"
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " dso.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        where_finco_ids = " 1=1 "
        if finco_ids :
            where_finco_ids = " dso.finco_id in %s" % str(
                tuple(finco_ids)).replace(',)', ')')
        
        query_penjualantax = "select dso.id as id_dso, " \
            "COALESCE(drsl.name, '') as no_registrasi, " \
            "round(COALESCE(dsol.price_subtotal,0) + round(dsol.price_subtotal*0.1,2) + COALESCE(dsol.price_bbn,0)) as piutang_total, " \
            "round(COALESCE(dsol.price_subtotal,0) + round(dsol.price_subtotal*0.1,2)) as total, " \
            "COALESCE(b.branch_status,'') as branch_status, " \
            "COALESCE(b.code,'') as branch_code, " \
            "COALESCE(spk.name,'') as spk_name, " \
            "COALESCE(dcp.name,'') as cabang_partner, " \
            "COALESCE(b.name,'') as branch_name, " \
            "COALESCE(md.default_code,'') as md_code, " \
            "COALESCE(dso.name,'') as name, " \
            "CASE WHEN dso.state = 'progress' THEN 'Sales Memo' " \
            "    WHEN dso.state = 'done' THEN 'Done' " \
            "    WHEN dso.state IS NULL THEN '' " \
            "    ELSE dso.state " \
            "END as state, " \
            "dso.date_order as date_order, " \
            "COALESCE(finco.name,'Cash') as finco_code, " \
            "CASE WHEN dso.is_cod = TRUE THEN 'COD' " \
            "    ELSE 'Reguler' " \
            "END as is_cod, " \
            "sm.id as stock_move_non_unit_id, " \
            "COALESCE(sales_koor.name,'') as sales_koor_name, " \
            "COALESCE(sales.name,'') as sales_name, " \
            "COALESCE(job.name,'') as job_name, " \
            "COALESCE(cust.default_code,'') as cust_code, " \
            "COALESCE(cust.name,'') as cust_name, " \
            "COALESCE(cust.npwp,'Non PKP') as pkp, " \
            "COALESCE(product.name_template,'') as product_name, COALESCE(pav.code,'') as pav_code, COALESCE(dsol.product_qty,0) as product_qty, " \
            "COALESCE(lot.name,'') as lot_name, COALESCE(lot.chassis_no,'') as lot_chassis, " \
            "COALESCE(dsol.price_unit,0) as price_unit, " \
            "COALESCE(dsol.discount_po,0) as discount_po, COALESCE(dsol_disc.ps_dealer,0) as ps_dealer, COALESCE(dsol_disc.ps_ahm,0) as ps_ahm, COALESCE(dsol_disc.ps_md,0) as ps_md, COALESCE(dsol_disc.ps_finco,0) as ps_finco, " \
            "COALESCE(dsol_disc.ps_dealer,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0) as ps_total, " \
            "COALESCE(dsol.price_unit/1.1,0) as sales, " \
            "COALESCE(dsol.discount_po/1.1,0) as disc_reg, COALESCE(dsol_disc.discount_pelanggan/1.1,0) as disc_quo, COALESCE(dsol_disc.discount_pelanggan) as disc_quo_incl_tax, " \
            "COALESCE(dsol.discount_po/1.1,0)+COALESCE(dsol_disc.discount_pelanggan/1.1,0) as disc_total, " \
            "COALESCE(dsol.price_subtotal,0) as price_subtotal, round(dsol.price_subtotal*0.1,2) as PPN, COALESCE(dsol.force_cogs,0) as force_cogs, " \
            "COALESCE(dso.customer_dp,0) as piutang_dp, " \
            "CASE WHEN finco.name = 'PT. ADIRA DINAMIKA MULTI FINANCE TBK.' THEN round((COALESCE(dsol.price_unit,0) + COALESCE(dsol.price_bbn,0) - COALESCE(dsol.discount_po,0))) - COALESCE(dso.customer_dp,0) " \
            "     ELSE round(COALESCE(dsol.price_unit,0) + COALESCE(dsol.price_bbn,0) - COALESCE(dsol.discount_po,0) - COALESCE(dsol_disc.discount_pelanggan,0)) - COALESCE(dso.customer_dp,0) " \
            "END as piutang, " \
            "COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0) as gp_dpp_minus_hpp, " \
            "COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0) as gp_unit, " \
            "COALESCE(dsol.price_bbn,0) as price_bbn, COALESCE(dsol.price_bbn_beli,0) as price_bbn_beli, COALESCE(dsol.price_bbn,0)-COALESCE(dsol.price_bbn_beli,0) as gp_bbn, " \
            "(COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0))+(COALESCE(dsol.price_bbn,0)-COALESCE(dsol.price_bbn_beli,0)) as gp_total, " \
            "0 as pph_komisi, " \
            "COALESCE(dsol.amount_hutang_komisi,0) as amount_hutang_komisi, " \
            "COALESCE(dsol.insentif_finco/1.1,0) as insentif_finco, insentif_finco as dpp_insentif_finco, " \
            "COALESCE(dsol.discount_po/1.1,0)+COALESCE(dsol_disc.ps_dealer/1.1,0)+COALESCE(amount_hutang_komisi,0) as beban_cabang, " \
            "COALESCE(prod_category.name,'') as categ_name, " \
            "COALESCE(prod_category2.name,'') as categ2_name, " \
            "COALESCE(prod_template.series,'') as prod_series, " \
            "COALESCE(fp.name,'') as faktur_pajak, " \
            "COALESCE(medi.name,'') as partner_komisi_id, " \
            "COALESCE(hk.name,'') as hutang_komisi_id, " \
            "CONCAT(pro.number, ' ', pro.name) as proposal_id, " \
            "CASE WHEN sp.state = 'draft' THEN 'Draft' " \
            "     WHEN sp.state = 'cancel' THEN 'Cancelled' " \
            "     WHEN sp.state = 'waiting' THEN 'Waiting Another Operation' " \
            "     WHEN sp.state = 'confirmed' THEN 'Waiting Availability' " \
            "     WHEN sp.state = 'partially_available' THEN 'Partially Available' " \
            "     WHEN sp.state = 'assigned' THEN 'Ready to Transfer' " \
            "     WHEN sp.state = 'done' THEN 'Transferred' " \
            "     ELSE sp.state " \
            "END as state_picking, " \
            "sp.name as oos_number " \
            "from dealer_sale_order dso " \
            "inner join dealer_spk spk on spk.dealer_sale_order_id = dso.id " \
            "inner join dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id = dso.id " \
            "left join stock_picking sp on sp.origin = dso.name " \
            "left join stock_move sm ON sm.dealer_sale_order_line_id = dsol.id and sm.state not in ('done','cancel','draft') and sm.product_id != dsol.product_id " \
            "left join dym_hutang_komisi hk ON dsol.hutang_komisi_id = hk.id " \
            "left join res_partner medi ON dso.partner_komisi_id = medi.id " \
            "left join dym_proposal_event pro ON dso.proposal_id = pro.id " \
            "left join dym_branch b ON dso.branch_id = b.id " \
            "left join res_partner md ON b.default_supplier_id = md.id " \
            "left join res_partner finco ON dso.finco_id = finco.id " \
            "left join hr_employee employee ON dso.employee_id = employee.id " \
            "left join resource_resource sales ON employee.resource_id = sales.id " \
            "left join hr_job job ON employee.job_id = job.id " \
            "left join crm_case_section sales_team ON dso.section_id = sales_team.id " \
            "left join hr_employee sales_leader ON sales_leader.id = sales_team.user_id " \
            "left join resource_resource sales_koor ON sales_leader.resource_id = sales_koor.id " \
            "left join res_partner cust ON dso.partner_id = cust.id " \
            "left join product_product product ON dsol.product_id = product.id " \
            "left join product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id " \
            "left join product_attribute_value pav ON pavpp.att_id = pav.id " \
            "left join product_template prod_template ON product.product_tmpl_id = prod_template.id " \
            "left join product_category prod_category ON prod_template.categ_id = prod_category.id " \
            "left join product_category prod_category2 ON prod_category.parent_id = prod_category2.id " \
            "left join stock_production_lot lot ON dsol.lot_id = lot.id " \
            "left join dym_faktur_pajak_out fp ON dso.faktur_pajak_id = fp.id " \
            "left join dym_cabang_partner dcp ON dcp.id = spk.partner_cabang " \
            "left join ( " \
            "select dealer_sale_order_line_discount_line_id, sum(ps_finco) as ps_finco, sum(ps_ahm) as ps_ahm, sum(ps_md) as ps_md, sum(ps_dealer) as ps_dealer, sum(ps_others) as ps_others, " \
            "sum(discount) as discount, sum(discount_pelanggan) as discount_pelanggan " \
            "from dealer_sale_order_line_discount_line " \
            "group by dealer_sale_order_line_discount_line_id " \
            ") dsol_disc ON dsol_disc.dealer_sale_order_line_discount_line_id = dsol.id " \
            "left join dealer_register_spk_line drsl ON drsl.id = dso.register_spk_id " \
            "WHERE " + where_section_id + " AND " + where_user_id + " AND " + where_product_ids + " AND " + where_start_date + " AND " + where_partner_komisi_id + " AND " + where_hutang_komisi_id + " AND " +where_proposal_id + " AND " + where_end_date + " AND " + where_state + " AND " + where_branch_ids + " AND " + where_finco_ids + " " \
            "order by b.code, dso.date_order"
            
        move_selection = ""
        report_info = _('')
        move_selection += ""
                
        reports = [report_penjualantax]
        for report in reports:
            cr.execute(query_penjualantax)
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
                        'cust_name': str(x['cust_name'].encode('ascii','ignore').decode('ascii')) if x['cust_name'] != None else '',
                        'pkp': str(x['pkp'].encode('ascii','ignore').decode('ascii')) if x['pkp'] != None else 'Non PKP',
                        'product_name': str(x['product_name'].encode('ascii','ignore').decode('ascii')) if x['product_name'] != None else '',
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
                        'hutang_komisi_id': x['hutang_komisi_id'],
                        'proposal_id': x['proposal_id']
                    },
                    
                    all_lines)
                for p in p_map:
                    if p['id_dso'] not in map(lambda x: x.get('id_dso', None), dso_ids):
                        records = filter(lambda x: x['id_dso'] == p['id_dso'], all_lines)
                        dso = self.pool.get('dealer.sale.order').browse(cr, uid, records[0]['id_dso'])
                        analytic_1_id, analytic_2_id, analytic_3_id, analytic_4_id = self.pool.get('account.analytic.account').get_analytical(cr, uid, dso.branch_id, 'Unit', False, 4, 'Sales')
                        analytic_1_name = self.pool.get('account.analytic.account').browse(cr, uid, analytic_1_id).name or ''
                        analytic_1 = self.pool.get('account.analytic.account').browse(cr, uid, analytic_1_id).code or ''

                        analytic_2_name = self.pool.get('account.analytic.account').browse(cr, uid, analytic_2_id).name or ''
                        analytic_2 = self.pool.get('account.analytic.account').browse(cr, uid, analytic_2_id).code or ''

                        analytic_3_name = self.pool.get('account.analytic.account').browse(cr, uid, analytic_3_id).name or ''
                        analytic_3 = self.pool.get('account.analytic.account').browse(cr, uid, analytic_3_id).code or ''
                        branch = dso.branch_id
                        branch_name = dso.branch_id.name
                        branch_status_1 = dso.branch_id.branch_status
                        branch_id = dso.branch_id.id

                        analytic_4_name = self.pool.get('account.analytic.account').browse(cr, uid, analytic_4_id).name or ''
                        analytic_4 = self.pool.get('account.analytic.account').browse(cr, uid, analytic_4_id).code or ''

                        if (branch and branch_ids and branch.id not in branch_ids) or (branch and branch_status and branch_status != branch.branch_status):
                            continue
                        analytic_2_branch = analytic_2
                        if analytic_2 in ['210','220','230']:
                            if branch_status_1 == 'H123':
                                analytic_2_branch = analytic_2[:2] + '1'
                            elif branch_status_1 == 'H23':
                                analytic_2_branch = analytic_2[:2] + '2'
                            else:
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
                        p.update({'invoice_status': ''})
                        p.update({'ar_days': '0'})
                        p.update({'tgl_lunas': ''})
                        voucher_ids = self.pool.get('account.voucher').search(cr, uid, ['|',('name','ilike',dso.name),('reference','ilike',dso.name)])
                        if voucher_ids:
                            vouchers = self.pool.get('account.voucher').browse(cr, uid, voucher_ids)
                            p.update({'or_name': ', '.join(vouchers.mapped('number'))})
                            #p.update({'or_amount': ', '.join([str(i) for i in vouchers.mapped('amount')])})
                        invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('origin','ilike',dso.name),('type','=','out_invoice')], limit=1)
                        if invoice_ids:
                            invoices = self.pool.get('account.invoice').browse(cr, uid, invoice_ids)
                            p.update({'invoice_number': ', '.join(invoices.mapped('internal_number'))})
                            p.update({'invoice_date': invoices.date_invoice and ', '.join(invoices.mapped('date_invoice')) or None})
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
                            inv_cust = invoices
                            if len(invoices) > 1:
                                inv_cust = invoices.filtered(lambda r: r.tipe == 'customer')
                            if inv_cust and inv_cust[0].state == 'paid' and inv_cust[0].payment_ids:
                                paid_date = inv_cust[0].payment_ids.sorted(key=lambda r: r.date)[len(inv_cust[0].payment_ids) - 1].date
                                paid_date = datetime.strptime(paid_date, '%Y-%m-%d')
                                paid_date = datetime.date(paid_date)
                                str_paid_date = paid_date.strftime('%Y-%m-%d')
                            else:
                                paid_date = date.today()
                                str_paid_date = ''
                            inv_date = inv_cust[0].date_invoice
                            if inv_date:
                                inv_date = datetime.strptime(inv_date, '%Y-%m-%d')
                                inv_date = datetime.date(inv_date)
                                date_diff = int((paid_date-inv_date).days)
                                p.update({'ar_days': str(date_diff)})
                                p.update({'tgl_lunas': str_paid_date})
                            else:
                                p.update({'ar_days': None})
                                p.update({'tgl_lunas': None})
                        dso_ids.append(p)
                dso_ids = sorted(dso_ids, key=lambda k: k['invoice_number'])
                report.update({'dso_ids': dso_ids})

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
                                'analytic_combination' : temp['analytic_combination'],
                                'gp_total' : z['gp_total'],
                                'price_bbn_beli' : z['price_bbn_beli'],
                                'ps_ahm' : z['ps_ahm'],
                                'invoice_date' : temp['invoice_date'],
                                'force_cogs' : z['force_cogs'],
                                'categ2_name' : z['categ2_name'],
                                'lot_chassis' : z['lot_chassis'],
                                'invoice_status' : temp['invoice_status'],
                                'partner_komisi_id' : temp['partner_komisi_id'],
                                'lot_name' : z['lot_name'],
                                'dpp_insentif_finco' : z['dpp_insentif_finco'],
                                'categ_name' : z['categ_name'],
                                'gp_unit' : z['gp_unit'],
                                'or_name' : temp['or_name'],
                                # 'or_amount' : str(temp['or_amount']),
                                'spk_name' : z['spk_name'],
                                'gp_dpp_minus_hpp' : z['gp_dpp_minus_hpp'],
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
            'proposal_id': 'NO DATA FOUND',
            'hutang_komisi_id': 'NO DATA FOUND',
            'partner_komisi_id': 'NO DATA FOUND',
            'or_name': 'NO DATA FOUND',
            # 'or_amount': 0,
            'product_name': 'NO DATA FOUND',
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
            'faktur_pajak': 'NO DATA FOUND'}], 'title_short': 'Laporan Penjualan Tax', 'type': '', 'title': ''}]
        
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_penjualantax_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_penjualantax_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

#register report
class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_penjualantax.report_penjualantax'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_penjualantax.report_penjualantax'
    _wrapped_report_class = dym_report_penjualantax_print
