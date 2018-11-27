import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .dym_report_stnk_bpkb import dym_stnk_bpkb_report_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)

_ir_translation_name = 'report.stnk.bpkb'

class dym_stnk_bpkb_print_xls(dym_stnk_bpkb_report_print):

    def __init__(self, cr, uid, name, context):
        super(dym_stnk_bpkb_print_xls, self).__init__(
            cr, uid, name, context=context)
        lot_obj = self.pool.get('stock.production.lot')
        self.context = context
        wl_overview = lot_obj._report_xls_stnk_bpkb_fields(
            cr, uid, context)
        tmpl_upd_overview = lot_obj._report_xls_arap_overview_template(
            cr, uid, context)
        wl_details = lot_obj._report_xls_arap_details_fields(
            cr, uid, context)
        tmpl_upd_details = lot_obj._report_xls_arap_overview_template(
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


class stnk_bpkb_report_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(stnk_bpkb_report_xls, self).__init__(
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
        ph_cell_format = _xs['bold'] + fill_blue + _xs['borders_all']
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
            'branch_id': {
                'header': [1, 30, 'text', _render("_('Cabang')")],
                'lines': [1, 0, 'text', _render("p['nama_branch'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'engine_no': {
                'header': [1, 22, 'text', _render("_('Engine No')")],
                'lines': [1, 0, 'text', _render("p['engine_no'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'chassis_no': {
                'header': [1, 22, 'text', _render("_('Chassis No')")],
                'lines': [1, 0, 'text', _render("p['chassis_no'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'nama_customer': {
                'header': [1, 22, 'text', _render("_('Customer')")],
                'lines': [1, 0, 'text', _render("p['nama_customer'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'mobile_customer': {
                'header': [1, 22, 'text', _render("_('No HP')")],
                'lines': [1, 0, 'text', _render("p['mobile_customer'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'lokasi_stnk': {
                'header': [1, 22, 'text', _render("_('Lokasi STNK')")],
                'lines': [1, 0, 'text', _render("p['lokasi_stnk'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'lokasi_bpkb': {
                'header': [1, 22, 'text', _render("_('Lokasi BPKB')")],
                'lines': [1, 0, 'text', _render("p['lokasi_bpkb'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},    
            'location_name': {
                'header': [1, 22, 'text', _render("_('Lokasi Stock')")],
                'lines': [1, 0, 'text', _render("p['location_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},        
            'supplier_name': {
                'header': [1, 30, 'text', _render("_('Supplier')")],
                'lines': [1, 0, 'text', _render("p['supplier_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},  
            'stnk_name': {
                'header': [1, 22, 'text', _render("_('Customer STNK')")],
                'lines': [1, 0, 'text', _render("p['stnk_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'state': {
                'header': [1, 10, 'text', _render("_('State')")],
                'lines': [1, 0, 'text', _render("p['state'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'finco_name': {
                'header': [1, 32, 'text', _render("_('Finance Company')")],
                'lines': [1, 0, 'text', _render("p['finco_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'birojasa_name': {
                'header': [1, 22, 'text', _render("_('Biro Jasa')")],
                'lines': [1, 0, 'text', _render("p['birojasa_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'sale_order': {
                'header': [1, 22, 'text', _render("_('No Sales Memo')")],
                'lines': [1, 0, 'text', _render("p['sale_order'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},  
            'tgl_sale_order': {
                'header': [1, 22, 'text', _render("_('Tgl Sales Memo')")],
                'lines': [1, 0, 'text', _render("p['tgl_sale_order'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},    
            'purchase_order': {
                'header': [1, 22, 'text', _render("_('No Purchase Order')")],
                'lines': [1, 0, 'text', _render("p['purchase_order'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},  
            'tgl_purchase_order': {
                'header': [1, 22, 'text', _render("_('Tgl Purchase Order')")],
                'lines': [1, 0, 'text', _render("p['tgl_purchase_order'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                      
            'no_permohonan_faktur': {
                'header': [1, 22, 'text', _render("_('No Permohonan Faktur')")],
                'lines': [1, 0, 'text', _render("p['no_permohonan_faktur'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'tgl_faktur': {
                'header': [1, 22, 'text', _render("_('Tgl Mohon Faktur')")],
                'lines': [1, 0, 'text', _render("p['tgl_faktur'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'no_penerimaan_faktur': {
                'header': [1, 22, 'text', _render("_('No Penerimaan Faktur')")],
                'lines': [1, 0, 'text', _render("p['no_penerimaan_faktur'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_terima': {
                'header': [1, 22, 'text', _render("_('Tgl Terima Faktur')")],
                'lines': [1, 0, 'text', _render("p['tgl_terima'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'no_faktur': {
                'header': [1, 22, 'text', _render("_('No Faktur')")],
                'lines': [1, 0, 'text', _render("p['no_faktur'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_cetak_faktur': {
                'header': [1, 22, 'text', _render("_('Tgl Cetak Faktur')")],
                'lines': [1, 0, 'text', _render("p['tgl_cetak_faktur'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},   
            'no_penyerahan_faktur': {
                'header': [1, 22, 'text', _render("_('No Penyerahan Faktur')")],
                'lines': [1, 0, 'text', _render("p['no_penyerahan_faktur'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'tgl_penyerahan_faktur': {
                'header': [1, 22, 'text', _render("_('Tgl Penyerahan Faktur')")],
                'lines': [1, 0, 'text', _render("p['tgl_penyerahan_faktur'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'no_proses_stnk': {
                'header': [1, 22, 'text', _render("_('No Proses STNK')")],
                'lines': [1, 0, 'text', _render("p['no_proses_stnk'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_proses_stnk': {
                'header': [1, 22, 'text', _render("_('Tgl Proses STNK')")],
                'lines': [1, 0, 'text', _render("p['tgl_proses_stnk'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'no_proses_birojasa': {
                'header': [1, 22, 'text', _render("_('No Proses Birojasa')")],
                'lines': [1, 0, 'text', _render("p['no_proses_birojasa'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_proses_birojasa': {
                'header': [1, 22, 'text', _render("_('Tgl Proses Birojasa')")],
                'lines': [1, 0, 'text', _render("p['tgl_proses_birojasa'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},   
            'no_penerimaan_stnk': {
                'header': [1, 22, 'text', _render("_('No Penerimaan STNK')")],
                'lines': [1, 0, 'text', _render("p['no_penerimaan_stnk'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'no_penerimaan_notice': {
                'header': [1, 22, 'text', _render("_('No Penerimaan Notice')")],
                'lines': [1, 0, 'text', _render("p['no_penerimaan_notice'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'no_penerimaan_no_polisi': {
                'header': [1, 22, 'text', _render("_('No Penerimaan Plat')")],
                'lines': [1, 0, 'text', _render("p['no_penerimaan_no_polisi'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'no_penerimaan_bpkb': {
                'header': [1, 22, 'text', _render("_('No Penerimaan BPKB')")],
                'lines': [1, 0, 'text', _render("p['no_penerimaan_bpkb'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},  
            'no_notice': {
                'header': [1, 15, 'text', _render("_('No Notice')")],
                'lines': [1, 0, 'text', _render("p['no_notice'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'no_bpkb': {
                'header': [1, 15, 'text', _render("_('No BPKB')")],
                'lines': [1, 0, 'text', _render("p['no_bpkb'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'no_polisi': {
                'header': [1, 15, 'text', _render("_('No Polisi')")],
                'lines': [1, 0, 'text', _render("p['no_polisi'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'no_stnk': {
                'header': [1, 15, 'text', _render("_('No STNK')")],
                'lines': [1, 0, 'text', _render("p['no_stnk'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_notice': {
                'header': [1, 15, 'text', _render("_('Tgl JTP Notice')")],
                'lines': [1, 0, 'text', _render("p['tgl_notice'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_stnk': {
                'header': [1, 15, 'text', _render("_('Tgl JTP STNK')")],
                'lines': [1, 0, 'text', _render("p['tgl_stnk'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},   
            'tgl_bpkb': {
                'header': [1, 15, 'text', _render("_('Tgl Jadi BPKB')")],
                'lines': [1, 0, 'text', _render("p['tgl_bpkb'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'no_urut_bpkb': {
                'header': [1, 15, 'text', _render("_('No Urut BPKB')")],
                'lines': [1, 0, 'text', _render("p['no_urut_bpkb'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_terima_stnk': {
                'header': [1, 15, 'text', _render("_('Tgl Terima STNK')")],
                'lines': [1, 0, 'text', _render("p['tgl_terima_stnk'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_terima_bpkb': {
                'header': [1, 15, 'text', _render("_('Tgl Terima BPKB')")],
                'lines': [1, 0, 'text', _render("p['tgl_terima_bpkb'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_terima_notice': {
                'header': [1, 15, 'text', _render("_('Tgl Terima Notice')")],
                'lines': [1, 0, 'text', _render("p['tgl_terima_notice'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_terima_no_polisi': {
                'header': [1, 15, 'text', _render("_('Tgl Terima Plat')")],
                'lines': [1, 0, 'text', _render("p['tgl_terima_no_polisi'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},     
            'no_penyerahan_stnk': {
                'header': [1, 22, 'text', _render("_('No Penyerahan STNK')")],
                'lines': [1, 0, 'text', _render("p['no_penyerahan_stnk'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'no_penyerahan_notice': {
                'header': [1, 22, 'text', _render("_('No Penyerahan Notice')")],
                'lines': [1, 0, 'text', _render("p['no_penyerahan_notice'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'no_penyerahan_polisi': {
                'header': [1, 22, 'text', _render("_('No Penyerahan Polisi')")],
                'lines': [1, 0, 'text', _render("p['no_penyerahan_polisi'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'no_penyerahan_bpkb': {
                'header': [1, 22, 'text', _render("_('No Penyerahan BPKB')")],
                'lines': [1, 0, 'text', _render("p['no_penyerahan_bpkb'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},   
            'tgl_penyerahan_stnk': {
                'header': [1, 15, 'text', _render("_('Tgl Penyerahan STNK')")],
                'lines': [1, 0, 'text', _render("p['tgl_penyerahan_stnk'] or 'n/a'")],
                'totals': [1, 0, 'text', None]}, 
            'tgl_penyerahan_notice': {
                'header': [1, 15, 'text', _render("_('Tgl Penyerahan Notice')")],
                'lines': [1, 0, 'text', _render("p['tgl_penyerahan_notice'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_penyerahan_plat': {
                'header': [1, 15, 'text', _render("_('Tgl Penyerahan Plat')")],
                'lines': [1, 0, 'text', _render("p['tgl_penyerahan_plat'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_penyerahan_bpkb': {
                'header': [1, 15, 'text', _render("_('Tgl Penyerahan BPKB')")],
                'lines': [1, 0, 'text', _render("p['tgl_penyerahan_bpkb'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'no_pengurusan_stnk_bpkb': {
                'header': [1, 15, 'text', _render("_('No Pengurusan STNK BPKB')")],
                'lines': [1, 0, 'text', _render("p['no_pengurusan_stnk_bpkb'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
            'tgl_pengurusan_stnk_bpkb': {
                'header': [1, 15, 'text', _render("_('Tgl Pengurusan STNK BPKB')")],
                'lines': [1, 0, 'text', _render("p['tgl_pengurusan_stnk_bpkb'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                          
            'aging_stnk': {
                'header': [1, 15, 'text', _render("_('Aging STNK')")],
                'lines': [1, 0, 'text', _render("p['aging_stnk'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
            'aging_bpkb': {
                'header': [1, 15, 'text', _render("_('Aging BPKB')")],
                'lines': [1, 0, 'text', _render("p['aging_bpkb'] or 'n/a'")],
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
                [_p.company.name, r['title'], _('Report STNK BPKB'),
                 _p.report_info])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            row_pos_o += 1
            report_name = ' '.join(
                [_p.company.name, r['title'], _('Details'),
                 _p.report_info + ' ' + _p.company.currency_id.name])
            c_specs_d = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_d, ['report_name'])
            

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



            for p in r['lots']:
                c_specs_o = map(
                    lambda x: self.render(
                        x, self.col_specs_template_overview, 'lines'),
                    wanted_list_overview)
                row_data = self.xls_row_template(
                    c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)

                row_pos_d += 1







            

    # end def generate_xls_report

# end class stock_report_xls

stnk_bpkb_report_xls(
    'report.dym_report_stnk_bpkb_xls',
    'stock.production.lot',
    parser=dym_stnk_bpkb_print_xls)
