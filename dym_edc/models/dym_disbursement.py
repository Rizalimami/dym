import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class dym_disbursement(models.Model):
    _name = "dym.disbursement"
    _description = "Disbursement EDC"
    
    @api.one
    @api.depends('disbursement_line.debit','amount')
    def _compute_amount(self):
        debit_amount = 0.00
        for x in self.disbursement_line :
            debit_amount += x.debit
        
        self.diff_amount = self.amount + self.bank_admin - debit_amount 

    @api.cr_uid_ids_context
    @api.depends('period_id')
    def _get_period(self, cr, uid, ids,context=None):
        if context is None: context = {}
        if context.get('period_id', False):
            return context.get('period_id')
        periods = self.pool.get('account.period').find(cr, uid, context=context)
        return periods and periods[0] or False

    @api.model
    def _get_default_branch(self):
        res = self.env.user.get_default_branch()
        return res

    def branch_id_disbursement(self,cr,uid,ids,branch_id,context=None):
        value = {}
        domain = {}
        if branch_id :
            branch_search = self.pool.get('dym.branch').browse(cr,uid,branch_id)
            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_search, 'Umum',False, 4, 'General')
            obj_bank = self.pool.get('account.journal')
            bank_acc=obj_bank.search(cr, uid,[('branch_id','=',branch_id), ('type','=','bank')])
            obj_edc = self.pool.get('account.journal')
            edc_journal=obj_edc.search(cr, uid,[('branch_id','=',branch_id), ('type','=','edc')])
            value['analytic_1'] = analytic_1
            value['analytic_2'] = analytic_2
            value['analytic_3'] = analytic_3
            value['analytic_4'] = analytic_4
            value['bank_account'] = bank_acc
            value['edc_journal_id'] = edc_journal
        return {'domain':domain,'value':value}
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('posted','Posted'),
        ('paid','Paid'),
        ('cancel','Cancelled')
    ]
    
    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_edc] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    @api.model
    def _getCompanyBranch(self):
        user = self.env.user
        if user.branch_type!='HO':
            if not user.branch_id:
                raise osv.except_osv(('Perhatian !'), ("User %s tidak memiliki default branch. Hubungi system administrator agar menambahkan default branch di User Setting." % self.env.user.name))
            return [('id','=',user.branch_id.id)]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        branch_ids = [b.id for b in self.env.user.branch_ids if b.company_id.id==company_id]
        return [('id','in',branch_ids)]

    name = fields.Char(string="Name",readonly=True,default='')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True,
                                 default=lambda self: self.env.user.company_id,
                                 help="Company related to this journal")
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True,default=_get_default_branch, domain=_getCompanyBranch)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], string='Division',default='Umum', required=True,change_default=True, select=True)
    journal_id = fields.Many2one('account.journal',string="Payment Method",domain="[('branch_id','in',[branch_id,False]),('type','in',['cash','bank'])]")
    edc_journal_id = fields.Many2one('account.journal',string="EDC",domain="[('type','=','edc'),('branch_id','in',[branch_id,False])]")    
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line',related='move_id.line_id',string='Journal Items', readonly=True)    
    disbursement_line = fields.One2many('dym.disbursement.line','disbursement_id')
    amount = fields.Float(string="Paid Amount")
    bank_admin = fields.Float(string="Bank Admin")
    bank_account = fields.Many2one('account.journal', string="Bank", domain="[('branch_id','in',[branch_id,False]),('type','in',['bank'])]")
    diff_amount = fields.Float(string='Difference Amount',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date = fields.Date(string="Date",required=True,readonly=True,default=fields.Date.context_today)
    description = fields.Text(string="Note")
    period_id = fields.Many2one('account.period',string="Period",required=True, readonly=True,default=_get_period)
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    paid_uid = fields.Many2one('res.users', string="Paid by")
    paid_date = fields.Datetime('Paid on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    due_date = fields.Date(string="Due Date", required=True)
    analytic_1 = fields.Many2one('account.analytic.account', string='Account Analytic Company', default=_get_analytic_company)
    analytic_2 = fields.Many2one('account.analytic.account', string='Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', string='Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', string='Account Analytic Cost Center')
    
    @api.model
    def create(self,vals,context=None):
        if vals['amount'] <= 0 :
            raise osv.except_osv(('Perhatian !'), ("Paid Amount tidak boleh kurang dari Rp.1 "))
        if 'disbursement_line' not in vals or not vals['disbursement_line']:
            raise osv.except_osv(('Perhatian !'), ("Detail belum diisi. Data tidak bisa di save."))
        move_pop = []   
        for x in vals['disbursement_line']:
            move_pop.append(x.pop(2))      
              
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'EDC', division="Umum")                               
        vals['date'] = time.strftime('%Y-%m-%d')
        del[vals['disbursement_line']]     
        
        disbursement_id = super(dym_disbursement, self).create(vals)
        if disbursement_id :
            for x in move_pop :
                disbursement = self.env['dym.disbursement.line']
                values = {
                    'name':x['name'],                               
                    'move_line_id':x['move_line_id'],
                    'disbursement_id':disbursement_id.id
                }
                disbursement.create(values)   
        else :
            return False           
        return disbursement_id
    
    @api.onchange('edc_journal_id')
    def onchange_reimbursement(self):          
        if self.edc_journal_id :
            move_line = self.env['account.move.line']
            move_line_search = move_line.search([
                ('journal_id','=',self.edc_journal_id.id),
                ('reconcile_id','=',False),
                ('debit','>',0),
                ('ref', 'not like','EDC')
                ])
            move = []
            if not move_line_search :
                raise osv.except_osv(('Perhatian !'), ("Transaksi menggunakan EDC %s tidak ditemukan!")%(self.edc_journal_id.name))
                move = []
            elif move_line_search :
                for x in move_line_search:
                    move.append([0,0,{
                        'name':x.name,                               
                        'move_line_id':x.id,
                        'partner_id':x.partner_id.id,
                        'debit':x.debit,
                        'ref':x.ref,
                        'account_id':x.account_id
                    }])   
            self.disbursement_line = move

    @api.one
    def post_disbursement(self):
        if self.due_date > datetime.today().strftime('%Y-%m-%d'):
            raise osv.except_osv(('Perhatian !'), ("Tidak bisa post data, data baru bisa di post setelah tanggal %s!")%(self.due_date))
        self.action_move_line_create()
        self.write({'date':datetime.today(),'state':'posted','confirm_uid':self._uid,'confirm_date':datetime.now()})
        return True

    @api.one
    def receieve_disbursement(self):
        if self.due_date > datetime.today().strftime('%Y-%m-%d'):
            raise osv.except_osv(('Perhatian !'),
                                 ("Tidak bisa paid data, data baru bisa di paid setelah tanggal %s!") % (self.due_date))
        self.action_move_line_create2()
        self.write({'date':datetime.today(),'state':'paid','paid_uid':self._uid,'paid_date':datetime.now(), 'bank_admin': self.bank_admin, 'amount': self.amount - self.bank_admin})
        # self.write({'date': datetime.today(), 'state': 'paid', 'paid_uid': self._uid, 'paid_date': datetime.now(), 'bank_account': self.bank_account, 'bank_admin': self.bank_admin, 'amount': self.amount - self.bank_admin })
        return True 

    @api.one
    def cancel_disbursement(self):
        self.write({'state':'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
        return True  
    
    @api.cr_uid_ids_context
    def action_move_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        periods = self.pool.get('account.period').find(cr, uid, context=context)
        move_line_rec = [] 
        disbursement = self.browse(cr, uid, ids, context=context)
        disbursement.write({'period_id':periods and periods[0]})
        
        name = disbursement.name
        date = disbursement.date
        journal_edc_id = disbursement.edc_journal_id.id
        debit_account_id = disbursement.edc_journal_id.default_debit_account_id.id
        if not debit_account_id:
            raise osv.except_osv(('Perhatian !'), ("Account belum diisi dalam journal %s!")%(disbursement.edc_journal_id.name))
        amount = disbursement.amount          
        period_id = disbursement.period_id.id
        diff_amount = disbursement.diff_amount

        config = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',disbursement.branch_id.id)])
        if config :
            config_browse = self.pool.get('dym.branch.config').browse(cr,uid,config)
            pl_account = config_browse.disburesement_pl_account_id.id
            if not pl_account :
                raise osv.except_osv(('Perhatian !'), ("Account Disbursement EDC belum diisi dalam setting branch !"))
                
        elif not config :
            raise osv.except_osv(('Perhatian !'), ("Account Disbursement EDC belum diisi dalam setting branch !"))

        if config_browse.max_difference < abs(diff_amount):
            raise osv.except_osv(('Perhatian !'), ("Maximum differnce amount adalah %s!")%(config_browse.max_difference))

        move = {
            'name': name,
            'journal_id': journal_edc_id,
            'date': date,
            'ref':name,
            'period_id':period_id,
            'transaction_id':disbursement.id,
            'model':disbursement.__class__.__name__,
        }
        move_id = move_pool.create(cr, uid, move, context=None)
        move_line1 = {
            'name': _('%s')%(disbursement.edc_journal_id.name),
            'ref':name,
            'account_id': debit_account_id,
            'move_id': move_id,
            'journal_id': journal_edc_id,
            'period_id': period_id,
            'date': date,
            'debit': amount,
            'credit': 0.0,
            'partner_id':disbursement.edc_journal_id.partner_id.id,
            'analytic_account_id' : disbursement.analytic_4.id,
            'branch_id' : disbursement.branch_id.id,
            'division' : disbursement.division,
            'clear_state': 'open',
        }   
        line_id = move_line_pool.create(cr, uid, move_line1, context)
        if diff_amount < 0 :
            diff_amount = abs(diff_amount)
            move_line = {
                'name': _('Shortage Pencairan'),
                'ref':name,
                'account_id': pl_account,
                'move_id': move_id,
                'journal_id': journal_edc_id,
                'period_id': period_id,
                'date': date,
                'debit': diff_amount,
                'credit': 0.0,
                'partner_id':disbursement.edc_journal_id.partner_id.id,
                'analytic_account_id' : disbursement.analytic_4.id,
                'branch_id' : disbursement.branch_id.id,
                'division' : disbursement.division
            }    
            line_id = move_line_pool.create(cr, uid, move_line, context) 
            
        elif diff_amount > 0 :
            move_line4 = {
                'name': _('Excess Disbursement'),
                'ref':name,
                'account_id': pl_account,
                'move_id': move_id,
                'journal_id': journal_edc_id,
                'period_id': period_id,
                'date': date,
                'debit': 0.0,
                'credit': diff_amount,
                'partner_id':disbursement.edc_journal_id.partner_id.id,
                'analytic_account_id' : disbursement.analytic_4.id,
                'branch_id' : disbursement.branch_id.id,
                'division' : disbursement.division
            }    
            line_id4 = move_line_pool.create(cr, uid, move_line4, context)  
            
        reconcile_by_account = {}                                      
        for y in disbursement.disbursement_line :
            move_line_rec = []
            move_line_2 = {
                'name': _('Disbursement %s')%(y.ref),
                'ref':name,
                'account_id': y.account_id.id,
                'move_id': move_id,
                'journal_id': journal_edc_id,
                'period_id': period_id,
                'date': date,
                'debit': 0.0,
                'credit': y.debit,
                'partner_id':y.partner_id.id,
                'analytic_account_id' : y.move_line_id.analytic_account_id.id,
                'branch_id' : y.move_line_id.branch_id.id,
                'division' : y.move_line_id.division
            }     
                   
            line_id2 = move_line_pool.create(cr, uid, move_line_2, context)
            curr_move_line = []
            if reconcile_by_account.get(y.account_id.id,0) != 0 :
                curr_move_line = reconcile_by_account[y.account_id.id]
            curr_move_line.append(line_id2)
            curr_move_line.append(y.move_line_id.id)    
            reconcile_by_account[y.account_id.id] = curr_move_line
            
        for key,value in reconcile_by_account.items() :
            self.pool.get('account.move.line').reconcile(cr, uid,  value)

        if disbursement.edc_journal_id.entry_posted:
            posted = move_pool.post(cr, uid, [move_id], context=None)

        self.write(cr, uid, disbursement.id, {'move_id': move_id})
        return True

    @api.cr_uid_ids_context
    def action_move_line_create2(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        periods = self.pool.get('account.period').find(cr, uid, context=context)
        move_line_rec = []
        disbursement = self.browse(cr, uid, ids, context=context)
        disbursement.write({'period_id': periods and periods[0]})

        name = disbursement.name
        date = disbursement.date

        journal_edc_id = disbursement.edc_journal_id.id
        credit_account_id = disbursement.edc_journal_id.default_credit_account_id.id
        debit_account_id = disbursement.bank_account.default_debit_account_id.id
        if not debit_account_id:
            raise osv.except_osv(('Perhatian !'), ("Account belum diisi dalam journal %s!") % (disbursement.edc_journal_id.name))
        amount = disbursement.amount
        amount_bank = disbursement.amount - disbursement.bank_admin
        bank_admin = disbursement.bank_admin
        period_id = disbursement.period_id.id

        config = self.pool.get('dym.branch.config').search(cr, uid, [('branch_id', '=', disbursement.branch_id.id)])
        if config:
            config_browse = self.pool.get('dym.branch.config').browse(cr, uid, config)
            pl_account = config_browse.disburesement_pl_account_id.id
            if not pl_account:
                raise osv.except_osv(('Perhatian !'), ("Account Disbursement EDC belum diisi dalam setting branch !"))

        elif not config:
            raise osv.except_osv(('Perhatian !'), ("Account Disbursement EDC belum diisi dalam setting branch !"))

        move_line1 = {
            'name': _('%s')%(disbursement.edc_journal_id.name),
            'ref': name,
            'account_id': credit_account_id,
            'move_id': disbursement.move_id.id,
            'journal_id': journal_edc_id,
            'period_id': period_id,
            'date': date,
            'debit': 0.0,
            'credit': amount,
            'partner_id': disbursement.edc_journal_id.partner_id.id,
            'analytic_account_id': disbursement.analytic_4.id,
            'branch_id': disbursement.branch_id.id,
            'division': disbursement.division,
            'clear_state': 'open',
        }
        line_id = move_line_pool.create(cr, uid, move_line1, context)

        move_line_rec = []
        move_line_2 = {
            'name': _('Bank Paid %s') % (name),
            'ref': name,
            'account_id': debit_account_id,
            'move_id': disbursement.move_id.id,
            'journal_id': journal_edc_id,
            'period_id': period_id,
            'date': date,
            'debit': amount_bank,
            'credit': 0.0,
            'partner_id': disbursement.edc_journal_id.partner_id.id,
            'analytic_account_id': disbursement.analytic_4.id,
            'branch_id': disbursement.branch_id.id,
            'division': disbursement.division,
        }

        line_id2 = move_line_pool.create(cr, uid, move_line_2, context)

        move_line_3 = {
            'name': _('Adm Bank %s') % (name),
            'ref': name,
            'account_id': pl_account,
            'move_id': disbursement.move_id.id,
            'journal_id': journal_edc_id,
            'period_id': period_id,
            'date': date,
            'debit': bank_admin,
            'credit': 0.0,
            'partner_id': disbursement.edc_journal_id.partner_id.id,
            'analytic_account_id': disbursement.analytic_4.id,
            'branch_id': disbursement.branch_id.id,
            'division': disbursement.division,
        }

        line_id3 = move_line_pool.create(cr, uid, move_line_3, context)
        posted = move_pool.post(cr, uid, [disbursement.move_id.id], context=None)
        self.write(cr, uid, disbursement.id, {'move_id': disbursement.move_id.id})
        return True      

    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Reimbursement EDC sudah diproses, data tidak bisa didelete !"))
        return super(dym_disbursement, self).unlink(cr, uid, ids, context=context)     
                
class dym_disbursement_line(models.Model):
    _name = 'dym.disbursement.line'

    name = fields.Char(string="Name",readonly=True,default='')
    disbursement_id = fields.Many2one('dym.disbursement')
    move_line_id = fields.Many2one('account.move.line')
    partner_id = fields.Many2one('res.partner',related="move_line_id.partner_id",string="Partner")
    debit = fields.Float(related="move_line_id.debit",string="Amount")
    ref = fields.Char(related='move_line_id.ref',string="Reference")
    account_id = fields.Many2one('account.account',related="move_line_id.account_id",string="Account")
                     