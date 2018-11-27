import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_kinerjamekanik import dym_report_kinerjamekanik_print
from openerp.tools.translate import translate
import string

class dym_report_kinerjamekanik_print_xls(dym_report_kinerjamekanik_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_kinerjamekanik_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('dym.work.order')._report_xls_kinerjamekanik_fields(cr, uid, context),
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US') 
        return translate(self.cr, 'report.kinerjamekanik', 'report', lang, src) or src

class report_kinerjamekanik_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_kinerjamekanik_xls, self).__init__(name, table, rml, parser, header, store)

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
            'nama_mekanik': {
                'header': [1, 32, 'text', _render("_('Nama Mekanik')")],
                'lines': [1, 0, 'text', _render("p['nama_mekanik']")],
                'totals': [1, 32, 'text', None]},
            'sum_claim': {
                'header': [1, 12, 'text', _render("_('Claim')")],
                'lines': [1, 0, 'number', _render("p['sum_claim']"), None, xlwt.easyxf(_xs['right'])],
                'totals': [1, 12, 'number', _render("p['sum_claim']"), None, xlwt.easyxf(_xs['right'])]},
            'sum_kpb': {
                'header': [1, 12, 'text', _render("_('KPB')")],
                'lines': [1, 0, 'number', _render("p['sum_kpb']"), None, xlwt.easyxf(_xs['right'])],
                'totals': [1, 12, 'number', _render("p['sum_kpb']"), None, xlwt.easyxf(_xs['right'])]},
            'sum_quickserv': {
                'header': [1, 14, 'text', _render("_('Quick Service')")],
                'lines': [1, 0, 'number', _render("p['sum_quickserv']"), None, xlwt.easyxf(_xs['right'])],
                'totals': [1, 14, 'number', _render("p['sum_quickserv']"), None, xlwt.easyxf(_xs['right'])]},
            'sum_lightrep': {
                'header': [1, 14, 'text', _render("_('Light Repair')")],
                'lines': [1, 0, 'number', _render("p['sum_lightrep']"), None, xlwt.easyxf(_xs['right'])],
                'totals': [1, 14, 'number', _render("p['sum_lightrep']"), None, xlwt.easyxf(_xs['right'])]},
            'sum_heavyrep': {
                'header': [1, 20, 'text', _render("_('Heavy Repair')")],
                'lines': [1, 0, 'number', _render("p['sum_heavyrep']"), None, xlwt.easyxf(_xs['right'])],
                'totals': [1, 20, 'number', _render("p['sum_heavyrep']"), None, xlwt.easyxf(_xs['right'])]},
            'sum_job': {
                'header': [1, 12, 'text', _render("_('Job Return')")],
                'lines': [1, 0, 'number', _render("p['sum_job']"), None, xlwt.easyxf(_xs['right'])],
                'totals': [1, 12, 'number', _render("p['sum_job']"), None, xlwt.easyxf(_xs['right'])]},
            'total': {
                'header': [1, 12, 'text', _render("_('Total')")],
                'lines': [1, 0, 'number', _render("p['total']"), None, xlwt.easyxf(_xs['right'])],
                'totals': [1, 12, 'number', _render("p['total']"), None, xlwt.easyxf(_xs['right'])]},
            'jam_terpakai': {
                'header': [1, 15, 'text', _render("_('Jam Terpakai')")],
                'lines': [1, 0, 'number', _render("p['jam_terpakai']"), None, self.pd_cell_style_decimal],
                'totals': [1, 15, 'number', _render("p['jam_terpakai']"), None, self.pd_cell_style_decimal]},
            'rp_jasa': {
                'header': [1, 15, 'text', _render("_('Rp. Jasa')")],
                'lines': [1, 0, 'number', _render("p['rp_jasa']"), None, self.pd_cell_style_decimal],
                'totals': [1, 15, 'number', _render("p['rp_jasa']"), None, self.pd_cell_style_decimal]},
            'rp_sparepart': {
                'header': [1, 15, 'text', _render("_('Rp. Sparepart')")],
                'lines': [1, 0, 'number', _render("p['rp_sparepart']"), None, self.pd_cell_style_decimal],
                'totals': [1, 15, 'number', _render("p['rp_sparepart']"), None, self.pd_cell_style_decimal]},
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        self.col_specs_template_overview.update({})
        _ = _p._

        for r in _p.reports:
            ws_o = wb.add_sheet('Laporan Kinerja Mekanik')
            
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
            c_specs_o = [('report_name', 1, 0, 'text', 'Laporan Prestasi/Kinerja Mekanik')]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)

            # Periode
            waktu = {
                'Harian' : str(data['start_date']) + ' s.d. ' + str(data['end_date']),
                'Bulanan' : str(data['start_month']) + '/' + str(data['start_year']) + ' s.d. ' + str(data['end_month']) + '/' + str(data['end_year']),
                'Tahunan' : str(data['start_year']) + ' s.d. ' + str(data['end_year'])
            }

            cell_style = xlwt.easyxf(_xs['left'])
            periode_str = ' '.join(['Periode:', data['report_type'], waktu[data['report_type']]])
            c_specs_o = [('periode', 1, 0, 'text', periode_str)]
            row_data = self.xls_row_template(c_specs_o, ['periode'])
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
            ws_o.write(row_pos_o, 0, 'Totals', self.ph_cell_style)   
            ws_o.write(row_pos_o, 1, None, self.ph_cell_style)
            ws_o.write(row_pos_o, 2, xlwt.Formula("SUM(C"+str(row_data_begin)+":C"+str(row_data_end)+")"), self.rt_cell_style_right)
            ws_o.write(row_pos_o, 3, xlwt.Formula("SUM(D"+str(row_data_begin)+":D"+str(row_data_end)+")"), self.rt_cell_style_right)
            ws_o.write(row_pos_o, 4, xlwt.Formula("SUM(E"+str(row_data_begin)+":E"+str(row_data_end)+")"), self.rt_cell_style_right)
            ws_o.write(row_pos_o, 5, xlwt.Formula("SUM(F"+str(row_data_begin)+":F"+str(row_data_end)+")"), self.rt_cell_style_right)
            ws_o.write(row_pos_o, 6, xlwt.Formula("SUM(G"+str(row_data_begin)+":G"+str(row_data_end)+")"), self.rt_cell_style_right)
            ws_o.write(row_pos_o, 7, xlwt.Formula("SUM(H"+str(row_data_begin)+":H"+str(row_data_end)+")"), self.rt_cell_style_right)
            ws_o.write(row_pos_o, 8, xlwt.Formula("SUM(I"+str(row_data_begin)+":I"+str(row_data_end)+")"), self.rt_cell_style_right)
            ws_o.write(row_pos_o, 9, xlwt.Formula("SUM(J"+str(row_data_begin)+":J"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 10, xlwt.Formula("SUM(K"+str(row_data_begin)+":K"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 11, xlwt.Formula("SUM(L"+str(row_data_begin)+":L"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            
            # Footer
            ws_o.write(row_pos_o + 2, 2, 'Dibuat Oleh:', self.pd_cell_style)
            ws_o.write(row_pos_o + 6, 2, '(Admin)', xlwt.easyxf(_xs['bold']))
            ws_o.write(row_pos_o + 2, 6, 'Diketahui Oleh:', self.pd_cell_style)
            ws_o.write(row_pos_o + 6, 6, '(Pimpinan Bengkel)', xlwt.easyxf(_xs['bold']))

            ws_o.write(row_pos_o + 8, 0, time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_kinerjamekanik_xls('report.Laporan Kinerja Mekanik', 'dym.work.order', parser = dym_report_kinerjamekanik_print_xls)
