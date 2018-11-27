import os
import zipfile
import base64
import json
from datetime import datetime
from openerp import api, models, fields
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF, DEFAULT_SERVER_DATETIME_FORMAT as DTF
from openerp.tools.translate import _
from openerp import tools
from lxml import etree

def zip(src, dst):
    zf = zipfile.ZipFile("%s.zip" % (dst), "w", zipfile.ZIP_DEFLATED)
    abs_src = os.path.abspath(src)
    for dirname, subdirs, files in os.walk(src):
        for filename in files:
            absname = os.path.abspath(os.path.join(dirname, filename))
            arcname = absname[len(abs_src) + 1:]
            zf.write(absname, arcname)
    zf.close()

class InternetBanking(models.TransientModel):
    _name = "bank.trf.request.ib"
    _description = "Internet Banking"

    bank = fields.Selection([('is_bca','BCA')], 'BANK')
    kode_transaksi = fields.Selection([('BCA','BCA'),('LLG','LLG'),('RTG','RTGS')], 'Kode Transaksi', default='LLG')
    date = fields.Date(string='Tanggal Efektif', required=True, default=lambda self: self.env.context.get('date', fields.Date.context_today(self)))
    account_number = fields.Char('Rekening Perusahaan')
    internet_banking_code = fields.Char('Kode Internet Banking')
    company_code = fields.Char('Kode Perusahaan')
    payment_method = fields.Many2one('account.journal', string='Payment Method')
    bank_account = fields.Many2one('res.partner.bank', string='Account Bank')
    amount_total = fields.Float('Total Payment')
    total_record = fields.Integer('Total Record')
    remarks_1 = fields.Char('Remarks 1')
    remarks_2 = fields.Char('Remarks 2')
    amount_total_show = fields.Float(related='amount_total', string='Total Payment', readonly=True)
    payment_method_show = fields.Many2one("account.journal", related='payment_method', string='Payment Method',readonly=True)
    data_file = fields.Binary('File')
    name = fields.Char('File Name')
    bank_trf_ids = fields.Many2many('dym.bank.transfer', 'internet_banking_transfer_rel', 'internet_banking_id', 'transfer_id', 'Bank Transfer')


    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(InternetBanking, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        active_model = self.env.context.get('active_model',False)
        active_ids = self.env.context.get('active_ids',[])
        if not active_model == 'bank.trf.request':
            return res
        if len(active_ids) < 1:
            raise ValidationError(_('Please select multiple order to merge in the list view.'))
        data = self.env['bank.trf.request'].browse(active_ids)
        if len(list(set([m.payment_from_id.id for m in data])))>1:
            raise UserError(_('You can only select multiple internet banking from same bank account'))
        for dt in data:
            if dt.payment_method != 'internet_banking':
                raise UserError(_('The bank transfer %s is not mark as Internet Banking.' % dt.name))
            if not dt.state in ['app_approve','waiting_for_confirm_received']:
                raise UserError(_('Only bank transfer in approved state can be process here'))
            if not self.env['res.partner.bank'].search([('journal_id','=',dt.payment_from_id.id)]):
                raise UserError(_('Warning!'), _("There is no bank account found fo journal %s.")% dt.payment_from_id.name)
            for line in dt.line_ids:
                bank_account_to = self.env['res.partner.bank'].search([('journal_id','=',line.payment_to_id.id)])
                if not bank_account_to:
                    raise UserError(_('Destination journal %s in bank transfer %s seem not a bank account journal, please check it again to continue.' % (line.payment_to_id.name,dt.name)))
        return res

    @api.model
    def default_get(self, fields):
        if self.env.context.get('active_ids', False):
            if len(self.env.context.get('active_ids')) < 1:
                raise UserError(_('Warning!'), _("Please select voucher from the list view!"))
        
        res = super(InternetBanking, self).default_get(fields)
        trf_ids = self.env.context.get('active_ids', False) or False

        bank_transfers = self.env['dym.bank.transfer'].browse(trf_ids)
        if not bank_transfers:
            return res
        bank_account_from = self.env['res.partner.bank'].search([('journal_id','=',bank_transfers[0].payment_from_id.id)])
        amount_total = 0
        vouchers = []
        for trf in bank_transfers:
            amount_total += trf.amount
            vouchers.append(trf.id)
        res.update({
            'payment_method':bank_transfers[0].payment_from_id.id,
            'payment_method_show':bank_transfers[0].payment_from_id.id,
            'bank_account':bank_account_from.id,
            'internet_banking_code':bank_account_from.bank.internet_banking_code,
            'company_code':bank_account_from.bank.company_code,
            'bank':bank_account_from.bank.bank,
            'account_number':bank_account_from.acc_number,
            'total_record':len(trf_ids),
            'bank_trf_ids':[(6, 0, vouchers)],
            'amount_total':amount_total,
            'amount_total_show':amount_total,
        })
        return res

    @api.model
    def format_number(self, char, maks, word, depan=True):
        if char:
            char = str(char)
        else:
            char = ''
        if len(char) < maks:
            while len(char) < maks:
                if depan == True:
                    char = word + char
                else:
                    char = char + word
        elif len(char) > maks:
            char = char[:maks]
        return char
    
    @api.model
    def eksport_bca(self, trx_obj):
        result = ''
        date = self.date
        bulan = str(date[5:7])
        tanggal = str(date[8:10])
        tahun = str(date[:4])
        tanggal_efektif = tahun+bulan+tanggal
        if len(self.account_number) != 10 or not self.account_number.isdigit():
            raise UserError(('Perhatian !'), ("Rekening Perusahaan harus 10 digit."))
        if len(self.company_code) > 23:
            raise UserError(('Perhatian !'), ("Kode Perusahaan tidak boleh lebih dari 23 digit."))
        if not self.bank_account.partner_id:
            raise UserError(('Perhatian !'), ("Account owner untuk account bank %s belum di set.")%(self.bank_account.name_get().pop()[1]))
        if not self.bank_account.bank.bic:
            raise UserError(('Perhatian !'), ("Bank identifier code untuk bank %s belum di set.")%(self.bank_account.name_get().pop()[1]))
        amount_total = str("%.2f"%float(self.amount_total))
        amount_total = self.format_number(amount_total, 16, '0')
        total_record = self.format_number(len(self.bank_trf_ids), 5, '0')
        company_code = self.format_number(self.company_code, 23, ' ',depan=False)
        if self.kode_transaksi == 'RTG':
            sisa_space = self.format_number('', 128, ' ')
        else:
            sisa_space = self.format_number('', 183, ' ')
        header = '0SP' + str(tanggal_efektif) + str(self.account_number) + ' ' + str(company_code) + '0000' + amount_total + total_record + self.kode_transaksi + sisa_space
        result += header
        result += '\r\n'

        groups = {}
        ib_files = []
        total_record = 0
        for voucher in trx_obj:
            effective_date = datetime.strptime(voucher.date,DF).strftime('%Y%m%d')
            if effective_date not in groups:
                groups.update({
                    effective_date:[]
                })
            for line in voucher.line_ids:
                total_record += 1
                net_amount = self.format_number(str("%.2f"%float(voucher.amount_total)),16,'0')
                values = {
                    'effective_date': effective_date,
                    'net_amount': net_amount,
                    'pengirim': self.format_number(self.bank_account.partner_id.name, 35, ' ', depan=False).upper()
                }

                bank_account_to = self.env['res.partner.bank'].search([('journal_id','=',line.payment_to_id.id)])
                account_number = bank_account_to.acc_number
                pengirim = self.format_number(self.bank_account.partner_id.name, 35, ' ', depan=False).upper()

                if self.kode_transaksi == 'BCA':
                    space_1 = self.format_number('', 42, ' ')
                    space_2 = self.format_number('', 35, ' ')
                    data_1 = self.format_number(self.bank_account.bank.bic, 18, ' ',depan=False)
                    data_2 = self.format_number(bank_account_to.bank.bic, 18, ' ',depan=False)
                    data_3 = self.format_number('', 18, ' ')
                    penutup_code = '2R' + self.internet_banking_code
                    values.update({
                        'space_1':space_1,
                        'space_2':space_2,
                        'data_1':data_1,
                        'data_2':data_2,
                        'data_3':data_3,
                        'penutup_code':penutup_code,
                    })
                elif self.kode_transaksi == 'LLG':
                    space_1 = self.format_number('', 36, ' ')
                    space_2 = self.format_number('', 35, ' ')
                    if not bank_account_to.bank.bank_indonesia_code or len(bank_account_to.bank.bank_indonesia_code) != 7:
                        raise UserError(('Perhatian !'), ("Kode BI di master bank %s harus 7 angka.")%(bank_account_to.bank.name_get()))
                    account_number = self.format_number(account_number, 16, ' ', depan=False)
                    data_1 = self.format_number(self.kode_transaksi, 7, ' ',depan=False)
                    data_1 += self.format_number(bank_account_to.bank.bank_indonesia_code, 11, ' ',depan=False)
                    data_2 = self.format_number(bank_account_to.bank.bic, 18, ' ',depan=False)
                    data_3 = self.format_number('', 18, ' ')
                    penutup_code = '1R' + '888'
                    values.update({
                        'space_1':space_1,
                        'space_2':space_2,
                        'data_1':data_1,
                        'data_2':data_2,
                        'data_3':data_3,
                        'penutup_code':penutup_code,
                        'account_number':account_number,
                    })
                elif self.kode_transaksi == 'RTG':
                    space_1 = self.format_number('', 18, ' ')
                    space_2 = ''
                    account_number = self.format_number(account_number, 16, ' ', depan=False)
                    data_1 = self.format_number('', 7, ' ')
                    data_1 += self.format_number(bank_account_to.bank.bank_indonesia_code, 11, ' ',depan=False)
                    data_2 = self.format_number(bank_account_to.bank.bic, 18, ' ',depan=False)
                    data_3 = self.format_number('', 18, ' ')
                    penutup_code = '888'
                    values.update({
                        'space_1':space_1,
                        'space_2':space_2,
                        'data_1':data_1,
                        'data_2':data_2,
                        'data_3':data_3,
                        'penutup_code':penutup_code,
                        'account_number':account_number,
                    })

                remarks_1 = self.format_number(self.remarks_1, 18, ' ', depan=False)
                remarks_2 = self.format_number(self.remarks_2, 18, ' ', depan=False)
                space_3 = self.format_number('', 18, ' ')
                detail = '1' + str(account_number) + str(space_1) + '0000' + net_amount + pengirim + space_2 + data_1 + data_2 + data_3 + remarks_1 + remarks_2 + space_3 + penutup_code
                result += detail
                result += '\r\n'
                values.update({
                    'remarks_1':remarks_1,
                    'remarks_2':remarks_2,
                    'space_3':space_3,
                })
                groups[effective_date].append(values)

        kode = str(self.kode_transaksi) +'-'+ str(tanggal_efektif)
        nama = kode + '.txt'
        out = base64.encodestring(result)
        export = self.write({'data_file':out, 'name': nama,' total_record': total_record})
        return export

    @api.multi
    def export(self):
        trx_obj = self.bank_trf_ids
        if self.bank == 'is_bca':
            result = self.eksport_bca(trx_obj)
        form_id  = 'Eksport Internet Banking'
        view_id = self.env['ir.ui.view'].search([("name", "=", form_id),("model", "=", 'bank.trf.request.ib')])
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id.id,
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'bank.trf.request.ib',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': self.env.context
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
