from openerp import models, fields, api 

class dym_report_registerpraso_ai(models.Model):
    _inherit = 'dealer.spk'
    
    def _report_xls_registerpraso_fields(self, cr, uid, context=None):
        return [
            'no',\
            'region',\
            'area',\
            'branch_code',\
            'branch_name',\
            'invoice_number',\
            'invoice_date',\
            'invoice_date_year',\
            'chosen_month',\
            'finco_code',\
            'cust_name',\
            'sls_pay',\
            'marketing',\
            'product_name',\
            'product_desc',\
            'lot_name',\
            'lot_chassis',\
            'price_unit',\
            'price_bbn',\
            'disc_total',\
            'cust_name_2',\
            'alamat_cust_name',\
            'kota_cabang',\
            'amount_hutang_komisi',\
            'product_qty',\
            'qty_retur',\
            'net_sales',\
            'invoice_date_date',\
            'cabang_partner',\
            'tanda_jadi',\
            'no_po',\
            'tgl_po',\
            'tenor',\
            'jp_po',\
            'discount_po',\
            'discount_extern_ps',\
            'discount_intern_ps',\
            'kota_cust_stnk_name',\
            'kec_cust_stnk_name',\
            'kel_cust_stnk_name',\
            'nik_sales_koor_name',\
            'sales_koor_name',\
            'job_name',\
            'mkt_join_date',\
            'lama_kerja',\
            'spv_nik',\
            'spv_name',\
            'nik_sales_name',\
            'sales_name',\
            # 'tambahan_bbn',\
            # 'nama_pendek',\
            # 'last_update_time',\
        ]
    