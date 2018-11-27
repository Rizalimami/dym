from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_monitoring_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_monitoring_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        branch_status = False
        detail_tipe = data['detail_tipe']

        title_prefix = ''
        title_short_prefix = ''
        
        report_monitoring = {
            'detail_tipe': detail_tipe,
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Monitoring')}
        if detail_tipe == False:
            query_start = "SELECT 0 as no, "\
                "po.date_order as tgl_po, " \
                "po.id as id_po, " \
                "po.name as no_po, " \
                "pol.product_qty as qty_po, " \
                "po.amount_total as amount_po, " \
                "pr.id as id_pr, " \
                "pr.date as tgl_pr, " \
                "pr.name as no_pr, " \
                "prl.product_qty as qty_pr, " \
                "b.id as branch_id, " \
                "b.name as branch_name, " \
                "po.division as division, " \
                "po.state as status " \
                "FROM " \
                "purchase_order po " \
                "LEFT JOIN (SELECT order_id, sum(product_qty) as product_qty FROM purchase_order_line group by order_id) pol ON pol.order_id = po.id " \
                "LEFT JOIN purchase_requisition pr ON po.requisition_id = pr.id " \
                "LEFT JOIN (SELECT requisition_id, sum(product_qty) as product_qty FROM purchase_requisition_line group by requisition_id) prl ON prl.requisition_id = pr.id " \
                "LEFT JOIN dym_branch b ON po.branch_id = b.id " \
                "WHERE 1=1 "
        else:
            query_start = "SELECT 0 as no, "\
                "po.date_order as tgl_po, " \
                "po.id as id_po, " \
                "po.name as no_po, " \
                "pol.product_qty as qty_po, " \
                "0 as amount_po, " \
                "pol.id as id_pol, " \
                "t.name as tipe_product, " \
                "p.id as product_id, " \
                "p.default_code as internal_reference, " \
                "pr.id as id_pr, " \
                "pr.date as tgl_pr, " \
                "pr.name as no_pr, " \
                "prl.product_qty as qty_pr, " \
                "b.id as branch_id, " \
                "b.name as branch_name, " \
                "pav.code as warna, "\
                "po.division as division, " \
                "po.state as status " \
                "FROM " \
                "purchase_order_line pol " \
                "LEFT JOIN purchase_order po ON po.id = pol.order_id " \
                "LEFT JOIN purchase_requisition pr ON po.requisition_id = pr.id " \
                "LEFT JOIN purchase_requisition_line prl ON prl.requisition_id = pr.id and prl.product_id = pol.product_id " \
                "LEFT JOIN dym_branch b ON po.branch_id = b.id " \
                "LEFT JOIN product_product p ON pol.product_id = p.id " \
                "LEFT JOIN product_template t ON p.product_tmpl_id = t.id " \
                "LEFT JOIN product_attribute_value_product_product_rel pavpp on pavpp.prod_id = p.id "\
                "LEFT JOIN product_attribute_value pav on pav.id = pavpp.att_id "\
                "WHERE 1=1 "

        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        division = data['division']
        branch_ids = data['branch_ids']
        start_date_pr = data['start_date_pr']
        end_date_pr = data['end_date_pr']
        pr_ids = data['pr_ids']
        start_date_po = data['start_date_po']
        end_date_po = data['end_date_po']
        po_ids = data['po_ids']

        query_end=""
        if division :
            query_end +=" AND po.division = '%s' " % str(division)
        if start_date_pr :
            query_end +=" AND pr.date >= '%s' " % str(start_date_pr)
        if end_date_pr :
            query_end +=" AND pr.date <= '%s' " % str(end_date_pr)
        if start_date_po :
            query_end +=" AND po.date_order >= '%s' " % str(start_date_po)
        if end_date_po :
            query_end +=" AND po.date_order <= '%s' " % str(end_date_po)
        if pr_ids :
            query_end +=" AND pr.id in %s " % str(
                tuple(pr_ids)).replace(',)', ')')
        if po_ids :
            query_end +=" AND po.id in %s " % str(
                tuple(po_ids)).replace(',)', ')')
        if branch_ids :
            query_end +=" AND b.id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
        reports = [report_monitoring]

        # query_order = "order by cabang"
        if detail_tipe == False:
            query_order = " group by po.date_order, po.id, po.name, pol.product_qty, po.amount_total, pr.id, pr.date, pr.name, prl.product_qty, b.id, b.name, po.division"
        else:
            query_order = " group by po.date_order, po.id, po.name, pol.product_qty, amount_po, pr.id, pr.date, pr.name, prl.product_qty, b.id, b.name, po.division, pol.id, t.name, p.id, p.default_code, pav.code"
        for report in reports:
            cr.execute(query_start + query_end + query_order)
            all_lines = cr.dictfetchall()
            detail_lines = []

            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': 0,      
                        'id_po': x['id_po'],
                        'id_pol': x['id_pol'] if 'id_pol' in x else '',
                        'product_id': str(x['product_id']) if 'product_id' in x and x['product_id'] != None else '',
                        'branch_name': str(x['branch_name']) if x['branch_name'] != None else '',
                        'tipe_product': str(x['tipe_product']) if 'tipe_product' in  x and x['tipe_product'] != None else '',
                        'internal_reference': str(x['internal_reference']) if 'internal_reference' in x and x['internal_reference'] != None else '',
                        'division': str(x['division']) if x['division'] != None else '',
                        'status': str(x['status']) if x['status'] != None else '',
                        'warna': str(x['warna']) if 'warna' in x and x['warna'] != None else '',
                        'tgl_po': str(x['tgl_po']) if x['tgl_po'] != None else '',
                        'tgl_pr': str(x['tgl_pr']) if x['tgl_pr'] != None else '',
                        # 'tgl_bpb': str(x['tgl_bpb']) if x['tgl_bpb'] != None else '',
                        # 'tgl_inv': str(x['tgl_inv']) if x['tgl_inv'] != None else '',
                        # 'tgl_consol': str(x['tgl_consol']) if x['tgl_consol'] != None else '',
                        # 'tgl_pay': str(x['tgl_pay']) if x['tgl_pay'] != None else '',

                        'no_po': str(x['no_po']) if x['no_po'] != None else '',
                        'no_pr': str(x['no_pr']) if x['no_pr'] != None else '',
                        # 'no_sugor': str(x['no_sugor']) if x['no_sugor'] != None else '',
                        # 'no_bpb': str(x['no_bpb']) if x['no_bpb'] != None else '',
                        # 'no_inv': str(x['no_inv']) if x['no_inv'] != None else '',
                        # 'no_consol': str(x['no_consol']) if x['no_consol'] != None else '',
                        # 'no_pay': str(x['no_pay']) if x['no_pay'] != None else '',

                        'qty_po': x['qty_po'] if x['qty_po'] != None else 0,
                        'qty_pr': x['qty_pr'] if x['qty_pr'] != None else 0,
                        # 'qty_sugor': x['qty_sugor'] if x['qty_sugor'] != None else 0,
                        # 'qty_bpb': x['qty_bpb'] if x['qty_bpb'] != None else 0,
                        # 'qty_inv': x['qty_inv'] if x['qty_inv'] != None else 0,
                        # 'qty_consol': x['qty_consol'] if x['qty_consol'] != None else 0,

                        'amount_po': x['amount_po'] if x['amount_po'] != None else 0,
                        # 'amount_inv': x['amount_inv'] if x['amount_inv'] != None else 0,
                        # 'amount_consol': x['amount_consol'] if x['amount_consol'] != None else 0,
                        # 'amount_pay': x['amount_pay'] if x['amount_pay'] != None else 0,
                    },
                    all_lines)
                p_map = sorted(p_map, key=lambda k: k['no_po'])
                if detail_tipe == False:
                    for p in p_map:
                        add_line = []
                        if p['id_po'] not in map(lambda x: x.get('id_po', None), detail_lines):
                            records = filter(lambda x: x['id_po'] == p['id_po'], all_lines)
                            add_line.append({
                                'no': 0,
                                'tgl_bpb': '',
                                'tgl_inv': '',
                                'tgl_consol': '',
                                'tgl_pay': '',
                                'no_sugor': '',
                                'no_bpb': '',
                                'no_inv': '',
                                'no_consol': '',
                                'no_pay': '',
                                'qty_sugor': 0,
                                'qty_bpb': 0,
                                'qty_inv': 0,
                                'qty_consol': 0,
                                'amount_inv': 0,
                                'amount_consol': 0,
                                'amount_pay': 0,
                                'branch_name': p['branch_name'],
                                'division': p['division'],
                                'status': p['status'],
                                'tgl_po': p['tgl_po'],
                                'tgl_pr': p['tgl_pr'],
                                'no_pr': p['no_pr'],
                                'no_po': p['no_po'],
                                'qty_po': p['qty_po'],
                                'qty_pr': p['qty_pr'],
                                'amount_po': p['amount_po'],
                            })
                            po = self.pool.get('purchase.order').browse(cr, uid, p['id_po'])
                            index = 0
                            consolidate_ids = self.pool.get('consolidate.invoice').search(cr, uid, [('invoice_id','in',po.invoice_ids.ids),('state','=','done')])
                            consolidate = self.pool.get('consolidate.invoice').browse(cr, uid, consolidate_ids)
                            invoice_res = {}
                            packing_res = {}
                            consol_index = 0
                            for consol in consolidate.sorted(key=lambda r: r.invoice_id):
                                qty_consol_invoice_picking = 0
                                amount_consol = 0 
                                amount_invoice = 0 
                                if consol.asset == False:
                                    packing_id = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id','=',consol.picking_id.id),('state','=','posted')]) 
                                    pack = self.pool.get('dym.stock.packing').browse(cr, uid, packing_id)
                                if consol.asset == True:
                                    pack = consol.receive_id
                                for line in consol.consolidate_line:
                                    if line.purchase_line_id.id in po.order_line.ids:
                                        qty_consol_invoice_picking += line.product_qty
                                        amount_consol += line.product_qty*line.price_unit
                                        inv_line_id = self.pool.get('account.invoice.line').search(cr, uid,
                                                                    [('purchase_line_id','=',line.purchase_line_id.id),
                                                                    ('invoice_id','=',consol.invoice_id.id),
                                                                    ], limit=1)
                                        if inv_line_id :
                                            inv_line = self.pool.get('account.invoice.line').browse(cr, uid, inv_line_id)
                                            total_discount = (inv_line.discount_amount + inv_line.discount_cash + inv_line.discount_lain + inv_line.discount_program) * line.product_qty / inv_line.quantity
                                            price = (inv_line.price_unit * line.product_qty) - total_discount
                                            taxes = inv_line.invoice_line_tax_id.compute_all(price, 1, product=inv_line.product_id, partner=inv_line.invoice_id.partner_id)
                                            amount_invoice += taxes['total_included']
                                            invoice_res[inv_line] = invoice_res.get(inv_line,0) + line.product_qty
                                        if consol.asset == False:
                                            packing_res[consol.picking_id] = packing_res.get(consol.picking_id,0) + line.product_qty
                                        if consol.asset == True:
                                            packing_res[consol.receive_id] = packing_res.get(consol.receive_id,0) + line.product_qty
                                if qty_consol_invoice_picking <= 0:
                                    continue
                                consol_index += 1
                                if len(add_line) - 1 < index:
                                    add_line.append({
                                        'no': 0,
                                        'tgl_bpb': '',
                                        'tgl_inv': '',
                                        'tgl_consol': '',
                                        'tgl_pay': '',
                                        'no_sugor': '',
                                        'no_bpb': '',
                                        'no_inv': '',
                                        'no_consol': '',
                                        'no_pay': '',
                                        'qty_sugor': 0,
                                        'qty_bpb': 0,
                                        'qty_inv': 0,
                                        'qty_consol': 0,
                                        'amount_inv': 0,
                                        'amount_consol': 0,
                                        'amount_pay': 0,
                                        'branch_name': p['branch_name'],
                                        'division': p['division'],
                                        'status': p['status'],
                                        'tgl_po': p['tgl_po'],
                                        'tgl_pr': p['tgl_pr'],
                                        'no_pr': p['no_pr'],
                                        'no_po': p['no_po'],
                                        'qty_po': 0,
                                        'qty_pr': 0,
                                        'amount_po': 0,
                                    })
                                    add_line[index].update({'lines':records})
                                add_line[index]['id_consol'] = consol.id
                                add_line[index]['tgl_consol'] = consol.date
                                add_line[index]['no_consol'] = consol.name
                                add_line[index]['qty_consol'] = qty_consol_invoice_picking
                                add_line[index]['amount_consol'] = amount_consol
                                add_line[index]['id_inv'] = consol.invoice_id.id
                                add_line[index]['tgl_inv'] = consol.invoice_id.date_invoice
                                add_line[index]['no_inv'] = consol.invoice_id.number
                                add_line[index]['qty_inv'] = qty_consol_invoice_picking
                                add_line[index]['amount_inv'] = amount_invoice
                                add_line[index]['id_bpb'] = pack.id
                                add_line[index]['tgl_bpb'] = pack.date
                                add_line[index]['no_bpb'] = pack.name
                                add_line[index]['qty_bpb'] = qty_consol_invoice_picking
                                index += 1
                            index = consol_index
                            invoice = po.invoice_ids.filtered(lambda r: r.state in ['open','paid'])
                            for inv in invoice:
                                qty_inv = 0
                                amount_invoice = 0
                                for line in inv.invoice_line:
                                    if line in invoice_res:
                                        line_qty = line.quantity - invoice_res[line]
                                    else:
                                        line_qty = line.quantity
                                    qty_inv += line_qty
                                    total_discount = (line.discount_amount + line.discount_cash + line.discount_lain + line.discount_program) * line_qty / line.quantity
                                    price = (line.price_unit * line_qty) - total_discount
                                    taxes = line.invoice_line_tax_id.compute_all(price, 1, product=line.product_id, partner=line.invoice_id.partner_id)
                                    amount_invoice += taxes['total_included']
                                if qty_inv <= 0:
                                    continue
                                if len(add_line) - 1 < index:
                                    add_line.append({
                                        'no': 0,
                                        'tgl_bpb': '',
                                        'tgl_inv': '',
                                        'tgl_consol': '',
                                        'tgl_pay': '',
                                        'no_sugor': '',
                                        'no_bpb': '',
                                        'no_inv': '',
                                        'no_consol': '',
                                        'no_pay': '',
                                        'qty_sugor': 0,
                                        'qty_bpb': 0,
                                        'qty_inv': 0,
                                        'qty_consol': 0,
                                        'amount_inv': 0,
                                        'amount_consol': 0,
                                        'amount_pay': 0,
                                        'branch_name': p['branch_name'],
                                        'division': p['division'],
                                        'status': p['status'],
                                        'tgl_po': p['tgl_po'],
                                        'tgl_pr': p['tgl_pr'],
                                        'no_pr': p['no_pr'],
                                        'no_po': p['no_po'],
                                        'qty_po': 0,
                                        'qty_pr': 0,
                                        'amount_po': 0,
                                    })
                                    add_line[index].update({'lines':records})
                                add_line[index]['id_inv'] = inv.id
                                add_line[index]['tgl_inv'] = inv.date_invoice
                                add_line[index]['no_inv'] = inv.number
                                add_line[index]['qty_inv'] = qty_inv
                                add_line[index]['amount_inv'] = amount_invoice
                                index += 1
                            index = 0
                            for sugor in po.sugor_ids:
                                qty_sugor = sum(line.suggestion_order_final for line in sugor.filtered(lambda r: r.check_order == True and r.suggestion_order_final > 0))
                                if len(add_line) - 1 < index:
                                    add_line.append({
                                        'no': 0,
                                        'tgl_bpb': '',
                                        'tgl_inv': '',
                                        'tgl_consol': '',
                                        'tgl_pay': '',
                                        'no_sugor': '',
                                        'no_bpb': '',
                                        'no_inv': '',
                                        'no_consol': '',
                                        'no_pay': '',
                                        'qty_sugor': 0,
                                        'qty_bpb': 0,
                                        'qty_inv': 0,
                                        'qty_consol': 0,
                                        'amount_inv': 0,
                                        'amount_consol': 0,
                                        'amount_pay': 0,
                                        'branch_name': p['branch_name'],
                                        'division': p['division'],
                                        'status': p['status'],
                                        'tgl_po': p['tgl_po'],
                                        'tgl_pr': p['tgl_pr'],
                                        'no_pr': p['no_pr'],
                                        'no_po': p['no_po'],
                                        'qty_po': 0,
                                        'qty_pr': 0,
                                        'amount_po': 0,
                                    })
                                    add_line[index].update({'lines':records})
                                add_line[index]['id_sugor'] = sugor.id
                                add_line[index]['no_sugor'] = sugor.name
                                add_line[index]['qty_sugor'] = qty_sugor
                                index += 1
                            index = consol_index
                            if po.asset == False and po.prepaid == False:
                                packing_ids = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id','in',po.picking_ids.ids),('state','=','posted')]) 
                                packing = self.pool.get('dym.stock.packing').browse(cr, uid, packing_ids) 
                            else:
                                receive_ids = self.pool.get('dym.receive.asset').search(cr, uid, [('purchase_id','in',po.id),('state','=','done')]) 
                                packing = self.pool.get('dym.receive.asset').browse(cr, uid, receive_ids) 
                            for pack in packing:
                                if po.asset == False and po.prepaid == False:
                                    pack_res = pack.picking_id
                                    qty_bpb = sum(line.quantity for line in pack.packing_line)
                                else:
                                    pack_res = pack
                                    qty_bpb = sum(line.quantity for line in pack.receive_line_ids)
                                if pack_res in packing_res:
                                    qty_bpb = qty_bpb - packing_res[pack_res]
                                else:
                                    qty_bpb = qty_bpb             
                                if qty_bpb <= 0:
                                    continue            
                                if len(add_line) - 1 < index:
                                    add_line.append({
                                        'no': 0,
                                        'tgl_bpb': '',
                                        'tgl_inv': '',
                                        'tgl_consol': '',
                                        'tgl_pay': '',
                                        'no_sugor': '',
                                        'no_bpb': '',
                                        'no_inv': '',
                                        'no_consol': '',
                                        'no_pay': '',
                                        'qty_sugor': 0,
                                        'qty_bpb': 0,
                                        'qty_inv': 0,
                                        'qty_consol': 0,
                                        'amount_inv': 0,
                                        'amount_consol': 0,
                                        'amount_pay': 0,
                                        'branch_name': p['branch_name'],
                                        'division': p['division'],
                                        'status': p['status'],
                                        'tgl_po': p['tgl_po'],
                                        'tgl_pr': p['tgl_pr'],
                                        'no_pr': p['no_pr'],
                                        'no_po': p['no_po'],
                                        'qty_po': 0,
                                        'qty_pr': 0,
                                        'amount_po': 0,
                                    })
                                    add_line[index].update({'lines':records})
                                add_line[index]['id_bpb'] = pack.id
                                add_line[index]['tgl_bpb'] = pack.date
                                add_line[index]['no_bpb'] = pack.name
                                add_line[index]['qty_bpb'] = qty_bpb
                                index += 1
                            index = 0
                            payment = invoice.mapped('payment_ids')
                            for pay in payment:
                                if len(add_line) - 1 < index:
                                    add_line.append({
                                        'no': 0,
                                        'tgl_bpb': '',
                                        'tgl_inv': '',
                                        'tgl_consol': '',
                                        'tgl_pay': '',
                                        'no_sugor': '',
                                        'no_bpb': '',
                                        'no_inv': '',
                                        'no_consol': '',
                                        'no_pay': '',
                                        'qty_sugor': 0,
                                        'qty_bpb': 0,
                                        'qty_inv': 0,
                                        'qty_consol': 0,
                                        'amount_inv': 0,
                                        'amount_consol': 0,
                                        'amount_pay': 0,
                                        'branch_name': p['branch_name'],
                                        'division': p['division'],
                                        'status': p['status'],
                                        'tgl_po': p['tgl_po'],
                                        'tgl_pr': p['tgl_pr'],
                                        'no_pr': p['no_pr'],
                                        'no_po': p['no_po'],
                                        'qty_po': 0,
                                        'qty_pr': 0,
                                        'amount_po': 0,
                                    })
                                    add_line[index].update({'lines':records})
                                add_line[index]['id_pay'] = pay.id
                                add_line[index]['tgl_pay'] = pay.date
                                add_line[index]['no_pay'] = pay.move_id.name
                                add_line[index]['amount_pay'] = pay.debit or pay.credit
                                index += 1
                            detail_lines += add_line
                else:
                    cur_obj = self.pool.get('res.currency')
                    tax_obj = self.pool.get('account.tax')
                    for p in p_map:
                        add_line = []
                        if p['id_pol'] not in map(lambda x: x.get('id_pol', None), detail_lines):
                            records = filter(lambda x: x['id_pol'] == p['id_pol'], all_lines)
                            pol = self.pool.get('purchase.order.line').browse(cr, uid, p['id_pol'])
                            product = self.pool.get('product.product').browse(cr, uid, p['product_id'])
                            amount_po = 0
                            # taxes = tax_obj.compute_all(cr, uid, pol.taxes_id, pol.price_unit, pol.product_qty, pol.product_id, pol.order_id.partner_id)
                            # cur = pol.order_id.pricelist_id.currency_id
                            # amount_po = taxes['total_included']
                            # if cur:
                            #     amount_po = cur_obj.round(cr, uid, cur, taxes['total_included'])
                            add_line.append({
                                'no': 0,
                                'tgl_bpb': '',
                                'tgl_inv': '',
                                'tgl_consol': '',
                                'tgl_pay': '',
                                'no_sugor': '',
                                'no_bpb': '',
                                'no_inv': '',
                                'no_consol': '',
                                'no_pay': '',
                                'qty_sugor': 0,
                                'qty_bpb': 0,
                                'qty_inv': 0,
                                'qty_consol': 0,
                                'amount_inv': 0,
                                'amount_consol': 0,
                                'amount_pay': 0,
                                'branch_name': p['branch_name'],
                                'division': p['division'],
                                'status': p['status'],
                                'tgl_po': p['tgl_po'],
                                'tgl_pr': p['tgl_pr'],
                                'no_pr': p['no_pr'],
                                'no_po': p['no_po'],
                                'qty_po': p['qty_po'],
                                'qty_pr': p['qty_pr'],
                                'amount_po': amount_po,
                                'tipe_product': p['tipe_product'],
                                'internal_reference': p['internal_reference'],
                                'warna': p['warna'],
                            })
                            index = 0
                            consolidate_ids = self.pool.get('consolidate.invoice.line').search(cr, uid, ['|',('move_id.purchase_line_id','=',pol.id),('receive_line_id.purchase_line_id','=',pol.id),('consolidate_id.state','=','done')])
                            consolidate = self.pool.get('consolidate.invoice.line').browse(cr, uid, consolidate_ids)
                            # invoice_res = {}
                            # packing_res = {}
                            # consol_index = 0
                            qty_consol_invoice_picking = 0
                            for consol in consolidate.sorted(key=lambda r: r.consolidate_id.invoice_id):
                                # qty_consol_invoice_picking = 0
                                # amount_consol = 0 
                                # amount_invoice = 0 
                                # if consol.consolidate_id.asset == False:
                                #     packing_id = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id','=',consol.consolidate_id.picking_id.id),('state','=','posted')]) 
                                #     pack = self.pool.get('dym.stock.packing').browse(cr, uid, packing_id)
                                # if consol.consolidate_id.asset == True:
                                #     pack = consol.consolidate_id.receive_id
                                qty_consol_invoice_picking += consol.product_qty
                                # amount_consol += consol.product_qty*consol.price_unit
                                # inv_line_id = self.pool.get('account.invoice.line').search(cr, uid,
                                #                             [('purchase_line_id','=',consol.purchase_line_id.id),
                                #                             ('invoice_id','=',consol.consolidate_id.invoice_id.id),
                                #                             ], limit=1)
                                # if inv_line_id :
                                #     inv_line = self.pool.get('account.invoice.line').browse(cr, uid, inv_line_id)
                                #     total_discount = (inv_line.discount_amount + inv_line.discount_cash + inv_line.discount_lain + inv_line.discount_program) * consol.product_qty / inv_line.quantity
                                #     price = (inv_line.price_unit * consol.product_qty) - total_discount
                                #     taxes = inv_line.invoice_line_tax_id.compute_all(price, 1, product=inv_line.product_id, partner=inv_line.invoice_id.partner_id)
                                #     amount_invoice += taxes['total_included']
                                #     invoice_res[inv_line] = invoice_res.get(inv_line,0) + consol.product_qty
                                # if consol.consolidate_id.asset == False:
                                #     packing_res[consol.move_id] = packing_res.get(consol.move_id,0) + consol.product_qty
                                # if consol.consolidate_id.asset == True:
                                #     packing_res[consol.receive_line_id] = packing_res.get(consol.receive_line_id,0) + consol.product_qty
                                # if qty_consol_invoice_picking <= 0:
                                #     continue
                                # consol_index += 1
                                # if len(add_line) - 1 < index:
                                #     add_line.append({
                                #         'no': 0,
                                #         'tgl_bpb': '',
                                #         'tgl_inv': '',
                                #         'tgl_consol': '',
                                #         'tgl_pay': '',
                                #         'no_sugor': '',
                                #         'no_bpb': '',
                                #         'no_inv': '',
                                #         'no_consol': '',
                                #         'no_pay': '',
                                #         'qty_sugor': 0,
                                #         'qty_bpb': 0,
                                #         'qty_inv': 0,
                                #         'qty_consol': 0,
                                #         'amount_inv': 0,
                                #         'amount_consol': 0,
                                #         'amount_pay': 0,
                                #         'branch_name': p['branch_name'],
                                #         'division': p['division'],
                                #         'tgl_po': p['tgl_po'],
                                #         'tgl_pr': p['tgl_pr'],
                                #         'no_pr': p['no_pr'],
                                #         'no_po': p['no_po'],
                                #         'qty_po': 0,
                                #         'qty_pr': 0,
                                #         'amount_po': 0,
                                #         'tipe_product': p['tipe_product'],
                                #         'internal_reference': p['internal_reference'],
                                #         'warna': p['warna'],
                                #     })
                                #     add_line[index].update({'lines':records})
                                # add_line[index]['id_consol'] = consol.consolidate_id.id
                                # add_line[index]['tgl_consol'] = consol.consolidate_id.date
                                # add_line[index]['no_consol'] = consol.consolidate_id.name
                                # add_line[index]['qty_consol'] = qty_consol_invoice_picking
                                # add_line[index]['amount_consol'] = amount_consol
                                # add_line[index]['id_inv'] = consol.consolidate_id.invoice_id.id
                                # add_line[index]['tgl_inv'] = consol.consolidate_id.invoice_id.date_invoice
                                # add_line[index]['no_inv'] = consol.consolidate_id.invoice_id.number
                                # add_line[index]['qty_inv'] = qty_consol_invoice_picking
                                # add_line[index]['amount_inv'] = amount_invoice
                                # add_line[index]['id_bpb'] = pack.id
                                # add_line[index]['tgl_bpb'] = pack.date
                                # add_line[index]['no_bpb'] = pack.name
                                # add_line[index]['qty_bpb'] = qty_consol_invoice_picking
                                # index += 1
                            add_line[index]['qty_consol'] = qty_consol_invoice_picking
                            # index = consol_index
                            invoice = pol.order_id.invoice_ids.mapped('invoice_line').filtered(lambda r: r.invoice_id.state in ['open','paid'] and r.purchase_line_id.id == pol.id)
                            qty_inv = 0
                            for inv in invoice:
                                qty_inv += inv.quantity
                                # qty_inv = 0
                                # amount_invoice = 0
                                # if inv in invoice_res:
                                #     line_qty = inv.quantity - invoice_res[inv]
                                # else:
                                #     line_qty = inv.quantity
                                # qty_inv += line_qty
                                # total_discount = (inv.discount_amount + inv.discount_cash + inv.discount_lain + inv.discount_program) * line_qty / inv.quantity
                                # price = (inv.price_unit * line_qty) - total_discount
                                # taxes = inv.invoice_line_tax_id.compute_all(price, 1, product=inv.product_id, partner=inv.invoice_id.partner_id)
                                # amount_invoice += taxes['total_included']
                                # if qty_inv <= 0:
                                #     continue
                                # if len(add_line) - 1 < index:
                                #     add_line.append({
                                #         'no': 0,
                                #         'tgl_bpb': '',
                                #         'tgl_inv': '',
                                #         'tgl_consol': '',
                                #         'tgl_pay': '',
                                #         'no_sugor': '',
                                #         'no_bpb': '',
                                #         'no_inv': '',
                                #         'no_consol': '',
                                #         'no_pay': '',
                                #         'qty_sugor': 0,
                                #         'qty_bpb': 0,
                                #         'qty_inv': 0,
                                #         'qty_consol': 0,
                                #         'amount_inv': 0,
                                #         'amount_consol': 0,
                                #         'amount_pay': 0,
                                #         'branch_name': p['branch_name'],
                                #         'division': p['division'],
                                #         'tgl_po': p['tgl_po'],
                                #         'tgl_pr': p['tgl_pr'],
                                #         'no_pr': p['no_pr'],
                                #         'no_po': p['no_po'],
                                #         'qty_po': 0,
                                #         'qty_pr': 0,
                                #         'amount_po': 0,
                                #         'tipe_product': p['tipe_product'],
                                #         'internal_reference': p['internal_reference'],
                                #         'warna': p['warna'],
                                #     })
                                #     add_line[index].update({'lines':records})
                                # add_line[index]['id_inv'] = inv.invoice_id.id
                                # add_line[index]['tgl_inv'] = inv.invoice_id.date_invoice
                                # add_line[index]['no_inv'] = inv.invoice_id.number
                                # add_line[index]['qty_inv'] = qty_inv
                                # add_line[index]['amount_inv'] = amount_invoice
                                # index += 1
                            add_line[index]['qty_inv'] = qty_inv
                            # index = 0
                            # for sugor in pol.order_id.sugor_ids:
                            #     qty_sugor = sum(line.suggestion_order_final for line in sugor.filtered(lambda r: r.check_order == True and r.suggestion_order_final > 0))
                            #     if len(add_line) - 1 < index:
                            #         add_line.append({
                            #             'no': 0,
                            #             'tgl_bpb': '',
                            #             'tgl_inv': '',
                            #             'tgl_consol': '',
                            #             'tgl_pay': '',
                            #             'no_sugor': '',
                            #             'no_bpb': '',
                            #             'no_inv': '',
                            #             'no_consol': '',
                            #             'no_pay': '',
                            #             'qty_sugor': 0,
                            #             'qty_bpb': 0,
                            #             'qty_inv': 0,
                            #             'qty_consol': 0,
                            #             'amount_inv': 0,
                            #             'amount_consol': 0,
                            #             'amount_pay': 0,
                            #             'branch_name': p['branch_name'],
                            #             'division': p['division'],
                            #             'tgl_po': p['tgl_po'],
                            #             'tgl_pr': p['tgl_pr'],
                            #             'no_pr': p['no_pr'],
                            #             'no_po': p['no_po'],
                            #             'qty_po': 0,
                            #             'qty_pr': 0,
                            #             'amount_po': 0,
                            #             'tipe_product': p['tipe_product'],
                            #             'internal_reference': p['internal_reference'],
                            #             'warna': p['warna'],
                            #         })
                            #         add_line[index].update({'lines':records})
                            #     add_line[index]['id_sugor'] = sugor.id
                            #     add_line[index]['no_sugor'] = sugor.name
                            #     add_line[index]['qty_sugor'] = qty_sugor
                            #     index += 1
                            # index = consol_index
                            if pol.order_id.asset == False and pol.order_id.prepaid == False:
                                move_ids = self.pool.get('stock.move').search(cr, uid, [('purchase_line_id','=',pol.id),('state','=','done')]) 
                                moves = self.pool.get('stock.move').browse(cr, uid, move_ids) 
                                # packing_ids = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id','in',pol.order_id.picking_ids.ids),('state','=','posted')]) 
                                # packing = self.pool.get('dym.stock.packing').browse(cr, uid, packing_ids) 
                            else:
                                receive_ids = self.pool.get('dym.receive.asset.line').search(cr, uid, [('purchase_line_id','=',pol.id),('state','=','done')]) 
                                moves = self.pool.get('dym.receive.asset.line').browse(cr, uid, receive_ids) 
                            qty_bpb = 0
                            for move in moves:
                                if pol.order_id.asset == False and pol.order_id.prepaid == False:
                                    packing_ids = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id','=',move.picking_id.id),('state','=','posted')]) 
                                    pack = self.pool.get('dym.stock.packing').browse(cr, uid, packing_ids) 
                                    qty_bpb += move.product_qty
                                else:
                                    pack = move.receive_id
                                    qty_bpb += move.quantity
                            #     if move in packing_res:
                            #         qty_bpb = qty_bpb - packing_res[move]
                            #     else:
                            #         qty_bpb = qty_bpb             
                            #     if qty_bpb <= 0:
                            #         continue            
                            #     if len(add_line) - 1 < index:
                            #         add_line.append({
                            #             'no': 0,
                            #             'tgl_bpb': '',
                            #             'tgl_inv': '',
                            #             'tgl_consol': '',
                            #             'tgl_pay': '',
                            #             'no_sugor': '',
                            #             'no_bpb': '',
                            #             'no_inv': '',
                            #             'no_consol': '',
                            #             'no_pay': '',
                            #             'qty_sugor': 0,
                            #             'qty_bpb': 0,
                            #             'qty_inv': 0,
                            #             'qty_consol': 0,
                            #             'amount_inv': 0,
                            #             'amount_consol': 0,
                            #             'amount_pay': 0,
                            #             'branch_name': p['branch_name'],
                            #             'division': p['division'],
                            #             'tgl_po': p['tgl_po'],
                            #             'tgl_pr': p['tgl_pr'],
                            #             'no_pr': p['no_pr'],
                            #             'no_po': p['no_po'],
                            #             'qty_po': 0,
                            #             'qty_pr': 0,
                            #             'amount_po': 0,
                            #             'tipe_product': p['tipe_product'],
                            #             'internal_reference': p['internal_reference'],
                            #             'warna': p['warna'],
                            #         })
                            #         add_line[index].update({'lines':records})
                            #     add_line[index]['id_bpb'] = pack.id
                            #     add_line[index]['tgl_bpb'] = pack.date
                            #     add_line[index]['no_bpb'] = pack.name
                            #     add_line[index]['qty_bpb'] = qty_bpb
                            #     index += 1
                            # index = 0
                            add_line[index]['qty_bpb'] = qty_bpb
                            # payment = invoice.mapped('invoice_id').mapped('payment_ids')
                            # for pay in payment:
                            #     if len(add_line) - 1 < index:
                            #         add_line.append({
                            #             'no': 0,
                            #             'tgl_bpb': '',
                            #             'tgl_inv': '',
                            #             'tgl_consol': '',
                            #             'tgl_pay': '',
                            #             'no_sugor': '',
                            #             'no_bpb': '',
                            #             'no_inv': '',
                            #             'no_consol': '',
                            #             'no_pay': '',
                            #             'qty_sugor': 0,
                            #             'qty_bpb': 0,
                            #             'qty_inv': 0,
                            #             'qty_consol': 0,
                            #             'amount_inv': 0,
                            #             'amount_consol': 0,
                            #             'amount_pay': 0,
                            #             'branch_name': p['branch_name'],
                            #             'division': p['division'],
                            #             'tgl_po': p['tgl_po'],
                            #             'tgl_pr': p['tgl_pr'],
                            #             'no_pr': p['no_pr'],
                            #             'no_po': p['no_po'],
                            #             'qty_po': 0,
                            #             'qty_pr': 0,
                            #             'amount_po': 0,
                            #             'tipe_product': p['tipe_product'],
                            #             'internal_reference': p['internal_reference'],
                            #             'warna': p['warna'],
                            #         })
                            #         add_line[index].update({'lines':records})
                            #     add_line[index]['id_pay'] = pay.id
                            #     add_line[index]['tgl_pay'] = pay.date
                            #     add_line[index]['no_pay'] = pay.move_id.name
                            #     add_line[index]['amount_pay'] = pay.debit or pay.credit
                            #     index += 1
                            detail_lines += add_line
                report.update({'detail_lines': detail_lines})
                # report.update({'detail_lines': p_map})

        reports = filter(lambda x: x.get('detail_lines'), reports)
        
        if not reports :
            reports = [{'title_short': 'Laporan Monitoring', 
                        'detail_lines':[{
                            'no': 0,
                            'branch_name': 'NO DATA FOUND',
                            'division': 'NO DATA FOUND',
                            'status': 'NO DATA FOUND',
                            'tgl_po': 'NO DATA FOUND',
                            'tgl_pr': 'NO DATA FOUND',
                            'tgl_bpb': 'NO DATA FOUND',
                            'tgl_inv': 'NO DATA FOUND',
                            'tgl_consol': 'NO DATA FOUND',
                            'tgl_pay': 'NO DATA FOUND',
                            'no_po': 'NO DATA FOUND',
                            'no_pr': 'NO DATA FOUND',
                            'no_sugor': 'NO DATA FOUND',
                            'no_bpb': 'NO DATA FOUND',
                            'no_inv': 'NO DATA FOUND',
                            'no_consol': 'NO DATA FOUND',
                            'no_pay': 'NO DATA FOUND',
                            'qty_po': 0,
                            'qty_pr': 0,
                            'qty_sugor': 0,
                            'qty_bpb': 0,
                            'qty_inv': 0,
                            'qty_consol': 0,
                            'amount_po': 0,
                            'amount_inv': 0,
                            'amount_consol': 0,
                            'amount_pay': 0,
                            'tipe_product': 'NO DATA FOUND',
                            'internal_reference': 'NO DATA FOUND',
                            'warna': 'NO DATA FOUND',
                        }],
                        'title': ''}]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        objects=False
        super(dym_report_monitoring_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_hutan_invoice_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_monitoring.report_monitoring'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_monitoring.report_monitoring'
    _wrapped_report_class = dym_report_monitoring_print
