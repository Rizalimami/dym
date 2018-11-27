from openerp.osv import fields, osv

class dym_branch_config(osv.osv):
    _inherit = 'dym.branch.config'
    _columns = {
                
        'wo_kpb_journal_id': fields.many2one('account.journal','Journal WO KPB', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi Work Order untuk type KPB",),
        'wo_claim_journal_id': fields.many2one('account.journal','Journal WO Claim', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi Work Order untuk Claim ",),   
        'wo_reg_journal_id': fields.many2one('account.journal','Journal WO Regular dan Part Sales', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi Work Order untuk type Reguler dan Part Sales ",),
        
        'wo_war_journal_id': fields.many2one('account.journal','Journal WO Job Return', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi Work Order untuk type Job Return ",), 
                
        'wo_collecting_claim_journal_id': fields.many2one('account.journal','Journal Collecting Claim', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi Collecting piutang kpb  ",),

        'wo_collecting_kpb_journal_id': fields.many2one('account.journal','Journal Collecting KPB', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi Collecting piutang kpb  ",),
        'wo_journal_psmd_id': fields.many2one('account.journal','Jurnal PS MD'),
        'wo_account_sisa_subsidi_id': fields.many2one('account.account','Account Sisa Program Subsidi'),
        'wo_account_potongan_subsidi_id': fields.many2one('account.account','Account Potongan Subsidi'),
        'wo_account_potongan_subsidi_external_id': fields.many2one('account.account','Account Potongan Subsidi External'),

        'dym_wo_account_discount_cash_id': fields.many2one('account.account','Account Discount Cash Customer'),
        'dym_wo_account_discount_program_id': fields.many2one('account.account','Account Discount Program Customer'),
        'dym_wo_account_discount_lainnya_id': fields.many2one('account.account','Account Discount lainnya Customer'),
        'wo_analytic_2_sparepart' : fields.many2one('account.analytic.account', 'Account Analytic BU Sparepart'),
        'wo_analytic_4_sparepart' : fields.many2one('account.analytic.account', 'Account Analytic Cost Center Sparepart'),
        'wo_analytic_2_aksesoris' : fields.many2one('account.analytic.account', 'Account Analytic BU Aksesoris'),
        'wo_analytic_4_aksesoris' : fields.many2one('account.analytic.account', 'Account Analytic Cost Center Aksesoris'),
        'wo_analytic_2_service' : fields.many2one('account.analytic.account', 'Account Analytic BU Service'),
        'wo_analytic_4_service' : fields.many2one('account.analytic.account', 'Account Analytic Cost Center Service'),
        'wo_journal_bbmd_id': fields.many2one('account.journal','Jurnal Barang Bonus MD'),
        'wo_account_potongan_langsung_id': fields.many2one('account.account','Account Potongan Langsung'),
        'wo_account_potongan_bundle_id': fields.many2one('account.account','Account Potongan Bundle'),
        'wo_collecting_kpb_kompensasi_account_id': fields.many2one('account.account','Account Kompensasi Oli'),
        'wo_collecting_kpb_selisih_account_id': fields.many2one('account.account','Account Selisih Collecting KPB'),
    }


class dym_branch_penggantian_oli_kpb(osv.osv):
    _inherit = 'dym.branch'
    _columns = {
        'kpb_ganti_oli_barang': fields.boolean('Oli KPB Diganti Barang'),
        'kpb_ganti_oli_barang_tax': fields.many2many('account.tax', 'dym_branch_kpb_tax_rel', 'branch_id','tax_id', 'Taxes (Kompensasi Oli)'),
    }