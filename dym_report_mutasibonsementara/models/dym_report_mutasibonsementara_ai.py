from openerp import models, fields, api 

class dym_report_mutasibonsementara_ai(models.Model):
    _inherit = 'dym.advance.payment'
    
    def _report_xls_mutasibonsementara_fields(self, cr, uid, context=None):
        return [
            'no',\
            'bs_tgl',\
            'karyawan',\
            'dept',\
            'bs_nama',\
            'bs_nilai',\
            'bs_ket',\
            'sp_date',\
            'sp_name',\
            'sp_nilai',\
            'sp_saldobs',\
            'current',\
            'overdue1_7',\
            'overdue8_30',\
            'overdue31_60',\
            'overdue61_90',\
            'overdue90',\
            'aa_combi',\
            'aa_company',\
            'aa_bisnisunit',\
            'aa_branch',\
            'aa_costcenter',\
        ]
    