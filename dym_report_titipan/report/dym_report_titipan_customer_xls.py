import xlwt
from xlwt import *
from datetime import datetime
from openerp.osv import orm
from openerp import tools
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_titipan_customer import dym_titipan_customer_report_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)
import time

_ir_translation_name = 'dym.report.cash'

class dym_titipan_customer_print_xls(dym_titipan_customer_report_print):

    def __init__(self, cr, uid, name, context):
        super(dym_titipan_customer_print_xls, self).__init__(
            cr, uid, name, context=context)
        moveline_obj = self.pool.get('account.move.line')
        self.context = context
        wl_overview = moveline_obj._report_xls_titipan_customer_fields(
            cr, uid, context)
        wl_stnk_overview = moveline_obj._report_xls_titipan_stnk_customer_fields(
            cr, uid, context)
        tmpl_upd_overview = moveline_obj._report_xls_arap_overview_template(
            cr, uid, context)
        wl_details = moveline_obj._report_xls_arap_details_fields(
            cr, uid, context)
        tmpl_upd_details = moveline_obj._report_xls_arap_overview_template(
            cr, uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': wl_overview,
            'wanted_list_stnk_overview': wl_stnk_overview,
            'template_update_overview': tmpl_upd_overview,
            'wanted_list_details': wl_details,
            'template_update_details': tmpl_upd_details,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src


class titipan_customer_report_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(titipan_customer_report_xls, self).__init__(
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
            'tgl_input': {
                'header': [1, 13, 'text', _render("_('Tgl Input')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['tgl_input'] or ''"),None,self.pd_cell_style_center],
                'totals': [1, 0, 'text', None]},  
            'divisi': {
                'header': [1, 10, 'text', _render("_('Divisi')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['divisi']"),None,self.pd_cell_style_center],
                'totals': [1, 0, 'text', None]},                                                                                      
            'cabang': {
                'header': [1, 28, 'text', _render("_('Cabang')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['cabang'] or ''")],
                'totals': [1, 0, 'text', None]},  
            'id_ai': {
                'header': [1, 15, 'text', _render("_('No Reference Titipan')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['id_ai']")],
                'totals': [1, 0, 'text', None]},                                  
            'kode_customer': {
                'header': [1, 35, 'text', _render("_('Kode Customer')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['kode_customer'] or ''")],
                'totals': [1, 0, 'text', None]},    

            'nama_customer': {
                'header': [1, 35, 'text', _render("_('Nama Customer')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['nama_customer'] or ''")],
                'totals': [1, 0, 'text', None]},    

            'payment_method': {
                'header': [1, 35, 'text', _render("_('Payment Method')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['payment_method'] or ''")],
                'totals': [1, 0, 'text', None]},  
            
            'account': {
                'header': [1, 35, 'text', _render("_('Account')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['account'] or ''")],
                'totals': [1, 0, 'text', None]},  
            
            'description': {
                'header': [1, 35, 'text', _render("_('Description')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['description'] or ''")],
                'totals': [1, 0, 'text', None]},    

            'nilai_titipan': {
                'header': [1, 20, 'text', _render("_('Nilai Titipan')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['nilai_titipan']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},  

            'account_analytic': {
                'header': [1, 30, 'text', _render("_('Account Analytic')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['account_analytic']")],
                'totals': [1, 0, 'text', None]},   
            'journal_item': {
                'header': [1, 15, 'text', _render("_('No Reference Alokasi')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['journal_item']")],
                'totals': [1, 0, 'text', None]}, 
            'nilai_alokasi': {
                'header': [1, 20, 'text', _render("_('Nilai Alokasi')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['nilai_alokasi']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},  
            'tgl_alokasi': {
                'header': [1, 13, 'text', _render("_('Tgl Alokasi')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['tgl_alokasi'] or ''"),None,self.pd_cell_style_center],
                'totals': [1, 0, 'text', None]},  
            'sisa_titipan': {
                'header': [1, 20, 'text', _render("_('Sisa Titipan')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['sisa_titipan']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]}, 
            'total_tagihan': {
                'header': [1, 20, 'text', _render("_('Total AP Stnk (Total Tagihan)')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['total_tagihan']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]}, 
            'total_jasa': {
                'header': [1, 20, 'text', _render("_('Total Jasa')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['total_jasa']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]}, 
            'selisih_margin': {
                'header': [1, 20, 'text', _render("_('Selisih Margin')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['selisih_margin']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]}, 
            'pajak_progresif': {
                'header': [1, 20, 'text', _render("_('Pajak Progresif')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['pajak_progresif']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},                                            
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
        }                                   
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
            #title_short = r['title_short'].replace('/', '-')
            jns_titipan = data['titipan'][8:]
            if jns_titipan == 'Titipan STNK':
                wanted_list_overview = _p.wanted_list_stnk_overview
            else:
                wanted_list_overview = _p.wanted_list_overview
            ws_o = wb.add_sheet('Laporan Titipan')
           
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

            #TITLE
            
            cell_style = xlwt.easyxf(_xs['xls_title'])         
            report_name = ' '.join(
                [_('Laporan '),(jns_titipan)])
            c_specs_o = [
                ('title', 1, 20, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['title'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            #row_pos_o += 1




            # COMPANY NAME
            cell_style_company = xlwt.easyxf(_xs['left'])
            c_specs_o = [
                ('company_name', 1, 0, 'text', str(_p.company.name)),
            ]
            row_data = self.xls_row_template(c_specs_o, ['company_name'])
            row_pos_o += self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style_company)
            

       
            # Start Date & End Date
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join([_('PERIODE : '), _('-' if data['start_date'] == False else str(data['start_date'])), _('s/d'), _('-' if data['end_date'] == False else str(data['end_date']))])
            c_specs_o = [('report_name', 1, 0, 'text', report_name)]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
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
            for p in r['move_lines']:
                c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'lines'), wanted_list_overview)
                for x in c_specs_o :
                    if x[0] == 'no' :
                        no += 1
                        x[4] = no
                row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
            
            row_data_end = row_pos_o
                     
            ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)   
            ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
            ws_o.set_vert_split_pos(4)
            ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)   
            ws_o.write(row_pos_o, 6, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 7, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 8, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 9, xlwt.Formula("SUM(J"+str(row_data_begin)+":J"+str(row_data_end)+")"), self.rt_cell_style_decimal)   
            ws_o.write(row_pos_o, 10, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 11, None, self.rt_cell_style_decimal)   
            ws_o.write(row_pos_o, 12, xlwt.Formula("SUM(M"+str(row_data_begin)+":M"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 13, None, self.rt_cell_style_decimal)
            if jns_titipan == 'Titipan STNK':
                ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 15, xlwt.Formula("SUM(P"+str(row_data_begin)+":P"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 16, xlwt.Formula("SUM(Q"+str(row_data_begin)+":Q"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 17, xlwt.Formula("SUM(R"+str(row_data_begin)+":R"+str(row_data_end)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 18, xlwt.Formula("SUM(S"+str(row_data_begin)+":S"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            else:
                ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"), self.rt_cell_style_decimal)

            #Footer
            ws_o.write(row_pos_o + 1, 0, None)
            #ws_o.write(row_pos_o + 2, 0, time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))
            ws_o.write(row_pos_o + 2, 0, 'Tgl cetak      : ' + time.strftime('%d-%m-%Y %H:%M:%S'),self.pd_cell_style)
            ws_o.write(row_pos_o + 3, 0, 'Dicetak oleh : ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name),self.pd_cell_style)


titipan_customer_report_xls(
    'report.Laporan Titipan',
    'account.move.line',
    parser=dym_titipan_customer_print_xls)
