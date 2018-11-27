import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp import tools
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .report_bank_book import dym_bank_book_report_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)
import time

_ir_translation_name = 'dym.bank.book'

class dym_bank_book_print_xls(dym_bank_book_report_print):

    def __init__(self, cr, uid, name, context):
        super(dym_bank_book_print_xls, self).__init__(
            cr, uid, name, context=context)
        moveline_obj = self.pool.get('account.move.line')
        self.context = context
        wl_overview = moveline_obj._report_xls_bank_book_fields(
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


class bank_book_report_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(bank_book_report_xls, self).__init__(
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
                'header': [1, 5, 'text', _render("_('No')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['no']"),None,self.pd_cell_style_center],
                'totals': [1, 5, 'text', None]},                                             
            'branch_name': {
                'header': [1, 20, 'text', _render("_('Branch')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['branch_name'] or ''")],
                'totals': [1, 0, 'text', None]}, 
            'date': {
                'header': [1, 15, 'text', _render("_('Date')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['date']")],
                'totals': [1, 0, 'text', None]},            
            # 'value_date': {
            #     'header': [1, 15, 'text', _render("_('Value Date')"),None,self.rh_cell_style_center],
            #     'lines': [1, 0, 'text', _render("p['value_date']")],
            #     'totals': [1, 0, 'text', None]},
            'partner_code': {
                'header': [1, 20, 'text', _render("_('Kode Partner')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['partner_code'] or ''")],
                'totals': [1, 0, 'text', None]},
            'partner_name': {
                'header': [1, 20, 'text', _render("_('Partner')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['partner_name'] or ''")],
                'totals': [1, 0, 'text', None]},
            'cabang': {
                'header': [1, 20, 'text', _render("_('Cabang')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['cabang'] or ''")],
                'totals': [1, 0, 'text', None]},
            'finance_company': {
                'header': [1, 20, 'text', _render("_('Finance Company')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['finance_company'] or ''")],
                'totals': [1, 0, 'text', None]},  
            'account_code2': {
                'header': [1, 20, 'text', _render("_('Account Code')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['account_code2'] or ''")],
                'totals': [1, 0, 'text', None]},  
            'account_name2': {
                'header': [1, 20, 'text', _render("_('Account Name')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['account_name2'] or ''")],
                'totals': [1, 0, 'text', None]},     
            'name': {
                'header': [1, 20, 'text', _render("_('Description')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['name'] or ''")],
                'totals': [1, 0, 'text', None]},
            'jurnal_item': {
                'header': [1, 20, 'text', _render("_('Jurnal Item')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['jurnal_item'] or ''")],
                'totals': [1, 0, 'text', None]},
            'giro': {
                'header': [1, 20, 'text', _render("_('Cek/Giro')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['cheque_giro_number'] or ''")],
                'totals': [1, 0, 'text', None]},  
            'ref': {
                'header': [1, 20, 'text', _render("_('Ref')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['ref'] or ''")],
                'totals': [1, 0, 'text', None]},
            'kas_bon': {
                'header': [1, 20, 'text', _render("_('Kas Bon (PCO)')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['kas_bon'] or ''")],
                'totals': [1, 0, 'text', None]},
            'debit': {
                'header': [1, 20, 'text', _render("_('Debit')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['debit'] or ''"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},  
            'credit': {
                'header': [1, 20, 'text', _render("_('Credit')"),None,self.rh_cell_style_center],
                'lines': [1, 20, 'number', _render("p['credit'] or ''"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},
            'cur_balance': {
                'header': [1, 20, 'text', _render("_('Current Balance')"), None, self.rh_cell_style_center],
                'lines': [1, 20, 'number', _render("p['cur_balance'] or ''"), None, self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},
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
            'state': {
                'header': [1, 20, 'text', _render("_('State')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['state'] or ''")],
                'totals': [1, 0, 'text', None]},
            'btr_type': {
                'header': [1, 20, 'text', _render("_('Tipe Bank Transfer')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['btr_type'] or ''")],
                'totals': [1, 0, 'text', None]},
            'source_of_fund': {
                'header': [1, 20, 'text', _render("_('Source Of Fund')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['source_of_fund'] or ''")],
                'totals': [1, 0, 'text', None]},
        }                                   

        # XLS Template
        self.col_specs_template_details = {
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):

        wanted_list_overview = _p.wanted_list_overview
        _ = _p._
        
        username = self.pool.get('res.users').browse(self.cr,self.uid,self.uid).name
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
            
            #TITLE
            cell_style = xlwt.easyxf(_xs['xls_title'])         
            report_name = _(' '.join(['LAPORAN BANK BOOK','(PROYEKSI)' if data['projection'] else '']))
            c_specs_o = [
                ('title', 1, 20, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['title'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            
            #JOURNAL
            ws_o.write(row_pos_o, 0, data['journal_id'][1], cell_style)    
            row_pos_o += 1

            ## Tanggal Start Date & End Date ##
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join(
                [_('Tanggal'), _('-' if data['start_value_date'] == False else str(data['start_value_date'])), _('s/d'), _('-' if data['end_value_date'] == False else str(data['end_value_date'])),
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
            for p in r['move_lines']:
                c_specs_o = map(
                    lambda x: self.render(
                        x, self.col_specs_template_overview, 'lines'),
                    wanted_list_overview)
                for x in c_specs_o :
                    if x[0] == 'no' :
                        no += 1
                        x[4] = no

                row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)

                row_pos_d += 1  
            row_data_end = row_pos_o
                   
            ws_o.write(row_pos_o, 0, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 1, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 2, None,self.ph_cell_style)   
            ws_o.write(row_pos_o, 3, None,self.ph_cell_style)   
            ws_o.write(row_pos_o, 4, None,self.ph_cell_style)        
            ws_o.write(row_pos_o, 5, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 6, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 7, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 8, "Total",self.ph_cell_style)
            ws_o.write(row_pos_o, 9, None,self.ph_cell_style)   
            ws_o.write(row_pos_o, 10, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 11, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 12, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 13, None,self.ph_cell_style)   
            ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"),self.pd_cell_style_decimal_fill)
            ws_o.write(row_pos_o, 15, xlwt.Formula("SUM(P"+str(row_data_begin)+":P"+str(row_data_end)+")"),self.pd_cell_style_decimal_fill)
            ws_o.write(row_pos_o, 16, xlwt.Formula("SUM(Q"+str(row_data_begin)+":Q"+str(row_data_end)+")"),self.pd_cell_style_decimal_fill)
            ws_o.write(row_pos_o, 17, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 18, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 19, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 20, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 21, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 22, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 23, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 24, None,self.ph_cell_style)

            row_pos_o += 2
            ws_o.write(row_pos_o, 1, "SALDO AWAL", self.ph_cell_style)
            ws_o.write(row_pos_o, 2, r['saldo_awal'], self.pd_cell_style_decimal_fill)    
            row_pos_o += 1
            saldo_awal_pos = row_pos_o

            ws_o.write(row_pos_o, 1, "TOTAL DEBIT", self.ph_cell_style)
            ws_o.write(row_pos_o, 2, xlwt.Formula("O"+str(row_data_end+1)), self.pd_cell_style_decimal_fill)
            row_pos_o += 1
            total_debit_pos = row_pos_o

            ws_o.write(row_pos_o, 1, "TOTAL CREDIT", self.ph_cell_style)
            ws_o.write(row_pos_o, 2, xlwt.Formula("P"+str(row_data_end+1)), self.pd_cell_style_decimal_fill)
            row_pos_o += 1
            total_credit_pos = row_pos_o

            ws_o.write(row_pos_o, 1, "SALDO AKHIR", self.ph_cell_style)
            ws_o.write(row_pos_o, 2, xlwt.Formula("SUM(C"+str(saldo_awal_pos)+",C"+str(total_debit_pos)+",-C"+str(total_credit_pos)+")"), self.pd_cell_style_decimal_fill)    
            row_pos_o += 1

            ws_o.write(row_pos_o+1, 0, _p.report_date+" "+username)

bank_book_report_xls(
    'report.dym_report_bank_book_xls',
    'account.move.line',
    parser=dym_bank_book_print_xls)