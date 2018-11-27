from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_unitentrynopol_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_unitentrynopol_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        
        
        query_unitentrynopol = """
            select wo.id id_wo, 
            lot.no_polisi no_pol, 
            wo.date::timestamp::date tgl_wo, 
            wo.name no_wo, 
            res.name nama_customer, 
            hr.name_related nama_mekanik
            from dym_work_order wo
            left join stock_production_lot lot on wo.lot_id = lot.id
            left join res_partner res on wo.customer_id = res.id
            left join hr_employee hr on wo.mekanik_id = hr.id
        """

        query_where = " where wo.no_pol is not null "
        if data['start_date']:
            query_where += " and wo.date >= '%s'" % str(data['start_date'])
        if data['end_date']:
            query_where += " and wo.date <= '%s'" % str(data['end_date'] + ' 23:59:59')
        if data['branch_ids']:
            query_where += " and wo.branch_id in %s" % str(tuple(data['branch_ids'])).replace(',)', ')')

        self.cr.execute(query_unitentrynopol + query_where)
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                'no' : 0,
                'id_wo' : x['id_wo'],
                'no_pol': x['no_pol'],
                'tgl_wo': x['tgl_wo'],
                'no_wo': x['no_wo'],
                'nama_customer': x['nama_customer'].upper(),
                'total_jasa': 0,
                'total_part': 0,
                'total': 0,
                'nama_mekanik': x['nama_mekanik'].upper()
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])

            for x in reports[0]['datas']:
                wol_ids = self.pool.get('dym.work.order.line').search(cr, uid, [('work_order_id','=', x['id_wo'])])
                wol = self.pool.get('dym.work.order.line').browse(cr, uid, wol_ids)
                for item_wol in wol:
                    x['total'] += item_wol.price_subtotal
                    if item_wol.categ_id == 'Service': x['total_jasa'] += item_wol.price_subtotal
                    if item_wol.categ_id == 'Sparepart': x['total_part'] += item_wol.price_subtotal

        else :
            reports = [{'datas': [{
                'no' : 0,
                'id_wo': 0,
                'no_pol': 'NO DATA FOUND',
                'tgl_wo': 'NO DATA FOUND',
                'no_wo': 'NO DATA FOUND',
                'nama_customer': 'NO DATA FOUND',
                'total_jasa': 0,
                'total_part': 0,
                'total': 0,
                'nama_mekanik': 'NO DATA FOUND'
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(dym_report_unitentrynopol_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_unitentrynopol_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_unitentrynopol.report_unitentrynopol'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_unitentrynopol.report_unitentrynopol'
    _wrapped_report_class = dym_report_unitentrynopol_print
    