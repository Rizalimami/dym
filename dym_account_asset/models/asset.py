import time
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
from datetime import date, datetime, timedelta
from lxml import etree
from openerp.osv.orm import setup_modifiers
from dateutil.relativedelta import relativedelta
from openerp import tools
import openerp.addons.decimal_precision as dp
from openerp import api

class dym_account_asset_depreciation(osv.osv):
    _inherit = "account.asset.asset"

    def create_asset_accum_move(self, cr, uid, ids, depreciations=None, period_id=None, depreciation_date= None, context=None):

        if not depreciations or not period_id:
            return False

        context = dict(context or {})
        can_close = False
        depreciation_obj = self.pool.get('account.asset.depreciation.line')
        period_obj = self.pool.get('account.period')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')

        asset = self.browse(cr, uid, [ids], context=context)[0]
        
        asset_name = asset.name
        reference = 'Accum.Depr. Period:'
        dept_id = depreciation_obj.search(cr, uid, [('id','in',depreciations)], order="depreciation_date", limit=1)
        period_start = depreciation_obj.browse(cr, uid, dept_id, context=context)[0]

        amount_total = 0.0
        for line in depreciation_obj.browse(cr, uid, depreciations, context=context):
            amount_total += line.amount

        company_currency = asset.company_id.currency_id.id
        current_currency = asset.currency_id.id
        context.update({'date': depreciation_date})
        amount = currency_obj.compute(cr, uid, current_currency, company_currency, amount_total, context=context)
        sign = (asset.category_id.journal_id.type == 'purchase' and 1) or -1
 
        reference = 'Accum. Depr. %s from %s - %s' % (asset_name, period_start.depreciation_date, depreciation_date)

        move_vals = {
            'name': asset_name,
            'date': depreciation_date,
            'ref': reference,
            'period_id': period_id,
            'journal_id': asset.category_id.journal_id.id,
            'transaction_id':asset.id,
            'model': asset.__class__.__name__,
            }
        move_id = move_obj.create(cr, uid, move_vals, context=context)

        journal_id = asset.category_id.journal_id.id
        partner_id = asset.partner_id.id
        move_line_obj.create(cr, uid, {
            'name': asset_name,
            'ref': reference,
            'move_id': move_id,
            'account_id': asset.category_id.account_depreciation_id.id,
            'debit': 0.0,
            'credit': amount,
            'period_id': period_id,
            'journal_id': journal_id,
            'branch_id': asset.analytic_3.branch_id.id or asset.branch_id.id,
            'division': 'Umum',
            'currency_id': company_currency != current_currency and  current_currency or False,
            'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
            'date': depreciation_date,
            'analytic_account_id' : asset.analytic_4.id,
        })

        analytic = asset.category_id.account_analytic_id
        analytic_4 = analytic.id
        branch_id = False
        if analytic.type == 'normal' and analytic.segmen == 3 and not branch_id:
            branch_id = analytic.branch_id.id
        while (analytic.parent_id and not branch_id):
            analytic = analytic.parent_id
            if analytic.type == 'normal' and analytic.segmen == 3:
                    branch_id = analytic.branch_id.id

        move_line_obj.create(cr, uid, {
            'name': asset_name,
            'ref': reference,
            'move_id': move_id,
            'account_id': asset.category_id.account_expense_depreciation_id.id,
            'credit': 0.0,
            'debit': amount,
            'period_id': period_id,
            'journal_id': journal_id,
            'branch_id': branch_id or asset.category_id.analytic_3.branch_id.id,
            'division': 'Umum',
            'currency_id': company_currency != current_currency and  current_currency or False,
            'amount_currency': company_currency != current_currency and sign * line.amount or 0.0,
            'date': depreciation_date,
            'asset_id': asset.id,
            'analytic_account_id': analytic_4,
        })

        for line in depreciation_obj.browse(cr, uid, depreciations, context=context):
            depreciation_obj.write(cr, uid, line.id, {'move_id':move_id,'move_check':True}, context=context)

        if currency_obj.is_zero(cr, uid, asset.currency_id, asset.value_residual):
            asset.write({'state': 'close'})

        periods = self.pool.get('account.period').find(cr, uid, context=context)

        for move_line in self.pool.get('account.move').browse(cr,uid,[move_id]):
            branch_id = False
            for x in move_line.line_id :
                if not branch_id :
                    branch_id = x.asset_id.branch_id.id
                x.write({'branch_id':branch_id,'division':'Umum'})
            get_name = self.pool.get('ir.sequence').get_per_branch(cr,uid,[branch_id], move_line.journal_id.code) 
            move_line.write({'name':get_name})

        return move_id