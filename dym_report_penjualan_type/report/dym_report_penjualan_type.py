from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_penjualan_type_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_penjualan_type_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        
        
        query_penjualan_type = """
            select b.branch_status as branch_status,
                b.code as branch_code,
                b.name as branch_name,
                product.name_template as type,
                pav.code as color,
                dsol.product_qty as qty,
                dsol.price_unit as off_the_road,
                dsol.discount_po as diskon_konsumen,
                dsol_disc.ps_dealer as ps_dealer,
                dsol_disc.ps_ahm as ps_ahm,
                dsol_disc.ps_md as ps_md,
                dsol_disc.ps_finco as ps_finco,
                (dsol_disc.ps_dealer)+(dsol_disc.ps_ahm)+(dsol_disc.ps_md)+(dsol_disc.ps_finco) as ps_total,
                dsol_disc.discount_pelanggan/1.1 as total_disc,
                dsol.price_unit/1.1 as penjualan_bersih,
                dsol.price_subtotal as dpp,
                dsol.force_cogs as hpp,
                (dsol.price_subtotal)-(dsol.force_cogs) as margin
                from dealer_sale_order dso
                inner join dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id = dso.id
                left join dym_branch b ON dso.branch_id = b.id
                left join product_product product ON dsol.product_id = product.id
                left join product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id
                left join product_attribute_value pav ON pavpp.att_id = pav.id
                left join dealer_sale_order_line_discount_line dsol_disc ON dsol_disc.dealer_sale_order_line_discount_line_id = dsol.id
        """

        query_where = " where b.id = {0} " .format(str(data['branch_ids'][0]))

        

        self.cr.execute(query_penjualan_type + query_where)
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                'no': 0,
                'branch_status': str(x['branch_status'].encode('ascii','ignore').decode('ascii')) if x['branch_status'] != None else '',
                'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                'type': str(x['type'].encode('ascii','ignore').decode('ascii')) if x['type'] != None else '',
                'color': str(x['color'].encode('ascii','ignore').decode('ascii')) if x['color'] != None else '',
                'qty': x['qty'] if x['qty'] > 0 else 0.0,
                'off_the_road': x['off_the_road'] if x['off_the_road'] > 0 else 0.0,
                'diskon_konsumen': x['diskon_konsumen'] if x['diskon_konsumen'] > 0 else 0.0,
                'ps_dealer': x['ps_dealer'] if x['ps_dealer'] > 0 else 0.0,
                'ps_ahm': x['ps_ahm'] if x['ps_ahm'] > 0 else 0.0,
                'ps_md': x['ps_md'] if x['ps_md'] > 0 else 0.0,
                'ps_finco': x['ps_finco'] if x['ps_finco'] > 0 else 0.0,
                'ps_total': x['ps_total'] if x['ps_total'] > 0 else 0.0,
                'total_disc': x['total_disc'] if x['total_disc'] > 0 else 0.0,
                'penjualan_bersih': x['penjualan_bersih'] if x['penjualan_bersih'] > 0 else 0.0,
                'dpp': x['dpp'] if x['dpp'] > 0 else 0.0,
                'hpp': x['hpp'] if x['hpp'] > 0 else 0.0,
                'margin': x['margin'] if x['margin'] > 0 else 0.0,

            }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            reports = [{'datas': [{
                'no': 'NO DATA FOUND',
                'branch_status': 'NO DATA FOUND',
                'branch_code': 'NO DATA FOUND',
                'branch_name': 'NO DATA FOUND',
                'type': 'NO DATA FOUND',
                'color': 'NO DATA FOUND',
                'qty': 0,
                'off_the_road': 0,
                'diskon_konsumen': 0,
                'ps_dealer': 0,
                'ps_ahm': 0,
                'ps_md': 0,
                'ps_finco': 0,
                'ps_total': 0,
                'total_disc': 0,
                'penjualan_bersih': 0,
                'dpp': 0,
                'hpp': 0,
                'margin': 0,
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(dym_report_penjualan_type_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_penjualan_type_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_penjualan_type.report_penjualan_type'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_penjualan_type.report_penjualan_type'
    _wrapped_report_class = dym_report_penjualan_type_print
    