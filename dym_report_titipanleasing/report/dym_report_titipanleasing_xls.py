import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_titipanleasing import dym_report_titipanleasing_print
from openerp.tools.translate import translate
import string

class dym_report_titipanleasing_print_xls(dym_report_titipanleasing_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_titipanleasing_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('dym.branch')._report_xls_titipanleasing_fields(cr, uid, context),
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US') 
        return translate(self.cr, 'report.titipanleasing', 'report', lang, src) or src

class report_titipanleasing_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_titipanleasing_xls, self).__init__(name, table, rml, parser, header, store)

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
                'header': [1, 22, 'text', _render("_('Branch Status')")],
                'lines': [1, 0, 'text', _render("p['branch_status']")],
                'totals': [1, 22, 'text', _render("_('Total')")]},
            'cabang': {
                'header': [1, 22, 'text', _render("_('Cabang')")],
                'lines': [1, 0, 'text', _render("p['cabang']")],
                'totals': [1, 22, 'number', None]},
            'divisi': {
                'header': [1, 22, 'text', _render("_('Divisi')")],
                'lines': [1, 0, 'text', _render("p['divisi']")],
                'totals': [1, 22, 'number', None]},
            'nama_leasing': {
                'header': [1, 22, 'text', _render("_('Nama Leasing')")],
                'lines': [1, 0, 'text', _render("p['nama_leasing']")],
                'totals': [1, 22, 'number', None]},
            'ket': {
                'header': [1, 22, 'text', _render("_('Keterangan')")],
                'lines': [1, 0, 'text', _render("p['ket']")],
                'totals': [1, 22, 'number', None]},
            'payment_method': {
                'header': [1, 22, 'text', _render("_('Payment Method')")],
                'lines': [1, 0, 'text', _render("p['payment_method']")],
                'totals': [1, 22, 'number', None]},
            'tanggal': {
                'header': [1, 22, 'text', _render("_('Tanggal')")],
                'lines': [1, 0, 'text', _render("p['tanggal']")],
                'totals': [1, 22, 'number', None]},
            'no_cde': {
                'header': [1, 22, 'text', _render("_('No. CDE')")],
                'lines': [1, 0, 'text', _render("p['no_cde']")],
                'totals': [1, 22, 'number', None]},
            'nilai_titipan': {
                'header': [1, 22, 'text', _render("_('Nilai Titipan')")],
                'lines': [1, 0, 'number', _render("p['nilai_titipan']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['nilai_titipan']"), None, self.pd_cell_style_decimal]},
            'alokasi_tanggal': {
                'header': [1, 22, 'text', _render("_('Tanggal Alokasi')")],
                'lines': [1, 0, 'text', _render("p['alokasi_tanggal']")],
                'totals': [1, 22, 'number', None]},
            'alokasi_no': {
                'header': [1, 22, 'text', _render("_('No. Alokasi')")],
                'lines': [1, 0, 'text', _render("p['alokasi_no']")],
                'totals': [1, 22, 'number', None]},
            'cpa_no': {
                'header': [1, 22, 'text', _render("_('No. CPA')")],
                'lines': [1, 0, 'text', _render("p['cpa_no']")],
                'totals': [1, 22, 'number', None]},
            'nilai_alokasi': {
                'header': [1, 22, 'text', _render("_('Nilai Alokasi')")],
                'lines': [1, 0, 'number', _render("p['nilai_alokasi']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['nilai_alokasi']"), None, self.pd_cell_style_decimal]},
            'sisa_titipan': {
                'header': [1, 22, 'text', _render("_('Sisa Titipan')")],
                'lines': [1, 0, 'number', _render("p['sisa_titipan']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['sisa_titipan']"), None, self.pd_cell_style_decimal]},
            'a_code':{
               'header': [1, 22, 'text', _render("_('No. Account')")],
               'lines': [1, 0, 'text', _render("p['a_code']")],
               'totals': [1, 22, 'text', None]},
            'a_name':{
               'header': [1, 22, 'text', _render("_('Nama Account')")],
               'lines': [1, 0, 'text', _render("p['a_name']")],
               'totals': [1, 22, 'text', None]},
            'aa_combi' :{
                'header': [1, 22, 'text', _render("_('Analytic Combination')")],
                'lines': [1, 0, 'text', _render("p['aa_combi']")],
                'totals': [1, 22, 'number', None]},
            'aa_company' :{
                'header': [1, 22, 'text', _render("_('Analytic Company')")],
                'lines': [1, 0, 'text', _render("p['aa_company']")],
                'totals': [1, 22, 'number', None]},
            'aa_bisnisunit' :{
                'header': [1, 22, 'text', _render("_('Analytic Bisnis Unit')")],
                'lines': [1, 0, 'text', _render("p['aa_bisnisunit']")],
                'totals': [1, 22, 'number', None]},
            'aa_branch' :{
                'header': [1, 22, 'text', _render("_('Analytic Branch')")],
                'lines': [1, 0, 'text', _render("p['aa_branch']")],
                'totals': [1, 22, 'number', None]},
            'aa_costcenter' :{
                'header': [1, 22, 'text', _render("_('Analytic Cost Center')")],
                'lines': [1, 0, 'text', _render("p['aa_costcenter']")],
                'totals': [1, 22, 'number', None]},
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        self.col_specs_template_overview.update({})
        _ = _p._

        for r in _p.reports:
            ws_o = wb.add_sheet('Laporan Titipan Leasing')
            
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
            c_specs_o = [('report_name', 1, 0, 'text', 'Laporan Titipan Leasing')]
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
            # ws_o.write(row_pos_o, 0, None, self.ph_cell_style)
            # ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)   
            # ws_o.write(row_pos_o, 2, None, self.ph_cell_style)
            # ws_o.write(row_pos_o, 3, xlwt.Formula("SUM(D"+str(row_data_begin)+":D"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_titipanleasing_xls('report.Laporan Titipan Leasing', 'dym.branch', parser = dym_report_titipanleasing_print_xls)
