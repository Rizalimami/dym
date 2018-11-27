# -*- coding: utf-8 -*-
import time
from datetime import datetime
from dateutil import relativedelta

from openerp import api, fields, models, tools, _
from openerp.exceptions import Warning as UserError, ValidationError
from openerp.addons.dym_base import DIVISION_SELECTION
import openerp.addons.decimal_precision as dp
import fungsi_terbilang

PAYSLIP_STATE_SELECTIONS = [
    ('draft', 'Draft'),
    ('close', 'Closed'),
]
PAYROLL_STATE_SELECTIONS = PAYSLIP_STATE_SELECTIONS

DIVISION_SELECTIONS_X = [
    ('Unit','Showroom'),
    ('Sparepart','Workshop'),
    ('Umum','General'),
    ('Finance','Finance'),
    ('Service','Service'),
]

class DymPayslipRun(models.Model):
    _name = 'dym.payslip.run'
    _description = 'DYM Payslip Batches'

    name = fields.Char(readonly=True, states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    slip_ids = fields.One2many('dym.payslip', 'payslip_run_id', string='Payslips', readonly=True,
        states={'draft': [('readonly', False)]})
    state = fields.Selection(PAYROLL_STATE_SELECTIONS, string='Status', index=True, readonly=True, copy=False, default='draft')
    date_start = fields.Date(string='Date From', required=True, readonly=True,
        states={'draft': [('readonly', False)]}, default=time.strftime('%Y-%m-01'))
    date_end = fields.Date(string='Date To', required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    description = fields.Text('Description')

    """
    This had been deactivated since it is no longer required
    ***

    @api.multi
    def get_slip_lines(self,branch,division):
        account_ids = self.env['account.account'].search([('code','in',ACCOUNTS),('company_id','=',self.company_id.id)])
        n = 0
        slip_lines = []
        request = '''
            SELECT DISTINCT 
                cost_center 
            FROM 
                account_analytic_account 
            WHERE 
                type='normal' AND 
                state='open' AND 
                segmen=4 AND 
                branch_id=%s'''
        params = (branch.id,)
        self._cr.execute(request, params)

        for account in account_ids:
            slip_analytics = []
            for row in self._cr.dictfetchall():
                cost_center = row['cost_center']
                analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(branch.id, division, False, 4, cost_center)
                analytics = {
                    'sequence': n,
                    'branch_id': branch.id,
                    'division': division,
                    'analytic_id': analytic_4,
                    'amount': 999,
                }
                slip_analytics.append((0,0,analytics))

            partner_id = self.company_id.partner_id
            n += 1
            values = {
                'sequence': n,
                'account_id': account.id,
                'partner_id': partner_id.id,
                'branch_id': branch.id,
                'division': division,
                'analytic_ids': slip_analytics,
            }
            slip_lines.append((0,0,values))
        return slip_lines

    @api.multi
    def get_slip_ids(self):
        Slip = self.env['dym.payslip']
        Branch = self.env['dym.branch']
        Analytic = self.env['account.analytic.account']
        branches = Branch.search([('company_id','=',self.company_id.id)])
        divisions = [d[0] for d in DIVISION_SELECTION]
        account_ids = self.env['account.account'].search([('code','in',ACCOUNTS),('company_id','=',self.company_id.id)])
        n = 0
        slips = []
        for branch in branches:
            for division in divisions:
                values = {
                    'company_id': self.company_id.id,
                    'branch_id': branch.id,
                    'division': division,
                    'line_ids': self.get_slip_lines(branch,division),
                }
                slip_id = Slip.create(values)
                slips.append(slip_id.id)
        return slips

    @api.multi
    def compute_payslip_run(self):
        for payslip in self:
            payslip.slip_ids.unlink()
            slip_ids = self.get_slip_ids()
            payslip.write({'slip_ids': [(6,0,slip_ids)]})
    """

    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil

    @api.model
    def create(self, vals):
        user = self.env.user
        branch_id = self.env['dym.branch'].search([('company_id','=',user.company_id.id),('branch_status','=','HO')])
        vals['name'] = self.env['ir.sequence'].get_per_branch(branch_id.id,'PRL', division='Finance')
        return super(DymPayslipRun, self).create(vals)

    @api.multi
    def validate_payslip_run(self):
        AccountMove = self.env['account.move']
        Withholdings = self.env['account.tax.withholding']
        wh_tax_ids = Withholdings.search([('company_id','=',self.company_id.id)])
        wh_tax_ids = list(set([t.account_id.id for t in wh_tax_ids]))
        # move_name = '%s (%s-%s)' % (self.name,self.date_start,self.date_end)
        period_id = self.env['account.period'].find(self.date_end)
        for payslip in self:
            for slip in payslip.slip_ids:
                move = {
                    'name': payslip.name,
                    'ref': payslip.name,
                    'journal_id': slip.journal_id.id,
                    'date': self.date_end,
                    'period_id': period_id.id,
                    'reverse_from_id': False,
                    'transaction_id': payslip.id,
                    'model': payslip.__class__.__name__,
                }
                line_id = []
                for line in slip.line_ids:
                    description = payslip.description if line.account_id.id in wh_tax_ids else line.account_id.name
                    for analytic in line.analytic_ids:
                        if not analytic.amount:
                            continue
                        move_line = {
                            'name': description,
                            'ref': slip.number,
                            'account_id': line.account_id.id,
                            'journal_id': slip.journal_id.id,
                            'period_id': period_id.id,
                            'date': self.date_end,
                            'debit': analytic.amount > 0.0 and analytic.amount or 0.0,
                            'credit': analytic.amount < 0.0 and abs(analytic.amount) or 0.0,
                            'branch_id' : line.branch_id.id,
                            'division' : line.division,
                            'partner_id' : line.partner_id.id,
                            'analytic_account_id' : analytic.analytic_id.id,     
                        } 
                        line_id.append((0,0,move_line))
                move.update({'line_id':line_id})
                move_id = AccountMove.create(move)
                slip.write({'move_id': move_id.id})
        self.write({'state':'close'})

class DymPayslip(models.Model):
    _name = 'dym.payslip'
    _description = 'Pay Slip'

    @api.model
    def _get_default_branch(self):
        user = self.env.user
        branch_ids = self.env['dym.branch'].search([('company_id','=',user.company_id.id),('branch_type','!=','HO')])
        for branch in user.branch_ids:
            if branch.id in branch_ids.ids and branch.branch_type!='HO':
                return branch.code

    @api.model
    def _getCompanyBranch(self):
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        branch_ids = [b.id for b in self.env.user.branch_ids if b.company_id.id==company_id]
        return [('id','in',branch_ids)]

    @api.one
    @api.depends('line_ids.amount')
    def _compute_amount(self):
        self.amount = sum(line.amount for line in self.line_ids)

    sequence = fields.Integer(string='Sequence', default=10,
        help="Gives the sequence of this line when displaying the invoice.")
    partner_id = fields.Many2one('res.partner')
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, default=_get_default_branch, domain=_getCompanyBranch)
    user_id = fields.Many2one('hr.employee', string='Responsible')
    division = fields.Selection(DIVISION_SELECTIONS_X, string='Division', change_default=True, select=True)
    journal_id = fields.Many2one("account.journal", string="Journal")
    analytic_id = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center')
    name = fields.Char(string='Payslip Name', readonly=True,
        states={'draft': [('readonly', False)]})
    number = fields.Char(string='Reference', readonly=True, copy=False,
        states={'draft': [('readonly', False)]})
    date_from = fields.Date(string='Date From', readonly=True, required=True,
        default=time.strftime('%Y-%m-01'), states={'draft': [('readonly', False)]})
    date_to = fields.Date(string='Date To', readonly=True, required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
        states={'draft': [('readonly', False)]})
    state = fields.Selection(PAYSLIP_STATE_SELECTIONS, string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")
    line_ids = fields.One2many('dym.payslip.line', 'slip_id', string='Payslip Lines', readonly=True,
        states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Company', readonly=True, copy=False,
        default=lambda self: self.env['res.company']._company_default_get(),
        states={'draft': [('readonly', False)]})
    paid = fields.Boolean(string='Made Payment Order ? ', readonly=True, copy=False,
        states={'draft': [('readonly', False)]})
    note = fields.Text(string='Internal Note', readonly=True, states={'draft': [('readonly', False)]})
    credit_note = fields.Boolean(string='Credit Note', readonly=True,
        states={'draft': [('readonly', False)]},
        help="Indicates this payslip has a refund of another")
    payslip_run_id = fields.Many2one('dym.payslip.run', string='Payslip Batches', readonly=True,
        copy=False, states={'draft': [('readonly', False)]})
    amount = fields.Float(string='Amount',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_line_ids = fields.One2many('account.move.line',related='move_id.line_id',string='Journal Items', readonly=True)

class DymPayslipLine(models.Model):
    _name = 'dym.payslip.line'

    @api.one
    @api.depends('analytic_ids.amount')
    def _compute_amount(self):
        self.amount = sum(analytic.amount for analytic in self.analytic_ids)

    sequence = fields.Integer(string='Sequence', default=10,
        help="Gives the sequence of this line when displaying the invoice.")
    slip_id = fields.Many2one('dym.payslip', string='Pay Slip', ondelete='cascade')
    account_id = fields.Many2one('account.account')
    company_id = fields.Many2one('res.company', string='Company')
    partner_id = fields.Many2one('res.partner')
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True)
    division = fields.Selection(DIVISION_SELECTIONS_X, string='Division', change_default=True, select=True)
    analytic_ids = fields.One2many('dym.payslip.analytic', 'line_id', string='Payslip Analytic', readonly=False)
    state = fields.Selection(PAYSLIP_STATE_SELECTIONS, string='Status', related="slip_id.state")
    date_from = fields.Date(string='Date From', readonly=True, required=True,
        default=time.strftime('%Y-%m-01'), states={'draft': [('readonly', False)]})
    date_to = fields.Date(string='Date To', readonly=True, required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
        states={'draft': [('readonly', False)]})
    amount = fields.Float(string='Amount',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')

class DymPayslipAnalytic(models.Model):
    _name = 'dym.payslip.analytic'

    name = fields.Char(string='Payslip Name')
    sequence = fields.Integer(string='Sequence', default=10,
        help="Gives the sequence of this line when displaying the invoice.")
    line_id = fields.Many2one('dym.payslip.line', string='Pay Slip Line', ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company')
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True)
    division = fields.Selection(DIVISION_SELECTIONS_X, string='Division', change_default=True, select=True)
    account_id = fields.Many2one('account.account')
    analytic_id = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center')
    amount = fields.Float(digits=dp.get_precision('Payroll'))
    state = fields.Selection(PAYSLIP_STATE_SELECTIONS, string='Status', related="line_id.state")
    date_from = fields.Date(string='Date From', readonly=True, required=True,
        default=time.strftime('%Y-%m-01'), states={'draft': [('readonly', False)]})
    date_to = fields.Date(string='Date To', readonly=True, required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
        states={'draft': [('readonly', False)]})
