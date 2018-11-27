from openerp import models, fields, api, _

class dym_branch_config(models.Model):
    _inherit = 'dym.branch.config'

    ahass_titipan_kas_journal_id = fields.Many2one('account.journal', string='Jurnal Titipan Kas',help='Journal titipan Kas Ahass. Akun default debit/credit diisi dengan "Titipan - Penggantian KK AHASS"')
    ahass_piutang_induk_journal_id = fields.Many2one('account.journal', string='Jurnal Piutang Kas Induk',help='Journal Piutang Kas Induk. Akun default debit/credit diisi dengan "Piutang Induk - Penggantian KK"')
    ahass_account_kas_induk = fields.Many2one('account.account', string='Account Kas AHASS')