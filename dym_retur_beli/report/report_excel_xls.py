import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .report_excel import dym_report_retur_pembelian_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)
import string

_ir_translation_name = 'report.retur.pembelian'

class dym_report_retur_pembelian_print_xls(dym_report_retur_pembelian_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_retur_pembelian_print_xls, self).__init__(
            cr, uid, name, context=context)
        move_line_obj = self.pool.get('dym.retur.beli')
        self.context = context
        wl_overview = move_line_obj._report_xls_retur_pembelian_fields(
            cr, uid, context)
        wl_overview_non_unit = move_line_obj._report_xls_retur_pembelian_non_unit_fields(cr, uid, context)
        tmpl_upd_overview = move_line_obj._report_xls_arap_overview_template(
            cr, uid, context)
        wl_details = move_line_obj._report_xls_arap_details_fields(
            cr, uid, context)
        tmpl_upd_details = move_line_obj._report_xls_arap_overview_template(
            cr, uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': wl_overview,
            'wanted_list_overview_non_unit': wl_overview_non_unit,
            'template_update_overview': tmpl_upd_overview,
            'wanted_list_details': wl_details,
            'template_update_details': tmpl_upd_details,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src

class report_retur_pembelian_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(report_retur_pembelian_xls, self).__init__(
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
           'division': {
               'header': [1, 22, 'text', _render("_('Divisi')")],
               'lines': [1, 0, 'text', _render("p['division']")],
               'totals': [1, 22, 'text', None]},
            'number': {
                'header': [1, 22, 'text', _render("_('No Register Retur')")],
                'lines': [1, 0, 'text', _render("p['number']")],
                'totals': [1, 22, 'text', None]},
            'date': {
                'header': [1, 22, 'text', _render("_('Tgl Register Retur')")],
                'lines': [1, 0, 'text', _render("p['date']")],
                'totals': [1, 22, 'text', None]},
            'invoice_retur': {
                'header': [1, 22, 'text', _render("_('Invoice Retur')")],
                'lines': [1, 0, 'text', _render("p['invoice_retur']")],
                'totals': [1, 22, 'text', None]},
            'supplier_invoice_number': {
                'header': [1, 22, 'text', _render("_('No Invoice (Supplier)')")],
                'lines': [1, 0, 'text', _render("p['supplier_invoice_number']")],
                'totals': [1, 22, 'text', None]},
            'document_date': {
                'header': [1, 22, 'text', _render("_('Tgl Invoice (Supplier)')")],
                'lines': [1, 0, 'text', _render("p['document_date']")],
                'totals': [1, 22, 'text', None]},
            'supplier': {
                'header': [1, 22, 'text', _render("_('Supplier')")],
                'lines': [1, 0, 'text', _render("p['supplier']")],
                'totals': [1, 22, 'text', None]},
            'coa': {
                'header': [1, 22, 'text', _render("_('COA')")],
                'lines': [1, 0, 'text', _render("p['coa']")],
                'totals': [1, 22, 'text', None]},
            'kode': {
                'header': [1, 22, 'text', _render("_('Kode Produk')")],
                'lines': [1, 0, 'text', _render("p['kode']")],
                'totals': [1, 22, 'text', None]},
            'deskripsi': {
                'header': [1, 22, 'text', _render("_('Deskripsi Produk')")],
                'lines': [1, 0, 'text', _render("p['deskripsi']")],
                'totals': [1, 22, 'text', None]},
            'warna': {
                'header': [1, 22, 'text', _render("_('Warna')")],
                'lines': [1, 0, 'text', _render("p['warna']")],
                'totals': [1, 22, 'text', None]},
            'engine_number': {
                'header': [1, 22, 'text', _render("_('No. Mesin')")],
                'lines': [1, 0, 'text', _render("p['engine_number']")],
                'totals': [1, 22, 'text', None]},
            'chassis_number': {
                'header': [1, 22, 'text', _render("_('No. Rangka')")],
                'lines': [1, 0, 'text', _render("p['chassis_number']")],
                'totals': [1, 22, 'text', None]},
            'price_unit': {
                'header': [1, 22, 'text', _render("_('Pembelian')")],
                'lines': [1, 0, 'number', _render("p['price_unit']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['price_unit']"), None, self.rt_cell_style_decimal]},
            'discount_amount': {
                'header': [1, 22, 'text', _render("_('Diskon')")],
                'lines': [1, 0, 'number', _render("p['discount_amount']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['discount_amount']"), None, self.rt_cell_style_decimal]},
            'price_subtotal': {
                'header': [1, 22, 'text', _render("_('Subtotal')")],
                'lines': [1, 0, 'number', _render("p['price_subtotal']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['price_subtotal']"), None, self.rt_cell_style_decimal]},
            'jumlah': {
                'header': [1, 22, 'text', _render("_('Jumlah')")],
                'lines': [1, 0, 'number', _render("p['jumlah']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['jumlah']"), None, self.rt_cell_style_decimal]},
            'product_qty': {
                'header': [1, 22, 'text', _render("_('Qty')")],
                'lines': [1, 0, 'number', _render("p['product_qty']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['product_qty']"), None, self.rt_cell_style_decimal]},
            'dpp': {
                'header': [1, 22, 'text', _render("_('DPP')")],
                'lines': [1, 0, 'number', _render("p['dpp']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['dpp']"), None, self.rt_cell_style_decimal]},
            'ppn': {
                'header': [1, 22, 'text', _render("_('PPN')")],
                'lines': [1, 0, 'number', _render("p['ppn']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['ppn']"), None, self.rt_cell_style_decimal]},
            'oos_number': {
               'header': [1, 22, 'text', _render("_('No. OOS')")],
               'lines': [1, 0, 'text', _render("p['oos_number']")],
               'totals': [1, 22, 'text', None]},
            'payment_number': {
               'header': [1, 22, 'text', _render("_('No. Payment')")],
               'lines': [1, 0, 'text', _render("p['payment_number']")],
               'totals': [1, 22, 'text', None]},
            'payment_date': {
               'header': [1, 22, 'text', _render("_('Date Payment')")],
               'lines': [1, 0, 'text', _render("p['payment_date']")],
               'totals': [1, 22, 'text', None]},
            'payment_reallocation': {
               'header': [1, 22, 'text', _render("_('Reallocation Payment')")],
               'lines': [1, 0, 'number', _render("p['payment_reallocation']"), None, self.pd_cell_style_decimal],
               'totals': [1, 22, 'text', None]},
            'saldo': {
               'header': [1, 22, 'text', _render("_('Saldo')")],
               'lines': [1, 0, 'number', _render("p['saldo']"), None, self.pd_cell_style_decimal],
               'totals': [1, 22, 'text', None]},
            'retur_type': {
               'header': [1, 22, 'text', _render("_('Tipe Retur')")],
               'lines': [1, 0, 'text', _render("p['retur_type']"), None, self.pd_cell_style_decimal],
               'totals': [1, 22, 'text', None]},
           'hutang': {
               'header': [1, 22, 'text', _render("_('Hutang')")],
               'lines': [1, 0, 'number', _render("p['hutang']"), None, self.pd_cell_style_decimal],
               'totals': [1, 22, 'text', None]},
            'nilai_persediaan': {
               'header': [1, 22, 'text', _render("_('Persediaan/HPP')")],
               'lines': [1, 0, 'number', _render("p['nilai_persediaan']"), None, self.pd_cell_style_decimal],
               'totals': [1, 22, 'text', None]},
            'invoice_beli_number': {
               'header': [1, 22, 'text', _render("_('No Nota Pembelian')")],
               'lines': [1, 0, 'text', _render("p['invoice_beli_number']")],
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
            if r['division'] == 'Unit':
                wanted_list_overview = _p.wanted_list_overview
            else:
                wanted_list_overview = _p.wanted_list_overview_non_unit
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
                [_('LAPORAN Retur Pembelian Per Tanggal'), _(str(datetime.today().date())),
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
            for p in r['id_retur_line']:
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
            if r['division'] == 'Unit':
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
                ws_o.write(row_pos_o, 10, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 11, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 12, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 13, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 14, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 15, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 16, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 17, xlwt.Formula("SUM(R"+str(row_data_begin)+":R"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 18, xlwt.Formula("SUM(S"+str(row_data_begin)+":S"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 19, xlwt.Formula("SUM(T"+str(row_data_begin)+":T"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 20, xlwt.Formula("SUM(U"+str(row_data_begin)+":U"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 21, xlwt.Formula("SUM(V"+str(row_data_begin)+":V"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 22, xlwt.Formula("SUM(W"+str(row_data_begin)+":W"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 23, xlwt.Formula("SUM(X"+str(row_data_begin)+":X"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 24, xlwt.Formula("SUM(Y"+str(row_data_begin)+":Y"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 25, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 26, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 27, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 28, xlwt.Formula("SUM(AC"+str(row_data_begin)+":AC"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 29, xlwt.Formula("SUM(AD"+str(row_data_begin)+":AD"+str(row_data_end)+")"), self.rt_cell_style_decimal)

            else:
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
                ws_o.write(row_pos_o, 10, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 11, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 12, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 13, xlwt.Formula("SUM(N"+str(row_data_begin)+":N"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 15, xlwt.Formula("SUM(P"+str(row_data_begin)+":P"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 16, xlwt.Formula("SUM(Q"+str(row_data_begin)+":Q"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 17, xlwt.Formula("SUM(R"+str(row_data_begin)+":R"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 18, xlwt.Formula("SUM(S"+str(row_data_begin)+":S"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 19, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 20, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 21, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 22, xlwt.Formula("SUM(W"+str(row_data_begin)+":W"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 23, xlwt.Formula("SUM(X"+str(row_data_begin)+":X"+str(row_data_end)+")"), self.rt_cell_style_decimal)

            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, _p.report_date + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_retur_pembelian_xls('report.Laporan Retur Pembelian', 'dym.retur.beli', parser = dym_report_retur_pembelian_print_xls)
