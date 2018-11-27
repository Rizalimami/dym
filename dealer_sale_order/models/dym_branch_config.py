from openerp import models, fields, api, _

class dym_branch_config(models.Model):
    _inherit = 'dym.branch.config'
   
    dealer_so_journal_pic_id = fields.Many2one('account.journal', string='Jurnal Penjualan Intercompany',help='Journal Penjualan Inter Company')
    dealer_so_journal_pelunasan_id = fields.Many2one('account.journal', string='Jurnal Penjualan',help='Journal Penjualan Regular (non intercompany)')
    dealer_so_journal_dp_id = fields.Many2one('account.journal', string='Jurnal Jaminan Pembelian')
    dealer_so_account_penjualan_pic_id = fields.Many2one('account.account', string='Account Penjualan Intercompany')
    dealer_so_account_potongan_langsung_id = fields.Many2one('account.account', string='Account Potongan Langsung')
    dealer_so_account_potongan_subsidi_id = fields.Many2one('account.account', string='Account Potongan Subsidi Dealer')
    dealer_so_account_potongan_subsidi_external_id = fields.Many2one('account.account', string='Account Potongan Subsidi External')
    dealer_so_account_potongan_pic_id = fields.Many2one('account.account', string='Potongan Inter Company')
    dealer_so_journal_psmd_id = fields.Many2one('account.journal', string='Jurnal PS MD')
    dealer_so_journal_psfinco_id = fields.Many2one('account.journal', string='Jurnal PS Finco')
    dealer_so_journal_bbnbeli_id = fields.Many2one('account.journal', string='Jurnal BBN Beli (Estimasi)')
    dealer_so_journal_insentive_finco_id = fields.Many2one('account.journal', string='Jurnal Insentive Finco')
    dealer_so_account_bbn_jual_id = fields.Many2one('account.account', string='Account BBN Jual')
    dealer_so_journal_bbmd_id = fields.Many2one('account.journal', string='Jurnal Barang Bonus MD')
    dealer_so_journal_bbfinco_id = fields.Many2one('account.journal', string='Jurnal Barang Bonus Finco')
    dealer_so_journal_hc_id = fields.Many2one('account.journal', string='Jurnal Hutang Komisi')
    dealer_so_account_sisa_subsidi_id = fields.Many2one('account.account', string='Account Sisa Program Subsidi')
    dealer_so_account_dp = fields.Many2one('account.account', string='Account Jaminan Pembelian')