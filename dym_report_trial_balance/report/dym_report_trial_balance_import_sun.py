from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)


class dym_trial_balance_import_sun_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_trial_balance_import_sun_report_print, self).__init__(
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
        account_ids = data['account_ids']        
        journal_ids = data['journal_ids']
        period_id = data['period_id']
        status = data['status']
        segmen = data['segmen']
        start_date = data['start_date']
        end_date = data['end_date']
        title_prefix = ''
        title_short_prefix = ''

        date_stop = self.pool.get('account.period').browse(cr,uid,period_id[0]).date_stop
        date_stop = datetime.strptime(date_stop, '%Y-%m-%d').strftime('%d %B %Y')
        
        report_trial_balance_import_sun = {
            'type': 'import_sun',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('LAPORAN MUTASI PER CABANG')   , 
            'period': date_stop
            }  

        where_account = " 1=1 "
        if account_ids :
            where_account=" aml.account_id  in %s " % str(
                tuple(account_ids)).replace(',)', ')')   
                           
        where_branch = " 1=1 "
        if branch_ids :
            where_branch = " aml.branch_id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')             
        else :
            area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids_user = [b.id for b in area_user]
            where_branch = " aml.branch_id in %s " % str(
                tuple(branch_ids_user))
            
        where_journal = " 1=1 "
        if journal_ids :
            where_account=" aml.journal_id  in %s " % str(
                tuple(journal_ids)).replace(',)', ')')   
            
        where_move_state = " 1=1 "
        if status == 'all' :
            where_move_state=" m.state is not Null "
        elif status == 'posted' :
            where_move_state=" m.state = 'posted' "  
             
        where_period = " 1=1 "                               
        if period_id :
            where_period = " aml.period_id = '%s' " % period_id[0]
        
        where_start_date = " 1=1 "
        where_end_date = " 1=1 "                               
        if start_date :
            where_start_date = " aml.date >= '%s' " % start_date
        if end_date :
            where_end_date = " aml.date <= '%s' " % end_date
        
        aml_segmen = ""
        select_segmen = ""
        left_join = ""
        group_by = ""
        if segmen:
            if segmen in [1,2,3,4]:
                aml_segmen += "al.analytic_1, "
                group_by += "al.analytic_1, "
                select_segmen += "anl1.name as analytic_1, anl1.code as analytic_1_code, "
                left_join += "LEFT JOIN account_analytic_account anl1 ON l.analytic_1 = anl1.id "
            if segmen in [2,3,4]:
                aml_segmen += "al.analytic_2, "
                group_by += "al.analytic_2, "
                select_segmen += "anl2.name as analytic_2, anl2.code as analytic_2_code, "
                left_join += "LEFT JOIN account_analytic_account anl2 ON l.analytic_2 = anl2.id "
            if segmen in [3,4]:
                aml_segmen += "al.analytic_3, "
                group_by += "al.analytic_3, "
                select_segmen += "anl3.name as analytic_3, anl3.code as analytic_3_code, "
                left_join += "LEFT JOIN account_analytic_account anl3 ON l.analytic_3 = anl3.id "
            if segmen == 4:
                aml_segmen += "al.account_id as analytic_account_id, "
                group_by += "al.account_id, "
                select_segmen += "anl4.name as analytic_account_id, anl4.code as analytic_account_id_code, "
                left_join += "LEFT JOIN account_analytic_account anl4 ON l.analytic_account_id = anl4.id "

        query_trial_balance = "SELECT ROW_NUMBER() OVER(ORDER BY l.branch_id,a.parent_left) as row, b.code as branch_code, a.code as account_code, '' as account_sap, a.name as account_name, "\
        "b.profit_centre as profit_centre, "+select_segmen+"  l.branch_id, l.account_id, l.debit as debit, l.credit as credit, l.debit - l.credit as balance , p.date_stop as date_stop "\
        "FROM account_account a INNER JOIN "\
        "(SELECT "+aml_segmen+"  aml.branch_id, aml.account_id, aml.period_id, SUM(aml.debit) as debit, SUM(aml.credit) as credit "\
        "FROM account_move_line aml LEFT JOIN account_analytic_line al ON al.move_id = aml.id "\
        "WHERE "+where_branch+" AND "+where_account+" AND "+where_period+" AND "+where_start_date+" AND "+where_end_date+" AND "+where_journal+" "\
        "GROUP BY "+group_by+" aml.branch_id, aml.account_id, aml.period_id) l "\
        "ON a.id = l.account_id "\
        "INNER JOIN dym_branch b ON l.branch_id = b.id "\
        "LEFT JOIN account_period p ON p.id = l.period_id "\
        "" + left_join + " "\
        "ORDER BY l.branch_id,a.parent_left "
        
        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        reports = [report_trial_balance_import_sun]
        for report in reports:
            cr.execute(query_trial_balance)
            all_lines = cr.dictfetchall()
                
            move_lines = []            
            if all_lines:

                p_map = map(
                    lambda x: {
                        'no':0,
                        'branch_code': x['branch_code'].encode('ascii','ignore').decode('ascii') if x['branch_code'] != None else '',   
                        'account_code': x['account_code'].encode('ascii','ignore').decode('ascii') if x['account_code'] != None else '', 
                        'account': x['account_sap'].split('-')[0].encode('ascii','ignore').decode('ascii') if x['account_sap'] != None and len(x['account_sap'].split('-')) > 0 else x['account_sap'].encode('ascii','ignore').decode('ascii') if x['account_sap'] != None else '', 
                        'profit_centre': x['profit_centre'].encode('ascii','ignore').decode('ascii') if x['profit_centre'] != None else '', 
                        'div': x['account_sap'].split('-')[1].encode('ascii','ignore').decode('ascii') if x['account_sap'] != None and len(x['account_sap'].split('-')) > 1 else '',
                        'dept': x['account_sap'].split('-')[2] if x['account_sap'] != None and len(x['account_sap'].split('-')) > 2 else '', 
                        'class': x['account_sap'].split('-')[3] if x['account_sap'] != None and len(x['account_sap'].split('-')) > 3 else '',
                        'type': x['account_sap'].split('-')[4] if x['account_sap'] != None and len(x['account_sap'].split('-')) > 4 else '',
                        'account_name': x['account_name'].encode('ascii','ignore').decode('ascii') if x['account_name'] != None else '', 
                        'transaction_amount': x['balance'],
                        'date_stop': x['date_stop'].encode('ascii','ignore').decode('ascii') if x['date_stop'] != None else '', 
                        'debit': x['debit'],
                        'credit': x['credit'],
                        'analytic_1': x['analytic_1_code'] + ' ' + x['analytic_1'] if segmen in [1,2,3,4] and x['analytic_1'] != None else '',
                        'analytic_2': x['analytic_2_code'] + ' ' + x['analytic_2'] if segmen in [2,3,4] and x['analytic_2'] != None else '',
                        'analytic_3': x['analytic_3_code'] + ' ' + x['analytic_3'] if segmen in [3,4] and x['analytic_3'] != None else '',
                        'analytic_4': x['analytic_account_id_code'] + ' ' + x['analytic_account_id'] if segmen == 4 and x['analytic_account_id'] != None else '',
                        'row': x['row'],
                        },
                            
                    all_lines)
                
                # for p in p_map:
                #     if p['row'] not in map(
                #             lambda x: x.get('row', None), move_lines):
                #         move_lines.append(p)
                #         account_move_lines = filter(
                #             lambda x: x['row'] == p['row'], all_lines)
                #         p.update({'lines': account_move_lines})
                #         analytic_id = account_move_lines[0]['analytic_account_id']
                #         analytic = self.pool.get('account.analytic.account').browse(cr, uid, analytic_id)
                #         analytic_1 = ''
                #         analytic_2 = ''
                #         analytic_3 = ''
                #         analytic_4 = ''
                #         if analytic:
                #             if analytic.type == 'normal':
                #                 if analytic.segmen == 1:
                #                     analytic_1 = analytic.code + ' ' + analytic.name
                #                 if analytic.segmen == 2:
                #                     analytic_2 = analytic.code + ' ' + analytic.name
                #                 if analytic.segmen == 3:
                #                     analytic_3 = analytic.code + ' ' + analytic.name
                #                 if analytic.segmen == 4:
                #                     analytic_4 = analytic.code + ' ' + analytic.name
                #             while (analytic.parent_id):
                #                 analytic = analytic.parent_id
                #                 if analytic.type == 'normal':
                #                     if analytic.segmen == 1:
                #                         analytic_1 = analytic.code + ' ' + analytic.name
                #                     if analytic.segmen == 2:
                #                         analytic_2 = analytic.code + ' ' + analytic.name
                #                     if analytic.segmen == 3:
                #                         analytic_3 = analytic.code + ' ' + analytic.name
                #                     if analytic.segmen == 4:
                #                         analytic_4 = analytic.code + ' ' + analytic.name
                #         p.update({'analytic_1': analytic_1})
                #         p.update({'analytic_2': analytic_2})
                #         p.update({'analytic_3': analytic_3})
                #         p.update({'analytic_4': analytic_4})
                # report.update({'move_lines': move_lines})
#                 for p in p_map:
#                     if p['branch_code'] not in map(
#                             lambda x: x.get('branch_code', None), move_lines):
#                         move_lines.append(p)
#                         account_move_lines = filter(
#                             lambda x: x['branch_code'] == p['branch_code'], all_lines)
#                         p.update({'lines': account_move_lines})
                report.update({'move_lines': p_map})


        reports = filter(lambda x: x.get('move_lines'), reports)
        if not reports:
            reports = [{
            'type': 'import_sun',
            'title': '',
            'period': date_stop,
            'title_short': title_short_prefix + ', ' + _('LAPORAN MUTASI PER CABANG')  ,
                        'move_lines':
                            [ {
                        'no':0,
                        'branch_code': 'NO DATA FOUND',
                        'account_code':'NO DATA FOUND',
                        'account': 'NO DATA FOUND',
                        'profit_centre': 'NO DATA FOUND',
                        'div': 'NO DATA FOUND',
                        'dept':'NO DATA FOUND',
                        'class': 'NO DATA FOUND',
                        'type': 'NO DATA FOUND',
                        'account_name': 'NO DATA FOUND',
                        'transaction_amount': 0,
                        'date_stop':'NO DATA FOUND',
                        'debit': 0.0,
                        'credit': 0.0,
                        'analytic_1': 'NO DATA FOUND',
                        'analytic_2': 'NO DATA FOUND',
                        'analytic_3': 'NO DATA FOUND',
                        'analytic_4': 'NO DATA FOUND',
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
        super(dym_trial_balance_import_sun_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_trial_balance_import_sun_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_account_move.report_trial_balance_import_sun'
    _inherit = 'report.abstract_report'
    _template = 'dym_account_move.report_trial_balance_import_sun'
    _wrapped_report_class = dym_trial_balance_import_sun_report_print
