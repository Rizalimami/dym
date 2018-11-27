import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_control_bank_book import dym_report_control_bank_book_print
from openerp.tools.translate import translate
import string

class dym_report_control_bank_book_print_xls(dym_report_control_bank_book_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_control_bank_book_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('account.move.line')._report_xls_control_bank_book_fields(cr, uid, context),
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US') 
        return translate(self.cr, 'report.control', 'report', lang, src) or src

class report_control_bank_book_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_control_bank_book_xls, self).__init__(name, table, rml, parser, header, store)

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
            'period': {
                'header': [1, 22, 'text', _render("_('Periode')")],
                'lines': [1, 0, 'text', _render("p['period']")],
                'totals': [1, 22, 'text', None]},
            'company_name': {
                'header': [1, 22, 'text', _render("_('Company')")],
                'lines': [1, 0, 'text', _render("p['company_name']")],
                'totals': [1, 22, 'text', None]},
            'branch_name': {
                'header': [1, 22, 'text', _render("_('Branch')")],
                'lines': [1, 0, 'text', _render("p['branch_name']")],
                'totals': [1, 22, 'text', None]},
            'account_code': {
                'header': [1, 22, 'text', _render("_('COA')")],
                'lines': [1, 0, 'text', _render("p['account_code']")],
                'totals': [1, 22, 'number', None]},
            'account_name': {
                'header': [1, 22, 'text', _render("_('Deskripsi COA')")],
                'lines': [1, 0, 'text', _render("p['account_name']")],
                'totals': [1, 22, 'text', None]},
            'saldo_bank_book': {
                'header': [1, 22, 'text', _render("_('Saldo Kas/Bank Menurut Kas dan Bank Book')")],
                'lines': [1, 0, 'number', _render("p['saldo_bank_book']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},  
            'saldo_general_ledger': {
                'header': [1, 22, 'text', _render("_('Saldo Kas/Bank Menurut General Ledger')")],
                'lines': [1, 0, 'number', _render("p['saldo_general_ledger']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},  
            'penjelasan': {
                'header': [1, 22, 'text', _render("_('Penjelasan')")],
                'lines': [1, 0, 'text', _render("p['penjelasan']")],
                'totals': [1, 22, 'text', None]},
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        self.col_specs_template_overview.update({})
        _ = _p._

        for r in _p.reports:
            ws_o = wb.add_sheet('Laporan Kontrol Kas dan Bank')
            
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
            c_specs_o = [('report_name', 1, 0, 'text', 'Laporan Kontrol Kas dan Bank')]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
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
            ws_o.write(row_pos_o, 3, xlwt.Formula("SUM(D"+str(row_data_begin)+":D"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_control_bank_book_xls('report.Laporan Kontrol Kas dan Bank', 'account.move.line', parser = dym_report_control_bank_book_print_xls)
