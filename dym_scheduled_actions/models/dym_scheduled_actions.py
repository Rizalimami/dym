from openerp import models, fields, api

class dym_scheduled_actions(models.Model):
    _name = "dym.scheduled.actions"
    
    
    ## Reset Monthly Sequence
    ## Expected runs on First Day of Every Month
    @api.multi
    def action_reset_sequence(self):
        sequences = self.env['ir.sequence'].search(['|',('prefix','like','%(month)s%'),('suffix','like','%(month)s%')])
        sequences.write({'number_next_actual':1})
    
    