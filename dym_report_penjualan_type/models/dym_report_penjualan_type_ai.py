from openerp import models, fields, api 

class dym_report_penjualan_type_ai(models.Model):
    _inherit = 'dealer.sale.order'
    
    def _report_xls_penjualan_type_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_status',\
            'branch_code',\
            'branch_name',\
            'type',\
            'color',\
            'qty',\
            'off_the_road',\
            'diskon_konsumen',\
            'ps_dealer',\
            'ps_ahm',\
            'ps_md',\
            'ps_finco',\
            'ps_total',\
            'total_disc',\
            'penjualan_bersih',\
            'dpp',\
            'hpp',\
            'margin',\
        ]
    