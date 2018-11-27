from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_request_trackingpco_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_request_trackingpco_print, self).__init__(
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
        
        report_request_trackingpco = {
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Request Tracking PCO')}


        query_start = """
            select  distinct pco.id as "pco_id", 
                pco.date as "pco_date",
                db.name as "cabang",
                pco.division as "division",
                pco.name as "pco_number",
                case when pco.state = 'approved' then 'Approved'
                    else case when pco.state = 'draft' then 'Draft'
                    else case when pco.state = 'posted' then 'Posted'
                    else case when pco.state = 'cancel' then 'Cancel'
                    else case when pco.state = 'reimbursed' then 'Reimbursed'
                    else case when pco.state = 'waiting_for_approval' then 'Waiting For Approval'
                else pco.state end end end end end end as "pco_state", 
                ac.name as "pco_acc",
                pcol.description as "pco_desc",
                pco.amount as "pco_total",
                ac_anl_bu.name as "pco_anl_bu",
                ac_anl_br.name as "pco_anl_br",
                ac_anl_cc.name as "pco_anl_cc",
                pci.name as "pci_number",
                case when pci.pettycash_id is not null then pco.amount else null end as "jml_kasbon",
                case when pci.pettycash_id is not null then pco.amount - pco.amount_reimbursed else null end as "receive_amount",
                pco_new.name as "pco_new_number",
                case when pco_new.state = 'approved' then 'Approved'
                    else case when pco_new.state = 'draft' then 'Draft'
                    else case when pco_new.state = 'posted' then 'Posted'
                    else case when pco_new.state = 'cancel' then 'Cancel'
                    else case when pco_new.state = 'reimbursed' then 'Reimbursed'
                    else case when pco_new.state = 'waiting_for_approval' then 'Waiting For Approval'
                else pco_new.state end end end end end end as "pco_new_state", 
                ac_new.name as "pco_new_acc",
                coalesce(pcol_new.description,'') as "pcol_new_desc",
                pco_new.amount as "pco_new_total",
                ac_anl_bu_new.name as "pco_new_anl_bu",
                ac_anl_br_new.name as "pco_new_anl_br",
                ac_anl_cc_new.name as "pco_new_anl_cc",
                dr.name as "reimbursed_number",
                dr.date_request as "reimbursed_request",
                dr.date_approve as "reimbursed_approve",
                case when dr.state = 'approved' then 'Approved'
                    else case when dr.state = 'draft' then 'Draft'
                    else case when dr.state = 'cancel' then 'Cancel'
                    else case when dr.state = 'request' then 'Requested'
                    else case when dr.state = 'req2ho' then 'Requested to HO'
                    else case when dr.state = 'hoapproved' then 'HO Approved'
                    else case when dr.state = 'horejected' then 'HO Rejected'
                    else case when dr.state = 'paid' then 'HO Paid'
                    else case when dr.state = 'done' then 'Done'
                    else case when dr.state = 'waiting_for_approval' then 'Waiting For Approval'
                else dr.state end end end end end end end end end end as "reimbursed_state",
                bta.bta_name as "bta_name",
                bta.bta_date as "bta_date",
                case when bta.bta_state = 'done' then 'Done'
                            else case when bta.bta_state = 'draft' then 'Draft'
                            else case when bta.bta_state = 'cancel' then 'Cancel'
                            else case when bta.bta_state = 'approved' then 'Approved'
                else bta.bta_state end end end end as "bta_state",
                dbt.name as "dbt_name",
                dbt.date as "dbt_date",
                case when dbt.state = 'approved' then 'Done'
                    else case when dbt.state = 'draft' then 'Draft'
                    else case when dbt.state = 'cancel' then 'Cancel'
                    else case when dbt.state = 'appreceived' then 'Received'
                    else case when dbt.state = 'appapprove' then 'Process Done'
                    else case when dbt.state = 'confirmed' then 'Waiting Approval'
                    else case when dbt.state = 'waiting_for_approval' then 'Payment in Process'
                    else case when dbt.state = 'waiting_for_confirm_received' then 'Waiting For Confirm Received'
                else dbt.state end end end end end end end end as "dbt_state",
                dbt_withdraw.name as "withdraw_name",
                dbt_withdraw.date as "withdraw_date",
                case when dbt_withdraw.state = 'approved' then 'Done'
                    else case when dbt_withdraw.state = 'draft' then 'Draft'
                    else case when dbt_withdraw.state = 'cancel' then 'Cancel'
                    else case when dbt_withdraw.state = 'appreceived' then 'Received'
                    else case when dbt_withdraw.state = 'appapprove' then 'Process Done'
                    else case when dbt_withdraw.state = 'confirmed' then 'Waiting Approval'
                    else case when dbt_withdraw.state = 'waiting_for_approval' then 'Payment in Process'
                    else case when dbt_withdraw.state = 'waiting_for_confirm_received' then 'Waiting For Confirm Received'
                else dbt_withdraw.state end end end end end end end end as "withdraw_state"
            from dym_pettycash pco
            LEFT JOIN (select string_agg(name, ', ') as "description", pettycash_id as "pco_id" from dym_pettycash_line group by pettycash_id) pcol on pco.id = pcol.pco_id
            left join dym_pettycash_in pci on pci.pettycash_id = pco.id
            left join dym_pettycash pco_new on pci.pettycash_new_id = pco_new.id
            LEFT JOIN (select string_agg(name, ', ') as "description", pettycash_id as "pco_id" from dym_pettycash_line group by pettycash_id) pcol_new on pco_new.id = pcol_new.pco_id
            left join dym_branch db on pco.branch_id = db.id
            left join account_account ac on pco.account_id = ac.id
            left join account_analytic_account ac_anl_bu on pco.analytic_2 = ac_anl_bu.id
            left join account_analytic_account ac_anl_br on pco.analytic_3 = ac_anl_br.id
            left join account_analytic_account ac_anl_cc on pco.analytic_4 = ac_anl_cc.id
            left join account_account ac_new on pco_new.account_id = ac_new.id
            left join account_analytic_account ac_anl_bu_new on pco_new.analytic_2 = ac_anl_bu_new.id
            left join account_analytic_account ac_anl_br_new on pco_new.analytic_3 = ac_anl_br_new.id
            left join account_analytic_account ac_anl_cc_new on pco_new.analytic_4 = ac_anl_cc_new.id
            left join (select distinct dr.id, dr.name, dr.transfer_request_id, dr.date_request, dr.date_approve, dr.state, drl.reimbursed_id, drl.pettycash_id 
                from dym_reimbursed dr
                left join dym_reimbursed_line drl on drl.reimbursed_id = dr.id) dr on dr.pettycash_id = pco.id
            left join (select trf_adv.id as "bta_id", trf_adv.name as "bta_name", trf_adv.date as "bta_date", trf_adv.state as "bta_state", trf_req.res_id 
                from bank_trf_request trf_req
                left join bank_trf_advice trf_adv on trf_adv.id = trf_req.advice_id
                where trf_req.obj = 'dym.reimbursed') bta on bta.res_id = dr.id
            --left join dym_bank_transfer_line dbtl on dbtl.reimbursement_id = dr.id and dbtl.transaction_type = 'withdraw'
            --left join dym_bank_transfer dbt_withdraw on dbt_withdraw.id = dbtl.bank_transfer_id and dbt_withdraw.state <> 'cancel' 
            left join dym_bank_transfer dbt on dbt.bank_trf_advice_id = bta.bta_id and dbt.state = 'approved'
            left join (select dbt_withdraw.name, dbt_withdraw.date, dbt_withdraw.state, dbtl_withdraw.reimbursement_id 
                    from dym_bank_transfer dbt_withdraw
                    left join dym_bank_transfer_line dbtl_withdraw on dbt_withdraw.id = dbtl_withdraw.bank_transfer_id
                    where dbt_withdraw.state not in ('cancel')) dbt_withdraw on dbt_withdraw.reimbursement_id = dr.id
            where 1=1 
            """ \

        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        query_end=""
        if division :
            query_end +=" AND pco.division = '%s'" % str(division)
        if trx_start_date :
            query_end +=" AND pco.date >= '%s'" % str(trx_start_date)
        if trx_end_date :
            query_end +=" AND pco.date <= '%s'" % str(trx_end_date)
        if start_date :
            query_end +=" AND pco.date_due >= '%s'" % str(start_date)
        if end_date :
            query_end +=" AND pco.date_due <= '%s'" % str(end_date)
        if partner_ids :
            query_end +=" AND pco.partner_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        if branch_ids :
            query_end +=" AND pco.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if account_id :
            query_end+=" AND pco.account_id in %s" % str(
                tuple(account_id)).replace(',)', ')')
        if journal_id :
            query_end+=" AND pco.journal_id in %s" % str(
                tuple(journal_id)).replace(',)', ')')
        reports = [report_request_trackingpco]
        
        # query_order = "order by cabang"
        query_order = " order by db.name, pco.name "
        for report in reports:
            cr.execute(query_start + query_end + query_order)
            # print query_start + query_end + query_order
            
            
            all_lines = cr.dictfetchall()
            pco_id = []

            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': 0,      
                        'pco_id': x['pco_id'],      
                        'pco_date': x['pco_date'],
                        'cabang': x['cabang'],
                        'division': x['division'],
                        'pco_number': x['pco_number'],
                        'pco_state': x['pco_state'],
                        'pco_acc': x['pco_acc'],
                        'pco_desc': x['pco_desc'],
                        'pco_total': x['pco_total'],
                        'pco_anl_bu': x['pco_anl_bu'],
                        'pco_anl_br': x['pco_anl_br'],
                        'pco_anl_cc': x['pco_anl_cc'],
                        'pci_number': x['pci_number'],
                        'jml_kasbon': x['jml_kasbon'],
                        'receive_amount': x['receive_amount'],
                        'pco_new_number': x['pco_new_number'],
                        'pco_new_state': x['pco_new_state'],
                        'pco_new_acc': x['pco_new_acc'],
                        'pcol_new_desc': x['pcol_new_desc'],
                        'pco_new_total': x['pco_new_total'],
                        'pco_new_anl_bu': x['pco_new_anl_bu'],
                        'pco_new_anl_br': x['pco_new_anl_br'],
                        'pco_new_anl_cc': x['pco_new_anl_cc'],
                        'reimbursed_number': x['reimbursed_number'],
                        'reimbursed_request': x['reimbursed_request'],
                        'reimbursed_approve': x['reimbursed_approve'],
                        'reimbursed_state': x['reimbursed_state'],
                        'bta_name': x['bta_name'],
                        'bta_date': x['bta_date'],
                        'bta_state': x['bta_state'],
                        'withdraw_name': x['withdraw_name'],
                        'withdraw_date': x['withdraw_date'],
                        'withdraw_state': x['withdraw_state'],
                        'dbt_name': x['dbt_name'],
                        'dbt_date': x['dbt_date'],
                        'dbt_state': x['dbt_state']
                        },
                    all_lines)



            reports = [{
                'title_short': 'Request Tracking PCO', 
                'pco_id': p_map, 
                'title': ''
            }]
        
        if not reports :
            reports = [{
                'title_short': 'Request Tracking PCO', 
                # 'type': ['out_invoice','in_invoice','in_refund','out_refund'], 
                'pco_id': [{
                    'no': 0,
                    'pco_date': 'NO DATA FOUND',
                    'cabang': 'NO DATA FOUND',
                    'division': 'NO DATA FOUND',
                    'pco_number': 'NO DATA FOUND',
                    'pco_state': 'NO DATA FOUND',
                    'pco_acc': 'NO DATA FOUND',
                    'pco_desc': 'NO DATA FOUND',
                    'pco_total': 0,
                    'pco_anl_bu': 'NO DATA FOUND',
                    'pco_anl_br': 'NO DATA FOUND',
                    'pco_anl_cc': 'NO DATA FOUND',
                    'pci_number': 'NO DATA FOUND',
                    'jml_kasbon': 0,
                    'receive_amount': 0,
                    'pco_new_number': 'NO DATA FOUND',
                    'pco_new_state': 'NO DATA FOUND',
                    'pco_new_acc': 'NO DATA FOUND',
                    'pco_new_desc': 'NO DATA FOUND',
                    'pco_new_total': 0,
                    'pco_new_anl_bu': 'NO DATA FOUND',
                    'pco_new_anl_br': 'NO DATA FOUND',
                    'pco_new_anl_cc': 'NO DATA FOUND',
                    'reimbursed_number': 'NO DATA FOUND',
                    'reimbursed_request': 'NO DATA FOUND',
                    'reimbursed_approve': 'NO DATA FOUND',
                    'reimbursed_state': 'NO DATA FOUND',
                    'bta_name': 'NO DATA FOUND',
                    'bta_date': 'NO DATA FOUND',
                    'bta_state': 'NO DATA FOUND',
                    'withdraw_name': 'NO DATA FOUND',
                    'withdraw_date': 'NO DATA FOUND',
                    'withdraw_state': 'NO DATA FOUND',
                    'dbt_name': 'NO DATA FOUND',
                    'dbt_date': 'NO DATA FOUND',
                    'dbt_state': 'NO DATA FOUND',
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
        super(dym_report_request_trackingpco_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_request_trackingpco_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_request_trackingpco.report_request_trackingpco'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_request_trackingpco.report_request_trackingpco'
    _wrapped_report_class = dym_report_request_trackingpco_print
