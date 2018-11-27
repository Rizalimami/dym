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

                where_account=" a.id  in %s " % str(
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
                for det in res_dict:
                    debit, credit = det['debit'], det['credit']
                    period_debit = debit and float(debit) or 0.0
                    period_credit = credit and float(credit) or 0.0
                mutasi_projection = period_debit - period_credit

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

        title_short = 'LAPORAN BANK BOOK'
        if data['projection']:
            title_short = title_short + ' (PROYEKSI)'
        report_bank_book = {
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

        query_bank_book = """
            SELECT DISTINCT
                l.id, 
                l.analytic_account_id, 
                case when avl.name is not null then avl.name 
                else case when right(l.ref,10) = '(Reversed)' then 'Reversed'
                else case when bt.description is not null then bt.description || ' -- ' || btr_aj.name
                --else case when left(l.ref,3) = 'SPA' and spa.code = '2102001' then ai_sin_spa.supplier_invoice_number
                --else case when left(l.ref,3) = 'SPA' and spa.code = '2106099' and left(avl_spa_sin.name,3) = 'PAR' then desc_par.desc
                --else case when left(l.ref,3) = 'SPA' and spa.code = '2106099' and left(avl_spa_sin.name,3) = 'SIN' then ail_sin_spa.name
                --else case when left(l.ref,3) = 'SPA' and spa.code = '2102004' then ai_sin_spa.origin
                else case when left(l.ref,3) = 'TBK' or left(l.ref,3) = 'TBM' then avl_bt.name
                else case when left(m.name,3) = 'CPA' then coalesce(av.name,av.reference)
                else case when left(m.name,3) = 'CBA' then l.name
                else case when left(l.ref,3) = 'LOA' then dl.memo
                else case when left(l.ref,3) = 'PCO' then dpl.name
                else case when left(l.ref,3) = 'PCI' then dpil.name
		else case when left(m.name,3) in ('APA') then l.name
		else case when left(m.name,3) in ('SAP') then l.ref
		else av.name end end end end end end end end end end end  as "name",
		        inv2.number || '(' || inv2.name || ')-' || case when left(l.ref,3) = 'TBK' or left(l.ref,3) = 'TBM' then tb_branch.name
                else case when left(l.ref,3) = 'BTR' then btr_p.name
                else coalesce(p.name,'') end end jurnal_item,              
                case when left(l.ref,3) in ('BTR','LOA') then l.ref
                else case when left(l.ref,3) in ('PCO','PCI') then m.name
                else case when left(m.name,3) in ('CPA','CDE') then m.name 
                else case when (left(l.ref,3) = 'TBM' or left(l.ref,3) = 'TBM') and right(l.ref,10) = '(Reversed)' then left(l.ref,5) || '/' || substring(l.ref,6,3) || '/' || substring(l.ref,9,4) || '/' || substring(l.ref,13,6) || ' ' || right(l.ref,10)
                else case when right(l.ref,10) = '(Reversed)' then left(l.ref,5) || '/' || substring(l.ref,6,5) || '/' || substring(l.ref,11,4) || '/' || substring(l.ref,15,5) || ' ' || right(l.ref,10)
                else case when left(m.name,3) in ('TBM','TBK') then m.name
                else case when left(m.name,3) in ('CBA') then dcg_spa.dcg_spa
                else case when left(l.ref,3) in ('SPA') then l.ref
		else case when left(m.name,3) in ('APA','SAP') then m.name
		else left(l.ref,5) || '/' || substring(l.ref,6,3) || '/' || substring(l.ref,9,4) || '/' || right(l.ref,5) end end end end end end end end end as ref, 
                dp2.name kas_bon,
                dcl.name cheque_giro_number,
		        case when left(l.ref,3) = 'TBK' or left(l.ref,3) = 'TBM' then tb_branch.code
                else case when left(l.ref,3) = 'BTR' then btr_p.default_code
                else coalesce(p.default_code,'') end end as partner_code,              
                case when left(l.ref,3) = 'TBK' or left(l.ref,3) = 'TBM' then tb_branch.name
                else case when left(l.ref,3) = 'BTR' then btr_p.name
                else coalesce(p.name,'') end end as partner_name,
                case when dso2.is_pic = 't' then pic.name else '' end as cabang,
                case when left(m.name,3) = 'CDE' and (right(m.name,10)  = '(Reversed)' or avl.name is null) then coalesce(ac.name,ac3.name)
                else case when left(l.ref,3) = 'BTR' then btr.ac_name 
                else case when left(m.name,3) = 'CPA' and (right(l.ref,10)  = '(Reversed)' or avl.name is null) then coalesce(ac.name,ac3.name)
                else case when left(l.ref,3) = 'SPA' and (right(l.ref,10)  = '(Reversed)' or avl.name is null) then coalesce(ac2.name,spa.ac_name)   
                else case when left(l.ref,3) = 'TBK' and (right(l.ref,10)  = '(Reversed)' or avl.name is null) then coalesce(tbk.ac_name ,ac2.name)  
                else case when left(l.ref,3) = 'TBM' and (right(l.ref,10)  = '(Reversed)' or avl.name is null) then coalesce(ac.name,ac3.name)
                else case when left(l.ref,3) = 'LOA' then loan_spa.ac_name
                else coalesce(ac.name,a.name)
                end end end end end end end as account_name2,
                case when left(m.name,3) = 'CDE' and (right(m.name,10)  = '(Reversed)' or avl.name is null) then coalesce(ac.code,ac3.code)
                else case when left(l.ref,3) = 'BTR' then btr.code
                else case when left(m.name,3) = 'CPA' and (right(l.ref,10)  = '(Reversed)' or avl.name is null) then coalesce(ac.code,ac3.code)
                else case when left(l.ref,3) = 'SPA' then spa.code
                else case when left(l.ref,3) = 'TBK' and (right(l.ref,10)  = '(Reversed)' or avl.name is null) then coalesce(tbk.code,ac2.code)    
                else case when left(l.ref,3) = 'TBM' and (right(l.ref,10)  = '(Reversed)' or avl.name is null) then coalesce(ac.code,ac3.code)
                else case when left(l.ref,3) = 'LOA' then loan_spa.ac_code
                else coalesce(ac.code,a.code)
                end end end end end end end as account_code2, 
                case when left(l.ref,3) = 'BTR' and bt.transaction_type = 'ats' then 'ATS' 
                else case when left(l.ref,3) = 'BTR' and bt.transaction_type = 'deposit' then 'Deposit' 
                else case when left(l.ref,3) = 'BTR' and bt.transaction_type = 'ho2branch' then 'HO to Branch' 
                else case when left(l.ref,3) = 'BTR' and bt.transaction_type = 'inhouse' then 'In House' 
                else case when left(l.ref,3) = 'BTR' and bt.transaction_type = 'withdraw' then 'Withdrawal' 
                else '' end end end end end as btr_type,
                case when left(l.ref,3) = 'BTR' and bt.transaction_type = 'ats' then btr_ats.name else null end as source_of_fund,
                l.account_id, 
                l.date, 
                l.debit  as debit, 
                case when left(l.ref,3) in ('PCO') then dpl.amount else l.credit end as credit, 
                case when dso2.is_credit = 't' then  fc2.name else case when right(coalesce(ac.name,a.name),14) ='Piutang Dagang' then 'CASH' else '' end end as finance_company, 
                fc2.name as finance_company2 ,
                bt.state as state
            FROM account_move_line l
            LEFT JOIN account_move m on m.id = l.move_id
            LEFT JOIN (select a.id,account_id  from account_move a,account_move_line b where a.id = b.move_id and b.debit >0) aml2 on aml2.id  = m.reverse_from_id
            LEFT JOIN (select a.id,account_id  from account_move a,account_move_line b where a.id = b.move_id and b.credit >0) aml3 on aml3.id  = m.reverse_from_id
            LEFT JOIN account_account ac2 on aml2.account_id = ac2.id
            LEFT JOIN account_account ac3 on aml3.account_id = ac3.id
            LEFT JOIN account_account a on a.id = l.account_id
            LEFT JOIN res_partner p on p.id = l.partner_id
            LEFT JOIN account_invoice inv on m.id = inv.move_id
            LEFT JOIN dealer_sale_order dso on dso.name = inv.name
            LEFT JOIN res_partner fc on fc.id = dso.finco_id
            LEFT JOIN account_voucher av on av.number = m.name
            LEFT JOIN account_voucher_line avl_bt on avl_bt.voucher_id = av.id
            LEFT JOIN dym_bank_transfer bt on bt.name = m.name
            LEFT JOIN dym_bank_transfer_line btl on btl.bank_transfer_id = bt.id
            LEFT JOIN res_partner btr_p on btr_p.default_code = btl.branch_destination_id
            LEFT JOIN dym_branch tb_branch on tb_branch.id = av.branch_id
            left join account_journal btr_aj on btr_aj.id = btl.payment_to_id
            left join account_journal btr_ats on btr_ats.id = bt.payment_from_id_ats
            LEFT JOIN account_voucher_line avl on av.id = avl.voucher_id and avl.type = 'cr'
            LEFT JOIN account_account ac on ac.id = avl.account_id
            LEFT JOIN account_move_line l2 on l2.id = avl.move_line_id
            LEFT JOIN account_invoice inv2 on inv2.move_id = l2.move_id
            LEFT JOIN dealer_sale_order dso2 on dso2.name = inv2.name
            LEFT JOIN dym_cabang_partner pic on pic.id = dso2.partner_cabang
            LEFT JOIN res_partner fc2 on fc2.id = dso2.finco_id
            LEFT JOIN dym_checkgyro_line dcl on av.cheque_giro_number = dcl.id
            LEFT JOIN (SELECT ac.code, ac.id as id, ac.name as ac_name, am.name as name from account_move_line aml 
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN account_account ac on aml.account_id = ac.id 
            WHERE left(am.name,3) = 'TBK' and aml.debit > 0) tbk on tbk.name = av.number
            LEFT JOIN account_account ac_tbk on ac_tbk.id = tbk.id
            LEFT JOIN (SELECT ac.code, ac.id as id, ac.name as ac_name, am.name as name, am.id as am_id from account_move_line aml 
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN account_account ac on aml.account_id = ac.id 
            WHERE left(am.name,3) = 'BTR' and left(ac.code,4) != '1102') btr on btr.am_id = m.id
            LEFT JOIN account_account ac_btr on ac_btr.id = btr.am_id
            left join (select dcg.id as dcg_id, dcg.name as dcg_name, dcg.ref as dcg_ref, am_spa.spa as dcg_spa
            from dym_clearing_giro dcg 
            left join account_move am on am.id = dcg.move_id
            left join account_move_line aml on am.id = aml.move_id and aml.reconcile_id is not null
            left join (select am.id as id, am.name as spa, aml.reconcile_id
                    from account_move am 
                    left join account_move_line aml on am.id = aml.move_id and aml.reconcile_id is not null
                    where left(am.name,3) = 'SPA') am_spa on am_spa.reconcile_id = aml.reconcile_id
            ) dcg_spa on dcg_spa.dcg_name = m.name
            LEFT JOIN account_move m_spa on m.ref = m_spa.ref and left(m_spa.name,3) = 'SPA'
            LEFT JOIN ( SELECT ac.code, ac.id as id, ac.name as ac_name, am.name as name, am.id as am_id, am.ref as ref from account_move_line aml 
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN account_account ac on aml.account_id = ac.id 
            WHERE left(am.name,3) = 'SPA' and aml.debit > 1000) spa on spa.name = m_spa.name
            LEFT JOIN account_account ac_spa on ac_spa.id = spa.am_id
            left join account_move_line aml_cpa on aml_cpa.id = avl.move_line_id
            left join account_voucher av_cpa on replace(av_cpa.number,'/','') = aml_cpa.ref
            left join account_voucher_line avl_cpa on avl_cpa.voucher_id = av_cpa.id
            left join account_voucher av_spa_sin on av_spa_sin.number = spa.name
            --left join account_voucher_line avl_spa_sin on avl_spa_sin.voucher_id = av_spa_sin.id
            --left join account_invoice ai_sin_spa on ai_sin_spa.number = avl_spa_sin.name
            --left join account_invoice_line ail_sin_spa on ail_sin_spa.invoice_id = ai_sin_spa.id
            left join account_voucher av_spa on av_spa.number = spa.name
            --left join account_voucher_line avl_spa on avl_spa.voucher_id = av_spa.id
            left join dym_loan dl on l.ref = dl.name
            left join ( SELECT ac.code as ac_code, ac.id as id, ac.name as ac_name, am.name as name, am.id as am_id, am.ref as ref from account_move_line aml 
                        LEFT JOIN account_move am on aml.move_id = am.id
                        LEFT JOIN account_account ac on aml.account_id = ac.id 
                        WHERE left(am.name,3) = 'SPA' and ac.code in ('2101002') and aml.debit > 1000) loan_spa on loan_spa.ref = dl.name
            --left join ( SELECT distinct(av.number) as number, avl.voucher_id as id, string_agg(distinct(avl.name), ', ') AS desc 
            --        from account_voucher av
            --        left join account_voucher_line avl on avl.voucher_id = av.id 
            --        where left(av.number,3) = 'PAR'
            --        group by avl.voucher_id, av.number) desc_par on desc_par.number = avl_spa.name
            LEFT JOIN dym_pettycash dp on m.name = dp.name
            LEFT JOIN dym_pettycash_line dpl on dp.id = dpl.pettycash_id 
            LEFT JOIN dym_pettycash_in dpi on m.name = dpi.name
            LEFT JOIN dym_pettycash_in_line dpil on dpi.id = dpil.pettycash_id
            LEFT JOIN dym_pettycash dp2 on dp2.id = dpi.pettycash_id
            LEFT JOIN account_period ap on ap.id = l.period_id 
            WHERE %s and %s and %s and %s and ap.special = FALSE 
            ORDER BY 15,5 """ % (where_account, where_start_date, where_end_date, where_analytic)

        move_selection = ""
        report_info = _('')
        move_selection += ""
        #print query_bank_book
        reports = [report_bank_book]
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
                a = cr.execute(query_bank_book)
            all_lines = cr.dictfetchall()

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
                for p in p_map:
                    # if p['ref'][:3] == 'BTR':
                    #     # btr_ids = self.pool.get('dym.bank.transfer').browse(cr, uid, p['ref'])
                    #     btr_ids = self.pool.get('dym.bank.transfer').search(cr, uid, [('name','ilike',p['ref'])])
                    #     if btr_ids:
                    #         btr_datas = self.pool.get('dym.bank.transfer').browse(cr, uid, btr_ids)
                    #         print "----------------", btr_datas.name
                    x = p['ref']

                    if x[:3] == 'SPA':
                        spa_ids = self.pool.get('account.voucher').search(cr, uid, [('number','ilike',x)])
                        if spa_ids:
                            spa_id = self.pool.get('account.voucher').browse(cr, uid, spa_ids)
                            list_spa = []
                            list_par = []
                            for spa_x in spa_id.line_dr_ids:
                                if spa_x.move_line_id.ref:
                                    if spa_x.move_line_id.ref[:3] == 'PAR':
                                        if len(spa_x.move_line_id.ref) == 17:
                                            par_number = spa_x.move_line_id.ref[:5], "/", spa_x.move_line_id.ref[5:8] ,"/", spa_x.move_line_id.ref[8:12] ,"/", spa_x.move_line_id.ref[12:]
                                            par_num = ''.join(par_number)
                                        elif len(spa_x.move_line_id.ref) == 19:
                                            par_number = spa_x.move_line_id.ref[:5], "/", spa_x.move_line_id.ref[5:10] ,"/", spa_x.move_line_id.ref[10:14] ,"/", spa_x.move_line_id.ref[14:]
                                            par_num = ''.join(par_number)
                                        elif len(spa_x.move_line_id.ref) == 21:
                                            par_number = spa_x.move_line_id.ref[:5], "/", spa_x.move_line_id.ref[5:12] ,"/", spa_x.move_line_id.ref[12:16] ,"/", spa_x.move_line_id.ref[16:]
                                            par_num = ''.join(par_number)
                                        #print 'vvvvv',spa_x.move_line_id.ref,'vvvvvv'
                                        par_ids = self.pool.get('account.voucher').search(cr, uid, [('number','ilike',par_num)])
                                        if par_ids:
                                            par_id = self.pool.get('account.voucher').browse(cr, uid, par_ids)
                                            for par_x in par_id.line_dr_ids:
                                                if par_x:
                                                    list_par.append(par_x.name)
                                    else:
                                        list_spa.append(spa_x.move_line_id.name)
                                    if spa_id.payment_method in ('cheque','giro'):
                                        p.update({'cheque_giro_number': spa_id.cheque_giro_number.name})
                                    elif spa_id.payment_method == ('internet_banking'):
                                        ibk_ids = self.pool.get('dym.ibanking').search(cr, uid, [('id','=',spa_id.ibanking_id.id)])
                                        ibk_id = self.pool.get('dym.ibanking').browse(cr, uid, ibk_ids)
                                        p.update({'cheque_giro_number': ibk_id.name})
                                    elif spa_id.payment_method == ('single_payment'):
                                        p.update({'cheque_giro_number': spa_id.reference})
                                    if list_spa:
                                        desc = ', '.join(list_spa)
                                    else:
                                        desc = ', '.join(list_par)
                                    p.update({'name': desc})

                    if p['id'] not in map(
                            lambda x: x.get('id', None), move_lines) or x[:3] == 'PCO' or x[:3] == 'PCI':
                        account_move_lines = filter(
                            lambda x: x['id'] == p['id'], all_lines)

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
                'title_short': title_short_prefix + ', ' + _(' '.join(['LAPORAN BANK BOOK','(PROYEKSI)' if data['projection'] else ''])),
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
