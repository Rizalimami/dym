from openerp import models, fields, api

class dym_report_transaksi_outstanding(models.Model):
    _inherit = 'dym.work.order.line'
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_transaksi_outstanding_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_name',\
            'transaksi',\
            'no_dokumen', \
            'status', \
            'value',\
            ]
