import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_penjualandwh import dym_report_penjualandwh_print
from openerp.tools.translate import translate
import string

_ir_translation_name = 'report.penjualandwh'

class dym_report_penjualandwh_print_xls(dym_report_penjualandwh_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_penjualandwh_print_xls, self).__init__(cr, uid, name, context=context)
        dso_obj = self.pool.get('dealer.sale.order')
        self.context = context
        wl_overview = dso_obj._report_xls_penjualandwh_fields(cr, uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': wl_overview,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src

class report_penjualandwh_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_penjualandwh_xls, self).__init__(name, table, rml, parser, header, store)

        # Cell Styles
        _xs = self.xls_styles
        # header

        # Report Column Headers format
        rh_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rh_cell_style = xlwt.easyxf(rh_cell_format)
        self.rh_cell_style_center = xlwt.easyxf(
            rh_cell_format + _xs['center'])
        self.rh_cell_style_right = xlwt.easyxf(rh_cell_format + _xs['right'])

        # Partner Column Headers format
        fill_blue = 'pattern: pattern solid, fore_color 27;'
        ph_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.ph_cell_style = xlwt.easyxf(ph_cell_format)
        self.ph_cell_style_decimal = xlwt.easyxf(
            ph_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)

        # Partner Column Data format
        pd_cell_format = _xs['borders_all']
        self.pd_cell_style = xlwt.easyxf(pd_cell_format)
        self.pd_cell_style_center = xlwt.easyxf(
            pd_cell_format + _xs['center'])
        self.pd_cell_style_date = xlwt.easyxf(
            pd_cell_format + _xs['left'],
            num_format_str=report_xls.date_format)
        self.pd_cell_style_decimal = xlwt.easyxf(
            pd_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)

        # totals
        rt_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rt_cell_style = xlwt.easyxf(rt_cell_format)
        self.rt_cell_style_right = xlwt.easyxf(rt_cell_format + _xs['right'])
        self.rt_cell_style_decimal = xlwt.easyxf(
            rt_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)

        # XLS Template
        self.col_specs_template_overview = {
            'no': {
                'header': [1, 5, 'text', _render("_('No')")],
                'lines': [1, 0, 'number', _render("p['no']")],
                'totals': [1, 5, 'number', None]},
            'region': {
                'header': [1, 10, 'text', _render("_('Region')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['region']")],
                'totals': [1, 0, 'text', None]},
            'area': {
                'header': [1, 10, 'text', _render("_('Area')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['area']")],
                'totals': [1, 0, 'text', None]},
            'branch_code': {
                'header': [1, 22, 'text', _render("_('Cab_ID')")],
                'lines': [1, 0, 'text', _render("p['branch_code']")],
                'totals': [1, 0, 'text', None]},
            'branch_name': {
                'header': [1, 22, 'text', _render("_('Cabang')")],
                'lines': [1, 0, 'text', _render("p['branch_name']")],
                'totals': [1, 22, 'number', None]},
            'invoice_number': {
                'header': [1, 22, 'text', _render("_('Invoice')")],
                'lines': [1, 0, 'text', _render("p['invoice_number']")],
                'totals': [1, 22, 'number', None]},
            'invoice_date': {
                'header': [1, 22, 'text', _render("_('Tgl Invoice')")],
                'lines': [1, 0, 'text', _render("p['invoice_date']")],
                'totals': [1, 22, 'number', None]},
            'invoice_date_year': {
                'header': [1, 22, 'text', _render("_('Tahun')")],
                'lines': [1, 0, 'text', _render("p['invoice_date_year']")],
                'totals': [1, 22, 'number', None]},
            'chosen_month': {
                'header': [1, 22, 'text', _render("_('Bulan')")],
                'lines': [1, 0, 'text', _render("p['chosen_month']")],
                'totals': [1, 22, 'number', None]},
            'finco_code': {
                'header': [1, 22, 'text', _render("_('Cust')")],
                'lines': [1, 0, 'text', _render("p['finco_code']")],
                'totals': [1, 22, 'number', None]},
            'cust_name': {
                'header': [1, 22, 'text', _render("_('Cust_Type')")],
                'lines': [1, 0, 'text', _render("p['cust_name']")],
                'totals': [1, 22, 'number', None]},
            'sls_pay': {
                'header': [1, 22, 'text', _render("_('Payment')")],
                'lines': [1, 0, 'text', _render("p['sls_pay']")],
                'totals': [1, 22, 'number', None]},
            'marketing': {
                'header': [1, 22, 'text', _render("_('Marketing')")],
                'lines': [1, 0, 'text', _render("p['marketing']")],
                'totals': [1, 22, 'number', None]},
            'product_name': {
                'header': [1, 22, 'text', _render("_('Product')")],
                'lines': [1, 0, 'text', _render("p['product_name']")],
                'totals': [1, 22, 'number', None]},
            'product_desc': {
                'header': [1, 22, 'text', _render("_('Prod Type')")],
                'lines': [1, 0, 'text', _render("p['product_desc']")],
                'totals': [1, 22, 'number', None]},
            'lot_name': {
                'header': [1, 22, 'text', _render("_('Nomesin')")],
                'lines': [1, 0, 'text', _render("p['lot_name']")],
                'totals': [1, 22, 'text', _render("p['lot_name']")]},
            'lot_chassis': {
                'header': [1, 22, 'text', _render("_('Norangka')")],
                'lines': [1, 0, 'text', _render("p['lot_chassis']")],
                'totals': [1, 22, 'text', _render("p['lot_chassis']")]},
            'price_unit': {
                'header': [1, 22, 'text', _render("_('Unit_Price')")],
                'lines': [1, 0, 'number', _render("p['price_unit']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['price_unit']"), None, self.rt_cell_style_decimal]},
            'price_bbn': {
                'header': [1, 22, 'text', _render("_('Unit STNK')")],
                'lines': [1, 0, 'number', _render("p['price_bbn']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['price_bbn']"), None, self.rt_cell_style_decimal]},
            'disc_total': {
                'header': [1, 22, 'text', _render("_('Discount')")],
                'lines': [1, 0, 'number', _render("p['disc_total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['disc_total']"), None, self.rt_cell_style_decimal]},
            'cust_name': {
                'header': [1, 22, 'text', _render("_('Nama')")],
                'lines': [1, 0, 'text', _render("p['cust_name']")],
                'totals': [1, 22, 'number', None]},
            'alamat_cust_name': {
                'header': [1, 22, 'text', _render("_('Alamat')")],
                'lines': [1, 0, 'text', _render("p['alamat_cust_name']")],
                'totals': [1, 22, 'number', None]},
            'kota_cabang': {
                'header': [1, 22, 'text', _render("_('Kota (Cabang)')")],
                'lines': [1, 0, 'text', _render("p['kota_cabang']")],
                'totals': [1, 22, 'number', None]},
            'amount_hutang_komisi': {
                'header': [1, 22, 'text', _render("_('Komisi Broker')")],
                'lines': [1, 0, 'number', _render("p['amount_hutang_komisi']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['amount_hutang_komisi']"), None, self.rt_cell_style_decimal]},
            'product_qty': {
                'header': [1, 22, 'text', _render("_('Qty')")],
                'lines': [1, 0, 'number', _render("p['product_qty']")],
                'totals': [1, 22, 'number', _render("p['product_qty']"), None, self.rt_cell_style_decimal]},
            'qty_retur': {
                'header': [1, 22, 'text', _render("_('Qty Retur')")],
                'lines': [1, 0, 'number', _render("p['qty_retur']")],
                'totals': [1, 22, 'number', _render("p['qty_retur']"), None, self.rt_cell_style_decimal]},
            'net_sales': {
                'header': [1, 22, 'text', _render("_('Net Sales')")],
                'lines': [1, 0, 'number', _render("p['net_sales']")],
                'totals': [1, 22, 'number', _render("p['net_sales']"), None, self.rt_cell_style_decimal]},
            'invoice_date_date': {
                'header': [1, 22, 'text', _render("_('Tanggal')")],
                'lines': [1, 0, 'text', _render("p['invoice_date_date']")],
                'totals': [1, 22, 'number', None]},
            'cabang_partner': {
                'header': [1, 20, 'text', _render("_('Trans')")],
                'lines': [1, 0, 'text', _render("p['cabang_partner']")],
                'totals': [1, 20, 'text', _render("p['cabang_partner']")]},
            'tanda_jadi': {
                'header': [1, 22, 'text', _render("_('Uang Muka')")],
                'lines': [1, 0, 'number', _render("p['tanda_jadi']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['tanda_jadi']"), None, self.rt_cell_style_decimal]},
            'no_po': {
                'header': [1, 22, 'text', _render("_('PO No')")],
                'lines': [1, 0, 'text', _render("p['no_po']")],
                'totals': [1, 22, 'number', None]},
            'tgl_po': {
                'header': [1, 22, 'text', _render("_('Tgl Bayar PO')")],
                'lines': [1, 0, 'text', _render("p['tgl_po']")],
                'totals': [1, 22, 'number', None]},
            'jp_po': {
                'header': [1, 22, 'text', _render("_('Tot Bayar PO')")],
                'lines': [1, 0, 'number', _render("p['jp_po']")],
                'totals': [1, 22, 'number', _render("p['jp_po']"), None, self.rt_cell_style_decimal]},
            'discount_po': {
                'header': [1, 22, 'text', _render("_('Disc Konsumen')")],
                'lines': [1, 0, 'number', _render("p['discount_po']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_po']"), None, self.rt_cell_style_decimal]},
            'discount_extern_ps': {
                'header': [1, 22, 'text', _render("_('Disc Extern')")],
                'lines': [1, 0, 'number', _render("p['discount_extern_ps']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_extern_ps']"), None, self.rt_cell_style_decimal]},
            'discount_intern_ps': {
                'header': [1, 22, 'text', _render("_('Disc Intern')")],
                'lines': [1, 0, 'number', _render("p['discount_intern_ps']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_intern_ps']"), None, self.rt_cell_style_decimal]},
            'kota_cust_name': {
                'header': [1, 22, 'text', _render("_('Kodya')")],
                'lines': [1, 0, 'text', _render("p['kota_cust_name']")],
                'totals': [1, 22, 'number', None]},
            'kec_cust_stnk_name': {
                'header': [1, 22, 'text', _render("_('Kecamatan')")],
                'lines': [1, 0, 'text', _render("p['kec_cust_stnk_name']")],
                'totals': [1, 22, 'number', None]},
            'kel_cust_stnk_name': {
                'header': [1, 22, 'text', _render("_('Kelurahan')")],
                'lines': [1, 0, 'text', _render("p['kel_cust_stnk_name']")],
                'totals': [1, 22, 'number', None]},
            'nik_sales_koor_name': {
                'header': [1, 22, 'text', _render("_('MKT_NIK')")],
                'lines': [1, 0, 'text', _render("p['nik_sales_koor_name']")],
                'totals': [1, 22, 'number', None]},
            'sales_koor_name': {
                'header': [1, 22, 'text', _render("_('MKT_Nama')")],
                'lines': [1, 0, 'text', _render("p['sales_koor_name']")],
                'totals': [1, 22, 'number', None]},
            'job_name': {
                'header': [1, 22, 'text', _render("_('MKT_Job')")],
                'lines': [1, 0, 'text', _render("p['job_name']")],
                'totals': [1, 22, 'number', None]},
            'mkt_join_date': {
                'header': [1, 22, 'text', _render("_('MKT_Join_date')")],
                'lines': [1, 0, 'text', _render("p['mkt_join_date']")],
                'totals': [1, 22, 'number', None]},
            'lama_kerja': {
                'header': [1, 22, 'text', _render("_('Lama Kerja')")],
                'lines': [1, 0, 'text', _render("p['lama_kerja']")],
                'totals': [1, 22, 'number', None]},
            'spv_nik': {
                'header': [1, 22, 'text', _render("_('SPV_NIK')")],
                'lines': [1, 0, 'text', _render("p['spv_nik']")],
                'totals': [1, 22, 'number', None]},
            'spv_name': {
                'header': [1, 22, 'text', _render("_('SPV_Nama')")],
                'lines': [1, 0, 'text', _render("p['spv_name']")],
                'totals': [1, 22, 'number', None]},
            'nik_sales_name': {
                'header': [1, 22, 'text', _render("_('Trainee')")],
                'lines': [1, 0, 'text', _render("p['nik_sales_name']")],
                'totals': [1, 22, 'number', None]},
            'sales_name': {
                'header': [1, 22, 'text', _render("_('Trainee_Desc')")],
                'lines': [1, 0, 'text', _render("p['sales_name']")],
                'totals': [1, 22, 'number', None]},
            'tambahan_bbn': {
                'header': [1, 22, 'text', _render("_('Tambahan BBN')")],
                'lines': [1, 0, 'number', _render("p['tambahan_bbn']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['tambahan_bbn']"), None, self.rt_cell_style_decimal]},
            'nama_pendek': {
                'header': [1, 22, 'text', _render("_('Nama_Pendek')")],
                'lines': [1, 0, 'text', _render("p['nama_pendek']")],
                'totals': [1, 22, 'number', None]},
            'last_update_time': {
                'header': [1, 22, 'text', _render("_('Last Update Time')")],
                'lines': [1, 0, 'text', _render("p['last_update_time']")],
                'totals': [1, 22, 'number', None]},
            
            'qty_pic': {
                'header': [1, 22, 'text', _render("_('Qty PIC')")],
                'lines': [1, 0, 'number', _render("p['qty_pic']")],
                'totals': [1, 22, 'number', _render("p['qty_pic']"), None, self.rt_cell_style_decimal]},
            'branch_status': {
                'header': [1, 10, 'text', _render("_('Branch Status')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['branch_status'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'invoice_status': {
                'header': [1, 22, 'text', _render("_('Status Invoice')")],
                'lines': [1, 0, 'text', _render("p['invoice_status']")],
                'totals': [1, 22, 'number', None]},
            'no_registrasi': {
                'header': [1, 22, 'text', _render("_('No Registrasi')")],
                'lines': [1, 0, 'text', _render("p['no_registrasi']")],
                'totals': [1, 22, 'number', None]},
            'spk_name': {
                'header': [1, 22, 'text', _render("_('Dealer Memo')")],
                'lines': [1, 0, 'text', _render("p['spk_name']")],
                'totals': [1, 22, 'number', None]},
            'name': {
                'header': [1, 22, 'text', _render("_('DSM Number')")],
                'lines': [1, 0, 'text', _render("p['name']")],
                'totals': [1, 22, 'number', None]},
            'date_order': {
                'header': [1, 22, 'text', _render("_('DSM Date')")],
                'lines': [1, 0, 'text', _render("p['date_order']")],
                'totals': [1, 22, 'number', None]},
            'state': {
                'header': [1, 22, 'text', _render("_('State')")],
                'lines': [1, 0, 'text', _render("p['state']")],
                'totals': [1, 22, 'number', None]},
            'state_ksu': {
                'header': [1, 22, 'text', _render("_('State KSU')")],
                'lines': [1, 0, 'text', _render("p['state_ksu']")],
                'totals': [1, 22, 'number', None]},
            'state_picking': {
                'header': [1, 22, 'text', _render("_('State Picking')")],
                'lines': [1, 0, 'text', _render("p['state_picking']")],
                'totals': [1, 22, 'number', None]},
            'oos_number': {
                'header': [1, 22, 'text', _render("_('OOS Number')")],
                'lines': [1, 0, 'text', _render("p['oos_number']")],
                'totals': [1, 22, 'number', None]},
            'is_cod': {
                'header': [1, 22, 'text', _render("_('Payment Type')")],
                'lines': [1, 0, 'text', _render("p['is_cod']")],
                'totals': [1, 22, 'number', None]},
            'sls_pay': {
                'header': [1, 22, 'text', _render("_('Payment')")],
                'lines': [1, 0, 'text', _render("p['sls_pay']")],
                'totals': [1, 22, 'number', None]},
            'vcust_id': {
                'header': [1, 22, 'text', _render("_('Finco Code')")],
                'lines': [1, 0, 'text', _render("p['vcust_id']")],
                'totals': [1, 22, 'number', None]},
            'finco_branch': {
                'header': [1, 22, 'text', _render("_('Finco Branch')")],
                'lines': [1, 0, 'text', _render("p['finco_branch']")],
                'totals': [1, 22, 'number', None]},
            'cust_code': {
                'header': [1, 22, 'text', _render("_('Customer Code')")],
                'lines': [1, 0, 'text', _render("p['cust_code']")],
                'totals': [1, 22, 'number', None]},
            'no_hp_cust_beli': {
                'header': [1, 22, 'text', _render("_('No HP Cust Beli')")],
                'lines': [1, 0, 'text', _render("p['no_hp_cust_beli']")],
                'totals': [1, 22, 'number', None]},
            'cust_stnk_code': {
                'header': [1, 22, 'text', _render("_('Customer STNK Code')")],
                'lines': [1, 0, 'text', _render("p['cust_stnk_code']")],
                'totals': [1, 22, 'number', None]},
            'cust_stnk_name': {
                'header': [1, 22, 'text', _render("_('Customer STNK Name')")],
                'lines': [1, 0, 'text', _render("p['cust_stnk_name']")],
                'totals': [1, 22, 'number', None]},
            'alamat_cust_stnk_name': {
                'header': [1, 22, 'text', _render("_('Alamat Customer STNK Name')")],
                'lines': [1, 0, 'text', _render("p['alamat_cust_stnk_name']")],
                'totals': [1, 22, 'number', None]},
            'kota_cust_stnk_name': {
                'header': [1, 22, 'text', _render("_('Kota Customer STNK Name')")],
                'lines': [1, 0, 'text', _render("p['kota_cust_stnk_name']")],
                'totals': [1, 22, 'number', None]},
            'jns_kota_cust_stnk_name': {
                'header': [1, 22, 'text', _render("_('Jenis Kota Customer STNK Name')")],
                'lines': [1, 0, 'text', _render("p['jns_kota_cust_stnk_name']")],
                'totals': [1, 22, 'number', None]},
            'no_hp_cust_stnk': {
                'header': [1, 22, 'text', _render("_('No HP Cust STNK')")],
                'lines': [1, 0, 'text', _render("p['no_hp_cust_stnk']")],
                'totals': [1, 22, 'number', None]},
            'partner_komisi_id': {
                'header': [1, 22, 'text', _render("_('ID Broker')")],
                'lines': [1, 0, 'text', _render("p['partner_komisi_id']")],
                'totals': [1, 22, 'number', None]},
            'hutang_komisi_id': {
                'header': [1, 22, 'text', _render("_('Nama Broker')")],
                'lines': [1, 0, 'text', _render("p['hutang_komisi_id']")],
                'totals': [1, 22, 'number', None]},
            'pph_komisi': {
                'header': [1, 22, 'text', _render("_('PPH Komisi')")],
                'lines': [1, 0, 'number', _render("p['pph_komisi']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['pph_komisi']"), None, self.rt_cell_style_decimal]},
            'lot_name': {
                'header': [1, 22, 'text', _render("_('Engine Number')")],
                'lines': [1, 0, 'text', _render("p['lot_name']")],
                'totals': [1, 22, 'text', _render("p['lot_name']")]},
            'lot_chassis': {
                'header': [1, 22, 'text', _render("_('Chassis Number')")],
                'lines': [1, 0, 'text', _render("p['lot_chassis']")],
                'totals': [1, 22, 'text', _render("p['lot_chassis']")]},
            'pav_code': {
                'header': [1, 22, 'text', _render("_('Color')")],
                'lines': [1, 0, 'text', _render("p['pav_code']")],
                'totals': [1, 22, 'number', None]},
            'categ_name': {
                'header': [1, 22, 'text', _render("_('Category Name')")],
                'lines': [1, 0, 'text', _render("p['categ_name']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['categ_name']")]},
            'categ2_name': {
                'header': [1, 22, 'text', _render("_('Parent Category Name')")],
                'lines': [1, 0, 'text', _render("p['categ2_name']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['categ2_name']")]},
            'prod_series': {
                'header': [1, 22, 'text', _render("_('Series')")],
                'lines': [1, 0, 'text', _render("p['prod_series']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['prod_series']")]},
            'tahun_rakit': {
                'header': [1, 22, 'text', _render("_('Tahun Rakit')")],
                'lines': [1, 0, 'text', _render("p['tahun_rakit']")],
                'totals': [1, 22, 'number', None]},
            'ps_ahm': {
                'header': [1, 22, 'text', _render("_('PS AHM (Juklak)')")],
                'lines': [1, 0, 'number', _render("p['ps_ahm']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['ps_ahm']"), None, self.rt_cell_style_decimal]},
            'ps_md': {
                'header': [1, 22, 'text', _render("_('PS MD (Juklak)')")],
                'lines': [1, 0, 'number', _render("p['ps_md']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['ps_md']"), None, self.rt_cell_style_decimal]},
            'ps_finco': {
                'header': [1, 22, 'text', _render("_('PS Finco (Juklak)')")],
                'lines': [1, 0, 'number', _render("p['ps_finco']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['ps_finco']"), None, self.rt_cell_style_decimal]},
            'ps_dealer': {
                'header': [1, 22, 'text', _render("_('PS Dealer (Juklak)')")],
                'lines': [1, 0, 'number', _render("p['ps_dealer']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['ps_dealer']"), None, self.rt_cell_style_decimal]},
            'ps_other': {
                'header': [1, 22, 'text', _render("_('PS Other (Juklak)')")],
                'lines': [1, 0, 'number', _render("p['ps_other']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['ps_other']"), None, self.rt_cell_style_decimal]},
            'ps_total': {
                'header': [1, 22, 'text', _render("_('PS Total (Juklak)')")],
                'lines': [1, 0, 'number', _render("p['ps_total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['ps_total']"), None, self.rt_cell_style_decimal]},
            'price_unit': {
                'header': [1, 22, 'text', _render("_('Off The Road')")],
                'lines': [1, 0, 'number', _render("p['price_unit']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['price_unit']"), None, self.rt_cell_style_decimal]},
            'sales': {
                'header': [1, 22, 'text', _render("_('Nett Sales')")],
                'lines': [1, 0, 'number', _render("p['sales']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['sales']"), None, self.rt_cell_style_decimal]},
            'disc_total': {
                'header': [1, 22, 'text', _render("_('Total Disc')")],
                'lines': [1, 0, 'number', _render("p['disc_total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['disc_total']"), None, self.rt_cell_style_decimal]},
            'disc_quo_incl_tax_no': {
                'header': [1, 34, 'text', _render("_('Total Disc PS (Incl Tax) Diskon JP2')")],
                'lines': [1, 0, 'number', _render("p['disc_quo_incl_tax_no']"), None, self.pd_cell_style_decimal],
                'totals': [1, 34, 'number', _render("p['disc_quo_incl_tax_no']"), None, self.rt_cell_style_decimal]},
            'amount_hutang_komisi': {
                'header': [1, 22, 'text', _render("_('Hutang Komisi')")],
                'lines': [1, 0, 'number', _render("p['amount_hutang_komisi']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['amount_hutang_komisi']"), None, self.rt_cell_style_decimal]},
            'piutang_total': {
                'header': [1, 22, 'text', _render("_('Piutang Total')")],
                'lines': [1, 0, 'number', _render("p['piutang_total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['piutang_total']"), None, self.rt_cell_style_decimal]},
            'beban_cabang': {
                'header': [1, 22, 'text', _render("_('Beban Cabang')")],
                'lines': [1, 0, 'number', _render("p['beban_cabang']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['beban_cabang']"), None, self.rt_cell_style_decimal]},
            'price_subtotal': {
                'header': [1, 22, 'text', _render("_('DPP')")],
                'lines': [1, 0, 'number', _render("p['price_subtotal']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['price_subtotal']"), None, self.rt_cell_style_decimal]},
            'PPN': {
                'header': [1, 22, 'text', _render("_('PPN')")],
                'lines': [1, 0, 'number', _render("p['PPN']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['PPN']"), None, self.rt_cell_style_decimal]},
            'total': {
                'header': [1, 22, 'text', _render("_('Total')")],
                'lines': [1, 0, 'number', _render("p['total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['total']"), None, self.rt_cell_style_decimal]},
            'force_cogs': {
                'header': [1, 22, 'text', _render("_('HPP')")],
                'lines': [1, 0, 'number', _render("p['force_cogs']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['force_cogs']"), None, self.rt_cell_style_decimal]},
            'gp_dpp_minus_hpp': {
                'header': [1, 22, 'text', _render("_('GP (DPP - HPP)')")],
                'lines': [1, 0, 'number', _render("p['gp_dpp_minus_hpp']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['gp_dpp_minus_hpp']"), None, self.rt_cell_style_decimal]},
            'gp_unit': {
                'header': [1, 22, 'text', _render("_('GP + Klaim')")],
                'lines': [1, 0, 'number', _render("p['gp_unit']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['gp_unit']"), None, self.rt_cell_style_decimal]},
            'price_bbn_beli': {
                'header': [1, 22, 'text', _render("_('HPP BBN')")],
                'lines': [1, 0, 'number', _render("p['price_bbn_beli']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['price_bbn_beli']"), None, self.rt_cell_style_decimal]},
            'gp_bbn': {
                'header': [1, 22, 'text', _render("_('GP BBN')")],
                'lines': [1, 0, 'number', _render("p['gp_bbn']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['gp_bbn']"), None, self.rt_cell_style_decimal]},
            'gp_total': {
                'header': [1, 22, 'text', _render("_('Total GP')")],
                'lines': [1, 0, 'number', _render("p['gp_total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['gp_total']"), None, self.rt_cell_style_decimal]},
            'dpp_insentif_finco': {
                'header': [1, 22, 'text', _render("_('DPP Insentif Finco')")],
                'lines': [1, 0, 'number', _render("p['dpp_insentif_finco']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['dpp_insentif_finco']"), None, self.rt_cell_style_decimal]},
            'tax_type': {
                'header': [1, 22, 'text', _render("_('Tax Type')")],
                'lines': [1, 0, 'text', _render("p['tax_type']")],
                'totals': [1, 22, 'number', None]},
            'cust_corp': {
                'header': [1, 22, 'text', _render("_('Cust Corp')")],
                'lines': [1, 0, 'text', _render("p['cust_corp']")],
                'totals': [1, 22, 'number', None]},
            'vchannel': {
                'header': [1, 22, 'text', _render("_('VChannel')")],
                'lines': [1, 0, 'text', _render("p['vchannel']")],
                'totals': [1, 22, 'number', None]},
            'proposal_id': {
                'header': [1, 22, 'text', _render("_('Proposal Event')")],
                'lines': [1, 0, 'text', _render("p['proposal_id']")],
                'totals': [1, 22, 'number', None]},
            'pmd_reff': {
                'header': [1, 22, 'text', _render("_('PMD Reff')")],
                'lines': [1, 0, 'text', _render("p['pmd_reff']")],
                'totals': [1, 22, 'number', None]},
            'proposal_address': {
                'header': [1, 22, 'text', _render("_('Proposal Address')")],
                'lines': [1, 0, 'text', _render("p['proposal_address']")],
                'totals': [1, 22, 'number', None]},
            'trans': {
                'header': [1, 22, 'text', _render("_('Trans')")],
                'lines': [1, 0, 'text', _render("p['trans']")],
                'totals': [1, 22, 'number', None]},
            'npwp_cust': {
                'header': [1, 22, 'text', _render("_('NPWP Cust')")],
                'lines': [1, 0, 'text', _render("p['npwp_cust']")],
                'totals': [1, 22, 'number', None]},
            'pkp': {
                'header': [1, 22, 'text', _render("_('PKP / Non PKP')")],
                'lines': [1, 0, 'text', _render("p['pkp']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['pkp']")]},
            'faktur_pajak': {
                'header': [1, 22, 'text', _render("_('Faktur Pajak')")],
                'lines': [1, 0, 'text', _render("p['faktur_pajak']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['faktur_pajak']")]},
            'or_name': {
                'header': [1, 22, 'text', _render("_('Other Receivables')")],
                'lines': [1, 0, 'text', _render("p['or_name']")],
                'totals': [1, 22, 'number', None]},
            'ar_days': {
                'header': [1, 22, 'text', _render("_('AR Days')")],
                'lines': [1, 0, 'number', _render("p['ar_days']")],
                'totals': [1, 22, 'number', None]},
            'tgl_lunas': {
                'header': [1, 22, 'text', _render("_('Lunas')")],
                'lines': [1, 0, 'text', _render("p['tgl_lunas']")],
                'totals': [1, 22, 'number', None]},
            'md_code': {
                'header': [1, 22, 'text', _render("_('Main Dealer')")],
                'lines': [1, 0, 'text', _render("p['md_code']")],
                'totals': [1, 22, 'number', None]},
            'analytic_combination': {
                'header': [1, 20, 'text', _render("_('Analytic Combination')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['analytic_combination'] or ''")],
                'totals': [1, 0, 'text', None]},
            'analytic_1': {
                'header': [1, 20, 'text', _render("_('Analytic Company')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['analytic_1'] or ''")],
                'totals': [1, 0, 'text', None]},
            'analytic_2': {
                'header': [1, 20, 'text', _render("_('Analytic Bisnis Unit')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['analytic_2'] or ''")],
                'totals': [1, 0, 'text', None]},
            'analytic_3': {
                'header': [1, 20, 'text', _render("_('Analytic Branch')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['analytic_3'] or ''")],
                'totals': [1, 0, 'text', None]},
            'analytic_4': {
                'header': [1, 20, 'text', _render("_('Analytic Cost Center')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['analytic_4'] or ''")],
                'totals': [1, 0, 'text', None]},
            'disc_quo_incl_tax': {
                'header': [1, 34, 'text', _render("_('Total Disc PS (Incl Tax) Diskon JP1')")],
                'lines': [1, 0, 'number', _render("p['disc_quo_incl_tax']"), None, self.pd_cell_style_decimal],
                'totals': [1, 34, 'number', _render("p['disc_quo_incl_tax']"), None, self.rt_cell_style_decimal]},
            'disc_reg': {
                'header': [1, 34, 'text', _render("_('Total Disc Reg (Nett)  Diskon JP1')")],
                'lines': [1, 0, 'number', _render("p['disc_reg']"), None, self.pd_cell_style_decimal],
                'totals': [1, 34, 'number', _render("p['disc_reg']"), None, self.rt_cell_style_decimal]},
            'disc_quo': {
                'header': [1, 34, 'text', _render("_('Total Disc PS (Nett)  Diskon JP1')")],
                'lines': [1, 0, 'number', _render("p['disc_quo']"), None, self.pd_cell_style_decimal],
                'totals': [1, 34, 'number', _render("p['disc_quo']"), None, self.rt_cell_style_decimal]},
            'piutang_dp': {
                'header': [1, 22, 'text', _render("_('Piutang JP Nett')")],
                'lines': [1, 0, 'number', _render("p['piutang_dp']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['piutang_dp']"), None, self.rt_cell_style_decimal]},
            'piutang': {
                'header': [1, 22, 'text', _render("_('Piutang')")],
                'lines': [1, 0, 'number', _render("p['piutang']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['piutang']"), None, self.rt_cell_style_decimal]},
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        self.col_specs_template_overview.update({})
        _ = _p._

        for r in _p.reports:
            title_short = r['title_short'].replace('/', '-')
            ws_o = wb.add_sheet(title_short)
            
            for ws in [ws_o]:
                ws.panes_frozen = True
                ws.remove_splits = True
                ws.portrait = 0  # Landscape
                ws.fit_width_to_pages = 1
            row_pos_o = 0
            row_pos_d = 0

            # set print header/footer
            for ws in [ws_o]:
                ws.header_str = self.xls_headers['standard']
                ws.footer_str = self.xls_footers['standard']

            # Company Name
            cell_style = xlwt.easyxf(_xs['left'])
            c_specs_o = [
                ('report_name', 1, 0, 'text', _p.company.name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            
            # Title
            cell_style = xlwt.easyxf(_xs['xls_title'])
            c_specs_o = [
                ('report_name', 1, 0, 'text', 'Laporan DWH New'),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            
            ## Start Date & End Date ##
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join(
                [_('Tanggal'), _('-' if data['start_date'] == False else str(data['start_date'])), _('s/d'), _('-' if data['end_date'] == False else str(data['end_date'])),
                 _p.report_info])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            row_pos_o += 1

            # Report Column Headers
            c_specs_o = map(
                lambda x: self.render(
                    x, self.col_specs_template_overview, 'header',
                    render_space={'_': _p._}),
                wanted_list_overview)
            row_data = self.xls_row_template(
                c_specs_o, [x[0] for x in c_specs_o])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=self.rh_cell_style,
                set_column_size=True)
            ws_o.set_horz_split_pos(row_pos_o)
            row_data_begin = row_pos_o
            
            # Columns and Rows
            # Columns and Rows
            no = 0
            for p in r['dso_ids']:
                if not 'disc_quo_incl_tax_no' in p:
                    p['disc_quo_incl_tax_no']=None
                c_specs_o = map(
                    lambda x: self.render(x, self.col_specs_template_overview, 'lines'),
                    wanted_list_overview)
                for x in c_specs_o :
                    if x[0] == 'no':
                        no += 1
                        x[4] = no
                row_data = self.xls_row_template(
                    c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
            row_data_end = row_pos_o            
            # Totals
            ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)   
            ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
            ws_o.set_vert_split_pos(3)
            ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)   
            ws_o.write(row_pos_o, 6, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 7, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 8, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 9, None, self.rt_cell_style_decimal)   
            ws_o.write(row_pos_o, 10, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 11, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 12, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 13, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 14, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 15, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 16, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 17, xlwt.Formula("SUM(R"+str(row_data_begin)+":R"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 18, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 19, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 20, xlwt.Formula("SUM(U"+str(row_data_begin)+":U"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 21, xlwt.Formula("SUM(V"+str(row_data_begin)+":V"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 22, xlwt.Formula("SUM(W"+str(row_data_begin)+":W"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 23, xlwt.Formula("SUM(X"+str(row_data_begin)+":X"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 24, xlwt.Formula("SUM(Y"+str(row_data_begin)+":Y"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 25, xlwt.Formula("SUM(Z"+str(row_data_begin)+":Z"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 26, xlwt.Formula("SUM(AA"+str(row_data_begin)+":AA"+str(row_data_end)+")"), self.rt_cell_style_decimal)   
            ws_o.write(row_pos_o, 27, xlwt.Formula("SUM(AB"+str(row_data_begin)+":AB"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 28, xlwt.Formula("SUM(AC"+str(row_data_begin)+":AC"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 29, xlwt.Formula("SUM(AD"+str(row_data_begin)+":AD"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 30, xlwt.Formula("SUM(AE"+str(row_data_begin)+":AE"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 31, xlwt.Formula("SUM(AF"+str(row_data_begin)+":AF"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 32, xlwt.Formula("SUM(AG"+str(row_data_begin)+":AG"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 33, xlwt.Formula("SUM(AH"+str(row_data_begin)+":AH"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 34, xlwt.Formula("SUM(AI"+str(row_data_begin)+":AI"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 35, xlwt.Formula("SUM(AJ"+str(row_data_begin)+":AJ"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 36, xlwt.Formula("SUM(AK"+str(row_data_begin)+":AK"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 37, xlwt.Formula("SUM(AL"+str(row_data_begin)+":AL"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 38, xlwt.Formula("SUM(AM"+str(row_data_begin)+":AM"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 39, xlwt.Formula("SUM(AN"+str(row_data_begin)+":AN"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 40, xlwt.Formula("SUM(AO"+str(row_data_begin)+":AO"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 41, xlwt.Formula("SUM(AP"+str(row_data_begin)+":AP"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 42, xlwt.Formula("SUM(AQ"+str(row_data_begin)+":AQ"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 43, xlwt.Formula("SUM(AR"+str(row_data_begin)+":AR"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 44, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 45, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 46, xlwt.Formula("SUM(AU"+str(row_data_begin)+":AU"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 47, xlwt.Formula("SUM(AV"+str(row_data_begin)+":AV"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 48, xlwt.Formula("SUM(AW"+str(row_data_begin)+":AW"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 49, xlwt.Formula("SUM(AX"+str(row_data_begin)+":AX"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 50, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 51, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 52, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 53, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 54, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 55, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 56, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 57, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 58, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 59, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 60, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 61, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 62, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 63, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 64, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 65, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 66, None, self.rt_cell_style_decimal)
            
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_penjualandwh_xls(
    'report.Laporan DWH New',
    'dealer.sale.order',
    parser = dym_report_penjualandwh_print_xls)
