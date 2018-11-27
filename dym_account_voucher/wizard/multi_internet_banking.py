from openerp.osv import fields, osv, orm
import base64
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.tools.translate import _
from openerp import tools
from lxml import etree

class internet_banking(osv.osv_memory):
    _name = "internet.banking"
    _description = "Internet Banking"

    _columns = {
        'bank':fields.selection([('is_bca','BCA')], 'BANK'),
        'kode_transaksi':fields.selection([('BCA','BCA'),('LLG','LLG'),('RTG','RTGS')], 'Kode Transaksi'),
        'date':fields.date('Tanggal Efektif'),
        'account_number': fields.char('Rekening Perusahaan'),
        'internet_banking_code': fields.char('Kode Internet Banking'),
        'company_code': fields.char('Kode Perusahaan'),
        'payment_method': fields.many2one('account.journal', string='Payment Method'),
        'bank_account': fields.many2one('res.partner.bank', string='Account Bank'),
        'amount_total': fields.float('Total Payment'),
        'total_record': fields.integer('Total Record'),
        'remarks_1': fields.char('Remarks 1'),
        'remarks_2': fields.char('Remarks 2'),
        'amount_total_show':fields.related('amount_total', type="float", string='Total Payment',readonly=True),
        'payment_method_show':fields.related('payment_method',type="many2one", relation="account.journal", string='Payment Method',readonly=True),
        'data_file': fields.binary('File'),
        'name': fields.char('File Name'),
        'voucher_ids': fields.many2many('account.voucher', 'internet_banking_voucher_rel', 'internet_banking_id', 'voucher_id', 'Supplier Payment'),
    }

    _defaults = {
        'date':fields.date.context_today,
    }

    def get_data_master_bank(self, cr, uid, ids, bank_account_id, context=None):
        bank_account = self.pool.get('res.partner.bank').browse(cr, uid, bank_account_id)
        if bank_account.bank.internet_banking == False:
            raise osv.except_osv(_('Warning!'), _("Bank %s tidak memiliki data internet banking!")%(bank_account.bank.name))
        account_number = ''
        for index in range(0,len(bank_account.acc_number)):
            if bank_account.acc_number[index].isdigit():
                account_number += bank_account.acc_number[index]
        result = {
            'internet_banking_code':bank_account.bank.internet_banking_code,
            'company_code':bank_account.company_code,
            'bank':bank_account.bank.bank,
            'account_number':account_number
        }
        return result

    def onchange_kode_transaksi(self, cr, uid, ids, kode_transaksi, context=None):
        context = context and dict(context) or {}
        res = {'value': {}}
        internet_banking_code = '014'
        if kode_transaksi != 'BCA':
            internet_banking_code = '888'
        res['value'].update({'internet_banking_code': internet_banking_code})
        return res

    def cek_payment(self, cr, uid, ids, context=None):
        payment = self.pool.get('account.voucher').browse(cr, uid, ids, context=context)
        result = {
            'payment_method':False,
            'bank_account':False,
            'internet_banking_code':False,
            'company_code':False,
            'account_number':False,
            'bank':False,
        }
        for pay in payment:
            if result['payment_method'] != False and pay.journal_id != result['payment_method']:
                raise osv.except_osv(_('Warning!'), _("Data yang dieksport harus memiliki payment method yang sama!"))
            else:
                result['payment_method'] = pay.journal_id
        bank_account = self.pool.get('res.partner.bank').search(cr, uid, [('journal_id','=',result['payment_method'].id)])
        if not bank_account:
            raise osv.except_osv(_('Warning!'), _("Tidak ditemukan bank account dengan jurnal %s")%(result['payment_method'].name))
        elif len(bank_account) == 1:
            result['bank_account'] = self.pool.get('res.partner.bank').browse(cr, uid, bank_account)
            data_master_bank = self.get_data_master_bank(cr, uid, ids, result['bank_account'].id)
            result['internet_banking_code'] = data_master_bank['internet_banking_code']
            result['company_code'] = data_master_bank['company_code']
            result['account_number'] = data_master_bank['account_number']
            result['bank'] = data_master_bank['bank']
        return result

    # def default_get(self, cr, uid, fields, context=None):
    #     if context is None:
    #         context = {}
    #     if context and context.get('active_ids', False):
    #         if len(context.get('active_ids')) < 1:
    #             raise osv.except_osv(_('Warning!'), _("Please select voucher from the list view!"))
    #     res = super(internet_banking, self).default_get(cr, uid, fields, context=context)
    #     payment_ids = context and context.get('active_ids', False) or False
    #     result = self.cek_payment(cr, uid, payment_ids, context=context)
    #     if 'payment_method' in fields:
    #         acc_number_ids = self.pool.get('res.partner.bank').search(cr, uid, [('journal_id','=',result['payment_method'].id)], context=context)
    #         if not acc_number_ids:
    #             raise osv.except_osv(_('Perhatian!'), _("Tidak ditemukan rekening bank atas jurnal %s!" % result['payment_method'].name))
    #     if 'payment_method_show' in fields:
    #         res.update({'payment_method_show':result['payment_method'].id})
    #     if 'bank_account' in fields and result['bank_account']:
    #         res.update({'bank_account':result['bank_account'].id})
    #     if 'internet_banking_code' in fields:
    #         res.update({'internet_banking_code':result['internet_banking_code']})
    #     if 'company_code' in fields:
    #         res.update({'company_code':result['company_code']})
    #     payment = self.pool.get('account.voucher').browse(cr, uid, payment_ids, context=context)
    #     amount_total = 0
    #     vouchers = []
    #     for pay in payment:
    #         amount_total += pay.net_amount
    #         vouchers.append(pay.id)
    #     if 'voucher_ids' in fields:
    #         res.update({'voucher_ids':[(6, 0, vouchers)]})
    #     if 'amount_total' in fields:
    #         res.update({'amount_total':amount_total})
    #     if 'amount_total_show' in fields:
    #         res.update({'amount_total_show':amount_total})
    #     if 'account_number' in fields:
    #         res.update({'account_number':result['account_number']})
    #     if 'bank' in fields:
    #         res.update({'bank':result['bank']})
    #     if 'total_record' in fields:
    #         res.update({'total_record':len(context.get('active_ids'))})
    #     return res

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) < 1:
                raise osv.except_osv(_('Warning!'), _("Please select voucher from the list view!"))
        res = super(internet_banking, self).default_get(cr, uid, fields, context=context)

        active_ids = context.get('active_ids', False) or False
        active_model = context.get('active_model', False) or False
        if not active_model == 'dym.ibanking' or not active_ids:
            raise UserError(_('Warning!'), _("Program ini hanya boleh dijalankan dari layar transaksi Internet Banking!"))
        ib_id = self.pool.get('dym.ibanking').browse(cr,uid,active_ids)
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

    def format_number(self, cr, uid, ids, char, maks, word, depan=True, context=None):
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
    
    def eksport_bca(self, cr, uid, ids, trx_obj, context=None):
        val = self.browse(cr, uid, ids)[0]
        result = ''
        if not val.date:
            raise osv.except_osv(('Perhatian !'), ("Tanggal Efektif waji diisi."))

        date = datetime.strptime(val.date, DSDF)
        bulan = date.strftime('%m')
        tanggal = date.strftime('%d')
        tahun = date.strftime('%Y')

        tanggal_efektif = tahun+bulan+tanggal
        if len(val.account_number) != 10 or not val.account_number.isdigit():
            raise osv.except_osv(('Perhatian !'), ("Rekening Perusahaan harus 10 digit."))
        if len(val.company_code) > 23:
            raise osv.except_osv(('Perhatian !'), ("Kode Perusahaan tidak boleh lebih dari 23 digit."))
        if not val.bank_account.partner_id:
            raise osv.except_osv(('Perhatian !'), ("Account owner untuk account bank %s belum di set.")%(val.bank_account.name_get().pop()[1]))
        if not val.bank_account.bank.bic:
            raise osv.except_osv(('Perhatian !'), ("Bank identifier code untuk bank %s belum di set.")%(val.bank_account.name_get().pop()[1]))
        amount_total = str("%.2f"%float(val.amount_total))
        amount_total = self.format_number(cr, uid, ids, amount_total, 16, '0')
        total_record = self.format_number(cr, uid, ids, val.total_record, 5, '0')
        company_code = self.format_number(cr, uid, ids, val.company_code, 23, ' ',depan=False)
        if val.kode_transaksi == 'RTG':
            sisa_space = self.format_number(cr, uid, ids, '', 128, ' ')
        else:
            sisa_space = self.format_number(cr, uid, ids, '', 183, ' ')
        if val.kode_transaksi == 'BCA':
            spcode = '0SP'
        else:
            spcode = '0MP'
        header = spcode + str(tanggal_efektif) + str(val.account_number) + ' ' + str(company_code) + '0000' + amount_total + total_record + val.kode_transaksi + sisa_space
        result += header
        result += '\r\n'

        if trx_obj[0].voucher_ids:
            for voucher in trx_obj[0].voucher_ids:
                if not voucher.bank_account:
                    raise osv.except_osv(('Perhatian !'), ("Account bank untuk payment nomor %s belum di set.")%(voucher.number))
                if not voucher.bank_account.partner_id:
                    raise osv.except_osv(('Perhatian !'), ("Account owner untuk account bank %s belum di set.")%(voucher.bank_account.name_get().pop()[1]))
                if not voucher.bank_account.bank.bic:
                    raise osv.except_osv(('Perhatian !'), ("Bank identifier code untuk bank %s belum di set.")%(voucher.bank_account.name_get().pop()[1]))
                if val.kode_transaksi == 'BCA' and voucher.bank_account.bank.bank != 'is_bca':
                    raise osv.except_osv(('Perhatian !'), ("Bank tujuan transfer %s bukan bank bca")%(voucher.number))
                account_number = ''
                for index in range(0,len(voucher.bank_account.acc_number)):
                    if voucher.bank_account.acc_number[index].isdigit():
                        account_number += voucher.bank_account.acc_number[index]
                if not account_number.isdigit():
                    raise osv.except_osv(('Perhatian !'), ("Nomor rekening %s tidak sah. Nomor rekening hanya boleh terdiri dari angka saja." % account_number))
                if val.kode_transaksi == 'BCA' and len(account_number) != 10:
                    raise osv.except_osv(('Perhatian !'), ("Untuk kode transaksi BCA, rekening tujuan harus 10 digit."))
                elif val.kode_transaksi != 'BCA' and len(account_number) > 16:
                    raise osv.except_osv(('Perhatian !'), ("Untuk kode transaksi selain BCA, rekening tujuan tidak boleh lebih dari 16 digit."))
                net_amount = str("%.2f"%float(voucher.net_amount))
                net_amount = self.format_number(cr, uid, ids, net_amount, 16, '0')
                pengirim = self.format_number(cr, uid, ids, val.bank_account.partner_id.name, 35, ' ', depan=False).upper()
                penerima = self.format_number(cr, uid, ids, voucher.bank_account_name, 35, ' ', depan=False).upper()
                if val.kode_transaksi == 'BCA':
                    space_1 = self.format_number(cr, uid, ids, '', 42, ' ')
                    space_2 = self.format_number(cr, uid, ids, '', 35, ' ')
                    data_1 = self.format_number(cr, uid, ids, val.bank_account.bank.bic, 18, ' ',depan=False)
                    data_2 = self.format_number(cr, uid, ids, voucher.bank_account.bank.bic, 18, ' ',depan=False)
                    data_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                    penutup_code = '2R' + val.internet_banking_code
                elif val.kode_transaksi == 'LLG':
                    space_1 = self.format_number(cr, uid, ids, '', 36, ' ')
                    space_2 = self.format_number(cr, uid, ids, '', 35, ' ')
                    if not voucher.bank_account.bank.bank_indonesia_code or len(voucher.bank_account.bank.bank_indonesia_code) != 7:
                        raise osv.except_osv(('Perhatian !'), ("Kode BI di master bank %s harus 7 angka.")%(voucher.bank_account.bank.name_get().pop()[1]))
                    account_number = self.format_number(cr, uid, ids, account_number, 16, ' ', depan=False)
                    data_1 = self.format_number(cr, uid, ids, val.kode_transaksi, 7, ' ',depan=False)
                    data_1 += self.format_number(cr, uid, ids, voucher.bank_account.bank.bank_indonesia_code, 11, ' ',depan=False)
                    data_2 = self.format_number(cr, uid, ids, voucher.bank_account.bank.bic, 18, ' ',depan=False)
                    data_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                    penutup_code = '1R' + '888'
                elif val.kode_transaksi == 'RTG':
                    space_1 = self.format_number(cr, uid, ids, '', 18, ' ')
                    space_2 = ''
                    account_number = self.format_number(cr, uid, ids, account_number, 16, ' ', depan=False)
                    data_1 = self.format_number(cr, uid, ids, '', 7, ' ')
                    data_1 += self.format_number(cr, uid, ids, voucher.bank_account.bank.bank_indonesia_code, 11, ' ',depan=False)
                    data_2 = self.format_number(cr, uid, ids, voucher.bank_account.bank.bic, 18, ' ',depan=False)
                    data_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                    penutup_code = '888'
                # remarks_1 = self.format_number(cr, uid, ids, val.remarks_1, 18, ' ', depan=False)
                # remarks_2 = self.format_number(cr, uid, ids, val.remarks_2, 18, ' ', depan=False)
                # space_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                remarks_1 = self.format_number(cr, uid, ids, val.remarks_1, 16, ' ', depan=False)
                remarks_2 = self.format_number(cr, uid, ids, val.remarks_2, 20, ' ', depan=False)
                space_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                detail = '1' + str(account_number) + str(space_1) + '0000' + net_amount + penerima + space_2 + data_1 + data_2 + data_3 + remarks_1 + remarks_2 + space_3 + penutup_code
                result += detail
                result += '\r\n'

        # BANK TRANSFER
        if trx_obj[0].transfer_ids:
            for trf in trx_obj[0].transfer_ids:
                for line in trf.line_ids:
                    bank_account_to = self.pool.get('res.partner.bank').search(cr,uid,[('journal_id','=',line.payment_to_id.id)])
                    bank=self.pool.get('res.partner.bank').browse(cr,uid,bank_account_to)
                    no_rek = bank.acc_number

                    # if not bank:
                    #     raise osv.except_osv(('Perhatian !'), ("Account bank untuk payment nomor %s belum di set.")%(line.number))
                    # if not bank.partner_id:
                    #     raise osv.except_osv(('Perhatian !'), ("Account owner untuk account bank %s belum di set.")%(bank.name_get().pop()[1]))
                    # if not bank.bank.bic:
                    #     raise osv.except_osv(('Perhatian !'), ("Bank identifier code untuk bank %s belum di set.")%(bank.name_get().pop()[1]))
                    # if val.kode_transaksi == 'BCA' and val.bank_account.bank != 'is_bca':
                    #     raise osv.except_osv(('Perhatian !'), ("Bank tujuan transfer %s bukan bank bca")%(line.name))
                    
                    account_number = ''
                    for index in range(0,len(no_rek)):
                        if no_rek[index].isdigit():
                            account_number += no_rek[index]
                    if not account_number.isdigit():
                        raise osv.except_osv(('Perhatian !'), ("Nomor rekening %s tidak sah. Nomor rekening hanya boleh terdiri dari angka saja." % account_number))
                    if val.kode_transaksi == 'BCA' and len(account_number) != 10:
                        raise osv.except_osv(('Perhatian !'), ("Untuk kode transaksi BCA, rekening tujuan harus 10 digit."))
                    elif val.kode_transaksi != 'BCA' and len(account_number) > 16:
                        raise osv.except_osv(('Perhatian !'), ("Untuk kode transaksi selain BCA, rekening tujuan tidak boleh lebih dari 16 digit."))
                    net_amount = str("%.2f"%float(line.amount))
                    net_amount = self.format_number(cr, uid, ids, line.amount, 16, '0')
                    pengirim = self.format_number(cr, uid, ids, val.bank_account.partner_id.name, 35, ' ', depan=False).upper()
                    # penerima = self.format_number(cr, uid, ids, val.bank_account_name, 35, ' ', depan=False).upper()
                    if val.kode_transaksi == 'BCA':
                        space_1 = self.format_number(cr, uid, ids, '', 42, ' ')
                        space_2 = self.format_number(cr, uid, ids, '', 35, ' ')
                        data_1 = self.format_number(cr, uid, ids, val.bank_account.bank.bic, 18, ' ',depan=False)
                        data_2 = self.format_number(cr, uid, ids, bank.bank.bic, 18, ' ',depan=False)
                        data_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                        penutup_code = '2R' + val.internet_banking_code
                    elif val.kode_transaksi == 'LLG':
                        space_1 = self.format_number(cr, uid, ids, '', 36, ' ')
                        space_2 = self.format_number(cr, uid, ids, '', 35, ' ')
                        if not bank.bank.bank_indonesia_code or len(bank.bank.bank_indonesia_code) != 7:
                            raise osv.except_osv(('Perhatian !'), ("Kode BI di master bank %s harus 7 angka.")%(val.bank_account.bank.name_get().pop()[1]))
                        account_number = self.format_number(cr, uid, ids, account_number, 16, ' ', depan=False)
                        data_1 = self.format_number(cr, uid, ids, val.kode_transaksi, 7, ' ',depan=False)
                        data_1 += self.format_number(cr, uid, ids, bank.bank.bank_indonesia_code, 11, ' ',depan=False)
                        data_2 = self.format_number(cr, uid, ids, bank.bank.bic, 18, ' ',depan=False)
                        data_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                        penutup_code = '1R' + '888'
                    elif val.kode_transaksi == 'RTG':
                        space_1 = self.format_number(cr, uid, ids, '', 18, ' ')
                        space_2 = ''
                        account_number = self.format_number(cr, uid, ids, account_number, 16, ' ', depan=False)
                        data_1 = self.format_number(cr, uid, ids, '', 7, ' ')
                        data_1 += self.format_number(cr, uid, ids, bank.bank.bank_indonesia_code, 11, ' ',depan=False)
                        data_2 = self.format_number(cr, uid, ids, bank.bank.bic, 18, ' ',depan=False)
                        data_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                        penutup_code = '888'
                    # remarks_1 = self.format_number(cr, uid, ids, val.remarks_1, 18, ' ', depan=False)
                    # remarks_2 = self.format_number(cr, uid, ids, val.remarks_2, 18, ' ', depan=False)
                    # space_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                    remarks_1 = self.format_number(cr, uid, ids, val.remarks_1, 16, ' ', depan=False)
                    remarks_2 = self.format_number(cr, uid, ids, val.remarks_2, 20, ' ', depan=False)
                    space_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                    detail = '1' + str(account_number) + str(space_1) + '0000' + net_amount + pengirim + space_2 + data_1 + data_2 + data_3 + remarks_1 + remarks_2 + space_3 + penutup_code
                    result += detail
                    result += '\r\n'
        # kode = str(val.kode_transaksi) + str(tanggal_efektif) + str(randint(100,999))
        # kode = self.file_name
        nama = trx_obj[0].file_name.replace('.txt','') + '.txt'
        out = base64.encodestring(result)
        export = self.write(cr, uid, ids, {'data_file':out, 'name': nama,'total_record': val.total_record}, context=context)
        for voucher in trx_obj:
            voucher.write({'data_file':out, 'file_name': nama, 'state':'process'})
        return export

    def export(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        trx_obj = val.voucher_ids
        active_ids = context.get('active_ids', False) or False
        ib_id = self.pool.get('dym.ibanking').browse(cr,uid,active_ids)     
        # trx_obj = self.pool.get('account.voucher').browse(cr,uid,trx_id,context=context)
        if val.bank == 'is_bca':
            if ib_id:
                result = self.eksport_bca(cr, uid, ids, ib_id, context)
            # elif ib_id.transfer_ids:
            #     result = self.eksport_bca(cr, uid, ids, ib_id.transfer_ids, context)
                
        form_id  = 'Eksport Internet Banking'
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
            ("name", "=", form_id), 
            ("model", "=", 'internet.banking'),
        ])
        # return {
        #     'name' : _('Export File'),
        #     'view_type': 'form',
        #     'view_id' : view_id,
        #     'view_mode': 'form',
        #     'res_id': ids[0],
        #     'res_model': 'internet.banking',
        #     'type': 'ir.actions.act_window',
        #     'target': 'new',
        #     'nodestroy': True,
        #     'context': context
        # }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
