import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class AccountFinancialReport(models.Model):
    _inherit = 'account.financial.report'

    @api.one
    @api.depends('account_ids','analytic_1','analytic_2','analytic_3','analytic_4')
    def _compute_balance_analytic(self):

        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
            'debit': "COALESCE(SUM(l.debit), 0) as debit",
            'credit': "COALESCE(SUM(l.credit), 0) as credit",
            'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
        }

        for account in self.account_ids:
            children_and_consolidated = account._get_children_and_consol()
            accounts = {}
            res = {}

            if children_and_consolidated:
                aml_query = self.env['account.move.line']._query_get()
                wheres = [""]
                if aml_query.strip():
                    wheres.append(aml_query.strip())
                filters = " AND ".join(wheres)
                request = ("SELECT l.account_id as id, " +\
                           ', '.join(mapping.values()) +
                           " FROM account_move_line l" \
                           " WHERE l.account_id IN %s " \
                                + filters +
                           " GROUP BY l.account_id")
                params = (tuple(children_and_consolidated),)
                self._cr.execute(request, params)

                for row in self._cr.dictfetchall():
                    accounts[row['id']] = row

                children_and_consolidated.reverse()
                brs = list(self.env['account.account'].browse(children_and_consolidated))
                sums = {}
                currency_obj = self.env['res.currency']
                while brs:
                    current = brs.pop(0)
                    fn = 'balance_analytic'
                    sums.setdefault(current.id, {})[fn] = accounts.get(current.id, {}).get(fn, 0.0)

                    for child in current.child_id:
                        if child.company_id.currency_id.id == current.company_id.currency_id.id:
                            sums[current.id][fn] += sums[child.id][fn]
                        else:
                            sums[current.id][fn] += currency_obj.compute(cr, uid, child.company_id.currency_id.id, current.company_id.currency_id.id, sums[child.id][fn], context=context)
            else:
                for id in ids:
                    res[id] = null_result
            return res

        self.balance_analytic = 999

    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    balance_analytic = fields.Float(string=_('Analytic Balance'), digits=dp.get_precision('Account'), compute=_compute_balance_analytic, help="Analytic Balance")
    analytic_1 = fields.Many2one('account.analytic.account', 'Account Analytic Company')
    analytic_2 = fields.Many2one('account.analytic.account', 'Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center')
