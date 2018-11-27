from openerp.tools.translate import _
from openerp import models, fields, api, SUPERUSER_ID
from openerp.osv import osv
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError, RedirectWarning

class dym_bank_transfer_ahass_deposit(models.Model):
    _name = 'dym.bank.transfer.ahass.deposit'

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('confirmed', 'Waiting Approval'),
        ('waiting_for_approval','Payment in Process'),
        ('waiting_for_confirm_received','Waiting For Confirm Received'),
        ('app_approve', 'Process Done'),
        ('app_received', 'Received'),
        ('approved','Done'),
        ('cancel','Cancelled')
    ]
    
    withdrawal_id = fields.Many2one('dym.bank.transfer', 'Withdrawal')
    deposit_ahass_id = fields.Many2one('dym.ahass.deposit', string="AHASS Deposit")
    name = fields.Char(related='deposit_ahass_id.name',string='Number')
    date = fields.Date(related='deposit_ahass_id.date',string='Date')
    branch_parent_id = fields.Many2one('dym.branch',related='deposit_ahass_id.branch_parent_id',string='AHASS Parent')
    branch_ahass_id = fields.Many2one('dym.branch',related='deposit_ahass_id.branch_ahass_id',string='AHASS Child')
    amount = fields.Float(string="Amount",digits_compute=dp.get_precision('Account'))
    withdraw_journal_id = fields.Many2one('account.journal', related="withdrawal_id.payment_from_id_withdraw", string="Source of Fund")
    withdraw_amount = fields.Float(related="withdrawal_id.amount_show", string='Amount')
    withdraw_date = fields.Date(related="withdrawal_id.date", string='Date')
    withdraw_payment_method = fields.Selection([
        ('giro','Giro'),
        ('cash','Cash'),
        ('ats','ATS'),
        ('cheque','Cheque'),
        ('internet_banking','Internet Banking'),
        ('auto_debit','Auto Debit')
        ], related='withdrawal_id.payment_method', string='Payment Method')
    state = fields.Selection(STATE_SELECTION, string='State', related='withdrawal_id.state',)

    @api.onchange('deposit_ahass_id')
    def onchange_deposit_ahass_id(self):
        dom = {}
        ahass_list = []
        dym_ahass_deposit = self.env['dym.ahass.deposit'].search([])
        for a in dym_ahass_deposit:
            if sum([x.withdraw_amount for x in a.withdrawal_ids]) < a.amount:
                ahass_list.append(a.id)
        dom['deposit_ahass_id']=[('id','in',ahass_list)]
        self.amount = self.deposit_ahass_id.amount
        return {'domain': dom}

class dym_bank_transfer(models.Model):
    _inherit = 'dym.bank.transfer'

    branch_via_id = fields.Many2one('dym.branch', string='Via Branch', domain="[('company_id','=',company_id)]")
    move_ahass_id = fields.Many2one('account.move', string='Account Entry AHASS', copy=False)
    move_ahass_ids = fields.One2many('account.move.line',related='move_ahass_id.line_id',string='Journal Items AHASS', readonly=True)
    move_piutang_induk_id = fields.Many2one('account.move', string='Account Entry AHASS', copy=False)
    move_piutang_induk_ids = fields.One2many('account.move.line',related='move_piutang_induk_id.line_id',string='Journal Items AHASS', readonly=True)
    deposit_ahass_ids = fields.One2many('dym.bank.transfer.ahass.deposit','withdrawal_id',string="AHASS Deposit")

    @api.one
    @api.depends('line_ids.amount','line_ids1.amount','line_ids2.amount','bank_fee','voucher_line_ids.amount_unreconciled','invoice_line_ids.amount_total','deposit_ahass_ids.amount')
    def _compute_amount(self):
        # super(dym_bank_transfer,self)._compute_amount()
        total_line = 0.0
        if self.line_ids:
            total_line = sum([line.amount for line in self.line_ids])
        if self.line_ids1:
            total_line = sum([line.amount for line in self.line_ids1])
        if self.line_ids2:
            total_line = sum([line.amount for line in self.line_ids2])
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
        if self.transaction_type in ['withdraw','ats','ho2branch'] and self.state=='draft' and self.amount_total > self.current_balance and not self.bank_trf_advice_id:
            raise UserError(_('Total transaksi tidak boleh lebih dari saldo tersedia.'))

    @api.model
    def _check_config_ahass(self,branch_id=None):
        config_ahass = self.env['dym.branch.config'].search([('branch_id','=',branch_id.id)])
        if not config_ahass:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan konfigurasi untuk cabang '%s', hubungi system administrator." % branch_id.name))  
        if not config_ahass.ahass_titipan_kas_journal_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan konfigurasi jurnal titipan kas AHASS untuk cabang induk '%s', hubungi system administrator." % branch_id.name))  
        if not config_ahass.ahass_piutang_induk_journal_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan konfigurasi jurnal piutang induk atas kas AHASS untuk cabang induk '%s', hubungi system administrator." % branch_id.name))  
        ahass_titipan_kas_journal_id = config_ahass.ahass_titipan_kas_journal_id
        ahass_piutang_induk_journal_id = config_ahass.ahass_piutang_induk_journal_id
        if not ahass_titipan_kas_journal_id.default_debit_account_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan default akun debit pada jurnal titipan kas AHASS untuk cabang induk '%s', hubungi system administrator." % branch_id.name))  
        if not ahass_titipan_kas_journal_id.default_credit_account_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan default akun credit pada jurnal titipan kas AHASS untuk cabang induk '%s', hubungi system administrator." % branch_id.name))  
        if not ahass_piutang_induk_journal_id.default_debit_account_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan default akun debit pada jurnal piutang kas induk AHASS untuk cabang induk '%s', hubungi system administrator." % branch_id.name))  
        if not ahass_piutang_induk_journal_id.default_credit_account_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan default akun credit pada jurnal piutang kas induk AHASS untuk cabang induk '%s', hubungi system administrator." % branch_id.name))  

    @api.model
    def _get_payment_from_id_withdraw(self,branch_id=None):
        config_ahass = self.env['dym.branch.config'].search([('branch_id','=',branch_id.id)])
        return config_ahass.ahass_piutang_induk_journal_id

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

    @api.cr_uid_ids_context
    def action_move_line_create(self, cr, uid, ids, mit=False, context=None):
        this = self.browse(cr, uid, ids, context=context)
        if context is None:
            context = {}
        move_ahass_id = False
        move_ahass_piutang_induk_id = False
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        for banktransfer in self.browse(cr, uid, ids, context=context):
            name = banktransfer.name
            date = banktransfer.date
            if banktransfer.state in ['approved','app_received']:
                if not banktransfer.receive_date:
                    raise osv.except_osv(('Perhatian !'), ("Tanggal terima wajib diisi"))
                date = banktransfer.receive_date

            if banktransfer.transaction_type == 'deposit':
                payment_from_id = banktransfer.payment_from_id_deposit 
            elif banktransfer.transaction_type == 'withdraw':
                payment_from_id = banktransfer.payment_from_id_withdraw 
            elif banktransfer.transaction_type == 'ats':
                payment_from_id = banktransfer.payment_from_id_ats 
            elif banktransfer.transaction_type == 'ho2branch':
                payment_from_id = banktransfer.payment_from_id_ho2branch 
            elif banktransfer.transaction_type == 'inhouse':
                payment_from_id = banktransfer.payment_from_id_inhouse 
            else:
                raise osv.except_osv(('Perhatian !'), ("Journal Bank Pengirim tidak ditemukan"))

            self.write(cr, uid, ids, {'payment_from_id':payment_from_id.id}, context=context) 
                
            journal_id = banktransfer.payment_from_id.id
            credit_account_id = banktransfer.payment_from_id.default_credit_account_id
            debit_account_id = banktransfer.payment_from_id.default_debit_account_id
            
            if not credit_account_id or not debit_account_id:
                raise osv.except_osv(('Perhatian !'), ("Account belum diisi dalam journal %s!")%(banktransfer.payment_from_id.name))
            amount = banktransfer.amount          
            period_id = banktransfer.period_id.id  
            config_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',banktransfer.branch_id.id)])

            if not config_id :
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan konfigurasi untuk cabang '%s', hubungi system administrator." % banktransfer.branch_id.name))  
           
            config = self.pool.get('dym.branch.config').browse(cr, uid, config_id, context=context)
            
            if mit and not config.banktransfer_mit:
                raise osv.except_osv(('Perhatian !'), ("System diminta untuk membuat journal entry dengan akun perantara (Money in transit) tapi di konfigurasi cabang bank transfer mit tidak dicentang. Hubungi system administrator untuk melanjutkan."))  

            if banktransfer.bank_fee > 0:
                bank_fee_account = config.bank_transfer_fee_account_id
                if not bank_fee_account:
                    raise osv.except_osv(('Perhatian !'), ("Akun untuk menampung bank transfer fee belum disetting. Silahkan setting dulu di Branch Config."))  

            if config.banktransfer_mit:
                if this.transaction_type=='deposit':
                    if not config.bank_deposit_mit_account_id:
                        raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan konfigurasi akun perantara untuk transaksi Setoran (biasanya akun Setoran Tunai Perantara) pada cabang '%s', hubungi system administrator." % this.branch_id.name))  
                    for line in this.line_ids:
                        if line.payment_to_id.type != 'bank':
                            raise osv.except_osv(('Perhatian !'), ("Jurnal %s tidak termasuk jurnal bank tapi jurnal %s. Transaksi Deposit / penyetoran kas ke bank hanya boleh dari jurnal Kas ke jurnal Bank saja. Silahkan hubungi system administrator untuk melanjutkan." % (line.payment_to_id.name,line.payment_to_id.type)))  
                    bank_mit_account = config.bank_deposit_mit_account_id

                elif this.transaction_type=='withdraw':
                    if not config.bank_withdrawal_mit_account_id:
                        raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan konfigurasi akun perantara untuk transaksi Penarikan (biasanya akun Penggantian Kas) pada cabang '%s', hubungi system administrator." % this.branch_id.name))  
                    for line in this.line_ids:
                        if line.payment_to_id.type not in ['pettycash','cash']:
                            raise osv.except_osv(('Perhatian !'), ("Jurnal %s tidak termasuk jurnal 'Cash/Petty Cash' tapi jurnal %s. Transaksi Withdrawal / pengambilan bank hanya boleh dari jurnal bank ke jurnal cash saja. Silahkan hubungi system administrator untuk melanjutkan." % (line.payment_to_id.name,line.payment_to_id.type)))  
                    bank_mit_account = config.bank_withdrawal_mit_account_id

                elif this.transaction_type in ['ats','ho2branch','inhouse']:
                    if not config.bank_transfer_mit_account_id:
                        raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan konfigurasi akun perantara untuk transaksi ATS, Ho2Branch dan Inhouse Transfer (biasanya akun Pindahan Antar bank) pada cabang '%s', hubungi system administrator." % this.branch_id.name))  
                    for line in this.line_ids:
                        if line.payment_to_id.type != 'bank':
                            raise osv.except_osv(('Perhatian !'), ("Jurnal %s tidak termasuk jurnal bank tapi jurnal %s. Transaksi ini hanya boleh dari jurnal bank ke jurnal bank saja. Silahkan hubungi system administrator untuk melanjutkan." % (line.payment_to_id.name,line.payment_to_id.type)))  
                    bank_mit_account = config.bank_transfer_mit_account_id
                else:
                    raise osv.except_osv(('Perhatian !'), ("System tidak mengenal transaksi ini, system hanya mengenal transaksi deposit, witdrawal, ats, ho2branch dan inhouse saja."))  

                if bank_mit_account.type != 'liquidity':
                    raise osv.except_osv(('Perhatian !'), ("Akun Money In Transit %s type-nya harus liquidity, silahkan hubungi administrator untuk melanjutkan." % bank_mit_account.name))  

                if not bank_mit_account.reconcile:
                    raise osv.except_osv(('Perhatian !'), ("Akun Money In Transit %s harus reconcileable (bisa direkonsiliasi), silahkan hubungi administrator untuk melanjutkan." % bank_mit_account.name))  

            move_vals = {
                'name': name,
                'ref':name,
                'journal_id': journal_id,
                'date': date,
                'period_id':period_id,
                'transaction_id':banktransfer.id,
                'model':banktransfer.__class__.__name__,
            }            
            move_id = move_pool.create(cr, uid, move_vals, context=None)
            clearing_bank = 'not_clearing'
            if banktransfer.clearing_bank:
                clearing_bank = 'open'
            if banktransfer.branch_id.ahass_parent_id:
                if not config.ahass_account_kas_induk:
                    raise osv.except_osv(('Perhatian !'), ("Akun Kas AHASS belum ditentukan untuk cabang %s, silahkan hubungi administrator untuk melanjutkan." % banktransfer.branch_id.name))  
                if mit==True:
                    account__id = config.ahass_account_kas_induk.id if banktransfer.transaction_type=='withdraw' else credit_account_id.id
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, SUPERUSER_ID, banktransfer.branch_id.ahass_parent_id.id, 'Umum', False, 4, 'General')
                    analytic__4 = analytic_4
                    branch__id = banktransfer.branch_id.ahass_parent_id.id if banktransfer.transaction_type=='withdraw' else banktransfer.branch_id.id
                else:
                    account__id = bank_mit_account.id
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, SUPERUSER_ID, banktransfer.branch_id.id, 'Umum', False, 4, 'General')
                    analytic__4 = analytic_4
                    branch__id = banktransfer.branch_id.id
            else:
                account__id = credit_account_id.id if not banktransfer.move_mit_id.id else bank_mit_account.id
                analytic__4 = banktransfer.analytic_4.id
                branch__id = banktransfer.branch_id.id

            #Tambahan kondisi untuk analytic jika transaksi withdrawal
            if banktransfer.transaction_type=='withdraw':
                if banktransfer.branch_id.ahass_parent_id:
                    analytic_wd_1, analytic_wd_2, analytic_wd_3, analytic_wd_4 = self.pool.get('account.analytic.account').get_analytical(cr, SUPERUSER_ID, banktransfer.branch_id.ahass_parent_id.id, 'Umum', False, 4, 'General')
                else:
                    analytic_wd_4 = banktransfer.analytic_4.id

            move_line1 = {
                'name':name,
                'ref':name,
                'account_id': account__id,
                'move_id': move_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'date': date,
                'debit': 0.0,
                'credit': banktransfer.amount,
                'branch_id' : branch__id,
                'division' : banktransfer.division,
                'analytic_account_id' : banktransfer.analytic_4.id if not banktransfer.transaction_type=='withdraw'  else analytic_wd_4,  # Tambahan kondisi
                'clear_state': clearing_bank,
            }
            line_id = move_line_pool.create(cr, uid, move_line1, context)   

            if mit == True:    
                move_line_mit = {
                    'name':name,
                    'clear_state':'open',
                    'ref':name,
                    'account_id': bank_mit_account.id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'date': date,
                    'debit': banktransfer.amount,
                    'credit': 0.0,
                    'branch_id' : banktransfer.branch_id.id,
                    'division' : banktransfer.division,
                    'clearing_bank': clearing_bank,
                    'analytic_account_id' : banktransfer.analytic_4.id if not banktransfer.transaction_type=='withdraw' else analytic_wd_4  # Tambahan kondisi   
                }
                line_mit_id = move_line_pool.create(cr, uid, move_line_mit, context)
                
                if banktransfer.branch_id.ahass_parent_id and banktransfer.transaction_type == 'withdraw': 
                    account_piutang_induk_id = config.ahass_piutang_induk_journal_id.default_credit_account_id.id
                    account_titipan_ahass_id = config.ahass_titipan_kas_journal_id.default_debit_account_id.id
                    move_line1 = {
                        'name':name,
                        'ref':name,
                        'account_id': account_piutang_induk_id,
                        'move_id': move_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'date': date,
                        'debit': 0.0,
                        'credit': banktransfer.amount,
                        'branch_id' : banktransfer.branch_id.id,
                        'division' : banktransfer.division,
                        'analytic_account_id' : banktransfer.analytic_4.id,
                        'clear_state': clearing_bank,
                    }
                    line_id = move_line_pool.create(cr, uid, move_line1, context)
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, SUPERUSER_ID, banktransfer.branch_id.ahass_parent_id.id, 'Umum', False, 4, 'General')
                    analytic__4 = analytic_4
                    move_line1 = {
                        'name':name,
                        'ref':name,
                        'account_id': account_titipan_ahass_id,
                        'move_id': move_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'date': date,
                        'debit': banktransfer.amount,
                        'credit': 0.0,
                        'branch_id' : banktransfer.branch_id.ahass_parent_id.id,
                        'division' : banktransfer.division,
                        'analytic_account_id' : analytic__4,
                        'clear_state': clearing_bank,
                    }
                    line_id = move_line_pool.create(cr, uid, move_line1, context)
            else:
                
                if banktransfer.bank_fee > 0 :
                    move_line3 = {
                        'name': _('Bank Transfer Fee'),
                        'ref':name,
                        'account_id': bank_fee_account.id,
                        'move_id': move_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'date': date,
                        'debit': banktransfer.bank_fee,
                        'credit': 0.0,
                        'branch_id' : banktransfer.branch_id.id,
                        'division' : banktransfer.division,
                        'analytic_account_id' : banktransfer.analytic_4.id                 
                    }    
                    line_id3 = move_line_pool.create(cr, uid, move_line3, context) 

                # Generate Move AHASS
                if banktransfer.branch_via_id:
                    self._check_config_ahass(cr, uid, banktransfer.branch_id, context=context)

                    # Generate Jurnal Titipan Kas di Induk
                    move_ahass_vals = {
                        'name': name,
                        'ref':name,
                        'journal_id': config.ahass_titipan_kas_journal_id.id,
                        'date': date,
                        'period_id':period_id,
                        'transaction_id':banktransfer.id,
                        'model':banktransfer.__class__.__name__,
                    }
                    move_ahass_id = move_pool.create(cr, uid, move_ahass_vals, context=None)
                    #Tambahan penentuan analytic
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, banktransfer.branch_via_id.id, 'Umum', False, 4, 'General')
                    move_ahass_line1 = {
                        'name':name,
                        'ref':name,
                        'account_id': config.ahass_titipan_kas_journal_id.default_credit_account_id.id,
                        'move_id': move_ahass_id,
                        'journal_id': config.ahass_titipan_kas_journal_id.id,
                        'period_id': period_id,
                        'date': date,
                        'debit': 0.0,
                        'credit': banktransfer.amount,
                        'branch_id' : banktransfer.branch_via_id.id, #via
                        'division' : banktransfer.inter_branch_division,
                        'analytic_account_id' : analytic_4,
                        'clear_state': clearing_bank,
                    }
                    line_ahass_id = move_line_pool.create(cr, uid, move_ahass_line1, context) 
                    
                    for y in banktransfer.line_ids:
                        branch_destination = self.pool.get('dym.branch').search(cr,SUPERUSER_ID,[('code','=',y.branch_destination_id)])
                        branch_dest = self.pool.get('dym.branch').browse(cr,SUPERUSER_ID,branch_destination)
                        total_debit = y.amount
                        move_ahass_line_2 = {
                            'name': _('Bank Transfer Detail %s')%(branch_dest.name),
                            'ref':name,
                            'account_id': bank_mit_account.id,
                            'move_id': move_ahass_id,
                            'journal_id': config.ahass_titipan_kas_journal_id.id,
                            'period_id': period_id,
                            'date': date,
                            'debit': total_debit,
                            'credit': 0.0,
                            'branch_id' : banktransfer.branch_via_id.id, #via
                            'division' : banktransfer.inter_branch_division,
                            'analytic_account_id' : y.analytic_4.id                             
                        }
                        line_ahass_id2 = move_line_pool.create(cr, uid, move_ahass_line_2, context)
                    
                    for y in banktransfer.voucher_line_ids:
                        branch_dest = y.branch_id
                        total_debit = y.amount_unreconciled
                        pettycash_journal_ids = self.pool.get('account.journal').search(cr, uid, [('company_id','=',y.company_id.id),('type','=','pettycash')], limit=1)
                        account_id = self.pool.get('account.journal').browse(cr, uid, pettycash_journal_ids, context=context)
                        move_ahass_ine_2 = {
                            'name': _('Bank Transfer Detail %s')%(branch_dest.name),
                            'ref':name,
                            'account_id': bank_mit_account.id,
                            'move_id': move_ahass_id,
                            'journal_id': config.ahass_titipan_kas_journal_id.id,
                            'period_id': period_id,
                            'date': date,
                            'debit': total_debit,
                            'credit': 0.0,
                            'branch_id' : branch_dest.branch_via_id.id, #via
                            'division' : y.move_line_id.inter_branch_division,
                            'analytic_account_id' : y.move_line_id.analytic_account_id.id                             
                        }
                        line_ahass_id2 = move_line_pool.create(cr, uid, move_ahass_ine_2, context)

                    # Added by Kahfi======================================start
                    for y in banktransfer.deposit_ahass_ids:
                        branch_dest = y.branch_parent_id
                        total_debit = y.amount
                        move_ahass_line_2 = {
                            'name': _('Bank Transfer Detail %s')%(branch_dest.name),
                            'ref':name,
                            'account_id': bank_mit_account.id,
                            'move_id': move_ahass_id,
                            'journal_id': config.ahass_titipan_kas_journal_id.id,
                            'period_id': period_id,
                            'date': date,
                            'debit': total_debit,
                            'credit': 0.0,
                            'branch_id' : branch_dest.id, #via
                            'division' : branch_dest.division,
                            'analytic_account_id' : banktransfer.analytic_4.id                             
                        }
                        line_ahass_id2 = move_line_pool.create(cr, uid, move_ahass_line_2, context)
                    
                    for y in banktransfer.invoice_line_ids:
                        branch_dest = y.invoice_id.branch_id
                        total_debit = y.amount_total
                        move_ahass_ine_2 = {
                            'name': _('Bank Transfer Detail %s')%(branch_dest.name),
                            'ref':name,
                            'account_id': bank_mit_account.id,
                            'move_id': move_ahass_id,
                            'journal_id': config.ahass_titipan_kas_journal_id.id,
                            'period_id': period_id,
                            'date': date,
                            'debit': total_debit,
                            'credit': 0.0,
                            'branch_id' : branch_dest.id,
                            'division' : branch_dest.division,
                            'analytic_account_id' : y.invoice_id.analytic_4.id                             
                        }
                        line_ahass_id2 = move_line_pool.create(cr, uid, move_ahass_ine_2, context) 
                    # Added by Kahfi======================================finish
                    
                    # Generate Jurnal Piutang Induk Kas AHASS
                    move_ahass_piutang_induk_vals = {
                        'name': name,
                        'ref':name,
                        'journal_id': config.ahass_piutang_induk_journal_id.id,
                        'date': date,
                        'period_id':period_id,
                        'transaction_id':banktransfer.id,
                        'model':banktransfer.__class__.__name__,
                    }
                    move_ahass_piutang_induk_id = move_pool.create(cr, uid, move_ahass_piutang_induk_vals, context=None)
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, banktransfer.branch_via_id.id, 'Umum', False, 4, 'General')
                    move_ahass_piutang_induk_line1 = {
                        'name':name,
                        'ref':name,
                        'account_id': bank_mit_account.id,
                        'move_id': move_ahass_piutang_induk_id,
                        'journal_id': config.ahass_piutang_induk_journal_id.id,
                        'period_id': period_id,
                        'date': date,
                        'debit': 0.0,
                        'credit': banktransfer.amount,
                        'branch_id' : banktransfer.branch_via_id.id,
                        'division' : banktransfer.inter_branch_division,
                        'analytic_account_id' : analytic_4,
                        'clear_state': clearing_bank,
                    }
                    
                    line_ahass_piutang_induk_id = move_line_pool.create(cr, uid, move_ahass_piutang_induk_line1, context)   
                    for y in banktransfer.line_ids:
                        branch_destination = self.pool.get('dym.branch').search(cr,SUPERUSER_ID,[('code','=',y.branch_destination_id)])
                        branch_dest = self.pool.get('dym.branch').browse(cr,SUPERUSER_ID,branch_destination)
                        total_debit = y.amount
                        analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_dest.id, 'Umum', False, 4, 'General')
                        move_ahass_piutang_induk_line_2 = {
                            'name': _('Bank Transfer Detail %s')%(branch_dest.name),
                            'ref':name,
                            'account_id': config.ahass_piutang_induk_journal_id.default_debit_account_id.id,
                            'move_id': move_ahass_piutang_induk_id,
                            'journal_id': config.ahass_piutang_induk_journal_id.id,
                            'period_id': period_id,
                            'date': date,
                            'debit': total_debit,
                            'credit': 0.0,
                            'branch_id' : branch_dest.id,
                            'division' : banktransfer.division,
                            'analytic_account_id' : analytic_4
                        }
                        line_ahass_piutang_induk_id2 = move_line_pool.create(cr, uid, move_ahass_piutang_induk_line_2, context)
                        
                    for y in banktransfer.voucher_line_ids:
                        branch_dest = y.branch_id
                        total_debit = y.amount_unreconciled
                        pettycash_journal_ids = self.pool.get('account.journal').search(cr, uid, [('company_id','=',y.company_id.id),('type','=','pettycash')], limit=1)
                        account_id = self.pool.get('account.journal').browse(cr, uid, pettycash_journal_ids, context=context)
                        analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_dest.id, 'Umum', False, 4, 'General')
                        move_ahass_piutang_induk_line_2 = {
                            'name': _('Bank Transfer Detail %s')%(branch_dest.name),
                            'ref':name,
                            'account_id': config.ahass_piutang_induk_journal_id.default_debit_account_id.id,
                            'move_id': move_ahass_piutang_induk_id,
                            'journal_id': config.ahass_piutang_induk_journal_id.id,
                            'period_id': period_id,
                            'date': date,
                            'debit': total_debit,
                            'credit': 0.0,
                            'branch_id' : branch_dest.id,
                            'division' : y.move_line_id.division,
                            'analytic_account_id' : analytic_4,
                        }
                        line_ahass_piutang_induk_id2 = move_line_pool.create(cr, uid, move_ahass_piutang_induk_line_2, context)

                    # Added by Kahfi======================================
                    for y in banktransfer.deposit_ahass_ids:
                        branch_dest = y.branch_parent_id
                        total_debit = y.amount
                        # analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_dest.id, 'Umum', False, 4, 'General')
                        move_ahass_piutang_induk_line_2 = {
                            'name': _('Bank Transfer Detail %s')%(branch_dest.name),
                            'ref':name,
                            'account_id': config.ahass_piutang_induk_journal_id.default_debit_account_id.id,
                            'move_id': move_ahass_piutang_induk_id,
                            'journal_id': config.ahass_piutang_induk_journal_id.id,
                            'period_id': period_id,
                            'date': date,
                            'debit': total_debit,
                            'credit': 0.0,
                            'branch_id' : branch_dest.id, #via
                            'division' : banktransfer.division,
                            'analytic_account_id' : banktransfer.analytic_4.id,
                        }
                        line_ahass_piutang_induk_id2 = move_line_pool.create(cr, uid, move_ahass_piutang_induk_line_2, context)

                    for y in banktransfer.voucher_line_ids:
                        branch_dest = y.invoice_id.branch_id
                        total_debit = y.amount_total
                        account_id = self.pool.get('account.journal').browse(cr, uid, pettycash_journal_ids, context=context)
                        # analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_dest.id, 'Umum', False, 4, 'General')
                        move_ahass_piutang_induk_line_2 = {
                            'name': _('Bank Transfer Detail %s')%(branch_dest.name),
                            'ref':name,
                            'account_id': config.ahass_piutang_induk_journal_id.default_debit_account_id.id,
                            'move_id': move_ahass_piutang_induk_id,
                            'journal_id': config.ahass_piutang_induk_journal_id.id,
                            'period_id': period_id,
                            'date': date,
                            'debit': total_debit,
                            'credit': 0.0,
                            'branch_id' : branch_dest.id,
                            'division' : y.invoice_id.division,
                            'analytic_account_id' : y.invoice_id.analytic_4.id                             
                         }
                        line_ahass_piutang_induk_id2 = move_line_pool.create(cr, uid, move_ahass_piutang_induk_line_2, context)
                    # Added by Kahfi======================================

                    # Create DYM AHASS DEPOSIT
                    Sequence = self.pool.get('ir.sequence')
                    values = {
                        'name': Sequence.get_per_branch(cr, uid, banktransfer.branch_via_id.id, 'ADE', division=banktransfer.division),
                        'date': date,
                        'branch_parent_id': banktransfer.branch_via_id.id,
                        'branch_ahass_id': banktransfer.inter_branch_id.id,
                        'amount': total_debit,
                    }
                    self.pool.get('dym.ahass.deposit').create(cr, uid, values, context=context)

                for y in banktransfer.line_ids:
                    # Tambahan
                    branch_destination = self.pool.get('dym.branch').search(cr,SUPERUSER_ID,[('code','=',y.branch_destination_id)])
                    branch_dest = self.pool.get('dym.branch').browse(cr,SUPERUSER_ID,branch_destination)    
                    name_detail = _('Bank Transfer Detail %s')%(branch_dest.name)
                    if banktransfer.branch_via_id:
                        branch_dest = banktransfer.branch_via_id
                        name_detail = _('Bank Transfer Detail %s via %s')%(branch_dest.name,banktransfer.branch_via_id.name)
                    total_debit = y.amount
                    move_line_2 = {
                        'name': name_detail,
                        'ref':name,
                        'account_id': account__id if mit==True else y.payment_to_id.default_debit_account_id.id,
                        'move_id': move_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'date': date,
                        'debit': total_debit,
                        'credit': 0.0,
                        'branch_id' : branch_dest.id,
                        'division' : banktransfer.division,
                        'analytic_account_id' : y.analytic_4.id  # Tambahan kondisi                         
                    }
                    line_id2 = move_line_pool.create(cr, uid, move_line_2, context)
                    if y.reimbursement_id :
                        y.reimbursement_id.write({'state':'done'})

                for y in banktransfer.voucher_line_ids:
                    branch_dest = y.branch_id
                    total_debit = y.amount_unreconciled
                    pettycash_journal_ids = self.pool.get('account.journal').search(cr, uid, [('company_id','=',y.company_id.id),('type','=','pettycash')], limit=1)
                    account_id = self.pool.get('account.journal').browse(cr, uid, pettycash_journal_ids, context=context)
                    name_detail = _('Bank Transfer Detail %s')%(branch_dest.name)
                    if banktransfer.branch_via_id:
                        branch_dest = banktransfer.branch_via_id
                        name_detail = _('Bank Transfer Detail %s via %s')%(branch_dest.name,banktransfer.branch_via_id.name)                    
                    move_line_2 = {
                        'name': name_detail,
                        'ref':name,
                        'account_id': account_id[0].default_debit_account_id.id,
                        'move_id': move_id,
                        'journal_id': pettycash_journal_ids[0],
                        'period_id': period_id,
                        'date': date,
                        'debit': total_debit,
                        'credit': 0.0,
                        'branch_id' : branch_dest.id,
                        'division' : y.move_line_id.division,
                        'analytic_account_id' : y.move_line_id.analytic_account_id.id
                    }
                    line_id2 = move_line_pool.create(cr, uid, move_line_2, context)
                
                # Added by Kahfi======================================    
                for y in banktransfer.deposit_ahass_ids:
                    branch_dest = y.branch_parent_id                    
                    name_detail = _('Bank Transfer Detail %s')%(branch_dest.name)
                    if banktransfer.branch_via_id:
                        branch_dest = banktransfer.branch_via_id
                        name_detail = _('Bank Transfer Detail %s via %s')%(branch_dest.name,banktransfer.branch_via_id.name)
                    total_debit = y.amount
                    move_line_2 = {
                        'name': name_detail,
                        'ref':name,
                        'account_id': config.ahass_account_kas_induk.id,
                        'move_id': move_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'date': date,
                        'debit': total_debit,
                        'credit': 0.0,
                        'branch_id' : branch_dest.id,
                        'division' : banktransfer.division,
                        'analytic_account_id' : banktransfer.analytic_4.id                             
                    }
                    line_id2 = move_line_pool.create(cr, uid, move_line_2, context)
                
                for y in banktransfer.invoice_line_ids:
                    branch_dest = y.invoice_id.branch_id
                    total_debit = y.amount_total
                    name_detail = _('Bank Transfer Detail %s')%(branch_dest.name)
                    if banktransfer.branch_via_id:
                        branch_dest = banktransfer.branch_via_id
                        name_detail = _('Bank Transfer Detail %s via %s')%(branch_dest.name,banktransfer.branch_via_id.name)                    
                    move_line_2 = {
                        'name': name_detail,
                        'ref':name,
                        'account_id': account__id,
                        'move_id': move_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'date': date,
                        'debit': total_debit,
                        'credit': 0.0,
                        'branch_id' : branch_dest.id,
                        'division' : y.invoice_id.division,
                        'analytic_account_id' : y.invoice_id.analytic_4.id
                    }
                    line_id2 = move_line_pool.create(cr, uid, move_line_2, context)
                # Added by Kahfi======================================

            #Replace Analytic Branch Untuk HO2Branch
            if banktransfer.transaction_type=='ho2branch':
                move=move_pool.browse(cr,uid,move_id)
                for line in move.line_id:
                    analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr,uid,line.branch_id.id, 'Umum', False, 4, 'General')
                    line.update({'analytic_account_id':analytic_4_general})

            if banktransfer.payment_from_id.entry_posted:
                move=self.pool.get('account.move').browse(cr,uid,move_id)          
                posted = move_pool.post(cr, uid, [move_id], context=None)        
                
            if mit == True:
                self.write(cr, uid, banktransfer.id, {
                    'move_mit_id': move_id,
                })
            else:
                if move_ahass_id:
                   move_ahass_posted = move_pool.post(cr, uid, [move_ahass_id], context=None)
            
                if move_ahass_piutang_induk_id:
                   move_ahass_piutang_induk_posted = move_pool.post(cr, uid, [move_ahass_piutang_induk_id], context=None)
            
                self.write(cr, uid, banktransfer.id, {
                    'state': 'approved', 
                    'move_id': move_id,
                    'move_ahass_id': move_ahass_id,
                    'move_piutang_induk_id': move_ahass_piutang_induk_id,
                })
  
        return True

   