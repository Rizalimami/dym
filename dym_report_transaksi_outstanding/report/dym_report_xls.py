import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp import tools
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report import dym_report_transaksi_outstanding_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)
import time

_ir_translation_name = 'report.transaksi.outstanding'

class dym_report_transaksi_outstanding_print_xls(dym_report_transaksi_outstanding_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_transaksi_outstanding_print_xls, self).__init__(
            cr, uid, name, context=context)
        moveline_obj = self.pool.get('dym.work.order.line')
        self.context = context
        wl_overview = moveline_obj._report_xls_transaksi_outstanding_fields(
            cr, uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': wl_overview,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src


class report_transaksi_outstanding_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(report_transaksi_outstanding_xls, self).__init__(
            name, table, rml, parser, header, store)

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
        self.ph_cell_style_center = xlwt.easyxf(ph_cell_format  + _xs['center'] )
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
        self.pd_cell_style_decimal_fill = xlwt.easyxf(
            pd_cell_format + _xs['right'] + _xs['fill'] + _xs['bold'] ,
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
            'totals': [1, 5, 'text', None]},
        'branch_name': {
           'header': [1, 22, 'text', _render("_('Branch Name')")],
           'lines': [1, 0, 'text', _render("p['branch_name']")],
           'totals': [1, 22, 'text', None]},
        'transaksi': {
            'header': [1, 22, 'text', _render("_('Transaksi')")],
            'lines': [1, 0, 'text', _render("p['transaksi']")],
            'totals': [1, 22, 'text', None]},
        'no_dokumen': {
            'header': [1, 22, 'text', _render("_('No Dokumen')")],
            'lines': [1, 0, 'text', _render("p['no_dokumen']")],
            'totals': [1, 22, 'text', None]},
        'status': {
           'header': [1, 22, 'text', _render("_('Status')")],
           'lines': [1, 0, 'text', _render("p['status']")],
           'totals': [1, 22, 'text', None]},
        'value': {
           'header': [1, 22, 'text', _render("_('Value')")],
           'lines': [1, 0, 'number', _render("p['value']")],
           'totals': [1, 22, 'number', None]},
        
            }
        # XLS Template
        self.col_specs_template_details = {
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):

        wanted_list_overview = _p.wanted_list_overview
        _ = _p._

        username = self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name
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

            # COMPANY NAME
            cell_style_company = xlwt.easyxf(_xs['left'])
            c_specs_o = [
                ('company_name', 1, 0, 'text', str(_p.company.name)),
            ]
            row_data = self.xls_row_template(c_specs_o, ['company_name'])
            row_pos_o += self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style_company)

            # TITLE
            cell_style = xlwt.easyxf(_xs['xls_title'])
            report_name = ' '.join(
                [_p.company.name, r['title'],
                 _p.report_info])
            c_specs_o = [
                ('title', 1, 20, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['title'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)

            # JOURNAL
            #ws_o.write(row_pos_o, 0, data['journal_id'][1], cell_style)
            row_pos_o += 1

            ## Tanggal Start Date & End Date ##
            cell_style = xlwt.easyxf(_xs['left'])
            ## Tanggal Trx Start Date & End Date ##
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join(
                [_('Tanggal Transaksi'), _('-' if data['trx_start_date'] == False else str(data['trx_start_date'])),
                 _('s/d'), _('-' if data['trx_end_date'] == False else str(data['trx_end_date'])),
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

            no = 0
            for p in r['id_ai']:
                c_specs_o = map(
                    lambda x: self.render(
                        x, self.col_specs_template_overview, 'lines'),
                    wanted_list_overview)
                for x in c_specs_o:
                    if x[0] == 'no':
                        no += 1
                        x[4] = no

                row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])

                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)

                row_pos_d += 1
            row_data_end = row_pos_o

            # Totals
            ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 1, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 5, xlwt.Formula("SUM(F" + str(row_data_begin) + ":F" + str(row_data_end) + ")"),
                       self.rt_cell_style_decimal)

            row_pos_o += 1

            ws_o.write(row_pos_o + 1, 0, _p.report_date + " " + username)




report_transaksi_outstanding_xls('report.Laporan Transaksi Outstanding', 'dym.work.order.line',
                         parser=dym_report_transaksi_outstanding_print_xls)
