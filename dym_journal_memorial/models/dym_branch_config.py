import time
from datetime import datetime
from openerp import models, fields, api

class dym_branch_config(models.Model):
    _inherit = "dym.branch.config"
    
    journal_memorial_journal_id = fields.Many2one('account.journal',string="Journal Memorial",domain="[('type','!=','view')]",help="Journal ini dibutuhkan dalam transaksi journal memorial")
    