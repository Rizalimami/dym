import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_mutasibonsementara import dym_report_mutasibonsementara_print
from openerp.tools.translate import translate
import string

class dym_report_mutasibonsementara_print_xls(dym_report_mutasibonsementara_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_mutasibonsementara_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('dym.advance.payment')._report_xls_mutasibonsementara_fields(cr, uid, context),
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US') 
        return translate(self.cr, 'report.mutasibonsementara', 'report', lang, src) or src

class report_mutasibonsementara_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_mutasibonsementara_xls, self).__init__(name, table, rml, parser, header, store)

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
            'bs_tgl' : {
                'header': [1, 22, 'text', _render("_('Tgl BS')")],
                'lines': [1, 0, 'text', _render("p['bs_tgl']")],
                'totals': [1, 22, 'number', None]},
            'karyawan' : {
                'header': [1, 22, 'text', _render("_('Karyawan')")],
                'lines': [1, 0, 'text', _render("p['karyawan']")],
                'totals': [1, 22, 'number', None]},
            'dept' : {
                'header': [1, 22, 'text', _render("_('Dept')")],
                'lines': [1, 0, 'text', _render("p['dept']")],
                'totals': [1, 22, 'number', None]},
            'bs_nama' : {
                'header': [1, 22, 'text', _render("_('No. Adv Payment')")],
                'lines': [1, 0, 'text', _render("p['bs_nama']")],
                'totals': [1, 22, 'number', None]},
            'bs_nilai' :{
                'header': [1, 22, 'text', _render("_('Nilai BS')")],
                'lines': [1, 0, 'number', _render("p['bs_nilai']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['bs_nilai']")]},
            'bs_ket' :{
                'header': [1, 22, 'text', _render("_('Keterangan BS')")],
                'lines': [1, 0, 'text', _render("p['bs_ket']")],
                'totals': [1, 22, 'number', None]},
            'sp_date' :{
                'header': [1, 22, 'text', _render("_('Tgl Settlement')")],
                'lines': [1, 0, 'text', _render("p['sp_date']")],
                'totals': [1, 22, 'number', None]},
            'sp_name' :{
                'header': [1, 22, 'text', _render("_('No. Settlement')")],
                'lines': [1, 0, 'text', _render("p['sp_name']")],
                'totals': [1, 22, 'number', None]},
            'sp_nilai' :{
                'header': [1, 22, 'text', _render("_('Nilai Settlement')")],
                'lines': [1, 0, 'number', _render("p['sp_nilai']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['sp_nilai']")]},
            'sp_saldobs' :{
                'header': [1, 22, 'text', _render("_('Saldo BS')")],
                'lines': [1, 0, 'number', _render("p['sp_saldobs']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['sp_saldobs']")]},
            'current' :{
                'header': [1, 22, 'text', _render("_('Current')")],
                'lines': [1, 0, 'number', _render("p['current']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['current']")]},
            'overdue1_7' :{
                'header': [1, 22, 'text', _render("_('Overdue 1-7')")],
                'lines': [1, 0, 'text', _render("p['overdue1_7']")],
                'totals': [1, 22, 'number', None]},
            'overdue8_30' :{
                'header': [1, 22, 'text', _render("_('Overdue 8-30')")],
                'lines': [1, 0, 'text', _render("p['overdue8_30']")],
                'totals': [1, 22, 'number', None]},
            'overdue31_60' :{
                'header': [1, 22, 'text', _render("_('Overdue 31-60')")],
                'lines': [1, 0, 'text', _render("p['overdue31_60']")],
                'totals': [1, 22, 'number', None]},
            'overdue61_90' :{
                'header': [1, 22, 'text', _render("_('Overdue 61-90')")],
                'lines': [1, 0, 'text', _render("p['overdue61_90']")],
                'totals': [1, 22, 'number', None]},
            'overdue90' :{
                'header': [1, 22, 'text', _render("_('Overdue >90')")],
                'lines': [1, 0, 'text', _render("p['overdue90']")],
                'totals': [1, 22, 'number', None]},
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
            ws_o = wb.add_sheet('Laporan Mutasi Bon Sementara')
            
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
            c_specs_o = [('report_name', 1, 0, 'text', 'Laporan Mutasi Bon Sementara')]
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
            ws_o.write(row_pos_o, 0, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)   
            ws_o.write(row_pos_o, 2, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 3, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 4, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 5, xlwt.Formula("SUM(F"+str(row_data_begin)+":F"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 6, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 7, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 8, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 9, xlwt.Formula("SUM(J"+str(row_data_begin)+":J"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 10, xlwt.Formula("SUM(K"+str(row_data_begin)+":K"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 11, xlwt.Formula("SUM(L"+str(row_data_begin)+":L"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 12, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 13, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 14, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 15, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 16, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 17, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 18, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 19, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 20, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 21, None, self.ph_cell_style)

            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_mutasibonsementara_xls('report.Laporan Mutasi Bon Sementara', 'dym.advance.payment', parser = dym_report_mutasibonsementara_print_xls)
