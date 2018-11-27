from openerp import models, fields, api, SUPERUSER_ID
from openerp.osv import osv
from openerp.tools.translate import _

class res_company(models.Model):
    _inherit = "res.company"
    
    @api.model
    def _default_get_company_initial(self):
        return 'xxx'

	initial_name = fields.Char('Initial', default=lambda self: self._default_get_company_initial())
