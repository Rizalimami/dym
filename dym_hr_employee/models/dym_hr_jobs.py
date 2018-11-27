from openerp.osv import osv, fields
from openerp.tools.translate import _

class hr_job(osv.osv):
    _inherit = 'hr.job'
    
    _columns = {
                'group_id' : fields.many2one('res.groups',string="Group"),
                'branch_control' : fields.boolean(string='Branch Control'),
                'salesman' : fields.boolean(string='Salesman'),
                'mekanik' : fields.boolean(string='Mekanik'),
                'service_advisor' : fields.boolean(string='Service Advisor'),
                }