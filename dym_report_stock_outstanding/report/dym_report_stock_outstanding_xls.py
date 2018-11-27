import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_stock_outstanding import dym_report_stock_outstanding_print
from openerp.tools.translate import translate
import string

_ir_translation_name = 'report.stock.outstanding'

class dym_report_stock_outstanding_print_xls(dym_report_stock_outstanding_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_stock_outstanding_print_xls, self).__init__(cr, uid, name, context=context)
        move_obj = self.pool.get('stock.move')
        self.context = context
        wl_overview = move_obj._report_xls_stock_outstanding_fields(cr, uid, context)
        #aris
        wl_overview_sparepart = move_obj._report_xls_stock_outstanding_fields_sparepart(cr,uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': wl_overview,
            #aris
            'wanted_list_overview_sparepart' : wl_overview_sparepart,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src

class report_stock_outstanding_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_stock_outstanding_xls, self).__init__(name, table, rml, parser, header, store)

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
            'branch_code': {
                'header': [1, 22, 'text', _render("_('Kode Cabang')")],
                'lines': [1, 0, 'text', _render("p['branch_code']")],
                'totals': [1, 22, 'text', _render("_('Total')")]},
            'branch_name': {
                'header': [1, 22, 'text', _render("_('Nama Cabang')")],
                'lines': [1, 0, 'text', _render("p['branch_name']")],
                'totals': [1, 22, 'text', None]},
            'division': {
                'header': [1, 22, 'text', _render("_('Division')")],
                'lines': [1, 0, 'text', _render("p['division']")],
                'totals': [1, 22, 'text', None]},
            'picking_type_name': {
                'header': [1, 22, 'text', _render("_('Movement Type')")],
                'lines': [1, 0, 'text', _render("p['picking_type_name']")],
                'totals': [1, 22, 'text', None]},
            'packing_name': {
                'header': [1, 22, 'text', _render("_('No. Mutation Request')")],
                'lines': [1, 0, 'text', _render("p['packing_name']")],
                'totals': [1, 22, 'text', None]},
            'packing_state': {
                'header': [1, 22, 'text', _render("_('Movement State')")],
                'lines': [1, 0, 'text', _render("p['packing_state']")],
                'totals': [1, 22, 'text', None]},
            'packing_date': {
                'header': [1, 22, 'text', _render("_('Tgl. Mutation Request')")],
                'lines': [1, 0, 'text', _render("p['packing_date']")],
                'totals': [1, 22, 'text', None]},
            'partner_code': {
                'header': [1, 22, 'text', _render("_('Partner Code')")],
                'lines': [1, 0, 'text', _render("p['partner_code']")],
                'totals': [1, 22, 'text', None]},
            'partner_name': {
                'header': [1, 44, 'text', _render("_('Partner Name')")],
                'lines': [1, 0, 'text', _render("p['partner_name']")],
                'totals': [1, 44, 'text', None]},
            'ekspedisi_code': {
                'header': [1, 22, 'text', _render("_('Expedition Code')")],
                'lines': [1, 0, 'text', _render("p['ekspedisi_code']")],
                'totals': [1, 22, 'text', None]},
            'ekspedisi_name': {
                'header': [1, 44, 'text', _render("_('Expedition Name')")],
                'lines': [1, 0, 'text', _render("p['ekspedisi_name']")],
                'totals': [1, 44, 'text', None]},
            'prod_tmpl': {
                'header': [1, 22, 'text', _render("_('Type')")],
                'lines': [1, 0, 'text', _render("p['prod_tmpl']")],
                'totals': [1, 22, 'text', None]},
            'color': {
                'header': [1, 22, 'text', _render("_('Warna')")],
                'lines': [1, 0, 'text', _render("p['color']")],
                'totals': [1, 22, 'text', None]},
            'engine': {
                'header': [1, 22, 'text', _render("_('Engine number')")],
                'lines': [1, 0, 'text', _render("p['engine']")],
                'totals': [1, 22, 'text', None]},
            'chassis': {
                'header': [1, 22, 'text', _render("_('Chassis Number')")],
                'lines': [1, 0, 'text', _render("p['chassis']")],
                'totals': [1, 22, 'text', None]},
            'qty': {
                'header': [1, 22, 'text', _render("_('Qty')")],
                'lines': [1, 0, 'number', _render("p['qty']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['qty']"), None, self.rt_cell_style_decimal]},
            'qty_out': {
                'header': [1, 22, 'text', _render("_('Qty out')")],
                'lines': [1, 0, 'number', _render("p['qty_out']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', _render("p['qty_out']"), None, self.rt_cell_style_decimal]},
            'location': {
                'header': [1, 22, 'text', _render("_('Lokasi')")],
                'lines': [1, 0, 'text', _render("p['location']")],
                'totals': [1, 22, 'text', None]},
            'parent_location': {
                'header': [1, 22, 'text', _render("_('Location Tujuan (Parent)')")],
                'lines': [1, 0, 'text', _render("p['parent_location']")],
                'totals': [1, 22, 'text', None]},
            'location_source': {
                'header': [1, 22, 'text', _render("_('Location Asal (Child)')")],
                'lines': [1, 0, 'text', _render("p['location_source']")],
                'totals': [1, 22, 'text', None]},
            'parent_location_source': {
                'header': [1, 22, 'text', _render("_('Location Asal (Parent)')")],
                'lines': [1, 0, 'text', _render("p['parent_location_source']")],
                'totals': [1, 22, 'text', None]},
            'status_rfs': {
                'header': [1, 22, 'text', _render("_('Status (RFS/NRFS)')")],
                'lines': [1, 0, 'text', _render("p['status_rfs']")],
                'totals': [1, 22, 'text', None]},
            'tahun': {
                'header': [1, 22, 'text', _render("_('Tahun Rakit')")],
                'lines': [1, 0, 'text', _render("p['tahun']")],
                'totals': [1, 22, 'text', None]},
            'picking_origin': {
                'header': [1, 22, 'text', _render("_('Source Document')")],
                'lines': [1, 0, 'text', _render("p['picking_origin']")],
                'totals': [1, 22, 'text', None]},
            'backorder': {
                'header': [1, 22, 'text', _render("_('Backorder')")],
                'lines': [1, 0, 'text', _render("p['backorder']")],
                'totals': [1, 22, 'text', None]},
            'categ_name': {
                'header': [1, 22, 'text', _render("_('Kategori')")],
                'lines': [1, 0, 'text', _render("p['categ_name']")],
                'totals': [1, 22, 'text', None]},
            'internal_ref': {
                'header': [1, 22, 'text', _render("_('Deskripsi')")],
                'lines': [1, 0, 'text', _render("p['internal_ref']")],
                'totals': [1, 22, 'text', None]},
            'branch_source': {
                'header': [1, 22, 'text', _render("_('Source Branch')")],
                'lines': [1, 0, 'text', _render("p['branch_source']")],
                'totals': [1, 22, 'text', None]},
        }

        # #XLS Template Sparepart
        # self.col_specs_template_overview_sparepart = {
        #     'no': {
        #         'header': [1, 5, 'text', _render("_('No')")],
        #         'lines': [1, 0, 'number', _render("p['no']")],
        #         'totals': [1, 5, 'text', None]},
        #     'branch_code': {
        #         'header': [1, 22, 'text', _render("_('Branch Code')")],
        #         'lines': [1, 0, 'text', _render("p['branch_code']")],
        #         'totals': [1, 22, 'text', _render("_('Total')")]},
        #     'branch_name': {
        #         'header': [1, 22, 'text', _render("_('Branch Name')")],
        #         'lines': [1, 0, 'text', _render("p['branch_name']")],
        #         'totals': [1, 22, 'text', None]},
        #     'division': {
        #         'header': [1, 22, 'text', _render("_('Division')")],
        #         'lines': [1, 0, 'text', _render("p['division']")],
        #         'totals': [1, 22, 'text', None]},
        #     'picking_type_name': {
        #         'header': [1, 22, 'text', _render("_('Picking Type')")],
        #         'lines': [1, 0, 'text', _render("p['picking_type_name']")],
        #         'totals': [1, 22, 'text', None]},
        #     'packing_name': {
        #         'header': [1, 22, 'text', _render("_('Packing Number')")],
        #         'lines': [1, 0, 'text', _render("p['packing_name']")],
        #         'totals': [1, 22, 'text', None]},
        #     'packing_state': {
        #         'header': [1, 22, 'text', _render("_('Packing State')")],
        #         'lines': [1, 0, 'text', _render("p['packing_state']")],
        #         'totals': [1, 22, 'text', None]},
        #     'packing_date': {
        #         'header': [1, 22, 'text', _render("_('Packing Date')")],
        #         'lines': [1, 0, 'text', _render("p['packing_date']")],
        #         'totals': [1, 22, 'text', None]},
        #     'partner_code': {
        #         'header': [1, 22, 'text', _render("_('Partner Code')")],
        #         'lines': [1, 0, 'text', _render("p['partner_code']")],
        #         'totals': [1, 22, 'text', None]},
        #     'partner_name': {
        #         'header': [1, 44, 'text', _render("_('Partner Name')")],
        #         'lines': [1, 0, 'text', _render("p['partner_name']")],
        #         'totals': [1, 44, 'text', None]},
        #     'ekspedisi_code': {
        #         'header': [1, 22, 'text', _render("_('Expedition Code')")],
        #         'lines': [1, 0, 'text', _render("p['ekspedisi_code']")],
        #         'totals': [1, 22, 'text', None]},
        #     'ekspedisi_name': {
        #         'header': [1, 44, 'text', _render("_('Expedition Name')")],
        #         'lines': [1, 0, 'text', _render("p['ekspedisi_name']")],
        #         'totals': [1, 44, 'text', None]},
        #     'prod_tmpl': {
        #         'header': [1, 22, 'text', _render("_('Type')")],
        #         'lines': [1, 0, 'text', _render("p['prod_tmpl']")],
        #         'totals': [1, 22, 'text', None]},
        #     'qty': {
        #         'header': [1, 22, 'text', _render("_('Qty')")],
        #         'lines': [1, 0, 'number', _render("p['qty']"), None, self.pd_cell_style_decimal],
        #         'totals': [1, 22, 'number', _render("p['qty']"), None, self.rt_cell_style_decimal]},
        #     'location': {
        #         'header': [1, 22, 'text', _render("_('Location')")],
        #         'lines': [1, 0, 'text', _render("p['location']")],
        #         'totals': [1, 22, 'text', None]},
        #     'status_rfs': {
        #         'header': [1, 22, 'text', _render("_('Status (RFS/NRFS)')")],
        #         'lines': [1, 0, 'text', _render("p['status_rfs']")],
        #         'totals': [1, 22, 'text', None]},
        #     'picking_origin': {
        #         'header': [1, 22, 'text', _render("_('Source Document')")],
        #         'lines': [1, 0, 'text', _render("p['picking_origin']")],
        #         'totals': [1, 22, 'text', None]},
        #     'backorder': {
        #         'header': [1, 22, 'text', _render("_('Backorder')")],
        #         'lines': [1, 0, 'text', _render("p['backorder']")],
        #         'totals': [1, 22, 'text', None]},
        # }
     

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        self.col_specs_template_overview.update({})
        _ = _p._
        for r in _p.reports:
            wanted_list_overview = _p.wanted_list_overview
            title_short = r['title_short'].replace('/', '-')
            division = r['division']
            if division=='Sparepart' :
                wanted_list_overview = _p.wanted_list_overview_sparepart

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
            c_specs_o = [
                ('report_name', 1, 0, 'text', 'LAPORAN Stock Outstanding ' + division),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            row_pos_o += 1
            row_pos_o += 1

            # cell_style = xlwt.easyxf(_xs['xls_title'])
            # if division == 'Sparepart':   
            #     ws_o.write(row_pos_o, 1, "Cabang", self.ph_cell_style)
            #     ws_o.write(row_pos_o, 2, r['cabang'], self.ph_cell_style)    
            #     row_pos_o += 1
            #     ws_o.write(row_pos_o, 1, "Kode Part/Aksesoris", self.ph_cell_style)
            #     ws_o.write(row_pos_o, 2, r['kode_produk'], self.ph_cell_style)    
            #     row_pos_o += 1
            #     ws_o.write(row_pos_o, 1, "Deskripsi", self.ph_cell_style)
            #     ws_o.write(row_pos_o, 2, r['deskripsi'], self.ph_cell_style)    
            #     row_pos_o += 1
            # elif division == 'Unit':
            #     ws_o.write(row_pos_o, 1, "Cabang", self.ph_cell_style)
            #     ws_o.write(row_pos_o, 2, r['cabang'], self.ph_cell_style)    
            #     row_pos_o += 1
            #     ws_o.write(row_pos_o, 1, "Kode Unit", self.ph_cell_style)
            #     ws_o.write(row_pos_o, 2, r['kode_produk'], self.ph_cell_style)    
            #     row_pos_o += 1
            #     ws_o.write(row_pos_o, 1, "Deskripsi", self.ph_cell_style)
            #     ws_o.write(row_pos_o, 2, r['deskripsi'], self.ph_cell_style)    
            #     row_pos_o += 1
            #     ws_o.write(row_pos_o, 1, "Warna", self.ph_cell_style)
            #     ws_o.write(row_pos_o, 2, r['warna'], self.ph_cell_style)    
            #     row_pos_o += 1
            #     ws_o.write(row_pos_o, 1, "Nosin", self.ph_cell_style)
            #     ws_o.write(row_pos_o, 2, r['nosin'], self.ph_cell_style)    
            #     row_pos_o += 1
            # row_pos_o += 1

            # Report Column Headers
            # ws_o.write(row_pos_o, 3, "STOCK AWAL", self.ph_cell_style)
            # ws_o.write(row_pos_o, 4, r['stock_awal'], self.rt_cell_style_decimal)    
            # row_pos_o += 1
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
            for p in r['picking_ids']:
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
                
            # if division=='Unit' :
            #     # Totals
            #     ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
            #     ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)   
            #     ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
            #     ws_o.write(row_pos_o, 3, xlwt.Formula("SUM(D"+str(row_data_begin)+":D"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            #     ws_o.write(row_pos_o, 4, xlwt.Formula("SUM(E"+str(row_data_begin)+":E"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            #     ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)   
            # else :
            #     # Totals
            #     ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
            #     ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)   
            #     ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
            #     ws_o.write(row_pos_o, 3, xlwt.Formula("SUM(D"+str(row_data_begin)+":D"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            #     ws_o.write(row_pos_o, 4, xlwt.Formula("SUM(E"+str(row_data_begin)+":E"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            #     ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)   
            
            row_pos_o += 1
            # ws_o.write(row_pos_o, 3, "STOCK AKHIR", self.ph_cell_style)
            # ws_o.write(row_pos_o, 4, r['stock_akhir'], self.rt_cell_style_decimal)    
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, 'Date ' + ('-' if data['date_start_date'] == False else str(data['date_start_date'])) + ' s/d ' + ('-' if data['date_end_date'] == False else str(data['date_end_date'])))

report_stock_outstanding_xls(
    'report.Laporan Stock Outstanding',
    'stock.move',
    parser = dym_report_stock_outstanding_print_xls)
