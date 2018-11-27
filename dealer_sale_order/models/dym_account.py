import time
from datetime import datetime
from openerp import models, fields, api, _
from openerp import workflow
import openerp.addons.decimal_precision as dp

class account_voucher(models.Model):
    _inherit = "account.voucher"

    dso_id = fields.Many2one('dealer.sale.order', string='Dealer Sales Memo')

class account_move_line(models.Model):
    _inherit = "account.move.line"

    @api.cr_uid_ids_context
    def reconcile_partial(self, cr, uid, ids, type='auto', context=None, writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        r_id = super(account_move_line,self).reconcile_partial(cr, uid, ids, type=type, context=context, writeoff_acc_id=writeoff_acc_id, writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id)
        self.pool.get('stock.picking').check_access_rights(cr, uid, 'create', raise_exception=True)
        move_line = self.browse(cr, uid, ids, context)
        for line in move_line:
            if line.invoice and line.invoice.customer_payment == False:
                inv = line.invoice
                dso_id = self.pool.get('dealer.sale.order').search(cr, uid, [('name','in',inv.origin.split(' ') or '')], limit=1)
                dso = self.pool.get('dealer.sale.order').browse(cr, uid, dso_id)
                if dso:
                    if dso.finco_id and dso.is_credit == True and dso.customer_dp <= 0:
                        inv.write({'customer_payment':True})
                    amount_dp = inv.amount_total
                    if inv.amount_dp > 0:
                        amount_dp = inv.amount_dp
                    if line.partner_id.id in [inv.partner_id.id or inv.qq_id.id] and line.debit == inv.amount_total and (line.reconcile_id or line.reconcile_partial_id) and line.amount_residual <= inv.amount_total - amount_dp:
                        workflow.trg_validate(uid, 'dealer.sale.order', dso.id, 'customer_payment', cr)
                        inv.write({'customer_payment':True})
                    elif line.account_id.id == inv.account_dp.id and line.reconcile_id and line.debit == amount_dp:
                        workflow.trg_validate(uid, 'dealer.sale.order', dso.id, 'customer_payment', cr)
                        inv.write({'customer_payment':True})
            if line.reconcile_id and line.dym_loan_id and not line.move_id.line_id.filtered(lambda r: not r.reconcile_id) and line.dym_loan_id.state != 'done':
                line.dym_loan_id.write({'state': 'done'})
                line.dym_loan_id.message_post(body=_("Loan %s Closed")%(line.dym_loan_id.name))


    @api.cr_uid_ids_context
    def reconcile(self, cr, uid, ids, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False, context=None):
        r_id = super(account_move_line,self).reconcile(cr, uid, ids, type=type, writeoff_acc_id=writeoff_acc_id, writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id, context=context)
        self.pool.get('stock.picking').check_access_rights(cr, uid, 'create', raise_exception=True)
        move_line = self.browse(cr, uid, ids, context)
        for line in move_line:
            if line.invoice and line.invoice.customer_payment == False:
                inv = line.invoice
                dso_id = self.pool.get('dealer.sale.order').search(cr, uid, [('name','in',inv.origin.split(' ') or '')], limit=1)
                dso = self.pool.get('dealer.sale.order').browse(cr, uid, dso_id)
                if dso:
                    if dso.finco_id and dso.is_credit == True and dso.customer_dp <= 0:
                        inv.write({'customer_payment':True})
                    amount_dp = inv.amount_total
                    if inv.amount_dp > 0:
                        amount_dp = inv.amount_dp
                    if line.partner_id.id in [inv.partner_id.id or inv.qq_id.id] and line.debit == inv.amount_total and (line.reconcile_id or line.reconcile_partial_id) and line.amount_residual <= inv.amount_total - amount_dp:
                        workflow.trg_validate(uid, 'dealer.sale.order', dso.id, 'customer_payment', cr)
                        inv.write({'customer_payment':True})
                    elif line.account_id.id == inv.account_dp.id and line.reconcile_id and line.debit == amount_dp:
                        workflow.trg_validate(uid, 'dealer.sale.order', dso.id, 'customer_payment', cr)
                        inv.write({'customer_payment':True})
            if line.reconcile_id and line.dym_loan_id and not line.move_id.line_id.filtered(lambda r: not r.reconcile_id) and line.dym_loan_id.state != 'done':
                line.dym_loan_id.write({'state': 'done'})
                line.dym_loan_id.message_post(body=_("Loan %s Closed")%(line.dym_loan_id.name))

class account_invoice(models.Model):
    _inherit = "account.invoice"
      
    dealer_sale_order_store_line_id = fields.Many2one('dealer.sale.order.line',string='Dealer Sales Memo Line')
    customer_payment = fields.Boolean(string='Customer Paid')
    tanda_jadi = fields.Float(string='Tanda Jadi',digits= dp.get_precision('Amount JP'), readonly=True)
    partner_cabang = fields.Many2one('dym.cabang.partner', related="dealer_sale_order_store_line_id.dealer_sale_order_line_id.partner_cabang", string='Customer Branch')

    @api.multi
    def confirm_paid(self):
        paid = super(account_invoice,self).confirm_paid()
        return paid