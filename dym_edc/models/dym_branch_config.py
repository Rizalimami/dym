import time
from datetime import datetime
from openerp import models, fields, api

class dym_branch_config(models.Model):
    _inherit = "dym.branch.config"
    
    disburesement_pl_account_id = fields.Many2one('account.account',string="Account PL Disbursement",domain=[('type','=','other')],help="Account ini prefix(799)")
    max_difference = fields.Float(string="Max Difference Amount")
    