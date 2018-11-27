from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class dym_branch_config_alokasi(models.Model):
    _inherit = "dym.branch.config"
    
    dym_mbd_allocation_journal = fields.Many2one('account.journal',string="Journal MBD Allocation")

class dym_voucher_residual_titipan(models.Model):
    _inherit = "account.voucher"

    @api.one
    @api.depends(
        'state',
        'move_id.line_id.account_id.type',
        'move_id.line_id.amount_residual',
        'move_id.line_id.reconcile_id',
        'move_id.line_id.amount_residual_currency',
        'move_id.line_id.currency_id',
        'move_id.line_id.reconcile_partial_id.line_partial_ids',
    )
    def _compute_mbd_allocation_residual(self):
        total_residual = 0
        if self.type == 'receipt' and self.is_hutang_lain != False:
            for line in self.move_ids:
                if line.fake_balance > 0 and line.credit > 0:
                    total_residual += line.fake_balance
        self.residual_titipan = total_residual

    residual_titipan = fields.Float(string='Residual Titipan', digits=dp.get_precision('Account'), readonly=True, compute='_compute_mbd_allocation_residual', method=True, store=True)

class dym_mbd_allocation(models.Model):
    _name = "dym.mbd.allocation"
    _description = "MBD Allocation"

    @api.model
    def _get_default_date(self):
        return self.env['dym.branch'].get_default_date_model()
        
    @api.one
    @api.depends('voucher_id','voucher_id.residual_titipan','state')
    def _compute_total_titipan(self):
        self.total_titipan = self.total_titipan
        if self.state not in ['cancel','done']:
            self.total_titipan = self.voucher_id.residual_titipan

    @api.one
    @api.depends('line_ids.amount')
    def _compute_total_alokasi(self):
        self.total_alokasi = sum(line.amount for line in self.line_ids)

    name = fields.Char('Name')
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('done','Posted'),
        ('cancel','Cancelled'),
        ('reject','Rejected'),
        ], 'State', default='draft')
    date = fields.Date('Entry Date', readonly=True)
    value_date = fields.Date('Transaction Date')
    branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True, domain=[('customer','=',True)])
    # journal_id = fields.Many2one('account.journal', 'Payment Method', required=True, domain="[('type','=','bank'),('branch_id','in',[branch_id,False])]")
    # voucher_id = fields.Many2one('account.voucher', 'Customer Deposit', required=True, domain="[('branch_id','in',[branch_id,False]),('division','=',division),('partner_id','!=',False),('partner_id','=',partner_id),('type','=','receipt'),('is_hutang_lain','!=',False),('residual_titipan','>',0),('state','=','posted')]")
    voucher_id = fields.Many2one('account.voucher', 'Customer Deposit', required=True, domain="[('branch_id','in',[branch_id,False]),('division','=',division),('partner_id','!=',False),('partner_id','=',partner_id),('type','=','receipt'),('is_hutang_lain','!=',False),('residual_titipan','>',0),('state','=','posted')]")

    # clearing_account_id = fields.Many2one(related='journal_id.clearing_account_id')

    # move_line_ids = fields.Many2many('account.move.line','dym_mbd_allocation_move_line_rel','clearing_id','move_line_id','Move Line', domain="[('move_id.journal_id','=',journal_id),('account_id','=',clearing_account_id),('partner_id','=',partner_id),('division','=',division),('branch_id','=',branch_id),('clear_state','=','open'),('credit','>',0),('ref','=?',ref)]")
    total_titipan = fields.Float(string='Total O/S Customer Deposit', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_titipan')
    total_alokasi = fields.Float(string='Total Alokasi', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_alokasi')
    line_ids = fields.One2many('dym.mbd.allocation.line', 'alokasi_id', 'Detail MBD Allocation')
    titipan_move = fields.Many2one(related='voucher_id.move_id')
    move_id = fields.Many2one('account.move', 'Journal', readonly=True)
    move_ids = fields.One2many(related='move_id.line_id', readonly=True)
    memo = fields.Char('Memo')
    
    _defaults={
        'date' : _get_default_date,
        'value_date' : _get_default_date,
        'state':'draft',
    }

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'MBD', division='Umum')
        return super(dym_mbd_allocation, self).create(cr, uid, vals, context=context)

    @api.onchange('division','partner_id','branch_id')
    def fields_change(self):
        self.voucher_id = False
        self.total_titipan = 0

    @api.onchange('voucher_id')
    def voucher_change(self):
        self.total_titipan = self.voucher_id.residual_titipan
        self.titipan_move = self.voucher_id.move_id

    @api.multi
    def wkf_action_cancel(self):        
        self.write({'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
    
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.state not in ['draft','cancel']:
            raise osv.except_osv(('Invalid action !'), ('Cannot delete this document which is in state \'%s\'!') % (val.state))
        return super(dym_mbd_allocation, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def confirm_alokasi(self):
        total_amount_alokasi = sum(line.amount for line in self.line_ids)
        if total_amount_alokasi <= 0 :
            raise osv.except_osv(('Tidak bisa confirm!'), ('Amount alokasi harus lebih besar dari 0'))
        if not self.line_ids:
            raise osv.except_osv(('Tidak bisa confirm!'), ('Detail MBD Allocation harus diisi'))
        if self.total_titipan < total_amount_alokasi:
            raise osv.except_osv(('Tidak bisa confirm!'), ('Total titipan [%s] lebih kecil dari total amount yang dialokasikan [%s]!')%(self.total_titipan, total_amount_alokasi))

        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        period_ids = self.env['account.period'].find()        
        branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if not branch_config :
            raise osv.except_osv(('Perhatian !'), ("Belum ada branch config atas branch %s !")%(branch_config.branch_id.code))
        journal_alokasi =  branch_config.dym_mbd_allocation_journal
        if not journal_alokasi:
            raise osv.except_osv(('Perhatian !'), ("Journal alokasi customer deposit belum lengkap dalam branch %s !")%(branch_config.branch_id.name))
        move_journal = {
            'name': self.name,
            'ref': self.memo,
            'journal_id': journal_alokasi.id,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'period_id':period_ids.id,
            'transaction_id':self.id,
            'model':self.__class__.__name__,
        }
        create_journal = move_obj.create(move_journal)
        titipan_line_list = []
        titipan_line_dict = {}
        for line in self.line_ids:
            if line.titipan_line_id not in titipan_line_list:
                titipan_line_list.append(line.titipan_line_id)
                titipan_line_dict[line.titipan_line_id] = {'amount':0}
            titipan_line_dict[line.titipan_line_id]['amount'] += line.amount
            created_move_line = move_line_obj.create({
                'name': _('MBD Allocation ' + self.name),
                'ref': _(line.description),
                'partner_id': line.partner_id.id,
                'account_id': line.titipan_line_id.account_id.id,
                'period_id':period_ids.id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'debit': 0.0,
                'credit': line.amount,
                'branch_id': line.branch_id.id,
                'division': line.division,
                'analytic_account_id' : line.titipan_line_id.analytic_account_id.id ,
                'move_id': create_journal.id
            })
            line.write({'move_line_id':created_move_line.id})
            
        titipan_line_ids = []
        for titipan_line in titipan_line_list:
            allocated_amount = titipan_line_dict[titipan_line]['amount']
            if allocated_amount > titipan_line.fake_balance:
                raise osv.except_osv(('Tidak bisa confirm!'), ("Total Customer Deposit [%s] untuk titipan %s lebih besar dari balance yang bisa dialokasikan [%s]")%(allocated_amount, titipan_line.name, titipan_line.fake_balance))
            created_move_line = move_line_obj.create({
                'name': _('Customer Deposit ' + titipan_line.name),
                'ref': _(self.name),
                'partner_id': titipan_line.partner_id.id,
                'account_id': titipan_line.account_id.id,
                'period_id':period_ids.id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'debit': allocated_amount,
                'credit': 0.0,
                'branch_id': titipan_line.branch_id.id,
                'division': titipan_line.division,
                'analytic_account_id' : titipan_line.analytic_account_id.id,
                'move_id': create_journal.id
            })
            if titipan_line.id not in titipan_line_ids:
                titipan_line_ids.append(titipan_line.id)
            titipan_line_ids.append(created_move_line.id)
        if titipan_line_ids:
            titipan_lines = move_line_obj.browse(titipan_line_ids)
            reconcile_id = titipan_lines.reconcile_partial('auto')
        
        if create_journal.journal_id.entry_posted:
            post_journal = create_journal.post()
        self.write({'state':'done','move_id':create_journal.id,'confirm_uid':self._uid,'confirm_date':datetime.now()})
        return True

class dym_mbd_allocation_line(models.Model):
    _name = "dym.mbd.allocation.line"
    _description = "MBD Allocation Line"

    @api.one
    @api.depends('alokasi_id.state')
    def _compute_state(self):
        self.state = self.alokasi_id.state

    lot_id = fields.Many2one('stock.production.lot', 'Engine Number')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Allocate to Division', required=True, default='Unit')
    branch_id = fields.Many2one('dym.branch', 'Allocate to Branch')
    alokasi_id = fields.Many2one('dym.mbd.allocation', 'MBD Allocation')
    titipan_line_id = fields.Many2one('account.move.line', 'Journal Item', required=True)
    open_balance = fields.Float('Open Balance')
    open_balance_show = fields.Float(related='open_balance')
    partner_id = fields.Many2one('res.partner', 'Ke Partner', required=True, domain=[('customer','=',True)])
    description = fields.Char('Description')
    amount = fields.Float('Amount', required=True)
    move_line_id = fields.Many2one('account.move.line', 'Move Line')
    voucher_id = fields.Many2one('account.voucher', 'RV No.', readonly=True, copy=False)
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('done','Posted'),
        ('cancel','Cancelled'),
        ('reject','Rejected'),
    ], 'State', compute='_compute_state')

    @api.constrains('titipan_line_id','alokasi_id','partner_id','amount')
    def _constraint_move_line(self):
        line_search =  self.search([('titipan_line_id','=',self.titipan_line_id.id),('id','!=',self.id),('alokasi_id','=',self.alokasi_id.id),('partner_id','=',self.partner_id.id)])
        if line_search:
            raise ValidationError("Kombinasi journal item " + self.titipan_line_id.move_id.name + " partner ke " + self.partner_id.name + " duplicate!")
        if self.amount < 0:
            raise ValidationError("Nilai amount harus lebih besar dari 0!")

    @api.onchange('titipan_line_id')
    def move_line_id_change(self):
        if not self.alokasi_id.branch_id or not self.alokasi_id.voucher_id or not self.alokasi_id.division or not self.alokasi_id.partner_id:
            raise osv.except_osv(('Tidak bisa menambah data!'), ('Mohon lengkapi data header terlebih dahulu'))
        self.open_balance = self.titipan_line_id.fake_balance or 0
        self.open_balance_show = self.titipan_line_id.fake_balance or 0

    @api.onchange('lot_id')
    def lot_change(self):
        if not self.alokasi_id.branch_id or not self.alokasi_id.voucher_id or not self.alokasi_id.division or not self.alokasi_id.partner_id:
            raise osv.except_osv(('Tidak bisa menambah data!'), ('Mohon lengkapi data header terlebih dahulu'))
        if self.lot_id:
            self.partner_id = self.lot_id.customer_id.id or False
            self.branch_id = self.lot_id.branch_id.id or False

    @api.multi
    def create_voucher(self):    
        move_line_id = self.move_line_id
        if not self.move_line_id:
            move_line_id = self.env['account.move.line'].search([('move_id','=', self.alokasi_id.move_id.id),('partner_id','=', self.partner_id.id),('account_id','=', self.titipan_line_id.account_id.id),('credit','=', self.amount),('reconcile_id','=', False)], limit=1)
            self.write({'move_line_id':move_line_id.id})
        if not move_line_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi %s, titipan!")%(self.alokasi_id.name, self.description))
        amount = self.amount if move_line_id.fake_balance >= self.amount else move_line_id.fake_balance
        move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_id.id, amount, False, False)
        voucher_line = [[0,0,{
            'move_line_id': move_line_vals['value']['move_line_id'], 
            'account_id': move_line_vals['value']['account_id'], 
            'date_original': move_line_vals['value']['date_original'], 
            'date_due': move_line_vals['value']['date_due'], 
            'amount_original': move_line_vals['value']['amount_original'], 
            'amount_unreconciled': move_line_vals['value']['amount_unreconciled'],
            'amount': amount, 
            'currency_id': move_line_vals['value']['currency_id'], 
            'type': 'dr', 
            'name': move_line_vals['value']['name'],
            'reconcile': True,
        }]]

        analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.branch_id, 'Umum',False, 4, 'General')

        voucher = {
            'branch_id':self.branch_id.id, 
            'division': self.division, 
            'inter_branch_id':self.branch_id.id, 
            'partner_id': self.partner_id.id, 
            'date':datetime.now().strftime('%Y-%m-%d'), 
            'amount': 0, 
            'reference': self.alokasi_id.name, 
            'name': self.alokasi_id.memo, 
            'user_id': self._uid,
            'type': 'receipt',
            'line_dr_ids': voucher_line,
            'line_cr_ids': [],
            'analytic_1': analytic_1,
            'analytic_2': analytic_2,
            'analytic_3': analytic_3,
            'analytic_4': analytic_4,
        }        
        voucher_obj = self.env['account.voucher']
        voucher_id = voucher_obj.create(voucher)
        self.write({'voucher_id': voucher_id.id})
        # self.loan_id.message_post(body=_("Loan %s <br/>Voucher %s Created <br/>Amount Voucher: %s")%(self.loan_id.name, voucher_id.number, voucher_id.amount))
        return True

    @api.cr_uid_ids_context
    def view_voucher(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        val = self.browse(cr, uid, ids)
        result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'action_vendor_receipt')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = val.voucher_id.id
        return result