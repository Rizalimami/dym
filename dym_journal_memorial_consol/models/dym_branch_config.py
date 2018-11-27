import time
from datetime import datetime
from openerp import models, fields, api

class res_company(models.Model):
    _inherit = "res.company"
    
    journal_memorial_journal_consol_id = fields.Many2one('account.journal',string="Journal Memorial Consolidation",domain="[('type','!=','view')]",help="Journal ini dibutuhkan dalam transaksi journal memorial consolidation")
    