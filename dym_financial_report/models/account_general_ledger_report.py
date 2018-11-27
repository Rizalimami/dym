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

class account_report_general_ledger(osv.osv_memory):
    _inherit = "account.report.general.ledger"
    _description = "General Ledger Report"

    _columns = {
        'journal_ids': fields.many2many('account.journal', 'account_report_general_ledger_journal_rel', 'account_id', 'journal_id', 'Journals'),
        'account_ids': fields.many2many('account.account', 'account_report_general_ledger_account_rel', 'gl_id', 'account_id', 'Account'),
        'analytic_ids': fields.many2many('account.analytic.account', 'account_report_general_ledger_analytic_rel', 'gl_id', 'analytic_id', 'Analytic'),
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
        data['form'].update(self.read(cr, uid, ids, ['landscape',  'initial_balance', 'amount_currency', 'sortby', 'account_ids', 'analytic_ids','konsolidasi','analytic_co_dari','analytic_co_sampai','analytic_bb_dari','analytic_bb_sampai','analytic_br_dari','analytic_br_sampai','analytic_cc_dari','analytic_cc_sampai'])[0])
        if not data['form']['fiscalyear_id']:# GTK client problem onchange does not consider in save record
            data['form'].update({'initial_balance': False})

        if data['form']['landscape'] is False:
            data['form'].pop('landscape')
        else:
            context['landscape'] = data['form']['landscape']

        if data['form']['konsolidasi'] is False:
            data['form'].pop('konsolidasi')
        else:
            context['konsolidasi'] = data['form']['konsolidasi']

        if data['form']['analytic_co_dari'] is False:
            data['form'].pop('analytic_co_dari')
        else:
            context['analytic_co_dari'] = data['form']['analytic_co_dari']

        if data['form']['analytic_co_sampai'] is False:
            data['form'].pop('analytic_co_sampai')
        else:
            context['analytic_co_sampai'] = data['form']['analytic_co_sampai']

        if data['form']['analytic_bb_dari'] is False:
            data['form'].pop('analytic_bb_dari')
        else:
            context['analytic_bb_dari'] = data['form']['analytic_bb_dari']

        if data['form']['analytic_bb_sampai'] is False:
            data['form'].pop('analytic_bb_sampai')
        else:
            context['analytic_bb_sampai'] = data['form']['analytic_bb_sampai']

        if data['form']['analytic_br_dari'] is False:
            data['form'].pop('analytic_br_dari')
        else:
            context['analytic_br_dari'] = data['form']['analytic_br_dari']

        if data['form']['analytic_br_sampai'] is False:
            data['form'].pop('analytic_br_sampai')
        else:
            context['analytic_br_sampai'] = data['form']['analytic_br_sampai']

        if data['form']['analytic_cc_dari'] is False:
            data['form'].pop('analytic_cc_dari')
        else:
            context['analytic_cc_dari'] = data['form']['analytic_cc_dari']

        if data['form']['analytic_cc_sampai'] is False:
            data['form'].pop('analytic_cc_sampai')
        else:
            context['analytic_cc_sampai'] = data['form']['analytic_cc_sampai']

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
        return self.pool['report'].get_action(cr, uid, [], 'account.report_generalledger', data=data, context=context)
