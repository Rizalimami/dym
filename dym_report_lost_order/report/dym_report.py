from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_lost_order_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_lost_order_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        product_ids = data['product_ids']

        branch_status = False
        division = data['division']

        title_prefix = ''
        title_short_prefix = ''
        
        report_lost_order = {
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Lost Order')}

        query_start = "SELECT COALESCE(b.name,'') as branch_id, " \
            "COALESCE(ld.tipe_dok,'') as tipe_dok, " \
            "ld.date as date, " \
            "COALESCE(ld.no_dok,'') as no_dok, " \
            "COALESCE(rp.name,'') as customer_name, " \
            "COALESCE(rp.mobile,'') as customer_hp, " \
            "COALESCE(rp.street,'') as customer_alamat, " \
            "COALESCE(p.name_template,'') as product_code, " \
            "COALESCE(p.default_code,'') as default_code, " \
            "COALESCE(t.description,'') as description, " \
            "COALESCE(ld.pemenuhan_qty,0) as pemenuhan_qty, " \
            "COALESCE(ld.lost_order_qty,0) as lost_order_qty, " \
            "COALESCE(ld.pemenuhan_qty,0)+COALESCE(ld.lost_order_qty,0) as permintaan_qty, " \
            "COALESCE(ld.lost_order_qty,0)/(COALESCE(ld.pemenuhan_qty,0)+COALESCE(ld.lost_order_qty,0))*100 as s_r, " \
            "COALESCE(ld.het,0) as het, " \
            "COALESCE(ld.het,0)*(COALESCE(ld.pemenuhan_qty,0)+COALESCE(ld.lost_order_qty,0)) as jumlah_het " \
            "FROM " \
            "dym_lost_order ld " \
            "LEFT JOIN dym_branch b ON ld.branch_id = b.id " \
            "LEFT JOIN product_product p ON p.id = ld.product_id " \
            "LEFT JOIN product_template t ON t.id = p.product_tmpl_id " \
            "LEFT JOIN res_partner rp on rp.id=ld.customer_id " \
            "where ld.branch_id is not null and ld.product_id is not null and ld.date is not null and ld.lost_order_qty > 0  "
            
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        query_end=""
        if start_date :
            query_end +=" AND ld.date >= '%s' " % str(start_date)
        if end_date :
            query_end +=" AND ld.date <= '%s' " % str(end_date)
        if product_ids :
            query_end +=" AND ld.product_id in %s " % str(
                tuple(product_ids)).replace(',)', ')')
        if branch_ids :
            query_end +=" AND ld.branch_id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
        reports = [report_lost_order]
        
        query_order = " "
        for report in reports:
            cr.execute(query_start + query_end + query_order)
            print query_start + query_end + query_order
            all_lines = cr.dictfetchall()
            id_ai = []
            if all_lines:

                p_map = map(
                    lambda x: {
                        'no': 0,      
                        'branch_id': str(x['branch_id'].encode('ascii','ignore').decode('ascii')) if x['branch_id'] != None else '',
                        'tipe_dok': str(x['tipe_dok'].encode('ascii','ignore').decode('ascii')) if x['tipe_dok'] != None else '',
                        'date': str(x['date']) if x['date'] != None else '',
                        'no_dok': str(x['no_dok'].encode('ascii','ignore').decode('ascii')) if x['no_dok'] != None else '',
                        'product_code': str(x['product_code'].encode('ascii','ignore').decode('ascii')) if x['product_code'] != None else '',
                        'product_name': str(x['default_code'].encode('ascii','ignore').decode('ascii')) if x['default_code'] != None else str(x['description'].encode('ascii','ignore').decode('ascii')) if x['description'] != None else '',
                        'permintaan_qty': x['permintaan_qty'],
                        'pemenuhan_qty': x['pemenuhan_qty'],
                        'lost_order_qty': x['lost_order_qty'],
                        's_r': str(x['s_r'])+'%',
                        'het': x['het'],
                        'jumlah_het': x['jumlah_het'],
                        'status': '',
                        'no_po': '',
                        'tgl_po': '',
                        'division': division,
                        'customer_name': x['customer_name'],
                        'customer_alamat': x['customer_alamat'],
                        'customer_hp': x['customer_hp'],
                        },
                       
                    all_lines)
                report.update({'id_ai': p_map})

        reports = filter(lambda x: x.get('id_ai'), reports)
        
        if not reports :
            reports = [{'title_short': 'Laporan Lost Order', 'type': ['out_invoice','in_invoice','in_refund','out_refund'], 'id_ai':
                            [{'no': 0,
                              'branch_id': 'NO DATA FOUND',
                              'tipe_dok': 'NO DATA FOUND',
                              'date': 'NO DATA FOUND',
                              'no_dok': 'NO DATA FOUND',
                              'product_code': 'NO DATA FOUND',
                              'product_name': 'NO DATA FOUND',
                              'permintaan_qty': 0,
                              'pemenuhan_qty': 0,
                              'lost_order_qty': 0,
                              's_r': 'NO DATA FOUND',
                              'het': 0,
                              'jumlah_het': 0,
                              'status': 'NO DATA FOUND',
                              'no_po': 'NO DATA FOUND',
                              'tgl_po': 'NO DATA FOUND',
                              'division': 'NO DATA FOUND',}], 'title': ''}]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_lost_order_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_hutan_invoice_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_lost_order.report_lost_order'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_lost_order.report_lost_order'
    _wrapped_report_class = dym_report_lost_order_print
