from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp import models, fields, api
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp.tools.translate import _
from random import randint

class account_voucher(models.Model):
    _inherit = 'account.voucher'
    _description = 'Account Voucher'

    disbursed = fields.Boolean('Cair HO')
    voucher_id = fields.Many2one('account.voucher')
    # journal_type = fields.Selection(related='journal_id.type',string="Journal Type")
    payment_method = fields.Selection([('giro','Giro'),('cheque','Cheque'),('internet_banking','Internet Banking'),('auto_debit','Auto Debit'),('single_payment','Single Payment')], string='Payment Method')
    cheque_giro_number = fields.Many2one('dym.checkgyro.line', string='Chk/Giro No', domain="[('journal_id','=',journal_id),('state_stored','=','available')]")
    cheque_giro_date = fields.Date(string='Chk/Giro Date',required=True,default=fields.Date.context_today)
    ibanking_id = fields.Many2one('dym.ibanking', 'ibanking')
    auto_debit_date = fields.Date(string='Auto Debit Date')

    @api.model
    def is_payment(self,):
        if self.type=='payment' and self.payment_method == 'internet_banking' and (not self.ibanking_id and self.ibanking_id.state != 'done'):
            raise UserError(_('Perhatian !'), _("Konfirmasi pembayaran ke supplier yang menggunakan metode internet banking, dilakukan saat proses internet banking berhasil dijalankan."))
        if self.payment_method=='auto_debit' and self.auto_debit_date > datetime.now().strftime('%Y-%m-%d'):
            raise UserError(_('Perhatian !'), _("Konfirmasi pembayaran ke supplier yang menggunakan metode auto debit, akan dilakukan secara otomatis sesuai tanggal auto debit."))
        res = super(account_voucher, self).is_payment()
        return res

    @api.multi
    def create_ibanking(self):
        iBanking = self.env['dym.ibanking']
        BankAccount = self.env['res.partner.bank']
        for rec in self:
            if not rec.bank_account:
                raise UserError(_('Perhatian !'), _("%s tidak memiliki rekening tujuan, harap lengkapi dulu pada kolom Rekening Pembayaran." % rec.number))
            AccNumber = rec.bank_account
            kode_transaksi = 'LLG'
            if rec.net_amount >= 500000000:
                kode_transaksi = 'RTG'
            if AccNumber.bank.bic=='BCA':
                kode_transaksi = 'BCA'

            ibanking_id = iBanking.search([
                ('date','=',rec.due_date_payment),
                ('kode_transaksi','=',kode_transaksi),
                ('payment_from_id','=',rec.journal_id.id),
                ('state','=','draft'),
            ])
            if not ibanking_id:
                name = '%s%s%s' % (kode_transaksi,datetime.strptime(rec.due_date_payment,DSDF).strftime('%Y%m%d'),randint(100,999))
                # name = '%s_%s%s%s' % (rec.journal_id.code,kode_transaksi,datetime.strptime(rec.due_date_payment,DSDF).strftime('%y%m%d'),randint(100,999))

            if not ibanking_id:
                user = self.env.user
                company_id = user.company_id.id
                branch_id = self.env['dym.branch'].search([('company_id','=',user.company_id.id),('branch_status','=','HO')])
                if not branch_id:
                    raise UserError(_('Perhatian !'), _("Tidak ditemukan cabang Head Office untuk perusahaan %s" % user.company_id.name))
                acc_number = self.env['res.partner.bank'].search([('journal_id','=',rec.journal_id.id)])
                if not acc_number:
                    raise UserError(_('Perhatian !'), _("Journal %s tidak memiliki rekening bank." % rec.journal_id.name))
                values = {
                    'branch_id': branch_id.id,
                    'division': 'Finance',
                    'name': '/',
                    'acc_number': acc_number.id,
                    'file_name': name,
                    'payment_from_id': rec.journal_id.id,
                    'date': rec.due_date_payment,
                    'company_id': rec.company_id.id,
                    'kode_transaksi': kode_transaksi,
                }
                ibanking_id = iBanking.create(values)
            else:
                ibanking_id = ibanking_id[0]
            rec.ibanking_id = ibanking_id.id
        return {}

    # @api.one
    # def write(self, vals):
    #     if 'cheque_giro_number' in vals and vals['cheque_giro_number']:
    #         checkgyro_id = self.env['dym.checkgyro.line'].browse([vals['cheque_giro_number']])
    #         if checkgyro_id:
    #             checkgyro_id.state = 'used'
    #             checkgyro_id.used_date = self.date
    #     return super(account_voucher, self).write(vals)
