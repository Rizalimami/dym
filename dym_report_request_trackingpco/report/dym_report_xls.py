import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report import dym_report_request_trackingpco_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)
import string

_ir_translation_name = 'report.request.trackingpco'

class dym_report_request_trackingpco_print_xls(dym_report_request_trackingpco_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_request_trackingpco_print_xls, self).__init__(
            cr, uid, name, context=context)
        move_line_obj = self.pool.get('account.voucher')
        self.context = context
        wl_overview = move_line_obj._report_xls_request_trackingpco_fields(
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

class report_request_trackingpco_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(report_request_trackingpco_xls, self).__init__(
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
            'pco_date': {
                'header': [1, 22, 'text', _render("_('Tanggal')")],
                'lines': [1, 0, 'text', _render("p['pco_date']")],
                'totals': [1, 22, 'text', None]},
            'cabang': {
                'header': [1, 22, 'text', _render("_('Cabang')")],
                'lines': [1, 0, 'text', _render("p['cabang']")],
                'totals': [1, 22, 'text', _render("_('Total')")]},
           'division': {
               'header': [1, 22, 'text', _render("_('Divisi')")],
               'lines': [1, 0, 'text', _render("p['division']")],
               'totals': [1, 22, 'text', None]},
            'pco_number': {
                'header': [1, 22, 'text', _render("_('Number PCO')")],
                'lines': [1, 0, 'text', _render("p['pco_number']")],
                'totals': [1, 22, 'text', None]},
            'pco_state': {
                'header': [1, 22, 'text', _render("_('State Number (PCO)')")],
                'lines': [1, 0, 'text', _render("p['pco_state']")],
                'totals': [1, 22, 'text', None]},
           'pco_acc': {
              'header': [1, 22, 'text', _render("_('Account')")],
               'lines': [1, 0, 'text', _render("p['pco_acc']")],
               'totals': [1, 22, 'text', None]},
           'pco_desc': {
               'header': [1, 22, 'text', _render("_('Description')")],
               'lines': [1, 0, 'text', _render("p['pco_desc']")],
               'totals': [1, 22, 'text', None]},
           'pco_total': {
               'header': [1, 22, 'text', _render("_('Total')")],
               'lines': [1, 0, 'number', _render("p['pco_total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['pco_total']"), None, self.rt_cell_style_decimal]},
           'pco_anl_bu' :{
                'header': [1, 22, 'text', _render("_('Analytic Bisnis Unit')")],
                'lines': [1, 0, 'text', _render("p['pco_anl_bu']")],
                'totals': [1, 22, 'number', None]},
            'pco_anl_br' :{
                'header': [1, 22, 'text', _render("_('Analytic Branch')")],
                'lines': [1, 0, 'text', _render("p['pco_anl_br']")],
                'totals': [1, 22, 'number', None]},
            'pco_anl_cc' :{
                'header': [1, 22, 'text', _render("_('Analytic Cost Center')")],
                'lines': [1, 0, 'text', _render("p['pco_anl_cc']")],
                'totals': [1, 22, 'number', None]},
            'pci_number': {
                'header': [1, 22, 'text', _render("_('Number PCI')")],
                'lines': [1, 0, 'text', _render("p['pci_number']")],
                'totals': [1, 22, 'text', None]},
            'jml_kasbon': {
               'header': [1, 22, 'text', _render("_('Jumlah Kas Bon')")],
               'lines': [1, 0, 'number', _render("p['jml_kasbon']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['jml_kasbon']"), None, self.rt_cell_style_decimal]},
            'receive_amount': {
               'header': [1, 22, 'text', _render("_('Jumlah Pengembalian Kas Bon')")],
               'lines': [1, 0, 'number', _render("p['receive_amount']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['receive_amount']"), None, self.rt_cell_style_decimal]},
            'pco_new_number': {
                'header': [1, 22, 'text', _render("_('Number PCO (New)')")],
                'lines': [1, 0, 'text', _render("p['pco_new_number']")],
                'totals': [1, 22, 'text', None]},
            'pco_new_state': {
                'header': [1, 22, 'text', _render("_('State Number (PCO)')")],
                'lines': [1, 0, 'text', _render("p['pco_new_state']")],
                'totals': [1, 22, 'text', None]},
           'pco_new_acc': {
              'header': [1, 22, 'text', _render("_('Account')")],
               'lines': [1, 0, 'text', _render("p['pco_new_acc']")],
               'totals': [1, 22, 'text', None]},
           'pcol_new_desc': {
               'header': [1, 22, 'text', _render("_('Description')")],
               'lines': [1, 0, 'text', _render("p['pcol_new_desc']")],
               'totals': [1, 22, 'text', None]},
           'pco_new_total': {
               'header': [1, 22, 'text', _render("_('Total')")],
               'lines': [1, 0, 'number', _render("p['pco_new_total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['pco_new_total']"), None, self.rt_cell_style_decimal]},
           'pco_new_anl_bu' :{
                'header': [1, 22, 'text', _render("_('Analytic Bisnis Unit')")],
                'lines': [1, 0, 'text', _render("p['pco_new_anl_bu']")],
                'totals': [1, 22, 'number', None]},
            'pco_new_anl_br' :{
                'header': [1, 22, 'text', _render("_('Analytic Branch')")],
                'lines': [1, 0, 'text', _render("p['pco_new_anl_br']")],
                'totals': [1, 22, 'number', None]},
            'pco_new_anl_cc' :{
                'header': [1, 22, 'text', _render("_('Analytic Cost Center')")],
                'lines': [1, 0, 'text', _render("p['pco_new_anl_cc']")],
                'totals': [1, 22, 'number', None]},
            'reimbursed_number' :{
                'header': [1, 22, 'text', _render("_('No RPC')")],
                'lines': [1, 0, 'text', _render("p['reimbursed_number']")],
                'totals': [1, 22, 'number', None]},
            'reimbursed_request': {
                'header': [1, 22, 'text', _render("_('Date Requested')")],
                'lines': [1, 0, 'text', _render("p['reimbursed_request']")],
                'totals': [1, 22, 'text', None]},
            'reimbursed_approve': {
                'header': [1, 22, 'text', _render("_('Date Approved')")],
                'lines': [1, 0, 'text', _render("p['reimbursed_approve']")],
                'totals': [1, 22, 'text', None]},
            'reimbursed_state' :{
                'header': [1, 22, 'text', _render("_('State RPC')")],
                'lines': [1, 0, 'text', _render("p['reimbursed_state']")],
                'totals': [1, 22, 'number', None]},
            'bta_name' :{
                'header': [1, 22, 'text', _render("_('No BTA')")],
                'lines': [1, 0, 'text', _render("p['bta_name']")],
                'totals': [1, 22, 'number', None]},
            'bta_date' :{
                'header': [1, 22, 'text', _render("_('Date BTA')")],
                'lines': [1, 0, 'text', _render("p['bta_date']")],
                'totals': [1, 22, 'number', None]},
            'bta_state' :{
                'header': [1, 22, 'text', _render("_('State BTA')")],
                'lines': [1, 0, 'text', _render("p['bta_state']")],
                'totals': [1, 22, 'number', None]},
            'dbt_name' :{
                'header': [1, 22, 'text', _render("_('No BTR (HO to Branch)')")],
                'lines': [1, 0, 'text', _render("p['dbt_name']")],
                'totals': [1, 22, 'number', None]},
            'dbt_date' :{
                'header': [1, 22, 'text', _render("_('Tgl BTR (HO to Branch)')")],
                'lines': [1, 0, 'text', _render("p['dbt_date']")],
                'totals': [1, 22, 'number', None]},
            'dbt_state' :{
                'header': [1, 22, 'text', _render("_('State BTR (HO to Branch)')")],
                'lines': [1, 0, 'text', _render("p['dbt_state']")],
                'totals': [1, 22, 'number', None]},
            'withdraw_name' :{
                'header': [1, 22, 'text', _render("_('No BTR (Withdrawal)')")],
                'lines': [1, 0, 'text', _render("p['withdraw_name']")],
                'totals': [1, 22, 'number', None]},
            'withdraw_date' :{
                'header': [1, 22, 'text', _render("_('Tgl BTR (Withdrawal)')")],
                'lines': [1, 0, 'text', _render("p['withdraw_date']")],
                'totals': [1, 22, 'number', None]},
            'withdraw_state' :{
                'header': [1, 22, 'text', _render("_('State BTR (Withdrawal)')")],
                'lines': [1, 0, 'text', _render("p['withdraw_state']")],
                'totals': [1, 22, 'number', None]},
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
            # title_short = r['title_short']
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
                [_('LAPORAN Request Tracking PCO Per Tanggal'), _(str(datetime.today().date())),
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
                [_('Tanggal Jatuh Tempo'), _('-' if data['start_date'] == False else str(data['start_date'])), _('s/d'), _('-' if data['end_date'] == False else str(data['end_date'])),
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
            for p in r['pco_id']:
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
            ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 6, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 7, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 8, xlwt.Formula("SUM(I"+str(row_data_begin)+":I"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 9, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 10, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 11, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 12, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 13, xlwt.Formula("SUM(N"+str(row_data_begin)+":N"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 15, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 16, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 17, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 18, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 19, xlwt.Formula("SUM(T"+str(row_data_begin)+":T"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 20, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 21, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 22, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 23, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 24, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 25, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 26, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 27, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 28, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 29, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 30, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 31, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 32, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 33, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 34, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 35, None, self.rt_cell_style_decimal)
            
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, _p.report_date + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_request_trackingpco_xls('report.Request Tracking PCO', 'account.voucher', parser = dym_report_request_trackingpco_print_xls)
