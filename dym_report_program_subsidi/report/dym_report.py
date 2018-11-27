from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_program_subsidi_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_program_subsidi_print, self).__init__(
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

        title_prefix = ''
        title_short_prefix = ''
        
        report_program_subsidi = {
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Program Subsidi')}

        query_start = """
                SELECT d.id as id_ai, 
            COALESCE(b.name,'') as branch_id, 
            dso.division as division, 
            dso.name as number, 
            dso.date_order as date, 
            COALESCE(inv.number,'') as invoice_number, 
            inv.date_invoice as invoice_date, 
            COALESCE(t.name,'') as type, 
            COALESCE(pav.code,'') as warna, 
            COALESCE(lot.name,'') as engine_number, 
            COALESCE(p.name,'') as program, 
            COALESCE(d.ps_md,0) as ps_md, 
            COALESCE(d.ps_ahm,0) as ps_ahm, 
            case when COALESCE(d.ps_finco,0) = COALESCE(d.discount_pelanggan,0) then COALESCE(d.ps_finco,0) else 
            case when COALESCE(d.ps_finco,0) = 0 then COALESCE(d.ps_finco,0) else COALESCE(d.discount_pelanggan,0) end end as ps_finco, 
            COALESCE(d.ps_dealer,0) as ps_dealer, 
            COALESCE(d.ps_others,0) as ps_others,
            case when COALESCE(d.ps_finco,0) = COALESCE(d.discount_pelanggan,0) then COALESCE(d.ps_finco,0) else COALESCE(d.discount_pelanggan,0) end as discount, 
            --COALESCE(d.discount_pelanggan,0) as disc_pelanggan 
            COALESCE(l.discount_po,0) as disc_pelanggan, 
            round(COALESCE(d.ps_md,0)/1.1) as ps_md_real, 
            round(COALESCE(d.ps_ahm,0)/1.1) as ps_ahm_real, 
            case when COALESCE(d.ps_finco,0) = COALESCE(d.discount_pelanggan,0) then round(COALESCE(d.ps_finco,0)/1.1) else 
            case when COALESCE(d.ps_finco,0) = 0 then round(COALESCE(d.ps_finco,0)/1.1) else round(COALESCE(d.discount_pelanggan,0)/1.1) end end as ps_finco_real, 
            round(COALESCE(d.ps_dealer,0)/1.1) as ps_dealer_real, 
            round(COALESCE(d.ps_others,0)/1.1) as ps_others_real,
            case when COALESCE(d.ps_finco,0) = COALESCE(d.discount_pelanggan,0) then round(COALESCE(d.ps_finco,0)/1.1) else round(COALESCE(d.discount_pelanggan,0)/1.1) end as discount_real,
            --COALESCE(d.discount_pelanggan,0) as disc_pelanggan 
            round(COALESCE(l.discount_po,0)/1.1) as disc_pelanggan_real 
            FROM 
            dealer_sale_order dso
            LEFT JOIN dealer_sale_order_line l ON l.dealer_sale_order_line_id = dso.id
            left join dealer_sale_order_line_discount_line d on l.id = d.dealer_sale_order_line_discount_line_id
            LEFT JOIN dym_program_subsidi p ON p.id = d.program_subsidi
            LEFT JOIN account_invoice inv ON inv.origin = dso.name and inv.type = 'out_invoice'
            /*dealer_sale_order_line_discount_line d 
            LEFT JOIN dym_program_subsidi p ON p.id = d.program_subsidi 
            LEFT JOIN dealer_sale_order_line l ON l.id = d.dealer_sale_order_line_discount_line_id 
            LEFT JOIN dealer_sale_order dso ON l.dealer_sale_order_line_id = dso.id 
            LEFT JOIN account_invoice inv ON inv.origin = dso.name and inv.type = 'out_invoice' */
            LEFT JOIN dym_branch b ON b.id = dso.branch_id 
            LEFT JOIN product_product pr ON l.product_id = pr.id 
            LEFT JOIN product_template t ON t.id = pr.product_tmpl_id 
            LEFT JOIN stock_production_lot lot ON lot.id = l.lot_id 
            LEFT JOIN product_attribute_value_product_product_rel pavpp ON pr.id = pavpp.prod_id 
            LEFT JOIN product_attribute_value pav ON pavpp.att_id = pav.id
            where dso.state in ('progress','done')
        """
            
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        query_end=""
        if division :
            query_end +=" AND dso.division = '%s'" % str(division)
        if trx_start_date :
            query_end +=" AND dso.date_order >= '%s'" % str(trx_start_date)
        if trx_end_date :
            query_end +=" AND dso.date_order <= '%s'" % str(trx_end_date)
        if product_ids :
            query_end +=" AND l.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        if branch_ids :
            query_end +=" AND dso.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        reports = [report_program_subsidi]
        
        query_order = "order by 2,4"
        #query_order = ""
        for report in reports:
            cr.execute(query_start + query_end + query_order)
            # --print query_start + query_end + query_order
            all_lines = cr.dictfetchall()
            id_ai = []

            if all_lines:
                # def lines_map(x):
                #         x.update({'docname': x['cabang']})
                # map(lines_map, all_lines)
                # for cnt in range(len(all_lines)-1):
                #     if all_lines[cnt]['id_aml'] != all_lines[cnt+1]['id_aml']:
                #         all_lines[cnt]['draw_line'] = 1
                #     else:
                #         all_lines[cnt]['draw_line'] = 0
                # all_lines[-1]['draw_line'] = 1

                p_map = map(
                    lambda x: {
                        'no': 0,      
                        'id_ai': x['id_ai'] if x['id_ai'] != None else 0,      
                        'branch_id': str(x['branch_id'].encode('ascii','ignore').decode('ascii')) if x['branch_id'] != None else '',
                        'division': str(x['division']) if x['division'] != None else '',
                        'invoice_number': str(x['invoice_number'].encode('ascii','ignore').decode('ascii')) if x['invoice_number'] != None else '',
                        'invoice_date': str(x['invoice_date'].encode('ascii','ignore').decode('ascii')) if x['invoice_date'] != None else '',
                        'number': str(x['number'].encode('ascii','ignore').decode('ascii')) if x['number'] != None else '',
                        'date': str(x['date']) if x['date'] != None else '',
                        'type': str(x['type'].encode('ascii','ignore').decode('ascii')) if x['type'] != None else '',
                        'warna': str(x['warna'].encode('ascii','ignore').decode('ascii')) if x['warna'] != None else '',
                        'engine_number': str(x['engine_number'].encode('ascii','ignore').decode('ascii')) if x['engine_number'] != None else '',
                        'program': str(x['program'].encode('ascii','ignore').decode('ascii')) if x['program'] != None else '',
                        'ps_md': x['ps_md'],
                        'ps_ahm': x['ps_ahm'],
                        'ps_finco': x['ps_finco'],
                        'ps_dealer': x['ps_dealer'],
                        'ps_others': x['ps_others'],
                        'discount': x['discount'],
                        'disc_pelanggan': x['disc_pelanggan'],
                        'ps_md_real': x['ps_md_real'],
                        'ps_ahm_real': x['ps_ahm_real'],
                        'ps_finco_real': x['ps_finco_real'],
                        'ps_dealer_real': x['ps_dealer_real'],
                        'ps_others_real': x['ps_others_real'],
                        'discount_real': x['discount_real'],
                        'disc_pelanggan_real': x['disc_pelanggan_real'],},
                       
                    all_lines)

                ps = []
                for p in p_map:
                    if p['number'] in ps:
                        p['disc_pelanggan'] = 0
                        p['disc_pelanggan_real'] = 0
                    else:
                        ps.append(p['number'])

                report.update({'id_ai': p_map})

        reports = filter(lambda x: x.get('id_ai'), reports)
        
        if not reports :
            reports = [{'title_short': 'Laporan Program Subsidi', 'type': ['out_invoice','in_invoice','in_refund','out_refund'], 'id_ai':
                            [{'no': 0,
                              'branch_id': 'NO DATA FOUND',
                              'division': 'NO DATA FOUND',
                              'number': 'NO DATA FOUND',
                              'date': 'NO DATA FOUND',
                              'invoice_number': 'NO DATA FOUND',
                              'invoice_date': 'NO DATA FOUND',
                              'type': 'NO DATA FOUND',
                              'warna': 'NO DATA FOUND',
                              'engine_number': 'NO DATA FOUND',
                              'program': 'NO DATA FOUND',
                              'ps_md': 0,
                              'ps_ahm': 0,
                              'ps_finco': 0,
                              'ps_dealer': 0,
                              'ps_others': 0,
                              'discount': 0,
                              'disc_pelanggan': 0,
                              'ps_md_real': 0,
                              'ps_ahm_real': 0,
                              'ps_finco_real': 0,
                              'ps_dealer_real': 0,
                              'ps_others_real': 0,
                              'discount_real': 0,
                              'disc_pelanggan_real': 0,
                              }], 'title': ''}]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(dym_report_program_subsidi_print, self).set_context(
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
    _name = 'report.dym_report_program_subsidi.report_program_subsidi'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_program_subsidi.report_program_subsidi'
    _wrapped_report_class = dym_report_program_subsidi_print
