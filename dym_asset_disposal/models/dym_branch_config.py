import time
from datetime import datetime
from openerp import models, fields, api

class dym_branch_config_asset_disposal(models.Model):
    _inherit = "dym.branch.config"
    
    asset_disposal_journal_id = fields.Many2one('account.journal',string="Journal Asset Disposal",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses Asset Disposal.")
    # asset_disposal_analytic_2_asset = fields.Many2one('account.analytic.account', 'Account Analytic BU Asset')
    # asset_disposal_analytic_4_asset = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center Asset')