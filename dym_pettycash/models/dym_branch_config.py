import time
from datetime import datetime
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools.translate import _
class dym_branch_config(models.Model):
    _inherit = "dym.branch.config"

    petty_cash_limit = fields.Float('Petty Cash Limit', default="3000000", help="Maximum value transaction of selected petty cash")

