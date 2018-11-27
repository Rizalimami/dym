import time
from openerp.osv import fields, osv
from openerp import api, _
from datetime import datetime, date, timedelta
from openerp import SUPERUSER_ID
from openerp.osv.orm import browse_record_list, browse_record, browse_null
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.report import report_sxw
from openerp.addons.account.report.common_report_header import common_report_header
import openerp
from lxml import etree

class dym_accounting_report(osv.osv_memory):
    _inherit = "accounting.report"
    _description = "Accounting Report"

    _columns = {
        'account_ids': fields.many2many('account.account', 'accounting_report_account_rel', 'ar_id', 'account_id', 'Account'),
        'analytic_ids': fields.many2many('account.analytic.account', 'accounting_report_analytic_rel', 'ar_id', 'analytic_id', 'Analytic'),
        'journal_ids': fields.many2many('account.journal', string='Journals', required=False),
        'konsolidasi' : fields.boolean('Konsolidasi'),
        'analytic_co_dari' : fields.many2one('account.analytic.account', string='Analytic Company Dari', domain="[('segmen','=','1')]"),
        'analytic_co_sampai' : fields.many2one('account.analytic.account', string='Analytic Company Sampai', domain="[('segmen','=','1')]"),
        'analytic_bb_dari' : fields.many2one('account.analytic.account', string='Analytic Bisnis Unit Dari', domain="[('segmen','=','2')]"),
        'analytic_bb_sampai' : fields.many2one('account.analytic.account', string='Analytic Bisnis Unit Sampai', domain="[('segmen','=','2')]"),
        'analytic_br_dari' : fields.many2one('account.analytic.account', string='Analytic Branch Dari', domain="[('segmen','=','3')]"),
        'analytic_br_sampai' : fields.many2one('account.analytic.account', string='Analytic Branch Sampai', domain="[('segmen','=','3')]"),
        'analytic_cc_dari' : fields.many2one('account.analytic.account', string='Analytic Cost Center Dari', domain="[('segmen','=','4')]"),
        'analytic_cc_sampai' : fields.many2one('account.analytic.account', string='Analytic Cost Center Sampai', domain="[('segmen','=','4')]"),

        # 'analytic_co_dari' : fields.char('Analytic Company Dari'),
        # 'analytic_co_sampai' : fields.char('Analytic Company Sampai'),
        # 'analytic_bb_dari' : fields.char('Analytic Bisnis Unit Dari'),
        # 'analytic_bb_sampai' : fields.char('Analytic Bisnis Unit Sampai'),
        # 'analytic_br_dari' : fields.char('Analytic Branch Dari'),
        # 'analytic_br_sampai' : fields.char('Analytic Branch Sampai'),
        # 'analytic_cc_dari' : fields.char('Analytic Cost Center Dari'),
        # 'analytic_cc_sampai' : fields.char('Analytic Cost Center Sampai'),
    }

    _defaults = {
        'journal_ids': False,
    }

    def _build_comparison_context(self, cr, uid, ids, data, context=None):
        res = super(dym_accounting_report, self)._build_comparison_context(cr, uid, ids, data, context=context)

        res['account_ids'] = 'account_ids' in data['form'] and data['form']['account_ids'] or False
        res['analytic_ids'] = 'analytic_ids' in data['form'] and data['form']['analytic_ids'] or False
        res['konsolidasi'] = 'konsolidasi' in data['form'] and data['form']['konsolidasi'] or False
        res['analytic_co_dari'] = 'analytic_co_dari' in data['form'] and data['form']['analytic_co_dari'] or False
        res['analytic_co_sampai'] = 'analytic_co_sampai' in data['form'] and data['form']['analytic_co_sampai'] or False
        res['analytic_bb_dari'] = 'analytic_bb_dari' in data['form'] and data['form']['analytic_bb_dari'] or False
        res['analytic_bb_sampai'] = 'analytic_bb_sampai' in data['form'] and data['form']['analytic_bb_sampai'] or False
        res['analytic_br_dari'] = 'analytic_br_dari' in data['form'] and data['form']['analytic_br_dari'] or False
        res['analytic_br_sampai'] = 'analytic_br_sampai' in data['form'] and data['form']['analytic_br_sampai'] or False
        res['analytic_cc_dari'] = 'analytic_cc_dari' in data['form'] and data['form']['analytic_cc_dari'] or False
        res['analytic_cc_sampai'] = 'analytic_cc_sampai' in data['form'] and data['form']['analytic_cc_sampai'] or False
        return res

    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = super(dym_accounting_report, self).check_report(cr, uid, ids, context=context)
        data = {}
        data['form'] = self.read(cr, uid, ids, ['account_report_id', 'date_from_cmp',  'date_to_cmp',  'fiscalyear_id_cmp', 'journal_ids', 'period_from_cmp', 'period_to_cmp',  'filter_cmp',  'chart_account_id', 'target_move',
            'account_ids','analytic_ids','konsolidasi','analytic_co_dari','analytic_co_sampai','analytic_bb_dari','analytic_bb_sampai','analytic_br_dari','analytic_br_sampai','analytic_cc_dari','analytic_cc_sampai'], context=context)[0]
        for field in ['fiscalyear_id_cmp', 'chart_account_id', 'period_from_cmp', 'period_to_cmp', 'account_report_id','konsolidasi','analytic_co_dari','analytic_co_sampai','analytic_bb_dari','analytic_bb_sampai','analytic_br_dari','analytic_br_sampai','analytic_cc_dari','analytic_cc_sampai']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        comparison_context = self._build_comparison_context(cr, uid, ids, data, context=context)
        res['data']['form']['comparison_context'] = comparison_context
        res['data']['form']['used_context']['account_ids'] = 'account_ids' in data['form'] and data['form']['account_ids'] or False
        res['data']['form']['used_context']['analytic_ids'] = 'analytic_ids' in data['form'] and data['form']['analytic_ids'] or False
        res['data']['form']['used_context']['konsolidasi'] = 'konsolidasi' in data['form'] and data['form']['konsolidasi'] or False
        res['data']['form']['used_context']['analytic_co_dari'] = 'analytic_co_dari' in data['form'] and data['form']['analytic_co_dari'] or False
        res['data']['form']['used_context']['analytic_co_sampai'] = 'analytic_co_sampai' in data['form'] and data['form']['analytic_co_sampai'] or False
        res['data']['form']['used_context']['analytic_bb_dari'] = 'analytic_bb_dari' in data['form'] and data['form']['analytic_bb_dari'] or False
        res['data']['form']['used_context']['analytic_bb_sampai'] = 'analytic_bb_sampai' in data['form'] and data['form']['analytic_bb_sampai'] or False
        res['data']['form']['used_context']['analytic_br_dari'] = 'analytic_br_dari' in data['form'] and data['form']['analytic_br_dari'] or False
        res['data']['form']['used_context']['analytic_br_sampai'] = 'analytic_br_sampai' in data['form'] and data['form']['analytic_br_sampai'] or False
        res['data']['form']['used_context']['analytic_cc_dari'] = 'analytic_cc_dari' in data['form'] and data['form']['analytic_cc_dari'] or False
        res['data']['form']['used_context']['analytic_cc_sampai'] = 'analytic_cc_sampai' in data['form'] and data['form']['analytic_cc_sampai'] or False
        return res

    def _print_report(self, cr, uid, ids, data, context=None):
        data['form'].update(self.read(cr, uid, ids, ['date_from_cmp',  'debit_credit', 'date_to_cmp',  'fiscalyear_id_cmp', 'period_from_cmp', 'period_to_cmp',  'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter','target_move','account_ids','analytic_ids','konsolidasi','analytic_co_dari','analytic_co_sampai','analytic_bb_dari','analytic_bb_sampai','analytic_br_dari','analytic_br_sampai','analytic_cc_dari','analytic_cc_sampai'], context=context)[0])
        return self.pool['report'].get_action(cr, uid, [], 'account.report_financial', data=data, context=context)
