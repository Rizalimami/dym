import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_lbb import dym_report_lbb_print
from openerp.tools.translate import translate
import string

class dym_report_lbb_print_xls(dym_report_lbb_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_lbb_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('dym.work.order')._report_xls_lbb_fields(cr, uid, context),
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US') 
        return translate(self.cr, 'report.lbb', 'report', lang, src) or src

class report_lbb_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_lbb_xls, self).__init__(name, table, rml, parser, header, store)

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
        self.pd_cell_style_right = xlwt.easyxf(pd_cell_format + _xs['right'])
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
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['no']")],
                'totals': [1, 5, 'number', None]},
            'type': {
                'header': [1, 22, 'text', None],
                'lines': [1, 0, 'text', _render("p['type']")],
                'totals': [1, 22, 'number', None]},
            'total_unit_entry': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['total_unit_entry']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'kpb_1': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['kpb_1']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'kpb_2': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['kpb_2']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'kpb_3': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['kpb_3']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'kpb_4': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['kpb_4']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'kpb_5': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['kpb_5']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'claim': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['claim']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'qs_cs': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['qs_cs']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'qs_ls': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['qs_ls']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'qs_or': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['qs_or']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'lr': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['lr']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'hr': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['hr']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'total': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['total']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'jr': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['jr']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'member_card': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['member_card']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'drive_thru': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['drive_thru']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},
            'unit_safety': {
                'header': [1, 5, 'text', None],
                'lines': [1, 0, 'number', _render("p['unit_safety']"), None, self.pd_cell_style_right],
                'totals': [1, 5, 'number', None]},            
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        self.col_specs_template_overview.update({})
        _ = _p._

        # for r in _p.reports:
        ws_o = wb.add_sheet('Laporan Bulanan Bengkel')
        
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
        
        # Title
        cell_style = xlwt.easyxf(_xs['xls_title']+_xs['center']+_xs['underline'])
        c_specs_o = [('report_name', 19, 0, 'text', 'LAPORAN BULANAN BENGKEL')]
        row_data = self.xls_row_template(c_specs_o, ['report_name'])
        row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
        cell_style = xlwt.easyxf(_xs['xls_title']+_xs['center'])
        c_specs_o = [('report_name', 19, 0, 'text', '(L.B.B)')]
        row_data = self.xls_row_template(c_specs_o, ['report_name'])
        row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)

        # Longkap
        cell_style = xlwt.easyxf(_xs['left'])
        row_pos_o = self.xls_write_row(ws_o, row_pos_o, '', row_style=cell_style)

        #Sub 1
        cell_style = xlwt.easyxf(_xs['left']+_xs['bold'])
        c_specs_o = [('report_name', 19, 0, 'text', 'I. LAPORAN PENDAPATAN BENGKEL')]
        row_data = self.xls_row_template(c_specs_o, ['report_name'])
        row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)

        #Column Header 1
        ws_o.write_merge(row_pos_o, row_pos_o, 0, 5, '1. Pendapatan Jasa dan Reparasi', self.rh_cell_style)
        ws_o.write_merge(row_pos_o + 1, row_pos_o + 1, 0, 3, 'a. Jasa KPB/ ASS', self.pd_cell_style)
        ws_o.write_merge(row_pos_o + 2, row_pos_o + 2, 0, 3, 'b. Jasa Claim C2', self.pd_cell_style)
        ws_o.write_merge(row_pos_o + 3, row_pos_o + 3, 0, 3, 'c. Jasa Quick Service (QS)', self.pd_cell_style)
        ws_o.write_merge(row_pos_o + 4, row_pos_o + 4, 0, 3, 'd. Jasa Light Repair (LR)', self.pd_cell_style)
        ws_o.write_merge(row_pos_o + 5, row_pos_o + 5, 0, 3, 'e. Jasa Heavy Repair (HR)', self.pd_cell_style)
        ws_o.write_merge(row_pos_o + 6, row_pos_o + 6, 0, 5, 'Total', self.rh_cell_style)

        ws_o.write_merge(row_pos_o, row_pos_o, 6, 10, '2. Pendapatan Penjualan Parts', self.rh_cell_style)
        ws_o.write_merge(row_pos_o + 1, row_pos_o + 1, 6, 8, 'a. Sparepart', self.pd_cell_style)
        ws_o.write_merge(row_pos_o + 2, row_pos_o + 2, 6, 8, 'b. Oli', self.pd_cell_style)
        ws_o.write_merge(row_pos_o + 3, row_pos_o + 3, 6, 8, 'c. Busi', self.pd_cell_style)
        ws_o.write_merge(row_pos_o + 4, row_pos_o + 4, 6, 8, 'd. Lain-lain', self.pd_cell_style)
        ws_o.write_merge(row_pos_o + 5, row_pos_o + 5, 6, 8, '', self.pd_cell_style)
        ws_o.write_merge(row_pos_o + 6, row_pos_o + 6, 6, 10, 'Total', self.rh_cell_style)

        row_pos_o += 7

        # Longkap
        cell_style = xlwt.easyxf(_xs['left'])
        row_pos_o = self.xls_write_row(ws_o, row_pos_o, '', row_style=cell_style)

        #Total
        cell_style = xlwt.easyxf(_xs['left']+_xs['bold'])
        c_specs_o = [('report_name', 19, 0, 'text', 'Penghasilan Bengkel:')]
        row_data = self.xls_row_template(c_specs_o, ['report_name'])
        row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)

        cell_style = xlwt.easyxf(_xs['left']+_xs['bold'])
        c_specs_o = [('report_name', 19, 0, 'text', 'Kerugian Jasa (Rp) Akibat JR:')]
        row_data = self.xls_row_template(c_specs_o, ['report_name'])
        row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)

        cell_style = xlwt.easyxf(_xs['left']+_xs['bold'])
        c_specs_o = [('report_name', 19, 0, 'text', 'Jumlah PIT AHASS:')]
        row_data = self.xls_row_template(c_specs_o, ['report_name'])
        row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)

        # Longkap
        cell_style = xlwt.easyxf(_xs['left'])
        row_pos_o = self.xls_write_row(ws_o, row_pos_o, '', row_style=cell_style)

        # Sub 2
        cell_style = xlwt.easyxf(_xs['left']+_xs['bold'])
        c_specs_o = [('report_name', 19, 0, 'text', 'II. JUMLAH UNIT SEPEDA MOTOR YANG DIKERJAKAN')]
        row_data = self.xls_row_template(c_specs_o, ['report_name'])
        row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)

        # Header 2
        ap_style_header = xlwt.easyxf('pattern: pattern solid, fore_colour 26; alignment: horiz centre, vert centre, wrap on; font: bold on; borders: left thin, right thin, top thin, bottom thin, left_colour 22, right_colour 22, top_colour 22, bottom_colour 22', num_format_str="0.0")

        ws_o.write_merge(row_pos_o, row_pos_o + 2, 0, 0, 'No', ap_style_header)
        ws_o.write_merge(row_pos_o, row_pos_o + 2, 1, 1, 'Type', ap_style_header)
        ws_o.write_merge(row_pos_o, row_pos_o + 2, 2, 2, 'Total Unit Entry', ap_style_header)
        ws_o.write_merge(row_pos_o, row_pos_o, 3, 15, 'Yang Dikerjakan Dari Unit Ini', ap_style_header)
        ws_o.write_merge(row_pos_o + 1, row_pos_o + 1, 3, 7, 'Kartu Perawatan Berkala / ASS', ap_style_header)
        ws_o.write_merge(row_pos_o + 1, row_pos_o + 2, 8, 8, 'Claim C2', ap_style_header)
        ws_o.write_merge(row_pos_o + 1, row_pos_o + 1, 9, 11, 'Quick Service (QS)', ap_style_header)
        ws_o.write_merge(row_pos_o + 1, row_pos_o + 2, 12, 12, 'LR', ap_style_header)
        ws_o.write_merge(row_pos_o + 1, row_pos_o + 2, 13, 13, 'HR', ap_style_header)
        ws_o.write_merge(row_pos_o + 1, row_pos_o + 2, 14, 14, 'Total', ap_style_header)
        ws_o.write_merge(row_pos_o + 1, row_pos_o + 2, 15, 15, 'JR', ap_style_header)
        ws_o.write_merge(row_pos_o, row_pos_o + 2, 16, 16, 'Member Card (Always Honda)', ap_style_header)
        ws_o.write_merge(row_pos_o, row_pos_o + 2, 17, 17, 'Total Unit Drive Thru', ap_style_header)
        ws_o.write_merge(row_pos_o, row_pos_o + 2, 18, 18, 'Total Unit Safety Check Item', ap_style_header)
        ws_o.write(row_pos_o + 2, 3, '1', ap_style_header) 
        ws_o.write(row_pos_o + 2, 4, '2', ap_style_header)
        ws_o.write(row_pos_o + 2, 5, '3', ap_style_header)
        ws_o.write(row_pos_o + 2, 6, '4', ap_style_header)
        ws_o.write(row_pos_o + 2, 7, '5-10', ap_style_header)
        ws_o.write(row_pos_o + 2, 9, 'CS', ap_style_header) 
        ws_o.write(row_pos_o + 2, 10, 'LS', ap_style_header)
        ws_o.write(row_pos_o + 2, 11, 'OR+', ap_style_header)
        
        row_pos_o += 3
        
        # Dict
        alph = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        
        # Columns and Rows Cub
        no = 0
        row_data_begin = row_pos_o + 1
        for p in _p.reports[0]['datas_cub']:
            c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'lines'), wanted_list_overview)
            for x in c_specs_o :
                if x[0] == 'no' :
                    no += 1
                    x[4] = no
            row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
        row_data_end = row_pos_o

        # Total Cub
        ws_o.write_merge(row_pos_o, row_pos_o, 0, 1, 'Total Cub/Bebek', self.rh_cell_style)
        for x in range(2,19):
            ws_o.write(row_pos_o, x, xlwt.Formula("SUM("+alph[x]+str(row_data_begin)+":"+alph[x]+str(row_data_end)+")"), self.rt_cell_style_right)
        row_pos_o += 1
        row_data_cub = row_pos_o

        # Columns and Rows Matic
        no = 0
        row_data_begin = row_pos_o + 1
        for p in _p.reports[1]['datas_matic']:
            c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'lines'), wanted_list_overview)
            for x in c_specs_o :
                if x[0] == 'no' :
                    no += 1
                    x[4] = no
            row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
        row_data_end = row_pos_o

        # Total Matic
        ws_o.write_merge(row_pos_o, row_pos_o, 0, 1, 'Total Matic', self.rh_cell_style)
        for x in range(2,19):
            ws_o.write(row_pos_o, x, xlwt.Formula("SUM("+alph[x]+str(row_data_begin)+":"+alph[x]+str(row_data_end)+")"), self.rt_cell_style_right)
        row_pos_o += 1
        row_data_matic = row_pos_o

        # Columns and Rows Sport
        no = 0
        row_data_begin = row_pos_o + 1
        for p in _p.reports[2]['datas_sport']:
            c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'lines'), wanted_list_overview)
            for x in c_specs_o :
                if x[0] == 'no' :
                    no += 1
                    x[4] = no
            row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
        row_data_end = row_pos_o

        # Total Matic
        ws_o.write_merge(row_pos_o, row_pos_o, 0, 1, 'Total Sport', self.rh_cell_style)
        for x in range(2,19):
            ws_o.write(row_pos_o, x, xlwt.Formula("SUM("+alph[x]+str(row_data_begin)+":"+alph[x]+str(row_data_end)+")"), self.rt_cell_style_right)
        row_pos_o += 1
        row_data_sport = row_pos_o

        # Total All
        ws_o.write_merge(row_pos_o, row_pos_o, 0, 1, 'Total', self.rh_cell_style)
        for x in range(2,19):
            ws_o.write(row_pos_o, x, xlwt.Formula(alph[x]+str(row_data_cub)+"+"+alph[x]+str(row_data_matic)+"+"+alph[x]+str(row_data_sport)), self.rt_cell_style_right)
        row_pos_o += 1

        # Longkap
        cell_style = xlwt.easyxf(_xs['left'])
        row_pos_o = self.xls_write_row(ws_o, row_pos_o, '', row_style=cell_style)

        # Tahun Kendaraan Header
        ws_o.write_merge(row_pos_o, row_pos_o, 0, 1, 'Tahun Kendaraan', self.rh_cell_style)
        ws_o.write(row_pos_o, 2, '<= 2007', self.rh_cell_style)
        ws_o.write(row_pos_o, 3, '2008', self.rh_cell_style)
        ws_o.write(row_pos_o, 4, '2009', self.rh_cell_style)
        ws_o.write(row_pos_o, 5, '2010', self.rh_cell_style)
        ws_o.write(row_pos_o, 6, '2011', self.rh_cell_style)
        ws_o.write(row_pos_o, 7, '2012', self.rh_cell_style)
        ws_o.write(row_pos_o, 8, '2013', self.rh_cell_style)
        ws_o.write(row_pos_o, 9, '2014', self.rh_cell_style)
        ws_o.write(row_pos_o, 10, '2015', self.rh_cell_style)
        ws_o.write(row_pos_o, 11, '2016', self.rh_cell_style)
        ws_o.write(row_pos_o, 12, '2017', self.rh_cell_style)
        ws_o.write(row_pos_o, 13, 'Total', self.rh_cell_style)
        row_pos_o += 1

        # Tahun Kendaraan Isi
        ws_o.write_merge(row_pos_o, row_pos_o, 0, 1, 'Jumlah Unit', self.rh_cell_style)
        ws_o.write(row_pos_o, 2, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 3, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 4, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 5, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 6, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 7, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 8, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 9, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 10, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 11, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 12, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 13, '', self.pd_cell_style_right)
        row_pos_o += 1

        # Longkap
        cell_style = xlwt.easyxf(_xs['left'])
        row_pos_o = self.xls_write_row(ws_o, row_pos_o, '', row_style=cell_style)

        # Paket Service Header
        ws_o.write_merge(row_pos_o, row_pos_o, 0, 1, 'Unit Entry Paket Service & BTL', self.rh_cell_style)
        ws_o.write(row_pos_o, 2, 'CVT Cleaner', self.rh_cell_style)
        ws_o.write(row_pos_o, 3, 'Kuras Tangki', self.rh_cell_style)
        ws_o.write(row_pos_o, 4, 'Kuras Oli Rem', self.rh_cell_style)
        ws_o.write(row_pos_o, 5, '...', self.rh_cell_style)
        ws_o.write(row_pos_o, 6, '...', self.rh_cell_style)
        ws_o.write(row_pos_o, 7, '...', self.rh_cell_style)
        ws_o.write(row_pos_o, 8, '...', self.rh_cell_style)
        ws_o.write(row_pos_o, 9, '...', self.rh_cell_style)
        ws_o.write(row_pos_o, 10, '...', self.rh_cell_style)
        ws_o.write(row_pos_o, 11, '...', self.rh_cell_style)
        ws_o.write(row_pos_o, 12, '...', self.rh_cell_style)
        ws_o.write(row_pos_o, 13, 'Total', self.rh_cell_style)
        row_pos_o += 1

        # Paket Service Isi
        ws_o.write_merge(row_pos_o, row_pos_o, 0, 1, 'Jumlah Unit', self.rh_cell_style)
        ws_o.write(row_pos_o, 2, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 3, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 4, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 5, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 6, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 7, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 8, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 9, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 10, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 11, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 12, '', self.pd_cell_style_right)
        ws_o.write(row_pos_o, 13, '', self.pd_cell_style_right)
        row_pos_o += 3

        # Sign
        ws_o.write_merge(row_pos_o, row_pos_o, 3, 4, 'Dibuat,', xlwt.easyxf(_xs['bold']+_xs['center']))
        ws_o.write_merge(row_pos_o, row_pos_o, 8, 10, 'Diperiksa,', xlwt.easyxf(_xs['bold']+_xs['center']))
        ws_o.write_merge(row_pos_o, row_pos_o, 14, 15, 'Mengetahui,', xlwt.easyxf(_xs['bold']+_xs['center']))
        ws_o.write_merge(row_pos_o + 3, row_pos_o + 3, 3, 4, 'Front Desk', xlwt.easyxf(_xs['bold']+_xs['center']))
        ws_o.write_merge(row_pos_o + 3, row_pos_o + 3, 8, 10, 'Kepala Bengkel', xlwt.easyxf(_xs['bold']+_xs['center']))
        ws_o.write_merge(row_pos_o + 3, row_pos_o + 3, 14, 15, 'Pemilik/Pimpinan', xlwt.easyxf(_xs['bold']+_xs['center']))


report_lbb_xls('report.Laporan LBB', 'dym.work.order', parser = dym_report_lbb_print_xls)
