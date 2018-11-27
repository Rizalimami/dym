from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_penjualan_spbynopol_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_penjualan_spbynopol_print, self).__init__(cr, uid, name, context=context)
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
        state = data['state']
        category = data['category']
        branch_ids = data['branch_ids']

        title_short_prefix = ''
        
        report_penjualan_sp = {
            'type': '',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Penjualan WO by NOPOL')}
        
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

        query_penjualan_sp = """select row_number() over (ORDER BY sp.no_pol) as id_sp, 
            COALESCE(b.branch_status,'') as branch_status, 
            tk.name as tipe_konsumen, 
            --COALESCE(spc.name,'') as oos_number, 
            --spc.date as oos_tgl, 
            --COALESCE(dspack.name,'') as dno_number,
            --dspack.date as dno_tgl,
            COALESCE(b.code,'') as branch_code, 
            COALESCE(b.name,'') as branch_name, 
            --COALESCE(sp.name,'') as name, 
            /*CASE WHEN sp.state = 'finished' THEN 'Finished' 
                WHEN sp.state = 'approved' THEN 'Approved' 
                WHEN sp.state = 'confirmed' THEN 'Confirmed' 
                WHEN sp.state = 'draft' THEN 'Draft' 
                WHEN sp.state IS NULL THEN '' 
                ELSE sp.state 
            END as state,*/ 
            CASE WHEN sp.type = 'KPB' THEN 'KPB ' || sp.kpb_ke 
                WHEN sp.type = 'REG' THEN 'Regular' 
                WHEN sp.type = 'WAR' THEN 'Job Return' 
                WHEN sp.type = 'CLA' THEN 'Claim' 
                WHEN sp.type IS NULL THEN '' 
                ELSE sp.type 
            END as tipe_transaksi, 
            to_char(sp.date,'yyyy-mm-dd') as date_order, 
            --spl.id as spl_id, 
            --pch_wo.wo_numb as wo_numb, 
            sum(pch_wo.hpp * spl.product_qty) as force_cogs, 
            COALESCE(sales.name,'') as sales_name, 
            --COALESCE(cust.name,'') as cust_name, 
            sum(COALESCE(spl.price_unit,0)) as price_unit, 
            sum(COALESCE(spl.qty_available,0)) as qty_available, 
            sum(COALESCE(spl.supply_qty,0)) as supply_qty, 
            --COALESCE(prod_template.name,'') as product_name, 
            sum(COALESCE(spl.discount_program,0)) as discount_program, 
            --COALESCE(spl.location_id,0) as location_id, 
            sum(COALESCE(spl.discount_persen,0)) as discount_persen, 
            sum(COALESCE(spl.discount,0)) as discount, 
            sum(COALESCE(spl.discount_pcs,0)) as discount_perpcs, 
            sum(COALESCE(spl_db.discount_bundle,0)) as discount_bundle, 
            sum(COALESCE(spl.product_qty,0)) as product_qty, 
            --COALESCE(prod_category.name,'') as categ_name, 
            sum(COALESCE(spl.supply_qty,0)*COALESCE(spl.price_unit,0)-COALESCE(spl.discount_program,0)-COALESCE(spl_db.discount_bundle,0)-COALESCE(spl.discount,0)) as price_subtotal, 
            sum(round((COALESCE(spl.supply_qty,0)*COALESCE(spl.price_unit,0)-COALESCE(spl.discount_program,0)-COALESCE(spl_db.discount_bundle,0)-COALESCE(spl.discount,0)) / 1.1)) as dpp, 
            sum(round(((COALESCE(spl.supply_qty,0)*COALESCE(spl.price_unit,0)-COALESCE(spl.discount_program,0)-COALESCE(spl_db.discount_bundle,0)-COALESCE(spl.discount,0)) / 1.1) * 0.1)) as ppn, 
            --COALESCE(fp.name,'') as faktur_pajak,
            sp.no_pol 
            from dym_work_order sp 
            inner join dym_work_order_line spl on spl.work_order_id = sp.id 
            left join hr_employee employee ON sp.mekanik_id = employee.id 
            left join resource_resource sales ON employee.resource_id = sales.id 
            left join dym_branch b ON sp.branch_id = b.id 
            left join res_partner cust ON sp.customer_id = cust.id 
            left join product_product product ON spl.product_id = product.id 
            left join product_template prod_template ON product.product_tmpl_id = prod_template.id 
            left join product_category prod_category ON prod_template.categ_id = prod_category.id 
            left join dym_faktur_pajak_out fp ON sp.faktur_pajak_id = fp.id 
            left join ( 
            select db.wo_line_id, sum(db.diskon) as discount_bundle 
            from dym_work_order_bundle db 
            group by db.wo_line_id 
            ) spl_db ON spl_db.wo_line_id = spl.id 
            left join stock_picking spc ON sp.name = spc.origin 
            left join dym_stock_packing dspack ON dspack.picking_id = spc.id
            left join (select origin || product_id as "wo_numb", round(old_cost_price::numeric,2) as "hpp" from dym_ppb_history_report) pch_wo on pch_wo.wo_numb = sp.name || spl.product_id
            left join tipe_konsumen tk ON sp.tipe_konsumen = tk.id """ \
            "WHERE sp.type !='WAR' AND " + where_section_id + " AND " + where_categ + " AND " + where_user_id + " AND " + where_product_ids + " AND " + where_start_date + " AND " + where_end_date + " AND " + where_state + " AND " + where_branch_ids + " " \
            "group by sp.no_pol,b.branch_status,tk.name,b.code, b.name, sp.type, sp.kpb_ke,to_char(sp.date,'yyyy-mm-dd'), sales.name " \
            "order by sp.no_pol, b.code, to_char(sp.date,'yyyy-mm-dd')"
            
        move_selection = ""
        report_info = _('')
        move_selection += ""
        reports = [report_penjualan_sp]
        
        for report in reports:
            cr.execute(query_penjualan_sp)
            print query_penjualan_sp
            all_lines = cr.dictfetchall()
            nopols = []

            if all_lines:
                def lines_map(x):
                        x.update({'docname': x['branch_code']})
                map(lines_map, all_lines)
                for cnt in range(len(all_lines)-1):
                    if all_lines[cnt]['no_pol'] != all_lines[cnt+1]['no_pol']:
                        all_lines[cnt]['draw_line'] = 1
                    else:
                        all_lines[cnt]['draw_line'] = 0
                all_lines[-1]['draw_line'] = 1

                p_map = map(
                    lambda x: {
                        'no': 0,
                        'id_sp': x['id_sp'],
                        # 'spl_id': x['spl_id'],
                        'branch_status': str(x['branch_status'].encode('ascii','ignore').decode('ascii')) if x['branch_status'] != None else '',
                        'no_pol': str(x['no_pol'].encode('ascii','ignore').decode('ascii')) if x['no_pol'] != None else '',
                        'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                        'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                        # 'name': str(x['name'].encode('ascii','ignore').decode('ascii')) if x['name'] != None else '',
                        # 'state': str(x['state'].encode('ascii','ignore').decode('ascii')) if x['state'] != None else '',
                        'date_order': str(x['date_order']) if x['date_order'] != None else False,
                        'sales_name': str(x['sales_name'].encode('ascii','ignore').decode('ascii')) if x['sales_name'] != None else '',
                        # 'cust_name': str(x['cust_name'].encode('ascii','ignore').decode('ascii')) if x['cust_name'] != None else '',
                        # 'product_name': str(x['product_name'].encode('ascii','ignore').decode('ascii')) if x['product_name'] != None else '',
                        'product_qty': x['product_qty'],
                        'supply_qty' : x['supply_qty'],
                        'price_unit': x['price_unit'],
                        'discount': x['discount'],
                        'discount_perpcs': x['discount_perpcs'],
                        'discount_program': x['discount_program'],
                        'discount_bundle': x['discount_bundle'],
                        'price_subtotal': x['price_subtotal'],
                        'dpp': x['dpp'],
                        'ppn': x['ppn'],
                        'force_cogs': x['force_cogs'],
                        # 'categ_name': str(x['categ_name'].encode('ascii','ignore').decode('ascii')) if x['categ_name'] != None else '',
                        # 'faktur_pajak': str(x['faktur_pajak'].encode('ascii','ignore').decode('ascii')) if x['faktur_pajak'] != None else '',
                        # 'oos_number': str(x['oos_number'].encode('ascii','ignore').decode('ascii')) if x['oos_number'] != None else '',
                        # 'oos_tgl': str(x['oos_tgl'].encode('ascii','ignore').decode('ascii')) if x['oos_tgl'] != None else '',
                        # 'dno_number': str(x['dno_number'].encode('ascii','ignore').decode('ascii')) if x['dno_number'] != None else '',
                        # 'dno_tgl': str(x['dno_tgl'].encode('ascii','ignore').decode('ascii')) if x['dno_tgl'] != None else '',
                        'tipe_konsumen': x['tipe_konsumen'],
                        'tipe_transaksi': x['tipe_transaksi'],
                    },
                    
                    all_lines)
                for p in p_map:
                    if p['no_pol'] not in map(
                            lambda x: x.get('id_sp', None), nopols):
                        nopols.append(p)
                        # sale_order = filter(lambda x: x['no_pol'] == p['no_pol'], all_lines)
                        # sale_order_line = filter(lambda x: x['no_pol'] == p['no_pol'], all_lines)

                        # wo = self.pool.get('dym.work.order').browse(cr, uid, sale_order[0]['id_sp'])
                        # wo_line = self.pool.get('dym.work.order.line').browse(cr, uid, sale_order_line[0]['spl_id'])
                        # analytic_1_name = ''
                        # analytic_2_name = ''
                        # analytic_3_name = ''
                        # analytic_4_name = ''
                        # analytic_combination = ''
                        # p.update({'lines': sale_order_line})
                        # p.update({'analytic_1': analytic_1_name})
                        # p.update({'analytic_2': analytic_2_name})
                        # p.update({'analytic_3': analytic_3_name})
                        # p.update({'analytic_4': analytic_4_name})
                        # p.update({'analytic_combination': analytic_combination})
                        # p.update({'category': ''})
                        # p.update({'invoice_name': ''})
                        # p.update({'invoice_date': ''})
                        # p.update({'tgl_bayar': ''})
                        # p.update({'bayar': 0})
                        # p.update({'ar_bayar': 0})
                        # p.update({'ar': 0})
                        # if not wo_line.bundle_line:
                        #     if wo_line and wo_line.product_id.categ_id:
                        #         category = wo_line.product_id.categ_id
                        #         while (category.parent_id and category.bisnis_unit == False):
                        #             category = category.parent_id
                        #         p.update({'category': category.name})
                        #         if category.name == 'Service':
                        #             invoice_name = wo.get_no_invoice(wo.name,'Service')
                        #         else:
                        #             invoice_name = wo.get_no_invoice(wo.name,'Sparepart')
                        #         invoice_date = wo.get_tanggal_invoice(wo.name)
                        #         inv_id = self.pool.get('account.invoice').search(cr, uid, [('number','=',invoice_name)], order='id desc', limit=1)
                        #         if inv_id:
                        #             inv = self.pool.get('account.invoice').browse(cr, uid, inv_id)
                        #             if inv.payment_ids:
                        #                 tgl_bayar = ', '.join(inv.payment_ids.mapped('date'))
                        #                 bayar = sum(inv.payment_ids.filtered(lambda r: r.date == inv.date_invoice).mapped('credit'))
                        #                 ar_bayar = sum(inv.payment_ids.filtered(lambda r: r.date != inv.date_invoice).mapped('credit'))
                        #                 ar = inv.residual
                        #                 p.update({'tgl_bayar': tgl_bayar})
                        #                 p.update({'bayar': bayar})
                        #                 p.update({'ar_bayar': ar_bayar})
                        #                 p.update({'ar': ar})
                        #         p.update({'invoice_name': invoice_name})
                        #         p.update({'invoice_date': invoice_date})
                        #     nopols.append(p)
                        # else:
                        #     res = []
                        #     for line in wo_line.bundle_line:
                        #         dicts = {
                                    # 'lines': sale_order_line,
                        # p.update({'no': p['no']})
                        # nopols += p
                # sorted_wo = sorted(nopols, key=lambda k: k['name'])
                # report.update({'nopols': nopols})
                        report.update({'nopols': nopols})
        
        reports = filter(lambda x: x.get('nopols'), reports)
        # temp = []
        
        # for item in reports[0]['nopols']:
        #     if item['category']=='Service':
        #         item['price_subtotal'] = item['product_qty']*item['price_unit']-item['discount_program']-item['discount_bundle']-item['discount']
        #         item['dpp'] = (item['product_qty']*item['price_unit']-item['discount_program']-item['discount_bundle']-item['discount'])/1.1
        #         item['ppn'] = ((item['product_qty']*item['price_unit']-item['discount_program']-item['discount_bundle']-item['discount'])/1.1)*0.1
        #     if not item['invoice_name'] or item['invoice_name']!='-':
        #         temp.append(item)
        #
        # reports[0]['nopols'] = temp
        
        if not reports :
            reports = [{'nopols': [{
            'no': 'NO DATA FOUND',
            'no_pol': 'NO DATA FOUND',
            'branch_status': 'NO DATA FOUND',
            'branch_code': 'NO DATA FOUND',
            'branch_name': 'NO DATA FOUND',
            'analytic_1': 'NO DATA FOUND',
            'analytic_2': 'NO DATA FOUND',
            'analytic_3': 'NO DATA FOUND',
            'analytic_4': 'NO DATA FOUND',
            'analytic_combination': 'NO DATA FOUND',
            # 'name': 'NO DATA FOUND',
            # 'state': 'NO DATA FOUND',
            'date_order': 'NO DATA FOUND',
            'sales_name': 'NO DATA FOUND',
            # 'cust_name': 'NO DATA FOUND',
            # 'product_name': 'NO DATA FOUND',
            'product_qty': 0,
            'supply_qty' : 0,
            'price_unit': 0,
            'discount_perpcs': 0,
            'discount': 0,
            'discount_program': 0,
            'discount_bundle': 0,
            'price_subtotal': 0,
            'dpp': 0,
            'ppn': 0,
            'force_cogs': 0,
            'tgl_bayar': 'NO DATA FOUND',
            'bayar': 0,
            'ar_bayar': 0,
            'ar': 0,
            # 'categ_name': 'NO DATA FOUND',
            'category': 'NO DATA FOUND',
            'invoice_name': 'NO DATA FOUND',
            'invoice_date': 'NO DATA FOUND',
            # 'oos_number': 'NO DATA FOUND',
            # 'oos_tgl': 'NO DATA FOUND',
            # 'dno_number': 'NO DATA FOUND',
            # 'dno_tgl': 'NO DATA FOUND',
            'tipe_konsumen': 'NO DATA FOUND',
            'tipe_transaksi': 'NO DATA FOUND',
            # 'faktur_pajak': 'NO DATA FOUND'
            }], 'title_short': 'Laporan Penjualan WO by NOPOL', 'type': '', 'title': ''}]
        
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_penjualan_spbynopol_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_penjualan_spbynopol_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_penjualan_spbynopol.report_penjualan_spbynopol'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_penjualan_spbynopol.report_penjualan_spbynopol'
    _wrapped_report_class = dym_report_penjualan_spbynopol_print
