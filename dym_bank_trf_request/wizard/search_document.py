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

class search_document(models.TransientModel):
    _name = 'dym.search.document'

    cari = fields.Char(string='Search')
    invoice_id = fields.Many2one('account.invoice', string='Invoice')
    request_id = fields.Many2one('bank.trf.request', string='Request')
    invoice_line = fields.One2many('account.invoice.line', related='invoice_id.invoice_line', string='Invoice Lines')
    amount_untaxed = fields.Float(related='invoice_id.amount_untaxed', string='Subtotal')
    amount_tax = fields.Float(related='invoice_id.amount_tax', string='Tax')
    amount_total = fields.Float(related='invoice_id.amount_total', string='Total')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id')
    residual = fields.Float(string='Balance', related='invoice_id.residual')

    voucher_id = fields.Many2one('account.voucher', string='Voucher')
    voucher_line = fields.One2many('account.voucher.line', related='voucher_id.line_dr_ids', string='Voucher Lines')

    amount = fields.Float('Total', related="voucher_id.amount")
    narration = fields.Text('Notes', related="voucher_id.narration")
    tax_amount = fields.Float('Tax Amount', related="voucher_id.tax_amount")
    tax_id = fields.Many2one('account.tax', string='Tax', related="voucher_id.tax_id")

    reimburse_id = fields.Many2one('dym.reimbursed', string='Reimbursement')
    reimburse_line = fields.One2many('dym.reimbursed.line', related='reimburse_id.line_ids', string='Reimburse Lines')
    reimburse_total = fields.Float(related='reimburse_id.amount_total', string='Total')

    doc_type = fields.Selection([
        ('invoice','Invoice'),
        ('voucher','Voucher'),
        ('reimburse','Reimburse'),
        ], string='Doc Type')

    state = fields.Selection([
        ('start','Start'),
        ('exist','Exist'),
        ('ready','Ready'),
        ], string='State', default='start')

    @api.model
    def default_get(self, default_fields):
        res = super(search_document, self).default_get(default_fields)
        res.update({
            'request_id': self.env.context.get('active_id',False),
        })
        return res

    @api.multi
    def action_search_doc(self):
        self.ensure_one()
        context_copy = self._context.copy()
        active_id = self._context.get('active_id', False)

        invoice_id = False
        voucher_id = False
        reimburse_id = False

        if not self.cari:
            raise UserError(
                _('Kunci pencarian wajib diisi dengan dokumen Invoice atau Voucher atau Reimbursement.')
            )

        if self.cari:
            invoice_id = self.env['account.invoice'].search([('number','=',self.cari)])
        if self.cari and not invoice_id:
            voucher_id = self.env['account.voucher'].search([('number','=',self.cari)])
        if self.cari and not all([invoice_id,voucher_id]):
            reimburse_id = self.env['dym.reimbursed'].search([('name','=',self.cari)])

        view_id = self.env['ir.ui.view'].search([                                     
            ("name", "=", "dym.search.document.form"), 
            ("model", "=", 'dym.search.document'),
        ])

        doc_type = False
        obj = False
        if invoice_id:
            doc_type = 'invoice'
            obj = 'account.invoice'
            res_id = invoice_id[0].id
        if voucher_id:
            doc_type = 'voucher'
            obj = 'account.voucher'
            res_id = voucher_id[0].id
        if reimburse_id:
            doc_type = 'reimburse'
            obj = 'dym.reimbursed'
            res_id = reimburse_id[0].id

        if not any([invoice_id,voucher_id,reimburse_id]):
            raise UserError(
                _('Data yang dicari tidak ditemukan')
            )

        is_exist = self.env['bank.trf.request.line'].search([('obj','=',obj),('res_id','=',res_id)])
        default_state = 'ready'
        if is_exist:
            default_state = 'exist'
        context_copy.update({
            'default_invoice_id':invoice_id and invoice_id.id or None,
            'default_voucher_id':voucher_id and voucher_id.id or None,
            'default_reimburse_id':reimburse_id and reimburse_id.id or None,
            'default_doc_type':doc_type,
            'default_request_id':self.request_id.id,
            'default_state':default_state,
        })

        return {
            'name': _('Document Search'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dym.search.document',
            'view_id': view_id.id,
            'domain': "[]",
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': context_copy,
        }
        return res

    @api.multi
    def import_line(self):
        res = {
            'request_id': self.env.context.get('active_id'),
        }
        for x in self:
            if x.doc_type == 'invoice':
                name = x.invoice_id.number
                description = ', '.join([y.name for y in x.invoice_line])
                amount_total = x.amount_total
                obj = 'account.invoice'
                res_id = x.invoice_id.id
            if x.doc_type == 'voucher':
                name = x.voucher_id.number
                description = ', '.join([y.name for y in x.voucher_line])
                amount_total = x.amount
                obj = 'account.voucher'
                res_id = x.voucher_id.id
            if x.doc_type == 'reimburse':
                name = x.reimburse_id.name
                description = ', '.join([y.name for y in x.reimburse_line])
                amount_total = x.reimburse_total
                obj = 'dym.reimbursed'
                res_id = x.reimburse_id.id
        res.update({
            'obj': obj,
            'res_id': res_id,
            'name': name,
            'description': description,
            'amount_total': amount_total,
        })
        self.env['bank.trf.request.line'].create(res)


    @api.multi
    def import_line_detail(self):
        res = {
            'request_id': self.env.context.get('active_id'),
        }
        for x in self:
            if x.doc_type == 'invoice':
                name = x.invoice_id.number
                description = ', '.join([y.name for y in x.invoice_line])
                amount_total = x.amount_total
                obj = 'account.invoice'
                res_id = x.invoice_id.id
            if x.doc_type == 'voucher':
                name = x.voucher_id.number
                description = ', '.join([y.name for y in x.voucher_line])
                amount_total = x.amount
                obj = 'account.voucher'
                res_id = x.voucher_id.id
            if x.doc_type == 'reimburse':
                name = x.reimburse_id.name
                description = ', '.join([y.name for y in x.reimburse_line])
                amount_total = x.reimburse_total
                obj = 'dym.reimbursed'
                res_id = x.reimburse_id.id
        res.update({
            'obj': obj,
            'res_id': res_id,
            'name': name,
            'description': description,
            'amount_total': amount_total,
        })
        self.env['bank.trf.request.line.detail'].create(res)
    
    @api.multi
    def import_them(self):
        self.import_line()
        self.import_line_detail()
