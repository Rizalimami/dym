import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report import dym_report_service_rate_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)
import string

_ir_translation_name = 'report.service.rate'

class dym_report_service_rate_print_xls(dym_report_service_rate_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_service_rate_print_xls, self).__init__(
            cr, uid, name, context=context)
        move_line_obj = self.pool.get('dym.work.order.line')
        self.context = context
        wl_overview = move_line_obj._report_xls_service_rate_fields(
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

class report_service_rate_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(report_service_rate_xls, self).__init__(
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
           'tipe_dok': {
               'header': [1, 22, 'text', _render("_('TIPE DOK')")],
               'lines': [1, 0, 'text', _render("p['tipe_dok']")],
               'totals': [1, 22, 'text', None]},
            'date': {
                'header': [1, 22, 'text', _render("_('Tanggal Transaksi')")],
                'lines': [1, 0, 'text', _render("p['date']")],
                'totals': [1, 22, 'text', None]},
            'number': {
                'header': [1, 22, 'text', _render("_('No Transaksi')")],
                'lines': [1, 0, 'text', _render("p['number']")],
                'totals': [1, 22, 'text', None]},
            'product_code': {
                'header': [1, 22, 'text', _render("_('KODE PART')")],
                'lines': [1, 0, 'text', _render("p['product_code']")],
                'totals': [1, 22, 'text', None]},
            'product_name': {
                'header': [1, 22, 'text', _render("_('DESKRIPSI')")],
                'lines': [1, 0, 'text', _render("p['product_name']")],
                'totals': [1, 22, 'text', None]},
            'het': {
                'header': [1, 22, 'text', _render("_('HET')")],
                'lines': [1, 0, 'number', _render("p['het']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['het']"), None, self.rt_cell_style_decimal]},
            'qty_demand': {
                'header': [1, 22, 'text', _render("_('QTY DEMAND')")],
                'lines': [1, 0, 'number', _render("p['qty_demand']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['qty_demand']"), None, self.rt_cell_style_decimal]},
            'qty_supply': {
                'header': [1, 22, 'text', _render("_('QTY SUPPLY')")],
                'lines': [1, 0, 'number', _render("p['qty_supply']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['qty_supply']"), None, self.rt_cell_style_decimal]},
            'qty_backorder': {
                'header': [1, 22, 'text', _render("_('QTY BACKORDER')")],
                'lines': [1, 0, 'number', _render("p['qty_backorder']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['qty_backorder']"), None, self.rt_cell_style_decimal]},
            'net_jual': {
                'header': [1, 22, 'text', _render("_('Net Jual')")],
                'lines': [1, 0, 'number', _render("p['net_jual']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['net_jual']"), None, self.rt_cell_style_decimal]},
            'jumlah_demand': {
                'header': [1, 22, 'text', _render("_('Jumlah Demand')")],
                'lines': [1, 0, 'number', _render("p['jumlah_demand']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['jumlah_demand']"), None, self.rt_cell_style_decimal]},
            'jumlah_supply': {
                'header': [1, 22, 'text', _render("_('Jumlah Supply')")],
                'lines': [1, 0, 'number', _render("p['jumlah_supply']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['jumlah_supply']"), None, self.rt_cell_style_decimal]},
            'jumlah_order': {
                'header': [1, 22, 'text', _render("_('Jumlah Order')")],
                'lines': [1, 0, 'number', _render("p['jumlah_order']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['jumlah_order']"), None, self.rt_cell_style_decimal]},
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
            ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 1, 'Grand Total', self.ph_cell_style)
            ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 6, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 7, xlwt.Formula("SUM(H"+str(row_data_begin)+":H"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 8, xlwt.Formula("SUM(I"+str(row_data_begin)+":I"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 9, xlwt.Formula("SUM(J"+str(row_data_begin)+":J"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 10, xlwt.Formula("SUM(K"+str(row_data_begin)+":K"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 11, xlwt.Formula("SUM(L"+str(row_data_begin)+":L"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 12, xlwt.Formula("SUM(M"+str(row_data_begin)+":M"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 13, xlwt.Formula("SUM(N"+str(row_data_begin)+":N"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            
            row_pos_o += 2
            ws_o.write(row_pos_o, 1, "S/R by QTY (%)", self.ph_cell_style)
            ws_o.write(row_pos_o, 2, xlwt.Formula('J'+str(row_data_end+1)+'/I'+str(row_data_end+1)+'*100'), self.rt_cell_style_decimal)
            row_pos_o += 1
            saldo_awal_pos = row_pos_o

            s_r_qty = 0
            if len(r['product_codes']) > 0:
                s_r_qty = len(r['product_supplied'])/len(r['product_codes'])
            ws_o.write(row_pos_o, 1, "S/R by ITEM (%)", self.ph_cell_style)
            ws_o.write(row_pos_o, 2, s_r_qty*100, self.ph_cell_style)
            row_pos_o += 1

            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, _p.report_date + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_service_rate_xls('report.Laporan Service Rate', 'dym.work.order.line', parser = dym_report_service_rate_print_xls)
