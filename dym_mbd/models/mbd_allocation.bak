import json
from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

VOUCHER_STATE_SELECTION = [
    ('draft','Draft'),
    ('waiting_for_approval','Waiting Approval'),
    ('confirmed', 'Waiting Approval'),
    ('request_approval','RFA'), 
    ('approved','Approve'), 
    ('cancel','Cancelled'),
    ('proforma','Pro-forma'),
    ('posted','Posted')
]

class dym_account_move_line(models.Model):
    _inherit = "account.move.line"
    
    mbd_line_ids = fields.One2many('dym.mbd.allocation.line', 'titipan_line_id', string="Journal MBD Allocation")


class dym_branch_config_alokasi(models.Model):
    _inherit = "dym.branch.config"
    
    dym_mbd_allocation_journal = fields.Many2one('account.journal',string="Journal MBD Allocation")
    dym_mbd_income_account = fields.Many2one('account.account',string="Income Account")

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

    @api.model
    def _get_default_transaction_date(self):
        today = date.today()
        return today.replace(day=1) - timedelta(days=1)
        
    @api.one
    @api.depends('state')
    def _compute_total_titipan(self):
        self.total_titipan = self.total_titipan
        # if self.state not in ['cancel','done']:
        #     self.total_titipan = self.voucher_id.residual_titipan

    @api.one
    @api.depends('line_ids.amount')
    def _compute_total_alokasi(self):
        self.total_alokasi = sum(line.amount for line in self.line_ids)

    @api.one
    @api.depends('line_ids.tax_base')
    def _compute_total_dpp(self):
        self.total_dpp = sum(line.tax_base for line in self.line_ids)

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
    value_date = fields.Date('Transaction Date', default=_get_default_transaction_date)
    branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=True)
    inter_branch_id = fields.Many2one('dym.branch', 'Branch', required=False)
    inter_division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=False)    
    partner_id = fields.Many2one('res.partner', 'Partner', required=True, domain=[('customer','=',True)])
    partner_cabang_id = fields.Many2one('dym.cabang.partner', string='Cabang Partner')
    journal_id = fields.Many2one('account.journal', 'Journal', required=True)
    voucher_id = fields.Many2one('account.voucher', 'Receivable Voucher', required=False, domain="[('branch_id','in',[branch_id,False]),('division','=',division),('partner_id','!=',False),('partner_id','=',partner_id),('type','=','receipt'),('is_hutang_lain','!=',False),('residual_titipan','>',0),('state','=','posted')]")
    voucher_state = fields.Selection(VOUCHER_STATE_SELECTION, 'Voucher Status', readonly=True, related='voucher_id.state')
    account_id = fields.Many2one('account.account', related='journal_id.default_debit_account_id')
    total_titipan = fields.Float(string='Total O/S Customer Deposit', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_titipan')
    total_alokasi = fields.Float(string='Total Alokasi', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_alokasi')
    total_dpp = fields.Float(string='Total DPP', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_dpp')
    line_ids = fields.One2many('dym.mbd.allocation.line', 'alokasi_id', 'Detail MBD Allocation', ondelete='cascade')
    # titipan_move = fields.Many2one(related='voucher_id.move_id')
    move_id = fields.Many2one('account.move', 'Journal', readonly=True)
    move_ids = fields.One2many(related='move_id.line_id', readonly=True)
    batch_id = fields.Many2one('dym.mbd.batch.import', 'Batch ID', readonly=True)
    memo = fields.Char('Memo')

    _defaults={
        'date' : _get_default_date,
        'value_date' : _get_default_date,
        'state':'draft',
    }

    @api.one
    @api.onchange('journal_id','branch_id')
    def onchange_journal_id(self):
        if self.branch_id:
            config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
            if config.dym_mbd_allocation_journal:
                self.journal_id = config.dym_mbd_allocation_journal.id

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'MBD', division='Umum')
        return super(dym_mbd_allocation, self).create(cr, uid, vals, context=context)

    @api.onchange('division','partner_id','branch_id')
    def fields_change(self):
        # self.voucher_id = False
        self.total_titipan = 0

    # @api.onchange('voucher_id')
    # def voucher_change(self):
    #     self.total_titipan = self.voucher_id.residual_titipan
    #     self.titipan_move = self.voucher_id.move_id

    @api.multi
    def view_voucher(self):
        voucher_form = self.env.ref('account_voucher.view_sale_receipt_form', False)

        return {
            'name': 'Other Receivable',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.voucher',
            'views': [(voucher_form.id, 'form')],
            'view_id': voucher_form.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': self.voucher_id.id
        }

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
        for line in self.line_ids:
            line.create_voucher()

        kkkkkkk

        self.write({'state':'done','confirm_uid':self._uid,'confirm_date':datetime.now()})
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
    parent_branch_id = fields.Many2one('dym.branch', related='alokasi_id.branch_id', string='Branch')
    branch_id = fields.Many2one('dym.branch', 'Allocate to Branch')
    alokasi_id = fields.Many2one('dym.mbd.allocation', 'MBD Allocation')
    account_id = fields.Many2one('account.account', related='alokasi_id.account_id', string='Account')
    leasing_id = fields.Many2one('res.partner', related='alokasi_id.partner_id', string='Leasing')
    titipan_line_id = fields.Many2one('account.move.line', 'Journal Item', required=False)
    open_balance = fields.Float('Open Balance')
    open_balance_show = fields.Float(related='open_balance')
    partner_id = fields.Many2one('res.partner', 'Ke Partner', required=True, domain=[('customer','=',True)])
    description = fields.Char('Description')
    amount = fields.Float('Amount', required=True)
    tax_base = fields.Float('DPP', required=True)
    move_line_id = fields.Many2one('account.move.line', 'Move Line')
    voucher_id = fields.Many2one('account.voucher', 'RV No.', readonly=True, copy=False)    
    deposit_id = fields.Many2one('account.voucher', 'Customer Deposit', readonly=True)
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('done','Posted'),
        ('cancel','Cancelled'),
        ('reject','Rejected'),
    ], 'State', compute='_compute_state')

    # @api.constrains('titipan_line_id','alokasi_id','partner_id','amount')
    # def _constraint_move_line(self):
    #     line_search =  self.search([('titipan_line_id','=',self.titipan_line_id.id),('id','!=',self.id),('alokasi_id','=',self.alokasi_id.id),('partner_id','=',self.partner_id.id)])
    #     if line_search:
    #         raise ValidationError("Kombinasi journal item " + self.titipan_line_id.move_id.name + " partner ke " + self.partner_id.name + " duplicate!")
    #     if self.amount < 0:
    #         raise ValidationError("Nilai amount harus lebih besar dari 0!")

    @api.onchange('titipan_line_id')
    def move_line_id_change(self):
        if not self.alokasi_id.branch_id:
            raise osv.except_osv(('Tidak bisa menambah data!'), ('Mohon lengkapi data header terlebih dahulu'))
        self.open_balance = self.titipan_line_id.fake_balance or 0
        self.open_balance_show = self.titipan_line_id.fake_balance or 0

    @api.onchange('lot_id')
    def lot_change(self):
        if not self.alokasi_id.branch_id:
            raise osv.except_osv(('Tidak bisa menambah data!'), ('Mohon lengkapi data header terlebih dahulu'))
        if self.lot_id:
            self.partner_id = self.lot_id.customer_id.id or False
            self.branch_id = self.lot_id.branch_id.id or False

    @api.multi
    def create_voucher(self):
        move_line_id = self.titipan_line_id
        if not move_line_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi titipan!"))
        amount = self.amount if move_line_id.fake_balance >= self.amount else move_line_id.fake_balance
        move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_id.id, amount, False, False)
        values = {
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
        }

        # print "~~~~~~~~~111~~~~~~~~",json.dumps(values,indent=4)

        voucher_line = [[0,0,values]]
        branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)], limit =1)
        move_line_ar = self.env['account.move.line'].search([('account_id','=', branch_config.dym_mbd_allocation_journal.default_debit_account_id.id),('partner_id','=',self.partner_id.id),('ref','=',self.alokasi_id.name),('reconcile_id','=', False),('debit','!=',0.0)])
        if not move_line_ar:
            move_line_ar = self.alokasi_id and self.alokasi_id.voucher_id and self.alokasi_id.voucher_id.move_ids and self.alokasi_id.voucher_id.move_ids.filtered(lambda x:x.account_id.type=='receivable') or False
        
        # print "--------ss-----",move_line_ar, move_line_ar.reconcile_id
        amount_ar = move_line_ar.debit


        move_line_ar_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_ar.id, amount_ar, False, False)


        print "move_line_ar_vals-------------->",amount_ar, " ========= ",move_line_ar_vals
        return True


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
                # if amount_ar < amount:
                #     voucher_line[0][2]['amount'] = move_line_ar.debit
                # elif amount_ar > amount:
                #     voucher_cr_line[0][2]['amount'] = amount      
        else:
            invoice = self.env['account.invoice'].search([('origin','=',self.lot_id.dealer_sale_order_id.name)], limit =1)
            cpa_line = ', '.join([x.move_id.name for x in invoice.payment_ids])
            if invoice.state == 'paid':
                raise osv.except_osv(('Perhatian!'), ('AR untuk Engine No. %s (%s) sudah dibayar di transaksi %s') % (self.lot_id.name,self.partner_id.name_get()[0][1],cpa_line))


        print "~~~~~~~~~222~~~~~~~~",json.dumps(voucher_cr_line,indent=4)


        journal_alokasi = branch_config.dym_mbd_allocation_journal
        if not journal_alokasi:
            raise osv.except_osv(('Perhatian !'), ("Journal alokasi MBD belum lengkap dalam branch %s !")%(branch_config.branch_id.name))
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

        # print "~~~~~~~333~~~~~~~~~~",json.dumps(voucher_id.read(),indent=4)


        self.write({'voucher_id': voucher_id.id})
        voucher_id.validate_or_rfa_credit()
        voucher_id.signal_workflow('approval_approve')
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