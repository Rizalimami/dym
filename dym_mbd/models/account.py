from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv

class account_account(models.Model):
    _inherit = "account.account"
    
    withholding_tax_ids = fields.Many2many('account.tax.withholding', 
        'account_account_withholding_tax_default_rel', 
        'account_id', 'withholding_tax_id',
        'Default Withholding Taxes')
