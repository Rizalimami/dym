import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from lxml import etree

class dym_journal_memorial_consol(models.Model):
    _name = 'dym.journal.memorial.consol'
    _description = 'Journal Memorial Consolidation'

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('confirm','Confirmed'),
        ('cancel','Cancelled')
    ]

    @api.one
    @api.depends('journal_memorial_line.amount')
    def _compute_debit(self):
        total_debit = 0.0
        for x in self.journal_memorial_line:
            if x.type == 'Dr' :
                total_debit += x.amount
        self.total_debit = total_debit

    @api.one
    @api.depends('journal_memorial_line.amount')
    def _compute_credit(self):
        total_credit = 0.0
        for x in self.journal_memorial_line :
            if x.type == 'Cr' :
                total_credit += x.amount
        self.total_credit = total_credit
                    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    @api.cr_uid_ids_context
    def get_group_company(self,cr,uid, ids, context=None):
        user_obj = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid)
        company = user_obj.company_id
        while company.parent_id:
            company = company.parent_id
        return company

    @api.cr_uid_ids_context
    def _get_default_periode(self,cr,uid,ids,context=None):
        periode_obj = self.pool.get('account.period')
        company = self.get_group_company(cr, uid, [])
        periode_now = periode_obj.search(cr,uid,[
                                      ('date_start','<=',datetime.today()),
                                      ('date_stop','>=',datetime.today()),
                                      ('company_id','=',company.id),
                                      ])  
        periode_id = False
        if periode_now:
            periode_id = periode_obj.browse(cr,uid,periode_now).id
        return periode_id
            
    name = fields.Char(string='No')
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, default=_get_default_branch)
    date = fields.Date(string="Date",required=True,readonly=True,default=fields.Date.context_today)
    periode_id = fields.Many2one('account.period',string='Periode')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], string='Division',default='Unit', required=True,change_default=True, select=True)
    auto_reverse = fields.Boolean(string="Auto Reverse ?")
    journal_memorial_line = fields.One2many('dym.journal.memorial.consol.line','journal_memorial_id')
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    total_debit = fields.Float(string='Total Debit',digits=dp.get_precision('Account'), store=True,compute='_compute_debit')
    total_credit = fields.Float(string='Total Credit',digits=dp.get_precision('Account'), store=True,compute='_compute_credit')
    move_id = fields.Many2one('account.move.consol', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line.consol',related='move_id.line_id',string='Journal Items', readonly=True)   
    auto_reverse_move_id = fields.Many2one('account.move.consol', string='Account Entry', copy=False)
    auto_reverse_move_ids = fields.One2many('account.move.line.consol',related='auto_reverse_move_id.line_id',string='Auto Reverse Journal Items', readonly=True)   
    prev_periode = fields.Boolean(string="Prev Periode")  
    current_periode_id = fields.Many2one('account.period',string='Current Periode',default=_get_default_periode)
    reverse_periode_id = fields.Many2one('account.period',string='Reverse Periode')
    description = fields.Char(string='Description')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    approval_state =  fields.Selection([
                                        ('b','Belum Request'),
                                        ('rf','Request For Approval'),
                                        ('a','Approved'),
                                        ('r','Reject')
                                        ],'Approval State', readonly=True,default='b')
    code = fields.Selection([(' ',' '),('cancel','Cancel')],string="Code",default=' ')
    state_periode = fields.Selection(related="periode_id.state")
    cancel_refered = fields.Many2one('dym.journal.memorial.consol')
    konsolidasi = fields.Selection([('Umum','General'),('Konsolidasi','Konsolidasi')], string='Type', default='Umum', change_default=True, select=True)
    partner_id = fields.Many2one('res.partner', string="Partner")
      
    @api.onchange('periode_id')
    def onchange_periode(self):
        if self.periode_id :
            if self.periode_id.date_stop > self.date :
                self.prev_periode = True
            else :
                self.prev_periode = False
            self.reverse_periode_id = self.env['account.period'].search([('date_start','>',self.periode_id.date_stop),('company_id','=',self.periode_id.company_id.id)], order="date_start asc", limit=1)
            
    @api.cr_uid_ids_context    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_journal_memorial_consol, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        periode_obj = self.pool.get('account.period')
        kolek_periode =[]
        company = self.get_group_company(cr, uid, [])
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        periode_now = periode_obj.search(cr,uid,[
                                      ('date_start','<=',datetime.today()),
                                      ('date_stop','>=',datetime.today()),
                                      ('company_id','=',company.id),
                                      ])
        if periode_now :
            periode_id = periode_obj.browse(cr,uid,periode_now)
            kolek_periode.append(periode_id.id)
            prev_periode = periode_obj.search(cr,uid,[
                                               ('date_start','<',datetime.today()),
                                               ('id','!=',periode_id.id),
                                               ('state','=','draft'),
                                               ('company_id','=',company.id),
                                               ])
            if prev_periode :
                perv_periode_id2 = periode_obj.browse(cr,uid,prev_periode)
                for x in perv_periode_id2 :
                    kolek_periode.append(x.id)
        
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='periode_id']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(kolek_periode)+')]')
        partner_ids = self.pool.get('res.partner').search(cr,uid,[
                                      ('partner_type','=','Konsolidasi'),
                                      ])
        nodes_branch = doc.xpath("//field[@name='partner_id']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(partner_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res

    @api.model
    def create(self,vals,context=None):
            
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'JMC', division=False) 
        vals['date'] = datetime.today()              
        if not vals.get('journal_memorial_line') and vals.get('code') != 'cancel':
            raise osv.except_osv(('Perhatian !'), ("Harap isi detail!"))   
            
        res =  super(dym_journal_memorial_consol, self).create(vals)  
        res.cek_balance()
        return res

    @api.multi
    def write(self,values,context=None):
        res =  super(dym_journal_memorial_consol,self).write(values)
        self.cek_balance()
        return res
        
    @api.one      
    def cek_balance(self):
        if self.total_debit != self.total_credit :
            raise osv.except_osv(('Perhatian !'), ("Total tidak balance, silahkan periksa kembali !"))   

    @api.multi
    def cancel_memorial(self):
        self.action_create_memorial()
        self.state = 'cancel'
        
    @api.multi
    def action_create_memorial(self):
        memorial_vals = {
                             'branch_id': self.branch_id.id  ,
                             'periode_id': self.periode_id.id ,
                             'description':'Cancel Journal Memorial Consolidation No %s'%(self.name),
                             'division' : self.division,
                             'date': datetime.today(),
                             'auto_reverse' : self.auto_reverse,
                             'code': 'cancel',
                             'total_debit': self.total_debit,
                             'total_credit' : self.total_credit,
                             'transaction_id':self.id,
                             'model':self.__class__.__name__,
                             }
        memorial_id = self.sudo().create(memorial_vals)
        for line in self.journal_memorial_line :
            memorial_line_vals = {
                                      'journal_memorial_id': memorial_id.id,
                                      'account_id': line.account_id.id,
                                      'amount': line.amount,
                                      'type': 'Dr' if line.type == 'Cr' else 'Cr',
                                      'branch_id':line.branch_id.id,
                                      'division' : self.division,
                                      'partner_id' : line.partner_id.id,
                                      'analytic_1' : line.analytic_1.id,
                                      'analytic_2' : line.analytic_2.id,
                                      'analytic_3' : line.analytic_3.id,
                                      'analytic_account_id' : line.analytic_account_id.id,
                                      }
            self.env['dym.journal.memorial.consol.line'].sudo().create(memorial_line_vals)
        memorial_id.wkf_request_approval()
        self.cancel_refered = memorial_id.id

    @api.cr_uid_ids_context
    def action_create_move_line(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move.consol')
        move_line_pool = self.pool.get('account.move.line.consol')
        branch_config = self.pool.get('dym.branch.config')   
        company = self.get_group_company(cr, uid, [])
        
        for memorial in self.browse(cr, uid, ids, context=context):       
            
            name = memorial.name
            date = memorial.date
            if not company.journal_memorial_journal_consol_id :
                raise osv.except_osv(('Perhatian !'), ("Journal Memorial Consolidation belum diisi di %s! !")%(company.name))  
            journal_id = company.journal_memorial_journal_consol_id.id            
            amount = memorial.total_credit          
            period_id = memorial.periode_id.id
                                   
            move = {
                'name': name,
                'ref':name,
                'journal_id': journal_id,
                'date': date if period_id == memorial.current_periode_id.id else memorial.periode_id.date_stop,
                'period_id':period_id,
                'reverse_from_id':False,
                'transaction_id':memorial.id,
                'model':memorial.__class__.__name__,
            }
            # for_name = False
            # if memorial.auto_reverse :
            #     for_name = memorial.description + ' (Auto Reverse)'
            # else :
            #     for_name = memorial.description
            move_id = move_pool.create(cr, uid, move, context=None)                    
            for y in memorial.journal_memorial_line :
                for_name = False
                if memorial.auto_reverse :
                    for_name = y.description + ' (Auto Reverse)'
                else :
                    for_name = y.description
                branch_dest = self.pool.get('dym.branch').browse(cr,uid,[y.branch_id.id])
                
                move_line_2 = {
                    'name': _('%s')%(for_name),
                    'ref':name,
                    'account_id': y.account_id.id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'date': date if period_id == memorial.current_periode_id.id else memorial.periode_id.date_stop,
                    'debit': y.amount if y.type == 'Dr' else 0.0,
                    'credit': y.amount if y.type == 'Cr' else 0.0,
                    'branch_id' : branch_dest.id,
                    'division' : memorial.division,
                    'partner_id' : y.partner_id.id,
                    'analytic_account_id' : y.analytic_account_id.id,                    
                }           
                line_id2 = move_line_pool.create(cr, uid, move_line_2, context)
            # self.create_intercompany_lines(cr,uid,ids,move_id,context=None) 
            if company.journal_memorial_journal_consol_id.entry_posted :
                posted = move_pool.post(cr, uid, [move_id], context=None)
            auto_reverse_move_id = False
            if memorial.auto_reverse :
                auto_reverse_move = {
                    'name': name,
                    'ref':name,
                    'journal_id': journal_id,
                    'date': date if memorial.reverse_periode_id.id == memorial.current_periode_id.id else memorial.reverse_periode_id.date_stop,
                    'period_id':memorial.reverse_periode_id.id,
                    'reverse_from_id':move_id,
                    'transaction_id':memorial.id,
                    'model':memorial.__class__.__name__,
                }
                # if not memorial.current_periode_id :
                #     raise osv.except_osv(('warning !'), ("Make sure you have active period for today!"))
                    
                auto_reverse_move_id = move_pool.create(cr,uid,auto_reverse_move,context)                      
                for y in memorial.journal_memorial_line :
                    for_name = False
                    if memorial.auto_reverse :
                        for_name = y.description + ' (Auto Reverse)'
                    else :
                        for_name = y.description
                    branch_destination = self.pool.get('dym.branch').browse(cr,uid,[y.branch_id.id])
                    autoreverse_move_line_2 = {
                        'name': _('%s')%(for_name),
                        'ref':name,
                        'account_id': y.account_id.id,
                        'move_id': auto_reverse_move_id,
                        'journal_id': journal_id,
                        'period_id': memorial.reverse_periode_id.id,
                        'date': date if memorial.reverse_periode_id.id == memorial.current_periode_id.id else memorial.reverse_periode_id.date_stop,
                        'debit': y.amount if y.type == 'Cr' else 0.0,
                        'credit': y.amount if y.type == 'Dr' else 0.0,
                        'branch_id' : branch_destination.id,
                        'division' : memorial.division,
                        'partner_id' : y.partner_id.id,
                        'analytic_account_id' : y.analytic_account_id.id,     
                    } 
                    autoreverse_line_id2 = move_line_pool.create(cr,uid,autoreverse_move_line_2,context)
                # self.create_intercompany_lines(cr,uid,ids,auto_reverse_move_id,context=None)  
                if company.journal_memorial_journal_consol_id.entry_posted :                                     
                    posted2 = move_pool.post(cr, uid, [auto_reverse_move_id], context=None)
                
            self.write(cr, uid, memorial.id, {'state': 'confirm', 'move_id': move_id,'auto_reverse_move_id':auto_reverse_move_id})
        return True

    @api.cr_uid_ids_context   
    def create_intercompany_lines(self,cr,uid,ids,move_id,context=None):
        ##############################################################
        ################# Add Inter Company Journal ##################
        ##############################################################
        branch_rekap = {}       
        branch_pool = self.pool.get('dym.branch')        
        vals = self.browse(cr,uid,ids) 
        move_line = self.pool.get('account.move.line.consol')
        move_line_srch = move_line.search(cr,uid,[('move_id','=',move_id)])
        move_line_brw = move_line.browse(cr,uid,move_line_srch)        
        branch = branch_pool.search(cr,uid,[('id','=',vals.branch_id.id)])
        company = self.get_group_company(cr, uid, [])

        if branch :
            branch_browse = branch_pool.browse(cr,uid,branch)
            inter_branch_header_account_id = branch_browse.inter_company_account_id.id
            if not inter_branch_header_account_id :
                raise osv.except_osv(('Perhatian !'), ("Account Inter Company belum diisi dalam Master branch %s !")%(vals.branch_id.name))
        if not company.journal_memorial_journal_consol_id :
            raise osv.except_osv(('Perhatian !'), ("Journal Memorial Consolidation belum diisi di %s! !")%(company.name))  
        journal_id = company.journal_memorial_journal_consol_id.id   
                    
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
            if key != vals.branch_id and value['debit'] != value['credit'] :
        
                inter_branch_detail_account_id = key.inter_company_account_id.id                
                if not inter_branch_detail_account_id :
                    raise osv.except_osv(('Perhatian !'), ("Account Intercompany belum diisi dalam Master branch %s - %s!")%(key.code, key.name))

                balance = value['debit']-value['credit']
                debit = abs(balance) if balance < 0 else 0
                credit = balance if balance > 0 else 0
                
                move_line_create = {
                    'name': _('Interco Journal Memorial Consolidation %s')%(key.name),
                    'ref':_('Interco Journal Memorial Consolidation %s')%(key.name),
                    'account_id': inter_branch_header_account_id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': vals.periode_id.id,
                    'date': vals.date,
                    'debit': debit,
                    'credit': credit,
                    'branch_id' : key.id,
                    'division' : vals.division                    
                }    
                inter_first_move = move_line.create(cr, uid, move_line_create, context)    
                         
                move_line2_create = {
                    'name': _('Interco Journal Memorial Consolidation %s')%(vals.branch_id.name),
                    'ref':_('Interco Journal Memorial Consolidation %s')%(vals.branch_id.name),
                    'account_id': inter_branch_detail_account_id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': vals.periode_id.id,
                    'date': vals.date,
                    'debit': credit,
                    'credit': debit,
                    'branch_id' : vals.branch_id.id,
                    'division' : vals.division                    
                }    
                inter_second_move = move_line.create(cr, uid, move_line2_create, context)  
                                                                 
        return True
        
    @api.multi
    def wkf_request_approval(self):
        if self.konsolidasi:
            partner_check = self.journal_memorial_line.search([('partner_id','!=',self.partner_id.id),('journal_memorial_id','=',self.id)])
            if partner_check:
                raise osv.except_osv(('Perhatian !'), ("Partner di header dan di line harus sama jika tipe konsolidasi, mohon periksa kembali!")) 
        obj_matrix = self.env["dym.approval.matrixbiaya"]
        if self.code == 'cancel' :
            obj_matrix.request_by_value(self, self.total_credit,code=self.code)
        else :
            obj_matrix.request_by_value(self, self.total_credit)

        self.state =  'waiting_for_approval'
        self.approval_state = 'rf'
        company = self.get_group_company()
        if not company.journal_memorial_journal_consol_id :
            raise osv.except_osv(('Perhatian !'), ("Journal Memorial Consolidation belum diisi di %s! !")%(company.name))  
                
    @api.multi      
    def wkf_approval(self):
        if not self.journal_memorial_line:
            raise osv.except_osv(('Perhatian !'), ("Detail belum diisi. Data tidak bisa di save."))       
        approval_sts = self.env['dym.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'date':datetime.today(),'approval_state':'a','confirm_uid':self._uid,'confirm_date':datetime.now()})
            self.action_create_move_line()
        elif approval_sts == 0:
                raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group Approval"))    
            
    @api.multi
    def has_approved(self):
       
        if self.approval_state == 'a':
            return True
        
        return False
    
    @api.multi
    def has_rejected(self):
        
        if self.approval_state == 'r':
            self.write({'state':'draft'})
            return True
        return False
    
    @api.one
    def wkf_set_to_draft(self):
        self.write({'state':'draft','approval_state':'r'})
        
    @api.cr_uid_ids_context    
    def view_jm(self,cr,uid,ids,context=None):  
        val = self.browse(cr, uid, ids, context={})[0]
        return {
            'name': 'Journal Memorial Consolidation',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dym.journal.memorial.consol',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': val.cancel_refered.id
            }        
                            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Journal Memorial Consolidation tidak bisa didelete !"))
        return super(dym_journal_memorial_consol, self).unlink(cr, uid, ids, context=context) 
                                
class dym_journal_memorial_consol_line(models.Model):
    _name = 'dym.journal.memorial.consol.line'
    _rec_name = 'account_id'
        
    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('dym.journal.memorial.consol').get_group_company(self._cr, self._uid, [])
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_journal_memorial_consol] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    account_id = fields.Many2one('account.account',string="Account",domain="[('type','not in',('view','consolidation')),('company_id.parent_id','=',False)]")
    amount = fields.Float(string="Amount")
    type = fields.Selection([('Dr','Dr'),('Cr','Cr')],string="Dr/Cr")
    journal_memorial_id = fields.Many2one('dym.journal.memorial.consol')
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True)   
    description = fields.Char(string='Description')
    partner_id = fields.Many2one('res.partner',string='Partner') 
    analytic_1 = fields.Many2one('account.analytic.account', string='Account Analytic Company', default=_get_analytic_company)
    analytic_2 = fields.Many2one('account.analytic.account', string='Account Analytic Bisnis Unit',help='Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', string='Account Analytic Branch',help='Account Analytic Branch')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Account Analytic Cost Center',help='Account Analytic Cost Center')

    @api.onchange('partner_id')
    def onchange_partner(self):
        domain = {}
        if self.journal_memorial_id.konsolidasi == 'Konsolidasi':
            if not self.journal_memorial_id.partner_id.id:
                raise osv.except_osv(('Perhatian !'), ("Mohon isi partner diatas terlebih dahulu!"))   
            self.partner_id = self.journal_memorial_id.partner_id.id
            domain['partner_id'] = '[("id","=",'+str(self.journal_memorial_id.partner_id.id)+')]'
        return {'domain':domain}   

    @api.onchange('account_id')
    def onchange_account(self):
        domain ={}
        branch_ids_user=self.env['res.users'].browse(self._uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        domain['account_id'] = '["|",("branch_id", "in", '+ str(branch_ids)+'),("branch_id", "=", False),("type","not in",("view","consolidation")),("company_id.parent_id","=",False)]'        
        if self.account_id :
            if self.account_id.branch_id :
                domain['branch_id'] = '[("id","=",'+str(self.account_id.branch_id.id)+')]'
                self.branch_id = self.account_id.branch_id.id
            else :
                domain['branch_id'] = []
                self.branch_id = False
        return {'domain':domain}   
    
    _sql_constraints = [
    ('unique_name_account_id', 'unique(journal_memorial_id,account_id,branch_id,partner_id)', 'Tidak boleh ada account yang sama dalam satu branch  !'),
] 
    