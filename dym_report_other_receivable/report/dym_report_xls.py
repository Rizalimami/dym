import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report import dym_report_other_receivable_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)
import string

_ir_translation_name = 'report.other.receivable'

class dym_report_other_receivable_print_xls(dym_report_other_receivable_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_other_receivable_print_xls, self).__init__(
            cr, uid, name, context=context)
        move_line_obj = self.pool.get('account.voucher')
        self.context = context
        wl_overview = move_line_obj._report_xls_other_receivable_fields(
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

class report_other_receivable_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(report_other_receivable_xls, self).__init__(
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
            'branch_status': {
                'header': [1, 10, 'text', _render("_('Branch Status')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['branch_status'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},   
            'branch_id': {
                'header': [1, 22, 'text', _render("_('Cabang')")],
                'lines': [1, 0, 'text', _render("p['branch_id']")],
                'totals': [1, 22, 'text', _render("_('Total')")]},
            'number': {
                'header': [1, 22, 'text', _render("_('Number')")],
                'lines': [1, 0, 'text', _render("p['number']")],
                'totals': [1, 22, 'text', None]},
           'division': {
               'header': [1, 22, 'text', _render("_('Divisi')")],
               'lines': [1, 0, 'text', _render("p['division']")],
               'totals': [1, 22, 'text', None]},
           'partner_code': {
              'header': [1, 22, 'text', _render("_('Customer')")],
               'lines': [1, 0, 'text', _render("p['partner_code']")],
               'totals': [1, 22, 'text', None]},
           'partner_name': {
               'header': [1, 22, 'text', _render("_('Nama Customer')")],
               'lines': [1, 0, 'text', _render("p['partner_name']")],
               'totals': [1, 22, 'text', None]},
           'journal_name': {
               'header': [1, 22, 'text', _render("_('Journal')")],
               'lines': [1, 0, 'text', _render("p['journal_name']")],
               'totals': [1, 22, 'text', None]},
           'account_code': {
               'header': [1, 22, 'text', _render("_('No COA')")],
               'lines': [1, 0, 'text', _render("p['account_code']")],
               'totals': [1, 22, 'text', None]},
           'account_name': {
               'header': [1, 22, 'text', _render("_('Nama COA')")],
               'lines': [1, 0, 'text', _render("p['account_name']")],
               'totals': [1, 22, 'text', None]},
           'analytic_combination': {
               'header': [1, 20, 'text', _render("_('Analytic Combination')"),None,self.rh_cell_style_center],
               'lines': [1, 0, 'text', _render("p['analytic_combination'] or ''")],
               'totals': [1, 0, 'text', None]},
           'analytic_1': {
               'header': [1, 20, 'text', _render("_('Analytic Company')"),None,self.rh_cell_style_center],
               'lines': [1, 0, 'text', _render("p['analytic_1'] or ''")],
               'totals': [1, 0, 'text', None]},
           'analytic_2': {
               'header': [1, 20, 'text', _render("_('Analytic Bisnis Unit')"),None,self.rh_cell_style_center],
               'lines': [1, 0, 'text', _render("p['analytic_2'] or ''")],
               'totals': [1, 0, 'text', None]},
           'analytic_3': {
               'header': [1, 20, 'text', _render("_('Analytic Branch')"),None,self.rh_cell_style_center],
               'lines': [1, 0, 'text', _render("p['analytic_3'] or ''")],
               'totals': [1, 0, 'text', None]},
           'analytic_4': {
               'header': [1, 20, 'text', _render("_('Analytic Cost Center')"),None,self.rh_cell_style_center],
               'lines': [1, 0, 'text', _render("p['analytic_4'] or ''")],
               'totals': [1, 0, 'text', None]},
           'memo': {
               'header': [1, 22, 'text', _render("_('Memo')")],
               'lines': [1, 0, 'text', _render("p['memo']")],
               'totals': [1, 0, 'text', None]},
           'ref': {
               'header': [1, 22, 'text', _render("_('Ref')")],
               'lines': [1, 0, 'text', _render("p['ref']")],
               'totals': [1, 22, 'text', None]},
            'date': {
                'header': [1, 22, 'text', _render("_('Tanggal')")],
                'lines': [1, 0, 'text', _render("p['date']")],
                'totals': [1, 22, 'text', None]},
            'date_due': {
                'header': [1, 22, 'text', _render("_('Tgl Jatuh Tempo')")],
                'lines': [1, 0, 'text', _render("p['date_due']")],
                'totals': [1, 22, 'text', None]},
           'state': {
               'header': [1, 22, 'text', _render("_('Status')")],
               'lines': [1, 0, 'text', _render("p['state']")],
               'totals': [1, 22, 'text', None]},
            'total': {
                'header': [1, 22, 'text', _render("_('Total')")],
                'lines': [1, 0, 'number', _render("p['total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['total']"), None, self.rt_cell_style_decimal]},
            'dpp': {
                'header': [1, 22, 'text', _render("_('DPP')")],
                'lines': [1, 0, 'number', _render("p['dpp']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['dpp']"), None, self.rt_cell_style_decimal]},
            'ppn':  {
                'header': [1, 22, 'text', _render("_('PPn')")],
                'lines': [1, 0, 'number', _render("p['ppn']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['ppn']"), None, self.rt_cell_style_decimal]},
            'pph':  {
                'header': [1, 22, 'text', _render("_('PPh')")],
                'lines': [1, 0, 'number', _render("p['pph']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['pph']"), None, self.rt_cell_style_decimal]},
            'piutang':  {
                'header': [1, 22, 'text', _render("_('Piutang')")],
                'lines': [1, 0, 'number', _render("p['piutang']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['piutang']"), None, self.rt_cell_style_decimal]},
            'residual': {
                'header': [1, 22, 'text', _render("_('Residual')")],
                'lines': [1, 0, 'number', _render("p['residual']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['residual']"), None, self.rt_cell_style_decimal]},
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
                [_('LAPORAN Other Receivable Per Tanggal'), _(str(datetime.today().date())),
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
            ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)
            ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 6, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 7, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 8, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 9, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 10, xlwt.Formula("SUM(K"+str(row_data_begin)+":K"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 11, xlwt.Formula("SUM(L"+str(row_data_begin)+":L"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 12, xlwt.Formula("SUM(M"+str(row_data_begin)+":M"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 13, xlwt.Formula("SUM(N"+str(row_data_begin)+":N"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 15, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 16, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 17, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 18, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 19, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 20, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 21, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 22, None, self.rt_cell_style_decimal)
            
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, _p.report_date + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_other_receivable_xls('report.Laporan Other Receivable', 'account.voucher', parser = dym_report_other_receivable_print_xls)
