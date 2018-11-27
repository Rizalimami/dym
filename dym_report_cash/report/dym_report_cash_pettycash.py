
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


class dym_cash_pettycash_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_cash_pettycash_report_print, self).__init__(
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
        option = data['option']
        journal_id = data['journal_id']
        
        title_prefix = ''
        title_short_prefix = ''
        
        journal_pool = self.pool.get('account.journal').browse(cr,uid,journal_id[0]
                                                               )
        default_account = journal_pool.default_debit_account_id or journal_pool.default_credit_account_id
        default_account_code = default_account.code
        default_account_name = default_account.name
        default_account_sap = ''
                
        report_cash_pettycash = {
            'title': '',
            'title_short': _('laporan'),
            'start_date': start_date,
            'end_date': end_date,
            'option':option,
            'default_account_code': default_account_code,
            'default_account_name':default_account_name,
            'default_account_sap':default_account_sap         
            }      
             
        where_branch = " 1=1 "
        area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids_user = [b.id for b in area_user]
        where_branch = " b.id in %s " % str(
            tuple(branch_ids_user)).replace(',)', ')')
            
        where_journal = " 1=1 "
        if journal_id :
            where_journal=" aj.id  = %s " % journal_id[0]  
                                            
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

        query_cash_pettycash = "SELECT aml.date as date, am.state as state, am.name as move_line_name, p.name as partner_name, "\
        "aml.ref as keterangan, "\
        "aml.debit as debit, aml.credit as credit, res.name as user_name, to_char(aml.create_date + interval '"+tz+" hours', 'HH12:MI AM') as Jam "\
        "FROM account_move_line aml "\
        "LEFT JOIN account_move am ON am.id = aml.move_id "\
        "LEFT JOIN account_account a ON a.id = aml.account_id "\
        "LEFT JOIN account_journal aj ON aj.id = aml.journal_id "\
        "LEFT JOIN res_partner p ON p.id = aml.partner_id "\
        "LEFT JOIN dym_branch b ON b.id = aml.branch_id "\
        "LEFT JOIN res_users u ON u.id = aml.create_uid "\
        "LEFT JOIN res_partner res ON res.id = u.partner_id "\
        "WHERE a.type = 'liquidity' AND "+where_journal+" AND "+where_branch+" AND "+where_start_date+" AND "+where_end_date+" "\
        "ORDER BY aml.date,p.name"
        move_selection = ""
        report_info = _('')
        move_selection += ""
        reports = [report_cash_pettycash]
        mutasi_debit = 0
        mutasi_credit = 0
        saldo_akhir = 0
        saldo_awal_tanggal = default_account.with_context(date_from=start_date, date_to=start_date, initial_bal=True).balance
        tanggal_awal_bulan = datetime.strptime(start_date, '%Y-%m-%d').replace(day=1).strftime('%Y-%m-%d')
        saldo_awal_bulan = default_account.with_context(date_from=tanggal_awal_bulan, date_to=tanggal_awal_bulan, initial_bal=True).balance
        for report in reports:
            cr.execute(query_cash_pettycash)
            all_lines = cr.dictfetchall()
            move_lines = []            
            if all_lines:
                p_map = map(
                    lambda x: {       
                        'no':0,                                      
                        'tgl_konf': x['date'].encode('ascii','ignore').decode('ascii') if x['date'] != None else '',    
                        'state': x['state'].encode('ascii','ignore').decode('ascii') if x['state'] != None else '',    
                        'move_line_name': x['move_line_name'].encode('ascii','ignore').decode('ascii') if x['move_line_name'] != None else '',    
                        'partner_name': x['partner_name'].encode('ascii','ignore').decode('ascii') if x['partner_name'] != None else '',    
                        'keterangan': x['keterangan'].encode('ascii','ignore').decode('ascii') if x['keterangan'] != None else '',    
                        'debit': x['debit'],
                        'credit': x['credit'],
                        'saldo' : x['debit'] - x['credit'],
                        'user_name' : x['user_name'].encode('ascii','ignore').decode('ascii') if x['user_name'] != None else '',    
                        'jam' : x['jam'].encode('ascii','ignore').decode('ascii') if x['jam'] != None else '',    
                        },
                    all_lines)
                report.update({'move_lines': p_map})
                for p in p_map:
                    mutasi_debit += p['debit']
                    mutasi_credit += p['credit']
                    saldo_akhir += p['saldo']
        reports[0]['saldo_awal_bulan'] = saldo_awal_bulan
        reports[0]['mutasi_debit'] = mutasi_debit
        reports[0]['mutasi_credit'] = mutasi_credit

        reports[0]['saldo_akhir'] = saldo_akhir
        reports[0]['saldo_awal_tanggal'] = saldo_awal_tanggal
        reports = filter(lambda x: x.get('move_lines'), reports)
        if not reports:
            reports = [{            
            'title': '',
            'title_short': _('laporan'),
            'start_date': start_date,
            'end_date': end_date,
            'option':option,
            'default_account_code': default_account_code,
            'default_account_name':default_account_name,
            'default_account_sap':default_account_sap  ,
            'saldo_awal_bulan':saldo_awal_bulan  ,
            'mutasi_debit':mutasi_debit  ,
            'mutasi_credit':mutasi_credit  ,
            'saldo_akhir':saldo_akhir  ,
            'saldo_awal_tanggal':saldo_awal_tanggal  ,
            'move_lines':
                            [{       
                            'no':0,                                      
                            'tgl_konf': 'NO DATA FOUND',
                            'state': 'NO DATA FOUND',
                            'move_line_name': 'NO DATA FOUND',
                            'partner_name': 'NO DATA FOUND',
                            'keterangan': 'NO DATA FOUND',  
                            'debit': 0.0,
                            'credit': 0.0,
                            'saldo':0.0,
                            'user_name' : 'NO DATA FOUND' ,
                            'jam' : 'NO DATA FOUND',
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
        objects=False
        super(dym_cash_pettycash_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_cash_pettycash_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_cash.report_cash_pettycash'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_cash.report_cash_pettycash'
    _wrapped_report_class = dym_cash_pettycash_report_print
