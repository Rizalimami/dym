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

class dym_bank_transfer_from_voucher(models.TransientModel):
    _name = 'dym.bank.transfer.from.voucher'

    date_start = fields.Date("Date Start")
    date_end = fields.Date("Date End")
    transfer_id = fields.Many2one('dym.bank.transfer', 'Transfer')
    line_ids = fields.One2many('dym.bank.transfer.from.voucher.items', 'transfer_id', 'Packs')

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(dym_bank_transfer_from_voucher, self).default_get(cr, uid, fields, context=context)
        transfer_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not transfer_ids or len(transfer_ids) != 1:
            return res
        res.update({'transfer_id':transfer_ids[0]})
        assert active_model in ('dym.bank.transfer'), 'Bad context propagation'
        voucher_ids = self.pool.get('account.voucher').search(cr, uid, [('disbursed','=',False),('state','=','posted')], context=context)
        vouchers = self.pool.get('account.voucher').browse(cr, uid, voucher_ids, context=context)
        items = []
        dates = []
        for voucher in vouchers:
            if voucher.date not in dates:
                dates.append(voucher.date)

        res.update({
            'date_start':min(dates),
            'date_end':max(dates),
        })
        return res

    @api.onchange('date_start','date_end')
    def change_date_start(self):
        now = time.strftime('%Y-%m-%d')
        if self.date_end > now:
            self.date_end = now
        if self.date_start > now or self.date_end > now:
            raise Warning(_('Start date can not be future date'))
        if self.date_start > self.date_end:
            raise Warning(_('Start date can not be later than date end'))
 
        vouchers = self.env['account.voucher'].search([('disbursed','=',False),('state','=','posted')])
        items = []
        self.line_ids = []
        for voucher in vouchers:
            if voucher.date >= self.date_start:
                if voucher.date<=self.date_end:
                    item = {
                        'bank_account': voucher.bank_account.id,
                        'number':voucher.number,
                        'journal_id':voucher.journal_id.id,
                        'date':voucher.date,
                        'due_date_payment':voucher.due_date_payment,
                        'amount':voucher.amount,
                        'net_amount':voucher.net_amount,
                        'withholdings_amount':voucher.withholdings_amount,
                        'state':voucher.state,
                    }
                    items.append((0,0,item))

        self.line_ids = items

    @api.multi
    def wizard_view(self):
        view = self.env.ref('stock.view_stock_enter_transfer_details')
        return {
            'name': _('Enter transfer details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.transfer.from.voucher',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.ids[0],
            'context': self.env.context,
        }

class dym_bank_transfer_from_voucher_items(models.TransientModel):
    _name = 'dym.bank.transfer.from.voucher.items'
    _order = 'date'

    transfer_id = fields.Many2one('dym.bank.transfer.from.voucher', 'Transfer')
    bank_account = fields.Many2one('res.partner.bank', string='Supplier Bank A/C')
    number = fields.Char()
    journal_id = fields.Many2one('account.journal', 'Journal')
    date = fields.Datetime('Date')
    due_date_payment = fields.Datetime('Due Date')
    amount = fields.Float(string='Total Amount', digits=dp.get_precision('Account'), help='Total Amount Paid',)
    net_amount = fields.Float(string='Amount', digits=dp.get_precision('Account'), help='Total Amount Paid',)
    withholdings_amount = fields.Float(string='PPh', digits=dp.get_precision('Account'))
    state = fields.Char()
