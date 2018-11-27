from openerp import models, fields, api 

class dym_report_rjual_ai(models.Model):
    _inherit = 'dealer.spk'
    
    def _report_xls_rjual_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_status',\
            'branch_code',\
            'branch_name',\
            'no_registrasi',\
            'spk_name',\
            'name',\
            'date_order',\
            'state',\
            'state_ksu',\
            'state_picking',\
            'oos_number',\
            'invoice_number',\
            'invoice_date',\
            'invoice_status',\
            'finco_code',\
            'is_cod',\
            'cust_code',\
            'cust_name',\
            'cabang_partner',\
            'cust_stnk_name',\
            'product_name',\
            'pav_code',\
            'product_qty',\
            'lot_name',\
            'lot_chassis',\
            'price_unit',\
            'discount_po',\
            'ps_dealer',\
            'ps_ahm',\
            'ps_md',\
            'ps_finco',\
            'ps_total',\
            'sales',\
            'disc_quo_incl_tax_no',\
            'disc_quo_incl_tax',\
            'disc_reg',\
            'disc_quo',\
            'disc_total',\
            'price_subtotal',\
            'PPN',\
            'total',\
            'force_cogs',\
            'piutang_dp',\
            'piutang',\
            'piutang_total',\
            'gp_dpp_minus_hpp',\
            'gp_unit',\
            'price_bbn',\
            'price_bbn_beli',\
            'gp_bbn',\
            'gp_total',\
            'partner_komisi_id',\
            'hutang_komisi_id',\
            'amount_hutang_komisi',\
            'pph_komisi',\
            'dpp_insentif_finco',\
            'beban_cabang',\
            'ar_days',\
            'tgl_lunas',\
            'categ_name',\
            'categ2_name',\
            'prod_series',\
            'faktur_pajak',\
            'pkp',\
            'proposal_id',\
            'or_name',\
            # 'or_amount',\
            'sales_name',\
            'job_name',\
            'sales_koor_name',\
            'spv_name',\
            'md_code',\
            'no_hp_cust_stnk',\
            'no_hp_cust_beli',\
            'tahun_rakit',\
            'no_po',\
            'tgl_po',\
        ]
    