import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from ..report import fungsi_terbilang
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

class dym_reimbursed(models.Model):
    _name = "dym.reimbursed"
    _description ="Reimbursed Petty Cash"
    _inherit = ['mail.thread']
        
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('request', 'Requested'),
        ('approved', 'Approved'),
        ('req2ho', 'Requested to HO'), #Saat dipanggil oleh tranfer request
        ('hoapproved', 'HO Approved'), #Saat orang HO pencet oleh tranfer request
        ('horejected', 'HO Rejected'), #Saat orang HO pencet oleh tranfer request
        ('paid', 'HO Paid'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ]   

    @api.one
    @api.depends('line_ids.amount')
    def _compute_amount(self):
        self.amount_total = sum(line.amount for line in self.line_ids)

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
        pettycash_ids = []
        count = 0
        for line in self.line_ids:
            if line.pettycash_id.id in pettycash_ids:
                continue
            count += 1
            pettycash_ids.append(line.pettycash_id.id)
        self.pettycash_count = count

    def ubah_tanggal(self,tanggal):
        if not tanggal:
            return ''
        tanggal = tanggal[:10]
        try:
            conv = datetime.strptime(tanggal, DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%m-%Y')
        except:
            return tanggal
        return conv

        # except Exception as e:
        #     conv = datetime.strptime(tanggal, '%Y-%m-%d %H:%M:%S')
        #     return conv.strftime('%d-%m-%Y')

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
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, domain=_getCompanyBranch)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], string='Division', default='Umum', change_default=True, select=True)
    journal_id = fields.Many2one('account.journal',string="Payment Method",domain="[('branch_id','in',[branch_id,False]),('type','=','pettycash')]")
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date_request = fields.Date(string="Date Requested",required=True,readonly=True,default=fields.Date.context_today)
    date_approve = fields.Date(string="Date Approved",readonly=True)
    date_cancel = fields.Date(string="Date Canceled",readonly=True)
    amount_total = fields.Float(string='Total Amount',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    confirm_uid = fields.Many2one('res.users',string="Requested by")
    confirm_date = fields.Datetime('Requested on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    pettycash_count = fields.Integer(compute=_count_detail_payslip, string="Items")
    # line_ids = fields.One2many('dym.reimbursed.line', 'reimbursed_id', string='Pettycash')
    # pettycash_ids = fields.One2many('dym.pettycash', string='Pettycash', compute='_compute_pettycash')
    pettycash_ids = fields.Many2many('dym.pettycash', 'reimbursed_pettycash_rel','reimbursed_id','pettycash_id', string='Pettycash')
    line_ids = fields.One2many('dym.reimbursed.line', 'reimbursed_id', string='Pettycash', compute='_compute_pettycash', store=True)
    notes = fields.Char('Notes')

    @api.depends('pettycash_ids')
    def _compute_pettycash(self):
        if self.pettycash_ids:
            vals = []
            for pc in self.pettycash_ids:
                for line in pc.line_ids:
                    vals.append((0,0,{
                        'name':str(line.name), 
                        'pettycash_id':pc.id,                                                                   
                        'account_id':line.account_id.id,
                        'amount':line.amount,                    
                    }))
            self.line_ids = vals

    @api.model
    def default_get(self, fields):
        res = super(dym_reimbursed, self).default_get(fields)
        user = self.env.user
        if user.branch_type=='HO':
            pass
        elif not user.branch_id:
            raise osv.except_osv(('Perhatian !'), ("User %s tidak memiliki default branch. Hubungi system administrator agar menambahkan default branch di User Setting." % self.env.user.name))
        if user.branch_type!='HO':
            res['division'] = 'Unit'
        else:
            res['division'] = 'Finance'
        res['branch_id'] = user.branch_id.id
        journal_id = self.env['account.journal'].search([('type','=','pettycash')], limit=1)
        if journal_id:
            res['journal_id'] = journal_id.id
        return res


    def button_pettycash_out(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')        
        act_obj = self.pool.get('ir.actions.act_window')        
        result = mod_obj.get_object_reference(cr, uid, 'dym_pettycash', 'pettycash_action')        
        id = result and result[1] or False        
        result = act_obj.read(cr, uid, [id], context=context)[0]
        val = self.browse(cr, uid, ids)
        pettycash_ids = []
        for line in val.line_ids:
            pettycash_ids.append(line.pettycash_id.id)
        if pettycash_ids:
            result['domain'] = "[('id','in',"+str(pettycash_ids)+")]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'dym_pettycash', 'pettycash_tree_view')
            result['views'] = [(res and res[1] or False, 'tree')]
            result['res_id'] = False 
        return result
    
    @api.cr_uid_ids_context
    def button_dummy(self, cr, uid, ids, context=None):
        return True
                
    @api.model
    def create(self,vals,context=None):
        if not vals.get('pettycash_ids',False):
            raise osv.except_osv(('Perhatian !'), ("Detail belum diisi. Data tidak bisa di save."))
 
        rekap = []
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'RPC', division='Umum')       
        vals['date_request'] = datetime.today()
        
        reimbursed_id = super(dym_reimbursed, self).create(vals)
        if reimbursed_id :         
            for x in self.search([('id','=',reimbursed_id.id)]).line_ids:
                if (str(x.pettycash_id.id) + ' - ' + str(x.account_id.id)) in rekap :
                    raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada Pettycash-Account yang sama dalam detail transaksi"))
                elif (str(x.pettycash_id.id) + ' - ' + str(x.account_id.id)) not in rekap :
                    rekap.append((str(x.pettycash_id.id) + ' - ' + str(x.account_id.id)))
        else :
            return False
        return reimbursed_id 
        
    @api.multi
    def action_update_amount_reimbursed(self, act, pettycash_id, account_id, amount):
        pettycash = self.env['dym.pettycash.line']
        srch_pettycash = pettycash.search([
           ('pettycash_id','=',pettycash_id),
           ('account_id','=',account_id)
        ])
        petty_obj = self.env['dym.pettycash'].browse(pettycash_id)
        if petty_obj.kas_bon == True and petty_obj.line_ids:
            srch_pettycash = petty_obj.line_ids[0]
        if amount <= 0:
            raise osv.except_osv(('Perhatian !'), ("Nilai Amount tidak boleh 0"))
        if not srch_pettycash:
            pettycash_name = self.env['dym.pettycash'].search([
               ('id','=',pettycash_id)
               ]).name
            account_name = self.env['account.account'].search([
               ('id','=',account_id)
               ]).name
            raise osv.except_osv(('Perhatian !'), (("Data Pettycash %s - Account %s tidak ditemukan")%(pettycash_name, account_name)))
        if srch_pettycash and act == 'cancel':
            cashback = srch_pettycash.amount_reimbursed - amount
            srch_pettycash.write({'amount_reimbursed':cashback})
        if srch_pettycash and act == 'request':
            cashback = srch_pettycash.amount_reimbursed + amount
            if cashback < 0:
                raise osv.except_osv(('Perhatian !'), (("Nilai amount Pettycash %s - Account %s tidak boleh lebih dari Rp.%s")%(srch_pettycash.pettycash_id.name, srch_pettycash.account_id.name, srch_pettycash.amount_real - srch_pettycash.amount_reimbursed)))
            srch_pettycash.write({'amount_reimbursed':cashback})
        pettycash_obj = self.env['dym.pettycash'].search([('id','=',pettycash_id)])
        amount_sisa = pettycash_obj.amount_real - pettycash_obj.amount_reimbursed
        return amount_sisa

    @api.multi
    def cancel(self):
        pettycash = self.env['dym.pettycash']
        for x in self.line_ids :
            if self.state != 'draft':
                cashback = self.action_update_amount_reimbursed('cancel', x.pettycash_id.id, x.account_id.id, x.amount)
                x.pettycash_id.write({'state':'posted'})
        self.state = 'cancel'
        self.date_cancel = datetime.today()
        self.cancel_uid = self._uid
        self.cancel_date = datetime.now()
    
    @api.multi
    def request(self):
        pettycash = self.env['dym.pettycash']
        cash = ''
        for x in self.line_ids:
            cashback = self.action_update_amount_reimbursed('request', x.pettycash_id.id, x.account_id.id, x.amount)
            if cashback > 0:
                cash += ('- '+str(x.pettycash_id.name)+' (Partial)<br/>')
            else:
                x.pettycash_id.write({'state':'reimbursed'})
                cash += ('- '+str(x.pettycash_id.name)+' (Full)<br/>')
        self.message_post(body=_("Reimbursed Requested Petty Cash No: <br/>%s")%(cash))                             
        self.state = 'request'
        self.confirm_uid = self._uid
        self.confirm_date = datetime.now()
        self.date_request = datetime.today()
        
    @api.cr_uid_ids_context
    def onchange_pettycash(self, cr, uid, ids,branch_id,division,journal_id,context=None):
        value = {}
        pettycash = self.pool.get('dym.pettycash')
        date_start = ''
        date_end = ''
        if context is None:
            context = {}
        if branch_id is None :
            context = {}
        if journal_id is None :
            context = {}
        if division is None :
            context = {}            
        if branch_id and journal_id and division :
            pettycash_search = pettycash.search(cr,uid,[
                ('branch_id','=',branch_id),
                ('journal_id','=',journal_id),
                ('kas_bon','=',False),
                ('division','=',division),
                ('state','=','posted'),
                ('amount_real','>',0)
            ], order='date')

            if not pettycash_search:
                raise osv.except_osv(('Perhatian !'), ("Maaf, saat ini tidak ada transaksi PCO yang dapat direimburse.!"))

            pcs_ids = pettycash.search(cr,uid,[('id','in',pettycash_search)], order='date asc', limit=1)
            pce_ids = pettycash.search(cr,uid,[('id','in',pettycash_search)], order='date desc', limit=1)

            date_start = pettycash.browse(cr, uid, pcs_ids, context=context).date
            date_end = pettycash.browse(cr, uid, pce_ids, context=context).date

            petty = []
            if not pettycash_search :
                petty = []
            elif pettycash_search:
                value['pettycash_ids'] = pettycash_search

            notes = ''
            if date_start and date_end:
                branch_code = self.pool.get('dym.branch').browse(cr, uid, branch_id, context=context) 
                notes = '[%s] Penggantian KK tgl %s - %s' % (
                    branch_code[0].code,
                    datetime.strptime(date_start,'%Y-%m-%d').strftime('%d/%m/%Y'),
                    datetime.strptime(date_end,'%Y-%m-%d').strftime('%d/%m/%Y'),
                )
            value['notes'] = notes
            return {'value':value}

    @api.multi
    def approve(self):
        pettycash = self.env['dym.pettycash']
        cash = ''
        for x in self.line_ids :
            cash += ('- '+str(x.pettycash_id.name)+'<br/>')
        self.message_post(body=_("Reimbursed Approved <br/> Petty Cash No : <br/>  %s ")%(cash))                             
        self.state = 'approved'
        self.date_approve = datetime.today()

    @api.cr_uid_ids_context        
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        reimbursed = self.browse(cr,uid,ids)
        petty = vals.get('line_ids', False)
        delcash = ''
        addcash = ''
        editcash = ''
        if petty:
            # del[vals['line_ids']]
            for x,item in enumerate(petty) :
                line_id = item[1]
                line = self.pool.get('dym.reimbursed.line').browse(cr, uid, [line_id])
                if item[0] == 2 :
                    if reimbursed.state == 'request':
                        cashback = self.action_update_amount_reimbursed(cr, uid, ids, 'cancel', line.pettycash_id.id, line.account_id.id, line.amount)
                        line.pettycash_id.write({'state':'posted'})
                    delcash += ('- '+str(line.pettycash_id.name)+'<br/>')
                elif item[0] == 0 :
                    value = item[2]
                    pettycash = self.pool.get('dym.pettycash').browse(cr, uid, [value['pettycash_id']])
                    if reimbursed.state == 'request':
                        cashback = self.action_update_amount_reimbursed(cr, uid, ids, 'request', value['pettycash_id'], value['account_id'], value['amount'])
                        if cashback == 0:
                            pettycash.write({'state':'reimbursed'})
                    addcash += ('- '+str(pettycash.name)+'<br/>')
                elif item[0] == 1:
                    value = item[2]
                    if reimbursed.state == 'request' and 'amount' in value:
                        cashback_cancel = self.action_update_amount_reimbursed(cr, uid, ids, 'cancel', line.pettycash_id.id, line.account_id.id, line.amount)
                        cashback_request = self.action_update_amount_reimbursed(cr, uid, ids, 'request', line.pettycash_id.id, line.account_id.id, value['amount'])
                        if cashback_request == 0:
                            line.pettycash_id.write({'state':'reimbursed'})
                        else:
                            line.pettycash_id.write({'state':'posted'})
                        editcash += ('- '+str(line.pettycash_id.name)+' ('+str(value['amount'])+')<br/>')
        update = super(dym_reimbursed, self).write(cr, uid, ids, vals, context=context) 
        rekap = []
        for x in reimbursed.line_ids:
            if (str(x.pettycash_id.id) + ' - ' + str(x.account_id.id)) in rekap :
                raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada Pettycash-Account yang sama dalam detail transaksi"))
            elif (str(x.pettycash_id.id) + ' - ' + str(x.account_id.id)) not in rekap :
                rekap.append((str(x.pettycash_id.id) + ' - ' + str(x.account_id.id)))
        if delcash or editcash or addcash :
            message = ''
            if addcash:
                message += ("Add Petty Cash No <br/> %s")%(addcash)
            if editcash:
                message += ("Edit Amount Petty Cash No <br/> %s")%(editcash)
            if delcash:
                message += ("Delete Petty Cash No <br/> %s")%(delcash)
            self.message_post(cr, uid, reimbursed.id, body=_("%s")%(message), context=context)
        return update

    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Reimbursed Petty Cash sudah diproses, sata tidak bisa didelete !"))
        return super(dym_reimbursed, self).unlink(cr, uid, ids, context=context)        

class dym_pettycash(models.Model):
    _inherit = "dym.pettycash"

    reimbursed_id = fields.Many2one('dym.reimbursed')  

class dym_reimbursed_line(models.Model):
    _name = "dym.reimbursed.line"
    _description ="Reimbursed Petty Cash Line"
    
    # @api.one
    # @api.depends('pettycash_id','account_id')
    # def _compute_balance(self):
    #     for x in self.pettycash_id.line_ids:
    #         balance = 0
    #         if x.account_id == self.account_id:
    #             balance = str(x.amount_real)
    #         self.balance = balance

    reimbursed_id = fields.Many2one('dym.reimbursed')  
    state = fields.Selection(related='reimbursed_id.state', readonly=True)
    pettycash_id = fields.Many2one('dym.pettycash', string='Petty Cash', domain="[('journal_id','=',parent.journal_id),('branch_id','=',parent.branch_id),('division','=',parent.division),('state','=','posted'),('amount_real','>',0)]")
    name = fields.Char(string="Description", required=True)
    account_id = fields.Many2one('account.account', string="Account", domain="[('type','!=','view')]")
    # balance = fields.Float(string='Balance',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_balance',)
    amount = fields.Float(string="Amount")

    @api.onchange('pettycash_id')
    def pettycash_change(self):
        if not self.reimbursed_id.branch_id or not self.reimbursed_id.division or not self.reimbursed_id.journal_id:
            raise osv.except_osv(('Attention!'), ('Sebelum menambah detil transaksi,\n harap isi data header terlebih dahulu.'))
        dom = []
        for x in self.pettycash_id.line_ids :
            if x.amount_real - x.amount_reimbursed > 0:
                dom.append(x.account_id.id)
        self.account_id = False
        self.name = ''
        # self.balance = 0
        self.amount = 0
        return {'domain' : {'account_id':[('id','in',dom)]}}  
    
    @api.onchange('account_id')
    def account_change(self):
        desc = ''
        balance = 0
        petty_line = self.env['dym.pettycash.line']
        petty_brw = petty_line.search([('pettycash_id','=',self.pettycash_id.id)])
        for x in petty_brw :
            if x.account_id == self.account_id:
                desc = str(x.name)
                balance = x.amount_real - x.amount_reimbursed
        self.name = desc
        # self.balance = balance
        self.amount = balance

    @api.onchange('amount')
    def onchange_amount(self):
        warning = {}
        # if self.amount:
        #     petty_line = self.env['dym.pettycash.line']
        #     petty_brw = petty_line.search([('pettycash_id','=',self.pettycash_id.id)])
        #     for x in petty_brw :
        #         if self.account_id == x.account_id :
        #             if self.amount > x.amount_real :
        #                 self.amount = False
        #                 warning = {
        #                     'title': ('Perhatian !'),
        #                     'message': (("Nilai amount tidak boleh lebih dari Rp.%s")%(x.amount_real)),
        #                 }  
        return {'warning':warning}
    
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