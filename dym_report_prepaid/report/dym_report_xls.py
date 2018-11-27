import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report import dym_report_account_prepaid_print
from openerp.tools.translate import translate
import logging

_logger = logging.getLogger(__name__)
import string

_ir_translation_name = 'report.account.prepaid'


class dym_report_account_prepaid_print_xls(dym_report_account_prepaid_print):
    def __init__(self, cr, uid, name, context):
        super(dym_report_account_prepaid_print_xls, self).__init__(
            cr, uid, name, context=context)
        move_line_obj = self.pool.get('account.asset.asset')
        self.context = context
        wl_overview = move_line_obj._report_xls_account_prepaid_fields(
            cr, uid, context)
        tmpl_upd_overview = move_line_obj._report_xls_arap_overview_template(
            cr, uid, context)
        wl_details = move_line_obj._report_xls_arap_details_fields(
            cr, uid, context)
        tmpl_upd_details = move_line_obj._report_xls_arap_overview_template(
            cr, uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': wl_overview,
            'template_update_overview': tmpl_upd_overview,
            'wanted_list_details': wl_details,
            'template_update_details': tmpl_upd_details,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src


class report_account_prepaid_xls(report_xls):
    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(report_account_prepaid_xls, self).__init__(
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
                'totals': [1, 5, 'text', None]},
            'branch_name': {
                'header': [1, 22, 'text', _render("_('Branch')")],
                'lines': [1, 0, 'text', _render("p['branch_name']")],
                'totals': [1, 22, 'text', None]},
            'asset_code': {
                'header': [1, 22, 'text', _render("_('Prepaid Code')")],
                'lines': [1, 0, 'text', _render("p['asset_code']")],
                'totals': [1, 22, 'text', None]},
            'asset_account': {
                'header': [1, 22, 'text', _render("_('Prepaid Account')")],
                'lines': [1, 0, 'text', _render("p['asset_account']")],
                'totals': [1, 22, 'text', None]},
            'nomor_sin': {
                'header': [1, 22, 'text', _render("_('Reference')")],
                'lines': [1, 0, 'text', _render("p['nomor_sin']")],
                'totals': [1, 22, 'text', None]},
            'category_name': {
                'header': [1, 22, 'text', _render("_('Prepaid Category')")],
                'lines': [1, 0, 'text', _render("p['category_name']")],
                'totals': [1, 22, 'text', None]},
            'asset_name': {
                'header': [1, 22, 'text', _render("_('Prepaid Name')")],
                'lines': [1, 0, 'text', _render("p['asset_name']")],
                'totals': [1, 22, 'text', None]},
            'asset_owner': {
                'header': [1, 22, 'text', _render("_('Prepaid Owner')")],
                'lines': [1, 0, 'text', _render("p['asset_owner']")],
                'totals': [1, 22, 'text', None]},
            'purchase_date': {
                'header': [1, 22, 'text', _render("_('Purchase Date')")],
                'lines': [1, 0, 'text', _render("p['purchase_date']")],
                'totals': [1, 22, 'text', None]},
            'number_of_depr': {
                'header': [1, 22, 'text', _render("_('Number of Amort')")],
                'lines': [1, 0, 'number', _render("p['number_of_depr']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['number_of_depr']"), None, self.rt_cell_style_decimal]},
            'depr_end_date': {
                'header': [1, 22, 'text', _render("_('Tanggal Berakhirnya Amortisasi')")],
                'lines': [1, 0, 'text', _render("p['depr_end_date']")],
                'totals': [1, 22, 'text', None]},
            'coa_depr_code': {
                'header': [1, 22, 'text', _render("_('COA Amort No')")],
                'lines': [1, 0, 'text', _render("p['coa_depr_code']")],
                'totals': [1, 22, 'text', None]},
            'coa_depr_name': {
                'header': [1, 22, 'text', _render("_('Amortization Name')")],
                'lines': [1, 0, 'text', _render("p['coa_depr_name']")],
                'totals': [1, 22, 'text', None]},
            'status': {
                'header': [1, 22, 'text', _render("_('Status')")],
                'lines': [1, 0, 'text', _render("p['status']")],
                'totals': [1, 22, 'text', None]},
            'purchase_value': {
                'header': [1, 22, 'text', _render("_('Gross Value')")],
                'lines': [1, 0, 'number', _render("p['purchase_value']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['purchase_value']"), None, self.rt_cell_style_decimal]},
            'depr_jan': {
                'header': [1, 22, 'text', _render("_('Jan')")],
                'lines': [1, 0, 'number', _render("p['depr_jan']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_jan']"), None, self.rt_cell_style_decimal]},
            'depr_feb': {
                'header': [1, 22, 'text', _render("_('Feb')")],
                'lines': [1, 0, 'number', _render("p['depr_feb']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_feb']"), None, self.rt_cell_style_decimal]},
            'depr_mar': {
                'header': [1, 22, 'text', _render("_('Mar')")],
                'lines': [1, 0, 'number', _render("p['depr_mar']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_mar']"), None, self.rt_cell_style_decimal]},
            'depr_apr': {
                'header': [1, 22, 'text', _render("_('Apr')")],
                'lines': [1, 0, 'number', _render("p['depr_apr']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_apr']"), None, self.rt_cell_style_decimal]},
            'depr_mei': {
                'header': [1, 22, 'text', _render("_('Mei')")],
                'lines': [1, 0, 'number', _render("p['depr_mei']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_mei']"), None, self.rt_cell_style_decimal]},
            'depr_jun': {
                'header': [1, 22, 'text', _render("_('Jun')")],
                'lines': [1, 0, 'number', _render("p['depr_jun']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_jun']"), None, self.rt_cell_style_decimal]},
            'depr_jul': {
                'header': [1, 22, 'text', _render("_('Jul')")],
                'lines': [1, 0, 'number', _render("p['depr_jul']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_jul']"), None, self.rt_cell_style_decimal]},
            'depr_aug': {
                'header': [1, 22, 'text', _render("_('Aug')")],
                'lines': [1, 0, 'number', _render("p['depr_aug']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_aug']"), None, self.rt_cell_style_decimal]},
            'depr_sep': {
                'header': [1, 22, 'text', _render("_('Sep')")],
                'lines': [1, 0, 'number', _render("p['depr_sep']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_sep']"), None, self.rt_cell_style_decimal]},
            'depr_okt': {
                'header': [1, 22, 'text', _render("_('Okt')")],
                'lines': [1, 0, 'number', _render("p['depr_okt']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_okt']"), None, self.rt_cell_style_decimal]},
            'depr_nop': {
                'header': [1, 22, 'text', _render("_('Nop')")],
                'lines': [1, 0, 'number', _render("p['depr_nop']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_nop']"), None, self.rt_cell_style_decimal]},
            'depr_des': {
                'header': [1, 22, 'text', _render("_('Des')")],
                'lines': [1, 0, 'number', _render("p['depr_des']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_des']"), None, self.rt_cell_style_decimal]},
            'depr_ttloy': {
                'header': [1, 22, 'text', _render("_('Total 1 Tahun')")],
                'lines': [1, 0, 'number', _render("p['depr_ttloy']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['depr_ttloy']"), None, self.rt_cell_style_decimal]},
            'amortizatied_value': {
                'header': [1, 22, 'text', _render("_('Amortization Value')")],
                # 'lines': [1, 0, 'number', _render("p['depreciated_value']"), None, self.pd_cell_style_decimal],
                'lines': [1, 0, 'number', _render("p['purchase_value'] - p['nbv']"), None, self.pd_cell_style_decimal],
                # 'totals': [1, 22, 'number', _render("p['depreciated_value']"), None, self.rt_cell_style_decimal]},
                'totals': [1, 22, 'number', _render("p['purchase_value'] - p['nbv']"), None,
                           self.rt_cell_style_decimal]},
            'nbv': {
                'header': [1, 22, 'text', _render("_('NBV')")],
                'lines': [1, 0, 'number', _render("p['nbv']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['nbv']"), None, self.rt_cell_style_decimal]},
            'analytic_combination': {
                'header': [1, 20, 'text', _render("_('Analytic Combination')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['analytic_combination'] or ''")],
                'totals': [1, 0, 'text', None]},
            'analytic_1': {
                'header': [1, 20, 'text', _render("_('Analytic Company')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['analytic_1'] or ''")],
                'totals': [1, 0, 'text', None]},
            'analytic_2': {
                'header': [1, 20, 'text', _render("_('Analytic Bisnis Unit')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['analytic_2'] or ''")],
                'totals': [1, 0, 'text', None]},
            'analytic_3': {
                'header': [1, 20, 'text', _render("_('Analytic Branch')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['analytic_3'] or ''")],
                'totals': [1, 0, 'text', None]},
            'analytic_4': {
                'header': [1, 20, 'text', _render("_('Analytic Cost Center')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['analytic_4'] or ''")],
                'totals': [1, 0, 'text', None]},
        }
        # XLS Template
        self.col_specs_template_details = {

        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        wanted_list_details = _p.wanted_list_details
        self.col_specs_template_overview.update(_p.template_update_overview)
        self.col_specs_template_details.update(_p.template_update_details)
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

            # Title
            ## Company ##
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join(
                [_p.company.name, r['title'],
                 _p.report_info])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)

            ## Text + Tgl ##
            cell_style = xlwt.easyxf(_xs['xls_title'])
            report_name = ' '.join(
                [_('LAPORAN Prepaid Per Tanggal'), _(str(datetime.today().date())),
                 _p.report_info])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)

            ## Tanggal Jtp Start Date & End Date ##
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join(
                [_('Tanggal Purchase'), _('-' if data['start_date'] == False else str(data['start_date'])), _('s/d'),
                 _('-' if data['end_date'] == False else str(data['end_date'])),
                 _p.report_info])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)

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
            for p in r['asset_ids']:
                c_specs_o = map(
                    lambda x: self.render(
                        x, self.col_specs_template_overview, 'lines'),
                    wanted_list_overview)
                for x in c_specs_o:
                    if x[0] == 'no':
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
            ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 6, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 7, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 8, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 9, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 10, xlwt.Formula("SUM(K" + str(row_data_begin) + ":K" + str(row_data_end) + ")"),
                       self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 11, xlwt.Formula("SUM(L" + str(row_data_begin) + ":L" + str(row_data_end) + ")"),
                       self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 12, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 13, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 14, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 15, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 16, None, self.rt_cell_style_decimal)

            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0,
                       _p.report_date + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))


report_account_prepaid_xls('report.Laporan Prepaid', 'account.asset.asset', parser=dym_report_account_prepaid_print_xls)
