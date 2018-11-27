from openerp import models, fields, api

class dym_report_penjualantax_sm(models.Model):
    _inherit = 'dealer.sale.order'
    
    def _report_xls_penjualantax_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_status',\
            'branch_code',\
            'branch_name',\
            'no_registrasi',\
            'spk_name',\
            'name',\
            'date_order',\
            'oos_number',\
            'invoice_number',\
            'invoice_date',\
            'invoice_status',\
            'cust_code',\
            'cust_name',\
            'cabang_partner',\
            'product_name',\
            'pav_code',\
            'product_qty',\
            'lot_name',\
            'lot_chassis',\
            'price_unit',\
            'discount_po',\
            'ps_total',\
            'price_subtotal',\
            'PPN',\
            'total',\
        ]
    