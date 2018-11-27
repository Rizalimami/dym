from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class dym_account_move_line_cleared_giro(models.Model):
    _inherit = "account.move.line"
    
    clear_state = fields.Selection([
        ('not_clearing','Not Clearing Giro'),
        ('running','In Progress'),
        ('open','Open'),
        ('cleared','Cleared')
        ], 'Clearing Giro State', default='not_clearing')

class dym_journal_clearing_account(models.Model):
    _inherit = "account.journal"
    
    clearing_account_id = fields.Many2one('account.account', 'Clearing Account')

    @api.multi
    def get_clearing_account_id(self):
        if self.type == 'bank':
            if not self.clearing_account_id:
                raise osv.except_osv(('Tidak bisa confirm!'), ('Clearing account di journal %s belum di set!')%(self.name))
        return self.clearing_account_id.id

class dym_clearing_giro(models.Model):
    _name = "dym.clearing.giro"
    _description = "Clearing Bank"
    _order = "date desc"

    def _report_xls_clearing_giro_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_id',\
            'division',\
            'date',\
            'due_date',\
            'status',\
            'tgl_cair',\
            'supplier',\
            'no_sp',\
            'no_bank',\
            'memo',\
            'total',\
        ]
 
    def _report_xls_arap_details_fields(self, cr, uid, context=None):
        return [
            'document', 'date', 'date_maturity', 'account', 'description',
            'rec_or_rec_part', 'debit', 'credit', 'balance',
        ]
 
    def _report_xls_arap_overview_template(self, cr, uid, context=None):
        return {}
 
    def _report_xls_arap_details_template(self, cr, uid, context=None):
        return {}
     
    @api.model
    def _get_default_date(self):
        return self.env['dym.branch'].get_default_date_model()
        
    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_clearing_giro] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    @api.model
    def _get_partner_type(self):
        partner_type = self.env['dym.partner.type'].search([('name','=','supplier')], limit=1)
        if partner_type:
            return partner_type.id
        return False

    @api.one
    @api.depends('move_line_ids')
    def _compute_total_giro(self):
        self.total_giro = sum(line.credit for line in self.move_line_ids)

    name = fields.Char('Name')
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('done','Posted'),
        ('cancel','Cancelled'),
        ('reject','Rejected'),
    ], 'State', default='draft')
    date = fields.Date('Tgl Cair', index=True)
    value_date = fields.Date('Value Date')
    branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=True)
    partner_type = fields.Many2one('dym.partner.type', 'Partner Type', domain="[('division','like',division)]")
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    journal_id = fields.Many2one('account.journal', 'Payment Method', required=True, domain="[('type','=','bank'),('branch_id','in',[branch_id,False])]")
    clearing_account_id = fields.Many2one('account.account', 'Clearing Account')
    ref = fields.Char('Payment Ref.')
    move_line_ids = fields.Many2many('account.move.line','dym_clearing_giro_move_line_rel','clearing_id','move_line_id','Move Line', domain="[('move_id.journal_id','=',journal_id),('account_id','=',clearing_account_id),('partner_id','=',partner_id),('division','=',division),('branch_id','=',branch_id),('clear_state','=','open'),('credit','>',0),('ref','=?',ref)]")
    total_giro = fields.Float(string='Total Bank', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_giro')
    move_id = fields.Many2one('account.move', 'Journal', readonly=True)
    memo = fields.Char('Memo')
    analytic_1 = fields.Many2one('account.analytic.account', string='Account Analytic Company', default=_get_analytic_company)
    analytic_2 = fields.Many2one('account.analytic.account', string='Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', string='Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', string='Account Analytic Cost Center')
    voucher_id = fields.Many2one('account.voucher', 'Voucher ID')
    bank_ref = fields.Char('Bank Ref')
    payment_method = fields.Selection([
        ('giro','Giro'),
        ('cheque','Cheque'),
        ('internet_banking','Internet Banking'),
        ('auto_debit','Auto Debit'),
        ('single_payment','Single Payment'),
    ], string='Payment Method')
    
    _defaults={
        'state':'draft',
        'partner_type':_get_partner_type,
    }

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get_per_branch(values['branch_id'], 'CBA', division='Umum')
        res = super(dym_clearing_giro, self).create(values)
        if 'move_line_ids' in values:
            move_lines = values['move_line_ids'][0][2]
            self.env['account.move.line'].browse(move_lines).write({'clear_state':'running'})
        return res

    def change_reset(self, cr, uid, ids, field, branch_id=False, context=None):
        res = {}
        if branch_id:
            branch = self.pool.get('dym.branch').browse(cr, uid, branch_id)
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, 'Umum', False, 4, 'General')
            res['analytic_1'] = analytic_1_general
            res['analytic_2'] = analytic_2_general
            res['analytic_3'] = analytic_3_general
            res['analytic_4'] = analytic_4_general
        result = {}
        result['value'] = res
        return result

    @api.onchange('date')
    def date_change(self):
        self.value_date = self.date
        for move_line in self.move_line_ids:
            if self.date:
                if self.date < move_line.date:
                    return {
                        'value':{
                            'date':False
                        },
                        'warning':{
                            'title':'Perhatian',
                            'message':'Tanggal cair tidak boleh lebih kecil dari tanggal transaksi yaitu (%s)!' % move_line.date
                        }
                    }

    @api.onchange('division','partner_id','journal_id')
    def branch_change(self):
        self.move_line_ids = False
        self.clearing_account_id = False
        if self.journal_id:
            self.clearing_account_id = self.journal_id.clearing_account_id

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
            self.move_line_ids = False
        return {'domain':dom} 

    @api.multi
    def wkf_action_cancel(self):      
        self.move_line_ids.write({'clear_state':'open'})  
        self.write({'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
    
    @api.multi
    def wkf_action_reset(self):      
        self.move_line_ids.write({'clear_state':'running'})
        self.write({'state': 'draft','cancel_uid':False,'cancel_date':False})


    @api.multi
    def unlink(self):
        for clearing in self:
            if clearing.state not in ['draft','cancel']:
                raise UserError(_('You can only delete Clearing Bank in draft state.'))
            if clearing.move_line_ids:
                clearing.move_line_ids.write({'clear_state':'open'})  
        return super(dym_clearing_giro, self).unlink()

    @api.multi
    def confirm_clearing(self):
        context = self.env.context.copy()
        auto_clearing_date = False
        if self.move_id.model == 'account.voucher':
            voucher_id = self.env['account.voucher'].browse([self.move_id.transaction_id])
            auto_clearing_date = voucher_id.payment_method=='auto_clearing' and voucher_id.auto_debit_date or False
            self.voucher_id = voucher_id.id
            self.payment_method = voucher_id.payment_method
            if voucher_id.payment_method=='single_payment' and voucher_id.reference == False and self.bank_ref == False:
                raise ValidationError(_('Mohon untuk mengisi nomor referensi pembayaran untuk voucher nomor %s' % voucher_id.number))
            if not voucher_id.reference:
                voucher_id.reference = self.bank_ref

        if not self.move_line_ids:
            raise osv.except_osv(('Tidak bisa confirm!'), ('Tidak ditemukan line transaksi'))
        if not self.clearing_account_id:
            raise osv.except_osv(('Tidak bisa confirm!'), ('Clearing account di journal %s belum di set!')%(self.journal_id.name))

        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        period_ids = self.env['account.period'].with_context(company_id=self.journal_id.company_id.id).find(dt=self.date)
        move_date = self.date
        if auto_clearing_date:
            move_date = auto_clearing_date

        move_journal = {
            'name': self.name,
            'ref': self.memo,
            'journal_id': self.journal_id.id,
            'date': move_date,
            'period_id':period_ids.id,
            'transaction_id':self.id,
            'model':self.__class__.__name__,
        }
        vals1 = {
            'name': _('Clearing Bank ' + self.name),
            'ref': self.memo,
            'partner_id': self.partner_id.id,
            'account_id': self.clearing_account_id.id,
            'period_id':period_ids.id,
            'date': move_date,
            'debit': self.total_giro,
            'credit': 0.0,
            'branch_id': self.branch_id.id,
            'division': self.division,
            'analytic_account_id' : self.analytic_4.id 
        }

        move_line = [[0,False,vals1]]
        move_journal['line_id'] = move_line
        create_journal = move_obj.create(move_journal)
        reconcile_clearing_line = create_journal.line_id.id
        reconcile_giro_ids = []
        if not self.journal_id.default_credit_account_id:
            raise osv.except_osv(('Tidak bisa confirm!'), ('Tidak ditemukan default credit account di journal %s')%(self.journal_id.name))
        for line in self.move_line_ids:
            vals2 = {
                'name': _('Bank ' + (line.ref or line.name)),
                'ref': self.memo,
                'partner_id': line.partner_id.id,
                'account_id': self.journal_id.default_credit_account_id.id,
                'period_id':period_ids.id,
                'date': move_date,
                'debit': 0.0,
                'credit': line.credit,
                'branch_id': line.branch_id.id,
                'division': line.division,
                'analytic_account_id' : line.analytic_account_id.id,
                'move_id': create_journal.id,
            }
            created_move_line = move_line_obj.create(vals2)
            reconcile_giro_ids.append(line.id)
        if self.journal_id.entry_posted:
            post_journal = create_journal.post()
        for rec_id in reconcile_giro_ids:
            reconcile_id = self.pool.get('account.move.line').reconcile_partial(self._cr,self._uid, [reconcile_clearing_line, rec_id], 'auto')
        self.move_line_ids.write({'clear_state':'cleared'})
        self.write({'state':'done','move_id':create_journal.id,'confirm_uid':self._uid,'confirm_date':datetime.now()})
        for move_line in self.move_line_ids:
            for line in move_line.move_id.line_id:
                if line.debit:
                    analytic_3 = line.analytic_3.id
        if analytic_3:
            for line in created_move_line.move_id.line_id:
                line.write({'analytic_3':analytic_3})
        return True


    @api.multi 
    def wkf_reverse_journal(self):
        ref_move = self.move_line_ids.move_id
        if not len(ref_move) > 1:
            if ref_move.model == 'account.voucher':
                voucher = self.env[ref_move.model].search([('id','=',ref_move.transaction_id)])
                voucher.write({'clearing_bank':False})
        self.move_id.action_reverse_journal()
        self.write({'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
