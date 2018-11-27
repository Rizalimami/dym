from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_penerimaan_unit_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_penerimaan_unit_print, self).__init__(
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
        trx_start_date = data['trx_start_date']
        trx_end_date = data['trx_end_date']

        title_prefix = ''
        title_short_prefix = ''
        
        report_penerimaan_unit = {
            'type': 'payable',
            'title': '',
            'title_short': 'Laporan Penerimaan Unit'}

        query_start = "SELECT l.id as id_ai, " \
            "COALESCE(b.name,'') as branch_id, " \
            "supplier.name as supplier, " \
            "obj.date as date, " \
            "obj.name as number, " \
            "COALESCE(obj.sj_no,'') as surat_jalan, " \
            "COALESCE(inv.supplier_invoice_number,'') as supplier_invoice_number, " \
            "inv.document_date as document_date, " \
            "COALESCE(t.name,'') as product_code, " \
            "CASE WHEN lot.state = 'intransit' THEN 'Intransit' " \
            "    WHEN lot.state = 'reserved' THEN 'Reserved' " \
            "    WHEN loc.usage = 'internal' and lot.state in ('sold','paid','sold_offtr','paid_offtr') THEN 'Undelivered' " \
            "    WHEN loc.usage = 'internal' THEN 'RFS' " \
            "    WHEN loc.usage = 'nrfs' THEN 'NRFS' " \
            "    ELSE '' " \
            "END as posisi, " \
            "COALESCE(lot.name,'') as mesin, " \
            "CONCAT(COALESCE(lot.chassis_code,''),COALESCE(lot.chassis_no,'')) as rangka, " \
            "COALESCE(invl.price_unit,0) as price_unit, " \
            "(COALESCE(invl.discount_amount,0)+COALESCE(invl.discount_cash,0)+COALESCE(invl.discount_program,0)+COALESCE(invl.discount_lain,0))/COALESCE(invl.quantity,0) as discount, " \
            "COALESCE(invl.price_unit,0)-((COALESCE(invl.discount_amount,0)+COALESCE(invl.discount_cash,0)+COALESCE(invl.discount_program,0)+COALESCE(invl.discount_lain,0))/COALESCE(invl.quantity,0)) as ap_unit " \
            "FROM " \
            "dym_stock_packing_line l " \
            "LEFT JOIN dym_stock_packing obj ON l.packing_id = obj.id " \
            "LEFT JOIN stock_picking pick ON pick.id = obj.picking_id " \
            "LEFT JOIN res_partner supplier ON supplier.id = pick.partner_id " \
            "LEFT JOIN dym_branch b ON b.id = pick.branch_id " \
            "LEFT JOIN stock_move m ON m.picking_id = pick.id and m.product_id = l.product_id " \
            "LEFT JOIN stock_production_lot lot ON lot.id = l.serial_number_id " \
            "LEFT JOIN stock_location loc ON loc.id = lot.location_id " \
            "LEFT JOIN product_product p ON p.id = l.product_id " \
            "LEFT JOIN product_template t ON t.id = p.product_tmpl_id " \
            "LEFT JOIN account_invoice_line invl ON invl.purchase_line_id = m.purchase_line_id " \
            "LEFT JOIN account_invoice inv ON inv.id = invl.invoice_id " \
            "where 1=1 and obj.state = 'posted' and pick.division = 'Unit' and m.purchase_line_id is not null and invl.purchase_line_id is not null "
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        query_end=""
        query_end2=""
        if trx_start_date :
            query_end +=" AND obj.date >= '%s'" % str(trx_start_date)
        if trx_end_date :
            query_end +=" AND obj.date <= '%s'" % str(trx_end_date)
        if branch_ids :
            query_end +=" AND pick.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        reports = [report_penerimaan_unit]
        
        query_order = " order by l.id, inv.date_invoice desc "
        for report in reports:
            cr.execute(query_start + query_end + query_order)
            all_lines = cr.dictfetchall()
            id_ai = []
            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': 0,      
                        'id_ai': x['id_ai'] if x['id_ai'] != None else 0,      
                        'branch_id': str(x['branch_id'].encode('ascii','ignore').decode('ascii')) if x['branch_id'] != None else '',
                        'supplier': str(x['supplier'].encode('ascii','ignore').decode('ascii')) if x['supplier'] != None else '',
                        'date': str(x['date']) if x['date'] != None else '',
                        'number': str(x['number'].encode('ascii','ignore').decode('ascii')) if x['number'] != None else '',
                        'surat_jalan': str(x['surat_jalan'].encode('ascii','ignore').decode('ascii')) if x['surat_jalan'] != None else '',
                        'supplier_invoice_number': str(x['supplier_invoice_number'].encode('ascii','ignore').decode('ascii')) if x['supplier_invoice_number'] != None else '',
                        'document_date': str(x['document_date']) if x['document_date'] != None else '',
                        'product_code': str(x['product_code'].encode('ascii','ignore').decode('ascii')) if x['product_code'] != None else '',
                        'posisi': str(x['posisi'].encode('ascii','ignore').decode('ascii')) if x['posisi'] != None else '',
                        'mesin': str(x['mesin'].encode('ascii','ignore').decode('ascii')) if x['mesin'] != None else '',
                        'rangka': str(x['rangka']) if 'rangka' in x and x['rangka'] != None else '',
                        'price_unit': x['price_unit'],
                        'discount': x['discount'],
                        'ap_unit': x['ap_unit'],
                        },
                    all_lines)
                line_id = []
                for p in p_map:
                    if p['id_ai'] not in map(
                            lambda x: x.get('id_ai', None), id_ai):
                        records = filter(
                            lambda x: x['id_ai'] == p['id_ai'], all_lines)
                        if records[0]['id_ai'] in line_id:
                            continue
                        line_id.append(records[0]['id_ai'])
                        p.update({'lines': records})
                        id_ai.append(p)
                report.update({'id_ai': id_ai})
                # report.update({'id_ai': p_map})

        reports = filter(lambda x: x.get('id_ai'), reports)

        if not reports :
            raise osv.except_osv(_('Data Not Found!'), _('Tidak ditemukan data dari hasil filter report Penerimaan Unit.'))

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_penerimaan_unit_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_penerimaan_unit_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_penerimaan_unit.report_penerimaan_unit'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_penerimaan_unit.report_penerimaan_unit'
    _wrapped_report_class = dym_report_penerimaan_unit_print
