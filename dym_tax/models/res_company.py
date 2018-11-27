from openerp import models, fields, api, SUPERUSER_ID
from openerp.osv import osv
from openerp.tools.translate import _

class res_company(models.Model):
    _inherit = "res.company"
    
    jenis_npwp = fields.Selection([('terpusat','Terpusat'),('percabang','Per Cabang')], string='Jenis NPWP', default='terpusat')
