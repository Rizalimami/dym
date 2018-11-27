from openerp import models, fields, api

class dym_report_stock_movement_sm(models.Model):
    _inherit = 'stock.move'
    
    def _report_xls_stock_movement_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'branch_name',\
            'categ_name',\
            'prod_tmpl',\
            'internal_ref',\
            'color',\
            'engine',\
            'chassis',\
            'tahun',\
            'picking_type_name',\
            'packing_name',\
            'packing_date',\
            'qty',\
            'location',\
            'partner_code',\
            'partner_name',\
            'ekspedisi_code',\
            'ekspedisi_name',\
            'picking_origin',\
            'status_rfs',\
            'packing_state',\
            'backorder',\
            'branch_source',\
        ]

    #aris
    def _report_xls_stock_movement_fields_sparepart(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'branch_name',\
            'categ_name',\
            'prod_tmpl',\
            'internal_ref',\
            'picking_type_name',\
            'packing_name',\
            'packing_date',\
            'qty',\
            'parent_location_source',\
            'location_source',\
            'parent_location',\
            'location',\
            'partner_code',\
            'partner_name',\
            'picking_origin',\
            'status_rfs',\
            'packing_state',\
            'backorder',\
            'branch_source',\
        ]
    