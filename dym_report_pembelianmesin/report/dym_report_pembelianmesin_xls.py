import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_pembelianmesin import dym_report_pembelianmesin_print
from openerp.tools.translate import translate
import string

class dym_report_pembelianmesin_print_xls(dym_report_pembelianmesin_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_pembelianmesin_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('account.invoice')._report_xls_pembelianmesin_fields(cr, uid, context),
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(self.cr, 'report.pembelianmesin', 'report', lang, src) or src

class report_pembelianmesin_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_pembelianmesin_xls, self).__init__(name, table, rml, parser, header, store)

        # Cell Styles
        _xs = self.xls_styles

        # Report Column Headers format
        rh_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rh_cell_style = xlwt.easyxf(rh_cell_format)
        self.rh_cell_style_center = xlwt.easyxf(rh_cell_format + _xs['center'])
        self.rh_cell_style_right = xlwt.easyxf(rh_cell_format + _xs['right'])

        # Partner Column Headers format
        fill_blue = 'pattern: pattern solid, fore_color 27;'
        ph_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.ph_cell_style = xlwt.easyxf(ph_cell_format)
        self.ph_cell_style_decimal = xlwt.easyxf(ph_cell_format + _xs['right'], num_format_str=report_xls.decimal_format)
        
        # Partner Column Data format
        pd_cell_format = _xs['borders_all']
        self.pd_cell_style = xlwt.easyxf(pd_cell_format)
        self.pd_cell_style_center = xlwt.easyxf(pd_cell_format + _xs['center'])
        self.pd_cell_style_date = xlwt.easyxf(pd_cell_format + _xs['left'], num_format_str=report_xls.date_format)
        self.pd_cell_style_decimal = xlwt.easyxf(pd_cell_format + _xs['right'], num_format_str=report_xls.decimal_format)

        # totals
        rt_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rt_cell_style = xlwt.easyxf(rt_cell_format)
        self.rt_cell_style_right = xlwt.easyxf(rt_cell_format + _xs['right'])
        self.rt_cell_style_decimal = xlwt.easyxf(rt_cell_format + _xs['right'], num_format_str=report_xls.decimal_format)

        # XLS Template
        self.col_specs_template_overview = {
            'no': {
                'header': [1, 5, 'text', _render("_('NO')")],
                'lines': [1, 0, 'number', _render("p['no']")],
                'totals': [1, 5, 'number', None]},
            'branch_status': {
                'header': [1, 10, 'text', _render("_('Branch Status')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['branch_status'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},   
            'branch_code': {
                'header': [1, 22, 'text', _render("_('Kode Cabang')")],
                'lines': [1, 0, 'text', _render("p['branch_code']")],
                'totals': [1, 22, 'text', _render("_('Total')")]},
            'branch_name': {
                'header': [1, 22, 'text', _render("_('Nama Cabang')")],
                'lines': [1, 0, 'text', _render("p['branch_name']")],
                'totals': [1, 22, 'number', None]},
            'date_invoice': {
                'header': [1, 22, 'text', _render("_('Tgl Reg Invoice')")],
                'lines': [1, 0, 'text', _render("p['date_invoice']")],
                'totals': [1, 22, 'number', None]},
            'inv_number': {
                'header': [1, 22, 'text', _render("_('No Reg Invoice')")],
                'lines': [1, 0, 'text', _render("p['inv_number']")],
                'totals': [1, 22, 'number', None]},
            'supplier_code': {
                'header': [1, 22, 'text', _render("_('Kode Supplier')")],
                'lines': [1, 0, 'text', _render("p['supplier_code']")],
                'totals': [1, 22, 'number', None]},    
            'supplier_name': {
                'header': [1, 22, 'text', _render("_('Supplier')")],
                'lines': [1, 0, 'text', _render("p['supplier_name']")],
                'totals': [1, 22, 'number', None]},
            'division': {
                'header': [1, 22, 'text', _render("_('Division')")],
                'lines': [1, 0, 'text', _render("p['division']")],
                'totals': [1, 22, 'number', None]},
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
            'consolidate_status': {
                'header': [1, 22, 'text', _render("_('Stock Status')")],
                'lines': [1, 0, 'text', _render("p['consolidate_status']")],
                'totals': [1, 22, 'number', None]},
            'document_date': {
                'header': [1, 22, 'text', _render("_('Tgl Invoice')")],
                'lines': [1, 0, 'text', _render("p['document_date']")],
                'totals': [1, 22, 'number', None]},
            'supplier_invoice_number': {
                'header': [1, 22, 'text', _render("_('No Invoice')")],
                'lines': [1, 0, 'text', _render("p['supplier_invoice_number']")],
                'totals': [1, 22, 'number', None]},
            'origin': {
                'header': [1, 22, 'text', _render("_('PO Number')")],
                'lines': [1, 0, 'text', _render("p['origin']")],
                'totals': [1, 22, 'number', None]},
            'state': {
                'header': [1, 22, 'text', _render("_('Status')")],
                'lines': [1, 0, 'text', _render("p['state']")],
                'totals': [1, 22, 'number', None]},
            'type': {
                'header': [1, 22, 'text', _render("_('Tipe Produk')")],
                'lines': [1, 0, 'text', _render("p['type']")],
                'totals': [1, 22, 'number', None]},
            'warna': {
                'header': [1, 22, 'text', _render("_('Color')")],
                'lines': [1, 0, 'text', _render("p['warna']")],
                'totals': [1, 22, 'number', None]},
            'prod_categ_name': {
                'header': [1, 22, 'text', _render("_('Kategori')")],
                'lines': [1, 0, 'text', _render("p['prod_categ_name']")],
                'totals': [1, 22, 'number', None]},
            'qty': {
                'header': [1, 22, 'text', _render("_('Qty')")],
                'lines': [1, 0, 'number', _render("p['qty']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'consolidated_qty': {
                'header': [1, 22, 'text', _render("_('Consol Qty')")],
                'lines': [1, 0, 'number', _render("p['consolidated_qty']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'unconsolidated_qty': {
                'header': [1, 22, 'text', _render("_('Unconsol Qty')")],
                'lines': [1, 0, 'number', _render("p['unconsolidated_qty']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'price_unit': {
                'header': [1, 22, 'text', _render("_('Harga Per Unit')")],
                'lines': [1, 0, 'number', _render("p['price_unit']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            # 'discount': {
            #     'header': [1, 22, 'text', _render("_('Discount 1 (%)')")],
            #     'lines': [1, 0, 'number', _render("p['discount']"), None, self.pd_cell_style_decimal],
            #     'totals': [1, 22, 'number', None]},
            'total_sales': {
                'header': [1, 22, 'text', _render("_('Total Pembelian')")],
                'lines': [1, 0, 'number', _render("p['total_sales']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'disc_amount': {
                'header': [1, 22, 'text', _render("_('Discount')")],
                'lines': [1, 0, 'number', _render("p['disc_amount']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            # 'sales_per_unit': {
            #     'header': [1, 30, 'text', _render("_('Gross Purchase (Per Unit)')")],
            #     'lines': [1, 0, 'number', _render("p['sales_per_unit']"), None, self.pd_cell_style_decimal],
            #     'totals': [1, 30, 'number', None]},
            'discount_cash_avg': {
                'header': [1, 22, 'text', _render("_('Disc Cash')")],
                'lines': [1, 0, 'number', _render("p['discount_cash_avg']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'discount_program_avg': {
                'header': [1, 22, 'text', _render("_('Disc Program')")],
                'lines': [1, 0, 'number', _render("p['discount_program_avg']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'discount_lain_avg': {
                'header': [1, 22, 'text', _render("_('Disc Lain-lain')")],
                'lines': [1, 0, 'number', _render("p['discount_lain_avg']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'total_dpp': {
                'header': [1, 22, 'text', _render("_('DPP')")],
                'lines': [1, 0, 'number', _render("p['total_dpp']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'total_ppn': {
                'header': [1, 22, 'text', _render("_('PPN')")],
                'lines': [1, 0, 'number', _render("p['total_ppn']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'total_hutang': {
                'header': [1, 22, 'text', _render("_('Total Hutang')")],
                'lines': [1, 0, 'number', _render("p['total_hutang']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'tgl_retur': {
                'header': [1, 20, 'text', _render("_('Tgl Retur')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['tgl_retur'] or ''")],
                'totals': [1, 0, 'text', None]}, 
            'no_retur': {
                'header': [1, 20, 'text', _render("_('No Retur')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['no_retur'] or ''")],
                'totals': [1, 0, 'text', None]},
            'qty_retur': {
                'header': [1, 22, 'text', _render("_('Qty Retur')")],
                'lines': [1, 0, 'number', _render("p['qty_retur']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'retur_total': {
                'header': [1, 22, 'text', _render("_('Retur')")],
                'lines': [1, 0, 'number', _render("p['retur_total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'taxes': {
                'header': [1, 20, 'text', _render("_('Taxes')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['taxes'] or ''")],
                'totals': [1, 0, 'text', None]},
            'account_code': {
                'header': [1, 20, 'text', _render("_('COA')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['account_code'] or ''")],
                'totals': [1, 0, 'text', None]},
            'loan_name': {
                'header': [1, 20, 'text', _render("_('Ref re-class')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['loan_name'] or ''")],
                'totals': [1, 0, 'text', None]},
            'loan_date': {
                'header': [1, 20, 'text', _render("_('Tgl re-class')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['loan_date'] or ''")],
                'totals': [1, 0, 'text', None]},
            'prod_desc': {
                'header': [1, 20, 'text', _render("_('Nama Produk')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['prod_desc']")],
                'totals': [1, 0, 'text', None]},
            'purchase_date': {
                'header': [1, 20, 'text', _render("_('TGL PO')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['purchase_date'] or ''")],
                'totals': [1, 0, 'text', None]},
            'purchase_name': {
                'header': [1, 20, 'text', _render("_('PO Number')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['purchase_name'] or ''")],
                'totals': [1, 0, 'text', None]},
            'tgl_grn': {
                'header': [1, 20, 'text', _render("_('TGL GRN')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['tgl_grn'] or ''")],
                'totals': [1, 0, 'text', None]},
            'no_grn': {
                'header': [1, 20, 'text', _render("_('No GRN')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['no_grn'] or ''")],
                'totals': [1, 0, 'text', None]},  
            'engine_number': {
                'header': [1, 20, 'text', _render("_('NO MESIN')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['engine_number'] or ''")],
                'totals': [1, 0, 'text', None]},
            'tgl_cin': {
                'header': [1, 20, 'text', _render("_('Tgl CIN')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['tgl_cin'] or ''")],
                'totals': [1, 0, 'text', None]},
            'no_cin': {
                'header': [1, 20, 'text', _render("_('No CIN')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['no_cin'] or ''")],
                'totals': [1, 0, 'text', None]},
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        self.col_specs_template_overview.update({})
        _ = _p._

        for r in _p.reports:
            ws_o = wb.add_sheet('Laporan Pembelian by No Mesin')
            
            for ws in [ws_o]:
                ws.panes_frozen = True
                ws.remove_splits = True
                ws.portrait = 0  # Landscape
                ws.fit_width_to_pages = 1
            row_pos_o = 0

            # set print header/footer
            for ws in [ws_o]:
                ws.header_str = self.xls_headers['standard']
                ws.footer_str = self.xls_footers['standard']

            
            # Title
            cell_style = xlwt.easyxf(_xs['xls_title'])
            c_specs_o = [('report_name', 1, 0, 'text', 'Laporan Pembelian by No Mesin')]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)        

            # Company Name
            cell_style = xlwt.easyxf(_xs['left'])
            c_specs_o = [('report_name', 1, 0, 'text', _p.company.name)]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
            
            # Start Date & End Date
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join([_('PERIODE : '), _('-' if data['start_date'] == False else str(data['end_date'])), _('s/d'), _('-' if data['end_date'] == False else str(data['end_date']))])
            c_specs_o = [('report_name', 1, 0, 'text', report_name)]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
            row_pos_o += 1
            
            # Report Column Headers
            c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'header', render_space={'_': _p._}), wanted_list_overview)
            row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.rh_cell_style, set_column_size=True)
            ws_o.set_horz_split_pos(row_pos_o)
            
            row_data_begin = row_pos_o
            
            # Columns and Rows
            no = 0
            for p in r['ail_id']:
                c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'lines'), wanted_list_overview)
                for x in c_specs_o :
                    if x[0] == 'no' :
                        no += 1
                        x[4] = no
                row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
            
            row_data_end = row_pos_o
            
            # Totals
            ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)   
            ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
            ws_o.set_vert_split_pos(3)
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
            ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":P"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 15, xlwt.Formula("SUM(P"+str(row_data_begin)+":P"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 16, xlwt.Formula("SUM(Q"+str(row_data_begin)+":Q"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 17, xlwt.Formula("SUM(R"+str(row_data_begin)+":R"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 18, xlwt.Formula("SUM(S"+str(row_data_begin)+":S"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 19, xlwt.Formula("SUM(T"+str(row_data_begin)+":T"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 20, xlwt.Formula("SUM(U"+str(row_data_begin)+":U"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 21, xlwt.Formula("SUM(V"+str(row_data_begin)+":V"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 22, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 23, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 24, xlwt.Formula("SUM(Y"+str(row_data_begin)+":Y"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 25, xlwt.Formula("SUM(Z"+str(row_data_begin)+":Z"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 26, xlwt.Formula("SUM(AA"+str(row_data_begin)+":AA"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 27, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 28, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 29, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 30, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 31, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 32, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 33, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 34, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 35, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 36, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 37, None, self.rt_cell_style_decimal)

            # ws_o.write(row_pos_o, 26, xlwt.Formula("SUM(AA"+str(row_data_begin)+":AA"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            # ws_o.write(row_pos_o, 27, xlwt.Formula("SUM(AB"+str(row_data_begin)+":AB"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            #ws_o.write(row_pos_o + 2, 0, time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))
            ws_o.write(row_pos_o + 2, 0, 'Tgl cetak      : ' + time.strftime('%d-%m-%Y %H:%M:%S'),self.pd_cell_style)
            ws_o.write(row_pos_o + 3, 0, 'Dicetak oleh : ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name),self.pd_cell_style)
report_pembelianmesin_xls('report.Laporan Pembelian by No Mesin', 'account.invoice', parser = dym_report_pembelianmesin_print_xls)
