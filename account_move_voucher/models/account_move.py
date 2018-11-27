# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
import logging
_logger = logging.getLogger(__name__)


class account_move(models.Model):
    _inherit = 'account.move'

    # residual_type = fields.Selection([
    #     ('receivable', 'Receivable'),
    #     ('payable', 'Payable'),
    #     ],
    #     string='Residual Type')
    receivable_residual = fields.Float(
        string=_('Receivable Balance'),
        digits=dp.get_precision('Account'),
        compute='_compute_residual',
        # store=True,
        help="Remaining receivable amount due."
        )
    payable_residual = fields.Float(
        string=_('Payable Balance'),
        digits=dp.get_precision('Account'),
        compute='_compute_residual',
        # store=True,
        help="Remaining payable amount due."
        )

    @api.one
    @api.depends(
        'state',
        'line_id.account_id.type',
        'line_id.amount_residual',
        # Fixes the fact that move_id.line_id.amount_residual, being not stored and old API, doesn't trigger recomputation
        'line_id.reconcile_id',
        # 'line_id.amount_residual_currency',
        # 'line_id.currency_id',
        'line_id.reconcile_partial_id.line_partial_ids',
        # 'line_id.reconcile_partial_id.line_partial_ids.invoice.type',
    )
    def _compute_residual(self):
        # TODO tal vez falta agregar lo de multi currency de donde lo sacamos
        # de invoice
        payable_residual = 0.0
        receivable_residual = 0.0
        # Each partial reconciliation is considered only once for each invoice
        # it appears into,
        # and its residual amount is divided by this number of invoices
        partial_reconciliations_done = []
        for line in self.sudo().line_id:
            if line.account_id.type not in ('receivable', 'payable'):
                continue
            if line.reconcile_partial_id and line.reconcile_partial_id.id in partial_reconciliations_done:
                continue
            # Get the correct line residual amount
            line_amount = line.amount_residual_currency if line.currency_id else line.amount_residual
            # For partially reconciled lines, split the residual amount
            if line.reconcile_partial_id:
                r = line.reconcile_partial_id
                line_amount = reduce(
                    lambda y, t: (t.credit or 0.0) - (
                        t.debit or 0.0) + y, r.line_partial_ids, 0.0)
            if line.account_id.type == 'receivable':
                receivable_residual += line_amount
            else:
                payable_residual += line_amount
        self.payable_residual = max(payable_residual, 0.0)
        self.receivable_residual = max(receivable_residual, 0.0)

    @api.multi
    def action_create_receipt_voucher(self):
        return self.create_voucher('receipt')

    @api.multi
    def action_create_payment_voucher(self):
        return self.create_voucher('payment')

    @api.multi
    def action_reverse_journal(self):
        reversed_move_ids = []
        for move in self:
            if move.state != 'posted':
                raise Warning(_('Reverse entries only available on posted journal'))
            if move.reverse_from_id or move.search([('reverse_from_id','=',move.id)]):
                raise Warning(_('Journal ' + (move.name or move.ref or '/') + ' sudah di reverse'))            
            period_ids = self.env['account.period'].with_context(company_id=move.company_id.id).find()
            reverse_move = {
                'name': (move.name or '/') + ' (Reversed)',
                'ref':(move.ref or '/') + ' (Reversed)',
                'journal_id': move.journal_id.id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'period_id':period_ids.id,
                'reverse_from_id':move.id,
                'transaction_id':move.id,
                'model':move.__class__.__name__,
            }
            reversed_move = move.create(reverse_move)
            reversed_move_ids.append(reversed_move.id)
            reconcile = True
            reconcile_ids = []
            for line in move.line_id :
                # if line.reconcile_partial_id:
                #     reconcile = False
                reverse_move_line = {
                    'name': (line.name or '/') + ' (Reversed)',
                    'ref': (line.ref or '/') + ' (Reversed)',
                    'account_id': line.account_id.id,
                    'move_id': reversed_move.id,
                    'journal_id': line.journal_id.id,
                    'period_id':period_ids.id,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'debit': line.credit,
                    'credit': line.debit,
                    'branch_id' : line.branch_id.id,
                    'division' : line.division,
                    'partner_id' : line.partner_id.id,
                    'analytic_account_id' : line.analytic_account_id.id,     
                } 
                reversed_move_line = line.create(reverse_move_line)
                if line.account_id.reconcile and line.account_id.type in ['receivable','payable'] and not line.reconcile_id:
                    reconcile_ids += [reversed_move_line.id, line.id]
            if reversed_move.journal_id.entry_posted :                                     
                move_posted = reversed_move.post()
            if reconcile == True and reconcile_ids:
                reconcile_id = self.pool.get('account.move.line').reconcile_partial(self._cr,self._uid, reconcile_ids, 'auto')
            elif reconcile == False:
                raise Warning(_('Journal ' + (move.name or move.ref or '/') + ' sudah di proses'))
        mod_obj = self.env['ir.model.data']
        result = mod_obj._get_id('account', 'view_account_move_filter')
        id = mod_obj.browse(result).read(['res_id'])[0]
        return {
            'domain': "[('id','in', [" + ','.join(map(str, reversed_move_ids)) + "])]",
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': id['res_id']
        }

    @api.multi
    def create_voucher(self, voucher_type):
        # todo ver como podemos incorporar cobros, si es que tiene sentido
        self.ensure_one()
        if voucher_type == 'payment':
            name = _('Payment')
            residual_amount = self.payable_residual
        else:
            name = _('Receipt')
            residual_amount = self.receivable_residual

        view_id = self.env['ir.model.data'].xmlid_to_res_id(
            'account_voucher.view_vendor_receipt_dialog_form')
        voucher_context = self._context.copy()
        voucher_context.update({
                'payment_expected_currency': self.company_id.currency_id.id,
                'default_partner_id': self.partner_id.id,
                'default_amount': residual_amount,
                # for compatibilit with other modules
                'default_net_amount': residual_amount,
                'default_reference': self.name,
                'close_after_process': True,
                # 'invoice_type': self.type,
                # 'invoice_id': self.id,
                'default_type': voucher_type,
                'default_company_id': self.company_id.id,
                'type': 'voucher_type',
                })
        res = {
            'name': name,
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': voucher_context
            }
        return res
