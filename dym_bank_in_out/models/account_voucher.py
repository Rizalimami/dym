from openerp import models, fields, api, _, SUPERUSER_ID
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError, RedirectWarning

class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    @api.model
    def _get_analytic_company(self):
        level_1_ids = self.env['account.analytic.account'].search([('segmen','=',1),('company_id','=',self.env.user.company_id.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            return False
        return level_1_ids

    transaction_type = fields.Selection([('in','Bank In'),('out','Bank Out')], string='Transaction Type')
    bank_in_type = fields.Selection([('normal','Normal'),('reimburse','Reimburse')], string='Bank In Type', default='normal')
    bank_trf_id = fields.Many2one('bank.trf.request', string='Bank Transfer')
    reimburse_ids = fields.One2many('voucher.reimbursed.line', 'voucher_id', string='Reimburse')
    bank_reimburse_ids = fields.One2many('dym.reimbursed.bank.line', 'voucher_id', string='Bank Reimburse')

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        domain = {}
        if self.branch_id:
            self.journal_id = False
            self.account_id = False
            self.line_ids = []
            self.line_cr_ids = []
            self.line_dr_ids = []
            domain['journal_id'] = [('branch_id','=',self.branch_id.id),('type','in',['bank'])]
        return {'domain':domain}

    @api.model
    def create(self,vals):
        res = super(AccountVoucher,self).create(vals)
        transaction_type = self.env.context.get('transaction_type',False)
        if transaction_type == 'in':
            res.number = self.env['ir.sequence'].get_sequence('TBM', division=res.division, padding=6, branch=res.branch_id)
        if transaction_type == 'out':
            res.number = self.env['ir.sequence'].get_sequence('TBK', division=res.division, padding=6, branch=res.branch_id)
        self.update_voucher_line()
        return res

    @api.multi
    def action_reimburse_process(self):
        self.update_voucher_line()

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        domain = {}
        if self.journal_id:
            self.account_id = self.journal_id.default_credit_account_id.id
        return {'domain':domain}

    @api.model
    def update_voucher_line(self):
        VoucherLine = self.env['account.voucher.line']
        identifiers = []
        values = {}
        total = 0.0
        if self.reimburse_ids:
            for reimburse in self.reimburse_ids:
                for rpc_line in reimburse.reimbursed_id.line_ids:
                    for pco_line in rpc_line.pettycash_id.line_ids:
                        aa1 = pco_line.analytic_1 or self._get_analytic_company()
                        aa2 = pco_line.analytic_2
                        aa3 = pco_line.analytic_3
                        aa4 = pco_line.analytic_4
                    identifier = '%s%s%s%s%s' % (
                        rpc_line.account_id.id,
                        aa1.id,
                        aa2.id,
                        aa3.id,
                        aa4.id,
                    )
                    if not identifier in identifiers:
                        identifiers.append(identifier)
                        values[identifier] = {
                            'account_id': rpc_line.account_id.id,
                            'type': 'cr',
                            'name': rpc_line.name,
                            'amount': rpc_line.amount,
                            'analytic_1': aa1.id,
                            'analytic_2': aa2.id,
                            'analytic_3': aa3.id,
                            'account_analytic_id': aa4.id,
                        }
                    else:
                        values[identifier]['amount'] += rpc_line.amount
                    total += rpc_line.amount
            for voucher_line_id in VoucherLine.search([('voucher_id','=',self.id)]):
                voucher_line_id.unlink()
            for k,v in values.items():
                v['voucher_id'] = self.id
                self.env['account.voucher.line'].create(v)
            self.amount = total
        return True

    @api.multi
    def button_dummy(self):
        return True

    @api.multi
    def write(self, vals):
        res = super(AccountVoucher, self).write(vals)
        return res

    @api.multi
    def action_move_line_create(self):
        if self.bank_in_type=='reimburse' and not self.line_cr_ids:
            raise osv.except_osv(('Perhatian !'), ("Silahkan klik tombol Proses sebelum klik tombol Validate !"))
        res = super(AccountVoucher,self).action_move_line_create()
        if self.bank_in_type == 'reimburse' and self.reimburse_ids:
            for reimburse in self.reimburse_ids:
                reimburse.reimbursed_id.write({'state':'paid'})
        return res


class AccountVoucherLine(models.Model):
    _inherit = 'account.voucher.line'

    @api.model
    def default_get(self, fields):
        res = super(AccountVoucherLine, self).default_get(fields)
        branch_id = self.env.context.get('branch_id',False)
        if branch_id:
            branch_id = self.env['dym.branch'].browse([branch_id])
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.env['account.analytic.account'].get_analytical(branch_id, 'Unit', False, 4, 'General')
            res.update({
                'analytic_1': analytic_1_general,
                'analytic_2': analytic_2_general,
                'analytic_3': analytic_3_general,
                'analytic_account_id' : analytic_4_general,
            })
        return res

    @api.model
    def create(self, vals):
        res = super(AccountVoucherLine, self).create(vals)
        return res

    @api.onchange('account_id')
    def onchange_account_id(self):
        if self.env.context.get('transaction_type',False) and self.account_id:
            self.name = self.account_id.name
            if not self.voucher_id.name:
                self.voucher_id.name = self.account_id.name

        dom = {}
        edi_doc_list = []
        acc_filter = self.env['dym.account.filter']
        if self.env.context.get('transaction_type',False) == 'in':        
            bank_in_filter = acc_filter.get_domain_account("bank_in")
            edi_doc_list.extend(bank_in_filter)
        if self.env.context.get('transaction_type',False) == 'out':        
            bank_out_filter = acc_filter.get_domain_account("bank_out")
            edi_doc_list.extend(bank_out_filter)

        dom['account_id'] = edi_doc_list
        if self.account_id:
            self.name = self.account_id.name
            if self.voucher_id.branch_id.id and self.voucher_id.division:
                aa2_ids = self.env['analytic.account.filter'].get_analytics_2(self.voucher_id.branch_id.id, self.voucher_id.division, self.account_id.id)
                if aa2_ids:
                    dom['analytic_2'] = [('id','in',aa2_ids.ids)]
                    self.analytic_2 = aa2_ids[0] 
        return {'domain':dom}

    @api.onchange('analytic_2')
    def onchange_analytic_2(self):
        dom = {}
        if self.analytic_2 and self.voucher_id.branch_id.id and self.voucher_id.division:
            aa3_ids = self.env['analytic.account.filter'].get_analytics_3(self.voucher_id.branch_id.id, self.voucher_id.division, self.account_id.id, self.analytic_2.code, self.analytic_2.id)
            if aa3_ids:
                dom['analytic_3'] = [('id','in',aa3_ids.ids)]
                self.analytic_3 = aa3_ids[0]
        return {'domain':dom}

    @api.onchange('analytic_2','analytic_3','account_id')
    def onchange_analytic_3(self):
        dom = {}
        if self.analytic_2 and self.analytic_3 and self.voucher_id.branch_id.id and self.voucher_id.division and self.account_id:
            aa4_ids = self.env['analytic.account.filter'].get_analytics_4(self.voucher_id.branch_id.id, self.voucher_id.division, self.account_id.id, self.analytic_2.code, self.analytic_2.id, self.analytic_3.id)            
            dom['account_analytic_id'] = [('id','in',[])]
            if aa4_ids:
                dom['account_analytic_id'] = [('id','in',aa4_ids.ids)]
                self.account_analytic_id = aa4_ids[0]
        return {'domain':dom}
