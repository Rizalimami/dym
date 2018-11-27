import time
from datetime import datetime, timedelta
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT as DSDF
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging

_logger = logging.getLogger(__name__)



class dym_kas_besar_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_kas_besar_report_print, self).__init__(
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
        branch_id = data['branch_id']
        start_date = data['start_date']
        end_date = data['end_date']
        title_prefix = ''
        title_short_prefix = ''
        
        bank_balance = 0.0
        where_analytic = " 1=1 "
        if branch_id:
            branch_ids = self.pool.get('dym.branch').browse(cr,uid,branch_id[0]).ids
        else:
            branch_ids = self.pool.get('res.users').browse(cr,uid,uid).branch_ids.ids
        where_account = " 1=1 "

        if journal_id:
            journals = self.pool.get('account.journal').browse(cr,uid,journal_id[0])
            account_ids = []
            sql_query = ''
            if branch_ids:
                analytic_branch_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',3),('branch_id','in',branch_ids),('type','=','normal'),('state','not in',('close','cancelled'))])
                analytic_cc_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',4),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',analytic_branch_ids)])
                where_analytic =" l.analytic_account_id  in %s " % str(
                    tuple(analytic_cc_ids)).replace(',)', ')')
                sql_query = ' AND l.analytic_account_id in %s' % str(tuple(analytic_cc_ids)).replace(',)', ')')
            for journal in journals:
                if journal.default_debit_account_id and journal.default_debit_account_id.id not in account_ids:
                    account_ids.append(journal.default_debit_account_id.id)
                if journal.default_credit_account_id and journal.default_credit_account_id.id not in account_ids:
                    account_ids.append(journal.default_credit_account_id.id)
            
            bal_cr_init = journal.default_credit_account_id.with_context(
                date_from=start_date, 
                date_to=end_date, 
                initial_bal=True,
                sql_query=sql_query
            ).balance
            bal_db_init = journal.default_debit_account_id.with_context(
                date_from=start_date, 
                date_to=end_date, 
                initial_bal=True,
                sql_query=sql_query
            ).balance
            bank_balance_init = bal_cr_init or bal_db_init

            where_account=" a.id  in %s " % str(
                tuple(account_ids)).replace(',)', ')')  

        title_short = 'LAPORAN Kas Besar'
       #if data['projection']:
       #     title_short = title_short + ' (PROYEKSI)'
        report_kas_besar = {
            'type': 'KasBesar',
            'title': '',
            'title_short': title_short_prefix + ', ' + _(title_short),
            #'saldo_awal': saldo_awal,
            #'saldo_awal_projection': saldo_awal_projection,
            'start_date': start_date,
            'end_date': end_date
        }  

        where_start_date = " l.date >= '%s' " % start_date
        where_end_date = " l.date <= '%s' " % end_date
        where_start_datex = " '%s' " % start_date 
        where_end_datex = " '%s' " % end_date

        days = {
            'Sun':'Minggu',
            'Mon':'Senin',
            'Tue':'Selasa',
            'Wed':'Rabu',
            'Thu':'Kamis',
            'Fri':'Jumat',
            'Sat':'Sabtu'
            }

        query_kas_besar = """
            select x.day"date",sum(x.debit) debit,sum(x.credit) credit from (
                select day::date,0 debit,0 credit from generate_series(timestamp %s, %s, '1 day') day
                union all
                select date,sum(debit) debit,sum(credit) from account_move_line l
                left join account_account a on a.id = l.account_id 
                WHERE %s and %s and %s and %s 
                GROUP BY l.date) x GROUP BY x.day ORDER BY 1""" % ( where_start_datex, where_end_datex,where_account, where_start_date, where_end_date, where_analytic)

        #print query_kas_besar

        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        reports = [report_kas_besar]
        
        for report in reports:
            a = cr.execute(query_kas_besar)
            all_lines = cr.dictfetchall()
            
            move_lines = []            
            if all_lines:
                p_map = map(
                    lambda x: {
                        'no':0,
                        'hari': '',
                        'date': x['date'] if x['date'] != None else '', 
                        'debit': x['debit'] if x['debit'] > 0 else 0.0,
                        'credit': x['credit'] if x['credit'] > 0 else 0.0,
                        'saldo_awal': 0.0,
                        'saldo_akhir': 0.0,
                        'lebih_setor': 0.0,
                        'kurang_setor': 0.0,
                    },
                    all_lines)
                
                for p in p_map:
                    if p['date'] not in map(
                            lambda x: x.get('date', None), move_lines):
                        account_move_lines = filter(
                            lambda x: x['date'] == p['date'], all_lines)

                        bal_cr_init = journal.default_credit_account_id.with_context(
                            date_from=p['date'], 
                            date_to=p['date'], 
                            initial_bal=True,
                            sql_query=sql_query
                        ).balance
                        bal_db_init = journal.default_debit_account_id.with_context(
                            date_from=p['date'], 
                            date_to=p['date'], 
                            initial_bal=True,
                            sql_query=sql_query
                        ).balance
                        bank_balance_init = bal_cr_init or bal_db_init

                        bal_cr_init = journal.default_credit_account_id.with_context(
                            date_from=datetime.strptime(p['date'], DSDF).replace(day=1).strftime(DSDF), 
                            date_to=datetime.strptime(p['date'], '%Y-%m-%d') - timedelta(days=1),
                            initial_bal=False,
                            sql_query=sql_query
                        ).balance
                        bal_db_init = journal.default_debit_account_id.with_context(
                            date_from=datetime.strptime(p['date'], DSDF).replace(day=1).strftime(DSDF), 
                            date_to=datetime.strptime(p['date'], '%Y-%m-%d') - timedelta(days=1),
                            initial_bal=False,
                            sql_query=sql_query
                        ).balance
                        saldo_awal= bank_balance_init + (bal_cr_init - bal_db_init)
                        saldo_akhir= saldo_awal + p['debit'] - p['credit']
     
                        if p['debit'] > saldo_akhir:
                            lebih_setor = p['debit'] - saldo_akhir
                        else:
                            lebih_setor = 0

                        if p['debit'] < saldo_akhir:
                            kurang_setor = saldo_akhir -p['debit'] 
                        else:
                            kurang_setor = 0

                        date_a =  datetime.strptime(p['date'], '%Y-%m-%d')
                        hari =days[date_a.strftime('%a')]  
                        p.update({'hari': hari})
                        p.update({'date': datetime.strptime(str(p['date']),'%Y-%m-%d').strftime('%m/%d/%Y')})
                        p.update({'saldo_awal': saldo_awal})
                        p.update({'lebih_setor': lebih_setor})
                        p.update({'kurang_setor': kurang_setor})
                        p.update({'saldo_akhir': saldo_akhir})

                        move_lines.append(p)
                report.update({'move_lines': move_lines})

        reports = filter(lambda x: x.get('move_lines'), reports)

        if not reports:
            reports = [{
                'type': 'KasBesar',
                'title': '',
                #'title_short': title_short_prefix + ', ' + _(' '.join(['LAPORAN Kas Besar','(PROYEKSI)' if data['projection'] else ''])),
                'saldo_awal': saldo_awal,
                'start_date': start_date,
                'end_date': end_date,
                'hari':hari,
                'move_lines': [{
                    'no':0,
                    'debit': 0,
                    'credit': 0,
                    'lebih_setor': 0,
                    'kurang_setor': 0,

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
        super(dym_kas_besar_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_kas_besar_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_account_move.report_kas_besar'
    _inherit = 'report.abstract_report'
    _template = 'dym_account_move.report_kas_besar'
    _wrapped_report_class = dym_kas_besar_report_print
