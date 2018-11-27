# -*- coding: utf-8 -*-
import time
from datetime import datetime
from dateutil import relativedelta

from openerp import api, fields, models, tools, _
from openerp.exceptions import Warning as UserError, ValidationError
from openerp.addons.dym_base import DIVISION_SELECTION
import openerp.addons.decimal_precision as dp
import fungsi_terbilang

class DymPayrollDuedate(models.Model):
    _name = 'dym.payroll.duedate'

    # @api.one
    # @api.depends('due_date')
    # def _get_period(self):
    #     print "_get_period================================="
    #     AccPeriod = self.env['account.period']
    #     period_id = AccPeriod.search([('company_id','=',self.company_id.id),('date_start','<=',self.due_date),('date_stop','>=',self.due_date)])
    #     self.period_id = period_id.id

    @api.model
    def _get_default_period(self):
        user = self.env.user
        AccPeriod = self.env['account.period']
        period_id = AccPeriod.search([('company_id','=',user.company_id.id),('date_start','<=',datetime.now()),('date_stop','>=',datetime.now())])
        return period_id.id

    @api.model
    def _get_account_period(self):
        user = self.env.user
        AccPeriod = self.env['account.period']
        period_ids = [x.id for x in AccPeriod.search([('company_id','=',user.company_id.id),('state','=','draft')])]
        return [('id', 'in', period_ids)]

    name = fields.Char(string='Name')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, copy=False,
        default=lambda self: self.env['res.company']._company_default_get())
    period_id = fields.Many2one('account.period', string='Period', required=True, domain=_get_account_period, default=_get_default_period)
    line_ids = fields.One2many('dym.payroll.duedate.line', 'payroll_date_id', string='Due Date Line')

    @api.constrains('company_id','period_id')
    def _check_company_period(self):
        data = self.search([('company_id','=',self.company_id.id),('period_id','=',self.period_id.id)])
        if len(data)>1:
            raise UserError(_("Period Due Date is already exist!"))

    @api.model
    def create(self, vals):
        period_id = self.env['account.period'].browse(vals['period_id'])
        vals['name'] = '[%s] %s' % (period_id.name, period_id.company_id.name)
        return super(DymPayrollDuedate, self).create(vals)

    @api.one
    def write(self, vals):
        if vals.get('period_id', False):
            period_id = self.env['account.period'].browse(vals.get('period_id'))
            vals['name'] = '[%s] %s' % (period_id.name, period_id.company_id.name)
        return super(DymPayrollDuedate, self).write(vals)

class DymPayrollDuedateLine(models.Model):
    _name = 'dym.payroll.duedate.line'

    payroll_date_id = fields.Many2one('dym.payroll.duedate', string='Payroll Due Date', readonly=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, domain="[('supplier','=',True)]")
    due_date = fields.Date(string='Due Date')

    @api.constrains('payroll_date_id','partner_id')
    def _check_partner_duedate(self):
        data = self.search([('payroll_date_id','=',self.payroll_date_id.id),('partner_id','=',self.partner_id.id)])
        if len(data)>1:
            raise UserError(_("Partner Due Date is already exist!"))
 
class DymPayslipRun(models.Model):
    _inherit = 'dym.payslip.run'

    @api.multi
    def validate_payslip_run(self):
        res = super(DymPayslipRun, self).validate_payslip_run()

        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line']
        period_id = self.env['account.period'].find(self.date_end)
        PayslipLine = self.env['dym.payslip.line']
        AccountAccount = self.env['account.account']
        PayrollDate = self.env['dym.payroll.duedate']
        PayrollDateLine = self.env['dym.payroll.duedate.line']

        list_account_payable = PayslipLine.read_group([('company_id','=',self.company_id.id),('slip_id','=',self.slip_ids[0].id)], fields=['account_id'], groupby=['account_id'])
        list_account_payable = [x['account_id'][0] for x in list_account_payable]
        list_account_payable = [x.id for x in AccountAccount.search([('id','in',list_account_payable),('type','=','payable')])]

        list_partner = PayslipLine.read_group([('company_id','=',self.company_id.id),('account_id','in',list_account_payable),('slip_id','=',self.slip_ids[0].id)], fields=['partner_id'], groupby=['partner_id'])
        list_partner = [x['partner_id'] for x in list_partner]

        move_id = AccountMove.browse(self.slip_ids[0].move_id.id)

        for partner in list_partner:
            pay_date = PayrollDate.search([('period_id','=',period_id.id),('company_id','=',self.company_id.id)])
            payroll_date_line_id = PayrollDateLine.search([('payroll_date_id','=',pay_date.id),('partner_id','=',partner[0])])
            if not payroll_date_line_id or not payroll_date_line_id.due_date:
                raise UserError(_("Please set Payroll Due Date for partner %s!") % partner[1])
            move_line_id = AccountMoveLine.search([('move_id','=',move_id.id),('partner_id','=',partner[0])])
            if move_line_id:
                move_line_id.write({'date_maturity':payroll_date_line_id.due_date})
        move_id.button_validate()
        return res