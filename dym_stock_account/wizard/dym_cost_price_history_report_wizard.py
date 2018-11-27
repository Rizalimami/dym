##############################################################################
#
#    Sipo Cloud Service
#    Copyright (C) 2015.
#
##############################################################################
from lxml import etree
from openerp.osv import osv
from openerp import api, fields, models, _

class dym_cost_price_history_report_wizard(models.TransientModel):
    _name = 'dym.cost.price.history.report.wizard'
    _description = 'Cost Price History Wizard'
    
    def _get_warehouse_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context:
            context = {}
        res = super(dym_cost_price_history_report_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        res['arch'] = etree.tostring(doc)
        return res
    
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    product_id = fields.Many2one('product.product', string='Products', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', copy=False, required=True)
    
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        data = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'Laporan History Cost Price', 'datas': data}
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
    