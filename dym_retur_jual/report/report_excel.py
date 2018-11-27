from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_retur_penjualan_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_retur_penjualan_print, self).__init__(
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
        customer_ids = data['customer_ids']
        retur_type = data['retur_type']

        title_prefix = ''
        title_short_prefix = ''
        
        report_retur_penjualan = {
            'type': 'payable',
            'division': division,
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Retur Penjualan')}

        query_start = "SELECT l.id as id_retur_line, " \
            "COALESCE(b.name,'') as branch_id, " \
            "r.division as division, " \
            "r.name as number, " \
            "r.date as date, " \
            "COALESCE(sp.name,'') as ois_number, " \
            "r.retur_type as type, " \
            "r.ket as keterangan, " \
            "COALESCE(ivs.number,'') as invoice_jual_number, " \
            "ivs.date_invoice as invoice_jual_date, " \
            "COALESCE(i.number,'') as invoice_retur_number, " \
            "i.id as invoice_retur_id, " \
            "i.date_invoice as invoice_retur_date, " \
            "COALESCE(p.name,'') as customer, " \
            "COALESCE(t.name,'') as kode, " \
            "COALESCE(l.name,'') as deskripsi, " \
            "COALESCE(pav.code,'') as warna, " \
            "COALESCE(lot.name,'') as engine_number, " \
            "CONCAT(COALESCE(lot.chassis_code,''),COALESCE(lot.chassis_no,'')) as chassis_number, " \
            "COALESCE(l.product_qty,0) as product_qty, " \
            "case when r.division = 'Unit' "\
                " then COALESCE(dsol.price_subtotal,0) " \
                " else COALESCE(sol.price_unit,0) " \
            "end as dpp, " \
            "case when r.division = 'Unit' " \
                " then COALESCE(dsol.price_subtotal*0.1,0) " \
                " else COALESCE(sol.price_unit*0.1,0) " \
            "end as ppn, " \
            "case when r.division = 'Unit' " \
                " then COALESCE(dsol.price_unit/1.1,0) " \
                " else 0 " \
            "end as sales," \
            "COALESCE(l.price_unit,0) as price_unit, " \
            "COALESCE(dsol.price_bbn,0) as price_bbn, " \
            "COALESCE(l.discount_total,0) as discount_total, " \
            "COALESCE(dsol.discount_po,0) as discount_konsumen, " \
            "COALESCE(psub.ps_dealer,0) as discount_dealer, " \
            "COALESCE(psub.ps_finco,0) as discount_finco, " \
            "COALESCE(psub.ps_md,0) as discount_md, " \
            "COALESCE(psub.ps_ahm,0) as discount_ahm " \
            "FROM " \
            "dym_retur_jual_line l " \
            "LEFT JOIN dym_retur_jual r ON r.id = l.retur_id " \
            "LEFT JOIN dealer_sale_order dso ON dso.id = r.dso_id " \
            "LEFT JOIN dealer_sale_order_line dsol ON dsol.id = l.dso_line_id " \
            "LEFT JOIN dealer_sale_order_line_discount_line psub ON psub.dealer_sale_order_line_discount_line_id = l.dso_line_id " \
            "LEFT JOIN sale_order so ON so.id = r.so_id " \
            "LEFT JOIN sale_order_line sol ON sol.id = l.so_line_id " \
            "LEFT JOIN account_invoice ivs ON ivs.id = r.invoice_id " \
            "LEFT JOIN account_invoice_line ils ON ils.id = l.invoice_line_id " \
            "LEFT JOIN account_invoice i ON i.origin = r.name and i.type = 'out_refund' " \
            "LEFT JOIN res_partner p ON p.id = r.partner_id " \
            "LEFT JOIN dym_branch b ON b.id = r.branch_id " \
            "LEFT JOIN product_product pr ON ils.product_id = pr.id " \
            "LEFT JOIN product_template t ON t.id = pr.product_tmpl_id " \
            "LEFT JOIN stock_production_lot lot ON lot.id = dsol.lot_id " \
            "LEFT JOIN product_attribute_value_product_product_rel pavpp ON pr.id = pavpp.prod_id " \
            "LEFT JOIN product_attribute_value pav ON pavpp.att_id = pav.id " \
            "LEFT JOIN stock_picking sp ON r.name = sp.origin "\
            "where 1=1 and r.state in ('approved','except_picking','except_invoice','done') "
            
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
        if customer_ids :
            query_end +=" AND r.partner_id in %s" % str(
                tuple(customer_ids)).replace(',)', ')')
        reports = [report_retur_penjualan]
        
        query_order = ""
        for report in reports:
            cr.execute(query_start + query_end + query_order)
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
                        'type': str(x['type'].encode('ascii','ignore').decode('ascii')) if x['type'] != None else '',
                        'keterangan': str(x['keterangan'].encode('ascii','ignore').decode('ascii')) if x['keterangan'] != None else '',
                        'date': str(x['date']) if x['date'] != None else '',
                        'invoice_jual_number': str(x['invoice_jual_number'].encode('ascii','ignore').decode('ascii')) if x['invoice_jual_number'] != None else '',
                        'invoice_retur_number': str(x['invoice_retur_number'].encode('ascii','ignore').decode('ascii')) if x['invoice_retur_number'] != None else '',
                        'invoice_jual_date': str(x['invoice_jual_date'].encode('ascii','ignore').decode('ascii')) if x['invoice_jual_date'] != None else '',
                        'invoice_retur_date': str(x['invoice_retur_date'].encode('ascii','ignore').decode('ascii')) if x['invoice_retur_date'] != None else '',
                        'customer': str(x['customer'].encode('ascii','ignore').decode('ascii')) if x['customer'] != None else '',
                        'kode': str(x['kode'].encode('ascii','ignore').decode('ascii')) if x['kode'] != None else '',
                        'deskripsi': str(x['deskripsi'].encode('ascii','ignore').decode('ascii')) if x['deskripsi'] != None else '',
                        'warna': str(x['warna'].encode('ascii','ignore').decode('ascii')) if x['warna'] != None else '',
                        'engine_number': str(x['engine_number'].encode('ascii','ignore').decode('ascii')) if x['engine_number'] != None else '',
                        'chassis_number': str(x['chassis_number'].encode('ascii','ignore').decode('ascii')) if x['chassis_number'] != None else '',
                        'ois_number': str(x['ois_number'].encode('ascii','ignore').decode('ascii')) if x['ois_number'] != None else '',
                        'price_unit': x['price_unit'],
                        'dpp': x['dpp'],
                        'ppn': x['ppn'],
                        'sales': x['sales'],
                        'price_bbn': x['price_bbn'],
                        'discount_total': x['discount_total'],
                        'invoice_retur_id': x['invoice_retur_id'],
                        'price_subtotal': 0,
                        'product_qty': x['product_qty'],
                        'biaya_retur': 0,
                        'payment_number': '',
                        'payment_date': '',
                        'payment_allocation': 0,
                        'saldo':0,
                        'aging':'',
                        'discount_konsumen': x['discount_konsumen'],
                        'discount_dealer':x['discount_dealer'],
                        'discount_finco':x['discount_finco'],
                        'discount_md':x['discount_md'],
                        'discount_ahm':x['discount_ahm'],
                        'nilai_hpp':0,
                        },
                    all_lines)
                retur_res = []

                inv_obj = self.pool.get('account.invoice')
                journal_obj = self.pool.get('account.move.line')
                voucher_obj = self.pool.get('account.voucher')

                for p in p_map:
                    if p['id_retur_line'] not in map(
                            lambda x: x.get('id_retur_line', None), id_retur_line):
                        id_retur_line.append(p)
                        retur_lines = filter(
                            lambda x: x['id_retur_line'] == p['id_retur_line'], all_lines)
                        p.update({'lines': retur_lines})
                        retur_line = self.pool.get('dym.retur.jual.line').browse(cr, uid, retur_lines[0]['id_retur_line'])
                        biaya_retur = 0
                        jumlah = (retur_line.price_unit * retur_line.product_qty) - retur_line.discount_total + retur_line.price_bbn
                        if retur_line.retur_id.biaya_retur != 0 and retur_line.retur_id.id not in retur_res:
                            retur_res.append(retur_line.retur_id.id)
                            biaya_retur = retur_line.retur_id.biaya_retur
                            jumlah += (retur_line.retur_id.biaya_retur * -1)
                        p.update({'biaya_retur': biaya_retur})
                        p.update({'jumlah': jumlah})
                        # p.update({'dpp': 0})
                        # p.update({'dpp': 0})

                        
                        # Edited Here
                        try:
                            inv_res = inv_obj.browse(cr, uid, p['invoice_retur_id'], context=context)
                            journal_res = journal_obj.browse(cr, uid, inv_res.payment_ids[len(inv_res.payment_ids)-1].id, context=context)
                            voucher_id = voucher_obj.search(cr, uid, [('number','=',journal_res.move_id.name)])
                            voucher_res = voucher_obj.browse(cr, uid, voucher_id[0], context=context)

                            p.update({'payment_number': voucher_res.number})
                            p.update({'payment_date': voucher_res.date})

                            if voucher_res.amount < 1:
                                p.update({'payment_allocation': voucher_res.amount * -1})
                            else:
                                p.update({'payment_allocation': voucher_res.amount})
                            p.update({'saldo': p['jumlah']-p['payment_allocation']})

                            start_date = datetime.strptime(p['date'], "%Y-%m-%d")
                            end_date = datetime.strptime(p['payment_date'], "%Y-%m-%d")
                            p.update({'aging': '%s Hari' % abs((end_date-start_date).days )})
                        except Exception as e:
                            p.update({'ois_number': '-'})
                            p.update({'payment_number': '-'})
                            p.update({'payment_date': '-'})
                            p.update({'payment_allocation': 0})
                            p.update({'saldo': 0})
                            p.update({'aging': '-'})

                        # Add Nilai HPP
                        move_srch = self.pool.get('account.move').search(cr, uid, [('name','=',p['invoice_jual_number'])])
                        move_brws = self.pool.get('account.move').browse(cr, uid, move_srch)
                        for move_item in move_brws.line_id:
                            if 'Harga Pokok Penjualan' in move_item.account_id.name and move_item.name == p['kode']:
                                p['nilai_hpp'] = move_item.debit
                        

                report.update({'id_retur_line': id_retur_line})

        reports = filter(lambda x: x.get('id_retur_line'), reports)

        if not reports :
            reports = [{'title_short': 'Laporan Program Subsidi', 'type': ['out_invoice','in_invoice','in_refund','out_refund'], 'id_retur_line':
                            [{'no': 0,
                              'type': 'NO DATA FOUND',
                              'branch_id': 'NO DATA FOUND',
                              'division': 'NO DATA FOUND',
                              'number': 'NO DATA FOUND',
                              'date': 'NO DATA FOUND',
                              'keterangan': 'NO DATA FOUND',
                              'invoice_jual_number': 'NO DATA FOUND',
                              'invoice_retur_number': 'NO DATA FOUND',
                              'invoice_jual_date': 'NO DATA FOUND',
                              'invoice_retur_date': 'NO DATA FOUND',
                              'customer': 'NO DATA FOUND',
                              'kode': 'NO DATA FOUND',
                              'deskripsi': 'NO DATA FOUND',
                              'warna': 'NO DATA FOUND',
                              'engine_number': 'NO DATA FOUND',
                              'chassis_number': 'NO DATA FOUND',
                              'ois_number': 'NO DATA FOUND',
                              'payment_number': 'NO DATA FOUND',
                              'payment_date': 'NO DATA FOUND',
                              'payment_allocation': 0,
                              'saldo':0,
                              'aging':'NO DATA FOUND',
                              'price_unit': 0,
                              'price_bbn': 0,
                              'discount_total': 0,
                              'price_subtotal': 0,
                              'product_qty': 0,
                              'jumlah': 0,
                              'dpp': 0,
                              'ppn': 0,
                              'sales': 0,
                              'biaya_retur': 0,
                              'discount_konsumen': 0,
                              'discount_dealer': 0,
                              'discount_finco': 0,
                              'discount_md': 0,
                              'discount_ahm': 0,
                              'nilai_hpp': 0,
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
        super(dym_report_retur_penjualan_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_retur_penjualan_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_retur_jual.report_retur_penjualan'
    _inherit = 'report.abstract_report'
    _template = 'dym_retur_jual.report_retur_penjualan'
    _wrapped_report_class = dym_report_retur_penjualan_print
