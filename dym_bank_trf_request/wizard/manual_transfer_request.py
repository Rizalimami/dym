# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api, models, fields
from openerp.tools.translate import _
from openerp.exceptions import Warning as UserError, RedirectWarning

class manual_transfer_request(models.TransientModel):
    _name = 'manual.transfer.request'


    @api.model
    def _get_default_branch(self):
        res = self.env.user.get_default_branch()
        return res

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")
    branch_id = fields.Many2one('dym.branch', string='From Branch', required=True, domain="[('company_id','=',company_id)]", default=_get_default_branch)
    doc_type = fields.Selection([
        ('supplier_invoice','Supplier Invoice'),
        ('payment_request','Payment Request'),
        ('customer_deposit','Customer Deposit'),
        ('pettycash_reimburse','Reimbuse Petty Cash'),
        ('bank_inout_reimburse','Bank In Out Reimbuse'),
        ], string='Document Type', default='supplier_invoice')
    inv_id = fields.Many2one('account.invoice', string='Supplier Invoice')
    par_id = fields.Many2one('account.voucher', string='Payment Request')
    cde_id = fields.Many2one('account.voucher', string='Customer Deposit')
    rpc_id = fields.Many2one('dym.reimbursed', string='Reimbuse Petty Cash')
    rbk_id = fields.Many2one('dym.reimbursed.bank', string='Reimbuse Bank')

    @api.multi
    def create_bank_transfer_request_from_supplier_invoice(self):
        inv = self.inv_id
        BankTransferRequest = self.env['bank.trf.request']
        if not BankTransferRequest.search([('res_id','=',inv.id),('obj','=','account.invoice')]):
            values = {
                'company_id': inv.company_id.id,
                'branch_id': inv.branch_id.id,
                'name': inv.number,
                'obj': 'account.invoice',
                'res_id': inv.id,
                'date_due': inv.date_due,
                'description': inv.comment,
                'amount': inv.amount_total,
                'partner_id': inv.partner_id.id,
                'state': 'confirmed',
            }
            req_id = BankTransferRequest.create(values)
            inv.transfer_request_id = req_id
            return req_id
        return False
    
    @api.multi
    def create_bank_transfer_request_from_payment_request(self):
        par = self.par_id
        BankTransferRequest = self.env['bank.trf.request']
        if not BankTransferRequest.search([('res_id','=',par.id),('obj','=','account.voucher')]):
            notes = '; '.join([l.name for l in par.line_dr_ids])
            
            amount = par.amount
            if par.withholdings_amount:
                amount = par.net_amount

            values = {
                'company_id': par.company_id.id,
                'branch_id': par.branch_id.id,
                'name': par.number,
                'obj': 'account.voucher',
                'res_id': par.id,
                'date_due': par.date_due,
                'description': par.comment,
                'notes': notes,
                'amount': amount,
                'partner_id': par.partner_id.id,
                'state': 'confirmed',
            }
            req_id = BankTransferRequest.create(values)
            par.transfer_request_id = req_id
            return req_id
        return False

    @api.multi
    def create_bank_transfer_request_from_customer_deposit(self):
        cde = self.cde_id
        BankTransferRequest = self.env['bank.trf.request']
        if not BankTransferRequest.search([('res_id','=',cde.id),('obj','=','account.voucher')]):
            notes = '; '.join([l.name for l in cde.line_dr_ids])
            values = {
                'company_id': cde.company_id.id,
                'branch_id': cde.branch_id.id,
                'name': cde.number,
                'obj': 'account.voucher',
                'res_id': cde.id,
                'date_due': cde.date_due,
                'description': cde.comment,
                'notes': notes,
                'amount': cde.amount,
                'partner_id': cde.partner_id.id,
                'state': 'confirmed',
            }
            req_id = BankTransferRequest.create(values)
            cde.transfer_request_id = req_id
            return req_id
        return False

    @api.multi
    def create_bank_transfer_request_from_pettycash_reimburse(self):
        rpc = self.rpc_id
        BankTransferRequest = self.env['bank.trf.request']
        if not BankTransferRequest.search([('res_id','=',rpc.id),('obj','=','dym.reimbursed')]):
            desc = []
            for line in rpc.line_ids:
                desc.append(line.name)
            description = ', '.join(desc)
            values = {
                'company_id': rpc.company_id.id,
                'branch_id': rpc.branch_id.id,
                'name': rpc.name,
                'obj': 'dym.reimbursed',
                'res_id': rpc.id,
                'date_due': rpc.date_approve,
                'description': description,
                'notes': rpc.notes,
                'amount': rpc.amount_total,
                'partner_id': rpc.company_id.partner_id.id,
                'state': 'confirmed',
            }
            req_id = BankTransferRequest.create(values)
            rpc.transfer_request_id = req_id
            return req_id
        return False

    @api.multi
    def create_bank_transfer_request_from_bank_inout_reimburse(self):
        rbk = self.rbk_id
        BankTransferRequest = self.env['bank.trf.request']
        if not BankTransferRequest.search([('res_id','=',rbk.id),('obj','=','dym.reimbursed.bank')]):
            description = 'Penggantian selisih biaya admin bank dan pendapatan jasa giro period %s - %s' % (rbk.period_start.name,rbk.period_end.name)
            values = {
                'company_id': rbk.company_id.id,
                'branch_id': rbk.branch_id.id,
                'name': rbk.name,
                'obj': 'dym.reimbursed.bank',
                'res_id': rbk.id,
                'date_due': rbk.date_approve,
                'description': description,
                'notes': description,
                'amount': rbk.amount_total,
                'partner_id': rbk.company_id.partner_id.id,
                'state': 'confirmed',
            }
            req_id = BankTransferRequest.create(values)
            rbk.transfer_request_id = req_id
            rbk.write({'state':'req2ho'})
            return req_id
        return False

    @api.multi
    def send_to_bank_transfer_request(self):
        if self.doc_type == 'supplier_invoice':
            req_id = self.create_bank_transfer_request_from_supplier_invoice()
        if self.doc_type == 'payment_request':
            req_id = self.create_bank_transfer_request_from_payment_request()
        if self.doc_type == 'customer_deposit':
            req_id = self.create_bank_transfer_request_from_customer_deposit()
        if self.doc_type == 'pettycash_reimburse':
            req_id = self.create_bank_transfer_request_from_pettycash_reimburse()
        if self.doc_type == 'bank_inout_reimburse':
            req_id = self.create_bank_transfer_request_from_bank_inout_reimburse()
        if req_id:
            view_id = self.env.ref('dym_bank_trf_request.bank_trf_request_form_view').id
            return {
                'name' : _('Bank Transfer Request'),
                'view_type': 'form',
                'view_id' : view_id,
                'view_mode': 'form',
                'res_id': req_id.id,
                'res_model': 'bank.trf.request',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'nodestroy': False,
                'context': self.env.context
            }



