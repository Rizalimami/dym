from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
from openerp import SUPERUSER_ID
_logger = logging.getLogger(__name__)

class dym_report_retur_pembelian_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_retur_pembelian_print, self).__init__(
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
        product_ids = data['product_ids']
        trx_start_date = data['trx_start_date']
        trx_end_date = data['trx_end_date']
        division = data['division']
        supplier_ids = data['supplier_ids']
        retur_type = data['retur_type']

        title_prefix = ''
        title_short_prefix = ''
        
        report_retur_pembelian = {
            'type': 'payable',
            'division': division,
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Retur Pembelian')}

        query_start = "SELECT l.id as id_retur_line, " \
            "r.id as retur_id, " \
            "COALESCE(b.name,'') as branch_id, " \
            "COALESCE(sp.name,'') as oos_number, " \
            "r.division as division, " \
            "r.name as number, " \
            "r.date as date, " \
            "r.retur_type as retur_type, " \
            "COALESCE(i.supplier_invoice_number,'') as supplier_invoice_number, " \
            "i.document_date as document_date, " \
            "COALESCE(a.code,'') as coa, " \
            "COALESCE(p.name,'') as supplier, " \
            "COALESCE(t.name,'') as kode, " \
            "COALESCE(l.name,'') as deskripsi, " \
            "COALESCE(pav.code,'') as warna, " \
            "inv.id as invoice_retur_id, " \
            "COALESCE(lot.name,'') as engine_number, " \
            "CONCAT(COALESCE(lot.chassis_code,''),COALESCE(lot.chassis_no,'')) as chassis_number, " \
            "COALESCE(l.product_qty,0) as product_qty, " \
            "COALESCE(l.price_unit,0) as price_unit, " \
            "COALESCE(l.discount_amount,0) as discount_amount, " \
            "inv.number as invoice_retur " \
            "FROM " \
            "dym_retur_beli_line l " \
            "LEFT JOIN dym_retur_beli r ON r.id = l.retur_id " \
            "LEFT JOIN consolidate_invoice c ON c.id = r.consolidate_id " \
            "LEFT JOIN consolidate_invoice_line cl ON cl.id = l.consolidate_line_id " \
            "LEFT JOIN account_invoice i ON i.id = c.invoice_id " \
            "LEFT JOIN account_account a ON a.id = i.account_id " \
            "LEFT JOIN res_partner p ON p.id = r.partner_id " \
            "LEFT JOIN dym_branch b ON b.id = r.branch_id " \
            "LEFT JOIN product_product pr ON cl.product_id = pr.id " \
            "LEFT JOIN product_template t ON t.id = pr.product_tmpl_id " \
            "LEFT JOIN stock_production_lot lot ON lot.id = cl.name " \
            "LEFT JOIN product_attribute_value_product_product_rel pavpp ON pr.id = pavpp.prod_id " \
            "LEFT JOIN product_attribute_value pav ON pavpp.att_id = pav.id " \
            "LEFT JOIN stock_picking sp ON r.name = sp.origin "\
            "LEFT JOIN account_invoice inv ON r.name = inv.origin "\
            "where 1=1 and r.state in ('approved','except_picking','except_invoice','done') and sp.name like 'OOS%' "
            
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        query_end=""
        if division :
            query_end +=" AND r.division = '%s'" % str(division)
        if retur_type :
            query_end +=" AND r.retur_type = '%s'" % str(retur_type)
        if trx_start_date :
            query_end +=" AND r.date >= '%s'" % str(trx_start_date)
        if trx_end_date :
            query_end +=" AND r.date <= '%s'" % str(trx_end_date)
        if product_ids :
            query_end +=" AND l.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        if branch_ids :
            query_end +=" AND r.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if supplier_ids :
            query_end +=" AND r.partner_id in %s" % str(
                tuple(supplier_ids)).replace(',)', ')')
        reports = [report_retur_pembelian]
        
        # query_order = "order by cabang"
        query_order = ""
        for report in reports:
            cr.execute(query_start + query_end + query_order)
            #print query_start + query_end + query_order
            all_lines = cr.dictfetchall()
            id_retur_line = []

            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': 0,      
                        'id_retur_line': x['id_retur_line'] if x['id_retur_line'] != None else 0,      
                        'branch_id': str(x['branch_id'].encode('ascii','ignore').decode('ascii')) if x['branch_id'] != None else '',
                        'division': str(x['division']) if x['division'] != None else '',
                        'number': str(x['number'].encode('ascii','ignore').decode('ascii')) if x['number'] != None else '',
                        'date': str(x['date']) if x['date'] != None else '',
                        'supplier_invoice_number': str(x['supplier_invoice_number'].encode('ascii','ignore').decode('ascii')) if x['supplier_invoice_number'] != None else '',
                        'document_date': str(x['document_date'].encode('ascii','ignore').decode('ascii')) if x['document_date'] != None else '',
                        'supplier': str(x['supplier'].encode('ascii','ignore').decode('ascii')) if x['supplier'] != None else '',
                        'coa': str(x['coa'].encode('ascii','ignore').decode('ascii')) if x['coa'] != None else '',
                        'kode': str(x['kode'].encode('ascii','ignore').decode('ascii')) if x['kode'] != None else '',
                        'deskripsi': str(x['deskripsi'].encode('ascii','ignore').decode('ascii')) if x['deskripsi'] != None else '',
                        'warna': str(x['warna'].encode('ascii','ignore').decode('ascii')) if x['warna'] != None else '',
                        'engine_number': str(x['engine_number'].encode('ascii','ignore').decode('ascii')) if x['engine_number'] != None else '',
                        'chassis_number': str(x['chassis_number'].encode('ascii','ignore').decode('ascii')) if x['chassis_number'] != None else '',
                        'price_unit': x['price_unit'],
                        'discount_amount': x['discount_amount'],
                        'price_subtotal': 0,
                        'product_qty': x['product_qty'],
                        'jumlah': (x['price_unit'] * x['product_qty']) - x['discount_amount'],
                        'oos_number': str(x['oos_number'].encode('ascii','ignore').decode('ascii')) if x['oos_number'] != None else '',
                        'payment_number': '',
                        'payment_date': '',
                        'payment_reallocation': 0,
                        'saldo':0,
                        'invoice_retur_id': x['invoice_retur_id'],
                        'retur_type' : x['retur_type'],
                        'retur_id' : x['retur_id'],
                        'hutang' : 0,
                        'nilai_persediaan' : 0,
                        'invoice_beli_number' : '',
                        'invoice_retur' :  str(x['invoice_retur'].encode('ascii','ignore').decode('ascii')) if x['invoice_retur'] != None else '',
                        },
                    all_lines)

                inv_obj = self.pool.get('account.invoice')
                journal_obj = self.pool.get('account.move.line')
                voucher_obj = self.pool.get('account.voucher')
                retur_obj = self.pool.get('dym.retur.beli')

                for p in p_map:
                    if p['id_retur_line'] not in map(
                            lambda x: x.get('id_retur_line', None), id_retur_line):
                        id_retur_line.append(p)
                        retur_lines = filter(
                            lambda x: x['id_retur_line'] == p['id_retur_line'], all_lines)
                        p.update({'lines': retur_lines})
                        retur_line = self.pool.get('dym.retur.beli.line').browse(cr, uid, retur_lines[0]['id_retur_line'])
                        price = (retur_line.price_unit * retur_line.product_qty) - retur_line.discount_amount
                        taxes = self.pool.get('account.tax').compute_all(cr, uid, retur_line.taxes_id, price, 1, retur_line.product_id, retur_line.retur_id.partner_id)
                        dpp = taxes['total']
                        ppn = 0
                        for a in taxes['taxes']:
                            ppn += a.get('amount',0.0)
                        p.update({'dpp': dpp})
                        p.update({'ppn': ppn})

                        p['hutang'] = p['dpp'] + p['ppn']
                        # Edited Here
                        
                        try:
                            inv_res = inv_obj.browse(cr, uid, p['invoice_retur_id'], context=context)
                            journal_res = journal_obj.browse(cr, uid, inv_res.payment_ids[len(inv_res.payment_ids)-1].id, context=context)
                            voucher_id = voucher_obj.search(cr, uid, [('number','=',journal_res.move_id.name)])
                            voucher_res = voucher_obj.browse(cr, uid, voucher_id[0], context=context)

                            p.update({'payment_number': voucher_res.number})
                            p.update({'payment_date': voucher_res.date})

                            if voucher_res.amount < 1:
                                p.update({'payment_reallocation': voucher_res.amount * -1})
                            else:
                                p.update({'payment_reallocation': voucher_res.amount})
                            p.update({'saldo': p['jumlah']-p['payment_reallocation']})

                        except Exception as e:
                            p.update({'oos_number': '-'})
                            p.update({'payment_number': '-'})
                            p.update({'payment_date': '-'})
                            p.update({'payment_reallocation': 0})
                            p.update({'saldo': 0})
                    
                    inv_brws = inv_obj.browse(cr, SUPERUSER_ID, p['invoice_retur_id'], context=context)
                    for move_item in inv_brws.move_id.line_id:
                        if 'persediaan barang baik' in (move_item.account_id.name).lower() and (move_item.name == p['kode'] or move_item.name == p['deskripsi']):
                            p['nilai_persediaan'] = move_item.credit
                    retur_brws = retur_obj.browse(cr, uid, p['retur_id'])

                    p['invoice_beli_number'] = retur_brws.invoice_id.number

                report.update({'id_retur_line': id_retur_line})
        reports = filter(lambda x: x.get('id_retur_line'), reports)
        
        if not reports :
            reports = [{'title_short': 'Laporan Program Subsidi', 'type': ['out_invoice','in_invoice','in_refund','out_refund'], 'id_retur_line':
                            [{'no': 0,
                              'branch_id': 'NO DATA FOUND',
                              'division': 'NO DATA FOUND',
                              'number': 'NO DATA FOUND',
                              'date': 'NO DATA FOUND',
                              'supplier_invoice_number': 'NO DATA FOUND',
                              'document_date': 'NO DATA FOUND',
                              'supplier': 'NO DATA FOUND',
                              'coa': 'NO DATA FOUND',
                              'kode': 'NO DATA FOUND',
                              'deskripsi': 'NO DATA FOUND',
                              'warna': 'NO DATA FOUND',
                              'engine_number': 'NO DATA FOUND',
                              'chassis_number': 'NO DATA FOUND',
                              'price_unit': 0,
                              'discount_amount': 0,
                              'price_subtotal': 0,
                              'product_qty': 0,
                              'jumlah': 0,
                              'retur_type' : 'NO DATA FOUND',
                              'dpp': 0,
                              'ppn': 0,
                              'oos_number': 'NO DATA FOUND',
                              'payment_number': 'NO DATA FOUND',
                              'payment_date': 'NO DATA FOUND',
                              'payment_reallocation': 0,
                              'saldo':0,
                              'hutang' : 0,
                              'nilai_persediaan' : 0,
                              'invoice_beli_number' : 'NO DATA FOUND',
                              'invoice_retur' : 'NO DATA FOUND',
                              }], 'title': '', 'division': division}]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        objects=False
        super(dym_report_retur_pembelian_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_retur_pembelian_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_retur_beli.report_retur_pembelian'
    _inherit = 'report.abstract_report'
    _template = 'dym_retur_beli.report_retur_pembelian'
    _wrapped_report_class = dym_report_retur_pembelian_print
