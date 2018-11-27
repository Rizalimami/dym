from openerp import models, fields, api
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import netsvc
from openerp.osv import osv

class BlindBonusBatchImport(models.Model):
    _inherit = 'dym.bb.batch.import'
    
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
        Config = self.env['dym.branch.config']
        config_id = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)], limit =1)

        if not config_id.dym_bb_journal:
            raise exceptions.ValidationError(("Cabang %s tidak memiliki journal piutang blind bonus. Silahkan setting di Branch Config" % (self.branch_id.name)))

        if not config_id.dym_bb_income_account_unit:
            raise exceptions.ValidationError(("Cabang %s tidak memiliki akun pendapatan blind bonus unit. Silahkan setting di Branch Config" % (self.branch_id.name)))

        if not config_id.dym_bb_income_account_oli:
            raise exceptions.ValidationError(("Cabang %s tidak memiliki akun pendapatan blind bonus oli. Silahkan setting di Branch Config" % (self.branch_id.name)))

        if not config_id.dym_bb_income_account_part:
            raise exceptions.ValidationError(("Cabang %s tidak memiliki akun pendapatan blind bonus part. Silahkan setting di Branch Config" % (self.branch_id.name)))

        if not self.line_ids:
            raise osv.except_osv(('Perhatian !'), ("Mohon lengkapi data untuk melanjutkan !")) 

        obj_matrix = self.env['dym.approval.matrixbiaya']
        obj_matrix.request_by_value(self,self.total_dpp)
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
        return True

    @api.multi
    def wkf_approval(self):
        titipan_line_list = []
        titipan_line_dict = {}
        approval_sts = self.env['dym.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'approval_state':'a', 'state':'approved','approve_uid':self._uid,'approve_date':datetime.now()})
        elif approval_sts == 0 :
            raise exceptions.ValidationError( ("User tidak termasuk group approval"))
        self.action_create_other_receivable_voucher()
        return True

    @api.model
    def action_create_other_receivable_voucher(self):
        return self._action_create_other_receivable_voucher()

    @api.multi
    def _action_create_other_receivable_voucher(self):
        Config = self.env['dym.branch.config']
        Fiscal = self.env['account.fiscal.position']
        vouchers = {}
        partners = []

        if not self.account_id.tax_ids:
            raise exceptions.ValidationError(("Account %s tidak memiliki default tax !" % self.account_id.name))




        for line in self.line_ids:

            if line.partner_id not in partners:
                partners.append(line.partner_id)
                analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.branch_id, 'Umum', False, 4, 'General')
                tax_id = Fiscal.map_tax(self.account_id.tax_ids)[0]
                vouchers[line.partner_id.id] = {
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
                    'partner_id': line.partner_id.id,
                    'journal_id': self.journal_id.id,
                    'account_id': self.account_id.id,
                    'state': 'draft',
                    'type': 'sale',
                    'analytic_2': analytic_2,
                    'analytic_3': analytic_3,
                    'analytic_4': analytic_4,
                    'line_cr_ids': [],
                    'line_dr_ids': [],
                    'withholding_ids': False,
                    'tax_id': tax_id.id,
                    'bb_batch_id': self.id,
                }

      
            branch_config_id = self.env['dym.branch.config'].search([('branch_id','=',line.inter_branch_id.id)], limit =1)
            analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(line.inter_branch_id, line.inter_division, False, 4, 'Sales')

            if not branch_config_id.dym_bb_income_account_unit:
                raise exceptions.ValidationError(("Cabang %s tidak memiliki akun pendapatan blind bonus unit. Silahkan setting di Branch Config" % (line.inter_branch_id.name)))

            values = {
                'account_id': branch_config_id.dym_bb_income_account_unit.id, 
                'date_original': self.value_date, 
                'date_due': self.value_date,
                'amount_original':line.amount_dpp, 
                'amount_unreconciled':line.amount_dpp,
                'amount': line.amount_dpp,
                'currency_id': branch_config_id.dym_bb_income_account_unit.currency_id.id or False, 
                'type': 'cr', 
                'name': self.memo,
                'reconcile': True,
                'analytic_1': analytic_1,
                'analytic_2': analytic_2,
                'analytic_3': analytic_3,
                'account_analytic_id': analytic_4,
            }
            vouchers[line.partner_id.id]['line_cr_ids'].append((0,0,values))

        new_vouchers = []
        for partner in partners:

            withholding_ids = [[0,0,{
                'tax_withholding_id': self.withholding_id.id,
                'tax_base': self.total_dpp,
                'amount': self.total_dpp * self.withholding_id.amount,
                'date': self.value_date,
            }]]

            vouchers[partner.id]['withholding_ids'] = withholding_ids
            voucher_id = self.env['account.voucher'].create(vouchers[partner.id])

            voucher_id.validate_or_rfa_credit()
            voucher_id.signal_workflow('approval_approve')
            new_vouchers.append(voucher_id.id)

        print ">>>>>>>>>",new_vouchers
        return True


