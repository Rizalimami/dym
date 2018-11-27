from openerp import models, fields, api

class dym_report_kinerja_so(models.Model):
    _inherit = 'sale.order'
    
    def _report_xls_kinerja_so_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_status',\
            'branch_code',\
            'branch_name',\
            'so_name',\
            'date_order',\
            'mekanik_id',\
            'product_name',\
            'product_qty',\
            'price_unit',\
            'discount',\
            'discount_program',\
            'discount_cash',\
            'discount_persen',\
             'price_subtotal',\
            'categ_name',\
            'faktur_pajak',\
        ]
    