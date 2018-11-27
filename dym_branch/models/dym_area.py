from openerp import api, fields, models, SUPERUSER_ID
from openerp.tools.translate import _

class dym_area(models.Model):
    _name = 'dym.area'
    _inherit = ['mail.thread']
    _rec_name='code'

    code = fields.Char('Code',required=True)
    description = fields.Char('Description',required=True)
    branch_ids = fields.Many2many('dym.branch','dym_area_cabang_rel','area_id','branch_id','Branches',required=True)
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            tit = "[%s] %s" % (record.code, record.description)
            res.append((record.id, tit))
        return res
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Code tidak boleh ada yang sama.'),  
    ]
