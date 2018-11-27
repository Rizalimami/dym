from openerp.osv import fields, osv, orm
import base64
from openerp import SUPERUSER_ID
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.tools.translate import _
from openerp import tools
from lxml import etree
import re

class wizard_efaktur(osv.osv_memory):
    _name = "wizard.efaktur"
    _description = "Export E-Faktur"

    _columns = {
        'in_out':fields.selection([('in','Masukan'),('out','Keluaran')], 'Pajak Masukan / Keluaran'),
        'faktur_ids': fields.many2many('dym.faktur.pajak.out', 'wizard_efaktur_fp_rel', 'wizard_id', 'fp_id', 'Faktur Pajak'),
        'data_file': fields.binary('File'),
        'name': fields.char('File Name'),
    }

    # def get_data_master_bank(self, cr, uid, ids, bank_account_id, context=None):
    #     bank_account = self.pool.get('res.partner.bank').browse(cr, uid, bank_account_id)
    #     if bank_account.bank.internet_banking == False:
    #         raise osv.except_osv(_('Warning!'), _("Bank %s tidak memiliki data internet banking!")%(bank_account.bank.name))
    #     account_number = ''
    #     for index in range(0,len(bank_account.acc_number)):
    #         if bank_account.acc_number[index].isdigit():
    #             account_number += bank_account.acc_number[index]
    #     result = {
    #         'internet_banking_code':bank_account.bank.internet_banking_code,
    #         'company_code':bank_account.bank.company_code,
    #         'bank':bank_account.bank.bank,
    #         'account_number':account_number
    #     }
    #     return result

    # def cek_payment(self, cr, uid, ids, context=None):
    #     payment = self.pool.get('account.voucher').browse(cr, uid, ids, context=context)
    #     result = {
    #         'payment_method':False,
    #         'bank_account':False,
    #         'internet_banking_code':False,
    #         'company_code':False,
    #         'account_number':False,
    #         'bank':False,
    #     }
    #     for pay in payment:
    #         if result['payment_method'] != False and pay.journal_id != result['payment_method']:
    #             raise osv.except_osv(_('Warning!'), _("Data yang dieksport harus memiliki payment method yang sama!"))
    #         else:
    #             result['payment_method'] = pay.journal_id
    #     bank_account = self.pool.get('res.partner.bank').search(cr, uid, [('journal_id','=',result['payment_method'].id)])
    #     if not bank_account:
    #         raise osv.except_osv(_('Warning!'), _("Tidak ditemukan bank account dengan jurnal %s")%(result['payment_method'].name))
    #     elif len(bank_account) == 1:
    #         result['bank_account'] = self.pool.get('res.partner.bank').browse(cr, uid, bank_account)
    #         data_master_bank = self.get_data_master_bank(cr, uid, ids, result['bank_account'].id)
    #         result['internet_banking_code'] = data_master_bank['internet_banking_code']
    #         result['company_code'] = data_master_bank['company_code']
    #         result['account_number'] = data_master_bank['account_number']
    #         result['bank'] = data_master_bank['bank']
    #     return result

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) < 1:
                raise osv.except_osv(_('Warning!'), _("Please select faktur from the list view!"))
        res = super(wizard_efaktur, self).default_get(cr, uid, fields, context=context)
        faktur_ids = context and context.get('active_ids', False) or False
        res.update({'faktur_ids':[(6, 0, faktur_ids)]})
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
    
    def faktur_pajak_out_row(self, cr, uid, object, val, faktur):
        result = ''
        total_dpp = 0
        total_ppn = 0
        referensi = ""
        if object == 'dealer.sale.order':
            for line in val.dealer_sale_order_line:
                kode_objek = line.template_id.name
                kode_objek = kode_objek.split(' ')[0]
                nama = line.template_id.default_code or line.template_id.description
                harga_satuan = line.price_unit
                harga_satuan = line.tax_id.compute_all(harga_satuan, 1, product=line.product_id, partner=val.partner_id)['total']
                harga_satuan = round(harga_satuan,0)
                jumlah_barang = line.product_qty
                harga_total = harga_satuan * jumlah_barang
                harga_total = round(harga_total,0)
                diskon = line.discount_total
                diskon = line.tax_id.compute_all(diskon, 1, product=line.product_id, partner=val.partner_id)['total']
                diskon = round(round(diskon,0),1)
                dpp = harga_total - diskon
                dpp = round(dpp,0)
                total_dpp += dpp
                dpp = str(dpp).split('.')[0]
                price = (line.price_unit * line.product_qty) - line.discount_total
                ppn = 0
                for tax in line.tax_id.compute_all(price, 1, product=line.product_id, partner=val.partner_id)['taxes']:
                    ppn += tax['amount']
                tarif_ppnbm = 0
                ppnbm = 0
                ppn = round(ppn,0)
                total_ppn += ppn
                ppn = str(ppn).split('.')[0]
                jumlah_barang = round(jumlah_barang,1)
                harga_satuan = str(harga_satuan).split('.')[0]
                harga_total = str(harga_total).split('.')[0]
                if not faktur.pajak_gabungan:
                    referensi = val.name
                result += 'OF;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;;;;;;;;' % (kode_objek, nama,harga_satuan,jumlah_barang,harga_total,diskon,dpp,ppn,tarif_ppnbm,ppnbm)
                result += '\n'
        elif object == 'dym.work.order' :
            for line in val.work_lines:
                kode_objek = line.product_id.product_tmpl_id.name
                kode_objek = kode_objek.split(' ')[0]
                nama = line.product_id.product_tmpl_id.default_code or line.product_id.product_tmpl_id.description
                harga_satuan = line.price_unit
                harga_satuan = line.tax_id.compute_all(harga_satuan, 1, product=line.product_id, partner=val.customer_id)['total']
                harga_satuan = round(harga_satuan,0)
                jumlah_barang = line.product_qty
                harga_total = harga_satuan * jumlah_barang
                harga_total = round(harga_total,0)
                diskon = line.discount + line.discount_program + line.discount_bundle
                diskon = line.tax_id.compute_all(diskon, 1, product=line.product_id, partner=val.customer_id)['total']
                diskon = round(round(diskon,0),1)
                dpp = harga_total - diskon
                dpp = round(dpp,0)
                total_dpp += dpp
                dpp = str(dpp).split('.')[0]
                price = (line.price_unit * line.product_qty) - (line.discount + line.discount_program + line.discount_bundle)
                ppn = 0
                for tax in line.tax_id.compute_all(price, 1, product=line.product_id, partner=val.customer_id)['taxes']:
                    ppn += tax['amount']
                tarif_ppnbm = 0
                ppnbm = 0
                ppn = round(ppn,0)
                total_ppn += ppn
                ppn = str(ppn).split('.')[0]
                jumlah_barang = round(jumlah_barang,1)
                harga_satuan = str(harga_satuan).split('.')[0]
                harga_total = str(harga_total).split('.')[0]
                if not faktur.pajak_gabungan:
                    referensi = val.name
                result += 'OF;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;;;;;;;;' % (kode_objek, nama,harga_satuan,jumlah_barang,harga_total,diskon,dpp,ppn,tarif_ppnbm,ppnbm)
                result += '\n'
        elif object == 'account.voucher' :
            for line in val.line_ids:
                kode_objek = ''
                nama = line.name
                harga_satuan = line.amount
                harga_satuan = val.tax_id.compute_all(harga_satuan, 1, partner=val.partner_id)['total']
                harga_satuan = round(harga_satuan,0)
                jumlah_barang = 1
                harga_total = harga_satuan * jumlah_barang
                harga_total = round(harga_total,0)
                diskon = 0
                diskon = round(round(diskon,0),1)
                dpp = harga_total - diskon
                dpp = round(dpp,0)
                total_dpp += dpp
                dpp = str(dpp).split('.')[0]
                price = line.amount
                ppn = 0
                for tax in val.tax_id.compute_all(price, 1, partner=val.partner_id)['taxes']:
                    ppn += tax['amount']
                tarif_ppnbm = 0
                ppnbm = 0
                ppn = round(ppn,0)
                total_ppn += ppn
                ppn = str(ppn).split('.')[0]
                jumlah_barang = round(jumlah_barang,1)
                harga_satuan = str(harga_satuan).split('.')[0]
                harga_total = str(harga_total).split('.')[0]
                if not faktur.pajak_gabungan:
                    referensi = val.number
                result += 'OF;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;;;;;;;;' % (kode_objek, nama,harga_satuan,jumlah_barang,harga_total,diskon,dpp,ppn,tarif_ppnbm,ppnbm)
                result += '\n'
        elif object == 'sale.order' :
            for line in val.order_line:
                kode_objek = line.product_id.product_tmpl_id.name
                kode_objek = kode_objek.split(' ')[0]
                nama = line.product_id.product_tmpl_id.default_code or line.product_id.product_tmpl_id.description
                harga_satuan = line.price_unit
                harga_satuan = line.tax_id.compute_all(harga_satuan, 1, product=line.product_id, partner=val.partner_id)['total']
                harga_satuan = round(harga_satuan,0)
                jumlah_barang = line.product_uom_qty
                harga_total = harga_satuan * jumlah_barang
                harga_total = round(harga_total,0)
                diskon = line.discount_show + line.discount_program + line.discount_lain + line.discount_cash
                diskon = line.tax_id.compute_all(diskon, 1, product=line.product_id, partner=val.partner_id)['total']
                diskon = round(round(diskon,0),1)
                dpp = harga_total - diskon
                dpp = round(dpp,0)
                total_dpp += dpp
                dpp = str(dpp).split('.')[0]
                price = (line.price_unit * line.product_uom_qty) - (line.discount_show + line.discount_program + line.discount_lain + line.discount_cash)
                ppn = 0
                for tax in line.tax_id.compute_all(price, 1, product=line.product_id, partner=val.partner_id)['taxes']:
                    ppn += tax['amount']
                tarif_ppnbm = 0
                ppnbm = 0
                ppn = round(ppn,0)
                total_ppn += ppn
                ppn = str(ppn).split('.')[0]
                jumlah_barang = round(jumlah_barang,1)
                harga_satuan = str(harga_satuan).split('.')[0]
                harga_total = str(harga_total).split('.')[0]
                if not faktur.pajak_gabungan:
                    referensi = val.name
                result += 'OF;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;;;;;;;;' % (kode_objek, nama,harga_satuan,jumlah_barang,harga_total,diskon,dpp,ppn,tarif_ppnbm,ppnbm)
                result += '\n'
        elif object == 'dym.asset.disposal' :
            kode_objek = ''
            nama = ', '.join(val.asset_disposal_line.mapped('asset_id.name'))
            harga_satuan = val.amount_untaxed
            harga_satuan = val.taxes_ids.compute_all(harga_satuan, 1, partner=val.partner_id)['total']
            harga_satuan = round(harga_satuan,0)
            jumlah_barang = 1
            harga_total = harga_satuan * jumlah_barang
            harga_total = round(harga_total,0)
            diskon = val.discount
            diskon = round(round(diskon,0),1)
            dpp = harga_total - diskon
            dpp = round(dpp,0)
            total_dpp += dpp
            dpp = str(dpp).split('.')[0]
            price = val.amount_net_price
            ppn = 0
            for tax in val.taxes_ids.compute_all(price, 1, partner=val.partner_id)['taxes']:
                ppn += tax['amount']
            tarif_ppnbm = 0
            ppnbm = 0
            ppn = round(ppn,0)
            total_ppn += ppn
            ppn = str(ppn).split('.')[0]
            jumlah_barang = round(jumlah_barang,1)
            harga_satuan = str(harga_satuan).split('.')[0]
            harga_total = str(harga_total).split('.')[0]
            if not faktur.pajak_gabungan:
                referensi = val.name
            result += 'OF;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;;;;;;;;' % (kode_objek, nama,harga_satuan,jumlah_barang,harga_total,diskon,dpp,ppn,tarif_ppnbm,ppnbm)
            result += '\n'
        elif object == 'account.invoice' :
            for line in val.invoice_line:
                kode_objek = line.product_id.product_tmpl_id.name or ''
                kode_objek = kode_objek.split(' ')[0]
                nama = line.name
                harga_satuan = line.price_unit
                harga_satuan = line.invoice_line_tax_id.compute_all(harga_satuan, 1, partner=val.partner_id)['total']
                harga_satuan = round(harga_satuan,0)
                jumlah_barang = line.quantity
                harga_total = harga_satuan * jumlah_barang
                harga_total = round(harga_total,0)
                diskon = line.discount_amount + line.discount_program + line.discount_lain + line.discount_cash
                diskon = round(round(diskon,0),1)
                dpp = harga_total - diskon
                dpp = round(dpp,0)
                total_dpp += dpp
                dpp = str(dpp).split('.')[0]
                price = (line.price_unit * line.quantity) - (line.discount_amount + line.discount_program + line.discount_lain + line.discount_cash)
                ppn = 0
                for tax in line.invoice_line_tax_id.compute_all(price, 1, partner=val.partner_id)['taxes']['amount']:
                    ppn += tax['amount']
                ppn = round(ppn,0)
                tarif_ppnbm = 0
                ppnbm = 0
                total_ppn += ppn
                ppn = str(ppn).split('.')[0]
                jumlah_barang = round(jumlah_barang,1)
                harga_satuan = str(harga_satuan).split('.')[0]
                harga_total = str(harga_total).split('.')[0]
                if not faktur.pajak_gabungan:
                    referensi = val.number
                result += 'OF;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;;;;;;;;' % (kode_objek, nama,harga_satuan,jumlah_barang,harga_total,diskon,dpp,ppn,tarif_ppnbm,ppnbm)
                result += '\n'   
        elif object == 'dym.faktur.pajak.gabungan' :
            for line in val.pajak_gabungan_line:
                if line.model in ('account.invoice','account.voucher'):
                    val_id = self.pool.get(line.model).search(cr, SUPERUSER_ID, [('number','=',line.name)])
                else:
                    val_id = self.pool.get(line.model).search(cr, SUPERUSER_ID, [('name','=',line.name)])
                val = self.pool.get(line.model).browse(cr, SUPERUSER_ID, val_id)
                for row in self.faktur_pajak_out_row(cr, uid, line.model, val, faktur):
                    datas_1 = str(row).split('\n')
                    for data in datas_1:
                        dt = str(data).split(';')
                        if len(dt) != 1:
                            total_dpp += int(dt[7])
                            total_ppn += int(dt[8])
                    if len(str(row).split(';')) != 1:
                        result += row
        elif object == 'dym.faktur.pajak.other' :
            kode_objek = ''
            nama = val.description
            harga_satuan = val.untaxed_amount
            harga_satuan = round(harga_satuan,0)
            jumlah_barang = 1
            harga_total = harga_satuan * jumlah_barang
            harga_total = round(harga_total,0)
            diskon = 0
            diskon = round(round(diskon,0),1)
            dpp = harga_total - diskon
            dpp = round(dpp,0)
            total_dpp += dpp
            dpp = str(dpp).split('.')[0]
            ppn = val.tax_amount
            ppn = round(ppn,0)
            tarif_ppnbm = 0
            ppnbm = 0
            total_ppn += ppn
            ppn = str(ppn).split('.')[0]
            jumlah_barang = round(jumlah_barang,1)
            harga_satuan = str(harga_satuan).split('.')[0]
            harga_total = str(harga_total).split('.')[0]
            result += 'OF;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;;;;;;;;' % (kode_objek, nama,harga_satuan,jumlah_barang,harga_total,diskon,dpp,ppn,tarif_ppnbm,ppnbm)
            result += '\n'
        total_dpp = str(total_dpp).split('.')[0]
        total_ppn = str(total_ppn).split('.')[0]
        return result, total_dpp, total_ppn, referensi

    def export_faktur_out(self, cr, uid, ids, trx_obj, context=None):
        work_order = self.pool.get('dym.work.order')
        other_receivable = self.pool.get('account.voucher')
        sales_order = self.pool.get('dealer.sale.order')
        sales_order_md = self.pool.get('sale.order')
        asset_disposal = self.pool.get('dym.asset.disposal')
        account_invoice = self.pool.get('account.invoice')
        val = self.browse(cr, uid, ids)[0]
        result = 'FK;KD_JENIS_TRANSAKSI;FG_PENGGANTI;NOMOR_FAKTUR;MASA_PAJAK;TAHUN_PAJAK;TANGGAL_FAKTUR;NPWP;NAMA;ALAMAT_LENGKAP;JUMLAH_DPP;JUMLAH_PPN;JUMLAH_PPNBM;ID_KETERANGAN_TAMBAHAN;FG_UANG_MUKA;UANG_MUKA_DPP;UANG_MUKA_PPN;UANG_MUKA_PPNBM;REFERENSI'
        result += '\n'
        result += 'LT;NPWP;NAMA;JALAN;BLOK;NOMOR;RT;RW;KECAMATAN;KELURAHAN;KABUPATEN;PROPINSI;KODE_POS;NOMOR_TELEPON;;;;;'
        result += '\n'
        result += 'OF;KODE_OBJEK;NAMA;HARGA_SATUAN;JUMLAH_BARANG;HARGA_TOTAL;DISKON;DPP;PPN;TARIF_PPNBM;PPNBM;;;;;;;;'
        result += '\n'
        for faktur in trx_obj:
            if faktur.in_out != 'out':
                raise osv.except_osv(('Perhatian !'), ("Faktur %s bukan merupakan faktur keluaran.")%(faktur.name))
            object = faktur.model_id.model
            no_faktur = re.sub("\D", "", faktur.name)
            no_faktur = no_faktur[-13:] if len(no_faktur) > 13 else no_faktur
            tgl_terbit = datetime.date(datetime.strptime(faktur.tgl_terbit, '%Y-%m-%d')) if faktur.tgl_terbit else ''
            tgl_faktur = datetime.date(datetime.strptime(faktur.date, '%Y-%m-%d'))
            npwp_cust = re.sub("\D", "", faktur.partner_id.npwp) if faktur.partner_id.npwp else '000000000000000'
            rt_rw = ''
            if faktur.partner_id.rt and faktur.partner_id.rw:
                rt_rw = 'RT. '+str(faktur.partner_id.rt) + 'RW. '+str(faktur.partner_id.kelurahan)
            alamat_cust = '%s %s %s %s' % (faktur.partner_id.street, rt_rw, faktur.partner_id.kelurahan or '', faktur.partner_id.kecamatan or '')
            total_ppnbm = 0
            fg_uang_muka = 0
            uang_muka_dpp = 0
            uang_muka_ppn = 0
            uang_muka_ppnbm = 0
            val = self.pool.get(object).browse(cr, SUPERUSER_ID, faktur.transaction_id)
            fp_content, total_dpp, total_ppn, referensi = self.faktur_pajak_out_row(cr, uid, object, val, faktur)
            fp_header = ''
            fp_header += 'FK;01;0;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;;%s;%s;%s;%s;%s' % (no_faktur,tgl_faktur.month if tgl_faktur else tgl_terbit.month,faktur.thn_penggunaan if faktur.thn_penggunaan else tgl_faktur.year,tgl_faktur.strftime('%d/%m/%Y'),npwp_cust,faktur.partner_id.name.upper(),alamat_cust.upper(),total_dpp,total_ppn,total_ppnbm,fg_uang_muka,uang_muka_dpp,uang_muka_ppn,uang_muka_ppnbm,referensi)
            fp_header += '\n'
            result += fp_header+fp_content
            faktur.write({'export_efaktur':True})
        kode = 'PAJAK KELUARAN'
        nama = kode + '.csv'
        out = base64.encodestring(result)
        export = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)
        return export

    def export_faktur_in(self, cr, uid, ids, trx_obj, context=None):
        work_order = self.pool.get('dym.work.order')
        other_receivable = self.pool.get('account.voucher')
        sales_order = self.pool.get('dealer.sale.order')
        sales_order_md = self.pool.get('sale.order')
        asset_disposal = self.pool.get('dym.asset.disposal')
        account_invoice = self.pool.get('account.invoice')
        val = self.browse(cr, uid, ids)[0]
        result = 'FM;KD_JENIS_TRANSAKSI;FG_PENGGANTI;NOMOR_FAKTUR;MASA_PAJAK;TAHUN_PAJAK;TANGGAL_FAKTUR;NPWP;NAMA;ALAMAT_LENGKAP;JUMLAH_DPP;JUMLAH_PPN;JUMLAH_PPNBM;IS_CREDITABLE'
        result += '\n'
        for faktur in trx_obj:
            if faktur.in_out != 'in':
                raise osv.except_osv(('Perhatian !'), ("Faktur %s bukan merupakan faktur masukan.")%(faktur.name))
            object = faktur.model_id.model
            no_faktur = re.sub("\D", "", faktur.name)
            no_faktur = no_faktur[-13:] if len(no_faktur) > 13 else no_faktur
            tgl_terbit = datetime.date(datetime.strptime(faktur.tgl_terbit, '%Y-%m-%d')) if faktur.tgl_terbit else ''
            tgl_faktur = datetime.date(datetime.strptime(faktur.date, '%Y-%m-%d'))
            npwp_cust = re.sub("\D", "", faktur.partner_id.npwp) if faktur.partner_id.npwp else '000000000000000'
            rt_rw = ''
            if faktur.partner_id.rt and faktur.partner_id.rw:
                rt_rw = 'RT. '+str(faktur.partner_id.rt) + 'RW. '+str(faktur.partner_id.kelurahan)
            alamat_cust = '%s %s %s %s' % (faktur.partner_id.street, rt_rw, faktur.partner_id.kelurahan or '', faktur.partner_id.kecamatan or '')
            total_ppnbm = 0
            is_creditable = 0
            total_dpp = round(faktur.untaxed_amount,0)
            total_dpp = str(total_dpp).split('.')[0]
            total_ppn = round(round(faktur.tax_amount,0),1)
            total_ppn = str(total_ppn).split('.')[0]
            result += 'FM;01;0;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s' % (no_faktur,tgl_faktur.month if tgl_faktur else tgl_terbit.month,faktur.thn_penggunaan if faktur.thn_penggunaan else tgl_faktur.year,tgl_faktur.strftime('%d/%m/%Y'),npwp_cust,faktur.partner_id.name.upper(),alamat_cust.upper(),total_dpp,total_ppn,total_ppnbm,is_creditable)
            result += '\n'
            faktur.write({'export_efaktur':True})
        kode = 'PAJAK MASUKAN'
        nama = kode + '.csv'
        out = base64.encodestring(result)
        export = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)
        return export

    def export(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        trx_obj = val.faktur_ids
        if val.in_out == 'out' :
            result = self.export_faktur_out(cr, uid, ids, trx_obj, context)
        if val.in_out == 'in' :
            result = self.export_faktur_in(cr, uid, ids, trx_obj, context)
        form_id  = 'Eksport Faktur Pajak'
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                                                             ("name", "=", form_id), 
                                                             ("model", "=", 'wizard.efaktur'),
                                                             ])
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'wizard.efaktur',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
