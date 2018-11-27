import time
from datetime import datetime
from openerp.osv import osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError, RedirectWarning

class dym_bank_transfer(models.Model):
    _inherit = 'dym.bank.transfer'

    is_settlement = fields.Boolean('Is Settlement')
    line_ids3 = fields.One2many('dym.bank.transfer.line','bank_transfer_id', string="Bank Transfer Line")

    @api.onchange('branch_type')
    def get_default_transaction_type(self):
    	if self.branch_type == 'HO':
    		self.transfer_type = 'normal'

    @api.one
    @api.depends('line_ids.amount','line_ids1.amount','line_ids2.amount','line_ids3.amount','bank_fee','voucher_line_ids.amount_unreconciled','invoice_line_ids.amount_total','deposit_ahass_ids.amount')
    def _compute_amount(self):
        # super(dym_bank_transfer,self)._compute_amount()
        total_line = 0.0
        if self.line_ids:
            total_line = sum([line.amount for line in self.line_ids])
        if self.line_ids1:
            total_line = sum([line.amount for line in self.line_ids1])
        if self.line_ids2:
            total_line = sum([line.amount for line in self.line_ids2])
        if self.line_ids3:
            total_line = sum([line.amount for line in self.line_ids3])
        if self.bank_fee:
            total_line += self.bank_fee
        if self.voucher_line_ids:
            total_line += sum([line.amount_unreconciled for line in self.voucher_line_ids])
        if self.invoice_line_ids:
            total_line += sum([line.amount_total for line in self.invoice_line_ids])
        if self.deposit_ahass_ids:
            total_line += sum([line.amount for line in self.deposit_ahass_ids])
        self.amount_total = total_line
        self.amount = total_line
        self.amount_show = total_line
        
        # if self.branch_id.branch_type!='HO' and self.transaction_type in ['withdraw','ats','ho2branch'] and self.state=='draft' and self.amount_total > self.current_balance and not self.bank_trf_advice_id:
        #     raise UserError(_('Total transaksi tidak boleh lebih dari saldo tersedia. 2'))


    @api.onchange('payment_from_id_deposit','payment_from_id_withdraw','payment_from_id_ats','payment_from_id_ho2branch','payment_from_id_inhouse','branch_id')
    def onchange_payment_from_dwhai_id(self):
        dom = {}
        val = {}
        war = {}
        for rec in self:
            user = self.env.user
            rec.payment_from_id = False
            if rec.payment_from_id_deposit:
                rec.payment_from_id = rec.payment_from_id_deposit.id
            if rec.payment_from_id_withdraw:
                rec.payment_from_id = rec.payment_from_id_withdraw.id
            if rec.payment_from_id_ats:
                rec.payment_from_id = rec.payment_from_id_ats.id
            if rec.payment_from_id_ho2branch:
                rec.payment_from_id = rec.payment_from_id_ho2branch.id
            if rec.payment_from_id_inhouse:
                rec.payment_from_id = rec.payment_from_id_inhouse.id

            branch_id = rec._context.get('branch_id',False)
            transaction_type = self.env.context.get('transaction_type',False)
            if not transaction_type:
                raise osv.except_osv(('Perhatian !'), _('Maaf, menu ini hanya boleh digunakan untuk melihat transaksi yang sudah dibuat sebelumnya.'))

            # Deposit
            if transaction_type == 'deposit':
                return {
                    'domain': {
                        'payment_from_id_deposit': [('company_id','=',user.company_id.id),('type','=',self.env.context.get('journal_type',False))]
                    },
                }

            # Withdrawal
            if transaction_type == 'withdraw':
                if rec.branch_id.ahass_parent_id:
                    self._check_config_ahass(rec.branch_id)
                    payment_from_id_withdraw = self._get_payment_from_id_withdraw(rec.branch_id)
                    withdraw_domain = [('id','=',payment_from_id_withdraw.id)]
                    rec.payment_method = 'cash'
                    rec.payment_from_id_withdraw = payment_from_id_withdraw.id
                else:
                    rec.clearing_bank = True
                    rec.payment_method = 'cheque'
                    # withdraw_domain = [('type','=','bank'),('transaction_type','=','out'),('branch_id','=',rec.branch_id.id)]
                    if self.branch_id.branch_status == 'HO':
                        withdraw_domain = [('type','=','bank'),('branch_id','=',rec.branch_id.id)]
                    else:
                        withdraw_domain = [('type','=','bank'),('transaction_type','=','out'),('branch_id','=',rec.branch_id.id)]
                    if rec.payment_from_id_withdraw:
                        payment_from_id_withdraw_ids = self.env['account.journal'].search(withdraw_domain)
                        if not rec.payment_from_id_withdraw.id in payment_from_id_withdraw_ids.ids:
                            rec.payment_from_id_withdraw = False
                        acc_number = self.env['res.partner.bank'].search([('journal_id','=',rec.payment_from_id_withdraw.id)])
                        if not acc_number:
                            rec.payment_from_id_withdraw = False
                            return {
                                'warning': {
                                    'title': _('Warning!'), 
                                    'message': _('Jurnal %s tidak memiliki rekening bank. Jika ini adalah jurnal bank, silahkan buat rekening di menu Sale > Configuration > Localization > Bank Account.' % self.payment_from_id_withdraw.name)
                                }
                            }
                    else:
                        payment_from_id_withdraw_ids = self.env['account.journal'].search(withdraw_domain)
                        selected_journal = False
                        for payment_from_id_withdraw_id in payment_from_id_withdraw_ids:
                            if self.env['res.partner.bank'].search([('journal_id','=',payment_from_id_withdraw_id.id)]):
                                selected_journal = payment_from_id_withdraw_id
                                break

                        if selected_journal:
                            rec.payment_from_id_withdraw = selected_journal.id
                        else:
                            return {
                                'warning': {
                                    'title': _('Warning!'), 
                                    'message': _('Cabang %s tidak memiliki satupun rekening bank. Hubungi system administrator untuk melanjutkan.' % rec.branch_id.name)
                                }
                            }
                return {
                    'domain': {
                        'payment_from_id_withdraw': withdraw_domain,
                    },
                }

            # ATS
            if transaction_type == 'ats':
                if rec.payment_from_id_ats:
                    acc_number = self.env['res.partner.bank'].search([('journal_id','=',rec.payment_from_id_ats.id)])
                    if not acc_number:
                        rec.payment_from_id_ats = False
                        return {
                            'warning': {
                                'title': _('Warning!'), 
                                'message': _('Jurnal %s tidak memiliki rekening bank. Jika ini adalah jurnal bank, silahkan buat rekening di menu Sale > Configuration > Localization > Bank Account.' % rec.payment_from_id_withdraw.name)
                            }
                        }
                return {
                    'domain': {
                        'payment_from_id_ats': [('type','=','bank'),('transaction_type','=','in'),('branch_id','=',rec.branch_id.id)],
                    },
                }

            # HO2Branch
            if transaction_type == 'ho2branch':
                if user.branch_type != 'HO':
                    rec.branch_id = False
                    raise osv.except_osv(('Perhatian !'), ("Maaf, user %s tidak memiliki akses untuk membuat transaksi Head Office." % user.login))
                journal_ids = []
                for jnl in self.env['account.journal'].sudo().search([('company_id','=',rec.branch_id.company_id.id),('branch_id','=',rec.branch_id.id),('type','=','bank'),('transaction_type','=','in')]):
                    if jnl.branch_id.id == rec.branch_id.id:
                        journal_ids.append(jnl.id)
                dom['payment_from_id_ho2branch'] = [('id','in',journal_ids)]
                return {'domain': dom}

            # InHouse
            if transaction_type == 'inhouse':
                if user.branch_type != 'HO':
                    rec.branch_id = False
                    raise osv.except_osv(('Perhatian !'), ("Maaf, user %s tidak diperbolehkan untuk membuat transaksi pemindahan uang antar rekening bank." % user.login))
                journal_ids = self.env['account.journal'].sudo().search([('company_id','=',rec.branch_id.company_id.id),('branch_id','=',rec.branch_id.id),('type','=','bank')])
                dom['payment_from_id_inhouse'] = [('id','in',journal_ids.ids)]
                if rec.payment_from_id_inhouse:
                    acc_number = self.env['res.partner.bank'].search([('journal_id','=',rec.payment_from_id_inhouse.id)])
                    if not acc_number:
                        rec.payment_from_id_inhouse = False
                        return {
                            'warning': {
                                'title': _('Warning!'), 
                                'message': _('Jurnal %s tidak memiliki rekening bank. Jika ini adalah jurnal bank, silahkan buat rekening di menu Sale > Configuration > Localization > Bank Account.' % rec.payment_from_id_withdraw.name)
                            }
                        }
                    rec.clearing_bank = True
                return {
                    'domain': dom,
                }

    @api.multi
    def wkf_approval(self):
        res = super(dym_bank_transfer, self).wkf_approval()
        if res:
            for line3 in self.line_ids3:
                if line3.reimburse_ho_id:
                    line3.reimburse_ho_id.state = 'done'
        return res

class dym_bank_transfer_line(models.Model): 
    _inherit = 'dym.bank.transfer.line'

    reimburse_ho_id = fields.Many2one('dym.reimbursed.ho',domain="[('state','=','approved')]", string="Reimbursed No")

    @api.onchange('reimburse_ho_id')
    def onchange_reimbursement_ho_id(self):
        if self.reimburse_ho_id:
            self.amount = self.reimburse_ho_id.amount_total
