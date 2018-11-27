from datetime import datetime, date, timedelta
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)
class dym_report_cash_flow_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_cash_flow_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        division = data['division']
        start_date = data['start_date']
        end_date = data['end_date']
        status = data['status']
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        bank_ids = data['bank_ids']
        account_ids = data['account_ids']
        journal_ids = data['journal_ids']

        title_prefix = ''
        title_short_prefix = ''
        
        report_cash_flow = {
            'type': 'receivable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Cash Flow')}

        query_start = "SELECT aml.id as id_aml, " \
            "b.code as cabang, " \
            "aml.division as division, " \
            "rp.default_code as partner_code, " \
            "rp.name as partner_name, " \
            "a.code as account_code, " \
            "'' as account_sap, " \
            "b.profit_centre as profit_centre, " \
            "aml.date as date_aml, " \
            "aml.date_maturity as due_date, " \
            "CURRENT_DATE - aml.date_maturity as overdue, " \
            "aml.reconcile_id as status, " \
            "aml.reconcile_partial_id as partial, " \
            "aml.debit as debit, " \
            "aml.credit as credit, " \
            "aml.name as name, " \
            "aml.ref as reference, " \
            "j.name as journal_name, " \
            "m.name as invoice_name, " \
            "CASE WHEN aml.reconcile_id IS NOT NULL THEN 0.0 " \
            "    WHEN aml.reconcile_partial_id IS NULL THEN aml.debit - aml.credit " \
            "    ELSE aml3.debit - aml3.credit " \
            "END as residual, " \
            "a.type as account_type " \
            "FROM " \
            "account_move_line aml " \
            "LEFT JOIN (SELECT aml2.reconcile_partial_id, SUM(aml2.debit) as debit, SUM(aml2.credit) as credit FROM account_move_line aml2 WHERE aml2.reconcile_partial_id is not Null GROUP BY aml2.reconcile_partial_id) aml3 on aml.reconcile_partial_id = aml3.reconcile_partial_id " \
            "LEFT JOIN dym_branch b ON b.id = aml.branch_id " \
            "LEFT JOIN account_move m ON m.id = aml.move_id " \
            "LEFT JOIN res_partner rp ON rp.id = aml.partner_id " \
            "LEFT JOIN account_account a ON a.id = aml.account_id " \
            "LEFT JOIN account_journal j ON j.id = aml.journal_id " \
            "where 1=1 "
            
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        query_order = ""
        query_end=""
        if division :
            query_end +=" AND aml.division = '%s'" % str(division)
        if status == 'reconciled' :
            query_end += "AND aml.date is not null"
            query_end +=" AND aml.reconcile_id is Null"
            # query_end +=" AND aml.reconcile_id is not Null"
            if start_date :
                query_end +=" AND aml.date >= '%s'" % str(start_date)
            if end_date :
                query_end +=" AND aml.date <= '%s'" % str(end_date)
            if bank_ids :
                query_end +=" AND aml.account_id in %s" % str(
                    tuple(bank_ids)).replace(',)', ')')
            query_order = "order by account_code"
            report_cash_flow['status'] = 'reconciled'
        elif status == 'outstanding' :
            query_end += "AND aml.date_maturity is not null"
            query_end +=" AND aml.reconcile_id is Null"
            if account_ids :
                query_end+=" AND aml.account_id in %s" % str(
                    tuple(account_ids)).replace(',)', ')')
            query_order = "order by account_type, cabang"
            report_cash_flow['status'] = 'outstanding'
        if branch_ids :
            query_end +=" AND aml.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if partner_ids :
            query_end+=" AND aml.partner_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        if journal_ids :
            query_end+=" AND aml.journal_id in %s" % str(
                tuple(journal_ids)).replace(',)', ')')
        reports = [report_cash_flow]
        
        for report in reports:
            cr.execute(query_start + query_end + query_order)
            all_lines = cr.dictfetchall()
            ids_aml = []

            if all_lines:
                def lines_map(x):
                        x.update({'docname': x['cabang']})
                map(lines_map, all_lines)
                for cnt in range(len(all_lines)-1):
                    if all_lines[cnt]['id_aml'] != all_lines[cnt+1]['id_aml']:
                        all_lines[cnt]['draw_line'] = 1
                    else:
                        all_lines[cnt]['draw_line'] = 0
                all_lines[-1]['draw_line'] = 1

                p_map = map(
                    lambda x: {
                        'no': 0,
                        'id_aml': str(x['id_aml']) if x['id_aml'] != None else '',
                        'cabang': str(x['cabang'].encode('ascii','ignore').decode('ascii')) if x['cabang'] != None else '',
                        'division': str(x['division'].encode('ascii','ignore').decode('ascii')) if x['division'] != None else '',
                        'partner_code': str(x['partner_code'].encode('ascii','ignore').decode('ascii')) if x['partner_code'] != None else '',
                        'partner_name': str(x['partner_name'].encode('ascii','ignore').decode('ascii')) if x['partner_name'] != None else '',
                        'account_code': str(x['account_code'].encode('ascii','ignore').decode('ascii')) if x['account_code'] != None else '',
                        'account_sap': str(x['account_sap'][:6].encode('ascii','ignore').decode('ascii')) + "-" + str(x['profit_centre'].encode('ascii','ignore').decode('ascii')) + str(x['account_sap'][6:].encode('ascii','ignore').decode('ascii')) if x['account_sap'] != None and x['profit_centre'] != None else '',
                        'invoice_name': str(x['invoice_name'].encode('ascii','ignore').decode('ascii')) if x['invoice_name'] != None else '',
                        'name': str(x['name'].encode('ascii','ignore').decode('ascii')) if x['name'] != None else '',
                        'date_aml': str(x['date_aml']) if x['date_aml'] != None else '',
                        'due_date': str(x['due_date']) if x['due_date'] != None else '',
                        'overdue': str(x['overdue']) if x['overdue'] != None else '',
                        'status': 'Outstanding' if str(x['status']) == 'None' else 'Reconciled',
                        'tot_invoice': x['debit'] - x['credit'],
                        'amount_residual': x['residual'] if x['residual'] != None else False,
                        'current': (x['residual'] if x['residual'] != None else False) if x['overdue'] <= 0 or x['overdue'] == None else False,
                        # 'overdue_1_30': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 0 and x['overdue'] < 31 else False,
                        # 'overdue_31_60': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 30 and x['overdue'] < 61 else False,
                        # 'overdue_61_90': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 60 and x['overdue'] < 91 else False,
                        # 'overdue_91_n': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 90 else False,
                        'reference': str(x['reference'].encode('ascii','ignore').decode('ascii')) if x['reference'] != None else '',
                        'journal_name': str(x['journal_name'].encode('ascii','ignore').decode('ascii')) if x['journal_name'] != None else '',
                        'account_type': str(x['account_type'].encode('ascii','ignore').decode('ascii')) if x['account_type'] != None else ''},
                        
                    all_lines)
                if status == 'outstanding':                 
                    date_check = 'due_date'
                elif status == 'reconciled':
                    date_check = 'date_aml'

                for line in p_map:
                    if not start_date:
                        line['first_date'] = sorted(p_map, key=lambda k: k[date_check])[0][date_check]
                    else:
                        line['first_date'] = str(start_date)

                    if not end_date:
                        line['last_date'] = sorted(p_map, key=lambda k: k[date_check], reverse=True)[0][date_check]
                    else:
                        line['last_date'] = str(end_date)
#                 for p in p_map:
#                     if p['id_aml'] not in map(
#                             lambda x: x.get('id_aml', None), ids_aml):
#                         ids_aml.append(p)
#                         lines = filter(
#                             lambda x: x['id_aml'] == p['id_aml'], all_lines)
#                         p.update({'lines': lines})
#                         p.update(
#                             {'d': 1,
#                              'c': 2,
#                              'b': 3})
                report.update({'ids_aml': p_map})

        reports = filter(lambda x: x.get('ids_aml'), reports)
        
        if not reports :
            raise osv.except_osv(('Perhatian !'), ("Data Cash Flow tidak ditemukan."))
            # reports = [{'title_short': 'Laporan Cash Flow','type': 'receivable', 'ids_aml':
            #                 [{'reference': 'NO DATA FOUND',
            #                   'due_date': 'NO DATA FOUND',
            #                   'tot_invoice': 0,
            #                   'date_aml': 'NO DATA FOUND',
            #                   'partner_code': 'NO DATA FOUND',
            #                   'no': 0,
            #                   'cabang': 'NO DATA FOUND',
            #                   'current': 0,
            #                   # 'overdue_91_n': 0,
            #                   'journal_name': 'NO DATA FOUND',
            #                   # 'overdue_61_90': 0,
            #                   'status': 'NO DATA FOUND',
            #                   'division': 'NO DATA FOUND',
            #                   # 'overdue_31_60': 0,
            #                   'partner_name': 'NO DATA FOUND',
            #                   'id_aml': 0,
            #                   'account_sap': 'NO DATA FOUND',
            #                   'amount_residual': 0,
            #                   # 'overdue_1_30': 0,
            #                   'name': 'NO DATA FOUND',
            #                   'invoice_name': 'NO DATA FOUND',
            #                   'account_code': 'NO DATA FOUND',
            #                   'first_date': datetime.now().strftime('%Y-%m-%d'),
            #                   'last_date': datetime.now().strftime('%Y-%m-%d'),
            #                   'account_type': 'NO DATA FOUND',
            #                   'overdue': 'NO DATA FOUND'}], 'title': ''}]

            if status == 'reconciled':
                reports[0]['status'] = 'reconciled'
            elif status == 'outstanding':
                reports[0]['status'] = 'outstanding'
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            'date_from': start_date,
            'date_to': end_date,
            })
        objects = False
        super(dym_report_cash_flow_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_cash_flow_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_cash_flow.report_cash_flow'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_cash_flow.report_cash_flow'
    _wrapped_report_class = dym_report_cash_flow_print
