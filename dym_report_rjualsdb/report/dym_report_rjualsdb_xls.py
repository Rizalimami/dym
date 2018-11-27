import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_rjualsdb import dym_report_rjualsdb_print
from openerp.tools.translate import translate
import string

class dym_report_rjualsdb_print_xls(dym_report_rjualsdb_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_rjualsdb_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('dealer.spk')._report_xls_rjualsdb_fields(cr, uid, context),
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US') 
        return translate(self.cr, 'report.rjualsdb', 'report', lang, src) or src

class report_rjualsdb_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_rjualsdb_xls, self).__init__(name, table, rml, parser, header, store)

        # Cell Styles
        _xs = self.xls_styles

        # Report Column Headers format
        rh_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rh_cell_style = xlwt.easyxf(rh_cell_format)
        self.rh_cell_style_center = xlwt.easyxf(rh_cell_format + _xs['center'])
        self.rh_cell_style_right = xlwt.easyxf(rh_cell_format + _xs['right'])

        # Partner Column Headers format
        fill_blue = 'pattern: pattern solid, fore_color 27;'
        ph_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.ph_cell_style = xlwt.easyxf(ph_cell_format)
        self.ph_cell_style_decimal = xlwt.easyxf(ph_cell_format + _xs['right'], num_format_str=report_xls.decimal_format)
        
        # Partner Column Data format
        pd_cell_format = _xs['borders_all']
        self.pd_cell_style = xlwt.easyxf(pd_cell_format)
        self.pd_cell_style_center = xlwt.easyxf(pd_cell_format + _xs['center'])
        self.pd_cell_style_date = xlwt.easyxf(pd_cell_format + _xs['left'], num_format_str=report_xls.date_format)
        self.pd_cell_style_decimal = xlwt.easyxf(pd_cell_format + _xs['right'], num_format_str=report_xls.decimal_format)

        # totals
        rt_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rt_cell_style = xlwt.easyxf(rt_cell_format)
        self.rt_cell_style_right = xlwt.easyxf(rt_cell_format + _xs['right'])
        self.rt_cell_style_decimal = xlwt.easyxf(rt_cell_format + _xs['right'], num_format_str=report_xls.decimal_format)

        # XLS Template
        self.col_specs_template_overview = {
            'no': {
                'header': [1, 5, 'text', _render("_('No')")],
                'lines': [1, 0, 'number', _render("p['no']")],
                'totals': [1, 5, 'number', None]},
            'branch_status': {
                'header': [1, 10, 'text', _render("_('Branch Status')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['branch_status'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},   
            'region': {
                'header': [1, 10, 'text', _render("_('Region')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['region']")],
                'totals': [1, 0, 'text', None]},
            'area': {
                'header': [1, 10, 'text', _render("_('Area')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['area']")],
                'totals': [1, 0, 'text', None]},
            'branch_code': {
                'header': [1, 22, 'text', _render("_('Branch Code')")],
                'lines': [1, 0, 'text', _render("p['branch_code']")],
                'totals': [1, 0, 'text', None]},
            'branch_name': {
                'header': [1, 22, 'text', _render("_('Branch Name')")],
                'lines': [1, 0, 'text', _render("p['branch_name']")],
                'totals': [1, 22, 'number', None]},
            'invoice_number': {
                'header': [1, 22, 'text', _render("_('Invoice Number')")],
                'lines': [1, 0, 'text', _render("p['invoice_number']")],
                'totals': [1, 22, 'number', None]},
            'invoice_date': {
                'header': [1, 22, 'text', _render("_('Date Invoice')")],
                'lines': [1, 0, 'text', _render("p['invoice_date']")],
                'totals': [1, 22, 'number', None]},
            'last_update_time': {
                'header': [1, 22, 'text', _render("_('Last Update Time')")],
                'lines': [1, 0, 'text', _render("p['last_update_time']")],
                'totals': [1, 22, 'number', None]},
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
                'header': [1, 22, 'text', _render("_('Sales Pay')")],
                'lines': [1, 0, 'text', _render("p['sls_pay']")],
                'totals': [1, 22, 'number', None]},
            'vcust_id': {
                'header': [1, 22, 'text', _render("_('Finco Code')")],
                'lines': [1, 0, 'text', _render("p['vcust_id']")],
                'totals': [1, 22, 'number', None]},
            'finco_code': {
                'header': [1, 22, 'text', _render("_('Sales Type')")],
                'lines': [1, 0, 'text', _render("p['finco_code']")],
                'totals': [1, 22, 'number', None]},
            'finco_branch': {
                'header': [1, 22, 'text', _render("_('Finco Branch')")],
                'lines': [1, 0, 'text', _render("p['finco_branch']")],
                'totals': [1, 22, 'number', None]},
            'no_po': {
                'header': [1, 22, 'text', _render("_('No PO')")],
                'lines': [1, 0, 'text', _render("p['no_po']")],
                'totals': [1, 22, 'number', None]},
            'tgl_po': {
                'header': [1, 22, 'text', _render("_('Tgl PO')")],
                'lines': [1, 0, 'text', _render("p['tgl_po']")],
                'totals': [1, 22, 'number', None]},
            'tenor': {
                'header': [1, 22, 'text', _render("_('Tenor')")],
                'lines': [1, 0, 'number', _render("p['tenor']")],
                'totals': [1, 22, 'number', None]},
            'jp_po': {
                'header': [1, 22, 'text', _render("_('JP PO')")],
                'lines': [1, 0, 'number', _render("p['jp_po']")],
                'totals': [1, 22, 'number', _render("p['jp_po']"), None, self.rt_cell_style_decimal]},
            'cust_code': {
                'header': [1, 22, 'text', _render("_('Customer Code')")],
                'lines': [1, 0, 'text', _render("p['cust_code']")],
                'totals': [1, 22, 'number', None]},
            'cust_name': {
                'header': [1, 22, 'text', _render("_('Customer Name')")],
                'lines': [1, 0, 'text', _render("p['cust_name']")],
                'totals': [1, 22, 'number', None]},
            'cabang_partner': {
                'header': [1, 20, 'text', _render("_('Cabang Partner')")],
                'lines': [1, 0, 'text', _render("p['cabang_partner']")],
                'totals': [1, 20, 'text', _render("p['cabang_partner']")]},
            'alamat_cust_name': {
                'header': [1, 22, 'text', _render("_('Alamat Customer Name')")],
                'lines': [1, 0, 'text', _render("p['alamat_cust_name']")],
                'totals': [1, 22, 'number', None]},
            'kota_cust_name': {
                'header': [1, 22, 'text', _render("_('Kota Customer Name')")],
                'lines': [1, 0, 'text', _render("p['kota_cust_name']")],
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
            'kec_cust_stnk_name': {
                'header': [1, 22, 'text', _render("_('Kec Customer STNK Name')")],
                'lines': [1, 0, 'text', _render("p['kec_cust_stnk_name']")],
                'totals': [1, 22, 'number', None]},
            'kel_cust_stnk_name': {
                'header': [1, 22, 'text', _render("_('Kel Customer STNK Name')")],
                'lines': [1, 0, 'text', _render("p['kel_cust_stnk_name']")],
                'totals': [1, 22, 'number', None]},
            'no_hp_cust_stnk': {
                'header': [1, 22, 'text', _render("_('No HP Cust STNK')")],
                'lines': [1, 0, 'text', _render("p['no_hp_cust_stnk']")],
                'totals': [1, 22, 'number', None]},
            'nik_sales_name': {
                'header': [1, 22, 'text', _render("_('NIK Sales Name')")],
                'lines': [1, 0, 'text', _render("p['nik_sales_name']")],
                'totals': [1, 22, 'number', None]},
            'sales_name': {
                'header': [1, 22, 'text', _render("_('Sales Name')")],
                'lines': [1, 0, 'text', _render("p['sales_name']")],
                'totals': [1, 22, 'number', None]},
            'job_name': {
                'header': [1, 22, 'text', _render("_('Job Name')")],
                'lines': [1, 0, 'text', _render("p['job_name']")],
                'totals': [1, 22, 'number', None]},
            'nik_sales_koor_name': {
                'header': [1, 22, 'text', _render("_('NIK Sales Coord Name')")],
                'lines': [1, 0, 'text', _render("p['nik_sales_koor_name']")],
                'totals': [1, 22, 'number', None]},
            'sales_koor_name': {
                'header': [1, 22, 'text', _render("_('Sales Coord Name')")],
                'lines': [1, 0, 'text', _render("p['sales_koor_name']")],
                'totals': [1, 22, 'number', None]},
            'spv_nik': {
                'header': [1, 22, 'text', _render("_('SPV NIK')")],
                'lines': [1, 0, 'text', _render("p['spv_nik']")],
                'totals': [1, 22, 'number', None]},
            'spv_name': {
                'header': [1, 22, 'text', _render("_('SPV Nama')")],
                'lines': [1, 0, 'text', _render("p['spv_name']")],
                'totals': [1, 22, 'number', None]},
            'partner_komisi_id': {
                'header': [1, 22, 'text', _render("_('ID Broker')")],
                'lines': [1, 0, 'text', _render("p['partner_komisi_id']")],
                'totals': [1, 22, 'number', None]},
            'partner_komisi_name': {
                'header': [1, 22, 'text', _render("_('Nama Broker')")],
                'lines': [1, 0, 'text', _render("p['partner_komisi_name']")],
                'totals': [1, 22, 'number', None]},
            'hutang_komisi_id': {
                'header': [1, 22, 'text', _render("_('Nama Hutang Komisi')")],
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
            'product_name': {
                'header': [1, 22, 'text', _render("_('Product Type')")],
                'lines': [1, 0, 'text', _render("p['product_name']")],
                'totals': [1, 22, 'number', None]},
            'product_desc': {
                'header': [1, 22, 'text', _render("_('Product Desc')")],
                'lines': [1, 0, 'text', _render("p['product_desc']")],
                'totals': [1, 22, 'number', None]},
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
            'discount_po': {
                'header': [1, 22, 'text', _render("_('Discount Konsumen')")],
                'lines': [1, 0, 'number', _render("p['discount_po']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_po']"), None, self.rt_cell_style_decimal]},
            'discount_extern_ps': {
                'header': [1, 22, 'text', _render("_('Discount Extern PS')")],
                'lines': [1, 0, 'number', _render("p['discount_extern_ps']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_extern_ps']"), None, self.rt_cell_style_decimal]},
            'discount_intern_ps': {
                'header': [1, 22, 'text', _render("_('Discount Intern PS')")],
                'lines': [1, 0, 'number', _render("p['discount_intern_ps']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_intern_ps']"), None, self.rt_cell_style_decimal]},
            'disc_quo_incl_tax_no': {
                'header': [1, 34, 'text', _render("_('Total Disc PS (Incl Tax) Diskon JP2')")],
                'lines': [1, 0, 'number', _render("p['disc_quo_incl_tax_no']"), None, self.pd_cell_style_decimal],
                'totals': [1, 34, 'number', _render("p['disc_quo_incl_tax_no']"), None, self.rt_cell_style_decimal]},
            'amount_hutang_komisi': {
                'header': [1, 22, 'text', _render("_('Hutang Komisi')")],
                'lines': [1, 0, 'number', _render("p['amount_hutang_komisi']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['amount_hutang_komisi']"), None, self.rt_cell_style_decimal]},
            'price_bbn': {
                'header': [1, 22, 'text', _render("_('Sales BBN')")],
                'lines': [1, 0, 'number', _render("p['price_bbn']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['price_bbn']"), None, self.rt_cell_style_decimal]},
            'piutang_total': {
                'header': [1, 22, 'text', _render("_('Piutang Total')")],
                'lines': [1, 0, 'number', _render("p['piutang_total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['piutang_total']"), None, self.rt_cell_style_decimal]},
            'dsb_name': {
                'header': [1, 22, 'text', _render("_('Nama SB')")],
                'lines': [1, 0, 'text', _render("p['dsb_name']")],
                'totals': [1, 22, 'number', None]},
            'dsbl_diskon_ahm': {
                'header': [1, 22, 'text', _render("_('SB AHM (Juklak)')")],
                'lines': [1, 0, 'number', _render("p['dsbl_diskon_ahm']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['dsbl_diskon_ahm']"), None, self.rt_cell_style_decimal]},
            'dsbl_diskon_md': {
                'header': [1, 22, 'text', _render("_('SB MD (Juklak)')")],
                'lines': [1, 0, 'number', _render("p['dsbl_diskon_md']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['dsbl_diskon_md']"), None, self.rt_cell_style_decimal]},
            'dsbl_diskon_dealer': {
                'header': [1, 22, 'text', _render("_('SB Dealer (Juklak)')")],
                'lines': [1, 0, 'number', _render("p['dsbl_diskon_dealer']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['dsbl_diskon_dealer']"), None, self.rt_cell_style_decimal]},
            'dsbl_diskon_finco': {
                'header': [1, 22, 'text', _render("_('SB Finco (Juklak)')")],
                'lines': [1, 0, 'number', _render("p['dsbl_diskon_finco']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['dsbl_diskon_finco']"), None, self.rt_cell_style_decimal]},
            'dsbl_diskon_others': {
                'header': [1, 22, 'text', _render("_('SB Others (Juklak)')")],
                'lines': [1, 0, 'number', _render("p['dsbl_diskon_others']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['dsbl_diskon_others']"), None, self.rt_cell_style_decimal]},
            'dsbl_total_diskon': {
                'header': [1, 22, 'text', _render("_('SB Total (Juklak)')")],
                'lines': [1, 0, 'number', _render("p['dsbl_total_diskon']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['dsbl_total_diskon']"), None, self.rt_cell_style_decimal]},
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
            'tambahan_bbn': {
                'header': [1, 22, 'text', _render("_('Tambahan BBN')")],
                'lines': [1, 0, 'number', _render("p['tambahan_bbn']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['tambahan_bbn']"), None, self.rt_cell_style_decimal]},
            'cust_corp': {
                'header': [1, 22, 'text', _render("_('Cust Corp')")],
                'lines': [1, 0, 'text', _render("p['cust_corp']")],
                'totals': [1, 22, 'number', None]},
            'product_qty': {
                'header': [1, 22, 'text', _render("_('Qty')")],
                'lines': [1, 0, 'number', _render("p['product_qty']")],
                'totals': [1, 22, 'number', _render("p['product_qty']"), None, self.rt_cell_style_decimal]},
            'qty_pic': {
                'header': [1, 22, 'text', _render("_('Qty PIC')")],
                'lines': [1, 0, 'number', _render("p['qty_pic']")],
                'totals': [1, 22, 'number', _render("p['qty_pic']"), None, self.rt_cell_style_decimal]},
            'qty_retur': {
                'header': [1, 22, 'text', _render("_('Qty Retur')")],
                'lines': [1, 0, 'number', _render("p['qty_retur']")],
                'totals': [1, 22, 'number', _render("p['qty_retur']"), None, self.rt_cell_style_decimal]},
            'net_sales': {
                'header': [1, 22, 'text', _render("_('Net Sales')")],
                'lines': [1, 0, 'number', _render("p['net_sales']")],
                'totals': [1, 22, 'number', _render("p['net_sales']"), None, self.rt_cell_style_decimal]},
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
            ws_o = wb.add_sheet('Laporan Jual SDB')
            
            for ws in [ws_o]:
                ws.panes_frozen = True
                ws.remove_splits = True

                # Landscape
                ws.portrait = 0  
                ws.fit_width_to_pages = 1
                
            row_pos_o = 0

            # set print header/footer
            for ws in [ws_o]:
                ws.header_str = self.xls_headers['standard']
                ws.footer_str = self.xls_footers['standard']

            # Company Name
            cell_style = xlwt.easyxf(_xs['left'])
            c_specs_o = [('report_name', 1, 0, 'text', _p.company.name)]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
            
            # Title
            cell_style = xlwt.easyxf(_xs['xls_title'])
            c_specs_o = [('report_name', 1, 0, 'text', 'Laporan Jual SDB')]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)

            # Tanggal
            cell_style = xlwt.easyxf(_xs['left'])
            tanggal_str = ' '.join(['Tanggal:', str(data['start_date']) + ' s.d. ' + str(data['end_date'])])
            c_specs_o = [('tanggal', 1, 0, 'text', tanggal_str)]
            row_data = self.xls_row_template(c_specs_o, ['tanggal'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)

            # Longkap
            cell_style = xlwt.easyxf(_xs['left'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, '', row_style=cell_style)
            
            # Report Column Headers
            c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'header', render_space={'_': _p._}), wanted_list_overview)
            row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.rh_cell_style, set_column_size=True)
            ws_o.set_horz_split_pos(row_pos_o)
            
            row_data_begin = row_pos_o
            
            # Columns and Rows
            no = 0
            for p in r['datas']:
                c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'lines'), wanted_list_overview)
                for x in c_specs_o :
                    if x[0] == 'no' :
                        no += 1
                        x[4] = no
                row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
            
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
            ws_o.write(row_pos_o, 17, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 18, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 19, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 20, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 21, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 22, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 23, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 24, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 25, xlwt.Formula("SUM(Z"+str(row_data_begin)+":Z"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 26, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 27, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 28, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 29, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 30, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 31, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 32, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 33, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 34, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 35, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 36, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 37, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 38, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 39, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 40, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 41, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 42, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 43, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 44, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 45, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 46, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 47, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 48, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 49, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 50, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 51, xlwt.Formula("SUM(AZ"+str(row_data_begin)+":AZ"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 52, xlwt.Formula("SUM(BA"+str(row_data_begin)+":BA"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 53, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 54, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 55, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 56, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 57, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 58, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 59, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 60, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 61, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 62, xlwt.Formula("SUM(BK"+str(row_data_begin)+":BK"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 63, xlwt.Formula("SUM(BL"+str(row_data_begin)+":BL"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 64, xlwt.Formula("SUM(BM"+str(row_data_begin)+":BM"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 65, xlwt.Formula("SUM(BN"+str(row_data_begin)+":BN"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 66, xlwt.Formula("SUM(BO"+str(row_data_begin)+":BO"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 67, xlwt.Formula("SUM(BP"+str(row_data_begin)+":BP"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 68, xlwt.Formula("SUM(BQ"+str(row_data_begin)+":BQ"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 69, xlwt.Formula("SUM(BR"+str(row_data_begin)+":BR"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 70, xlwt.Formula("SUM(BS"+str(row_data_begin)+":BS"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 71, xlwt.Formula("SUM(BT"+str(row_data_begin)+":BT"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 72, xlwt.Formula("SUM(BU"+str(row_data_begin)+":BU"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 73, xlwt.Formula("SUM(BV"+str(row_data_begin)+":BV"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 74, xlwt.Formula("SUM(BW"+str(row_data_begin)+":BW"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 75, xlwt.Formula("SUM(BX"+str(row_data_begin)+":BX"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 76, xlwt.Formula("SUM(BY"+str(row_data_begin)+":BY"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 77, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 78, xlwt.Formula("SUM(CA"+str(row_data_begin)+":CA"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 79, xlwt.Formula("SUM(CB"+str(row_data_begin)+":CB"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 80, xlwt.Formula("SUM(CC"+str(row_data_begin)+":CC"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 81, xlwt.Formula("SUM(CD"+str(row_data_begin)+":CD"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 82, xlwt.Formula("SUM(CE"+str(row_data_begin)+":CE"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 83, xlwt.Formula("SUM(CF"+str(row_data_begin)+":CF"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 84, xlwt.Formula("SUM(CG"+str(row_data_begin)+":CG"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 85, xlwt.Formula("SUM(CH"+str(row_data_begin)+":CH"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 86, xlwt.Formula("SUM(CI"+str(row_data_begin)+":CI"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 87, xlwt.Formula("SUM(CJ"+str(row_data_begin)+":CJ"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 88, xlwt.Formula("SUM(CK"+str(row_data_begin)+":CK"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 89, xlwt.Formula("SUM(CL"+str(row_data_begin)+":CL"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 90, xlwt.Formula("SUM(CM"+str(row_data_begin)+":CM"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 91, xlwt.Formula("SUM(CN"+str(row_data_begin)+":CN"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 92, xlwt.Formula("SUM(CO"+str(row_data_begin)+":CO"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 93, xlwt.Formula("SUM(CP"+str(row_data_begin)+":CP"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 94, xlwt.Formula("SUM(CQ"+str(row_data_begin)+":CQ"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 95, xlwt.Formula("SUM(CR"+str(row_data_begin)+":CR"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 96, xlwt.Formula("SUM(CS"+str(row_data_begin)+":CS"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 97, xlwt.Formula("SUM(CT"+str(row_data_begin)+":CT"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 98, xlwt.Formula("SUM(CU"+str(row_data_begin)+":CU"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 99, xlwt.Formula("SUM(CV"+str(row_data_begin)+":CV"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 100, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 101, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 102, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 103, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 104, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 105, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 106, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 107, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 108, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 109, None, self.rt_cell_style_decimal)

            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_rjualsdb_xls('report.Laporan Jual SDB', 'dealer.spk', parser = dym_report_rjualsdb_print_xls)
