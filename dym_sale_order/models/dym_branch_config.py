from openerp import models, fields, api, _

class dym_branch_config(models.Model):
    _inherit = 'dym.branch.config'
   
    dym_so_journal_unit_id = fields.Many2one('account.journal', string='Jurnal Penjualan Unit',help='Journal pembentukan invoice penjualan unit')
    dym_so_journal_sparepart_id = fields.Many2one('account.journal', string='Jurnal Penjualan Sparepart',help='Journal pembentukan invoice penjualan sparepart')
    dym_so_account_discount_cash_id = fields.Many2one('account.account',string='Account Discount Cash Customer')
    dym_so_account_discount_program_id = fields.Many2one('account.account',string='Account Discount Program Subsidi Dealer')
    dym_so_account_discount_program_external_id = fields.Many2one('account.account',string='Account Discount Program Subsidi External')
    dym_so_account_discount_lainnya_id = fields.Many2one('account.account',string='Account Discount lainnya Customer')
    dym_so_journal_psmd_id = fields.Many2one('account.journal', string='Jurnal PS MD')
    dym_so_account_sisa_subsidi_id = fields.Many2one('account.account',string='Account Sisa Program Subsidi')
    dym_so_account_potongan_subsidi_id = fields.Many2one('account.account',string='Account Potongan Subsidi')
    so_journal_bbmd_id = fields.Many2one('account.journal', string='Jurnal Barang Bonus MD')
    so_account_potongan_langsung_id = fields.Many2one('account.account',string='Account Potongan Langsung')
    dym_so_journal_pic_id = fields.Many2one('account.journal', string='Jurnal Penjualan (SO) Intercompany',help='Journal Penjualan (SO) Inter Company')
    dym_so_account_penjualan_pic_id = fields.Many2one('account.account', string='Account Penjualan (SO) Intercompany')
    dym_so_account_potongan_pic_id = fields.Many2one('account.account', string='Potongan (SO) Inter Company')
    # so_analytic_2_sparepart = fields.Many2one('account.analytic.account', 'Account Analytic BU Sparepart')
    # so_analytic_4_sparepart = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center Sparepart')
    # so_analytic_2_aksesoris = fields.Many2one('account.analytic.account', 'Account Analytic BU Aksesoris')
    # so_analytic_4_aksesoris = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center Aksesoris')