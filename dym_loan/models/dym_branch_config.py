import time
from datetime import datetime
from openerp import models, fields, api

class dym_branch_config_retur(models.Model):
    _inherit = "dym.branch.config"
    
    dym_journal_loan_pinjaman = fields.Many2one('account.journal',string="Journal Pengakuan Pinjaman Jangka Panjang",help="Journal ini dibutuhkan saat proses pengakuan pinjaman jangka panjang.")
    dym_journal_loan_pinjaman_pendek = fields.Many2one('account.journal',string="Journal Pengakuan Pinjaman Jangka Pendek",help="Journal ini dibutuhkan saat proses pengakuan pinjaman jangka pendek.")
    dym_journal_loan_pinjaman_intercompany = fields.Many2one('account.journal',string="Journal Pengakuan Pinjaman Intercompany",help="Journal ini dibutuhkan saat proses pengakuan pinjaman intercompany.")
    dym_journal_loan_piutang = fields.Many2one('account.journal',string="Journal Pengakuan Piutang",help="Journal ini dibutuhkan saat proses pengakuan piutang.")
    dym_journal_loan_reklasifikasi = fields.Many2one('account.journal',string="Journal Pengakuan Reklasifikasi hutang DF",help="Journal ini dibutuhkan saat proses pengakuan reklasifikasi hutang DF.")
    dym_journal_loan_bunga_pinjaman = fields.Many2one('account.journal',string="Journal Bunga Pinjaman")
    dym_journal_loan_bunga_piutang = fields.Many2one('account.journal',string="Journal Bunga Piutang")
    dym_journal_loan_bunga_reklasifikasi = fields.Many2one('account.journal',string="Journal Bunga Reklasifikasi")
