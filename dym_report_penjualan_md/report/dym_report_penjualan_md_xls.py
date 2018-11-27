import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_penjualan_md import dym_report_penjualan_md_print
from openerp.tools.translate import translate
import string

_ir_translation_name = 'report.penjualan.md'

class dym_report_penjualan_md_print_xls(dym_report_penjualan_md_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_penjualan_md_print_xls, self).__init__(cr, uid, name, context=context)
        so_obj = self.pool.get('sale.order')
        self.context = context
        wl_overview = so_obj._report_xls_penjualan_md_fields(cr, uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': wl_overview,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src

class report_penjualan_md_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_penjualan_md_xls, self).__init__(name, table, rml, parser, header, store)

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
            'branch_code': {
                'header': [1, 22, 'text', _render("_('Branch Code')")],
                'lines': [1, 0, 'text', _render("p['branch_code']")],
                'totals': [1, 22, 'text', _render("_('Sub Totals')")]},
            'branch_name': {
                'header': [1, 22, 'text', _render("_('Branch Name')")],
                'lines': [1, 0, 'text', _render("p['branch_name']")],
                'totals': [1, 22, 'number', None]},
            'name': {
                'header': [1, 22, 'text', _render("_('SO Number')")],
                'lines': [1, 0, 'text', _render("p['name']")],
                'totals': [1, 22, 'number', None]},
            'state': {
                'header': [1, 22, 'text', _render("_('State')")],
                'lines': [1, 0, 'text', _render("p['state']")],
                'totals': [1, 22, 'number', None]},
            'date_order': {
                'header': [1, 22, 'text', _render("_('Date')")],
                'lines': [1, 0, 'text', _render("p['date_order']")],
                'totals': [1, 22, 'number', None]},
            'cust_code': {
                'header': [1, 22, 'text', _render("_('Customer Code')")],
                'lines': [1, 0, 'text', _render("p['cust_code']")],
                'totals': [1, 22, 'number', None]},
            'cust_name': {
                'header': [1, 22, 'text', _render("_('Customer Name')")],
                'lines': [1, 0, 'text', _render("p['cust_name']")],
                'totals': [1, 22, 'number', None]},
            'type': {
                'header': [1, 22, 'text', _render("_('Type')")],
                'lines': [1, 0, 'text', _render("p['type']")],
                'totals': [1, 22, 'number', None]},
            'warna': {
                'header': [1, 22, 'text', _render("_('Color')")],
                'lines': [1, 0, 'text', _render("p['warna']")],
                'totals': [1, 22, 'number', None]},
            'qty': {
                'header': [1, 22, 'text', _render("_('Qty')")],
                'lines': [1, 0, 'number', _render("p['qty']")],
                'totals': [1, 22, 'number', _render("p['qty']"), None, self.rt_cell_style_decimal]},
            
            'hpp': {
                'header': [1, 22, 'text', _render("_('HPP')")],
                'lines': [1, 0, 'number', _render("p['hpp']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['hpp']"), None, self.rt_cell_style_decimal]},
            'harga_jual': {
                'header': [1, 22, 'text', _render("_('Harga Jual')")],
                'lines': [1, 0, 'number', _render("p['harga_jual']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['harga_jual']"), None, self.rt_cell_style_decimal]},
            'disc': {
                'header': [1, 22, 'text', _render("_('Disc (%)')")],
                'lines': [1, 0, 'number', _render("p['disc']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['disc']"), None, self.rt_cell_style_decimal]},
            'harga_jual_excl_tax': {
                'header': [1, 22, 'text', _render("_('Harga Jual Excl Tax')")],
                'lines': [1, 0, 'number', _render("p['harga_jual_excl_tax']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['harga_jual_excl_tax']"), None, self.rt_cell_style_decimal]},
            'total_hpp': {
                'header': [1, 22, 'text', _render("_('Total HPP')")],
                'lines': [1, 0, 'number', _render("p['total_hpp']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['total_hpp']"), None, self.rt_cell_style_decimal]},
            'nett_sales': {
                'header': [1, 22, 'text', _render("_('Sales')")],
                'lines': [1, 0, 'number', _render("p['nett_sales']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['nett_sales']"), None, self.rt_cell_style_decimal]},
            'discount_cash_avg': {
                'header': [1, 22, 'text', _render("_('Disc Cash (Avg)')")],
                'lines': [1, 0, 'number', _render("p['discount_cash_avg']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_cash_avg']"), None, self.rt_cell_style_decimal]},
            'discount_lain_avg': {
                'header': [1, 22, 'text', _render("_('Disc Lain (Avg)')")],
                'lines': [1, 0, 'number', _render("p['discount_lain_avg']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_lain_avg']"), None, self.rt_cell_style_decimal]},
            'discount_program_avg': {
                'header': [1, 22, 'text', _render("_('Disc Program (Avg)')")],
                'lines': [1, 0, 'number', _render("p['discount_program_avg']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_program_avg']"), None, self.rt_cell_style_decimal]},
            'dpp': {
                'header': [1, 22, 'text', _render("_('DPP')")],
                'lines': [1, 0, 'number', _render("p['dpp']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['dpp']"), None, self.rt_cell_style_decimal]},
            'tax': {
                'header': [1, 22, 'text', _render("_('Tax')")],
                'lines': [1, 0, 'number', _render("p['tax']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['tax']"), None, self.rt_cell_style_decimal]},
            'total': {
                'header': [1, 22, 'text', _render("_('Total Piutang')")],
                'lines': [1, 0, 'number', _render("p['total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['total']"), None, self.rt_cell_style_decimal]},
            'gp': {
                'header': [1, 22, 'text', _render("_('Gross Profit')")],
                'lines': [1, 0, 'number', _render("p['gp']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['gp']"), None, self.rt_cell_style_decimal]},
            'gp_avg': {
                'header': [1, 22, 'text', _render("_('Gross Profit (Avg)')")],
                'lines': [1, 0, 'number', _render("p['gp_avg']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['gp_avg']"), None, self.rt_cell_style_decimal]},
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
            'faktur_pajak': {
                'header': [1, 22, 'text', _render("_('Faktur Pajak')")],
                'lines': [1, 0, 'text', _render("p['faktur_pajak']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['faktur_pajak']")]},
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
                ('report_name', 1, 0, 'text', 'Laporan Penjualan MD'),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            
            ## Start Date & End Date ##
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join(
                [_('Tanggal'), _('-' if data['start_date'] == False else str(data['end_date'])), _('s/d'), _('-' if data['end_date'] == False else str(data['end_date'])),
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
            no = 0
            for p in r['so_ids']:
                c_specs_o = map(
                    lambda x: self.render(
                        x, self.col_specs_template_overview, 'lines'),
                    wanted_list_overview)
                for x in c_specs_o :
                    if x[0] == 'no' :
                        no += 1
                        x[4] = no
                row_data = self.xls_row_template(
                    c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
            
            row_data_end = row_pos_o
            
            # Totals
            ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 1, 'Sub Totals', self.ph_cell_style)   
            ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
            ws_o.set_vert_split_pos(3)
            ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)   
            ws_o.write(row_pos_o, 6, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 7, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 8, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 9, None, self.rt_cell_style_decimal)   
            ws_o.write(row_pos_o, 10, xlwt.Formula("SUM(K"+str(row_data_begin)+":K"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 11, xlwt.Formula("SUM(L"+str(row_data_begin)+":L"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 12, xlwt.Formula("SUM(M"+str(row_data_begin)+":M"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 13, xlwt.Formula("SUM(N"+str(row_data_begin)+":N"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 15, xlwt.Formula("SUM(P"+str(row_data_begin)+":P"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 16, xlwt.Formula("SUM(Q"+str(row_data_begin)+":Q"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 17, xlwt.Formula("SUM(R"+str(row_data_begin)+":R"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 18, xlwt.Formula("SUM(S"+str(row_data_begin)+":S"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 19, xlwt.Formula("SUM(T"+str(row_data_begin)+":T"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 20, xlwt.Formula("SUM(U"+str(row_data_begin)+":U"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 21, xlwt.Formula("SUM(V"+str(row_data_begin)+":V"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 22, xlwt.Formula("SUM(W"+str(row_data_begin)+":W"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 23, xlwt.Formula("SUM(X"+str(row_data_begin)+":X"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 24, xlwt.Formula("SUM(Y"+str(row_data_begin)+":Y"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 25, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 26, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 27, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 28, None, self.rt_cell_style_decimal)
            
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, _p.report_date + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_penjualan_md_xls(
    'report.Laporan Penjualan MD',
    'sale.order',
    parser = dym_report_penjualan_md_print_xls)
