import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp import workflow
from openerp.osv import osv
from ..report import fungsi_terbilang

class dym_advance_payment(models.Model):
    _inherit = 'dym.advance.payment'

    advance_payment_line = fields.One2many('dym.advance.payment.line','advance_payment_id')

    @api.multi
    def create_payment_detail(self):
        avp_line_obj = self.env['dym.advance.payment.line']
        avp_line = {
            'advance_payment_id': self.id,
            'due_date':self.date,
            'amount':self.amount,
        }
        avp_line_id = avp_line_obj.create(avp_line)
        return avp_line_id

    @api.multi
    def wkf_action_confirm(self):
        res = super(dym_advance_payment, self).wkf_action_confirm()
        self.create_payment_detail()
        return res

class dym_advance_payment_line(models.Model):
    _name = "dym.advance.payment.line"
    # _inherit = ['mail.thread']

    @api.one
    @api.depends('advance_payment_id.state')
    def _compute_state(self):
        self.state = self.voucher_id.state

    advance_payment_id = fields.Many2one('dym.advance.payment', 'Advance Payment')
    due_date = fields.Date('Due Date', required=True)
    amount = fields.Float(string='Jumlah', digits=dp.get_precision('Account'), readonly=True)
    voucher_id = fields.Many2one('account.voucher', 'RV/PV No.', readonly=True, copy=False)
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting Approval'),
        ('request_approval','RFA'),
        ('approved','Approved'),
        ('confirmed','Confirmed'),
        ('proforma','Pro-forma'),
        ('cancel','Cancelled'),
        ('posted','Posted'),
    ], 'State', compute='_compute_state')

    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.voucher_id and val.voucher_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Cannot cancel voucher which is in state \'%s\'!') % (val.voucher_id.state))
        if val.voucher_id:
                val.voucher_id.cancel_voucher()
        return super(dym_loan_line, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def create_voucher(self):
        voucher_obj = self.env['account.voucher']
        obj_branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.advance_payment_id.branch_id.id)])
        voucher = {
            'branch_id':self.advance_payment_id.branch_id.id, 
            'division': self.advance_payment_id.division, 
            'inter_branch_id':self.advance_payment_id.branch_id.id, 
            'partner_id': self.advance_payment_id.user_id.id, 
            'date': self.advance_payment_id.date, 
            'amount': self.amount,
            'type': 'payment',
            'journal_id': self.advance_payment_id.payment_method.id,
            'payment_method': 'internet_banking',
            # 'pay_now': 'pay_now', 
            'date_due_payment': self.advance_payment_id.date, 
            'reference': self.advance_payment_id.name, 
            'name': self.advance_payment_id.description, 
            'user_id': self.advance_payment_id.confirm_uid.id,
            'analytic_account_id': self.advance_payment_id.analytic_account_id.id,
            'analytic_2': self.advance_payment_id.analytic_2.id,
            'analytic_3': self.advance_payment_id.analytic_3.id,
            'analytic_4': self.advance_payment_id.analytic_account_id.id,
        }

        move_line_id = self.env['account.move.line'].search([
            ('move_id','=',self.advance_payment_id.account_move_id.id),
            ('account_id','=',obj_branch_config.advance_payment_hutang_lain.id)
        ], limit=1)

        if not move_line_id :
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi %s!")%(self.name))
        move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_id.id, self.amount, False, False)
        voucher_line = [0,0,{
            'move_line_id': move_line_vals['value']['move_line_id'], 
            'account_id': move_line_vals['value']['account_id'], 
            'date_original': move_line_vals['value']['date_original'], 
            'date_due': move_line_vals['value']['date_due'], 
            'amount_original': move_line_vals['value']['amount_original'], 
            'amount_unreconciled': move_line_vals['value']['amount_unreconciled'],
            'amount': self.amount, 
            'currency_id': move_line_vals['value']['currency_id'], 
            'type': 'dr', 
            'name': move_line_vals['value']['name'],
            'reconcile': True,
            'branch_dest_id': self.advance_payment_id.branch_id.id,
        }]
        
        voucher['line_dr_ids'] = [voucher_line]
        voucher['line_cr_ids'] = []
        voucher_id = voucher_obj.create(voucher)
        update_vcr = voucher_id.onchange_journal_account_voucher(
            self.advance_payment_id.branch_id.id, 
            self.advance_payment_id.payment_method.id, 
            voucher_id.line_cr_ids, 
            False, 
            self.advance_payment_id.user_id.id, 
            self.advance_payment_id.date, 
            self.advance_payment_id.amount, 
            voucher_id.type, 
            self.advance_payment_id.branch_id.company_id.id)
        update_vcr['value']['account_id'] = update_vcr['value']['account_id'].id
        voucher_id.write(update_vcr['value'])
        self.write({'voucher_id':voucher_id.id,'state':'draft'})
        # self.message_post(body=_("Advance Payment %s - Voucher Created <br/>Amount: %s")%(self.name, self.advance_payment_id.amount))

        return voucher_id

    @api.cr_uid_ids_context
    def view_voucher(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        val = self.browse(cr, uid, ids)

        result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'action_vendor_payment')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')

        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = val.voucher_id.id
        return result
    