from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_collecting_kpb_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_collecting_kpb_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def get_pay_array(self, cr, uid, int_trf_date='', int_trf_number='', int_trf_qty=0, collecting_lines=[]):
        res = {
            'no': 0,
            'branch_id': '',
            'number': '',
            'no_claim_md': '',
            'date': '',
            'category': '',
            'kpb_ke': '',
            'no_wo': '',
            'no_kartu': '',
            'invoice_jasa_number': '',
            'invoice_oli_number': '',
            'invoice_kompensasi_number': '',
            'state': '',
            'invoice_jasa_amount': 0,
            'invoice_oli_amount': 0,
            'invoice_kompensasi_amount': 0,
            'total': 0,
            'qty_claim': 0,
            'sisa_nrfs': 0,
            'int_trf_date': int_trf_date,
            'int_trf_number': int_trf_number,
            'int_trf_qty': int_trf_qty,
            'lines': collecting_lines,
        }
        return res
    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        trx_start_date = data['trx_start_date']
        trx_end_date = data['trx_end_date']
        option = data['option']

        title_prefix = ''
        title_short_prefix = ''
        
        if option == 'invoice':
            report_collecting_kpb = {
                'type': 'payable',
                'title': '',
                'option': option,
                'title_short': 'Laporan Collecting KPB'}

            query_start = "SELECT l.id as id_ai, " \
                "COALESCE(b.name,'') as branch_id, " \
                "obj.name as number, " \
                "obj.supplier_ref as no_claim_md, " \
                "obj.date as date, " \
                "COALESCE(l.categ,'') as category, " \
                "COALESCE(l.kpb_ke,'') as kpb_ke, " \
                "COALESCE(wo.name,'') as no_wo, " \
                "COALESCE(wo.nama_buku,'') as no_kartu, " \
                "COALESCE(invsv.number,'') as invoice_jasa_number, " \
                "COALESCE(l.jasa,0) as invoice_jasa_amount, " \
                "COALESCE(invsp.number,'') as invoice_oli_number, " \
                "COALESCE(l.oli,0) as invoice_oli_amount, " \
                "COALESCE(invcol.number,'') as invoice_kompensasi_number, " \
                "COALESCE(l.kompensasi,0) as invoice_kompensasi_amount, " \
                "COALESCE(l.jasa,0)+COALESCE(l.oli,0)+COALESCE(l.kompensasi,0) as total, " \
                "obj.state as state " \
                "FROM " \
                "dym_collecting_kpb_line l " \
                "INNER JOIN collect_line_wo_rel col_wo ON col_wo.collect_line_id = l.id " \
                "LEFT JOIN dym_work_order wo ON col_wo.wo_id = wo.id " \
                "LEFT JOIN dym_collecting_kpb obj ON obj.id = l.collecting_id " \
                "LEFT JOIN dym_branch b ON b.id = obj.branch_id " \
                "LEFT JOIN account_invoice invsp ON invsp.origin = wo.name and invsp.number like 'NSC%' " \
                "LEFT JOIN account_invoice invsv ON invsv.origin = wo.name and invsv.number like 'NJB%' " \
                "LEFT JOIN account_invoice invcol ON invcol.origin = obj.name " \
                "where 1=1 and obj.state in ('open','done') "
        elif option == 'mutasi':
            report_collecting_kpb = {
                'type': 'payable',
                'title': '',
                'option': option,
                'title_short': 'Laporan Mutasi Oli KPB On Claim'}

            query_start = "SELECT obj.id as id_ai, " \
                "COALESCE(b.name,'') as branch_id, " \
                "obj.date as date, " \
                "obj.name as number, " \
                "obj.supplier_ref as no_claim_md " \
                "FROM " \
                "dym_collecting_kpb obj " \
                "LEFT JOIN dym_branch b ON b.id = obj.branch_id " \
                "where 1=1 and obj.state in ('open','done') "

        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        query_end=""
        if trx_start_date :
            query_end +=" AND obj.date >= '%s'" % str(trx_start_date)
        if trx_end_date :
            query_end +=" AND obj.date <= '%s'" % str(trx_end_date)
        if partner_ids :
            query_end +=" AND b.default_supplier_workshop_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        if branch_ids :
            query_end +=" AND obj.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        reports = [report_collecting_kpb]
        
        # query_order = "order by cabang"
        query_order = ""
        for report in reports:
            cr.execute(query_start + query_end + query_order)
            all_lines = cr.dictfetchall()
            id_ai = []

            if all_lines:
                if option == 'invoice':
                    p_map = map(
                        lambda x: {
                            'no': 0,      
                            'id_ai': x['id_ai'] if x['id_ai'] != None else 0,      
                            'branch_id': str(x['branch_id'].encode('ascii','ignore').decode('ascii')) if x['branch_id'] != None else '',
                            'number': str(x['number'].encode('ascii','ignore').decode('ascii')) if x['number'] != None else '',
                            'no_claim_md': str(x['no_claim_md'].encode('ascii','ignore').decode('ascii')) if x['no_claim_md'] != None else '',
                            'date': str(x['date']) if x['date'] != None else '',
                            'category': str(x['category'].encode('ascii','ignore').decode('ascii')) if x['category'] != None else '',
                            'kpb_ke': str(x['kpb_ke'].encode('ascii','ignore').decode('ascii')) if x['kpb_ke'] != None else '',
                            'no_wo': str(x['no_wo'].encode('ascii','ignore').decode('ascii')) if x['no_wo'] != None else '',
                            'no_kartu': str(x['no_kartu'].encode('ascii','ignore').decode('ascii')) if x['no_kartu'] != None else '',
                            'invoice_jasa_number': str(x['invoice_jasa_number'].encode('ascii','ignore').decode('ascii')) if x['invoice_jasa_number'] != None else '',
                            'invoice_oli_number': str(x['invoice_oli_number'].encode('ascii','ignore').decode('ascii')) if x['invoice_oli_number'] != None else '',
                            'invoice_kompensasi_number': str(x['invoice_kompensasi_number'].encode('ascii','ignore').decode('ascii')) if x['invoice_kompensasi_number'] != None else '',
                            'state': str(x['state'].encode('ascii','ignore').decode('ascii')) if x['state'] != None else '',
                            'invoice_jasa_amount': x['invoice_jasa_amount'],
                            'invoice_oli_amount': x['invoice_oli_amount'],
                            'invoice_kompensasi_amount': x['invoice_kompensasi_amount'],
                            'total': x['total'],
                            },
                           
                        all_lines)
                elif option == 'mutasi':
                    p_map = map(
                        lambda x: {
                            'no': 0,      
                            'id_ai': x['id_ai'] if x['id_ai'] != None else 0,      
                            'branch_id': str(x['branch_id'].encode('ascii','ignore').decode('ascii')) if x['branch_id'] != None else '',
                            'date': str(x['date']) if x['date'] != None else '',
                            'number': str(x['number'].encode('ascii','ignore').decode('ascii')) if x['number'] != None else '',
                            'no_claim_md': str(x['no_claim_md'].encode('ascii','ignore').decode('ascii')) if x['no_claim_md'] != None else '',
                            },
                        all_lines)
                no = 0
                per_moves = {}
                for p in p_map:
                    if p['id_ai'] not in map(
                            lambda x: x.get('id_ai', None), id_ai):
                        collecting_lines = filter(
                            lambda x: x['id_ai'] == p['id_ai'], all_lines)
                        if option == 'mutasi':
                            collecting = self.pool.get('dym.collecting.kpb').browse(cr, uid, collecting_lines[0]['id_ai'])
                            no += 1
                            p.update({
                                'no': no,
                                'qty_claim': 0,
                                'sisa_nrfs': 0,
                                'int_trf_date': '',
                                'int_trf_number': '',
                                'int_trf_qty': 0,
                                'lines': collecting_lines,
                            })
                            id_ai.append(p)
                            index = len(id_ai) - 1
                            moves = collecting.work_order_ids.mapped('picking_ids.move_lines').filtered(lambda r: r.state == 'done' and r.location_dest_id.usage == 'kpb')
                            int_trf_qty = 0
                            for move in moves:
                                for quant in move.quant_ids:
                                    move_internal = move.search([('id', 'in', quant.history_ids.ids),('id', '>', move.id),('picking_type_id.code', '=', 'internal')], order="picking_id asc")
                                    if move_internal:
                                        if move_internal not in per_moves:
                                            per_moves[move_internal] = move_internal.product_uom_qty
                                        qty_tambahan = 0
                                        if per_moves[move_internal] >= quant.qty:
                                            qty_tambahan = quant.qty
                                        else:
                                            qty_tambahan = quant.qty - per_moves[move_internal]
                                        int_trf_qty += qty_tambahan
                                        per_moves[move_internal] -= qty_tambahan
                                        if (id_ai[index]['int_trf_date'] == '' and id_ai[index]['int_trf_number'] == '' and id_ai[index]['int_trf_qty'] == 0) or (id_ai[index]['int_trf_number'] == move_internal.picking_id.name):
                                            if id_ai[index]['int_trf_number'] == move_internal.picking_id.name:
                                                id_ai[index]['int_trf_qty'] += qty_tambahan
                                            else:
                                                id_ai[index]['int_trf_date'] = move_internal.picking_id.confirm_date
                                                id_ai[index]['int_trf_number'] = move_internal.picking_id.name
                                                id_ai[index]['int_trf_qty'] = qty_tambahan
                                        else:
                                            collecting_res = self.get_pay_array(cr, uid, int_trf_date=move_internal.picking_id.confirm_date, int_trf_number=move_internal.picking_id.name, int_trf_qty=qty_tambahan, collecting_lines=collecting_lines)
                                            id_ai.append(collecting_res)
                            qty_claim = sum(moves.mapped('product_uom_qty'))
                            p.update({
                                'qty_claim': qty_claim,
                                'sisa_nrfs': qty_claim-int_trf_qty,
                            })
                        elif option == 'invoice':
                            p.update({
                                'lines': collecting_lines,
                            })
                            id_ai.append(p)
                report.update({'id_ai': id_ai})
                # report.update({'id_ai': p_map})

        reports = filter(lambda x: x.get('id_ai'), reports)

        if not reports :
            reports = [{'title_short': 'Laporan Collecting KPB', 'type': ['out_invoice','in_invoice','in_refund','out_refund'], 'id_ai':
                            [{'no': 0,
                              'branch_id': 'NO DATA FOUND',
                              'number': 'NO DATA FOUND',
                              'no_claim_md': 'NO DATA FOUND',
                              'date': 'NO DATA FOUND',
                              'category': 'NO DATA FOUND',
                              'kpb_ke': 'NO DATA FOUND',
                              'no_wo': 'NO DATA FOUND',
                              'no_kartu': 'NO DATA FOUND',
                              'invoice_jasa_number': 'NO DATA FOUND',
                              'invoice_oli_number': 'NO DATA FOUND',
                              'invoice_kompensasi_number': 'NO DATA FOUND',
                              'state': 'NO DATA FOUND',
                              'invoice_jasa_amount': 0,
                              'invoice_oli_amount': 0,
                              'invoice_kompensasi_amount': 0,
                              'total': 0,
                              'qty_claim': 0,
                              'sisa_nrfs': 0,
                              'int_trf_date': '',
                              'int_trf_number': '',
                              'int_trf_qty': 0,
                              }], 'title': '', 'option': option}]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_collecting_kpb_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_collecting_kpb_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_collecting_kpb.report_collecting_kpb'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_collecting_kpb.report_collecting_kpb'
    _wrapped_report_class = dym_report_collecting_kpb_print
