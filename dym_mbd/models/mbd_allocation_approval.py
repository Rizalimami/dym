from openerp import models, fields, api
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import netsvc
from openerp.osv import osv

class dym_mbd_allocation_approval(models.Model):
    _inherit = 'dym.mbd.allocation'
    
    approval_ids = fields.One2many('dym.approval.line', 'transaction_id', string="Table Approval", domain=[('form_id','=',_inherit)])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Reject')
        ], 'Approval State', readonly=True, default='b')
    approve_uid = fields.Many2one('res.users',string="Approved by")
    approve_date = fields.Datetime('Approved on')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')    
        
    @api.multi
    def wkf_request_approval(self):
        titipan_line_list = []
        titipan_line_dict = {}
        if not self.line_ids:
            raise osv.except_osv(('Perhatian !'), ("Mohon lengkapi data")) 

        for line in self.line_ids:
            if line.titipan_line_id not in titipan_line_list:
                titipan_line_list.append(line.titipan_line_id)
                titipan_line_dict[line.titipan_line_id] = {'amount':0}
            titipan_line_dict[line.titipan_line_id]['amount'] += line.amount
        for titipan_line in titipan_line_list:
            allocated_amount = titipan_line_dict[titipan_line]['amount']
            if allocated_amount > titipan_line.fake_balance:
                raise osv.except_osv(('Tidak bisa request approval!'), ("Total Customer Deposit [%s] untuk titipan %s lebih besar dari balance yang bisa dialokasikan [%s]")%(allocated_amount, titipan_line.name, titipan_line.fake_balance))
        obj_matrix = self.env['dym.approval.matrixbiaya']
        obj_matrix.request_by_value(self,self.total_alokasi)
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
        return True
    
    @api.model
    def action_create_other_receivable_voucher(self):
        return self._action_create_other_receivable_voucher()

    @api.multi
    def _action_create_other_receivable_voucher(self):
        Config = self.env['dym.branch.config']

        if not self.account_id.tax_ids:
            raise exceptions.ValidationError(("Akun %s %s tidak memiliki default pajak PPN, silahkan setting dulu di form account: Accounting > Confifuration > Accounts > Accounts." % (self.account_id.code,self.account_id.name)))

        if not self.account_id.withholding_tax_ids:
            raise exceptions.ValidationError(("Akun %s %s tidak memiliki default pajak PPH, silahkan setting dulu di form account: Accounting > Confifuration > Accounts > Accounts." % (self.account_id.code,self.account_id.name)))

        if len(self.account_id.tax_ids)>1:
            raise exceptions.ValidationError(("Akun %s %s memiliki lebih dari 1 jenis pajak PPN, silahkan setting satu saja di form account: Accounting > Confifuration > Accounts > Accounts." % (self.account_id.code,self.account_id.name)))

        if len(self.account_id.withholding_tax_ids)>1:
            raise exceptions.ValidationError(("Akun %s %s memiliki lebih dari 1 jenis pajak PPH, silahkan setting satu saja di form account: Accounting > Confifuration > Accounts > Accounts." % (self.account_id.code,self.account_id.name)))

        config_id = Config.search([('branch_id','=',self.inter_branch_id.id)])
        if not config_id.dym_mbd_income_account:
            raise exceptions.ValidationError(("Cabang %s tidak memiliki akun pendapatan atas program TAC/MBD. Silahkan setting di Branch Config" % (self.branch_id.name)))

        WHT = self.env['account.tax.withholding']
        wht_id = WHT.browse(67)
        analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.inter_branch_id, self.inter_division, False, 4, 'Sales')

        periode_name = datetime.strftime(datetime.strptime(self.value_date, '%Y-%m-%d'), "%B %Y") or None

        voucher_cr_line = [[0,0,{
            # 'move_line_id': move_line_ar_vals['value']['move_line_id'], 
            'account_id': config_id.dym_mbd_income_account.id, 
            'date_original': self.value_date, 
            'date_due': self.value_date,
            'amount_original':self.total_dpp, 
            'amount_unreconciled':self.total_dpp,
            'amount': self.total_dpp, 
            'currency_id': self.journal_id.default_credit_account_id.currency_id.id or False, 
            'type': 'cr', 
            'name': 'Subsidi program leasing periode: %s' % periode_name,
            'reconcile': True,
            'analytic_1': analytic_1,
            'analytic_2': analytic_2,
            'analytic_3': analytic_3,
            'account_analytic_id': analytic_4,
        }]]

        withholding_ids = [(0,0,{
            'tax_withholding_id': 67,
            'tax_base': self.total_dpp,
            'amount': self.total_dpp * wht_id.amount,
            'date': self.value_date,
        })]

        analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.branch_id, 'Umum', False, 4, 'General')

        voucher_data = {
            'pay_now': 'pay_later',
            'date': self.value_date,
            'date_due': self.value_date,
            'reference': self.name,
            'user_id': self.env.user.id,
            'company_id': self.branch_id.company_id.id,
            'branch_id': self.branch_id.id,
            'inter_branch_id': self.inter_branch_id.id,
            'partner_id': self.partner_id.id,
            'journal_id': self.journal_id.id,
            'division': self.division,
            'inter_branch_division': self.inter_division,
            'amount': self.total_dpp,
            'net_amount': self.total_dpp,
            'account_id': self.account_id.id,
            'state': 'draft',
            'type': 'sale',
            'analytic_2': analytic_2,
            'analytic_3': analytic_3,
            'analytic_4': analytic_4,
            'line_dr_ids': voucher_cr_line,
            'line_cr_ids': [],
            'withholding_ids': withholding_ids,
            'tax_id': 23,
        }
        voucher_id = self.env['account.voucher'].create(voucher_data)
        self.voucher_id = voucher_id.id
        return True

    @api.multi
    def wkf_approval(self):
        titipan_line_list = []
        titipan_line_dict = {}
        for line in self.line_ids:
            if line.titipan_line_id not in titipan_line_list:
                titipan_line_list.append(line.titipan_line_id)
                titipan_line_dict[line.titipan_line_id] = {'amount':0}
            titipan_line_dict[line.titipan_line_id]['amount'] += line.amount
        for titipan_line in titipan_line_list:
            allocated_amount = titipan_line_dict[titipan_line]['amount']
            if allocated_amount > titipan_line.fake_balance:
                raise osv.except_osv(('Tidak bisa approve!'), ("Total Customer Deposit [%s] untuk titipan %s lebih besar dari balance yang bisa dialokasikan [%s]")%(allocated_amount, titipan_line.name, titipan_line.fake_balance))
        approval_sts = self.env['dym.approval.matrixbiaya'].approve(self)
        if approval_sts == 1 :
            self.write({'approval_state':'a', 'state':'approved','approve_uid':self._uid,'approve_date':datetime.now()})
        elif approval_sts == 0 :
            raise exceptions.ValidationError( ("User tidak termasuk group approval"))
        self.action_create_other_receivable_voucher()
        return True

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
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})