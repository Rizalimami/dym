from openerp import models, fields, api

class dym_report_kartu_stock_sm(models.Model):
    _inherit = 'stock.move'
    
    def _report_xls_kartu_stock_fields(self, cr, uid, context=None):
        return [
            'no',\
            'packing_date',\
            'packing_name',\
            'qty',\
            'qty_out',\
            'location',\
        ]

    #aris
    def _report_xls_kartu_stock_fields_sparepart(self, cr, uid, context=None):
        return [
            'no',\
            'packing_date',\
            'packing_name',\
            'qty',\
            'qty_out',\
            'location',\
        ]
