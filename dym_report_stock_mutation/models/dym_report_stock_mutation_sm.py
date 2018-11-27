from openerp import models, fields, api

class dym_report_stock_mutation_sm(models.Model):
    _inherit = 'stock.move'
    
    def _report_xls_stock_mutation_fields(self, cr, uid, context=None):
        return [
            'no',\
            'prod_tmpl',\
            'color',\
            'packing_date',\
            'packing_name',\
            'engine',\
            'chassis',\
            'qty_awal',\
            'amount_awal',\
            'qty',\
            'amount',\
            'qty_retur_beli',\
            'amount_retur_beli',\
            'qty_out',\
            'amount_out',\
            'qty_retur_jual',\
            'amount_retur_jual',\
            'qty_adjustment_in',\
            'amount_adjustment_in',\
            'qty_adjustment_out',\
            'amount_adjustment_out',\
            'qty_akhir',\
            'amount_akhir',\
        ]

    #aris
    def _report_xls_stock_mutation_fields_sparepart(self, cr, uid, context=None):
        return [
            'no',\
            'packing_date',\
            'packing_name',\
            'prod_tmpl',\
            'internal_ref',\
            'qty_awal',\
            'amount_awal',\
            'qty',\
            'amount',\
            'qty_retur_beli',\
            'amount_retur_beli',\
            'qty_out',\
            'amount_out',\
            'qty_retur_jual',\
            'amount_retur_jual',\
            'qty_adjustment_in',\
            'amount_adjustment_in',\
            'qty_adjustment_out',\
            'amount_adjustment_out',\
            'qty_akhir',\
            'amount_akhir',\
        ]
