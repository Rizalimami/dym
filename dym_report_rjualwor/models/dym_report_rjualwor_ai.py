from openerp import models, fields, api 

class dym_report_rjualwor_ai(models.Model):
    _inherit = 'dym.work.order'
    
    def _report_xls_rjualwor_fields(self, cr, uid, context=None):
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
            'dno_number',\
            'dno_tgl',\
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
            'dpp',\
            'ppn',\
            'force_cogs',\
            'tgl_bayar',\
            'ar',\
            # 'ar_bayar',\
            # 'ar',\
            'faktur_pajak',\
            'sales_name',\
        ]
    