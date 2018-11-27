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

import time
from openerp import models, fields, api
from openerp.exceptions import Warning
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime


class dym_bank_transfer_request_wizard(models.TransientModel):
    _name = 'dym.bank.transfer.request.wizard'

    @api.model
    def _getCompanyBranch(self):
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        branch_ids = [b.id for b in self.env.user.branch_ids if b.company_id.id==company_id]
        return [('id','in',branch_ids)]

    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, default=_getCompanyBranch)
    acc_number = fields.Many2one('res.partner.bank', domain="[('branch_ids','in',branch_id)]", string="Bank Account")
    state = fields.Selection([('new','New'),('done','Done')], string='State')
    line_in_ids = fields.Char()
    line_out_ids = fields.Char()
    amount = fields.Float(string='Amount', help='Different amount amongs Bank in and out')
    amount_request = fields.Float(string='Amount Request', help='Requested amount to transfer')

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(dym_bank_transfer_request_wizard, self).default_get(cr, uid, fields, context=context)
        transfer_id = context.get('active_id', [])
        transfer_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not transfer_ids or len(transfer_ids) != 1:
            return res
        return res

    @api.onchange('branch_id','acc_number')
    def onchange_branch_id(self):
        domain = {}
        value = {}
        if not self.branch_id:
            return False
        if self.branch_id and not self.branch_id.company_id:
            return {
                'warning': {
                        'title': _('Error!'), 
                        'message': _("Branch %s is not related to any company yet. Please relate it first to continue or contact system administrator to do it." % self.branch_id.name)
                    }, 
                'value': {
                    'branch_id': []
                }
            }
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        if self.acc_number:
            if not self.acc_number.journal_id:
                return {
                    'warning': {
                            'title': _('Error!'), 
                            'message': _("Rekening Bank %s tidak memiliki jurnal. Mohon diset terlebih dahulu" % self.acc_number.name)
                        }, 
                    'value': {
                        'acc_number': False
                    }
                }

        if self.branch_id and self.acc_number:
            bank_in_ids = self.env['account.voucher'].search([
                ('branch_id','=',self.branch_id.id),
                ('journal_id','=',self.acc_number.journal_id.id),
                ('transaction_type','=','in'),
                ('bank_trf_id','=',False),
                ])
            bank_out_ids = self.env['account.voucher'].search([
                ('branch_id','=',self.branch_id.id),
                ('journal_id','=',self.acc_number.journal_id.id),
                ('transaction_type','=','out'),
                ('bank_trf_id','=',False),
                ])

            self.line_in_ids = bank_in_ids.ids
            self.line_out_ids = bank_out_ids.ids
            total_bank_in = sum([x.debit for x in bank_in_ids.mapped('move_ids').filtered(lambda r:r.debit>0)])
            total_bank_out = sum([x.credit for x in bank_out_ids.mapped('move_ids').filtered(lambda r:r.credit>0)])
            amount = total_bank_out - total_bank_in
            self.amount_request = amount > 0 and amount or 0
            self.amount = amount

    @api.multi
    def submit_bank_transfer(self):
        for rec in self:
            res = {
                'request_id': rec.id,
            }
            description = []
            values = {
                'obj': 'account.voucher',
                'res_id': False,
                'name': '',
                'description': '',
                'amount_total': rec.amount_request,
            }
            res.update()
            self.env['bank.trf.request.line'].create(res)

