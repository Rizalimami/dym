import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp import workflow
from openerp.osv import osv
from ..report import fungsi_terbilang

class dym_account_move_line(models.Model):
    _inherit = "account.move.line"
    
    @api.one
    def get_settlement(self):
        settlement = self.env['dym.settlement'].search([('advance_payment_id','=',self.avp_id.id)])
        self.settlement_id = settlement
        
    avp_id = fields.Many2one('dym.advance.payment', "Advance Payment")
    settlement_id = fields.Many2one('dym.settlement', string='Settlement', compute="get_settlement")

class dym_advance_payment(models.Model):
    _name = "dym.advance.payment"
    _description = "Advance Payment"
    _order = "id asc"
    
    #===========================================================================
    # @api.one
    # @api.depends('advance_payment_line.amount')
    # def _compute_amount(self):
    #     self.amount_total = sum(line.amount for line in self.advance_payment_line)
    #===========================================================================

    def ubah_tanggal(self,tanggal):
        try:
            conv = datetime.strptime(tanggal, '%d-%m-%Y %H:%M')
            return conv.strftime('%d/%m/%Y')
        except Exception as e:
            conv = datetime.strptime(tanggal, '%Y-%m-%d %H:%M:%S')
            return conv.strftime('%d/%m/%Y')

    def ubah_tanggal_2(self,tanggal):
        try:
            conv = datetime.strptime(tanggal, '%d-%m-%Y')
            return conv.strftime('%d-%m-%Y')
        except Exception as e:
            conv = datetime.strptime(tanggal, '%Y-%m-%d')
            return conv.strftime('%d-%m-%Y')

    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil

    def get_department(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)
        partner = self.pool.get('hr.employee').search(cr,uid,[('nip','=',val.user_id.default_code)])
        emp = partner or val.employee_id.id
        department = ""
        if emp:
            emp_browse = self.pool.get('hr.employee').browse(cr,uid,emp)[0]
            department = "%s / %s" % (emp_browse.department_id.parent_id.name, emp_browse.department_id.name) or "-"
        return department

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_advance_payment, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company_id),('type','=','normal'),('state','not in',('close','cancelled'))])
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='analytic_2']")
        for node in nodes_branch :
            node.set('domain', "[('segmen','=',2),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',"+str(level_1_ids)+")]")
        res['arch'] = etree.tostring(doc)
        return res

    @api.one
    @api.depends('payment_method')
    def _journal_is_bank(self):
        self.journal_is_bank = True if self.payment_method.type == 'bank' else False
        
    @api.one
    @api.depends('account_move_id.line_id.reconcile_id','account_move_id.line_id.reconcile_partial_id')
    def get_move_balance(self):
        settlement = self.env['dym.settlement'].search([('advance_payment_id','=',self.id),('state','!=','cancel')])

        balance = self.amount
        if self.account_move_id:
            for line in self.account_move_id.line_id:
                if line.debit > 0:
                    balance = abs(line.fake_balance)
                    break

        if settlement:
            invoice_id = settlement.settlement_line[0].invoice_id
            if invoice_id:
                for line in invoice_id.move_id.line_id:
                    if line.debit > 0:
                        balance = abs(line.fake_balance)
                        break
        self.open_balance = balance

    @api.multi
    @api.depends('payment_method')
    def _get_balance(self):
        aa_obj = self.env['account.analytic.account']
        start_date = fields.Date.context_today(self)
        for rec in self:
            bank_balance = 0
            today_balance = 0
            branch_id = rec.branch_id
            if rec.payment_method:            
                sql_query = ''
                if branch_id:
                    analytic_branch = aa_obj.search([('segmen','=',3),('branch_id','=',branch_id.id),('type','=','normal'),('state','not in',('close','cancelled'))])
                    analytic_cc = aa_obj.search([('segmen','=',4),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',analytic_branch.ids)])
                    sql_query = ' and l.period_id in (select id from  account_period where special= FALSE) AND l.analytic_account_id in %s' % str(tuple(analytic_cc.ids)).replace(',)', ')')
                bank_balance = rec.payment_method.default_credit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=True,sql_query=sql_query).balance or rec.payment_method.default_debit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=True,sql_query=sql_query).balance
                today_balance = rec.payment_method.default_credit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=False,sql_query=sql_query).balance or rec.payment_method.default_debit_account_id.with_context(date_from=start_date, date_to=start_date, initial_bal=False,sql_query=sql_query).balance
            rec.balance = bank_balance + today_balance
        return True

    @api.one
    def _get_bank_name(self):
        self.partner_bank_name = self.partner_bank_id.owner_name

    name = fields.Char(string='Advance Payment')
    user_id = fields.Many2one('res.partner',string='Partner',required=True)
    branch_id = fields.Many2one('dym.branch', string='Branch',required=True, default=_get_default_branch)
    date = fields.Date(string='Date',default=fields.Date.context_today)
    account_id = fields.Many2one('account.account',string='Account Advance Payment')
    payment_method = fields.Many2one('account.journal',string='Payment Method',required=True)
    journal_is_bank = fields.Boolean('Journal is Bank', compute='_journal_is_bank')
    division = fields.Selection([
                                 ('Unit','Showroom'),
                                 ('Sparepart','Workshop'),
                                 ('Umum','General'),
                                 ('Finance','Finance')
                                 ],required=True,string='Division')
    amount = fields.Float(string='Original Amount',required=True)
    open_balance = fields.Float(string='Open Balance', compute='get_move_balance', readonly=True)
    balance = fields.Float(compute='_get_balance', string='Balance')
    
    state = fields.Selection([
            ('draft','Draft'),
            ('waiting_for_approval','Waiting Approval'),
            ('approved','Approved'),
            ('confirmed','Confirmed'),
            ('done','Done'),
            ('cancel','Cancelled')
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,)
    description = fields.Text(string='Description')
    user_balance = fields.Float(string='Total O/S Balance',compute='onchange_user_id')
    employee_id = fields.Many2one('hr.employee', 'Responsible')
    account_move_id = fields.Many2one('account.move')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by", copy=False)
    confirm_date = fields.Datetime('Confirmed on')
    date_due = fields.Date(string='Due Date')
    analytic_2 = fields.Many2one('account.analytic.account', string='Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', string='Account Analytic Branch')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Account Analytic Cost Center')
    source_settlement = fields.Char(string='Source Settlement', readonly=True)
    clearing_bank = fields.Boolean(string='Clearing Bank')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    partner_bank_name = fields.Char(string='Owner Name', compute='_get_bank_name')
    partner_bank_id = fields.Many2one('res.partner.bank', string='Rekening Pembayaran')
     
    @api.onchange('branch_id')
    def branch_change(self):
        if self.branch_id:
            branch = self.branch_id
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(self._cr, self._uid, branch, 'Umum', False, 4, 'General')
            self.analytic_2 = analytic_2_general
            self.analytic_3 = analytic_3_general
            self.analytic_account_id = analytic_4_general

    @api.onchange('payment_method')
    def payment_method_change(self):
        self.clearing_bank = False
        if self.payment_method.type == 'bank':
            self.journal_is_bank = True
        else:
            self.journal_is_bank = False

    @api.multi
    def get_sequence(self,branch_id,context=None):
        doc_code = self.env['dym.branch'].browse(branch_id).doc_code
        seq_name = 'APA-G/{0}'.format(doc_code)
        seq = self.env['ir.sequence']
        ids = seq.sudo().search([('name','=',seq_name)])
        if not ids:
            prefix = '/%(y)s%(month)s/'
            prefix = seq_name + prefix
            ids = seq.create({'name':seq_name,
                                 'implementation':'no_gap',
                                 'prefix':prefix,
                                 'padding':5})
        
        return seq.get_id(ids.id)
    
    @api.model
    def create(self,values,context=None):
        branch = self.env['dym.branch'].browse(values['branch_id'])
        values['name'] = self.env['ir.sequence'].get_sequence('APA', division=values['division'], padding=6, branch=branch)
        obj_branch_config = self.env['dym.branch.config'].search([('branch_id','=',values['branch_id'])])
        # values['date'] = datetime.today()
        if not obj_branch_config:
            raise Warning("Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu")
        else:
            if not(obj_branch_config.dym_advance_payment_account_id):
                raise Warning("Branch Configuration jurnal Advance Payment belum dibuat, silahkan setting terlebih dulu")
            
        values['account_id'] = obj_branch_config.dym_advance_payment_account_id.id    
        advance_payment = super(dym_advance_payment,self).create(values)
        return advance_payment
    
    @api.multi
    def wkf_action_confirm(self):
        period_ids = self.env['account.period'].find(self.date)
        obj_branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if not obj_branch_config:
            raise Warning("Konfigurasi jurnal cabang belum dibuat, silahkan setting terlebih dulu")
        else:
            if not(obj_branch_config.dym_advance_payment_account_id) or not(obj_branch_config.advance_payment_hutang_lain):
                raise Warning("Branch Configuration Jurnal Advance Payment belum dibuat, silahkan setting terlebih dulu")

        date = datetime.now().strftime('%Y-%m-%d')

        if self.journal_is_bank == True:
            account = self.env['account.account']
            account_id = obj_branch_config.advance_payment_hutang_lain.id
            date = self.date
        elif self.clearing_bank == False:
            account_id = self.payment_method.default_credit_account_id.id or self.payment_method.default_debit_account_id.id
        else:
            account_id = self.payment_method.get_clearing_account_id()

        move_line = []
        move_journal = {
                        'name': self.name,
                        'ref': self.name,
                        'journal_id': self.payment_method.id,
                        'date': date,
                        'period_id':period_ids.id,
                        'transaction_id':self.id,
                        'model':self.__class__.__name__,
                        }

        # account_id = self.payment_method.default_credit_account_id.id or self.payment_method.default_debit_account_id.id

        move_line.append([0,False,{
                    'name': self.description or '',
                    'partner_id': self.user_id.id,
                    'account_id': account_id if self.clearing_bank == False else self.payment_method.get_clearing_account_id(),
                    'period_id': period_ids.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': self.amount,
                    'branch_id': self.branch_id.id,
                    'division': self.division,
                    'date_maturity': date,
                    'analytic_account_id' : self.analytic_account_id.id,
                    'clear_state': 'open' if self.clearing_bank == True else 'not_clearing',
                    'ref': self.name,
                     }])
       
        move_line.append([0,False,{
                    'name': _('Advance Payment'),
                    'partner_id': self.user_id.id,
                    'account_id': obj_branch_config.dym_advance_payment_account_id.id,
                    'period_id': period_ids.id,
                    'date': date,
                    'debit': self.amount,
                    'credit': 0.0,
                    'branch_id': self.branch_id.id,
                    'division': self.division,
                    'date_maturity': date,
                    'analytic_account_id' : self.analytic_account_id.id, 
                    'avp_id' : self.id,
                    'ref': self.name, 
                     }])
        
        move_journal['line_id']=move_line
        
        move_obj = self.env['account.move']
        create_journal = move_obj.create(move_journal)
        if create_journal:
            create_journal.button_validate()
        self.write({'date':date,'state':'confirmed','account_move_id':create_journal.id,'confirm_uid':self._uid,'confirm_date':datetime.now()})
        return True
    
    @api.onchange('user_id','amount')
    def onchange_user_id(self):
        if self.amount < 0:
            self.amount = 0.0
            return {'warning':{'title':'Perhatian !','message':'Tidak boleh input nilai negatif!'}}
        
        advance_payment = self.search([('user_id','=',self.user_id.id),('state','=','confirmed')])
        balance = 0.0
        for avp in advance_payment:
            balance+=avp.amount
        
        self.user_balance = balance
        
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Advance Payment sudah diproses, data tidak bisa dihapus !"))
        return super(dym_advance_payment, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def wkf_action_cancel(self):
        settlement_id = self.env['dym.settlement'].search([('advance_payment_id','=',self.id),('state','!=','cancel')])
        if self.account_move_id and not settlement_id:
            if self.journal_is_bank:
                for line in self.advance_payment_line:
                    if line.voucher_id.state!='cancel':
                        raise osv.except_osv(('Perhatian !'), ("Advance Payment sudah dibuat SPA %s ! \n Mohon cancel SPA terlebih dahulu !" % line.voucher_id.number))
                self.account_move_id.action_reverse_journal()
            else:
                self.account_move_id.action_reverse_journal()
        elif settlement_id:
            raise osv.except_osv(('Perhatian !'), ("Advance Payment sudah dibuat Settlement %s ! \n Mohon cancel Settlement terlebih dahulu !" % (settlement_id.name)))
        self.write({'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
