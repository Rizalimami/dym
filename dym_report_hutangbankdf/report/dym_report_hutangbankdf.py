from datetime import datetime, timedelta, date
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_hutangbankdf_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_hutangbankdf_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def get_pay_array(self, cr, uid, pay_no, pay_date, pay_amount, pay_pindahan, pay_retur, account_move_lines):
        # print saldo_awal
        # print penambahan
        # print pay_amount
        res = {
            'pay_no': pay_no,
            'pay_date': pay_date,
            'pay_amount': pay_amount,
            'pay_pindahan': pay_pindahan,
            'pay_retur': pay_retur,
            'lines': account_move_lines,
            'reference': '',
            'acc_number': '',
            'tgl_retur': '',
            'payment_term': '',
            'no_retur': '',
            'total_retur': 0,
            'saldo_awal': 0,
            'bank': '',
            'an_rek': '',
            'supplier_invoice_number': '',
            'supplier_invoice_date': '',
            'tot_invoice': 0,
            'date_aml': '',
            'partner_code': '',
            'no': 0,
            'branch_code': '',
            'branch_name': '',
            'amount_residual': 0,
            'journal_name': '',
            'status': '',
            'division': '',
            'belum_jatuh_tempo': 0,
            'id_aml': '',
            'due_date': '',
            'overdue_31_60': 0,
            'partner_name': '',
            'overdue_1_30': 0,
            'overdue_61_90': 0,
            'overdue_91_n': 0,
            'invoice_name': 0,
            'md': '',
            'bunga': 0,
            'branch_inv': '',
            'name': '',
            'account_code': 0,
            'analytic_1': '',
            'analytic_2': '',
            'analytic_3': '',
            'analytic_4': '',
            'analytic_combination': '',
            'branch_status': '',
            'overdue': ''
        }
        # print res
        return res

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        division = data['division']
        start_date = data['start_date']
        end_date = data['end_date']
        trx_start_date = data['trx_start_date']
        trx_end_date = data['trx_end_date']
        status = data['status']
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        account_ids = data['account_ids']
        journal_ids = data['journal_ids']
        segmen = data['segmen']
        branch_status = data['branch_status']
        detail_pembayaran = data['detail_pembayaran']
        where_end_datex = "av.date  <=  '%s' " % trx_end_date
        title_prefix = ''
        title_short_prefix = ''
        
        report_hutang = {
            'detail_pembayaran': detail_pembayaran,
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Hutang Bank DF')}
        #print "-----------", '"""+ str(start_date) + """'
        query_start = """SELECT distinct aml.id as id_aml, 
           aml.division as division, 
           rp.default_code as partner_code, 
           rp.name as partner_name, 
           a.code as account_code, 
           '' as account_sap, 
           aml.date as date_aml, 
           aml.date_maturity as due_date, 
           CURRENT_DATE - aml.date_maturity as overdue, 
           aml.reconcile_id as status, 
           aml.reconcile_partial_id as partial, 
           aml.debit as debit, 
           aml.credit as credit, 
           aml.name as name, 
           aml.ref as reference, 
           j.name as journal_name, 
           m.name as invoice_name, 
           '' as branch_code, 
           ai2.supplier_invoice_number as supplier_invoice_number, 
           ai2.document_date as supplier_invoice_date, 
               CASE WHEN aml.reconcile_id IS NOT NULL and  aml4.account_id in (2533) and aml2.amount - aml4.amount  < 0  then  aml2.amount   
                WHEN aml.reconcile_id IS NOT NULL and  aml4.account_id in (2533) and aml2.amount - aml4.amount  = 0  then  aml2.amount - aml4.amount 
		        WHEN aml.reconcile_id IS NOT NULL then  aml2.amount
                WHEN aml.reconcile_id IS NOT NULL and av.state is null THEN 0.0 
                WHEN aml.reconcile_partial_id IS NULL THEN aml.credit - aml.debit 
                WHEN count_credit <> 0 THEN  (aml3.credit - aml3.debit) / count_credit 
            ELSE 0 
            END as residual, 
            pt.name as payment_term,
            p2.name md,
            db.name branch_inv,
            ai2.number inv_number,
            pokok,
            bunga,
            amlsa.amount saldo_awal
            FROM 
            account_move_line aml 
            LEFT JOIN (SELECT aml2.reconcile_partial_id, (select count(aml4.credit) from account_move_line aml4 where aml2.reconcile_partial_id = aml4.reconcile_partial_id and aml4.credit > 0
            and aml4.date >='2018-02-01' and aml4.date <='2018-02-28') as count_credit, SUM(aml2.debit) as debit, SUM(aml2.credit) as credit FROM account_move_line aml2 
            WHERE aml2.reconcile_partial_id is not Null and aml2.date >='2018-02-01' and aml2.date <='2018-02-28' GROUP BY aml2.reconcile_partial_id) aml3 
            on aml.reconcile_partial_id = aml3.reconcile_partial_id 
            LEFT JOIN account_move m ON m.id = aml.move_id 
            LEFT JOIN res_partner rp ON rp.id = aml.partner_id 
            LEFT JOIN account_account a ON a.id = aml.account_id 
            LEFT JOIN account_journal j ON j.id = aml.journal_id 
            LEFT JOIN account_invoice ai ON ai.move_id = aml.move_id 
            LEFT JOIN account_payment_term pt ON ai.payment_term = pt.id 
            LEFT JOIN account_voucher_line avl on aml.id = avl.move_line_id 
            LEFT JOIN account_voucher av ON avl.voucher_id = av.id 
            LEFT JOIN (select sum(credit- debit) amount,reconcile_id from account_move_line where date <= '2018-02-28' and state <> 'cancel' group by reconcile_id) aml2 on aml.reconcile_id = aml2.reconcile_id
            LEFT JOIN (select sum(debit- credit) amount,move_id,account_id from account_move_line where date <= '2018-02-28' and state <> 'cancel' and  account_id in (2533)  group by move_id,account_id) aml4 on aml.move_id = aml4.move_id
            LEFT JOIN (select credit as amount ,move_id, reconcile_id, aml.date, ref, name from account_move_line aml 
			where state <> 'cancel' and date <= '2018-02-01' and credit > 0 and debit = 0) amlsa on aml.reconcile_id = amlsa.reconcile_id
            LEFT JOIN dym_loan l on l.name=aml.name
            LEFT JOIN res_partner p2 on p2.id=l.partner_id_dari
            LEFT JOIN dym_loan_invoice_rel lir on lir.loan_id=l.id
            LEFT JOIN account_invoice ai2 on ai2.id=lir.invoice_id
            LEFT JOIN dym_branch db on db.id=ai2.branch_id
            LEFT JOIN dym_loan_line ll on ll.loan_id=l.id
            where 1=1 and right(m.name,10) <> '(Reversed)' AND m.state = 'posted'"""

        move_selection = ""
        report_info = _('')
        move_selection += ""

        query_end=""
        if division :
            query_end +=" AND aml.division = '%s'" % str(division)
        if start_date :
            query_end +=" AND aml.date_maturity >= '%s'" % str(start_date)
        if end_date :
            query_end +=" AND aml.date_maturity <= '%s'" % str(end_date)
        if trx_start_date :
            query_end +=" AND (aml.date >= '%s' or aml.date_maturity >= '%s')" % (str(trx_start_date),str(trx_start_date))
        if trx_end_date :
            query_end +=" AND (aml.date <= '%s' or aml.date_maturity <= '%s')" % (str(trx_end_date),str(trx_end_date))
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
        reports = [report_hutang]
        query_order = ""
        add_line_x=""

        print "=================", query_start + query_end + query_order
        for report in reports:
            cr.execute(query_start + query_end + query_order)
            print query_start + query_end + query_order
            all_lines = cr.dictfetchall()
            ids_aml = []

            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': 0,
                        'id_aml': x['id_aml'] if x['id_aml'] != None else '',
                        'payment_term': x['payment_term'] if x['payment_term'] != None else '',
                        'branch_code': x['branch_code'] if x['branch_code'] != None else '',
                        'division': str(x['division'].encode('ascii','ignore').decode('ascii')) if x['division'] != None else '',
                        'partner_code': str(x['partner_code'].encode('ascii','ignore').decode('ascii')) if x['partner_code'] != None else '',
                        'partner_name': str(x['partner_name'].encode('ascii','ignore').decode('ascii')) if x['partner_name'] != None else '',
                        'account_code': str(x['account_code'].encode('ascii','ignore').decode('ascii')) if x['account_code'] != None else '',
                        'invoice_name': str(x['invoice_name'].encode('ascii','ignore').decode('ascii')) if x['invoice_name'] != None else '',
                        'name': str(x['name'].encode('ascii','ignore').decode('ascii')) if x['name'] != None else '',
                        'supplier_invoice_date': str(x['supplier_invoice_date'].encode('ascii','ignore').decode('ascii')) if x['supplier_invoice_date'] != None else '',
                        'supplier_invoice_number': str(x['supplier_invoice_number'].encode('ascii','ignore').decode('ascii')) if x['supplier_invoice_number'] != None else '',
                        'date_aml': str(x['date_aml']) if x['date_aml'] != None else '',
                        'due_date': str(x['due_date']) if x['due_date'] != None else '',
                        'overdue': str(x['overdue']) if x['overdue'] != None and x['residual'] != None and  x['residual'] > 0  else '',
                        'status': 'Outstanding' if str(x['status']) == 'None' else 'Reconciled',
                        'tot_invoice': x['credit'] - x['debit'],
                        #'saldo_awal': 0,
                        'amount_residual': x['residual'] if x['residual'] != None else False,
                        'belum_jatuh_tempo': (x['residual'] if x['residual'] != None else False) if x['overdue'] <= 0 or x['overdue'] == None else False,
                        'overdue_1_30': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 0 and x['overdue'] < 31 else False,
                        'overdue_31_60': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 30 and x['overdue'] < 61 else False,
                        'overdue_61_90': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 60 and x['overdue'] < 91 else False,
                        'overdue_91_n': (x['residual'] if x['residual'] != None else False) if x['overdue'] > 91 else False,
                        'reference': str(x['reference'].encode('ascii','ignore').decode('ascii')) if x['reference'] != None else '',
                        'journal_name': str(x['journal_name'].encode('ascii','ignore').decode('ascii')) if x['journal_name'] != None else '',
                        'md': str(x['md'].encode('ascii','ignore').decode('ascii')) if x['md'] != None else '',
                        'branch_inv': str(x['branch_inv'].encode('ascii','ignore').decode('ascii')) if x['branch_inv'] != None else '',
                        'inv_number': str(x['inv_number'].encode('ascii','ignore').decode('ascii')) if x['inv_number'] != None else '',
                        'pokok': x['pokok'] if x['pokok'] != None else False,
                        'bunga': x['bunga'] if x['bunga'] != None else False,
                        'saldo_awal': x['saldo_awal'] if x['saldo_awal'] != None else 0,
                        },

                    all_lines)
                for p in p_map:
                    # print p['md'],'********'
                    # print p['id_aml'], 'check'
                    if p['id_aml'] not in map(
                            lambda x: x.get('id_aml', None), ids_aml):
                        account_move_lines = filter(
                            lambda x: x['id_aml'] == p['id_aml'], all_lines)
                        # print len(all_lines)
                        # print account_move_lines, 'test1'
                        # print p['id_aml'], 'check'
                        analytic_1 = ''
                        analytic_2 = ''
                        analytic_3 = ''
                        analytic_4 = ''
                        analytic_1_name = ''
                        analytic_2_name = ''
                        analytic_3_name = ''
                        analytic_4_name = ''
                        # saldo_awal = 0
                        # print len (account_move_lines), 'move line'
                        am = self.pool.get('account.move.line').browse(cr, uid, account_move_lines[0]['id_aml'])
                        print p['id_aml'], 'check'
                        if am.debit > 0:
                            continue
                        analytic = am.analytic_account_id or ''
                        # print len(analytic)
                        # saldo_awal = 0
                        branch_code = ''
                        branch_name = ''
                        branch = False
                        branch_status_1 = ''
                        branch_name = ''
                        branch_code = ''
                        if analytic:
                            # print len(analytic), 'test'
                            # raise 'test'
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
                                    branch_code = branch.code
                                    branch_status_1 = branch.branch_status
                                    branch_id = branch.id
                                if analytic.segmen == 4 and analytic_4 == '':
                                    analytic_4_name = analytic.name
                                    analytic_4 = analytic.code
                                    analytic_id = analytic
                            # print analytic.parent_id
                            # raise 'test'
                            # print 'hello'
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
                                        branch_code = branch.code
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
                            p.update({'analytic_1': analytic_1_name})
                            p.update({'analytic_2': analytic_2_name})
                            p.update({'analytic_3': analytic_3_name})
                            p.update({'analytic_4': analytic_4_name})
                            p.update({'branch_status': branch_status_1})
                            p.update({'branch_name': branch_name})
                            p.update({'branch_code': branch_code})
                            p.update({'analytic_combination': analytic_combination})
                            acc_number = ''
                            bank = ''
                            an_rek = ''
                            if am.partner_id.bank_ids:
                                acc_number = am.partner_id.bank_ids[0].acc_number
                                bank = am.partner_id.bank_ids[0].bank.name
                                an_rek = am.partner_id.bank_ids[0].owner_name
                            p.update({'acc_number': acc_number})
                            p.update({'bank': bank})
                            p.update({'an_rek': an_rek})
                            tgl_retur = ''
                            no_retur = ''
                            total_retur = 0
                            p.update({'tgl_retur': tgl_retur})
                            p.update({'no_retur': no_retur})
                            p.update({'total_retur': total_retur})
                            if am.sudo().invoice:
                                rb_ids = self.pool.get('dym.retur.beli').search(cr, uid, [('consolidate_id.invoice_id','=',am.sudo().invoice.id),('state','in',['approved','except_picking','except_invoice','done'])])
                                if rb_ids:
                                    rb = self.pool.get('dym.retur.beli').browse(cr, uid, rb_ids)
                                    tgl_retur = ', '.join(rb.mapped('date'))
                                    no_retur = ', '.join(rb.mapped('name'))
                                    total_retur = sum(x.amount_total for x in rb)
                            if total_retur > 0:
                                if p['tot_invoice'] > total_retur:
                                    p.update({'tot_invoice': p['tot_invoice'] - total_retur})
                                if p['overdue_1_30'] > total_retur:
                                    p.update({'overdue_1_30': p['overdue_1_30'] - total_retur})
                                if p['overdue_31_60'] > total_retur:
                                    p.update({'overdue_31_60': p['overdue_31_60'] - total_retur})
                                if p['overdue_61_90'] > total_retur:
                                    p.update({'overdue_61_90': p['overdue_61_90'] - total_retur})
                                if p['overdue_91_n'] > total_retur:
                                    p.update({'overdue_91_n': p['overdue_91_n'] - total_retur})
                            p.update({'pay_no': ''})
                            p.update({'pay_date': ''})
                            p.update({'pay_amount': 0})
                            # p.update({'saldo_akhir': 0})
                            p.update({'pay_pindahan': 0})
                            p.update({'pay_retur': 0})
                            if "OPBAL" in p['journal_name'] and p['tot_invoice'] > 0:
                                p.update({'saldo_awal': p['tot_invoice']})
                                p.update({'tot_invoice': 0})
                            else:
                                p.update({'saldo_awal': p['saldo_awal']})
                            ids_aml.append(p)
                            # print len(ids_aml)
                            index = len(ids_aml) - 1
                            partial_lines = lines = self.pool.get('account.move.line').browse(cr, uid, [])
                            if am.sudo().reconcile_id:
                                lines |= am.sudo().reconcile_id.line_id
                            elif am.sudo().reconcile_partial_id:
                                lines |= am.sudo().reconcile_partial_id.line_partial_ids
                            partial_lines += am
                            payments = (lines - partial_lines).sorted().filtered(lambda r: r.debit > 0)
                            if payments and detail_pembayaran == True:
                                # print p['saldo_awal']
                                saldo_awal = p['saldo_awal']
                                penambahan = p['tot_invoice']
                                # print p['tot_invoice']
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
                                        if voucher.amount != 0 :
                                            if voucher.type == 'receipt':
                                                bayar += voucher.amount
                                            else:
                                                bayar += voucher.amount


                                            if voucher.amount == pay.debit:
                                                pay_amount_res = self.get_pay_array(cr, uid, voucher.number, voucher.date, voucher.amount, 0, 0, account_move_lines)
                                            else:
                                                pay_amount_res = self.get_pay_array(cr, uid, voucher.number, voucher.date,  pay.debit, 0, 0, account_move_lines)
                                            add_line.append(pay_amount_res)
                                        for voucher_line in voucher.line_ids.filtered(lambda r: r.type == 'cr' and r.amount > 0):
                                            rb_name = voucher_line.move_line_id.sudo().invoice.origin or ''
                                            retur_beli_id = self.pool.get('dym.retur.beli').search(cr, uid, [('name','in',rb_name.split(' '))])
                                            if not retur_beli_id:
                                                pindahan += voucher_line.amount
                                                pay_amount_res = self.get_pay_array(cr, uid, voucher_line.move_line_id.move_id.name, voucher.date, voucher_line.amount, 0, 0, account_move_lines)
                                                add_line.append(pay_amount_res)
                                    else:
                                        if pay.move_id.model == 'dym.loan':
                                            pay_amount_res = self.get_pay_array(cr, uid, pay.move_id.name, pay.date, 0, pay.debit, 0, account_move_lines)
                                            add_line.append(pay_amount_res)
                                        else:
                                            pay_amount_res = self.get_pay_array(cr, uid, pay.move_id.name, pay.date, pay.debit, 0, 0, account_move_lines)
                                            add_line.append(pay_amount_res)

                                if add_line:
                                    if  str(trx_end_date) >= pay.date:
                                        ids_aml += add_line
                # print len(ids_aml)
                # raise 'test'
                report.update({'ids_aml': ids_aml})                    
        reports = filter(lambda x: x.get('ids_aml'), reports)
        # print len(reports)
        
        if not reports :
            reports = [{
                'title_short': 'Laporan Hutang Bank DF',
                'type': 'payable', 
                'ids_aml': [{
                    'reference': 'NO DATA FOUND',
                    'acc_number': 'NO DATA FOUND',
                    'tgl_retur': 'NO DATA FOUND',
                    'no_retur': 'NO DATA FOUND',
                    'payment_term': 'NO DATA FOUND',
                    'total_retur': 0,
                    'bank': 'NO DATA FOUND',
                    'an_rek': 'NO DATA FOUND',
                    'supplier_invoice_number': 'NO DATA FOUND',
                    'supplier_invoice_date': 'NO DATA FOUND',
                    'tot_invoice': 0,
                    'saldo_awal': 0,
                    'date_aml': 'NO DATA FOUND',
                    'partner_code': 'NO DATA FOUND',
                    'no': 0,
                    'branch_code': 'NO DATA FOUND',
                    'branch_name': 'NO DATA FOUND',
                    'amount_residual': 0,
                    'journal_name': 'NO DATA FOUND',
                    'status': 'NO DATA FOUND',
                    'division': 'NO DATA FOUND',
                    'belum_jatuh_tempo': 0,
                    'id_aml': 'NO DATA FOUND',
                    'due_date': 'NO DATA FOUND',
                    'overdue_31_60': 0,
                    'partner_name': 'NO DATA FOUND',
                    'overdue_1_30': 0,
                    'overdue_61_90': 0,
                    'overdue_91_n': 0,
                    'invoice_name': 0,
                    'pay_no': 'NO DATA FOUND',
                    'pay_date': 'NO DATA FOUND',
                    'pay_amount': 0,
                    'pay_pindahan': 0,
                    'pay_retur': 0,
                    'name': 'NO DATA FOUND',
                    'account_code': 0,
                    'analytic_1': 'NO DATA FOUND',
                    'analytic_2': 'NO DATA FOUND',
                    'analytic_3': 'NO DATA FOUND',
                    'analytic_4': 'NO DATA FOUND',
                    'analytic_combination': 'NO DATA FOUND',
                    'branch_status': 'NO DATA FOUND',
                    'overdue': 'NO DATA FOUND',
                    'md': 'NO DATA FOUND',
                    'branch_inv': 'NO DATA FOUND',
                    'inv_number': 'NO DATA FOUND',
                    'pokok': 0,
                    'bunga': 0
                }],
                'title': '', 
                'detail_pembayaran': detail_pembayaran
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
        super(dym_report_hutangbankdf_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_hutangbankdf_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_hutangbankdf.report_hutang'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_hutangbankdf.report_hutang'
    _wrapped_report_class = dym_report_hutangbankdf_print
