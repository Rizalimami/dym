from openerp import models, fields, api 

class dym_report_rworsorcpa_ai(models.Model):
    _inherit = 'dealer.spk'
    
    def _report_xls_rworsorcpa_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch',\
            'number',\
            'tipe_konsumen',\
            'type',\
            'o_date',\
            'total',\
            'cpa',\
            'cpa_date',\
            'cpa_total',\
        ]
    