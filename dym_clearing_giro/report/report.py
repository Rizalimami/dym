from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_clearing_bank_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_clearing_bank_print, self).__init__(
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
        start_due_date = data['start_due_date']
        end_due_date = data['end_due_date']
        state = data['state']
        division = data['division']
        branch_ids = data['branch_ids']
        journal_ids = data['journal_ids']
        account_ids = data['account_ids']
        partner_ids = data['partner_ids']


        title_prefix = ''
        title_short_prefix = ''
        
        report_clearing_bank = {
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Clearing Bank')}

        query_start = "SELECT COALESCE(b.name,'') as branch_id, " \
            "COALESCE(l.division,'') as division, " \
            "l.date as date, " \
            "l.date_maturity as due_date, " \
            "COALESCE(l.clear_state,'') as status, " \
            "c.value_date as tgl_cair, " \
            "r.name as supplier, " \
            "COALESCE(c.ref,'') as no_sp, " \
            "n.name as no_bank, " \
            "COALESCE(c.memo,'') as memo, " \
            "COALESCE(l.credit,0) as total " \
            "FROM " \
            "account_move_line l " \
            "LEFT JOIN account_move m ON l.move_id = m.id " \
            "LEFT JOIN account_journal n ON l.journal_id = n.id " \
            "LEFT JOIN dym_branch b ON l.branch_id = b.id " \
            "LEFT JOIN res_partner r ON l.partner_id = r.id " \
            "LEFT JOIN dym_clearing_giro_move_line_rel cgml ON cgml.move_line_id = l.id " \
            "LEFT JOIN dym_clearing_giro c ON cgml.clearing_id = c.id and c.state = 'done' " \
            "where 1=1 "
            
        move_selection = ""
        report_info = _('')
        move_selection += ""

        query_end=""
        if start_date :
            query_end +=" AND l.date >= '%s' " % str(start_date)
        if end_date :
            query_end +=" AND l.date <= '%s' " % str(end_date)
        if start_due_date :
            query_end +=" AND l.date_maturity >= '%s' " % str(start_due_date)
        if end_due_date :
            query_end +=" AND l.date_maturity <= '%s' " % str(end_due_date)
        if state == 'open_cleared':
            query_end +=" AND l.clear_state in ('open','running','cleared') "
        else:
            query_end +=" AND l.clear_state = '%s' " % str(state)
        if division :
            query_end +=" AND l.division = '%s' " % str(division)
        if journal_ids :
            query_end +=" AND l.journal_id in %s " % str(
                tuple(journal_ids)).replace(',)', ')')
        if account_ids :
            query_end +=" AND l.account_id in %s " % str(
                tuple(account_ids)).replace(',)', ')')
        if partner_ids :
            query_end +=" AND l.partner_id in %s " % str(
                tuple(partner_ids)).replace(',)', ')')
        if branch_ids :
            query_end +=" AND l.branch_id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
        reports = [report_clearing_bank]
        
        # query_order = "order by cabang"
        query_order = " "
        for report in reports:
            cr.execute(query_start + query_end + query_order)
            all_lines = cr.dictfetchall()
            id_ai = []
            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': 0,      
                        'branch_id': str(x['branch_id'].encode('ascii','ignore').decode('ascii')) if x['branch_id'] != None else '',
                        'division': str(x['division'].encode('ascii','ignore').decode('ascii')) if x['division'] != None else '',
                        'date': str(x['date']) if x['date'] != None else '',
                        'due_date': str(x['due_date']) if x['due_date'] != None else '',
                        'status': x['status'],
                        'supplier': str(x['supplier']) if x['supplier'] != None else '',
                        'no_sp': str(x['no_sp']) if x['no_sp'] != None else '',
                        'no_bank': str(x['no_bank']) if x['no_bank'] != None else '',
                        'tgl_cair': str(x['tgl_cair']) if x['tgl_cair'] != None else '',
                        'memo': str(x['memo'].encode('ascii','ignore').decode('ascii')) if x['memo'] != None else '',
                        'total': x['total'],
                        },
                       
                    all_lines)
                report.update({'id_ai': p_map})

        reports = filter(lambda x: x.get('id_ai'), reports)
        
        if not reports :
            reports = [{'title_short': 'Laporan Clearing Bank', 'type': ['out_invoice','in_invoice','in_refund','out_refund'], 'id_ai':
                            [{'no': 0,
                              'branch_id': 'NO DATA FOUND',
                              'division': 'NO DATA FOUND',
                              'date': 'NO DATA FOUND',
                              'due_date': 'NO DATA FOUND',
                              'status': 'NO DATA FOUND',
                              'tgl_cair': 'NO DATA FOUND',
                              'supplier': 'NO DATA FOUND',
                              'no_sp': 'NO DATA FOUND',
                              'no_bank': 'NO DATA FOUND',
                              'memo': 'NO DATA FOUND',
                              'total': 0,}], 'title': ''}]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_clearing_bank_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_clearing_bank_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_clearing_giro.report_clearing_bank'
    _inherit = 'report.abstract_report'
    _template = 'dym_clearing_giro.report_clearing_bank'
    _wrapped_report_class = dym_report_clearing_bank_print
