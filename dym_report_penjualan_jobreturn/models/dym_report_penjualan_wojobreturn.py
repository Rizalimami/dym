from openerp import models, fields, api

class dym_report_penjualan_wojobreturn(models.Model):
    _inherit = 'dym.work.order'
    
    def _report_xls_penjualan_wojobreturn_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_status',\
            'branch_code',\
            'branch_name',\
            'name',\
            'state',\
            'date_order',\
            'reff_number',\
            'reff_date',\
            'cust_name',\
            'tipe_konsumen',\
            'tipe_transaksi',\
            'product_name',\
            'categ_name',\
            'category',\
            'product_qty',\
            'supply_qty',\
            'price_unit',\
            'discount_perpcs',\
            'discount',\
            'discount_program',\
            'discount_bundle',\
            'price_subtotal',\
            'sales_name',\
        ]
    