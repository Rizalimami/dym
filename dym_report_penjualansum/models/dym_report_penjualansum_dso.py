from openerp import models, fields, api

class dym_report_penjualansum_sm(models.Model):
    _inherit = 'dealer.sale.order'
    
    def _report_xls_penjualansum_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_status',\
            'branch_code',\
            'branch_name',\
            'cash',\
            'retur_cash',\
            'net_cash',\
            'adira',\
            'retur_adira',\
            'net_adira',\
            'astra_buana',\
            'retur_astra_buana',\
            'net_astra_buana',\
            'csf',\
            'retur_csf',\
            'net_csf',\
            'fif',\
            'retur_fif',\
            'net_fif',\
            'ifi',\
            'retur_ifi',\
            'net_ifi',\
            'mandala',\
            'retur_mandala',\
            'net_mandala',\
            'mandiri_tunas',\
            'retur_mandiri_tunas',\
            'net_mandiri_tunas',\
            'mandiri_utama',\
            'retur_mandiri_utama',\
            'net_mandiri_utama',\
            'mcf',\
            'retur_mcf',\
            'net_mcf',\
            'mpmf',\
            'retur_mpmf',\
            'net_mpmf',\
            'rbf',\
            'retur_rbf',\
            'net_rbf',\
            'sof',\
            'retur_sof',\
            'net_sof',\
            'wom',\
            'retur_wom',\
            'net_wom',\
            'total_credit',\
            'retur_credit',\
            'net_credit',\
            'penjualan_bruto',\
            'retur_penjualan',\
            'net_penjualan',\
            'jual_pic',\
            'retur_jual_pic',\
            'net_jual_pic',\
        ]