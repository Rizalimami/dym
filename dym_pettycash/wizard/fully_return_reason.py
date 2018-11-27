# -*- coding: utf-8 -*-
##############################################################################
#
#    This module copyright (C) 2015 Therp BV (<http://therp.nl>).
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

import base64
from datetime import datetime
from openerp import models, fields, api, _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

class FullyReturnReason(models.TransientModel):
    _name = 'dym.pettycash.full.return.reason'

    pco_id = fields.Many2one('dym.pettycash')
    pci_id = fields.Many2one('dym.pettycash.in')
    reasons = fields.Many2one('dym.pettycash.in.full.refund.reason', string="Reasons")
    reason = fields.Text()

    @api.model
    def default_get(self, fields):
        res = super(FullyReturnReason, self).default_get(fields)
        active_model = self.env.context.get('active_model',False)
        active_ids = self.env.context.get('active_ids',[])
        if not active_model or not active_ids:
            return res
        pci = self.env['dym.pettycash.in'].browse(active_ids)[0]
        res['pci_id'] = pci.id
        res['pco_id'] = pci.pettycash_id.id
        default_reason_id = self.env['dym.pettycash.in.full.refund.reason'].search([], order='sequence', limit=1)
        if default_reason_id:
            res['reasons'] = default_reason_id.id
        return res

    @api.onchange('reasons')
    def change_reasons(self):
        self.reason = self.reasons.notes


    @api.multi
    def action_full_refund(self):
        self.ensure_one()
        self.pci_id.action_move_line_create()
        self.pci_id.action_update_amount_real()
