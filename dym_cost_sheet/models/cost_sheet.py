from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class dym_biaya_lain(models.Model):
    _name = "dym.biaya.lain"

    name = fields.Char(string='Nama Biaya')
    account_id = fields.Many2one('account.account', string='Account')
    value = fields.Float(string='Nilai Biaya')

class dym_cost_sheet_dealer_spk(models.Model):
    _inherit = "dealer.spk"

    @api.multi
    def _get_harga_pricelist(self, line, pricelist):
        date_order_str = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        if self.confirm_date:
            date_order_str = self.confirm_date
        price = pricelist.price_get(line.product_id.id, line.product_qty, context={'date': date_order_str})[pricelist.id]
        if price != False:
            return price
        else:
            return 0

    @api.multi
    def _get_harga_bbn_detail_on_date(self, line):
        date_order_str = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        if self.confirm_date:
            date_order_str = self.confirm_date
        biro_jasa_def = self.env['dym.harga.birojasa'].search([('branch_id','=',self.branch_id.id),('default_birojasa','=',True)])
        if biro_jasa_def:
            birojasa_id = biro_jasa_def.birojasa_id.id
            plat = 'H'
            city =  line.partner_stnk_id.city_tab_id.id
            if line.partner_stnk_id.sama == True:
                city =  line.partner_stnk_id.city_id.id
            product_template_id = line.product_id.product_tmpl_id.id
            branch_id = self.branch_id.id

            if not birojasa_id:
                return 0
            birojasa = self.env['dym.harga.birojasa']
            harga_birojasa = birojasa.search([
                                             ('birojasa_id','=',birojasa_id),
                                             ('branch_id','=',branch_id)
                                             ])
            if not harga_birojasa :
                return 0            
            bbn_search = self.env['dym.harga.bbn'].search([
                                                           ('id','=',harga_birojasa.harga_bbn_id.id)
                                                           ])
            if not bbn_search :
                return 0                         
            pricelist_harga_bbn = self.env['dym.harga.bbn.line'].search([
                    ('bbn_id','=',bbn_search.id),                                                                    
                    ('tipe_plat','=',plat),
                    ('active','=',True),
                    ('start_date','<=',date_order_str),
                    ('end_date','>=',date_order_str),
                ])
            if not pricelist_harga_bbn:
                return 0
            for pricelist_bbn in pricelist_harga_bbn:
                bbn_detail = self.env['dym.harga.bbn.line.detail'].search([
                        ('harga_bbn_line_id','=',pricelist_bbn.id),
                        ('product_template_id','=',product_template_id),
                        ('city_id','=',city)
                    ])
                
                if bbn_detail:
                    return bbn_detail[0].total
        return 0

    @api.multi
    def _get_insentif_finco_value_on_date(self):
        if self.is_credit == False:
            return 0
        date_order_str = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        if self.confirm_date:
            date_order_str = self.confirm_date
        branch_id = self.branch_id.id
        finco_id = self.finco_id.id
        if not finco_id or not branch_id:
            return 0
        pricelist_incentives = self.env['dym.incentive.finco.line'].search([
                ('partner_id','=',finco_id),
                ('active','=',True),
                ('start_date','<=',date_order_str),
                ('end_date','>=',date_order_str),
            ])
        if not pricelist_incentives:
            return 0

        incentive_value = self.env['dym.incentive.finco.line.detail'].search([
                ('incentive_finco_line_id','=',pricelist_incentives[0].id),
                ('branch_id','=',branch_id),
            ])
        if incentive_value:
            return incentive_value[0]['incentive']
        return 0

    @api.one
    @api.depends('partner_id','is_credit','dealer_spk_line','confirm_date','branch_id','finco_id')
    def _get_costsheet(self):
        alamat = ''
        if self.partner_id.street:
            alamat += self.partner_id.street
        if self.partner_id.street2:
            alamat += ' ' + self.partner_id.street2
        if self.partner_id.rt:
            alamat += ' RT' + self.partner_id.rt
        if self.partner_id.rw:
            alamat += ' RW' + self.partner_id.rw
        alamat += '\n'
        if self.partner_id.kelurahan:
            alamat += self.partner_id.kelurahan + ', '
        if self.partner_id.kecamatan:
            alamat += self.partner_id.kecamatan + ', '
        elif self.partner_id.kecamatan_id:
            alamat += self.partner_id.kecamatan_id.name + ', '
        if self.partner_id.city_id:
            alamat += self.partner_id.city_id.name + ', '
        alamat = alamat[:-2]
        alamat += '\n'
        if self.partner_id.state_id:
            alamat += self.partner_id.state_id.name + ', '
        alamat += ' INDONESIA'
        if self.partner_id.zip_id:
            alamat += ' - ' + self.partner_id.zip_id.zip
        self.alamat = alamat
        tunai_kredit = 'Tunai'
        if self.is_credit:
            tunai_kredit = 'Kredit'
        self.tunai_kredit = tunai_kredit
        tipe_motor = ''
        product_line_ids = []
        total_harga_jual = 0
        total_harga_beli = 0
        total_harga_bbn = 0
        total_harga_birojasa = 0
        total_biaya_insentif = 0
        for line in self.dealer_spk_line:
            if line.product_id.id:
                if line.product_id.id not in product_line_ids:
                    product_line_ids.append(line.product_id.id)
                    tipe_motor += line.product_id.name + ', '
                total_harga_jual += self._get_harga_pricelist(line, self.branch_id.pricelist_unit_sales_id) * line.product_qty
                total_harga_beli += self._get_harga_pricelist(line, self.branch_id.pricelist_unit_purchase_id) * line.product_qty
                total_harga_bbn += self._get_harga_pricelist(line, self.branch_id.pricelist_bbn_hitam_id) * line.product_qty
                total_harga_birojasa += self._get_harga_bbn_detail_on_date(line) * line.product_qty
                total_biaya_insentif += self._get_insentif_finco_value_on_date() * line.product_qty
        self.tipe_motor = tipe_motor[:-2]
        self.harga_jual_motor = total_harga_jual / 1.1
        self.discount_konsumen = sum(line.discount_po for line in self.dealer_spk_line) 
        self.netto_jual = self.harga_jual_motor - (self.discount_konsumen/1.1 + self.discount_prog_intern/1.1)
        self.ppn_keluaran = (self.harga_jual_motor - (self.discount_konsumen/1.1 + self.discount_prog_intern/1.1 + self.discount_prog_extern/1.1)) * 10/100
        self.harga_standar = total_harga_beli
        self.ppn_masukan = self.harga_standar * 10/100
        self.selisih_penjualan = self.netto_jual - self.harga_standar
        self.selisih_ppn = self.ppn_keluaran - self.ppn_masukan
        self.harga_stnk_md = total_harga_bbn
        self.harga_stnk_birojasa = total_harga_birojasa
        self.selisih_stnk = (self.harga_stnk_md + self.tambahan_pendapatan_bbn) - (self.harga_stnk_birojasa + self.tambahan_biaya_bbn)
        self.profit_penjualan = self.selisih_penjualan + self.selisih_ppn + self.selisih_stnk - self.biaya_broker
        self.insentif_leasing = total_biaya_insentif
        self.dym_biaya_lain = self.env['dym.biaya.lain'].search([]).ids
        self.biaya_lain = sum(line.value for line in self.dym_biaya_lain) 
        self.profit_lain = (self.subsidi_leasing_oi + self.insentif_leasing) - self.biaya_lain
        self.net_profit = self.profit_penjualan + self.profit_lain

    nomor_faktur_jual = fields.Char(related="name", string='Nomor Faktur Jual')
    tanggal_faktur_jual = fields.Date(related="date_order", string='Tanggal Faktur Jual')
    nama_konsumen = fields.Many2one(related="partner_id",string='Nama Konsumen')
    alamat = fields.Text(string='Alamat', compute='_get_costsheet', store=True)
    tipe_motor = fields.Char(string='Tipe Motor', compute='_get_costsheet', store=True)
    tunai_kredit = fields.Char(string='Tunai / Kredit', compute='_get_costsheet', store=True)
    marketing_counter = fields.Many2one(related="employee_id", string='Marketing / Counter')
    harga_jual_motor = fields.Float(string='Harga Jual DPP (Exc. BBN dan PPN)', compute='_get_costsheet', store=True)
    discount_konsumen = fields.Float(string='Discount Konsumen', compute='_get_costsheet', store=True)
    discount_prog_intern = fields.Float(string='Discount Prog Intern')
    discount_prog_extern = fields.Float(string='Discount Prog Extern')
    netto_jual = fields.Float(string='Harga Jual Netto (Exc.PPN)', compute='_get_costsheet', store=True)
    ppn_keluaran = fields.Float(string='PPN Keluaran (PK)', compute='_get_costsheet', store=True)
    harga_standar = fields.Float(string='Harga Beli Standar (DPP)', compute='_get_costsheet', store=True)
    ppn_masukan = fields.Float(string='PPN Masukan (PM)', compute='_get_costsheet', store=True)
    selisih_penjualan = fields.Float(string='GP Unit', compute='_get_costsheet', store=True)
    selisih_ppn = fields.Float(string='Selisih PPN (SPN)', compute='_get_costsheet', store=True)
    harga_stnk_md = fields.Float(string='Harga Jual STNK', compute='_get_costsheet', store=True)
    harga_stnk_birojasa = fields.Float(string='Beban STNK Biro Jasa', compute='_get_costsheet', store=True)
    tambahan_pendapatan_bbn = fields.Float(string='Tambahan Pendapatan BBN')
    tambahan_biaya_bbn = fields.Float(string='Tambahan Biaya BBN')
    selisih_stnk = fields.Float(string='Margin BBN', compute='_get_costsheet', store=True)
    biaya_broker = fields.Float(string='Mediator')
    profit_penjualan = fields.Float(string='Laba Penjualan (GP OTR)', compute='_get_costsheet', store=True)
    subsidi_leasing_oi = fields.Float(string='Subsidi Leasing')
    insentif_leasing = fields.Float(string='Insentif Leasing', compute='_get_costsheet', store=True)
    biaya_lain = fields.Float(string='Biaya Lain-lain', compute='_get_costsheet', store=True)
    dym_biaya_lain = fields.Many2many('dym.biaya.lain', string='Biaya Lain', compute='_get_costsheet')
    profit_lain = fields.Float(string='Other Income (Net)', compute='_get_costsheet', store=True)
    net_profit = fields.Float(string='Laba Operasi', compute='_get_costsheet', store=True)


class dym_cost_sheet_dealer_dso(models.Model):
    _inherit = "dealer.sale.order"

    @api.multi
    def _get_harga_pricelist(self, line, pricelist):
        date_order_str = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        if self.confirm_date:
            date_order_str = self.confirm_date
        price = pricelist.price_get(line.product_id.id, line.product_qty, context={'date': date_order_str})[pricelist.id]
        if price != False:
            return price
        else:
            return 0

    @api.multi
    def _get_harga_bbn_detail_on_date(self, line):
        date_order_str = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        if self.confirm_date:
            date_order_str = self.confirm_date
        biro_jasa_def = line.biro_jasa_id or self.env['dym.harga.birojasa'].search([('branch_id','=',self.branch_id.id),('default_birojasa','=',True)]).birojasa_id
        if biro_jasa_def:
            birojasa_id = biro_jasa_def.id
            plat = line.plat
            city =  line.partner_stnk_id.city_tab_id.id
            if line.partner_stnk_id.sama == True:
                city =  line.partner_stnk_id.city_id.id
            product_template_id = line.product_id.product_tmpl_id.id
            branch_id = self.branch_id.id

            if not birojasa_id:
                return 0
            birojasa = self.env['dym.harga.birojasa']
            harga_birojasa = birojasa.search([
                                             ('birojasa_id','=',birojasa_id),
                                             ('branch_id','=',branch_id)
                                             ])
            if not harga_birojasa :
                return 0            
            bbn_search = self.env['dym.harga.bbn'].search([
                                                           ('id','=',harga_birojasa.harga_bbn_id.id)
                                                           ])
            if not bbn_search :
                return 0                         
            pricelist_harga_bbn = self.env['dym.harga.bbn.line'].search([
                    ('bbn_id','=',bbn_search.id),                                                                    
                    ('tipe_plat','=',plat),
                    ('active','=',True),
                    ('start_date','<=',date_order_str),
                    ('end_date','>=',date_order_str),
                ])
            if not pricelist_harga_bbn:
                return 0
            for pricelist_bbn in pricelist_harga_bbn:
                bbn_detail = self.env['dym.harga.bbn.line.detail'].search([
                        ('harga_bbn_line_id','=',pricelist_bbn.id),
                        ('product_template_id','=',product_template_id),
                        ('city_id','=',city)
                    ])
                
                if bbn_detail:
                    return bbn_detail[0].total
        return 0

    @api.multi
    def _get_insentif_finco_value_on_date(self):
        if self.is_credit == False:
            return 0
        date_order_str = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        if self.confirm_date:
            date_order_str = self.confirm_date
        branch_id = self.branch_id.id
        finco_id = self.finco_id.id
        if not finco_id or not branch_id:
            return 0
        pricelist_incentives = self.env['dym.incentive.finco.line'].search([
                ('partner_id','=',finco_id),
                ('active','=',True),
                ('start_date','<=',date_order_str),
                ('end_date','>=',date_order_str),
            ])
        if not pricelist_incentives:
            return 0

        incentive_value = self.env['dym.incentive.finco.line.detail'].search([
                ('incentive_finco_line_id','=',pricelist_incentives[0].id),
                ('branch_id','=',branch_id),
            ])
        if incentive_value:
            return incentive_value[0]['incentive']
        return 0

    @api.one
    @api.depends('partner_id','is_credit','dealer_sale_order_line','confirm_date','branch_id','finco_id')
    def _get_costsheet(self):
        alamat = ''
        if self.partner_id.street:
            alamat += self.partner_id.street
        if self.partner_id.street2:
            alamat += ' ' + self.partner_id.street2
        if self.partner_id.rt:
            alamat += ' RT' + self.partner_id.rt
        if self.partner_id.rw:
            alamat += ' RW' + self.partner_id.rw
        alamat += '\n'
        if self.partner_id.kelurahan:
            alamat += self.partner_id.kelurahan + ', '
        if self.partner_id.kecamatan:
            alamat += self.partner_id.kecamatan + ', '
        elif self.partner_id.kecamatan_id:
            alamat += self.partner_id.kecamatan_id.name + ', '
        if self.partner_id.city_id:
            alamat += self.partner_id.city_id.name + ', '
        alamat = alamat[:-2]
        alamat += '\n'
        if self.partner_id.state_id:
            alamat += self.partner_id.state_id.name + ', '
        alamat += ' INDONESIA'
        if self.partner_id.zip_id:
            alamat += ' - ' + self.partner_id.zip_id.zip
        self.alamat = alamat
        tunai_kredit = 'Tunai'
        if self.is_credit:
            tunai_kredit = 'Kredit'
        self.tunai_kredit = tunai_kredit
        tipe_motor = ''
        nomor_mesin = ''
        nomor_rangka = ''
        tanggal_faktur_beli = ''
        nomor_faktur_beli = ''
        total_discount_intern = 0
        total_discount_extern = 0
        total_discount_finco = 0
        total_biaya_insentif = 0
        total_beban_subsidi_barang = 0
        total_harga_birojasa = 0
        total_subsidi_external = 0
        product_line_ids = []
        for line in self.dealer_sale_order_line:
            if line.product_id.id:
                if line.product_id.id not in product_line_ids:
                    product_line_ids.append(line.product_id.id)
                    tipe_motor += line.product_id.name + ', '
                nomor_mesin += line.lot_id.name + ', '
                nomor_rangka += line.lot_id.chassis_no + ', '
                if line.sudo().lot_id.purchase_order_id:
                    nomor_faktur_beli += line.sudo().lot_id.purchase_order_id.name + ', '
                if line.lot_id.po_date:
                    tanggal_faktur_beli += line.lot_id.po_date + ', '
                for disc in line.discount_line:
                    total_subsidi_external += disc.ps_ahm + disc.ps_md + disc.ps_others
                    total_claim_discount = disc.ps_ahm + disc.ps_md + disc.ps_finco + disc.ps_others + disc.ps_dealer
                    if disc.include_invoice == False:
                        total_discount_finco += (total_claim_discount - disc.discount_pelanggan)
                    else:
                        total_diskon_pelanggan = 0 if total_claim_discount - disc.discount_pelanggan >= disc.ps_dealer else disc.ps_dealer - (total_claim_discount - disc.discount_pelanggan)
                        total_diskon_external = disc.discount_pelanggan - total_diskon_pelanggan
                        total_discount_extern += total_diskon_external
                        total_discount_intern += total_diskon_pelanggan
                        total_discount_finco += disc.ps_finco
                total_harga_birojasa += self._get_harga_bbn_detail_on_date(line) * line.product_qty
                total_biaya_insentif += line.insentif_finco * line.product_qty
                total_beban_subsidi_barang = sum(disc.bb_dealer for disc in line.barang_bonus_line)
        if len(self.dealer_sale_order_line) > 1:
            self.nomor_mesin = 'Multiple'
            self.nomor_rangka = 'Multiple'
            self.nomor_faktur_beli = 'Multiple'
            self.tanggal_faktur_beli = 'Multiple'
        else:
            self.nomor_mesin = nomor_mesin[:-2]
            self.nomor_rangka = nomor_rangka[:-2]
            self.nomor_faktur_beli = nomor_faktur_beli[:-2]
            self.tanggal_faktur_beli = tanggal_faktur_beli[:-2]
        self.tipe_motor = tipe_motor[:-2]
        self.harga_jual_motor = sum(line.price_unit * line.product_qty for line in self.dealer_sale_order_line) / 1.1
        self.discount_konsumen = sum(line.discount_po for line in self.dealer_sale_order_line)
        self.discount_prog_intern = total_discount_intern
        self.discount_prog_extern = total_discount_extern
        self.netto_jual = self.harga_jual_motor - (self.discount_konsumen/1.1 + self.discount_prog_intern/1.1)
        self.ppn_keluaran = (self.harga_jual_motor - (self.discount_konsumen/1.1 + self.discount_prog_intern/1.1 + self.discount_prog_extern/1.1)) * 10/100
        hpp = 0
        for line in self.dealer_sale_order_line:
            consol_line = line.lot_id.sudo().consolidate_id.mapped('consolidate_line').filtered(lambda r: r.name == line.lot_id)
            if consol_line.price_unit:
                hpp += consol_line.price_unit
                if consol_line.price_unit != line.lot_id.hpp:
                    line.lot_id.write({'hpp':consol_line.price_unit})
            else:
                hpp += line.lot_id.hpp
        self.harga_standar = hpp
        self.ppn_masukan = self.harga_standar * 10/100
        self.selisih_penjualan = self.netto_jual - self.harga_standar
        self.selisih_ppn = self.ppn_keluaran - self.ppn_masukan
        self.harga_stnk_md = sum(line.price_bbn for line in self.dealer_sale_order_line)
        self.harga_stnk_birojasa =  total_harga_birojasa
        self.selisih_stnk = (self.harga_stnk_md + self.tambahan_pendapatan_bbn) - (self.harga_stnk_birojasa + self.tambahan_biaya_bbn)
        self.biaya_broker = sum(line.amount_hutang_komisi for line in self.dealer_sale_order_line)
        self.profit_penjualan = self.selisih_penjualan + self.selisih_ppn + self.selisih_stnk - self.biaya_broker
        self.subsidi_external = total_subsidi_external
        self.subsidi_leasing_oi = total_discount_finco
        self.insentif_leasing = total_biaya_insentif
        self.subsidi_barang = total_beban_subsidi_barang
        self.dym_biaya_lain = self.env['dym.biaya.lain'].search([]).ids
        self.biaya_lain = sum(line.value for line in self.dym_biaya_lain) 
        self.profit_lain = (self.subsidi_external + self.subsidi_leasing_oi + self.insentif_leasing) - self.biaya_lain - self.subsidi_barang
        self.net_profit = self.profit_penjualan + self.profit_lain

    nomor_faktur_jual = fields.Char(related="name", string='Nomor Faktur Jual')
    tanggal_faktur_jual = fields.Date(related="date_order", string='Tanggal Faktur Jual')
    nomor_mesin = fields.Char(string='Nomor Mesin', compute='_get_costsheet', store=True)
    nomor_rangka = fields.Char(string='Nomor Rangka', compute='_get_costsheet', store=True)
    nama_konsumen = fields.Many2one(related="partner_id",string='Nama Konsumen')
    alamat = fields.Text(string='Alamat', compute='_get_costsheet', store=True)
    nomor_faktur_beli = fields.Char(string='Nomor Faktur Beli', compute='_get_costsheet', store=True)
    tanggal_faktur_beli = fields.Char(string='Tanggal Faktur Beli', compute='_get_costsheet', store=True)
    sistem_pembelian = fields.Selection([('Cash','Cash'),('DF','DF')], string='Sistem Pembelian')
    tipe_motor = fields.Char(string='Tipe Motor', compute='_get_costsheet', store=True)
    tunai_kredit = fields.Char(string='Tunai / Kredit', compute='_get_costsheet', store=True)
    marketing_counter = fields.Many2one(related="employee_id", string='Marketing / Counter')
    harga_jual_motor = fields.Float(string='Harga Jual DPP (Exc. BBN dan PPN)', compute='_get_costsheet', store=True)
    discount_konsumen = fields.Float(string='Discount Konsumen', compute='_get_costsheet', store=True)
    discount_prog_intern = fields.Float(string='Discount Prog Intern', compute='_get_costsheet', store=True)
    discount_prog_extern = fields.Float(string='Discount Prog Extern', compute='_get_costsheet', store=True)
    netto_jual = fields.Float(string='Harga Jual Netto (Exc.PPN)', compute='_get_costsheet', store=True)
    ppn_keluaran = fields.Float(string='PPN Keluaran (PK)', compute='_get_costsheet', store=True)
    harga_standar = fields.Float(string='Harga Beli Standar (DPP)', compute='_get_costsheet', store=True)
    ppn_masukan = fields.Float(string='PPN Masukan (PM)', compute='_get_costsheet', store=True)
    selisih_penjualan = fields.Float(string='GP Unit', compute='_get_costsheet', store=True)
    selisih_ppn = fields.Float(string='Selisih PPN (SPN)', compute='_get_costsheet', store=True)
    harga_stnk_md = fields.Float(string='Harga Jual STNK', compute='_get_costsheet', store=True)
    harga_stnk_birojasa = fields.Float(string='Beban STNK Biro Jasa', compute='_get_costsheet', store=True)
    tambahan_pendapatan_bbn = fields.Float(string='Tambahan Pendapatan BBN')
    tambahan_biaya_bbn = fields.Float(string='Tambahan Biaya BBN')
    selisih_stnk = fields.Float(string='Margin BBN', compute='_get_costsheet', store=True)
    biaya_broker = fields.Float(string='Mediator', compute='_get_costsheet', store=True)
    profit_penjualan = fields.Float(string='Laba Penjualan (GP OTR)', compute='_get_costsheet', store=True)
    subsidi_external = fields.Float(string='Subsidi External', compute='_get_costsheet', store=True)
    subsidi_leasing_oi = fields.Float(string='Subsidi Leasing', compute='_get_costsheet', store=True)
    insentif_leasing = fields.Float(string='Insentif Leasing', compute='_get_costsheet', store=True)
    subsidi_barang = fields.Float(string='Beban Barang Subsidi', compute='_get_costsheet', store=True)
    biaya_lain = fields.Float(string='Biaya Lain-lain', compute='_get_costsheet', store=False)
    dym_biaya_lain = fields.Many2many('dym.biaya.lain', string='Biaya Lain', compute='_get_costsheet')
    profit_lain = fields.Float(string='Other Income (Net)', compute='_get_costsheet', store=True)
    net_profit = fields.Float(string='Laba Operasi', compute='_get_costsheet', store=True)