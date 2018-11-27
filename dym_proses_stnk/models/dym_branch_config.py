import time
from datetime import datetime
from openerp import models, fields, api

class dym_branch_config_proses_birojasa(models.Model):
    _inherit = "dym.branch.config"
    
    tagihan_birojasa_progressive_journal_id = fields.Many2one('account.journal',string="Journal Pajak Progressive (Aktual)",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses Tagihan Biro Jasa, jika Unitnya memiliki pajak progressive.")
    tagihan_birojasa_progressive_account_id = fields.Many2one('account.account',string="Account Pajak Progressive (Aktual)",help="Account ini dibutuhkan saat proses Tagihan Biro Jasa, jika Unitnya memiliki pajak progressive.")
    tagihan_birojasa_bbn_journal_id = fields.Many2one('account.journal',string="Journal BBN Beli (Aktual)",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses Tagihan Biro Jasa, Nilai yang dikeluarkan adalah Nilai BBN Beli / Tagihan dari Biro Jasa.")
    tagihan_birojasa_bbn_account_id = fields.Many2one('account.account',string="Account Pendapatan STNK BBN Beli",help="Account ini dibutuhkan saat proses Tagihan Biro Jasa, Nilai yang dikeluarkan adalah Nilai BBN Beli / Tagihan dari Biro Jasa.")
    proses_stnk_journal_bbnbeli_id = fields.Many2one('account.journal',string="Journal BBN Beli (Estimasi)",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses STNK, Nilai yang dikeluarkan adalah Nilai BBN Beli.")
    biaya_jasa_pengurusan_stnk_account_id = fields.Many2one('account.account',string="Account Biaya Jasa Perantara Pengurusan STNK",help="Account ini dibutuhkan saat proses Tagihan Biro Jasa, Nilai yang dikeluarkan adalah Biaya Jasa Perantara Pengurusan STNK.")