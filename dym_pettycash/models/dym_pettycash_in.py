import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.osv import orm
from openerp.addons.dym_base import DIVISION_SELECTION

class dym_pettycash_in(models.Model):
    _name = "dym.pettycash.in"
    _description ="Petty Cash In"
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
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

    @api.one
    @api.depends('line_ids.amount_real')
    def _compute_amount(self):
        if self.line_ids:
            self.amount_real = sum(line.amount_real for line in self.line_ids)
                    
    @api.one
    @api.depends('line_ids.amount','pettycash_id.amount')
    def _get_amount(self):
        if self.line_ids:
            amount = self.pettycash_id.amount - sum(line.amount for line in self.line_ids)
            self.amount = amount

    @api.one
    @api.depends('line_ids.amount','pettycash_id.amount')
    def _get_total_cash_in(self):
        total_cash_in = sum(line.amount for line in self.line_ids)
        self.total_cash_in = total_cash_in

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
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    name = fields.Char(string="Name",readonly=True,default='')
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, default=_get_default_branch, domain=_getCompanyBranch)
    division = fields.Selection(DIVISION_SELECTION, string='Division', default='Umum', change_default=True, select=True)
    amount = fields.Float('Receive Amount', compute=_get_amount)
    branch_destination_id =  fields.Many2one('dym.branch', string='Branch Destination', required=True)
    journal_id = fields.Many2one('account.journal',string="Payment Method",domain="[('branch_id','in',[branch_id,False]),('type','=','pettycash')]")
    line_ids = fields.One2many('dym.pettycash.in.line','pettycash_id',string="PettyCash Line")
    line_ids2 = fields.One2many('dym.pettycash.in.line','pettycash_id',string="PettyCash Line")
    pay_supplier_invoice = fields.Boolean('Pay Supplier Invoice')
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date = fields.Date(string="Date",required=True,readonly=True,default=fields.Date.context_today)
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line',related='move_id.line_id',string='Journal Items', readonly=True)    
    period_id = fields.Many2one('account.period',string="Period",required=True, readonly=True,default=_get_period)
    account_id = fields.Many2one('account.account',string="Account")
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    pettycash_id = fields.Many2one('dym.pettycash',string='PCO (Kas Bon)',domain="[('state','=','posted'),('branch_id','=',branch_id),('division','=',division),('kas_bon','=',True),('cash_in_ids','=',False),('line_ids.settlement','=',False)]")
    pettycash_new_id = fields.Many2one('dym.pettycash',string='PCO (New)')
    pettycash_amount = fields.Float(related='pettycash_id.amount', string='Jumlah Kas Bon', readonly=True)
    journal_id_show = fields.Many2one(related='journal_id',store=True,readonly=True,string="Payment Method",domain="[('branch_id','=',branch_id),('type','=','pettycash')]")
    branch_destination_id_show =  fields.Many2one(related='branch_destination_id', string='Branch Destination',readonly=True,store=True)

    analytic_1 = fields.Many2one('account.analytic.account', 'Account Analytic Company')
    analytic_2 = fields.Many2one('account.analytic.account', 'Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center')

    balance = fields.Float('Balance')
    total_cash_in = fields.Float('Exepensed', compute=_get_total_cash_in)
    refund_all = fields.Boolean(string='Dikembalikan Semua', help='Cengtang jika uang tidak jadi digunakan, dikembalikan semua')

    date_cancel = fields.Date(string="Date Canceled",readonly=True)
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')

    _defaults = {
        'analytic_1':_get_analytic_company,
    }

    # @api.constrains('line_ids','pettycash_id')
    # def _constraint_amount(self):
    #     if self.amount < 0:
    #         raise osv.except_osv(('Perhatian !'), ("Amount di detail tidak boleh lebih besar dari Jumlah Kas Bon..."))

    @api.model
    def default_get(self, fields):
        res = super(dym_pettycash_in, self).default_get(fields)
        user = self.env.user
        if not user.branch_id:
            raise osv.except_osv(('Perhatian !'), ("User %s tidak memiliki default branch. Hubungi system administrator agar menambahkan default branch di User Setting." % self.env.user.name))
        if user.branch_type!='HO':
            res['division'] = 'Unit'
        else:
            res['division'] = 'Finance'
        return res

    @api.multi
    def get_equal_amount(self,pettycash_id,received_amount,pettycash):
        pco = self.env['dym.pettycash'].browse(pettycash_id)
        pco_amount = pco.amount
        total_expenses = 0.0
        for x in pettycash :
            total_expenses += x['amount']
        if pco_amount != total_expenses + received_amount:
            raise osv.except_osv(('Perhatian !'), ("Total Amount tidak sesuai, mohon cek kembali data Anda."))
        return True
            
    @api.model
    def create(self,vals,context=None):
        # if not vals['line_ids'] :
        #     raise osv.except_osv(('Perhatian !'), ("Detail belum diisi. Data tidak bisa di save."))
        pettycash = []
        rekap = []
        for x in vals['line_ids']:
            pettycash.append(x.pop(2))
        vals['date'] = datetime.today()
        if vals['journal_id'] :
            journal_obj = self.env['account.journal'].search([('id','=',vals['journal_id'])])
            vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], "PCI", division='Umum')
        if not vals['line_ids']:
            pettycash_id = super(dym_pettycash_in, self).create(vals)
        else:
            del[vals['line_ids']]
            equal_amount = self.get_equal_amount(vals['pettycash_id'],vals['amount'],pettycash)
            pettycash_id = super(dym_pettycash_in, self).create(vals)
            if pettycash_id:
                total_amount = 0
                for y in pettycash :
                    pettycash_pool = self.env['dym.pettycash.in.line']
                    pettycash_pool.create({
                        'pettycash_id':pettycash_id.id,
                        'name':y['name'],
                        'account_id':y['account_id'],
                        'amount':y['amount'],
                        'analytic_1': y['analytic_1'],
                        'analytic_2': y['analytic_2'],
                        'analytic_3': y['analytic_3'],
                        'analytic_4': y['analytic_4'],
                    })
                    if y['account_id'] in rekap :
                        raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada Account yang sama dalam detail transaksi"))
                    elif y['account_id'] not in rekap :
                        rekap.append(y['account_id'])
                    total_amount += y['amount']

                # if pettycash_id.pettycash_id.amount - total_amount < 0:
                #     raise osv.except_osv(('Perhatian !'), ("Amount di detail tidak boleh lebih besar dari Jumlah Kas Bon"))
            else :
                return False  
        return pettycash_id

    @api.onchange('division')
    def onchange_division(self):
        val = {}
        if self.branch_id and self.division:
            analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.branch_id.id, self.division, False, 4, 'General')
            self.analytic_1 = analytic_1
            self.analytic_2 = analytic_2
            self.analytic_3 = analytic_3
            self.analytic_4 = analytic_4
        self.pettycash_id = False
        val['line_ids'] = []
        return {'value':val}
        
    @api.onchange('pettycash_id','branch_id','division')
    def onchange_branch(self):
        dom = {}
        self.branch_destination_id = self.pettycash_id.branch_destination_id
        self.journal_id = self.pettycash_id.journal_id
        self.account_id = self.pettycash_id.account_id
        self.journal_id_show = self.pettycash_id.journal_id
        self.branch_destination_id_show = self.pettycash_id.branch_destination_id       
        self.pettycash_amount = self.pettycash_id.amount
        if self.branch_id and self.division:
            analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.branch_id, 'Umum', False, 4, 'General')
            self.analytic_1 = analytic_1
            self.analytic_2 = analytic_2
            self.analytic_3 = analytic_3
            self.analytic_4 = analytic_4
        return {'domain':dom}


    # @api.multi
    # def action_return_all(self):
    #     move_line_id = self.pettycash_id.move_ids.filtered(lambda s:s.debit>0)
    #     for rec in self:
    #         rec.refund_all = True
    #         rec.amount = move_line_id.debit 
    #         if not rec.line_ids:
    #             values = {
    #                 'name':move_line_id.name, 
    #                 'pettycash_id':rec.id,                                                                   
    #                 'account_id':move_line_id.account_id.id,
    #                 'amount':move_line_id.debit,
    #             }
    #             rec.write({'line_ids':[(0,0,values)]})

    @api.multi
    def action_cancel_return_all(self):
        for rec in self:
            rec.refund_all = False
            rec.amount = 0.0   
            if rec.line_ids:
                rec.write({'line_ids':[(6,0,[])]})

    @api.multi
    def post_pettycash_in(self):
        if not self.line_ids:
            view_id = self.env['ir.ui.view'].search([
                ("name", "=", "dym.pettycash.full.return.reason.wizard"), 
                ("model", "=", 'dym.pettycash.full.return.reason'),
            ])
            return {
                'name': _('Petty cash full refund reason'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'dym.pettycash.full.return.reason',
                'view_id': view_id.id,
                'domain': "[]",
                'target': 'new',
                'type': 'ir.actions.act_window',
            }
        self.action_move_line_create()
        self.action_update_amount_real()
        return True
    
    @api.multi
    def action_update_amount_real(self):
        pettycash = self.env['dym.pettycash.line']
        petty_in = {}
        srch_pettycash = pettycash.search([
            ('pettycash_id','=',self.pettycash_id.id),
            ])[0]
        amount = 0
        for x in self.line_ids :
            amount += x.amount
        if amount > 0:
            srch_pettycash.write({'amount_real':amount, 'settlement':True, 'amount_reimbursed':0})
        else:
            srch_pettycash.write({'settlement':True, 'amount_reimbursed':0})

    @api.multi
    def action_revise(self):
        pass

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
        return super(dym_pettycash_in,self).write(vals)
            
    @api.multi
    def cancel_pettycash(self):
        self.state = 'cancel'
        self.date_cancel = datetime.today()
        self.cancel_uid = self._uid
        self.cancel_date = datetime.now()
    
    @api.multi
    def action_move_line_create(self):
        move_pool = self.env['account.move']
        move_line_pool = self.env['account.move.line']
        pco_pool = self.env['dym.pettycash']
        petty_line = self.env['dym.pettycash.line']
        for pci in self:
            account_id = pci.journal_id.default_credit_account_id.id or pci.journal_id.default_debit_account_id.id
            amount = pci.amount
            periods = self.env['account.period'].find(pci.date)
            pci.write({'period_id':periods.id})

            # REVERSE PCO KASBON JOURNAL
            move_data = {
                'name': pci.name,
                'journal_id': pci.journal_id.id,
                'date': pci.date,
                'ref': pci.pettycash_id.name,
                'period_id': pci.period_id.id,
                'transaction_id': pci.id,
                'model': pci.__class__.__name__,
            }
            move_id = move_pool.create(move_data)
            for pml in self.pettycash_id.move_id.line_id:
                pml_data = {
                    'name': pml.name,
                    'ref': pml.ref,
                    'account_id': pml.account_id.id,
                    'move_id': move_id.id,
                    'journal_id': pml.journal_id.id,
                    'period_id': periods.id,
                    'date': pci.date,
                    'debit': pml.credit or 0.0,
                    'credit': pml.debit or 0.0,
                    'branch_id' : self.branch_id.id,
                    'division' : self.division,   
                    'analytic_account_id' :pml.analytic_4.id
                }
                line_id = move_line_pool.create(pml_data)

            if pci.line_ids:
                # CREATE NEW PCO
                new_pco_lines = []
                total_amount_real = 0.0
                total_amount = 0.0
                for tpl in pci.line_ids:
                    total_amount_real += tpl.amount
                    total_amount += tpl.amount             
                    new_pco_lines.append([0,False,{                
                        'branch_id': tpl.branch_id.id,
                        'division': tpl.division,
                        'name': tpl.name,
                        'account_id': tpl.account_id.id,
                        'amount': tpl.amount,
                        'kas_bon': False,
                        'amount_total': tpl.amount,
                        'amount_real': tpl.amount,
                        'amount_reimbursed': tpl.amount,
                        'analytic_1': tpl.analytic_1.id,
                        'analytic_2': tpl.analytic_2.id,
                        'analytic_3': tpl.analytic_3.id,
                        'analytic_4': tpl.analytic_4.id,
                        'analytic_4_readonly': tpl.analytic_4.id,
                    }])
                old_pco = pci.pettycash_id
                
                new_pco = {
                    "branch_id": self.branch_id.id,
                    "analytic_1": old_pco.analytic_1.id,
                    "analytic_2": old_pco.analytic_2.id,
                    "analytic_3": old_pco.analytic_3.id,
                    "analytic_4": old_pco.analytic_4.id,
                    "journal_id": old_pco.journal_id.id,
                    "amount_real": total_amount_real, 
                    "division": old_pco.division, 
                    "account_id": old_pco.account_id.id,
                    "branch_destination_id": old_pco.branch_destination_id.id,
                    "period_id": periods.id,
                    "date": pci.date,
                    "name": self.env['ir.sequence'].get_per_branch(self.branch_id.id, 'PCO', division=old_pco.division)  , 
                    "amount": total_amount, 
                    "kas_bon": False, 
                    "line_ids": new_pco_lines,
                    "cash_in": pci.id,
                }

                new_pco_id = pco_pool.create(new_pco)
                pci.pettycash_new_id = new_pco_id
                if pci.journal_id.entry_posted :    
                    posted = move_id.post()

            pci.write({
                'date':datetime.today(),
                'state': 'posted', 
                'move_id': move_id.id,
                'account_id':account_id,
                'confirm_uid':self.env.user.id,
                'confirm_date':datetime.now()
            })

        return True 

    '''
    @api.cr_uid_ids_context
    def action_move_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        petty_line = self.pool.get('dym.pettycash.line')
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
                'date': date,
                'ref':name,
                'period_id':period_id,
                'transaction_id':pettycash.id,
                'model':pettycash.__class__.__name__,
            }
            move_id = move_pool.create(cr, uid, move, context=None)

            if pettycash.refund_all:
                analytic_4 = pettycash.pettycash_id.analytic_4.id
                move_line1 = {
                    'name': _('PCO dikembalikah full'),
                    'ref':name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'date': date,
                    'debit': pettycash.pettycash_amount,
                    'credit': 0.0,
                    'branch_id' : pettycash.branch_destination_id.id,
                    'division' : pettycash.division,   
                    'analytic_account_id' :analytic_4   
                }      
                line_id = move_line_pool.create(cr, uid, move_line1, context)
                move_line2 = {
                    'name': _('PCO dikembalikah full'),
                    'ref':name,
                    'account_id': pettycash.pettycash_id.line_ids[0].account_id.id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'date': date,
                    'debit': 0.0,
                    'credit': pettycash.pettycash_amount,
                    'branch_id' : pettycash.branch_id.id,
                    'division' : pettycash.division,
                    'analytic_account_id' : pettycash.pettycash_id.line_ids[0].analytic_4.id     
                }
                line_id = move_line_pool.create(cr, uid, move_line2, context)
                if pettycash.journal_id.entry_posted:
                    posted = move_pool.post(cr, uid, [move_id], context=None)
                self.write(cr, uid, pettycash.id, {'date':datetime.today(),'state': 'posted', 'move_id': move_id,'account_id':account_id,'confirm_uid':uid,'confirm_date':datetime.now()})
            else:
                move_line1 = {
                    'name': _('PCO Kas Bon'),
                    'ref':name,
                    'account_id': pettycash.pettycash_id.line_ids[0].account_id.id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'date': date,
                    'debit': 0.0,
                    'credit': pettycash.pettycash_amount,
                    'branch_id' : pettycash.branch_id.id,
                    'division' : pettycash.division,
                    'analytic_account_id' : pettycash.pettycash_id.line_ids[0].analytic_4.id     
                }
                line_id = move_line_pool.create(cr, uid, move_line1, context)
                if pettycash.amount > 0:
                    move_line1 = {
                        'name': _('Cash Back'),
                        'ref':name,
                        'account_id': account_id,
                        'move_id': move_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'date': date,
                        'debit': pettycash.amount,
                        'credit': 0.0,
                        'branch_id' : pettycash.pettycash_id.branch_id.id,
                        'division' : pettycash.pettycash_id.division,
                        'analytic_account_id' : pettycash.pettycash_id.analytic_4.id     
                    }
                    line_id3 = move_line_pool.create(cr, uid, move_line1, context)

                if pettycash.amount < 0:
                    move_line2 = {
                        'name': _('PCO Kas Bon'),
                        'ref':name,
                        'account_id': account_id,
                        'move_id': move_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'date': date,
                        'debit': 0.0,
                        'credit': abs(pettycash.amount),
                        'branch_id' : pettycash.branch_id.id,
                        'division' : pettycash.division,
                        'analytic_account_id' : pettycash.pettycash_id.line_ids[0].analytic_4.id     
                    }
                    line_id = move_line_pool.create(cr, uid, move_line2, context)

                for y in pettycash.line_ids :
                    petty_line_src = petty_line.search(cr, uid, [('pettycash_id','=',pettycash.pettycash_id.id),('account_id','=',y.account_id.id)])
                    analytic_4 = False
                    if petty_line_src:
                        analytic_4 = petty_line.browse(cr, uid, petty_line_src[0]).analytic_4.id
                    total_expenses = y.amount
                    move_line_3 = {
                        'name': y.name,
                        'ref':name,
                        'account_id': y.account_id.id,
                        'move_id': move_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'date': date,
                        'debit': y.amount,
                        'credit': 0.0,
                        'branch_id' : pettycash.branch_destination_id.id,
                        'division' : pettycash.division,   
                        'analytic_account_id' :y.analytic_4.id
                    }
                    line_id2 = move_line_pool.create(cr, uid, move_line_3, context)
                if pettycash.journal_id.entry_posted :    
                    posted = move_pool.post(cr, uid, [move_id], context=None)
                self.write(cr, uid, pettycash.id, {'date':datetime.today(),'state': 'posted', 'move_id': move_id,'account_id':account_id,'confirm_uid':uid,'confirm_date':datetime.now()})
                move_line_uang_muka = pettycash.pettycash_id.move_ids.filtered(lambda r: r.debit > 0 and r.account_id.id == pettycash.pettycash_id.line_ids[0].account_id.id)
                reconcile_id = move_line_pool.reconcile_partial(cr, uid, [line_id] + move_line_uang_muka.ids, 'auto')
        return True 
    '''
    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Petty Cash in sudah diproses, data tidak bisa didelete !"))
        return super(dym_pettycash_in, self).unlink(cr, uid, ids, context=context)     
                           
    @api.cr_uid_ids_context   
    def create_intercompany_lines(self,cr,uid,ids,move_id,context=None):
        branch_rekap = {}       
        branch_pool = self.pool.get('dym.branch')        
        vals = self.browse(cr,uid,ids) 
        move_line = self.pool.get('account.move.line')
        move_line_srch = move_line.search(cr,uid,[('move_id','=',move_id)])
        move_line_brw = move_line.browse(cr,uid,move_line_srch)
        config = branch_pool.search(cr,uid,[('id','=',vals.branch_id.id)])
        if config :
            config_browse = branch_pool.browse(cr,uid,config)
            inter_branch_header_account_id = config_browse.inter_company_account_id.id
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
                branch = branch_pool.search(cr,uid,[('id','=',key.id)])
        
                if branch :
                    branch_browse = branch_pool.browse(cr,uid,branch)
                    inter_branch_detail_account_id = branch_browse.inter_company_account_id.id                
                    if not inter_branch_detail_account_id :
                        raise osv.except_osv(('Perhatian !'), ("Account Inter belum diisi dalam Master branch %s - %s!")%(key.code, key.name))

                balance = value['debit']-value['credit']
                debit = abs(balance) if balance < 0 else 0
                credit = balance if balance > 0 else 0
                
                if balance != 0:
                    move_line_create = {
                        'name': _('Interco Petty Cash In %s')%(key.name),
                        'ref':_('Interco Petty Cash In %s')%(key.name),
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
                        'name': _('Interco Petty Cash In %s')%(vals.branch_id.name),
                        'ref':_('Interco Petty Cash In %s')%(vals.branch_id.name),
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
           
class dym_pettycash_in_line(models.Model): 
    _name = "dym.pettycash.in.line"
    _description = "Petty Cash In Line"

    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_pettycash-2] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]
             
    pettycash_id = fields.Many2one('dym.pettycash.in',string="Petty Cash In")
    # refund_all = fields.Boolean(related='pettycash_id.refund_all')
    branch_id = fields.Many2one('dym.branch', related="pettycash_id.branch_id", store=True,)
    division = fields.Selection(DIVISION_SELECTION, string='Division', default='Umum', change_default=True, select=True, related="pettycash_id.division")
    
    invoice_id = fields.Many2one('account.invoice',string="Invoice")
    name = fields.Char(string="Description", required = True)
    account_id = fields.Many2one('account.account',string="Account",domain="[('type','!=','view')]")
    amount = fields.Float(string="Amount")

    analytic_1 = fields.Many2one('account.analytic.account', 'Account Analytic Company')
    analytic_2 = fields.Many2one('account.analytic.account', 'Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center')

    _defaults = {
        'analytic_1': _get_analytic_company,
    }

    _sql_constraints = [
        ('unique_name_pettycash_id', 'unique(account_id,pettycash_id)', 'Detail account duplicate, mohon cek kembali !'),
    ] 

    @api.onchange('account_id')
    def onchange_account_id(self):
        dom = {}
        account_domain = ['&', ('active','=',True), ('type','!=','view')] 
        Filter = self.env['dym.account.filter']
        account_domain += Filter.get_domain_account("pettycash")
        dom['account_id'] = account_domain
        if self.account_id:
            self.name = self.account_id.name
            aa2_ids = self.env['analytic.account.filter'].get_analytics_2(self.branch_id.id, self.division, self.account_id.id)
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
            if aa4_ids:
                dom['analytic_4'] = [('id','in',[a2.id for a2 in aa4_ids])]
                self.analytic_4 = aa4_ids[0]
        return {'domain':dom}

    @api.onchange('invoice_id')
    def onchange_invoice_id(self):
        dom = {}
        if self.invoice_id:
            self.name = ', '.join([i.name for i in self.invoice_id.invoice_line])
            self.amount = self.invoice_id.amount_total
            self.analytic_2 = self.invoice_id.analytic_2
            self.analytic_3 = self.invoice_id.analytic_3
            self.analytic_4 = self.invoice_id.analytic_4
            self.account_id = self.invoice_id.account_id.id
        config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
        dom['invoice_id'] = [
            ('consolidated','=',True),
            ('type','=','in_invoice'),
            ('state','=','open'),                
            ('residual','>',0),
        ]
        if config and config.petty_cash_limit:
            dom['invoice_id'].append(('amount_total','<=',config.petty_cash_limit))
        return {'domain':dom}

    @api.onchange('amount')
    def amount_change(self):    
        warning = {}     
        if self.amount < 0 :
            self.amount = 0 
            warning = {
                'title': ('Perhatian !'),
                'message': (("Nilai amount tidak boleh kurang dari 0")),
            }                      
        return {'warning':warning}     
