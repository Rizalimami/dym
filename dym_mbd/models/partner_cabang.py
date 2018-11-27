from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv

class CabangPartner(models.Model):
    _inherit = "dym.cabang.partner"
    
    code = fields.Char('Code')