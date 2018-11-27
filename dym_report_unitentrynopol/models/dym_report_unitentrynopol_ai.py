from openerp import models, fields, api 

class dym_report_unitentrynopol_ai(models.Model):
    _inherit = 'dym.work.order'
    
    def _report_xls_unitentrynopol_fields(self, cr, uid, context=None):
        return [
            'no' ,
            #'id_wo' ,
            'no_pol',
            'tgl_wo',
            'no_wo',
            'nama_customer',
            'total_jasa',
            'total_part',
            'total',
            'nama_mekanik',
        ]
    