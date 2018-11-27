import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_penjualansum import dym_report_penjualansum_print
from openerp.tools.translate import translate
import string

_ir_translation_name = 'report.penjualansum'

class dym_report_penjualansum_print_xls(dym_report_penjualansum_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_penjualansum_print_xls, self).__init__(cr, uid, name, context=context)
        dso_obj = self.pool.get('dealer.sale.order')
        self.context = context
        wl_overview = dso_obj._report_xls_penjualansum_fields(cr, uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': wl_overview,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src

class report_penjualansum_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_penjualansum_xls, self).__init__(name, table, rml, parser, header, store)

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
                'header': [1, 5, 'text', _render("_('No.')")],
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
            'cash': {
                'header': [1, 22, 'text', _render("_('Cash')")],
                'lines': [1, 0, 'number', _render("p['cash']")],
                'totals': [1, 22, 'number', _render("p['cash']")]},
            'retur_cash': {
                'header': [1, 22, 'text', _render("_('Retur Cash')")],
                'lines': [1, 0, 'number', _render("p['retur_cash']")],
                'totals': [1, 22, 'number', _render("p['retur_cash']")]},
            'net_cash': {
                'header': [1, 22, 'text', _render("_('Net Cash')")],
                'lines': [1, 0, 'number', _render("p['net_cash']")],
                'totals': [1, 22, 'number', _render("p['net_cash']")]},
            'adira': {
                'header': [1, 22, 'text', _render("_('ADIRA')")],
                'lines': [1, 0, 'number', _render("p['adira']")],
                'totals': [1, 22, 'number', _render("p['adira']")]},
            'retur_adira': {
                'header': [1, 22, 'text', _render("_('Retur ADIRA')")],
                'lines': [1, 0, 'number', _render("p['retur_adira']")],
                'totals': [1, 22, 'number', _render("p['retur_adira']")]},
            'net_adira': {
                'header': [1, 22, 'text', _render("_('Net ADIRA')")],
                'lines': [1, 0, 'number', _render("p['net_adira']")],
                'totals': [1, 22, 'number', _render("p['net_adira']")]},
            'fif': {
                'header': [1, 22, 'text', _render("_('FIF')")],
                'lines': [1, 0, 'number', _render("p['fif']")],
                'totals': [1, 22, 'number', _render("p['fif']")]},
            'retur_fif': {
                'header': [1, 22, 'text', _render("_('Retur FIF')")],
                'lines': [1, 0, 'number', _render("p['retur_fif']")],
                'totals': [1, 22, 'number', _render("p['retur_fif']")]},
            'net_fif': {
                'header': [1, 22, 'text', _render("_('Net FIF')")],
                'lines': [1, 0, 'number', _render("p['net_fif']")],
                'totals': [1, 22, 'number', _render("p['net_fif']")]},
            'ifi': {
                'header': [1, 22, 'text', _render("_('IFI')")],
                'lines': [1, 0, 'number', _render("p['ifi']")],
                'totals': [1, 22, 'number', _render("p['ifi']")]},
            'retur_ifi': {
                'header': [1, 22, 'text', _render("_('Retur IFI')")],
                'lines': [1, 0, 'number', _render("p['retur_ifi']")],
                'totals': [1, 22, 'number', _render("p['retur_ifi']")]},
            'net_ifi': {
                'header': [1, 22, 'text', _render("_('Net IFI')")],
                'lines': [1, 0, 'number', _render("p['net_ifi']")],
                'totals': [1, 22, 'number', _render("p['net_ifi']")]},
            'sof': {
                'header': [1, 22, 'text', _render("_('SOF')")],
                'lines': [1, 0, 'number', _render("p['sof']")],
                'totals': [1, 22, 'number', _render("p['sof']")]},
            'retur_sof': {
                'header': [1, 22, 'text', _render("_('Retur SOF')")],
                'lines': [1, 0, 'number', _render("p['retur_sof']")],
                'totals': [1, 22, 'number', _render("p['retur_sof']")]},
            'net_sof': {
                'header': [1, 22, 'text', _render("_('Net SOF')")],
                'lines': [1, 0, 'number', _render("p['net_sof']")],
                'totals': [1, 22, 'number', _render("p['net_sof']")]},
            'csf': {
                'header': [1, 22, 'text', _render("_('CSF')")],
                'lines': [1, 0, 'number', _render("p['csf']")],
                'totals': [1, 22, 'number', _render("p['csf']")]},
            'retur_csf': {
                'header': [1, 22, 'text', _render("_('Retur CSF')")],
                'lines': [1, 0, 'number', _render("p['retur_csf']")],
                'totals': [1, 22, 'number', _render("p['retur_csf']")]},
            'net_csf': {
                'header': [1, 22, 'text', _render("_('Net CSF')")],
                'lines': [1, 0, 'number', _render("p['net_csf']")],
                'totals': [1, 22, 'number', _render("p['net_csf']")]},
            'mpmf': {
                'header': [1, 22, 'text', _render("_('MPMF')")],
                'lines': [1, 0, 'number', _render("p['mpmf']")],
                'totals': [1, 22, 'number', _render("p['mpmf']")]},
            'retur_mpmf': {
                'header': [1, 22, 'text', _render("_('Retur MPMF')")],
                'lines': [1, 0, 'number', _render("p['retur_mpmf']")],
                'totals': [1, 22, 'number', _render("p['retur_mpmf']")]},
            'net_mpmf': {
                'header': [1, 22, 'text', _render("_('Net MPMF')")],
                'lines': [1, 0, 'number', _render("p['net_mpmf']")],
                'totals': [1, 22, 'number', _render("p['net_mpmf']")]},
            'wom': {
                'header': [1, 22, 'text', _render("_('WOM')")],
                'lines': [1, 0, 'number', _render("p['wom']")],
                'totals': [1, 22, 'number', _render("p['wom']")]},
            'retur_wom': {
                'header': [1, 22, 'text', _render("_('Retur WOM')")],
                'lines': [1, 0, 'number', _render("p['retur_wom']")],
                'totals': [1, 22, 'number', _render("p['retur_wom']")]},
            'net_wom': {
                'header': [1, 22, 'text', _render("_('Net WOM')")],
                'lines': [1, 0, 'number', _render("p['net_wom']")],
                'totals': [1, 22, 'number', _render("p['net_wom']")]},
            'rbf': {
                'header': [1, 22, 'text', _render("_('RBF')")],
                'lines': [1, 0, 'number', _render("p['rbf']")],
                'totals': [1, 22, 'number', _render("p['rbf']")]},
            'retur_rbf': {
                'header': [1, 22, 'text', _render("_('Retur RBF')")],
                'lines': [1, 0, 'number', _render("p['retur_rbf']")],
                'totals': [1, 22, 'number', _render("p['retur_rbf']")]},
            'net_rbf': {
                'header': [1, 22, 'text', _render("_('Net RBF')")],
                'lines': [1, 0, 'number', _render("p['net_rbf']")],
                'totals': [1, 22, 'number', _render("p['net_rbf']")]},
            'mcf': {
                'header': [1, 22, 'text', _render("_('MCF')")],
                'lines': [1, 0, 'number', _render("p['mcf']")],
                'totals': [1, 22, 'number', _render("p['mcf']")]},
            'retur_mcf': {
                'header': [1, 22, 'text', _render("_('Retur MCF')")],
                'lines': [1, 0, 'number', _render("p['retur_mcf']")],
                'totals': [1, 22, 'number', _render("p['retur_mcf']")]},
            'net_mcf': {
                'header': [1, 22, 'text', _render("_('Net MCF')")],
                'lines': [1, 0, 'number', _render("p['net_mcf']")],
                'totals': [1, 22, 'number', _render("p['net_mcf']")]},
            'mandiri_utama': {
                'header': [1, 22, 'text', _render("_('Mandiri Utama')")],
                'lines': [1, 0, 'number', _render("p['mandiri_utama']")],
                'totals': [1, 22, 'number', _render("p['mandiri_utama']")]},
            'retur_mandiri_utama': {
                'header': [1, 22, 'text', _render("_('Retur Mandiri Utama')")],
                'lines': [1, 0, 'number', _render("p['retur_mandiri_utama']")],
                'totals': [1, 22, 'number', _render("p['retur_mandiri_utama']")]},
            'net_mandiri_utama': {
                'header': [1, 22, 'text', _render("_('Net Mandiri Utama')")],
                'lines': [1, 0, 'number', _render("p['net_mandiri_utama']")],
                'totals': [1, 22, 'number', _render("p['net_mandiri_utama']")]},
            'mandiri_tunas': {
                'header': [1, 22, 'text', _render("_('Mandiri Tunas')")],
                'lines': [1, 0, 'number', _render("p['mandiri_tunas']")],
                'totals': [1, 22, 'number', _render("p['mandiri_tunas']")]},
            'retur_mandiri_tunas': {
                'header': [1, 22, 'text', _render("_('Retur Mandiri Tunas')")],
                'lines': [1, 0, 'number', _render("p['retur_mandiri_tunas']")],
                'totals': [1, 22, 'number', _render("p['retur_mandiri_tunas']")]},
            'net_mandiri_tunas': {
                'header': [1, 22, 'text', _render("_('Net Mandiri Tunas')")],
                'lines': [1, 0, 'number', _render("p['net_mandiri_tunas']")],
                'totals': [1, 22, 'number', _render("p['net_mandiri_tunas']")]},
            'mandala': {
                'header': [1, 22, 'text', _render("_('Mandala')")],
                'lines': [1, 0, 'number', _render("p['mandala']")],
                'totals': [1, 22, 'number', _render("p['mandala']")]},
            'retur_mandala': {
                'header': [1, 22, 'text', _render("_('Retur Mandala')")],
                'lines': [1, 0, 'number', _render("p['retur_mandala']")],
                'totals': [1, 22, 'number', _render("p['retur_mandala']")]},
            'net_mandala': {
                'header': [1, 22, 'text', _render("_('Net Mandala')")],
                'lines': [1, 0, 'number', _render("p['net_mandala']")],
                'totals': [1, 22, 'number', _render("p['net_mandala']")]},
            'astra_buana': {
                'header': [1, 22, 'text', _render("_('Astra Buana')")],
                'lines': [1, 0, 'number', _render("p['astra_buana']")],
                'totals': [1, 22, 'number', _render("p['astra_buana']")]},
            'retur_astra_buana': {
                'header': [1, 22, 'text', _render("_('Retur Astra Buana')")],
                'lines': [1, 0, 'number', _render("p['retur_astra_buana']")],
                'totals': [1, 22, 'number', _render("p['retur_astra_buana']")]},
            'net_astra_buana': {
                'header': [1, 22, 'text', _render("_('Net Astra Buana')")],
                'lines': [1, 0, 'number', _render("p['net_astra_buana']")],
                'totals': [1, 22, 'number', _render("p['net_astra_buana']")]},
            'jual_pic': {
                'header': [1, 22, 'text', _render("_('Jual PIC')")],
                'lines': [1, 0, 'number', _render("p['jual_pic']")],
                'totals': [1, 22, 'number', _render("p['jual_pic']")]},
            'retur_jual_pic': {
                'header': [1, 22, 'text', _render("_('Retur Jual PIC')")],
                'lines': [1, 0, 'number', _render("p['retur_jual_pic']")],
                'totals': [1, 22, 'number', _render("p['retur_jual_pic']")]},
            'net_jual_pic': {
                'header': [1, 22, 'text', _render("_('Net Jual PIC')")],
                'lines': [1, 0, 'number', _render("p['net_jual_pic']")],
                'totals': [1, 22, 'number', _render("p['net_jual_pic']")]},
            'total_credit': {
                'header': [1, 22, 'text', _render("_('Total Credit')")],
                'lines': [1, 0, 'number', _render("p['total_credit']")],
                'totals': [1, 22, 'number', _render("p['total_credit']")]},
            'retur_credit': {
                'header': [1, 22, 'text', _render("_('Retur Credit')")],
                'lines': [1, 0, 'number', _render("p['retur_credit']")],
                'totals': [1, 22, 'number', _render("p['retur_credit']")]},
            'net_credit': {
                'header': [1, 22, 'text', _render("_('Net Credit')")],
                'lines': [1, 0, 'number', _render("p['net_credit']")],
                'totals': [1, 22, 'number', _render("p['net_credit']")]},
            'penjualan_bruto': {
                'header': [1, 22, 'text', _render("_('Total Penjualan Bruto')")],
                'lines': [1, 0, 'number', _render("p['penjualan_bruto']")],
                'totals': [1, 22, 'number', _render("p['penjualan_bruto']")]},
            'retur_penjualan': {
                'header': [1, 22, 'text', _render("_('Retur Penjualan')")],
                'lines': [1, 0, 'number', _render("p['retur_penjualan']")],
                'totals': [1, 22, 'number', _render("p['retur_penjualan']")]},
            'net_penjualan': {
                'header': [1, 22, 'text', _render("_('Net Penjualan')")],
                'lines': [1, 0, 'number', _render("p['net_penjualan']")],
                'totals': [1, 22, 'number', _render("p['net_penjualan']")]},
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        self.col_specs_template_overview.update({})
        _ = _p._

        for r in _p.reports:
            # title_short = r['title_short'].replace('/', '-')
            ws_o = wb.add_sheet('Laporan Penjualan (Summary)')
           
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
            report_name = ' '.join(
                [_('LAPORAN Penjualan Summary (Qty) Per Tanggal '), _('-' if data['end_date'] == False else str(data['end_date']))])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            
            ## Start Date & End Date ##
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join(
                [_('Tanggal'), _('-' if data['start_date'] == False else str(data['start_date'])), _('s/d'), _('-' if data['end_date'] == False else str(data['end_date']))])
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
            for p in r['datas']:
                c_specs_o = map(
                    lambda x: self.render(x, self.col_specs_template_overview, 'lines'),
                    wanted_list_overview)
                for x in c_specs_o :
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
            ws_o.set_vert_split_pos(3)
            ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 4, xlwt.Formula("SUM(E"+str(row_data_begin)+":E"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 5, xlwt.Formula("SUM(F"+str(row_data_begin)+":F"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 6, xlwt.Formula("SUM(G"+str(row_data_begin)+":G"+str(row_data_end)+")"), self.rt_cell_style_decimal)   
            ws_o.write(row_pos_o, 7, xlwt.Formula("SUM(H"+str(row_data_begin)+":H"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 8, xlwt.Formula("SUM(I"+str(row_data_begin)+":I"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 9, xlwt.Formula("SUM(J"+str(row_data_begin)+":J"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 10, xlwt.Formula("SUM(K"+str(row_data_begin)+":K"+str(row_data_end)+")"), self.rt_cell_style_decimal)   
            ws_o.write(row_pos_o, 11, xlwt.Formula("SUM(L"+str(row_data_begin)+":L"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 12, xlwt.Formula("SUM(M"+str(row_data_begin)+":M"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 13, xlwt.Formula("SUM(N"+str(row_data_begin)+":N"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 15, xlwt.Formula("SUM(P"+str(row_data_begin)+":P"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 16, xlwt.Formula("SUM(Q"+str(row_data_begin)+":Q"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 17, xlwt.Formula("SUM(R"+str(row_data_begin)+":R"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 18, xlwt.Formula("SUM(S"+str(row_data_begin)+":S"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 19, xlwt.Formula("SUM(T"+str(row_data_begin)+":T"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 20, xlwt.Formula("SUM(U"+str(row_data_begin)+":U"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 21, xlwt.Formula("SUM(V"+str(row_data_begin)+":V"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 22, xlwt.Formula("SUM(W"+str(row_data_begin)+":W"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 23, xlwt.Formula("SUM(X"+str(row_data_begin)+":X"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 24, xlwt.Formula("SUM(Y"+str(row_data_begin)+":Y"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 25, xlwt.Formula("SUM(Z"+str(row_data_begin)+":Z"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 26, xlwt.Formula("SUM(AA"+str(row_data_begin)+":AA"+str(row_data_end)+")"), self.rt_cell_style_decimal)
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
            
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_penjualansum_xls(
    'report.Laporan Penjualan Sum',
    'dealer.sale.order',
    parser = dym_report_penjualansum_print_xls)
