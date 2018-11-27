import time
from datetime import datetime
from openerp import models, fields, api

class dym_branch_config_retur(models.Model):
    _inherit = "dym.branch.config"
    
    retur_beli_journal_id = fields.Many2one('account.journal',string="Journal Retur Pembelian",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses retur pembelian.")    
    account_retur_variance = fields.Many2one('account.account',string="Account Retur Variance")    