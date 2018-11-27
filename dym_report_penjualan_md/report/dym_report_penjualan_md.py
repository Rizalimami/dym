from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_penjualan_md_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_penjualan_md_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        division = data['division']
        product_ids = data['product_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        state = data['state']
        branch_ids = data['branch_ids']
        dealer_ids = data['dealer_ids']

        title_short_prefix = ''
        
        report_penjualan_md = {
            'type': '',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Penjualan MD')}
        
        where_product_ids = " 1=1 "
        if product_ids :
            where_product_ids = " sol.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        where_division = " 1=1 "
        if division :
            where_division = " so.division = '%s'" % str(division)
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
        where_dealer_ids = " 1=1 "
        if dealer_ids :
            where_dealer_ids = " so.partner_id in %s" % str(
                tuple(dealer_ids)).replace(',)', ')')
        
        user = self.pool.get('res.users').browse(cr,uid,uid)
        timezone = user.tz or 'Asia/Jakarta'
        if timezone == 'Asia/Jayapura' :
            tz = '9 hours'
        elif timezone == 'Asia/Pontianak' :
            tz = '8 hours'
        else :
            tz = '7 hours'
        
        if division == 'Unit' :
            query_penjualan = """
                select so.id as id_so, b.code as branch_code, b.name as branch_name, so.name as name, CASE WHEN so.state = 'progress' THEN 'Sales Memo' WHEN so.state = 'done' THEN 'Done' WHEN so.state IS NULL THEN '' ELSE so.state END as state, to_char(so.date_order + interval %s, 'YYYY-MM-DD HH12:MI AM') as date_order, customer.default_code as cust_code, customer.name as cust_name, product.name_template as type, pav.code as warna, sol.product_uom_qty as qty,
                COALESCE(inv.force_cogs,0) / sol.product_uom_qty as hpp,
                sol.price_unit as harga_jual, sol.discount as disc,
                sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 as harga_jual_excl_tax,
                COALESCE(inv.force_cogs,0) as total_hpp,
                sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty as nett_sales,
                COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty as discount_cash_avg,
                COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty as discount_lain_avg,
                COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty as discount_program_avg,
                (sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty) as dpp,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 0.1 as tax,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 1.1 as total,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) - COALESCE(inv.force_cogs,0) as gp,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) - COALESCE(inv.force_cogs,0) / sol.product_uom_qty as gp_avg,
                COALESCE(prod_category.name,'') as categ_name,
                COALESCE(prod_category2.name,'') as categ2_name,
                COALESCE(prod_template.series,'') as prod_series,
                COALESCE(fp.name,'') as faktur_pajak
                from sale_order so
                inner join sale_order_line sol on so.id = sol.order_id
                inner join (select tent_so.id, COALESCE(sum(tent_sol.product_uom_qty),0) as total_qty from sale_order tent_so inner join sale_order_line tent_sol on tent_so.id = tent_sol.order_id group by tent_so.id) tent on so.id = tent.id
                left join dym_branch b on so.branch_id = b.id
                left join res_partner customer on so.partner_id = customer.id
                left join product_product product on sol.product_id = product.id
                left join product_template prod_template ON product.product_tmpl_id = prod_template.id
                left join product_category prod_category ON prod_template.categ_id = prod_category.id
                left join product_category prod_category2 ON prod_category.parent_id = prod_category2.id
                left join dym_faktur_pajak_out fp ON so.faktur_pajak_id = fp.id
                left join product_attribute_value_product_product_rel pavpp on pavpp.prod_id = product.id
                left join product_attribute_value pav on pavpp.att_id = pav.id
                left join (select ai.origin, ail.product_id, ail.force_cogs from account_invoice ai
                inner join account_invoice_line ail on ai.id = ail.invoice_id where ail.product_id is not null) inv on inv.origin = so.name and inv.product_id = sol.product_id 
            """
        else :
            query_penjualan = """
                select so.id as id_so, b.code as branch_code, b.name as branch_name, so.name as name, CASE WHEN so.state = 'progress' THEN 'Sales Memo' WHEN so.state = 'done' THEN 'Done' WHEN so.state IS NULL THEN '' ELSE so.state END as state, to_char(so.date_order + interval %s, 'YYYY-MM-DD HH12:MI AM') as date_order, customer.default_code as cust_code, customer.name as cust_name, product.name_template as type, '' as warna, sol.product_uom_qty as qty,
                COALESCE(inv.force_cogs,0) / sol.product_uom_qty as hpp,
                sol.price_unit as harga_jual, sol.discount as disc,
                sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 as harga_jual_excl_tax,
                COALESCE(inv.force_cogs,0) as total_hpp,
                sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty as nett_sales,
                COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty as discount_cash_avg,
                COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty as discount_lain_avg,
                COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty as discount_program_avg,
                (sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty) as dpp,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 0.1 as tax,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 1.1 as total,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) - COALESCE(inv.force_cogs,0) as gp,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) - COALESCE(inv.force_cogs,0) / sol.product_uom_qty as gp_avg,
                COALESCE(prod_category.name,'') as categ_name,
                COALESCE(prod_category2.name,'') as categ2_name,
                COALESCE(prod_template.series,'') as prod_series,
                COALESCE(fp.name,'') as faktur_pajak
                from sale_order so
                inner join sale_order_line sol on so.id = sol.order_id
                inner join (select tent_so.id, COALESCE(sum(tent_sol.product_uom_qty),0) as total_qty from sale_order tent_so inner join sale_order_line tent_sol on tent_so.id = tent_sol.order_id group by tent_so.id) tent on so.id = tent.id
                left join dym_branch b on so.branch_id = b.id
                left join res_partner customer on so.partner_id = customer.id
                left join product_product product on sol.product_id = product.id
                left join product_template prod_template ON product.product_tmpl_id = prod_template.id
                left join product_category prod_category ON prod_template.categ_id = prod_category.id
                left join product_category prod_category2 ON prod_category.parent_id = prod_category2.id
                left join dym_faktur_pajak_out fp ON so.faktur_pajak_id = fp.id
                left join (select am.ref as name, aml.product_id, aml.debit as force_cogs from account_move am
                inner join account_move_line aml on am.id = aml.move_id where aml.product_id is not null and aml.debit > 0 and aml.account_id in (1128, 1129)) inv on inv.name = so.name and inv.product_id = sol.product_id
            """
        
        where = "WHERE " + where_division + " AND " + where_branch_ids + " AND " + where_dealer_ids + " AND " + where_start_date + " AND " + where_end_date + " AND " + where_product_ids + " AND " + where_state
        
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        reports = [report_penjualan_md]
        
        for report in reports:
            cr.execute(query_penjualan + where,(tz,))
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
                        'id_so': str(x['id_so']),
                        'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                        'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                        'name': str(x['name'].encode('ascii','ignore').decode('ascii')) if x['name'] != None else '',
                        'state': str(x['state'].encode('ascii','ignore').decode('ascii')) if x['state'] != None else '',
                        'date_order': str(x['date_order'].encode('ascii','ignore').decode('ascii')) if x['date_order'] != None else '',
                        'cust_code': str(x['cust_code'].encode('ascii','ignore').decode('ascii')) if x['cust_code'] != None else '',
                        'cust_name': str(x['cust_name'].encode('ascii','ignore').decode('ascii')) if x['cust_name'] != None else '',
                        'type': str(x['type'].encode('ascii','ignore').decode('ascii')) if x['type'] != None else '',
                        'warna': str(x['warna'].encode('ascii','ignore').decode('ascii')) if x['warna'] != None else '',
                        'qty': x['qty'],
                        'hpp': x['hpp'],
                        'harga_jual': x['harga_jual'],
                        'disc': x['disc'],
                        'harga_jual_excl_tax': x['harga_jual_excl_tax'],
                        'total_hpp': x['total_hpp'],
                        'nett_sales': x['nett_sales'],
                        'discount_cash_avg': x['discount_cash_avg'],
                        'discount_lain_avg': x['discount_lain_avg'],
                        'discount_program_avg': x['discount_program_avg'],
                        'dpp': x['dpp'],
                        'tax': x['tax'],
                        'total': x['total'],
                        'gp': x['gp'],
                        'gp_avg': x['gp_avg'],
                        'categ_name': str(x['categ_name'].encode('ascii','ignore').decode('ascii')) if x['categ_name'] != None else '',
                        'categ2_name': str(x['categ2_name'].encode('ascii','ignore').decode('ascii')) if x['categ2_name'] != None else '',
                        'prod_series': str(x['prod_series'].encode('ascii','ignore').decode('ascii')) if x['prod_series'] != None else '',
                        'faktur_pajak': str(x['faktur_pajak'].encode('ascii','ignore').decode('ascii')) if x['faktur_pajak'] != None else '',
                    },
                    
                    all_lines)
                report.update({'so_ids': p_map})

        reports = filter(lambda x: x.get('so_ids'), reports)
        
        if not reports :
            reports = [{'so_ids': [{
            'no': 'NO DATA FOUND',
            'branch_code': 'NO DATA FOUND',
            'branch_name': 'NO DATA FOUND',
            'name': 'NO DATA FOUND',
            'state': 'NO DATA FOUND',
            'date_order': 'NO DATA FOUND',
            'cust_code': 'NO DATA FOUND',
            'cust_name': 'NO DATA FOUND',
            'type': 'NO DATA FOUND',
            'warna': 'NO DATA FOUND',
            'qty': 0,
            'hpp': 0,
            'harga_jual': 0,
            'disc': 0,
            'harga_jual_excl_tax': 0,
            'total_hpp': 0,
            'nett_sales': 0,
            'discount_cash_avg': 0,
            'discount_lain_avg': 0,
            'discount_program_avg': 0,
            'dpp': 0,
            'tax': 0,
            'total': 0,
            'gp': 0,
            'gp_avg': 0,
            'categ_name': 'NO DATA FOUND',
            'categ2_name': 'NO DATA FOUND',
            'prod_series': 'NO DATA FOUND',
            'faktur_pajak': 'NO DATA FOUND'}], 'title_short': 'Laporan Penjualan MD', 'type': '', 'title': ''}]
        
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_penjualan_md_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_penjualan_md_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_penjualan_md.report_penjualan_md'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_penjualan_md.report_penjualan_md'
    _wrapped_report_class = dym_report_penjualan_md_print
