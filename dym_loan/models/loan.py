from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from lxml import etree
import fungsi_terbilang

class AccountFilter(models.Model):
    _inherit = "dym.account.filter"

    def _register_hook(self, cr):
        selection = self._columns['name'].selection
        if ('loan_account_pengakuan_pinjaman','Loan - Account Pencairan Pinjaman') not in selection: 
            self._columns['name'].selection.append(
                ('loan_account_pengakuan_pinjaman', 'Loan - Account Pencairan Pinjaman')
                )
        if ('loan_account_pengakuan_piutang','Loan - Account Pencairan Piutang') not in selection: 
            self._columns['name'].selection.append(
                ('loan_account_pengakuan_piutang', 'Loan - Account Pencairan Piutang')
                )
        return super(AccountFilter, self)._register_hook(cr)  

class dym_loan(models.Model):
    _name = "dym.loan"
    _inherit = ['mail.thread']
    _description = "Loan"

    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil

    def ubah_tanggal(self,tanggal):
        try:
            conv = datetime.strptime(tanggal, '%d-%m-%Y %H:%M')
            return conv.strftime('%d/%m/%Y')
        except Exception as e:
            conv = datetime.strptime(tanggal, '%Y-%m-%d %H:%M:%S')
            return conv.strftime('%d/%m/%Y')
    
    @api.one
    @api.depends('invoice_ids')
    def _compute_jumlah_rekla(self):
        jumlah_loan_rekla = 0.0
        move_line_obj = self.env['account.move.line']
        move_line_ids = []
        for inv in self.invoice_ids:
            move_lines_check = move_line_obj.search([
                ('move_id','=',inv.move_id.id),
                ('credit','!=',0),
                ('account_id.type','=','payable'),
                # ('reconcile_partial_id','!=',False)
                ('reconcile_id','!=',False),
            ])
            if not move_lines_check:
                move_lines = move_line_obj.search([
                    ('move_id','=',inv.move_id.id),
                    ('credit','!=',0),
                    ('account_id.type','=','payable'),
                    ('reconcile_id','=',False),
                    # ('reconcile_partial_id','=',False)
                    ])
                for line in move_lines:
                    amount_unreconciled = abs(line.fake_balance)
                    jumlah_loan_rekla += amount_unreconciled
                    move_line_ids.append(line.id)
        self.jumlah_loan = jumlah_loan_rekla
        self.jumlah_loan_rekla = jumlah_loan_rekla
        self.move_line_ids = move_line_ids

    @api.model
    def _get_default_date(self):
        return self.env['dym.branch'].get_default_date_model()
        
    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_loan] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    name = fields.Char('Name')
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('confirmed','Confirmed'),
        # ('open','Open'),
        ('done','Done'),
        ('cancel','Cancelled'),
        ('reject','Rejected'),
        ], 'State', default='draft')
    date = fields.Date('Transaction Date', readonly=False)
    branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    partner_id = fields.Many2one('res.partner', 'Ke Partner', domain="[('creditur_debitur','=',True)]", required=True)
    loan_type = fields.Selection([
        ('Pinjaman','Pinjaman'),
        ('Piutang','Piutang'),
        ('Reklasifikasi','Reklasifikasi Hutang DF'),
        ], 'Type')
    jumlah_loan = fields.Float('Jumlah', digits=dp.get_precision('Account'))
    invoice_ids = fields.Many2many('account.invoice','dym_loan_invoice_rel','loan_id','invoice_id','Invoices', domain="[('partner_id','=',partner_id_dari),('division','=',division),('type','=','in_invoice'),('move_id','!=',False),('state','=','open'),('residual','>',0),('consolidated','=',True)]")
    partner_id_dari = fields.Many2one('res.partner', 'Dari Partner', domain="[('principle','=',True)]")
    jumlah_loan_rekla = fields.Float('Jumlah', digits=dp.get_precision('Account'), readonly=True, compute='_compute_jumlah_rekla', store=True) 
    move_line_ids = fields.Many2many('account.move.line','dym_loan_move_line_rel','loan_id','move_line_id','Move Line', compute='_compute_jumlah_rekla', store=True)
    user_id = fields.Many2one('res.users', 'Responsible')
    loan_line = fields.One2many('dym.loan.line', 'loan_id', 'Detail Loan')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=True)
    loan_id = fields.Many2one('dym.loan', string='Source Loan')
    reference = fields.Char('Reference #')
    memo = fields.Char('Memo')
    effective_date = fields.Date('Effective Date', required=True)
    first_due_date = fields.Date('First Due Date', required=True)
    final_due_date = fields.Date('Final Due Date')
    jadwal = fields.Selection([('Harian','Harian'),('Bulanan','Bulanan'),('Tahunan','Tahunan')], 'Jadwal')
    due_type = fields.Selection([
                              ('Sekaligus','Sekaligus'),
                              ('Jadwal','Jadwal'),
                              ], 'Due Type')
    account_id = fields.Many2one('account.account', 'Account Pencairan')
    voucher_id = fields.Many2one('account.voucher', 'RV/PV No.', readonly=True, copy=False)
    analytic_1 = fields.Many2one('account.analytic.account', string='Account Analytic Company', default=_get_analytic_company)
    analytic_2 = fields.Many2one('account.analytic.account', string='Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', string='Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', string='Account Analytic Cost Center')
    journal_id = fields.Many2one('account.journal', string="Payment Method")
    tipe_pinjaman = fields.Selection([
                                  ('pendek','Jangka Pendek'),
                                  ('panjang','Jangka Panjang'),
                                  ('intercompany','Pinjaman Intercompany'),
                                ], 'Tipe Pinjaman')
    
    _defaults={
        'user_id': lambda obj, cr, uid, context:uid,
        'date' : _get_default_date,
        'state':'draft'
    }

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'LOA', division='Umum')
        return super(dym_loan, self).create(cr, uid, vals, context=context)

    @api.onchange('loan_id')
    def loan_id_change(self):
        if self.loan_id:
            self.reference = self.loan_id.name
            self.jumlah_loan = self.loan_id.jumlah_loan

    @api.onchange('partner_id')
    def partner_id_change(self):
        domains = {}
        values = {}
        if self.partner_id:
            loan_ids = [x.id for x in self.sudo().search([('loan_type','=','Pinjaman'),('branch_id.company_id.partner_id','=',self.partner_id.id),('state','!=','done')])]
            domains['loan_id'] = [('id','in',loan_ids)]
        return {
            'domain': domains,
            'value': values,
        }


    @api.onchange('loan_type')
    def account_change(self):
        dom = {}
        edi_doc_list = ['&', ('active','=',True), ('type','!=','view')] 
        filter = self.env['dym.account.filter']         
        if self.loan_type == 'Pinjaman':
            dict = filter.get_domain_account("loan_account_pengakuan_pinjaman")
            edi_doc_list.extend(dict)
            dom['account_id']=edi_doc_list
        elif self.loan_type == 'Piutang':
            dict = filter.get_domain_account("loan_account_pengakuan_piutang")
            edi_doc_list.extend(dict)
            dom['account_id']=edi_doc_list
        return {'domain':dom}

    @api.onchange('branch_id')
    def branch_change(self):
        self.loan_line = False

    @api.onchange('due_type','jadwal','first_due_date','final_due_date')
    def jadwal_change(self):
        self.loan_line = False

    @api.onchange('loan_type','division')
    def divisi_type(self):
        if self.loan_type == 'Reklasifikasi' and self.division != 'Unit':
            self.loan_type = False
            return {'warning':{'title':'Invalid action!','message':'Tipe reklasifikasi hanya bisa diproses di divisi unit!'}}

    @api.onchange('branch_id','loan_type','invoice_ids')
    def analytic_loan_change(self):
        if self.loan_type in ['Pinjaman','Piutang'] and self.branch_id:
            analytic_1,analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(self._cr, self._uid, self.branch_id, 'Umum',False, 4, 'General')
            self.analytic_1 = analytic_1
            self.analytic_2 = analytic_2
            self.analytic_3 = analytic_3
            self.analytic_4 = analytic_4
        elif self.loan_type == 'Reklasifikasi' and self.invoice_ids:
            self.analytic_1 = self.invoice_ids[0].analytic_1.id
            self.analytic_2 = self.invoice_ids[0].analytic_2.id
            self.analytic_3 = self.invoice_ids[0].analytic_3.id
            self.analytic_4 = self.invoice_ids[0].analytic_4.id
        else:  
            self.analytic_1 = False
            self.analytic_2 = False
            self.analytic_3 = False
            self.analytic_4 = False

    @api.multi
    def wkf_action_cancel(self):
        if self.state != 'draft':
            for line in self.loan_line:
                if line.voucher_id and line.voucher_id.state not in ['draft','cancel']:
                    raise osv.except_osv(('Invalid action !'), ('Data payment %s sudah di proses, tidak bisa mencancel data!') % (line.voucher_id.number))
                if line.voucher_id.id and line.voucher_id.state != 'cancel':
                    line.voucher_id.cancel_voucher()
            if self.voucher_id and self.voucher_id.state not in ['draft','cancel']:
                raise osv.except_osv(('Invalid action !'), ('Data payment %s sudah di proses, tidak bisa mencancel data!') % (self.voucher_id.number))
            if self.voucher_id.id and self.voucher_id.state != 'cancel':
                self.voucher_id.cancel_voucher()
            move = False
            if self.state != 'done':
                if self.loan_type == 'Pinjaman':
                    move = self.env['account.move.line'].search([
                        ('dym_loan_id','=',self.id),
                        ('credit','>',0)
                    ]).move_id
                if self.loan_type == 'Piutang':
                    move = self.env['account.move.line'].search([
                        ('dym_loan_id','=',self.id),
                        ('credit','>',0)
                    ]).move_id
            if move:
                for move_line in move.line_id:
                    if move_line.reconcile_partial_id.line_partial_ids or move_line.reconcile_id.line_id:
                        raise except_orm(_('Error!'), _('You cannot cancel an invoice which is paid. You need to unreconcile related payment entries first.'))
                move.action_reverse_journal()
            if self.loan_type == 'Reklasifikasi':
                # raise osv.except_osv(('Invalid action !'), ('Data payment %s sudah di proses, tidak bisa mencancel data!') % (self.voucher_id.number))
                if self.state == 'confirmed' or self.state == 'done':
                    self.cancel_loan_reklas()
        self.write({'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
        self.message_post(body=_("Loan %s Canceled")%(self.name))
        
    @api.multi
    def close_loan(self):
        total_loan = 0
        if self.voucher_id and self.voucher_id.state != 'posted':
            raise osv.except_osv(('Invalid action !'), ('Data payment %s belum di proses, tidak bisa close data!') % (self.voucher_id.number))
        for line in self.loan_line:
            if line.voucher_id.state == 'posted':
                total_loan += line.pokok
        if total_loan < self.jumlah_loan:
            raise osv.except_osv(('Invalid action !'), ('Total loan yang di buat kurang dari jumlah loan yang di set, mohon di tambah!'))
        self.write({'state': 'done'})
        self.message_post(body=_("Loan %s Closed")%(self.name))
    
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Cannot delete a loan which is in state \'%s\'!') % (val.state))
        val.message_post(body=_("Loan %s Deleted")%(val.name))
        return super(dym_loan, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def generate_schedule(self):
        for lo_line in self.loan_line:
            lo_line.unlink()
        loan_line_obj = self.env['dym.loan.line']
        res = []
        if self.due_type == 'Sekaligus':
            res.append({'loan_id':self.id, 'due_date': self.first_due_date, 'pokok': self.jumlah_loan, 'bunga': 0, 'voucher_id':False})
        if self.due_type == 'Jadwal':
            if self.first_due_date > self.final_due_date:
                raise osv.except_osv(('Tidak bisa generate !'), ('tanggal awal due date tidak boleh lebih dari tanggal final due date'))
            first_date_obj = datetime.strptime(self.first_due_date, '%Y-%m-%d')
            final_date_obj = datetime.strptime(self.final_due_date, '%Y-%m-%d')
            if self.jadwal == 'Harian':                
                date_diff = int((datetime.date(final_date_obj)-datetime.date(first_date_obj)).days)
                pokok_split = self.jumlah_loan / (date_diff+1)
                for i in range(date_diff+1):
                    res.append({'loan_id':self.id, 'due_date': (first_date_obj+timedelta(days=i)).strftime('%Y-%m-%d'), 'pokok': pokok_split, 'bunga': 0, 'voucher_id':False})
            elif self.jadwal == 'Bulanan':
                month_diff = (final_date_obj.year - first_date_obj.year)*12 + final_date_obj.month - first_date_obj.month
                pokok_split = self.jumlah_loan / (month_diff+1)
                for i in range(month_diff+1):
                    if (first_date_obj+relativedelta(months=i)).month != final_date_obj.month:
                        res.append({'loan_id':self.id, 'due_date': (first_date_obj+relativedelta(months=i)).strftime('%Y-%m-%d'), 'pokok': pokok_split, 'bunga': 0, 'voucher_id':False})
                    else:
                        res.append({'loan_id':self.id, 'due_date': final_date_obj.strftime('%Y-%m-%d'), 'pokok': pokok_split, 'bunga': 0, 'voucher_id':False})
            elif self.jadwal == 'Tahunan':
                year_diff = final_date_obj.year - first_date_obj.year
                pokok_split = self.jumlah_loan / (year_diff+1)
                for i in range(year_diff+1):
                    if (first_date_obj+relativedelta(years=i)).year != final_date_obj.year:
                        res.append({'loan_id':self.id, 'due_date': (first_date_obj+relativedelta(years=i)).strftime('%Y-%m-%d'), 'pokok': pokok_split, 'bunga': 0, 'voucher_id':False})
                    else:
                        res.append({'loan_id':self.id, 'due_date': final_date_obj.strftime('%Y-%m-%d'), 'pokok': pokok_split, 'bunga': 0, 'voucher_id':False})
        for line in res:
            loan_line_obj.create(line)
        return True

    @api.multi
    def generate_sisa(self):
        loan_line_obj = self.env['dym.loan.line']
        sisa = 0
        bayar = 0
        for lo_line in self.loan_line:
            if self.loan_type == 'Pinjaman':
                for line in lo_line.voucher_id.line_dr_ids:
                    if not line.reconcile:
                        bayar += line.amount
            else:
                for line in lo_line.voucher_id.line_cr_ids:
                    if not line.reconcile:
                        bayar += line.amount
             
        sisa = self.jumlah_loan - bayar
        if sisa > 0:
            loan_line = loan_line_obj.create({
                            'loan_id': self.id,
                            'due_date': datetime.strptime(self.first_due_date, '%Y-%m-%d'),
                            'bunga': 0,
                            'pokok': sisa,
                            })
    
    @api.multi
    def cancel_loan_reklas(self):
        obj_acc_move = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        acc_move = obj_acc_move.search([('model','=',self._name),('transaction_id', '=', self.id)])

        for invoice in self.invoice_ids:
            invoice.write({'state':'open','reconciled':False})
            move_lines = move_line_obj.search([
                ('move_id','=',invoice.move_id.id),
                ('credit','!=',0),
                ('account_id.type','=','payable'),
                ('reconcile_id','!=',False),
            ])

            if move_lines:
                for line in move_lines:
                    line.write({'reconcile_id':False})

        if acc_move:
            for move in acc_move:
                move.action_reverse_journal()

        for line in self.loan_line:
            acc_move_bunga = obj_acc_move.search([('model','=',line._name),('transaction_id', '=', line.id)])
            if acc_move_bunga:
                acc_move_bunga.action_reverse_journal()

        return True


class dym_loan_line(models.Model):
    _name = "dym.loan.line"
    _order = "due_date asc"

    @api.one
    @api.depends('loan_id.state','loan_id.voucher_id.state','loan_id.loan_type')
    def _compute_state(self):
        self.state = self.loan_id.state
        self.loan_voucher_state = self.loan_id.voucher_id.state
        self.loan_type = self.loan_id.loan_type

    @api.one
    @api.depends('pokok', 'bunga')
    def _compute_jumlah(self):
        self.jumlah = self.pokok + self.bunga

    loan_id = fields.Many2one('dym.loan', 'Loan')
    due_date = fields.Date('Due Date', required=True)
    interest_date = fields.Date('Interest Date', required=False)
    jumlah = fields.Float(string='Jumlah', digits=dp.get_precision('Account'), readonly=True, compute='_compute_jumlah')
    pokok = fields.Float(string='Pokok', digits=dp.get_precision('Account'), required=True)
    bunga = fields.Float(string='Bunga', digits=dp.get_precision('Account'), required=True)
    voucher_id = fields.Many2one('account.voucher', 'RV/PV No.', readonly=True, copy=False)
    loan_type = fields.Char('Loan Type', compute='_compute_state')
    loan_voucher_state = fields.Char('Voucher State', compute='_compute_state')
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('confirmed','Confirmed'),
        ('done','Done'),
        ('cancel','Cancelled'),
        ('reject','Rejected'),
    ], 'State', compute='_compute_state')
    
    @api.onchange('pokok')
    def pokok_change(self):
        if not self.pokok:
            sisa = self.loan_id.jumlah_loan
            for line in self.loan_id.loan_line:
                if line.voucher_id.state != 'draft':
                    sisa -= line.pokok
            self.pokok = sisa

    @api.onchange('bunga')
    def interest_bunga(self):
        if self.bunga:
            self.interest_date = self.loan_id.first_due_date

    @api.onchange('due_date')
    def due_date_change(self):
        if self.loan_id.due_type == 'Jadwal':
            if not self.due_date:
                if datetime.strftime(date.today(), '%Y-%m-%d') <= self.loan_id.final_due_date:
                    self.due_date = date.today()
                else:
                    self.due_date = False
                    return {'warning':{'title':'Invalid action!','message':'Tanggal final due date sudah lewat'}}
            else:
                if self.due_date > self.loan_id.final_due_date:
                    self.due_date = False
                    return {'warning':{'title':'Invalid action!','message':'Tanggal due date tidak boleh lebih tanggal final due date'}}

    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.voucher_id and val.voucher_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Cannot cancel voucher which is in state \'%s\'!') % (val.voucher_id.state))
        if val.voucher_id:
                val.voucher_id.cancel_voucher()
        return super(dym_loan_line, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def action_move_create(self, journal, jumlah, account_debit, account_credit):
        move_obj = self.env['account.move']
        analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.loan_id.branch_id.id, 'Umum', False, 4, 'General')
        """
        # Beban Bunga Loan ke HO
        analytic_id = analytic_4
        # Beban Bunga Loan ke Cabang
        analytic_id = self.loan_id.analytic_4.id
        """
        analytic_id = analytic_4
        period_ids = self.env['account.period'].find()
        move_journal = {
            'name': self.loan_id.name,
            'ref': self.loan_id.name,
            'journal_id': journal.id,
            'date': self.loan_id.first_due_date,
            'period_id':period_ids.id,
            'transaction_id':self.id,
            'model':self.__class__.__name__,
        }
        move_line = [[0,False,{
            'name': _('Bunga Loan ' + self.loan_id.name),
            'partner_id': self.loan_id.partner_id.id,
            'account_id': account_credit,
            'period_id':period_ids.id,
            'date': self.interest_date,
            'debit': 0.0,
            'credit': jumlah,
            'branch_id': self.loan_id.branch_id.id,
            'division': self.loan_id.division,
            'date_maturity': self.due_date,
            'analytic_account_id' : analytic_id
        }]]        
        move_line.append([0,False,{
            'name': _('Bunga Loan ' + self.loan_id.name),
            'partner_id': self.loan_id.partner_id.id,
            'account_id': account_debit,
            'period_id':period_ids.id,
            'date': self.interest_date,
            'debit': jumlah,
            'credit': False,
            'branch_id': self.loan_id.branch_id.id,
            'division': self.loan_id.division,
            'date_maturity': self.due_date,
            'analytic_account_id' : analytic_id
        }])
        move_journal['line_id'] = move_line
        create_journal = move_obj.create(move_journal)
        if journal.entry_posted:
            post_journal = create_journal.post()
        return create_journal

    @api.multi
    def create_voucher(self):
        branch_id = self.loan_id.branch_id.id
        branch_config = self.env['dym.branch.config'].search([
            ('branch_id','=',branch_id)
        ])
        if not branch_config :
            raise osv.except_osv(('Perhatian !'), ("Belum ada branch config atas branch %s !")%(branch_config.branch_id.code))
        analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(branch_id, 'Umum', False, 4, 'General')
        voucher_obj = self.env['account.voucher']
        journal_id = self.loan_id.journal_id
        voucher = {
            'branch_id':self.loan_id.branch_id.id, 
            'division': self.loan_id.division, 
            'inter_branch_id':self.loan_id.branch_id.id, 
            'inter_branch_division': self.loan_id.division,
            'partner_id': self.loan_id.partner_id.id, 
            'date': self.loan_id.first_due_date, 
            'amount': self.jumlah, 
            'date_due_payment': self.due_date, 
            'reference': self.loan_id.name, 
            'name': self.loan_id.memo, 
            'user_id': self.loan_id.user_id.id,
            'analytic_1': analytic_1,
            'analytic_2': analytic_2,
            'analytic_3': analytic_3,
            'analytic_4': analytic_4,
            'journal_id': journal_id.id,
            'account_id': journal_id.default_credit_account_id.id,
        }

        if self.loan_id.loan_type == 'Pinjaman':
            move_line_id = self.env['account.move.line'].search([
                ('dym_loan_id','=',self.loan_id.id),
                ('credit','>',0)
            ]).id
            if not move_line_id :
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi %s!")%(self.loan_id.name))
        
            move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_id, self.pokok, False, False)
            voucher_line = [[0,0,{
                'move_line_id': move_line_vals['value']['move_line_id'], 
                'account_id': move_line_vals['value']['account_id'], 
                'date_original': move_line_vals['value']['date_original'], 
                'date_due': move_line_vals['value']['date_due'], 
                'amount_original': move_line_vals['value']['amount_original'], 
                'amount_unreconciled': move_line_vals['value']['amount_unreconciled'],
                'amount': self.pokok, 
                'currency_id': move_line_vals['value']['currency_id'], 
                'type': 'dr', 
                'name': move_line_vals['value']['name'],
                'reconcile': True,
            }]]
            if self.bunga:
                journal_bunga =  branch_config.dym_journal_loan_bunga_pinjaman
                if not journal_bunga or not journal_bunga.default_debit_account_id or not journal_bunga.default_credit_account_id:
                    raise osv.except_osv(('Perhatian !'), ("Journal bunga pinjaman belum lengkap dalam branch %s !")%(branch_config.branch_id.code))
                created_move = self.action_move_create(journal_bunga, self.bunga, journal_bunga.default_debit_account_id.id, journal_bunga.default_credit_account_id.id)
                for line in created_move.line_id:
                    if line.credit > 0.0:
                        move_line_bunga = line.id
                        if line.account_id.type != 'payable':
                            raise osv.except_osv(('Perhatian !'), ("Account %s harus tipe payable dan allow reconcile!")%(line.account_id.name))
                if not move_line_bunga :
                    raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi %s!")%(self.loan_id.name))
                move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_bunga, self.bunga, False, False)
                voucher_line.append([0,0,{
                    'move_line_id': move_line_vals['value']['move_line_id'], 
                    'account_id': move_line_vals['value']['account_id'], 
                    'date_original': move_line_vals['value']['date_original'], 
                    'date_due': move_line_vals['value']['date_due'], 
                    'amount_original': move_line_vals['value']['amount_original'], 
                    'amount_unreconciled': move_line_vals['value']['amount_unreconciled'],
                    'amount': self.bunga, 
                    'currency_id': move_line_vals['value']['currency_id'], 
                    'type': 'dr', 
                    'name': move_line_vals['value']['name'],
                    'reconcile': True,
                }])
            voucher['type'] = 'payment'
            voucher['line_dr_ids'] = voucher_line
            voucher['line_cr_ids'] = []
        elif self.loan_id.loan_type == 'Piutang':
            move_line_id = self.env['account.move.line'].search([
                ('dym_loan_id','=',self.loan_id.id),
                ('debit','>',0)
            ]).id
            if not move_line_id :
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi %s!")%(self.loan_id.name))
            move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_id, self.pokok, False, False)
            voucher_line = [[0,0,{
                'move_line_id': move_line_vals['value']['move_line_id'], 
                'account_id': move_line_vals['value']['account_id'], 
                'date_original': move_line_vals['value']['date_original'], 
                'date_due': move_line_vals['value']['date_due'], 
                'amount_original': move_line_vals['value']['amount_original'], 
                'amount_unreconciled': move_line_vals['value']['amount_unreconciled'],
                'amount': self.pokok, 
                'currency_id': move_line_vals['value']['currency_id'], 
                'type': 'cr', 
                'name': move_line_vals['value']['name'],
                'reconcile': True,
            }]]
            if self.bunga:
                journal_bunga =  branch_config.dym_journal_loan_bunga_piutang
                if not journal_bunga or not journal_bunga.default_debit_account_id or not journal_bunga.default_credit_account_id:
                    raise osv.except_osv(('Perhatian !'), ("Journal bunga piutang belum lengkap dalam branch %s !")%(branch_config.branch_id.code))
                created_move = self.action_move_create(journal_bunga, self.bunga, journal_bunga.default_debit_account_id.id, journal_bunga.default_credit_account_id.id)
                for line in created_move.line_id:
                    if line.debit > 0.0:
                        move_line_bunga = line.id
                        if line.account_id.type != 'receivable':
                            raise osv.except_osv(('Perhatian !'), ("Account %s harus tipe receivable dan allow reconcile!")%(line.account_id.name))
                if not move_line_bunga :
                    raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi %s!")%(self.loan_id.name))
                move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_bunga, self.bunga, False, False)
                voucher_line.append([0,0,{
                    'move_line_id': move_line_vals['value']['move_line_id'], 
                    'account_id': move_line_vals['value']['account_id'], 
                    'date_original': move_line_vals['value']['date_original'], 
                    'date_due': move_line_vals['value']['date_due'], 
                    'amount_original': move_line_vals['value']['amount_original'], 
                    'amount_unreconciled': move_line_vals['value']['amount_unreconciled'],
                    'amount': self.bunga, 
                    'currency_id': move_line_vals['value']['currency_id'], 
                    'type': 'cr', 
                    'name': move_line_vals['value']['name'],
                    'reconcile': True,
                }])
            voucher['type'] = 'receipt'
            voucher['line_cr_ids'] = voucher_line
            voucher['line_dr_ids'] = []
        elif self.loan_id.loan_type == 'Reklasifikasi':
            move_line_id = self.env['account.move.line'].search([
                ('dym_loan_id','=',self.loan_id.id),
                ('credit','>',0)
            ]).id
            if not move_line_id :
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi %s!")%(self.loan_id.name))
            move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_id, self.pokok, False, False)
            voucher_line = [[0,0,{
                'move_line_id': move_line_vals['value']['move_line_id'], 
                'account_id': move_line_vals['value']['account_id'], 
                'date_original': move_line_vals['value']['date_original'], 
                'date_due': move_line_vals['value']['date_due'], 
                'amount_original': move_line_vals['value']['amount_original'], 
                'amount_unreconciled': move_line_vals['value']['amount_unreconciled'],
                'amount': self.pokok, 
                'currency_id': move_line_vals['value']['currency_id'], 
                'type': 'dr', 
                'name': move_line_vals['value']['name'],
                'reconcile': True,
            }]]
            if self.bunga:
                journal_bunga =  branch_config.dym_journal_loan_bunga_reklasifikasi
                if not journal_bunga or not journal_bunga.default_debit_account_id or not journal_bunga.default_credit_account_id:
                    raise osv.except_osv(('Perhatian !'), ("Journal bunga reklasifikasi belum lengkap dalam branch %s !")%(branch_config.branch_id.code))
                created_move = self.action_move_create(journal_bunga, self.bunga, journal_bunga.default_debit_account_id.id, journal_bunga.default_credit_account_id.id)
                for line in created_move.line_id:
                    if line.credit > 0.0:
                        move_line_bunga = line.id
                        if line.account_id.type != 'payable':
                            raise osv.except_osv(('Perhatian !'), ("Account %s harus tipe payable dan allow reconcile!")%(line.account_id.name))
                if not move_line_bunga :
                    raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi %s!")%(self.loan_id.name))
                move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_bunga, self.bunga, False, False)
                voucher_line.append([0,0,{
                    'move_line_id': move_line_vals['value']['move_line_id'], 
                    'account_id': move_line_vals['value']['account_id'], 
                    'date_original': move_line_vals['value']['date_original'], 
                    'date_due': move_line_vals['value']['date_due'], 
                    'amount_original': move_line_vals['value']['amount_original'], 
                    'amount_unreconciled': move_line_vals['value']['amount_unreconciled'],
                    'amount': self.bunga, 
                    'currency_id': move_line_vals['value']['currency_id'], 
                    'type': 'dr', 
                    'name': move_line_vals['value']['name'],
                    'reconcile': True,
                }])
            voucher['type'] = 'payment'
            voucher['line_dr_ids'] = voucher_line
            voucher['line_cr_ids'] = []
        voucher_id = voucher_obj.create(voucher)
        self.write({'voucher_id': voucher_id.id})
        self.loan_id.message_post(body=_("Loan %s <br/>Voucher %s Created <br/>Amount Voucher: %s")%(self.loan_id.name, voucher_id.number, voucher_id.amount))
        return True

    @api.cr_uid_ids_context
    def view_voucher(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        val = self.browse(cr, uid, ids)
        if val.loan_id.loan_type == 'Pinjaman':
            result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'action_vendor_payment')
            id = result and result[1] or False
            result = act_obj.read(cr, uid, [id], context=context)[0]
            res = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')
        elif val.loan_id.loan_type == 'Piutang':
            result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'action_vendor_receipt')
            id = result and result[1] or False
            result = act_obj.read(cr, uid, [id], context=context)[0]
            res = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
        elif val.loan_id.loan_type == 'Reklasifikasi':
            result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'action_vendor_payment')
            id = result and result[1] or False
            result = act_obj.read(cr, uid, [id], context=context)[0]
            res = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = val.voucher_id.id
        return result