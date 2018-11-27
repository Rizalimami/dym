##############################################################################
#
#    Sipo Cloud Service
#    Copyright (C) 2015.
#
##############################################################################
from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_cost_price_history_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_cost_price_history_report_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context

        start_date = data['start_date']
        end_date = data['end_date']
        product_id = data['product_id']
        warehouse_id = data['warehouse_id']
        criteria = ""

        if start_date :
            criteria += " AND s.datetime >= '%s'" % str(start_date)
        if end_date :
            criteria += " AND s.datetime <= '%s'" % str(end_date)
        if product_id :
            criteria += " AND s.product_id = %s" % product_id[0]
        if warehouse_id :
            criteria += " AND s.warehouse_id = %s" % warehouse_id[0]

        query = """
            select
            b.code as cabang_code, 
            b.name as cabang_nama, 
            pc.name as category,
            t.name as product_code,
            p.default_code as product_name,
            CASE WHEN s.trans_qty < 0 THEN sm.location_id
                WHEN s.trans_qty > 0 THEN sm.location_dest_id
            END as lokasi_id,
            s.origin,
            COALESCE(sp.name, '-') as document_movement,
            CASE WHEN s.trans_qty < 0 THEN 'Sold'
                WHEN s.trans_qty > 0 THEN 'Ready For Sales'
            END as status,
            s.stock_qty as qty_awal,
            s.old_cost_price as cost_awal,
            s.trans_qty as qty_trans,
            s.trans_price as cost_trans,
            s.new_qty as qty_akhir,
            s.cost as cost_akhir
            from product_price_history s
            join stock_warehouse w on (s.warehouse_id=w.id)
            left join product_product p on (s.product_id=p.id)
            left join product_template t on (p.product_tmpl_id=t.id)
            left join product_category c on (t.categ_id=c.id)
            left join dym_branch b on (w.branch_id=b.id)
            left join product_category pc on (t.categ_id=pc.id)
            left join stock_move sm on (sm.origin=s.origin and sm.product_id=s.product_id)
            left join dym_stock_packing sp on (sp.picking_id = sm.picking_id)
        """
        
        where = "WHERE 1 = 1 " + criteria 
        order = "ORDER BY s.id, s.warehouse_id"
        
        self.cr.execute(query + where + order)
        all_lines = self.cr.dictfetchall()
        
        if all_lines :
            datas = map(lambda x : {
                'no': 0,
                'cabang_code':  x['cabang_code'],
                'cabang_nama':  x['cabang_nama'],
                'category':  x['category'],
                'product_code':  x['product_code'],
                'product_name':  x['product_name'],
                'lokasi_id':  x['lokasi_id'],
                'lokasi':  '',
                'document_movement': x['document_movement'],
                'origin': str(x['origin'].encode('ascii','ignore').decode('ascii')) if x['origin'] != None else '',
                'status': x['status'],
                'qty_awal': x['qty_awal'],
                'cost_awal': x['cost_awal'],
                'qty_trans': x['qty_trans'],
                'cost_trans': x['cost_trans'],
                'qty_akhir': x['qty_akhir'],
                'cost_akhir': x['cost_akhir'],
                }, all_lines)

            tampung = []
            for item in datas:
                lokasi_id = self.pool.get('stock.location').search(cr, uid, [('id','=',item['lokasi_id'])])
                lokasi_data = self.pool.get('stock.location').browse(cr, uid, lokasi_id)
                lokasi_parent = self.pool.get('stock.location').browse(cr, uid, lokasi_data.location_id.id)
                item['lokasi'] =  '%s / %s' % (lokasi_parent.name, lokasi_data.name)
                tampung.append(item)

            reports = filter(lambda x: datas, [{'datas': tampung}])
        else :
            reports = [{'datas': [{
                'no': 0,
                'cabang_code':  'NO DATA FOUND',
                'cabang_nama':  'NO DATA FOUND',
                'category':  'NO DATA FOUND',
                'product_code':  'NO DATA FOUND',
                'product_name':  'NO DATA FOUND',
                'lokasi':  'NO DATA FOUND',
                'origin': 'NO DATA FOUND',
                'document_movement': 'NO DATA FOUND',
                'status': 'NO DATA FOUND',
                'qty_awal': 0,
                'cost_awal': 0,
                'qty_trans': 0,
                'cost_trans': 0,
                'qty_akhir': 0,
                'cost_akhir': 0,
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(dym_cost_price_history_report_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_cost_price_history_report_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_sotck_account.product_history_cost_price_report'
    _inherit = 'report.abstract_report'
    _template = 'dym_sotck_account.product_history_cost_price_report'
    _wrapped_report_class = dym_cost_price_history_report_print
