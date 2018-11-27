# -*- coding: utf-8 -*-

import re
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
import time

import openerp
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.osv import fields, osv, expression
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools.safe_eval import safe_eval as eval

import openerp.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)

class dym_account_move_line(osv.osv):
    _inherit = 'account.move.line'

    def _query_get(self, cr, uid, obj='l', context=None):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalperiod_obj = self.pool.get('account.period')
        account_obj = self.pool.get('account.account')
        fiscalyear_ids = []
        context = self._get_context_analytic_code(cr, uid, dict(context or {}))
        initial_bal = context.get('initial_bal', False)
        company_clause = " "
        query = ''
        query_params = {}
        if context.get('company_id'):
            company_clause = " AND " +obj+".company_id = %(company_id)s"
            query_params['company_id'] = context['company_id']
        if not context.get('fiscalyear'):
            if context.get('all_fiscalyear'):
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [])
            else:
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [('state', '=', 'draft')])
        else:
            fiscalyear_ids = context['fiscalyear']
            if isinstance(context['fiscalyear'], (int, long)):
                fiscalyear_ids = [fiscalyear_ids]

        query_params['fiscalyear_ids'] = tuple(fiscalyear_ids) or (0,)
        state = context.get('state', False)
        where_move_state = ''
        where_move_lines_by_date = ''

        table_account_move = 'account_move'
        if 'konsolidasi' in context and context['konsolidasi'] == True:
            table_account_move = 'account_move_consol'

        if context.get('date_from') and context.get('date_to'):
            query_params['date_from'] = context['date_from']
            query_params['date_to'] = context['date_to']
            if initial_bal:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM "+table_account_move+" WHERE date < %(date_from)s)"
            else:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM "+table_account_move+" WHERE date >= %(date_from)s AND date <= %(date_to)s)"

        if state:
            if state.lower() not in ['all']:
                query_params['state'] = state
                where_move_state= " AND "+obj+".move_id IN (SELECT id FROM "+table_account_move+" WHERE "+table_account_move+".state = %(state)s)"
        if context.get('period_from') and context.get('period_to') and not context.get('periods'):
            if initial_bal:
                period_company_id = fiscalperiod_obj.browse(cr, uid, context['period_from'], context=context).company_id.id
                first_period = fiscalperiod_obj.search(cr, uid, [('company_id', '=', period_company_id)], order='date_start', limit=1)[0]
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, first_period, context['period_from'])
            else:
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, context['period_from'], context['period_to'])
        if context.get('periods'):
            query_params['period_ids'] = tuple(context['periods'])
            if initial_bal:
                query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s)" + where_move_state + where_move_lines_by_date
                period_ids = fiscalperiod_obj.search(cr, uid, [('id', 'in', context['periods'])], order='date_start', limit=1)
                if period_ids and period_ids[0]:
                    first_period = fiscalperiod_obj.browse(cr, uid, period_ids[0], context=context)
                    query_params['date_start'] = first_period.date_start
                    query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s AND date_start <= %(date_start)s AND id NOT IN %(period_ids)s)" + where_move_state + where_move_lines_by_date
            else:
                query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s AND id IN %(period_ids)s)" + where_move_state + where_move_lines_by_date
        else:
            query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s)" + where_move_state + where_move_lines_by_date

        if initial_bal and not context.get('periods') and not where_move_lines_by_date:
            raise osv.except_osv(_('Warning!'),_("You have not supplied enough arguments to compute the initial balance, please select a period and a journal in the context."))

        if context.get('journal_ids'):
            query_params['journal_ids'] = tuple(context['journal_ids'])
            query += ' AND '+obj+'.journal_id IN %(journal_ids)s'

        if context.get('account_ids'):
            query_params['account_ids'] = tuple(context['account_ids'])
            query += ' AND '+obj+'.account_id IN %(account_ids)s'

        if context.get('analytic_ids'):
            query_params['analytic_ids'] = tuple(context['analytic_ids'])
            query += ' AND '+obj+'.analytic_account_id IN %(analytic_ids)s'

        if context.get('chart_account_id'):
            child_ids = account_obj._get_children_and_consol(cr, uid, [context['chart_account_id']], context=context)
            # query_params['child_ids'] = tuple(child_ids)
            # query += ' AND '+obj+'.account_id IN %(child_ids)s'

        if context.get('sql_query'):
            query += context['sql_query']

        if context.get('analytic_co_dari'):
            if context.get('analytic_co_dari').isdigit():
                query_params['analytic_co_dari'] = int(context['analytic_co_dari'])
                query += " AND cast(coalesce(a1.code, '-1') as integer) >= %(analytic_co_dari)s"

        if context.get('analytic_co_sampai'):
            if context.get('analytic_co_sampai').isdigit():
                query_params['analytic_co_sampai'] = int(context['analytic_co_sampai'])
                query += " AND cast(coalesce(a1.code, '9999999999') as integer) <= %(analytic_co_sampai)s"

        if context.get('analytic_bb_dari'):
            if context.get('analytic_bb_dari').isdigit():
                query_params['analytic_bb_dari'] = int(context['analytic_bb_dari'])
                query += " AND cast(coalesce(a2.code, '-1') as integer) >= %(analytic_bb_dari)s"

        if context.get('analytic_bb_sampai'):
            if context.get('analytic_bb_sampai').isdigit():
                query_params['analytic_bb_sampai'] = int(context['analytic_bb_sampai'])
                query += " AND cast(coalesce(a2.code, '9999999999') as integer) <= %(analytic_bb_sampai)s"

        if context.get('analytic_br_dari'):
            if context.get('analytic_br_dari').isdigit():
                query_params['analytic_br_dari'] = int(context['analytic_br_dari'])
                query += " AND cast(coalesce(a3.code, '-1') as integer) >= %(analytic_br_dari)s"

        if context.get('analytic_br_sampai'):
            if context.get('analytic_br_sampai').isdigit():
                query_params['analytic_br_sampai'] = int(context['analytic_br_sampai'])
                query += " AND cast(coalesce(a3.code, '9999999999') as integer) <= %(analytic_br_sampai)s"

        if context.get('analytic_cc_dari'):
            if context.get('analytic_cc_dari').isdigit():
                query_params['analytic_cc_dari'] = int(context['analytic_cc_dari'])
                query += " AND cast(coalesce(a4.code, '-1') as integer) >= %(analytic_cc_dari)s"

        if context.get('analytic_cc_sampai'):
            if context.get('analytic_cc_sampai').isdigit():
                query_params['analytic_cc_sampai'] = int(context['analytic_cc_sampai'])
                query += " AND cast(coalesce(a4.code, '9999999999') as integer) <= %(analytic_cc_sampai)s"

        query += company_clause
        res = cr.mogrify(query, query_params)
        return res

class account_financial_report(osv.osv):
    _inherit = 'account.financial.report'

    _columns = {
        'analytic2_ids': fields.char('Analytic Bisnis Unit'),
        'analytic4_ids': fields.char('Analytic Cost Center'),
    }

    def onchange_analytic4_ids(self, cr, uid, ids, analytic4_ids=None, context=None):
        context and dict(context) or {}
        analytic4_ids = re.findall(r'[0-9][0-9,.]+', analytic4_ids)
        if analytic4_ids:
            analytic4_ids = analytic4_ids[0]
            analytic4_ids = ','.join(analytic4_ids.split(','))
            analytic4_ids = analytic4_ids.rstrip(',')

        childs = self.search(cr, uid, [('id','child_of',ids)], context=context)
        self.write(cr, uid, childs, {'analytic4_ids':analytic4_ids}, context=context)
        res = {'value': {'analytic4_ids':analytic4_ids}}
        return res
