import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_penjualan_non_mt import dym_report_penjualan_non_mt_print
from openerp.tools.translate import translate
import string

class dym_report_penjualan_non_mt_print_xls(dym_report_penjualan_non_mt_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_penjualan_non_mt_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('dealer.sale.order')._report_xls_penjualan_non_mt_fields(cr, uid, context),
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US') 
        return translate(self.cr, 'report.penjualan.non.mt', 'report', lang, src) or src

class report_penjualan_non_mt_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_penjualan_non_mt_xls, self).__init__(name, table, rml, parser, header, store)

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
            'cabang': {
                'header': [1, 22, 'text', _render("_('Cabang')")],
                'lines': [1, 0, 'text', _render("p['cabang']")],
                'totals': [1, 22, 'text', None]},
            'faktur': {
                'header': [1, 22, 'text', _render("_('Faktur')")],
                'lines': [1, 0, 'text', _render("p['faktur']")],
                'totals': [1, 22, 'text', None]},
            'date': {
                'header': [1, 22, 'text', _render("_('Date')")],
                'lines': [1, 0, 'text', _render("p['date']")],
                'totals': [1, 22, 'text', None]},
            'customer': {
                'header': [1, 22, 'text', _render("_('Customer')")],
                'lines': [1, 0, 'text', _render("p['customer']")],
                'totals': [1, 22, 'text', None]},
            'motor': {
                'header': [1, 22, 'text', _render("_('Motor')")],
                'lines': [1, 0, 'text', _render("p['motor']")],
                'totals': [1, 22, 'number', None]},
            'no_mesin': {
                'header': [1, 22, 'text', _render("_('No. Mesin')")],
                'lines': [1, 0, 'text', _render("p['no_mesin']")],
                'totals': [1, 22, 'text', None]},
            'salesman': {
                'header': [1, 22, 'text', _render("_('Salesman')")],
                'lines': [1, 0, 'text', _render("p['salesman']")],
                'totals': [1, 22, 'text', None]},
            'division': {
                'header': [1, 22, 'text', _render("_('Division')")],
                'lines': [1, 0, 'text', _render("p['division']")],
                'totals': [1, 22, 'text', None]},
            'disc_konsumen': {
                'header': [1, 22, 'text', _render("_('Disc. Konsumen')")],
                'lines': [1, 0, 'number', _render("p['disc_konsumen']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},  
            'disc_intern': {
                'header': [1, 22, 'text', _render("_('Disc. Intern')")],
                'lines': [1, 0, 'number', _render("p['disc_intern']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},  
            'disc_extern': {
                'header': [1, 22, 'text', _render("_('Disc. Extern')")],
                'lines': [1, 0, 'number', _render("p['disc_extern']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},  
            'broker': {
                'header': [1, 22, 'text', _render("_('Broker')")],
                'lines': [1, 0, 'number', _render("p['broker']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},  
            'total': {
                'header': [1, 22, 'text', _render("_('Total')")],
                'lines': [1, 0, 'number', _render("p['total']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},  
            'ar_days': {
                'header': [1, 22, 'text', _render("_('A/R Days')")],
                'lines': [1, 0, 'number', _render("p['ar_days']")],
                'totals': [1, 0, 'text', None]},  
            'lunas': {
                'header': [1, 22, 'text', _render("_('Lunas')")],
                'lines': [1, 0, 'text', _render("p['lunas'] or 'Belum Lunas'")],
                'totals': [1, 22, 'text', None]},                
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        self.col_specs_template_overview.update({})
        _ = _p._

        for r in _p.reports:
            ws_o = wb.add_sheet('Laporan Penjualan Non MT')
            
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
            c_specs_o = [('report_name', 1, 0, 'text', 'Laporan Penjualan Non MT')]
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

report_penjualan_non_mt_xls('report.Laporan Penjualan Non MT', 'dealer.sale.order', parser = dym_report_penjualan_non_mt_print_xls)
