import time
from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)


class dym_bank_book_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_bank_book_report_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def get_fiscalyear(self,period_id):
        cr = self.cr
        query_fiscal = "SELECT fiscalyear_id FROM account_period WHERE id = %s"
        
        cr.execute(query_fiscal, (period_id, ))
        fiscalyear_id = cr.fetchall()
        return fiscalyear_id[0][0]
    
    def get_period(self,period_id,fiscalyear_id):
        cr = self.cr
        query_period = "SELECT id from account_period " \
            "WHERE id < %s AND fiscalyear_id = %s "
            
        cr.execute(query_period, (period_id,fiscalyear_id ))
        period_ids = cr.fetchall() 
        period_id_kolek = []
        for id in period_ids:
            period_id_kolek.append(id)      
        if not period_id_kolek :
            return False 
             
        return period_id_kolek

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        journal_id = data['journal_id']
        start_date = data['start_date']
        end_date = data['end_date']
        start_value_date = data['start_value_date']
        end_value_date = data['end_value_date']
        title_prefix = ''
        title_short_prefix = ''
        
        bank_balance = 0
        where_account = " 1=1 "
        if journal_id:
            journals = self.pool.get('account.journal').browse(cr,uid,journal_id[0])
            account_ids = []
            for journal in journals:
                if journal.default_debit_account_id and journal.default_debit_account_id.id not in account_ids:
                    account_ids.append(journal.default_debit_account_id.id)
                if journal.default_credit_account_id and journal.default_credit_account_id.id not in account_ids:
                    account_ids.append(journal.default_credit_account_id.id)
                bank_balance = journal.default_credit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=True).balance or journal.default_debit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=True).balance
            where_account=" a.id  in %s " % str(
                tuple(account_ids)).replace(',)', ')')              
        
        saldo_awal = bank_balance

        report_bank_book = {
            'type': 'BankBook',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('LAPORAN BANK BOOK'),
            'saldo_awal': saldo_awal,
            'start_date': start_date,
            'end_date': end_date
            }  

        area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids_user = [b.id for b in area_user]
        branch_ids = branch_ids_user
        where_start_date = " l.date >= '%s' " % start_date
        where_end_date = " l.date <= '%s' " % end_date
        where_value_start = " 1=1 "
        if start_value_date:
            where_value_start = " (at.value_date >= '%s' OR " % start_value_date
            where_value_start += " cg.value_date >= '%s' OR " % start_value_date
            where_value_start += " av.value_date >= '%s' OR " % start_value_date
            where_value_start += " bt.value_date >= '%s') " % start_value_date
        where_value_end = " 1=1 "
        if end_value_date:
            where_value_end = " (at.value_date <= '%s' OR " % end_value_date
            where_value_end += " cg.value_date <= '%s' OR " % end_value_date
            where_value_end += " av.value_date <= '%s' OR " % end_value_date
            where_value_end += " bt.value_date <= '%s') " % end_value_date
        query_bank_book = "SELECT l.id, l.analytic_account_id, l.name, l.ref, p.name as partner_name, a.name as account_name, a.code as account_code, l.account_id, l.date, l.debit, l.credit, fc.name as finance_company, at.value_date as at_value_date, cg.value_date as cg_value_date, av.value_date as av_value_date, bt.value_date as bt_value_date, avp.date as avp_value_date FROM account_move_line l LEFT JOIN account_move m on m.id = l.move_id LEFT JOIN account_account a on a.id = l.account_id LEFT JOIN res_partner p on p.id = l.partner_id LEFT JOIN res_partner fc on fc.id = l.finco_id LEFT JOIN dym_alokasi_titipan at on at.name = m.name LEFT JOIN dym_clearing_giro cg on cg.name = m.name LEFT JOIN account_voucher av on av.number = m.name LEFT JOIN dym_bank_transfer bt on bt.name = m.name LEFT JOIN dym_advance_payment avp on avp.name = m.name WHERE %s and %s and %s and %s and %s ORDER BY l.id asc" % (where_account, where_start_date, where_end_date, where_value_start, where_value_end)

        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        reports = [report_bank_book]
        
        for report in reports:
            a = cr.execute(query_bank_book)
            all_lines = cr.dictfetchall()
            
            move_lines = []            
            if all_lines:
                p_map = map(
                    lambda x: {
                        'no':0,
                        'id': x['id'],
                        'date': x['date'] if x['date'] != None else '',  
                        'value_date': x['at_value_date'] if x['at_value_date'] and x['at_value_date'] != None else x['cg_value_date'] if x['cg_value_date'] and x['cg_value_date'] != None else x['av_value_date'] if x['av_value_date'] and x['av_value_date'] != None else x['bt_value_date'] if x['bt_value_date'] and x['bt_value_date'] != None else x['avp_value_date'] if x['avp_value_date'] and x['avp_value_date'] != None else '',
                        'debit': x['debit'] if x['debit'] > 0 else 0.0,
                        'credit': x['credit'] if x['credit'] > 0 else 0.0,
                        'account_code': x['account_code'].encode('ascii','ignore').decode('ascii') if x['account_code'] != None else '',
                        'account_name': x['account_name'].encode('ascii','ignore').decode('ascii') if x['account_name'] != None else '',
                        'partner_name': x['partner_name'].encode('ascii','ignore').decode('ascii') if x['partner_name'] != None else '',
                        'finance_company': x['finance_company'].encode('ascii','ignore').decode('ascii') if x['finance_company'] != None else '',
                        'name': x['name'].encode('ascii','ignore').decode('ascii') if x['name'] != None else '',
                        'ref': x['ref'].encode('ascii','ignore').decode('ascii') if x['ref'] != None else '',
                        'analytic_4': x['analytic_account_id'] if x['analytic_account_id'] != None else '',
                        },
                            
                    all_lines)
                
                for p in p_map:
                    if p['id'] not in map(
                            lambda x: x.get('id', None), move_lines):
                        account_move_lines = filter(
                            lambda x: x['id'] == p['id'], all_lines)
                        analytic_1 = ''
                        analytic_2 = ''
                        analytic_3 = ''
                        analytic_4 = ''
                        analytic_1_name = ''
                        analytic_2_name = ''
                        analytic_3_name = ''
                        analytic_4_name = ''
                        analytic = self.pool.get('account.analytic.account').browse(cr, uid, account_move_lines[0]['analytic_account_id']) or ''
                        branch_name = ''
                        branch = False
                        branch_status_1 = ''
                        branch_name = ''
                        branch_id = ''
                        if analytic:
                            if analytic.type == 'normal':
                                if analytic.segmen == 1 and analytic_1 == '':
                                    analytic_1_name = analytic.name
                                    analytic_1 = analytic.code
                                if analytic.segmen == 2 and analytic_2 == '':
                                    analytic_2_name = analytic.name
                                    analytic_2 = analytic.code
                                if analytic.segmen == 3 and analytic_3 == '':
                                    analytic_3_name = analytic.name
                                    analytic_3 = analytic.code
                                    branch = analytic.sudo().branch_id
                                    branch_name = branch.name
                                    branch_status_1 = branch.branch_status
                                    branch_id = branch.id
                                if analytic.segmen == 4 and analytic_4 == '':
                                    analytic_4_name = analytic.name
                                    analytic_4 = analytic.code
                                    analytic_id = analytic
                            while (analytic.parent_id):
                                analytic = analytic.parent_id
                                if analytic.type == 'normal':
                                    if analytic.segmen == 1 and analytic_1 == '':
                                        analytic_1_name = analytic.name
                                        analytic_1 = analytic.code
                                    if analytic.segmen == 2 and analytic_2 == '':
                                        analytic_2_name = analytic.name
                                        analytic_2 = analytic.code
                                    if analytic.segmen == 3 and analytic_3 == '':
                                        analytic_3_name = analytic.name
                                        analytic_3 = analytic.code
                                        branch = analytic.sudo().branch_id
                                        branch_name = branch.name
                                        branch_status_1 = branch.branch_status
                                        branch_id = branch.id
                                    if analytic.segmen == 4 and analytic_4 == '':
                                        analytic_4_name = analytic.name
                                        analytic_4 = analytic.code
                                        analytic_id == analytic
                            if (branch and branch_ids and branch.id not in branch_ids):
                                continue

                            analytic_2_branch = analytic_2
                            if analytic_2 in ['210','220','230']:
                                if branch_status_1 == 'H123':
                                    analytic_2_branch = analytic_2[:2] + '1'
                                elif branch_status_1 == 'H23':
                                    analytic_2_branch = analytic_2[:2] + '2'
                                else:
                                    analytic_2_branch = analytic_2

                            analytic_1_code = analytic_1
                            analytic_2_code = analytic_2_branch
                            analytic_3_code = analytic_3
                            analytic_4_code = analytic_4

                            analytic_combination = analytic_1 + '/' + analytic_2_branch + '/' + analytic_3 + '/' + analytic_4

                            p.update({'lines': account_move_lines})
                            p.update({'analytic_1': analytic_1_code})
                            p.update({'analytic_2': analytic_2_code})
                            p.update({'analytic_3': analytic_3_code})
                            p.update({'analytic_4': analytic_4_code})
                            p.update({'branch_id': branch_id})
                            p.update({'branch_status': branch_status_1})
                            p.update({'branch_name': branch_name})
                            p.update({'analytic_combination': analytic_combination})
                            move_lines.append(p)
                report.update({'move_lines': move_lines})

        reports = filter(lambda x: x.get('move_lines'), reports)

        if not reports:
            reports = [{
            'type': 'BankBook',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('LAPORAN BANK BOOK')   ,
            'saldo_awal': saldo_awal,
            'start_date': start_date,
            'end_date': end_date,
            'move_lines':
                        [{
                        'no':0,
                        'branch_status': 'NO DATA FOUND',
                        'branch_name': 'NO DATA FOUND',
                        'account_code': 'NO DATA FOUND',
                        'account_name': 'NO DATA FOUND',
                        'partner_name':'NO DATA FOUND',
                        'finance_company':'NO DATA FOUND',
                        'name': 0,
                        'ref': 0,
                        'date': 'NO DATA FOUND',
                        'value_date': 'NO DATA FOUND',
                        'debit': 0.0,
                        'credit':  0.0,
                        'analytic_1': 'NO DATA FOUND',
                        'analytic_2': 'NO DATA FOUND',
                        'analytic_3': 'NO DATA FOUND',
                        'analytic_4': 'NO DATA FOUND',
                        'analytic_combination': 'NO DATA FOUND',
                        }], 
                        
            }]
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        objects = False
        super(dym_bank_book_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_bank_book_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_account_move.report_bank_book'
    _inherit = 'report.abstract_report'
    _template = 'dym_account_move.report_bank_book'
    _wrapped_report_class = dym_bank_book_report_print
