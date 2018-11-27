from openerp import models, fields, api 

class dym_report_jualbysalesman_ai(models.Model):
    _inherit = 'dealer.sale.order'
    
    def _report_xls_jualbysalesman_fields(self, cr, uid, context=None):
        return [
            'cabang',\
            'salesman',\
            'spv_name',\
            'faktur',\
            'date',\
            'invoice_no',\
            'invoice_date',\
            'finco_code',\
            'finco_branch',\
            'is_cod',\
            'customer',\
            'motor',\
            'no_mesin',\
            'product_qty',\
            'harga_unit',\
            'disc_konsumen',\
            'disc_intern',\
            'disc_extern',\
            'broker',\
            'total',\
            'ar_days',\
            'lunas',\
        ]
    