import time
from datetime import datetime
from openerp import models, fields, api

class dym_intercompany_ref(models.Model):
    _name = 'dym.intercompany.ref'

    name = fields.Char('Name')
    company_id = fields.Many2one('res.company','Company')
    model = fields.Char('Model')
    res_id = fields.Integer('Transaction ID')
    fcompany_id = fields.Many2one('res.company','Foreign Company')
    fmodel = fields.Char('Foreign Model')
    fres_id = fields.Integer('Foreign Transaction ID')
