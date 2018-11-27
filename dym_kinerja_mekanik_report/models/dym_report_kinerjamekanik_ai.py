from openerp import models, fields, api 

class dym_report_kinerjamekanik_ai(models.Model):
    _inherit = 'dym.work.order'
    
    def _report_xls_kinerjamekanik_fields(self, cr, uid, context=None):
        return [
            'no',\
            'nama_mekanik',\
            'sum_claim', \
            'sum_kpb', \
            'sum_quickserv',\
			'sum_lightrep',\
			'sum_heavyrep', \
			'sum_job',\
			'total',\
			'jam_terpakai',\
			'rp_jasa',\
			'rp_sparepart'
        ]
    