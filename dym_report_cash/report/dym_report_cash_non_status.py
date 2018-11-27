
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


class dym_cash_non_status_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_cash_non_status_report_print, self).__init__(
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
        journal_ids = data['journal_ids']
        status = data['status']
        start_date = data['start_date']
        end_date = data['end_date']
        option = data['option']
        
        title_prefix = ''
        title_short_prefix = ''

        report_cash_non_status = {
            'type': 'Cash_non_status',
            'title': '',
            'title_short': _('laporan'),
            'start_date': start_date,
            'end_date': end_date,
            'option':option          
            }   
            
        where_option = " 1=1 "
        where_type = " 1=1 "
        if option == 'All Non Petty Cash' :
            where_option=" j.type in ('bank','cash','edc','situation') "
            where_type = " a.type = 'liquidity' "
        elif option == 'Cash' :
            where_option=" j.type in ('cash','situation') "
            where_type = " a.type = 'liquidity' "
        elif option == 'EDC' :
            where_option=" j.type in ('edc','situation') "   
            where_type = " a.type = 'receivable' "
        elif option == 'Bank' :
            where_option=" j.type in ('bank','situation') "   
            where_type = " a.type = 'liquidity' "  
        elif option == 'Petty Cash' :
            where_option=" j.type in ('pettycash','situation') "    
            where_type = " a.type = 'liquidity' "
             
        where_branch = " 1=1 "
        if branch_ids :
            where_branch = " b.id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')             
        else :
            area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids_user = [b.id for b in area_user]
            where_branch = " b.id in %s " % str(
                tuple(branch_ids_user))
            
        where_journal = " 1=1 "
        if journal_ids :
            where_journal=" j.id  in %s " % str(
                tuple(journal_ids)).replace(',)', ')')   
                          
        where_status = " 1=1 "
        if status == 'outstanding' :
            where_status=" aml.reconcile_id is Null "
        elif status == 'reconcile' :
            where_status=" aml.reconcile_id is not Null "   
                        
        where_start_date = " 1=1 "
        where_end_date = " 1=1 "                               
        if start_date :
            where_start_date = " aml.date >= '%s' " % start_date
        if end_date :
            where_end_date = " aml.date <= '%s' " % end_date         
        user = self.pool.get('res.users').browse(cr,uid,uid)
        timezone = user.tz or 'Asia/Jakarta'
        if timezone == 'Asia/Jayapura' :
            tz = '9'
        elif timezone == 'Asia/Pontianak' :
            tz = '8'
        else :
            tz = '7'
        query_cash_non_status = "SELECT aml.date as tanggal, b.code as branch_code, to_char(am.create_date + interval '"+tz+" hours', 'HH12:MI AM') as Jam, "\
        "k.name as kwitansi_name, a.code as account_code, aml.name as keterangan, aml.debit - aml.credit as balance, "\
        "j.type as journal_type, am.name as scr "\
        "FROM account_move_line aml "\
        "LEFT JOIN account_move am ON am.id = aml.move_id "\
        "LEFT JOIN account_journal j ON j.id = aml.journal_id "\
        "LEFT JOIN account_account a ON a.id = aml.account_id "\
        "LEFT JOIN dym_register_kwitansi_line k ON k.id = aml.kwitansi_id "\
        "LEFT JOIN dym_branch b ON b.id = aml.branch_id "\
        "WHERE "+where_branch+" AND "+where_type+" AND "+where_journal+" AND "+where_status+" AND "+where_start_date+" AND "+where_end_date+" AND "+where_option+" "\
        "ORDER BY b.code, aml.date "
        
        move_selection = ""
        report_info = _('')
        move_selection += ""
        reports = [report_cash_non_status]
        for report in reports:
            cr.execute(query_cash_non_status)
            all_lines = cr.dictfetchall()
            move_lines = []            
            if all_lines:

                p_map = map(
                    lambda x: {       
                        'no':0,                                      
                        'branch_code': x['branch_code'],    
                        'tanggal': x['tanggal'],    
                        'jam': x['jam'],    
                        'kwitansi_name': x['kwitansi_name'],    
                        'account_code': x['account_code'],  
                        'keterangan': x['keterangan'].encode('ascii','ignore').decode('ascii') if x['keterangan'] != None else '',    
                        'tunai': x['balance'] if x['journal_type'] == 'cash' else 0.0 ,
                        'bank_check' : x['balance'] if x['journal_type'] == 'bank' else 0.0 ,
                        'edc' : x['balance'] if x['journal_type'] == 'edc' else 0.0 ,
                        'total': x['balance'],
                        'move_name': x['scr'],    
                        },
                            
                    all_lines)

                report.update({'move_lines': p_map})


        reports = filter(lambda x: x.get('move_lines'), reports)
        if not reports:
            reports = [{'title_short': 'laporan', 'type': 'Cash_non_status','start_date': start_date,
                        'end_date': end_date,
                        'option':option ,
                        'move_lines':
                            [{       
                                'no':0,                                      
                                'branch_code': 'NO DATA FOUND',
                                'tanggal': 'NO DATA FOUND',
                                'jam': 'NO DATA FOUND',
                                'kwitansi_name': 'NO DATA FOUND',
                                'account_code':0,  
                                'keterangan': 'NO DATA FOUND',
                                'tunai': 0.0 ,
                                'bank_check' : 0.0 ,
                                'edc' : 0.0 ,
                                'total': 0.0,
                                'move_name': 'NO DATA FOUND',
                                }], 
                        
                        'title': ''}]
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        objects=False
        super(dym_cash_non_status_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_cash_non_status_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_cash.report_cash_non_status'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_cash.report_cash_non_status'
    _wrapped_report_class = dym_cash_non_status_report_print
