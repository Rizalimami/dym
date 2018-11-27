

from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)


class dym_stnk_bpkb_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_stnk_bpkb_report_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        loc_stnk_ids = data['loc_stnk_ids']
        loc_bpkb_ids = data['loc_bpkb_ids']
        lot_ids = data['lot_ids']
        birojasa_ids = data['birojasa_ids']
        finco_ids = data['finco_ids']
        
        title_prefix = ''
        title_short_prefix = ''
     
        report_stnk_bpkb = {
            'type': 'Track',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Data History STNK BPKB')}


        query_start = "select a.id as lot_id, " \
            "b.name as nama_branch,  " \
            "c.name as lokasi_stnk , " \
            "d.name as lokasi_bpkb,  " \
            "e.name as nama_customer,  " \
            "e.mobile as mobile_customer,  " \
            "a.name as engine_no,  " \
            "f.name as location_name,  " \
            "g.name as supplier_name,  " \
            "h.name as stnk_name,  " \
            "a.state as state,  " \
            "i.name as finco_name,  " \
            "j.name as birojasa_name,  " \
            "k.name as sale_order,  " \
            "a.invoice_date as tgl_sale_order,  " \
            "z.name as purchase_order,  " \
            "a.po_date as tgl_purchase_order,  " \
            "l.name as no_permohonan_faktur,  " \
            "a.tgl_faktur as tgl_faktur,  " \
            "m.name as no_penerimaan_faktur,  " \
            "a.tgl_terima as tgl_terima,  " \
            "a.faktur_stnk as no_faktur,  " \
            "a.tgl_cetak_faktur as tgl_cetak_faktur,  " \
            "n.name as no_proses_stnk,  " \
            "a.tgl_proses_stnk as tgl_proses_stnk,  " \
            "o.name as no_proses_birojasa,  " \
            "a.tgl_proses_birojasa as tgl_proses_birojasa,  " \
            "p.name as no_penyerahan_faktur,  " \
            "q.name as no_penerimaan_stnk,  " \
            "a.tgl_penyerahan_faktur as tgl_penyerahan_faktur,  " \
            "r.name as no_penerimaan_notice,  " \
            "s.name as no_penerimaan_no_polisi,  " \
            "t.name as no_penerimaan_bpkb,  " \
            "a.no_notice as no_notice,  " \
            "a.no_stnk as no_stnk,  " \
            "a.no_polisi as no_polisi,  " \
            "a.no_bpkb as no_bpkb,  " \
            "a.tgl_notice as tgl_notice,  " \
            "a.tgl_stnk as tgl_stnk,  " \
            "a.tgl_bpkb as tgl_bpkb,  " \
            "a.no_urut_bpkb as no_urut_bpkb,  " \
            "a.tgl_terima_stnk as tgl_terima_stnk,  " \
            "a.tgl_terima_notice as tgl_terima_notice,  " \
            "a.tgl_terima_no_polisi as tgl_terima_no_polisi,  " \
            "a.tgl_terima_bpkb as tgl_terima_bpkb,  " \
            "u.name as no_penyerahan_stnk,  " \
            "v.name as no_penyerahan_bpkb,  " \
            "w.name as no_penyerahan_notice,  " \
            "x.name as no_penyerahan_polisi,  " \
            "a.tgl_penyerahan_stnk as tgl_penyerahan_stnk,  " \
            "a.tgl_penyerahan_notice as tgl_penyerahan_notice,  " \
            "a.tgl_penyerahan_plat as tgl_penyerahan_plat,  " \
            "a.tgl_penyerahan_bpkb as tgl_penyerahan_bpkb,  " \
            "y.name as no_pengurusan_stnk_bpkb,  " \
            "a.tgl_pengurusan_stnk_bpkb as tgl_pengurusan_stnk_bpkb,  " \
            "CASE WHEN a.tgl_penyerahan_stnk IS NOT NULL THEN a.tgl_penyerahan_stnk - a.invoice_date " \
            "    WHEN a.tgl_penyerahan_stnk IS NULL THEN CURRENT_DATE - a.invoice_date " \
            "    ELSE 0 " \
            "END as aging_stnk, " \
            "CASE WHEN a.tgl_penyerahan_bpkb IS NOT NULL THEN a.tgl_penyerahan_bpkb - a.invoice_date " \
            "    WHEN a.tgl_penyerahan_bpkb IS NULL THEN CURRENT_DATE - a.invoice_date " \
            "    ELSE 0 " \
            "END as aging_bpkb, " \
            "a.chassis_no as chassis_no  " \
            "From stock_production_lot a " \
            "LEFT JOIN dym_branch b ON b.id = a.branch_id " \
            "LEFT JOIN dym_lokasi_stnk c ON c.id = a.lokasi_stnk_id " \
            "LEFT JOIN dym_lokasi_bpkb d ON d.id = a.lokasi_bpkb_id " \
            "LEFT JOIN res_partner e ON e.id = a.customer_id " \
            "LEFT JOIN stock_location f ON f.id = a.location_id " \
            "LEFT JOIN res_partner g ON g.id = a.supplier_id " \
            "LEFT JOIN res_partner h ON h.id = a.customer_stnk " \
            "LEFT JOIN res_partner i ON i.id = a.finco_id " \
            "LEFT JOIN res_partner j ON j.id = a.biro_jasa_id " \
            "LEFT JOIN dealer_sale_order k ON k.id = a.dealer_sale_order_id " \
            "LEFT JOIN dym_permohonan_faktur l ON l.id = a.permohonan_faktur_id " \
            "LEFT JOIN dym_penerimaan_faktur m ON m.id = a.penerimaan_faktur_id " \
            "LEFT JOIN dym_proses_stnk n ON n.id = a.proses_stnk_id " \
            "LEFT JOIN dym_proses_birojasa o ON o.id = a.proses_biro_jasa_id " \
            "LEFT JOIN dym_penyerahan_faktur p ON p.id = a.penyerahan_faktur_id " \
            "LEFT JOIN dym_penerimaan_stnk q ON q.id = a.penerimaan_stnk_id " \
            "LEFT JOIN dym_penerimaan_stnk r ON r.id = a.penerimaan_notice_id " \
            "LEFT JOIN dym_penerimaan_stnk s ON s.id = a.penerimaan_no_polisi_id " \
            "LEFT JOIN dym_penerimaan_bpkb t ON t.id = a.penerimaan_bpkb_id " \
            "LEFT JOIN dym_penyerahan_stnk u ON u.id = a.penyerahan_stnk_id " \
            "LEFT JOIN dym_penyerahan_bpkb v ON v.id = a.penyerahan_bpkb_id " \
            "LEFT JOIN dym_penyerahan_stnk w ON w.id = a.penyerahan_notice_id " \
            "LEFT JOIN dym_penyerahan_stnk x ON x.id = a.penyerahan_polisi_id " \
            "LEFT JOIN dym_pengurusan_stnk_bpkb y ON y.id = a.pengurusan_stnk_bpkb_id " \
            "LEFT JOIN purchase_order z ON z.id = a.purchase_order_id " \
            "where a.name is not Null and a.state not in ('workshop','intransit','stock','reserved','returned','asset','loss') "

        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        query_end=""
        if lot_ids :
            query_end +=" AND  a.id in %s" % str(
                tuple(lot_ids)).replace(',)', ')')            
        if branch_ids :
            query_end +=" AND  a.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if partner_ids :
            query_end+="AND  a.customer_id  in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        if loc_stnk_ids :
            query_end+="AND  a.lokasi_stnk_id  in %s" % str(
                tuple(loc_stnk_ids)).replace(',)', ')')
        if loc_bpkb_ids :
            query_end+="AND  a.lokasi_bpkb_id  in %s" % str(
                tuple(loc_bpkb_ids)).replace(',)', ')')   
        if birojasa_ids :
            query_end+="AND  a.biro_jasa_id  in %s" % str(
                tuple(birojasa_ids)).replace(',)', ')')    
        if finco_ids :
            query_end+="AND  a.finco_id  in %s" % str(
                tuple(finco_ids)).replace(',)', ')')                                   
                             
        reports = [report_stnk_bpkb]
        
        query_order="order by nama_branch,nama_customer,lokasi_stnk,lokasi_bpkb"
        
        for report in reports:
            cr.execute(query_start + query_end+query_order)
            all_lines = cr.dictfetchall()
            lots = []

            if all_lines:
                def lines_map(x):
                        x.update({'docname': x['nama_branch']})
                map(lines_map, all_lines)
                for cnt in range(len(all_lines)-1):
                    if all_lines[cnt]['lot_id'] != all_lines[cnt+1]['lot_id']:
                        all_lines[cnt]['draw_line'] = 1
                    else:
                        all_lines[cnt]['draw_line'] = 0
                all_lines[-1]['draw_line'] = 1

                p_map = map(
                    lambda x: {
                        'lot_id': x['lot_id'],
                        'nama_branch': str(x['nama_branch'].encode('ascii','ignore').decode('ascii')) if x['nama_branch'] != None else '',
                        'lokasi_stnk': str(x['lokasi_stnk'].encode('ascii','ignore').decode('ascii')) if x['lokasi_stnk'] != None else '',
                        'lokasi_bpkb': str(x['lokasi_bpkb'].encode('ascii','ignore').decode('ascii')) if x['lokasi_bpkb'] != None else '',
                        'nama_customer': str(x['nama_customer'].encode('ascii','ignore').decode('ascii')) if x['nama_customer'] != None else '',
                        'mobile_customer': str(x['mobile_customer'].encode('ascii','ignore').decode('ascii')) if x['mobile_customer'] != None else '',
                        'engine_no': str(x['engine_no'].encode('ascii','ignore').decode('ascii')) if x['engine_no'] != None else '',
                        'chassis_no': str(x['chassis_no'].encode('ascii','ignore').decode('ascii')) if x['chassis_no'] != None else '',
                        'location_name': str(x['location_name'].encode('ascii','ignore').decode('ascii')) if x['location_name'] != None else '',
                        'supplier_name': str(x['supplier_name'].encode('ascii','ignore').decode('ascii')) if x['supplier_name'] != None else '',
                        'stnk_name': str(x['stnk_name'].encode('ascii','ignore').decode('ascii')) if x['stnk_name'] != None else '',
                        'state': str(x['state'].encode('ascii','ignore').decode('ascii')) if x['state'] != None else '',
                        'finco_name': str(x['finco_name'].encode('ascii','ignore').decode('ascii')) if x['finco_name'] != None else '',
                        'birojasa_name': str(x['birojasa_name'].encode('ascii','ignore').decode('ascii')) if x['birojasa_name'] != None else '',
                        'sale_order': str(x['sale_order'].encode('ascii','ignore').decode('ascii')) if x['sale_order'] != None else '',
                        'tgl_sale_order': str(x['tgl_sale_order'].encode('ascii','ignore').decode('ascii')) if x['tgl_sale_order'] != None else '',
                        'purchase_order': str(x['purchase_order'].encode('ascii','ignore').decode('ascii')) if x['purchase_order'] != None else '',
                        'tgl_purchase_order': str(x['tgl_purchase_order'].encode('ascii','ignore').decode('ascii')) if x['tgl_purchase_order'] != None else '',
                        'no_permohonan_faktur': str(x['no_permohonan_faktur'].encode('ascii','ignore').decode('ascii')) if x['no_permohonan_faktur'] != None else '',
                        'tgl_faktur': str(x['tgl_faktur'].encode('ascii','ignore').decode('ascii')) if x['tgl_faktur'] != None else '',
                        'no_penerimaan_faktur': str(x['no_penerimaan_faktur'].encode('ascii','ignore').decode('ascii')) if x['no_penerimaan_faktur'] != None else '',
                        'tgl_terima': str(x['tgl_terima'].encode('ascii','ignore').decode('ascii')) if x['tgl_terima'] != None else '',
                        'no_faktur': str(x['no_faktur'].encode('ascii','ignore').decode('ascii')) if x['no_faktur'] != None else '',
                        'tgl_cetak_faktur': str(x['tgl_cetak_faktur'].encode('ascii','ignore').decode('ascii')) if x['tgl_cetak_faktur'] != None else '',
                        'no_proses_stnk': str(x['no_proses_stnk'].encode('ascii','ignore').decode('ascii')) if x['no_proses_stnk'] != None else '',
                        'tgl_proses_stnk': str(x['tgl_proses_stnk'].encode('ascii','ignore').decode('ascii')) if x['tgl_proses_stnk'] != None else '',
                        'no_proses_birojasa': str(x['no_proses_birojasa'].encode('ascii','ignore').decode('ascii')) if x['no_proses_birojasa'] != None else '',
                        'tgl_proses_birojasa': str(x['tgl_proses_birojasa'].encode('ascii','ignore').decode('ascii')) if x['tgl_proses_birojasa'] != None else '',
                        'no_penyerahan_faktur': str(x['no_penyerahan_faktur'].encode('ascii','ignore').decode('ascii')) if x['no_penyerahan_faktur'] != None else '',
                        'tgl_penyerahan_faktur': str(x['tgl_penyerahan_faktur'].encode('ascii','ignore').decode('ascii')) if x['tgl_penyerahan_faktur'] != None else '',                       
                        'no_penerimaan_stnk': str(x['no_penerimaan_stnk'].encode('ascii','ignore').decode('ascii')) if x['no_penerimaan_stnk'] != None else '',
                        'no_penerimaan_notice': str(x['no_penerimaan_notice'].encode('ascii','ignore').decode('ascii')) if x['no_penerimaan_notice'] != None else '',
                        'no_penerimaan_no_polisi': str(x['no_penerimaan_no_polisi'].encode('ascii','ignore').decode('ascii')) if x['no_penerimaan_no_polisi'] != None else '',
                        'no_penerimaan_bpkb': str(x['no_penerimaan_bpkb'].encode('ascii','ignore').decode('ascii')) if x['no_penerimaan_bpkb'] != None else '',
                        'no_notice': str(x['no_notice'].encode('ascii','ignore').decode('ascii')) if x['no_notice'] != None else '',
                        'no_bpkb': str(x['no_bpkb'].encode('ascii','ignore').decode('ascii')) if x['no_bpkb'] != None else '',
                        'no_polisi': str(x['no_polisi'].encode('ascii','ignore').decode('ascii')) if x['no_polisi'] != None else '',
                        'no_stnk': str(x['no_stnk'].encode('ascii','ignore').decode('ascii')) if x['no_stnk'] != None else '',
                        'tgl_notice': str(x['tgl_notice'].encode('ascii','ignore').decode('ascii')) if x['tgl_notice'] != None else '',
                        'tgl_stnk': str(x['tgl_stnk'].encode('ascii','ignore').decode('ascii')) if x['tgl_stnk'] != None else '',
                        'tgl_bpkb': str(x['tgl_bpkb'].encode('ascii','ignore').decode('ascii')) if x['tgl_bpkb'] != None else '',
                        'no_urut_bpkb': str(x['no_urut_bpkb'].encode('ascii','ignore').decode('ascii')) if x['no_urut_bpkb'] != None else '',
                        'tgl_terima_stnk': str(x['tgl_terima_stnk'].encode('ascii','ignore').decode('ascii')) if x['tgl_terima_stnk'] != None else '',
                        'tgl_terima_bpkb': str(x['tgl_terima_bpkb'].encode('ascii','ignore').decode('ascii')) if x['tgl_terima_bpkb'] != None else '',
                        'tgl_terima_notice': str(x['tgl_terima_notice'].encode('ascii','ignore').decode('ascii')) if x['tgl_terima_notice'] != None else '',
                        'tgl_terima_no_polisi': str(x['tgl_terima_no_polisi'].encode('ascii','ignore').decode('ascii')) if x['tgl_terima_no_polisi'] != None else '',           
                        'no_penyerahan_stnk': str(x['no_penyerahan_stnk'].encode('ascii','ignore').decode('ascii')) if x['no_penyerahan_stnk'] != None else '',
                        'no_penyerahan_notice': str(x['no_penyerahan_notice'].encode('ascii','ignore').decode('ascii')) if x['no_penyerahan_notice'] != None else '',
                        'no_penyerahan_polisi': str(x['no_penyerahan_polisi'].encode('ascii','ignore').decode('ascii')) if x['no_penyerahan_polisi'] != None else '',
                        'no_penyerahan_bpkb': str(x['no_penyerahan_bpkb'].encode('ascii','ignore').decode('ascii')) if x['no_penyerahan_bpkb'] != None else '',
                        'tgl_penyerahan_stnk': str(x['tgl_penyerahan_stnk'].encode('ascii','ignore').decode('ascii')) if x['tgl_penyerahan_stnk'] != None else '',
                        'tgl_penyerahan_notice': str(x['tgl_penyerahan_notice'].encode('ascii','ignore').decode('ascii')) if x['tgl_penyerahan_notice'] != None else '',
                        'tgl_penyerahan_plat': str(x['tgl_penyerahan_plat'].encode('ascii','ignore').decode('ascii')) if x['tgl_penyerahan_plat'] != None else '',
                        'tgl_penyerahan_bpkb': str(x['tgl_penyerahan_bpkb'].encode('ascii','ignore').decode('ascii')) if x['tgl_penyerahan_bpkb'] != None else '',
                        'no_pengurusan_stnk_bpkb': str(x['no_pengurusan_stnk_bpkb'].encode('ascii','ignore').decode('ascii')) if x['no_pengurusan_stnk_bpkb'] != None else '',
                        'tgl_pengurusan_stnk_bpkb': str(x['tgl_pengurusan_stnk_bpkb'].encode('ascii','ignore').decode('ascii')) if x['tgl_pengurusan_stnk_bpkb'] != None else '',                                                              
                        'aging_stnk': str(x['aging_stnk']) if x['aging_stnk'] != None else '',
                        'aging_bpkb': str(x['aging_bpkb']) if x['aging_bpkb'] != None else '',
                        },
                            
                    all_lines)
                
                for p in p_map:
                    if p['lot_id'] not in map(
                            lambda x: x.get('lot_id', None), lots):
                        lots.append(p)
                        lot_lines = filter(
                            lambda x: x['lot_id'] == p['lot_id'], all_lines)
                        p.update({'lines': lot_lines})
                        p.update(
                            {'d': 1,
                             'c': 2,
                             'b': 3})
                report.update({'lots': lots})

                

        reports = filter(lambda x: x.get('lots'), reports)
        if not reports:
            raise osv.except_osv(('No Data Available !'), ("No records found for your selection!"))            

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_stnk_bpkb_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_stnk_bpkb_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_permohonan_faktur.report_stnk_bpkb'
    _inherit = 'report.abstract_report'
    _template = 'dym_permohonan_faktur.report_stnk_bpkb'
    _wrapped_report_class = dym_stnk_bpkb_report_print
