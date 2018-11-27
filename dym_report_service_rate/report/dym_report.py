from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_service_rate_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_service_rate_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        branch_ids = data['branch_ids']
        trx_start_date = data['trx_start_date']
        trx_end_date = data['trx_end_date']

        title_prefix = ''
        title_short_prefix = ''
        
        report_service_rate = {
            'product_codes' : [],
            'product_supplied' : [],
            'type': 'payable',
            'title': '',
            'title_short': 'Laporan Service Rate'}

        query_start = "SELECT CONCAT(cast(l.id as text),'-',cast(obj.id as text),'-','WO') as id_ai, " \
            "COALESCE(b.name,'') as branch_id, " \
            "'WO' as tipe_dok, " \
            "obj.date as date, " \
            "obj.name as number, " \
            "COALESCE(t.name,'') as product_code, " \
            "COALESCE(t.description,'') as description, " \
            "COALESCE(p.default_code,'') as default_code, " \
            "COALESCE(l.price_unit,0) as het, " \
            "COALESCE(l.product_qty,0)+COALESCE(l.lost_order_qty,0) as qty_demand, " \
            "COALESCE(l.product_qty,0) as qty_supply, " \
            "COALESCE(l.lost_order_qty,0) as qty_backorder, " \
            "(COALESCE(l.price_unit,0)-(COALESCE(l.discount,0)/COALESCE(l.product_qty,0))-(COALESCE(l.discount_program,0)/COALESCE(l.product_qty,0))-COALESCE(s_db.discount_bundle,0)) / 1.1 as net_jual, " \
            "((COALESCE(l.price_unit,0)-(COALESCE(l.discount,0)/COALESCE(l.product_qty,0))-(COALESCE(l.discount_program,0)/COALESCE(l.product_qty,0))-COALESCE(s_db.discount_bundle,0)) / 1.1)*(COALESCE(l.product_qty,0)+COALESCE(l.lost_order_qty,0)) as jumlah_demand, " \
            "((COALESCE(l.price_unit,0)-(COALESCE(l.discount,0)/COALESCE(l.product_qty,0))-(COALESCE(l.discount_program,0)/COALESCE(l.product_qty,0))-COALESCE(s_db.discount_bundle,0)) / 1.1)*(COALESCE(l.product_qty,0)) as jumlah_supply, " \
            "((COALESCE(l.price_unit,0)-(COALESCE(l.discount,0)/COALESCE(l.product_qty,0))-(COALESCE(l.discount_program,0)/COALESCE(l.product_qty,0))-COALESCE(s_db.discount_bundle,0)) / 1.1)*(COALESCE(l.lost_order_qty,0)) as jumlah_order " \
            "FROM " \
            "dym_work_order_line l " \
            "LEFT JOIN dym_work_order obj ON l.work_order_id = obj.id " \
            "LEFT JOIN dym_branch b ON b.id = obj.branch_id " \
            "LEFT JOIN product_product p ON p.id = l.product_id " \
            "LEFT JOIN product_template t ON t.id = p.product_tmpl_id " \
            "LEFT JOIN (select db.wo_line_id, sum(db.diskon) as discount_bundle from dym_work_order_bundle db group by db.wo_line_id) s_db ON s_db.wo_line_id = l.id " \
            "where 1=1 and obj.state in ('open','done') and l.categ_id = 'Sparepart' "
        query_start2 = "SELECT CONCAT(cast(l.id as text),'-',cast(obj.id as text),'-','SO') as id_ai, " \
            "COALESCE(b.name,'') as branch_id, " \
            "'SO' as tipe_dok, " \
            "obj.date_order as date, " \
            "obj.name as number, " \
            "COALESCE(t.name,'') as product_code, " \
            "COALESCE(t.description,'') as description, " \
            "COALESCE(p.default_code,'') as default_code, " \
            "COALESCE(l.price_unit,0) as het, " \
            "COALESCE(l.product_uom_qty,0)+COALESCE(l.lost_order_qty,0) as qty_demand, " \
            "COALESCE(l.product_uom_qty,0) as qty_supply, " \
            "COALESCE(l.lost_order_qty,0) as qty_backorder, " \
            "(COALESCE(l.price_unit,0)*(1-COALESCE(l.discount,0)/100)-(COALESCE(l.discount_program,0)/COALESCE(l.product_uom_qty,0))-(COALESCE(l.discount_cash,0)/COALESCE(l.product_uom_qty,0))-(COALESCE(l.discount_lain,0)/COALESCE(l.product_uom_qty,0))) / 1.1 as net_jual, " \
            "((COALESCE(l.price_unit,0)*(1-COALESCE(l.discount,0)/100)-(COALESCE(l.discount_program,0)/COALESCE(l.product_uom_qty,0))-(COALESCE(l.discount_cash,0)/COALESCE(l.product_uom_qty,0))-(COALESCE(l.discount_lain,0)/COALESCE(l.product_uom_qty,0))) / 1.1)*(COALESCE(l.product_uom_qty,0)+COALESCE(l.lost_order_qty,0)) as jumlah_demand, " \
            "((COALESCE(l.price_unit,0)*(1-COALESCE(l.discount,0)/100)-(COALESCE(l.discount_program,0)/COALESCE(l.product_uom_qty,0))-(COALESCE(l.discount_cash,0)/COALESCE(l.product_uom_qty,0))-(COALESCE(l.discount_lain,0)/COALESCE(l.product_uom_qty,0))) / 1.1)*(COALESCE(l.product_uom_qty,0)) as jumlah_supply, " \
            "((COALESCE(l.price_unit,0)*(1-COALESCE(l.discount,0)/100)-(COALESCE(l.discount_program,0)/COALESCE(l.product_uom_qty,0))-(COALESCE(l.discount_cash,0)/COALESCE(l.product_uom_qty,0))-(COALESCE(l.discount_lain,0)/COALESCE(l.product_uom_qty,0))) / 1.1)*(COALESCE(l.lost_order_qty,0)) as jumlah_order " \
            "FROM " \
            "sale_order_line l " \
            "LEFT JOIN sale_order obj ON l.order_id = obj.id " \
            "LEFT JOIN dym_branch b ON b.id = obj.branch_id " \
            "LEFT JOIN product_product p ON p.id = l.product_id " \
            "LEFT JOIN product_template t ON t.id = p.product_tmpl_id " \
            "where 1=1 and obj.state in ('progress','manual','shipping_except','invoice_except','done') "
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        query_end=""
        query_end2=""
        if trx_start_date :
            query_end +=" AND obj.date >= '%s'" % str(trx_start_date)
            query_end2 +=" AND obj.date_order >= '%s'" % str(trx_start_date)
        if trx_end_date :
            query_end +=" AND obj.date <= '%s 23:59:59'" % str(trx_end_date)
            query_end2 +=" AND obj.date_order <= '%s 23:59:59'" % str(trx_end_date)
        if branch_ids :
            query_end +=" AND obj.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
            query_end2 +=" AND obj.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        reports = [report_service_rate]
        
        # query_order = "order by cabang"
        query_order = ""
        for report in reports:
            cr.execute(query_start + query_end + query_order + " UNION ALL " + query_start2 + query_end2 + query_order)
            all_lines = cr.dictfetchall()
            id_ai = []
            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': 0,      
                        'id_ai': x['id_ai'] if x['id_ai'] != None else 0,      
                        'branch_id': str(x['branch_id'].encode('ascii','ignore').decode('ascii')) if x['branch_id'] != None else '',
                        'tipe_dok': str(x['tipe_dok'].encode('ascii','ignore').decode('ascii')) if x['tipe_dok'] != None else '',
                        'date': str(x['date']) if x['date'] != None else '',
                        'number': str(x['number'].encode('ascii','ignore').decode('ascii')) if x['number'] != None else '',
                        'product_code': str(x['product_code'].encode('ascii','ignore').decode('ascii')) if x['product_code'] != None else '',
                        'product_name': str(x['description']) if 'description' in x and x['description'] != None else str(x['default_code']) if 'default_code' in x and x['default_code'] != None else '',
                        'het': x['het'],
                        'qty_demand': x['qty_demand'],
                        'qty_supply': x['qty_supply'],
                        'qty_backorder': x['qty_backorder'],
                        'net_jual': x['net_jual'],
                        'jumlah_demand': x['jumlah_demand'],
                        'jumlah_supply': x['jumlah_supply'],
                        'jumlah_order': x['jumlah_order'],
                        },
                    all_lines)
                for p in p_map:
                    if p['id_ai'] not in map(
                            lambda x: x.get('id_ai', None), id_ai):
                        records = filter(
                            lambda x: x['id_ai'] == p['id_ai'], all_lines)
                        p.update({'lines': records})
                        id_ai.append(p)
                        if records[0]['product_code'] not in report['product_codes']:
                            report['product_codes'].append(records[0]['product_code'])
                        if records[0]['product_code'] not in report['product_supplied'] and records[0]['qty_supply'] > 0:
                            report['product_supplied'].append(records[0]['product_code'])
                report.update({'id_ai': id_ai})
                # report.update({'id_ai': p_map})

        reports = filter(lambda x: x.get('id_ai'), reports)

        if not reports :
            raise osv.except_osv(_('Data Not Found!'), _('Tidak ditemukan data dari hasil filter report service rate.'))

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_service_rate_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_service_rate_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_service_rate.report_service_rate'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_service_rate.report_service_rate'
    _wrapped_report_class = dym_report_service_rate_print
