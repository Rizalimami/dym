import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _
import pdb

class dym_pit(models.Model):
    _name="dym.pit"
    _description="Pit"
    
    branch_id=fields.Many2one("dym.branch",string="Branch",required=True)
    name=fields.Char(string="Pit Name",required=True)
    active=fields.Boolean(string="Active", default=True)
    pit_type = fields.Selection([('Express','Express'),('Reguler','Reguler'),('Heavy','Heavy Repair'),('Booking','Booking')], 'Tipe', required=True)
    mekanik_ids = fields.Many2many('hr.employee', 'dym_pit_employee_rel', 'pit_id', 'employee_id', 'Mekanik')

    @api.constrains('pit_type','mekanik_ids')
    def _total_mekanik_available(self):
        if self.pit_type == 'Reguler' and len(self.mekanik_ids) > 1:
            raise ValidationError("Tipe pit reguler tidak boleh lebih dari 1 mekanik")

    @api.onchange('branch_id')
    def onchange_branch(self):
    	self.mekanik_ids = False
        return {}