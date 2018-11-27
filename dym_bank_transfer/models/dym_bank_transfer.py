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
from openerp.addons.dym_base import DIVISION_SELECTION
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF
from random import randint
from openerp import workflow, api

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
        ('confirmed', 'Waiting Approval'),
        ('waiting_for_approval','Payment in Process'),
        ('waiting_for_confirm_received','Waiting For Confirm Received'),
        ('app_approve', 'Process Done'),
        ('app_received', 'Received'),
        ('approved','Done'),
        ('cancel','Cancelled')
    ]

    @api.one
    @api.depends('line_ids.amount','line_ids1.amount','line_ids2.amount','bank_fee','voucher_line_ids.amount_unreconciled')
    def _compute_amount(self):
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
        self.amount_total = total_line
        self.amount = total_line
        self.amount_show = total_line

        if self.transaction_type in ['withdraw','ats','ho2branch','deposit'] and self.state=='draft' and self.amount_total > self.current_balance and not self.bank_trf_advice_id:
            raise UserError(_('Total transaksi tidak boleh lebih dari Total transaksi tidak boleh lebih dari saldo tersediasaldo tersedia.'))

    @api.cr_uid_ids_context
    @api.depends('period_id')
    def _get_period(self, cr, uid, ids,context=None):
        if context is None: context = {}
        if context.get('period_id', False):
            return context.get('period_id')
        periods = self.pool.get('account.period').find(cr, uid, context=context)
        return periods and periods[0] or False

    def desc_cetakan_btr_sin(self,cr,uid,invoice_name,context=None):
        sin_ids = self.pool.get('account.invoice').search(cr,uid,[('number','=',invoice_name)])
        sin_browse = self.pool.get('account.invoice').browse(cr,uid,sin_ids)
        if not sin_browse.invoice_line:
            return 'N/A'
        print "sin_browse.invoice_line[0].name", sin_browse.invoice_line[0].name
        print "sin_browse.partner_id.name", sin_browse.partner_id.name
        desc_btr_sin = sin_browse.invoice_line[0].name, " - ", sin_browse.partner_id.name
        desc_btr_sin_f = " ".join(desc_btr_sin)
        return desc_btr_sin_f

    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    
    def ubah_tanggal(self,tanggal):
        try:
            conv = datetime.strptime(tanggal, '%d-%m-%Y %H:%M')
            return conv.strftime('%d-%m-%Y')
        except Exception as e:
            return 'N/A'
            # conv = datetime.strptime(tanggal, '%Y-%m-%d %H:%M:%S')
            # return conv.strftime('%d-%m-%Y')
    
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

        if transaction_type == 'ho2branch':
            branch_ids = [b.id for b in user.branch_ids if b.branch_type=='HO' and b.company_id.id==company_id]
        else:
            my_branch = self.env.user.branch_id
            if self.env.user.branch_type!='HO':
                if not my_branch:
                    raise osv.except_osv(('Perhatian !'), ("User %s tidak memiliki default branch. Hubungi system administrator agar menambahkan default branch di User Setting." % self.env.user.name))
                else:
                    branch_ids = [my_branch.id]
            else:
                branch_ids = [b.id for b in self.env.user.branch_ids if b.company_id.id==company_id]
        return [('id','in',branch_ids)]

    @api.multi
    @api.depends('payment_from_id')
    def _get_current_balance_branch(self):
        if self.payment_from_id_deposit:
            self.xcurrent_balance = self.get_current_balance_branch(self.payment_from_id_deposit.id, self.branch_id.id)
        elif self.payment_from_id_withdraw:
            self.xcurrent_balance = self.get_current_balance_branch(self.payment_from_id_withdraw.id, self.branch_id.id)
        elif self.payment_from_id_ats:
            self.xcurrent_balance = self.get_current_balance_branch(self.payment_from_id_ats.id, self.branch_id.id)
        elif self.payment_from_id_ho2branch:
            self.xcurrent_balance = self.get_current_balance_branch(self.payment_from_id_ho2branch.id, self.branch_id.id)
        elif self.payment_from_id_inhouse:
            self.xcurrent_balance = self.get_current_balance_branch(self.payment_from_id_inhouse.id, self.branch_id.id)
        else:
            self.xcurrent_balance = self.get_current_balance_branch(self.payment_from_id.id, self.branch_id.id)
    #    print '*****************',self.xcurrent_balance
    #@api.onchange('branch_id','payment_from_id_deposit','payment_from_id_withdraw','payment_from_id_ats','payment_from_id_ho2branch','payment_from_id_inhouse')
    #def onchange_current_balance_branch(self):
    #if self.payment_from_id_deposit:
    #        self.xcurrent_balance = self.get_current_balance_branch(self.payment_from_id_deposit.id, self.branch_id.id)
    #    elif self.payment_from_id_withdraw:
    #        self.xcurrent_balance = self.get_current_balance_branch(self.payment_from_id_withdraw.id, self.branch_id.id)
    #    elif self.payment_from_id_ats:
    #        self.xcurrent_balance = self.get_current_balance_branch(self.payment_from_id_ats.id, self.branch_id.id)
    #    elif self.payment_from_id_ho2branch:
    #        self.xcurrent_balance = self.get_current_balance_branch(self.payment_from_id_ho2branch.id, self.branch_id.id)
    #    elif self.payment_from_id_inhouse:
    #        self.xcurrent_balance = self.get_current_balance_branch(self.payment_from_id_inhouse.id, self.branch_id.id)
    #    else:
    #        self.xcurrent_balance = self.get_current_balance_branch(self.payment_from_id.id, self.branch_id.id)


    @api.cr_uid_ids_context
    def get_current_balance_branch(self, cr, uid, ids, bank, branch_id, context=None):
        branch = self.pool.get('dym.branch').browse(cr,uid,branch_id)
        bal_db_init= 0
        if bank == 'False':
            bank == self.payment_from_id.id

        if bank and branch_id:
            journal = self.pool.get('account.journal')
            account_ids = []
            journal_srch = journal.search(cr, uid, [('id', '=', bank)])
            journal_brw = journal.browse(cr, uid, journal_srch)
            if journal_brw.type in ['cash', 'bank']:
                analytic_branch_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen', '=', 3), ('branch_id', '=',branch_id), ('type', '=', 'normal'), ('state', 'not in', ('close', 'cancelled'))])
                analytic_cc_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen', '=', 4),('type', '=', 'normal'), ('state', 'not in',('close', 'cancelled')), ('parent_id', 'child_of',analytic_branch_ids)])

                sql_query = '  and l.period_id in (select id from  account_period where special= FALSE) AND l.analytic_account_id in %s' % str(
                    tuple(analytic_cc_ids)).replace(',)', ')')

                for journals in journal_brw:
                    if journals.default_debit_account_id and journals.default_debit_account_id.id not in account_ids:
                        account_ids.append(journals.default_debit_account_id.id)
                    if journals.default_credit_account_id and journals.default_credit_account_id.id not in account_ids:
                        account_ids.append(journals.default_credit_account_id.id)

                bal_db_init = journals.default_debit_account_id.with_context(
                    date_from=datetime.now(),
                    date_to=datetime.now(),
                    initial_bal=True,
                    sql_query=sql_query
                ).balance
            elif branch.ahass_parent_id:
                bal_db_init = journal_brw.default_debit_account_id.balance
        else:
            #print 'KELUAR'
            bal_db_init= 0
        return bal_db_init

    @api.onchange('date')
    def get_default_date(self):
        if not self.allow_backdate:
            user = self.env['res.users'].search([('id','=',self._uid)])
            tz = pytz.timezone(user.tz) if user.tz else pytz.timezone('Asia/Jakarta')
            date_time = pytz.UTC.localize(datetime.now())
            date_time_utc = date_time.astimezone(tz)
            self.date = date_time_utc.date()

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
        
    ibanking_id = fields.Many2one('dym.ibanking', 'ibanking')
    allow_backdate = fields.Boolean(string='Backdate', default=_get_default_backdate)
    name = fields.Char(string="Name", readonly=True, default='/')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")

    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, default=_get_default_branch, domain=_getCompanyBranch)
    division = fields.Selection(DIVISION_SELECTION, string='Division', required=True, change_default=True, select=True)

    inter_branch_id = fields.Many2one('dym.branch', string='Branch Destination')
    inter_branch_division = fields.Selection(DIVISION_SELECTION, 'Division Destination')

    amount = fields.Float('Amount', compute='_compute_amount')
    state = fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date = fields.Date(string="Date", required=True)
    receive_date = fields.Date(string="Receive Date", required=False)
    payment_from_id = fields.Many2one('account.journal',string="Source of Fund",domain="[('branch_id','in',[branch_id,False]),('type','in',['cash','bank'])]")

    payment_from_id_deposit = fields.Many2one('account.journal', string="Source of Fund",domain="[('branch_id','in',[branch_id,False]),('type','in',['cash'])]")
    payment_from_id_withdraw = fields.Many2one('account.journal', string="Source of Fund",domain="[('branch_id','in',[branch_id,False]),('type','in',['bank'])]")
    payment_from_id_ats = fields.Many2one('account.journal', string="Source of Fund",domain="[('branch_id','in',[branch_id,False]),('type','in',['bank'])]")
    payment_from_id_ho2branch = fields.Many2one('account.journal', string="Source of Fund")
    payment_from_id_inhouse = fields.Many2one('account.journal', string="Source of Fund",domain="[('branch_id','in',[branch_id,False]),('type','in',['bank'])]")

    description = fields.Char(string="Description")
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line',related='move_id.line_id',string='Journal Items', readonly=True)    
    line_ids = fields.One2many('dym.bank.transfer.line','bank_transfer_id',string="Bank Transfer Line")
    line_ids1 = fields.One2many('dym.bank.transfer.line','bank_transfer_id', related='line_ids', string="Bank Transfer Line")
    line_ids2 = fields.One2many('dym.bank.transfer.line','bank_transfer_id', related='line_ids', string="Bank Transfer Line")
    bank_fee = fields.Float(string='Bank Transfer Fee',digits=dp.get_precision('Account'))
    amount_total = fields.Float(string='Total Amount',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    period_id = fields.Many2one('account.period',string="Period",required=True, readonly=True,default=_get_period)
    note = fields.Text(string="Note")
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

    analytic_2_view = fields.Many2one('account.analytic.account', 'Account Analytic Bisnis Unit', related="analytic_2", readonly="1" )
    analytic_3_view = fields.Many2one('account.analytic.account', 'Account Analytic Branch', related="analytic_3", readonly="1" )
    analytic_4_view = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center', related="analytic_4", readonly="1" )

    move_mit_id = fields.Many2one('account.move', string='Account Entry MIT', copy=False)
    move_mit_ids = fields.One2many('account.move.line',related='move_mit_id.line_id',string='Journal Items MIT', readonly=True)
    value_date = fields.Date('Value Date')
    transfer_type = fields.Selection([('normal','Normal'),('branch_replenishment','Penggantian Uang Cabang')], default="branch_replenishment")
    branch_type = fields.Selection(related='branch_id.branch_type')
    voucher_ids = fields.One2many('dym.bank.transfer.voucher', 'bank_transfer_id', string='Vouchers')
    voucher_line_ids = fields.One2many('bank.transfer.voucher.line','bank_transfer_id', string='Hutang')

    reimburse_ids = fields.One2many('dym.bank.transfer.reimburse', 'bank_transfer_id', string='Reimburse')
    invoice_line_ids = fields.One2many('bank.transfer.invoice.line','bank_transfer_id', string='Invoice')

    ref = fields.Char('Reff')
    current_balance = fields.Float(compute=_get_current_balance, string='Current Balance',invisible=True)
    xcurrent_balance = fields.Float(compute=_get_current_balance_branch, string='Current Balance',readonly=True)
    transaction_type = fields.Selection(TRANSACTION_TYPES, string='Trasnsaction Type')
    payment_method = fields.Selection([
        ('giro','Giro'),
        ('cash','Cash'),
        ('ats','ATS'),
        ('cheque','Cheque'),
        ('internet_banking','Internet Banking'),
        ('auto_debit','Auto Debit'),
        ('single_payment','Single Payment')
        ], string='Payment Method')
    cheque_giro_number = fields.Many2one('dym.checkgyro.line', string='Chk/Giro No', domain="[('journal_id','=',payment_from_id)]")
    cheque_giro_date = fields.Date(string='Chk/Giro Date',required=True,default=fields.Date.context_today)
    clearing_bank = fields.Boolean(string='Clearing Bank', default=True)
    clearing_bank_readonly = fields.Boolean(string='Clearing Bank', related="clearing_bank")
    topup_pettycash = fields.Boolean(string='Top Up Pettycash', default=False)

    @api.cr_uid_ids_context
    def button_dummy(self, cr, uid, ids, context=None):
        return True

    @api.multi
    def create_ibanking(self):
        iBanking = self.env['dym.ibanking']
        BankAccount = self.env['res.partner.bank']
        for rec in self:
            payment_to_id = rec.bank_trf_advice_id.payment_to_id
            if not payment_to_id:
                payment_to_id = rec.line_ids1.payment_to_id[0]
            AccNumber = BankAccount.search([('journal_id','=',payment_to_id.id)], limit=1)
            kode_transaksi = 'LLG'
            if rec.amount_total >= 500000000:
                kode_transaksi = 'RTGS'
            if AccNumber.bank.bic=='BCA':
                kode_transaksi = 'BCA'

            ibanking_id = iBanking.search([
                ('date','=',rec.date),
                ('kode_transaksi','=',kode_transaksi),
                ('payment_from_id','=',rec.payment_from_id.id),
                ('state','=','draft'),
            ])
            if not ibanking_id:
                name = '%s%s%s' % (kode_transaksi,datetime.strptime(rec.date,DSDF).strftime('%Y%m%d'),randint(100,999))
                # name = '%s_%s%s%s' % (rec.journal_id.code,kode_transaksi,datetime.strptime(rec.due_date_payment,DSDF).strftime('%y%m%d'),randint(100,999))
            if not ibanking_id:
                user = self.env.user
                company_id = user.company_id.id
                branch_id = self.env['dym.branch'].search([('company_id','=',user.company_id.id),('branch_status','=','HO')])
                if not branch_id:
                    raise UserError(_('Perhatian !'), _("Tidak ditemukan cabang Head Office untuk perusahaan %s" % user.company_id.name))
                acc_number = self.env['res.partner.bank'].search([('journal_id','=',rec.payment_from_id.id)])
                if not acc_number:
                    raise UserError(_('Perhatian !'), _("Journal %s tidak memiliki rekening bank." % rec.journal_id.name))
                values = {
                    'branch_id': branch_id.id,
                    'division': 'Finance',
                    'name': '/',
                    'file_name': name,
                    'payment_from_id': rec.payment_from_id.id,
                    'date': rec.date,
                    'acc_number': acc_number.id,
                    'company_id': rec.company_id.id,
                    'kode_transaksi': kode_transaksi,
                }
                ibanking_id = iBanking.create(values)
            else:
                ibanking_id = ibanking_id[0]
            rec.ibanking_id = ibanking_id.id
        return {}

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        dom = {}
        val = {}
        if self.branch_id:
            user = self.env.user
            transaction_type = self.env.context.get('transaction_type',False)
            branchs = [b.id for b in user.branch_ids if b.company_id.id==user.company_id.id and b.branch_type!='HO']
            self.inter_branch_id = branchs[0]
            if transaction_type=='ats':
                branchs = [b.id for b in user.branch_ids if b.company_id.id==user.company_id.id and b.branch_type=='HO']
            elif transaction_type=='inhouse':
                branchs = [b.id for b in user.branch_ids if b.company_id.id==user.company_id.id]
            if branchs:
                self.inter_branch_id = branchs[0]
                dom['inter_branch_id'] = [('id','in',branchs)]
            if transaction_type=='withdraw':
                self.inter_branch_id = self.branch_id.id
                self.inter_branch_division = self.division
        self.inter_branch_division = 'Finance'
        self.division = 'Finance'
        return {'domain':dom,'value':val}

    @api.onchange('division')
    def onchange_division(self):
        self.division = 'Finance'

    @api.onchange('payment_method')
    def onchange_payment_method(self):
        self.clearing_bank = False
        if self.payment_method in ['giro','ho2branch','cheque','internet_banking']:
            self.clearing_bank = True
        if self.transaction_type in ['deposit','withdraw','inhouse','ats','ho2branch']:
            self.clearing_bank = True

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
            else:
                value = {'amount_show':False}    
        else:
            value = {'payment_from_id':False}
        return {'value':value}

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

        branch_id = self._context.get('branch_id',False)
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
                    'payment_from_id_ats': [('type','=','bank'),('transaction_type','=','in'),('branch_id','=',self.branch_id.id)],
                },
            }

        # HO2Branch
        if transaction_type == 'ho2branch':
            if user.branch_type != 'HO':
                self.branch_id = False
                raise osv.except_osv(('Perhatian !'), ("Maaf, user %s tidak memiliki akses untuk membuat transaksi Head Office." % user.login))
            journal_ids = []
            for jnl in self.env['account.journal'].sudo().search([('company_id','=',self.branch_id.company_id.id),('branch_id','=',self.branch_id.id),('type','=','bank'),('transaction_type','=','in')]):
                if jnl.branch_id.id == self.branch_id.id:
                    journal_ids.append(jnl.id)
            dom['payment_from_id_ho2branch'] = [('id','in',journal_ids)]
            return {'domain': dom}

        # InHouse
        if transaction_type == 'inhouse':
            if user.branch_type != 'HO':
                self.branch_id = False
                raise osv.except_osv(('Perhatian !'), ("Maaf, user %s tidak diperbolehkan untuk membuat transaksi pemindahan uang antar rekening bank." % user.login))
            journal_ids = self.env['account.journal'].sudo().search([('company_id','=',self.branch_id.company_id.id),('branch_id','=',self.branch_id.id),('type','=','bank')])
            dom['payment_from_id_inhouse'] = [('id','in',journal_ids.ids)]
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
                'domain': dom,
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
        if self.transaction_type == 'withdraw' and not self.topup_pettycash and not self.is_settlement:
            if self.line_ids:
                for line in self.line_ids:
                    if not line.reimbursement_id and not self.voucher_line_ids:
                        raise osv.except_osv(('Perhatian!'), ("Untuk transaksi selain topup kas kecil, harus memilih RPC dan atau Hutang"))            
        self.update_cheque_giro_book(vals)
        if self.line_ids:
            for line in self.line_ids:
                line.write({'bank_transfer_id':self.id})
        
    @api.model
    def create(self,vals,context=None):
        tt = vals.get('transaction_type',False)
        if tt and tt == 'withdraw' and not vals['topup_pettycash']:
            if not vals['line_ids'] and not vals['voucher_line_ids'] and not vals['deposit_ahass_ids'] and not vals['invoice_line_ids'] and not vals['line_ids3']:
                raise osv.except_osv(('Perhatian !'), ("Untuk transaksi selain topup kas kecil, harus memilih RPC, Hutang, AHASS Deposit dan atau Invoice"))
        res_id = super(dym_bank_transfer, self).create(vals)
        if tt == 'ho2branch':
            if not res_id.line_ids1:
                vals['line_ids1'][0][2]['bank_transfer_id']=res_id.id
                data=self.env['dym.bank.transfer.line'].create(vals['line_ids1'][0][2])
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
            periods = self.env['account.period'].find(dt=self.date)
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

    @api.one
    def bank_cancel2(self):
        if self.move_mit_id:
            self.move_mit_id.action_reverse_journal()
        if self.move_id:
            self.move_id.action_reverse_journal()
        self.write({'state':'cancel'})

    @api.cr_uid_ids_context
    def action_move_line_create(self, cr, uid, ids, mit=False, context=None):
        this = self.browse(cr, uid, ids, context=context)
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        print "==action_move_line_create==="
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

                for y in banktransfer.line_ids:
                    branch_destination = self.pool.get('dym.branch').search(cr,SUPERUSER_ID,[('code','=',y.branch_destination_id)])
                    branch_dest = self.pool.get('dym.branch').browse(cr,SUPERUSER_ID,branch_destination)
                    total_debit = y.amount
                    move_line_2 = {
                        'name': _('Bank Transfer Detail %s')%(branch_dest.name),
                        'ref':name,
                        'account_id': y.payment_to_id.default_debit_account_id.id,
                        'move_id': move_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'date': date,
                        'debit': total_debit,
                        'credit': 0.0,
                        'branch_id' : branch_dest.id,
                        'division' : banktransfer.division,
                        'analytic_account_id' : y.analytic_4.id                             
                    }           
                    line_id2 = move_line_pool.create(cr, uid, move_line_2, context)
                    if y.reimbursement_id :
                        y.reimbursement_id.write({'state':'paid'})

                for y in banktransfer.voucher_line_ids:
                    branch_dest = y.branch_id
                    total_debit = y.amount_unreconciled
                    pettycash_journal_ids = self.pool.get('account.journal').search(cr, uid, [('company_id','=',y.company_id.id),('type','=','pettycash')], limit=1)
                    account_id = self.pool.get('account.journal').browse(cr, uid, pettycash_journal_ids, context=context)
                    move_line_2 = {
                        'name': _('Bank Transfer Detail %s')%(branch_dest.name),
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
           
            #Replace Analytic Branch Untuk HO2Branch
            if banktransfer.transaction_type=='ho2branch':
                move=move_pool.browse(cr,uid,move_id)
                for line in move.line_id:
                    analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr,uid,line.branch_id.id, 'Umum', False, 4, 'General')
                    line.update({'analytic_3':analytic_3_general})

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

    @api.onchange('branch_id')
    def branch_id_change(self):
        value = {}
        if self.branch_id:
            value['payment_from_id'] = False
            value['payment_from_id_deposit'] = False
            value['payment_from_id_withdraw'] = False
            value['payment_from_id_ats'] = False
            value['payment_from_id_ho2branch'] = False
            value['payment_from_id_inhouse'] = False
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.env['account.analytic.account'].get_analytical(self.branch_id.id, 'Umum', False, 4, 'General')
            self.analytic_1 = analytic_1_general
            self.analytic_2 = analytic_2_general
            self.analytic_3 = analytic_3_general
            self.analytic_4 = analytic_4_general
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



class bank_transfer_invoice_line(models.Model): 
    _name = 'bank.transfer.invoice.line'
    _description = 'Bank Transfer Invoice Line'

    bank_transfer_id = fields.Many2one('dym.bank.transfer',string="Bank Transfer")
    company_id = fields.Many2one('res.company', string='Company', related='bank_transfer_id.company_id')
    branch_id = fields.Many2one('dym.branch', string='Branch', related='bank_transfer_id.branch_id')
    division = fields.Selection(DIVISION_SELECTION, string='Division', related='bank_transfer_id.division')
    invoice_id = fields.Many2one('account.invoice', string='Invoice Item', copy=False)
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'), related='invoice_id.amount_total', help="Total invoice amount.")
    residual = fields.Float(string='Balance', digits=dp.get_precision('Account'), related='invoice_id.residual', help="Remaining amount due.")


class account_invoice(models.Model): 
    _inherit = 'account.invoice'

    withdraw_line_id = fields.One2many('bank.transfer.invoice.line','invoice_id', string='Withdraw Line')

class bank_transfer_voucher_line(models.Model): 
    _name = 'bank.transfer.voucher.line'
    _description = 'Bank Transfer Voucher Line'

    bank_transfer_id = fields.Many2one('dym.bank.transfer',string="Bank Transfer")
    company_id = fields.Many2one('res.company', string='Company', related='bank_transfer_id.company_id')
    branch_id = fields.Many2one('dym.branch', string='Branch', related='bank_transfer_id.branch_id')
    division = fields.Selection(DIVISION_SELECTION, string='Division', related='bank_transfer_id.division')
    move_line_id = fields.Many2one('account.move.line', string='Journal Item', copy=False)
    date_original = fields.Date(related='move_line_id.date', string='Date', readonly=1)
    date_due = fields.Date(related='move_line_id.date_maturity', string='Due Date', readonly=1)
    amount_original = fields.Float(string='Original Amount')
    amount_original_view = fields.Float(string='Original Amount', related="amount_original" )
    amount_unreconciled = fields.Float(related='move_line_id.amount_residual', string='Open Balance', readonly=1)

    @api.onchange('move_line_id')
    def onchange_move_line_id(self):
        if self.move_line_id:
            self.amount_original = self.move_line_id.credit or self.move_line_id.debit

        Account = self.env['account.account']
        AML = self.env['account.move.line']
        account_hutang_lain_id = Account.search([('code','in',('2106099','2102099')),('company_id','=',self.company_id.id),('type','=','payable')])
        ml_domain = [
            # ('account_id.type','=','payable'),
            ('dym_loan_id','=',False),
            ('branch_id','=',self.branch_id.id),
            ('account_id','in',account_hutang_lain_id.ids),
            ('bank_trf_voucher_line_id','=',False),
        ]
        aml_ids = []
        amls = AML.search(ml_domain)
        for aml in amls:
            if aml.reconcile_id:
                for amlrec_id in AML.search([('reconcile_id','=',aml.reconcile_id.id)]):
                    if amlrec_id.journal_id.type == 'pettycash':
                        if not '(Reversed)' in amlrec_id.ref:
                            if not AML.search([('ref','=','%s (Reversed)' % amlrec_id.ref)]):
                                aml_ids.append(amlrec_id.id)
            else:
                if aml.ref and not '(Reversed)' in aml.ref:
                    aml_ids.append(aml.id)

        dom = {
            'move_line_id': [
                ('id','in',aml_ids)
            ]
        }
        return {'domain':dom}

class account_move_line(models.Model): 
    _inherit = 'account.move.line'

    bank_trf_voucher_line_id = fields.One2many('bank.transfer.voucher.line','move_line_id')

class dym_bank_transfer_reimburse(models.Model): 
    _name = 'dym.bank.transfer.reimburse'
    _description = 'Bank Transfer Line Reimburse'

    bank_transfer_id = fields.Many2one('dym.bank.transfer',string="Bank Transfer")
    reimburse_id = fields.Many2one('dym.reimbursed', string="Reimburse")
    date = fields.Date(related="reimburse_id.date_approve")
    # date_due = fields.Date(related="reimburse_id.date_due")
    amount = fields.Float(related="reimburse_id.amount_total")
    # net_amount = fields.Float(related="reimburse_id.net_amount")
    notes = fields.Text('Notes')
    account_id = fields.Many2one('account.account', string="Account")
    line_amount = fields.Float(string="Amount")

    @api.onchange('reimburse_id')
    def onchange_reimburse_id(self):
        context = self._context
        notes = []
        for vline in self.reimburse_id.line_ids:
            notes.append(vline.name)
        self.notes = ', '.join(notes)

class dym_bank_transfer_line(models.Model): 
    _name = 'dym.bank.transfer.line'
    _description = 'Bank Transfer Line'

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
    payment_to_id = fields.Many2one('account.journal',string="Bank")
    description = fields.Char(string="Description")
    amount = fields.Float('Amount')
    bank_transfer_id = fields.Many2one('dym.bank.transfer',string="Bank Transfer")
    transaction_type = fields.Selection(TRANSACTION_TYPES, string='Trasnsaction Type')
    reimbursement_id = fields.Many2one('dym.reimbursed',domain="[('state','=','paid')]", string="Reimbursed No")
    topup_pettycash = fields.Boolean(string='Top Up Pettycash', related="bank_transfer_id.topup_pettycash")

    # reimbursement_id = fields.Many2one('dym.reimbursed',domain="[('state','=','approved')]", string="Reimbursed No")
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
        inter_branch_id = self._context.get('inter_branch_id',False)
        branch_via_id = self._context.get('branch_via_id',False)
        # topup_pettycash = self._context.get('topup_pettycash',False)
        # if topup_pettycash:
        #     res['topup_pettycash'] = topup_pettycash
        if transaction_type:
            res['transaction_type'] = transaction_type
        if inter_branch_id:
            res['branch_destination_select'] = branch_via_id or inter_branch_id
        return res

    @api.onchange('reimbursement_id')
    def onchange_reimbursement_id(self):
        dom = {}
        if self.reimbursement_id:
            self.amount = self.reimbursement_id.amount_total
        if self.bank_transfer_id.branch_id.branch_type == 'HO':
            dom['reimbursement_id'] = ['|',('state','=','paid'),'&',('state','=','approved'),('branch_id','=',self.bank_transfer_id.branch_id.id)]
            return {'domain': dom}

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

        if not self.reimbursement_id :
            self.payment_to_id = False

        branch_obj = self.env['dym.branch']
        journal_obj = self.env['account.journal']
        user = self.env.user

        transaction_type = self._context.get('transaction_type',False)
        branch_id = self._context.get('inter_branch_id',False)
        payment_from_id = self._context.get('payment_from_id',False)
        if not branch_id:
            raise osv.except_osv(('Perhatian !'), ("Silahkan pilih cabang terlebih dahulu.")) 

        branch = branch_obj.browse(branch_id)

        if transaction_type == 'deposit':
            dom['branch_destination_select'] = [('id','=',branch_id)]
            self.branch_destination_select = branch_id
            branch_dest_id = branch
            journal_ids = journal_obj.sudo().search([('company_id','=',branch_dest_id.company_id.id),('branch_id','=',branch_dest_id.id),('type','=','bank'),('transaction_type','=','in')])
            dom['payment_to_id'] = [('id','in',journal_ids.ids)]
            self.payment_to_id = journal_ids and journal_ids[0] or False

        if transaction_type == 'withdraw':
            dom['branch_destination_select'] = [('id','=',branch_id)]
            self.branch_destination_select = branch_id
            branch_dest_id = branch
            type_journal = []
            if branch.branch_status == 'HO':
                type_journal.extend(['cash','pettycash'])
            else:
                type_journal.append('pettycash')
            journal_ids = journal_obj.sudo().search([('company_id','=',branch_dest_id.company_id.id),('type','in',type_journal)])
            dom['payment_to_id'] = [('id','in',journal_ids.ids)]
            self.payment_to_id = journal_ids and journal_ids[0] or False

        if transaction_type == 'ats':

            if user.branch_type != 'HO':
                branch_dest_id = branch_obj.sudo().search([('company_id','=',branch.company_id.id),('branch_type','=','HO')])
            else:
                branch_dest_id = branch
            dom['branch_destination_select'] = [('id','=',branch_dest_id.id)]
            self.branch_destination_select = branch_dest_id.id
            if self.branch_destination_select:
                journal_ids = journal_obj.sudo().search([('ats_from_branch_ids','in',self.bank_transfer_id.branch_id.id),('type','=','bank'),('transaction_type','=','in')])
                if journal_ids:
                    dom['payment_to_id'] = [('id','in',journal_ids.ids)]
                    self.payment_to_id = journal_ids and journal_ids.ids[0] or False
                else:
                    raise osv.except_osv(('Perhatian !'), ("Cabang %s tidak memiliki rekening bank keluar (out)." % branch_dest_id.name)) 

        if transaction_type == 'ho2branch':
            branch_dest_id = False
            branch_dest_ids = branch_obj.search([('company_id','=',branch.company_id.id),('branch_type','!=','HO')])
            dom['branch_destination_select'] = [('id','in',branch_dest_ids.ids)]
            dom['payment_to_id'] = []
            if self.branch_destination_select:
                branch_dest_id = self.branch_destination_select
                journal_ids = journal_obj.sudo().search([('branch_id','=',branch_dest_id.id),('type','=','bank'),('transaction_type','=','out')])
                if journal_ids:
                    dom['payment_to_id'] = [('id','in',journal_ids.ids)]
                    self.payment_to_id = journal_ids[0].id
                else:
                    raise osv.except_osv(('Perhatian !'), ("Cabang %s tidak memiliki rekening bank keluar (out)." % branch_dest_id.name)) 

        if transaction_type == 'inhouse':
            dom['branch_destination_select'] = [('id','=',branch_id)]
            self.branch_destination_select = branch_id
            if self.branch_destination_select:
                branch_dest_id = branch
                journal_ids = []
                for jnl in self.env['account.journal'].sudo().search([('company_id','=',branch_dest_id.company_id.id),('branch_id','=',branch_dest_id.id),('type','=','bank')]):
                    if jnl.branch_id.id == branch_dest_id.id and jnl.id != payment_from_id:
                        journal_ids.append(jnl.id)
                if journal_ids:
                    dom['payment_to_id'] = [('id','in',journal_ids)]

        if self.branch_destination_select:
            self.branch_destination_id = self.branch_destination_select.code

        self.description = self.bank_transfer_id.description

        if branch_dest_id:
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.env['account.analytic.account'].get_analytical(branch_dest_id, 'Finance', False, 4, 'General')
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

