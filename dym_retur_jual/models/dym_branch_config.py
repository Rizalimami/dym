import time
from datetime import datetime
from openerp import models, fields, api

class dym_branch_config_retur(models.Model):
    _inherit = "dym.branch.config"
    
    retur_jual_dso_journal_id = fields.Many2one('account.journal',string="Journal Retur Penjualan DSO",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses retur penjualan dealer sale order.")
    retur_jual_so_journal_id = fields.Many2one('account.journal',string="Journal Retur Penjualan SO",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses retur penjualan sale order.")
    retur_jual_biaya_tambahan_retur_account_id = fields.Many2one('account.account',string="Account biaya tambahan retur jual",domain="[('type','!=','view')]",help="Account biaya tambahan retur jual.")
    retur_jual_notes = fields.Text('Warning on Retur', help='Warning on sale return')
    retur_jual_dso_pic_account_id = fields.Many2one('account.account', string="Account Retur Penjualan DSO (PIC)",domain="[('type','!=','view')]",help="Account ini dibutuhkan saat proses retur penjualan dealer sale order (PIC).")