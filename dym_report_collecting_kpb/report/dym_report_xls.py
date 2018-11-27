import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report import dym_report_collecting_kpb_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)
import string

_ir_translation_name = 'report.collecting.kpb'

class dym_report_collecting_kpb_print_xls(dym_report_collecting_kpb_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_collecting_kpb_print_xls, self).__init__(
            cr, uid, name, context=context)
        move_line_obj = self.pool.get('dym.collecting.kpb.line')
        self.context = context
        wl_overview = move_line_obj._report_xls_collecting_kpb_fields(
            cr, uid, context)
        wl_overview_mutasi = move_line_obj._report_xls_collecting_kpb_mutasi_fields(
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
            'wanted_list_overview_mutasi': wl_overview_mutasi,
            'template_update_overview': tmpl_upd_overview,
            'wanted_list_details': wl_details,
            'template_update_details': tmpl_upd_details,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src

class report_collecting_kpb_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(report_collecting_kpb_xls, self).__init__(
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
            'branch_id': {
                'header': [1, 22, 'text', _render("_('Cabang')")],
                'lines': [1, 0, 'text', _render("p['branch_id']")],
                'totals': [1, 22, 'text', _render("_('Total')")]},
            'number': {
                'header': [1, 22, 'text', _render("_('No Transaksi')")],
                'lines': [1, 0, 'text', _render("p['number']")],
                'totals': [1, 22, 'text', None]},
           'no_claim_md': {
               'header': [1, 22, 'text', _render("_('No Claim MD')")],
               'lines': [1, 0, 'text', _render("p['no_claim_md']")],
               'totals': [1, 22, 'text', None]},
            'date': {
                'header': [1, 22, 'text', _render("_('Tanggal Transaksi')")],
                'lines': [1, 0, 'text', _render("p['date']")],
                'totals': [1, 22, 'text', None]},
            'category': {
                'header': [1, 22, 'text', _render("_('Category')")],
                'lines': [1, 0, 'text', _render("p['category']")],
                'totals': [1, 22, 'text', None]},
            'kpb_ke': {
                'header': [1, 22, 'text', _render("_('KPB Ke')")],
                'lines': [1, 0, 'text', _render("p['kpb_ke']")],
                'totals': [1, 22, 'text', None]},
            'no_wo': {
                'header': [1, 22, 'text', _render("_('No. WO')")],
                'lines': [1, 0, 'text', _render("p['no_wo']")],
                'totals': [1, 22, 'text', None]},
            'no_kartu': {
                'header': [1, 22, 'text', _render("_('No. Kartu')")],
                'lines': [1, 0, 'text', _render("p['no_kartu']")],
                'totals': [1, 22, 'text', None]},
            'invoice_jasa_number': {
                'header': [1, 22, 'text', _render("_('JASA')")],
                'lines': [1, 0, 'text', _render("p['invoice_jasa_number']")],
                'totals': [1, 22, 'text', None]},
            'invoice_oli_number': {
                'header': [1, 22, 'text', _render("_('OLI')")],
                'lines': [1, 0, 'text', _render("p['invoice_oli_number']")],
                'totals': [1, 22, 'text', None]},
            'invoice_kompensasi_number': {
                'header': [1, 22, 'text', _render("_('KOMPENSASI OLI')")],
                'lines': [1, 0, 'text', _render("p['invoice_kompensasi_number']")],
                'totals': [1, 22, 'text', None]},
            'state': {
                'header': [1, 22, 'text', _render("_('Status Collecting')")],
                'lines': [1, 0, 'text', _render("p['state']")],
                'totals': [1, 22, 'text', None]},
            'invoice_jasa_amount': {
                'header': [1, 22, 'text', _render("_('Nilai')")],
                'lines': [1, 0, 'number', _render("p['invoice_jasa_amount']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['invoice_jasa_amount']"), None, self.rt_cell_style_decimal]},
            'invoice_oli_amount': {
                'header': [1, 22, 'text', _render("_('Nilai')")],
                'lines': [1, 0, 'number', _render("p['invoice_oli_amount']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['invoice_oli_amount']"), None, self.rt_cell_style_decimal]},
            'invoice_kompensasi_amount': {
                'header': [1, 22, 'text', _render("_('Nilai')")],
                'lines': [1, 0, 'number', _render("p['invoice_kompensasi_amount']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['invoice_kompensasi_amount']"), None, self.rt_cell_style_decimal]},
            'total': {
                'header': [1, 22, 'text', _render("_('Total')")],
                'lines': [1, 0, 'number', _render("p['total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['total']"), None, self.rt_cell_style_decimal]},
            'qty_claim': {
                'header': [1, 22, 'text', _render("_('QTY on Claim')")],
                'lines': [1, 0, 'number', _render("p['qty_claim']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['qty_claim']"), None, self.rt_cell_style_decimal]},
            'sisa_nrfs': {
                'header': [1, 22, 'text', _render("_('Sisa NRFS')")],
                'lines': [1, 0, 'number', _render("p['sisa_nrfs']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['sisa_nrfs']"), None, self.rt_cell_style_decimal]},
            'int_trf_qty': {
                'header': [1, 22, 'text', _render("_('QTY on Internal Transfer')")],
                'lines': [1, 0, 'number', _render("p['int_trf_qty']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['int_trf_qty']"), None, self.rt_cell_style_decimal]},
            'int_trf_number': {
                'header': [1, 22, 'text', _render("_('No. Internal Transfer')")],
                'lines': [1, 0, 'text', _render("p['int_trf_number']")],
                'totals': [1, 22, 'text', None]},
            'int_trf_date': {
                'header': [1, 22, 'text', _render("_('Tgl Internal Transfer')")],
                'lines': [1, 0, 'text', _render("p['int_trf_date']")],
                'totals': [1, 22, 'text', None]},
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
            option = r['option']
            if option == 'invoice':
                wanted_list_overview = _p.wanted_list_overview
            elif option == 'mutasi':
                wanted_list_overview = _p.wanted_list_overview_mutasi

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
                [_(title_short), _(str(datetime.today().date())),
                 _p.report_info])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            
            ## Tanggal Trx Start Date & End Date ##
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join(
                [_('Tanggal Transaksi'), _('-' if data['trx_start_date'] == False else str(data['trx_start_date'])), _('s/d'), _('-' if data['trx_end_date'] == False else str(data['trx_end_date'])),
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
            for p in r['id_ai']:
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
            if option == 'invoice':
                ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)
                ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 6, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 7, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 8, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 9, xlwt.Formula("SUM(J"+str(row_data_begin)+":J"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 10, xlwt.Formula("SUM(K"+str(row_data_begin)+":K"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 11, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 12, xlwt.Formula("SUM(M"+str(row_data_begin)+":M"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 13, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 15, xlwt.Formula("SUM(P"+str(row_data_begin)+":P"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 16, None, self.rt_cell_style_decimal)
            elif option == 'mutasi':
                ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)
                ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 5, xlwt.Formula("SUM(F"+str(row_data_begin)+":F"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 6, xlwt.Formula("SUM(G"+str(row_data_begin)+":G"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 7, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 8, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 9, xlwt.Formula("SUM(J"+str(row_data_begin)+":J"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, _p.report_date + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_collecting_kpb_xls('report.Laporan Collecting KPB', 'dym.collecting.kpb.line', parser = dym_report_collecting_kpb_print_xls)
