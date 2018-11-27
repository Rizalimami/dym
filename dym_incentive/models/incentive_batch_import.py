# -*- coding: utf-8 -*-
import time
from datetime import datetime, date, timedelta
from dateutil import relativedelta

from openerp import api, fields, models, tools, _, exceptions
from openerp.addons.dym_base import DIVISION_SELECTION
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp.exceptions import Warning as UserError, RedirectWarning


INCENTIVE_STATE_SELECTIONS = [
    ('draft','Draft'),
    ('waiting_for_approval','Waiting For Approval'),
    ('approved','Approved'),
    ('done','Posted'),
    ('cancel','Cancelled'),
    ('reject','Rejected'),
]

DIVISION_SELECTIONS = [
    ('Unit','Showroom'),
    ('Sparepart','Workshop'),
    ('Umum','General'),
    ('Finance','Finance'),
    ('Service','Service'),
]

class IncentiveBatchImport(models.Model):
    _name = 'dym.incentive.batch.import'
    _description = 'DYM Incentive Batch Import'

    @api.one
    @api.depends('incentive_ids.total_cair')
    def _compute_total_cair(self):
        self.total_cair = sum(inc.total_cair for inc in self.incentive_ids)

    @api.one
    @api.depends('incentive_ids.total_dpp')
    def _compute_total_dpp(self):
        self.total_dpp = sum(inc.total_dpp for inc in self.incentive_ids)

    @api.one
    @api.depends('total_cair','cde_amount','state','cde_id')
    def _compute_writeoff_amount(self):
        AccMove = self.env['account.move']
        AccMoveLine = self.env['account.move.line']
        if self.incentive_payment_type == 'postpaid':
            cde_amount_balance = self.total_cair
            if self.cde_id:
                move_id = AccMove.search([('model','=','account.voucher'),('transaction_id','=',self.cde_id.id)])
                move_line_id = AccMoveLine.search([('move_id','=',move_id.id),('credit','!=',0)])
                if move_line_id:
                    cde_amount_balance = move_line_id.fake_balance
            self.writeoff_amount = cde_amount_balance - self.total_cair
        else:
            if self.state not in ('done'):
                total_cair = 0
                total_cde = 0
                cde_list = []
                for inc in self.incentive_ids:
                    total_cair = sum([x.debit for x in inc.voucher_id.move_ids if self.account_id.id == x.account_id.id and self.partner_id.id == x.partner_id.id])#inc.total_cair
                    for line in inc.line_ids:
                        if line.titipan_line_id.id not in cde_list:
                            total_cde += line.titipan_line_id.credit
                            cde_list.append(line.titipan_line_id.id)
                if total_cair != total_cde:
                    writeoff_amount = total_cde - total_cair
                    self.writeoff_amount = writeoff_amount
        
    name = fields.Char(required=True, readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', string='Leasing', domain=[('finance_company','=',True)], required=True)
    incentive_payment_type = fields.Selection([('prepaid','Pre-Paid'),('postpaid','Post-Paid')], related='partner_id.incentive_payment_type', string='Incentive Payment Type', help='Pre-Paid=Leasing company drop the money before the invoice, Post-Paid: Leasing drop the money after we send them invoice.')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal')
    account_id = fields.Many2one('account.account', string='Account')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=True)
    voucher_ids = fields.One2many('account.voucher', 'incentive_batch_id', 'Vouchers')
    incentive_ids = fields.One2many('dym.incentive.allocation', 'batch_id', string='Incentive Allocations', readonly=True,
        states={'draft': [('readonly', False)]})
    state = fields.Selection(INCENTIVE_STATE_SELECTIONS, string='Status', index=True, readonly=True, copy=False, default='draft')
    value_date = fields.Date(string='Transaction Date', required=True, readonly=True,
        states={'draft': [('readonly', False)]})    
    date = fields.Date(string='Date', required=True, readonly=True,
        states={'draft': [('readonly', False)]})
    total_cair = fields.Float(string='Total Cair', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_cair')
    total_dpp = fields.Float(string='Total DPP', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_dpp')
    cde_id = fields.Many2one('account.voucher', 'Customer Deposit', readonly=False)
    cde_amount = fields.Float('CDE Amount', related='cde_id.amount')
    use_withholding = fields.Boolean('Use Withholding')
    use_ppn = fields.Boolean('Use PPN')
    memo = fields.Char('Memo')
    payment_option = fields.Selection([
            ('without_writeoff', 'Keep Open'),
            ('with_writeoff', 'Reconcile Payment Balance'),
        ], 'Payment Difference', default='with_writeoff', required=True, help="This field helps you to choose what you want to do with the eventual difference between the paid amount and the sum of allocated amounts. You can either choose to keep open this difference on the partner's account, or reconcile it with the payment(s)")
    writeoff_amount = fields.Float(string='Diff Amount', digits=dp.get_precision('Account'), readonly=True, compute='_compute_writeoff_amount')       
    writeoff_account_id = fields.Many2one('account.account','Write-Off Account', )
    
    @api.one
    @api.model
    def write_memo(self):
        for incentive in self.incentive_ids:
            incentive.update({'description': self.memo})

    @api.one
    @api.onchange('branch_id','division')
    def onchange_branch_id(self):
        if not self.branch_id:
            return False
        config_id = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)], limit =1)
        incentive_journal_id = config_id.dym_incentive_allocation_journal
        if not incentive_journal_id:
            raise exceptions.ValidationError(_("Jurnal alokasi incentive tidak ditemukan. Silahkan configure di: Advance Config > Branch and Area > Branch Config."))
        self.journal_id = incentive_journal_id.id
        if not incentive_journal_id.default_debit_account_id:
            raise exceptions.ValidationError(_("Jurnal %s tidak memiliki default debit account."))
        self.account_id = incentive_journal_id.default_debit_account_id.id

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Incentive Batch Import tidak bisa di delete pada state %s' % rec.state))
        return super(IncentiveBatchImport, self).unlink()

    
    @api.onchange('branch_id','cde_id')
    def onchange_writeoff_account_id(self):
        config_id = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)], limit =1)
        return {'domain': {'writeoff_account_id':[('id','=',config_id.dym_writeoff_account_ids.ids)]}}
    
        
    @api.one
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id and self.partner_id.incentive_date_type=='current':
            self.value_date = self.date
        else:
            self.value_date = date.today().replace(day=1) - timedelta(days=1)

        if self.partner_id and self.value_date:
            self.name = 'Batch Import Incentive %s tgl %s' % (self.partner_id.ref or self.partner_id.default_code or self.partner_id.name, self.value_date)
        if self.partner_id:
            self.use_withholding = self.partner_id.use_withholding
            self.use_ppn = self.partner_id.use_ppn

    @api.model
    def default_get(self, fields_list):
        res = super(IncentiveBatchImport, self).default_get(fields_list)
        context = dict(self.env.context or {})
        date_end = date.today().replace(day=1) - timedelta(days=1)
        date_start = date_end.replace(day=1)
        date_end = date_end
        period_name = '%s - %s' % (date_start.strftime('%d'),date_end.strftime('%d %b %Y'))
        res['value_date'] = date_end.strftime(DATE_FORMAT)
        res['date'] = date.today().strftime(DATE_FORMAT)
        res['name'] = '/' 
        return res

    @api.multi
    def validate_incentive_batch_import(self):
        pass

    @api.multi
    def action_confirm_payment(self):
        if not self.branch_id:
            raise exceptions.ValidationError(_("Silahkan pilih cabang untuk melanjutkan!"))
        if not self.division:
            raise exceptions.ValidationError(_("Silahkan pilih division untuk melanjutkan!"))

        config_id = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)], limit =1)
        incentive_journal_id = config_id.dym_incentive_allocation_journal

        if not incentive_journal_id:
            raise exceptions.ValidationError(_("Jurnal alokasi incentive tidak ditemukan. Silahkan configure di: Advance Config > Branch and Area > Branch Config."))
        if not incentive_journal_id.default_debit_account_id:
            raise exceptions.ValidationError(_("Jurnal %s tidak memiliki default debit account."))
        if not incentive_journal_id.default_credit_account_id:
            raise exceptions.ValidationError(_("Jurnal %s tidak memiliki default credit account."))
        if not self.cde_id and self.incentive_payment_type != 'prepaid':
            raise exceptions.ValidationError(_("Tidak ditemukan CDE untuk mengkonfirmasi pembayaran, silahkan pilih CDE dulu!"))
        if self.cde_id.amount < self.total_cair and self.payment_option=='with_writeoff' and not self.writeoff_account_id and self.incentive_payment_type != 'prepaid':
            raise exceptions.ValidationError(_("Total CDE dan total tagihan tidak sesuai, tentukan write-off account untuk melanjutkan!")) 
        if self.cde_id.state!='posted' and self.incentive_payment_type != 'prepaid':
            raise exceptions.ValidationError(_("Status CDE Nomor %s belum posted, silahkan diposting dulu untuk melanjutkan!" % self.cde_id.state))
        titipan_line_id = self.cde_id.move_ids.filtered(lambda r: r.credit > 0 and r.account_id.id == incentive_journal_id.default_credit_account_id.id)

        if self.incentive_payment_type == 'prepaid':
            # Prepaid
            cde_move_line_id = False
            voucher_ar = False
            for inc in self.incentive_ids:
                for inc_line in inc.line_ids:
                    if not cde_move_line_id:
                        voucher = inc_line.create_voucher()
                        cde_move_line_id = inc_line.titipan_line_id.id
                        voucher_ar = voucher.id
                        inc_line.write({'voucher_id': voucher_ar})
                    else:
                        inc_line.write({'voucher_id': voucher_ar})
                inc.write({'state': 'done'})
            self.write({'state': 'done'})
        else: 
            #PostPaid
            if self.cde_id:
                cde_move_line_id = False
                voucher_ar = False
                for inc in self.incentive_ids:
                    for inc_line in inc.line_ids:
                        if not cde_move_line_id:
                            inc_line.write({'titipan_line_id': [x.id for x in self.cde_id.move_ids if x.partner_id.id == self.partner_id.id and x.credit > 0][0]})
                            voucher = inc_line.create_voucher(total=True)
                            voucher_ar = voucher.id
                            cde_move_line_id = inc_line.titipan_line_id.id
                            inc_line.write({'voucher_id': voucher_ar})
                        else:
                            inc_line.write({'voucher_id': voucher_ar, 'titipan_line_id':cde_move_line_id, 'state': 'done'})
                    inc.write({'state': 'done'})
                self.write({'state': 'done'})
       

    @api.multi
    def view_voucher(self):
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        dummy, act_window_id = mod_obj.get_object_reference('dym_account_voucher', 'action_sale_receipt2')
        result = act_obj.browse(act_window_id).read()[0]
        voucher_ids = [v.voucher_id.id for v in self.incentive_ids]
        result.update({
            'domain': [('id','in',voucher_ids)],
            'name': _('Other Receivable'),
            'view_type': 'form',
            'view_mode': 'tree,form',
        })
        return result

    @api.multi
    def view_voucher_cpa(self):
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        dummy, act_window_id = mod_obj.get_object_reference('account_voucher', 'action_vendor_receipt')
        result = act_obj.browse(act_window_id).read()[0]
        cpa_list = []
        for v in self.incentive_ids:
            for cpa in v.line_ids:
                if cpa.voucher_id.id not in cpa_list:
                    cpa_list.append(cpa.voucher_id.id)
        voucher_ids = cpa_list
        result.update({
            'domain': [('id','in',voucher_ids)],
            'name': _('Customer Payments'),
            'view_type': 'form',
            'view_mode': 'tree,form',
        })
        return result
