import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class account_account(models.Model):
    _inherit = "account.account"
        
    is_bon_sementara = fields.Boolean('Bon Sementara')
