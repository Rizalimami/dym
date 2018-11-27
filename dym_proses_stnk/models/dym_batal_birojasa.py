from openerp import models, fields, api, _, workflow, SUPERUSER_ID
from openerp.osv import osv
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.exceptions import Warning as UserError, RedirectWarning

class dym_batal_birojasa(models.Model):
    _name = "dym.batal.birojasa"
    _description = "Batal Tagihan Biro Jasa"

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval', 'Waiting For Approval'),
        ('confirmed', 'Waiting Approval'),
        ('approved', 'Confirmed'),
        ('except_invoice', 'Invoice Exception'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ]

    APPROVAL_STATE = [
        ('b', 'Belum Request'),
        ('rf', 'Request For Approval'),
        ('a', 'Approved'),
        ('r', 'Reject')
    ]

    name = fields.Char('Pembatalan TBJ', compute='_get_transaction_name')
    birojasa_id = fields.Many2one('dym.proses.birojasa', "Nomor Biro Jasa", required=True, readonly=True)
    request_date = fields.Date("Request Date", default=datetime.today())
    branch_id = fields.Many2one('dym.branch', string='Branch')
    division = fields.Selection(related='birojasa_id.division')
    partner_id = fields.Many2one('res.partner', 'Biro Jasa', related='birojasa_id.partner_id')
    type = fields.Selection(related='birojasa_id.type')
    no_dok = fields.Char("Supplier Invoice Number", related='birojasa_id.no_dok')
    tgl_dok = fields.Date("Supplier Invoice Date", related='birojasa_id.tgl_dok')
    tgl_tbj = fields.Date("Tanggal TBJ", related='birojasa_id.tanggal')
    reason = fields.Text('Alasan Cancel', required=True)
    amount_total = fields.Float("Total Tagihan", related='birojasa_id.amount_total')
    total_progressive = fields.Float("Total Progresif", related='birojasa_id.total_progressive')
    state = fields.Selection(STATE_SELECTION, 'State', readonly=True)
    proses_birojasa_line = fields.One2many('dym.proses.birojasa.line', related='birojasa_id.proses_birojasa_line')
    approval_line = fields.One2many('dym.approval.line', 'transaction_id', string="Table Approval",
                                   domain=[('form_id', '=', _name)])
    approval_state = fields.Selection(APPROVAL_STATE, 'Approval State', readonly=True)

    @api.multi
    @api.constrains('birojasa_id')
    def cons_birojasa(self):
        if self.birojasa_id:
            if len(self.search([('birojasa_id', '=', self.birojasa_id.id)])) > 1:
                raise RedirectWarning("Maaf request batal birojasa sudah pernah dilakukan!")

    @api.depends('birojasa_id')
    def _get_transaction_name(self):
        self.name = "B-"+self.birojasa_id.name

    @api.multi
    def wkf_rfa(self):
        obj_matrix_approval = self.env['dym.approval.matrixbiaya']
        obj_matrix_approval.request(self, 'amount_total')
        self.write({'state': 'waiting_for_approval'})

    @api.multi
    def wkf_approve_cancel(self):
        approval_sts = self.env['dym.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'approval_state':'a', 'state':'approved'})
            self.birojasa_id.write({'state':'approved_cancel'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
        return True

    @api.multi
    def wkf_action_cancel_tagihan(self):
        proses_batal = self.birojasa_id.wkf_action_proses_cancel_tagihan()
        if proses_batal:
            self.write({'state':'done'})
            self.birojasa_id.write({'state':'cancel'})

class dym_birojasa_batal(models.Model):
    _inherit = "dym.proses.birojasa"

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('confirmed', 'Waiting Approval'),
        ('approved','Process Confirmed'),
        ('except_invoice', 'Invoice Exception'),
        ('done','Done'),
        ('waiting_approval_cancel', 'Waiting For Approval Cancel'),
        ('approved_cancel', 'Cancel Confirmed'),
        ('cancel','Cancelled')
    ]

    state = fields.Selection(STATE_SELECTION, 'State', readonly=True)
    batal_jasa_line = fields.One2many('dym.batal.birojasa','birojasa_id', string='Pembatalan Birojasa')
    approval_batal_line = fields.One2many('dym.approval.line','transaction_id', string="Table Approval Batal",domain=[('form_id','=',_inherit)])

    @api.multi
    def wkf_request_batal_birojasa(self):
        paymentstatus = self.get_paymentstatus(self.name)
        if paymentstatus == 'Paid':
            raise osv.except_osv(('Perhatian !'), ("Maaf status invoice sudah paid."))

        obj_acc_invoice = self.env['account.invoice']
        obj_acc_move = self.env['account.move']
        obj_acc_voucher_line = self.env['account.voucher.line']
        src_invoice_nde = obj_acc_invoice.search([('origin','=',self.name),('type','=','out_invoice')])
        src_invoice_sin = obj_acc_invoice.search([('origin','=',self.name),('type','=','in_invoice')])
        str_cpa = ""
        for inv in src_invoice_nde:
            move = obj_acc_move.search([('model','=',obj_acc_invoice._name),('transaction_id','=',inv.id)])
            if len(move.line_id) > 1:
                for mv in move.line_id:
                    voucher_line = obj_acc_voucher_line.search([('move_line_id','=',mv.id)])
                    if voucher_line:
                        break
            else:
                voucher_line = obj_acc_voucher_line.search([('move_line_id','=',move.line_id.id)])

            if voucher_line.voucher_id.number and voucher_line.voucher_id.state != 'cancel':
                str_cpa += "\n"+inv.number
                str_cpa += ", "+voucher_line.voucher_id.number
                str_cpa += ", "+inv.partner_id.name
        if str_cpa:
            raise osv.except_osv(('Perhatian !'), ("Maaf... sudah ada Customer Payment atas Invoice Pajak Progresif, sebagai berikut : \
            " + str_cpa + ". \n Mohon cancel CPA terlebih dahulu."))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wiz.dym.batal.birojasa',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'branch_id':self.branch_id.id, 
                'partner_id':self.partner_id.id, 
                'birojasa_id':self.id,
                'division':self.division
            }
        }

    @api.multi
    def wkf_action_proses_cancel_tagihan(self):
        stock_lot = self.env['stock.production.lot']
        for x in self.proses_birojasa_line :
            lot_search = stock_lot.search([('id','=',x.name.id)])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_search :
                lot_search.write({
                                  'proses_biro_jasa_id': False,
                                  'tgl_proses_birojasa':False,
                                  'no_notice_copy':False,
                                  'tgl_notice_copy':False,
                                  'total_jasa':False,
                                  'total_notice':False,
                                })

        self.reverse_journal()

        self.write({'state':'cancel'})

        return True

    @api.multi
    def reverse_journal(self):
        paymentstatus = self.get_paymentstatus(self.name)
        if paymentstatus == 'Paid':
            raise osv.except_osv(('Perhatian !'), ("Maaf status invoice sudah paid."))
            
        obj_acc_invoice = self.env['account.invoice']
        obj_acc_move = self.env['account.move']
        acc_invoice = obj_acc_invoice.search([('origin','=',self.name)])

        reversed_move_ids = []
        for invoice in acc_invoice:
            # First, set the invoices as cancelled
            invoice.write({'state': 'cancel'})

            acc_move = obj_acc_move.search([('model','=',obj_acc_invoice._name),('transaction_id', '=', invoice.id)])

            for move in acc_move:
                if move.state != 'posted':
                    raise RedirectWarning(_('Reverse entries only available on posted journal'))
                if move.reverse_from_id or move.search([('reverse_from_id','=',move.id)]):
                    raise RedirectWarning(_('Journal ' + (move.name or move.ref or '/') + ' sudah di reverse'))            
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

                for line in move.line_id :
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

            # First, set the invoices as cancelled and detach the move ids
            # invoice.action_cancel()
        return True

    @api.multi
    def view_batal_birojasa(self):
        batal_tbj = self.env['dym.batal.birojasa'].search([('birojasa_id','=',self.id)])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dym.batal.birojasa',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'res_id': batal_tbj.id
        }
