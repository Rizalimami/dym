from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm
from openerp import SUPERUSER_ID

class dym_report_penjualan_sowo_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_penjualan_sowo_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def get_wo(self, data):
        cr = self.cr
        uid = self.uid
        context = self.context

        section_id = data['section_id']
        user_id = data['user_id']
        product_ids = data['product_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        state = data['state']
        category = data['category']
        branch_ids = data['branch_ids']

        title_short_prefix = ''
        
        user_brw = self.pool.get('res.users').browse(cr, uid, uid)
        user_branch_type = user_brw.branch_type        

        report_penjualan_sowo = {
            'type': '',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Penjualan WO')}
        
        where_section_id = " 1=1 "
        if section_id :
            where_section_id = " sp.section_id = '%s'" % str(section_id)
        where_user_id = " 1=1 "
        if user_id :
            where_user_id = " sp.employee_id = '%s'" % str(user_id)
        where_product_ids = " 1=1 "
        if product_ids :
            where_product_ids = " spl.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " sp.date >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " sp.date <= '%s 23:59:59'" % str(end_date)
        where_state = " 1=1 "
        if state in ['open','done'] :
            where_state = " sp.state = '%s'" % str(state)
        else :
            where_state = " sp.state in ('open','done')"
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " sp.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        where_categ = " 1=1 "
        if category:
            obj_categ = self.pool.get('product.category')
            all_categ_ids = obj_categ.search(cr, uid, [])
            categs = obj_categ.get_child_ids(cr, uid, all_categ_ids, category)
            if category == 'Sparepart':
                aksesoris_categs = obj_categ.get_child_ids(cr, uid, all_categ_ids, 'ACCESSORIES')
                where_categ = " prod_category.id in %s and prod_category.id not in %s " % (str(
                    tuple(categs)).replace(',)', ')'),str(
                    tuple(aksesoris_categs)).replace(',)', ')'))
            if category in ['ACCESSORIES','Service']:
                where_categ = " prod_category.id in %s " % (str(
                    tuple(categs)).replace(',)', ')'))

        query_penjualan_sowo = "select sp.id as id_sp, " \
            "COALESCE(b.branch_status,'') as branch_status,  " \
            "COALESCE(b.code,'') as branch_code,  "\
            "COALESCE(b.name,'') as branch_name,  "\
            "COALESCE(sp.name,'') as name,    "\
            "CASE WHEN sp.state = 'finished' THEN 'Finished'  "\
            "    WHEN sp.state = 'approved' THEN 'Approved'  "\
            "    WHEN sp.state = 'confirmed' THEN 'Confirmed'  "\
            "    WHEN sp.state = 'draft' THEN 'Draft'  "\
            "    WHEN sp.state IS NULL THEN ''  "\
            "    ELSE sp.state  "\
            "END as state,  "\
            "sp.date as date_order, "\
            "COALESCE(spc.name,'') as oos_number,  "\
            "spc.date as oos_tgl, "\
            "COALESCE(cust.name,'') as cust_name,  "\
            "tk.name as tipe_konsumen,"\
            "spl.product_id as product_id,  "\
            "COALESCE(prod_template.name,'') as product_name,  "\
            "COALESCE(prod_category.name,'') as categ_name,  "\
            "COALESCE(spl.product_qty,0) as product_qty, "\
            "COALESCE(spl.supply_qty,0) as supply_qty, "\
            "COALESCE(spl.price_unit,0) as price_unit,  "\
            "COALESCE(spl.discount_pcs,0) as discount_perpcs, "\
            "COALESCE(spl.discount,0) as discount,  "\
            "COALESCE(spl.discount_program,0) as discount_program,  "\
            "COALESCE(spl_db.discount_bundle,0) as discount_bundle,   "\
            "COALESCE(spl.supply_qty,0)*COALESCE(spl.price_unit,0)-COALESCE(spl.discount_program,0)-COALESCE(spl_db.discount_bundle,0)-COALESCE(spl.discount,0) as price_subtotal,  "\
            "COALESCE(fp.name,'') as faktur_pajak,"\
            "COALESCE(sales.name,'') as sales_name, "\
            "spl.id as spl_id "\
            "from dym_work_order sp " \
            "inner join dym_work_order_line spl on spl.work_order_id = sp.id " \
            "left join hr_employee employee ON sp.mekanik_id = employee.id " \
            "left join resource_resource sales ON employee.resource_id = sales.id " \
            "left join dym_branch b ON sp.branch_id = b.id " \
            "left join res_partner cust ON sp.customer_id = cust.id " \
            "left join product_product product ON spl.product_id = product.id " \
            "left join product_template prod_template ON product.product_tmpl_id = prod_template.id " \
            "left join product_category prod_category ON prod_template.categ_id = prod_category.id " \
            "left join dym_faktur_pajak_out fp ON sp.faktur_pajak_id = fp.id " \
            "left join ( " \
            "select db.wo_line_id, sum(db.diskon) as discount_bundle " \
            "from dym_work_order_bundle db " \
            "group by db.wo_line_id " \
            ") spl_db ON spl_db.wo_line_id = spl.id " \
            "left join stock_picking spc ON sp.name = spc.origin " \
            "left join tipe_konsumen tk ON sp.tipe_konsumen = tk.id " \
            "WHERE " + where_section_id + " AND " + where_categ + " AND " + where_user_id + " AND " + where_product_ids + " AND " + where_start_date + " AND " + where_end_date + " AND " + where_state + " AND " + where_branch_ids + " " \
            "order by prod_category.name, b.code, sp.date"
            
        reports = [report_penjualan_sowo]

        for report in reports:
            cr.execute(query_penjualan_sowo)
            all_lines = cr.dictfetchall()
            sp_ids = []

            if all_lines:
                def lines_map(x):
                        x.update({'docname': x['branch_code']})
                map(lines_map, all_lines)
                for cnt in range(len(all_lines)-1):
                    if all_lines[cnt]['id_sp'] != all_lines[cnt+1]['id_sp']:
                        all_lines[cnt]['draw_line'] = 1
                    else:
                        all_lines[cnt]['draw_line'] = 0
                all_lines[-1]['draw_line'] = 1

                p_map = map(
                    lambda x: {
                        'no': 0,
                        'id_sp': x['id_sp'],
                        'spl_id': x['spl_id'],
                        'branch_status': str(x['branch_status'].encode('ascii','ignore').decode('ascii')) if x['branch_status'] != None else '',
                        'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                        'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                        'name': str(x['name'].encode('ascii','ignore').decode('ascii')) if x['name'] != None else '',
                        'state': str(x['state'].encode('ascii','ignore').decode('ascii')) if x['state'] != None else '',
                        'date_order': str(x['date_order']) if x['date_order'] != None else False,
                        'sales_name': str(x['sales_name'].encode('ascii','ignore').decode('ascii')) if x['sales_name'] != None else '',
                        'cust_name': str(x['cust_name'].encode('ascii','ignore').decode('ascii')) if x['cust_name'] != None else '',
                        'product_name': str(x['product_name'].encode('ascii','ignore').decode('ascii')) if x['product_name'] != None else '',
                        'product_qty': x['product_qty'],
                        'supply_qty' : x['supply_qty'],
                        'price_unit': x['price_unit'],
                        'discount': x['supply_qty'] * x['discount_perpcs'],
                        'discount_program': x['discount_program'],
                        'discount_bundle': x['discount_bundle'],
                        'price_subtotal': x['price_subtotal'],
                        'categ_name': str(x['categ_name'].encode('ascii','ignore').decode('ascii')) if x['categ_name'] != None else '',
                        'faktur_pajak': str(x['faktur_pajak'].encode('ascii','ignore').decode('ascii')) if x['faktur_pajak'] != None else '',
                        'oos_number': str(x['oos_number'].encode('ascii','ignore').decode('ascii')) if x['oos_number'] != None else '',
                        'oos_tgl': str(x['oos_tgl'].encode('ascii','ignore').decode('ascii')) if x['oos_tgl'] != None else '',
                        'tipe_konsumen': x['tipe_konsumen'],
                        'hpp': 0,
                        'discount_perpcs':x['discount_perpcs'],
                        'product_id': x['product_id'],
                        'retur': 0
                    },
                    
                    all_lines)
                for p in p_map:
                    if p['spl_id'] not in map(
                            lambda x: x.get('spl_id', None), sp_ids):
                        sale_order = filter(lambda x: x['id_sp'] == p['id_sp'], all_lines)
                        sale_order_line = filter(lambda x: x['spl_id'] == p['spl_id'], all_lines)
                        if user_branch_type == 'HO':
                            wo = self.pool.get('dym.work.order').browse(cr, SUPERUSER_ID, sale_order[0]['id_sp'])
                            wo_line = self.pool.get('dym.work.order.line').browse(cr, SUPERUSER_ID, sale_order_line[0]['spl_id'])
                        else:
                            wo = self.pool.get('dym.work.order').browse(cr, uid, sale_order[0]['id_sp'])
                            wo_line = self.pool.get('dym.work.order.line').browse(cr, uid, sale_order_line[0]['spl_id'])
                        analytic_1_name = ''
                        analytic_2_name = ''
                        analytic_3_name = ''
                        analytic_4_name = ''
                        analytic_combination = ''
                        p.update({'lines': sale_order_line})
                        p.update({'analytic_1': analytic_1_name})
                        p.update({'analytic_2': analytic_2_name})
                        p.update({'analytic_3': analytic_3_name})
                        p.update({'analytic_4': analytic_4_name})
                        p.update({'analytic_combination': analytic_combination})
                        p.update({'category': ''})
                        p.update({'invoice_name': ''})
                        p.update({'invoice_date': ''})
                        p.update({'tgl_bayar': ''})
                        p.update({'bayar': 0})
                        p.update({'ar_bayar': 0})
                        p.update({'ar': 0})
                        if not wo_line.bundle_line:
                            if wo_line and wo_line.product_id.categ_id:
                                category = wo_line.product_id.categ_id
                                while (category.parent_id and category.bisnis_unit == False):
                                    category = category.parent_id
                                p.update({'category': category.name})
                                if category.name == 'Service':
                                    invoice_name = wo.get_no_invoice(wo.name,'Service')
                                else:
                                    invoice_name = wo.get_no_invoice(wo.name,'Sparepart')
                                invoice_date = wo.get_tanggal_invoice(wo.name)
                                inv_id = self.pool.get('account.invoice').search(cr, uid, [('number','=',invoice_name)], order='id desc', limit=1)
                                if inv_id:
                                    inv = self.pool.get('account.invoice').browse(cr, uid, inv_id)
                                    if inv.payment_ids:
                                        tgl_bayar = ', '.join(inv.payment_ids.mapped('date'))
                                        bayar = sum(inv.payment_ids.filtered(lambda r: r.date == inv.date_invoice).mapped('credit'))
                                        ar_bayar = sum(inv.payment_ids.filtered(lambda r: r.date != inv.date_invoice).mapped('credit'))
                                        ar = inv.residual
                                        p.update({'tgl_bayar': tgl_bayar})
                                        p.update({'bayar': bayar})
                                        p.update({'ar_bayar': ar_bayar})
                                        p.update({'ar': ar})
                                p.update({'invoice_name': invoice_name})
                                p.update({'invoice_date': invoice_date})
                            sp_ids.append(p)
                        else:
                            res = []
                            for line in wo_line.bundle_line:
                                dicts = {
                                    'lines': sale_order_line,
                                    'no': p['no'],
                                    'branch_status': p['branch_status'],
                                    'branch_code': p['branch_code'],
                                    'branch_name': p['branch_name'],
                                    'analytic_1': analytic_1_name,
                                    'analytic_2': analytic_2_name,
                                    'analytic_3': analytic_3_name,
                                    'analytic_4': analytic_4_name,
                                    'analytic_combination': analytic_combination,
                                    'name': p['name'],
                                    'state': p['state'],
                                    'date_order': p['date_order'],
                                    'sales_name': p['sales_name'],
                                    'cust_name': p['cust_name'],
                                    'product_name': line.product_id.name,
                                    'product_qty': line.product_uom_qty,
                                    'price_unit': line.price_bundle,
                                    'discount': 0,
                                    'discount_program': 0,
                                    'discount_bundle': line.diskon,
                                    'price_subtotal': (line.product_uom_qty * line.price_bundle) - line.diskon,
                                    'categ_name': line.product_id.categ_id.name,
                                    'faktur_pajak': p['faktur_pajak'],
                                    'category': '',
                                    'invoice_name': '',
                                    'invoice_date': '',
                                    'tgl_bayar': '',
                                    'bayar': 0,
                                    'ar_bayar': 0,
                                    'ar': 0,
                                }
                                if line and line.product_id.categ_id:
                                    category = line.product_id.categ_id
                                    while (category.parent_id and category.bisnis_unit == False):
                                        category = category.parent_id
                                    dicts.update({'category': category.name})
                                    if category.name == 'Service':
                                        invoice_name = wo.get_no_invoice(wo.name,'Service')
                                    else:
                                        invoice_name = wo.get_no_invoice(wo.name,'Sparepart')
                                    invoice_date = wo.get_tanggal_invoice(wo.name)
                                    inv_id = self.pool.get('account.invoice').search(cr, uid, [('number','=',invoice_name)], order='id desc', limit=1)
                                    if inv_id:
                                        inv = self.pool.get('account.invoice').browse(cr, uid, inv_id)
                                        if inv.payment_ids:
                                            tgl_bayar = ', '.join(inv.payment_ids.mapped('date'))
                                            bayar = sum(inv.payment_ids.filtered(lambda r: r.date == inv.date_invoice).mapped('credit'))
                                            ar_bayar = sum(inv.payment_ids.filtered(lambda r: r.date != inv.date_invoice).mapped('credit'))
                                            ar = inv.residual
                                            dicts.update({'tgl_bayar': tgl_bayar})
                                            dicts.update({'bayar': bayar})
                                            dicts.update({'ar_bayar': ar_bayar})
                                            dicts.update({'ar': ar})
                                    dicts.update({'invoice_name': invoice_name})
                                    dicts.update({'invoice_date': invoice_date})
                                    res.append(dicts)
                            res[0].update({'discount': p['discount']})
                            res[0].update({'discount_program': p['discount_program']})
                            res[0].update({'price_subtotal': res[0]['price_subtotal'] -  p['discount_program'] - p['discount']})
                            sp_ids += res
                sorted_wo = sorted(sp_ids, key=lambda k: k['name'])
                report.update({'sp_ids': sorted_wo})

        reports = filter(lambda x: x.get('sp_ids'), reports)

        obj_invoice = self.pool.get('account.invoice')
        obj_moveline = self.pool.get('account.move.line')
        new_spids = []
        for item in reports[0]['sp_ids']:

            invoice_id = obj_invoice.search(cr, uid, [('origin','=',item['name']), ('number','like','NSC%')])
            invoice_data = obj_invoice.browse(cr, uid, invoice_id, context=context)

            if invoice_data:

                moveline_id = obj_moveline.search(cr, uid, [
                ('move_id','=', invoice_data.move_id.id), 
                ('product_id','=', item['product_id']),
                ('account_id.name','like', '%Harga Pokok Penjualan%')
                ])

                moveline_data = obj_moveline.browse(cr, uid, moveline_id, context=context)
                item['hpp'] = moveline_data.debit

            new_spids.append(item)

        del reports[0]['sp_ids']
        report.update({'sp_ids': new_spids})
        return reports

    def get_so(self, data):
        cr = self.cr
        uid = self.uid
        context = self.context

        section_id = data['section_id']
        user_id = data['user_id']
        product_ids = data['product_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        state = data['state']
        category = data['category']
        branch_ids = data['branch_ids']

        title_short_prefix = ''

        user_brw = self.pool.get('res.users').browse(cr, uid, uid)
        user_branch_type = user_brw.branch_type        
        
        report_penjualan_so = {
            'type': '',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Penjualan SO')}
        
        where_section_id = " 1=1 "
        if section_id :
            where_section_id = " so.section_id = '%s'" % str(section_id)
        where_user_id = " 1=1 "
        if user_id :
            where_user_id = " so.employee_id = '%s'" % str(user_id)
        where_product_ids = " 1=1 "
        if product_ids :
            where_product_ids = " sol.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " so.date_order >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " so.date_order <= '%s 23:59:59'" % str(end_date)
        where_state = " 1=1 "
        if state in ['progress','done'] :
            where_state = " so.state = '%s'" % str(state)
        else :
            where_state = " so.state in ('progress','done')"
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " so.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        where_categ = " 1=1 "
        if category:
            obj_categ = self.pool.get('product.category')
            all_categ_ids = obj_categ.search(cr, uid, [])
            categs = obj_categ.get_child_ids(cr, uid, all_categ_ids, category)
            if category == 'Sparepart':
                aksesoris_categs = obj_categ.get_child_ids(cr, uid, all_categ_ids, 'ACCESSORIES')
                where_categ = " prod_category.id in %s and prod_category.id not in %s " % (str(
                    tuple(categs)).replace(',)', ')'),str(
                    tuple(aksesoris_categs)).replace(',)', ')'))
            if category == 'ACCESSORIES':
                where_categ = " prod_category.id in %s " % (str(
                    tuple(categs)).replace(',)', ')'))

        query_penjualan_so = "select so.id as id_so, " \
            "COALESCE(b.branch_status,'') as branch_status, " \
            "COALESCE(sol.force_cogs,0) as hpp, "\
            "tk.name as tipe_konsumen, " \
            "COALESCE(sp.name,'') as oos_number, " \
            "sp.date as oos_tgl, " \
            "COALESCE(b.code,'') as branch_code, " \
            "COALESCE(b.name,'') as branch_name, " \
            "COALESCE(so.name,'') as name, " \
            "CASE WHEN so.state = 'progress' THEN 'Sales Memo' " \
            "    WHEN so.state = 'done' THEN 'Done' " \
            "    WHEN so.state IS NULL THEN '' " \
            "    ELSE so.state " \
            "END as state, " \
            "so.date_order as date_order, " \
            "sol.id as sol_id, " \
            "COALESCE(sales.name,'') as sales_name, " \
            "COALESCE(job.name,'') as job_name, " \
            "COALESCE(cust.name,'') as cust_name, " \
            "COALESCE(sol.price_unit,0) as price_unit, " \
            "COALESCE(sol.discount_show,0) as discount_show, " \
            "COALESCE(sol.discount,0) as discount, " \
            "COALESCE(product.name_template,'') as product_name, COALESCE(sol.product_uom_qty,0) as product_qty, " \
            "COALESCE(prod_category.name,'') as categ_name, " \
            "COALESCE(sol.price_unit,0)*COALESCE(sol.product_uom_qty,0)-COALESCE(sol.discount_show,0)-COALESCE(sol.discount_cash,0)-COALESCE(sol.discount_lain,0)-COALESCE(sol.discount_program,0)-COALESCE(sol.discount,0) as price_subtotal, " \
            "COALESCE(sol.discount_program,0) as discount_program, " \
            "COALESCE(sol.discount_lain,0) as discount_lain, " \
            "COALESCE(sol.discount_cash,0) as discount_cash, " \
            "COALESCE(fp.name,'') as faktur_pajak " \
            "from sale_order so " \
            "inner join sale_order_line sol on sol.order_id = so.id " \
            "left join dym_branch b ON so.branch_id = b.id " \
            "left join hr_employee employee ON so.employee_id = employee.id " \
            "left join resource_resource sales ON employee.resource_id = sales.id " \
            "left join hr_job job ON employee.job_id = job.id " \
            "left join crm_case_section sales_team ON so.section_id = sales_team.id " \
            "left join res_partner cust ON so.partner_id = cust.id " \
            "left join product_product product ON sol.product_id = product.id " \
            "left join product_template prod_template ON product.product_tmpl_id = prod_template.id " \
            "left join product_category prod_category ON prod_template.categ_id = prod_category.id " \
            "left join dym_faktur_pajak_out fp ON so.faktur_pajak_id = fp.id " \
            "left join ( " \
            "select dealer_sale_order_line_discount_line_id, " \
            "sum(discount) as discount_total, sum(discount_pelanggan) as discount_pel " \
            "from dealer_sale_order_line_discount_line " \
            "group by dealer_sale_order_line_discount_line_id " \
            ") sol_disc ON sol_disc.dealer_sale_order_line_discount_line_id = sol.id " \
            "left join stock_picking sp ON so.name = sp.origin " \
            "left join tipe_konsumen tk ON so.tipe_konsumen = tk.id " \
            "WHERE " + where_section_id + " AND " + where_categ + " AND " + where_user_id + " AND " + where_product_ids + " AND " + where_start_date + " AND " + where_end_date + " AND " + where_state + " AND " + where_branch_ids + " " \
            "order by b.code, so.date_order"
            
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        reports = [report_penjualan_so]
        
        for report in reports:
            cr.execute(query_penjualan_so)
            all_lines = cr.dictfetchall()
            so_ids = []
            if all_lines:
                def lines_map(x):
                        x.update({'docname': x['branch_code']})
                map(lines_map, all_lines)
                for cnt in range(len(all_lines)-1):
                    if all_lines[cnt]['id_so'] != all_lines[cnt+1]['id_so']:
                        all_lines[cnt]['draw_line'] = 1
                    else:
                        all_lines[cnt]['draw_line'] = 0
                all_lines[-1]['draw_line'] = 1

                p_map = map(
                    lambda x: {
                        'no': 0,
                        'id_so': x['id_so'],
                        'sol_id': x['sol_id'],
                        'branch_status': str(x['branch_status'].encode('ascii','ignore').decode('ascii')) if x['branch_status'] != None else '',
                        'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                        'oos_number': str(x['oos_number'].encode('ascii','ignore').decode('ascii')) if x['oos_number'] != None else '',
                        'oos_tgl': str(x['oos_tgl'].encode('ascii','ignore').decode('ascii')) if x['oos_tgl'] != None else '',
                        'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                        'name': str(x['name'].encode('ascii','ignore').decode('ascii')) if x['name'] != None else '',
                        'state': str(x['state'].encode('ascii','ignore').decode('ascii')) if x['state'] != None else '',
                        'date_order': str(x['date_order']) if x['date_order'] != None else False,
                        'sales_name': str(x['sales_name'].encode('ascii','ignore').decode('ascii')) if x['sales_name'] != None else '',
                        'job_name': str(x['job_name'].encode('ascii','ignore').decode('ascii')) if x['job_name'] != None else '',
                        'cust_name': str(x['cust_name'].encode('ascii','ignore').decode('ascii')) if x['cust_name'] != None else '',
                        'product_name': str(x['product_name'].encode('ascii','ignore').decode('ascii')) if x['product_name'] != None else '',
                        'product_qty': x['product_qty'],
                        'price_unit': x['price_unit'],
                        'discount_show': x['discount_show'],
                        'discount': x['discount'],
                        'tipe_konsumen': x['tipe_konsumen'],
                        'hpp' : x['hpp'],
                        'discount_program': x['discount_program'],
                        'discount_lain': x['discount_lain'],
                        'discount_cash': x['discount_cash'],
                        'price_subtotal': x['price_subtotal'],
                        'categ_name': str(x['categ_name'].encode('ascii','ignore').decode('ascii')) if x['categ_name'] != None else '',
                        'faktur_pajak': str(x['faktur_pajak'].encode('ascii','ignore').decode('ascii')) if x['faktur_pajak'] != None else '',
                        'discount_bundle' : 0
                    },
                    
                    all_lines)
                for p in p_map:
                    if p['sol_id'] not in map(
                            lambda x: x.get('sol_id', None), so_ids):
                        sale_order = filter(lambda x: x['id_so'] == p['id_so'], all_lines)
                        sale_order_line = filter(lambda x: x['sol_id'] == p['sol_id'], all_lines)

                        if user_branch_type == 'HO':
                            so = self.pool.get('sale.order').browse(cr, SUPERUSER_ID, sale_order[0]['id_so'])
                            sol = self.pool.get('sale.order.line').browse(cr, SUPERUSER_ID, sale_order_line[0]['sol_id'])
                        else:
                            so = self.pool.get('sale.order').browse(cr, uid, sale_order[0]['id_so'])
                            sol = self.pool.get('sale.order.line').browse(cr, uid, sale_order_line[0]['sol_id'])

                        discount_program = sol.discount_program
                        analytic_1_name = ''
                        analytic_2_name = ''
                        analytic_3_name = ''
                        analytic_4_name = ''
                        p.update({'lines': sale_order})
                        p.update({'analytic_1': analytic_1_name})
                        p.update({'analytic_2': analytic_2_name})
                        p.update({'analytic_3': analytic_3_name})
                        p.update({'analytic_4': analytic_4_name})
                        p.update({'discount_program': discount_program})
                        p.update({'category': ''})
                        p.update({'invoice_name': ''})
                        p.update({'invoice_date': ''})
                        p.update({'tgl_bayar': ''})
                        p.update({'bayar': 0})
                        p.update({'ar_bayar': 0})
                        p.update({'ar': 0})
                        p.update({'retur': 0})
                        if sol and sol.product_id.categ_id:
                            category = sol.product_id.categ_id
                            while (category.parent_id and category.bisnis_unit == False):
                                category = category.parent_id
                            p.update({'category': category.name})
                            if sol.invoice_lines:
                                inv = sol.invoice_lines.mapped('invoice_id')
                                if inv.mapped('payment_ids'):
                                    tgl_bayar = ', '.join(inv.mapped('payment_ids.date'))
                                    bayar = sum(inv.mapped('payment_ids').filtered(lambda r: r.date in inv.mapped('date_invoice')).mapped('credit'))
                                    ar_bayar = sum(inv.mapped('payment_ids').filtered(lambda r: r.date not in inv.mapped('date_invoice')).mapped('credit'))
                                    ar = sum(inv.mapped('residual'))
                                    p.update({'tgl_bayar': tgl_bayar})
                                    p.update({'bayar': bayar})
                                    p.update({'ar_bayar': ar_bayar})
                                    p.update({'ar': ar})
                            invoice_name = ', '.join(sol.invoice_lines.mapped('invoice_id').filtered(lambda r: r.number).mapped('number')) if sol.invoice_lines.mapped('invoice_id').filtered(lambda r: r.number) else '-'
                            try:
                                invoice_date = ', '.join(sol.invoice_lines.mapped('invoice_id').filtered(lambda r: r.number).mapped('date_invoice')) if sol.invoice_lines.mapped('invoice_id').filtered(lambda r: r.number) else '-'
                            except:
                                invoice_date = ''

                            p.update({'invoice_name': invoice_name})
                            p.update({'invoice_date': invoice_date})
                            retur_line_id = self.pool.get('dym.retur.jual.line').search(cr, uid, [('so_line_id','=',sol.id)])
                            if retur_line_id:
                                retur_line = self.pool.get('dym.retur.jual.line').browse(cr, uid, retur_line_id)
                                p.update({'retur': sum(retur_line.mapped('retur_id').mapped(lambda r: r.amount_total - r.biaya_retur))})
                        so_ids.append(p)
                sorted_so = sorted(so_ids, key=lambda k: k['name'])
                report.update({'so_ids': sorted_so})

        reports = filter(lambda x: x.get('so_ids'), reports)
        return reports

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context

        reports = []
        reports.append(self.get_wo(data)[0])
        reports.append(self.get_so(data)[0])
        
        if not reports :
            raise osv.except_osv(('Warning'), ('Data Report Tidak Ditemukan !'))
        
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        report_info = _('')

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        objects = False
        super(dym_report_penjualan_sowo_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_penjualan_sowo_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_penjualan_sowo.report_penjualan_sowo'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_penjualan_sowo.report_penjualan_sowo'
    _wrapped_report_class = dym_report_penjualan_sowo_print
