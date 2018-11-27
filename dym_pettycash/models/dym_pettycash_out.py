import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.osv import orm
from ..report import fungsi_terbilang
from openerp.addons.dym_base import DIVISION_SELECTION

class dym_pettycash(models.Model):
    _name = "dym.pettycash"
    _description ="Petty Cash"
    _order = "create_date desc"
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting Approval'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('fully_returned', 'Fully Returned'),
        ('horejected', 'HO Rejected'),
        ('reimbursed', 'Reimbursed'),
        ('cancel', 'Cancelled'),
    ]   
    
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

    @api.one
    @api.depends('line_ids.amount_real','line_ids.amount_reimbursed')
    def _compute_amount(self):
        self.amount_real = sum(line.amount_real for line in self.line_ids)
        self.amount_reimbursed = sum(line.amount_reimbursed for line in self.line_ids)
        # self.balance = sum(line.amount_real for line in self.line_ids)
                    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil

    def ubah_tanggal(self,tanggal):
        if not tanggal:
            return False
        try:
            conv = datetime.strptime(tanggal, '%d-%m-%Y %H:%M')
            return conv.strftime('%d-%m-%Y')
        except Exception as e:
            conv = datetime.strptime(tanggal, '%Y-%m-%d %H:%M:%S')
            return conv.strftime('%d-%m-%Y')

    def ubah_tanggal_2(self,tanggal):
        if not tanggal:
            return False
        try:
            conv = datetime.strptime(tanggal, '%d-%m-%Y')
            return conv.strftime('%d-%m-%Y')
        except Exception as e:
            conv = datetime.strptime(tanggal, '%Y-%m-%d')
            return conv.strftime('%d-%m-%Y')

    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_pettycash-1] Tidak ditemukan data analytic untuk company %s")%(company.name))
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

    @api.multi
    @api.depends('journal_id')
    def _get_balance(self):
        aa_obj = self.env['account.analytic.account']
        start_date = fields.Date.context_today(self)
        for rec in self:
            bank_balance = 0
            today_balance = 0
            branch_id = rec.branch_id
            if rec.journal_id:            
                sql_query = ''
                if branch_id:
                    analytic_branch = aa_obj.search([('segmen','=',3),('branch_id','=',branch_id.id),('type','=','normal'),('state','not in',('close','cancelled'))])
                    analytic_cc = aa_obj.search([('segmen','=',4),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',analytic_branch.ids)])
                    sql_query = ' and l.period_id in (select id from  account_period where special= FALSE) AND l.analytic_account_id in %s' % str(tuple(analytic_cc.ids)).replace(',)', ')')
                bank_balance = rec.journal_id.default_credit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=True,sql_query=sql_query).balance or rec.journal_id.default_debit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=True,sql_query=sql_query).balance
                today_balance = rec.journal_id.default_credit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=False,sql_query=sql_query).balance or rec.journal_id.default_debit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=False,sql_query=sql_query).balance
            rec.balance = bank_balance + today_balance
        return True

    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, default=_get_default_branch, domain=_getCompanyBranch)
    name = fields.Char(string="Name",readonly=True,default='')
    user_id = fields.Many2one('hr.employee', string='Responsible')
    division = fields.Selection(DIVISION_SELECTION, string='Division', change_default=True, select=True, readonly=True)
    amount = fields.Float('Paid Amount')
    branch_destination_id =  fields.Many2one('dym.branch', string='Branch Destination', required=True)
    journal_id = fields.Many2one('account.journal',string="Payment Method",domain="[('branch_id','in',[branch_id,False]),('type','=','pettycash')]")
    line_ids = fields.One2many('dym.pettycash.line','pettycash_id',string="PettyCash Line")
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date = fields.Date(string="Date",required=True,readonly=True,default=fields.Date.context_today)
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line',related='move_id.line_id',string='Journal Items', readonly=True)    
    period_id = fields.Many2one('account.period',string="Period",required=True, readonly=True,default=_get_period)
    #company_id = fields.Many2one(related='journal_id.company_id',string='Company',store=True, readonly=True),
    account_id = fields.Many2one('account.account',string="Account")    
    #reimbursed_id = fields.Many2one('dym.reimbursed')  
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    amount_real = fields.Float(string='Amount Biaya',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',) 
    amount_reimbursed = fields.Float(string='Amount Reimbursed',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',) 
    kas_bon = fields.Boolean('Kas Bon')
    pay_supplier_invoice = fields.Boolean('Pay Supplier Invoice')

    date_cancel = fields.Date(string="Date Canceled",readonly=True)
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    
    balance = fields.Float(compute=_get_balance, string='Balance', readonly=True)
    balance_on_posted = fields.Float(string='Balance On Posted', readonly=True) 
    analytic_1 = fields.Many2one('account.analytic.account', 'Account Analytic Company')
    analytic_2 = fields.Many2one('account.analytic.account', 'Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center')

    analytic_2_readonly = fields.Many2one('account.analytic.account', 'Account Analytic Bisnis Unit', related="analytic_2")
    analytic_3_readonly = fields.Many2one('account.analytic.account', 'Account Analytic Branch', related="analytic_3")
    analytic_4_readonly = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center', related="analytic_4")

    wo_ids = fields.Many2many('dym.work.order','pettycash_out_wo_rel','pettycash_id','wo_id','Work Order Reference')
    so_ids = fields.Many2many('sale.order','pettycash_out_so_rel','pettycash_id','so_id','Sales Memo Reference')
    cash_in_ids = fields.One2many('dym.pettycash.in','pettycash_id',string="Cash In")
    cash_in = fields.Many2one('dym.pettycash.in', string='Pettycash In Reff')

    _defaults = {
        'analytic_1':_get_analytic_company,
    }

    @api.onchange('kas_bon')
    def onchange_kas_bon(self):
        self.line_ids = []

    @api.multi
    def get_equal_amount(self,amount,pettycash):
        total_amount = 0.0
        for x in pettycash :
            total_amount += x['amount']
        return total_amount
            
    @api.model
    def default_get(self, fields):
        res = super(dym_pettycash, self).default_get(fields)
        journal_id = self.env['account.journal'].search([('branch_id','in',[self.branch_id,False]),('type','=','pettycash')])
        res['journal_id'] = journal_id.id
        return res

    @api.multi
    @api.constrains('amount')
    def check_amount(self):
        for rec in self:
            if rec.amount > rec.balance:
                raise osv.except_osv(('Perhatian !'), ("Nilai amount tidak boleh lebih besar dari balance."))

    @api.model
    def create(self,vals,context=None):

        if not vals['line_ids'] :
            raise osv.except_osv(('Perhatian !'), ("Detail belum diisi. Data tidak bisa di save."))
        try:
            pettycash = []
            for x in vals['line_ids']:
                x_pop = x.pop(2)
                pettycash.append(x_pop)        
            vals['date'] = datetime.today()            
            if vals['journal_id'] :
                journal_obj = self.env['account.journal'].search([('id','=',vals['journal_id'])])
                vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'PCO', division='Umum')  
                     
            del[vals['line_ids']]
            vals['amount'] = self.get_equal_amount(vals['amount'],pettycash)
        except:
            pass
        
        pettycash_id = super(dym_pettycash, self).create(vals)
        if pettycash_id :
            rekap = []
            for x in pettycash :
                if x['account_id'] not in rekap :
                    rekap.append(x['account_id'])
                elif x['account_id'] in rekap :
                    raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada Account yang sama dalam detail transaksi"))
                     
                pettycash_pool = self.env['dym.pettycash.line']
                pettycash_pool.create({
                    'pettycash_id':pettycash_id.id,
                    'name':x['name'],
                    'account_id':x['account_id'],
                    'amount':x['amount'],
                    'analytic_1':x['analytic_1'],
                    'analytic_2':x['analytic_2'],
                    'analytic_3':x['analytic_3'],
                    'analytic_4':x['analytic_4'],
                })
        else :
            return False    
        return pettycash_id
    
    @api.multi
    def write(self,vals,context=None):
        vals.get('line_ids',[]).sort(reverse=True)        
        line = vals.get('line_ids',False)
        if line:
            for x,item in enumerate(line) :
                petty_id = item[1]
                if item[0] == 1 or item[0] == 0:
                    value = item[2]
                    if value.get('account_id') :
                        for y in self.line_ids :
                            if y.account_id.id == value['account_id'] :
                                raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada Account yang sama dalam detail transaksi"))
        res = super(dym_pettycash,self).write(vals)
        return res        

    @api.onchange('division')
    def onchange_division(self):
        value = {}
        value['line_ids'] = []
        return {'value':value}

    @api.onchange('branch_id')
    def onchange_branch(self):
        dom={}
        val={}
        self.branch_destination_id = self.branch_id
        if self.branch_id:
            branch = self.branch_id
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(self._cr, self._uid, branch, 'Umum', False, 4, 'General')
            self.analytic_1 = analytic_1_general
            self.analytic_2 = analytic_2_general
            self.analytic_3 = analytic_3_general
            self.analytic_4 = analytic_4_general
            dom['user_id'] = [('branch_id','=',self.branch_id.id)]
            self.line_ids = []
            print "self.branch_id.branch_status",self.branch_id.branch_status
            if self.branch_id.branch_status == 'HO':
                self.division = 'Finance'
            if self.branch_id.branch_status == 'H1':
                self.division = 'Unit'
            if self.branch_id.branch_status == 'H23':
                self.division = 'Sparepart'
            if self.branch_id.branch_status == 'H123':
                self.division = 'Unit'
        return {'domain':dom,'value':val}

    @api.multi
    def post_pettycash(self):
        max_amount = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if max_amount and max_amount.petty_cash_limit and self.amount > max_amount.petty_cash_limit:            
            warning = {
                'title': ('Perhatian !'),
                'message': (("Nilai amount tidak boleh dari limit (%s)" % '{:20,.2f}'.format(max_amount.petty_cash_limit))),
            }                      
            return {'warning':warning}
        self.update({'balance_on_posted': self.balance-float(self.amount)})
        self.action_move_line_create()
        self.set_amount_real()
        return True
    
    @api.multi
    def set_amount_real(self):
        for x in self.line_ids :
            x.amount_reimbursed = 0
            if self.kas_bon:
                x.amount_real = 0
            else:
                x.amount_real = x.amount
                    
    @api.multi
    def reimbursed_pettycash(self):
        self.state = 'reimbursed'
    
    @api.multi
    def cancel_pettycash(self):
        if self.move_id:
            self.move_id.action_reverse_journal()
        self.state = 'cancel'
        self.date_cancel = datetime.today()
        self.cancel_uid = self._uid
        self.cancel_date = datetime.now()
     
    @api.cr_uid_ids_context
    def action_move_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        periods = self.pool.get('account.period').find(cr, uid, context=context)
        for pettycash in self.browse(cr, uid, ids, context=context):
            pettycash.write({'period_id':periods and periods[0]})
            name = pettycash.name
            date = pettycash.date
            journal_id = pettycash.journal_id.id
            account_id = pettycash.journal_id.default_credit_account_id.id or pettycash.journal_id.default_debit_account_id.id
            amount = pettycash.amount          
            period_id = pettycash.period_id.id
            
            move = {
                'name': name,
                'journal_id': journal_id,
                'ref':name,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'period_id':period_id,
                'transaction_id':pettycash.id,
                'model':pettycash.__class__.__name__,
            }
            move_id = move_pool.create(cr, uid, move, context=None)

            names = []
            for y in pettycash.line_ids:
                names.append(y.name)
            names = ', '.join(names)

            move_line1 = {
                'name': _('Petty Cash Out: %s' % names),
                'ref':name,
                'account_id': account_id,
                'move_id': move_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'debit': 0.0,
                'credit': pettycash.amount,
                'branch_id' : pettycash.branch_id.id,
                'division' : pettycash.division,
                'analytic_account_id' : pettycash.analytic_4.id                    
            }           
            line_id = move_line_pool.create(cr, uid, move_line1, context)            
            for y in pettycash.line_ids :
                move_line_2 = {
                    'name': y.name,
                    'ref':name,
                    'account_id': y.account_id.id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'debit': y.amount,
                    'credit': 0.0,
                    'branch_id' : pettycash.branch_destination_id.id,
                    'division' : pettycash.division,
                    'analytic_1': y.analytic_1.id,
                    'analytic_2': y.analytic_2.id,
                    'analytic_3': y.analytic_3.id,
                    'analytic_4': y.analytic_4.id,
                    'analytic_account_id' : y.analytic_4.id                    
                }           
                line_id2 = move_line_pool.create(cr, uid, move_line_2, context)
                
            # self.create_intercompany_lines(cr,uid,ids,move_id,context=None)      
            if  pettycash.journal_id.entry_posted :    
                posted = move_pool.post(cr, uid, [move_id], context=None)
            self.write(cr, uid, pettycash.id, {'date':datetime.today(),'state': 'posted', 'move_id': move_id,'account_id':account_id,'confirm_uid':uid,'confirm_date':datetime.now()})
        return True 

    @api.cr_uid_ids_context   
    def create_intercompany_lines(self,cr,uid,ids,move_id,context=None):
        branch_rekap = {}       
        branch_pool = self.pool.get('dym.branch')        
        vals = self.browse(cr,uid,ids) 
        move_line = self.pool.get('account.move.line')
        move_line_srch = move_line.search(cr,uid,[('move_id','=',move_id)])
        move_line_brw = move_line.browse(cr,uid,move_line_srch)
        
        branch = branch_pool.search(cr,uid,[('id','=',vals.branch_id.id)])

        if branch :
            branch_browse = branch_pool.browse(cr,uid,branch)
            inter_branch_header_account_id = branch_browse.inter_company_account_id.id
            if not inter_branch_header_account_id :
                raise osv.except_osv(('Perhatian !'), ("Account Inter Company belum diisi dalam Master branch %s !")%(vals.branch_id.name))
        
        #Merge Credit and Debit by Branch                                
        for x in move_line_brw :
            if x.branch_id not in branch_rekap :
                branch_rekap[x.branch_id] = {}
                branch_rekap[x.branch_id]['debit'] = x.debit
                branch_rekap[x.branch_id]['credit'] = x.credit
            else :
                branch_rekap[x.branch_id]['debit'] += x.debit
                branch_rekap[x.branch_id]['credit'] += x.credit  
        
        #Make account move       
        for key,value in branch_rekap.items() :
            if key != vals.branch_id :
                config = branch_pool.search(cr,uid,[('id','=',key.id)])
        
                if config :
                    config_browse = branch_pool.browse(cr,uid,config)
                    inter_branch_detail_account_id = config_browse.inter_company_account_id.id                
                    if not inter_branch_detail_account_id :
                        raise osv.except_osv(('Perhatian !'), ("Account Inter belum diisi dalam Master branch %s - %s!")%(key.code, key.name))

                balance = value['debit']-value['credit']
                debit = abs(balance) if balance < 0 else 0
                credit = balance if balance > 0 else 0
                
                if balance != 0:
                    move_line_create = {
                        'name': _('Interco Petty Cash Out %s')%(key.name),
                        'ref':_('Interco Petty Cash Out %s')%(key.name),
                        'account_id': inter_branch_header_account_id,
                        'move_id': move_id,
                        'journal_id': vals.journal_id.id,
                        'period_id': vals.period_id.id,
                        'date': vals.date,
                        'debit': debit,
                        'credit': credit,
                        'branch_id' : key.id,
                        'division' : vals.division                    
                    }    
                    inter_first_move = move_line.create(cr, uid, move_line_create, context)    
                             
                    move_line2_create = {
                        'name': _('Interco Petty Cash Out %s')%(vals.branch_id.name),
                        'ref':_('Interco Petty Cash Out %s')%(vals.branch_id.name),
                        'account_id': inter_branch_detail_account_id,
                        'move_id': move_id,
                        'journal_id': vals.journal_id.id,
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
                raise osv.except_osv(('Perhatian !'), ("Petty Cash sudah diproses, data tidak bisa didelete !"))
        return super(dym_pettycash, self).unlink(cr, uid, ids, context=context) 

    @api.onchange('amount')
    def amount_change(self):    
        self.amount = sum([x.amount for x in self.line_ids])
        warning = {}     
        if self.amount < 0 :
            self.amount = 0 
            warning = {
                'title': ('Perhatian !'),
                'message': (("Nilai amount tidak boleh kurang dari 0")),
            }                      
            return {'warning':warning}

        max_amount = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if max_amount and max_amount.petty_cash_limit and self.amount > max_amount.petty_cash_limit:            
            warning = {
                'title': ('Perhatian !'),
                'message': (("Nilai amount tidak boleh dari limit (%s)" % '{:20,.2f}'.format(max_amount.petty_cash_limit))),
            }                      
            return {'warning':warning}


    @api.onchange('line_ids')
    def amount_line_ids(self):
        self.amount = sum([x.amount for x in self.line_ids])
                      
class dym_pettycash_line(models.Model): 
    _name = "dym.pettycash.line"
    _description = "Petty Cash Line"
             
    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_pettycash-2] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    @api.one
    @api.depends('amount_real')
    def _get_settlement(self):
        if self.amount_real > 0:
            self.settlement = True

    pettycash_id = fields.Many2one('dym.pettycash',string="Petty Cash")
    branch_id = fields.Many2one('dym.branch', related="pettycash_id.branch_id", store=True,)
    division = fields.Selection(DIVISION_SELECTION, string='Division', related="pettycash_id.division", store=True,)
    name = fields.Char(string="Description", required=True)
    account_id = fields.Many2one('account.account',string="Account")
    amount = fields.Float(string="Amount")
    kas_bon = fields.Boolean('Kas Bon', related="pettycash_id.kas_bon")
    amount_total = fields.Float(related="pettycash_id.amount", string="Amount")
    amount_real = fields.Float(string="Amount Biaya")
    amount_reimbursed = fields.Float(string="Amount Reimbursed")
    analytic_1 = fields.Many2one('account.analytic.account', 'Account Analytic Company')
    analytic_2 = fields.Many2one('account.analytic.account', 'Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center')
    analytic_4_readonly = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center', related="analytic_4")
    settlement = fields.Boolean('Settlement', compute='_get_settlement', store=True)

    _defaults = {
        # 'analytic_1': _get_analytic_company,
    }

    _sql_constraints = [
        ('unique_name_pettycash_id', 'unique(account_id,pettycash_id)', 'Detail account duplicate, mohon cek kembali !'),
    ] 

    @api.model
    def default_get(self, fields):
        res = super(dym_pettycash_line, self).default_get(fields)
        branch_id = self._context.get('branch_id',[])
        division = self._context.get('division',False)
        if branch_id:
            res['branch_id'] = branch_id
        kas_bon = self._context.get('kas_bon',False)
        if kas_bon:
            is_bon_sementara = self.env['account.account'].search([('is_bon_sementara','=',True)], limit=1)
            res['account_id'] = is_bon_sementara.id
        return res

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        dom = {}
        account_domain = ['&', ('active','=',True), ('type','!=','view')] 
        Filter = self.env['dym.account.filter']
        if self.pettycash_id.kas_bon == True:
            account_domain += Filter.get_domain_account("pettycash_kasbon")
        else:
            account_domain += Filter.get_domain_account("pettycash")
        dom['account_id'] = account_domain
        return {'domain':dom}

    @api.onchange('account_id')
    def onchange_account_id(self):
        dom = {}
        if self.account_id:
            self.name = self.account_id.name
            branch_id = self._context.get('branch_id',[])
            division = self._context.get('division',False)
            aa2_ids = self.env['analytic.account.filter'].get_analytics_2(branch_id, division, self.account_id.id)
            dom['analytic_2'] = [('id','in',[a2.id for a2 in aa2_ids])]
            if aa2_ids:
                self.analytic_2 = aa2_ids[0] 

        return {'domain':dom}

    @api.onchange('analytic_2')
    def onchange_analytic_2(self):
        dom = {}
        if self.analytic_2:
            branch_id = self._context.get('branch_id',[])
            division = self._context.get('division',False)
            aa3_ids = self.env['analytic.account.filter'].get_analytics_3(branch_id, division, self.account_id.id, self.analytic_2.code, self.analytic_2.id)
            dom['analytic_3'] = [('id','in',[a3.id for a3 in aa3_ids])]
            self.analytic_3 = aa3_ids[0]
        return {'domain':dom}

    @api.onchange('analytic_3')
    def onchange_analytic_3(self):
        dom = {}
        if self.analytic_2 and self.analytic_3:
            branch_id = self._context.get('branch_id',[])
            division = self._context.get('division',False)
            aa4_ids = self.env['analytic.account.filter'].get_analytics_4(branch_id, division, self.account_id.id, self.analytic_2.code, self.analytic_2.id, self.analytic_3.id)
            dom['analytic_4'] = [('id','in',[a2.id for a2 in aa4_ids])]
            self.analytic_4 = aa4_ids[0]
        return {'domain':dom}


    @api.onchange('kas_bon')
    def onchange_kas_bon(self):
        dom = {}
        return {'domain':dom}

    @api.model
    def create(self,vals):
        pettycash_id = False
        if 'pettycash_id' in vals:
            pettycash_id = self.env['dym.pettycash'].browse(vals['pettycash_id'])
        if pettycash_id and pettycash_id.kas_bon and 'name' in vals:
            vals['name'] = 'Pengeluaran Kasbon: %s' % vals['name']
        res = super(dym_pettycash_line, self).create(vals)
        return res

    @api.one
    def write(self, vals):
        if self.pettycash_id and self.pettycash_id.kas_bon and 'name' in vals:
            vals['name'] = 'Pengeluaran Kasbon: %s' % vals['name'].replace('Pengeluaran Kasbon: ','')
        return super(dym_pettycash_line, self).write(vals)

class AccountFilter(orm.Model):
    _inherit = "dym.account.filter"

    def _register_hook(self, cr):
        selection = self._columns['name'].selection
        if ('pettycash','Petty Cash') not in selection:         
            self._columns['name'].selection.append(
                ('pettycash', 'Petty Cash'))
        if ('pettycash_kasbon','Petty Cash Kas Bon') not in selection:         
            self._columns['name'].selection.append(
                ('pettycash_kasbon', 'Petty Cash Kas Bon'))
        return super(AccountFilter, self)._register_hook(cr)    
    
class dym_pc_journal_type(orm.Model):
    _inherit = "account.journal"
 
    def _register_hook(self, cr):
        selection = self._columns['type'].selection
        if ('pettycash','Petty Cash') not in selection:         
            self._columns['type'].selection.append(
                ('pettycash', 'Petty Cash'))
        return super(dym_pc_journal_type, self)._register_hook(cr)      
