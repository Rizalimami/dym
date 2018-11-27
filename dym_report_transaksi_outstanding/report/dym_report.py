from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_transaksi_outstanding_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_transaksi_outstanding_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def get_pay_array(self, cr, uid, transaksi_lines=[]):
        res = {
            'no': 0,
            'branch_name': '',
            'transaksi': '',
            'no_dokumen': '',
            'status': '',
            'value': '',
            'lines': transaksi_lines,
        }
        return res
    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        branch_ids = data['branch_ids']
        #partner_ids = data['partner_ids']
        trx_start_date = data['trx_start_date']
        trx_end_date = data['trx_end_date']


        title_prefix = ''
        title_short_prefix = ''
        

        report_transaksi_outstanding = {
            'type': 'payable',
            'title': '',
            'title_short': 'Laporan Transaksi Outstanding'}

        query_start = """select b.name branch_name,'PO' transaksi,h.name no_dokumen,h.state status,amount_total "value" from purchase_order h
                        left join dym_branch b on h.branch_id = b.id
                        where  date_order  between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')') + """ and 
                        h.state not in ('done','posted','paid','cancel') and left(h.name,3) = 'POR'
                        union all
                        select  b.name branch_name,'Suplier Invoices' transaksi,h.name no_dokumen,h.state status,amount_total "value" from account_invoice h 
                        left join dym_branch b on h.branch_id = b.id
                        left join res_partner r on h.partner_id = r.id
                        where date_invoice  between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') and r.supplier = 't' 
                        union all
                        select  b.name branch_name,'Consolidate Invoices' transaksi,h.name no_dokumen,h.state status,sum(d.price_unit*product_qty) "value" from consolidate_invoice h 
                        inner join  consolidate_invoice_line d  on h.id = d.consolidate_id
                        left join dym_branch b on h.branch_id = b.id
                        where date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') group by  h.name,h.state,b.name
                        union all
                        select  b.name branch_name,'On Incoming Shipment' transaksi,h.name no_dokumen,h.state status,sum(d.price_unit*product_qty) "value" from stock_picking h 
                        inner join  stock_move d  on h.id = d.picking_id 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') and left(h.name,3)= 'OIS' group by  h.name,h.state,b.name
                        union all
                        select  b.name branch_name,'Suplier Payment' transaksi,h.number no_dokumen,h.state status,amount_total "value" from account_invoice h 
                        left join dym_branch b on h.branch_id = b.id
                        where date_invoice  between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') and left(number,3) = 'SPA'  
                        union all
                        select  b.name branch_name,'Retur Pembelian' transaksi,h.name no_dokumen,h.state status,amount_total "value" from dym_retur_beli h
                        left join dym_branch b on h.branch_id = b.id 
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') 
                        union all
                        select b.name branch_name,'Work Order' transaksi,h.name no_dokumen,h.state status,sum(product_qty*(price_unit-discount)) "value" from dym_work_order h
                        inner join dym_work_order_line d on h.id = d.work_order_id
                        left join dym_branch b on h.branch_id = b.id 
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') 
                        group by  h.name,h.state,b.name
                        union all
                        select b.name branch_name,'Sales Order' transaksi,h.name no_dokumen,h.state status,amount_total "value" from sale_order h
                        left join dym_branch b on h.branch_id = b.id 
                        where h.date_order between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') 
                        union all
                        select b.name branch_name,'Dealer Sales Memo' transaksi,h.name no_dokumen,h.state status,amount_total "value" from dealer_sale_order h
                        left join dym_branch b on h.branch_id = b.id 
                        where h.date_order between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel')
                        union all
                        select  b.name branch_name,'Customer Invoices' transaksi,coalesce(h.number,h.name) no_dokumen,h.state status,amount_total "value" from account_invoice h 
                        left join dym_branch b on h.branch_id = b.id 
                        left join res_partner r on h.partner_id = r.id  
                        where date_invoice  between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') and r.supplier = 'f' and r.customer= 't'
                        union all
                        select  b.name branch_name,'Suplier Payment' transaksi,h.number no_dokumen,h.state status,amount_total "value" from account_invoice h 
                        left join dym_branch b on h.branch_id = b.id
                        where date_invoice  between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') and left(number,3) = 'CPA'  
                        union all
                        select  b.name branch_name,'On Outgoing Shipment' transaksi,h.name no_dokumen,h.state status,sum(d.price_unit*product_qty) "value" from stock_picking h 
                        inner join  stock_move d  on h.id = d.picking_id 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') and left(h.name,3)= 'OOS' group by  h.name,h.state,b.name       
                        union all
                        select  b.name branch_name,'Delivery Note' transaksi,s.name no_dokumen,h.state status,sum(quantity) "value" from dym_stock_packing h 
                        inner join  dym_stock_packing_line d  on h.id = d.packing_id 
                        left join stock_picking s on h.picking_id = s.id 
                        left join dym_branch b on s.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') and left(s.origin,3) <>'POR' group by  s.name,h.state,b.name,s.origin                        
                        union all
                        select  b.name branch_name,'Retur Penjualan' transaksi,h.name no_dokumen,h.state status,amount_total "value" from dym_retur_jual h 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel')                       
                        union all
                        select  b.name branch_name,'Internal Transfer' transaksi,h.name no_dokumen,h.state status,sum(d.price_unit*product_qty) "value" from stock_picking h 
                        inner join  stock_move d  on h.id = d.picking_id 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') and left(h.name,3)= 'ITR' group by  h.name,h.state,b.name                       
                        union all
                        select  b.name branch_name,'Mutation Request' transaksi,h.name no_dokumen,h.state status,amount_total "value" from dym_mutation_request h 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel')                       
                        union all
                        select  b.name branch_name,'Stock Distribution' transaksi,h.name no_dokumen,h.state status,amount_total "value" from dym_stock_distribution h 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel')                      
                        union all
                        select  b.name branch_name,'Mutation Order' transaksi,h.name no_dokumen,h.state status,amount_total "value" from dym_mutation_order h 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel')                      
                        union all
                        select  b.name branch_name,'Petty Cash Out' transaksi,h.name no_dokumen,h.state status,amount "value" from dym_pettycash h 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel')                       
                        union all
                        select  b.name branch_name,'Petty Cash In' transaksi,h.name no_dokumen,h.state status,sum(d.amount) "value" from dym_pettycash_in h 
                        left join dym_pettycash_in_line d on h.id = d.pettycash_id
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """ and
                        h.state not in ('done','posted','paid','cancel') group by b.name,h.name,h.state                        
                        union all
                        select  b.name branch_name,'All Bank Transfer' transaksi,h.name no_dokumen,h.state status,amount "value" from dym_bank_transfer h 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel')                       
                        union all
                        select  b.name branch_name,'Bank In/Out' transaksi,h.number no_dokumen,h.state status,amount "value" from account_voucher h 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') and left(h.number,3) in ('TBK','TBM')                                              
                        union all
                        select  b.name branch_name,'Other Receivable' transaksi,h.number no_dokumen,h.state status,amount "value" from account_voucher h 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') and left(h.number,3) not in ('TBK','TBM','CDE')                       
                        union all
                        select  b.name branch_name,'Loan' transaksi,h.name no_dokumen,h.state status,jumlah_loan_rekla "value" from dym_loan h 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel')                        
                        union all
                        select  b.name branch_name,'Customer Deposit' transaksi,h.number no_dokumen,h.state status,amount "value" from account_voucher h 
                        left join dym_branch b on h.branch_id = b.id
                        where h.date between '"""+ str(trx_start_date) + """' and '"""+ str(trx_end_date) + """' and h.branch_id in """ + str(tuple(branch_ids)).replace(',)', ')')  + """  and
                        h.state not in ('done','posted','paid','cancel') and left(h.number,3)  in ('CDE')

  """

        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        query_end=""
        if trx_start_date :
            query_end +=" AND dwo.date >= '%s'" % str(trx_start_date)
        if trx_end_date :
            query_end +=" AND dwo.date <= '%s'" % str(trx_end_date)
        #if partner_ids :
        #    query_end +=" AND branch.default_supplier_workshop_id in %s" % str(
        #        tuple(partner_ids)).replace(',)', ')')
        if branch_ids :
            query_end +=" AND dwo.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        reports = [report_transaksi_outstanding]
        
        # query_order = "order by cabang"
        query_order = " order by 5"

        #print query_start
        for report in reports:
            cr.execute(query_start)
            all_lines = cr.dictfetchall()
            id_ai = []

            if all_lines:

                p_map = map(
                    lambda x: {
                        'no': 0,
                        'branch_name': str(x['branch_name'].encode('ascii', 'ignore').decode('ascii')) if x['branch_name'] != None else '',
                        'transaksi': str(x['transaksi'].encode('ascii', 'ignore').decode('ascii')) if x['transaksi'] != None else '',
                        'no_dokumen': str(x['no_dokumen'].encode('ascii', 'ignore').decode('ascii')) if x['no_dokumen'] != None else '',
                        'status': str(x['status'].encode('ascii', 'ignore').decode('ascii')) if x['status'] != None else '',
                        'value': x['value'] if x['value'] > 0 else 0.0,
                        },

                    all_lines)

                no = 0
                per_moves = {}
                for p in p_map:
                    transaksi_lines = filter(
                        lambda x: x['no_dokumen'] == p['no_dokumen'], all_lines)
                    p.update({
                        'lines': transaksi_lines,
                    })
                    id_ai.append(p)
                report.update({'id_ai': id_ai})

        reports = filter(lambda x: x.get('id_ai'), reports)

        if not reports :
            reports = [{'title_short': 'Laporan Transaksi Outstanding', 'id_ai':
                            [{'no': 0,
                            'branch_name': 'NO DATA FOUND',
                            'transaksi': 'NO DATA FOUND',
                            'no_dokumen': 'NO DATA FOUND',
                            'status': 'NO DATA FOUND',
                            'value': 'NO DATA FOUND',
  
                              }], 'title': ''}]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_transaksi_outstanding_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_transaksi_outstanding_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_transaksi_outstanding.report_transaksi_outstanding'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_transaksi_outstanding.report_transaksi_outstanding'
    _wrapped_report_class = dym_report_transaksi_outstanding_print
