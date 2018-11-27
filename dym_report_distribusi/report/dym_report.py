from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_distribusi_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_distribusi_print, self).__init__(
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

        title_prefix = ''
        title_short_prefix = ''
        
        report_distribusi = {
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Distribusi Sparepart')}
        query_start = "SELECT 0 as no, "\
            "po.date_order as tgl_po, " \
            "po.id as id_po, " \
            "po.name as no_po, " \
            "pot.name as type_po, " \
            "pol.product_qty as qty_po, " \
            "pol.id as id_pol, " \
            "t.name as no_sparepart, " \
            "p.id as product_id, " \
            "p.default_code as nama_sparepart, " \
            "t.description as description, " \
            "b.id as branch_id, " \
            "b.name as branch_name, " \
            "pc.name as kategori, "\
            "po.division as division " \
            "FROM " \
            "purchase_order_line pol " \
            "LEFT JOIN purchase_order po ON po.id = pol.order_id " \
            "LEFT JOIN dym_purchase_order_type pot ON pot.id = po.purchase_order_type_id " \
            "LEFT JOIN dym_branch b ON po.branch_id = b.id " \
            "LEFT JOIN product_product p ON pol.product_id = p.id " \
            "LEFT JOIN product_category pc ON pol.categ_id = pc.id " \
            "LEFT JOIN product_template t ON p.product_tmpl_id = t.id " \
            "LEFT JOIN product_attribute_value_product_product_rel pavpp on pavpp.prod_id = p.id "\
            "LEFT JOIN product_attribute_value pav on pav.id = pavpp.att_id "\
            "WHERE 1=1 "

        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        division = data['division']
        type_po = data['type_po']
        branch_ids = data['branch_ids']
        start_date_po = data['start_date_po']
        end_date_po = data['end_date_po']
        po_ids = data['po_ids']

        query_end=""
        if division :
            query_end +=" AND po.division = '%s' " % str(division)
        if type_po in ['Fix','Additional','Administratif']:
            query_end +=" AND pot.name = '%s' " % str(type_po)    
        if start_date_po :
            query_end +=" AND po.date_order >= '%s' " % str(start_date_po)
        if end_date_po :
            query_end +=" AND po.date_order <= '%s' " % str(end_date_po)
        if po_ids :
            query_end +=" AND po.id in %s " % str(
                tuple(po_ids)).replace(',)', ')')
        if branch_ids :
            query_end +=" AND b.id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
        reports = [report_distribusi]

        query_order = "order by pol.id"
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
                        'no_sparepart': str(x['no_sparepart']) if 'no_sparepart' in  x and x['no_sparepart'] != None else '',
                        'type_po': str(x['type_po']) if 'type_po' in  x and x['type_po'] != None else '',
                        'nama_sparepart': str(x['nama_sparepart']) if 'nama_sparepart' in x and x['nama_sparepart'] != None else str(x['nama_sparepart']) if 'nama_sparepart' in x and x['nama_sparepart'] != None else '',
                        'division': str(x['division']) if x['division'] != None else '',
                        'kategori': str(x['kategori']) if 'kategori' in x and x['kategori'] != None else '',
                        'tgl_po': str(x['tgl_po']) if x['tgl_po'] != None else '',
                        'no_po': str(x['no_po']) if x['no_po'] != None else '',
                        'qty_po': x['qty_po'] if x['qty_po'] != None else 0,
                    },
                    all_lines)
                no = 0
                for p in p_map:
                    if p['id_pol'] not in map(lambda x: x.get('id_pol', None), detail_lines):
                        records = filter(lambda x: x['id_pol'] == p['id_pol'], all_lines)
                        pol = self.pool.get('purchase.order.line').browse(cr, uid, records[0]['id_pol'])
                        no += 1
                        p.update({
                            'no': str(no),
                            'qty_bpb': 0,
                            'qty_sisa': 0,
                            'no_bpb': '',
                            'tgl_bpb': '',
                            'lines': records,
                        })
                        detail_lines.append(p)
                        index = len(detail_lines) - 1
                        move_ids = self.pool.get('stock.move').search(cr, uid, [('product_id','=',pol.product_id.id),('purchase_line_id','=',pol.id),('state','=','done')])
                        moves = self.pool.get('stock.move').browse(cr, uid, move_ids)
                        total_grn = 0
                        for pick in moves.mapped('picking_id'):
                            grn_id = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id','=',pick.id),('state','=','posted')], limit=1)
                            grn = self.pool.get('dym.stock.packing').browse(cr, uid, grn_id)
                            moves_qty = sum(pick.move_lines.filtered(lambda r: r.product_id == pol.product_id and r.purchase_line_id == pol and r.state == 'done').mapped('product_uom_qty'))
                            total_grn += moves_qty
                            if (detail_lines[index]['no_bpb'] == '' and detail_lines[index]['tgl_bpb'] == '' and detail_lines[index]['qty_bpb'] == 0):
                                detail_lines[index]['no_bpb'] = grn.name or ''
                                detail_lines[index]['tgl_bpb'] = grn.date or ''
                                detail_lines[index]['qty_bpb'] = moves_qty
                            else:
                                collecting_res = {
                                        'no': '',
                                        'branch_name':'',
                                        'type_po': '',
                                        'tgl_po': '',
                                        'no_po':'',
                                        'no_sparepart': '',
                                        'nama_sparepart': '',
                                        'kategori': '',
                                        'qty_po': '',
                                        'qty_bpb': moves_qty,
                                        'qty_sisa': 0,
                                        'no_bpb': grn.name or '',
                                        'tgl_bpb': grn.date or '',
                                        'division': '',
                                    }
                                detail_lines.append(collecting_res)
                        qty_sisa = records[0]['qty_po'] - total_grn
                        p.update({
                            'qty_sisa': qty_sisa,
                        })
                report.update({'detail_lines': detail_lines})
                # report.update({'detail_lines': p_map})

        reports = filter(lambda x: x.get('detail_lines'), reports)
        
        if not reports :
            reports = [{'title_short': 'Laporan Distribusi Sparepart', 
                        'detail_lines':[{
                            'no': '',
                            'branch_name':'NO DATA FOUND',
                            'type_po': 'NO DATA FOUND',
                            'tgl_po': 'NO DATA FOUND',
                            'no_po':'NO DATA FOUND',
                            'no_sparepart': 'NO DATA FOUND',
                            'nama_sparepart': 'NO DATA FOUND',
                            'kategori': 'NO DATA FOUND',
                            'qty_po': 'NO DATA FOUND',
                            'qty_bpb': 0,
                            'qty_sisa': 0,
                            'no_bpb': 'NO DATA FOUND',
                            'tgl_bpb': 'NO DATA FOUND',
                            'division': 'NO DATA FOUND',
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
        super(dym_report_distribusi_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_distribusi_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_distribusi.report_distribusi'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_distribusi.report_distribusi'
    _wrapped_report_class = dym_report_distribusi_print
