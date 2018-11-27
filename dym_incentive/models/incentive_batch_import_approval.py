from openerp import models, fields, api
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import netsvc
from openerp.osv import osv
import json

class IncentiveBatchImport(models.Model):
    _inherit = 'dym.incentive.batch.import'
    
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
        for inc in self.incentive_ids:
            if not inc.line_ids:
                raise osv.except_osv(('Perhatian !'), ("Mohon lengkapi data untuk incecntive nomor %s" % inc.name)) 
        if self.partner_id.incentive_payment_type=='prepaid':
            allocated_amount = 0.0
            titipan_amount = 0.0
            for inc in self.incentive_ids:
                allocated_amount += inc.total_cair
                titipan_amount += sum([l.amount for l in inc.line_ids])
            if allocated_amount != titipan_amount:
                raise osv.except_osv(('Perhatian !'), ("Total Cair/Allocated Amount (%d) tidak sama dengan Total Titipan (%d)" % (allocated_amount,titipan_amount))) 
        else:
            print "Tidak diperlukan deposit ...."
        obj_matrix = self.env['dym.approval.matrixbiaya']
        obj_matrix.request_by_value(self,self.total_cair)
        for inc in self.incentive_ids:
            inc.wkf_request_approval()
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
        return True

    @api.multi
    def wkf_approval(self):
        approval_sts = self.env['dym.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'approval_state':'a', 'state':'approved','approve_uid':self._uid,'approve_date':datetime.now()})
        elif approval_sts == 0:
            raise exceptions.ValidationError( ("User tidak termasuk group approval"))
        
        for inc in self.incentive_ids:
            inc.wkf_approval()

        voucher_id = self.action_create_other_receivable_voucher_batch()
        for inc in self.incentive_ids:
            inc.write({'voucher_id': voucher_id})
        return True

    @api.model
    def action_create_other_receivable_voucher_batch(self):
        return self._action_create_other_receivable_voucher_batch()

    @api.multi
    def _action_create_other_receivable_voucher_batch(self):

        Config = self.env['dym.branch.config']
        config_id = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)], limit =1)

        if not config_id.dym_incentive_income_account:
            raise exceptions.ValidationError(("Cabang %s tidak memiliki akun pendapatan atas program Incentive. Silahkan setting di Branch Config" % (self.inter_branch_id.name)))

        if not config_id.dym_incentive_income_account.tax_ids:
            raise exceptions.ValidationError(("Akun %s %s tidak memiliki default pajak PPN, silahkan setting dulu di form account: Accounting > Confifuration > Accounts > Accounts." % (config_id.dym_incentive_income_account.code,config_id.dym_incentive_income_account.name)))

        if not config_id.dym_incentive_income_account.withholding_tax_ids:
            raise exceptions.ValidationError(("Akun %s %s tidak memiliki default pajak PPH, silahkan setting dulu di form account: Accounting > Confifuration > Accounts > Accounts." % (config_id.dym_incentive_income_account.code,config_id.dym_incentive_income_account.name)))

        if len(config_id.dym_incentive_income_account.tax_ids)>1:
            raise exceptions.ValidationError(("Akun %s %s memiliki lebih dari 1 jenis pajak PPN, silahkan setting satu saja di form account: Accounting > Confifuration > Accounts > Accounts." % (config_id.dym_incentive_income_account.code,config_id.dym_incentive_income_account.name)))

        if len(config_id.dym_incentive_income_account.withholding_tax_ids)>1:
            raise exceptions.ValidationError(("Akun %s %s memiliki lebih dari 1 jenis pajak PPH, silahkan setting satu saja di form account: Accounting > Confifuration > Accounts > Accounts." % (config_id.dym_incentive_income_account.code,config_id.dym_incentive_income_account.name)))

        if not self.account_id.tax_ids:
            raise exceptions.ValidationError(("Akun %s %s tidak memiliki default pajak PPN, silahkan setting dulu di form account: Accounting > Confifuration > Accounts > Accounts." % (self.account_id.code,self.account_id.name)))

        if not self.account_id.withholding_tax_ids:
            raise exceptions.ValidationError(("Akun %s %s tidak memiliki default pajak PPH, silahkan setting dulu di form account: Accounting > Confifuration > Accounts > Accounts." % (self.account_id.code,self.account_id.name)))

        if len(self.account_id.tax_ids)>1:
            raise exceptions.ValidationError(("Akun %s %s memiliki lebih dari 1 jenis pajak PPN, silahkan setting satu saja di form account: Accounting > Confifuration > Accounts > Accounts." % (self.account_id.code,self.account_id.name)))

        if len(self.account_id.withholding_tax_ids)>1:
            raise exceptions.ValidationError(("Akun %s %s memiliki lebih dari 1 jenis pajak PPH, silahkan setting satu saja di form account: Accounting > Confifuration > Accounts > Accounts." % (self.account_id.code,self.account_id.name)))

        total_dpp = 0
        total_cair = 0
        line_value = []

        for inc in self.incentive_ids:

            WHT = self.env['account.tax.withholding']
            analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(inc.inter_branch_id, inc.inter_division, False, 4, 'Sales')
            periode_name = datetime.strftime(datetime.strptime(inc.value_date, '%Y-%m-%d'), "%B %Y") or None
            
            line_value.append([0,0,{
                'account_id': config_id.dym_incentive_income_account.id, 
                'date_original': inc.value_date, 
                'date_due': inc.value_date,
                'amount_original':inc.total_dpp, 
                'amount_unreconciled':inc.total_dpp,
                'amount': inc.total_dpp,
                'currency_id': config_id.dym_incentive_income_account.currency_id.id or False, 
                'type': 'cr', 
                'name': inc.description,
                'reconcile': True,
                'analytic_1': analytic_1,
                'analytic_2': analytic_2,
                'analytic_3': analytic_3,
                'account_analytic_id': analytic_4,
            }])

            total_dpp += inc.total_dpp
            total_cair += inc.total_cair
        voucher_dr_line = line_value
        withholding_ids = [[0,0,{
            'tax_withholding_id': config_id.dym_incentive_income_account.withholding_tax_ids[0].id,
            'tax_base': total_dpp,
            'amount': total_dpp * config_id.dym_incentive_income_account.withholding_tax_ids[0].amount,
            'date': self.value_date,
        }]]
        analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.branch_id, 'Umum', False, 4, 'General')

        voucher_data = {
            'branch_id': self.branch_id.id,
            'division': self.division,
            'inter_branch_id': self.branch_id.id,
            'inter_branch_division': self.division,
            'pay_now': 'pay_later',
            'date': self.value_date,
            'date_due': self.value_date,
            'reference': self.name,
            'user_id': self.env.user.id,
            'company_id': self.branch_id.company_id.id,
            'partner_id': self.partner_id.id,
            'journal_id': config_id.dym_incentive_allocation_journal.id,
            'amount': self.total_cair,
            'net_amount': self.total_cair,
            'account_id': config_id.dym_incentive_allocation_journal.default_debit_account_id.id,
            'state': 'draft',
            'type': 'sale',
            'analytic_2': analytic_2,
            'analytic_3': analytic_3,
            'analytic_4': analytic_4,
            'line_dr_ids': voucher_dr_line,
            'line_cr_ids': [],
            'withholding_ids': self.use_withholding and withholding_ids or False,
            'tax_id': self.partner_id.use_ppn and config_id.dym_incentive_income_account.tax_ids[0].id or False,
            'incentive_batch_id': self.id,
        }

        voucher_id = self.env['account.voucher'].create(voucher_data)
        voucher_id.validate_or_rfa_credit()
        voucher_id.signal_workflow('approval_approve')
        return voucher_id.id
