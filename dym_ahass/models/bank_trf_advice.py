
import json
from datetime import datetime
from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class BankTrfAdvice(models.Model):
    _inherit = 'bank.trf.advice'

    branch_via_id = fields.Many2one('dym.branch', string='Via Branch', domain="[('company_id','=',company_id)]")

    @api.multi
    def action_submit(self):
        for rec in self:
            #Tambahan kondisi pemilihan branch
            branch = False
            if rec.branch_via_id:
                branch = rec.branch_via_id
            else:
                branch = self.env['dym.branch'].search([('code','=',rec.branch_destination_id)])
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.env['account.analytic.account'].get_analytical(branch, 'Umum', False, 4, 'General')
            bta_date = datetime.strptime(rec.date, DEFAULT_SERVER_DATE_FORMAT)
            period_id = self.env['account.period'].search([('company_id','=',self.env.user.company_id.id),('date_start','<=',bta_date),('date_stop','>=',bta_date)])

            voucher_lines = []
            reimburse_lines = []
            bank_trf_request_ids = []
            for rec1 in rec.bank_trf_request_ids: 
                bank_trf_request_ids.append(rec1.id)             
                if rec1.obj == 'account.voucher':
                    for rec2 in self.env[rec1.obj].browse([rec1.res_id]):
                        for rec3 in rec2.line_dr_ids:
                            voucher_lines.append(
                                (0,0,{
                                    'voucher_id': rec2.id,
                                    'notes': ' '.join([rec3.account_id.name,rec3.name]),
                                    'account_id': rec3.account_id.id,
                                    'line_amount': rec3.amount,
                                })
                            )
            branch_destination = self.env['dym.branch'].search([('code','=',rec.branch_destination_id)])
            lines = {
                'branch_destination_select': branch_destination.id,
                'branch_destination_id': branch_destination.code,
                'payment_to_id': rec.payment_to_id.id,
                'description': rec.description,
                'analytic_1': analytic_1_general,
                'analytic_2': analytic_2_general,
                'analytic_3': analytic_3_general,
                'analytic_4': analytic_4_general,
                'amount': rec.amount,
                'reimbursement_id': False, 
            }
            # Analytic untuk header bank transfer
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.env['account.analytic.account'].get_analytical(rec.branch_id, 'Umum', False, 4, 'General') 
            values = {
                'allow_backdate': True,
                'name': '/',
                'company_id': rec.company_id.id,
                'branch_id': rec.branch_id.id,
                'division': 'Finance',
                'inter_branch_id': branch_destination.id,
                'branch_via_id': rec.branch_via_id.id,
                'inter_branch_division': 'Umum',
                'state': 'draft',
                'date': rec.transfer_date,
                'payment_from_id': rec.payment_from_id.id,
                'description': rec.description,
                'period_id': period_id.id,
                'note': 'Notes',
                'journal_type': 'bank',
                'analytic_1': analytic_1_general,
                'analytic_2': analytic_2_general,
                'analytic_3': analytic_3_general,
                'analytic_4': analytic_4_general,
                'value_date': False,
                'transfer_type': 'branch_replenishment',
                'transaction_type': 'ho2branch',
                'branch_type': rec.branch_id.branch_type, 
                'voucher_ids': voucher_lines,
                'bank_trf_request_ids': [(6,0,bank_trf_request_ids)],
                'ref': 'reffff',
                'bank_trf_advice_id': rec.id,
                'payment_from_id_ho2branch': rec.payment_from_id.id,
                'value_date': rec.transfer_date,
                'line_ids': [(0,False,lines)],
                # isi amount bank transfer
                'amount': lines['amount'],
            }
            trf_id = self.env['dym.bank.transfer'].create(values)
            rec.state = 'done'
            
        view_id = self.env.ref('dym_bank_transfer.banktransfer_form_view').id
        return {
            'name' : _('Bank Transfer'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': trf_id.id,
            'res_model': 'dym.bank.transfer',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': False,
            'context': self.env.context
        }


    # @api.multi
    # def action_rfa(self):
    #     for rec in self:
    #         rec.state = 'approved'
    #         for btrq in rec.bank_trf_request_ids:
    #             if btrq.obj == 'dym.reimbursed':
    #                 for prc_id in self.env['dym.reimbursed'].browse([btrq.res_id]):
    #                     prc_id.state = 'hoapproved'
    #             if btrq.obj == 'dym.reimbursed.bank':
    #                 for prc_id in self.env['dym.reimbursed.bank'].browse([btrq.res_id]):
    #                     prc_id.state = 'hoapproved'

    # @api.multi
    # def action_reset_draft(self):
    #     for rec in self:
    #         rec.revision_number = rec.revision_number + 1
    #         rec.state = 'draft'

    # @api.multi
    # def action_cancel(self):
    #     for rec in self:
    #         rec.state = 'cancel'

    # @api.multi
    # def action_confirm(self):
    #     for rec in self:
    #         rec.state = 'confirmed'
