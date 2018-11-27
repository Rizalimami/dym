from openerp import models, fields, api 

class dym_report_penjualan_non_mt_ai(models.Model):
    _inherit = 'dealer.sale.order'
    
    def _report_xls_penjualan_non_mt_fields(self, cr, uid, context=None):
        return [
            'no',\
            'cabang',\
            'faktur',\
            'date',\
            'customer',\
            'motor',\
            'no_mesin',\
            'salesman',\
            'division',\
            'disc_konsumen',\
            'disc_intern',\
            'disc_extern',\
            'broker',\
            'total',\
            'ar_days',\
            'lunas',\
        ]
    