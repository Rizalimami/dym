import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class dym_reimbursed_bank(models.Model):
    _name = "dym.reimbursed.bank"
    _description ="Reimbursed Bank"
    _inherit = ['mail.thread']
        
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('requested', 'Requested'),
        ('nextrequest', 'Next Requested'),
        ('norequest', 'No Requested'),
        ('req2ho', 'Requested to HO'), #Saat dipanggil oleh tranfer request
        ('hoapproved', 'HO Approved'), #Saat orang HO pencet oleh tranfer request
        ('horejected', 'HO Rejected'), #Saat orang HO pencet oleh tranfer request
        ('paid', 'HO Paid'),
        ('cancel', 'Cancelled'),
    ]   

    @api.depends('period_id')
    def _get_period(self):
        for x in self.search([]):
            print "---->",x

        periods = self.env['account.period'].find()
        return periods and periods[0] or False

    @api.one
    @api.depends('line_ids.amount')
    def _compute_amount(self):
        total_debit = sum(line.debit for line in self.line_ids)
        total_credit = sum(line.credit for line in self.line_ids)
        self.amount_total = total_credit - total_debit

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil 

    @api.one
    @api.depends('line_ids')            
    def _count_detail_payslip(self):
        bank_ids = []
        count = 0
        for line in self.line_ids:
            if line.bank_id.id in bank_ids:
                continue
            count += 1
            bank_ids.append(line.bank_id.id)
        self.bank_count = count

    def ubah_tanggal(self,tanggal):
        try:
            conv = datetime.strptime(tanggal, '%d-%m-%Y %H:%M')
            return conv.strftime('%d-%m-%Y')
        except Exception as e:
            conv = datetime.strptime(tanggal, '%Y-%m-%d %H:%M:%S')
            return conv.strftime('%d-%m-%Y')

    def ubah_tanggal_2(self,tanggal):
        try:
            conv = datetime.strptime(tanggal, '%d-%m-%Y')
            return conv.strftime('%d-%m-%Y')
        except Exception as e:
            conv = datetime.strptime(tanggal, '%Y-%m-%d')
            return conv.strftime('%d-%m-%Y')

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
    period_start = fields.Many2one('account.period', string="Period Start", required=True, default=_get_period)
    period_end = fields.Many2one('account.period', string="Period End")
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, domain=_getCompanyBranch)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], string='Division', default='Umum', change_default=True, select=True)
    journal_id = fields.Many2one('account.journal',string="Payment Method",domain="[('branch_id','in',[branch_id,False]),('type','=','bank')]")
    state = fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date = fields.Date(string="Date Requested",required=True,readonly=True,default=fields.Date.context_today)
    date_approve = fields.Date(string="Date Approved",readonly=True)
    date_cancel = fields.Date(string="Date Canceled",readonly=True)
    amount_total = fields.Float(string='Total Amount',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    confirm_uid = fields.Many2one('res.users',string="Requested by")
    confirm_date = fields.Datetime('Requested on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    line_ids = fields.One2many('dym.reimbursed.bank.line','reimbursed_id')
    notes = fields.Char('Notes')

    @api.model
    def default_get(self, fields):
        res = super(dym_reimbursed_bank, self).default_get(fields)
        user = self.env.user
        if not user.branch_id:
            raise osv.except_osv(('Perhatian !'), ("User %s tidak memiliki default branch. Hubungi system administrator agar menambahkan default branch di User Setting." % self.env.user.name))
        res['branch_id'] = user.branch_id.id
        if user.branch_type!='HO':
            res['division'] = 'Finance'
        else:
            raise osv.except_osv(('Perhatian !'), ("User %s tidak diijinkan untuk membuat transaksi ini." % self.env.user.name))
        return res

    @api.onchange('period_start')
    def onchange_period_start(self):
        dom = {}
        if self.period_start:
            periods = self.env['account.period'].search([('date_start','>=',self.period_start.date_start)])
            dom['period_end'] = [('id','in',periods.ids)]
        return {'domain':dom}

    @api.onchange('period_start','period_end')
    def onchange_periods(self):
        self._action_compute_lines()

    @api.multi
    def action_validate(self):
        warning = {}
        if not self.line_ids:
            raise osv.except_osv(('Perhatian !'), ("TidaK ditemukan baris baris transaksi, silahkan Compute dulu. Tapi jika ternyata memang tidak ada transaksi pada periode yang dipilih, silahkan coba lagi periode berikutnya."))
        else:
            self.name = self.env['ir.sequence'].get_per_branch(self.branch_id.id, 'RBK', division=self.division)  
            self.action_post()

    @api.multi
    def action_post(self):
        self.state = 'posted'

    @api.multi
    def action_draft(self):
        self.state = 'draft'

    @api.multi
    def action_compute(self):
        return self._action_compute_lines()

    @api.multi
    def _action_compute_lines(self):
        res = {}
        Voucher = self.env['account.voucher']
        vouchers = Voucher.search([
            ('period_id','>=',self.period_start.id),
            ('period_id','<=',self.period_end.id),
            ('journal_id','=',self.journal_id.id),            
            ('journal_id.type','in',['bank']),
            ('type','in',('receipt','payment')),
            ('state','=','posted'),
            ('move_id','!=',False),
            ('transaction_type','in',('in','out'))
        ], order="date")
        lines = []
        for voucher in vouchers:
            for ml in voucher.move_id.line_id:
                if voucher.transaction_type == 'in' and ml.credit == 0.0:
                    continue
                if voucher.transaction_type == 'out' and ml.debit == 0.0:
                    continue
                values = {
                    'voucher_id': voucher.id,
                    'name': ml.name,
                    'date': voucher.date,
                    'account_id': ml.account_id.id,
                    'debit': ml.credit,
                    'credit': ml.debit,
                }
                lines.append((0,0,values))
        self.line_ids.unlink()
        self.write({'line_ids':lines})
        return res

    # def button_bank_out(self,cr,uid,ids,context=None):
    #     mod_obj = self.pool.get('ir.model.data')        
    #     act_obj = self.pool.get('ir.actions.act_window')        
    #     result = mod_obj.get_object_reference(cr, uid, 'dym_bank', 'bank_action')        
    #     id = result and result[1] or False        
    #     result = act_obj.read(cr, uid, [id], context=context)[0]
    #     val = self.browse(cr, uid, ids)
    #     bank_ids = []
    #     for line in val.line_ids:
    #         bank_ids.append(line.bank_id.id)
    #     if bank_ids:
    #         result['domain'] = "[('id','in',"+str(bank_ids)+")]"
    #     else:
    #         res = mod_obj.get_object_reference(cr, uid, 'dym_bank', 'bank_tree_view')
    #         result['views'] = [(res and res[1] or False, 'tree')]
    #         result['res_id'] = False 
    #     return result
    
    @api.cr_uid_ids_context
    def button_dummy(self, cr, uid, ids, context=None):
        return True
                
    # @api.model
    # def create(self,vals,context=None):
    #     if not vals['line_ids'] :
    #         raise osv.except_osv(('Perhatian !'), ("Detail belum diisi. Data tidak bisa di save."))
 
    #     rekap = []
    #     vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'RPC', division='Umum')       
    #     vals['date'] = datetime.today()
        
    #     reimbursed_id = super(dym_reimbursed_bank, self).create(vals)
    #     if reimbursed_id :         
    #         for x in self.search([('id','=',reimbursed_id.id)]).line_ids:
    #             if (str(x.bank_id.id) + ' - ' + str(x.account_id.id)) in rekap :
    #                 raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada Bank-Account yang sama dalam detail transaksi"))
    #             elif (str(x.bank_id.id) + ' - ' + str(x.account_id.id)) not in rekap :
    #                 rekap.append((str(x.bank_id.id) + ' - ' + str(x.account_id.id)))
    #     else :
    #         return False
    #     return reimbursed_id 
        
    # @api.multi
    # def action_update_amount_reimbursed(self, act, bank_id, account_id, amount):
    #     voucher_line = self.env['account.voucher.line']
    #     srch_bank = voucher_line.search([
    #        ('bank_id','=',bank_id),
    #        ('account_id','=',account_id)
    #     ])
    #     petty_obj = self.env['account.voucher'].browse(bank_id)
    #     if petty_obj.kas_bon == True and petty_obj.line_ids:
    #         srch_bank = petty_obj.line_ids[0]
    #     if amount <= 0:
    #         raise osv.except_osv(('Perhatian !'), ("Nilai Amount tidak boleh 0"))
    #     if not srch_bank:
    #         bank_name = self.env['account.voucher'].search([
    #            ('id','=',bank_id)
    #            ]).name
    #         account_name = self.env['account.account'].search([
    #            ('id','=',account_id)
    #            ]).name
    #         raise osv.except_osv(('Perhatian !'), (("Data Bank %s - Account %s tidak ditemukan")%(bank_name, account_name)))
    #     if srch_bank and act == 'cancel':
    #         cashback = srch_bank.amount_reimbursed - amount
    #         srch_bank.write({'amount_reimbursed':cashback})
    #     if srch_bank and act == 'request':
    #         cashback = srch_bank.amount_reimbursed + amount
    #         if cashback < 0:
    #             raise osv.except_osv(('Perhatian !'), (("Nilai amount Bank %s - Account %s tidak boleh lebih dari Rp.%s")%(srch_bank.bank_id.name, srch_bank.account_id.name, srch_bank.amount_real - srch_bank.amount_reimbursed)))
    #         srch_bank.write({'amount_reimbursed':cashback})
    #     bank_obj = self.env['account.voucher'].search([('id','=',bank_id)])
    #     amount_sisa = bank_obj.amount_real - bank_obj.amount_reimbursed
    #     return amount_sisa

    # @api.multi
    # def cancel(self):
    #     bank = self.env['account.voucher']
    #     for x in self.line_ids :
    #         if self.state != 'draft':
    #             cashback = self.action_update_amount_reimbursed('cancel', x.bank_id.id, x.account_id.id, x.amount)
    #             x.bank_id.write({'state':'posted'})
    #     self.state = 'cancel'
    #     self.date_cancel = datetime.today()
    #     self.cancel_uid = self._uid
    #     self.cancel_date = datetime.now()
    
    # @api.multi
    # def request(self):
    #     bank = self.env['account.voucher']
    #     cash = ''
    #     for x in self.line_ids:
    #         cashback = self.action_update_amount_reimbursed('request', x.bank_id.id, x.account_id.id, x.amount)
    #         if cashback > 0:
    #             cash += ('- '+str(x.bank_id.name)+' (Partial)<br/>')
    #         else:
    #             x.bank_id.write({'state':'reimbursed'})
    #             cash += ('- '+str(x.bank_id.name)+' (Full)<br/>')
    #     self.message_post(body=_("Reimbursed Requested Bank No: <br/>%s")%(cash))                             
    #     self.state = 'request'
    #     self.confirm_uid = self._uid
    #     self.confirm_date = datetime.now()
    #     self.date = datetime.today()
        
    # @api.cr_uid_ids_context
    # def onchange_bank(self, cr, uid, ids,branch_id,division,journal_id,context=None):
    #     bank = self.pool.get('account.voucher')
    #     date_start = ''
    #     date_end = ''
    #     if context is None:
    #         context = {}
    #     if branch_id is None :
    #         context = {}
    #     if journal_id is None :
    #         context = {}
    #     if division is None :
    #         context = {}            
    #     if branch_id and journal_id and division :
    #         bank_search = bank.search(cr,uid,[
    #             ('branch_id','=',branch_id),
    #             ('journal_id','=',journal_id),
    #             ('division','=',division),
    #             ('state','=','posted'),
    #             ('amount_real','>',0)
    #         ])
    #         petty = []
    #         if not bank_search :
    #             petty = []
    #         elif bank_search :
    #             bank_brw = bank.browse(cr,uid,bank_search)
    #             for x in bank_brw:
    #                 if not date_start:
    #                     date_start = x.date
    #                 if not date_end:
    #                     date_end = x.date
    #                 if date_start > x.date:
    #                     date_start = x.date
    #                 if date_end < x.date:
    #                     date_end = x.date

    #                 if x.kas_bon == False:
    #                     for line in x.line_ids:
    #                         if line.amount_real - line.amount_reimbursed == 0.0:
    #                             continue
    #                         petty.append([0,0,{
    #                             'name':str(line.name), 
    #                             'bank_id':x.id,                                                                   
    #                             'account_id':line.account_id.id,
    #                             'amount':line.amount_real - line.amount_reimbursed,
    #                         }])
    #                 else:
    #                     pci_id = self.pool.get('account.voucher.in').search(cr, uid, [('bank_id','=',x.id),('state','=','posted')])
    #                     if pci_id:
    #                         continue

    #                     petty_in_id = self.pool.get('account.voucher.in.line').search(cr, uid, [('bank_id.refund_all','!=',True),('bank_id.bank_id','=',x.id)])
    #                     petty_in = self.pool.get('account.voucher.in.line').browse(cr, uid, petty_in_id)
    #                     for line in petty_in:
    #                         if line.amount == 0.0:
    #                             continue
    #                         petty.append([0,0,{
    #                             'name':str(line.name), 
    #                             'bank_id':x.id,                                                                   
    #                             'account_id':line.account_id.id,
    #                             'amount':line.amount,
    #                         }])
    #         notes = ''
    #         if date_start and date_end:
    #             branch_code = self.pool.get('dym.branch').browse(cr, uid, branch_id, context=context) 
    #             notes = '[%s] Penggantian KK tgl %s - %s' % (
    #                 branch_code[0].code,
    #                 datetime.strptime(date_start,'%Y-%m-%d').strftime('%d/%m/%Y'),
    #                 datetime.strptime(date_end,'%Y-%m-%d').strftime('%d/%m/%Y'),
    #             )
    #         return {'value':{'line_ids':petty,'notes':notes}}   

    # @api.multi
    # def approve(self):
    #     bank = self.env['account.voucher']
    #     cash = ''
    #     for x in self.line_ids :
    #         cash += ('- '+str(x.bank_id.name)+'<br/>')
    #     self.message_post(body=_("Reimbursed Approved <br/> Bank No : <br/>  %s ")%(cash))                             
    #     self.state = 'approved'
    #     self.date_approve = datetime.today()

    # @api.cr_uid_ids_context        
    # def write(self, cr, uid, ids, vals, context=None):
    #     if context is None:
    #         context = {}
    #     reimbursed = self.browse(cr,uid,ids)
    #     petty = vals.get('line_ids', False)
    #     delcash = ''
    #     addcash = ''
    #     editcash = ''
    #     if petty:
    #         # del[vals['line_ids']]
    #         for x,item in enumerate(petty) :
    #             line_id = item[1]
    #             line = self.pool.get('dym.reimbursed.bank.line').browse(cr, uid, [line_id])
    #             if item[0] == 2 :
    #                 if reimbursed.state == 'request':
    #                     cashback = self.action_update_amount_reimbursed(cr, uid, ids, 'cancel', line.bank_id.id, line.account_id.id, line.amount)
    #                     line.bank_id.write({'state':'posted'})
    #                 delcash += ('- '+str(line.bank_id.name)+'<br/>')
    #             elif item[0] == 0 :
    #                 value = item[2]
    #                 bank = self.pool.get('account.voucher').browse(cr, uid, [value['bank_id']])
    #                 if reimbursed.state == 'request':
    #                     cashback = self.action_update_amount_reimbursed(cr, uid, ids, 'request', value['bank_id'], value['account_id'], value['amount'])
    #                     if cashback == 0:
    #                         bank.write({'state':'reimbursed'})
    #                 addcash += ('- '+str(bank.name)+'<br/>')
    #             elif item[0] == 1:
    #                 value = item[2]
    #                 if reimbursed.state == 'request' and 'amount' in value:
    #                     cashback_cancel = self.action_update_amount_reimbursed(cr, uid, ids, 'cancel', line.bank_id.id, line.account_id.id, line.amount)
    #                     cashback_request = self.action_update_amount_reimbursed(cr, uid, ids, 'request', line.bank_id.id, line.account_id.id, value['amount'])
    #                     if cashback_request == 0:
    #                         line.bank_id.write({'state':'reimbursed'})
    #                     else:
    #                         line.bank_id.write({'state':'posted'})
    #                     editcash += ('- '+str(line.bank_id.name)+' ('+str(value['amount'])+')<br/>')
    #     update = super(dym_reimbursed_bank, self).write(cr, uid, ids, vals, context=context) 
    #     rekap = []
    #     for x in reimbursed.line_ids:
    #         if (str(x.bank_id.id) + ' - ' + str(x.account_id.id)) in rekap :
    #             raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada Bank-Account yang sama dalam detail transaksi"))
    #         elif (str(x.bank_id.id) + ' - ' + str(x.account_id.id)) not in rekap :
    #             rekap.append((str(x.bank_id.id) + ' - ' + str(x.account_id.id)))
    #     if delcash or editcash or addcash :
    #         message = ''
    #         if addcash:
    #             message += ("Add Bank No <br/> %s")%(addcash)
    #         if editcash:
    #             message += ("Edit Amount Bank No <br/> %s")%(editcash)
    #         if delcash:
    #             message += ("Delete Bank No <br/> %s")%(delcash)
    #         self.message_post(cr, uid, reimbursed.id, body=_("%s")%(message), context=context)
    #     return update

    # @api.cr_uid_ids_context
    # def unlink(self, cr, uid, ids, context=None):
    #     for item in self.browse(cr, uid, ids, context=context):
    #         if item.state != 'draft':
    #             raise osv.except_osv(('Perhatian !'), ("Reimbursed Bank sudah diproses, sata tidak bisa didelete !"))
    #     return super(dym_reimbursed_bank, self).unlink(cr, uid, ids, context=context)        

class dym_reimbursed_bank_line(models.Model):
    _name = "dym.reimbursed.bank.line"
    _description ="Reimbursed Bank Line"
    
    reimbursed_id = fields.Many2one('dym.reimbursed.bank')  
    state = fields.Selection(related='reimbursed_id.state', readonly=True)
    date = fields.Date('Date')
    voucher_id = fields.Many2one('account.voucher', string='Bank', domain="[('bank_reimburse_ids','=',False),('journal_id','=',parent.journal_id),('branch_id','=',parent.branch_id),('state','=','posted')]")
    name = fields.Char(string="Description", required=True)
    account_id = fields.Many2one('account.account', string="Account", domain="[('type','!=','view')]")
    debit = fields.Float(string="Debit")
    credit = fields.Float(string="Credit")
    amount = fields.Float(string="Credit")


    # @api.onchange('bank_id')
    # def bank_change(self):
    #     if not self.reimbursed_id.branch_id or not self.reimbursed_id.division or not self.reimbursed_id.journal_id:
    #         raise osv.except_osv(('Attention!'), ('Sebelum menambah detil transaksi,\n harap isi data header terlebih dahulu.'))
    #     dom = []
    #     for x in self.bank_id.line_ids :
    #         if x.amount_real - x.amount_reimbursed > 0:
    #             dom.append(x.account_id.id)
    #     self.account_id = False
    #     self.name = ''
    #     # self.balance = 0
    #     self.amount = 0
    #     return {'domain' : {'account_id':[('id','in',dom)]}}  
    
    # @api.onchange('account_id')
    # def account_change(self):
    #     desc = ''
    #     balance = 0
    #     petty_line = self.env['account.voucher.line']
    #     petty_brw = petty_line.search([('bank_id','=',self.bank_id.id)])
    #     for x in petty_brw :
    #         if x.account_id == self.account_id:
    #             desc = str(x.name)
    #             balance = x.amount_real - x.amount_reimbursed
    #     self.name = desc
    #     # self.balance = balance
    #     self.amount = balance

    # @api.onchange('amount')
    # def onchange_amount(self):
    #     warning = {}
    #     # if self.amount:
    #     #     petty_line = self.env['account.voucher.line']
    #     #     petty_brw = petty_line.search([('bank_id','=',self.bank_id.id)])
    #     #     for x in petty_brw :
    #     #         if self.account_id == x.account_id :
    #     #             if self.amount > x.amount_real :
    #     #                 self.amount = False
    #     #                 warning = {
    #     #                     'title': ('Perhatian !'),
    #     #                     'message': (("Nilai amount tidak boleh lebih dari Rp.%s")%(x.amount_real)),
    #     #                 }  
    #     return {'warning':warning}
    
    # @api.onchange('amount')
    # def amount_change(self):    
    #     warning = {}     
    #     if self.amount < 0 :
    #         self.amount = 0 
    #         warning = {
    #             'title': ('Perhatian !'),
    #             'message': (("Nilai amount tidak boleh kurang dari 0")),
    #         }                      
    #     return {'warning':warning}    