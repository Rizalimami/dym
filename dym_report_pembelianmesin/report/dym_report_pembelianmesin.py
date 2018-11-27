from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_pembelianmesin_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_pembelianmesin_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        division = data['division']
        state = data['state']
        branch_ids = data['branch_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        product_ids = data['product_ids']
        partner_ids = data['partner_ids']
        segmen = data['segmen']
        branch_status = data['branch_status']
        
        where_division = " 1=1 "
        if division :
            where_division = " ai.division = '%s'" % str(division)
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " ai.date_invoice >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " ai.date_invoice <= '%s'" % str(end_date)
        where_state = " 1=1 "
        if state in ['open','paid'] :
            where_state = " ai.state = '%s'" % str(state)
        else :
            where_state = " ai.state in ('open','paid')"
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " ai.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        where_product_ids = " 1=1 "
        if product_ids :
            where_product_ids = " ail.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        where_partner_ids = " 1=1 "
        if partner_ids :
            where_partner_ids = " ai.partner_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')

        report_pembelian_unit = {
            'type': 'payable',
            'title': '',
            'title_short': 'Laporan Pembelian Unit'}
        
        query_pembelianmesin = """
            select  dpl.id as ail_id, b.branch_status as branch_status, b.code as branch_code, b.name as branch_name, ai.division as division, 
            ai.number as inv_number, to_char(ai.date_invoice,'DD-MM-YYYY') as date_invoice, ai.origin as origin, 
            CASE 
                WHEN ai.state = 'open' THEN 'Open' 
                WHEN ai.state = 'done' THEN 'Done' 
                WHEN ai.state IS NULL THEN '' 
            ELSE ai.state 
            END as state, 
            product.name_template as type, COALESCE(pav.code,'') as warna, prod_cat.name as prod_categ_name, 
            ail.quantity as qty, 
            case when ci.date is null then 0 when ci.date <= '2018-04-30'then   ail.consolidated_qty else 0 end as consolidated_qty, 
            case when  ci.date is null then  ail.consolidated_qty  when ci.date <= '2018-04-30' then 0 else   ail.consolidated_qty end   as unconsolidated_qty,
            --ail.consolidated_qty as consolidated_qty, 
            --0 as unconsolidated_qty,
            prod.default_code as prod_desc,
            ail.price_unit as price_unit, ail.discount as discount, ail.discount_amount/ail.quantity as disc_amount,
            CASE WHEN ail.quantity = 0 THEN 0 
            ELSE ail.price_subtotal / ail.quantity
            END as sales_per_unit,  
            ail.price_unit as total_sales,
            ail.discount_cash / ail.quantity as discount_cash_avg,
            ail.discount_program/ ail.quantity  as discount_program_avg,
            p.name as purchase_name,
            to_char(p.date_order,'DD-MM-YYYY') as purchase_date,
            ail.discount_lain/ ail.quantity as discount_lain_avg,
            ail.price_subtotal/ ail.quantity as total_dpp,
            ail.price_subtotal/ ail.quantity * 0.1 as total_ppn,
            ail.price_subtotal as total_hutang,
            ai.supplier_invoice_number as supplier_invoice_number,
            substring(pr.display_name,2,15) as supplier_code, 
            pr.name as supplier_name,
            acc.code as account_code,
            to_char(ai.document_date,'DD-MM-YYYY') as document_date,
            ai.analytic_4 as account_analytic_id,
            retur.tgl_retur as tgl_retur,
            retur.no_retur as no_retur,
            retur.qty_retur as qty_retur,
            retur.retur_total as retur_total,
            dp.date as tgl_grn,
            dp.name as no_grn,
            dpl.engine_number,
            ci.date tgl_cin,
            ci.name no_cin
            from account_invoice ai inner join account_invoice_line ail on ai.id = ail.invoice_id
            inner join (select tent_ai.id, COALESCE(sum(tent_ail.quantity),0) as total_qty from account_invoice tent_ai inner join account_invoice_line tent_ail on tent_ai.id = tent_ail.invoice_id group by tent_ai.id) tent on ai.id = tent.id
            left join account_account acc on ai.account_id = acc.id
            left join dym_branch b on ai.branch_id = b.id
            left join purchase_order_line pl on ail.purchase_line_id = pl.id
            left join purchase_order p on pl.order_id = p.id
            left join res_partner pr on ai.partner_id = pr.id
            left join product_product product on product.id = ail.product_id
            left join product_product prod on product.name_template = prod.name_template and prod.default_code is not null
            left join product_attribute_value_product_product_rel pavpp on pavpp.prod_id = product.id
            left join product_attribute_value pav on pav.id = pavpp.att_id
            left join product_template prod_template on product.product_tmpl_id = prod_template.id
            left join product_category prod_cat_last on prod_template.categ_id = prod_cat_last.id
            left join product_category prod_cat on prod_cat_last.parent_id = prod_cat.id
            left join (
            select r.date as tgl_retur,r.name as no_retur, sum(rl.product_qty) as qty_retur ,rl.invoice_line_id, sum((rl.price_unit*rl.product_qty)-rl.discount_amount) as retur_total
            from dym_retur_beli_line rl left join dym_retur_beli r on r.id = rl.retur_id
            where r.state in ('approved','except_picking','except_invoice','done')
            group by rl.invoice_line_id,r.date ,r.name 
            ) retur ON retur.invoice_line_id = ail.id
            left join consolidate_invoice ci on ai.id = ci.invoice_id
            left join consolidate_invoice_line cil on ci.id = cil.consolidate_id and pl.product_id = cil.product_id and pl.template_id = cil.template_id
            left join dym_stock_packing_line dpl on cil.move_id = dpl.move_id and dpl.product_id = cil.product_id and dpl.template_id = cil.template_id --and ail.purchase_line_id = dpl.purchase_line_id
            left join dym_stock_packing dp on dpl.packing_id = dp.id

        """
        where = "WHERE (ail.purchase_line_id is not null OR ai.tipe = 'purchase') and dpl.engine_number <>'' and  " + where_division + " AND " + where_state + " AND " + where_branch_ids + " AND " + where_start_date + " AND " + where_end_date + " AND " + where_product_ids + " AND " + where_partner_ids
        order = "order by b.code, dpl.id"

        #print query_pembelianmesin + where + order
        reports = [report_pembelian_unit]
        for report in reports:
            self.cr.execute(query_pembelianmesin + where + order)
            all_lines = self.cr.dictfetchall()
            id_ai = []
            ail_id = []
            if all_lines :
                datas = map(lambda x : {
                    #'id_ai': x['id_ai'],
                    'ail_id': x['ail_id'],
                    'no': 0,
                    'prod_desc': str(x['prod_desc'].encode('ascii','ignore').decode('ascii')) if x['prod_desc'] != None else '',
                    'account_code': str(x['account_code'].encode('ascii','ignore').decode('ascii')) if x['account_code'] != None else '',
                    'branch_status': str(x['branch_status'].encode('ascii','ignore').decode('ascii')) if x['branch_status'] != None else '',
                    'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                    'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                    'division': str(x['division'].encode('ascii','ignore').decode('ascii')) if x['division'] != None else '',
                    'inv_number': str(x['inv_number'].encode('ascii','ignore').decode('ascii')) if x['inv_number'] != None else '',
                    'date_invoice':  x['date_invoice'],
                    'origin': str(x['purchase_name'].encode('ascii','ignore').decode('ascii')) if x['purchase_name'] != None else str(x['origin'].encode('ascii','ignore').decode('ascii')) if x['origin'] != None else '',
                    'purchase_name': str(x['purchase_name'].encode('ascii','ignore').decode('ascii')) if x['purchase_name'] != None else '',
                    'purchase_date': str(x['purchase_date'].encode('ascii','ignore').decode('ascii')) if x['purchase_date'] != None else '',
                    'state': str(x['state'].encode('ascii','ignore').decode('ascii')) if x['state'] != None else '',
                    'type': str(x['type'].encode('ascii','ignore').decode('ascii')) if x['type'] != None else '',
                    'warna': str(x['warna'].encode('ascii','ignore').decode('ascii')) if x['warna'] != None else '',
                    'prod_categ_name': str(x['prod_categ_name'].encode('ascii','ignore').decode('ascii')) if x['prod_categ_name'] != None else '',
                    'qty': x['qty'],
                    'consolidated_qty': x['consolidated_qty'],
                    'unconsolidated_qty': float(x['qty'] or 0) - float(x['consolidated_qty'] or 0),
                    'price_unit': x['price_unit'],
                    'discount': x['discount'],
                    'disc_amount': x['disc_amount'],
                    'sales_per_unit': x['sales_per_unit'],
                    'total_sales': x['total_sales'],
                    'discount_cash_avg': x['discount_cash_avg'],
                    'discount_program_avg': x['discount_program_avg'],
                    'discount_lain_avg': x['discount_lain_avg'],
                    'total_dpp': x['total_dpp'],
                    'total_ppn': x['total_ppn'],
                    'total_hutang': x['total_dpp'] + x['total_ppn'],
                    'no_retur': str(x['no_retur'].encode('ascii','ignore').decode('ascii')) if x['no_retur'] != None else '',
                    'tgl_retur': x['tgl_retur'],
                    'qty_retur': x['qty_retur'],
                    'retur_total': x['retur_total'],
                    'consolidate_status' : 'Intransit' if float(x['qty'] or 0) - float(x['consolidated_qty'] or 0) > float(0) else '',
                    'supplier_invoice_number': x['supplier_invoice_number'],
                    'supplier_name': x['supplier_name'],
                    'supplier_code': x['supplier_code'],
                    'document_date': x['document_date'],
                    'analytic_4': x['account_analytic_id'] if x['account_analytic_id'] != None else '',
                    #'id_ail': x['ail_idl'] if x['ail_idl'] != None else '',
                    'tgl_grn': x['tgl_grn'],
                    'no_grn': x['no_grn'],
                    'engine_number': str(x['engine_number'].encode('ascii','ignore').decode('ascii')) if x['engine_number'] != None else '',
                    'tgl_cin': x['tgl_cin'],
                    'no_cin': x['no_cin'],
                    }, all_lines)
                total_ppn_per_inv = 0
                amount_tax = 0
                invoice_id = False
                line_id = []
                for p in datas:
                    if p['ail_id'] not in map(
                            lambda x: x.get('ail_id', None), ail_id):
                        records = filter(
                            lambda x: x['ail_id'] == p['ail_id'], all_lines)
                        if records[0]['ail_id'] in line_id:
                            continue
                        line_id.append(records[0]['ail_id'])
                        p.update({'lines': records})
                        ail_id.append(p)
                report.update({'ail_id': ail_id})
                       
        reports = filter(lambda x: x.get('ail_id'), reports)
        if not reports :
            raise osv.except_osv(_('Data Not Found!'), _('Tidak ditemukan data dari hasil filter Report Pembelian Unit by Mesin.'))
        
        self.localcontext.update({'reports': reports})
        objects = False
        super(dym_report_pembelianmesin_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_pembelianmesin_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_pembelianmesin.report_pembelianmesin'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_pembelianmesin.report_pembelianmesin'
    _wrapped_report_class = dym_report_pembelianmesin_print
    