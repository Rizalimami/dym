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
from openerp.osv import osv
from openerp.exceptions import Warning
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime

class dym_bank_transfer_confirm_received_wizard(models.TransientModel):
    _name = 'dym_bank_transfer.confirm.received.wizard'

    name = fields.Char()
    line_ids = fields.Many2many('dym.bank.transfer','post_trf_rel','post_id','trf_id', string='Bank Transfers')

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(dym_bank_transfer_confirm_received_wizard, self).default_get(cr, uid, fields, context=context)
        active_ids = context.get('active_ids', [])
        active_model = context.get('active_model')
        res.update({'line_ids':active_ids})
        return res

    @api.multi
    def post_transfer(self):
        for trf in self.line_ids:
            trf.post_bank()
