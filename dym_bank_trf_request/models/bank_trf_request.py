from openerp import models, fields, api, _, SUPERUSER_ID
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError, RedirectWarning

import logging
_logger = logging.getLogger(__name__)

STATE_SELECTION = [
    ('draft', 'Draft'),
    ('confirmed', 'Waiting BTA'),
    ('approved','HO Approved'),
    ('rejected','HO Rejected'),
    ('bta_process','BTA Process'),
    ('cancel','Cancelled'),
    ('done','Done'),
]

class BankTransferRequest(models.Model):
    _name = 'bank.trf.request'
    _order = 'date_due'

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user = self.pool.get('res.users').browse(cr,uid,uid)
        branch_ids = self.pool.get('dym.branch').search(cr,uid,[('company_id','=',user.company_id.id)],context=context)
        user_branch_ids = user.branch_ids 
        for branch in user_branch_ids:
            if branch.id in branch_ids and branch.branch_type!='HO':
                return branch.id
        return False

    @api.multi
    def _get_notes(self):
        notes = []
        for rec in self:
            if rec.obj=='account.voucher':
                for obj in self.env[rec.obj].browse(rec.res_id):
                    for obj_line in obj.line_dr_ids:
                        notes.append(obj_line.name)
            rec.notes = '; '.join(notes)
    
    @api.one
    @api.depends('obj', 'res_id')
    def _get_res_id_state(self):
        state = 'Gak tahu'
        if not self.obj or not self.res_id:
            state = 'Unknown'
        state = self.env[self.obj].browse([self.res_id]).state
        self.res_id_state = state

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")
    branch_id = fields.Many2one('dym.branch', string='Your Branch', required=True, domain="[('company_id','=',company_id)]", default=_get_default_branch)
    partner_id = fields.Many2one("res.partner", string="Partner")
    advice_id = fields.Many2one("bank.trf.advice", string="Transfer Advice")
    transfer_id = fields.Many2one("dym.bank.transfer", string="Bank Transfer")
    name = fields.Char()
    obj = fields.Char()
    res_id = fields.Integer()
    res_id_state = fields.Char(compute='_get_res_id_state', string='Doc Status', readonly=True)
    model_data_id = fields.Many2one('ir.model.data')
    date_request = fields.Date('Request Date',default=fields.Date.context_today)
    date_due = fields.Date('Due Date', readonly=True, index=True)
    description = fields.Text()
    notes = fields.Text(compute="_get_notes", string='Notes', store=True)
    amount = fields.Float(digits=dp.get_precision('Account'), string='Amount')
    state = fields.Selection(STATE_SELECTION, string='State', readonly=True, default='confirmed')
    reject_reason = fields.Char('Rejection Reason')

    @api.model
    def default_get(self, default_fields):
        """If we're creating a new account through a many2one, there are chances that we typed the account code
        instead of its name. In that case, switch both fields values.
        """
        default_branch_id = self._context.get('default_branch_id')
        default_date_due = self._context.get('default_date_due')
        if not default_branch_id:
            user = self.env.user
            company_id = self.env.user.company_id
            branch_ids = self.env['dym.branch'].search([('company_id','=',user.company_id.id)])
            for branch in user.branch_ids:
                if branch.id in branch_ids.ids and branch.branch_type!='HO':
                    default_branch_id = branch

        if not default_date_due:
            default_date_due = fields.Date.context_today(self)

        contextual_self = self.with_context(default_branch_id=default_branch_id, default_date_due=default_date_due)
        res = super(BankTransferRequest, contextual_self).default_get(default_fields)
        return res

    @api.model
    def create(self, vals):
        obj = vals.get('obj',False)
        res_id = vals.get('res_id',False)
        if obj == 'dym.reimbursed':
            reimb_id = self.env['dym.reimbursed'].browse(res_id)
            if reimb_id and reimb_id.state != 'req2ho':
                reimb_id.write({'state':'req2ho'})
        return super(BankTransferRequest, self).create(vals)

    @api.multi
    def action_remove(self):
        bank_transfer_obj = self.env['dym.bank.transfer']
        bank_transfer = bank_transfer_obj.search([('bank_trf_advice_id','=',self.advice_id.id),('state','!=','cancel')])
        if bank_transfer:
            for btr in bank_transfer:
                if btr.state != 'draft':
                    raise RedirectWarning(_('Maaf item tidak dapat di delete karena BTR sudah di proses, \n \
                        mohon hubungi PIC terkait untuk mengubah BTR kembali ke draft.'))
        for rec in self:
            if bank_transfer:
                bank_transfer.line_ids1.amount -= rec.amount
                bank_transfer.amount = bank_transfer.line_ids1.amount
            advice_id = rec.advice_id
            rec.advice_id = False
            rec.transfer_id = False
        return { 'type': 'ir.actions.client', 'tag': 'reload' }

    @api.multi
    def action_view_invoice(self):
        for rec in self:
            invoice_id = rec.res_id
        view_id = self.env.ref('account.invoice_supplier_form').id
        return {
            'name' : _('Supplier Invoice'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': invoice_id,
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': False,
            'context': self.env.context
        }

    @api.multi
    def action_view_reimburse(self):
        for rec in self:
            reimburse_id = rec.res_id
        view_id = self.env.ref('dym_pettycash.reimbursed_form_view').id
        return {
            'name' : _('Petty Cash Reimburse'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': reimburse_id,
            'res_model': 'dym.reimbursed',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': False,
            'context': self.env.context
        }

    @api.multi
    def action_view_voucher(self):
        for rec in self:
            voucher_id = rec.res_id
        view_id = self.env.ref('account_voucher.view_purchase_receipt_form').id
        return {
            'name' : _('Payment Request'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': voucher_id,
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': False,
            'context': self.env.context
        }

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.advice_id:
                raise UserError(_('You cannot delete bank transfer request that contains bank transfer advice item.'))
        return super(BankTransferRequest, self).unlink()

    @api.multi
    def action_ho_approve(self):
        for rec in self:
            if rec.obj == 'dym.reimbursed':
                reimb_id = self.env['dym.reimbursed'].browse(rec.res_id)
                if reimb_id and reimb_id.state != 'hoapproved':
                    reimb_id.write({
                        'state':'hoapproved',
                        'date_hoapprove':fields.Date.context_today(self)
                    })
            rec.state = 'approved'

    @api.multi
    def action_ho_reject(self):
        for rec in self:
            if rec.obj == 'dym.reimbursed':
                reimb_id = self.env['dym.reimbursed'].browse(rec.res_id)
                if reimb_id and reimb_id.state != 'horejected':
                    reimb_id.write({
                        'state':'horejected',
                        'date_horejected':fields.Date.context_today(self)
                    })
            rec.state = 'rejected'


    @api.multi
    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    @api.model
    def list_dates_due(self):
        dates_due = []
        for req in self.search([]):
            date_due = (req.date_due,req.date_due)
            if date_due not in dates_due:
                dates_due.append(date_due)
        return dates_due

    @api.model
    def list_branches(self):
        branches = []
        for req in self.search([]):
            branch = (req.branch_id.id,req.branch_id.name)
            if branch not in branches:
                branches.append(branch)
        return branches

    @api.model
    def _cron_transfer_request(self):
        print "_cron_transfer_request===="
        for voucher in self.env['account.voucher'].search([
                ('journal_id.type','in',['purchase','purchase_refund']),
                ('type','=','purchase'),
                ('transfer_request_id','=',False),
                # ('fully_paid','=',True),
                ('branch_id.branch_type','!=','HO'),
                ('state','=','posted'),
                ('clearing_bank','=',True),
                ]):
            if not self.search([('res_id','=',voucher.id),('obj','=','account.voucher')]):
                values = {
                    'company_id': voucher.company_id.id,
                    'branch_id': voucher.branch_id.id,
                    'name': voucher.number,
                    'obj': 'account.voucher',
                    'res_id': voucher.id,
                    'date_due': voucher.date_due,
                    'description': voucher.comment,
                    'amount': voucher.amount,
                    'partner_id': voucher.partner_id.id,
                    'state': 'confirmed',
                }
                req_id = self.create(values)
                voucher.transfer_request_id = req_id

        for invoice in self.env['account.invoice'].search([
                ('type','=','in_invoice'),
                ('transfer_request_id','=',False),
                ('state','=','paid')
                ]):
            if not self.search([('res_id','=',invoice.id),('obj','=','account.invoice')]):
                values = {
                    'company_id': invoice.company_id.id,
                    'branch_id': invoice.branch_id.id,
                    'name': invoice.number,
                    'obj': 'account.invoice',
                    'res_id': invoice.id,
                    'date_due': invoice.date_due,
                    'description': invoice.comment,
                    'amount': invoice.amount_total,
                    'partner_id': invoice.partner_id.id,
                    'state': 'confirmed',
                }
                req_id = self.create(values)
                invoice.transfer_request_id = req_id

        for rpc in self.env['dym.reimbursed'].search([
                ('state','=','paid'),
                ('transfer_request_id','=',False),
                ]):
            if not self.search([('res_id','=',rpc.id),('obj','=','dym.reimbursed')]):
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
                    'amount': rpc.amount_total,
                    'partner_id': rpc.company_id.partner_id.id,
                    'state': 'confirmed',
                }
                req_id = self.create(values)
                rpc.transfer_request_id = req_id





