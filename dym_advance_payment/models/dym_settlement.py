import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, exceptions, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp import workflow
from openerp.osv import osv
from lxml import etree
from ..report import fungsi_terbilang

class dym_settlement(models.Model):
    _name = "dym.settlement"
    _description = "Settlement"
    _order = "id asc"

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

    def get_department(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)
        partner = self.pool.get('hr.employee').search(cr,uid,[('nip','=',val.user_id.default_code)])
        emp = partner or val.employee_id.id
        department = ""
        if emp:
            emp_browse = self.pool.get('hr.employee').browse(cr,uid,emp)[0]
            department = "%s / %s" % (emp_browse.department_id.parent_id.name, emp_browse.department_id.name) or "-"
        return department

    @api.one
    @api.depends('settlement_line.amount')
    def _compute_amount(self):
        self.amount_total = sum(line.amount for line in self.settlement_line)
        if self.type:
            if self.type=='kembali':
                self.amount_gap = self.amount_avp - self.amount_total
            else:
                self.amount_gap = self.amount_total - self.amount_avp
        else:
            self.amount_gap = 0

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False
        return branch_ids 
        
    @api.one
    @api.depends('payment_method')
    def _journal_is_bank(self):
        self.journal_is_bank = True if self.payment_method.type == 'bank' else False

    @api.model
    def _get_default_backdate(self):
        flag = False
        if self.env['res.users'].has_group('dym_account_voucher.group_dym_account_voucher_allow_backdate'):
            flag = True
        return flag

    name = fields.Char(string='Settlement')
    user_id = fields.Many2one('res.partner',string='Employee',required=True)
    branch_id = fields.Many2one('dym.branch', string='Branch',required=True, default=_get_default_branch)
    advance_payment_id = fields.Many2one('dym.advance.payment',string='Advance Payment',required=True)
    employee_id = fields.Many2one(related='advance_payment_id.employee_id')
    amount_avp = fields.Float(string='Total Avp',digits=dp.get_precision('Account'),related='advance_payment_id.amount',store=True)
    amount_avp_show = fields.Float(string='Total Avp',related = 'amount_avp')
    date = fields.Date(string='Date',default=fields.Date.context_today)
    division = fields.Selection([
                                 ('Unit','Showroom'),
                                 ('Sparepart','Workshop'),
                                 ('Umum','General'),
                                 ('Finance','Finance')
                                 ],required=True,string='Division')
    state = fields.Selection([
            ('draft','Draft'),
            ('waiting_for_approval','Waiting Approval'),
            ('approved','Approved'),
            ('done','Done'),
            ('cancel','Cancelled')
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,)
    description = fields.Text(string='Description')
    payment_method = fields.Many2one('account.journal',string='Payment Method',required=True)
    type = fields.Selection([
                             ('tambah','Tambah'),
                             ('kembali','Kembali')                             
                             ],string='Type Kas')
    amount_total = fields.Float(string='Total',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount')
    amount_gap = fields.Float(string='Total Kembalian/Tambahan',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount')
    settlement_line = fields.One2many('dym.settlement.line','settlement_id',required=True)
    account_id = fields.Many2one('account.account',string='Account Advance Payment')
    account_move_id = fields.Many2one('account.move')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    clearing_bank = fields.Boolean(string='Clearing Bank')
    journal_is_bank = fields.Boolean('Journal is Bank', compute='_journal_is_bank')
    allow_backdate = fields.Boolean(string='Backdate', default=_get_default_backdate)
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
        
    # _sql_constraints = [
    # ('unique_advance_payment_id', 'unique(advance_payment_id)', 'Nomor Advance Payment sudah pernah di buat sudah ada !'),
    # ]
    
    @api.constrains('advance_payment_id')
    def advance_payment_constraint(self):
        if self.advance_payment_id.id:
            settle_avp = self.search([('advance_payment_id','=', self.advance_payment_id.id),('state','!=', 'cancel')])
            if len(settle_avp)>1:
                raise Warning("Nomor Advance Payment sudah pernah di buat!")

    @api.onchange('payment_method','type')
    def payment_method_change(self):
        self.clearing_bank = False
        if self.payment_method.type == 'bank':
            self.journal_is_bank = True
        else:
            self.journal_is_bank = False
    
    @api.multi
    def get_sequence(self,branch_id,context=None):
        doc_code = self.env['dym.branch'].browse(branch_id).doc_code
        seq_name = 'SAP-G/{0}'.format(doc_code)
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
        if not values['settlement_line'] and values['type'] != 'kembali':
            raise Warning("Tidak Ada detail Settlement, tidak bisa di save")
        obj_branch_config = self.env['dym.branch.config'].search([('branch_id','=',values['branch_id'])])
        if not obj_branch_config:
            raise Warning("Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu")
        else:
            if not(obj_branch_config.dym_advance_payment_account_id):
                raise Warning("Konfigurasi cabang jurnal Advance Payment belum dibuat, silahkan setting dulu")
        # values['name'] = self.get_sequence(values['branch_id'],context)
        values['name'] = self.env['ir.sequence'].get_sequence('SAP', division=values['division'], padding=6, branch=obj_branch_config.branch_id)
        # values['date'] = datetime.today()
        settlement = super(dym_settlement,self).create(values)
        amount_line = 0
        for line in settlement.settlement_line:
            if line.amount <= 0 and values['type']!='kembali':
                raise Warning("Amount detail settlement harus lebih dari 0")
            amount_line += line.amount
        debit = settlement.total_net 
        credit = settlement.amount_avp
        if settlement.type == 'kembali':
            if settlement.total_net >= settlement.amount_avp:
                raise Warning('Amount harus lebih kecil dari total AVP untuk tipe kembali')
            debit += abs(settlement.amount_gap)
        elif settlement.type == 'tambah':
            if settlement.total_net <= settlement.amount_avp:
                raise Warning('Amount harus lebih besar dari total AVP untuk tipe tambah')
            credit += abs(settlement.amount_gap)
        if debit != credit:
            raise Warning("Data tidak balance! Mohon di cek kembali. credit: %s, debit: %s" % (credit,debit))
        # raise Warning("credit: %s, debit: %s" % (credit,debit))
        return settlement

    @api.multi
    def write(self,values,context=None):
        settlement = super(dym_settlement,self).write(values)
        amount_line = 0
        for line in self.settlement_line:
            if line.amount <= 0 and self.type!='kembali':
                raise Warning("Amount detail settlement harus lebih dari 0")
            amount_line += line.amount
        debit = self.total_net 
        credit = self.amount_avp
        if self.type == 'kembali':
            debit += abs(self.amount_gap)
        elif self.type == 'tambah':
            credit += abs(self.amount_gap)
        if debit != credit:
            raise Warning("Data tidak balance! Mohon di cek kembali. credit: %s, debit: %s" % (credit,debit))
        return settlement

    @api.multi
    def onchange_avp_id(self,advance_payment_id):
        avp = self.env['dym.advance.payment'].browse(advance_payment_id)
        result = {'value':{
                  'user_id':avp.user_id.id,
                  'branch_id': avp.branch_id.id,
                  'division': avp.division,
                  'amount_avp': avp.open_balance,
                  'account_id': avp.account_id.id,
                  'payment_method': avp.payment_method.id
                  }}
        
        return result
    
    @api.multi
    def wkf_action_confirm(self,context=None):
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        date = self.date if self.journal_is_bank else datetime.now().strftime('%Y-%m-%d')
        period_ids = self.env['account.period'].find(dt=date)
        tax_wh_obj = self.env['account.tax.withholding']
        
        obj_branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if not obj_branch_config:
            raise Warning("Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu")
        else:
            if not(obj_branch_config.dym_advance_payment_account_id) or not(obj_branch_config.advance_payment_hutang_lain):
                raise Warning("Branch Configuration Jurnal Advance Payment belum dibuat, silahkan setting terlebih dulu")
        
        account_id = self.payment_method.default_credit_account_id.id or self.payment_method.default_debit_account_id.id
            
        move_line_values = []
        move_journal = {
                        'name': self.name,
                        'ref': self.advance_payment_id.name or self.description or False,
                        'journal_id': self.payment_method.id,
                        'date': date,
                        'period_id':period_ids.id,
                        'transaction_id':self.id,
                        'model':self.__class__.__name__,
                        }
        # amount = self.amount_total
        # if self.type == 'kembali':
        #     amount = self.amount_avp
        amount = self.amount_total if self.type == 'tambah' else self.amount_avp

        for line in self.settlement_line:
            tran_id = line.invoice_id or line.voucher_id
            if tran_id:
                move_line_ids = move_line_obj.search([('move_id','=',tran_id.move_id.id),('account_id','=',line.account_id.id)])
                for move_line in move_line_ids:
                    tax_withholding = tax_wh_obj.search([('account_id','=',move_line.account_id.id)])

                    # if move_line.account_id.type == 'payable' and not tax_withholding and move_line.credit > 0:
                    if not tax_withholding and move_line.credit > 0:
                        move_line_values.append([0,False,{
                            'ref': self.advance_payment_id.name or move_line.ref or False,
                            'name': move_line.name,
                            'partner_id': move_line.partner_id.id,
                            'account_id': move_line.account_id.id,
                            'period_id': period_ids.id,
                            'date': date,
                            'date_maturity': datetime.now().strftime('%Y-%m-%d'),
                            'debit': move_line.credit,
                            # 'debit': self.amount_avp,
                            'credit': 0.0,
                            'branch_id': move_line.branch_id.id,
                            'company_id': move_line.company_id.id,
                            'division': move_line.division,
                            'analytic_account_id' : move_line.analytic_account_id.id,
                        }])
            elif line.amount > 0:
                move_line_values.append([0,False,{
                    'ref': self.advance_payment_id.name or self.description or False,
                    'name': self.advance_payment_id.description or self.advance_payment_id.name,
                    'partner_id': self.user_id.id,
                    'account_id': line.account_id.id,
                    'period_id': period_ids.id,
                    'date': date,
                    'date_maturity': datetime.now().strftime('%Y-%m-%d'),
                    'debit': line.amount,
                    'credit': 0.0,
                    'branch_id': self.branch_id.id,
                    'company_id': self.branch_id.company_id.id,
                    'division': self.division,
                    'analytic_account_id': line.analytic_account_id.id, 
                }])

        if self.withholding_ids:
            # line.write({'credit':line.credit - self.withholdings_amount})
            for pph in self.withholding_ids:
                # amount -= pph.amount
                move_line_values.append([0,False,{
                                    'name': pph.comment or self.description or self.advance_payment_id.description or '/',
                                    'ref': self.name or '/',
                                    'account_id': pph.tax_withholding_id.account_id.id,
                                    'journal_id': self.payment_method.id,
                                    'period_id': period_ids.id,
                                    'date': date,
                                    # 'date_maturity':self.date_due,
                                    'debit': 0,
                                    'credit': pph.amount,
                                    'branch_id' : self.branch_id.id,
                                    'division' : self.division,
                                    'partner_id' : pph.partner_id.id,
                                    'company_id': self.branch_id.company_id.id,
                                    # 'move_id': self.move_id.id,
                                    # 'analytic_account_id' : line.analytic_account_id.id,
                                    'analytic_account_id' : self.advance_payment_id.analytic_account_id.id,
                                    'tax_code_id':pph.tax_withholding_id.tax_code_id.id,
                                    'tax_amount':pph.tax_base,
                                    # 'analytic_4':self.analytic_4.id,
                                }])

        if self.type == 'tambah':
            amount -= (self.amount_gap + self.withholdings_amount)
            move_line_values.append([0,False,{
                'ref': self.advance_payment_id.name or self.description or False,
                'name': _('Kekurangan Advance Payment'),
                'partner_id': self.user_id.id,
                'account_id': account_id if not self.journal_is_bank else obj_branch_config.advance_payment_hutang_lain.id,
                'period_id': period_ids.id,
                'date': date,
                'date_maturity': datetime.now().strftime('%Y-%m-%d'),
                'debit': 0.0,
                'credit': abs(self.amount_gap),
                'branch_id': self.branch_id.id,
                'company_id': self.branch_id.company_id.id,
                'division': self.division,
                'analytic_account_id' : self.advance_payment_id.analytic_account_id.id,
                'clear_state': 'open' if self.clearing_bank == True else 'not_clearing',
            }])
        elif self.type == 'kembali':
            # amount -= self.amount_gap
            amount_gap = self.amount_gap
            move_line_values.append([0,False,{
                'ref': self.advance_payment_id.name or self.description or False,
                'name': _('Kembalian Advance Payment'),
                'partner_id': self.user_id.id,
                'account_id': self.payment_method.default_debit_account_id.id or self.payment_method.default_credit_account_id.id,
                'period_id': period_ids.id,
                'date': date,
                'date_maturity': datetime.now().strftime('%Y-%m-%d'),
                'debit': abs(amount_gap),
                'credit': 0.0,
                'branch_id': self.branch_id.id,
                'company_id': self.branch_id.company_id.id,
                'division': self.division,
                'analytic_account_id' : self.advance_payment_id.analytic_account_id.id,
            }])

        move_line_values.append([0,False,{
            'ref': self.advance_payment_id.name or self.description or False,
            'name': _('Payment Amount'),
            'partner_id': self.user_id.id,
            'account_id': self.account_id.id,
            'period_id': period_ids.id,
            'date': date,
            'debit': 0.0,
            'credit': amount,
            'branch_id': self.branch_id.id,
            'company_id': self.branch_id.company_id.id,
            'division': self.division,
            'analytic_account_id' : self.advance_payment_id.analytic_account_id.id,
        }])
        
        move_journal['line_id']=move_line_values
        create_journal = move_obj.create(move_journal)
        if self.payment_method.entry_posted:
            create_journal.post()
        move_line_avp = move_line_obj.search([('move_id','=',self.advance_payment_id.account_move_id.id),('account_id','=',self.account_id.id)])
        move_line_stl = move_line_obj.search([('move_id','=',create_journal.id),('account_id','=',self.account_id.id)])
        
        if not self.settlement_line[0].invoice_id:
            self.pool.get('account.move.line').reconcile_partial(self._cr,self._uid, [move_line_avp.id,move_line_stl.id],'auto')
        if self.settlement_line[0].invoice_id:
            self.settlement_line[0].invoice_id.state = 'paid'
        
        self.write({'state':'done','account_move_id':create_journal.id,'confirm_uid':self._uid,'confirm_date':datetime.now()})
        workflow.trg_validate(self._uid, 'dym.advance.payment', self.advance_payment_id.id, 'avp_done', self._cr)
        self.advance_payment_id.write({'source_settlement':self.name})
        return True

    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Settlement sudah diproses, data tidak bisa dihapus !"))
        return super(dym_settlement, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def wkf_action_cancel(self):
        if self.account_move_id:
            reimbursed_id = self.env['dym.reimbursed.ho.line'].search([('settlement_id','=',self.id)]).reimbursed_id
            for line in self.settlement_line:
                if line.invoice_id or line.voucher_id:
                    raise osv.except_osv(('Perhatian !'), ("Maaf settlement voucher atau invoice tidak dapat dicancel."))
            if not reimbursed_id:
                MoveLine = self.env['account.move.line']
                self.account_move_id.action_reverse_journal()
                avp_id = self.env['dym.advance.payment'].browse([self.advance_payment_id.id])
                move_line_id = MoveLine.search([('move_id','=',avp_id.account_move_id.id),('debit','>',0)])
                MoveLine._remove_move_reconcile([move_line_id.id])
                avp_id.delete_workflow()
                avp_id.create_workflow()
                # avp_id.signal_workflow('confirm')
                workflow.trg_validate(self._uid, avp_id._name, self.advance_payment_id.id, 'confirmed', self._cr)
                avp_id.write({'state':'confirmed','source_settlement':'','open_balance':self.amount_avp})
                # raise osv.except_osv(('Perhatian !'), ("debug!"))
            else:
                raise osv.except_osv(('Perhatian !'), ("Settlement sudah direimburse %s, data tidak bisa dicancel!" % (reimbursed_id.name)))
        self.write({'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
        
class dym_settlement_line(models.Model):
    _name = 'dym.settlement.line'
        
    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_advance_payment] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]    
        
    settlement_id = fields.Many2one('dym.settlement',ondelete='cascade')
    invoice_id = fields.Many2one('account.invoice', string="Invoice")
    voucher_id = fields.Many2one('account.voucher', string="Voucher")
    account_id = fields.Many2one('account.account',string='Account',required=True)
    # for_branch = fields.Boolean('For Branch', related='settlement_id.for_branch')
    amount = fields.Float(string='Amount',required=True)
    analytic_1 = fields.Many2one('account.analytic.account', string='Account Analytic Company', default=_get_analytic_company)
    analytic_2 = fields.Many2one('account.analytic.account', string='Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', string='Account Analytic Branch')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Account Analytic Cost Center')

    @api.model
    def create(self, vals):
        invoice = vals.get('invoice_id', False)
        if invoice:
            analytic_branch = self.env['account.analytic.account'].browse(vals.get('analytic_3', False))
            invoice_id = self.env['account.invoice'].browse(invoice)
            branch_conf = self.env['dym.branch.config'].search([('branch_id','=',analytic_branch.branch_id.id)])
            if invoice_id.journal_id.id != branch_conf.tagihan_birojasa_bbn_journal_id.id and not invoice_id.consolidated:
                raise osv.except_osv(('Perhatian !'), ("Maaf invoice harus condolidate terlebih dahulu!"))
        return super(dym_settlement_line, self).create(vals)

    @api.onchange('invoice_id')
    def onchange_by_invoice(self):
        if self.invoice_id:
            self.account_id = self.invoice_id.account_id.id
            self.analytic_2 = self.invoice_id.analytic_2.id
            self.analytic_3 = self.invoice_id.analytic_3.id
            self.analytic_account_id = self.invoice_id.analytic_4.id
            self.amount = self.invoice_id.total_net

    @api.onchange('voucher_id')
    def onchange_by_voucher(self):
        if self.voucher_id:
            move_line_obj = self.env['account.move.line']
            move_line = move_line_obj.search([('move_id','=',self.voucher_id.move_id.id),('credit','>',0)])
            self.account_id = move_line.account_id.id
            self.analytic_2 = self.voucher_id.analytic_2.id
            self.analytic_3 = self.voucher_id.analytic_3.id
            self.analytic_account_id = self.voucher_id.analytic_4.id
            self.amount = self.voucher_id.net_amount
    
    @api.onchange('account_id','voucher_id')
    def name_change(self):
        dom = {}
        edi_doc_list = ['&', ('active','=',True), ('type','!=','view')]
        if not self.voucher_id:
            filter = self.env['dym.account.filter']         
            dict = filter.get_domain_account("settlement_advance_payment")
            edi_doc_list.extend(dict)
        dom['account_id']=edi_doc_list
        return {'domain':dom}
    
    @api.onchange('account_id')
    def onchange_account_id(self):
        dom = {}
        if self.account_id:
            self.name = self.account_id.name
            if self.settlement_id.branch_id.id and self.settlement_id.division:
                aa2_ids = self.env['analytic.account.filter'].get_analytics_2(self.settlement_id.branch_id.id, self.settlement_id.division, self.account_id.id)
                if aa2_ids:
                    dom['analytic_2'] = [('id','in',aa2_ids.ids)]
                    self.analytic_2 = aa2_ids[0]
        return {'domain':dom}

    @api.onchange('account_id','analytic_2')
    def onchange_analytic_2(self):
        dom = {}
        if self.analytic_2 and self.settlement_id.branch_id.id and self.settlement_id.division:
            aa3_ids = self.env['analytic.account.filter'].get_analytics_3(self.settlement_id.branch_id.id, self.settlement_id.division, self.account_id.id, self.analytic_2.code, self.analytic_2.id)
            if aa3_ids:
                dom['analytic_3'] = [('id','in',aa3_ids.ids)]
                self.analytic_3 = aa3_ids[0]
        return {'domain':dom}

    @api.onchange('analytic_2','analytic_3','account_id')
    def onchange_analytic_3(self):
        dom = {}
        if self.analytic_2 and self.analytic_3 and self.settlement_id.branch_id.id and self.settlement_id.division and self.account_id:
            aa4_ids = self.env['analytic.account.filter'].get_analytics_4(self.settlement_id.branch_id.id, self.settlement_id.division, self.account_id.id, self.analytic_2.code, self.analytic_2.id, self.analytic_3.id)            
            dom['analytic_account_id'] = [('id','in',[])]
            if aa4_ids:
                dom['analytic_account_id'] = [('id','in',aa4_ids.ids)]
                self.analytic_account_id = aa4_ids[0]
        return {'domain':dom}
    
    @api.multi
    def onchange_amount(self,amount,type,total_avp):
        return True
        # if amount:
        #     if amount < 0:
        #         raise exceptions.ValidationError('Tidak boleh input nilai negatif')
            
        #     if type == 'kembali':
        #         if amount >= total_avp:
        #             #raise exceptions.ValidationError('Amount harus lebih kecil dari total AVP untuk tipe kembali')
        #             return {'value':{'settlement_id':False,'account_id':False,'amount':0,'amount_total':0,'amount_gap':0},'warning':{'title':'Perhatian !','message':'Amount harus lebih kecil dari total AVP untuk tipe kembali'}}
        #     elif type == 'tambah':
        #         if amount <= total_avp:
        #             #raise exceptions.ValidationError('Amount harus lebih besar dari total AVP untuk tipe tambah')
        #             return {'value':{'settlement_id':False,'account_id':False,'amount':0},'warning':{'title':'Perhatian !','message':'Amount harus lebih besar dari total AVP untuk tipe tambah'}}
        #     else:
        #         if amount != total_avp:
        #             return {'value':{'settlement_id':False,'account_id':False,'amount':0},'warning':{'title':'Perhatian !','message':'Amount harus sama dengan total AVP'}}
        #             #raise exceptions.ValidationError('Amount harus sama dengan total AVP')
