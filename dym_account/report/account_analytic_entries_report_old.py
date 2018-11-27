# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import tools
from openerp.osv import fields,osv

class analytic_entries_report(osv.osv):
    _inherit = "analytic.entries.report"
    _columns = {
        'date': fields.date('Date', readonly=True),
        'user_id': fields.many2one('res.users', 'User',readonly=True),
        'name': fields.char('Description', size=64, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
        'account_id': fields.many2one('account.analytic.account', 'Account', required=False),
        'general_account_id': fields.many2one('account.account', 'General Account', required=True),
        'journal_id': fields.many2one('account.analytic.journal', 'Journal', required=True),
        'move_id': fields.many2one('account.move.line', 'Move', required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_uom_id': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'amount': fields.float('Amount', readonly=True),
        'unit_amount': fields.integer('Unit Amount', readonly=True),
        'nbr': fields.integer('# Entries', readonly=True),  # TDE FIXME master: rename into nbr_entries
        'move_id' : fields.many2one('account.move', string='Account Analytic Company'),
        'analytic_1' : fields.many2one('account.analytic.account', string='Segmen Company'),
        'analytic_2' : fields.many2one('account.analytic.account', string='Segmen Business Unit'),
        'analytic_3' : fields.many2one('account.analytic.account', string='Segmen Branch'),
        'analytic_4' : fields.many2one('account.analytic.account', string='Segmen Cost Center'),
        'branch_status' : fields.selection([('HO','HO'),('H1','H1'),('H23','H23'),('H123','H123')],string='Branch Status'),


    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'analytic_entries_report')
        cr.execute("""
            create or replace view analytic_entries_report as (
                 select
                     min(a.id) as id,
                     count(distinct a.id) as nbr,
                     a.date as date,
                     a.user_id as user_id,
                     a.name as name,
                     analytic.partner_id as partner_id,
                     a.company_id as company_id,
                     a.currency_id as currency_id,
                     a.account_id as account_id,
                     a.general_account_id as general_account_id,
                     a.journal_id as journal_id,
                     a.move_id as move_id,
                     a.product_id as product_id,
                     a.product_uom_id as product_uom_id,
                     a.analytic_1 as analytic_1,
                     a.analytic_2 as analytic_2,
                     a.analytic_3 as analytic_3,
                     a.analytic_4 as analytic_4,
                     a.branch_status as branch_status,
                     sum(a.amount) as amount,
                     sum(a.unit_amount) as unit_amount
                 from
                     account_analytic_line a, account_analytic_account analytic
                 where analytic.id = a.account_id
                 group by
                     a.date, a.user_id,a.name,analytic.partner_id,a.company_id,a.currency_id,
                     a.account_id,a.general_account_id,a.journal_id,
                     a.move_id,a.product_id,a.product_uom_id, a.analytic_1, a.analytic_2, a.analytic_3, a.analytic_4, a.branch_status
            )
        """)

class account_invoice_report(osv.osv):
    _inherit= "account.invoice.report"


    def _select(self):
        select_str = """
            SELECT sub.id, sub.date, sub.product_id, sub.partner_id, sub.country_id,
                sub.payment_term, sub.period_id, sub.uom_name, sub.currency_id, sub.journal_id,
                sub.fiscal_position, sub.user_id, sub.company_id, sub.nbr, sub.type, sub.state,
                sub.categ_id, sub.date_due, sub.account_id, sub.account_line_id, sub.partner_bank_id,
                sub.product_qty, sub.price_total / cr.rate as price_total, sub.price_average /cr.rate as price_average,
                cr.rate as currency_rate, sub.residual / cr.rate as residual, sub.commercial_partner_id as commercial_partner_id
        """
        return select_str

    def _sub_select(self):
        select_str = """
        SELECT min(ail.id) AS id,
            ai.date_invoice AS date,
            ail.product_id, ai.partner_id, ai.payment_term, ai.period_id,
            u2.name AS uom_name,
            ai.currency_id, ai.journal_id, ai.fiscal_position, ai.user_id, ai.company_id,
            count(ail.*) AS nbr,
            ai.type, ai.state, pt.categ_id, ai.date_due, ai.account_id, ail.account_id AS account_line_id,
            ai.partner_bank_id,
            SUM(CASE
                 WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                    THEN (- ail.quantity) / u.factor * u2.factor
                    ELSE ail.quantity / u.factor * u2.factor
                END) AS product_qty,
            SUM(CASE
                 WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                    THEN - ail.price_subtotal
                    ELSE ail.price_subtotal
                END) AS price_total,
            CASE
             WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                THEN SUM(- ail.price_subtotal)
                ELSE SUM(ail.price_subtotal)
            END / CASE
                   WHEN SUM(ail.quantity / u.factor * u2.factor) <> 0::numeric
                       THEN CASE
                             WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                                THEN SUM((- ail.quantity) / u.factor * u2.factor)
                                ELSE SUM(ail.quantity / u.factor * u2.factor)
                            END
                       ELSE 1::numeric
                  END AS price_average,
            CASE
             WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                THEN - ai.residual
                ELSE ai.residual
            END / (SELECT count(*) FROM account_invoice_line l where invoice_id = ai.id) *
            count(*) AS residual,
            ai.commercial_partner_id as commercial_partner_id,
            partner.country_id
        """
        return select_str

    def _from(self):
        from_str = """
            FROM account_invoice_line ail
            JOIN account_invoice ai ON ai.id = ail.invoice_id
            JOIN res_partner partner ON ai.commercial_partner_id = partner.id
            LEFT JOIN product_product pr ON pr.id = ail.product_id
            left JOIN product_template pt ON pt.id = pr.product_tmpl_id
            LEFT JOIN product_uom u ON u.id = ail.uos_id
            LEFT JOIN product_uom u2 ON u2.id = pt.uom_id
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY ail.product_id, ai.date_invoice, ai.id,
            ai.partner_id, ai.payment_term, ai.period_id, u2.name, u2.id, ai.currency_id, ai.journal_id,
            ai.fiscal_position, ai.user_id, ai.company_id, ai.type, ai.state, pt.categ_id,
            ai.date_due, ai.account_id, ail.account_id, ai.partner_bank_id, ai.residual,
            ai.amount_total, ai.commercial_partner_id, partner.country_id
        """
        return group_by_str

    def init(self, cr):
        # self._table = account_invoice_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            WITH currency_rate (currency_id, rate, date_start, date_end) AS (
                SELECT r.currency_id, r.rate, r.name AS date_start,
                    (SELECT name FROM res_currency_rate r2
                     WHERE r2.name > r.name AND
                           r2.currency_id = r.currency_id
                     ORDER BY r2.name ASC
                     LIMIT 1) AS date_end
                FROM res_currency_rate r
            )
            %s
            FROM (
                %s %s %s
            ) AS sub
            JOIN currency_rate cr ON
                (cr.currency_id = sub.currency_id AND
                 cr.date_start <= COALESCE(sub.date, NOW()) AND
                 (cr.date_end IS NULL OR cr.date_end > COALESCE(sub.date, NOW())))
        )""" % (
                    self._table,
                    self._select(), self._sub_select(), self._from(), self._group_by()))

class account_invoice_report(osv.osv):
    _inherit = 'account.invoice.report'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }
    _depends = {
        'account.invoice': ['section_id'],
    }

    def _select(self):
        return  super(account_invoice_report, self)._select() + ", sub.section_id as section_id"

    def _sub_select(self):
        return  super(account_invoice_report, self)._sub_select() + ", ai.section_id as section_id"

    def _group_by(self):
        return super(account_invoice_report, self)._group_by() + ", ai.section_id"


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
