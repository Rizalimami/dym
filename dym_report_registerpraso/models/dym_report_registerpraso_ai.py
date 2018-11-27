from openerp import models, fields, api 

class dym_report_registerpraso_ai(models.Model):
    _inherit = 'dealer.spk'
    
    def _report_xls_registerpraso_fields(self, cr, uid, context=None):
        return [
            'no',\
            'no_reg',\
            'branch',\
            'salesman',\
            'tgl_distribusi',\
            'no_pso',\
            'no_dso',\
            'state',\
            'aging',\
        ]
    