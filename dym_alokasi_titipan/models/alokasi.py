import logging
from openerp import models, fields, api, _, SUPERUSER_ID, workflow
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
_logger = logging.getLogger(__name__)

class dym_branch_config_alokasi(models.Model):
    _inherit = "dym.branch.config"
    
    dym_journal_alokasi_customer_deposit = fields.Many2one('account.journal',string="Journal Alokasi Customer Deposit")
    # Tambahan
    dym_journal_selisih_alokasi_cde = fields.Many2one('account.journal', string="Journal Selisih Alokasi Customer Deposit")

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
    def _compute_residual_titipan(self):
        total_residual = 0
        if self.type == 'receipt' and self.is_hutang_lain != False:
            for line in self.move_ids:
                if line.fake_balance > 0 and line.credit > 0:
                    total_residual += line.fake_balance
        self.residual_titipan = total_residual

    residual_titipan = fields.Float(string='Residual Titipan', digits=dp.get_precision('Account'), readonly=True, compute='_compute_residual_titipan', method=True, store=True)
    alokasi_cd = fields.Boolean('Alokasi CD')
    voucher_ref_id = fields.Many2one('account.voucher','CDE Ref.', readonly=True)
    alokasi_id = fields.Many2one('dym.alokasi.titipan','Alokasi CDE',readonly=True)

class dym_alokasi_titipan(models.Model):
    _name = "dym.alokasi.titipan"
    _description = "Alokasi Customer Deposit"
    _order = "name desc"


    @api.one
    def action_reset_draft(self):
        self.state = 'draft'

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
        if not self.force_alocate:
            self.total_alokasi = sum(line.amount for line in self.line_ids if line.lot_id.name not in str(line.alokasi_id.log_import))
        else:
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
    voucher_id = fields.Many2one('account.voucher', 'Customer Deposit', required=True, domain="[('branch_id','in',[branch_id,False]),('division','=',division),('partner_id','!=',False),('partner_id','=',partner_id),('type','=','receipt'),('is_hutang_lain','!=',False),('residual_titipan','>',0),('state','=','posted')]")
    total_titipan = fields.Float(string='Total O/S Customer Deposit', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_titipan')
    total_alokasi = fields.Float(string='Total Alokasi', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_alokasi')
    line_ids = fields.One2many('dym.alokasi.titipan.line', 'alokasi_id', 'Detail Alokasi Customer Deposit')
    titipan_move = fields.Many2one(related='voucher_id.move_id')
    move_id = fields.Many2one('account.move', 'Journal', readonly=True)
    move_ids = fields.One2many(related='move_id.line_id', readonly=True)
    memo = fields.Char('Memo')
    log_import = fields.Text('Log Import', readonly = True)
    force_alocate = fields.Boolean('Force Alocate')
    
    _defaults={
        'date' : _get_default_date,
        'value_date' : _get_default_date,
        'state':'draft',
    }

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'ACD', division='Umum')
        return super(dym_alokasi_titipan, self).create(cr, uid, vals, context=context)

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
        return super(dym_alokasi_titipan, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def confirm_alokasi(self):
        #Tambahan
        if not self.force_alocate:
            total_amount_alokasi = sum(line.amount for line in self.line_ids if line.lot_id.name not in str(line.alokasi_id.log_import))
        else:
            total_amount_alokasi = sum(line.amount for line in self.line_ids)
        
        if total_amount_alokasi <= 0 :
            raise osv.except_osv(('Tidak bisa confirm!'), ('Amount alokasi harus lebih besar dari 0'))
        if not self.line_ids:
            raise osv.except_osv(('Tidak bisa confirm!'), ('Detail Alokasi Customer Deposit harus diisi'))
        if self.total_titipan < total_amount_alokasi:
            raise osv.except_osv(('Tidak bisa confirm!'), ('Total titipan [%s] lebih kecil dari total amount yang dialokasikan [%s]!')%(self.total_titipan, total_amount_alokasi))

        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        period_ids = self.env['account.period'].find()        
        branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if not branch_config :
            raise osv.except_osv(('Perhatian !'), ("Belum ada branch config atas branch %s !")%(branch_config.branch_id.code))
        journal_alokasi =  branch_config.dym_journal_alokasi_customer_deposit
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
            _logger.warn(
                _('Processing Alokasi Titipan %s' % line.id)
            )

            #Tambahan
            if line.lot_id.name not in str(self.log_import) or self.force_alocate:
                if line.titipan_line_id not in titipan_line_list:
                    titipan_line_list.append(line.titipan_line_id)
                    titipan_line_dict[line.titipan_line_id] = {'amount':0}
                titipan_line_dict[line.titipan_line_id]['amount'] += line.amount
                created_move_line = move_line_obj.create({
                    'name': _('Alokasi Customer Deposit ' + self.name),
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

        #Tambahan
        for line in self.line_ids:
            line.create_voucher()

        return True

class dym_alokasi_titipan_line(models.Model):
    _name = "dym.alokasi.titipan.line"
    _description = "Alokasi Custemer Deposit Line"

    @api.one
    @api.depends('alokasi_id.state')
    def _compute_state(self):
        self.state = self.alokasi_id.state

    lot_id = fields.Many2one('stock.production.lot', 'Engine Number')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Allocate to Division', required=True, default='Unit')
    branch_id = fields.Many2one('dym.branch', 'Allocate to Branch')
    alokasi_id = fields.Many2one('dym.alokasi.titipan', 'Alokasi Customer Deposit')
    titipan_line_id = fields.Many2one('account.move.line', 'Journal Item', required=True)
    open_balance = fields.Float('Open Balance')
    open_balance_show = fields.Float(related='open_balance')
    partner_id = fields.Many2one('res.partner', 'Ke Partner', required=True, domain=[('customer','=',True)])
    description = fields.Char('Description')
    amount = fields.Float('Amount', required=True)
    move_line_id = fields.Many2one('account.move.line', 'Move Line')
    voucher_id = fields.Many2one('account.voucher', 'RV No.', readonly=True, copy=False)
    voucher_cde_id = fields.Many2one('account.voucher', 'New CDE', readonly=True, copy=False)
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
            if not self.alokasi_id.force_alocate:
                if self.lot_id.name in self.alokasi_id.log_import:
                    return True
            else:
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi %s %s, titipan!")%(self.alokasi_id.name, self.description))
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

        branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)], limit =1)
        move_line_ar = self.env['account.move.line'].search([('account_id','=', branch_config.dealer_so_journal_pelunasan_id.default_debit_account_id.id),('partner_id','=',self.partner_id.id),('ref','=',self.lot_id.dealer_sale_order_id.name),('reconcile_id','=', False)])
        amount_ar = move_line_ar.debit if move_line_ar.fake_balance >= move_line_ar.debit else move_line_ar.fake_balance
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
                    'amount': amount, 
                    'currency_id': move_line_ar_vals['value']['currency_id'], 
                    'type': 'cr', 
                    'name': move_line_ar_vals['value']['name'],
                    'reconcile': True if amount == amount_ar else (False if amount < amount_ar else True),
                       }]]
            else:
                if not self.alokasi_id.force_alocate:
                    return True
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
                    'reconcile': True if amount == amount_ar else (False if amount < amount_ar else True),
                       }]]

                    if amount_ar < amount:
                        voucher_line[0][2]['amount'] = move_line_ar.debit
                    elif amount_ar > amount:
                        voucher_cr_line[0][2]['amount'] = amount                                 
        else:
            invoice = self.env['account.invoice'].search([('origin','=',self.lot_id.dealer_sale_order_id.name)], limit =1)
            cpa_line = ', '.join([x.move_id.name for x in invoice.payment_ids])
            if invoice.state == 'paid':
                raise osv.except_osv(('Perhatian!'), ('AR untuk Engine No. %s (%s) sudah dibayar di transaksi %s') % (self.lot_id.name,self.partner_id.name_get()[0][1],cpa_line))
        journal_alokasi = branch_config.dym_journal_alokasi_customer_deposit
        if not journal_alokasi:
            raise osv.except_osv(('Perhatian !'), ("Journal alokasi customer deposit belum lengkap dalam branch %s !")%(branch_config.branch_id.name))
        analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.branch_id, 'Umum',False, 4, 'General')
        voucher = {
            'branch_id':self.branch_id.id, 
            'division': self.division, 
            'inter_branch_id':self.branch_id.id, 
            'inter_branch_division': self.division, 
            'partner_id': self.partner_id.id, 
            'date':datetime.now().strftime('%Y-%m-%d'), 
            'amount': 0, 
            'reference': self.alokasi_id.name, 
            'name': self.alokasi_id.memo, 
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
            'alokasi_cd': True,
        }        
        
        voucher_obj = self.env['account.voucher']
        voucher_id = voucher_obj.create(voucher)
        self.write({'voucher_id': voucher_id.id})

        voucher_id.validate_or_rfa_credit()
        voucher_id.signal_workflow('approval_approve')

        if amount > amount_ar :
            analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.alokasi_id.branch_id, 'Umum',False, 4, 'General')
            if not branch_config.dym_journal_selisih_alokasi_cde:
                raise osv.except_osv(('Perhatian !'), ("Mohon lengkapi Journal selisih alokasi customer deposit branch %s !")%(branch_config.branch_id.name))  
            else:
                diff = amount - amount_ar 
                new_cde_line = [[0,0,{
                    'account_id': branch_config.dym_journal_selisih_alokasi_cde.default_credit_account_id.id, 
                    'name': 'Selisih kelebihan bayar transaksi %s' % voucher_id.name, 
                    'analytic_2': analytic_2, 
                    'analytic_3': analytic_3,
                    'account_analytic_id': analytic_4,
                    'amount': diff, 
                }]]
                new_cde = {
                    'company_id':self.alokasi_id.voucher_id.company_id.id,
                    'branch_id':self.alokasi_id.voucher_id.branch_id.id, 
                    'division': self.alokasi_id.voucher_id.division, 
                    'partner_id': self.alokasi_id.voucher_id.partner_id.id, 
                    'date':datetime.now().strftime('%Y-%m-%d'), 
                    'amount': diff, 
                    'reference': self.alokasi_id.name, 
                    'name': self.alokasi_id.voucher_id.name, 
                    'user_id': self._uid,
                    'type': self.alokasi_id.voucher_id.type,
                    'line_dr_ids': False,
                    'line_cr_ids': new_cde_line,
                    'analytic_1': self.alokasi_id.voucher_id.analytic_1.id,
                    'analytic_2': self.alokasi_id.voucher_id.analytic_2.id,
                    'analytic_3': self.alokasi_id.voucher_id.analytic_3.id,
                    'analytic_4': self.alokasi_id.voucher_id.analytic_4.id,
                    'journal_id': journal_alokasi.id,
                    'account_id': branch_config.dym_journal_selisih_alokasi_cde.default_debit_account_id.id,
                    'alokasi_id': self.alokasi_id.id,
                    'voucher_ref_id': self.alokasi_id.voucher_id.id,
                    'is_hutang_lain': True,
                    'paid_amount': diff,
                }  
                voucher_obj = self.env['account.voucher']
                new_cde_id = voucher_obj.create(new_cde)
                self.write({'voucher_cde_id': new_cde_id.id})
                new_cde_id.validate_or_rfa_credit()
                new_cde_id.signal_workflow('approval_approve')
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

    @api.cr_uid_ids_context
    def view_voucher_cde(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        val = self.browse(cr, uid, ids)
        result = mod_obj.get_object_reference(cr, uid, 'dym_account_voucher', 'action_other_payable')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'dym_account_voucher', 'view_other_payable_form')
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = val.voucher_cde_id.id
        return result