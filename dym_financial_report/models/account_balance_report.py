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

class account_balance_report(osv.osv_memory):
    _inherit = "account.balance.report"
    _description = 'Trial Balance Report'

    _columns = {
        'journal_ids': fields.many2many('account.journal', 'account_balance_report_journal_rel', 'account_id', 'journal_id', 'Journals'),
        'account_ids': fields.many2many('account.account', 'account_report_trial_balance_account_rel', 'tb_id', 'account_id', 'Account'),
        'analytic_ids': fields.many2many('account.analytic.account', 'account_report_trial_balance_analytic_rel', 'tb_id', 'analytic_id', 'Analytic'),
        'konsolidasi' : fields.boolean('Konsolidasi'),
        'analytic_co_dari' : fields.char('Analytic Company Dari'),
        'analytic_co_sampai' : fields.char('Analytic Company Sampai'),
        'analytic_bb_dari' : fields.char('Analytic Bisnis Unit Dari'),
        'analytic_bb_sampai' : fields.char('Analytic Bisnis Unit Sampai'),
        'analytic_br_dari' : fields.char('Analytic Branch Dari'),
        'analytic_br_sampai' : fields.char('Analytic Branch Sampai'),
        'analytic_cc_dari' : fields.char('Analytic Cost Center Dari'),
        'analytic_cc_sampai' : fields.char('Analytic Cost Center Sampai'),
    }

    _defaults = {
        'journal_ids': False,
    }

    def _print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        data['form'].update(self.read(cr, uid, ids, ['journal_ids', 'account_ids', 'analytic_ids','konsolidasi','analytic_co_dari','analytic_co_sampai','analytic_bb_dari','analytic_bb_sampai','analytic_br_dari','analytic_br_sampai','analytic_cc_dari','analytic_cc_sampai'])[0])
        data['form']['used_context']['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        data['form']['used_context']['account_ids'] = 'account_ids' in data['form'] and data['form']['account_ids'] or False
        data['form']['used_context']['analytic_ids'] = 'analytic_ids' in data['form'] and data['form']['analytic_ids'] or False
        data['form']['used_context']['konsolidasi'] = 'konsolidasi' in data['form'] and data['form']['konsolidasi'] or False
        data['form']['used_context']['analytic_co_dari'] = 'analytic_co_dari' in data['form'] and data['form']['analytic_co_dari'] or False
        data['form']['used_context']['analytic_co_sampai'] = 'analytic_co_sampai' in data['form'] and data['form']['analytic_co_sampai'] or False
        data['form']['used_context']['analytic_bb_dari'] = 'analytic_bb_dari' in data['form'] and data['form']['analytic_bb_dari'] or False
        data['form']['used_context']['analytic_bb_sampai'] = 'analytic_bb_sampai' in data['form'] and data['form']['analytic_bb_sampai'] or False
        data['form']['used_context']['analytic_br_dari'] = 'analytic_br_dari' in data['form'] and data['form']['analytic_br_dari'] or False
        data['form']['used_context']['analytic_br_sampai'] = 'analytic_br_sampai' in data['form'] and data['form']['analytic_br_sampai'] or False
        data['form']['used_context']['analytic_cc_dari'] = 'analytic_cc_dari' in data['form'] and data['form']['analytic_cc_dari'] or False
        data['form']['used_context']['analytic_cc_sampai'] = 'analytic_cc_sampai' in data['form'] and data['form']['analytic_cc_sampai'] or False
        return self.pool['report'].get_action(cr, uid, [], 'account.report_trialbalance', data=data, context=context)
