from openerp import models, fields, api 

class dym_report_titipanleasing_ai(models.Model):
    _inherit = 'dym.branch'
    
    def _report_xls_titipanleasing_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_status',\
            'cabang',\
            'divisi',\
            'nama_leasing',\
            'ket',\
            'payment_method',\
            'tanggal',\
            'no_cde',\
            'nilai_titipan',\
            'alokasi_tanggal',\
            'alokasi_no',\
            'cpa_no',\
            'nilai_alokasi',\
            'sisa_titipan',\
            'a_code', \
            'a_name', \
            'aa_combi', \
            'aa_company', \
            'aa_bisnisunit', \
            'aa_branch', \
            'aa_costcenter', \
        ]
    