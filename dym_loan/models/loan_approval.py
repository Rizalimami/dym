from openerp.osv import osv
from openerp import models, fields, api
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import netsvc

class dym_account_move_line(models.Model):
    _inherit = "account.move.line"
    
    dym_loan_id = fields.Many2one('dym.loan', "Loan")

class dym_loan_approval(models.Model):
    _inherit = 'dym.loan'
    
    approval_ids = fields.One2many('dym.approval.line', 'transaction_id', string="Table Approval", domain=[('form_id','=',_inherit)])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Reject')
    ], 'Approval State', readonly=True, default='b')
    confirm_uid = fields.Many2one('res.users',string="Approved by")
    confirm_date = fields.Datetime('Approved on')
    confirm2_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm2_date = fields.Datetime('Confirmed on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')    
        
    @api.multi
    def wkf_request_approval(self):
        total_loan = 0
        if self.jumlah_loan <= 0 :
            raise osv.except_osv(('Perhatian !'), ("Jumlah Loan harus lebih besar dari 0!"))
        if not self.loan_line:
            raise exceptions.ValidationError(("Silahkan genearte detil loan terlebih dahulu"))
        obj_matrix = self.env['dym.approval.matrixbiaya']
        obj_matrix.request_by_value(self,self.jumlah_loan)
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
        self.message_post(body=_("Loan %s - Request Approval <br/>Amount Loan: %s")%(self.name, self.jumlah_loan))
        return True
    
    @api.multi
    def action_move_create(self, journal, jumlah, account_debit, account_credit):
        #create_move
        move_obj = self.env['account.move']
        inv_text = ''
        effective_date = self.effective_date if self.effective_date >= str(datetime.today().date()) else self.date
        if self.loan_type == 'Reklasifikasi' and self.invoice_ids:
            inv_text = '[' + ', '.join(self.invoice_ids.mapped('supplier_invoice_number')) + ']'
            effective_date = self.effective_date
        period_ids = self.env['account.period'].find(dt=effective_date)
        move_journal = {
            'name': self.name,
            'ref': inv_text,
            'journal_id': journal.id,
            'date': effective_date,
            'period_id':period_ids.id,
            'transaction_id':self.id,
            'model':self.__class__.__name__,
        }

        analytic_1,analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(self._cr, self._uid, self.branch_id, 'Umum',False, 4, 'General')
        move_line = [[0,False,{
            'name': _(self.name),
            'ref': _(inv_text),
            'partner_id': self.partner_id.id,
            'account_id': account_credit,
            'period_id':period_ids.id,
            'date': effective_date,
            'debit': 0.0,
            'credit': jumlah,
            'branch_id': self.branch_id.id,
            'division': self.division,
            'date_maturity': self.first_due_date,
            'dym_loan_id': self.id,
            'analytic_1': analytic_1,
            'analytic_2': analytic_2,
            'analytic_3': analytic_3,
            'analytic_account_id': analytic_4,
        }]]
        if self.loan_type == 'Reklasifikasi':
            move_line_obj = self.env['account.move.line']
            for inv in self.invoice_ids:
                move_line_id = move_line_obj.search([
                    ('move_id','=',inv.move_id.id),
                    ('credit','!=',0),
                    ('account_id.type','=','payable'),
                    ('reconcile_id','!=',False),
                ])
                if not move_line_id:
                    move_line_id = move_line_obj.search([
                        ('move_id','=',inv.move_id.id),
                        ('credit','!=',0),
                        ('account_id.type','=','payable'),
                        ('reconcile_id','=',False),
                    ])
                move_line.append([0,False,{
                    'name': _(self.name),
                    'ref': _(inv.supplier_invoice_number),
                    'partner_id': inv.partner_id.id,
                    'account_id': inv.account_id.id,
                    'period_id':period_ids.id,
                    'date': effective_date,
                    'debit': move_line_id.fake_balance,
                    'credit': 0.0,
                    'branch_id': move_line_id.branch_id.id,
                    'division': move_line_id.division,
                    'date_maturity': self.first_due_date,
                    'dym_loan_id': self.id,
                    'analytic_account_id' : move_line_id.analytic_4.id 
                }])
        else:
            move_line.append([0,False,{
                'name': _(self.name),
                'partner_id': self.partner_id.id,
                'account_id': account_debit,
                'period_id':period_ids.id,
                'date': effective_date,
                'debit': jumlah,
                'credit': 0.0,
                'branch_id': self.branch_id.id,
                'division': self.division,
                'date_maturity': self.first_due_date,
                'dym_loan_id': self.id,
                'analytic_account_id' : self.analytic_4.id 
            }])

        move_journal['line_id'] = move_line
        create_journal = move_obj.create(move_journal)
        if journal.entry_posted:
            post_journal = create_journal.post()
        return create_journal

    @api.multi
    def confirm_loan(self):
        branch_id = self.branch_id.id
        branch_config = self.env['dym.branch.config'].search([('branch_id','=',branch_id)])
        if not branch_config :
            raise osv.except_osv(('Perhatian !'), ("Belum ada branch config atas branch %s !")%(branch_config.branch_id.code))
        if self.loan_type == 'Pinjaman':
            journal_pinjaman = False
            if self.tipe_pinjaman == 'panjang':
                journal_pinjaman =  branch_config.dym_journal_loan_pinjaman
            elif self.tipe_pinjaman == 'pendek':
                journal_pinjaman =  branch_config.dym_journal_loan_pinjaman_pendek
            elif self.tipe_pinjaman == 'intercompany':
                journal_pinjaman =  branch_config.dym_journal_loan_pinjaman_intercompany
            if not journal_pinjaman:
                raise osv.except_osv(('Perhatian !'), ("Journal pinjaman belum lengkap dalam branch %s !")%(branch_config.branch_id.code))
            account_debit = self.account_id.id
            account_credit = journal_pinjaman.default_credit_account_id.id
            if  not account_credit:
                raise osv.except_osv(('Perhatian !'), ("Data account default credit di journal %s belum di set!")%(journal_pinjaman.sudo().name))
            if not account_debit:
                raise osv.except_osv(('Perhatian !'), ("Data account pengakuan belum di set!")%(self.account_id.name))
            created_move = self.action_move_create(journal_pinjaman, self.jumlah_loan, account_debit, account_credit)
            self.message_post(body=_("Loan Pinjaman %s - Confirmed <br/>Amount Loan: %s")%(self.name, self.jumlah_loan))
        elif self.loan_type == 'Piutang':
            journal_piutang =  branch_config.dym_journal_loan_piutang
            if not journal_piutang:
                raise osv.except_osv(('Perhatian !'), ("Journal Piutang belum lengkap dalam branch %s !")%(branch_config.branch_id.code))  
            account_debit = journal_piutang.default_debit_account_id.id
            account_credit = self.account_id.id
            if not account_debit:
                raise osv.except_osv(('Perhatian !'), ("Data account default debit di journal %s belum di set!")%(journal_piutang.sudo().name))
            if not account_credit:
                raise osv.except_osv(('Perhatian !'), ("Data account pengakuan belum di set!")%(journal_piutang.sudo().name))
            created_move = self.action_move_create(journal_piutang, self.jumlah_loan, account_debit, account_credit)
            self.message_post(body=_("Loan Piutang %s - Confirmed <br/>Amount Loan: %s")%(self.name, self.jumlah_loan))
        elif self.loan_type == 'Reklasifikasi':
            journal_reklasifikasi =  branch_config.dym_journal_loan_reklasifikasi
            if not journal_reklasifikasi:
                raise osv.except_osv(('Perhatian !'), ("Journal Reklasifikasi belum lengkap dalam branch %s !")%(branch_config.branch_id.code))  
            account_debit = journal_reklasifikasi.default_debit_account_id.id
            account_credit = journal_reklasifikasi.default_credit_account_id.id
            if not account_credit:
                raise osv.except_osv(('Perhatian !'), ("Data account default credit di journal %s belum di set!")%(journal_reklasifikasi.sudo().name))
            created_move = self.action_move_create(journal_reklasifikasi, self.jumlah_loan, False, account_credit)
            for line in created_move.line_id:
                if line.debit > 0.0:
                    move_line_id = line.id
                    for inv_move_line in self.move_line_ids:
                        if line.debit == inv_move_line.credit and not inv_move_line.reconcile_id and not line.reconcile_id:
                            reconcile_id = self.pool.get('account.move.line').reconcile_partial(self._cr,self._uid, [move_line_id, inv_move_line.id], 'auto')
            self.message_post(body=_("Loan Reklasifikasi %s - Confirmed <br/>Amount Loan: %s")%(self.name, self.jumlah_loan))
        self.write({'confirm2_uid':self._uid,'confirm2_date':datetime.now(),'state':'confirmed'})
        return True

    @api.multi
    def create_voucher(self):
        voucher_obj = self.env['account.voucher']
        voucher = {
            'branch_id':self.branch_id.id, 
            'division': self.division, 
            'inter_branch_id':self.branch_id.id, 
            'inter_branch_division':self.division, 
            'partner_id': self.partner_id.id, 
            'date':datetime.now().strftime('%Y-%m-%d'), 
            'amount': self.jumlah_loan, 
            # 'pay_now': 'pay_now', 
            'date_due_payment': self.first_due_date, 
            'reference': self.name, 
            'name': self.memo, 
            'user_id': self.user_id.id,
            'journal_id': self.journal_id.id, 
        }

        if self.loan_type == 'Pinjaman':
            move_line_id = self.env['account.move.line'].search([
                ('dym_loan_id','=',self.id),
                ('debit','>',0)
            ], limit=1)
            if not move_line_id :
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi %s!")%(self.name))
            move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_id.id, self.jumlah_loan, False, False)
            voucher_line = [0,0,{
                'move_line_id': move_line_vals['value']['move_line_id'], 
                'account_id': move_line_vals['value']['account_id'], 
                'date_original': move_line_vals['value']['date_original'], 
                'date_due': move_line_vals['value']['date_due'], 
                'amount_original': move_line_vals['value']['amount_original'], 
                'amount_unreconciled': move_line_vals['value']['amount_unreconciled'],
                'amount': self.jumlah_loan, 
                'currency_id': move_line_vals['value']['currency_id'], 
                'type': 'cr', 
                'name': move_line_vals['value']['name'],
                'reconcile': True,
            }]
            voucher['type'] = 'receipt'
            voucher['line_dr_ids'] = [voucher_line]
            voucher['line_cr_ids'] = []
            voucher_id = voucher_obj.create(voucher)
            self.write({'voucher_id': voucher_id.id})
            self.message_post(body=_("Loan Pinjaman %s - Voucher Created <br/>Amount Loan: %s")%(self.name, self.jumlah_loan))
        elif self.loan_type == 'Piutang':
            move_line_id = self.env['account.move.line'].search([
                ('dym_loan_id','=',self.id),
                ('credit','>',0)
            ], limit=1)
            if not move_line_id :
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi %s!")%(self.name))
            move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_id.id, self.jumlah_loan, False, False)
            voucher_line = [0,0,{
                'move_line_id': move_line_vals['value']['move_line_id'], 
                'account_id': move_line_vals['value']['account_id'], 
                'date_original': move_line_vals['value']['date_original'], 
                'date_due': move_line_vals['value']['date_due'], 
                'amount_original': move_line_vals['value']['amount_original'], 
                'amount_unreconciled': move_line_vals['value']['amount_unreconciled'],
                'amount': self.jumlah_loan, 
                'currency_id': move_line_vals['value']['currency_id'], 
                'type': 'dr', 
                'name': move_line_vals['value']['name'],
                'reconcile': True,
            }]
            voucher['type'] = 'payment'
            voucher['line_cr_ids'] = [voucher_line]
            voucher['line_dr_ids'] = []
            voucher_id = voucher_obj.create(voucher)
            self.write({'voucher_id': voucher_id.id})
            self.message_post(body=_("Loan Piutang %s - Voucher Created <br/>Amount Loan: %s")%(self.name, self.jumlah_loan))
        return voucher_id

    @api.multi
    def wkf_approval(self):
        approval_sts = self.env['dym.approval.matrixbiaya'].approve(self)
        if approval_sts == 1 :
            self.write({'approval_state':'a', 'state':'approved','confirm_uid':self._uid,'confirm_date':datetime.now()})
        elif approval_sts == 0 :
            raise exceptions.ValidationError( ("User tidak termasuk group approval"))
        else:
            return True        
            self.message_post(body=_("Loan %s - Approved <br/>Amount Loan: %s")%(self.name, self.jumlah_loan))
        return True

    def convert_thousand_separator(self,num):
        res = "{:,}".format(int(num))
        return res
    
    @api.cr_uid_ids_context
    def view_voucher(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = {}
        val = self.browse(cr, uid, ids)
        if not val.confirm2_date:
            raise osv.except_osv(('Perhatian !'), ("Belum bisa melakukan pencairan! Mohon confirm loan terlebih dahulu!"))
        confirm_date = datetime.strptime(val.confirm2_date, "%Y-%m-%d %H:%M:%S").date()
        effective_date = val.effective_date if val.effective_date >= str(confirm_date) else str(confirm_date)
        res = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
        
        if val.loan_type == 'Pinjaman':
            if val.effective_date > str(datetime.today().date()):
                raise osv.except_osv(('Perhatian !'), ("Belum bisa melakukan pencairan! Tanggal efektif loan %s adalah %s!")%(val.name, val.effective_date))
            if not val.voucher_id:
                voucher = val.create_voucher()
            if val.voucher_id.date < effective_date:
                val.voucher_id.write({'date':effective_date})
            result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'action_vendor_receipt')
            id = result and result[1] or False
            result = act_obj.read(cr, uid, [id], context=context)[0]
            res = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
        elif val.loan_type == 'Piutang':
            if val.effective_date > str(datetime.today().date()):
                raise osv.except_osv(('Perhatian !'), ("Belum bisa melakukan pencairan! Tanggal efektif loan %s adalah %s!")%(val.name, val.effective_date))
            if not val.voucher_id:
                voucher = val.create_voucher()
            if val.voucher_id.date < effective_date:
                val.voucher_id.write({'date':effective_date})
            result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'action_vendor_payment')
            id = result and result[1] or False
            result = act_obj.read(cr, uid, [id], context=context)[0]
            res = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')

        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = val.voucher_id.id
        return result

    @api.multi
    def has_approved(self):
        if self.approval_state == 'a':
            return True
        return False
    
    @api.multi
    def has_rejected(self):
        if self.approval_state == 'r':
            self.write({'state':'draft'})
            return True
        return False
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})
