from openerp.osv import fields, osv, orm
import base64
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.tools.translate import _
from openerp import tools
from lxml import etree

class internet_banking(osv.osv_memory):
    _name = "bank.trf.request.ib"
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
        'advice_ids': fields.many2many('bank.trf.advice', 'internet_banking_advice_rel', 'internet_banking_id', 'advice_id', 'Bank Transfer Advice'),
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
            'company_code':bank_account.bank.company_code,
            'bank':bank_account.bank.bank,
            'account_number':account_number
        }
        return result

    def cek_payment(self, cr, uid, ids, context=None):
        payment = self.pool.get('bank.trf.advice').browse(cr, uid, ids, context=context)
        result = {
            'payment_method':False,
            'bank_account':False,
            'internet_banking_code':False,
            'company_code':False,
            'account_number':False,
            'bank':False,
        }
        for pay in payment:
            if result['payment_method'] != False and pay.payment_from_id != result['payment_method']:
                raise osv.except_osv(_('Warning!'), _("Data yang dieksport harus memiliki payment method yang sama!"))
            else:
                result['payment_method'] = pay.payment_from_id
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

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) < 1:
                raise osv.except_osv(_('Warning!'), _("Please select voucher from the list view!"))
        res = super(internet_banking, self).default_get(cr, uid, fields, context=context)
        payment_ids = context and context.get('active_ids', False) or False
        result = self.cek_payment(cr, uid, payment_ids, context=context)
        if 'payment_method' in fields:
            res.update({'payment_method':result['payment_method'].id})
        if 'payment_method_show' in fields:
            res.update({'payment_method_show':result['payment_method'].id})
        if 'bank_account' in fields and result['bank_account']:
            res.update({'bank_account':result['bank_account'].id})
        if 'internet_banking_code' in fields:
            res.update({'internet_banking_code':result['internet_banking_code']})
        if 'company_code' in fields:
            res.update({'company_code':result['company_code']})
        payment = self.pool.get('bank.trf.advice').browse(cr, uid, payment_ids, context=context)
        amount_total = 0
        vouchers = []
        for pay in payment:
            amount_total += pay.amount
            vouchers.append(pay.id)
        if 'advice_ids' in fields:
            res.update({'advice_ids':[(6, 0, vouchers)]})
        if 'amount_total' in fields:
            res.update({'amount_total':amount_total})
        if 'amount_total_show' in fields:
            res.update({'amount_total_show':amount_total})
        if 'account_number' in fields:
            res.update({'account_number':result['account_number']})
        if 'bank' in fields:
            res.update({'bank':result['bank']})
        if 'total_record' in fields:
            res.update({'total_record':len(context.get('active_ids'))})
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
        date = val.date
        bulan = str(date[5:7])
        tanggal = str(date[8:10])
        tahun = str(date[:4])
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
        total_record = self.format_number(cr, uid, ids, len(val.advice_ids), 5, '0')
        company_code = self.format_number(cr, uid, ids, val.company_code, 23, ' ',depan=False)
        if val.kode_transaksi == 'RTG':
            sisa_space = self.format_number(cr, uid, ids, '', 128, ' ')
        else:
            sisa_space = self.format_number(cr, uid, ids, '', 183, ' ')
        header = '0SP' + str(tanggal_efektif) + str(val.account_number) + ' ' + str(company_code) + '0000' + amount_total + total_record + val.kode_transaksi + sisa_space
        result += header
        result += '\r\n'
        for voucher in trx_obj:
            bank_account_destination = self.pool.get('res.partner.bank').search(cr, uid, [('journal_id','=',voucher.payment_to_id.id)])
            if not bank_account_destination:
                raise osv.except_osv(('Perhatian !'), ("Account bank untuk payment nomor %s belum di set.")%(voucher.number))
            if not bank_account_destination.partner_id:
                raise osv.except_osv(('Perhatian !'), ("Account owner untuk account bank %s belum di set.")%(voucher.payment_to_id.name_get().pop()[1]))
            if not bank_account_destination.bank.bic:
                raise osv.except_osv(('Perhatian !'), ("Bank identifier code untuk bank %s belum di set.")%(voucher.payment_to_id.name_get().pop()[1]))
            if val.kode_transaksi == 'BCA' and bank_account_destination.bank.bank != 'is_bca':
                raise osv.except_osv(('Perhatian !'), ("%s - Bank tujuan transfer %s bukan bank bca")%(voucher.number))

            account_number = ''
            for index in range(0,len(voucher.payment_to_id.acc_number)):
                if voucher.payment_to_id.acc_number[index].isdigit():
                    account_number += voucher.payment_to_id.acc_number[index]
            if len(account_number) != 10 or not account_number.isdigit() and val.kode_transaksi == 'BCA':
                raise osv.except_osv(('Perhatian !'), ("Rekening tujuan harus 10 digit."))
            if len(account_number) > 16 or not account_number.isdigit() and val.kode_transaksi != 'BCA':
                raise osv.except_osv(('Perhatian !'), ("Rekening tujuan tidak boleh lebih dari 16 digit."))
            net_amount = str("%.2f"%float(voucher.net_amount))
            net_amount = self.format_number(cr, uid, ids, net_amount, 16, '0')
            pengirim = self.format_number(cr, uid, ids, val.bank_account.partner_id.name, 35, ' ', depan=False).upper()
            if val.kode_transaksi == 'BCA':
                space_1 = self.format_number(cr, uid, ids, '', 42, ' ')
                space_2 = self.format_number(cr, uid, ids, '', 35, ' ')
                data_1 = self.format_number(cr, uid, ids, val.bank_account.bank.bic, 18, ' ',depan=False)
                data_2 = self.format_number(cr, uid, ids, voucher.payment_to_id.bank.bic, 18, ' ',depan=False)
                data_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                penutup_code = '2R' + val.internet_banking_code
            elif val.kode_transaksi == 'LLG':
                space_1 = self.format_number(cr, uid, ids, '', 36, ' ')
                space_2 = self.format_number(cr, uid, ids, '', 35, ' ')
                if not voucher.payment_to_id.bank.bank_indonesia_code or len(voucher.payment_to_id.bank.bank_indonesia_code) != 7:
                    raise osv.except_osv(('Perhatian !'), ("Kode BI di master bank %s harus 7 angka.")%(voucher.payment_to_id.bank.name_get().pop()[1]))
                account_number = self.format_number(cr, uid, ids, account_number, 16, ' ', depan=False)
                data_1 = self.format_number(cr, uid, ids, val.kode_transaksi, 7, ' ',depan=False)
                data_1 += self.format_number(cr, uid, ids, voucher.payment_to_id.bank.bank_indonesia_code, 11, ' ',depan=False)
                data_2 = self.format_number(cr, uid, ids, voucher.payment_to_id.bank.bic, 18, ' ',depan=False)
                data_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                penutup_code = '1R' + '888'
            elif val.kode_transaksi == 'RTG':
                space_1 = self.format_number(cr, uid, ids, '', 18, ' ')
                space_2 = ''
                account_number = self.format_number(cr, uid, ids, account_number, 16, ' ', depan=False)
                data_1 = self.format_number(cr, uid, ids, '', 7, ' ')
                data_1 += self.format_number(cr, uid, ids, voucher.payment_to_id.bank.bank_indonesia_code, 11, ' ',depan=False)
                data_2 = self.format_number(cr, uid, ids, voucher.payment_to_id.bank.bic, 18, ' ',depan=False)
                data_3 = self.format_number(cr, uid, ids, '', 18, ' ')
                penutup_code = '888'
            remarks_1 = self.format_number(cr, uid, ids, val.remarks_1, 18, ' ', depan=False)
            remarks_2 = self.format_number(cr, uid, ids, val.remarks_2, 18, ' ', depan=False)
            space_3 = self.format_number(cr, uid, ids, '', 18, ' ')
            detail = '1' + str(account_number) + str(space_1) + '0000' + net_amount + pengirim + space_2 + data_1 + data_2 + data_3 + remarks_1 + remarks_2 + space_3 + penutup_code
            result += detail
            result += '\r\n'
        kode = str(val.kode_transaksi) +'-'+ str(tanggal_efektif)
        nama = kode + '.txt'
        out = base64.encodestring(result)
        export = self.write(cr, uid, ids, {'data_file':out, 'name': nama,' total_record': len(val.advice_ids)}, context=context)
        return export

    def export(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        trx_obj = val.advice_ids
        if val.bank == 'is_bca' :
            result = self.eksport_bca(cr, uid, ids, trx_obj, context)
        form_id  = 'Eksport Internet Banking'
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[("name", "=", form_id),("model", "=", 'bank.trf.request.ib')])
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'bank.trf.request.ib',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
