from openerp import models, fields, api, _
from ..report import fungsi_terbilang
from openerp.addons.dym_base import DIVISION_SELECTION
from openerp.exceptions import Warning as UserError, RedirectWarning

class iBanking(models.Model):
    _name = 'dym.ibanking'
    _description = 'Internet Banking (known as damrek)'

    @api.depends('transfer_ids.amount_total','voucher_ids.amount')
    def _amount_all(self):
        for ib in self:
            amount_total = 0.0
            for line in ib.transfer_ids:
                amount_total += line.amount_total
            for line in ib.voucher_ids:
                amount_total += line.amount
            ib.update({
                'amount_total': amount_total,
                'total_record': len(ib.transfer_ids) + len(ib.voucher_ids),
            })

    name = fields.Char('No')
    file_name = fields.Char('Filename')
    branch_id = fields.Many2one('dym.branch', string='Branch')
    division = fields.Selection(DIVISION_SELECTION, 'Division')
    payment_from_id = fields.Many2one('account.journal',string="Source of Fund",domain="[('branch_id','in',[branch_id,False]),('type','in',['cash','bank'])]")
    acc_number = fields.Many2one('res.partner.bank', string='Bank Account')
    bank = fields.Many2one('res.bank', string='Bank Name', related='acc_number.bank')
    kode_transaksi = fields.Selection([('BCA','BCA'),('LLG','LLG'),('RTG','RTGS')], string="Kode Transaksi")
    date = fields.Date(string="Date", required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")
    transfer_ids = fields.One2many('dym.bank.transfer', 'ibanking_id', 'Transfer')
    voucher_ids = fields.One2many('account.voucher', 'ibanking_id', 'Transfer')
    amount_total = fields.Float(string='Total Amount', store=True, readonly=True, compute='_amount_all')
    total_record = fields.Integer(string='Total Records', store=True, readonly=True, compute='_amount_all')

    data_file = fields.Binary(
        'CSV File',
        help='CSV file to be exported to Internet Banking')


    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancel'),
        ('confirm', 'Confirm'),
        ('process', 'iBanking Process'),        
        ('done', 'Done'),
        ], string='State', default='draft')


    @api.model
    def default_get(self, fields):
        res = super(iBanking, self).default_get(fields)
        active_model = self.env.context.get('active_model',False)
        active_ids = self.env.context.get('active_ids',[])

        user = self.env.user
        company_id = user.company_id.id

        branch_id = self.env['dym.branch'].search([('company_id','=',user.company_id.id),('branch_status','=','HO')])
        if not branch_id:
            raise UserError(_('Perhatian !'), _("Tidak ditemukan cabang Head Office untuk perusahaan %s" % user.company_id.name))
        res['branch_id'] = branch_id.id
        res['division'] = 'Finance'
        return res

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            if rec.name == '/':
                name = rec.file_name
            else:
                name = rec.name
            res.append((rec.id, name))
        return res

    def get_rek_bank_sup_own(self,journal_id):
        bank_partner = self.env['res.partner.bank'].search([('journal_id','=',journal_id)])
        # return [str(bank_partner.acc_number), str(bank_partner.bank.bic), str(bank_partner.partner_id.name), str(bank_partner.owner_name)]
        return [bank_partner.acc_number.encode('utf-8'), bank_partner.bank.bic.encode('utf-8'), bank_partner.partner_id.name.encode('utf-8'), bank_partner.owner_name.encode('utf-8')]

    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil

    @api.one
    def act_confirm(self):
        if self.name=='/':
            self.name = self.env['ir.sequence'].get_per_branch(self.branch_id.id, 'IBK', division='Finance') 
        self.state = 'confirm'

    @api.multi
    def act_cancel(self):
        for trf_line in self.transfer_ids:
            trf_line.write({'ibanking_id':False})
        for vcr_line in self.voucher_ids:
            vcr_line.write({'ibanking_id':False})
        self.write({'state':'cancel','total_record':0})

    @api.multi
    def act_cancel_post(self):
        if self.transfer_ids:
            for transfer in self.transfer_ids:
                if transfer.move_id:
                    transfer.cancel_bank()

        if self.voucher_ids:
            for voucher in self.voucher_ids:
                move_obj = self.env['account.move']
                acc_move = move_obj.search([('model','=',voucher._name),('transaction_id','=',voucher.id),('name','=like','IBK%'),('state','=','posted')])
                if acc_move:
                    acc_move.action_reverse_journal()
        self.write({'state':'cancel'})

    @api.one
    def set_to_draft(self):
        self.data_file = False
        self.state = 'draft'

