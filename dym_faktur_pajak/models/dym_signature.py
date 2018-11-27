from datetime import datetime, timedelta
from openerp import models, fields, api, _

class dym_signature(models.Model):
    _name = 'dym.signature'
    _description = 'Signature Report'
    
    name = fields.Char(string="Name")
    
    _sql_constraints = [
    ('unique_model_id', 'unique(name)', 'Master data duplicate !'),
    ]    