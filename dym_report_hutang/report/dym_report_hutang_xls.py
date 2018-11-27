import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_hutang import dym_report_hutang_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)
import string

_ir_translation_name = 'report.hutang'

class dym_report_hutang_print_xls(dym_report_hutang_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_hutang_print_xls, self).__init__(
            cr, uid, name, context=context)
        move_line_obj = self.pool.get('account.move.line')
        self.context = context
        wl_overview = move_line_obj._report_xls_hutang_fields(
            cr, uid, context)
        tmpl_upd_overview = move_line_obj._report_xls_arap_overview_template(
            cr, uid, context)
        wl_overview_detail_pembayaran = move_line_obj._report_xls_hutang_fields_detail_pembayaran(
            cr, uid, context)
        wl_details = move_line_obj._report_xls_arap_details_fields(
            cr, uid, context)
        tmpl_upd_details = move_line_obj._report_xls_arap_overview_template(
            cr, uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': wl_overview,
            'wl_overview_detail_pembayaran': wl_overview_detail_pembayaran,
            'template_update_overview': tmpl_upd_overview,
            'wanted_list_details': wl_details,
            'template_update_details': tmpl_upd_details,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src

class report_hutang_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(report_hutang_xls, self).__init__(
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
            'branch_code': {
                'header': [1, 22, 'text', _render("_('Kode Cabang')")],
                'lines': [1, 0, 'text', _render("p['branch_code'] or ''")],
                'totals': [1, 22, 'text', None]},
            'branch_name': { 
                'header': [1, 22, 'text', _render("_('Nama Cabang')")],
                'lines': [1, 0, 'text', _render("p['branch_name']")],
                'totals': [1, 22, 'text', None]},
            'division': {
                'header': [1, 22, 'text', _render("_('Divisi')")],
                'lines': [1, 0, 'text', _render("p['division']")],
                'totals': [1, 22, 'text', None]},
            'partner_code': {
                'header': [1, 22, 'text', _render("_('Kode Supplier')")],
                'lines': [1, 0, 'text', _render("p['partner_code']")],
                'totals': [1, 22, 'text', None]},
            'partner_name': {
                'header': [1, 22, 'text', _render("_('Nama Supplier')")],
                'lines': [1, 0, 'text', _render("p['partner_name']")],
                'totals': [1, 22, 'text', None]},
            'account_code': {
                'header': [1, 22, 'text', _render("_('COA')")],
                'lines': [1, 0, 'text', _render("p['account_code']")],
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
            'branch_x': {
                'header': [1, 22, 'text', _render("_('Cabang')")],
                'lines': [1, 0, 'text', _render("p['branch_x']")],
                'totals': [1, 22, 'text', None]},
            'invoice_name': {
                'header': [1, 22, 'text', _render("_('No Reg Invoice')")],
                'lines': [1, 0, 'text', _render("p['invoice_name']")],
                'totals': [1, 22, 'text', None]},
            'name': {
                'header': [1, 22, 'text', _render("_('Name')")],
                'lines': [1, 0, 'text', _render("p['name']")],
                'totals': [1, 22, 'text', None]},
            'supplier_invoice_number': {
                'header': [1, 22, 'text', _render("_('No Invoice')")],
                'lines': [1, 0, 'text', _render("p['supplier_invoice_number']")],
                'totals': [1, 22, 'text', None]},
            'date_aml': {
                'header': [1, 22, 'text', _render("_('Tgl Reg Invoice')")],
                'lines': [1, 0, 'text', _render("p['date_aml']")],
                'totals': [1, 22, 'text', None]},
            'due_date': {
                'header': [1, 22, 'text', _render("_('Tgl Jatuh Tempo')")],
                'lines': [1, 0, 'text', _render("p['due_date']")],
                'totals': [1, 22, 'text', None]},
            'payment_term': {
                'header': [1, 20, 'text', _render("_('Payment Term')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['payment_term'] or ''")],
                'totals': [1, 0, 'text', None]},  
            'overdue': {
                'header': [1, 22, 'text', _render("_('Overdue')")],
                'lines': [1, 0, 'text', _render("p['overdue']")],
                'totals': [1, 22, 'text', None]},
            'status': {
                'header': [1, 22, 'text', _render("_('Status')")],
                'lines': [1, 0, 'text', _render("p['status']")],
                'totals': [1, 22, 'text', None]},
            'saldo_awal': {
                'header': [1, 22, 'text', _render("_('Saldo Awal')")],
                'lines': [1, 0, 'number', _render("p['saldo_awal']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['saldo_awal']"), None, self.rt_cell_style_decimal]},
            'tot_invoice': {
                'header': [1, 22, 'text', _render("_('Penambahan')")],
                'lines': [1, 0, 'number', _render("p['tot_invoice']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['tot_invoice']"), None, self.rt_cell_style_decimal]},
            'amount_residual': {
                'header': [1, 22, 'text', _render("_('Sisa Hutang')")],
                'lines': [1, 0, 'number', _render("p['amount_residual']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['amount_residual']"), None, self.rt_cell_style_decimal]},
            'belum_jatuh_tempo': {
                'header': [1, 22, 'text', _render("_('Current')")],
                'lines': [1, 0, 'number', _render("p['belum_jatuh_tempo']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['belum_jatuh_tempo']"), None, self.rt_cell_style_decimal]},
            'overdue_1_30': {
                'header': [1, 22, 'text', _render("_('Overdue 1 - 30')")],
                'lines': [1, 0, 'number', _render("p['overdue_1_30']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['overdue_1_30']"), None, self.rt_cell_style_decimal]},
            'overdue_31_60': {
                'header': [1, 22, 'text', _render("_('Overdue 31 - 60')")],
                'lines': [1, 0, 'number', _render("p['overdue_31_60']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['overdue_31_60']"), None, self.rt_cell_style_decimal]},
            'overdue_61_90': {
                'header': [1, 22, 'text', _render("_('Overdue 61 - 90')")],
                'lines': [1, 0, 'number', _render("p['overdue_61_90']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['overdue_61_90']"), None, self.rt_cell_style_decimal]},
            'overdue_91_n': {
                'header': [1, 22, 'text', _render("_('Overdue > 90')")],
                'lines': [1, 0, 'number', _render("p['overdue_91_n']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['overdue_91_n']"), None, self.rt_cell_style_decimal]},
            'reference': {
                'header': [1, 22, 'text', _render("_('Ref')")],
                'lines': [1, 0, 'text', _render("p['reference']")],
                'totals': [1, 22, 'text', None]},
            'journal_name': {
                'header': [1, 22, 'text', _render("_('Scr')")],
                'lines': [1, 0, 'text', _render("p['journal_name']")],
                'totals': [1, 22, 'text', None]},
            'supplier_invoice_date': {
                'header': [1, 22, 'text', _render("_('Tgl Invoice')")],
                'lines': [1, 0, 'text', _render("p['supplier_invoice_date']")],
                'totals': [1, 22, 'text', None]},
            'acc_number': {
                'header': [1, 22, 'text', _render("_('No Rekening Supplier')")],
                'lines': [1, 0, 'text', _render("p['acc_number']")],
                'totals': [1, 22, 'text', None]},
            'bank': {
                'header': [1, 22, 'text', _render("_('Bank')")],
                'lines': [1, 0, 'text', _render("p['bank']")],
                'totals': [1, 22, 'text', None]},
            'an_rek': {
                'header': [1, 22, 'text', _render("_('An Supplier Di Rekening')")],
                'lines': [1, 0, 'text', _render("p['an_rek']")],
                'totals': [1, 22, 'text', None]},
            'tgl_retur': {
                'header': [1, 22, 'text', _render("_('Tgl Retur')")],
                'lines': [1, 0, 'text', _render("p['tgl_retur']")],
                'totals': [1, 22, 'text', None]},
            'no_retur': {
                'header': [1, 22, 'text', _render("_('No Retur')")],
                'lines': [1, 0, 'text', _render("p['no_retur']")],
                'totals': [1, 22, 'text', None]},
            'total_retur': {
                'header': [1, 22, 'text', _render("_('Retur')")],
                'lines': [1, 0, 'number', _render("p['total_retur']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['total_retur']"), None, self.rt_cell_style_decimal]},
            'pay_no': {
                'header': [1, 22, 'text', _render("_('No Supplier Payment')")],
                'lines': [1, 0, 'text', _render("p['pay_no']")],
                'totals': [1, 22, 'text', None]},
            'pay_date': {
                'header': [1, 22, 'text', _render("_('Tgl Supplier Payment')")],
                'lines': [1, 0, 'text', _render("p['pay_date']")],
                'totals': [1, 22, 'text', None]},
            'pay_retur': {
                'header': [1, 22, 'text', _render("_('Retur')")],
                'lines': [1, 0, 'number', _render("p['pay_retur']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['pay_retur']"), None, self.rt_cell_style_decimal]},
            'pay_pindahan': {
                'header': [1, 22, 'text', _render("_('Re-Class')")],
                'lines': [1, 0, 'number', _render("p['pay_pindahan']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['pay_pindahan']"), None, self.rt_cell_style_decimal]},
            'pay_amount': {
                'header': [1, 22, 'text', _render("_('Bayar')")],
                'lines': [1, 0, 'number', _render("p['pay_amount']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['pay_amount']"), None, self.rt_cell_style_decimal]},


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
            if r['detail_pembayaran'] == False:
                wanted_list_overview = _p.wanted_list_overview
            else:
                wanted_list_overview = _p.wl_overview_detail_pembayaran
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
                [_('LAPORAN MUTASI HUTANG Per Tanggal'), _(str(datetime.today().date())),
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
                [_('Cabang :'),'-', r['title'],
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
                [_('Periode :'), _('-' if data['trx_start_date'] == False else str(data['trx_start_date'])), _('s/d'), _('-' if data['trx_end_date'] == False else str(data['trx_end_date'])),
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

            for p in r['ids_aml']:
                c_specs_o = map(
                    lambda x: self.render(
                        x, self.col_specs_template_overview, 'lines'),
                    wanted_list_overview)

                for x in c_specs_o :
                    #print x
                    if x[0] == 'no' :
                        no += 1
                        x[4] = no
                row_data = self.xls_row_template(
                    c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
                
                row_pos_d += 1  
            row_data_end = row_pos_o
#             # Totals
#             tot_invoice = 0
#             amount_residual = 0
#             belum_jatuh_tempo = 0
#             overdue_1_30 = 0
#             overdue_31_60 = 0
#             overdue_61_90 = 0
#             for p in r['ids_aml']:
#                 tampung = map(
#                     lambda x: self.render(
#                         x, self.col_specs_template_overview, 'totals'),
#                     wanted_list_overview)
#                 for x in tampung :
#                     if x[0] == 'tot_invoice' and x[4] != False :
#                         tot_invoice += float(x[4])
#                     if x[0] == 'amount_residual' and x[4] != False :
#                         amount_residual += float(x[4])
#                     if x[0] == 'belum_jatuh_tempo' and x[4] != False :
#                         belum_jatuh_tempo += float(x[4])
#                     if x[0] == 'overdue_1_30' and x[4] != False :
#                         overdue_1_30 += float(x[4])
#                     if x[0] == 'overdue_31_60' and x[4] != False :
#                         overdue_31_60 += float(x[4])
#                     if x[0] == 'overdue_61_90' and x[4] != False :
#                         overdue_61_90 += float(x[4])
#                     
#             c_specs_o = map(
#                 lambda x: self.render(
#                     x, self.col_specs_template_overview, 'totals'),
#                 wanted_list_overview)
#             for x in c_specs_o :
#                 if x[0] == 'tot_invoice' :
#                     x[4] = tot_invoice
#                 if x[0] == 'amount_residual' :
#                     x[4] = amount_residual
#                 if x[0] == 'belum_jatuh_tempo' :
#                     x[4] = belum_jatuh_tempo
#                 if x[0] == 'overdue_1_30' :
#                     x[4] = overdue_1_30
#                 if x[0] == 'overdue_31_60' :
#                     x[4] = overdue_31_60
#                 if x[0] == 'overdue_61_90' :
#                     x[4] = overdue_61_90
#             row_data = self.xls_row_template(
#                 c_specs_o, [x[0] for x in c_specs_o])
#             row_pos_o = self.xls_write_row(
#                 ws_o, row_pos_o, row_data, row_style=self.rh_cell_style,
#                 set_column_size=True)
#             row_pos_o += 1
#             
#             # Footer
#             cell_style = xlwt.easyxf(_xs['left'])
#             report_name = ' '.join(
#                 [_(_p.report_date), _(str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name)),
#                  _p.report_info])
#             c_specs_o = [
#                 ('report_name', 1, 0, 'text', report_name),
#             ]
#             row_data = self.xls_row_template(c_specs_o, ['report_name'])
#             row_pos_o = self.xls_write_row(
#                 ws_o, row_pos_o, row_data, row_style=cell_style)
#             row_pos_o += 2

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
            ws_o.write(row_pos_o, 10, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 11, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 12, xlwt.Formula("SUM(M"+str(row_data_begin)+":M"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 13, xlwt.Formula("SUM(N"+str(row_data_begin)+":N"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            if r['detail_pembayaran'] == False:
                ws_o.write(row_pos_o, 14, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 15, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 16, xlwt.Formula("SUM(Q"+str(row_data_begin)+":Q"+str(row_data_end)+")"), self.rt_cell_style_decimal)
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
            else:
                ws_o.write(row_pos_o, 14, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 15, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 16, xlwt.Formula("SUM(Q"+str(row_data_begin)+":Q"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 17, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 18, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 19, xlwt.Formula("SUM(T"+str(row_data_begin)+":T"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 20, xlwt.Formula("SUM(U"+str(row_data_begin)+":U"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 21, xlwt.Formula("SUM(V"+str(row_data_begin)+":V"+str(row_data_end)+")"), self.rt_cell_style_decimal)
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
            
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, _p.report_date + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_hutang_xls('report.Laporan Hutang', 'account.move.line', parser = dym_report_hutang_print_xls)