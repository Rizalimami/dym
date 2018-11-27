# -*- coding: utf-8 -*-
import time
from datetime import datetime, date, timedelta
from dateutil import relativedelta

from openerp import api, fields, models, tools, _, exceptions
from openerp.addons.dym_base import DIVISION_SELECTION
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp.exceptions import Warning as UserError, RedirectWarning


BB_STATE_SELECTIONS = [
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

class BlindBonusBatchImport(models.Model):
    _name = 'dym.bb.batch.import'
    _description = 'DYM Blind Bonus Batch Import'

    @api.one
    @api.depends('line_ids.amount_dpp')
    def _compute_total_dpp(self):
        self.total_dpp = sum(inc.amount_dpp for inc in self.line_ids)
        # if self.withholding_id:
        #     self.withholding_amount = self.withholding_id.amount * self.total_dpp
    @api.one
    @api.depends('total_dpp')
    def _compute_total_cair(self):
        self.total_cair = self.total_dpp + (self.total_dpp * 0.1)
        if self.withholding_id:
            self.total_cair = self.total_dpp + (self.total_dpp * 0.1) - (self.withholding_id.amount * self.total_dpp)
            
    @api.one
    @api.depends('total_cair','cde_amount')
    def _compute_writeoff_amount(self):
        self.writeoff_amount = self.cde_amount - self.total_cair

    

    name = fields.Char(required=True, readonly=True, states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=True)
    
    journal_id = fields.Many2one('account.journal', 'Journal', required=True)
    account_id = fields.Many2one('account.account', related='journal_id.default_debit_account_id')

    line_ids = fields.One2many('dym.bb.batch.import.line', 'batch_id', string='Line', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(BB_STATE_SELECTIONS, string='Status', index=True, readonly=True, copy=False, default='draft')
    value_date = fields.Date(string='Transaction Date', required=True, readonly=True, states={'draft': [('readonly', False)]})    
    date = fields.Date(string='Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    # total_cair = fields.Float(string='Total Cair', digits=dp.get_precision('Account'), readonly=True)
    total_cair = fields.Float(string='Total Cair', digits=dp.get_precision('Account'), compute='_compute_total_cair')
    
    total_dpp = fields.Float(string='Total DPP', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_dpp')
    voucher_id = fields.Many2one('account.voucher', 'Invoice', readonly=False)
    cde_id = fields.Many2one('account.voucher', 'Customer Deposit', readonly=False)
    cde_amount = fields.Float('CDE Amount', related='cde_id.amount')
    memo = fields.Char('Memo')
    withholding_id = fields.Many2one('account.tax.withholding','Withholding', readonly=True, states={'draft': [('readonly', False)]})
    voucher_ids = fields.One2many('account.voucher', 'bb_batch_id', 'Vouchers')
    cde_id = fields.Many2one('account.voucher', 'Customer Deposit')
    cde_amount = fields.Float('CDE Amount', related='cde_id.amount') 
    writeoff_amount = fields.Float(string='Diff Amount', digits=dp.get_precision('Account'), readonly=True, compute='_compute_writeoff_amount')       
    writeoff_account_id = fields.Many2one('account.account','Write-Off Account', )
    # withholding_amount = fields.Float("Withholding Amount")


    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'BLB', division='Umum')
        return super(BlindBonusBatchImport, self).create(vals)

    
    @api.onchange('account_id')
    def onchange_account_id(self):
        if self.account_id:
            dom={}
            dom['withholding_id'] = [('id','in',self.account_id.withholding_tax_ids.ids)]

            return {'domain':dom}

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Blind Bonus Batch Import tidak bisa di delete pada state %s' % rec.state))
        return super(BlindBonusBatchImport, self).unlink()  


    # @api.onchange('withholding_id')
    # def onchange_withholding_id(self):
    #     if self.withholding_id:
    #         self.withholding_amount = self.withholding_id.amount * self.total_dpp
    #         print self.withholding_amount,'---------------------'
    #         self.write({'withholding_amount': self.withholding_amount})            


    @api.onchange('branch_id','cde_id')
    def onchange_writeoff_account_id(self):
        config_id = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)], limit =1)
        return {'domain': {'writeoff_account_id':[('id','=',config_id.dym_writeoff_account_ids.ids)]}}
    

    @api.model
    def default_get(self, fields_list):
        res = super(BlindBonusBatchImport, self).default_get(fields_list)
        context = dict(self.env.context or {})
        company_id = self.env.user.company_id
        branch_id = self.env['dym.branch'].search([('company_id','=',company_id.id),('branch_type','=','HO')], limit=1)
        if branch_id:
            res['branch_id'] = branch_id.id
        res['division'] = 'Finance'
        res['value_date'] = date.today().strftime(DATE_FORMAT)
        res['date'] = date.today().strftime(DATE_FORMAT)
        res['name'] = '/' 
        res['memo'] = 'Sales Insentif/Pembelian'
        return res

    @api.one
    @api.onchange('branch_id')
    def onchange_branch_id(self):
        if self.branch_id:
            config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
            if config.dym_bb_journal:
                self.journal_id = config.dym_bb_journal.id

    @api.multi
    def view_voucher(self):
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        dummy, act_window_id = mod_obj.get_object_reference('dym_account_voucher', 'action_sale_receipt2')
        result = act_obj.browse(act_window_id).read()[0]
        voucher_ids = [v.id for v in self.voucher_ids if 'NDE-' in v.number]
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
        voucher_ids = [v.id for v in self.voucher_ids if 'CPA-' in v.number]
        result.update({
            'domain': [('id','in',voucher_ids)],
            'name': _('Customer Payments'),
            'view_type': 'form',
            'view_mode': 'tree,form',
        })
        return result


    @api.multi
    def action_confirm_payment(self):
        # if self.incentive_payment_type != 'postpaid':
        #     raise exceptions.ValidationError(_("Confirm payment hanya digunakan untuk Leasing yang pemnbayaran incentive-nya dibelakang ('Post Paid') saja!"))
        if not self.branch_id:
            raise exceptions.ValidationError(_("Silahkan pilih cabang untuk melanjutkan!"))
        if not self.division:
            raise exceptions.ValidationError(_("Silahkan pilih division untuk melanjutkan!"))

        config_id = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)], limit =1)
        bb_journal_id = config_id.dym_bb_journal

        if not bb_journal_id:
            raise exceptions.ValidationError(_("Jurnal Blind Bonus tidak ditemukan. Silahkan configure di: Advance Config > Branch and Area > Branch Config."))
        if not bb_journal_id.default_debit_account_id:
            raise exceptions.ValidationError(_("Jurnal %s tidak memiliki default debit account."))
        if not bb_journal_id.default_credit_account_id:
            raise exceptions.ValidationError(_("Jurnal %s tidak memiliki default credit account."))
        if not self.cde_id:
            raise exceptions.ValidationError(_("Tidak ditemukan CDE untuk mengkonfirmasi pembayaran, silahkan pilih CDE dulu!"))
        if self.cde_id.amount < self.total_cair and not self.writeoff_account_id:
            # raise exceptions.ValidationError(_("Total CDE hanya sebesar %s, sedangkan total tagihannya sebesar %s!" % (self.cde_id.amount,self.total_cair)))
            raise exceptions.ValidationError(_("Total CDE dan total tagihan tidak sesuai, tentukan write-off account untuk melanjutkan!")) 
        

        if self.cde_id.state!='posted':
            raise exceptions.ValidationError(_("Status CDE Nomor %s belum posted, silahkan diposting dulu untuk melanjutkan!" % self.cde_id.state))
        # titipan_line_id = self.cde_id.move_ids.filtered(lambda r: r.credit > 0 and r.account_id.id == incentive_journal_id.default_credit_account_id.id)

        # fake_balance = titipan_line_id.fake_balance
        # for inc in self.incentive_ids:
        #     inc.write({
        #         'cde_id': self.cde_id.id,
        #         'titipan_line_id': titipan_line_id.id,
        #     })
        #     if not inc.voucher_id:
        #         inc.create_voucher()
        #     inc.write({'state':'done'})
        # self.write({'state':'done'})
        self.create_voucher_cpa()
        self.write({'state': 'done'})
       
    @api.multi
    def create_voucher_cpa(self):
        move_line_id = self.cde_id.move_ids.filtered(lambda r: r.credit > 0)
        if not move_line_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi titipan!"))
        amount = self.total_cair if move_line_id.fake_balance >= self.total_cair else move_line_id.fake_balance
        move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_id.id, amount, False, False)
        values = {
            'move_line_id': move_line_vals['value']['move_line_id'], 
            'account_id': move_line_vals['value']['account_id'], 
            'date_original': move_line_vals['value']['date_original'], 
            'date_due': move_line_vals['value']['date_due'], 
            'amount_original': move_line_vals['value']['amount_original'], 
            'amount_unreconciled': move_line_vals['value']['amount_unreconciled'],
            'amount': move_line_id.fake_balance, 
            'currency_id': move_line_vals['value']['currency_id'], 
            'type': 'dr', 
            'name': move_line_vals['value']['name'],
            'reconcile': True,
        }
        voucher_line = [[0,0,values]]
        branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)], limit =1)
        move_line_ar = self.env['account.move.line'].search([('account_id','=', branch_config.dym_bb_journal.default_debit_account_id.id),('partner_id','=',self.line_ids[0].partner_id.id),('ref','=',self.name),('reconcile_id','=', False),('debit','!=',0.0)])[0]
        amount_ar = move_line_ar.debit
        move_line_ar_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_ar.id, amount_ar, False, False)
        if move_line_ar:
            if amount_ar == amount:
                voucher_cr_line = [[0,0,{
                    'move_line_id': move_line_ar_vals['value']['move_line_id'], 
                    'account_id': move_line_ar_vals['value']['account_id'], 
                    'date_original': move_line_ar_vals['value']['date_original'], 
                    'date_due': move_line_ar_vals['value']['date_due'], 
                    'amount_original':move_line_ar.debit, 
                    'amount_unreconciled': amount_ar,
                    'amount': amount_ar, 
                    'currency_id': move_line_ar_vals['value']['currency_id'], 
                    'type': 'cr', 
                    'name': move_line_ar_vals['value']['name'],
                    'reconcile': True, #if amount == amount_ar else (False if amount < amount_ar else True),
                }]]
            else:
                voucher_cr_line = [[0,0,{
                    'move_line_id': move_line_ar_vals['value']['move_line_id'], 
                    'account_id': move_line_ar_vals['value']['account_id'], 
                    'date_original': move_line_ar_vals['value']['date_original'], 
                    'date_due': move_line_ar_vals['value']['date_due'], 
                    'amount_original':move_line_ar.debit, 
                    'amount_unreconciled':move_line_ar.debit,
                    'amount': move_line_ar.debit, 
                    'currency_id': move_line_ar_vals['value']['currency_id'], 
                    'type': 'cr', 
                    'name': move_line_ar_vals['value']['name'],
                    'reconcile': True, #if amount == amount_ar else (False if amount < amount_ar else True),
                }]]
        else:
            invoice = self.env['account.invoice'].search([('origin','=',self.lot_id.dealer_sale_order_id.name)], limit =1)
            cpa_line = ', '.join([x.move_id.name for x in invoice.payment_ids])
            if invoice.state == 'paid':
                raise osv.except_osv(('Perhatian!'), ('AR untuk Engine No. %s (%s) sudah dibayar di transaksi %s') % (self.lot_id.name,self.partner_id.name_get()[0][1],cpa_line))


        journal_alokasi = branch_config.dym_bb_journal
        if not journal_alokasi:
            raise osv.except_osv(('Perhatian !'), ("Journal alokasi Incentive belum lengkap dalam branch %s !")%(branch_config.branch_id.name))
        analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.branch_id, 'Umum',False, 4, 'General')
        writeoff_account_id = False
        payment_option = 'without_writeoff'
        if self.writeoff_account_id:
            writeoff_account_id = self.writeoff_account_id.id
            payment_option = 'with_writeoff'
        # print self.writeoff_amount,'******'
        # print a
        voucher = {
            'branch_id':self.branch_id.id, 
            'division': self.division, 
            'inter_branch_id':self.branch_id.id, 
            'inter_branch_division': self.division, 
            'partner_id': self.line_ids[0].partner_id.id, 
            'date':datetime.now().strftime('%Y-%m-%d'), 
            'amount':0, 
            'reference': self.name, 
            'name': self.memo, 
            'user_id': self._uid,
            'type': 'receipt',
            'line_dr_ids': voucher_line,
            'line_cr_ids': voucher_cr_line,
            'analytic_1': analytic_1,
            'analytic_2': analytic_2,
            'analytic_3': analytic_3,
            'analytic_4': analytic_4,
            'journal_id': journal_alokasi.id,
            'account_id': journal_alokasi.default_debit_account_id.id,
            'bb_batch_id': self.id,
            'writeoff_amount': self.writeoff_amount,
            'payment_option':  payment_option,
            'writeoff_acc_id': writeoff_account_id,

        }        
        
        voucher_obj = self.env['account.voucher']
        voucher_id = voucher_obj.create(voucher)
        self.write({
            'voucher_id': voucher_id.id,
            'state':'done',
        })
        voucher_id.validate_or_rfa_credit()
        voucher_id.signal_workflow('approval_approve')
        return True


class BlindBonusBatchImportLine(models.Model):
    _name = 'dym.bb.batch.import.line'
    _description = 'DYM Blind Bonus Batch Import Line'

    name = fields.Char(required=True, readonly=True)
    batch_id = fields.Many2one('dym.bb.batch.import', 'Batch', required=True)
    inter_branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    inter_division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=True)
    partner_id = fields.Many2one('res.partner', string='Main Dealer', domain=[('principle','=',True)], required=True)    
    amount_dpp = fields.Float(string='Amount', digits=dp.get_precision('Account'), readonly=True)
    type = fields.Selection([('unit','Unit'),('oli','Oli'),('part','Part')], string='Type')


