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

import json
from openerp import api, models, fields
from openerp.tools.translate import _
from openerp.exceptions import Warning as UserError, RedirectWarning

class AutoClearing(models.TransientModel):
    _name = 'auto.clearing'

    @api.model
    def _get_default_branch(self,):
        user = self.env.user
        branch_ids = self.env['dym.branch'].search([('company_id','=',user.company_id.id)])
        for branch in user.branch_ids:
            if branch.id in branch_ids.ids:
                return branch.id
        return False

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, domain="[('company_id','=',company_id)]", default=_get_default_branch)

    @api.multi
    def action_process(self):        
        bank_journal_ids = self.env['account.journal'].search([('type','=','bank'),('clearing_account_id','!=',False)])
        clearing_account_ids = bank_journal_ids.mapped('clearing_account_id').ids
        move_line_ids = self.env['account.move.line'].search([
            ('branch_id','=',self.branch_id.id),
            ('account_id','in',clearing_account_ids),
            ('clear_state','=','open'),
            ('credit','>',0),
        ])

        new_clearing_bank_ids = []
        partner_types = self.env['dym.partner.type'].search_read([])
        partner_types = dict([(t['name'],t['id']) for t in partner_types])
        for move_line in move_line_ids:
            move_line_partner_type = move_line.partner_id and move_line.partner_id.partner_type or 'Pihak_ke_3'
            partner_type_id = partner_types[move_line_partner_type]
            values = {
                'name': 'new',
                'state': 'draft',
                'date': move_line.date,
                'value_date': move_line.date,
                'branch_id': move_line.branch_id.id,
                'division': move_line.division,
                'partner_type': partner_type_id,
                'partner_id': move_line.partner_id and move_line.partner_id.id or 1,
                'journal_id': move_line.journal_id.id,
                'clearing_account_id': move_line.account_id.id,
                'ref': move_line.ref,
                'move_line_ids': [(6,0,[move_line.id])],
                'total_giro': move_line.credit,
                'move_id': move_line.move_id.id,
                'memo': move_line.ref,
                'analytic_1': move_line.analytic_1.id,
                'analytic_2': move_line.analytic_2.id,
                'analytic_3': move_line.analytic_3.id,
                'analytic_4': move_line.analytic_4.id,
            }
            new_clearing_bank_id = self.env['dym.clearing.giro'].create(values)
            new_clearing_bank_ids.append(new_clearing_bank_id.id)

        search_view_id = self.env.ref('dym_clearing_giro.view_clearing_giro_search').id
        return {
            'domain': "[('id','in',%s)]" % str(new_clearing_bank_ids),
            'name': _('Clearing Banks'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'dym.clearing.giro',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': False,
            'search_view_id': search_view_id,
            'context': self.env.context
        }
