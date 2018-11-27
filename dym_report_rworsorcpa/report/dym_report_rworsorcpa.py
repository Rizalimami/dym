from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_rworsorcpa_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_rworsorcpa_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        
        start_date = data['start_date']
        end_date = data['end_date']
        type = data['type']
        branch_ids = data['branch_ids']
        # raise osv.except_osv(('Perhatian !'), ("No \'%s\' ...")%(type))

        if type == 'wor':
            where_start_date = " 1=1 "
            if start_date :
                where_start_date = " wo.date >= '%s'" % str(start_date)
            where_end_date = " 1=1 "
            if end_date :
                where_end_date = " wo.date <= '%s'" % str(end_date)
            where_branch_ids = " 1=1 "
            if branch_ids :
                where_branch_ids = " wo.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        else:
            where_start_date = " 1=1 "
            if start_date :
                where_start_date = " wo.date_order >= '%s'" % str(start_date)
            where_end_date = " 1=1 "
            if end_date :
                where_end_date = " wo.date_order <= '%s'" % str(end_date)
            where_branch_ids = " 1=1 "
            if branch_ids :
                where_branch_ids = " wo.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        
        query_rworcpa = """
            select  db.name as branch, 
                    wo.name as number,
                    tipe_kons.name as tipe_konsumen,
                    case when wo.type = 'CLA' then 'Claim'
                        else case when wo.type = 'KPB' then 'KPB'
                    else 'Reguler' end end as type,
                    wo.date as o_date,
                    sum((price_unit - discount) * product_qty) as total,
                    cpa.cpa as cpa,
                    av_cpa.date as cpa_date,
                    av_cpa.amount as cpa_total
                    --wol.product_id,
                    --prod.default_code,
                    --prod.name_template,
                    --wol.price_unit,
                    --wol.categ_id,
                    --wol.categ_id_2,
                    --wol.count_wo,
                    --wol.supply_qty,
                    --wol.product_qty,
                    --wol.discount,
                    --wol.state
                from    dym_work_order wo
                left join dym_work_order_line wol on wol.work_order_id = wo.id
                left join dym_branch db on db.id = wo.branch_id
                left join (select   aml_inv.name as wor,
                            --aml_cpa.name, aml_inv.reconcile_id, aml_cpa.reconcile_id, av_cpa.number
                            am_cpa.name as cpa
                       from     account_move_line aml_inv
                       left join    account_move_line aml_cpa on aml_inv.reconcile_id = aml_cpa.reconcile_id 
                       left join    account_move am_cpa on am_cpa.id = aml_cpa.move_id
                       where    aml_cpa.name = '/' and left(aml_inv.name,3) = 'WOR'
                       group by     aml_inv.name, am_cpa.name) cpa on cpa.wor = wo.name
                left join account_voucher av_cpa on av_cpa.number = cpa.cpa
                left join tipe_konsumen tipe_kons on tipe_kons.id = wo.tipe_konsumen
                --left join product_product prod on prod.id = wol.product_id
                """

        query_rsorcpa = """
            select  db.name as branch, 
                    so.name as number,
                    tipe_kons.name as tipe_konsumen,
                    case when so.tipe_transaksi = 'reguler' then 'Reguler'
                        else case when so.tipe_transaksi = 'hotline' then 'Hotline'
                    else 'PIC' end end as type,
                    so.date_order as o_date,
                    sum((price_unit - discount) * coalesce(product_uos_qty, product_uom_qty)) as total,
                    cpa.cpa as cpa,
                    av_cpa.date as cpa_date,
                    av_cpa.amount as cpa_total
                    --sol.product_id,
                    --prod.default_code,
                    --prod.name_template,
                    --sol.price_unit,
                    --sol.categ_id,
                    --sol.categ_id_2,
                    --sol.count_so,
                    --sol.supply_qty,
                    --sol.product_qty,
                    --sol.discount,
                    --sol.state
                from    sale_order so
                left join sale_order_line sol on sol.order_id = so.id
                left join dym_branch db on db.id = so.branch_id
                left join (select   aml_inv.name as sor,
                            --aml_cpa.name, aml_inv.reconcile_id, aml_cpa.reconcile_id, av_cpa.number
                            am_cpa.name as cpa
                       from     account_move_line aml_inv
                       left join    account_move_line aml_cpa on aml_inv.reconcile_id = aml_cpa.reconcile_id 
                       left join    account_move am_cpa on am_cpa.id = aml_cpa.move_id
                       where    aml_cpa.name = '/' and left(aml_inv.name,3) = 'SOR'
                       group by     aml_inv.name, am_cpa.name) cpa on cpa.sor = so.name
                left join account_voucher av_cpa on av_cpa.number = cpa.cpa
                left join tipe_konsumen tipe_kons on tipe_kons.id = so.tipe_konsumen
                """

        if type == 'wor':
            query_where = " WHERE wo.state in ('open','done') "
            if data['start_date']:
                query_where += " and wo.date >= '%s'" % str(data['start_date'])
            if data['end_date']:
                query_where += " and wo.date <= '%s'" % str(data['end_date'])
            if data['branch_ids']:
                query_where += " and wo.branch_id in %s" % str(tuple(data['branch_ids'])).replace(',)', ')')
            query_group = """   group by db.name, wo.name, wo.type, wo.date, cpa.cpa, av_cpa.date, av_cpa.amount, tipe_kons.name"""
        else:
            query_where = " WHERE so.state in ('open','done') "
            if data['start_date']:
                query_where += " and so.date_order >= '%s'" % str(data['start_date'])
            if data['end_date']:
                query_where += " and so.date_order <= '%s'" % str(data['end_date'])
            if data['branch_ids']:
                query_where += " and so.branch_id in %s" % str(tuple(data['branch_ids'])).replace(',)', ')')
            query_group = """   group by db.name, so.name, so.tipe_transaksi, so.date_order, cpa.cpa, av_cpa.date, av_cpa.amount, tipe_kons.name"""

        query_order = " order by 1,2"

        if type == 'wor':
            self.cr.execute(query_rworcpa + query_where + query_group + query_order)
            # raise osv.except_osv(('Perhatian !'), ("No \'%s\' ...")%(query_rworcpa + query_where + query_group + query_order))
        else:
            self.cr.execute(query_rsorcpa + query_where + query_group + query_order)
            # raise osv.except_osv(('Perhatian !'), ("No \'%s\' ...")%(query_rsorcpa + query_where + query_group + query_order))
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                # 'id_wo': x['id_wo'],
                'no': 0,
                'branch':x['branch'], 
                'number':x['number'],
                'tipe_konsumen':x['tipe_konsumen'],
                'type':x['type'],
                'o_date':x['o_date'],
                'total':x['total'],
                'cpa':x['cpa'],
                'cpa_date':x['cpa_date'],
                'cpa_total':x['cpa_total'],
                # 'last_update_time':x['last_update_time'],
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            reports = [{'datas': [{
                'no': 'NO DATA FOUND',
                'branch':'NO DATA FOUND',
                'number':'NO DATA FOUND',
                'tipe_konsumen':'NO DATA FOUND',
                'type':'NO DATA FOUND',
                'o_date':'NO DATA FOUND',
                'total':0,
                'cpa':'NO DATA FOUND',
                'cpa_date':'NO DATA FOUND',
                'cpa_total':0
                # 'faktur_pajak': 'NO DATA FOUND'
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(dym_report_rworsorcpa_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_rworsorcpa_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_rworsorcpa.report_rworsorcpa'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_rworsorcpa.report_rworsorcpa'
    _wrapped_report_class = dym_report_rworsorcpa_print
    