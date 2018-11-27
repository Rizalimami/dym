import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_kinerja_wo import dym_report_kinerja_wo_print
from openerp.tools.translate import translate
import string

_ir_translation_name = 'report.kinerja.wo'

class dym_report_kinerja_wo_print_xls(dym_report_kinerja_wo_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_kinerja_wo_print_xls, self).__init__(cr, uid, name, context=context)
        kw_obj = self.pool.get('dym.work.order')
        self.context = context
        wl_overview = kw_obj._report_xls_kinerja_wo_fields(cr, uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': wl_overview,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src

class report_kinerja_wo_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_kinerja_wo_xls, self).__init__(name, table, rml, parser, header, store)

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
            'date_order': {
                'header': [1, 22, 'text', _render("_('Date')")],
                'lines': [1, 0, 'text', _render("p['date_order']")],
                'totals': [1, 22, 'number', None]},
            'mekanik_id': {
                'header': [1, 22, 'text', _render("_('Mekanik Name')")],
                'lines': [1, 0, 'text', _render("p['mekanik_id']")],
                'totals': [1, 22, 'number', None]},
            'product_name': {
                'header': [1, 22, 'text', _render("_('Nama Product')")],
                'lines': [1, 0, 'text', _render("p['product_name']")],
                'totals': [1, 22, 'number', None]},
            'product_qty': {
                'header': [1, 22, 'text', _render("_('Qty')")],
                'lines': [1, 0, 'number', _render("p['product_qty']")],
                'totals': [1, 22, 'number', _render("p['product_qty']"), None, self.rt_cell_style_decimal]},
            'price_unit': {
                'header': [1, 22, 'text', _render("_('Harga Satuan')")],
                'lines': [1, 0, 'number', _render("p['price_unit']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['price_unit']"), None, self.rt_cell_style_decimal]},
            'discount': {
                'header': [1, 22, 'text', _render("_('Discount')")],
                'lines': [1, 0, 'number', _render("p['discount']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount']"), None, self.rt_cell_style_decimal]},
            'discount_program': {
                'header': [1, 22, 'text', _render("_('Discount Program')")],
                'lines': [1, 0, 'number', _render("p['discount_program']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_program']"), None, self.rt_cell_style_decimal]},
            'discount_persen': {
                'header': [1, 22, 'text', _render("_('Discount Bundle')")],
                'lines': [1, 0, 'number', _render("p['discount_persen']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_persen']"), None, self.rt_cell_style_decimal]},
            'price_subtotal': {
                'header': [1, 22, 'text', _render("_('Subtotal')")],
                'lines': [1, 0, 'number', _render("p['price_subtotal']"), None, self.pd_cell_style_decimal],
                 'totals': [1, 22, 'number', _render("p['price_subtotal']"), None, self.rt_cell_style_decimal]},
            'amount_tax': {
                'header': [1, 22, 'text', _render("_('Pajak')")],
                'lines': [1, 0, 'number', _render("p['amount_tax']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['amount_tax']"), None, self.rt_cell_style_decimal]},
            'categ_name': {
                'header': [1, 22, 'text', _render("_('Category Name')")],
                'lines': [1, 0, 'text', _render("p['categ_name']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['categ_name']")]},
            'faktur_pajak': {
                'header': [1, 22, 'text', _render("_('Faktur Pajak')")],
                'lines': [1, 0, 'text', _render("p['faktur_pajak']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['faktur_pajak']")]},
            'collecting_id': {
                'header': [1, 22, 'text', _render("_('Collecting KPB')")],
                'lines': [1, 0, 'text', _render("p['collecting_id']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['collecting_id']")]},
            'sa_id': {
                'header': [1, 22, 'text', _render("_('Nama SA')")],
                'lines': [1, 0, 'text', _render("p['sa_id']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['sa_id']")]},
            'wo_name': {
                'header': [1, 22, 'text', _render("_('WO Number')")],
                'lines': [1, 0, 'text', _render("p['wo_name']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'text', _render("p['wo_name']")]},


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
                ('report_name', 1, 0, 'text', 'LAPORAN KINERJA WO'),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            
            ## Start Date & End Date ##
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join(
                [_('Tanggal'), _('-' if data['start_date'] == False else str(data['start_date'])), _('s/d'), _('-' if data['end_date'] == False else str(data['end_date'])),
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
            for p in r['kw_ids']:
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
            ws_o.write(row_pos_o, 24, xlwt.Formula("SUM(Y"+str(row_data_begin)+":Y"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 25, None, self.rt_cell_style_decimal)            
            ws_o.write(row_pos_o, 26, None, self.rt_cell_style_decimal)            
            ws_o.write(row_pos_o, 27, xlwt.Formula("SUM(AB"+str(row_data_begin)+":AB"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 28, xlwt.Formula("SUM(AC"+str(row_data_begin)+":AC"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 29, xlwt.Formula("SUM(AD"+str(row_data_begin)+":AD"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 30, xlwt.Formula("SUM(AE"+str(row_data_begin)+":AE"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 31, xlwt.Formula("SUM(AF"+str(row_data_begin)+":AF"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 32, xlwt.Formula("SUM(AG"+str(row_data_begin)+":AG"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 33, xlwt.Formula("SUM(AH"+str(row_data_begin)+":AH"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 34, xlwt.Formula("SUM(AI"+str(row_data_begin)+":AI"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 35, xlwt.Formula("SUM(AJ"+str(row_data_begin)+":AJ"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 36, xlwt.Formula("SUM(AK"+str(row_data_begin)+":AK"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 37, xlwt.Formula("SUM(AL"+str(row_data_begin)+":AL"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 38, xlwt.Formula("SUM(AM"+str(row_data_begin)+":AM"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 39, xlwt.Formula("SUM(AN"+str(row_data_begin)+":AN"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 40, xlwt.Formula("SUM(AO"+str(row_data_begin)+":AO"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 41, xlwt.Formula("SUM(AP"+str(row_data_begin)+":AP"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 42, xlwt.Formula("SUM(AQ"+str(row_data_begin)+":AQ"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 43, xlwt.Formula("SUM(AR"+str(row_data_begin)+":AR"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 44, xlwt.Formula("SUM(AS"+str(row_data_begin)+":AS"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 45, xlwt.Formula("SUM(AT"+str(row_data_begin)+":AT"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 46, xlwt.Formula("SUM(AU"+str(row_data_begin)+":AU"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 47, xlwt.Formula("SUM(AV"+str(row_data_begin)+":AV"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 48, xlwt.Formula("SUM(AW"+str(row_data_begin)+":AW"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 49, xlwt.Formula("SUM(AX"+str(row_data_begin)+":AX"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 50, xlwt.Formula("SUM(AY"+str(row_data_begin)+":AY"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 51, xlwt.Formula("SUM(AZ"+str(row_data_begin)+":AZ"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 52, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 53, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 54, None, self.rt_cell_style_decimal)
            
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, _p.report_date + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_kinerja_wo_xls(
    'report.Laporan Kinerja WO',
    'dym.work.order',
    parser = dym_report_kinerja_wo_print_xls)
