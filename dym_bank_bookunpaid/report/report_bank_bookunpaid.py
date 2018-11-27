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

class dym_bank_bookunpaid_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_bank_bookunpaid_report_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    # def get_fiscalyear(self,period_id):
    #     cr = self.cr
    #     query_fiscal = "SELECT fiscalyear_id FROM account_period WHERE id = %s"
        
    #     cr.execute(query_fiscal, (period_id, ))
    #     fiscalyear_id = cr.fetchall()
    #     return fiscalyear_id[0][0]
    
    # def get_period(self,period_id,fiscalyear_id):
    #     cr = self.cr
    #     query_period = "SELECT id from account_period " \
    #         "WHERE id < %s AND fiscalyear_id = %s "
            
    #     cr.execute(query_period, (period_id,fiscalyear_id ))
    #     period_ids = cr.fetchall() 
    #     period_id_kolek = []
    #     for id in period_ids:
    #         period_id_kolek.append(id)      
    #     if not period_id_kolek :
    #         return False 
             
    #     return period_id_kolek

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
            journal_ids = self.pool.get('account.journal').browse(cr,uid,journal_id[0]).ids
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
                date_from=start_value_date, 
                date_to=end_value_date, 
                initial_bal=True,
                sql_query=sql_query
            ).balance
            bal_db_init = journal.default_debit_account_id.with_context(
                date_from=start_value_date, 
                date_to=end_value_date, 
                initial_bal=True,
                sql_query=sql_query
            ).balance
            bank_balance_init = bal_cr_init or bal_db_init

        #     if data['projection']:
        #         sql_query_projection1 = """
        #             SELECT 
        #                 sum(l.debit) as debit,
        #                 sum(l.credit) as credit
        #             FROM 
        #                 account_move_line l
        #             WHERE 
        #                 l.clear_state in ('open') AND 
        #                 l.date < '%s' AND
        #                 %s
        #         """ % (start_value_date, where_analytic)

        #         where_account=" a.id  in %s " % str(
        #             tuple(account_ids)).replace(',)', ')')
        #         where_start_date = " l.date >= '%s' " % start_value_date
        #         where_end_date = " l.date <= '%s' " % end_value_date

        #         sql_query_projection = """
        #         SELECT 
        #         l.id, 
        #         l.analytic_account_id, 
        #         case when avl.name is not  null then avl.name else case when  bt.description is not null then bt.description else av.name end  end  "name" , 
        #         l.ref, 
        #         dcl.name cheque_giro_number,
        #         p.name as partner_name, 
        #         coalesce(ac.name,a.name) as account_name2,
        #         coalesce(ac.code,a.code) as account_code2, 
        #         '' as btr_type,
        #         l.account_id, 
        #         l.date, 
        #         l.debit, 
        #         l.credit,
        #         bt.state,
        #         fc.name as finance_company, 
        #         fc2.name as finance_company2, 
        #         at.value_date as at_value_date, 
        #         cg.value_date as cg_value_date, 
        #         av.value_date as av_value_date, 
        #         bt.value_date as bt_value_date, 
        #         avp.date as avp_value_date,
        #         bta.name as bta_name,
        #         bta.amount as amount,
        #         bta.transfer_date as trf_date 
        #         FROM account_move_line l 
        #         LEFT JOIN account_move m on m.id = l.move_id 
        #         LEFT JOIN account_account a on a.id = l.account_id 
        #         LEFT JOIN res_partner p on p.id = l.partner_id 
        #         LEFT JOIN account_invoice inv on m.id = inv.move_id 
        #         LEFT JOIN dealer_sale_order dso on dso.name = inv.name 
        #         LEFT JOIN res_partner fc on fc.id = dso.finco_id 
        #         LEFT JOIN dym_alokasi_titipan at on at.name = m.name 
        #         LEFT JOIN dym_clearing_giro cg on cg.name = m.name 
        #         LEFT JOIN account_voucher av on av.number = m.name and av.type in ('purchase','payment') and av.state not in ('posted','draft','cancel')
        #         LEFT JOIN dym_bank_transfer bt on bt.name = m.name and bt.state not in ('approved','draft','cancel')
        #         LEFT JOIN dym_advance_payment avp on avp.name = m.name 
        #         LEFT JOIN account_voucher_line avl on av.id = avl.voucher_id and avl.type = 'cr'
        #         LEFT JOIN account_account ac on ac.id = avl.account_id 
        #         LEFT JOIN account_move_line l2 on l2.id = avl.move_line_id 
        #         LEFT JOIN account_invoice inv2 on inv2.move_id = l2.move_id 
        #         LEFT JOIN dealer_sale_order dso2 on dso2.name = inv2.name 
        #         LEFT JOIN res_partner fc2 on fc2.id = dso2.finco_id 
        #         LEFT JOIN dym_checkgyro_line dcl on av.cheque_giro_number = dcl.id
        #         LEFT JOIN bank_trf_advice bta on bta.name=bt.name and bta.state in ('done')
        #         WHERE %s and %s and %s and %s 
        #         ORDER BY bt.state


        #         """ % (where_account, where_start_date, where_end_date, where_analytic) 


                # cr.execute(sql_query_projection)
                # res_dict = cr.dictfetchall()
            #     init_debit = 0.0
            #     init_credit = 0.0
            #     for det in res_dict:
            #         debit, credit = det['debit'], det['credit']
            #         init_debit = debit and float(debit) or 0.0
            #         init_credit = credit and float(credit) or 0.0
            #     saldo_awal_projection = init_debit - init_credit

            #     # Blance On Range Dates
            #     sql_query_projection2 = """
            #         SELECT 
            #             sum(l.debit) as debit,
            #             sum(l.credit) as credit
            #         FROM 
            #             account_move_line l
            #         WHERE 
            #             l.clear_state in ('open') AND 
            #             l.date >= '%s' AND
            #             l.date <= '%s' AND
            #             %s
            #     """ % (start_value_date, end_value_date, where_analytic)
            #     cr.execute(sql_query_projection)
            #     res_dict = cr.dictfetchall()

            #     period_debit = 0.0
            #     period_credit = 0.0
            #     for det in res_dict:
            #         debit, credit = det['debit'], det['credit']
            #         period_debit = debit and float(debit) or 0.0
            #         period_credit = credit and float(credit) or 0.0
            #     mutasi_projection = period_debit - period_credit

            # day_start = datetime.strptime(start_value_date, DSDF).day            
            # if day_start==1:
            #     saldo_awal = bank_balance_init
            # else:
            #     bal_cr_init = journal.default_credit_account_id.with_context(
            #         date_from=datetime.strptime(start_value_date, DSDF).replace(day=1).strftime(DSDF), 
            #         date_to=datetime.strptime(start_value_date, '%Y-%m-%d') - timedelta(days=1),
            #         initial_bal=False,
            #         sql_query=sql_query
            #     ).balance
            #     bal_db_init = journal.default_debit_account_id.with_context(
            #         date_from=datetime.strptime(start_value_date, DSDF).replace(day=1).strftime(DSDF), 
            #         date_to=datetime.strptime(start_value_date, '%Y-%m-%d') - timedelta(days=1),
            #         initial_bal=False,
            #         sql_query=sql_query
            #     ).balance
            #     saldo_awal = bank_balance_init + (bal_cr_init - bal_db_init)

            # where_account=" a.id  in %s " % str(
            #     tuple(account_ids)).replace(',)', ')')  

        title_short = 'LAPORAN BANK BOOK'
        if data['projection']:
            title_short = title_short + ' (PROYEKSI)'
        report_bank_bookunpaid = {
            'type': 'BankBookUnpaid',
            'title': '',
            'title_short': title_short_prefix + ', ' + _(title_short)
            }  

        # where_start_date = " l.date >= '%s' " % start_value_date
        # where_end_date = " l.date <= '%s' " % end_value_date
        # where_value_start = " 1=1 "
        # if start_value_date:
        #     where_value_start = " (at.value_date >= '%s' OR " % start_value_date
        #     where_value_start += " cg.value_date >= '%s' OR " % start_value_date
        #     where_value_start += " av.value_date >= '%s' OR " % start_value_date
        #     where_value_start += " bt.value_date >= '%s') " % start_value_date
        # where_value_end = " 1=1 "
        # if end_value_date:
        #     where_value_end = " (at.value_date <= '%s' OR " % end_value_date
        #     where_value_end += " cg.value_date <= '%s' OR " % end_value_date
        #     where_value_end += " av.value_date <= '%s' OR " % end_value_date
        #     where_value_end += " bt.value_date <= '%s') " % end_value_date

        query_bank_bookunpaid_projection = """
            --IBanking
            select  ib.id as id,
                db.name as branch_name,
                ib.date as date,
                case when rp.name is null then db_dbt.name else rp.name end as partner_name,
                '' as finance_company,
                ac.code as account_code2,
                ac.name as account_name2,
                case when dbt.description is not null then dbt.description || '(' || db_dbt.name || ')' else avl_spa.name end as name,
                ib.name as cheque_giro_number,
                case when av.number is null then dbt.name else av.number end as ref,
                --dbt.name as ref,
                0 as debit,
                case when av.amount is null then dbtl.amount else av.amount end as credit,
                --dbtl.amount as credit,
                case when acc_spa_1.code is null then acc_dbt_1.code || '/' || acc_dbt_2.code || '/' || acc_dbt_3.code || '/' || acc_dbt_4.code else acc_spa_1.code || '/' || acc_spa_2.code || '/' || acc_spa_3.code || '/' || acc_spa_4.code end as analytic_combination,
                case when acc_spa_1.code is null then acc_dbt_1.code else acc_spa_1.code end as analytic_1,
                case when acc_spa_2.code is null then acc_dbt_2.code else acc_spa_2.code end as analytic_2,
                case when acc_spa_3.code is null then acc_dbt_3.code else acc_spa_3.code end as analytic_3,
                case when acc_spa_4.code is null then acc_dbt_4.code else acc_spa_4.code end as analytic_4,
                case when av.state is null then (case when dbt.state = 'approved' then 'Done'
                        else case when dbt.state = 'draft' then 'Draft'
                        else case when dbt.state = 'cancel' then 'Cancel'
                        else case when dbt.state = 'appreceived' then 'Received'
                        else case when dbt.state = 'appapprove' then 'Process Done'
                        else case when dbt.state = 'confirmed' then 'Waiting Approval'
                        else case when dbt.state = 'waiting_for_approval' then 'Payment in Process'
                        else case when dbt.state = 'waiting_for_confirm_received' then 'Waiting For Confirm Received'
                        else dbt.state end end end end end end end end )
                else (case when av.state = 'posted' then 'Posted'
                        else case when av.state = 'draft' then 'Draft'
                        else case when av.state = 'cancel' then 'Cancelled'
                        else case when av.state = 'request_approval' then 'RFA'
                        else case when av.state = 'approved' then 'Approve'
                        else case when av.state = 'confirmed' then 'Waiting Approval'
                        else case when av.state = 'waiting_for_approval' then 'Waiting Approval'
                    else av.state end end end end end end end)
                end as state,
                case when dbt.transaction_type = 'ho2branch' then 'HO to Branch' else '' end as btr_type,
                ib.state as state_ib_dcg
            from    dym_ibanking ib
            left join account_voucher av on av.ibanking_id = ib.id and av.state not in ('cancel')
            left join dym_bank_transfer dbt on dbt.ibanking_id = ib.id and dbt.state not in ('cancel')
            left join dym_bank_transfer_line dbtl on dbtl.bank_transfer_id = dbt.id
            left join (select string_agg(distinct(am.name), ', ') as sin, string_agg(distinct(aml.name), ', ') as name, av.number as number
                    from account_move am 
                    left join account_move_line aml on am.id = aml.move_id
                    left join account_voucher_line avl on aml.id = avl.move_line_id
                    left join account_voucher av on av.id = avl.voucher_id and left(av.number,3) in ('SPA') 
                    where left(am.name,3) in ('SIN') and av.ibanking_id is not null and av.state not in ('cancel')
                    and av.branch_id in %s
                    group by av.number) avl_spa on avl_spa.number = av.number
            left join dym_branch db on ib.branch_id = db.id
            left join dym_branch db_dbt on db_dbt.id = dbt.inter_branch_id
            left join res_partner rp on rp.id = av.partner_id
            left join account_journal aj on ib.payment_from_id = aj.id
            left join account_account ac on ac.id = aj.default_debit_account_id
            left join account_analytic_account acc_spa_1 on acc_spa_1.id = av.analytic_1
            left join account_analytic_account acc_spa_2 on acc_spa_2.id = av.analytic_2
            left join account_analytic_account acc_spa_3 on acc_spa_3.id = av.analytic_3
            left join account_analytic_account acc_spa_4 on acc_spa_4.id = av.analytic_4
            left join account_analytic_account acc_dbt_1 on acc_dbt_1.id = dbt.analytic_1
            left join account_analytic_account acc_dbt_2 on acc_dbt_2.id = dbt.analytic_2
            left join account_analytic_account acc_dbt_3 on acc_dbt_3.id = dbt.analytic_3
            left join account_analytic_account acc_dbt_4 on acc_dbt_4.id = dbt.analytic_4
            where ib.state not in ('cancel') and ib.kode_transaksi not in ('RTG')
            and (left(av.number,3) = 'SPA' or left(dbt.name,3) = 'BTR')
            """ % str(tuple(branch_ids)).replace(',)', ')')

        query_bank_bookunpaid_projection1 =""" 
            union all

            --Supplier Payment
            select distinct av.id as id,
                db.name as branch_name,
                av.due_date_payment as date,
                case when rp.name is null then '' else rp.name end as partner_name,
                '' as finance_company,
                ac.code as account_code2,
                ac.name as account_name2,
                avl.name as name,
                case when av.cheque_giro_number::text is not null then dcg.name else null end as cheque_giro_number,
                case when av.number is null then '' else av.number end as ref,
                0 as debit,
                av.amount as credit,
                acc_spa_1.code || '/' || acc_spa_2.code || '/' || acc_spa_3.code || '/' || acc_spa_4.code as analytic_combination,
                acc_spa_1.code as analytic_1,
                acc_spa_2.code as analytic_2,
                acc_spa_3.code as analytic_3,
                acc_spa_4.code as analytic_4,
                case when av.state = 'posted' then 'Posted'
                    else case when av.state = 'draft' then 'Draft'
                    else case when av.state = 'cancel' then 'Cancelled'
                    else case when av.state = 'request_approval' then 'RFA'
                    else case when av.state = 'approved' then 'Approve'
                    else case when av.state = 'confirmed' then 'Waiting Approval'
                    else case when av.state = 'waiting_for_approval' then 'Waiting Approval'
                else av.state end end end end end end end as state,
                case when av.payment_method = 'cheque' then 'Cheque'
                    else case when av.payment_method = 'auto_debit' then 'Auto Debit'
                    else case when av.payment_method = 'giro' then 'Giro'
                    else case when av.payment_method is null then 'Auto Debit (Kosong)'
                end end end end as btr_type,
                av.state as state_ib_dcg
            from account_voucher av 
            left join account_voucher_line avl on av.id = avl.voucher_id
            left join dym_branch db on av.branch_id = db.id
            left join res_partner rp on rp.id = av.partner_id
            left join dym_checkgyro_line dcg on dcg.id = av.cheque_giro_number
            left join account_journal aj on av.journal_id = aj.id
            left join account_account ac on ac.id = aj.default_debit_account_id
            left join account_analytic_account acc_spa_1 on acc_spa_1.id = av.analytic_1
            left join account_analytic_account acc_spa_2 on acc_spa_2.id = av.analytic_2
            left join account_analytic_account acc_spa_3 on acc_spa_3.id = av.analytic_3
            left join account_analytic_account acc_spa_4 on acc_spa_4.id = av.analytic_4
            where (av.payment_method not in ('internet_banking') or av.payment_method is null)
            and av.state not in ('cancel','draft','waiting_for_approval','request_approval','confirmed') 
            --and (left(av.number,5) != 'SPA-W' and left(number,3)='SPA')
            and left(number,3)='SPA'
            """

        query_bank_bookunpaid_projection2 = """
        union all

        select  dbt.id as id, 
                db.name as branch_name,
                dbt.date as date, 
                --case when rp.name is null then db_dbt.name else rp.name end as partner_name,
                db_dbt.name as partner_name,
                '' as finance_company,
                ac.code as account_code2,
                ac.name as account_name2,
                dbt.description || '(' || db_dbt.name || ')' as name,
                ib.name as cheque_giro_number,
                dbt.name as ref, 
                0 as debit,
                dbtl.amount as credit,
                acc_dbt_1.code || '/' || acc_dbt_2.code || '/' || acc_dbt_3.code || '/' || acc_dbt_4.code as analytic_combination,
                acc_dbt_1.code as analytic_1,
                acc_dbt_2.code as analytic_2,
                acc_dbt_3.code as analytic_3,
                acc_dbt_4.code as analytic_4,
                case when dbt.state = 'approved' then 'Done'
                    else case when dbt.state = 'draft' then 'Draft'
                    else case when dbt.state = 'cancel' then 'Cancel'
                    else case when dbt.state = 'appreceived' then 'Received'
                    else case when dbt.state = 'appapprove' then 'Process Done'
                    else case when dbt.state = 'confirmed' then 'Waiting Approval'
                    else case when dbt.state = 'waiting_for_approval' then 'Payment in Process'
                    else case when dbt.state = 'waiting_for_confirm_received' then 'Waiting For Confirm Received'
                    else dbt.state end end end end end end end end as state,
                case when dbt.transaction_type = 'ho2branch' then 'HO to Branch' else '' end as btr_type,
                ib.state as state_ib_dcg
            From dym_bank_transfer dbt
            left join dym_bank_transfer_line dbtl on dbtl.bank_transfer_id = dbt.id
            left join dym_ibanking ib on dbt.ibanking_id = ib.id and dbt.state not in ('cancel')
            left join account_journal aj on dbt.payment_from_id_ho2branch = aj.id
            left join dym_branch db on dbt.branch_id = db.id
            left join dym_branch db_dbt on db_dbt.id = dbt.inter_branch_id
            left join account_account ac on ac.id = aj.default_debit_account_id
            left join account_analytic_account acc_dbt_1 on acc_dbt_1.id = dbt.analytic_1
            left join account_analytic_account acc_dbt_2 on acc_dbt_2.id = dbt.analytic_2
            left join account_analytic_account acc_dbt_3 on acc_dbt_3.id = dbt.analytic_3
            left join account_analytic_account acc_dbt_4 on acc_dbt_4.id = dbt.analytic_4
            where 
            dbt.state not in ('draft','waiting_for_approval','cancel') 
            and dbt.payment_method in ('giro','cheque','single_payment','auto_debit','internet_banking')
            and dbt.branch_id not IN (328)
            and dbt.payment_from_id_ho2branch is not null
            """

        query_bank_bookunpaid = """
            --IBanking
            select  ib.id as id,
                db.name as branch_name,
                ib.date as date,
                case when rp.name is null then db_dbt.name else rp.name end as partner_name,
                '' as finance_company,
                ac.code as account_code2,
                ac.name as account_name2,
                case when dbt.description is not null then dbt.description || '(' || db_dbt.name || ')' else avl_spa.name end as name,
                ib.name as cheque_giro_number,
                case when av.number is null then dbt.name else av.number end as ref,
                --dbt.name as ref,
                0 as debit,
                case when av.amount is null then dbtl.amount else av.amount end as credit,
                --dbtl.amount as credit,
                case when acc_spa_1.code is null then acc_dbt_1.code || '/' || acc_dbt_2.code || '/' || acc_dbt_3.code || '/' || acc_dbt_4.code else acc_spa_1.code || '/' || acc_spa_2.code || '/' || acc_spa_3.code || '/' || acc_spa_4.code end as analytic_combination,
                case when acc_spa_1.code is null then acc_dbt_1.code else acc_spa_1.code end as analytic_1,
                case when acc_spa_2.code is null then acc_dbt_2.code else acc_spa_2.code end as analytic_2,
                case when acc_spa_3.code is null then acc_dbt_3.code else acc_spa_3.code end as analytic_3,
                case when acc_spa_4.code is null then acc_dbt_4.code else acc_spa_4.code end as analytic_4,
                case when av.state is null then (case when dbt.state = 'approved' then 'Done'
                        else case when dbt.state = 'draft' then 'Draft'
                        else case when dbt.state = 'cancel' then 'Cancel'
                        else case when dbt.state = 'appreceived' then 'Received'
                        else case when dbt.state = 'appapprove' then 'Process Done'
                        else case when dbt.state = 'confirmed' then 'Waiting Approval'
                        else case when dbt.state = 'waiting_for_approval' then 'Payment in Process'
                        else case when dbt.state = 'waiting_for_confirm_received' then 'Waiting For Confirm Received'
                        else dbt.state end end end end end end end end )
                else (case when av.state = 'posted' then 'Posted'
                        else case when av.state = 'draft' then 'Draft'
                        else case when av.state = 'cancel' then 'Cancelled'
                        else case when av.state = 'request_approval' then 'RFA'
                        else case when av.state = 'approved' then 'Approve'
                        else case when av.state = 'confirmed' then 'Waiting Approval'
                        else case when av.state = 'waiting_for_approval' then 'Waiting Approval'
                    else av.state end end end end end end end)
                end as state,
                --dbt.name as "No BTR",
                --dbt.date as "Date BTR",
                --dbt.amount as "Amount BTR",
                --dbt.state as "State BTR",
                --dbt.payment_method as "Payment Method BTR"
                case when dbt.transaction_type = 'ho2branch' then 'HO to Branch' else '' end as btr_type,
                ib.state as state_ib_dcg
            from    dym_ibanking ib
            left join account_voucher av on av.ibanking_id = ib.id and av.state not in ('posted','cancel') --and left(av.number,5) != 'SPA-W' 
            left join dym_bank_transfer dbt on dbt.ibanking_id = ib.id and dbt.state not in ('approved','cancel','draft')
            left join dym_bank_transfer_line dbtl on dbtl.bank_transfer_id = dbt.id
            left join (select string_agg(distinct(am.name), ', ') as sin, string_agg(distinct(aml.name), ', ') as name, av.number as number
                    from account_move am 
                    left join account_move_line aml on am.id = aml.move_id
                    left join account_voucher_line avl on aml.id = avl.move_line_id
                    left join account_voucher av on av.id = avl.voucher_id and left(av.number,3) in ('SPA') 
                    where left(am.name,3) in ('SIN') and av.ibanking_id is not null and av.state not in ('cancel')
                    and av.branch_id in %s
                    group by av.number) avl_spa on avl_spa.number = av.number
            left join dym_branch db on ib.branch_id = db.id
            left join dym_branch db_dbt on db_dbt.id = dbt.inter_branch_id
            left join res_partner rp on rp.id = av.partner_id
            left join account_journal aj on ib.payment_from_id = aj.id
            left join account_account ac on ac.id = aj.default_debit_account_id
            left join account_analytic_account acc_spa_1 on acc_spa_1.id = av.analytic_1
            left join account_analytic_account acc_spa_2 on acc_spa_2.id = av.analytic_2
            left join account_analytic_account acc_spa_3 on acc_spa_3.id = av.analytic_3
            left join account_analytic_account acc_spa_4 on acc_spa_4.id = av.analytic_4
            left join account_analytic_account acc_dbt_1 on acc_dbt_1.id = dbt.analytic_1
            left join account_analytic_account acc_dbt_2 on acc_dbt_2.id = dbt.analytic_2
            left join account_analytic_account acc_dbt_3 on acc_dbt_3.id = dbt.analytic_3
            left join account_analytic_account acc_dbt_4 on acc_dbt_4.id = dbt.analytic_4
            where ib.state not in ('done','cancel') and ib.kode_transaksi not in ('RTG')
            and (left(av.number,3) = 'SPA' or left(dbt.name,3) = 'BTR')
            """ % str(tuple(branch_ids)).replace(',)', ')')

        query_bank_bookunpaid1 = """

            union all
            --Supplier Payment
            select distinct  av.id as id,
                db.name as branch_name,
                av.due_date_payment as date,
                case when rp.name is null then '' else rp.name end as partner_name,
                '' as finance_company,
                ac.code as account_code2,
                ac.name as account_name2,
                avl.name as name,
                case when av.cheque_giro_number::text is not null then dcg.name else null end as cheque_giro_number,
                case when av.number is null then '' else av.number end as ref,
                0 as debit,
                av.amount as credit,
                acc_spa_1.code || '/' || acc_spa_2.code || '/' || acc_spa_3.code || '/' || acc_spa_4.code as analytic_combination,
                acc_spa_1.code as analytic_1,
                acc_spa_2.code as analytic_2,
                acc_spa_3.code as analytic_3,
                acc_spa_4.code as analytic_4,
                case when av.state = 'posted' then 'Posted'
                    else case when av.state = 'draft' then 'Draft'
                    else case when av.state = 'cancel' then 'Cancelled'
                    else case when av.state = 'request_approval' then 'RFA'
                    else case when av.state = 'approved' then 'Approve'
                    else case when av.state = 'confirmed' then 'Waiting Approval'
                    else case when av.state = 'waiting_for_approval' then 'Waiting Approval'
                else av.state end end end end end end end as state,
                case when av.payment_method = 'cheque' then 'Cheque'
                    else case when av.payment_method = 'auto_debit' then 'Auto Debit'
                    else case when av.payment_method = 'giro' then 'Giro'
                    else case when av.payment_method is null then 'Auto Debit (Kosong)'
                end end end end as btr_type,
                av.state as state_ib_dcg
            from account_voucher av 
            left join account_voucher_line avl on av.id = avl.voucher_id
            left join dym_branch db on av.branch_id = db.id
            left join res_partner rp on rp.id = av.partner_id
            left join dym_checkgyro_line dcg on dcg.id = av.cheque_giro_number
            left join account_journal aj on av.journal_id = aj.id
            left join account_account ac on ac.id = aj.default_debit_account_id
            left join account_analytic_account acc_spa_1 on acc_spa_1.id = av.analytic_1
            left join account_analytic_account acc_spa_2 on acc_spa_2.id = av.analytic_2
            left join account_analytic_account acc_spa_3 on acc_spa_3.id = av.analytic_3
            left join account_analytic_account acc_spa_4 on acc_spa_4.id = av.analytic_4
            where (av.payment_method not in ('internet_banking') or av.payment_method is null)
            and av.state not in ('cancel','draft','waiting_for_approval','request_approval','confirmed','posted') 
            --and (left(av.number,5) != 'SPA-W' and left(number,3)='SPA')
            and left(number,3)='SPA'
            """

        query_bank_bookunpaid2 = """
        union all

        select  dbt.id as id, 
                db.name as branch_name,
                dbt.date as date, 
                --case when rp.name is null then db_dbt.name else rp.name end as partner_name,
                db_dbt.name as partner_name,
                '' as finance_company,
                ac.code as account_code2,
                ac.name as account_name2,
                dbt.description || '(' || db_dbt.name || ')' as name,
                ib.name as cheque_giro_number,
                dbt.name as ref, 
                0 as debit,
                dbtl.amount as credit,
                acc_dbt_1.code || '/' || acc_dbt_2.code || '/' || acc_dbt_3.code || '/' || acc_dbt_4.code as analytic_combination,
                acc_dbt_1.code as analytic_1,
                acc_dbt_2.code as analytic_2,
                acc_dbt_3.code as analytic_3,
                acc_dbt_4.code as analytic_4,
                case when dbt.state = 'approved' then 'Done'
                    else case when dbt.state = 'draft' then 'Draft'
                    else case when dbt.state = 'cancel' then 'Cancel'
                    else case when dbt.state = 'appreceived' then 'Received'
                    else case when dbt.state = 'appapprove' then 'Process Done'
                    else case when dbt.state = 'confirmed' then 'Waiting Approval'
                    else case when dbt.state = 'waiting_for_approval' then 'Payment in Process'
                    else case when dbt.state = 'waiting_for_confirm_received' then 'Waiting For Confirm Received'
                    else dbt.state end end end end end end end end as state,
                case when dbt.transaction_type = 'ho2branch' then 'HO to Branch' else '' end as btr_type,
                ib.state as state_ib_dcg
            From dym_bank_transfer dbt
            left join dym_bank_transfer_line dbtl on dbtl.bank_transfer_id = dbt.id
            left join dym_ibanking ib on dbt.ibanking_id = ib.id and dbt.state not in ('cancel')
            left join account_journal aj on dbt.payment_from_id_ho2branch = aj.id
            left join dym_branch db on dbt.branch_id = db.id
            left join dym_branch db_dbt on db_dbt.id = dbt.inter_branch_id
            left join account_account ac on ac.id = aj.default_debit_account_id
            left join account_analytic_account acc_dbt_1 on acc_dbt_1.id = dbt.analytic_1
            left join account_analytic_account acc_dbt_2 on acc_dbt_2.id = dbt.analytic_2
            left join account_analytic_account acc_dbt_3 on acc_dbt_3.id = dbt.analytic_3
            left join account_analytic_account acc_dbt_4 on acc_dbt_4.id = dbt.analytic_4
            where 
            dbt.state not in ('draft','waiting_for_approval','cancel','approved','app_received','app_approve','waiting_for_confirm_received') 
            and dbt.payment_method in ('giro','cheque','single_payment','auto_debit','internet_banking')
            and dbt.branch_id not IN (328)
            and dbt.payment_from_id_ho2branch is not null
            """
        
        query_end_av=""
        if branch_ids :
            query_end_av +=" AND av.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')

        where_end_dcg=""
        if branch_ids :
            where_end_dcg +=" AND av.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if journal_id :
            where_end_dcg +=" AND av.journal_id in %s" % str(
                tuple(journal_ids)).replace(',)', ')')
        if start_value_date:
            where_end_dcg += " and av.due_date_payment >= '%s' " % start_value_date
        if end_value_date:
            where_end_dcg += " and av.due_date_payment <= '%s' " % end_value_date
    
        where_end_ibk=""
        if branch_ids :
            where_end_ibk +=" AND ib.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if journal_id :
            where_end_ibk+=" AND ib.payment_from_id in %s" % str(
                tuple(journal_ids)).replace(',)', ')')
        if start_value_date:
            where_end_ibk += " and ib.date >= '%s' " % start_value_date
        if end_value_date:
            where_end_ibk += " and ib.date <= '%s' " % end_value_date

        where_end_ibk_additional=""
        if branch_ids :
            where_end_ibk_additional +=" AND dbt.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if journal_id :
            where_end_ibk_additional+=" AND dbt.payment_from_id_ho2branch in %s" % str(
                tuple(journal_ids)).replace(',)', ')')
        if start_value_date:
            where_end_ibk_additional += " and dbt.date >= '%s' " % start_value_date
        if end_value_date:
            where_end_ibk_additional += " and dbt.date <= '%s' " % end_value_date

        query_order = " order by 2,3,10"

        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        reports = [report_bank_bookunpaid]
        for report in reports:
            if data['projection'] and data['unpaid']:
                a = cr.execute(query_bank_bookunpaid_projection + where_end_ibk + query_bank_bookunpaid_projection1 + where_end_dcg + query_bank_bookunpaid_projection2 + where_end_ibk_additional + query_order)
                print query_bank_bookunpaid_projection + where_end_ibk + query_bank_bookunpaid_projection1 + where_end_dcg + query_bank_bookunpaid_projection2 + where_end_ibk_additional + query_order
            elif data['unpaid']:
                a = cr.execute(query_bank_bookunpaid + where_end_ibk + query_bank_bookunpaid1 + where_end_dcg + query_bank_bookunpaid2 + where_end_ibk_additional + query_order)
                print query_bank_bookunpaid + where_end_ibk + query_bank_bookunpaid1 + where_end_dcg + query_bank_bookunpaid2 + where_end_ibk_additional + query_order
            all_lines = cr.dictfetchall()
            
            move_lines = []            

            p_map = ()
            if all_lines:
                p_map = map(
                    lambda x: {
                        'no':0,
                        'id': x['id'],
                        # 'account_id': x['account_id'],
                        'branch_name':x['branch_name'],
                        'date': x['date'],  
                        'state_ib_dcg': x['state_ib_dcg'],
                        'partner_name': x['partner_name'],
                        'finance_company': x['finance_company'],
                        'account_code2': x['account_code2'],
                        'account_name2': x['account_name2'],
                        'name': x['name'],
                        'cheque_giro_number': x['cheque_giro_number'],
                        'ref': x['ref'],
                        'debit': x['debit'],
                        'credit': x['credit'],
                        'analytic_combination': x['analytic_combination'],
                        'analytic_1': x['analytic_1'],
                        'analytic_2': x['analytic_2'],
                        'analytic_3': x['analytic_3'],
                        'analytic_4': x['analytic_4'],
                        'state': x['state'],
                        'btr_type': x['btr_type']
                    },
                    all_lines)

            reports = [{
                'title_short': 'BankBookUnpaid', 
                'id': p_map, 
                'title': ''
            }]
        #     report.update({'move_lines': all_lines})
        # reports = filter(lambda x: x.get('move_lines'), reports)

        if not reports:
            reports = [{
                'type': 'BankBook',
                'title': '',
                'title_short': title_short_prefix + ', ' + _(' '.join(['LAPORAN BANK BOOK','(PROYEKSI)' if data['projection'] else ''])),
                # 'saldo_awal': saldo_awal,
                'start_date': start_value_date,
                'end_date': end_value_date,
                'move_lines': [{
                    'no':0,
                    'branch_status': 'NO DATA FOUND',
                    'branch_name': 'NO DATA FOUND',
                    'account_code2': 'NO DATA FOUND',
                    'account_name2': 'NO DATA FOUND',
                    'btr_type': 'NO DATA FOUND',
                    'partner_name':'NO DATA FOUND',
                    'finance_company':'NO DATA FOUND',
                    'name': 0,
                    'cheque_giro_number':'NO DATA FOUND',
                    'ref': 0,
                    'date': 'NO DATA FOUND',
                    'state_ib_dcg': 'NO DATA FOUND',
                    'value_date': 'NO DATA FOUND',
                    'debit': 0.0,
                    'credit':  0.0,
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
        super(dym_bank_bookunpaid_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_bank_bookunpaid_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_account_move.report_bank_bookunpaid'
    _inherit = 'report.abstract_report'
    _template = 'dym_account_move.report_bank_bookunpaid'
    _wrapped_report_class = dym_bank_bookunpaid_report_print