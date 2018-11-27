from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_request_tracking_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_request_tracking_print, self).__init__(
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
        branch_ids = data['branch_ids']
        account_id = data['account_ids']
        journal_id = data['journal_ids']
        branch_status = False
        trx_start_date = data['trx_start_date']
        trx_end_date = data['trx_end_date']
        division = data['division']
        partner_ids = data['partner_ids']

        title_prefix = ''
        title_short_prefix = ''
        
        report_request_tracking = {
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan User Request Tracking')}


        query_start = """
            SELECT  av.id as id_ai, 
                av.date as date,
                COALESCE(b.name,'') as branch_id,
                av.division as division,
                av.number as number,
                rp.default_code as partner_code,
                rp.name as partner_name,
                user_create.name as create_by,
                av.date_due as date_due,
                av.name as memo,
                av.reference as ref,
                av.net_amount as net_total,
                av.amount as total,
                '' as nama_account,
                '' as description,
                case when av.payment_request_type='biaya' then 'Biaya'  when av.payment_request_type='prepaid' then 'Prepaid'  when av.payment_request_type='cip' then 'CIP' end par_type,
                trf_adv.name as no_bta,
                trf_adv.date as date_bta,
                case when trf_adv.state = 'done' then 'Done'
                else case when trf_adv.state = 'draft' then 'Draft'
                else case when trf_adv.state = 'cancel' then 'Cancel'
                else case when trf_adv.state = 'approved' then 'Approved'
                else trf_adv.state end end end end as state_bta,
                dbt.name as no_btr,
                dbt.date as date_btr,
                case when dbt.state = 'approved' then 'Done'
                else case when dbt.state = 'draft' then 'Draft'
                else case when dbt.state = 'app_received' then 'Received'
                else case when dbt.state = 'app_approve' then 'Approved'
                else case when dbt.state = 'waiting_for_confirm_received' then 'Waiting For Confirm Received'
                else case when dbt.state = 'cancel' then 'Cancel'
                else case when dbt.state = 'waiting_for_approval' then 'Waiting For Approval'
                else dbt.state end end end end end end end as state_btr,
                case when av.state = 'approved' then 'Approved'
                else case when av.state = 'draft' then 'Draft'
                else case when av.state = 'posted' then 'Posted'
                else case when av.state = 'cancel' then 'Cancel'
                else case when av.state = 'request_approval' then 'RFA'
                else case when av.state = 'confirmed' then 'RFA'
                else case when av.state = 'waiting_for_approval' or av.state = 'confirmed' then 'Waiting For Approval'
                else av.state end end end end end end end as state_par,
                btr_withdraw.btr_withdraw_name as no_withdrawal,
                case when btr_withdraw.btr_state = 'approved' then 'Done'
                else case when btr_withdraw.btr_state = 'draft' then 'Draft'
                else case when btr_withdraw.btr_state = 'app_received' then 'Received'
                else case when btr_withdraw.btr_state = 'app_approve' then 'Approved'
                else case when btr_withdraw.btr_state = 'waiting_for_confirm_received' then 'Waiting For Confirm Received'
                else case when btr_withdraw.btr_state = 'cancel' then 'Cancel'
                else case when btr_withdraw.btr_state = 'waiting_for_approval' then 'Waiting For Approval'
                else dbt.state end end end end end end end as state_withdrawal,
                btr_withdraw.btr_date as date_withdrawal
            FROM  account_voucher av 
            LEFT JOIN dym_branch b ON av.branch_id = b.id 
            LEFT JOIN res_partner rp ON rp.id = av.partner_id 
            LEFT JOIN account_account a ON a.id = av.account_id 
            LEFT JOIN account_journal j ON j.id = av.journal_id 
            LEFT JOIN res_users users ON users.id = av.create_uid 
            LEFT JOIN res_partner user_create ON user_create.id = users.partner_id 
            LEFT JOIN account_voucher_line avl_spa ON av.number = avl_spa.name 
            LEFT JOIN account_voucher av_spa ON avl_spa.voucher_id = av_spa.id
            left join bank_trf_request trf_req on av.number = trf_req.name
            left join bank_trf_advice trf_adv on trf_req.advice_id = trf_adv.id
            left join (select distinct am.name as "par_name", dbt.name as "btr_withdraw_name", dbt.date as "btr_date", dbt.state as "btr_state", dbt.transaction_type as "btr_transaction_type" From bank_transfer_voucher_line btvl
                       left join account_move_line aml on aml.id = btvl.move_line_id
                       left join account_move am on am.id = aml.move_id
                       left join dym_bank_transfer dbt on dbt.id = btvl.bank_transfer_id) btr_withdraw on btr_withdraw.par_name = av.number
            --left join dym_bank_transfer dbt on dbt.bank_trf_advice_id = trf_adv.id
            left join (select id, bank_trf_advice_id, state, date, name from dym_bank_transfer) dbt on dbt.bank_trf_advice_id = trf_adv.id 
            where j.type in ('purchase','purchase_refund') and 
            --av.state = 'posted' and
            av.type = 'purchase' """ \

        query_start_new = """
            SELECT distinct av.id as id_ai,
              av.date as date,
              COALESCE(b.name,'') as branch_id,
              av.division as division,
              av.number as number,
              spa_spa.spa_name as spa_name,
              case when length(spa_spa.spa_name) > 22 then spa_spa.spa_amount else avl_spa.amount end as spa_amount,
              dcl.name as nomor_giro,
              dcg.name as nomor_cba,
              rp.default_code as partner_code,
              rp.name as partner_name,
              user_create.name as create_by,
              av.date_due as date_due,
              av.name as memo,
              av.reference as ref,
              av.net_amount as net_total,
              av.amount as total,
              aj_spa.name as spa_method,
              '' as nama_account,
              '' as description,
              case when av.payment_request_type='biaya' then 'Biaya'  when av.payment_request_type='prepaid' then 'Prepaid'  when av.payment_request_type='cip' then 'CIP' end par_type,
              trf_adv.name as no_bta,
              trf_adv.date as date_bta,
              case when trf_adv.state = 'done' then 'Done'
                else case when trf_adv.state = 'draft' then 'Draft'
                else case when trf_adv.state = 'cancel' then 'Cancel'
              else trf_adv.state end end end as state_bta,
              dbt.name as no_btr,
              dbt.date as date_btr,
              case when dbt.state = 'approved' then 'Done'
                else case when dbt.state = 'draft' then 'Draft'
                else case when dbt.state = 'app_received' then 'Received'
                else case when dbt.state = 'app_approve' then 'Approved'
                else case when dbt.state = 'waiting_for_confirm_received' then 'Waiting For Confirm Received'
                else case when dbt.state = 'cancel' then 'Cancel'
                else case when dbt.state = 'waiting_for_approval' then 'Waiting For Approval'
              else dbt.state end end end end end end end as state_btr,
              btr_withdraw.btr_withdraw_name,
              btr_withdraw.btr_state,
              btr_withdraw.btr_date,
              --btr_withdraw.btr_transaction_type,
              case when av.state = 'approved' then 'Approved'
                else case when av.state = 'draft' then 'Draft'
                else case when av.state = 'posted' then 'Posted'
                else case when av.state = 'cancel' then 'Cancel'
                else case when av.state = 'request_approval' then 'RFA'
                else case when av.state = 'confirmed' then 'RFA'
                else case when av.state = 'waiting_for_approval' or av.state = 'confirmed' then 'Waiting For Approval'
              else av.state end end end end end end end as state_par,
              btr_withdraw.btr_withdraw_name as no_withdrawal,
              case when btr_withdraw.btr_state = 'approved' then 'Done'
                else case when btr_withdraw.btr_state = 'draft' then 'Draft'
                else case when btr_withdraw.btr_state = 'app_received' then 'Received'
                else case when btr_withdraw.btr_state = 'app_approve' then 'Approved'
                else case when btr_withdraw.btr_state = 'waiting_for_confirm_received' then 'Waiting For Confirm Received'
                else case when btr_withdraw.btr_state = 'cancel' then 'Cancel'
                else case when btr_withdraw.btr_state = 'waiting_for_approval' then 'Waiting For Approval'
                else btr_withdraw.btr_state end end end end end end end as state_withdrawal,
              btr_withdraw.btr_date as date_withdrawal
            FROM  account_voucher av 
            LEFT JOIN account_voucher_line avl ON avl.voucher_id = av.id
            LEFT JOIN account_move am_par ON am_par.id = av.move_id
            LEFT JOIN account_move_line aml_par ON am_par.id = aml_par.move_id and aml_par.account_id in (select id from account_account where code = '2106099')--reconcile_ref is not null
            LEFT JOIN account_voucher_line avl_spa ON avl_spa.move_line_id = aml_par.id
            LEFT JOIN account_voucher av_spa ON avl_spa.voucher_id = av_spa.id
            LEFT JOIN (select string_agg(distinct(av.number), ', ') as spa_name, sum(av.amount) as spa_amount, am.name as par_name from account_voucher av 
                 left join account_voucher_line avl on avl.voucher_id = av.id
                 left join account_move_line aml on aml.id = avl.move_line_id
                 left join account_move am on aml.move_id = am.id
                 where left(av.number,3) = 'SPA' and left(am.name,3) = 'PAR'
                 group by am.name) spa_spa on spa_spa.par_name = av.number
            LEFT JOIN account_move am_spa ON am_spa.id = av_spa.move_id 
            LEFT JOIN account_move_line aml_spa ON aml_spa.move_id = am_spa.id and aml_spa.account_id in (select id from account_account where code = '1102998')
            left join dym_checkgyro_line dcl on dcl.id = av_spa.cheque_giro_number
            left join dym_clearing_giro_move_line_rel dcgmlr on dcgmlr.move_line_id = aml_spa.id
            left join dym_clearing_giro dcg on dcg.id = dcgmlr.clearing_id
            LEFT JOIN dym_branch b ON av.branch_id = b.id 
            LEFT JOIN res_partner rp ON rp.id = av.partner_id 
            LEFT JOIN account_account a ON a.id = av.account_id 
            LEFT JOIN account_journal j ON j.id = av.journal_id 
            LEFT JOIN account_journal aj_spa ON aj_spa.id = av_spa.journal_id 
            LEFT JOIN res_users users ON users.id = av.create_uid 
            LEFT JOIN res_partner user_create ON user_create.id = users.partner_id 
            left join bank_trf_request trf_req on av.number = trf_req.name
            left join bank_trf_advice trf_adv on trf_req.advice_id = trf_adv.id
            left join (select distinct am.name as "par_name", dbt.name as "btr_withdraw_name", dbt.date as "btr_date", dbt.state as "btr_state", dbt.transaction_type as "btr_transaction_type" From bank_transfer_voucher_line btvl
                       left join account_move_line aml on aml.id = btvl.move_line_id
                       left join account_move am on am.id = aml.move_id
                       left join dym_bank_transfer dbt on dbt.id = btvl.bank_transfer_id) btr_withdraw on btr_withdraw.par_name = av.number
            --left join dym_bank_transfer dbt on dbt.bank_trf_advice_id = trf_adv.id
            left join (select id, bank_trf_advice_id, state, date, name from dym_bank_transfer) dbt on dbt.bank_trf_advice_id = trf_adv.id 
            where j.type in ('purchase','purchase_refund') and 
            --av.state = 'posted' and
            av.type = 'purchase' """ \

        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        query_end=""
        if division :
            query_end +=" AND av.division = '%s'" % str(division)
        if trx_start_date :
            query_end +=" AND av.date >= '%s'" % str(trx_start_date)
        if trx_end_date :
            query_end +=" AND av.date <= '%s'" % str(trx_end_date)
        if start_date :
            query_end +=" AND av.date_due >= '%s'" % str(start_date)
        if end_date :
            query_end +=" AND av.date_due <= '%s'" % str(end_date)
        if partner_ids :
            query_end +=" AND av.partner_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        if branch_ids :
            query_end +=" AND av.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if account_id :
            query_end+=" AND av.account_id in %s" % str(
                tuple(account_id)).replace(',)', ')')
        if journal_id :
            query_end+=" AND av.journal_id in %s" % str(
                tuple(journal_id)).replace(',)', ')')
        reports = [report_request_tracking]
        
        # query_order = "order by cabang"
        query_order = " group by av.id, av.date, b.name, av.division, av.number, rp.default_code, rp.name, user_create.name, av.date_due, av.name , av.reference, av.amount, av.state, trf_adv.name, trf_adv.date, dbt.name, dbt.date, dbt.state, trf_adv.state, btr_withdraw.btr_withdraw_name, btr_withdraw.btr_state, btr_withdraw.btr_date, dcl.name, dcg.name, spa_spa.spa_name, spa_spa.spa_amount order by b.name, av.number "
        query_order_new = " group by av.id, av.date, b.name, av.division, av.number, rp.default_code, rp.name, user_create.name, av.date_due, av.name , av.reference, av.amount, av.state, trf_adv.name, trf_adv.date, dbt.name, dbt.date, dbt.state, trf_adv.state, btr_withdraw.btr_withdraw_name, btr_withdraw.btr_state, btr_withdraw.btr_date, dcl.name, dcg.name, spa_spa.spa_name, spa_spa.spa_amount, avl_spa.amount, aj_spa.name order by 3,5 "
        for report in reports:
            cr.execute(query_start_new + query_end + query_order_new)
            
            all_lines = cr.dictfetchall()
            id_ai = []

            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': 0,      
                        'id_ai': x['id_ai'] if x['id_ai'] != None else '',      
                        'date': str(x['date']) if x['date'] != None else '',
                        'branch_id': str(x['branch_id'].encode('ascii','ignore').decode('ascii')) if x['branch_id'] != None else '',
                        'division': str(x['division']) if x['division'] != None else '',
                        'number': str(x['number'].encode('ascii','ignore').decode('ascii')) if x['number'] != None else '',
                        'partner_code': str(x['partner_code']) if x['partner_code'] != None else '',
                        'partner_name': str(x['partner_name'].encode('ascii','ignore').decode('ascii')) if x['partner_name'] != None else '',
                        'create_by': str(x['create_by'].encode('ascii','ignore').decode('ascii')) if x['create_by'] != None else '',
                        'date_due': str(x['date_due']) if x['date_due'] != None else '',
                        'memo': str(x['memo']) if x['memo'] != None else '',
                        'ref': str(x['ref']) if x['ref'] != None else '',
                        'total': x['total'],
                        'net_total': x['net_total'],
                        'par_type': x['par_type'],
                        'nama_account': '',
                        'description': '',
                        # 'spa_number': '',
                        'spa_name': x['spa_name'],
                        'spa_amount': x['spa_amount'],
                        'spa_method': x['spa_method'],
                        'nomor_giro': x['nomor_giro'],
                        'nomor_cba': x['nomor_cba'],
                        'a_code': '',
                        'a_name': '',
                        'aa_combi': '',
                        'aa_company': '',
                        'aa_bisnisunit': '',
                        'aa_branch': '',
                        'aa_costcenter': '',
                        'no_bta': x['no_bta'],
                        'date_bta': x['date_bta'],
                        'state_bta': x['state_bta'],
                        'no_btr': x['no_btr'],
                        'date_btr': x['date_btr'],
                        'state_btr': x['state_btr'],
                        'state_par': x['state_par'],
                        'no_withdrawal': x['no_withdrawal'],
                        'date_withdrawal': x['date_withdrawal'],
                        'state_withdrawal': x['state_withdrawal'],
                        },
                    all_lines)

                for p in p_map:
                   if p['id_ai'] not in map(
                           lambda x: x.get('id_ai', None), id_ai):
                       records = filter(
                           lambda x: x['id_ai'] == p['id_ai'], all_lines)
                       p.update({'lines': records})
                       av = self.pool.get('account.voucher').browse(cr, uid, records[0]['id_ai'])
                       first = av.move_ids.filtered(lambda r: r.credit > 0).mapped('reconcile_id.line_id').filtered(lambda s: s.debit > 0)
                       clearing = False
                       line = False
                       for journal in first.mapped('journal_id'):
                          if journal.clearing_account_id.id in first.mapped('move_id.line_id').filtered(lambda r: r.credit > 0).mapped('account_id').ids:
                             clearing = True
                             line = first.mapped('move_id.line_id').filtered(lambda r: r.credit > 0).mapped('reconcile_id.line_id').filtered(lambda r: r.account_id == journal.clearing_account_id and r.debit > 0)
                             break
                       settlement_name = ''
                       status_cair = 'Belum Cair'
                       if clearing == True and line:
                          settlement_name = ', '.join(line.mapped('move_id.name'))
                          status_cair = 'Cair'
                       elif clearing == False and first:
                          settlement_name = ', '.join(first.mapped('move_id.name'))
                          status_cair = 'Cair'
                       
                       p.update({'status_cair': status_cair})
                       filtered_approval = av.approval_ids.filtered(lambda r: r.pelaksana_id and r.sts == '2')
                       p.update({'approved_by': ''})
                       p.update({'approved_date': ''})
                       if filtered_approval:
                         p.update({'approved_by': filtered_approval.sorted(key=lambda r: r.tanggal)[len(filtered_approval)-1].pelaksana_id.name})
                         p.update({'approved_date': filtered_approval.sorted(key=lambda r: r.tanggal)[len(filtered_approval)-1].tanggal})
                       id_ai.append(p)

                       # No. Supplier Payment
                       # domain_avlspa = [('name','=', p['number'])]
                       # avlspa_ids = self.pool.get('account.voucher.line').search(cr, uid, domain_avlspa, limit=1)
                       # avlspa = self.pool.get('account.voucher.line').browse(cr, uid, avlspa_ids)
                       # p.update({'spa_number': avlspa.voucher_id.number})
                       # p.update({'spa_amount': avlspa.amount})
                       # p.update({'payment_ref': avlspa.voucher_id.cheque_giro_number.name})
                       # p.update({'spa_method': avlspa.voucher_id.journal_id.name})

                       # if settlement_name[:3] == 'CBA':
                       #    p.update({'settlement_name': settlement_name})
                       #    p.update({'spa_number': avlspa.voucher_id.number})
                       # elif settlement_name[:3] == 'SPA':
                       #    p.update({'settlement_name': ''})
                       #    p.update({'spa_number': settlement_name})
                       # else:
                       #    p.update({'settlement_name': ''})
                       #    p.update({'spa_number': avlspa.voucher_id.number})

                       # Account
                       av_account = self.pool.get('account.voucher').browse(cr, uid, p['id_ai'])
                       accounts_biaya = []
                       descs = []
                       for x in av_account.line_dr_ids:
                          accounts_biaya.append(x.account_id.code)
                          accounts_biaya.append(x.account_id.name)
                       for x in av_account.line_dr_ids:
                          descs.append(x.name)
                       av_account_desc = "; ".join(descs)
                       av_account_biaya = "; ".join(accounts_biaya)
                       p.update({'description': av_account_desc})
                       p.update({'nama_account': av_account_biaya})
                       p.update({'a_code': av_account.account_id.code})
                       p.update({'a_name': av_account.account_id.name})
                       p.update({'aa_combi': "%s/%s/%s/%s" % (av_account.analytic_1.code,av_account.analytic_2.code,av_account.analytic_3.code,av_account.analytic_4.code) })
                       p.update({'aa_company': av_account.analytic_1.name})
                       p.update({'aa_bisnisunit': av_account.analytic_2.name})
                       p.update({'aa_branch': av_account.analytic_3.name})
                       p.update({'aa_costcenter': av_account.analytic_4.name})

                       # p.update({'spa_number': avlspa.voucher_id.number})
                       # p.update({'spa_amount': avlspa.voucher_id.number})
                       # p.update({'payment_ref': avlspa.voucher_id.number})
                       # p.update({'settlement_name': avlspa.voucher_id.number})

                report.update({'id_ai': id_ai})

        reports = filter(lambda x: x.get('id_ai'), reports)
        
        if not reports :
            reports = [{
                'title_short': 'Laporan User Request Tracking', 
                'type': ['out_invoice','in_invoice','in_refund','out_refund'], 
                'id_ai': [{
                    'total': 0,
                    'net_total': 0,
                    'date': 'NO DATA FOUND',
                    'branch_id': 'NO DATA FOUND',
                    'division': 'NO DATA FOUND',
                    'number': 'NO DATA FOUND',
                    'partner_code': 'NO DATA FOUND',
                    'partner_name': 'NO DATA FOUND',
                    'create_by': 'NO DATA FOUND',
                    'approved_by': 'NO DATA FOUND',
                    'approved_date': 'NO DATA FOUND',
                    'settlement_name': 'NO DATA FOUND',
                    'payment_ref': 'NO DATA FOUND',
                    'date_due': 'NO DATA FOUND',
                    'status_cair': 'NO DATA FOUND',
                    'memo': 'NO DATA FOUND',
                    'ref': 'NO DATA FOUND',
                    'description': 'NO DATA FOUND',
                    # 'spa_number': 'NO DATA FOUND',
                    'spa_name': 'NO DATA FOUND',
                    'spa_amount': 'NO DATA FOUND',
                    'spa_method': 'NO DATA FOUND',
                    'nomor_giro': 'NO DATA FOUND',
                    'nomor_cba': 'NO DATA FOUND',
                    'no_bta': 'NO DATA FOUND',
                    'date_bta': 'NO DATA FOUND',
                    'no_btr': 'NO DATA FOUND',
                    'date_btr': 'NO DATA FOUND',
                    'state_btr': 'NO DATA FOUND',
                    'state_bta': 'NO DATA FOUND',
                    'no_withdrawal': 'NO DATA FOUND',
                    'date_withdrawal': 'NO DATA FOUND',
                    'state_withdrawal': 'NO DATA FOUND',
                    'state_par': 'NO DATA FOUND'
                }], 'title': ''
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
        super(dym_report_request_tracking_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_request_tracking_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_request_tracking.report_request_tracking'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_request_tracking.report_request_tracking'
    _wrapped_report_class = dym_report_request_tracking_print
