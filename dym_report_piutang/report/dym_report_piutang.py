from datetime import datetime, timedelta, date
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT as DSDF
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_piutang_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_piutang_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def get_pay_array(self, cr, uid, pay_no, pay_date, pay_amount, pay_pindahan, pay_retur, account_move_lines):
        res = {
            'pay_no': pay_no,
            'pay_date': pay_date,
            'pay_amount': pay_amount,
            'pay_pindahan': pay_pindahan,
            'pay_retur': pay_retur,
            'no': '',
            'id_aml': '',
            'division': '',
            'partner_code': '',
            'partner_name': '',
            'cabang_partner': '',
            'piutang_jpnett': '',
            'finance_company': '',
            'finco_branch': '',
            'payment_type': '',
            'bill_date': '',
            'account_code': '',
            'invoice_name': '',
            'name': '',
            'date_aml': '',
            'due_date': '',
            'overdue': 0,
            'status': '',
            'tot_invoice': 0,
            'saldo_awal': 0,
            'amount_residual': 0,
            'current': 0,
            'overdue_1_3': 0,
            'overdue_4_7': 0,
            'overdue_8_30': 0,
            'overdue_31_60': 0,
            'overdue_61_90': 0,
            'overdue_91_n': 0,
            'reference': '',
            'journal_name': '',
            'lines': account_move_lines,
            'analytic_1': '',
            'analytic_2': '',
            'analytic_3': '',
            'analytic_4': '',
            'branch_id': '',
            'branch_status': '',
            'branch_name': '',
            'analytic_combination': '',
            'invoice_origin': '',
        }
        return res

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
        account_ids = data['account_ids']
        journal_ids = data['journal_ids']
        segmen = data['segmen']
        branch_status = data['branch_status']
        detail_pembayaran = data['detail_pembayaran']
        per_tgl = data['per_tgl']

        title_prefix = ''
        title_short_prefix = ''
        
        report_piutang = {
            'per_tgl': datetime.date(datetime.strptime(per_tgl, '%Y-%m-%d')),
            'detail_pembayaran': detail_pembayaran,
            'type': 'receivable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Piutang')}

        query_per_tgl = " 1=1 "
        query_per_tgly = " 1=1 "
        if per_tgl :
            query_per_tgl = ("((REPLACE(am2.model, '.', '' ) = 'accountvoucher' and av.value_date is not null and av.value_date <= '%s')  OR (REPLACE(am2.model, '.', '' ) = 'accountvoucher' and av.value_date is null and av.date is not null and av.date <= '%s') OR (REPLACE(am2.model, '.', '' ) = 'accountvoucher' and av.value_date is null and av.date is null and aml2.date <= '%s') OR (REPLACE(am2.model, '.', '' ) != 'accountvoucher' and (aml2.date is not null and aml2.date <= '%s')))") % (str(per_tgl), str(per_tgl), str(per_tgl), str(per_tgl))
            query_per_tgly = ("((REPLACE(am2y.model, '.', '' ) = 'accountvoucher' and avy.value_date is not null and avy.value_date <= '%s')  OR (REPLACE(am2y.model, '.', '' ) = 'accountvoucher' and avy.value_date is null and avy.date is not null and avy.date <= '%s') OR (REPLACE(am2y.model, '.', '' ) = 'accountvoucher' and avy.value_date is null and avy.date is null and aml2y.date <= '%s') OR (REPLACE(am2y.model, '.', '' ) != 'accountvoucher' and (aml2y.date is not null and aml2y.date <= '%s')))") % (str(per_tgl), str(per_tgl), str(per_tgl), str(per_tgl))

        aml_date_start = " 1=1 "
        aml_saldo_awal = " 1=1 "
        aml_saldo_awalz = " 1=1 "

        where_branch = " 1=1 "
        if branch_ids :
            branch_ids = branch_ids
            #where_branch = " b.id in %s " % str(
            where_branch = " aml.branch_id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
            where_branch2 = " branch_id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
        else :
            area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids_user = [b.id for b in area_user]
            branch_ids = branch_ids_user
            #where_branch = " b.id in %s " % str(
            where_branch = " aml.branch_id in %s " % str(
                tuple(branch_ids_user))
            where_branch2 = " branch_id in %s " % str(
                tuple(branch_ids_user))


        if start_date :
            aml_date_start +=" AND aml_date.date >= '%s' " % str(start_date)
            aml_saldo_awal =("((REPLACE(am2x.model, '.', '' ) = 'accountvoucher' and avx.value_date is not null and avx.value_date < '%s')  OR (REPLACE(am2x.model, '.', '' ) = 'accountvoucher' and avx.value_date is null and avx.date is not null and avx.date < '%s') OR (REPLACE(am2x.model, '.', '' ) = 'accountvoucher' and avx.value_date is null and avx.date is null and aml2x.date < '%s') OR (REPLACE(am2x.model, '.', '' ) != 'accountvoucher' and (aml2x.date is not null and aml2x.date < '%s')))") % (str(start_date), str(start_date), str(start_date), str(start_date))
            o_awalz =("((REPLACE(am2z.model, '.', '' ) = 'accountvoucher' and avz.value_date is not null and avz.value_date < '%s')  OR (REPLACE(am2z.model, '.', '' ) = 'accountvoucher' and avz.value_date is null and avz.date is not null and avz.date < '%s') OR (REPLACE(am2z.model, '.', '' ) = 'accountvoucher' and avz.value_date is null and avz.date is null and aml2z.date < '%s') OR (REPLACE(am2z.model, '.', '' ) != 'accountvoucher' and (aml2z.date is not null and aml2z.date < '%s')))") % (str(start_date), str(start_date), str(start_date), str(start_date))
        if end_date :
            aml_date_start +=" AND aml_date.date <= '%s' " % end_date
            start_date = datetime.strptime(end_date, DSDF).replace(day=1).strftime(DSDF)
            #print "ttttttttttttttttttttttttt",start_date

        query_start = """SELECT distinct  aml.id as id_aml,
            aml.division as division,
            COALESCE(dcp.name,'') as cabang_partner,
            COALESCE(dso.customer_dp,0) as piutang_jpnett,
            CASE WHEN dso.is_cod = TRUE THEN 'COD'
            ELSE CASE WHEN dso.is_pic = 't' THEN 'PIC' 
                ELSE 'Reguler'
            END END as payment_type,
            rp.default_code as partner_code,
            rp.name as partner_name,
            a.code as account_code,
            '' as account_sap,
            aml.date as date_aml,
            aml.date_maturity as due_date,
            CASE WHEN (CASE WHEN aml.reconcile_id IS NOT NULL then aml2.amount
		    WHEN aml.reconcile_partial_id IS NOT NULL then aml3.amount
		    WHEN aml.reconcile_id IS NULL AND aml.account_id in (2395)  then aml4.amount
		    WHEN aml.reconcile_id IS NULL then coalesce(avl2.amount,aml.debit-aml.credit)
            WHEN aml.reconcile_partial_id IS NULL THEN avl2.amount 
            ELSE 0
            END = 0)  THEN CASE WHEN (coalesce(av.date,'"""+ str(end_date) + """') - dso.date_order) + 1 > 0 THEN  (coalesce(av.date,'"""+ str(end_date) + """') - dso.date_order) + 1 ELSE 0 END ELSE ('"""+ str(end_date) + """' - dso.date_order) + 1 
            END  as overdue,
            CASE WHEN (CASE WHEN aml.reconcile_id IS NOT NULL then aml2.amount
		    WHEN aml.reconcile_partial_id IS NOT NULL then aml3.amount
		    WHEN aml.reconcile_id IS NULL AND aml.account_id in (2395)  then aml4.amount
		    WHEN aml.reconcile_id IS NULL then coalesce(avl2.amount,aml.debit-aml.credit)
            WHEN aml.reconcile_partial_id IS NULL THEN avl2.amount 
            ELSE 0
            END <> 0)  THEN CASE WHEN aml.date_maturity  <'"""+ str(end_date) + """' THEN  ('"""+ str(end_date) + """' - coalesce(aml.date_maturity ,aml.date))  + 1 ELSE 0 END ELSE 0
            END  as overdue2,
            aml.reconcile_id as status,
            aml.reconcile_partial_id as partial,
            aml.debit as debit,
            aml.credit as credit,
            aml.name as name,
            dso.date_order,
            aml.ref as reference,
            fc.name as finance_company,
            j.name as journal_name,
            m.name as invoice_name,
            CASE WHEN j.type!='situation' THEN 0.0
               WHEN j.type='situation' THEN
                   CASE WHEN aml.reconcile_id IS NULL  THEN avl2.amount
			WHEN aml.reconcile_partial_id IS NULL THEN avl2.amount
                   ELSE 0
                END
            END as saldo_awal, 

            CASE WHEN aml.reconcile_id IS NOT NULL  then aml2.amount
		    WHEN aml.reconcile_partial_id IS NOT NULL then aml3.amount
		    WHEN aml.reconcile_id IS NULL AND aml.account_id in (2395)  then aml4.amount
		    WHEN aml.reconcile_id IS NULL then coalesce(avl2.amount,aml.debit-aml.credit)
            WHEN aml.reconcile_partial_id IS NULL THEN avl2.amount 
            ELSE 0
            END as residual,
            dp.name finco_branch,
            dso.bill_date
            FROM
            account_move_line aml
            LEFT JOIN account_move m ON m.id = aml.move_id
            LEFT JOIN res_partner rp ON rp.id = aml.partner_id
            LEFT JOIN account_invoice inv ON m.id = inv.move_id
            LEFT JOIN dealer_sale_order dso ON dso.name = inv.name
            LEFT JOIN dym_cabang_partner dp ON  dso.finco_cabang =dp.id 
            LEFT JOIN res_partner fc ON fc.id = dso.finco_id
            LEFT JOIN account_account a ON a.id = aml.account_id
            LEFT JOIN account_journal j ON j.id = aml.journal_id
            LEFT JOIN dealer_spk spk ON spk.dealer_sale_order_id = dso.id
            LEFT JOIN dym_cabang_partner dcp ON dcp.id = spk.partner_cabang
            LEFT JOIN account_voucher_line avl on aml.id = avl.move_line_id
            LEFT JOIN account_voucher av ON avl.voucher_id = av.id  and ((av.date <= '"""+ str(end_date) + """') or av.date is null) 
            LEFT JOIN (select avl2.move_line_id,sum(avl2.amount) amount from account_voucher_line avl2,account_voucher av2  where
            avl2.voucher_id = av2.id  and av2.date <= '"""+ str(end_date) + """' group by avl2.move_line_id) avl2 on avl2.move_line_id = aml.id 
            --LEFT JOIN (select a.id ,sum(debit) amount from account_move_line a, account_move b where a.move_id = b.id and a.date <= '"""+ str(end_date) + """' group by a.id) aml2 on  avl.move_line_id =aml2.id
            LEFT JOIN account_voucher av2 on m.name = av2.number
            LEFT JOIN (select sum(debit- credit) amount,reconcile_id from account_move_line where date <= '"""+ str(end_date) + """' and state <> 'cancel'  and reconcile_id is not null group by reconcile_id) aml2 on aml.reconcile_id = aml2.reconcile_id
	        LEFT JOIN (select sum(debit- credit) amount,reconcile_partial_id from account_move_line where date <= '"""+ str(end_date) + """' and state <> 'cancel' group by reconcile_partial_id) aml3 on aml.reconcile_partial_id = aml3.reconcile_partial_id
            LEFT JOIN (select sum(debit- credit) amount,move_id from account_move_line where date <= '"""+ str(end_date) + """' and state <> 'cancel' and  account_id in (2395)  group by move_id) aml4 on aml.move_id = aml4.move_id
            where   aml.name <>'Piutang Dagang' AND aml.name <>'/ (Reversed)' AND m.state = 'posted'   AND (aml.date < '"""+ str(start_date) + """' ) AND aml.account_id in """+ (str(tuple(account_ids)).replace(',)', ')')) +"""
	        and
	        (CASE WHEN aml.reconcile_id IS NOT NULL  then aml2.amount
		    WHEN aml.reconcile_partial_id IS NOT NULL then aml3.amount
		    WHEN aml.reconcile_id IS NULL AND aml.account_id in (2395)  then aml4.amount
		    WHEN aml.reconcile_id IS NULL then coalesce(avl2.amount,aml.debit-aml.credit)
            WHEN aml.reconcile_partial_id IS NULL THEN avl2.amount 
            ELSE 0
            END >0 or av.date >='"""+ str(start_date) + """')  and ("""+ where_branch +""" or  aml.analytic_account_id in (select id from account_analytic_account where  """+ where_branch2 +""") )         """

        query_start2 = """ union all

            SELECT distinct  aml.id as id_aml,
            aml.division as division,
            COALESCE(dcp.name,'') as cabang_partner,
            COALESCE(dso.customer_dp,0) as piutang_jpnett,
            CASE WHEN dso.is_cod = TRUE THEN 'COD'
            ELSE CASE WHEN dso.is_pic = 't' THEN 'PIC'
                ELSE 'Reguler'
            END END as payment_type,
            rp.default_code as partner_code,
            rp.name as partner_name,
            a.code as account_code,
            '' as account_sap,
            aml.date as date_aml,
            aml.date_maturity as due_date,
            CASE WHEN (CASE WHEN aml.reconcile_id IS NOT NULL then aml2.amount
		    WHEN aml.reconcile_partial_id IS NOT NULL then aml3.amount
		    WHEN aml.reconcile_id IS NULL AND aml.account_id in (2395)  then aml4.amount
		    WHEN aml.reconcile_id IS NULL then coalesce(avl2.amount,aml.debit-aml.credit)
            WHEN aml.reconcile_partial_id IS NULL THEN avl2.amount
            ELSE 0
            END = 0)  THEN CASE WHEN (coalesce(av.date,'"""+ str(end_date) + """') - dso.date_order) + 1 > 0 THEN  (coalesce(av.date,'"""+ str(end_date) + """') - dso.date_order) + 1 ELSE 0 END ELSE ('"""+ str(end_date) + """' - dso.date_order) + 1
            END  as overdue,
            CASE WHEN (CASE WHEN aml.reconcile_id IS NOT NULL then aml2.amount
		    WHEN aml.reconcile_partial_id IS NOT NULL then aml3.amount
		    WHEN aml.reconcile_id IS NULL AND aml.account_id in (2395)  then aml4.amount
		    WHEN aml.reconcile_id IS NULL then coalesce(avl2.amount,aml.debit-aml.credit)
            WHEN aml.reconcile_partial_id IS NULL THEN avl2.amount
            ELSE 0
            END <> 0)  THEN CASE WHEN aml.date_maturity  <'"""+ str(end_date) + """' THEN  ('"""+ str(end_date) + """' - coalesce(aml.date_maturity ,aml.date))  + 1 ELSE 0 END ELSE 0
            END  as overdue2,
            aml.reconcile_id as status,
            aml.reconcile_partial_id as partial,
            aml.debit as debit,
            aml.credit as credit,
            aml.name as name,
            dso.date_order,
            aml.ref as reference,
            fc.name as finance_company,
            j.name as journal_name,
            m.name as invoice_name,
            CASE WHEN j.type!='situation' THEN 0.0
               WHEN j.type='situation' THEN
                   CASE WHEN aml.reconcile_id IS NULL  THEN avl2.amount
			WHEN aml.reconcile_partial_id IS NULL THEN avl2.amount
                   ELSE 0
                END
            END as saldo_awal,

            CASE WHEN aml.reconcile_id IS NOT NULL then  aml2.amount
		    WHEN aml.reconcile_partial_id IS NOT NULL then aml3.amount
		    WHEN aml.reconcile_id IS NULL AND aml.account_id in (2395)  then aml4.amount
		    WHEN aml.reconcile_id IS NULL then coalesce(avl2.amount,aml.debit-aml.credit)
            WHEN aml.reconcile_partial_id IS NULL THEN avl2.amount
            ELSE 0
            END as residual,
            dp.name finco_branch,
            dso.bill_date
            FROM
            account_move_line aml
            LEFT JOIN account_move m ON m.id = aml.move_id
            LEFT JOIN res_partner rp ON rp.id = aml.partner_id
            LEFT JOIN account_invoice inv ON m.id = inv.move_id
            LEFT JOIN dealer_sale_order dso ON dso.name = inv.name
            LEFT JOIN dym_cabang_partner dp ON  dso.finco_cabang =dp.id
            LEFT JOIN res_partner fc ON fc.id = dso.finco_id
            LEFT JOIN account_account a ON a.id = aml.account_id
            LEFT JOIN account_journal j ON j.id = aml.journal_id
            LEFT JOIN dealer_spk spk ON spk.dealer_sale_order_id = dso.id
            LEFT JOIN dym_cabang_partner dcp ON dcp.id = spk.partner_cabang
            LEFT JOIN account_voucher_line avl on aml.id = avl.move_line_id
            LEFT JOIN account_voucher av ON avl.voucher_id = av.id  and ((av.date >= '"""+ str(start_date) + """' and av.date <= '"""+ str(end_date) + """') or av.date is null)
            LEFT JOIN (select avl2.move_line_id,sum(avl2.amount) amount from account_voucher_line avl2,account_voucher av2  where
            avl2.voucher_id = av2.id  and av2.date >= '"""+ str(start_date) + """' and av2.date <= '"""+ str(end_date) + """'  and av2.state = 'posted'  group by avl2.move_line_id) avl2 on avl2.move_line_id = aml.id
            --LEFT JOIN (select a.id ,sum(debit) amount from account_move_line a, account_move b where a.move_id = b.id and a.date <= '"""+ str(end_date) + """' ) aml2 on  avl.move_line_id =aml2.id
            LEFT JOIN account_voucher av2 on m.name = av2.number
            LEFT JOIN (select sum(debit- credit) amount,reconcile_id from account_move_line where date >= '"""+ str(start_date) + """' and date <= '"""+ str(end_date) + """' and state <> 'cancel' and  reconcile_id is not null group by reconcile_id) aml2 on aml.reconcile_id = aml2.reconcile_id
	         LEFT JOIN (select sum(debit- credit) amount,reconcile_partial_id from account_move_line where date >= '"""+ str(start_date) + """' and date <= '"""+ str(end_date) + """' and state <> 'cancel' group by reconcile_partial_id) aml3 on aml.reconcile_partial_id = aml3.reconcile_partial_id
            LEFT JOIN (select sum(debit- credit) amount,move_id from account_move_line where date >= '"""+ str(start_date) + """' and date <= '"""+ str(end_date) + """' and state <> 'cancel' and  account_id in (2395)  group by move_id) aml4 on aml.move_id = aml4.move_id
            where   aml.name <>'Piutang Dagang' AND aml.name <>'/ (Reversed)' AND m.state = 'posted' and aml.date >= '"""+ str(start_date) + """' and aml.date <= '"""+ str(end_date) + """' and ("""+ where_branch +""" or  aml.analytic_account_id in (select id from account_analytic_account where  """+ where_branch2 +""") )         """

        move_selection = ""
        report_info = _('')
        move_selection += ""


        query_end=""
        if division :
            query_end +=" AND aml.division = '%s'" % str(division)
        #if start_date :
        #    query_end +=" AND (aml.date >= '%s' )" % str(start_date)
        #if end_date :
            #query_end +=" AND (aml.date <= '%s' )" % str(end_date)
            #print 'uuuuuuuuuuuuuuuuuuuuuuuuu',start_date
            #print 'yyyyyyyyyyyyyyyyyyyyyyyyyyyy',end_date
            #query_end += " AND (aml.date >= '%s')" % str(start_date) % " AND (aml.date <= '%s' )" % str(end_date)
        if status == 'reconciled' :
            query_end +=" AND aml.reconcile_id is not Null"
        elif status == 'outstanding' :
            query_end +=" AND aml.reconcile_id is Null"
        if partner_ids :
            query_end+=" AND aml.partner_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        if account_ids :
            query_end+=" AND aml.account_id in %s" % str(
                tuple(account_ids)).replace(',)', ')')
        if journal_ids :
            query_end+=" AND aml.journal_id in %s" % str(
                tuple(journal_ids)).replace(',)', ')')
        reports = [report_piutang]
        query_order = " order by 1 "


        for report in reports:
            #print query_start + query_end + query_start2 + query_end + query_order
            cr.execute(query_start + query_end + query_start2 + query_end + query_order)

            all_lines = cr.dictfetchall()
            ids_aml = []

            if all_lines:
                p_map = map(
                    lambda x: {

                        'piutang_jpnett' : x['piutang_jpnett'],
                        'payment_type': str(x['payment_type'].encode('ascii','ignore').decode('ascii')) if x['payment_type'] != None else '',
                        'cabang_partner': x['cabang_partner'],
                        'no': 0,
                        'id_aml': x['id_aml'] if x['id_aml'] != None else '',
                        'division': str(x['division'].encode('ascii','ignore').decode('ascii')) if x['division'] != None else '',
                        'partner_code': str(x['partner_code'].encode('ascii','ignore').decode('ascii')) if x['partner_code'] != None else '',
                        'partner_name': str(x['partner_name'].encode('ascii','ignore').decode('ascii')) if x['partner_name'] != None else '',
                        'finance_company': str(x['finance_company'].encode('ascii','ignore').decode('ascii')) if x['finance_company'] != None else '',
                        'account_code': str(x['account_code'].encode('ascii','ignore').decode('ascii')) if x['account_code'] != None else '',
                        'invoice_name': str(x['invoice_name'].encode('ascii','ignore').decode('ascii')) if x['invoice_name'] != None else '',
                        'name': str(x['name'].encode('ascii','ignore').decode('ascii')) if x['name'] != None else '',
                        'date_order': str(x['date_order']) if x['date_order'] != None else '',
                        'date_aml': str(x['date_aml']) if x['date_aml'] != None else '',
                        'due_date': str(x['due_date']) if x['due_date'] != None else '',
                        'overdue': str(x['overdue']) if x['overdue'] != None and x['residual'] != None else '',
                        'overdue2': str(x['overdue']) if x['overdue'] != None and x['residual'] != None else '',
                        'status': 'Outstanding' if str(x['status']) == 'None' else 'Reconciled',
                        'saldo_awal': x['debit'] - x['credit']  if str(x['date_aml']) < str(start_date) else 0,
                        'tot_invoice': x['debit'] - x['credit'] if str(x['date_aml'])>= str(start_date) else 0,
                        #'saldo_awal': x['saldo_awal'] if x['saldo_awal'] != None else False,
                        'amount_residual': x['residual'] if x['residual'] != None else False,
                        'current': (x['residual'] if x['residual'] != None else False) if x['overdue2'] <= 0 or x['overdue2'] == None else False,
                        'overdue_1_3': (x['residual'] if x['residual'] != None else False) if x['overdue2'] > 0 and x['overdue2'] < 4 else False,
                        'overdue_4_7': (x['residual'] if x['residual'] != None else False) if x['overdue2'] > 3 and x['overdue2'] < 8 else False,
                        'overdue_8_30': (x['residual'] if x['residual'] != None else False) if x['overdue2'] > 7 and x['overdue2'] < 31 else False,
                        'overdue_31_60': (x['residual'] if x['residual'] != None else False) if x['overdue2'] > 30 and x['overdue2'] < 61 else False,
                        'overdue_61_90': (x['residual'] if x['residual'] != None else False) if x['overdue2'] > 60 and x['overdue2'] < 91 else False,
                        'overdue_91_n': (x['residual'] if x['residual'] != None else False) if x['overdue2'] > 90 else False,
                        'reference': str(x['reference'].encode('ascii','ignore').decode('ascii')) if x['reference'] != None else '',
                        'journal_name': str(x['journal_name'].encode('ascii','ignore').decode('ascii')) if x['journal_name'] != None else '',
                        'finco_branch': x['finco_branch'],
                        'bill_date': str(x['bill_date']) if x['bill_date'] != None else '',
                        },
                        
                    all_lines)
                no = 0

                p_map = sorted(p_map, key=lambda k: k['invoice_name'])
                for p in p_map:


                    if p['id_aml'] not in map(
                            lambda x: x.get('id_aml', None), ids_aml):

                        account_move_lines = filter(
                            lambda x: x['id_aml'] == p['id_aml'], all_lines)

                        analytic_1 = ''
                        analytic_2 = ''
                        analytic_3 = ''
                        analytic_4 = ''
                        analytic_1_name = ''
                        analytic_2_name = ''
                        analytic_3_name = ''
                        analytic_4_name = ''
                        am = self.pool.get('account.move.line').browse(cr, uid, account_move_lines[0]['id_aml'])

                        if am.credit > 0 and not am.sudo().dym_loan_id :

                            continue

                        analytic = am.analytic_account_id or ''
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
                            if (branch and branch_ids and branch.id not in branch_ids) or (branch and branch_status and branch_status != branch.branch_status):
                                continue
                            analytic_2_branch = analytic_2
                            if analytic_2 in ['210','220','230']:
                                if branch_status_1 == 'H123':
                                    analytic_2_branch = analytic_2[:2] + '1'
                                elif branch_status_1 == 'H23':
                                    analytic_2_branch = analytic_2[:2] + '2'
                                else:
                                    analytic_2_branch = analytic_2
                            analytic_combination = analytic_1 + '/' + analytic_2_branch + '/' + analytic_3 + '/' + analytic_4
                            p.update({'lines': account_move_lines})
                            no += 1
                            p.update({'no': str(no)})
                            p.update({'analytic_1': analytic_1_name})
                            p.update({'analytic_2': analytic_2_name})
                            p.update({'analytic_3': analytic_3_name})
                            p.update({'analytic_4': analytic_4_name})
                            p.update({'branch_id': branch_id})
                            p.update({'branch_status': branch_status_1})
                            p.update({'branch_name': branch_name})
                            p.update({'analytic_combination': analytic_combination})
                            p.update({'pay_no': ''})
                            p.update({'pay_date': ''})
                            p.update({'pay_amount': 0})
                            p.update({'pay_pindahan': 0})
                            p.update({'pay_retur': 0})
                            origin = ''

                            if p['amount_residual'] > p['saldo_awal'] + p['tot_invoice']:
                                p.update({'amount_residual': p['saldo_awal'] + p['tot_invoice']})

                            if am.reconcile_id:
                                am_reconcile_ids = self.pool.get('account.move.line').search(cr, uid, [('reconcile_id','=',am.reconcile_id.id)])
                                am_reconcile = self.pool.get('account.move.line').browse(cr, uid, am_reconcile_ids)
                                origin = ', '.join(am_reconcile.sudo().mapped('invoice').mapped('number')) or ''
                            elif am.reconcile_partial_id:
                                am_reconcile_ids = self.pool.get('account.move.line').search(cr, uid, [('reconcile_partial_id','=',am.reconcile_partial_id.id)])
                                am_reconcile = self.pool.get('account.move.line').browse(cr, uid, am_reconcile_ids)
                                origin = ', '.join(am_reconcile.sudo().mapped('invoice').mapped('number')) or ''
                            if not origin and am.sudo().invoice:
                                origin = am.sudo().invoice.number
                            p.update({'invoice_origin': origin})
                            if p['invoice_origin'][:3]=="NJB":
                                p.update({'invoice_origin': p['invoice_name']})

                            ids_aml.append(p)
                            partial_lines = lines = self.pool.get('account.move.line').browse(cr, uid, [])

                            if am.sudo().reconcile_id:
                                lines |= am.sudo().reconcile_id.line_id

                            elif am.sudo().reconcile_partial_id:

                                lines |= am.sudo().reconcile_partial_id.line_partial_ids
                            partial_lines += am

                            payments = (lines - partial_lines).sorted().filtered(lambda r: (r.credit > 0 and r.date <= str(end_date) and r.ref[:3]!='WOR' and r.ref[:3]!='CDE') or (r.debit > 0 and r.date <= str(end_date) and r.ref[:3]!='WOR' and r.ref[:3]!='CDE'))
                            if payments and detail_pembayaran == True:
                                add_line = []
                                move_ids = []

                                for pay in payments:

                                    #print pay.move_id.name
                                    #if pay.move_id.id in move_ids:
                                    #    continue


                                    move_ids.append(pay.move_id.id)
                                    voucher_id = self.pool.get('account.voucher').search(cr, uid, [('move_id','=',pay.move_id.id)])

                                    #voucher_a = self.pool.get('account.voucher').search(cr, uid, [
                                    #    ('number', '=', pay.move_id.name)])
                                    #voucher_x = self.pool.get('account.voucher').browse(cr, uid, voucher_a)

                                    if str(division) == 'xxxxs' and voucher_id:
                                    #if voucher_id:
                                        bayar = 0
                                        pindahan = 0
                                        retur = 0
                                        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id)




                                        if voucher.amount != 0 and voucher.date <= str(end_date) and pay.date <= str(end_date)  :
                                            bayar += voucher.amount
                                            if voucher.amount == pay.credit:
                                                pay_amount_res = self.get_pay_array(cr, uid, voucher.number,  voucher.date, voucher.amount, 0, 0, account_move_lines)
                                            else:
                                                pay_amount_res = self.get_pay_array(cr, uid, voucher.number,  voucher.date, pay.credit, 0, 0, account_move_lines)

                                            add_line.append(pay_amount_res)
                                        #for voucher_line in voucher.line_ids.filtered(lambda r:  r.amount > 0):
                                        for voucher_line in voucher.line_ids.filtered(lambda r: r.type == 'dr' and r.amount > 0 ):
                                            hutang_lain_id = self.pool.get('account.voucher').search(cr, uid, [('move_id','=',voucher_line.move_line_id.move_id.id),('is_hutang_lain','=',True)])
                                      

                                            if hutang_lain_id:
                                                pindahan += voucher_line.amount
                                                pay_amount_res = self.get_pay_array(cr, uid, voucher_line.move_line_id.move_id.name, voucher.value_date if voucher.value_date else voucher.date, 0, voucher_line.amount, 0, account_move_lines)
       
                                                add_line.append(pay_amount_res)
                                            rj_name = voucher_line.move_line_id.sudo().invoice.origin or ''
                                            retur_jual_id = self.pool.get('dym.retur.jual').search(cr, uid, [('name','in',rj_name.split(' '))])
                                            if retur_jual_id:
                                                retur += voucher_line.amount
                                                pay_amount_res = self.get_pay_array(cr, uid, voucher_line.move_line_id.move_id.name, voucher.value_date if voucher.value_date else voucher.date, 0, 0, voucher_line.amount, account_move_lines)
                                                add_line.append(pay_amount_res)
                                            if not retur_jual_id and not hutang_lain_id:
                                                pindahan += voucher_line.amount
                                                pay_amount_res = self.get_pay_array(cr, uid, voucher_line.move_line_id.move_id.name, voucher.value_date if voucher.value_date else voucher.date, voucher_line.amount, 0, 0, account_move_lines)
                                                add_line.append(pay_amount_res)

                                    else:


                                        #if not (pay.date and pay.date <= str(end_date)) :  #and account_ids == '[2370]'):
                                        #    continue

                                        amount = -1 * pay.debit or pay.credit

                                        if amount > p['tot_invoice'] + p['saldo_awal'] :
                                            amount =  p['tot_invoice'] + p['saldo_awal']

                                        #print 'cccc', amount,'cccccc',pay.date ,'cccccccccccc', p['tot_invoice'],'cccccccccccc',p['saldo_awal']
                                        if pay.date < str(start_date) and  p['tot_invoice'] ==0:
                                            p.update({'saldo_awal': p['saldo_awal']- amount})

                                        if not (pay.date and pay.date >= str(start_date) and pay.date <= str(end_date)) :
                                            continue

                                        if pay.move_id.name[23:]=="(Reversed)":
                                            pay_amount_res = self.get_pay_array(cr, uid, pay.move_id.name, pay.date,-1*amount, 0, 0, account_move_lines)
                                            add_line.append(pay_amount_res)
                                        #elif voucher_x.state != 'cancel':

                                        elif pay.move_id.name[:3]=="CUI":
                                            pay_amount_res = self.get_pay_array(cr, uid, pay.move_id.name, pay.date, amount, 0,0, account_move_lines)
                                            add_line.append(pay_amount_res)

                                        else:
                                            pay_amount_res = self.get_pay_array(cr, uid, pay.move_id.name, pay.date, amount, 0, 0, account_move_lines)
                                            add_line.append(pay_amount_res)
                                        move_a = self.pool.get('account.move').search(cr, uid, [('reverse_from_id', '=', pay.move_id.id)])
                                        move_x = self.pool.get('account.move').browse(cr, uid, move_a)
                                        #print pay.move_id.id,move_x.id
                                        if move_x.id:

                                            move_rec = self.pool.get('account.move.line').search(cr, uid, [('move_id','=',move_x.id)])
                                            move_y = self.pool.get('account.move.line').browse(cr, uid, move_rec)
                                            for moves in move_y:
                                                if moves.analytic_account_id.id:
                                                    #print moves.analytic_account_id.id,'zzzz',pay.analytic_account_id.id
                                                    if moves.reconcile_id.id !=  pay.reconcile_id.id and moves.analytic_account_id.id ==pay.analytic_account_id.id :
                                                        if  move_x.date  >= str(start_date) and move_x.date  <= str(end_date):
                                                            pay_amount_res = self.get_pay_array(cr, uid, move_x.name, move_x.date,-1*amount, 0, 0, account_move_lines)
                                                            add_line.append(pay_amount_res)
                                                            p.update({'amount_residual':p['amount_residual'] + amount})

                                                            if p['overdue2'] <= 0:
                                                                p.update({'current': p['amount_residual']})

                                                            if p['overdue2'] > 0 and p['overdue2'] < 4:
                                                                p.update({'overdue_1_3':p['amount_residual']})

                                                            if p['overdue2'] > 3 and p['overdue2'] < 8:
                                                                p.update({'overdue_4_7':p['amount_residual']})

                                                            if p['overdue2'] > 7 and p['overdue2'] < 31:
                                                                p.update({'overdue_8_30':p['amount_residual']})

                                                            if p['overdue2'] > 30 and p['overdue2'] < 61:
                                                                p.update({'overdue_31_60':p['amount_residual']})

                                                            if p['overdue2'] > 60 and p['overdue2'] < 91:
                                                                p.update({'overdue_61_90':p['amount_residual']})

                                                            if p['overdue2'] > 90:
                                                                p.update({'overdue_91_n':p['amount_residual']})

                                                            move_rec2 = self.pool.get('account.move.line').search(cr, uid, [('reconcile_id', '=', moves.reconcile_id.id),('credit', '>',0)],limit = 1,order ='id desc')
                                                            move_y2 = self.pool.get('account.move.line').browse(cr, uid, move_rec2)
                                                            if move_y2.date >= str(start_date) and move_y2.date <= str(end_date):
                                                                pay_amount_res = self.get_pay_array(cr, uid,  move_y2.ref,  move_y2.date, amount, 0, 0, account_move_lines)
                                                                add_line.append(pay_amount_res)
                                                                p.update({'amount_residual': p['amount_residual'] - amount})

                                                                if p['overdue2'] <= 0:
                                                                    p.update({'current': p['amount_residual']})

                                                                if p['overdue2'] > 0 and p['overdue2'] < 4:
                                                                    p.update({'overdue_1_3': p['amount_residual']})

                                                                if p['overdue2'] > 3 and p['overdue2'] < 8:
                                                                    p.update({'overdue_4_7': p['amount_residual']})

                                                                if p['overdue2'] > 7 and p['overdue2'] < 31:
                                                                    p.update({'overdue_8_30': p['amount_residual']})

                                                                if p['overdue2'] > 30 and p['overdue2'] < 61:
                                                                    p.update({'overdue_31_60': p['amount_residual']})

                                                                if p['overdue2'] > 60 and p['overdue2'] < 91:
                                                                    p.update({'overdue_61_90': p['amount_residual']})

                                                                if p['overdue2'] > 90:
                                                                    p.update({'overdue_91_n': p['amount_residual']})

                                if add_line:
                                    ids_aml += add_line

                report.update({'ids_aml': ids_aml})

        reports = filter(lambda x: x.get('ids_aml'), reports)

        if not reports :
            reports = [{'title_short': 'Laporan Piutang','type': 'receivable', 'ids_aml':
                            [{'reference': 'NO DATA FOUND',                                
                              'due_date': 'NO DATA FOUND',
                              'tot_invoice': 0,
                              'date_aml': 'NO DATA FOUND',
                              'partner_code': 'NO DATA FOUND',
                              'finance_company': 'NO DATA FOUND',
                              'finco_branch': 'NO DATA FOUND',
                              'no': '',
                              'cabang_partner':'',
                              'branch_name': 'NO DATA FOUND',
                              'current': 0,
                              'overdue_91_n': 0,
                              'journal_name': 'NO DATA FOUND',
                              'overdue_61_90': 0,
                              'status': 'NO DATA FOUND',
                              'division': 'NO DATA FOUND',
                              'overdue_31_60': 0,
                              'partner_name': 'NO DATA FOUND',
                              'id_aml': 'NO DATA FOUND',
                              'invoice_origin': 'NO DATA FOUND',
                              'amount_residual': 0,
                              'saldo_awal': 0,
                              'overdue_1_3': 0,
                              'overdue_4_7': 0,
                              'overdue_8_30': 0,
                              'pay_no': 'NO DATA FOUND',
                              'pay_date': 'NO DATA FOUND',
                              'pay_amount': 0,
                              'pay_pindahan': 0,
                              'pay_retur': 0,
                              'name': 'NO DATA FOUND',
                              'invoice_name': 'NO DATA FOUND',
                              'account_code': 'NO DATA FOUND',
                              'analytic_1': 'NO DATA FOUND',
                              'analytic_2': 'NO DATA FOUND',
                              'analytic_3': 'NO DATA FOUND',
                              'analytic_4': 'NO DATA FOUND',
                              'analytic_combination': 'NO DATA FOUND',
                              'branch_status': 'NO DATA FOUND',
                              'piutang_jpnett' : 0,
                              'payment_type': 'NO DATA FOUND',
                              'bill_date': 'NO DATA FOUND',
                              'overdue': 'NO DATA FOUND'}], 'title': '', 'detail_pembayaran': detail_pembayaran, 'per_tgl': datetime.date(datetime.strptime(per_tgl, '%Y-%m-%d')),}]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        objects = False
        super(dym_report_piutang_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_piutang_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_piutang.report_piutang'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_piutang.report_piutang'
    _wrapped_report_class = dym_report_piutang_print
