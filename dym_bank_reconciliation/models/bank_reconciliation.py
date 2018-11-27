from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class dym_account_move_line_bank_reconciliation(models.Model):
    _inherit = "account.move.line"
    
    bank_recon = fields.Boolean('Bank Reconciliation')
    statement_date = fields.Date('Bank Statement Date')

class dym_bank_reconciliation(models.Model):
    _name = "dym.bank.reconciliation"
    _description = "Bank Reconciliation"

    @api.model
    def _get_default_date(self):
        return self.env['dym.branch'].get_default_date_model()
    
    @api.one
    def _get_saldo(self):
        start_date = self.start_date
        bank_balance = self.default_credit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=True).balance or self.default_debit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=True).balance
        self.saldo_awal = bank_balance
        total_debit = 0
        total_credit = 0
        for line in self.line_ids:
            total_debit += line.debit
            total_credit += line.credit
        self.total_debit = total_debit
        self.total_credit = total_credit
        self.saldo_akhir = bank_balance + total_debit - total_credit

    name = fields.Char('Name')
    state = fields.Selection([
                              ('draft','Draft'),
                              ('done','Posted'),
                              ('cancel','Cancelled'),
                              ], 'State', default='draft')
    date = fields.Date('Transaction Date', readonly=True)
    branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=True)
    partner_type = fields.Many2one('dym.partner.type', 'Partner Type', domain="[('division','like',division)]")
    partner_id = fields.Many2one('res.partner', 'Partner')
    journal_id = fields.Many2one('account.journal', 'Payment Method', required=True, domain="[('type','=','bank'),('branch_id','in',[branch_id,False])]")
    default_debit_account_id = fields.Many2one(related='journal_id.default_debit_account_id')
    default_credit_account_id = fields.Many2one(related='journal_id.default_credit_account_id')

    line_ids = fields.One2many('dym.bank.reconciliation.line', 'bank_reconcile_id', 'Detail Bank Reconciliation')

    memo = fields.Char('Memo')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')    
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    saldo_awal = fields.Float(string='Saldo Awal', compute='_get_saldo')
    total_debit = fields.Float(string='Total Debit', compute='_get_saldo')
    total_credit = fields.Float(string='Total Credit', compute='_get_saldo')
    saldo_akhir = fields.Float(string='Saldo Akhir', compute='_get_saldo')
    
    _defaults={
                'date' : _get_default_date,
                'state':'draft',
               }

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'BRE', division='Umum')
        return super(dym_bank_reconciliation, self).create(cr, uid, vals, context=context)

    @api.onchange('division','journal_id','branch_id','start_date','end_date')
    def branch_change(self):
        self.line_ids = False
        self.default_debit_account_id = False
        self.default_credit_account_id = False
        if self.journal_id:
            self.default_debit_account_id = self.journal_id.default_debit_account_id
            self.default_credit_account_id = self.journal_id.default_credit_account_id

    @api.onchange('partner_type')
    def partner_type_change(self):
        dom={}        
        if self.partner_type:
            domain_search = []
            if self.partner_type.field_type == 'boolean':
                domain_search += [(self.partner_type.name,'!=',False)]
            elif self.partner_type.field_type == 'selection':
                domain_search += [(self.partner_type.selection_name,'=',self.partner_type.name)]
            dom['partner_id'] = domain_search
            self.partner_id = False
        return {'domain':dom} 

    @api.multi
    def wkf_action_cancel(self):        
        self.write({'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
    
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.state not in ['draft','cancel']:
            raise osv.except_osv(('Invalid action !'), ('Cannot delete a bank reconciliation which is in state \'%s\'!') % (val.state))
        return super(dym_bank_reconciliation, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def confirm_recon(self):
        if not self.line_ids:
            raise osv.except_osv(('Tidak bisa confirm!'), ('Tidak ditemukan line transaksi'))
        move_line_obj = self.env['account.move.line']
        for line in self.line_ids:
            if line.move_line_id.bank_recon == True:
                raise osv.except_osv(('Tidak bisa confirm rekonsiliasi'), ('Journal item ' + line.move_line_id.move_id.name + ' sudah di rekonsiliasi!'))
            if line.bank_recon == True:
                line.move_line_id.write({'bank_recon':True,'statement_date':line.statement_date})
        self.write({'state':'done','confirm_uid':self._uid,'confirm_date':datetime.now()})
        return True

    @api.multi
    def generate_journal(self):
        self.line_ids.unlink()
        recon_line_obj = self.env['dym.bank.reconciliation.line']
        move_line_obj = self.env['account.move.line']
        move_line_search = move_line_obj.search([('account_id','in',[self.default_debit_account_id.id,self.default_credit_account_id.id]),('partner_id','=?',self.partner_id.id),('bank_recon','=',False),('date','>=',self.start_date),('date','<=',self.end_date)])
        if not move_line_search:
            raise osv.except_osv(('Tidak bisa generate journal'), ('Data tidak ditemukan!'))
        for move_line in move_line_search:
            recon_line_obj.create({'bank_reconcile_id':self.id, 'move_line_id': move_line.id, 'bank_recon': False, 'statement_date': False})
        return True

class dym_bank_reconciliation_line(models.Model):
    _name = "dym.bank.reconciliation.line"
    _description = "Bank Reconciliation Line"

    bank_reconcile_id = fields.Many2one('dym.bank.reconciliation', 'Bank Reconciliation')
    move_line_id = fields.Many2one('account.move.line', 'Journal Item', required=True)
    bank_recon = fields.Boolean('OK/OS')
    statement_date = fields.Date('Statement Date')
    name = fields.Char(related='move_line_id.name')
    ref = fields.Char(related='move_line_id.ref')
    partner_id = fields.Many2one(related='move_line_id.partner_id')
    account_id = fields.Many2one(related='move_line_id.account_id')
    date = fields.Date(related='move_line_id.date')
    debit = fields.Float(related='move_line_id.debit')
    credit = fields.Float(related='move_line_id.credit')

    @api.constrains('move_line_id','bank_reconcile_id')
    def _constraint_move_line(self):
        # line_search =  self.search([('move_line_id','=',self.move_line_id.id),
        #                             '|','&',('id','!=',self.id),('move_line_id.bank_recon','=',True),
        #                             '|','&',('id','!=',self.id),('bank_reconcile_id','=',self.bank_reconcile_id.id),
        #                             '&',('id','!=',self.id),('bank_recon','=',True)])
        line_search =  self.search([('move_line_id','=',self.move_line_id.id),('id','!=',self.id),('bank_reconcile_id','=',self.bank_reconcile_id.id),])
        if line_search:
            raise ValidationError("Journal item " + self.move_line_id.move_id.name + " duplicate!")

    @api.onchange('move_line_id')
    def move_line_id_change(self):
        if not self.bank_reconcile_id.branch_id or not self.bank_reconcile_id.journal_id or not self.bank_reconcile_id.division or not self.bank_reconcile_id.start_date or not self.bank_reconcile_id.end_date :
            raise osv.except_osv(('Tidak bisa menambah data!'), ('Mohon lengkapi data header terlebih dahulu'))
        self.debit = self.move_line_id.debit or 0
        self.credit = self.move_line_id.credit or 0
        self.name = self.move_line_id.name or ''
        self.ref = self.move_line_id.ref or ''
        self.date = self.move_line_id.date or False
        self.partner_id = self.move_line_id.partner_id or False
        self.account_id = self.move_line_id.account_id or False
