import base64
from datetime import datetime
from openerp import api, models, fields, _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF, DEFAULT_SERVER_DATETIME_FORMAT as DTF

class ExportInternetBanking(models.TransientModel):
    _name = "export.internet.banking"
    _description = "Internet Banking"

    name = fields.Char('File Name')
    file_name = fields.Char('File Name')
    ibanking_id = fields.Many2one('dym.ibanking',string='iBanking')
    bank = fields.Selection([('is_bca','BCA')], 'BANK')
    kode_transaksi = fields.Selection([('BCA','BCA'),('LLG','LLG'),('RTG','RTGS')], 'Kode Transaksi', default='LLG')
    date = fields.Date(string='Tanggal Efektif', required=True)
    account_number = fields.Char('Rekening Perusahaan')
    internet_banking_code = fields.Char('Kode Internet Banking')
    company_code = fields.Char('Kode Perusahaan')
    payment_method = fields.Many2one('account.journal', string='Payment Method')
    payment_method_show = fields.Many2one("account.journal", related='payment_method', string='Payment Method',readonly=True)
    bank_account = fields.Many2one('res.partner.bank', string='Account Bank')
    amount_total = fields.Float('Total Payment')
    amount_total_show = fields.Float(related='amount_total', string='Total Payment', readonly=True)
    total_record = fields.Integer('Total Record')
    remarks_1 = fields.Char('Remarks 1')
    remarks_2 = fields.Char('Remarks 2')
    data_file = fields.Binary('File')

    @api.model
    def default_get(self, fields):        
        res = super(ExportInternetBanking, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', False) or False
        active_model = self.env.context.get('active_model', False) or False
        if not active_model == 'dym.ibanking' or not active_ids:
            raise UserError(_('Warning!'), _("Program ini hanya boleh dijalankan dari layar transaksi Internet Banking!"))
        ib_id = self.env['dym.ibanking'].browse(active_ids)
        # bank_account_from = self.env['res.partner.bank'].search([('journal_id','=',ib_id.payment_from_id.id)])
        # if not bank_account_from:
        #     raise UserError(_('Warning!'), _("Journal %s tidak memiliki rekening bank!" % ib_id.payment_from_id.name))
        number_of_transfers = len(ib_id.transfer_ids.ids) + len(ib_id.voucher_ids.ids)

        if ib_id.kode_transaksi == 'BCA':
            internet_banking_code = '014'
        else:
            internet_banking_code = '888'

        res.update({
            'file_name': ib_id.file_name,
            'ibanking_id': ib_id.id,
            'date': ib_id.date,
            'payment_method':ib_id.payment_from_id.id,
            'payment_method_show':ib_id.payment_from_id.id,
            'bank_account':ib_id.acc_number.id,
            'kode_transaksi':ib_id.kode_transaksi,
            'internet_banking_code':internet_banking_code,
            'company_code':ib_id.acc_number.company_code,
            'bank':ib_id.bank.bank,
            'account_number':ib_id.acc_number.acc_number,
            'total_record':number_of_transfers,
            'amount_total':ib_id.amount_total,
            'amount_total_show':ib_id.amount_total,
            'remarks_2': ib_id.name,
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
    def eksport_bca(self):
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
        total_record = self.format_number(self.total_record, 5, '0')
        company_code = self.format_number(self.company_code, 23, ' ',depan=False)
        if self.kode_transaksi == 'RTG':
            sisa_space = self.format_number('', 128, ' ')
        else:
            sisa_space = self.format_number('', 183, ' ')

        if self.kode_transaksi in ['RTG','LLG']:
            header_code = '0MP'
        else:
            header_code = '0SP'

        header = header_code + str(tanggal_efektif) + str(self.account_number) + ' ' + str(company_code) + '0000' + amount_total + total_record + self.kode_transaksi + sisa_space
        result += header
        result += '\r\n'

        groups = {}
        ib_files = []
        total_record = 0

        # DATA FROM VOUCHER
        for voucher in self.ibanking_id.voucher_ids:
            effective_date = datetime.strptime(self.date,DF).strftime('%Y%m%d')
            if effective_date not in groups:
                groups.update({
                    effective_date:[]
                })

            total_record += 1
            net_amount = self.format_number(str("%.2f"%float(voucher.net_amount)),16,'0')
            values = {
                'effective_date': effective_date,
                'net_amount': net_amount,
                'pengirim': self.format_number(self.bank_account.partner_id.name, 35, ' ', depan=False).upper()
            }

            bank_account_to = voucher.bank_account
            account_number = bank_account_to.acc_number
            pengirim = self.format_number(self.bank_account.partner_id.name, 35, ' ', depan=False).upper()

            if self.kode_transaksi == 'BCA':
                space_1 = self.format_number('', 42, ' ')
                space_2 = self.format_number('', 46, ' ')
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
                space_2 = self.format_number('', 46, ' ')
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
            penerima = voucher.bank_account_name
            detail = '1' + str(account_number) + str(space_1) + '0000' + net_amount + penerima + space_2 + data_1 + data_2 + data_3 + remarks_1 + remarks_2 + space_3 + penutup_code
            # detail = '1' + str(account_number) + str(space_1) + '0000' + net_amount + pengirim + space_2 + data_1 + data_2 + data_3 + remarks_1 + remarks_2 + space_3 + penutup_code
            result += detail
            result += '\r\n'
            values.update({
                'remarks_1':remarks_1,
                'remarks_2':remarks_2,
                'space_3':space_3,
            })
            groups[effective_date].append(values)

        # DATA FROM BANK TRANSFER
        for trf in self.ibanking_id.transfer_ids:
            effective_date = datetime.strptime(self.date,DF).strftime('%Y%m%d')
            if effective_date not in groups:
                groups.update({
                    effective_date:[]
                })

            for line in trf.line_ids:
                total_record += 1
                net_amount = self.format_number(str("%.2f"%float(line.amount)),16,'0')
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

        out = base64.encodestring(result)
        name = self.file_name.replace('.txt','') + '.txt'
        export = self.ibanking_id.write({
            'data_file': out,
            'file_name': name, 
            'total_record': total_record,
            'state': 'process',
        })
        return export

    @api.multi
    def export(self):
        result = False
        if self.bank == 'is_bca':
            result = self.eksport_bca()
        if result:
            print "======",self.env.context
