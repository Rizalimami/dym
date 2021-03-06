from openerp import models, fields, api

class dym_branch_config(models.Model):
    _inherit = "dym.branch.config"
    
    offtr_to_ontr_bbn_jual_journal_id = fields.Many2one('account.journal',string="Journal BBN Jual",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses pengurusan STNK & BPKB Unit Off The Road ke On The Road , hasilnya akan menjadi Customer Invoice dengan nama Customer 'Biro Jasa' yang dipilih")
    offtr_to_ontr_bbn_jual_account_id = fields.Many2one('account.account',string="Accont BBN Jual", help="Account ini dibutuhkan saat proses pengurusan STNK & BPKB Unit Off The Road ke On The Road , hasilnya akan menjadi Customer Invoice dengan nama Customer 'Biro Jasa' yang dipilih")
    offtr_to_ontr_bbn_beli_journal_id = fields.Many2one('account.journal',string="Journal BBN Beli",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses pengurusan STNK & BPKB Unit Off The Road ke On The Road, hasilnya akan menjadi Supplier Invoice per masing masing no engine ")
    