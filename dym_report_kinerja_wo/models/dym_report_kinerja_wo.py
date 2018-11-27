from openerp import models, fields, api

class dym_report_kinerja_wo(models.Model):
    _inherit = 'dym.work.order'
    
    def _report_xls_kinerja_wo_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_status',\
            'branch_code',\
            'branch_name',\
            'wo_name',\
            'date_order',\
            'mekanik_id',\
            'sa_id',\
            'product_name',\
            'product_qty',\
            'price_unit',\
            'discount',\
            'discount_program',\
            'discount_persen',\
             'price_subtotal',\
            'categ_name',\
            'faktur_pajak',\
            'collecting_id',\
        ]
    