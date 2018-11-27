from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    incentive_date_type = fields.Selection([('current','Current'),('last_month','Last Month')], default='last_month', string='Incentive Date Type', help='Last Month = Incentive date will be posted on last day of previous month, Current = Incentive date will be posted on current date.')
    incentive_payment_type = fields.Selection([('prepaid','Pre-Paid'),('postpaid','Post-Paid')], default='prepaid', string='Incentive Payment Type', help='Pre-Paid=Leasing company drop the money before the invoice, Post-Paid: Leasing drop the money after we send them invoice.')
    use_withholding = fields.Boolean('Use Withholding', default=True)
    use_ppn = fields.Boolean('Use PPN', default=True)