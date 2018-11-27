import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError, RedirectWarning

class DymCheckgyro(models.Model):
    _name = "dym.checkgyro"
    _description = "Cheque or Giro Book"

    @api.multi
    def _get_checkgyro_book_status(self):
        for rec in self:
            if rec.state == 'running':
                for line in rec.line_ids:
                    if line.state == 'available':
                        break
                rec.state = 'done'

    @api.model
    def _getCompanyBranch(self):
        user = self.env.user
        if user.branch_type!='HO':
            if not user.branch_id:
                raise osv.except_osv(('Perhatian !'), ("User %s tidak memiliki default branch. Hubungi system administrator agar menambahkan default branch di User Setting." % self.env.user.name))
            return [('id','=',user.branch_id.id)]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        branch_ids = [b.id for b in self.env.user.branch_ids if b.company_id.id==company_id]
        return [('id','in',branch_ids)]

    name = fields.Char(string="Book Name", default="new", required=True)
    date_received = fields.Date('Date Received', required=False, default=fields.Date.context_today)
    date_activated = fields.Date('Date Ativated', required=False)
    company_id = fields.Many2one('res.company', string='Company',
        related='journal_id.company_id', store=True, readonly=True)
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, domain=_getCompanyBranch)
    journal_id = fields.Many2one('account.journal', string="Bank Account", required=True, domain="[('branch_id','in',[branch_id,False]),('type','in',['bank'])]")
    line_ids = fields.One2many('dym.checkgyro.line', 'checkgyro_id', string="Lines")
    pages = fields.Selection([('25','25 Pages'),('50','50 Pages')], string="Pages", default='25')
    number_start = fields.Integer("Start")
    number_end = fields.Integer('End')
    prefix = fields.Char('Prefix')
    state = fields.Selection([('draft','Draft'),('running','Running'),('done','Done')], string="State", compute='_get_checkgyro_book_status', store=True, default='draft')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'CGR', division='Finance')
        return super(DymCheckgyro, self).create(vals)

    @api.multi
    def action_generate_lines(self):
        context = {}
        allowed = True
        for x in self.line_ids:
            if x.state == 'used':
                raise UserError(
                    _('Maaf, tidak boleh generate ulang, sebab sudah ada yang terpakai')
                )
        view_id = self.env['ir.ui.view'].search([                                     
            ("name", "=", "dym.checkgyro.generate.line.form"), 
            ("model", "=", 'dym.checkgyro.generate.line'),
        ]).id

        res = {
            'name': _('Generate Lines'),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'dym.checkgyro.generate.line',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': context
        }
        return res

    @api.multi
    def action_validate(self):
        for rec in self:
            if not rec.date_activated:
                raise UserError(
                    _('Please fill in cheque/giro activation date')
                )                

            if not rec.line_ids:
                raise UserError(
                    _('This check or giro book does not have any pages. Please generate first.')
                )                
        self.state = 'running'

    @api.multi
    def action_reset_draft(self):
        for rec in self:
            for line in rec.line_ids:
                if line.state!='available':
                    raise UserError(
                        _('Maaf, tidak boleh direset, sebab sudah ada yang terpakai')
                    )
            rec.state = 'draft'

    @api.one
    def unlink(self):
        for x in self.line_ids:
            if x.state == 'used':
                raise UserError(
                    _('Maaf, tidak boleh hapus, sebab sudah ada yang terpakai')
                )
        return super(DymCheckgyro, self).unlink()

class DymCheckgyro_line(models.Model):
    _name = "dym.checkgyro.line"
    _description = "Cheque or Giro Book Pages"

    @api.one
    @api.depends('voucher_ids','transfer_ids','is_opbal')
    def _get_checkgyro_status(self):        
        if self.voucher_ids:
            state = 'used'
            self.voucher_id = self.voucher_ids.ids[0]
            self.used_date = self.voucher_ids.filtered(lambda s:s.id==self.voucher_id.id).date
            self.vouchers = len(self.voucher_ids.ids)
        elif self.transfer_ids:
            state = 'used'
            self.transfer_id = self.transfer_ids.ids[0]
            self.used_date = self.transfer_ids.filtered(lambda s:s.id==self.transfer_id.id).date
            self.transfers = len(self.transfer_ids.ids)
        else:
            state = 'available'
        if self.is_opbal:
            state = 'used'
        self.state = state
        self.state_stored = state

    name = fields.Char(string="Check/Giro Number")
    used_date = fields.Date('Used Date')
    checkgyro_id = fields.Many2one('dym.checkgyro', string="Chek/Giro Book", ondelete='cascade')

    branch_id = fields.Many2one(related="checkgyro_id.branch_id", string="Branch")
    journal_id = fields.Many2one(related="checkgyro_id.journal_id")
    company_id = fields.Many2one('res.company', string='Company',
        related='journal_id.company_id', store=True, readonly=True)
    state = fields.Selection([('alocated','Alocated'),('available','Available'),('used','Used')], string="State", compute='_get_checkgyro_status', default="available")
    amount = fields.Float('Amount')
    voucher_id = fields.Many2one('account.voucher', string="Voucher")
    voucher_ids = fields.One2many('account.voucher', 'cheque_giro_number', string="Vouchers")
    vouchers = fields.Integer('# of Vouchers')
    transfer_id = fields.Many2one('dym.bank.transfer', string="Transfer")
    transfer_ids = fields.One2many('dym.bank.transfer', 'cheque_giro_number', string="Transfers")
    transfers = fields.Integer('# of Transfers')
    is_opbal = fields.Boolean('Is Opbal')
    state_stored = fields.Selection([('alocated','Alocated'),('available','Available'),('used','Used')], string="State Stored")

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            name = "%s %s (%s)" % (rec.name,rec.checkgyro_id.journal_id.name,rec.state)
            res.append((rec.id, name))
        return res
