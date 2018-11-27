import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv

class dym_branch_harga_birojasa(models.Model):
    _inherit = 'dym.branch'
    
    harga_birojasa_ids = fields.One2many('dym.harga.birojasa','branch_id',string="Harga Biro Jasa")
    
class dym_harga_biro(models.Model):
    _name = "dym.harga.birojasa"
    _description = 'Harga Biro Jasa'

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    
    branch_id = fields.Many2one('dym.branch',string="Branch", default=_get_default_branch)
    birojasa_id = fields.Many2one('res.partner',domain=[('biro_jasa','=',True)],string="Biro Jasa")
    default_birojasa = fields.Boolean(string="Default")
    harga_bbn_id = fields.Many2one('dym.harga.bbn',string="Harga Beli BBN")
    
    _sql_constraints = [
       ('code_unique', 'unique(birojasa_id,branch_id)', '`Biro Jasa` tidak boleh ada yang sama.'),  
    ]    
    