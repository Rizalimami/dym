from openerp import models, fields, api

class dym_report_stock_outstanding_sm(models.Model):
    _inherit = 'stock.move'
    
    def _report_xls_stock_outstanding_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'branch_name',\
            'packing_date',\
            'packing_name',\
            'prod_tmpl',\
            'internal_ref',\
            'color',\
            'engine',\
            'chassis',\
            'qty',\
            'partner_code',\
            'partner_name',\
            'ekspedisi_code',\
            'ekspedisi_name',\
        ]
        
    #aris
    def _report_xls_stock_outstanding_fields_sparepart(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'branch_name',\
            'packing_date',\
            'packing_name',\
            'prod_tmpl',\
            'internal_ref',\
            'qty',\
            'partner_code',\
            'partner_name',\
            'ekspedisi_code',\
            'ekspedisi_name',\
        ]
