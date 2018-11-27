from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_pembelian_sum_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_pembelian_sum_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        division = data['division']
        state = data['state']
        branch_ids = data['branch_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        product_ids = data['product_ids']
        partner_ids = data['partner_ids']
        segmen = data['segmen']
        branch_status = data['branch_status']
        
        where_division = " 1=1 "
        if division :
            where_division = " ai.division = '%s'" % str(division)
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " ai.date_invoice >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " ai.date_invoice <= '%s'" % str(end_date)
        where_state = " 1=1 "
        if state in ['open','paid'] :
            where_state = " ai.state = '%s'" % str(state)
        else :
            where_state = " ai.state in ('open','paid')"
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " ai.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        where_product_ids = " 1=1 "
        if product_ids :
            where_product_ids = " ail.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        where_partner_ids = " 1=1 "
        if partner_ids :
            where_partner_ids = " ai.partner_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        
        query_pembelian_sum = """
            select  b.code as branch_code, 
            b.name as branch_name, 
            pr.name as supplier, 
            sum(ail.quantity) as qty_beli_gross, 
            sum(retur.qty_retur) as qty_retur,
            sum(ail.quantity) as qty_beli_net
            from account_invoice ai inner join account_invoice_line ail on ai.id = ail.invoice_id
            inner join (select tent_ai.id, COALESCE(sum(tent_ail.quantity),0) as total_qty from account_invoice tent_ai inner join account_invoice_line tent_ail on tent_ai.id = tent_ail.invoice_id group by tent_ai.id) tent on ai.id = tent.id
            left join dym_branch b on ai.branch_id = b.id
            left join res_partner pr on ai.partner_id = pr.id
            left join account_journal aj on ai.journal_id = aj.id
            left join account_account aa on ai.account_id = aa.id
            left join (
                select r.date as tgl_retur,r.name as no_retur, sum(rl.product_qty) as qty_retur ,rl.invoice_line_id, sum((rl.price_unit*rl.product_qty)-rl.discount_amount) as retur_total
                from dym_retur_beli_line rl left join dym_retur_beli r on r.id = rl.retur_id
                where r.state in ('approved','except_picking','except_invoice','done')
                group by rl.invoice_line_id,r.date ,r.name 
            ) retur ON retur.invoice_line_id = ail.id 
            
            ---and ai.division = 'Unit' 

        """
        where = " where (ail.purchase_line_id is not null or ai.tipe = 'purchase') and aa.code = '2102001' and ai.type = 'in_invoice' and ai.state in ('open','paid') AND " + where_division + " AND " + where_state + " AND " + where_branch_ids + " AND " + where_start_date + " AND " + where_end_date + " AND " + where_product_ids + " AND " + where_partner_ids
        group = " group by b.code,b.name,pr.name"
        order = " order by b.code,b.name,pr.name "
 
        self.cr.execute(query_pembelian_sum + where + group + order)
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                'no': 0,
                'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',    
                'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                'supplier': str(x['supplier'].encode('ascii','ignore').decode('ascii')) if x['supplier'] != None else '',
                'qty_beli_gross': x['qty_beli_gross'],
                'qty_retur': x['qty_retur'],
                'qty_beli_net': x['qty_beli_net'],
                }, all_lines)
            total_ppn_per_inv = 0
            amount_tax = 0
            invoice_id = False
            for p in datas:
                #if p['supplier'] not in map(
                #        lambda x: x.get('supplier', None), move_lines):
                    #account_invoice_line = filter(
                     #   lambda x: x['supplier'] == p['supplier'], all_lines)
                
                    move_lines.append(p)
            reports = filter(lambda x: datas, [{'datas': move_lines}])
        else :
            raise osv.except_osv(_('Data Not Found!'), _('Tidak ditemukan data dari hasil filter Report Pembelian Summary.'))
        
        self.localcontext.update({'reports': reports})
        super(dym_report_pembelian_sum_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_pembelian_sum_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_pembelian_sum.report_pembelian_sum'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_pembelian_sum.report_pembelian_sum'
    _wrapped_report_class = dym_report_pembelian_sum_print
    