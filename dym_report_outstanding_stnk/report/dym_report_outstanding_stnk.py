from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_outstanding_stnk_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_outstanding_stnk_print, self).__init__(
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
        partner_ids = data['partner_ids']

        title_prefix = ''
        title_short_prefix = ''
        
        report_outstanding_stnk = {
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Outstanding STNK')}

        query_start = "SELECT rec.id as record_id, " \
            "COALESCE(ps.name,'') as proses_stnk, "\
            "COALESCE(tb.name,'') as trans_no, " \
            "COALESCE(b.name,'') as branch_name, " \
            "p.name as partner_name, " \
            "ai1.number as invoice_tagihan_number, " \
            "ai1.date_invoice as invoice_tagihan_date, " \
            "ai2.number as invoice_dso_number, " \
            "ai2.date_invoice as invoice_dso_date, " \
            "lot.name as nosin, " \
            "rec.total_notice as notice, " \
            "rec.total_jasa as jasa, " \
            "rec.total_estimasi as total_estimasi, " \
            "rec.pajak_progressive as pajak_progressive, " \
            "rec.total_tagihan as total_tagihan, " \
            "COALESCE(rec.total_tagihan,0) - COALESCE(rec.total_estimasi,0) - COALESCE(rec.pajak_progressive,0) as koreksi " \
            "FROM " \
            "stock_production_lot lot "\
            "LEFT JOIN dym_proses_stnk ps ON ps.id = lot.proses_stnk_id "\
            "LEFT JOIN dym_proses_birojasa tb ON tb.id = lot.proses_biro_jasa_id "\
            "LEFT JOIN dym_proses_birojasa_line rec ON lot.id = rec.name "\
            "LEFT JOIN dym_branch b ON ps.branch_id = b.id "\
            "LEFT JOIN res_partner p ON p.id = lot.biro_jasa_id "\
            "LEFT JOIN account_invoice ai1 ON ai1.origin = tb.name and ai1.type = 'in_invoice' "\
            "LEFT JOIN dealer_sale_order dso ON dso.id = lot.dealer_sale_order_id "\
            "LEFT JOIN account_invoice ai2 ON ai2.origin = dso.name and ai2.type = 'out_invoice' and ((ai2.tipe = 'finco' and dso.finco_id is not null) or (ai2.tipe = 'customer' and dso.finco_id is null)) "\
            "WHERE 1=1 and ps.state='posted' AND lot.penerimaan_stnk_id is null "
            
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        query_end=""
        if trx_start_date :
            query_end +=" AND ps.tgl_proses_stnk >= '%s'" % str(trx_start_date)
        if trx_end_date :
            query_end +=" AND ps.tgl_proses_stnk <= '%s'" % str(trx_end_date)
        if partner_ids :
            query_end +=" AND ps.partner_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        if branch_ids :
            query_end +=" AND ps.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        reports = [report_outstanding_stnk]
        
        query_order = ""

        print query_start + query_end + query_order

        for report in reports:
            cr.execute(query_start + query_end + query_order)
            all_lines = cr.dictfetchall()
            records = []

            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': 0, 
                        'proses_stnk': x['proses_stnk'],     
                        'record_id': x['record_id'] if x['record_id'] != None else '',      
                        'trans_no': str(x['trans_no'].encode('ascii','ignore').decode('ascii')) if x['trans_no'] != None else '',
                        'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                        'partner_name': str(x['partner_name'].encode('ascii','ignore').decode('ascii')) if x['partner_name'] != None else '',
                        'invoice_tagihan_number': str(x['invoice_tagihan_number'].encode('ascii','ignore').decode('ascii')) if x['invoice_tagihan_number'] != None else '',
                        'invoice_tagihan_date': str(x['invoice_tagihan_date'].encode('ascii','ignore').decode('ascii')) if x['invoice_tagihan_date'] != None else '',
                        'invoice_dso_number': str(x['invoice_dso_number'].encode('ascii','ignore').decode('ascii')) if x['invoice_dso_number'] != None else '',
                        'invoice_dso_date': str(x['invoice_dso_date'].encode('ascii','ignore').decode('ascii')) if x['invoice_dso_date'] != None else '',
                        'nosin': str(x['nosin'].encode('ascii','ignore').decode('ascii')) if x['nosin'] != None else '',
                        'notice': x['notice'],
                        'jasa': x['jasa'],
                        'total_estimasi': x['total_estimasi'],
                        'pajak_progressive': x['pajak_progressive'],
                        'total_tagihan': x['total_tagihan'],
                        'koreksi': x['koreksi'],
                        },
                    all_lines)

                for p in p_map:
                    p.update({'margin': 0})
                    records.append(p)
                    # if p['record_id'] not in map(lambda x: x.get('record_id', None), records):
                       #res = filter(lambda x: x['record_id'] == p['record_id'], all_lines)
                       #tb_line = self.pool.get('dym.proses.birojasa.line').browse(cr, uid, res[0]['record_id'])
                       #p.update({'margin': tb_line.margin})
                       # records.append(p)
                report.update({'records': records})

        reports = filter(lambda x: x.get('records'), reports)
        
        if not reports :
            raise osv.except_osv(('No Data Available !'), ("No records found for your selection!"))     

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        objects = False
        super(dym_report_outstanding_stnk_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_outstanding_stnk_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_outstanding_stnk.report_outstanding_stnk'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_outstanding_stnk.report_outstanding_stnk'
    _wrapped_report_class = dym_report_outstanding_stnk_print
