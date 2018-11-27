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



class dym_bank_book_new_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_bank_book_new_report_print, self).__init__(
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
        # query_period = "SELECT id from account_period " \
        #     "WHERE id < %s AND fiscalyear_id = %s "
        # Replaced by Kahfi ================================
        query_period = "SELECT id from account_period " \
            "WHERE id < %s AND fiscalyear_id = %s AND special = False"
        # Replaced by Kahfi ================================
            
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
        # start_date = data['start_date']
        # end_date = data['end_date']
        start_value_date = data['start_value_date']
        end_value_date = data['end_value_date']
        title_prefix = ''
        title_short_prefix = ''
        
        saldo_awal_projection = 0.0
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
                analytic = str(
                    tuple(analytic_cc_ids)).replace(',)', ')')
                sql_query = ' and l.period_id in (select id from  account_period where special= FALSE) AND l.analytic_account_id in %s' % str(tuple(analytic_cc_ids)).replace(',)', ')')


            for journal in journals:
                if journal.default_debit_account_id and journal.default_debit_account_id.id not in account_ids:
                    account_ids.append(journal.default_debit_account_id.id)
                if journal.default_credit_account_id and journal.default_credit_account_id.id not in account_ids:
                    account_ids.append(journal.default_credit_account_id.id)




            bal_cr_init = journal.default_credit_account_id.with_context(
                date_from=start_value_date,
                date_to=start_value_date,
                initial_bal=True,
                sql_query=sql_query
            ).balance

            bal_db_init = journal.default_debit_account_id.with_context(
                date_from=start_value_date,
                date_to=start_value_date,
                initial_bal=True,
                sql_query=sql_query
            ).balance
            bank_balance_init = bal_cr_init or bal_db_init





            if data['projection']:
                sql_query_projection1 = """
                    SELECT 
                        sum(l.debit) as debit,
                        sum(l.credit) as credit
                    FROM 
                        account_move_line l
                        LEFT JOIN account_period ap on ap.id = l.period_id
                    WHERE 
                        l.clear_state in ('open') AND 
                        l.date < '%s' AND
                        %s AND 
                        ap.special = False
                """ % (start_value_date, where_analytic)

                where_account=" l.account_id  in %s " % str(
                    tuple(account_ids)).replace(',)', ')')
                account =str(
                    tuple(account_ids)).replace(',)', ')')
                where_start_date = " l.date >= '%s' " % start_value_date
                where_end_date = " l.date <= '%s' " % end_value_date

                sql_query_projection = """
                SELECT 
                l.id, 
                l.analytic_account_id, 
                case when avl.name is not  null then avl.name else case when  bt.description is not null then bt.description else av.name end  end  "name" , 
                l.ref, 
                dcl.name cheque_giro_number,
                p.name as partner_name, 
                coalesce(ac.name,a.name) as account_name2,
                coalesce(ac.code,a.code) as account_code2, 
                '' as btr_type,
                '' as source_of_fund,
                l.account_id, 
                l.date, 
                l.debit, 
                l.credit,
                bt.state,
                fc.name as finance_company, 
                fc2.name as finance_company2, 
                at.value_date as at_value_date, 
                cg.value_date as cg_value_date, 
                av.value_date as av_value_date, 
                bt.value_date as bt_value_date, 
                avp.date as avp_value_date,
                bta.name as bta_name,
                bta.amount as amount,
                bta.transfer_date as trf_date 
                FROM account_move_line l 
                LEFT JOIN account_move m on m.id = l.move_id 
                LEFT JOIN account_account a on a.id = l.account_id 
                LEFT JOIN res_partner p on p.id = l.partner_id 
                LEFT JOIN account_invoice inv on m.id = inv.move_id 
                LEFT JOIN dealer_sale_order dso on dso.name = inv.name 
                LEFT JOIN res_partner fc on fc.id = dso.finco_id 
                LEFT JOIN dym_alokasi_titipan at on at.name = m.name 
                LEFT JOIN dym_clearing_giro cg on cg.name = m.name 
                LEFT JOIN account_voucher av on av.number = m.name and av.type in ('purchase','payment') and av.state not in ('posted','draft','cancel')
                LEFT JOIN dym_bank_transfer bt on bt.name = m.name and bt.state not in ('approved','draft','cancel')
                LEFT JOIN dym_advance_payment avp on avp.name = m.name 
                LEFT JOIN account_voucher_line avl on av.id = avl.voucher_id and avl.type = 'cr'
                LEFT JOIN account_account ac on ac.id = avl.account_id 
                LEFT JOIN account_move_line l2 on l2.id = avl.move_line_id 
                LEFT JOIN account_invoice inv2 on inv2.move_id = l2.move_id 
                LEFT JOIN dealer_sale_order dso2 on dso2.name = inv2.name 
                LEFT JOIN res_partner fc2 on fc2.id = dso2.finco_id 
                LEFT JOIN dym_checkgyro_line dcl on av.cheque_giro_number = dcl.id
                LEFT JOIN bank_trf_advice bta on bta.name=bt.name and bta.state in ('done')
                LEFT JOIN account_period ap on ap.id = l.period_id 
                WHERE %s and %s and %s and %s and ap.special = False
                ORDER BY bt.state


                """ % (where_account, where_start_date, where_end_date, where_analytic) 


                cr.execute(sql_query_projection)
                res_dict = cr.dictfetchall()
                init_debit = 0.0
                init_credit = 0.0
                for det in res_dict:
                    debit, credit = det['debit'], det['credit']
                    init_debit = debit and float(debit) or 0.0
                    init_credit = credit and float(credit) or 0.0
                saldo_awal_projection = init_debit - init_credit

                # Blance On Range Dates
                sql_query_projection2 = """
                    SELECT 
                        sum(l.debit) as debit,
                        sum(l.credit) as credit
                    FROM 
                        account_move_line l
                    LEFT JOIN account_period ap on ap.id = l.period_id       
                    WHERE 
                        l.clear_state in ('open') AND 
                        l.date >= '%s' AND
                        l.date <= '%s' AND
                        %s AND 
                        ap.special = False
                """ % (start_value_date, end_value_date, where_analytic)
                cr.execute(sql_query_projection)
                res_dict = cr.dictfetchall()

                period_debit = 0.0
                period_credit = 0.0
                for det in res_dict:s
                    #debit, credit = det['debit'], det['credit']
                    #period_debit = debit and float(debit) or 0.0
                   #period_credit = credit and float(credit) or 0.0
                #mutasi_projection = period_debit - period_credit

            day_start = datetime.strptime(start_value_date, DSDF).day            
            if day_start==1:
                saldo_awal = bank_balance_init

                #print 'sa', bank_balance_init
            else:
                bal_cr_init = journal.default_credit_account_id.with_context(
                    date_from=datetime.strptime(start_value_date, DSDF).replace(day=1).strftime(DSDF), 
                    date_to=datetime.strptime(start_value_date, '%Y-%m-%d') - timedelta(days=1),
                    initial_bal=False,
                    sql_query=sql_query
                ).balance
                bal_db_init = journal.default_debit_account_id.with_context(
                    date_from=datetime.strptime(start_value_date, DSDF).replace(day=1).strftime(DSDF), 
                    date_to=datetime.strptime(start_value_date, '%Y-%m-%d') - timedelta(days=1),
                    initial_bal=False,
                    sql_query=sql_query
                ).balance
                saldo_awal = bank_balance_init + (bal_cr_init - bal_db_init)


            where_account=" a.id  in %s " % str(
                tuple(account_ids)).replace(',)', ')')
            accounts = str(
                tuple(account_ids)).replace(',)', ')')

        title_short = 'LAPORAN BANK BOOK NEW'
        if data['projection']:
            title_short = title_short + ' (PROYEKSI)'
        report_bank_book_new = {
            'type': 'BankBook',
            'title': '',
            'title_short': title_short_prefix + ', ' + _(title_short),
            'saldo_awal': saldo_awal,
            'saldo_awal_projection': saldo_awal_projection,
            'start_date': start_value_date,
            'end_date': end_value_date
        }   

        where_start_date = " l.date >= '%s' " % start_value_date
        where_end_date = " l.date <= '%s' " % end_value_date
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

        query_bank_book_new = """
            with recursive dym_bankbook as (
                select ll.*
                     from (
                    select m.id,l.analytic_account_id,m.name,l.ref,l.account_id,l.date,l.debit,l.credit,l.period_id ,
                    av.number as av_number,av.name as av_name,av.reference as av_reference,bt.id as bt_id,bt.description as bt_description,
                    avl_bt.name as avl_bt_name,btr_aj.name as btr_aj_name,avl.move_line_id,avl.name as avl_name,dpl.name as dpl_name,dpil.name as dpil_name,
                    dl.memo,av_par.name as av_par_name,inv2.number as inv2_number,tb_branch.name as tb_branch_name,btr_p.name as btr_p_name,p.name as p_name,
                    dp2.name as dp2_name,av.reference,tb_branch.code as tb_branch_code,btr_p.default_code as btr_p_default_code,pic.name as pic_name,
                    p.default_code as p_default_code,dso2.is_pic as dso2_is_pic,ac.name as ac_name,ac3.name as ac3_name,btr.ac_name as btr_ac_name,
                    ac2.name as ac2_name,loan_spa.ac_name as loan_spa_ac_name,a.name as a_name,ac.code as ac_code,ac3.code as ac3_code,btr.code as btr_ac_code,
                    ac2.code as ac2_code,loan_spa.ac_code as loan_spa_ac_code,a.code as a_code,bt.transaction_type,btr_ats.name as btr_ats_name,
                    dpl.amount as dpl_amount,dso2.is_credit,fc2.name as fc2_name,bt.state as bt_state 
                    FROM account_move_line l
                    inner join account_move m on m.id = l.move_id
                    left join (select a.id,account_id  from account_move a,account_move_line b where a.id = b.move_id and b.debit >0 and b.date >= '"""+ str(start_value_date) + """'  and  b.date <= '"""+ str(end_value_date) + """' ) aml2 on aml2.id  = m.reverse_from_id
                    left join (select a.id,account_id  from account_move a,account_move_line b where a.id = b.move_id and b.credit >0 and b.date >= '"""+ str(start_value_date) + """'  and  b.date <= '"""+ str(end_value_date) + """') aml3 on aml3.id  = m.reverse_from_id
                    left join account_account ac2 on aml2.account_id = ac2.id
                    left join account_account ac3 on aml3.account_id = ac3.id
                    inner join account_account a on a.id = l.account_id
                    left join res_partner p on p.id = l.partner_id
                    left join account_invoice inv on m.id = inv.move_id
                    left join dealer_sale_order dso on dso.name = inv.name
                    left join res_partner fc on fc.id = dso.finco_id
                    left join account_voucher av on av.number = m.name
                    left join account_voucher_line avl_bt on avl_bt.voucher_id = av.id
                    left join dym_branch tb_branch on tb_branch.id = av.branch_id
                    left join dym_bank_transfer bt on bt.name = m.name
                    left join dym_bank_transfer_line btl on btl.bank_transfer_id = bt.id
                    left join account_period ap on ap.id = l.period_id
                    left join res_partner btr_p on btr_p.default_code = btl.branch_destination_id
                    left join account_journal btr_aj on btr_aj.id = btl.payment_to_id
                    left join account_journal btr_ats on btr_ats.id = bt.payment_from_id_ats
                    left join account_voucher_line avl on av.id = avl.voucher_id and avl.type = 'cr'
                    left join account_account ac on ac.id = avl.account_id
                    left join account_move_line l2 on l2.id = avl.move_line_id
                    left join account_invoice inv2 on inv2.move_id = l2.move_id
                    left join dealer_sale_order dso2 on dso2.name = inv2.name
                    left join dym_cabang_partner pic on pic.id = dso2.partner_cabang
                    left join res_partner fc2 on fc2.id = dso2.finco_id
                    left join dym_pettycash dp on m.name = dp.name
                    left join dym_pettycash_line dpl on dp.id = dpl.pettycash_id 
                    left join dym_pettycash_in dpi on m.name = dpi.name
                    left join dym_pettycash_in_line dpil on dpi.id = dpil.pettycash_id
                    left join dym_pettycash dp2 on dp2.id = dpi.pettycash_id 
                    left join dym_loan dl on l.ref = dl.name
                    left join (select ac.code as ac_code, ac.id as id, ac.name as ac_name, am.name as name, am.id as am_id, am.ref as ref from account_move_line aml 
                        inner join account_move am on aml.move_id = am.id
                        inner join account_account ac on aml.account_id = ac.id 
                        where left(am.name,3) = 'SPA' and ac.code in ('2101002') and aml.debit > 1000  and  aml.date >= '"""+ str(start_value_date) + """' and  aml.date <='"""+ str(end_value_date) + """') loan_spa 
                        on loan_spa.ref = dl.name
                    left join (select av_giro.number,string_agg(distinct(aml.name),', ') as name from account_voucher av_giro 
                        inner join account_voucher_line av_giro_line on av_giro.id = av_giro_line.voucher_id
                        inner join account_move_line aml on av_giro_line.move_line_id = aml.id 
                        where aml.date >= '"""+ str(start_value_date) + """'  and left(av_giro.number,3) = 'SPA' group by av_giro.number) av_par 
                        on l.ref = av_par.number 
                    left join(select ac.code, ac.id as id, ac.name as ac_name, move_id as am_id from account_move_line aml 
                        left join account_account ac on aml.account_id = ac.id where aml.date >= '"""+ str(start_value_date) + """'
                        and aml.date <= '"""+ str(end_value_date) + """' and left(aml.ref,3) = 'BTR'  and left(ac.code,4) != '1102') btr 
                        on btr.am_id = m.id
                                
                    where    l.account_id  in """ + (str(accounts)) + """  and  l.date >= '"""+ str(start_value_date) + """'  and  l.date <= '"""+ str(end_value_date) + """'  and  l.analytic_account_id  in """+ (str(analytic)) +""") ll)
            
                    --select * from dym_bankbook
                    
                    select ll.id,ll.analytic_account_id,
                    case when ll.avl_name is not null then ll.avl_name 
                            else case when right(ll.ref,10) = '(Reversed)' then 'Reversed'
                            else case when ll.bt_description is not null then ll.bt_description || ' -- ' || btr_aj_name
                            else case when left(ll.ref,3) = 'TBK' or left(ll.ref,3) = 'TBM' then ll.avl_bt_name
                            else case when left(ll.name,3) = 'CPA' then coalesce(ll.av_name,ll.av_reference)
                            else case when left(ll.name,3) = 'CBA' then ll.name 
                            else case when left(ll.ref,3) = 'LOA' then ll.memo
                            else case when left(ll.ref,3) = 'PCO' then ll.dpl_name
                            else case when left(ll.ref,3) = 'PCI' then ll.dpil_name
                    else case when left(ll.name,3) in ('APA') then ll.name
                    else case when left(ll.name,3) in ('SAP') then ll.ref
                    else case when left(ll.ref,3) = 'SPA' then ll.av_par_name
                    else ll.av_name end end end end end end end end end end end end as "name",
                        ll.inv2_number || '(' || ll.inv2_number || ')-' || case when left(ll.ref,3) = 'TBK' or left(ll.ref,3) = 'TBM' then ll.tb_branch_name
                            else case when left(ll.ref,3) = 'BTR' then ll.btr_p_name
                            else coalesce(ll.p_name,'') end end jurnal_item,
                    
                    case when left(ll.ref,3) in ('BTR','LOA') then ll.ref
                            else case when left(ll.ref,3) in ('PCO','PCI') then ll.name
                            else case when left(ll.name,3) in ('CPA','CDE') then ll.name 
                            else case when (left(ll.ref,3) = 'TBM' or left(ll.ref,3) = 'TBM') and right(ll.ref,10) = '(Reversed)' then left(ll.ref,5) || '/' || substring(ll.ref,6,3) || '/' || substring(ll.ref,9,4) || '/' || substring(ll.ref,13,6) || ' ' || right(ll.ref,10)
                            else case when right(ll.ref,10) = '(Reversed)' then left(ll.ref,5) || '/' || substring(ll.ref,6,5) || '/' || substring(ll.ref,11,4) || '/' || substring(ll.ref,15,5) || ' ' || right(ll.ref,10)
                            else case when left(ll.name,3) in ('TBM','TBK') then ll.name
                            else case when left(ll.name,3) in ('CBA') then dcg_spa.dcg_spa
                            else case when left(ll.ref,3) in ('SPA') then ll.ref
                    else case when left(ll.name,3) in ('APA','SAP') then ll.name
                    else left(ll.ref,5) || '/' || substring(ll.ref,6,3) || '/' || substring(ll.ref,9,4) || '/' || right(ll.ref,5) end end end end end end end end end as ref, 
                    ll.dp2_name kas_bon, 
                        ll.reference,
                        case when av_giro2.payment_method in ('cheque','giro') then coalesce(dcl.name,av_giro2.reference) 
                    else case when av_giro2.payment_method in ('single_payment') then av_giro2.reference 
                    else case when av_giro.payment_method in ('internet_banking') then ibk.name 
                    else '-' end  end end cheque_giro_number, 
                    case when left(ll.ref,3) = 'TBK' or left(ll.ref,3) = 'TBM' then ll.tb_branch_code
                            else case when left(ll.ref,3) = 'BTR' then ll.btr_p_default_code
                            else coalesce(ll.p_default_code,'') end end as partner_code,              
                            case when left(ll.ref,3) = 'TBK' or left(ll.ref,3) = 'TBM' then ll.tb_branch_name
                            else case when left(ll.ref,3) = 'BTR' then ll.btr_p_name
                            else coalesce(ll.p_name,'') end end as partner_name,
                            case when ll.dso2_is_pic = 't' then ll.pic_name else '' end as cabang,
                        case when left(ll.name,3) = 'CDE' and (right(ll.name,10)  = '(Reversed)' or ll.avl_name is null) then coalesce(ll.ac_name,ll.ac3_name)
                            else case when left(ll.ref,3) = 'BTR' then ll.btr_ac_name 
                            else case when left(ll.name,3) = 'CPA' and (right(ll.ref,10)  = '(Reversed)' or ll.avl_name is null) then coalesce(ll.ac_name,ll.ac3_name)
                            else case when left(ll.ref,3) = 'SPA' and (right(ll.ref,10)  = '(Reversed)' or ll.avl_name is null) then coalesce(ll.ac2_name,spa.ac_name)   
                            else case when left(ll.ref,3) = 'TBK' and (right(ll.ref,10)  = '(Reversed)' or ll.avl_name is null) then coalesce(tbk.ac_name ,ll.ac2_name)  
                            else case when left(ll.ref,3) = 'TBM' and (right(ll.ref,10)  = '(Reversed)' or ll.avl_name is null) then coalesce(ll.ac_name,ll.ac3_name)
                            else case when left(ll.ref,3) = 'LOA' then ll.loan_spa_ac_name
                            else coalesce(ll.ac_name,ll.a_name)
                            end end end end end end end as account_name2,
                        case when left(ll.name,3) = 'CDE' and (right(ll.name,10)  = '(Reversed)' or avl_name is null) then coalesce(ll.ac_code,ll.ac3_code)
                            else case when left(ll.ref,3) = 'BTR' then ll.btr_ac_code
                            else case when left(ll.name,3) = 'CPA' and (right(ll.ref,10)  = '(Reversed)' or avl_name is null) then coalesce(ll.ac_code,ll.ac3_code)
                            else case when left(ll.ref,3) = 'SPA' then spa.code
                            else case when left(ll.ref,3) = 'TBK' and (right(ll.ref,10)  = '(Reversed)' or avl_name is null) then coalesce(tbk.code,ll.ac2_code)    
                            else case when left(ll.ref,3) = 'TBM' and (right(ll.ref,10)  = '(Reversed)' or avl_name is null) then coalesce(ll.ac_code,ll.ac3_code)
                            else case when left(ll.ref,3) = 'LOA' then ll.loan_spa_ac_code
                            else coalesce(ll.ac_code,ll.a_code)
                            end end end end end end end as account_code2,
                        case when left(ll.ref,3) = 'BTR' and ll.transaction_type = 'ats' then 'ATS' 
                            else case when left(ll.ref,3) = 'BTR' and ll.transaction_type = 'deposit' then 'Deposit' 
                            else case when left(ll.ref,3) = 'BTR' and ll.transaction_type = 'ho2branch' then 'HO to Branch' 
                            else case when left(ll.ref,3) = 'BTR' and ll.transaction_type = 'inhouse' then 'In House' 
                            else case when left(ll.ref,3) = 'BTR' and ll.transaction_type = 'withdraw' then 'Withdrawal' 
                            else '' end end end end end as btr_type,
                        case when left(ll.ref,3) = 'BTR' and ll.transaction_type = 'ats' then ll.btr_ats_name else null end as source_of_fund,
                        ll.account_id, 
                        ll.date, 
                        ll.debit  as debit, 
                        case when left(ll.ref,3) in ('PCO') then ll.dpl_amount else ll.credit end as credit, 
                        case when ll.is_credit = 't' then  ll.fc2_name else case when right(coalesce(ll.ac_name,ll.a_name),14) ='Piutang Dagang' then 'CASH' else '' end end as finance_company, 
                        ll.fc2_name as finance_company2 ,
                        ll.bt_state as state
                
                    from dym_bankbook ll 
                        
                        left join (select ac.code, ac.id as id, ac.name as ac_name, am.name as name from account_move_line aml 
                        inner join account_move am on aml.move_id = am.id
                        inner join account_account ac on aml.account_id = ac.id 
                        where left(am.name,3) = 'TBK' and aml.debit > 0 and  aml.date >= '"""+ str(start_value_date) + """' and aml.date <= '"""+ str(end_value_date) + """') 
                        tbk on tbk.name = ll.av_number
                        left join (select dcg.id as dcg_id, dcg.name as dcg_name, dcg.ref as dcg_ref, am_spa.spa as dcg_spa
                        from dym_clearing_giro dcg 
                        left join account_move am on am.id = dcg.move_id
                        left join account_move_line aml on am.id = aml.move_id and aml.reconcile_id is not null
                        left join (select am.id as id, am.name as spa, aml.reconcile_id from account_move am 
                                   inner join account_move_line aml on am.id = aml.move_id and aml.reconcile_id is not null
                        where left(am.name,3) = 'SPA' and  aml.date >= '"""+ str(start_value_date) + """'::date + cast('-1 month' as interval)) am_spa on am_spa.reconcile_id = aml.reconcile_id ) dcg_spa on dcg_spa.dcg_name = ll.name
                        left join account_move m_spa on ll.ref = m_spa.ref and left(m_spa.name,3) = 'SPA'
                        left join (select ac.code, ac.id as id, ac.name as ac_name, am.name as name, am.id as am_id, am.ref as ref from account_move_line aml 
                        inner join account_move am on aml.move_id = am.id
                        inner join account_account ac on aml.account_id = ac.id 
                        where left(am.name,3) = 'SPA' and aml.debit > 1000  and  aml.date >= '"""+ str(start_value_date) + """' and aml.date <= '"""+ str(end_value_date) + """') spa on spa.name = m_spa.name
                        left join account_account ac_spa on ac_spa.id = spa.am_id
                        left join account_move_line aml_cpa on aml_cpa.id = ll.move_line_id
                        left join account_voucher av_cpa on replace(av_cpa.number,'/','') = aml_cpa.ref
                        left join account_voucher_line avl_cpa on avl_cpa.voucher_id = av_cpa.id
                        left join account_voucher av_spa_sin on av_spa_sin.number = spa.name
                        left join account_voucher av_spa on av_spa.number = spa.name
                        left join account_voucher av_giro on replace(ll.ref,'/','') = replace(av_giro.number,'/','')
                        left join account_voucher_line av_giro_line on av_giro.id = av_giro_line.voucher_id
                        left join account_voucher av_giro2 on dcg_spa.dcg_spa= av_giro2.number
                        left join dym_ibanking ibk on av_giro.ibanking_id = ibk.id 
                        left join dym_checkgyro_line dcl on av_giro2.cheque_giro_number = dcl.id 
                        ORDER BY 15,5 """


        move_selection = ""
        report_info = _('')
        move_selection += ""

        reports = [report_bank_book_new]
        states = {
            'draft':'Draft',
            'waiting_for_approval':'Waiting For Approval',
            'waiting_for_confirm_received':'Waiting For Confirm Received',
            'confirmed':'Waiting Approval',
            'app_approve':'Approved',
            'app_received':'Received',
            'approved':'Done',
            'cancel':'Cancelled',
            None:'',
        }

        for report in reports:
            if data['projection']:
                a = cr.execute(sql_query_projection)
            else:
                a = cr.execute(query_bank_book_new)
            all_lines = cr.dictfetchall()
            #print query_bank_book_new

            move_lines = []            
            if all_lines:
                p_map = map(
                    lambda x: {
                        'no':0,
                        'id': x['id'],
                        'account_id': x['account_id'],
                        'date': x['date'] if x['date'] != None else '',  
                        #'value_date': x['at_value_date'] if x['at_value_date'] and x['at_value_date'] != None else x['cg_value_date'] if x['cg_value_date'] and x['cg_value_date'] != None else x['av_value_date'] if x['av_value_date'] and x['av_value_date'] != None else x['bt_value_date'] if x['bt_value_date'] and x['bt_value_date'] != None else x['avp_value_date'] if x['avp_value_date'] and x['avp_value_date'] != None else '',
                        'debit': x['debit'] if x['debit'] > 0 else 0.0,
                        'credit': x['credit'] if x['credit'] > 0 else 0.0,
                        'cur_balance': 0.0,
                        'account_code2': x['account_code2'],
                        'account_name2': x['account_name2'],
                        'btr_type': x['btr_type'],
                        'source_of_fund': x['source_of_fund'],
                        'partner_code': x['partner_code'].encode('ascii', 'ignore').decode('ascii')if x['partner_code'] != None else '',
                        'partner_name': x['partner_name'].encode('ascii','ignore').decode('ascii') if x['partner_name'] != None else '',
                        'cabang': x['cabang'].encode('ascii', 'ignore').decode('ascii') if x['cabang'] != None else '',
                        'finance_company': x['finance_company2'].encode('ascii','ignore').decode('ascii') if x['finance_company2'] != None else x['finance_company'].encode('ascii','ignore').decode('ascii') if x['finance_company'] != None else '',
                        'name': x['name'].encode('ascii','ignore').decode('ascii') if x['name'] != None else '',
                        'ref': x['ref'].encode('ascii','ignore').decode('ascii') if x['ref'] != None else '',
                        'kas_bon': x['kas_bon'].encode('ascii', 'ignore').decode('ascii') if x['kas_bon'] != None else '',
                        'jurnal_item': x['jurnal_item'].encode('ascii', 'ignore').decode('ascii') if x['jurnal_item'] != None else '',
                        'analytic_4': x['analytic_account_id'] if x['analytic_account_id'] != None else '',
                        'cheque_giro_number': x['cheque_giro_number'].encode('ascii','ignore').decode('ascii') if x['cheque_giro_number'] != None else '',
                        'state': states[x['state'].encode('ascii','ignore').decode('ascii')] if x['state'] != None else '',
                    },
                    all_lines)
                cur_balance = saldo_awal
                #print 'saldo awal: ' ,cur_balance
                #n=1
                for p in p_map:
                    x = p['ref']
                    if p['id'] not in map(
                            lambda x: x.get('id', None), move_lines) or x[:3] == 'PCO' or x[:3] == 'PCI':
                        account_move_lines = filter(
                            lambda x: x['id'] == p['id'], all_lines)

                        #print n
                        #n=n+1
                        cur_balance = cur_balance + p['debit'] - p['credit']
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
                        account_code2=''
                        account_name2=''
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
                            p.update({'cur_balance': cur_balance})
                            move_lines.append(p)
                report.update({'move_lines': move_lines})
        reports = filter(lambda x: x.get('move_lines'), reports)

        if not reports:
            reports = [{
                'type': 'BankBook',
                'title': '',
                'title_short': title_short_prefix + ', ' + _(' '.join(['LAPORAN BANK BOOK NEW','(PROYEKSI)' if data['projection'] else ''])),
                'saldo_awal': saldo_awal,
                'start_date': start_value_date,
                'end_date': end_value_date,
                'move_lines': [{
                    'no':0,
                    'branch_status': 'NO DATA FOUND',
                    'branch_name': 'NO DATA FOUND',
                    'account_code2': 'NO DATA FOUND',
                    'account_name2': 'NO DATA FOUND',
                    'btr_type': 'NO DATA FOUND',
                    'source_of_fund': 'NO DATA FOUND',
                    'partner_code': 'NO DATA FOUND',
                    'partner_name':'NO DATA FOUND',
                    'cabang': 'NO DATA FOUND',
                    'finance_company':'NO DATA FOUND',
                    'name': 0,
                    'cheque_giro_number':'NO DATA FOUND',
                    'ref': 0,
                    'kas_bon': 'NO DATA FOUND',
                    'jurnal_item': 'NO DATA FOUND',
                    'date': 'NO DATA FOUND',
                    'value_date': 'NO DATA FOUND',
                    'debit': 0.0,
                    'credit':  0.0,
                    'cur_balance': 0.0,
                    'analytic_1': 'NO DATA FOUND',
                    'analytic_2': 'NO DATA FOUND',
                    'analytic_3': 'NO DATA FOUND',
                    'analytic_4': 'NO DATA FOUND',
                    'analytic_combination': 'NO DATA FOUND',
                    'state': 'NO DATA FOUND',
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
        super(dym_bank_book_new_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_bank_book_new_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_account_move.report_bank_book_new'
    _inherit = 'report.abstract_report'
    _template = 'dym_account_move.report_bank_book_new'
    _wrapped_report_class = dym_bank_book_new_report_print
