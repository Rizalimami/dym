import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_rjualworsor import dym_report_rjualworsor_print
from openerp.tools.translate import translate
import string

class dym_report_rjualworsor_print_xls(dym_report_rjualworsor_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_rjualworsor_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('dym.work.order')._report_xls_rjualworsor_fields(cr, uid, context),
            'wanted_list_overview_detail': self.pool.get('dym.work.order')._report_xls_rjualworsor_detail_fields(cr, uid, context),
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US') 
        return translate(self.cr, 'report.rjualworsor', 'report', lang, src) or src

class report_rjualworsor_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_rjualworsor_xls, self).__init__(name, table, rml, parser, header, store)

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
            'branch_code': {
                'header': [1, 22, 'text', _render("_('Branch Code')")],
                'lines': [1, 0, 'text', _render("p['branch_code']")],
                'totals': [1, 22, 'text', _render("_('Total')")]},
            'branch_name': {
                'header': [1, 22, 'text', _render("_('Branch Name')")],
                'lines': [1, 0, 'text', _render("p['branch_name']")],
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
            'name': {
                'header': [1, 22, 'text', _render("_('WO Number')")],
                'lines': [1, 0, 'text', _render("p['name']")],
                'totals': [1, 22, 'number', None]},
            'invoice_name': {
                'header': [1, 22, 'text', _render("_('Invoice Name')")],
                'lines': [1, 0, 'text', _render("p['invoice_name']")],
                'totals': [1, 22, 'number', None]},
            'invoice_date': {
                'header': [1, 22, 'text', _render("_('Invoice Date')")],
                'lines': [1, 0, 'text', _render("p['invoice_date']")],
                'totals': [1, 22, 'number', None]},
            'state': {
                'header': [1, 22, 'text', _render("_('State')")],
                'lines': [1, 0, 'text', _render("p['state']")],
                'totals': [1, 22, 'number', None]},
            'date_order': {
                'header': [1, 22, 'text', _render("_('Date')")],
                'lines': [1, 0, 'text', _render("p['date_order']")],
                'totals': [1, 22, 'number', None]},
            'sales_name': {
                'header': [1, 22, 'text', _render("_('Sales/Mechanic Name')")],
                'lines': [1, 0, 'text', _render("p['sales_name']")],
                'totals': [1, 22, 'number', None]},
            'job_name': {
                'header': [1, 22, 'text', _render("_('Job Name')")],
                'lines': [1, 0, 'text', _render("p['job_name']")],
                'totals': [1, 22, 'number', None]},
            'cust_name': {
                'header': [1, 22, 'text', _render("_('Customer Name')")],
                'lines': [1, 0, 'text', _render("p['cust_name']")],
                'totals': [1, 22, 'number', None]},
            'product_name': {
                'header': [1, 22, 'text', _render("_('Nama Product')")],
                'lines': [1, 0, 'text', _render("p['product_name']")],
                'totals': [1, 22, 'number', None]},
            'product_type': {
                'header': [1, 22, 'text', _render("_('Type Product')")],
                'lines': [1, 0, 'text', _render("p['product_type']")],
                'totals': [1, 22, 'number', None]},
            'product_desc': {
                'header': [1, 22, 'text', _render("_('Desc Product')")],
                'lines': [1, 0, 'text', _render("p['product_desc']")],
                'totals': [1, 22, 'number', None]},
            'supply_qty': {
                'header': [1, 22, 'text', _render("_('Qty Supply')")],
                'lines': [1, 0, 'number', _render("p['supply_qty']")],
                'totals': [1, 22, 'number', _render("p['supply_qty']"), None, self.rt_cell_style_decimal]},
            'product_qty': {
                'header': [1, 22, 'text', _render("_('Qty Demand')")],
                'lines': [1, 0, 'number', _render("p['product_qty']")],
                'totals': [1, 22, 'number', _render("p['product_qty']"), None, self.rt_cell_style_decimal]},
            'price_unit': {
                'header': [1, 22, 'text', _render("_('Harga Satuan')")],
                'lines': [1, 0, 'number', _render("p['price_unit']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['price_unit']"), None, self.rt_cell_style_decimal]},
            'discount': {
                'header': [1, 22, 'text', _render("_('Discount Sum')")],
                'lines': [1, 0, 'number', _render("p['discount']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount']"), None, self.rt_cell_style_decimal]},
            'discount_perpcs': {
                'header': [1, 22, 'text', _render("_('Discount Per Pcs')")],
                'lines': [1, 0, 'number', _render("p['discount_perpcs']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_perpcs']"), None, self.rt_cell_style_decimal]},
            'discount_program': {
                'header': [1, 22, 'text', _render("_('Discount Program')")],
                'lines': [1, 0, 'number', _render("p['discount_program']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_program']"), None, self.rt_cell_style_decimal]},
            'discount_bundle': {
                'header': [1, 22, 'text', _render("_('Discount Bundle')")],
                'lines': [1, 0, 'number', _render("p['discount_bundle']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_bundle']"), None, self.rt_cell_style_decimal]},
            'price_subtotal': {
                'header': [1, 22, 'text', _render("_('AR')")],
                'lines': [1, 0, 'number', _render("p['price_subtotal']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['price_subtotal']"), None, self.rt_cell_style_decimal]},
            'dpp': {
                'header': [1, 22, 'text', _render("_('DPP')")],
                'lines': [1, 0, 'number', _render("p['dpp']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['dpp']"), None, self.rt_cell_style_decimal]},
            'ppn': {
                'header': [1, 22, 'text', _render("_('PPN')")],
                'lines': [1, 0, 'number', _render("p['ppn']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['ppn']"), None, self.rt_cell_style_decimal]},
            'force_cogs': {
                'header': [1, 22, 'text', _render("_('HPP')")],
                'lines': [1, 0, 'number', _render("p['force_cogs']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['force_cogs']"), None, self.rt_cell_style_decimal]},
            'tgl_bayar': {
                'header': [1, 22, 'text', _render("_('Tgl Bayar')")],
                'lines': [1, 0, 'text', _render("p['tgl_bayar']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['tgl_bayar']")]},
            'bayar': {
                'header': [1, 22, 'text', _render("_('Bayar')")],
                'lines': [1, 0, 'number', _render("p['bayar']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['bayar']"), None, self.rt_cell_style_decimal]},
            'ar_bayar': {
                'header': [1, 22, 'text', _render("_('(AR) Bayar')")],
                'lines': [1, 0, 'number', _render("p['ar_bayar']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['ar_bayar']"), None, self.rt_cell_style_decimal]},
            'ar': {
                'header': [1, 22, 'text', _render("_('(AR)')")],
                'lines': [1, 0, 'number', _render("p['ar']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['ar']"), None, self.rt_cell_style_decimal]},
            'categ_name': {
                'header': [1, 22, 'text', _render("_('Category Name')")],
                'lines': [1, 0, 'text', _render("p['categ_name']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['categ_name']")]},
            'category': {
                'header': [1, 22, 'text', _render("_('Category')")],
                'lines': [1, 0, 'text', _render("p['category']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['category']")]},
            'faktur_pajak': {
                'header': [1, 22, 'text', _render("_('Faktur Pajak')")],
                'lines': [1, 0, 'text', _render("p['faktur_pajak']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['faktur_pajak']")]},
            'oos_number': {
                'header': [1, 25, 'text', _render("_('No. OOS')")],
                'lines': [1, 0, 'text', _render("p['oos_number']")],
                'totals': [1, 25, 'number', None]},
            'oos_tgl': {
                'header': [1, 22, 'text', _render("_('Tanggal OOS')")],
                'lines': [1, 0, 'text', _render("p['oos_tgl']")],
                'totals': [1, 22, 'number', None]},
            'dno_number': {
                'header': [1, 25, 'text', _render("_('No. DNO')")],
                'lines': [1, 0, 'text', _render("p['dno_number']")],
                'totals': [1, 25, 'number', None]},
            'dno_tgl': {
                'header': [1, 22, 'text', _render("_('Tanggal DNO')")],
                'lines': [1, 0, 'text', _render("p['dno_tgl']")],
                'totals': [1, 22, 'number', None]},
            'tipe_konsumen': {
                'header': [1, 25, 'text', _render("_('Tipe Konsumen')")],
                'lines': [1, 0, 'text', _render("p['tipe_konsumen']")],
                'totals': [1, 25, 'number', None]},
            'tipe_transaksi': {
                'header': [1, 25, 'text', _render("_('Tipe Transaksi')")],
                'lines': [1, 0, 'text', _render("p['tipe_transaksi']")],
                'totals': [1, 25, 'number', None]},
            'tgl_beli': {
                'header': [1, 22, 'text', _render("_('Tanggal Pembelian')")],
                'lines': [1, 0, 'text', _render("p['tgl_beli']")],
                'totals': [1, 22, 'number', None]},
            'sa': {
                'header': [1, 22, 'text', _render("_('SA')")],
                'lines': [1, 0, 'text', _render("p['sa']")],
                'totals': [1, 22, 'number', None]},
            'mekanik': {
                'header': [1, 22, 'text', _render("_('Mekanik')")],
                'lines': [1, 0, 'text', _render("p['mekanik']")],
                'totals': [1, 22, 'number', None]},
            'km': {
                'header': [1, 22, 'text', _render("_('KM')")],
                'lines': [1, 0, 'number', _render("p['km']")],
                'totals': [1, 22, 'number', None]},
            'total': {
                'header': [1, 22, 'text', _render("_('Total')")],
                'lines': [1, 0, 'number', _render("p['total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['total']"), None, self.rt_cell_style_decimal]},
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        wanted_list_overview_detail = _p.wanted_list_overview_detail
        self.col_specs_template_overview.update({})
        _ = _p._

        for r in _p.reports:
            ws_o = wb.add_sheet('Laporan Jual WOR-SOR')
            
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
            c_specs_o = [('report_name', 1, 0, 'text', 'Laporan Jual WOR/SOR')]
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
            print "------------------------------------------------------------", data['detail'], "----------------------------------------------------------"
            # Report Column Headers
            if data['detail'] == False:
                c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'header', render_space={'_': _p._}), wanted_list_overview)
            else:
                c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'header', render_space={'_': _p._}), wanted_list_overview_detail)
            row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.rh_cell_style, set_column_size=True)
            ws_o.set_horz_split_pos(row_pos_o)
            
            row_data_begin = row_pos_o
            
            # Columns and Rows
            no = 0
            if data['detail'] == False:
                for p in r['datas']:
                    c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'lines'), wanted_list_overview)
                    for x in c_specs_o :
                        if x[0] == 'no' :
                            no += 1
                            x[4] = no
                    row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
                    row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
            else:
                for p in r['datas']:
                    c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'lines'), wanted_list_overview_detail)
                    for x in c_specs_o :
                        if x[0] == 'no' :
                            no += 1
                            x[4] = no
                    row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
                    row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
            
            row_data_end = row_pos_o
                        
            if data['detail'] == True:
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
                ws_o.write(row_pos_o, 19, xlwt.Formula("SUM(T"+str(row_data_begin)+":T"+str(row_data_end)+")"), self.rt_cell_style_decimal)
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
                ws_o.write(row_pos_o, 30, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 31, xlwt.Formula("SUM(AF"+str(row_data_begin)+":AF"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            
            else:
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
                ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                

            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_rjualworsor_xls('report.Laporan Jual WOR/SOR', 'dym.work.order', parser = dym_report_rjualworsor_print_xls)
