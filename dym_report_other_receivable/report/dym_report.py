from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_other_receivable_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_other_receivable_print, self).__init__(
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
        
        report_other_receivable = {
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Other Receivable')}

        query_start = "SELECT av.id as id_ai, " \
            "COALESCE(b.name,'') as branch_id, " \
            "av.date as date, " \
            "av.amount as total, " \
            "av.name as memo, " \
            "av.reference as ref, " \
            "av.division as division, " \
            "av.name as name, " \
            "av.number as number, " \
            "av.state as state, " \
            "av.date_due as date_due, " \
            "rp.default_code as partner_code, " \
            "rp.name as partner_name, " \
            "a.code as account_code, " \
            "a.name as account_name, " \
            "j.name as journal_name " \
            "FROM " \
            "account_voucher av " \
            "LEFT JOIN dym_branch b ON av.branch_id = b.id " \
            "LEFT JOIN res_partner rp ON rp.id = av.partner_id " \
            "LEFT JOIN account_account a ON a.id = av.account_id " \
            "LEFT JOIN account_journal j ON j.id = av.journal_id " \
            "where 1=1 and av.state = 'posted' and j.type in ('sale','sale_refund') and av.type = 'sale' "
            
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
        reports = [report_other_receivable]
        
        query_order = ""
        for report in reports:
            cr.execute(query_start + query_end + query_order)
            all_lines = cr.dictfetchall()
            id_ai = []

            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': x['id_ai'] if x['id_ai'] != None else '',      
                        'id_ai': x['id_ai'] if x['id_ai'] != None else '',      
                        'branch_id': str(x['branch_id'].encode('ascii','ignore').decode('ascii')) if x['branch_id'] != None else '',
                        'date': str(x['date']) if x['date'] != None else '',
                        'number': str(x['number'].encode('ascii','ignore').decode('ascii')) if x['number'] != None else '',
                        'partner_name': str(x['partner_name'].encode('ascii','ignore').decode('ascii')) if x['partner_name'] != None else '',
                        'date_due': str(x['date_due']) if x['date_due'] != None else '',
                        'division': str(x['division']) if x['division'] != None else '',
                        'partner_code': str(x['partner_code']) if x['partner_code'] != None else '',
                        'journal_name': str(x['journal_name']) if x['journal_name'] != None else '',
                        'account_code': str(x['account_code'].encode('ascii','ignore').decode('ascii')) if x['account_code'] != None else '',
                        'account_name': str(x['account_name'].encode('ascii','ignore').decode('ascii')) if x['account_name'] != None else '',
                        'memo': str(x['memo']) if x['memo'] != None else '',
                        'ref': str(x['ref']) if x['ref'] != None else '',
                        'name': str(x['name']) if x['name'] != None else '',
                        'total': x['total'],
                        'state': x['state'],
                        'dpp': 0,
                        'ppn': 0,
                        'pph': 0,
                        'piutang': 0
                        },
                       
                    all_lines)
                for p in p_map:
                   if p['id_ai'] not in map(
                           lambda x: x.get('id_ai', None), id_ai):
                       account_analytic_account = filter(
                           lambda x: x['id_ai'] == p['id_ai'], all_lines)
                       analytic_1 = ''
                       analytic_2 = ''
                       analytic_3 = ''
                       analytic_4 = ''
                       analytic_1_name = ''
                       analytic_2_name = ''
                       analytic_3_name = ''
                       analytic_4_name = ''
                       ai = self.pool.get('account.voucher').browse(cr, uid, account_analytic_account[0]['id_ai'])
                       analytic = ai.analytic_4 or ''
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
                           if analytic_2 in ['210','220','230']:
                               if branch_status_1 == 'H123':
                                   analytic_2_branch = analytic_2[:2] + '1'
                               elif branch_status_1 == 'H23':
                                   analytic_2_branch = analytic_2[:2] + '2'
                               else:
                                   analytic_2_branch = analytic_2
                           analytic_combination = analytic_1 + '/' + analytic_2_branch + '/' + analytic_3 + '/' + analytic_4
                           move_line = ai.move_ids.filtered(lambda r: r.account_id.id == ai.account_id.id and r.debit > 0)
                           residual = 0
                           if move_line:
                              residual = self.pool.get('account.move.line').get_residual_date_based(cr, uid, move_line[0].id, trx_end_date)
                           p.update({'residual': residual})
                           p.update({'lines': account_analytic_account})
                           p.update({'analytic_1': analytic_1_name})
                           p.update({'analytic_2': analytic_2_name})
                           p.update({'analytic_3': analytic_3_name})
                           p.update({'analytic_4': analytic_4_name})
                           p.update({'branch_status': branch_status_1})
                           p.update({'branch_id': branch_name})
                           p.update({'analytic_combination': analytic_combination})
                           id_ai.append(p)
                    
                   av = self.pool.get('account.voucher').browse(cr, uid, p['id_ai'])
                   sum_ppn = av.tax_amount
                   sum_dpp = sum([sales_info.amount for sales_info in av.line_cr_ids])
                   sum_pph = sum([pph_line.amount for pph_line in av.withholding_ids])
                   sum_piutang = sum_dpp + sum_ppn - sum_pph
                   p.update({'dpp': sum_dpp})
                   p.update({'ppn': sum_ppn})
                   p.update({'pph': sum_pph})
                   p.update({'piutang': sum_piutang})

                report.update({'id_ai': id_ai})

        reports = filter(lambda x: x.get('id_ai'), reports)
        
        if not reports :
            reports = [{'title_short': 'Laporan Other Receivable', 'type': ['out_invoice','in_invoice','in_refund','out_refund'], 'id_ai':
                            [{'total': 0,
                              'date': 'NO DATA FOUND',
                              'branch_id': 'NO DATA FOUND',
                              'number': 'NO DATA FOUND',
                              'memo': 'NO DATA FOUND',
                              'ref': 'NO DATA FOUND',
                              'division': 'NO DATA FOUND',
                              'id_ai': 'NO DATA FOUND',
                              'analytic_1': 'NO DATA FOUND',
                              'analytic_2': 'NO DATA FOUND',
                              'analytic_3': 'NO DATA FOUND',
                              'analytic_4': 'NO DATA FOUND',
                              'analytic_combination': 'NO DATA FOUND',
                              'branch_status': 'NO DATA FOUND',
                              'state': 'NO DATA FOUND',
                              'partner_code': 'NO DATA FOUND',
                              'partner_name': 'NO DATA FOUND',
                              'journal_name': 'NO DATA FOUND',
                              'date_due': 'NO DATA FOUND',
                              'account_code': 'NO DATA FOUND',
                              'account_name': 'NO DATA FOUND',
                              'residual': 0,
                              'no': 0,
                              'name': 'NO DATA FOUND',}], 'title': ''}]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        objects=False
        super(dym_report_other_receivable_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_hutan_invoice_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_other_receivable.report_other_receivable'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_other_receivable.report_other_receivable'
    _wrapped_report_class = dym_report_other_receivable_print
