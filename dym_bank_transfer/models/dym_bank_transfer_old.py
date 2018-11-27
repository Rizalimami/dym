import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp import SUPERUSER_ID
from openerp import tools
import pytz
from ..report import fungsi_terbilang

TRANSACTION_TYPES = [
    ('deposit','Deposit'),
    ('withdraw','Withdraw'),
    ('ats','ATS'),
    ('ho2branch','HO to Branch'),
    ('inhouse','In House')
]

class dym_bank_transfer(models.Model):
    _name = 'dym.bank.transfer'
    _description = 'Bank Transfer'
    _order = 'date desc, name desc'
       
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('waiting_for_confirm_received','Waiting For Confirm Received'),
        ('confirmed', 'Waiting Approval'),
        ('app_approve', 'Approved'),
        ('app_received', 'Received'),
        ('approved','Done'),
        ('cancel','Cancelled')
    ]

    @api.one
    @api.depends('line_ids.amount','bank_fee')
    def _compute_amount(self):
        self.amount_total = sum(line.amount for line in self.line_ids) + self.bank_fee
        self.amount_show = self.amount_total
        # Allow Backdate
        # if self.amount_total > self.current_balance:
        #     raise UserError(_('Total transaksi tidak boleh lebih dari saldo tersedia.'))

    @api.cr_uid_ids_context
    @api.depends('period_id')
    def _get_period(self, cr, uid, ids,context=None):
        if context is None: context = {}
        if context.get('period_id', False):
            return context.get('period_id')
        periods = self.pool.get('account.period').find(cr, uid, context=context)
        return periods and periods[0] or False

    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    
    def ubah_tanggal(self,tanggal):
        try:
            conv = datetime.strptime(tanggal, '%d-%m-%Y %H:%M')
            return conv.strftime('%d-%m-%Y')
        except Exception as e:
            conv = datetime.strptime(tanggal, '%Y-%m-%d %H:%M:%S')
            return conv.strftime('%d-%m-%Y')

    @api.cr_uid_ids_context
    def change_amount(self,cr,uid,ids,bank,branch_id,context=None):
        value = {}
        if bank and branch_id:
            journal = self.pool.get('account.journal')
            journal_srch = journal.search(cr,uid,[('id','=',bank)])
            journal_brw = journal.browse(cr,uid,journal_srch)
            if journal_brw.type in ['cash','bank']: 
                analytic_branch_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',3),('branch_id','=',branch_id),('type','=','normal'),('state','not in',('close','cancelled'))])
                analytic_cc_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',4),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',analytic_branch_ids)])
                sql_query = ' AND l.analytic_account_id in %s' % str(tuple(analytic_cc_ids))
            else :
                value = {'amount_show':False}    
        else :
            value = {'payment_from_id':False}
        return {'value':value}
    
    @api.cr_uid_ids_context
    def change_amount_show(self,cr,uid,ids,amount,context=None):
        value = {}
        if amount :
            value = {'amount':amount}
        else :
            value = {'amount':False}
        return {'value':value}    
    
    @api.model
    def _get_default_branch(self):
        res = self.env.user.get_default_branch()
        return res

    @api.model
    def _getCompanyBranch(self):
        transaction_type = self._context.get('default_transaction_type',False)
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        user = self.env.user
        if user.branch_type == 'HO':
            branch_ids = [b.id for b in user.branch_ids if b.branch_type=='HO' and b.company_id.id==company_id]
        else:
            branch_ids = [user.get_default_branch()]
        return [('id','in',branch_ids)]
            
    @api.onchange('date')
    def get_default_date(self):
        if not self.allow_backdate:
            user = self.env['res.users'].search([('id','=',self._uid)])
            tz = pytz.timezone(user.tz) if user.tz else pytz.timezone('Asia/Jakarta')
            date_time = pytz.UTC.localize(datetime.now())
            date_time_utc = date_time.astimezone(tz)
            self.date = date_time_utc.date()

    @api.onchange('division')
    def onchange_division(self):
        self.division = 'Finance'

    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_bank_transfer-2] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    @api.model
    def _get_default_backdate(self):
        flag = False
        if self.env['res.users'].has_group('dym_account_voucher.group_dym_account_voucher_allow_backdate'):
            flag = True
        return flag

    @api.multi
    @api.depends('payment_from_id')
    def _get_current_balance(self):
        for rec in self:
            rec.current_balance = rec.payment_from_id.default_debit_account_id.balance
        return True
        
    allow_backdate = fields.Boolean(string='Backdate', default=_get_default_backdate)
    name = fields.Char(string="Name", readonly=True, default='/')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")

    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, default=_get_default_branch, domain=_getCompanyBranch)
    amount = fields.Float('Amount')
    state = fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date = fields.Date(string="Date", required=True)
    receive_date = fields.Date(string="Receive Date", required=False)
    payment_from_id = fields.Many2one('account.journal',string="Source of Fund",domain="[('branch_id','in',[branch_id,False]),('type','in',['cash','bank'])]")

    payment_from_id_deposit = fields.Many2one('account.journal', string="Source of Fund",domain="[('branch_id','in',[branch_id,False]),('type','in',['cash'])]")
    payment_from_id_withdraw = fields.Many2one('account.journal', string="Source of Fund",domain="[('branch_id','in',[branch_id,False]),('type','in',['bank'])]")
    payment_from_id_ats = fields.Many2one('account.journal', string="Source of Fund",domain="[('branch_id','in',[branch_id,False]),('type','in',['bank'])]")
    payment_from_id_ho2branch = fields.Many2one('account.journal', string="Source of Fund",domain="[('branch_id','in',[branch_id,False]),('type','in',['bank'])]")
    payment_from_id_inhouse = fields.Many2one('account.journal', string="Source of Fund",domain="[('branch_id','in',[branch_id,False]),('type','in',['bank'])]")

    description = fields.Char(string="Description")
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line',related='move_id.line_id',string='Journal Items', readonly=True)    
    line_ids = fields.One2many('dym.bank.transfer.line','bank_transfer_id',string="Bank Transfer Line")
    line_ids2 = fields.One2many('dym.bank.transfer.line','bank_transfer_id', related='line_ids', string="Bank Transfer Line")
    bank_fee = fields.Float(string='Bank Transfer Fee',digits=dp.get_precision('Account'))
    amount_total = fields.Float(string='Total Amount',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    period_id = fields.Many2one('account.period',string="Period",required=True, readonly=True,default=_get_period)
    note = fields.Text(string="Note")
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], string='Division',default='Unit', required=True,change_default=True, select=True)
    journal_type = fields.Selection(related='payment_from_id.type',string="Journal Type")
    amount_show = fields.Float(related='amount',string='Amount')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    analytic_1 = fields.Many2one('account.analytic.account', 'Account Analytic Company', default=_get_analytic_company)
    analytic_2 = fields.Many2one('account.analytic.account', 'Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center')
    move_mit_id = fields.Many2one('account.move', string='Account Entry MIT', copy=False)
    move_mit_ids = fields.One2many('account.move.line',related='move_mit_id.line_id',string='Journal Items MIT', readonly=True)
    value_date = fields.Date('Value Date')
    transfer_type = fields.Selection([('normal','Normal'),('branch_replenishment','Penggantian Uang Cabang')], default="branch_replenishment")
    branch_type = fields.Selection(related='branch_id.branch_type')
    voucher_ids = fields.One2many('dym.bank.transfer.voucher', 'bank_transfer_id', string='Vouchers')
    ref = fields.Char('Reff')    
    current_balance = fields.Float(compute=_get_current_balance, string='Current Balance')
    transaction_type = fields.Selection(TRANSACTION_TYPES, string='Trasnsaction Type')
    payment_method = fields.Selection([
        ('giro','Giro'),
        ('ats','ATS'),
        ('cheque','Cheque'),
        ('internet_banking','Internet Banking'),
        ('auto_debit','Auto Debit')
        ], string='Payment Method')
    cheque_giro_number = fields.Many2one('dym.checkgyro.line', string='Chk/Giro No', domain="[('journal_id','=',payment_from_id)]")
    cheque_giro_date = fields.Date(string='Chk/Giro Date',required=True,default=fields.Date.context_today)
    clearing_bank = fields.Boolean(string='Clearing Bank', default=True)
    clearing_bank_readonly = fields.Boolean(string='Clearing Bank', related="clearing_bank")

    @api.cr_uid_ids_context
    def button_dummy(self, cr, uid, ids, context=None):
        return True

    @api.onchange('payment_method')
    def onchange_payment_method(self):
        self.clearing_bank = False
        if self.payment_method in ['giro','ho2branch','cheque','internet_banking']:
            self.clearing_bank = True
        if self.transaction_type in ['deposit','withdraw','inhouse','ats','ho2branch']:
            self.clearing_bank = True

    @api.onchange('payment_from_id_deposit','payment_from_id_withdraw','payment_from_id_ats','payment_from_id_ho2branch','payment_from_id_inhouse')
    def onchange_payment_from_dwhai_id(self):

        dom = {}
        val = {}
        war = {}

        user = self.env.user
        self.payment_from_id = False
        if self.payment_from_id_deposit:
            self.payment_from_id = self.payment_from_id_deposit.id
        if self.payment_from_id_withdraw:
            self.payment_from_id = self.payment_from_id_withdraw.id
        if self.payment_from_id_ats:
            self.payment_from_id = self.payment_from_id_ats.id
        if self.payment_from_id_ho2branch:
            self.payment_from_id = self.payment_from_id_ho2branch.id
        if self.payment_from_id_inhouse:
            self.payment_from_id = self.payment_from_id_inhouse.id

        transaction_type = self.env.context.get('transaction_type',False)
        # Deposit
        if transaction_type == 'deposit':
            return {
                'domain': {
                    'payment_from_id_deposit': [('type','=',self.env.context.get('journal_type',False))]
                },
            }

        # Withdrawal
        if transaction_type == 'withdraw':
            if self.payment_from_id_withdraw:
                acc_number = self.env['res.partner.bank'].search([('journal_id','=',self.payment_from_id_withdraw.id)])
                if not acc_number:
                    return {
                        'warning': {
                            'title': _('Warning!'), 
                            'message': _('Jurnal %s tidak memiliki rekening bank. Jika ini adalah jurnal bank, silahkan buat rekening di menu Sale > Configuration > Localization > Bank Account.' % self.payment_from_id_withdraw.name)
                        }
                    }
                self.clearing_bank = True
            return {
                'domain': {
                    # 'payment_from_id_withdraw': [('type','=',self.env.context.get('journal_type',False))],
                    'payment_from_id_withdraw': [('type','=','bank'),('transaction_type','=','out'),('branch_id','=',self.branch_id.id)],
                },
                'value': {
                    'payment_method': 'cheque',
                }
            }

        # ATS
        if transaction_type == 'ats':
            if self.payment_from_id_ats:
                acc_number = self.env['res.partner.bank'].search([('journal_id','=',self.payment_from_id_ats.id)])
                if not acc_number:
                    self.payment_from_id_ats = False
                    return {
                        'warning': {
                            'title': _('Warning!'), 
                            'message': _('Jurnal %s tidak memiliki rekening bank. Jika ini adalah jurnal bank, silahkan buat rekening di menu Sale > Configuration > Localization > Bank Account.' % self.payment_from_id_withdraw.name)
                        }
                    }
            return {
                'domain': {
                    'payment_from_id_ats': [('type','=',self.env.context.get('journal_type',False))]
                },
            }

        # HO2Branch
        if transaction_type == 'ho2branch':
            if user.branch_type != 'HO':
                self.branch_id = False
                raise osv.except_osv(('Perhatian !'), ("Maaf, user %s tidak memiliki akses untuk membuat transaksi Head Office." % user.login))
            if self.payment_from_id_ho2branch:
                acc_number = self.env['res.partner.bank'].search([('journal_id','=',self.payment_from_id_ho2branch.id)])
                if not acc_number:
                    self.payment_from_id_ho2branch = False
                    return {
                        'warning': {
                            'title': _('Warning!'), 
                            'message': _('Jurnal %s tidak memiliki rekening bank. Jika ini adalah jurnal bank, silahkan buat rekening di menu Sale > Configuration > Localization > Bank Account.' % self.payment_from_id_withdraw.name)
                        }
                    }
                self.clearing_bank = True
            return {
                'domain': {
                    'payment_from_id_ho2branch': [('type','=',self.env.context.get('journal_type',False))]
                },
            }

        # InHouse
        if transaction_type == 'inhouse':
            if user.branch_type != 'HO':
                self.branch_id = False
                raise osv.except_osv(('Perhatian !'), ("Maaf, user %s tidak diperbolehkan untuk membuat transaksi pemindahan uang antar rekening bank." % user.login))
            if self.payment_from_id_inhouse:
                acc_number = self.env['res.partner.bank'].search([('journal_id','=',self.payment_from_id_inhouse.id)])
                if not acc_number:
                    self.payment_from_id_inhouse = False
                    return {
                        'warning': {
                            'title': _('Warning!'), 
                            'message': _('Jurnal %s tidak memiliki rekening bank. Jika ini adalah jurnal bank, silahkan buat rekening di menu Sale > Configuration > Localization > Bank Account.' % self.payment_from_id_withdraw.name)
                        }
                    }
                self.clearing_bank = True
            return {
                'domain': {
                    'payment_from_id_inhouse': [('type','=',self.env.context.get('journal_type',False))]
                },
            }

    @api.multi
    def update_cheque_giro_book(self,vals):
        for rec in self:
            if not rec.cheque_giro_number:
                return
            transfer_id = rec.id
            if transfer_id:
                for x in self.env['dym.checkgyro.line'].search([('transfer_id','=',transfer_id)]):
                    x.state = 'available'
                    x.transfer_id = False

            cheque_giro_id = vals.get('cheque_giro_number',False)
            checkgyro_id = self.env['dym.checkgyro.line'].browse([cheque_giro_id])

            if not transfer_id:
                return False

            amount = 0.0
            if 'amount' in vals and vals.get('amount',False):
                amount = vals.get('amount',False)
            if rec.cheque_giro_number:
                rec.cheque_giro_number.amount = amount
            rec.cheque_giro_number.state = 'used'
            rec.cheque_giro_number.transfer_id = transfer_id
            rec.cheque_giro_number.used_date = rec.date

    @api.one
    def write(self, vals):
        super(dym_bank_transfer, self).write(vals)
        self.update_cheque_giro_book(vals)
        
    @api.model
    def create(self,vals,context=None):        
        # vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'BTR', division='Umum') 
        # vals['date'] = datetime.today() 
        bank_transfer = []
        for x in vals['line_ids']:
            bank_transfer.append(x[2]) 
        total_amount = 0.0
        if 'bank_fee' in vals:
            total_amount = vals['bank_fee']
        for y in bank_transfer :
            total_amount += y['amount']
        vals['amount_show'] = total_amount
        vals['amount'] = total_amount
        res_id = super(dym_bank_transfer, self).create(vals)
        self.update_cheque_giro_book(vals)
        return res_id
    
    @api.one
    def post_bank(self):
        user = self.env['res.users'].search([('id','=',self._uid)])
        tz = pytz.timezone(user.tz) if user.tz else 'Asia/Jakarta'

        date_time = pytz.UTC.localize(datetime.now())
        date_time_utc = date_time.astimezone(tz)  # Convert to UTC

        if self.allow_backdate == True:
            self.write({'state':'approved','confirm_uid':self._uid,'confirm_date':datetime.now()})    
        else:
            periods = self.env['account.period'].find(dt=date_time_utc.date())
            self.write({'state':'approved','confirm_uid':self._uid,'confirm_date':datetime.now(),'date':date_time_utc.date(),'period_id':periods and periods[0].id})    
        debit_account = self.payment_from_id.default_debit_account_id
        if self.move_mit_id:
            for mit_line in self.move_mit_ids:
                if mit_line.account_id.id != self.payment_from_id.default_debit_account_id.id:
                    debit_account = mit_line.account_id
        if self.payment_from_id.type == 'cash' :
            analytic_branch_ids = self.env['account.analytic.account'].search([('segmen','=',3),('branch_id','=',self.branch_id.id),('type','=','normal'),('state','not in',('close','cancelled'))])
            analytic_cc_ids = self.env['account.analytic.account'].search([('segmen','=',4),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',analytic_branch_ids.ids)])
            sql_query = ' AND l.analytic_account_id in %s' % str(tuple(analytic_cc_ids.ids))
            if not self.move_mit_id:
                if self.amount > debit_account.with_context(sql_query=sql_query).balance or self.amount_show > debit_account.with_context(sql_query=sql_query).balance :
                    raise osv.except_osv(('Perhatian !'), ("xSaldo kas di account %s tidak mencukupi !") % (debit_account.name))

        self.action_move_line_create()
        return True  

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel', 'move_id': False})
        if moves:
            moves.button_cancel()
            moves.unlink()
        self._log_event(-1.0, 'Cancel Invoice')
        return True

    @api.one
    def cancel_bank(self):
        if self.move_mit_id:
            self.move_mit_id.action_reverse_journal()
        if self.move_id:
            self.move_id.action_reverse_journal()
        self.write({'state':'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
        return True    

    @api.cr_uid_ids_context
    def action_move_line_create(self, cr, uid, ids, mit=False, context=None):
        this = self.browse(cr, uid, ids, context=context)
        if context is None:
            context = {}
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

            # clearing_bank = banktransfer.payment_from_id.type == 'bank' and 'open' or 'not_clearing'
            clearing_bank = 'not_clearing'
            if banktransfer.clearing_bank:
                clearing_bank = 'open'
            move_line1 = {
                'name':name,
                'ref':name,
                'account_id': credit_account_id.id if not banktransfer.move_mit_id.id else bank_mit_account.id,
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
                    'analytic_account_id' : banktransfer.analytic_4.id     
                }     
                line_mit_id = move_line_pool.create(cr, uid, move_line_mit, context)
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
                for y in banktransfer.line_ids :
                    branch_destination = self.pool.get('dym.branch').search(cr,SUPERUSER_ID,[('code','=',y.branch_destination_id)])
                    branch_dest = self.pool.get('dym.branch').browse(cr,SUPERUSER_ID,branch_destination)
                
                    move_line_2 = {
                        'name': _('Bank Transfer Detail %s')%(branch_dest.name),
                        'ref':name,
                        'account_id': y.payment_to_id.default_debit_account_id.id,
                        'move_id': move_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'date': date,
                        'debit': y.amount,
                        'credit': 0.0,
                        'branch_id' : branch_dest.id,
                        'division' : banktransfer.division,
                        'analytic_account_id' : y.analytic_4.id                             
                    }           
                    line_id2 = move_line_pool.create(cr, uid, move_line_2, context)
                    if y.reimbursement_id :
                        y.reimbursement_id.write({'state':'paid'})
            if banktransfer.payment_from_id.entry_posted:
                posted = move_pool.post(cr, uid, [move_id], context=None)
            if mit == False:
                self.write(cr, uid, banktransfer.id, {'state': 'approved', 'move_id': move_id})
            else:
                self.write(cr, uid, banktransfer.id, {'move_mit_id': move_id})
        return True
     
    @api.cr_uid_ids_context   
    def create_intercompany_lines(self,cr,uid,ids,move_id,context=None):       
        branch_rekap = {}       
        branch_pool = self.pool.get('dym.branch')        
        vals = self.browse(cr,uid,ids) 
        move_line = self.pool.get('account.move.line')
        move_line_srch = move_line.search(cr,SUPERUSER_ID,[('move_id','=',move_id)])
        move_line_brw = move_line.browse(cr,SUPERUSER_ID,move_line_srch)
        
        branch = branch_pool.search(cr,uid,[('id','=',vals.branch_id.id)])

        if branch :
            branch_browse = branch_pool.browse(cr,uid,branch)
            inter_branch_header_account_id = branch_browse.inter_company_account_id.id
            if not inter_branch_header_account_id :
                raise osv.except_osv(('Perhatian !'), ("Account Inter Company belum diisi dalam Master branch %s !")%(vals.branch_id.name))
        
        for x in move_line_brw :
            if x.branch_id not in branch_rekap :
                branch_rekap[x.branch_id] = {}
                branch_rekap[x.branch_id]['debit'] = x.debit
                branch_rekap[x.branch_id]['credit'] = x.credit
            else :
                branch_rekap[x.branch_id]['debit'] += x.debit
                branch_rekap[x.branch_id]['credit'] += x.credit  
        
        for key,value in branch_rekap.items() :
            if key != vals.branch_id :        
                inter_branch_detail_account_id = key.inter_company_account_id.id                
                if not inter_branch_detail_account_id :
                    raise osv.except_osv(('Perhatian !'), ("Account Inter belum diisi dalam Master branch %s - %s!")%(key.code, key.name))

                balance = value['debit']-value['credit']
                debit = abs(balance) if balance < 0 else 0
                credit = balance if balance > 0 else 0
                
                if balance != 0:
                    move_line_create = {
                        'name': _('Interco Bank Transfer %s')%(key.name),
                        'ref':_('Interco Bank Transfer %s')%(key.name),
                        'account_id': inter_branch_header_account_id,
                        'move_id': move_id,
                        'journal_id': vals.payment_from_id.id,
                        'period_id': vals.period_id.id,
                        'date': vals.date,
                        'debit': debit,
                        'credit': credit,
                        'branch_id' : key.id,
                        'division' : vals.division                    
                    }    
                    inter_first_move = move_line.create(cr, uid, move_line_create, context)    
                             
                    move_line2_create = {
                        'name': _('Interco Bank Transfer %s')%(vals.branch_id.name),
                        'ref':_('Interco Bank Transfer %s')%(vals.branch_id.name),
                        'account_id': inter_branch_detail_account_id,
                        'move_id': move_id,
                        'journal_id': vals.payment_from_id.id,
                        'period_id': vals.period_id.id,
                        'date': vals.date,
                        'debit': credit,
                        'credit': debit,
                        'branch_id' : vals.branch_id.id,
                        'division' : vals.division                    
                    }    
                    inter_second_move = move_line.create(cr, uid, move_line2_create, context)       
        return True

    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Bank Transfer sudah diproses, data tidak bisa didelete !"))
        return super(dym_bank_transfer, self).unlink(cr, uid, ids, context=context)     

    def branch_id_change(self, cr, uid, ids, branch_id, context=None):
        value = {}
        if branch_id :
            value['payment_from_id'] = False
            branch = self.pool.get('dym.branch').browse(cr, uid, branch_id)
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, 'Umum', False, 4, 'General')
            value['analytic_1'] = analytic_1_general
            value['analytic_2'] = analytic_2_general
            value['analytic_3'] = analytic_3_general
            value['analytic_4'] = analytic_4_general

            branch_config_obj = self.pool.get('dym.branch.config')
            config_id = branch_config_obj.search(cr, uid,[('branch_id','=',branch_id)])
        return {'value':value}


    @api.onchange('payment_from_id')
    def onchange_payment_from_id(self):
        return {
            'domain': {
                'cheque_giro_number': [('journal_id','=',self.payment_from_id.id)]
            }
        }

class dym_bank_transfer_voucher(models.Model): 
    _name = 'dym.bank.transfer.voucher'
    _description = 'Bank Transfer Line Voucher'

    bank_transfer_id = fields.Many2one('dym.bank.transfer',string="Bank Transfer")
    voucher_id = fields.Many2one('account.voucher', string="Voucher")
    reimburse_id = fields.Many2one('account.voucher', string="Voucher")
    date = fields.Date(related="voucher_id.date")
    date_due = fields.Date(related="voucher_id.date_due")
    amount = fields.Float(related="voucher_id.amount")
    net_amount = fields.Float(related="voucher_id.net_amount")
    notes = fields.Text('Notes')
    account_id = fields.Many2one('account.account', string="Account")
    line_amount = fields.Float(string="Amount")

    @api.onchange('voucher_id')
    def onchange_voucher_id(self):
        context = self._context
        notes = []
        for vline in self.voucher_id.line_dr_ids:
            notes.append(vline.name)
        self.notes = ', '.join(notes)

class dym_bank_transfer_line(models.Model): 
    _name = 'dym.bank.transfer.line'
    _description = 'Bank Transfer Line'

    # @api.model
    # def _get_branch(self):
    #     user = self.env['res.users'].browse(self._uid)
    #     company_id = user.company_id.id
    #     branch_user = user.branch_ids
    #     branch_ids = [x.id for x in branch_user]
    #     branch_total = self.env['dym.branch'].sudo().search([
    #         ('company_id','=',company_id),
    #         ],order='name')
    #     res = [(branch.code,branch.name) for branch in branch_total ]
    #     return res

    @api.model
    def _get_destination_branch(self):
        user = self.env['res.users'].browse(self._uid)
        company_id = user.company_id.id
        branch_user = user.branch_ids
        branch_ids = [x.id for x in branch_user]
        domain = [('company_id','=',company_id),]
        transaction_type = self._context.get('transaction_type',False)
        br_id = self._context.get('branch_id',False)
        if br_id and transaction_type and transaction_type in ('deposit'):
            domain += [('id','=',br_id)]
        branch_total = self.env['dym.branch'].sudo().search(domain,order='name')
        res = [(branch.code,branch.name) for branch in branch_total ]
        return res

    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_bank_transfer-3] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    name = fields.Char(string="Name",readonly=True)
    branch_destination_id = fields.Char(string='Branch Destination', required=True)   
    branch_destination_select = fields.Many2one('dym.branch', string='Branch Destination')   
    payment_to_id = fields.Many2one('account.journal',string="Bank", domain="[('type','in',('cash','bank','pettycash'))]")
    description = fields.Char(string="Description")
    amount = fields.Float('Amount')
    bank_transfer_id = fields.Many2one('dym.bank.transfer',string="Bank Transfer")
    transaction_type = fields.Selection(TRANSACTION_TYPES, string='Trasnsaction Type')
    reimbursement_id = fields.Many2one('dym.reimbursed',domain="[('state','=','approved')]", string="Reimbursed No")
    analytic_1 = fields.Many2one('account.analytic.account', 'Account Analytic Company')
    analytic_2 = fields.Many2one('account.analytic.account', 'Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center')
    
    _defaults = {
        'analytic_1':_get_analytic_company,
    }

    @api.model
    def default_get(self, fields):
        res = super(dym_bank_transfer_line, self).default_get(fields)
        transaction_type = self._context.get('transaction_type',False)
        if transaction_type:
            res['transaction_type'] = transaction_type
        return res

    @api.onchange('branch_destination_select')
    def onchange_branch_destination_select(self):
        res = {}
        dom = {}

        if not self.bank_transfer_id.description:
            raise osv.except_osv(('Perhatian !'), ("Sebelum menambah detil transaksi, Description wajib diisi terlebih dahulu."))
        if not self.bank_transfer_id.branch_id:
            raise osv.except_osv(('Perhatian !'), ("Sebelum menambah detil transaksi, Branch wajib diisi terlebih dahulu.")) 
        if not self.bank_transfer_id.payment_from_id :
            raise osv.except_osv(('Perhatian !'), ("Sebelum menambah detil transaksi, Source of Fund waib disii terlebih dahulu.")) 

        transaction_type = self._context.get('transaction_type',False)
        branch_id = self._context.get('branch_id',False)
        if not branch_id:
            raise osv.except_osv(('Perhatian !'), ("Silahkan pilih cabang terlebih dahulu.")) 

        if transaction_type == 'deposit':
            dom['branch_destination_select'] = [('id','=',branch_id)]
            self.branch_destination_select = branch_id
        if transaction_type == 'withdraw':
            dom['branch_destination_select'] = [('id','=',branch_id)]
            self.branch_destination_select = branch_id
        if transaction_type == 'ats':
            dom['branch_destination_select'] = [('id','=',branch_id)]
            self.branch_destination_select = branch_id

        if self.branch_destination_select:
            self.branch_destination_id = self.branch_destination_select.code
        self.description = self.bank_transfer_id.description
        if not self.reimbursement_id :
            self.payment_to_id = False

        rekap_journal_id = []
        journal_id = self.env['account.journal'].sudo().search(['|',('branch_id.code','=',self.branch_destination_id),('branch_id','=',False),('type','in',['cash','bank','pettycash'])])
        if journal_id :
            for x in journal_id :
                rekap_journal_id.append(x.id)            
            dom['payment_to_id'] = [('id','in',rekap_journal_id)]
        else :
            dom['payment_to_id'] = ['|',('branch_id.code','=',self.branch_destination_id),('branch_id','=',False),('type','in',('cash','bank','pettycash'))]  

        if self.branch_destination_id:
            branch = self.env['dym.branch'].sudo().search([('code','=',self.branch_destination_id)], limit=1)
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(self._cr, self._uid, branch, 'Finance', False, 4, 'General')
            self.analytic_1 = analytic_1_general
            self.analytic_2 = analytic_2_general
            self.analytic_3 = analytic_3_general
            self.analytic_4 = analytic_4_general

        res = {
            'domain': dom,
        }
        return res

    @api.onchange('amount')
    def change_amount(self):
        if self.amount and self.reimbursement_id :
            self.amount = self.reimbursement_id.amount_total

