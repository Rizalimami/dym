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

class AccountFilter(orm.Model):
    _inherit = "dym.account.filter"

    def _register_hook(self, cr):
        selection = self._columns['name'].selection
        if ('laba_rugi_berjalan','Account Laba-Rugi Periode Berjalan') not in selection:         
            self._columns['name'].selection.append(
                ('laba_rugi_berjalan', 'Account Laba-Rugi Periode Berjalan'))
        return super(AccountFilter, self)._register_hook(cr)    

class dym_trial_balance_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_trial_balance_report_print, self).__init__(
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
    
    def get_period(self,period_id,fiscalyear_id, period_to_id=False):
        cr = self.cr
        if period_to_id:
            # query_period = "SELECT id from account_period " \
            #     "WHERE id >= %s AND id <= %s "
            # cr.execute(query_period, (period_id,period_to_id ))
            #Replaced By Kahfi=========================================================
            period_from = self.pool.get('account.period').browse(cr,self.uid,period_id)
            period_to = self.pool.get('account.period').browse(cr,self.uid,period_to_id)
            query_period = "SELECT id from account_period " \
                "WHERE date_start >= %s AND date_stop <= %s AND company_id = %s"
            cr.execute(query_period, (period_from.date_start,period_to.date_stop,period_from.company_id.id ))
            #Replaced By Kahfi=========================================================
        elif period_id == False and fiscalyear_id and period_to_id == False:
            query_period = "SELECT id from account_period " \
                "WHERE fiscalyear_id = %s order by id asc "
            cr.execute(query_period, (fiscalyear_id,))
        else:
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
        branch_ids = data['branch_ids']
        branch_status = data['branch_status']
        account_ids = data['account_ids']
        period_id = data['period_id']
        status = data['status']
        segmen = data['segmen']
        start_date = data['start_date']
        end_date = data['end_date']
        konsolidasi = data['konsolidasi']
        option = data['option']
        period_to_id = data['period_to_id']
        fiscalyear_id = data['fiscalyear_id'][0]
        title_prefix = ''
        title_short_prefix = ''
        
        jenis_laporan = ''
        where_account_type = " 1=1 "
        if option == 'trial_balance':  
            jenis_laporan = 'Trial Balance'
        elif option == 'balance_sheet':
            jenis_laporan = 'Balance Sheet'
            where_account_type = " at.report_type in ('asset','liability','income','expense') "
        elif option == 'profit_loss':
            jenis_laporan = 'Profit & Loss'
            where_account_type = " at.report_type in ('income','expense') "


        where_account = " 1=1 "
        if account_ids :
            where_account=" a.id  in %s " % str(
                tuple(account_ids)).replace(',)', ')')              
        where_branch = " 1=1 "
        if branch_ids :
            branch_ids = branch_ids
            where_branch = " b.id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')             
        else :
            area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids_user = [b.id for b in area_user]
            branch_ids = branch_ids_user
            where_branch = " b.id in %s " % str(
                tuple(branch_ids_user))
        where_move_state = " 1=1 "
        if status == 'all' :
            where_move_state=" m.state is not Null "
        elif status == 'posted' :
            where_move_state=" m.state = 'posted' "   
        where_prev_period = " 1!=1 "
        where_period = " 1=1 "        
        if period_id :
            # fiscalyear_id = self.get_fiscalyear(period_id[0])
            prev_period_ids = self.get_period(period_id[0], fiscalyear_id)
            if prev_period_ids :
                where_prev_period =" l.period_id  in %s " % str(
                    tuple(prev_period_ids)).replace(',)', ')')
            else :
                where_prev_period = " 1!=1 "
                
            period_ids = self.get_period(period_id[0], fiscalyear_id, period_to_id=period_to_id[0])
            #Added By Kahfi ========================================================================
            period_list = []
            for p in period_ids:
                period = self.pool.get('account.period').browse(cr,self.uid,int(str(p).replace(',)','').replace('(','')))
                if not period.special:
                    period_list.append(p)
                else:
                    where_prev_period =" l.period_id  in %s " % str(
                    tuple(p)).replace(',)', ')')
            period_ids = period_list
            #Added By Kahfi ========================================================================
            where_period =" l.period_id  in %s " % str(
                tuple(period_ids)).replace(',)', ')')
        else:
            period_year_ids = self.get_period(False, fiscalyear_id, period_to_id=False)
            where_period = " l.period_id  in %s " % str(
                tuple(period_year_ids)).replace(',)', ')')
            prev_period_ids = self.get_period(period_year_ids[0][0], fiscalyear_id)
            if prev_period_ids :
                where_prev_period =" l.period_id  in %s " % str(
                    tuple(prev_period_ids)).replace(',)', ')')
            else :
                where_prev_period = " 1!=1 "

        where_prev_start_date = " 1!=1 "
        where_start_date = " 1=1 "
        where_end_date = " 1=1 "
        if start_date :
            where_prev_start_date = " l.date < '%s' " % start_date
            where_start_date = " l.date >= '%s' " % start_date
        if end_date :
            where_end_date = " l.date <= '%s' " % end_date
        # date_stop = self.pool.get('account.period').browse(cr,uid,period_to_id[0]).date_stop
        # date_stop = datetime.strptime(date_stop, '%Y-%m-%d').strftime('%d %B %Y')
        report_trial_balance = {
            'type': 'BukuBesar',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('LAPORAN BUKU BESAR'),
            'konsolidasi': konsolidasi,
            'jenis_laporan': jenis_laporan,
            # 'period': date_stop,
            'start_date': start_date,
            'end_date': end_date
            }  

        select_segmen = ""
        aml_segmen = ""
        select_segmen_2 = ""
        group_by = ""
        where_segmen = ""
        left_join = ""
        
        move_line = 'account_move_line'
        move = 'account_move'
        consol_1 = ''
        consol_2 = ''
        consol_3 = ',  SUM(l.debit) as mutasi_debit, SUM(l.credit) as mutasi_credit'
        if konsolidasi == True:
            move_line = 'account_move_line_consol'
            move = 'account_move_consol'
            consol_1 = ', COALESCE(line.elim_debit,0) as elim_debit, COALESCE(line.elim_credit,0) as elim_credit'
            consol_2 = ', COALESCE(aml2.elim_debit,0) as elim_debit, COALESCE(aml2.elim_credit,0) as elim_credit'
            consol_3 = ',  SUM(CASE WHEN l.elimination_move_line_id is not null THEN 0 ELSE l.debit END) as mutasi_debit, SUM(CASE WHEN l.elimination_move_line_id is not null THEN 0 ELSE l.credit END) as mutasi_credit, SUM(CASE WHEN l.elimination_move_line_id is not null THEN l.debit ELSE 0 END) as elim_debit, SUM(CASE WHEN l.elimination_move_line_id is not null THEN l.credit ELSE 0 END) as elim_credit'

        query_trial_balance = "SELECT ROW_NUMBER() OVER(ORDER BY a.parent_left) as row, line.analytic_account_id as analytic_account_id, at.report_type as report_type, at.name as account_type, a.code as account_code, a.name as account_name, '' as account_sap, COALESCE(line.saldo_awal_debit,0) as saldo_awal_debit, "\
            "COALESCE(line.saldo_awal_credit,0) as saldo_awal_credit, "\
            "COALESCE(line.mutasi_debit,0) as mutasi_debit, "\
            "COALESCE(line.mutasi_credit,0) as mutasi_credit, "\
            "saldo_awal_debit - saldo_awal_credit as saldo_awal, "\
            "saldo_awal_debit - saldo_awal_credit + mutasi_debit - mutasi_credit as saldo_akhir "+consol_1+" "\
            "FROM account_account a LEFT JOIN account_account_type at on at.id = a.user_type "\
            "LEFT JOIN "\
            "(SELECT COALESCE(aml1.analytic_account_id,aml2.analytic_account_id) as analytic_account_id, COALESCE(aml1.account_id,aml2.account_id) as account_id, "\
            "COALESCE(aml1.saldo_awal_debit,0) as saldo_awal_debit, "\
            "COALESCE(aml1.saldo_awal_credit,0) as saldo_awal_credit, "\
            "COALESCE(aml2.mutasi_debit,0) as mutasi_debit, "\
            "COALESCE(aml2.mutasi_credit,0) as mutasi_credit "+consol_2+" FROM "\
            "(SELECT l.analytic_account_id as analytic_account_id, l.account_id as account_id, SUM(l.debit) as saldo_awal_debit, SUM(l.credit) as saldo_awal_credit "\
            "FROM "+move_line+" l LEFT JOIN "+move+" m ON l.move_id = m.id WHERE "+where_move_state+" AND ("+where_prev_period+" OR ("+where_period+" AND "+where_prev_start_date+")) GROUP BY l.analytic_account_id, l.account_id) AS aml1 "\
            "FULL OUTER JOIN "\
            "(SELECT l.analytic_account_id as analytic_account_id, l.account_id as account_id "+consol_3+" "\
            "FROM "+move_line+" l LEFT JOIN "+move+" m ON l.move_id = m.id WHERE "+where_move_state+" AND "+where_period+" AND "+where_start_date+" AND "+where_end_date+" GROUP BY l.analytic_account_id, l.account_id) AS aml2 "\
            "ON aml1.account_id = aml2.account_id AND aml1.analytic_account_id = aml2.analytic_account_id) line ON line.account_id = a.id "\
            "WHERE a.type != 'view' AND a.type != 'consolidation' AND a.type != 'closed' AND line.analytic_account_id is not null "\
            "AND "+where_account+" AND "+where_account_type+"  "\
            "ORDER BY a.parent_left"

        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        reports = [report_trial_balance]
        
        for report in reports:
            a = cr.execute(query_trial_balance)
            all_lines = cr.dictfetchall()

            #print query_trial_balance
            
            move_lines = []            
            if all_lines:
                p_map = map(
                    lambda x: {
                        'no':0,
                        'saldo_awal_debit': x['saldo_awal_debit'] if x['saldo_awal_debit'] > 0 else 0.0,
                        'saldo_awal_credit': x['saldo_awal_credit'] if x['saldo_awal_credit'] > 0 else 0.0,
                        'account_code': x['account_code'].encode('ascii','ignore').decode('ascii') if x['account_code'] != None else '',
                        'account_name': x['account_name'].encode('ascii','ignore').decode('ascii') if x['account_name'] != None else '',
                        'account_type': x['account_type'].encode('ascii','ignore').decode('ascii') if x['account_type'] != None else '',
                        'report_type': x['report_type'].encode('ascii','ignore').decode('ascii') if x['report_type'] != None else '',
                        'mutasi_debit': x['mutasi_debit'],
                        'mutasi_credit': x['mutasi_credit'],
                        'elim_debit': 0 if konsolidasi == False else x['elim_debit'],
                        'elim_credit': 0 if konsolidasi == False else x['elim_credit'],
                        'debit_neraca': (x['saldo_awal_debit'] if x['saldo_awal_debit'] > 0 else 0.0) +  x['mutasi_debit'],
                        'credit_neraca': (x['saldo_awal_credit'] if x['saldo_awal_credit'] > 0 else 0.0) +  x['mutasi_credit'],
                        'net': ((x['saldo_awal_debit'] if x['saldo_awal_debit'] > 0 else 0.0) +  x['mutasi_debit']) - ((x['saldo_awal_credit'] if x['saldo_awal_credit'] > 0 else 0.0) +  x['mutasi_credit']),
                        'consol_debit': 0 if konsolidasi == False else (x['saldo_awal_debit'] if x['saldo_awal_debit'] > 0 else 0.0) +  x['mutasi_debit'] + x['elim_debit'],
                        'consol_credit': 0 if konsolidasi == False else (x['saldo_awal_credit'] if x['saldo_awal_credit'] > 0 else 0.0) +  x['mutasi_credit'] + x['elim_credit'],
                        'consol_net': 0 if konsolidasi == False else ((x['saldo_awal_debit'] if x['saldo_awal_debit'] > 0 else 0.0) +  x['mutasi_debit'] + x['elim_debit']) - ((x['saldo_awal_credit'] if x['saldo_awal_credit'] > 0 else 0.0) +  x['mutasi_credit'] + x['elim_credit']),
                        # 'debit_neraca': x['saldo_akhir'] if x['saldo_akhir'] > 0 else 0.0,
                        # 'credit_neraca': -1*x['saldo_akhir'] if x['saldo_akhir'] < 0 else 0.0,
                        'analytic_4': x['analytic_account_id'] if x['analytic_account_id'] != None else '',
                        'row': x['row'],
                        },
                            
                    all_lines)
                
                if option == 'balance_sheet':
                    account_filter_bs_pl_ids = self.pool.get('dym.account.filter').search(cr, uid, [('name','=','laba_rugi_berjalan')])
                    account_filter_bs_pl = self.pool.get('dym.account.filter').browse(cr, uid, account_filter_bs_pl_ids)
                    account_bs_pl_ids = self.pool.get('account.account').search(cr, uid, [('code','=',account_filter_bs_pl.prefix)])
                    account_bs_pl = self.pool.get('account.account').browse(cr, uid, account_bs_pl_ids)

                for p in p_map:
                    if p['row'] not in map(
                            lambda x: x.get('row', None), move_lines):
                        account_move_lines = filter(
                            lambda x: x['row'] == p['row'], all_lines)
                        if option == 'balance_sheet':
                            if account_move_lines[0]['report_type'] in ('income','expense'):
                                if not account_bs_pl:
                                    raise osv.except_osv(('Perhatian !'), ('Mohon tambahkan/perbaiki Account Laba-Rugi Periode Berjalan di master account filter!'))
                                else:
                                    p.update({'account_code': account_bs_pl[0].code})
                                    p.update({'account_name': account_bs_pl[0].name})
                                    p.update({'account_type': account_bs_pl[0].user_type.name})
                        analytic_1 = ''
                        analytic_2 = ''
                        analytic_3 = ''
                        analytic_4 = ''
                        analytic_1_name = ''
                        analytic_2_name = ''
                        analytic_3_name = ''
                        analytic_4_name = ''
                        uid = 1
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
                                    branch = analytic.branch_id
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
                                        branch = analytic.branch_id
                                        branch_name = branch.name
                                        branch_status_1 = branch.branch_status
                                        branch_id = branch.id
                                    if analytic.segmen == 4 and analytic_4 == '':
                                        analytic_4_name = analytic.name
                                        analytic_4 = analytic.code
                                        analytic_id == analytic
                            if (branch and branch_ids and branch.id not in branch_ids) or (branch and branch_status and branch_status != branch.branch_status):
                                continue

                            analytic_2_branch = analytic_2
                            #if analytic_2 in ['210','220','230']:
                                #if branch_status_1 == 'H123':
                                    #analytic_2_branch = analytic_2[:2] + '1'
                                #elif branch_status_1 == 'H23':
                                    #analytic_2_branch = analytic_2[:2] + '2'
                                #else:
                                    #analytic_2_branch = analytic_2

                            analytic_1_code = analytic_1
                            analytic_2_code = analytic_2_branch
                            analytic_3_code = analytic_3
                            analytic_4_code = analytic_4

                            account_code = account_move_lines[0]['account_code'].encode('ascii','ignore').decode('ascii') if account_move_lines[0]['account_code'] != None else ''
                            saldo_awal_debit = account_move_lines[0]['saldo_awal_debit'] if account_move_lines[0]['saldo_awal_debit'] > 0 else 0.0
                            saldo_awal_credit = account_move_lines[0]['saldo_awal_credit'] if account_move_lines[0]['saldo_awal_credit'] > 0 else 0.0
                            mutasi_debit = account_move_lines[0]['mutasi_debit']
                            mutasi_credit = account_move_lines[0]['mutasi_credit']
                            elim_debit = 0 if konsolidasi == False else account_move_lines[0]['elim_debit']
                            elim_credit = 0 if konsolidasi == False else account_move_lines[0]['elim_credit']
                            debit_neraca = (account_move_lines[0]['saldo_awal_debit'] if account_move_lines[0]['saldo_awal_debit'] > 0 else 0.0) + mutasi_debit
                            credit_neraca = (account_move_lines[0]['saldo_awal_credit'] if account_move_lines[0]['saldo_awal_credit'] > 0 else 0.0) + mutasi_credit
                            net = ((account_move_lines[0]['saldo_awal_debit'] if account_move_lines[0]['saldo_awal_debit'] > 0 else 0.0) + mutasi_debit) - ((account_move_lines[0]['saldo_awal_credit'] if account_move_lines[0]['saldo_awal_credit'] > 0 else 0.0) + mutasi_credit)
                            consol_debit = debit_neraca + elim_debit
                            consol_credit = credit_neraca + elim_credit
                            consol_net = consol_debit - consol_credit
                            index = 0
                            indexes = []
                            if not segmen:
                                for x in move_lines:
                                    if x['account_code'] == account_code and (not branch_status or x['branch_status'] == branch_status) and (not branch_ids or x['branch_id'] in branch_ids) and (not branch_id or x['branch_id'] == branch_id):
                                        p.update({'saldo_awal_debit': saldo_awal_debit + x['saldo_awal_debit']})
                                        p.update({'saldo_awal_credit': saldo_awal_credit + x['saldo_awal_credit']})
                                        p.update({'mutasi_debit': mutasi_debit + x['mutasi_debit']})
                                        p.update({'mutasi_credit': mutasi_credit + x['mutasi_credit']})
                                        p.update({'elim_debit': elim_debit + x['elim_debit']})
                                        p.update({'elim_credit': elim_credit + x['elim_credit']})
                                        p.update({'consol_debit': consol_debit + x['consol_debit']})
                                        p.update({'consol_credit': consol_credit + x['consol_credit']})
                                        p.update({'debit_neraca': debit_neraca + x['debit_neraca']})
                                        p.update({'credit_neraca': credit_neraca + x['credit_neraca']})
                                        p.update({'net': net + x['net']})
                                        p.update({'consol_net': net + x['consol_net']})
                                        indexes.append(index)
                                    index += 1
                                analytic_1_name = ''
                                analytic_2_name = ''
                                analytic_3_name = ''
                                analytic_4_name = ''
                                analytic_1_code = ''
                                analytic_2_code = ''
                                analytic_3_code = ''
                                analytic_4_code = ''
                                analytic_combination = ''
                            if segmen == 1:
                                for x in move_lines:
                                    if x['analytic_1'] == analytic_1 and x['account_code'] == account_code and (not branch_status or x['branch_status'] == branch_status) and (not branch_ids or x['branch_id'] in branch_ids) and (not branch_id or x['branch_id'] == branch_id):
                                        p.update({'saldo_awal_debit': saldo_awal_debit + x['saldo_awal_debit']})
                                        p.update({'saldo_awal_credit': saldo_awal_credit + x['saldo_awal_credit']})
                                        p.update({'mutasi_debit': mutasi_debit + x['mutasi_debit']})
                                        p.update({'mutasi_credit': mutasi_credit + x['mutasi_credit']})
                                        p.update({'elim_debit': elim_debit + x['elim_debit']})
                                        p.update({'elim_credit': elim_credit + x['elim_credit']})
                                        p.update({'consol_debit': consol_debit + x['consol_debit']})
                                        p.update({'consol_credit': consol_credit + x['consol_credit']})
                                        p.update({'debit_neraca': debit_neraca + x['debit_neraca']})
                                        p.update({'credit_neraca': credit_neraca + x['credit_neraca']})
                                        p.update({'net': net + x['net']})
                                        p.update({'consol_net': net + x['consol_net']})
                                        indexes.append(index)
                                    index += 1
                                analytic_2_name = ''
                                analytic_3_name = ''
                                analytic_4_name = ''
                                analytic_2_code = ''
                                analytic_3_code = ''
                                analytic_4_code = ''
                                analytic_combination = analytic_1
                            if segmen == 2:
                                for x in move_lines:
                                    if x['analytic_1'] == analytic_1 and x['analytic_2'] == analytic_2_branch and x['account_code'] == account_code and (not branch_status or x['branch_status'] == branch_status) and (not branch_ids or x['branch_id'] in branch_ids) and (not branch_id or x['branch_id'] == branch_id):
                                        p.update({'saldo_awal_debit': saldo_awal_debit + x['saldo_awal_debit']})
                                        p.update({'saldo_awal_credit': saldo_awal_credit + x['saldo_awal_credit']})
                                        p.update({'mutasi_debit': mutasi_debit + x['mutasi_debit']})
                                        p.update({'mutasi_credit': mutasi_credit + x['mutasi_credit']})
                                        p.update({'elim_debit': elim_debit + x['elim_debit']})
                                        p.update({'elim_credit': elim_credit + x['elim_credit']})
                                        p.update({'consol_debit': consol_debit + x['consol_debit']})
                                        p.update({'consol_credit': consol_credit + x['consol_credit']})
                                        p.update({'debit_neraca': debit_neraca + x['debit_neraca']})
                                        p.update({'credit_neraca': credit_neraca + x['credit_neraca']})
                                        p.update({'net': net + x['net']})
                                        p.update({'consol_net': net + x['consol_net']})
                                        indexes.append(index)
                                    index += 1
                                analytic_3_name = ''
                                analytic_4_name = ''
                                analytic_3_code = ''
                                analytic_4_code = ''
                                analytic_combination = analytic_1 + '/' + analytic_2_branch
                            if segmen == 3:
                                for x in move_lines:
                                    if x['analytic_1'] == analytic_1 and x['analytic_2'] == analytic_2_branch and x['analytic_3'] == analytic_3 and x['account_code'] == account_code and (not branch_status or x['branch_status'] == branch_status) and (not branch_ids or x['branch_id'] in branch_ids) and (not branch_id or x['branch_id'] == branch_id):
                                        p.update({'saldo_awal_debit': saldo_awal_debit + x['saldo_awal_debit']})
                                        p.update({'saldo_awal_credit': saldo_awal_credit + x['saldo_awal_credit']})
                                        p.update({'mutasi_debit': mutasi_debit + x['mutasi_debit']})
                                        p.update({'mutasi_credit': mutasi_credit + x['mutasi_credit']})
                                        p.update({'elim_debit': elim_debit + x['elim_debit']})
                                        p.update({'elim_credit': elim_credit + x['elim_credit']})
                                        p.update({'consol_debit': consol_debit + x['consol_debit']})
                                        p.update({'consol_credit': consol_credit + x['consol_credit']})
                                        p.update({'debit_neraca': debit_neraca + x['debit_neraca']})
                                        p.update({'credit_neraca': credit_neraca + x['credit_neraca']})
                                        p.update({'net': net + x['net']})
                                        p.update({'consol_net': net + x['consol_net']})
                                        indexes.append(index)
                                    index += 1
                                analytic_4_name = ''
                                analytic_4_code = ''
                                analytic_combination = analytic_1 + '/' + analytic_2_branch + '/' + analytic_3
                            if segmen == 4:
                                for x in move_lines:
                                    if x['analytic_1'] == analytic_1 and x['analytic_2'] == analytic_2_branch and x['analytic_3'] == analytic_3 and x['analytic_4'] == analytic_4 and x['account_code'] == account_code and (not branch_status or x['branch_status'] == branch_status) and (not branch_ids or x['branch_id'] in branch_ids) and (not branch_id or x['branch_id'] == branch_id):
                                        p.update({'saldo_awal_debit': saldo_awal_debit + x['saldo_awal_debit']})
                                        p.update({'saldo_awal_credit': saldo_awal_credit + x['saldo_awal_credit']})
                                        p.update({'mutasi_debit': mutasi_debit + x['mutasi_debit']})
                                        p.update({'mutasi_credit': mutasi_credit + x['mutasi_credit']})
                                        p.update({'elim_debit': elim_debit + x['elim_debit']})
                                        p.update({'elim_credit': elim_credit + x['elim_credit']})
                                        p.update({'consol_debit': consol_debit + x['consol_debit']})
                                        p.update({'consol_credit': consol_credit + x['consol_credit']})
                                        p.update({'debit_neraca': debit_neraca + x['debit_neraca']})
                                        p.update({'credit_neraca': credit_neraca + x['credit_neraca']})
                                        p.update({'net': net + x['net']})
                                        p.update({'consol_net': net + x['consol_net']})
                                        indexes.append(index)
                                    index += 1
                                analytic_combination = analytic_1 + '/' + analytic_2_branch + '/' + analytic_3 + '/' + analytic_4
                            min_i = 0
                            for i in indexes:
                                del move_lines[i - min_i]
                                min_i += 1
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
                        # else:
                        #     analytic_4 = ''
                        #     p.update({'lines': account_move_lines})
                        #     p.update({'analytic_1': analytic_1})
                        #     p.update({'analytic_2': analytic_2})
                        #     p.update({'analytic_3': analytic_3})
                        #     p.update({'analytic_4': analytic_4})
                        #     move_lines.append(p)
                report.update({'move_lines': move_lines})

#                 for p in p_map:
#                     if p['branch_name'] not in map(
#                             lambda x: x.get('branch_name', None), move_lines):
#                         move_lines.append(p)
#                         account_move_lines = filter(
#                             lambda x: x['branch_name'] == p['branch_name'], all_lines)
#                         p.update({'lines': account_move_lines})
                # report.update({'move_lines': p_map})

        reports = filter(lambda x: x.get('move_lines'), reports)

        if not reports:
            reports = [{
            'type': 'BukuBesar',
            'title': '',
            # 'period': date_stop ,
            'konsolidasi': konsolidasi,
            'jenis_laporan': jenis_laporan,
            'title_short': title_short_prefix + ', ' + _('LAPORAN BUKU BESAR')   ,
                        'move_lines':
                            [{
                        'no':0,
                        'branch_status': 'NO DATA FOUND',
                        'branch_name': 'NO DATA FOUND',
                        'saldo_awal_debit': 0.0,
                        'saldo_awal_credit':  0.0,
                        'account_code': 'NO DATA FOUND',
                        'account_type': 'NO DATA FOUND',
                        'account_sap':'NO DATA FOUND',
                        'account_name': 'NO DATA FOUND',
                        'mutasi_debit': 0,
                        'mutasi_credit': 0,
                        'elim_debit': 0,
                        'elim_credit': 0,
                        'consol_debit': 0,
                        'consol_credit': 0,
                        'consol_net': 0,
                        'debit_neraca':  0.0,
                        'credit_neraca': 0.0,
                        'analytic_1': 'NO DATA FOUND',
                        'analytic_2': 'NO DATA FOUND',
                        'analytic_3': 'NO DATA FOUND',
                        'analytic_4': 'NO DATA FOUND',
                        'analytic_combination': 'NO DATA FOUND',
                        'net': 0.0,
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
        super(dym_trial_balance_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_trial_balance_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_account_move.report_trial_balance'
    _inherit = 'report.abstract_report'
    _template = 'dym_account_move.report_trial_balance'
    _wrapped_report_class = dym_trial_balance_report_print
