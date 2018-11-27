from datetime import datetime, timedelta, date
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_piutang_pajak_progresif_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_piutang_pajak_progresif_print, self).__init__(
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
            'finance_company': '',
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
        
        report_piutang_pajak_progresif = {
            'per_tgl': datetime.date(datetime.strptime(per_tgl, '%Y-%m-%d')),
            'detail_pembayaran': detail_pembayaran,
            'type': 'receivable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Piutang Pajak Progresif')}

        query_per_tgl = " 1=1 "
        query_per_tgly = " 1=1 "
        if per_tgl :
            query_per_tgl = ("((REPLACE(am2.model, '.', '' ) = 'accountvoucher' and av.value_date is not null and av.value_date <= '%s')  OR (REPLACE(am2.model, '.', '' ) = 'accountvoucher' and av.value_date is null and av.date is not null and av.date <= '%s') OR (REPLACE(am2.model, '.', '' ) = 'accountvoucher' and av.value_date is null and av.date is null and aml2.date <= '%s') OR (REPLACE(am2.model, '.', '' ) != 'accountvoucher' and (aml2.date is not null and aml2.date <= '%s')))") % (str(per_tgl), str(per_tgl), str(per_tgl), str(per_tgl))
            query_per_tgly = ("((REPLACE(am2y.model, '.', '' ) = 'accountvoucher' and avy.value_date is not null and avy.value_date <= '%s')  OR (REPLACE(am2y.model, '.', '' ) = 'accountvoucher' and avy.value_date is null and avy.date is not null and avy.date <= '%s') OR (REPLACE(am2y.model, '.', '' ) = 'accountvoucher' and avy.value_date is null and avy.date is null and aml2y.date <= '%s') OR (REPLACE(am2y.model, '.', '' ) != 'accountvoucher' and (aml2y.date is not null and aml2y.date <= '%s')))") % (str(per_tgl), str(per_tgl), str(per_tgl), str(per_tgl))

        aml_date_start = " 1=1 "
        aml_saldo_awal = " 1=1 "
        aml_saldo_awalz = " 1=1 "
        if start_date :
            aml_date_start +=" AND aml_date.date >= '%s' " % str(start_date)
            aml_saldo_awal =("((REPLACE(am2x.model, '.', '' ) = 'accountvoucher' and avx.value_date is not null and avx.value_date < '%s')  OR (REPLACE(am2x.model, '.', '' ) = 'accountvoucher' and avx.value_date is null and avx.date is not null and avx.date < '%s') OR (REPLACE(am2x.model, '.', '' ) = 'accountvoucher' and avx.value_date is null and avx.date is null and aml2x.date < '%s') OR (REPLACE(am2x.model, '.', '' ) != 'accountvoucher' and (aml2x.date is not null and aml2x.date < '%s')))") % (str(start_date), str(start_date), str(start_date), str(start_date))
            aml_saldo_awalz =("((REPLACE(am2z.model, '.', '' ) = 'accountvoucher' and avz.value_date is not null and avz.value_date < '%s')  OR (REPLACE(am2z.model, '.', '' ) = 'accountvoucher' and avz.value_date is null and avz.date is not null and avz.date < '%s') OR (REPLACE(am2z.model, '.', '' ) = 'accountvoucher' and avz.value_date is null and avz.date is null and aml2z.date < '%s') OR (REPLACE(am2z.model, '.', '' ) != 'accountvoucher' and (aml2z.date is not null and aml2z.date < '%s')))") % (str(start_date), str(start_date), str(start_date), str(start_date))
        if end_date :
            aml_date_start +=" AND aml_date.date <= '%s' " % str(end_date)

        query_start = "SELECT aml.id as id_aml, " \
            "aml.division as division, " \
            "COALESCE(dcp.name,'') as cabang_partner, " \
            "COALESCE(dso.customer_dp,0) as piutang_jpnett, " \
            "CASE WHEN dso.is_cod = TRUE THEN 'COD' " \
            "    ELSE 'Reguler' " \
            "END as payment_type, " \
            "rp.default_code as partner_code, " \
            "rp.name as partner_name, " \
            "a.code as account_code, " \
            "'' as account_sap, " \
            "aml.date as date_aml, " \
            "aml.date_maturity as due_date, " \
            "'" + str(per_tgl) + "' - aml.date_maturity as overdue, " \
            "aml.reconcile_id as status, " \
            "aml.reconcile_partial_id as partial, " \
            "aml.debit as debit, " \
            "aml.credit as credit, " \
            "aml.name as name, " \
            "aml.ref as reference, " \
            "fc.name as finance_company, " \
            "j.name as journal_name, " \
            "m.name as invoice_name, " \
            "CASE WHEN j.type!='situation' THEN 0.0 " \
            "   WHEN j.type='situation' THEN " \
            "       CASE WHEN aml.reconcile_id IS NOT NULL and aml3z.count_debit < 1 THEN 0.0 " \
            "           WHEN aml.reconcile_id IS NOT NULL THEN (aml3z.debit - aml3z.credit) / aml3z.count_debit " \
            "           WHEN aml.reconcile_partial_id IS NULL THEN aml.debit - aml.credit " \
            "           WHEN aml.reconcile_partial_id IS NOT NULL and aml3x.count_debit < 1 THEN 0.0 " \
            "           ELSE (aml3x.debit - aml3x.credit) / aml3x.count_debit " \
            "       END " \
            "END as saldo_awal, "\
            "CASE WHEN aml.reconcile_id IS NOT NULL and aml3y.count_debit < 1 THEN 0.0 " \
            "    WHEN aml.reconcile_id IS NOT NULL THEN (aml3y.debit - aml3y.credit) / aml3y.count_debit " \
            "    WHEN aml.reconcile_partial_id IS NULL THEN aml.debit - aml.credit " \
            "    WHEN aml.reconcile_partial_id IS NOT NULL and aml3.count_debit < 1 THEN 0.0 " \
            "    ELSE (aml3.debit - aml3.credit) / aml3.count_debit " \
            "END as residual " \
            "FROM " \
            "account_move_line aml " \
            "LEFT JOIN (SELECT aml2.reconcile_partial_id, (select count(aml4.debit) from account_move_line aml4 where aml2.reconcile_partial_id = aml4.reconcile_partial_id and aml4.debit > 0) as count_debit, SUM(aml2.debit) as debit, SUM(aml2.credit) as credit FROM account_move_line aml2 LEFT JOIN account_move am2 on am2.id = aml2.move_id LEFT JOIN account_voucher av on av.move_id = am2.id WHERE aml2.reconcile_partial_id is not Null and "+query_per_tgl+" GROUP BY aml2.reconcile_partial_id) aml3 on aml.reconcile_partial_id = aml3.reconcile_partial_id " \
            "LEFT JOIN (SELECT aml2y.reconcile_id, (select count(aml4y.debit) from account_move_line aml4y where aml2y.reconcile_id = aml4y.reconcile_id and aml4y.debit > 0) as count_debit, SUM(aml2y.debit) as debit, SUM(aml2y.credit) as credit FROM account_move_line aml2y LEFT JOIN account_move am2y on am2y.id = aml2y.move_id LEFT JOIN account_voucher avy on avy.move_id = am2y.id WHERE aml2y.reconcile_id is not Null and "+query_per_tgly+" GROUP BY aml2y.reconcile_id) aml3y on aml.reconcile_id = aml3y.reconcile_id " \
            "LEFT JOIN (SELECT aml2x.reconcile_partial_id, (select count(aml4x.debit) from account_move_line aml4x where aml2x.reconcile_partial_id = aml4x.reconcile_partial_id and aml4x.debit > 0) as count_debit, SUM(aml2x.debit) as debit, SUM(aml2x.credit) as credit FROM account_move_line aml2x LEFT JOIN account_move am2x on am2x.id = aml2x.move_id LEFT JOIN account_voucher avx on avx.move_id = am2x.id WHERE aml2x.reconcile_partial_id is not Null and " + aml_saldo_awal + " GROUP BY aml2x.reconcile_partial_id) aml3x on aml.reconcile_partial_id = aml3x.reconcile_partial_id " \
            "LEFT JOIN (SELECT aml2z.reconcile_id, (select count(aml4z.debit) from account_move_line aml4z where aml2z.reconcile_id = aml4z.reconcile_id and aml4z.debit > 0) as count_debit, SUM(aml2z.debit) as debit, SUM(aml2z.credit) as credit FROM account_move_line aml2z LEFT JOIN account_move am2z on am2z.id = aml2z.move_id LEFT JOIN account_voucher avz on avz.move_id = am2z.id WHERE aml2z.reconcile_id is not Null and " + aml_saldo_awalz + " GROUP BY aml2z.reconcile_id) aml3z on aml.reconcile_id = aml3z.reconcile_id " \
            "LEFT JOIN account_move_line aml_date on (aml_date.reconcile_partial_id = aml.reconcile_partial_id OR aml_date.reconcile_id = aml.reconcile_id) AND aml_date.date <> aml.date and aml_date.date is not null AND "+aml_date_start+" " \
            "LEFT JOIN account_move m ON m.id = aml.move_id " \
            "LEFT JOIN res_partner rp ON rp.id = aml.partner_id " \
            "LEFT JOIN account_invoice inv ON m.id = inv.move_id " \
            "LEFT JOIN dealer_sale_order dso ON dso.name = inv.name " \
            "LEFT JOIN res_partner fc ON fc.id = dso.finco_id " \
            "LEFT JOIN account_account a ON a.id = aml.account_id " \
            "LEFT JOIN account_journal j ON j.id = aml.journal_id " \
            "LEFT JOIN dealer_spk spk ON spk.dealer_sale_order_id = dso.id " \
            "LEFT JOIN dym_cabang_partner dcp ON dcp.id = spk.partner_cabang " \
            "where 1=1 AND m.state = 'posted' "
            
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        query_end=""
        if division :
            query_end +=" AND aml.division = '%s'" % str(division)
        if start_date :
            query_end +=" AND (aml.date >= '%s' OR aml_date.id is not null)" % str(start_date)
        if end_date :
            query_end +=" AND (aml.date <= '%s' OR aml_date.id is not null)" % str(end_date)
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
        reports = [report_piutang_pajak_progresif]
        query_order = ""
        
        for report in reports:
            cr.execute(query_start + query_end + query_order)
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
                        'date_aml': str(x['date_aml']) if x['date_aml'] != None else '',
                        'due_date': str(x['due_date']) if x['due_date'] != None else '',
                        'overdue': str(x['overdue']) if x['overdue'] != None and x['residual'] != None else '',
                        'status': 'Outstanding' if str(x['status']) == 'None' else 'Reconciled',
                        'tot_invoice': x['debit'] - x['credit'],
                        'saldo_awal': x['saldo_awal'] if x['saldo_awal'] != None else False,
                        'amount_residual': x['residual'] if x['residual'] != None else False,
                        'current': (x['residual'] if x['residual'] != None else False) if x['overdue'] <= 0 or x['overdue'] == None else False,
                        'overdue_1_3': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 0 and x['overdue'] < 4 else False,
                        'overdue_4_7': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 3 and x['overdue'] < 8 else False,
                        'overdue_8_30': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 7 and x['overdue'] < 31 else False,
                        'overdue_31_60': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 30 and x['overdue'] < 61 else False,
                        'overdue_61_90': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 60 and x['overdue'] < 91 else False,
                        'overdue_91_n': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 90 else False,
                        'reference': str(x['reference'].encode('ascii','ignore').decode('ascii')) if x['reference'] != None else '',
                        'journal_name': str(x['journal_name'].encode('ascii','ignore').decode('ascii')) if x['journal_name'] != None else ''},
                        
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
                        if am.credit > 0 and not am.sudo().dym_loan_id:
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
                            ids_aml.append(p)
                            partial_lines = lines = self.pool.get('account.move.line').browse(cr, uid, [])
                            if am.sudo().reconcile_id:
                                lines |= am.sudo().reconcile_id.line_id
                            elif am.sudo().reconcile_partial_id:
                                lines |= am.sudo().reconcile_partial_id.line_partial_ids
                            partial_lines += am
                            payments = (lines - partial_lines).sorted().filtered(lambda r: (r.credit > 0 and not am.sudo().dym_loan_id) or (r.debit > 0 and am.sudo().dym_loan_id))
                            if payments and detail_pembayaran == True:
                                add_line = []
                                move_ids = []
                                for pay in payments:
                                    if pay.move_id.id in move_ids:
                                        continue
                                    move_ids.append(pay.move_id.id)
                                    voucher_id = self.pool.get('account.voucher').search(cr, uid, [('move_id','=',pay.move_id.id)])
                                    if voucher_id:
                                        bayar = 0
                                        pindahan = 0
                                        retur = 0
                                        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id)
                                        if not ((voucher.value_date and voucher.value_date <= str(per_tgl)) or (not voucher.value_date and voucher.date and voucher.date <= str(per_tgl)) or (not voucher.value_date and not voucher.date and pay.date <= str(per_tgl))):
                                            continue
                                        if voucher.amount != 0:
                                            bayar += voucher.amount
                                            pay_amount_res = self.get_pay_array(cr, uid, voucher.number, voucher.value_date if voucher.value_date else voucher.date, voucher.amount, 0, 0, account_move_lines)
                                            add_line.append(pay_amount_res)
                                        for voucher_line in voucher.line_ids.filtered(lambda r: r.type == 'dr' and r.amount > 0):
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
                                        if not (pay.date and pay.date <= str(per_tgl)):
                                            continue
                                        amount = pay.debit or pay.credit
                                        amount = amount if amount < p['tot_invoice'] else p['tot_invoice']
                                        pay_amount_res = self.get_pay_array(cr, uid, pay.move_id.name, pay.date, amount, 0, 0, account_move_lines)
                                        add_line.append(pay_amount_res)
                                if add_line:
                                    ids_aml += add_line

                report.update({'ids_aml': ids_aml})

        reports = filter(lambda x: x.get('ids_aml'), reports)
        
        if not reports :
            reports = [{'title_short': 'Laporan Piutang Pajak Progresif','type': 'receivable', 'ids_aml':
                            [{'reference': 'NO DATA FOUND',                                
                              'due_date': 'NO DATA FOUND',
                              'tot_invoice': 0,
                              'date_aml': 'NO DATA FOUND',
                              'partner_code': 'NO DATA FOUND',
                              'finance_company': 'NO DATA FOUND',
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
                              'overdue': 'NO DATA FOUND'}], 'title': '', 'detail_pembayaran': detail_pembayaran, 'per_tgl': datetime.date(datetime.strptime(per_tgl, '%Y-%m-%d')),}]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_piutang_pajak_progresif_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_piutang_pajak_progresif_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_piutang_pajak_progresif.report_piutang_pajak_progresif'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_piutang_pajak_progresif.report_piutang_pajak_progresif'
    _wrapped_report_class = dym_report_piutang_pajak_progresif_print
