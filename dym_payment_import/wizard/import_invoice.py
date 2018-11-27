# -*- coding: utf-8 -*-
##############################################################################
#
#    This module copyright (C) 2015 Therp BV (<http://therp.nl>).
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

import base64
from datetime import datetime
from openerp import models, fields, api, _, exceptions
from openerp.osv import osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp.exceptions import Warning as UserError, RedirectWarning
import openerp.addons.decimal_precision as dp

class ImportAccountInvoice(models.TransientModel):
    _name = 'import.account.invoice'

    @api.depends('period_id')
    def _get_period(self):
        context = dict(self.env.context or {})
        if context.get('period_id', False):
            return context.get('period_id')
        periods = self.env['account.period'].find()
        return periods and periods[0] or False

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    partner_id = fields.Many2one(
        'res.partner', string='Supplier',
        help='Supplier name.')
    branch_id = fields.Many2one('dym.branch', string='Branch')
    account_id = fields.Many2one('account.account', string='Account')
    voucher_id = fields.Many2one('account.voucher', string='Voucher')
    payment_multi = fields.Boolean('Multi Payment', default=False)
    due_date_payment = fields.Date('Due Date')
    period_id = fields.Many2one('account.period',string="Period",required=True, default=_get_period)
    import_lines = fields.One2many('import.account.invoice.line','import_id','Debits')

    @api.model
    def default_get(self, fields):
        MoveLine = self.env['account.move.line']
        res = super(ImportAccountInvoice, self).default_get(fields)
        context = dict(self.env.context or {})
        active_model = context.get('active_model',False)
        active_ids = context.get('active_ids',[])
        if not active_model=='account.voucher':
            return res
        voucher = self.env['account.voucher'].browse(active_ids)
        res['voucher_id'] = voucher.id
        res['partner_id'] = voucher.partner_id.id
        res['period_id'] = voucher.period_id.id
        res['due_date_payment'] = voucher.due_date_payment
        res['payment_multi'] = voucher.payment_multi

        print "voucher.inter_branch_id.id>>>",voucher.inter_branch_id.id

        search_move_line = [
            ('account_id.type','=','payable'),
            ('credit','!=',0),
            ('reconcile_id','=',False),
            ('dym_loan_id','=',False),
            ('date_maturity','<=',voucher.due_date_payment),
            ('partner_id','=',voucher.partner_id.id),
            ('company_id','=',voucher.company_id.id),
        ]
        if not voucher.payment_multi:
            res['branch_id'] = voucher.inter_branch_id.id
            search_move_line.append(('branch_id','=',voucher.inter_branch_id.id))

        payables = MoveLine.search(search_move_line)
        if payables:
            res['account_id'] = payables[0].account_id.id
        else:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan hutang yang dapat dibayar."))
        return res

    @api.onchange('account_id')
    def onchange_account_id(self):
        MoveLine = self.env['account.move.line']
        if not all ([self.account_id,self.due_date_payment,self.partner_id]):
            return {}
        if self.import_lines:
            self.import_lines.unlink()

        search_move_line = [
            ('account_id.type','=','payable'),
            ('credit','!=',0),
            ('reconcile_id','=',False),
            ('dym_loan_id','=',False),
            ('date_maturity','<=',self.due_date_payment),
            ('date','>=',self.period_id.date_start),
            ('date','<=',self.period_id.date_stop),
            ('partner_id','=',self.partner_id.id),
        ]

        if not self.payment_multi:
            search_move_line.append(('branch_id','=',self.branch_id.id))
        payables = MoveLine.search(search_move_line)
        account_ids = list(set([p.account_id.id for p in payables]))

        search_move_line = [
            ('account_id.type','=','payable'),
            ('credit','!=',0),
            ('account_id','=',self.account_id.id),
            ('reconcile_id','=',False),
            ('dym_loan_id','=',False),
            ('date_maturity','<=',self.due_date_payment),
            ('date','>=',self.period_id.date_start),
            ('date','<=',self.period_id.date_stop),
            ('partner_id','=',self.partner_id.id),
        ]

        if not self.payment_multi:
            search_move_line.append(('branch_id','=',self.branch_id.id))
        payables = MoveLine.search(search_move_line)

        import_lines = []
        for payable in payables:
            import_lines.append((0,0,{
                'move_line_id': payable.id,
                'account_id': payable.account_id.id,
                'amount': payable.credit,
                'date_due': payable.date_maturity,
                'branch_id': payable.branch_id.id,
                'branch_dest_id': payable.analytic_3.branch_id.id,
            }))
        if import_lines:
            self.import_lines = import_lines
        return {
            'domain':{'account_id':[('id','in',account_ids)]},
        }

    @api.onchange('period_id')
    def onchange_period(self):
        if self.period_id:
            MoveLine = self.env['account.move.line']
            if not all ([self.account_id,self.due_date_payment,self.partner_id]):
                return {}
            if self.import_lines:
                self.import_lines.unlink()

            search_move_line = [
                ('account_id.type','=','payable'),
                ('credit','!=',0),
                ('reconcile_id','=',False),
                ('dym_loan_id','=',False),
                ('date_maturity','<=',self.due_date_payment),
                ('date','>=',self.period_id.date_start),
                ('date','<=',self.period_id.date_stop),
                ('partner_id','=',self.partner_id.id),
            ]

            if not self.payment_multi:
                search_move_line.append(('branch_id','=',self.branch_id.id))
            payables = MoveLine.search(search_move_line)
            account_ids = list(set([p.account_id.id for p in payables]))

            search_move_line = [
                ('account_id.type','=','payable'),
                ('credit','!=',0),
                ('account_id','=',self.account_id.id),
                ('reconcile_id','=',False),
                ('dym_loan_id','=',False),
                ('date_maturity','<=',self.due_date_payment),
                ('date','>=',self.period_id.date_start),
                ('date','<=',self.period_id.date_stop),
                ('partner_id','=',self.partner_id.id),
            ]

            if not self.payment_multi:
                search_move_line.append(('branch_id','=',self.branch_id.id))
            payables = MoveLine.search(search_move_line)

            import_lines = []
            for payable in payables:
                import_lines.append((0,0,{
                    'move_line_id': payable.id,
                    'account_id': payable.account_id.id,
                    'amount': payable.credit,
                    'date_due': payable.date_maturity,
                    'branch_id': payable.branch_id.id,
                    'branch_dest_id': payable.analytic_3.branch_id.id,
                }))
            if import_lines:
                self.import_lines = import_lines
            self.import_lines = import_lines
            return {
                'domain':{'account_id':[('id','in',account_ids)]},
            }

    @api.multi
    def action_import_lines(self):
        Voucher = self.env['account.voucher'].browse(self.voucher_id.id)
        VoucherLine = self.env['account.voucher.line']
        amount = 0
        for line in self.import_lines:
            amount += line.amount
            values = {
                'voucher_id': self.voucher_id.id,
                'move_line_id': line.move_line_id.id,
                'account_id': self.account_id.id,
                'reconcile': True,
                'amount': line.amount,
                'date_due': line.date_due,
                'type': 'dr',
                'branch_dest_id': line.move_line_id.branch_id.id,
                'account_analytic_id': line.move_line_id.analytic_4.id,
                'analytic_1': line.move_line_id.analytic_1.id,
                'analytic_2': line.move_line_id.analytic_2.id,
                'analytic_3': line.move_line_id.analytic_3.id,
            }
            voucher_line_id = VoucherLine.create(values)
        Voucher.write({'amount':amount,'net_amount':amount})

    @api.multi
    def get_lines(self):
        Invoice = self.env['account.invoice']
        invoices = Invoice.search([('partner_id','=',self.partner_id.id),('type','in',['in_invoice'])])

class ImportAccountInvoiceLine(models.TransientModel):
    _name = 'import.account.invoice.line'

    name = fields.Char('Description')
    import_id = fields.Many2one('import.account.invoice', string='Import')
    account_id = fields.Many2one('account.account','Account', required=True)
    branch_id = fields.Many2one('dym.branch', string='Branch')
    untax_amount = fields.Float('Untax Amount')
    amount = fields.Float('Amount', digits_compute=dp.get_precision('Account'))
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    move_line_id = fields.Many2one('account.move.line', 'Journal Item', copy=False)
    date_original = fields.Date(related='move_line_id.date', string='Date Original', readonly=1)
    date_due = fields.Date(related='move_line_id.date_maturity', string='Date Due', readonly=1)
    branch_dest_id = fields.Many2one('dym.branch', string='For Branch')
