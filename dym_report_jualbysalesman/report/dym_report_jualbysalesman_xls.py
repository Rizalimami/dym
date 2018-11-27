import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_jualbysalesman import dym_report_jualbysalesman_print
from openerp.tools.translate import translate
import string

class dym_report_jualbysalesman_print_xls(dym_report_jualbysalesman_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_jualbysalesman_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('dealer.sale.order')._report_xls_jualbysalesman_fields(cr, uid, context),
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US') 
        return translate(self.cr, 'report.jualbysalesman', 'report', lang, src) or src

class report_jualbysalesman_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_jualbysalesman_xls, self).__init__(name, table, rml, parser, header, store)

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
            'cabang':{
                'header': [1, 23, 'text', _render("_('Cabang')")],
                'lines': [1, 0, 'text', _render("p['cabang']")],
                'totals': [1, 23, 'number', None]},
            'salesman':{
                'header': [1, 30, 'text', _render("_('Salesman')")],
                'lines': [1, 0, 'text', _render("p['salesman']")],
                'totals': [1, 30, 'number', None]},
            'spv_name':{
                'header': [1, 30, 'text', _render("_('Sales SPV')")],
                'lines': [1, 0, 'text', _render("p['spv_name']")],
                'totals': [1, 30, 'number', None]},
            'invoice_no':{
                'header': [1, 25, 'text', _render("_('Faktur')")],
                'lines': [1, 0, 'text', _render("p['invoice_no']")],
                'totals': [1, 25, 'number', None]},
            'invoice_date':{
                'header': [1, 15, 'text', _render("_('Tgl Faktur')")],
                'lines': [1, 0, 'text', _render("p['invoice_date']")],
                'totals': [1, 15, 'number', None]},
            'faktur':{
                'header': [1, 25, 'text', _render("_('DSM')")],
                'lines': [1, 0, 'text', _render("p['faktur']")],
                'totals': [1, 25, 'number', None]},
            'date':{
                'header': [1, 15, 'text', _render("_('Tgl DSM')")],
                'lines': [1, 0, 'text', _render("p['date']")],
                'totals': [1, 15, 'number', None]},
            'customer':{
                'header': [1, 40, 'text', _render("_('Customer')")],
                'lines': [1, 0, 'text', _render("p['customer']")],
                'totals': [1, 40, 'number', None]},
            'motor':{
                'header': [1, 25, 'text', _render("_('Motor')")],
                'lines': [1, 0, 'text', _render("p['motor']")],
                'totals': [1, 25, 'number', None]},
            'is_cod':{
                'header': [1, 16, 'text', _render("_('Payment Type')")],
                'lines': [1, 0, 'text', _render("p['is_cod']")],
                'totals': [1, 16, 'number', None]},
            'no_mesin':{
                'header': [1, 16, 'text', _render("_('No. Mesin')")],
                'lines': [1, 0, 'text', _render("p['no_mesin']")],
                'totals': [1, 16, 'number', None]},
            'harga_unit':{
                'header': [1, 17, 'text', _render("_('Harga/Unit')")],
                'lines': [1, 0, 'number', _render("p['harga_unit']"), None, self.pd_cell_style_decimal],
                'totals': [1, 17, 'number', _render("p['harga_unit']")]},
            'disc_konsumen':{
                'header': [1, 18, 'text', _render("_('Diskon Konsumen')")],
                'lines': [1, 0, 'number', _render("p['disc_konsumen']"), None, self.pd_cell_style_decimal],
                'totals': [1, 18, 'number', _render("p['disc_konsumen']")]},
            'disc_intern':{
                'header': [1, 14, 'text', _render("_('Diskon Intern')")],
                'lines': [1, 0, 'number', _render("p['disc_intern']"), None, self.pd_cell_style_decimal],
                'totals': [1, 14, 'number', _render("p['disc_intern']")]},
            'disc_extern':{
                'header': [1, 14, 'text', _render("_('Diskon Extern')")],
                'lines': [1, 0, 'number', _render("p['disc_extern']"), None, self.pd_cell_style_decimal],
                'totals': [1, 14, 'number', _render("p['disc_extern']")]},
            'broker':{
                'header': [1, 14, 'text', _render("_('Broker')")],
                'lines': [1, 0, 'number', _render("p['broker']"), None, self.pd_cell_style_decimal],
                'totals': [1, 14, 'number', _render("p['broker']")]},
            'total':{
                'header': [1, 18, 'text', _render("_('Total')")],
                'lines': [1, 0, 'number', _render("p['total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 18, 'number', _render("p['total']")]},
            'ar_days':{
                'header': [1, 9, 'text', _render("_('AR Days')")],
                'lines': [1, 0, 'number', _render("p['ar_days']")],
                'totals': [1, 9, 'number', _render("p['ar_days']")]},
            'lunas':{
                'header': [1, 14, 'text', _render("_('Lunas')")],
                'lines': [1, 0, 'text', _render("p['lunas']")],
                'totals': [1, 14, 'text', _render("p['lunas']")]},
            'finco_code': {
                'header': [1, 22, 'text', _render("_('Sales Type')")],
                'lines': [1, 0, 'text', _render("p['finco_code']")],
                'totals': [1, 22, 'number', None]},
            'finco_branch': {
                'header': [1, 22, 'text', _render("_('Finco Branch')")],
                'lines': [1, 0, 'text', _render("p['finco_branch']")],
                'totals': [1, 22, 'number', None]},
            'product_qty': {
                'header': [1, 22, 'text', _render("_('Qty')")],
                'lines': [1, 0, 'number', _render("p['product_qty']")],
                'totals': [1, 22, 'number', _render("p['product_qty']"), None, self.rt_cell_style_decimal]},
        }
    
    def format_tanggal(self, tanggal):
        return datetime.strptime(str(tanggal),'%Y-%m-%d').strftime('%d-%m-%Y')

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        self.col_specs_template_overview.update({})
        _ = _p._

        for r in _p.reports:
            ws_o = wb.add_sheet('Laporan Penjualan By Salesman')
            
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
            c_specs_o = [('report_name', 1, 0, 'text', 'Laporan Penjualan By Salesman')]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)

            # Tanggal
            cell_style = xlwt.easyxf(_xs['left'])
            tanggal_str = ' '.join(['Tanggal:', self.format_tanggal(data['start_date']) + ' s.d. ' + self.format_tanggal(data['end_date'])])
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
            ws_o.write(row_pos_o, 0, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)   
            ws_o.write(row_pos_o, 2, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 3, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 4, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 5, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 6, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 7, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 8, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 9, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 10, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 11, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 12, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 13, xlwt.Formula("SUM(N"+str(row_data_begin)+":N"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 15, xlwt.Formula("SUM(P"+str(row_data_begin)+":P"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 16, xlwt.Formula("SUM(Q"+str(row_data_begin)+":Q"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 17, xlwt.Formula("SUM(R"+str(row_data_begin)+":R"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 18, xlwt.Formula("SUM(S"+str(row_data_begin)+":S"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 19, xlwt.Formula("SUM(T"+str(row_data_begin)+":T"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 20, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 21, None, self.ph_cell_style)
                        
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, time.strftime('%d-%m-%Y %H:%M:%S') + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_jualbysalesman_xls('report.Laporan Penjualan By Salesman', 'dealer.sale.order', parser = dym_report_jualbysalesman_print_xls)
