from openerp import models, fields, api

class dym_report_pembelian_sum_ai(models.Model):
    _inherit = 'account.invoice'
    
    def _report_xls_pembelian_sum_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'branch_name',\
            'supplier',\
            'qty_beli_gross',\
            'qty_retur',\
            'qty_beli_net',\
        ]
    
