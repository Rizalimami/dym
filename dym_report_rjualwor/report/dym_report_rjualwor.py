from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_rjualwor_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_rjualwor_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        
        start_date = data['start_date']
        end_date = data['end_date']
        category = data['category']
        branch_ids = data['branch_ids']

        where_category = " 1=1 "
        if category == 'Sparepart':
            where_category = " test_ctg.parent_name = '%s'" % str(category)
        elif category == 'ACCESSORIES':
            where_category = " test_ctg.parent_name = '%s'" % str(category)
        elif category == 'Service':
            where_category = " test_ctg.parent_name = '%s'" % str(category)
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " wo.date >= '%s'" % str(start_date)
            where_start_date_inv = " ai.date_invoice >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " wo.date <= '%s'" % str(end_date)
            where_end_date_inv = " ai.date_invoice <= '%s'" % str(end_date)
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " wo.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
            where_branch_ids_inv = " ai.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        
        query_rjualwor = """
            select  db.branch_status as branch_status,
                    db.code as branch_code, 
                    db.name as branch_name,
                    wo.name as name,
                    CASE WHEN wo.state = 'finished' THEN 'Finished' 
                    else CASE WHEN wo.state = 'approved' THEN 'Approved' 
                    else CASE WHEN wo.state = 'confirmed' THEN 'Confirmed' 
                    else CASE WHEN wo.state = 'draft' THEN 'Draft' 
                    else CASE WHEN wo.state = 'open' THEN 'Open' 
                    else CASE WHEN wo.state = 'done' THEN 'Done' 
                    else CASE WHEN wo.state IS NULL THEN '' 
                    ELSE wo.state 
                    END end end end end end end as state, 
                    wo.date as date_order,
                    case when wo.type || ' ' || wo.kpb_ke = 'KPB 1' then ai_kpb1.number else ai.number end as invoice_name,
                    case when wo.type || ' ' || wo.kpb_ke = 'KPB 1' then ai_kpb1.date_invoice else ai.date_invoice end as invoice_date,
                    COALESCE(spick.name,'') as oos_number, 
                    spick.date as oos_tgl, 
                    COALESCE(spack.name,'') as dno_number,
                    spack.date as dno_tgl,
                    rp.name as cust_name,
                    tipe_kons.name as tipe_konsumen,
                    case when wo.type = 'KPB' then wo.type || ' ' || wo.kpb_ke else wo.type end as tipe_transaksi,
                    COALESCE(prod_template.name,'') as product_name, 
                    COALESCE(prod_category.name,'') as categ_name, 
                    test_ctg.parent_name as category,
                    COALESCE(wol.product_qty,0) as product_qty, 
                    COALESCE(wol.supply_qty,0) as supply_qty, 
                    COALESCE(wol.price_unit,0) as price_unit, 
                    COALESCE(wol.discount_pcs,0) as discount_perpcs, 
                    COALESCE(wol.discount,0) as discount, 
                    COALESCE(wol.discount_program,0) as discount_program, 
                    COALESCE(wol_db.discount_bundle,0) as discount_bundle,
                    COALESCE(wol.product_qty,0)*COALESCE(wol.price_unit,0)-COALESCE(wol.discount_program,0)-COALESCE(wol_db.discount_bundle,0)-COALESCE(wol.discount,0) as price_subtotal, 
                    round((COALESCE(wol.product_qty,0)*COALESCE(wol.price_unit,0)-COALESCE(wol.discount_program,0)-COALESCE(wol_db.discount_bundle,0)-COALESCE(wol.discount,0)) / 1.1) as dpp, 
                    round(((COALESCE(wol.product_qty,0)*COALESCE(wol.price_unit,0)-COALESCE(wol.discount_program,0)-COALESCE(wol_db.discount_bundle,0)-COALESCE(wol.discount,0)) / 1.1) * 0.1) as ppn,  
                    coalesce(pch_wo.hpp * wol.product_qty,0) as force_cogs,
                    CASE WHEN db.kpb_ganti_oli_barang = 'f' then COALESCE(wol_db2.qty_bundle,0) * COALESCE(wol_db2.price_bundle,0) else 0 end as force_cogs2,
                    CASE WHEN db.kpb_ganti_oli_barang = 'f' then COALESCE(wol_db2.qty_bundle,0) else 0 end as supply_qty2,
                    cpa.cpa as cpa,
                    cpa.date as tgl_bayar,
                    cpa.total as ar,
                    COALESCE(sales.name,'') as sales_name, 
                    COALESCE(fp.name,'') as faktur_pajak,
                    wo.km as km
                from    dym_work_order wo
                left join dym_work_order_line wol on wol.work_order_id = wo.id 
                left join stock_picking spick ON wo.name = spick.origin 
                left join dym_stock_packing spack ON spack.picking_id = spick.id and spack.state <> 'cancelled'
                left join dym_branch db on db.id = wo.branch_id
                left join tipe_konsumen tipe_kons on tipe_kons.id = wo.tipe_konsumen
                left join res_partner rp on rp.id = wo.customer_id
                left join hr_employee mech on mech.id = wo.mekanik_id
                left join hr_employee sa on sa.id = wo.sa_id
                left join product_product product ON wol.product_id = product.id 
                left join product_template prod_template ON product.product_tmpl_id = prod_template.id 
                left join product_category prod_category ON prod_template.categ_id = prod_category.id 
                left join product_product prod on prod.id = wol.product_id
                left join (select   parent_ctg.id as parent_id,
                            parent_ctg.name as parent_name,
                            btm_ctg_1.id as btm_id_1,
                            btm_ctg_1.name as btm_1,
                            btm_ctg_2.id as btm_id_2,
                            btm_ctg_2.name as btm_2
                        from    product_category parent_ctg
                        left join product_category btm_ctg_1 on parent_ctg.id = btm_ctg_1.parent_id 
                        left join product_category btm_ctg_2 on btm_ctg_1.id = btm_ctg_2.parent_id 
                        where   parent_ctg.id in (305,309,492)
                            and btm_ctg_1.bisnis_unit <> True) test_ctg on (prod_category.name = test_ctg.btm_2 or prod_category.name = test_ctg.btm_1)
                left join ( select db.wo_line_id, sum(db.diskon) as discount_bundle 
                    from dym_work_order_bundle db 
                    group by db.wo_line_id ) wol_db ON wol_db.wo_line_id = wol.id 
                left join ( select wo_line_id, sum(price_bundle) price_bundle,sum(product_uom_qty) qty_bundle 
                    from dym_work_order_bundle 
                    where type = 'product' 
                    group by wo_line_id ) wol_db2 on wol_db2.wo_line_id = wol.id  
                left join (select origin || product_id as "wo_numb", round(old_cost_price::numeric,2) as "hpp" from dym_ppb_history_report where left(origin,3) = 'WOR') pch_wo on pch_wo.wo_numb = wo.name || wol.product_id
                left join (select   aml_inv.name as wor,
                            string_agg(distinct(am_cpa.name), ', ') as cpa,
                            string_agg(distinct(to_char(am_cpa.date, 'YYYY-MM-DD')), ', ') as date,
                            sum(aml_cpa.credit) as total,
                            case when aaa.name = 'Jasa' then 'Service'
                            else case when aaa.name = 'Part' then 'Sparepart'
                            else 'ACCESSORIES' end end as category
                        from    account_move_line aml_inv
                        left join   account_move_line aml_cpa on aml_inv.reconcile_id = aml_cpa.reconcile_id and aml_inv.branch_id = aml_cpa.branch_id
                        left join   account_move am_cpa on am_cpa.id = aml_cpa.move_id 
                        left join   account_analytic_account aaa on aaa.id = aml_cpa.analytic_2
                        left join   dym_branch db on db.id = aml_cpa.branch_id
                        where   aml_cpa.name = '/' and left(aml_inv.name,3) = 'WOR'
                        group by    aml_inv.name, aaa.name
                       ) cpa on cpa.wor = wo.name and cpa.category = test_ctg.parent_name
                left join account_voucher av_cpa on av_cpa.number = cpa.cpa
                left join dym_faktur_pajak_out fp ON wo.faktur_pajak_id = fp.id 
                left join hr_employee employee ON wo.mekanik_id = employee.id 
                left join resource_resource sales ON employee.resource_id = sales.id 
                left join (select   ai.number,
                            ai.date_invoice,
                            ail.product_id,
                            ai.origin,
                            ai.origin || ail.product_id as cek
                        from    account_invoice ai
                        left join account_invoice_line ail on ail.invoice_id = ai.id
                        left join dym_branch db on db.id = ai.branch_id
                        where   ail.product_id is not null
                            and ai.division = 'Sparepart' """ \
                " and " + where_start_date_inv + " AND " + where_end_date_inv + " AND " + where_branch_ids_inv + " " \
                            """) ai on ai.cek = wo.name || wol.product_id
                left join (select   ai.number,
                            ai.date_invoice,
                            ai.origin
                        from    account_invoice ai
                        left join account_invoice_line ail on ail.invoice_id = ai.id
                        left join dym_work_order wo on wo.name = ai.origin
                        left join dym_branch db on db.id = ai.branch_id
                        where   wo.type || ' ' || wo.kpb_ke = 'KPB 1'
                            and ail.product_id is not null
                            and ai.division = 'Sparepart' """ \
                " and " + where_start_date_inv + " AND " + where_end_date_inv + " AND " + where_branch_ids_inv + " " \
                """) ai_kpb1 on ai_kpb1.origin = wo.name
                """

        query_where = " WHERE wo.state in ('open','done') and wo.type in ('REG','KPB','CLA') "
        if data['category']:
            if data['category'] == 'Sparepart':
                query_where = "and test_ctg.parent_name = '%s'" % str(data['category'])
            elif data['category'] == 'ACCESSORIES':
                query_where = "and test_ctg.parent_name = '%s'" % str(data['category'])
            elif data['category'] == 'Service':
                query_where = "and test_ctg.parent_name = '%s'" % str(data['category'])

        if data['start_date']:
            query_where += " and wo.date >= '%s'" % str(data['start_date'])
        if data['end_date']:
            query_where += " and wo.date <= '%s'" % str(data['end_date'])
        if data['branch_ids']:
            query_where += " and wo.branch_id in %s" % str(tuple(data['branch_ids'])).replace(',)', ')')
        query_group = """   
                        """
        query_order = " order by db.name, wo.name"

        self.cr.execute(query_rjualwor + query_where + query_order)
        # raise osv.except_osv(('Perhatian !'), ("No \'%s\' ...")%(query_rjualwor + query_where + query_order))
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                # 'id_dso': x['id_dso'],
                'no': 0,
                'branch_status':x['branch_status'],
                'branch_code':x['branch_code'],
                'branch_name':x['branch_name'],
                'name':x['name'],
                'state':x['state'],
                'date_order':x['date_order'],
                'invoice_name':x['invoice_name'],
                'invoice_date':x['invoice_date'],
                'oos_number':x['oos_number'],
                'oos_tgl':x['oos_tgl'],
                'dno_number':x['dno_number'],
                'dno_tgl':x['dno_tgl'],
                'cust_name':x['cust_name'],
                'tipe_konsumen':x['tipe_konsumen'],
                'tipe_transaksi':x['tipe_transaksi'],
                'product_name':x['product_name'],
                'categ_name':x['categ_name'],
                'category':x['category'],
                'product_qty':x['product_qty'],
                'supply_qty':x['supply_qty'],
                'price_unit':x['price_unit'],
                'discount_perpcs':x['discount_perpcs'],
                'discount':x['discount'],
                'discount_program':x['discount_program'],
                'discount_bundle':x['discount_bundle'],
                'price_subtotal':x['price_subtotal'],
                'dpp':x['dpp'],
                'ppn':x['ppn'],
                'force_cogs':x['force_cogs'],
                'tgl_bayar':x['tgl_bayar'],
                'ar':x['ar'],
                # 'ar_bayar':x['ar_bayar'],
                # 'ar':x['ar'],
                'faktur_pajak':x['faktur_pajak'],
                'sales_name':x['sales_name'],
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            reports = [{'datas': [{
                'no': 'NO DATA FOUND',
                'branch_status':'NO DATA FOUND',
                'branch_code':'NO DATA FOUND',
                'branch_name':'NO DATA FOUND',
                'name':'NO DATA FOUND',
                'state':'NO DATA FOUND',
                'date_order':'NO DATA FOUND',
                'invoice_name':'NO DATA FOUND',
                'invoice_date':'NO DATA FOUND',
                'oos_number':'NO DATA FOUND',
                'oos_tgl':'NO DATA FOUND',
                'dno_number':'NO DATA FOUND',
                'dno_tgl':'NO DATA FOUND',
                'cust_name':'NO DATA FOUND',
                'tipe_konsumen':'NO DATA FOUND',
                'tipe_transaksi':'NO DATA FOUND',
                'product_name':'NO DATA FOUND',
                'categ_name':'NO DATA FOUND',
                'category':'NO DATA FOUND',
                'product_qty':0,
                'supply_qty':0,
                'price_unit':0,
                'discount_perpcs':0,
                'discount':0,
                'discount_program':0,
                'discount_bundle':0,
                'price_subtotal':0,
                'dpp':0,
                'ppn':0,
                'force_cogs':0,
                'tgl_bayar':'NO DATA FOUND',
                'ar':0,
                # 'ar_bayar':x['ar_bayar'],
                # 'ar':x['ar'],
                'faktur_pajak':'NO DATA FOUND',
                'sales_name':'NO DATA FOUND'
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(dym_report_rjualwor_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_rjualwor_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_rjualwor.report_rjualwor'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_rjualwor.report_rjualwor'
    _wrapped_report_class = dym_report_rjualwor_print
    