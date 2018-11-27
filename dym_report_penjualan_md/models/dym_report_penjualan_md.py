from openerp import models, fields, api

class dym_report_penjualan_md(models.Model):
    _inherit = 'sale.order'
    
    def _report_xls_penjualan_md_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'branch_name',\
            'name',\
            'state',\
            'date_order',\
            'cust_code',\
            'cust_name',\
            'type',\
            'warna',\
            'qty',\
            'hpp',\
            'harga_jual',\
            'disc',\
            'harga_jual_excl_tax',\
            'total_hpp',\
            'nett_sales',\
            'discount_cash_avg',\
            'discount_lain_avg',\
            'discount_program_avg',\
            'dpp',\
            'tax',\
            'total',\
            'gp',\
            'gp_avg',\
            'categ_name',\
            'categ2_name',\
            'prod_series',\
            'faktur_pajak',\
        ]
    