import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_stock_extras import dym_stock_extras_report_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)

_ir_translation_name = 'dym.stock.report'


class dym_stock_report_extras_print_xls(dym_stock_extras_report_print):

    def __init__(self, cr, uid, name, context):
        super(dym_stock_report_extras_print_xls, self).__init__(
            cr, uid, name, context=context)
        quant_obj = self.pool.get('stock.quant')
        self.context = context
        wl_overview = quant_obj._report_xls_stock_extras_fields(
            cr, uid, context)
        tmpl_upd_overview = quant_obj._report_xls_arap_overview_template(
            cr, uid, context)
        wl_details = quant_obj._report_xls_arap_details_fields(
            cr, uid, context)
        tmpl_upd_details = quant_obj._report_xls_arap_overview_template(
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


class stock_report_sprepart_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(stock_report_sprepart_xls, self).__init__(
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
        self.pd_cell_style_decimal_fill = xlwt.easyxf(
            pd_cell_format + _xs['right'] + _xs['fill'] + _xs['bold'] ,
            num_format_str=report_xls.decimal_format)        
        self.pd_cell_style_number_fill = xlwt.easyxf(
            pd_cell_format + _xs['right'] + _xs['fill'] + _xs['bold']) 
        
        # totals
        rt_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rt_cell_style = xlwt.easyxf(rt_cell_format)
        self.rt_cell_style_right = xlwt.easyxf(rt_cell_format + _xs['right'])
        self.rt_cell_style_decimal = xlwt.easyxf(
            rt_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)

        # XLS Template
        self.col_specs_template_overview = {
            'branch_code': {
                'header': [1, 15, 'text', _render("_('Kode Cabang')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['branch_code'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'branch_name': {
                'header': [1, 35, 'text', _render("_('Cabang')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['branch_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},       
            'parent_category': {
                'header': [1, 35, 'text', _render("_('Kategori')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['parent_category'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},      
            'product_desc': {
                'header': [1, 22, 'text', _render("_('Kode Product')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['product_desc'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'default_code': {
                'header': [1, 22, 'text', _render("_('Internal Reference')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['default_code'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'categ_name': {
                'header': [1, 22, 'text', _render("_('Kategori')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['categ_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'product_name': {
                'header': [1, 22, 'text', _render("_('Nama Barang')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['product_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'move_origin': {
                'header': [1, 22, 'text', _render("_('Origin')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['move_origin'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'picking_name': {
                'header': [1, 22, 'text', _render("_('Picking')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['picking_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'unit_grn': {
                'header': [1, 22, 'text', _render("_('GRN Unit')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['unit_grn'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'location_parent': {
                'header': [1, 35, 'text', _render("_('Lokasi Parent')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['location_parent'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'location_name': {
                'header': [1, 35, 'text', _render("_('Lokasi')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['location_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'status': {
                'header': [1, 15, 'text', _render("_('Status')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['status']")],
                'totals': [1, 0, 'text', None]},                                            
            # 'aging': {
            #     'header': [1, 15, 'text', _render("_('Aging')"),None,self.rh_cell_style_center],
            #     'lines': [1, 0, 'text', _render("p['aging']")],
            #     'totals': [1, 0, 'text', None]},
            'quantity': {
                'header': [1, 15, 'text', _render("_('Quantity')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['quantity']")],
                'totals': [1, 0, 'text', None]},
            'harga_satuan': {
                'header': [1, 22, 'text', _render("_('Harga Satuan')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['harga_satuan']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},
            'total_harga': {
                'header': [1, 22, 'text', _render("_('Total Harga')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['total_harga']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                       
            
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

            # Title
            cell_style = xlwt.easyxf(_xs['xls_title'])
            report_name = ' '.join(
                [_p.company.name, r['title'], _('Laporan Stock KSU'),
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
            for p in r['quants']:
                c_specs_o = map(
                    lambda x: self.render(
                        x, self.col_specs_template_overview, 'lines'),
                    wanted_list_overview)
                row_data = self.xls_row_template(
                    c_specs_o, [x[0] for x in c_specs_o])
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
            ws_o.write(row_pos_o, 8, None,self.ph_cell_style) 
            ws_o.write(row_pos_o, 9, None,self.ph_cell_style) 
            ws_o.write(row_pos_o, 10, None,self.ph_cell_style) 
            ws_o.write(row_pos_o, 11, None,self.ph_cell_style) 
            ws_o.write(row_pos_o, 12, "Total",self.ph_cell_style) 
            ws_o.write(row_pos_o, 13, xlwt.Formula("SUM(N"+str(row_data_begin)+":N"+str(row_data_end)+")"),self.pd_cell_style_number_fill)
            ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"),self.pd_cell_style_number_fill)
            ws_o.write(row_pos_o, 15, xlwt.Formula("SUM(P"+str(row_data_begin)+":P"+str(row_data_end)+")"),self.pd_cell_style_decimal_fill)        
            ws_o.write(row_pos_o+1, 0, _p.report_date+" "+username)


stock_report_sprepart_xls(
    'report.dym.stock.extras.report.xls',
    'account.period',
    parser=dym_stock_report_extras_print_xls)
