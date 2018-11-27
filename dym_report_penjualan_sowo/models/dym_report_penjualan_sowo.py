from openerp import models, fields, api

class dym_report_penjualan_sowo(models.Model):
    _inherit = 'dym.work.order'
    
    def _report_xls_penjualan_sowo_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_status',\
            'branch_code',\
            'branch_name',\
            'name',\
            'state',\
            'date_order',\
            'invoice_name',\
            'invoice_date',\
            'oos_number',\
            'oos_tgl',\
            'cust_name',\
            'tipe_konsumen',\
            'product_name',\
            'categ_name',\
            'category',\
            'product_qty',\
            'discount_program',\
            'discount_bundle',\
            'price_subtotal',\
            'hpp',\
            'retur',\
            'tgl_bayar',\
            'bayar',\
            'ar_bayar',\
            'ar',\
            'faktur_pajak',\
            'sales_name',\
        ]
    