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

CC_SELECTION = [
    ('General','General'),
    ('Sales','Sales'),
    ('Marketing','Marketing'),
    ('Service','Service'),
    ('Sparepart_Accesories','Sparepart & Accesories'),
    ('Finance','Finance'),
    ('Accounting_Budget','Accounting & Budget'),
    ('Tax','Tax'),
    ('BC','BC'),
    ('HRGA','HRGA'),
    ('Mdev','Mdev'),
    ('Training_Culture','Training & Culture'),
    ('IT','IT'),
    ('Other','Other'),
]

class res_partner_bank(osv.osv):
    _inherit = 'res.partner.bank'

    # def _get_is_companys_bank_account(self, cr, uid, ids, name, args, context=None):
    #     res = {}
    #     for line in self.browse(cr, uid, ids, context=context):
    #         res[line.id] = True
    #     return res

    _columns = {
        'is_companys_bank_account': fields.boolean(string='Is Companys Account'),
        # 'is_companys_bank_account': fields.function(
        #     _get_is_companys_bank_account, method=True, type='boolean', string='Company Account',
        #     store=True),
    }

class account_report_functions(osv.osv):
    _inherit = 'res.company'

    def analyitc_list(self, cr, uid, financial_report=False, context=None):
        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
            'debit': "COALESCE(SUM(l.debit), 0) as debit",
            'credit': "COALESCE(SUM(l.credit), 0) as credit",
            'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
        }
        analytic_lines = []
        obj_account = self.pool.get('account.account')
        children_and_consolidated = obj_account._get_children_and_consol(cr, uid, context['account_ids'], context)
        if children_and_consolidated:
            aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
            wheres = [""]
            if aml_query.strip():
                wheres.append(aml_query.strip())
            filters = " AND ".join(wheres)
            table_account_move_line = 'account_move_line'
            if 'konsolidasi' in context and context['konsolidasi'] == True:
                table_account_move_line = 'account_move_line_consol'
            request = ("SELECT l.account_id as id, l.analytic_account_id as analytic_id, " +\
                       ', '.join(mapping.values()) +
                       " FROM " + table_account_move_line + " l " \
                       " LEFT JOIN account_analytic_account a4 on a4.id = l.analytic_account_id " \
                       " LEFT JOIN account_analytic_account a3 on a3.id = a4.analytic_3 " \
                       " LEFT JOIN account_analytic_account a2 on a2.id = a4.analytic_2 " \
                       " LEFT JOIN account_analytic_account a1 on a1.id = a4.analytic_1 " \
                       " WHERE l.account_id IN %s " \
                            + filters +
                       " GROUP BY l.account_id, l.analytic_account_id")
            params = (tuple(children_and_consolidated),)
            cr.execute(request, params)
            for row in cr.dictfetchall():
                analytic = self.pool.get('account.analytic.account').browse(cr, uid, row['analytic_id'])
                if analytic:
                    if financial_report == True:
                        res = {
                            'name': '',
                            'analytic': analytic.analytic_combination,
                            'balance':  row['balance'] != 0 and row['balance'] * context['report_sign'] or row['balance'],
                            'type': analytic.type,
                            'level': 4,
                            'account_type': '',
                        }
                        if context['debit_credit'] == True:
                            res['debit'] = row['debit']
                            res['credit'] = row['credit']
                        if context['enable_filter'] == True:
                            res['balance_cmp'] =  0.0
                    else:
                        res = {
                            'id': analytic.id,
                            'type': analytic.type,
                            'code': '',
                            'name': '',
                            'analytic': analytic.analytic_combination,
                            'level': 0,
                            'debit': row['debit'],
                            'credit': row['credit'],
                            'balance': row['balance'],
                            'parent_id': 0,
                            'bal_type': '',
                        }
                    analytic_lines.append(res)
        return analytic_lines

    def _process_child(self, cr, uid, accounts, disp_acc, parent, result_acc, context):
        account_rec = [acct for acct in accounts if acct['id']==parent][0]
        currency_obj = self.pool.get('res.currency')
        acc_id = self.pool.get('account.account').browse(cr, uid, account_rec['id'])
        currency = acc_id.currency_id and acc_id.currency_id or acc_id.company_id.currency_id
        res = {
            'id': account_rec['id'],
            'type': account_rec['type'],
            'code': account_rec['code'],
            'name': account_rec['name'],
            'analytic': '',
            'level': account_rec['level'],
            'debit': account_rec['debit'],
            'credit': account_rec['credit'],
            'balance': account_rec['balance'],
            'parent_id': account_rec['parent_id'],
            'bal_type': '',
        }
        ctx2 = context.copy()
        ctx2['account_ids'] = [account_rec['id']]
        analytic_lines = self.analyitc_list(cr, uid, context=ctx2)
        if disp_acc == 'movement':
            if not currency_obj.is_zero(cr, uid, currency, res['credit']) or not currency_obj.is_zero(cr, uid, currency, res['debit']) or not currency_obj.is_zero(cr, uid, currency, res['balance']):
                result_acc.append(res)
                result_acc += analytic_lines
        elif disp_acc == 'not_zero':
            if not currency_obj.is_zero(cr, uid, currency, res['balance']):
                result_acc.append(res)
                result_acc += analytic_lines
        else:
            result_acc.append(res)
            result_acc += analytic_lines
        if account_rec['child_id']:
            for child in account_rec['child_id']:
                result_acc = self._process_child(cr, uid, accounts, disp_acc, child, result_acc, context)
        return result_acc

    def lines(self, cr, uid, ids, form, done=None):
        result_acc = []

        obj_account = self.pool.get('account.account')
        ids = 'chart_account_id' in form and [form['chart_account_id']] or []
        if not ids:
            return []
        if not done:
            done={}

        ctx = {}
        ctx['fiscalyear'] = form['fiscalyear_id']
        if form['account_ids']:
            ctx['account_ids'] = form['account_ids']
        if form['journal_ids']:
            ctx['journal_ids'] = form['journal_ids']
        if form['analytic_ids']:
            ctx['analytic_ids'] = form['analytic_ids']
        if form['analytic_co_dari']:
            ctx['analytic_co_dari'] = form['analytic_co_dari']
        if form['analytic_co_sampai']:
            ctx['analytic_co_sampai'] = form['analytic_co_sampai']
        if form['analytic_bb_dari']:
            ctx['analytic_bb_dari'] = form['analytic_bb_dari']
        if form['analytic_bb_sampai']:
            ctx['analytic_bb_sampai'] = form['analytic_bb_sampai']
        if form['analytic_br_dari']:
            ctx['analytic_br_dari'] = form['analytic_br_dari']
        if form['analytic_br_sampai']:
            ctx['analytic_br_sampai'] = form['analytic_br_sampai']
        if form['analytic_cc_dari']:
            ctx['analytic_cc_dari'] = form['analytic_cc_dari']
        if form['analytic_cc_sampai']:
            ctx['analytic_cc_sampai'] = form['analytic_cc_sampai']
        if form['konsolidasi']:
            ctx['konsolidasi'] = form['konsolidasi']
        if form['filter'] == 'filter_period':
            ctx['period_from'] = form['period_from']
            ctx['period_to'] = form['period_to']
        elif form['filter'] == 'filter_date':
            ctx['date_from'] = form['date_from']
            ctx['date_to'] =  form['date_to']
        ctx['state'] = form['target_move']
        parents = ids
        child_ids = obj_account._get_children_and_consol(cr, uid, ids, ctx)
        if child_ids:
            ids = child_ids
        accounts = obj_account.read(cr, uid, ids, ['type','code','name','debit','credit','balance','parent_id','level','child_id'], ctx)

        for parent in parents:
            if parent in done:
                continue
            done[parent] = 1
            result_acc = self._process_child(cr, uid, accounts, form['display_account'], parent, result_acc, ctx)
        return result_acc

    def analytic_values(self, cr, uid, financial_report=False, context=None):
        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
            'debit': "COALESCE(SUM(l.debit), 0) as debit",
            'credit': "COALESCE(SUM(l.credit), 0) as credit",
            'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
        }
        analytic_lines = []
        obj_account = self.pool.get('account.account')
        children_and_consolidated = obj_account._get_children_and_consol(cr, uid, context['account_ids'], context)
        if children_and_consolidated:
            aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
            wheres = [""]
            if aml_query.strip():
                wheres.append(aml_query.strip())
            filters = " AND ".join(wheres)
            table_account_move_line = 'account_move_line'
            if 'konsolidasi' in context and context['konsolidasi'] == True:
                table_account_move_line = 'account_move_line_consol'
            request = ("SELECT l.account_id as id, l.analytic_account_id as analytic_id, " +\
                       ', '.join(mapping.values()) +
                       " FROM " + table_account_move_line + " l " \
                       " LEFT JOIN account_analytic_account a4 on a4.id = l.analytic_account_id " \
                       " LEFT JOIN account_analytic_account a3 on a3.id = a4.analytic_3 " \
                       " LEFT JOIN account_analytic_account a2 on a2.id = a4.analytic_2 " \
                       " LEFT JOIN account_analytic_account a1 on a1.id = a4.analytic_1 " \
                       " WHERE l.account_id IN %s " \
                            + filters +
                       " GROUP BY l.account_id, l.analytic_account_id")
            params = (tuple(children_and_consolidated),)
            cr.execute(request, params)
            for row in cr.dictfetchall():
                analytic = self.pool.get('account.analytic.account').browse(cr, uid, row['analytic_id'])
                if analytic:
                    if financial_report == True:
                        res = {
                            'name': '',
                            'analytic_2': analytic.analytic_combination.split('/')[1],
                            'analytic_4': analytic.analytic_combination.split('/')[3],
                            'analytic': analytic.analytic_combination,
                            'balance':  row['balance'] != 0 and row['balance'] * context['report_sign'] or row['balance'],
                            'type': analytic.type,
                            'level': 4,
                            'account_type': '',
                        }
                        if context['debit_credit'] == True:
                            res['debit'] = row['debit']
                            res['credit'] = row['credit']
                        if context['enable_filter'] == True:
                            res['balance_cmp'] =  0.0
                    else:
                        res = {
                            'id': analytic.id,
                            'type': analytic.type,
                            'code': '',
                            'name': '',
                            'analytic_2': analytic.analytic_combination.split('/')[1],
                            'analytic_4': analytic.analytic_combination.split('/')[3],
                            'analytic': analytic.analytic_combination,
                            'level': 0,
                            'debit': row['debit'],
                            'credit': row['credit'],
                            'balance': row['balance'],
                            'parent_id': 0,
                            'bal_type': '',
                        }
                    analytic_lines.append(res)
        return analytic_lines



    def analytic_lines_value(self, cr, uid, account_line_ids=None, context=None):
        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
            'debit': "COALESCE(SUM(l.debit), 0) as debit",
            'credit': "COALESCE(SUM(l.credit), 0) as credit",
            'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
        }
        analytic_lines = []
        aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        wheres = [""]
        if aml_query.strip():
            wheres.append(aml_query.strip())
        filters = " AND ".join(wheres)
        table_account_move_line = 'account_move_line'
        if 'konsolidasi' in context and context['konsolidasi'] == True:
            table_account_move_line = 'account_move_line_consol'
        request = ("SELECT l.account_id as id, l.analytic_account_id as analytic_id, " +\
                   ', '.join(mapping.values()) +
                   " FROM " + table_account_move_line + " l " \
                   " LEFT JOIN account_analytic_account a4 on a4.id = l.analytic_account_id " \
                   " LEFT JOIN account_analytic_account a3 on a3.id = l.analytic_3 " \
                   " LEFT JOIN account_analytic_account a2 on a2.id = l.analytic_2 " \
                   " LEFT JOIN account_analytic_account a1 on a1.id = l.analytic_1 " \
                   " WHERE l.account_id IN %s " \
                        + filters + 
                   " GROUP BY l.account_id, l.analytic_account_id")
        params = (tuple(account_line_ids),)
        cr.execute(request, params)
        for row in cr.dictfetchall():
            analytic = self.pool.get('account.analytic.account').browse(cr, uid, row['analytic_id'])
            if analytic:
                res = {
                    'name': '',
                    'analytic_2': analytic.analytic_combination.split('/')[1],
                    'analytic_4': analytic.analytic_combination.split('/')[3],
                    'analytic': analytic.analytic_combination,
                    'balance':  row['balance'] != 0 and row['balance'] * context['report_sign'] or row['balance'],
                    'type': analytic.type,
                    'level': 4,
                    'account_type': '',
                }
                if context['debit_credit'] == True:
                    res['debit'] = row['debit']
                    res['credit'] = row['credit']
                if context['enable_filter'] == True:
                    res['balance_cmp'] =  0.0
                analytic_lines.append(res)
        return analytic_lines

    def get_lines(self, cr, uid, ids, data):
        lines = []
        account_obj = self.pool.get('account.account')
        currency_obj = self.pool.get('res.currency')
        afr_obj = self.pool.get('account.financial.report')
        ids2 = afr_obj._get_children_by_order(cr, uid, [data['form']['account_report_id'][0]], context=data['form']['used_context'])

        for report in afr_obj.browse(cr, uid, ids2, context=data['form']['used_context']):
            vals = {
                'name': report.name,
                'analytic': '',
                'balance': report.balance * report.sign or 0.0,
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type =='sum' and 'view' or False, #used to underline the financial report balances
            }

            if data['form']['debit_credit']:
                vals['debit'] = report.debit
                vals['credit'] = report.credit
            if data['form']['enable_filter']:
                vals['balance_cmp'] = afr_obj.browse(cr, uid, report.id, context=data['form']['comparison_context']).balance * report.sign or 0.0

            if report.analytic4_ids and report.type in ['accounts','account_type','sum']:
                account_line_ids = []

                if report.type == 'accounts' and report.account_ids:
                    account_line_ids = [a.id for a in report.account_ids]

                if report.type == 'account_type' and report.account_type_ids:
                    account_line_ids = account_obj.search(cr, uid, [('user_type','in', [x.id for x in report.account_type_ids])])

                if report.type == 'sum':
                    rpt_ids = afr_obj.search(cr, uid, [('id','child_of',report.id)], context=data['form']['used_context'])
                    for rpt_id in afr_obj.browse(cr, uid, rpt_ids, context=data['form']['used_context']):
                        if rpt_id.type == 'accounts' and rpt_id.account_ids:
                            account_line_ids += [a.id for a in rpt_id.account_ids]
                        if rpt_id.type == 'account_type' and rpt_id.account_type_ids:
                            account_line_ids += account_obj.search(cr, uid, [('user_type','in', [x.id for x in rpt_id.account_type_ids])], context=data['form']['used_context'])

                if account_line_ids and report.type in ['accounts','account_type','sum']:
                    ctx2 = data['form']['used_context'].copy()
                    ctx2['report_sign'] = report.sign
                    ctx2['report_name'] = report.name
                    ctx2['debit_credit'] = data['form']['debit_credit']
                    ctx2['enable_filter'] = data['form']['enable_filter']
                    ctx2['comparison_context'] = data['form']['comparison_context']
                    analytic_lines_value = self.analytic_lines_value(cr, uid, account_line_ids, context=ctx2)
                    new_balance = 0.0
                    for alv in analytic_lines_value:
                        if alv['analytic_4'] in report.analytic4_ids:
                            new_balance += alv['balance']
                    vals['balance'] = new_balance

            if report.analytic2_ids and report.type in ['accounts','account_type','sum']:
                account_line_ids = []

                if report.type == 'accounts' and report.account_ids:
                    account_line_ids = [a.id for a in report.account_ids]

                if report.type == 'account_type' and report.account_type_ids:
                    account_line_ids = account_obj.search(cr, uid, [('user_type','in', [x.id for x in report.account_type_ids])])

                if report.type == 'sum':
                    rpt_ids = afr_obj.search(cr, uid, [('id','child_of',report.id)], context=data['form']['used_context'])
                    for rpt_id in afr_obj.browse(cr, uid, rpt_ids, context=data['form']['used_context']):
                        if rpt_id.type == 'accounts' and rpt_id.account_ids:
                            account_line_ids += [a.id for a in rpt_id.account_ids]
                        if rpt_id.type == 'account_type' and rpt_id.account_type_ids:
                            account_line_ids += account_obj.search(cr, uid, [('user_type','in', [x.id for x in rpt_id.account_type_ids])], context=data['form']['used_context'])

                if account_line_ids and report.type in ['accounts','account_type','sum']:
                    ctx2 = data['form']['used_context'].copy()
                    ctx2['report_sign'] = report.sign
                    ctx2['report_name'] = report.name
                    ctx2['debit_credit'] = data['form']['debit_credit']
                    ctx2['enable_filter'] = data['form']['enable_filter']
                    ctx2['comparison_context'] = data['form']['comparison_context']
                    analytic_lines_value = self.analytic_lines_value(cr, uid, account_line_ids, context=ctx2)
                    new_balance = 0.0
                    for alv in analytic_lines_value:
                        if alv['analytic_2'] in report.analytic2_ids:
                            new_balance += alv['balance']
                    vals['balance'] = new_balance

            lines.append(vals)
            account_ids = []
            if report.display_detail == 'no_detail':
                #the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue
            if report.type == 'accounts' and report.account_ids:
                account_ids = account_obj._get_children_and_consol(cr, uid, [x.id for x in report.account_ids])
            elif report.type == 'account_type' and report.account_type_ids:
                account_ids = account_obj.search(cr, uid, [('user_type','in', [x.id for x in report.account_type_ids])])
            if account_ids:
                for account in account_obj.browse(cr, uid, account_ids, context=data['form']['used_context']):
                    #if there are accounts to display, we add them to the lines with a level equals to their level in
                    #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
                    #financial reports for Assets, liabilities...)
                    if report.display_detail == 'detail_flat' and account.type == 'view':
                        continue
                    flag = False
                    vals = {
                        'name': account.code + ' ' + account.name,
                        'analytic': '',
                        'balance':  account.balance != 0 and account.balance * report.sign or account.balance,
                        'type': 'account',
                        'level': report.display_detail == 'detail_with_hierarchy' and min(account.level + 1,6) or 6, #account.level + 1
                        'account_type': account.type,
                    }

                    if data['form']['debit_credit']:
                        vals['debit'] = account.debit
                        vals['credit'] = account.credit
                    if not currency_obj.is_zero(cr, uid, account.company_id.currency_id, vals['balance']):
                        flag = True
                    if data['form']['enable_filter']:
                        vals['balance_cmp'] = account_obj.browse(cr, uid, account.id, context=data['form']['comparison_context']).balance * report.sign or 0.0
                        if not currency_obj.is_zero(cr, uid, account.company_id.currency_id, vals['balance_cmp']):
                            flag = True
                    if flag:
                        lines.append(vals)
                        ctx2 = data['form']['used_context'].copy()
                        ctx2['account_ids'] = [account.id]
                        ctx2['report_sign'] = report.sign
                        ctx2['debit_credit'] = data['form']['debit_credit']
                        ctx2['enable_filter'] = data['form']['enable_filter']
                        ctx2['comparison_context'] = data['form']['comparison_context']
                        analytic_lines = self.analyitc_list(cr, uid, financial_report=True, context=ctx2)
                        lines += analytic_lines
        return lines

class dym_accounting_report(osv.osv_memory):
    _inherit = "accounting.report"
    _description = "Accounting Report"

    _columns = {
        'account_ids': fields.many2many('account.account', 'accounting_report_account_rel', 'ar_id', 'account_id', 'Account'),
        'analytic_ids': fields.many2many('account.analytic.account', 'accounting_report_analytic_rel', 'ar_id', 'analytic_id', 'Analytic'),
        'journal_ids': fields.many2many('account.journal', string='Journals', required=False),
        'konsolidasi' : fields.boolean('Konsolidasi'),
        'analytic_co_dari': fields.many2one('account.analytic.account', string='Analytic Company Dari'),
        'analytic_co_sampai' : fields.many2one('account.analytic.account', string='Analytic Company Sampai'),
        'analytic_bb_dari' : fields.many2one('account.analytic.account', string='Analytic Bisnis Unit Dari'),
        'analytic_bb_sampai' : fields.many2one('account.analytic.account', string='Analytic Bisnis Unit Sampai'),
        'analytic_br_dari' : fields.many2one('account.analytic.account', string='Analytic Branch Dari'),
        'analytic_br_sampai' : fields.many2one('account.analytic.account', string='Analytic Branch Sampai'),
        'analytic_cc_dari' : fields.many2one('account.analytic.account', string='Analytic Cost Center Dari'),
        'analytic_cc_sampai' : fields.many2one('account.analytic.account', string='Analytic Cost Center Sampai'),
    }

    _defaults = {
        'journal_ids': False,
    }

    def onchange_analytic_dari_sampai(self, cr, uid, ids, analytic_co_dari=None, analytic_co_sampai=None, analytic_bb_dari=None, analytic_bb_sampai=None, analytic_br_dari=None, analytic_br_sampai=None, analytic_cc_dari=None, analytic_cc_sampai=None, context=None):
        context = context and dict(context) or {}
        res = {'value': {}}
        return res

    def _build_comparison_context(self, cr, uid, ids, data, context=None):
        res = super(dym_accounting_report, self)._build_comparison_context(cr, uid, ids, data, context=context)

        res['account_report_id'] = 'account_report_id' in data['form'] and data['form']['account_report_id'] or False
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
        res['data']['form']['used_context']['account_report_id'] = 'account_report_id' in data['form'] and data['form']['account_report_id'] or False
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

class dym_account_account_type(osv.osv):
    _inherit = "account.account.type"

    _columns = {
        'report_type': fields.selection([('none','/'),('income', _('Profit & Loss (Income account)')),('expense', _('Profit & Loss (Expense account)')),('asset', _('Balance Sheet (Asset account)')),('liability', _('Balance Sheet (Liability account)'))], help="This field is used to generate legal reports: profit and loss, balance sheet.", string='P&L / BS Category', required=True),
    }

class dym_account_financial_report(osv.osv):
    _inherit = "account.financial.report"
    _description = "Account Report"
    _order = "sequence asc"

class dym_account_account(osv.osv):
    _inherit = "account.account"

    def get_analytic(self, cr, uid, ids, move_line_id):
        analytic = ''
        if move_line_id and move_line_id > 0:
            line = self.pool.get('account.move.line').browse(cr, uid, move_line_id)
            if line:
                analytic = line.analytic_account_id.analytic_combination
        return analytic

    def _compute_balance_consolidated(self, cr, uid, ids, field_names, arg=None, context=None,
                  query='', query_params=()):
        mapping = {
            'consolidate_amount': "COALESCE(SUM(l2.debit),0) - COALESCE(SUM(l2.credit), 0) as consolidate_amount",
        }
        res = {}
        children_and_consolidated = self._get_children_and_consol(cr, uid, ids, context=context)
        consolidate_amount = 0
        consolidate_balance = 0
        if children_and_consolidated:
            aml_query = self.pool.get('account.move.line')._query_get_consolidate(cr, uid, context=context)
            wheres = [""]
            if query.strip():
                wheres.append(query.strip())
            if aml_query.strip():
                wheres.append(aml_query.strip())
            filters = " AND ".join(wheres)
            request = ("SELECT l1.account_id as account_id, " +\
                       ', '.join(mapping.values()) +
                       " FROM account_move_line l1, account_move_line_consol l2" \
                       " WHERE l2.consolidation_move_line_id = l1.id and" \
                       " l1.account_id IN %s" \
                            + filters +
                       " GROUP BY l1.account_id")
            params = (tuple(children_and_consolidated),) + query_params
            cr.execute(request, params)
            rows = {}
            for row in cr.dictfetchall():
                account_id = row['account_id']
                consolidate_amount = row['consolidate_amount']
                consolidate_balance = self.browse(cr, uid, account_id).balance + consolidate_amount
                rows[account_id] = {
                    'consolidate_amount': consolidate_amount,
                    'consolidate_balance': consolidate_balance,
                }
            request = ("SELECT l1.account_id as account_id, l2.id as line_id " + \
               " FROM account_move_line l1, account_move_line_consol l2" \
               " WHERE l2.consolidation_move_line_id = l1.id and" \
               " l1.account_id IN %s" \
                    + filters)
            params = (tuple(children_and_consolidated),) + query_params
            cr.execute(request, params)
            for row in cr.dictfetchall():
                if 'eliminate_line_ids' not in rows[row['account_id']]:
                    rows[row['account_id']]['eliminate_line_ids'] = []
                rows[row['account_id']]['eliminate_line_ids'] += [row['line_id']]
            for id in ids:
                res[id] = rows[id] if id in rows else {'consolidate_amount':0, 'consolidate_balance':0, 'eliminate_line_ids': []}
        else:
            for id in ids:
                res[id] = {'consolidate_amount':0, 'consolidate_balance':0, 'eliminate_line_ids': []}
        return res

    def _set_credit_debit(self, cr, uid, account_id, name, value, arg, context=None):
        if context.get('config_invisible', True):
            return True

        account = self.browse(cr, uid, account_id, context=context)
        diff = value - getattr(account,name)
        if not diff:
            return True

        journal_obj = self.pool.get('account.journal')
        jids = journal_obj.search(cr, uid, [('type','=','situation'),('centralisation','=',1),('company_id','=',account.company_id.id)], context=context)
        if not jids:
            raise osv.except_osv(_('Error!'),_("You need an Opening journal with centralisation checked to set the initial balance."))

        period_obj = self.pool.get('account.period')
        pids = period_obj.search(cr, uid, [('special','=',True),('company_id','=',account.company_id.id)], context=context)
        if not pids:
            raise osv.except_osv(_('Error!'),_("There is no opening/closing period defined, please create one to set the initial balance."))

        move_obj = self.pool.get('account.move.line')
        move_id = move_obj.search(cr, uid, [
            ('journal_id','=',jids[0]),
            ('period_id','=',pids[0]),
            ('account_id','=', account_id),
            (name,'>', 0.0),
            ('name','=', _('Opening Balance'))
        ], context=context)
        if move_id:
            move = move_obj.browse(cr, uid, move_id[0], context=context)
            move_obj.write(cr, uid, move_id[0], {
                name: diff+getattr(move,name)
            }, context=context)
        else:
            if diff<0.0:
                raise osv.except_osv(_('Error!'),_("Unable to adapt the initial balance (negative value)."))
            nameinv = (name=='credit' and 'debit') or 'credit'
            move_id = move_obj.create(cr, uid, {
                'name': _('Opening Balance'),
                'account_id': account_id,
                'journal_id': jids[0],
                'period_id': pids[0],
                name: diff,
                nameinv: 0.0
            }, context=context)
        return True

    def __compute(self, cr, uid, ids, field_names, arg=None, context=None,
                  query='', query_params=()):
        """ compute the balance, debit and/or credit for the provided
        account ids
        Arguments:
        `ids`: account ids
        `field_names`: the fields to compute (a list of any of
                       'balance', 'debit' and 'credit')
        `arg`: unused fields.function stuff
        `query`: additional query filter (as a string)
        `query_params`: parameters for the provided query string
                        (__compute will handle their escaping) as a
                        tuple
        """
        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
            'debit': "COALESCE(SUM(l.debit), 0) as debit",
            'credit': "COALESCE(SUM(l.credit), 0) as credit",
            # by convention, foreign_balance is 0 when the account has no secondary currency, because the amounts may be in different currencies
            'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
        }
        children_and_consolidated = self._get_children_and_consol(cr, uid, ids, context=context)

        acc_ts = self.pool.get('account.account').search(cr, uid, [], context=context)
        acc_ts = self.pool.get('account.account').browse(cr, uid, acc_ts, context=context)
        acc_ts = dict([(a.id,a.name) for a in acc_ts])

        accounts = {}
        res = {}
        null_result = dict((fn, 0.0) for fn in field_names)
        if children_and_consolidated:
            aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
            wheres = [""]
            if query.strip():
                wheres.append(query.strip())
            if aml_query.strip():
                wheres.append(aml_query.strip())
            filters = " AND ".join(wheres)
            table_account_move_line = 'account_move_line'
            if 'konsolidasi' in context and context['konsolidasi'] == True:
                table_account_move_line = 'account_move_line_consol'

            request = ("SELECT l.account_id as id, " +\
                       ', '.join(mapping.values()) +
                       " FROM " + table_account_move_line + " l " \
                       " LEFT JOIN account_analytic_account a4 on a4.id = l.analytic_account_id " \
                       " LEFT JOIN account_analytic_account a3 on a3.id = l.analytic_3 " \
                       " LEFT JOIN account_analytic_account a2 on a2.id = l.analytic_2 " \
                       " LEFT JOIN account_analytic_account a1 on a1.id = l.analytic_1 " \
                       " WHERE l.account_id IN %s " \
                            + filters +
                       " GROUP BY l.account_id")

            params = (tuple(children_and_consolidated),) + query_params
            cr.execute(request, params)
            rows = cr.dictfetchall()
            for row in rows:
                accounts[row['id']] = row

            # consolidate accounts with direct children
            children_and_consolidated.reverse()
            brs = list(self.browse(cr, uid, children_and_consolidated, context=context))
            sums = {}
            currency_obj = self.pool.get('res.currency')
            while brs:
                current = brs.pop(0)
                for fn in field_names:
                    sums.setdefault(current.id, {})[fn] = accounts.get(current.id, {}).get(fn, 0.0)
                    for child in current.child_id:
                        if child.company_id.currency_id.id == current.company_id.currency_id.id:
                            sums[current.id][fn] += sums[child.id][fn]
                        else:
                            sums[current.id][fn] += currency_obj.compute(cr, uid, child.company_id.currency_id.id, current.company_id.currency_id.id, sums[child.id][fn], context=context)

                # as we have to relay on values computed before this is calculated separately than previous fields
                if current.currency_id and current.exchange_rate and \
                            ('adjusted_balance' in field_names or 'unrealized_gain_loss' in field_names):
                    # Computing Adjusted Balance and Unrealized Gains and losses
                    # Adjusted Balance = Foreign Balance / Exchange Rate
                    # Unrealized Gains and losses = Adjusted Balance - Balance
                    adj_bal = sums[current.id].get('foreign_balance', 0.0) / current.exchange_rate
                    sums[current.id].update({'adjusted_balance': adj_bal, 'unrealized_gain_loss': adj_bal - sums[current.id].get('balance', 0.0)})

            for id in ids:
                res[id] = sums.get(id, null_result)
        else:
            for id in ids:
                res[id] = null_result
        return res

    _columns = {
        'analytical_account': fields.one2many('account.analytic.account','natural_account',string="Analytical Account",domain=[('type','=','normal')], readonly=True),
        'analytical_account_ids': fields.many2many('account.analytic.account','account_analytic_rel', 'account_id', 'analytic_id', string="Analytical Account Mapping",domain=[('type','=','normal'),('segmen','=','4')], readonly=False),
        'group_account': fields.many2one('account.account', string='Group Account', domain="[('type','not in',['view','consolidation']),('company_id','=',company_id)]", copy=False),
        'consolidate_balance': fields.function(_compute_balance_consolidated, digits_compute=dp.get_precision('Account'), string='Eliminanted Balance', multi='sums'),
        'consolidate_amount': fields.function(_compute_balance_consolidated, digits_compute=dp.get_precision('Account'), string='Eliminanted Amount', multi='sums'),
        'eliminate_line_ids': fields.function(_compute_balance_consolidated, type='one2many', relation="account.move.line", string="Eliminate Line", multi='sums', readonly=True),
        'balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Balance', multi='balance'),
        'credit': fields.function(__compute, fnct_inv=_set_credit_debit, digits_compute=dp.get_precision('Account'), string='Credit', multi='balance'),
        'debit': fields.function(__compute, fnct_inv=_set_credit_debit, digits_compute=dp.get_precision('Account'), string='Debit', multi='balance'),
        'foreign_balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Foreign Balance', multi='balance',
            help="Total amount (in Secondary currency) for transactions held in secondary currency for this account."),
        'adjusted_balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Adjusted Balance', multi='balance',
            help="Total amount (in Company currency) for transactions held in secondary currency for this account."),
        'unrealized_gain_loss': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Unrealized Gain or Loss', multi='balance',
            help="Value of Loss or Gain due to changes in exchange rate when doing multi-currency transactions."),
        'analytic_filter_ids': fields.one2many('analytic.account.filter', 'account_id', string='Analytic Filter'),
    }

    def name_get(self, cr, uid, ids, context=None):
        res = super(dym_account_account, self).name_get(cr, uid, ids, context=context)
        if not ids:
            return []
        if isinstance(ids, (int, long)):
                    ids = [ids]
        reads = self.read(cr, uid, ids, ['name', 'code','company_id'], context=context)

        res = []
        for record in reads:
            name = record['name']
            if record['code']:
                name = record['code'] + ' ' + name
            res.append((record['id'], name))
        return res
    
class dym_account_move_line_cost(osv.osv):
    _inherit = 'account.move.line'

    _columns = {    
        'product_cost_id': fields.many2one('product.product', string='Product Cost ID'),
        'product_cost_price': fields.float('Product Cost Price'),
    }

class dym_product_category(osv.osv):
    _inherit = 'product.category'

    _columns = {    
        'bisnis_unit' : fields.boolean(string='Bisnis Unit'),
    }

class dym_account_analytic(osv.osv):
    _inherit = "account.analytic.account"

    def _cek_is_group(self, cr, uid, ids, name, args, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            res[val.id] = True if not val.company_id.parent_id else False
        return res

    def _get_analytic_combination(self, cr, uid, ids, name, args, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            analytic_name = ''
            analytic_1 = self.browse(cr, uid, [])
            analytic_2 = self.browse(cr, uid, [])
            analytic_3 = self.browse(cr, uid, [])
            analytic_4 = self.browse(cr, uid, [])
            analytic = val
            if analytic.type == 'normal':
                if analytic.segmen == 1:
                    analytic_1 = analytic
                if analytic.segmen == 2:
                    analytic_2 = analytic
                if analytic.segmen == 3:
                    analytic_3 = analytic
                if analytic.segmen == 4:
                    analytic_4 = analytic
            while (analytic.parent_id):
                analytic = analytic.parent_id
                if analytic.type == 'normal':
                    if analytic.segmen == 1:
                        analytic_1 = analytic
                    if analytic.segmen == 2:
                        analytic_2 = analytic
                    if analytic.segmen == 3:
                        analytic_3 = analytic
                    if analytic.segmen == 4:
                        analytic_4 = analytic
            analytic_2_code = analytic_2.code
            analytic_2_branch = analytic_2_code
            if analytic_2_code in ['210','220','230']:
                if analytic_3.sudo().branch_id.branch_status == 'H123':
                    analytic_2_branch = analytic_2_code[:2] + '1'
                elif analytic_3.sudo().branch_id.branch_status == 'H23':
                    analytic_2_branch = analytic_2_code[:2] + '2'
                else:
                    analytic_2_branch = analytic_2_code            
            analytic_name = (str(analytic_1.code) or '') + ('/' + str(analytic_2_branch) or '') + ('/' + str(analytic_3.code) or '') + ( '/' + str(analytic_4.code) or '')
            res[val.id] = analytic_name
        return res

    def _get_parent_segmen(self, cr, uid, ids, name, args, context):
        res = {}
        for analytic in self.browse(cr, uid, ids):
            res[analytic.id] = (analytic.segmen or 0) - 1
        return res

    def _get_analytic(self, cr, uid, ids, name, args, context=None):
        rs_data = {}
        for val in self.browse(cr, uid, ids, context=context):
            res = {
                'analytic_1' : False,
                'analytic_2' : False,
                'analytic_3' : False,
            }
            if val.segmen == 4 and val.type == 'normal':
                analytic = val
                if analytic.type == 'normal':
                    if analytic.segmen == 1 and not val.analytic_1:
                        res['analytic_1'] = analytic.id
                    if analytic.segmen == 2 and not val.analytic_2:
                        res['analytic_2'] = analytic.id
                    if analytic.segmen == 3 and not val.analytic_3:
                        res['analytic_3'] = analytic.id
                while (analytic.parent_id):
                    analytic = analytic.parent_id
                    if analytic.type == 'normal':
                        if analytic.segmen == 1 and not val.analytic_1:
                            res['analytic_1'] = analytic.id
                        if analytic.segmen == 2 and not val.analytic_2:
                            res['analytic_2'] = analytic.id
                        if analytic.segmen == 3 and not val.analytic_3:
                            res['analytic_3'] = analytic.id
                rs_data[val.id] = res
        return rs_data

    def _cek_kombinasi(self, cr, uid, obj, name, args, context=None):
        res = ['&','&','&']
        for field, operator, value in args:
            if not value:
                raise osv.except_osv(('Perhatian !'), ("Ada transaksi / jurnal yang tidak ada data analyticnya, tapi saya juga gak tahu yang mana. Coba minta bantuan sama orang IT, tolong buatkan query 'select date,name,debit,credit from account_move_line where analytic_account_id is null;', kalau sudah ketemu, tolong lengkapi accout analyticnya."))
            segmen = value.split('/')
            if len(segmen) != 4:
                raise osv.except_osv(('Perhatian !'), ("Mohon lengkapi segmen! ex: %s")%('seg1/seg2/seg3/seg4'))
            if segmen[1][:1] == '2':
                segmen[1] = segmen[1][:2] + '0'
            res.append(('analytic_1.code', operator, segmen[0]))
            res.append(('analytic_2.code', operator, segmen[1]))
            res.append(('analytic_3.code', operator, segmen[2]))
            res.append(('code', operator, segmen[3]))
        return res

    _columns = {    
        'is_group': fields.function(_cek_is_group, string='Is Group', type="boolean"),
        'analytic_konsolidasi_ids': fields.many2many('account.analytic.account', 'analytic_konsolidasi_analytic_rel', 'analytic_id', 'analytic2_id', 'Analytic Konsolidasi'),
        'natural_account' : fields.many2one('account.account', string='Natural Account',domain=[('type','!=','view')]),
        'parent_code' : fields.related('parent_id', 'code', string='Parent Code', type='char'),
        'segmen':fields.selection([(1,'Company'),(2,'Bisnis Unit'),(3,'Branch'),(4,'Cost Center')], 'Segmen'),
        'branch_id': fields.many2one('dym.branch', 'Branch'),
        'bisnis_unit': fields.many2one('product.category', 'Bisnis Unit', domain=[('bisnis_unit','=',True)]),
        'cost_center':fields.selection(CC_SELECTION, 'Cost Center'),
        'parent_ids': fields.many2many('account.analytic.account', 'account_analytic_account_analytic_rel', 'analytic_id', 'analytic2_id', 'Parent'),
        'analytic_combination': fields.function(_get_analytic_combination, string='Analytic Combination', type="char", fnct_search=_cek_kombinasi),
        'parent_segmen': fields.function(_get_parent_segmen, string='Parent Segmen', type="integer",
            store={
                'account.analytic.account': (lambda self, cr, uid, ids, c={}: ids, ['segmen'], 10),
                }, help="Parent Segmen."),
        'analytic_1': fields.function(_get_analytic, multi="analytic", type="many2one", string='Account Analytic Company', relation='account.analytic.account', store={
                'account.analytic.account': (lambda self, cr, uid, ids, c={}: ids, ['parent_id','segmen','type','company_id','parent_id','child_id','child_complete_ids'], 10),
                }),
        'analytic_2': fields.function(_get_analytic, multi="analytic", type="many2one", string='Account Analytic Bisnis Unit', relation='account.analytic.account', store={
                'account.analytic.account': (lambda self, cr, uid, ids, c={}: ids, ['parent_id','segmen','type''bisnis_unit','parent_id','child_id','child_complete_ids'], 10),
                }),
        'analytic_3': fields.function(_get_analytic, multi="analytic", type="many2one", string='Account Analytic Branch', relation='account.analytic.account', store={
                'account.analytic.account': (lambda self, cr, uid, ids, c={}: ids, ['parent_id','segmen','type''branch_id','parent_id','child_id','child_complete_ids'], 10),
                }),
    }

    def name_get(self, cr, uid, ids, context=None):
        res = []
        if not ids:
            return res
        if isinstance(ids, (int, long)):
            ids = [ids]
        for id in ids:
            elmt = self.browse(cr, uid, id, context=context)
            if ('params' in context and 'model' in context['params'] and context['params']['model'] == 'account.analytic.account') or ('params_model' in context and context['params_model'] == 'account.analytic.account'):
                res.append((id, elmt.code + ' ' + self._get_one_full_name(elmt)))
            else:
                res.append((id, elmt.code + ' ' + elmt.name))
        return res

    def copy(self, cr, uid, id, default=None, context=None, done_list=None, local=False):
        default = {} if default is None else default.copy()
        if done_list is None:
            done_list = []
        analytic = self.browse(cr, uid, id, context=context)
        new_child_ids = []
        default.update(code=_("%s (copy)") % (analytic['code'] or ''),name=_("%s (copy)") % (analytic['name'] or ''))
        if not local:
            done_list = []
        if analytic.id in done_list:
            return False
        done_list.append(analytic.id)
        if analytic:
            for child in analytic.child_ids:
                child_ids = self.copy(cr, uid, child.id, default, context=context, done_list=done_list, local=True)
                if child_ids:
                    new_child_ids.append(child_ids)
            default['child_ids'] = [(6, 0, new_child_ids)]
        else:
            default['child_ids'] = False
        return super(dym_account_analytic, self).copy(cr, uid, id, default, context=context)


    def get_analytical(self, cr, uid, branch, bu_name, categ, level, cc):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        if type(branch)==int:
            branch = self.pool.get('dym.branch').browse(cr, uid, [branch])
        if branch.company_id:
            company = branch.company_id
        level_1_ids = self.search(cr, uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if level == 1 and level_1_ids:
            return level_1_ids[0], False, False, False
        elif not level_1_ids: 
            raise osv.except_osv(('Perhatian !'), ("Konfigurasi analytic untuk segmen company '%s' belum lengkap, silahkan setting dulu")%(company.name))
        bu_ids = []
        if categ:
            if categ.bisnis_unit:
                bu_ids = [categ.id]
                bu_name = categ.name
            else:
                while (categ.parent_id):
                    categ = categ.parent_id
                    if categ.bisnis_unit and not bu_ids:
                        bu_ids = [categ.id]
                        bu_name = categ.name
                        break

            if bu_name == 'Finance':
                bu_name = 'Umum'            

            if not bu_name:
                raise osv.except_osv(('Perhatian !'), ("tidak ditemukan data analytic untuk kategori %s")%(categ.name))
        elif bu_name:

            if bu_name == 'Finance':
                bu_name = 'Umum'            

            bu_ids = self.pool.get('product.category').search(cr, uid, [('name','=',bu_name),('bisnis_unit','=',True)])
        level_2_ids = self.search(cr, uid, [('segmen','=',2),('bisnis_unit','in',bu_ids),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',level_1_ids)])

        if level == 2 and level_2_ids:
            return level_1_ids[0], level_2_ids[0], False, False
        elif not level_2_ids: 
            raise osv.except_osv(('Perhatian !'), ("Konfigurasi analytic untuk segmen bisnis unit '%s' belum lengkap, silahkan setting dulu")%(bu_name))
        level_3_ids = self.search(cr, uid, [('segmen','=',3),('branch_id','=',branch.id),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',level_2_ids)])

        if level == 3 and level_3_ids:
            return level_1_ids[0], level_2_ids[0], level_3_ids[0], False
        elif not level_3_ids: 
            raise osv.except_osv(('Perhatian !'), ("Konfigurasi analytic untuk segmen branch '%s' belum lengkap, silahkan setting dulu")%(branch.name))
        level_4_ids = self.search(cr, uid, [('segmen','=',4),('cost_center','=',cc),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',level_3_ids)])
        if level == 4 and level_4_ids:
            return level_1_ids[0], level_2_ids[0], level_3_ids[0], level_4_ids[0]
        elif not level_4_ids: 
            raise osv.except_osv(('Perhatian !'), ("Konfigurasi analytic untuk segmen cost center '%s' belum lengkap, silahkan setting dulu")%(cc))

    def onchange_segmen(self,cr,uid,ids,segmen):
        return {'value':{'parent_segmen':(segmen or 0) - 1}}

class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def name_get(self, cr, uid, ids, context=None):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Supplier Invoice'),
            'out_refund': _('Refund'),
            'in_refund': _('Supplier Refund'),
        }

        result = []
        for inv in self.browse(cr, uid , ids):
            supp_invoice = ''
            if inv.supplier_invoice_number:
                supp_invoice = ' [' + inv.supplier_invoice_number + ']'
            result.append((inv.id, "%s %s %s" % (inv.number or TYPES[inv.type], inv.name or '', supp_invoice or '')))
        return result
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name and len(name) >= 3:
            recs = self.search([('number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('supplier_invoice_number', operator, name)] + args, limit=limit)
        return recs.name_get()

    def do_merge(self, cr, uid, ids, context=None):
        #TOFIX: merged order line should be unlink
        def make_key(br, fields):
            list_key = []
            for field in fields:
                field_val = getattr(br, field)
                if field in ('product_id', 'account_analytic_id'):
                    if not field_val:
                        field_val = False
                if isinstance(field_val, browse_record):
                    field_val = field_val.id
                elif isinstance(field_val, browse_null):
                    field_val = False
                elif isinstance(field_val, browse_record_list):
                    field_val = ((6, 0, tuple([v.id for v in field_val])),)
                list_key.append((field, field_val))
            list_key.sort()
            return tuple(list_key)
        context = dict(context or {})

        # Compute what the new orders should contain
        new_invoices = {}
        invoice_lines_to_move = {}
        for ainvoice in [invoice for invoice in self.browse(cr, uid, ids, context=context) if invoice.state == 'draft']:
            invoice_key = make_key(ainvoice, ('partner_id', 'branch_id', 'division', 'asset', 'account_id', 'journal_id','tipe','type','analytic_1','analytic_2','analytic_3','analytic_4'))
            new_invoice = new_invoices.setdefault(invoice_key, ({}, []))
            new_invoice[1].append(ainvoice.id)
            invoice_infos = new_invoice[0]
            invoice_lines_to_move.setdefault(invoice_key, [])

            if not invoice_infos:
                invoice_infos.update({
                    'branch_id': ainvoice.branch_id.id,
                    'division': ainvoice.division,
                    'origin': ainvoice.origin,
                    'date': date.today(),
                    'partner_id': ainvoice.partner_id.id,
                    'state': 'draft',
                    'name': ainvoice.name,
                    'reference': ainvoice.reference,
                    'account_id': ainvoice.account_id.id,
                    'journal_id': ainvoice.journal_id.id,
                    'type': ainvoice.type,
                    'invoice_line': {},
                    'fiscal_position': ainvoice.fiscal_position.id or False,
                    'payment_term': ainvoice.payment_term.id or False,
                    'company_id': ainvoice.company_id.id,
                    'tipe': ainvoice.tipe,
                    'asset': ainvoice.asset,
                    'partner_type': ainvoice.partner_type.id or False,
                    'reference_type': 'none',
                    'analytic_1': ainvoice.analytic_1.id,
                    'analytic_2': ainvoice.analytic_2.id,
                    'analytic_3': ainvoice.analytic_3.id,
                    'analytic_4': ainvoice.analytic_4.id,
                })
            else:
                if ainvoice.partner_type.id != False:
                    invoice_infos['partner_type'] = ainvoice.partner_type.id
                if ainvoice.origin:
                    invoice_infos['origin'] = (invoice_infos['origin'] or '') + ' ' + ainvoice.origin
                if ainvoice.name:
                    invoice_infos['name'] = (invoice_infos['name'] or '') + ' ' + ainvoice.name
                if ainvoice.reference:
                    invoice_infos['reference'] = (invoice_infos['reference'] or '') + ' ' + ainvoice.reference

            invoice_lines_to_move[invoice_key] += [line.id for line in ainvoice.invoice_line]

        allinvoices = []
        invoices_info = {}
        for invoice_key, (invoice_data, old_ids) in new_invoices.iteritems():
            # skip merges with only one shipment
            if len(old_ids) < 2:
                allinvoices += (old_ids or [])
                continue

            # cleanup picking line data
            for key, value in invoice_data['invoice_line'].iteritems():
                del value['uom_factor']
                value.update(dict(key))
            invoice_data['invoice_line'] = [(6, 0, invoice_lines_to_move[invoice_key])]

            # create the new shipment
            context.update({'mail_create_nolog': True})
            newinvoice_id = self.create(cr, uid, invoice_data)
            self.message_post(cr, uid, [newinvoice_id], body=_("Invoice created"), context=context)
            invoices_info.update({newinvoice_id: old_ids})
            allinvoices.append(newinvoice_id)
            self.button_reset_taxes(cr, uid, [newinvoice_id])
            inv = self.browse(cr, uid, [newinvoice_id])
            if inv.tipe == 'purchase' and inv.type == 'in_invoice':
                po_search = self.pool.get('purchase.order').search(cr, uid, [('invoice_ids','in',old_ids)])
                po_browse = self.pool.get('purchase.order').browse(cr, uid, po_search)
                po_browse.write({'invoice_ids': [(6, 0, [newinvoice_id])]})
                cr.execute('UPDATE wkf_instance SET res_id = %s WHERE res_id in %s and res_type = %s', (newinvoice_id, tuple(old_ids), str(self)))
                    
            #make triggers pointing to the old pickings point to the new order
            self.unlink(cr, uid , old_ids)
        if not invoices_info:
            raise osv.except_osv(_('Attention!'), _('Nomor supplier invoice yang akan di merge harus sama!'))
        return invoices_info 

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')       
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False              
        return branch_ids
    
    def _check_product_jasa(self, cr, uid, ids, name, args, context):
        res = {}
        for inv in self.browse(cr, uid, ids):
            product_jasa = False
            for line in inv.invoice_line:
                if line.product_id.categ_id.get_root_name() == 'Service':
                    product_jasa = True
                    break
            res[inv.id] = product_jasa
        return res

    _columns = {    
        'bast_jasa':fields.char(string='BAST Jasa'),
        'product_jasa': fields.function(_check_product_jasa, string='Produk Jasa', type="boolean"),
        'branch_id' : fields.many2one('dym.branch', string='Branch', required=True),
        'division' : fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], string='Division', change_default=True, select=True),
        'lot_id' : fields.many2one('stock.production.lot',string='No. Mesin'),
        'qq_id' : fields.many2one('res.partner',string='QQ'),
        'qq2_id': fields.many2many('res.partner','acinv_partner_rel','invoice_id','partner_id',string='QQ',required=False),
        'tipe' : fields.selection([('customer','Customer'),('finco','Finco'),('ps_ahm','Program Subsidi AHM'),('ps_md','Program Subsidi MD'),('ps_finco','Program Subsidi Finco'),('bb_md','Barang Bonus MD'),('bb_finco','Barang Bonus Finco'),('bbn','BBN'),('insentif','Insentif'),('hc','Hutang Komisi'),('blind_bonus_beli','Blind Bonus Beli')]),
        'validate_date': fields.date('Validate Date'),
        'confirm_uid':fields.many2one('res.users',string="Validated by"),
        'confirm_date':fields.datetime('Validated on'),
        'cancel_uid':fields.many2one('res.users',string="Set to draft by"),
        'cancel_date':fields.datetime('Set to draft on'),
        'document_date':fields.date('Supplier Invoice Date'),
        'pajak_gunggung':fields.boolean('Tanpa Faktur Pajak'),
        'pajak_gabungan':fields.boolean('Faktur Pajak Gabungan'),
        'no_faktur_pajak':fields.char(string='No Faktur Pajak'),
        'tgl_faktur_pajak':fields.date(string='Tgl Faktur Pajak'),
        'date_invoice' : fields.date(string='Date',
            readonly=True, states={'draft': [('readonly', False)]}, index=True,
            help="Keep empty to use the current date", copy=False),
        'transaction_id': fields.integer('Transaction ID'),
        'model_id': fields.many2one('ir.model','Model'),
        'asset':fields.boolean('Asset'),
        'is_pedagang_eceran': fields.related('branch_id', 'is_pedagang_eceran', relation='dym.branch',type='boolean',string='Pedagang Eceran',store=False),        
        'partner_type':fields.many2one('dym.partner.type',string="Partner Type",domain="[('division','like',division)]"),
        'faktur_pajak_id':fields.many2one('dym.faktur.pajak.out',string='No Faktur Pajak'),
        'faktur_pajak_tgl': fields.related('faktur_pajak_id', 'date', relation='dym.faktur_pajak_out',type='date',string='Tgl Faktur Pajak',store=False),
        'create_manual': fields.boolean('Manual Created'),
   }

    def onchange_gabungan_gunggung(self,cr,uid,ids,gabungan_gunggung,pajak_gabungan,pajak_gunggung,context=None):
        value = {}
        if gabungan_gunggung == 'pajak_gabungan' and pajak_gabungan == True:
            value['pajak_gunggung'] = False
        if gabungan_gunggung == 'pajak_gunggung' and pajak_gunggung == True:
            value['pajak_gabungan'] = False
        return {'value':value}

    def change_create_manual(self,cr,uid,ids,create_manual,context=None):
        val = {}
        val['create_manual'] = True
        return {'value':val}

    def onchange_partner_type(self,cr,uid,ids,partner_type,context=None):
        dom={}        
        val={}
        if partner_type:
            domain_search = []
            obj_partner_type = self.pool.get('dym.partner.type').browse(cr, uid, [partner_type])
            if obj_partner_type.field_type == 'boolean':
                domain_search += [(obj_partner_type.name,'!=',False)]
            elif obj_partner_type.field_type == 'selection':
                domain_search += [(obj_partner_type.selection_name,'=',obj_partner_type.name)]
            dom['partner_id'] = domain_search
            val['partner_id'] = False
        return {'domain':dom,'value':val} 
        
    def faktur_pajak_change(self,cr,uid,ids,no_faktur_pajak,context=None):   
        value = {}
        warning = {}
        if no_faktur_pajak :
            cek = no_faktur_pajak.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Nomor Faktur Pajak Hanya Boleh Angka ! ')),
                }
                value = {
                         'no_faktur_pajak':False
                         }     
        return {'warning':warning,'value':value} 
        
    _defaults = {
        'branch_id' : _get_default_branch,
        'date_invoice': fields.date.context_today,
    }
    
    def get_ponumber(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)
        try:
            po = self.pool.get('purchase.order').search(cr,uid,[('name','in',val.origin.split(' ') or '')])
            po_browse = self.pool.get('purchase.order').browse(cr,uid,po)[0]
            return po_browse.name   
        except Exception as e:
            return "-"

    def invoice_validate(self, cr, uid, ids, context=None):
        res = super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        tgl = time.strftime('%Y-%m-%d')

        self.write(cr, uid, ids, {'confirm_uid':uid,'confirm_date':datetime.now(),'date_invoice':datetime.today()}, context=context)
        val = self.browse(cr,uid,ids)
        price_group = {}
        if val.division == 'Umum' :
            po = self.pool.get('purchase.order').search(cr,uid,[
                ('name','in',val.origin.split(' ') or '')
            ])
            if po :
                asset_pool = self.pool.get('account.asset.asset')
                po_browse = self.pool.get('purchase.order').browse(cr,uid,po)[0]
                for x in val.invoice_line :
                    price_group[x.product_id.id] = x.price_subtotal / x.quantity
                    asset = asset_pool.search(cr,uid,[
                        ('purchase_id','=',po_browse.id),
                        ('product_id','=',x.product_id.id),
                        ('state','in',('draft','open'))
                    ])
                    if asset :
                        asset_data = asset_pool.browse(cr,uid,asset) 
                        for y in asset_data :
                            if y.purchase_value != x.price_subtotal / x.quantity :
                                if y.state == 'draft' :
                                    y.write({'purchase_value':x.price_subtotal / x.quantity})
                                    asset_pool.compute_depreciation_board(cr,uid,y.id,context=context)
                                elif y.state == 'open' :
                                    asset_pool.set_to_draft(cr,uid,y.id,context=context)
                                    y.write({'purchase_value':x.price_subtotal / x.quantity})
                                    asset_pool.compute_depreciation_board(cr,uid,y.id,context=context)
                                    asset_pool.validate(cr,uid,y.id,context=context)

        if val.amount_tax and not val.pajak_gabungan and not val.pajak_gunggung and (val.create_manual == True or val.type != 'out_invoice'):
            if not val.tgl_faktur_pajak or not val.no_faktur_pajak:
                raise osv.except_osv(_('Attention!'), _('Total tax belum dihitung, mohon klik tombol update di amount tax!'))
            model = self.pool.get('ir.model').search(cr,uid,[
                                                         ('model','=',val.__class__.__name__)
                                                         ])
            if val.type == 'out_invoice':
                self.pool.get('dym.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'account.invoice',context=context) 
            else:
                in_out = 'in'
                if val.type == 'in_refund':
                    in_out = 'out'
                faktur_pajak_id = self.pool.get('dym.faktur.pajak.out').create(cr, uid, {
                    'name': val.no_faktur_pajak,
                    'state': 'close',
                    'thn_penggunaan' : int(val.tgl_faktur_pajak[:4]),
                    'tgl_terbit' : val.tgl_faktur_pajak,
                    'model_id':model[0],
                    'amount_total':val.amount_total,
                    'untaxed_amount':val.amount_untaxed,
                    'tax_amount':val.amount_tax,                                                    
                    'state':'close',
                    'transaction_id':val.id,
                    'date':val.date_invoice,
                    'partner_id':val.partner_id.id,
                    'company_id':1,
                    'in_out':in_out,
                }, context=context)
                self.write(cr, uid, ids, {'faktur_pajak_id':faktur_pajak_id}, context=context)
        if val.amount_tax and val.pajak_gunggung == True :   
            self.pool.get('dym.faktur.pajak.out').create_pajak_gunggung(cr,uid,ids,'account.invoice',context=context)
        return res

    def _get_accounting_data_for_valuation(self, cr, uid, product, context=None):
        product_obj = self.pool.get('product.template')
        accounts = product_obj.get_product_accounts(cr, uid, product.product_tmpl_id.id, context)
        acc_src = accounts['stock_account_input']
        acc_dest = accounts['stock_account_output']
        acc_valuation = accounts.get('property_stock_valuation_account_id', False)
        journal_id = accounts['stock_journal']
        return journal_id, acc_src, acc_dest, acc_valuation

    def finalize_invoice_move_lines(self,cr,uid,ids, move_lines,context=None):
        ##################################################################################################
        # This method used to attached branch and division on both customer invoice and supplier invoice #
        ##################################################################################################
        
        finalize =  super(account_invoice, self).finalize_invoice_move_lines(cr,uid,ids, move_lines,context=context)
        vals = self.browse(cr,uid,ids)
        if not vals.branch_id.id or not vals.division :
            raise osv.except_osv(_('Attention!'), _('Pastikan Branch dan Division sudah diisi !'))
        res = []
        branch =  vals.branch_id
        for x in finalize :
            x[2]['branch_id'] = vals.branch_id.id
            x[2]['division'] = vals.division
            x[2]['date_maturity'] = vals.date_due
            #BARANG KELUAR (PENJUALAN) CREATE STOCK KELUAR DI INVOICE
            if 'product_id' in x[2] and x[2]['product_id'] and vals.create_manual == False and vals.type == 'out_invoice':
                product_price_obj = self.pool.get('product.price.branch')
                new_valuation_amount = 0.0
                currency_obj = self.pool.get('res.currency')
                product = self.pool.get('product.product').browse(cr, uid, x[2]['product_id'])
                if product.cost_method == 'average':
                    warehouse_id = self.pool.get('stock.warehouse').search(cr, uid, [('branch_id','=',vals.branch_id.id)], limit=1)
                    if not warehouse_id:
                        raise osv.except_osv(_('Attention!'),_('Branch %s belum memiliki warehouse') % (vals.branch_id.name))
                    valuation_amount = product_price_obj._get_price(cr, uid, warehouse_id, x[2]['product_id'])
                else:
                    valuation_amount = product.standard_price
                origin = vals.origin or ''
                wo_ids = self.pool.get('dym.work.order').search(cr, uid, [('name','=',origin.split(' '))], limit=1)
                wo = self.pool.get('dym.work.order').browse(cr, uid, wo_ids)
                if product.product_tmpl_id.is_bundle:
                    for line in product.product_tmpl_id.item_ids:
                        if (branch.kpb_ganti_oli_barang == True and line.product_id.is_oli and wo and wo.kpb_ke == '1') or line.product_id.type == 'service':
                            continue
                        if line.product_id.cost_method == 'average':
                            warehouse_id = self.pool.get('stock.warehouse').search(cr, uid, [('branch_id','=',vals.branch_id.id)], limit=1)
                            if not warehouse_id:
                                raise osv.except_osv(_('Attention!'),_('Branch %s belum memiliki warehouse') % (vals.branch_id.name))
                            valuation_amount = product_price_obj._get_price(cr, uid, warehouse_id, line.product_id.id)
                        else:
                            valuation_amount = line.product_id.standard_price
                        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, line.product_id, context=context)
                        analytic_4 = False
                        analytic_4_general = False
                        cost_center = ''
                        if line.product_id.categ_id.get_root_name() in ('Unit','Extras'):
                            cost_center = 'Sales'
                        elif line.product_id.categ_id.get_root_name() == 'Sparepart':
                            cost_center = 'Sparepart_Accesories'
                        elif line.product_id.categ_id.get_root_name() =='Umum':
                            cost_center = 'General'
                        elif line.product_id.categ_id.get_root_name() =='Service':
                            cost_center = 'Service'
                        if cost_center:
                            categ_obj = line.product_id.categ_id
                            category = ''
                            if line.product_id.categ_id.get_root_name() == 'Extras':
                                categ_obj = False
                                category = 'Unit'
                            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, category, categ_obj, 4, cost_center)
                            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, category, categ_obj, 4, 'General')
                        res.append((0,0,{
                            'name': line.product_id.name,
                            'account_id': acc_dest,
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'debit': valuation_amount * ((x[2]['quantity'] or 1.0) * (line.product_uom_qty or 1.0)),
                            'credit': 0.0,
                            'branch_id': vals.branch_id.id,
                            'division': vals.division,
                            'product_id': line.product_id.id,
                            'quantity': x[2]['quantity'],
                            'product_uom_id': line.product_id.uom_id.id,
                            'ref': vals.name or False,
                            'analytic_account_id' : analytic_4,
                            'product_cost_id' : line.product_id.id,
                            'product_cost_price' : valuation_amount
                        }))
                        res.append((0,0,{
                            'name': line.product_id.name,
                            'account_id': acc_valuation,
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'debit': 0.0,
                            'credit': valuation_amount * ((x[2]['quantity'] or 1.0) * (line.product_uom_qty or 1.0)),
                            'branch_id': vals.branch_id.id,
                            'division': vals.division,
                            'product_id': line.product_id.id,
                            'quantity': x[2]['quantity'],
                            'product_uom_id': line.product_id.uom_id.id,
                            'ref': vals.name or False,
                            'analytic_account_id' : analytic_4_general,
                            'product_cost_id' : line.product_id.id,
                            'product_cost_price' : valuation_amount
                        }))
                else:
                    if (branch.kpb_ganti_oli_barang == True and wo and wo.kpb_ke == '1' and product.is_oli) or product.type == 'service':
                        continue
                    if product.type != 'service':    
                        analytic_4 = False
                        analytic_4_general = False
                        cost_center = ''
                        if product.categ_id.get_root_name() in ('Unit','Extras'):
                            cost_center = 'Sales'
                        elif product.categ_id.get_root_name() == 'Sparepart':
                            cost_center = 'Sparepart_Accesories'
                        elif product.categ_id.get_root_name() =='Umum':
                            cost_center = 'General'
                        elif product.categ_id.get_root_name() =='Service':
                            cost_center = 'Service'
                        if cost_center:
                            categ_obj = product.categ_id
                            category = ''
                            if product.categ_id.get_root_name() == 'Extras':
                                categ_obj = False
                                category = 'Unit'
                            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, category, categ_obj, 4, cost_center)
                            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, category, categ_obj, 4, 'General')
                        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, product, context=context)
                        res.append((0,0,{
                            'name': product.name,
                            'account_id': acc_dest,
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'debit': valuation_amount * (x[2]['quantity'] or 1.0),
                            'credit': 0.0,
                            'branch_id': vals.branch_id.id,
                            'division': vals.division,
                            'product_id': product.id,
                            'quantity': x[2]['quantity'],
                            'product_uom_id': product.uom_id.id,
                            'ref': vals.name or False,
                            'analytic_account_id' : analytic_4,
                            'product_cost_id' : product.id,
                            'product_cost_price' : valuation_amount
                        }))
                        res.append((0,0,{
                            'name': product.name,
                            'account_id': acc_valuation,
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'debit': 0.0,
                            'credit': valuation_amount * (x[2]['quantity'] or 1.0),
                            'branch_id': vals.branch_id.id,
                            'division': vals.division,
                            'product_id': product.id,
                            'quantity': x[2]['quantity'],
                            'product_uom_id': product.uom_id.id,
                            'ref': vals.name or False,
                            'analytic_account_id' : analytic_4_general,
                            'product_cost_id' : product.id,
                            'product_cost_price' : valuation_amount
                        }))
            #BARANG MASUK (RETUR BELI) SPLIT BANDINGKAN DENGAN CURRENT COST
            if 'product_id' in x[2] and x[2]['product_id'] and vals.create_manual == False and vals.type == 'in_refund':
                config = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',branch.id)])
                if not config :
                    raise osv.except_osv(_('Attention!'), _('Belum ada konfigurasi branch %s!') % (branch.name))
                config_browse = self.pool.get('dym.branch.config').browse(cr,uid,config)
                if not config_browse.account_retur_variance :
                    raise osv.except_osv(_('Attention!'), _('Mohon isi account variance di konfigurasi branch %s!') % (branch.name))
                account_variance = config_browse.account_retur_variance.id
                product_price_obj = self.pool.get('product.price.branch')
                new_valuation_amount = 0.0
                currency_obj = self.pool.get('res.currency')
                product = self.pool.get('product.product').browse(cr, uid, x[2]['product_id'])
                if product.cost_method == 'average':
                    warehouse_id = self.pool.get('stock.warehouse').search(cr, uid, [('branch_id','=',vals.branch_id.id)], limit=1)
                    if not warehouse_id:
                        raise osv.except_osv(_('Attention!'),_('Branch %s belum memiliki warehouse') % (vals.branch_id.name))
                    valuation_amount = product_price_obj._get_price(cr, uid, warehouse_id, x[2]['product_id'])
                else:
                    valuation_amount = product.standard_price
                origin = vals.origin or ''
                if product.product_tmpl_id.is_bundle:
                    for line in product.product_tmpl_id.item_ids:
                        if line.product_id.cost_method == 'average':
                            warehouse_id = self.pool.get('stock.warehouse').search(cr, uid, [('branch_id','=',vals.branch_id.id)], limit=1)
                            if not warehouse_id:
                                raise osv.except_osv(_('Attention!'),_('Branch %s belum memiliki warehouse') % (vals.branch_id.name))
                            valuation_amount = product_price_obj._get_price(cr, uid, warehouse_id, line.product_id.id)
                        else:
                            valuation_amount = line.product_id.standard_price                        
                        total_valuation += (valuation_amount * ((x[2]['quantity'] or 1.0) * (line.product_uom_qty or 1.0)))
                    debit = 0
                    credit = 0
                    if x[2]['credit'] > 0:
                        amount_variance = x[2]['credit'] - total_valuation
                        debit =  (amount_variance * -1) if amount_variance < 0 else 0
                        credit = amount_variance if amount_variance > 0 else 0
                        if credit > 0:
                            x[2]['credit'] = x[2]['credit'] - credit
                        if debit > 0:
                            x[2]['credit'] = x[2]['credit'] + debit
                    elif x[2]['debit'] > 0:
                        amount_variance = x[2]['debit'] - total_valuation
                        debit = amount_variance if amount_variance > 0 else 0
                        credit =  (amount_variance * -1) if amount_variance < 0 else 0
                        if debit > 0:
                            x[2]['debit'] = x[2]['debit'] - debit
                        if credit > 0:
                            x[2]['debit'] = x[2]['debit'] + credit
                    if debit > 0 or credit > 0:
                        analytic_4 = False
                        analytic_4_general = False
                        cost_center = ''
                        if product.categ_id.get_root_name() in ('Unit','Extras'):
                            cost_center = 'Sales'
                        elif product.categ_id.get_root_name() == 'Sparepart':
                            cost_center = 'Sparepart_Accesories'
                        elif product.categ_id.get_root_name() =='Umum':
                            cost_center = 'General'
                        elif product.categ_id.get_root_name() =='Service':
                            cost_center = 'Service'
                        if cost_center:
                            categ_obj = product.categ_id
                            category = ''
                            if product.categ_id.get_root_name() == 'Extras':
                                categ_obj = False
                                category = 'Unit'
                            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, category, categ_obj, 4, cost_center)
                            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, category, categ_obj, 4, 'General')
                        res.append((0,0,{
                            'name': product.name,
                            'account_id': account_variance,
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'debit':  debit,
                            'credit': credit,
                            'branch_id': vals.branch_id.id,
                            'division': vals.division,
                            'product_id': product.id,
                            'quantity': x[2]['quantity'],
                            'product_uom_id': product.uom_id.id,
                            'ref': vals.name or False,
                            'analytic_account_id' : analytic_4_general,
                            'product_cost_id' : product.id,
                            'product_cost_price' : debit or credit
                        }))
                else:
                    debit = 0
                    credit = 0
                    valuation_amount = valuation_amount * (x[2]['quantity'] or 1.0)
                    if x[2]['credit'] > 0:
                        amount_variance = x[2]['credit'] - valuation_amount
                        debit =  (amount_variance * -1) if amount_variance < 0 else 0
                        credit = amount_variance if amount_variance > 0 else 0
                        if credit > 0:
                            x[2]['credit'] = x[2]['credit'] - credit
                        if debit > 0:
                            x[2]['credit'] = x[2]['credit'] + debit
                    elif x[2]['debit'] > 0:
                        amount_variance = x[2]['debit'] - valuation_amount
                        debit = amount_variance if amount_variance > 0 else 0
                        credit =  (amount_variance * -1) if amount_variance < 0 else 0
                        if debit > 0:
                            x[2]['debit'] = x[2]['debit'] - debit
                        if credit > 0:
                            x[2]['debit'] = x[2]['debit'] + credit
                    if product.type != 'service' and (debit > 0 or credit > 0):
                        analytic_4 = False
                        analytic_4_general = False
                        cost_center = ''
                        if product.categ_id.get_root_name() in ('Unit','Extras'):
                            cost_center = 'Sales'
                        elif product.categ_id.get_root_name() == 'Sparepart':
                            cost_center = 'Sparepart_Accesories'
                        elif product.categ_id.get_root_name() =='Umum':
                            cost_center = 'General'
                        elif product.categ_id.get_root_name() =='Service':
                            cost_center = 'Service'
                        if cost_center:
                            categ_obj = product.categ_id
                            category = ''
                            if product.categ_id.get_root_name() == 'Extras':
                                categ_obj = False
                                category = 'Unit'
                            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, category, categ_obj, 4, cost_center)
                            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, category, categ_obj, 4, 'General')
                        res.append((0,0,{
                            'name': product.name,
                            'account_id': account_variance,
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'debit': debit,
                            'credit': credit,
                            'branch_id': vals.branch_id.id,
                            'division': vals.division,
                            'product_id': product.id,
                            'quantity': x[2]['quantity'],
                            'product_uom_id': product.uom_id.id,
                            'ref': vals.name or False,
                            'analytic_account_id' : analytic_4_general,
                            'product_cost_id' : product.id,
                            'product_cost_price' : debit or credit
                        }))
        finalize += res
        return finalize
    
    def action_cancel(self,cr,uid,ids,context=None):
        for inv in self.browse(cr, uid, ids):
            if inv.state == 'open':
                inv.write({'origin':(inv.origin or '') + ' ' + (inv.number or '')})
                for inv_line in inv.invoice_line:
                    if inv_line.consolidated_qty > 0:
                        raise osv.except_osv(_('Attention!'), _('Invoice sudah di consolidate!'))
                    current_invoiced = inv_line.purchase_line_id.qty_invoiced
                    new_invoiced = current_invoiced - inv_line.quantity
                    inv_line.purchase_line_id.write({'qty_invoiced':new_invoiced, 'invoiced':False})
        vals = super(account_invoice,self).action_cancel(cr,uid,ids,context=context)
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})
        return vals 
    
    def _fill_due_date(self, cr, uid, ids, document_date, payment_term, context=None):
        value = {}
        if not document_date:
            document_date = fields.date.context_today(self,cr,uid,context=context)
        if not payment_term:
            # To make sure the invoice due date should contain due date which is
            # entered by user when there is no payment term defined
            value =  {'date_due': document_date}
        if payment_term and document_date:
            pterm = self.pool.get('account.payment.term').browse(cr,uid,payment_term)
            pterm_list = pterm.compute(value=1, date_ref=document_date)[0]
            if pterm_list:
                value = {'date_due': max(line[0] for line in pterm_list)}
        return value
    
    def onchange_document_date(self, cr, uid, ids, document_date, payment_term, context=None):
        value = self._fill_due_date(cr, uid, ids, document_date, payment_term, context)
        return {'value': value}

    def create(self, cr, uid, vals, context=None):
        vals['date_invoice'] = datetime.today()
        res = super(account_invoice,self).create(cr, uid, vals, context=context)
        invoice = self.browse(cr,uid,res)        
        if not invoice.payment_term :
            pterm = self.pool.get('account.payment.term').search(cr,uid,[('name','=','Immediate Payment')])
            if pterm :
                pterm_browse = self.pool.get('account.payment.term').browse(cr,uid,pterm)
                invoice.write({'payment_term':pterm_browse.id})
        # self.button_reset_taxes(cr, uid, [res])
        if invoice.partner_id and not invoice.partner_bank_id and invoice.partner_id.bank_ids:
            bank_id = invoice.partner_id.bank_ids and invoice.partner_id.bank_ids[0].id or False
            invoice.write({'partner_bank_id':bank_id})
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        #Recalculate date_due value based on document_date and payment_term
        if vals.get('document_date') or vals.get('payment_term') :
            invoice_id = self.browse(cr, uid, ids, context=context)
            vals.update(self._fill_due_date(cr, uid, ids, vals.get('document_date', invoice_id.document_date), vals.get('payment_term', invoice_id.payment_term.id), context))
        invoice_update = super(account_invoice, self).write(cr, uid, ids, vals, context=context)
        # self.button_reset_taxes(cr, uid, ids)
        return invoice_update
    
    def action_date_assign(self,cr,uid,ids,context=None):
        res1 = super(account_invoice,self).action_date_assign(cr,uid,ids,context=context)
        for inv in self.browse(cr,uid,ids):
            res = self.onchange_document_date(cr,uid,ids,inv.document_date,inv.payment_term.id,context=context)
            if res and res.get('value'):
                inv.write(res['value'])
        return res1

    @api.multi
    def _action_move_create(self):
        """ Hack original account.action_account_move_create to 
        eheck if journal.entry_posted is true then post it otherwise leave it unposted"""
        account_invoice_tax = self.env['account.invoice.tax']
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise except_orm(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise except_orm(_('No Invoice Lines!'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            company_currency = inv.company_id.currency_id
            if not inv.date_invoice:
                # FORWARD-PORT UP TO SAAS-6
                if inv.currency_id != company_currency and inv.tax_line:
                    raise except_orm(
                        _('Warning!'),
                        _('No invoice date!'
                            '\nThe invoice currency is not the same than the company currency.'
                            ' An invoice date is required to determine the exchange rate to apply. Do not forget to update the taxes!'
                        )
                    )
                inv.with_context(ctx).write({'date_invoice': openerp.fields.Date.context_today(self)})
            date_invoice = inv.date_invoice

            # create the analytical lines, one move line per invoice line
            iml = inv._get_analytic_lines()
            # check if taxes are all computed
            compute_taxes = account_invoice_tax.compute(inv.with_context(lang=inv.partner_id.lang))
            inv.check_tax_lines(compute_taxes)

            # I disabled the check_total feature
            # if self.env.user.has_group('account.group_supplier_inv_check_total'):
            #     if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding / 2.0):
            #         raise except_orm(_('Bad Totalx!'), _('Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise except_orm(_('Error!'), _("Cannot create the invoice.\nThe related payment term is probably misconfigured as it gives a computed amount greater than the total invoiced amount. In order to avoid rounding issues, the latest line of your payment term must be of type 'balance'."))

            # Force recomputation of tax_amount, since the rate potentially changed between creation
            # and validation of the invoice
            inv._recompute_tax_amount()
            # one move line per tax line
            iml += account_invoice_tax.move_line_get(inv.id)
            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
            else:
                ref = inv.number

                
            # if inv.type in ('out_refund'):
                

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, ref, iml)

            name = inv.supplier_invoice_number or inv.name or '/'
            totlines = []
            if inv.payment_term:
                totlines = inv.with_context(ctx).payment_term.compute(total, date_invoice)[0]
            if totlines:
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'ref': ref,
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'ref': ref
                })

            date = date_invoice

            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id, date)) for l in iml]
            line = inv.group_lines(iml, line)
            journal = inv.journal_id.with_context(ctx)
            if journal.centralisation:
                raise except_orm(_('User Error!'),
                        _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            line = inv.finalize_invoice_move_lines(line)
            move_vals = {
                'ref': inv.reference or inv.name,
                'line_id': line,
                'journal_id': journal.id,
                'date': inv.date_invoice,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
            }
            ctx['company_id'] = inv.company_id.id
            period = inv.period_id
            if not period:
                period = period.with_context(ctx).find(date_invoice)[:1]
            if period:
                move_vals['period_id'] = period.id
                for i in line:
                    i[2]['period_id'] = period.id

            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'period_id': period.id,
                'move_name': move.name,
            }

            inv.with_context(ctx).write(vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:

            if journal.entry_posted:
                move.post()
        self._log_event()
        return True
    
    def action_move_create(self,cr,uid,ids,context=None):
        res = self._action_move_create(cr,uid,ids,context=context)
        val = self.browse(cr,uid,ids)


        
        detail_line=False;category=False;branch=False;line_ids=[];analytic_4_general=False

        for line in val.invoice_line:
            if line.product_id.type!='service':
                if val.origin:
                    if val.origin[:3]=='WOR':  
                        line_ids=self.pool.get('dym.work.order.line').search(cr,uid,[('product_id','=',line.product_id.id),('work_order_id.name','=',line.origin)])
                    
                    elif val.origin[:3]=='SOR':
                        line_ids=self.pool.get('sale.order.line').search(cr,uid,[('product_id','=',line.product_id.id),('order_id.name','=',line.origin)])       
                    
                    if line_ids:
                        if val.origin[:3]=='WOR':  
                            detail_line=self.pool.get('dym.work.order.line').browse(cr,uid,line_ids)
                            category=detail_line.categ_id_2
                            branch=detail_line.work_order_id.branch_id
                    
                        elif val.origin[:3]=='SOR':
                            detail_line=self.pool.get('sale.order.line').browse(cr,uid,line_ids)
                            category=detail_line.categ_id
                            branch=detail_line.order_id.branch_id

                        if detail_line and category and branch:
                            if line.account_id.id != line.product_id.categ_id.property_stock_valuation_account_id.id:
                                analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, 'Sparepart', category, 4, 'Sparepart_Accesories')
                                line.write({'analytic_account_id':analytic_4})
                            else:
                                analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, 'Sparepart', category, 4, 'General')
                                line.write({'analytic_account_id':analytic_4})
                           

        for line in val.move_id.line_id:
            if line.product_id:
                if line.product_id.type!='service':
                    if val.origin:
                        if val.origin[:3]=='WOR':  
                            line_ids=self.pool.get('dym.work.order.line').search(cr,uid,[('product_id','=',line.product_id.id),('work_order_id.name','=',line.ref)])
                        
                        elif val.origin[:3]=='SOR':
                            line_ids=self.pool.get('sale.order.line').search(cr,uid,[('product_id','=',line.product_id.id),('order_id.name','=',line.ref)])       
                        
                        if line_ids:
                            if val.origin[:3]=='WOR':  
                                detail_line=self.pool.get('dym.work.order.line').browse(cr,uid,line_ids)
                                category=detail_line.categ_id_2
                                branch=detail_line.work_order_id.branch_id
                        
                            elif val.origin[:3]=='SOR':
                                detail_line=self.pool.get('sale.order.line').browse(cr,uid,line_ids)
                                category=detail_line.categ_id
                                branch=detail_line.order_id.branch_id
                                if not category.bisnis_unit:
                                    is_part = True
                                    analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr,uid,branch, '', category, 4, 'General')

                            if detail_line and category and branch:
                                if line.account_id.id != line.product_id.categ_id.property_stock_valuation_account_id.id:
                                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, 'Sparepart', category, 4, 'Sparepart_Accesories')
                                    line.write({'analytic_account_id':analytic_4})
                                else:
                                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, 'Sparepart', category, 4, 'General')
                                    line.write({'analytic_account_id':analytic_4})              
                                
        #AR Part ke Accessories
        if 'SOR' in val.origin and analytic_4_general:
            for line in val.move_id.line_id:
                so_ids=self.pool.get('sale.order').search(cr,uid,[('name','=',line.ref)])
                if so_ids and len(so_ids)==1:
                    so=self.pool.get('sale.order').browse(cr,uid,so_ids[0])    
                    if line.name == so.name or 'PPN' in line.name:
                        line.write({'analytic_account_id':analytic_4_general})
        
#         move.write(cr,uid,val.move_id.id,values)

        return res
    
    @api.model
    def _prepare_refund(self, invoice, date=None, period_id=None, description=None, journal_id=None):
        res = super(account_invoice,self)._prepare_refund(invoice, date, period_id, description, journal_id)
        res['branch_id'] = invoice.branch_id.id
        res['division'] = invoice.division
        res['document_date'] = invoice.document_date
        res['origin'] = invoice.origin
        return res
    
    @api.model
    def line_get_convert(self, line, part, date):
        return {
            'date_maturity': line.get('date_maturity', False),
            'partner_id': part,
            'name': line['name'][:64],
            'date': date,
            'debit': line['price']>0 and line['price'],
            'credit': line['price']<0 and -line['price'],
            'account_id': line['account_id'],
            'analytic_lines': line.get('analytic_lines', []),
            'amount_currency': line['price']>0 and abs(line.get('amount_currency', False)) or -abs(line.get('amount_currency', False)),
            'currency_id': line.get('currency_id', False),
            'tax_code_id': line.get('tax_code_id', False),
            'tax_amount': line.get('tax_amount', False),
            'ref': line.get('ref', False),
            'quantity': line.get('quantity',1.00),
            'product_id': line.get('product_id', False),
            'product_uom_id': line.get('uos_id', False),
            'analytic_account_id': line.get('account_analytic_id', False),
            #iman 'force_partner_id': line.get('force_partner_id', False),
        }

    @api.multi
    def _get_analytic_lines(self):
        """ Return a list of dict for creating analytic lines for self[0] """
        company_currency = self.company_id.currency_id
        sign = 1 if self.type in ('out_invoice', 'in_refund') else -1
        iml = self.env['account.invoice.line'].move_line_get(self.id)
        return iml

class account_invoice_line(osv.osv):
    
    _inherit = 'account.invoice.line'
    
    _columns = {
        'force_cogs': fields.float(),
    }
           
    @api.model
    def move_line_get_item(self, line):
        res =  super(account_invoice_line, self).move_line_get_item(line)
        res['account_analytic_id'] = line.account_analytic_id.id or line.analytic_3.id or line.analytic_2.id or False
        res['force_partner_id'] = line.force_partner_id.id or False
        return res

class dym_partner_type(osv.osv):
    
    _name = 'dym.partner.type'

    def _get_division_string(self, cr, uid, ids, name, args, context):
        res = {}
        for partner_type in self.browse(cr, uid, ids):
            type_str = ''
            if partner_type.unit == True:
                type_str += 'Unit,'
            if partner_type.sparepart == True:
                type_str += 'Sparepart,'
            if partner_type.umum == True:
                type_str += 'Umum,'
            if partner_type.finance == True:
                type_str += 'Finance,'
            res[partner_type.id] = type_str
        return res

    _columns = {
        'name': fields.char('Name'),
        'value': fields.char('Value'),
        'division': fields.function(_get_division_string, string='Division', type="char",
              store={
                    'dym.partner.type': (lambda self, cr, uid, ids, c={}: ids, ['unit','sparepart','umum','finance'], 10),
                     }, help="Division"),
        'unit': fields.boolean('Unit'),
        'sparepart': fields.boolean('Sparepart'),
        'umum': fields.boolean('Umum'),
        'finance': fields.boolean('Finance'),
        'field_type': fields.selection([('boolean','Boolean'),('selection','Selection')], 'Field Type'),
        'selection_name': fields.char('Selection Field Name'),
    }

    def name_get(self, cr, uid, ids, context=None):
        return_val = super(dym_partner_type, self).name_get(cr, uid, ids, context=context)
        res = []
        for partner_type in self.browse(cr, uid, ids, context=context):
            res.append((partner_type.id, (partner_type.value)))
        return res or return_val

class account_period(osv.osv):
    _inherit = "account.period"

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            name = rec.company_id.name
            if rec.company_id and rec.name:
                name = '['+rec.name+'] '+ rec.company_id.name
            res.append((rec.id, name))
        return res

class account_journal(osv.osv):
    _inherit = "account.journal"

    _columns = {
        'allow_negative_balance': fields.boolean('Allow Negative Balance'),
        'is_intercompany': fields.boolean('Is Intercompany'),
        'max_overdraft': fields.float('Max Overdraft', digits_compute=dp.get_precision('Account'), help="This is a field only used for internal purpose and shouldn't be displayed"),
    }

    _defaults = {
        'allow_negative_balance': False,
        'max_overdraft': 0,
        'is_intercompany': False,
    }

    @api.onchange('allow_negative_balance')
    def change_allow_negative_balance(self):
        if not self.allow_negative_balance:
            self.max_overdraft = 0.0

    # @api.multi
    # def name_get(self):
    #     res = []
    #     for rec in self:
    #         name = rec.company_id.name
    #         if rec.company_id and rec.name:
    #             name = '['+rec.name+'] '+ rec.company_id.name
    #         res.append((rec.id, name))
    #     return res

class account_fiscalyear(osv.osv):
    _inherit = "account.fiscalyear"

    @api.multi
    def name_get(self):
        res = super(account_fiscalyear,self).name_get()
        for rec in self:
            name = rec.company_id.name
            if rec.company_id and rec.name:
                name = '['+rec.name+'] '+ rec.company_id.name
            res.append((rec.id, name))
        return res
