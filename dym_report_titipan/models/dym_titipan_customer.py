from openerp import models, fields, api

class dym_titipan_customer(models.Model):
    _inherit = 'account.move.line'

    def _report_xls_titipan_customer_fields(self, cr,uid,context=None):
        return [
            'cabang',\
            'divisi',\
            'tgl_input',\
            'id_ai',\
            'kode_customer',\
            'nama_customer',\
            'payment_method',\
            'account',\
            'description',\
            'nilai_titipan',\
            'account_analytic',\
            'journal_item',\
            'nilai_alokasi',\
            'tgl_alokasi',\
            'sisa_titipan',\
        ]

    def _report_xls_titipan_stnk_customer_fields(self, cr,uid,context=None):
        return [
            'cabang',\
            'divisi',\
            'tgl_input',\
            'id_ai',\
            'kode_customer',\
            'nama_customer',\
            'payment_method',\
            'account',\
            'description',\
            'nilai_titipan',\
            'account_analytic',\
            'journal_item',\
            'nilai_alokasi',\
            'tgl_alokasi',\
            'sisa_titipan',\
            'total_tagihan',\
            'total_jasa',\
            'selisih_margin',\
            'pajak_progresif',\
        ]

