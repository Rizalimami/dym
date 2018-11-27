import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from lxml import etree
from openerp.osv.orm import setup_modifiers
from ..report import fungsi_terbilang

class dym_reimbursed_ho(models.Model):
    _name = 'dym.reimbursed.ho'
    _description ="Reimbursed HO"
    _inherit = ['mail.thread']

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('request', 'Requested'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ]

    @api.one
    @api.depends('line_ids.amount')
    def _compute_amount(self):
        amount = sum(line.total_net for line in self.settle_ids)
        self.amount_total = amount

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

    def ubah_tanggal(self,tanggal):
        try:
            conv = datetime.strptime(tanggal, '%d-%m-%Y %H:%M')
            return conv.strftime('%d/%m/%Y')
        except Exception as e:
            conv = datetime.strptime(tanggal, '%Y-%m-%d %H:%M:%S')
            return conv.strftime('%d/%m/%Y') 

    # @api.one
    # @api.depends('line_ids')            
    # def _count_detail_payslip(self):
    #     settle_ids = []
    #     count = 0
    #     for line in self.line_ids:
    #         if line.settlement_id.id in settle_ids:
    #             continue
    #         count += 1
    #         settle_ids.append(line.settlement_id.id)
    #     self.settle_count = count

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
    journal_id = fields.Many2one('account.journal',string="Payment Method",domain="[('branch_id','in',[branch_id,False]),('type','in',['pettycash','cash','bank'])]")
    state = fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date_request = fields.Date(string="Date Requested",required=True,readonly=True,default=fields.Date.context_today)
    date_approve = fields.Date(string="Date Approved",readonly=True)
    date_cancel = fields.Date(string="Date Canceled",readonly=True)
    amount_total = fields.Float(string='Total Amount',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    confirm_uid = fields.Many2one('res.users',string="Requested by")
    confirm_date = fields.Datetime('Requested on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    # settle_count = fields.Integer(compute=_count_detail_payslip, string="Items")
    settle_ids = fields.Many2many('dym.settlement', 'reimbursed_settle_avp_rel','reimbursed_id','settle_avp_id', string='Settlement')
    line_ids = fields.One2many('dym.reimbursed.ho.line', 'reimbursed_id', string='Reimburse Details', compute='_compute_details', store=True)
    notes = fields.Char('Notes')

    @api.depends('settle_ids')
    def _compute_details(self):
        if self.settle_ids:
            vals = []
            for settle in self.settle_ids:
                for line in settle.settlement_line:
                    vals.append((0,0,{
                        'name':str(settle.description or settle.name), 
                        'settlement_id':settle.id,                                                                   
                        'account_id':line.account_id.id,
                        'amount':line.amount,                    
                    }))
            self.line_ids = vals

    @api.model
    def default_get(self, fields):
        res = super(dym_reimbursed_ho, self).default_get(fields)
        user = self.env.user
        # if not user.branch_id:
        #     raise osv.except_osv(('Perhatian !'), ("User %s tidak memiliki default branch. Hubungi system administrator agar menambahkan default branch di User Setting." % self.env.user.name))

        res['branch_id'] = user.branch_id.id
        if user.branch_type != 'HO':
            res['division'] = 'Finance'
        else:
            # raise osv.except_osv(('Perhatian !'), ("User %s tidak diijinkan untuk membuat transaksi ini." % self.env.user.name))
            return res

    @api.multi
    def action_validate(self):
        warning = {}
        if not self.line_ids:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan baris baris transaksi, silahkan Compute dulu. Tapi jika ternyata memang tidak ada transaksi pada periode yang dipilih, silahkan coba lagi periode berikutnya."))
        else:
            self.name = self.env['ir.sequence'].get_per_branch(self.branch_id.id, 'RBK', division=self.division)  
            self.action_post()

    @api.model
    def create(self,vals,context=None):
        rekap = []
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'RAP', division='Umum')       
        vals['date_request'] = datetime.today()

        reimbursed_id = super(dym_reimbursed_ho, self).create(vals)
        return reimbursed_id

    @api.multi
    def cancel(self):
        self.state = 'cancel'
        self.date_cancel = datetime.today()
        self.cancel_uid = self._uid
        self.cancel_date = datetime.now()

    @api.multi
    def request(self):
        cash = ''
        self.message_post(body=_("Reimbursed Requested Advance Payment No: <br/>%s")%(cash))                             
        self.state = 'request'
        self.confirm_uid = self._uid
        self.confirm_date = datetime.now()
        self.date_request = datetime.today()

    @api.multi
    def approve(self):
        cash = ''
        self.message_post(body=_("Reimbursed Approved <br/> Advance Payment No : <br/>  %s ")%(cash))                             
        self.state = 'approved'
        self.date_approve = datetime.today()

    @api.onchange('branch_id','division')
    def onchange_settlement(self):
        dom = {}
        val = {}
        if self.branch_id:
            if self._context.get('transaction_type',False) == 'avp':
                # branch = self.env['dym.branch'].browse(self.branch_id.id)
                account_bank_ids = self.env['account.journal'].search([('company_id','=',self.branch_id.company_id.id),('type','=','cash')])
                bank_ids = [x.id for x in account_bank_ids]
                settlement = self.env['dym.settlement'].search([
                    ('branch_id','=',self.branch_id.id),
                    ('division','=',self.division),
                    ('state','=','done'),
                    ('amount_total','>',0),
                    ('payment_method','in',bank_ids)
                ])
                settle = [x.id for x in settlement]
                dom['settle_ids'] = [('id','in',settle)]
        return {'domain':dom}

    @api.cr_uid_ids_context
    def button_dummy(self, cr, uid, ids, context=None):
        return True

class dym_reimbursed_avp_line(models.Model):
    _name = "dym.reimbursed.ho.line"
    _description ="Reimbursed Advance Payment Line"

    reimbursed_id = fields.Many2one('dym.reimbursed.ho')  
    state = fields.Selection(related='reimbursed_id.state', readonly=True)
    settlement_id = fields.Many2one('dym.settlement', string='Settlement', domain="[('journal_id','=',parent.journal_id),('branch_id','=',parent.branch_id),('state','=','posted')]")
    name = fields.Char(string="Description", required=True)
    account_id = fields.Many2one('account.account', string="Account", domain="[('type','!=','view')]")
    amount = fields.Float(string="Amount")

    @api.onchange('settlement_id')
    def onchange_settlement_id(self):
        if self.settlement_id:
            self.amount = self.settlement_id.total_net