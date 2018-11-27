import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_stock import dym_stock_unit_report_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)
_ir_translation_name = 'dym.stock.unit.report'


class dym_stock_unit_report_print_xls(dym_stock_unit_report_print):

    def __init__(self, cr, uid, name, context):
        super(dym_stock_unit_report_print_xls, self).__init__(
            cr, uid, name, context=context)
        quant_obj = self.pool.get('stock.quant')
        self.context = context
        wl_overview = quant_obj._report_xls_stock_unit_fields(
            cr, uid, context)
        tmpl_upd_overview = quant_obj._report_xls_arap_overview_template(
            cr, uid, context)
        wl_details = quant_obj._report_xls_arap_details_fields(
            cr, uid, context)
        tmpl_upd_details = quant_obj._report_xls_arap_overview_template(
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


class stock_report_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(stock_report_xls, self).__init__(
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
        ph_cell_format = _xs['bold'] + fill_blue + _xs['borders_all']
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
            'cabang': {
                'header': [1, 44, 'text', _render("_('Cabang')")],
                'lines': [1, 0, 'text', _render("p['p_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'code': {
                'header': [1, 44, 'text', _render("_('Kode Cabang')")],
                'lines': [1, 0, 'text', _render("p['p_code'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'parent_category': {
                'header': [1, 44, 'text', _render("_('Category')")],
                'lines': [1, 0, 'text', _render("p['p_parent_category'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},              
            'p_categ_name': {
                'header': [1, 44, 'text', _render("_('Kategori')")],
                'lines': [1, 0, 'text', _render("p['p_categ_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                    
            'kode_product': {
                'header': [1, 22, 'text', _render("_('Kode Unit')")],
                'lines': [1, 0, 'text', _render("p['p_kode_product'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                        
            'default_code': {
                'header': [1, 22, 'text', _render("_('Deskripsi')")],
                'lines': [1, 0, 'text', _render("p['p_default_code'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'color': {
                'header': [1, 22, 'text', _render("_('Warna')")],
                'lines': [1, 0, 'text', _render("p['p_warna'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'location_id': {
                'header': [1, 22, 'text', _render("_('Lokasi')")],
                'lines': [1, 0, 'text', _render("p['p_nama_lokasi'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'tanggal': {
                'header': [1, 22, 'text', _render("_('Tanggal GRN')")],
                'lines': [1, 0, 'text', _render("p['p_tanggal'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'grn_no': {
                'header': [1, 22, 'text', _render("_('Nomor GRN')")],
                'lines': [1, 0, 'text', _render("p['p_grn_no'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'engine': {
                'header': [1, 22, 'text', _render("_('Mesin')")],
                'lines': [1, 0, 'text', _render("p['p_mesin'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'chassis': {
                'header': [1, 22, 'text', _render("_('Rangka')")],
                'lines': [1, 0, 'text', _render("p['p_rangka'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'tahun': {
                'header': [1, 22, 'text', _render("_('Tahun Rakit')")],
                'lines': [1, 0, 'text', _render("p['p_tahun'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'jumlah': {
                'header': [1, 22, 'text', _render("_('Jumlah')")],
                'lines': [1, 0, 'text', _render("p['p_qty'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'nilai': {
                'header': [1, 22, 'text', _render("_('Nilai Stock')")],
                'lines': [1, 0, 'number', _render("p['p_cost']")],
                'totals': [1, 0, 'number', None]},
            'state_stock': {
                'header': [1, 22, 'text', _render("_('Posisi Stock')")],
                'lines': [1, 0, 'text', _render("p['state_stock'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'state': {
                'header': [1, 22, 'text', _render("_('Status')")],
                'lines': [1, 0, 'text', _render("p['p_state'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'umur': {
                'header': [1, 22, 'text', _render("_('Umur Stock / (hari)')")],
                'lines': [1, 0, 'text', _render("p['p_umur'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'umur_mutasi': {
                'header': [1, 22, 'text', _render("_('Umur Mutasi / (hari)')")],
                'lines': [1, 0, 'text', _render("p['p_umur_mutasi'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'origin': {
                'header': [1, 22, 'text', _render("_('Source Doc')")],
                'lines': [1, 0, 'text', _render("p['p_origin'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'branch_source': {
                'header': [1, 22, 'text', _render("_('Source Branch')")],
                'lines': [1, 0, 'text', _render("p['branch_source'] or 'n/a'")],
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
            
            if r['show_valuation'] == True:
                wanted_list_overview.append('nilai')
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
            cell_style = xlwt.easyxf(_xs['xls_title'])
            report_name = ' '.join(
                [_p.company.name, r['title'], _('Laporan Stock Unit'),
                 _p.report_info])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            row_pos_o += 1
            report_name = ' '.join(
                [_p.company.name, r['title'], _('Details'),
                 _p.report_info + ' ' + _p.company.currency_id.name])
            c_specs_d = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_d, ['report_name'])
            
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

            for p in r['partners']:
                c_specs_o = map(
                    lambda x: self.render(
                        x, self.col_specs_template_overview, 'lines'),
                    wanted_list_overview)
                row_data = self.xls_row_template(
                    c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
                row_pos_d += 1

stock_report_xls(
    'report.dym.stock.report.unit.xls',
    'account.period',
    parser=dym_stock_unit_report_print_xls)
