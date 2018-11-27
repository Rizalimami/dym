import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class dym_transaction_withholding(models.Model):
    _name = "dym.transaction.withholding"
    _description = "Transaction Withholding"
    
    settle_id = fields.Many2one(
        'dym.settlement',
        'Settlement',
        required=True,
        ondelete='cascade',
        )

    display_name = fields.Char(
        compute='get_display_name'
        )
    name = fields.Char(
        'Nomor Bukti Potong',
        )
    internal_number = fields.Char(
        'Internal Number',
        required=True,
        default='/',
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    date = fields.Date(
        'Date',
        required=True,
        default=fields.Date.context_today,
        )
    tax_withholding_id = fields.Many2one(
        'account.tax.withholding',
        string='Jenis PPh',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    comment = fields.Text(
        'Additional Information',
        )
    amount = fields.Float(
        'Jumlah PPh',
        required=True,
        digits=dp.get_precision('Account'),
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    tax_base = fields.Float(
        'Tax Base',
        required=True,
        digits=dp.get_precision('Account'),
        states={'draft': [('readonly', False)]},
        )
    move_line_id = fields.Many2one(
        'account.move.line',
        'Journal Item',
        readonly=True,
        )
    # Related fields
    partner_id = fields.Many2one(
        'res.partner',
        'Partner', readonly=True,
        )
    company_id = fields.Many2one(
        'res.company',
        # related='settle_id.company_id',
        string='Company', store=True, readonly=True
        )
    # branch_id = fields.Many2one(
    #     'account.voucher.line',
    #     related='settle_id.voucher_line.bra',
    #     string='Branch'
    #     )
    state = fields.Selection(
        related='settle_id.state',
        default='draft',
        )
    type = fields.Selection(
        related='settle_id.type',
        string='Tipe',
        # string='Type',
        # waiting for a PR 9081 to fix computed fields translations
        readonly=True,
        )

    analytic_2 = fields.Many2one('account.analytic.account', 'Bisnis Unit')
    model = fields.Char('Model')
    transaction_id = fields.Integer('ID Transaction')

    tax_state = fields.Selection(
        related='move_line_id.tax_state'
    )

    type_tax_use = fields.Selection(
        [('receipt', 'Receipt'), ('payment', 'Payment'), ('all', 'All')],
        'Tax Application',
        related="tax_withholding_id.type_tax_use",
        required=True
    )

    @api.one
    @api.depends('settle_id')
    def get_tax_base(self):
        self.tax_base = self.settle_id.net_amount

    def _unit_compute_inv(self, cr, uid, taxes, price_unit):
        res = []
        cur_price_unit = price_unit

        tax_parent_tot = 0.0
        for tax in taxes:
            if tax.type=='percent':
                tax_parent_tot += tax.amount

        for tax in taxes:
            if tax.type=='fixed':
                cur_price_unit -= tax.amount

        for tax in taxes:
            if tax.type=='percent':
                amount = (cur_price_unit / (1 + tax_parent_tot)) * tax.amount

            elif tax.type=='fixed':
                amount = tax.amount

            todo = 1
            values = {
                'id': tax.id,
                'todo': todo,
                'name': tax.name,
                'amount': amount,
                'account_collected_id': tax.account_id.id,
                'account_paid_id': tax.ref_account_id.id,
                'account_analytic_collected_id': tax.account_analytic_id.id,
                'account_analytic_paid_id': tax.ref_account_analytic_id.id,
                'base_code_id': tax.base_code_id.id,
                'ref_base_code_id': tax.ref_base_code_id.id,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'price_unit': cur_price_unit,
                'tax_code_id': tax.tax_code_id.id,
                'ref_tax_code_id': tax.ref_tax_code_id.id,
            }
            res.append(values)

        total = 0.0
        for r in res:
            if r['todo']:
                total += r['amount']
        for r in res:
            r['price_unit'] -= total
            r['todo'] = 0
        return res

    def compute_inv(self, cr, uid, taxes, price_unit, precision=None):
        if not precision:
            precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        res = self._unit_compute_inv(cr, uid, taxes, price_unit)
        total = 0.0
        for r in res:
            if r.get('balance',False):
                r['amount'] = round(r['balance'], precision) - total
            else:
                r['amount'] = round(r['amount'], precision)
                total += r['amount']
        return res

    def _unit_compute(self, cr, uid, taxes, price_unit):
        res = []
        cur_price_unit=price_unit
        for tax in taxes:
            # we compute the amount for the current tax object and append it to the result
            if tax.type=='percent':
                amount = cur_price_unit * tax.amount

            elif tax.type=='fixed':
                amount = tax.amount

            data = {
                'id':tax.id,
                'name': tax.name,
                'amount': amount,
                'account_collected_id':tax.account_id.id,
                'account_paid_id':tax.ref_account_id.id,
                'account_analytic_collected_id': tax.account_analytic_id.id,
                'account_analytic_paid_id': tax.ref_account_analytic_id.id,
                'base_code_id': tax.base_code_id.id,
                'ref_base_code_id': tax.ref_base_code_id.id,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'price_unit': cur_price_unit,
                'tax_code_id': tax.tax_code_id.id,
                'ref_tax_code_id': tax.ref_tax_code_id.id,
            }
            res.append(data)
        return res

    def _compute(self, cr, uid, taxes, price_unit, precision=None):
        if not precision:
            precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        res = self._unit_compute(cr, uid, taxes, price_unit)
        total = 0.0
        for r in res:
            if r.get('balance',False):
                r['amount'] = round(r.get('balance', 0.0), precision) - total
            else:
                r['amount'] = round(r.get('amount', 0.0), precision)
                total += r['amount']
        return res

    @api.onchange('tax_base','tax_withholding_id')
    def get_tax_amount(self):
        amount = 0
        if self.tax_base == 0:
            self.tax_base = self.settle_id.amount_total
        if self.model == 'dym.settlement':
            settlement = self.env[self.model].browse(self.transaction_id)
            self.tax_base = sum(line.amount for line in settlement.settlement_line)

        if self.tax_base and self.tax_withholding_id and self.tax_withholding_id.type != 'none':
            precision = self.env['decimal.precision'].precision_get('Account')
            tax_compute_precision = precision
            if self.tax_withholding_id.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_compute_precision += 5
            totalin = totalex = round(self.tax_base, precision)
            tin = []
            tex = []
            if not self.tax_withholding_id.price_include:
                tex.append(self.tax_withholding_id)
            else:
                tin.append(self.tax_withholding_id)
            tin = self.compute_inv(tin, self.tax_base, precision=tax_compute_precision)
            for r in tin:
                totalex -= r.get('amount', 0.0)
            totlex_qty = 0.0
            try:
                totlex_qty = totalex
            except:
                pass
            tex = self._compute(tex, totlex_qty, precision=tax_compute_precision)
            for r in tex:
                totalin += r.get('amount', 0.0)
            res = {
                'total': totalex,
                'total_included': totalin,
                'taxes': tin + tex
            }
            amount = sum(t['amount'] for t in res['taxes'])            
        self.amount = amount

    @api.one
    @api.depends('name', 'internal_number')
    def get_display_name(self):
        display_name = self.internal_number
        if self.name:
            display_name += ' (%s)' % self.name
        self.display_name = display_name

    @api.one
    @api.constrains('tax_withholding_id', 'settle_id')
    def check_tax_withholding(self):
        if self.settle_id.branch_id.company_id != self.tax_withholding_id.company_id:
            raise Warning(_(
                'Voucher and Tax Withholding must belong to the same company'))

    @api.onchange('net_amount')
    def onchange_amount_total_view(self):
        self.amountview = self.net_amount

    @api.model
    def create(self, vals):
        if vals.get('internal_number', '/') == '/':
            tax_withholding = self.tax_withholding_id.browse(
                vals.get('tax_withholding_id'))
            if not tax_withholding:
                raise Warning(_('Tax Withholding is Required!'))
            sequence = tax_withholding.sequence_id
            vals['internal_number'] = sequence.next_by_id(sequence.id) or '/'
        vals['company_id'] = tax_withholding.company_id.id
        kas_negara_id = self.env['res.partner'].search([('kas_negara','=',True)])
        if not kas_negara_id:
            raise Warning(_(
                'Kas Negara belum ditentukan, silahkan centang Kas Negara di form Partner'))
        vals['partner_id'] = kas_negara_id.id
        return super(dym_transaction_withholding, self).create(vals)
        return res