import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv

class dym_request_platform(models.Model):
    _name = 'dym.request.platform'
    _description = 'Request Platform'

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('confirmed', 'Waiting Approval'),
        ('approved','Approved'),
        ('cancel','Cancelled')
    ] 
            
    name = fields.Char(string='Ref')
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop')], string='Division', required=True,change_default=True, select=True)    
    partner_id = fields.Many2one('res.partner',domain=[('is_customer_depo','=',True),'|','|',('customer','=',True),('dealer','=',True),('ahass','=',True)],required=True)
    current_limit_unit = fields.Float(string="Current Credit Limit Unit",readonly=True)
    current_limit_part = fields.Float(string="Current Credit Limit Sparepart",readonly=True)    
    limit  = fields.Float(string="Amount",required=True)
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    confirm_uid = fields.Many2one('res.users',string="Approved by")
    confirm_date = fields.Datetime('Approved on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    approval_field = fields.Float(string='Approval Fields')
    date = fields.Date(string='Date',default=fields.Date.context_today)
        
    @api.onchange('division','partner_id')
    def change_division(self):
        if self.partner_id :
            if self.division == 'Unit' :
                self.current_limit_unit = self.partner_id.credit_limit_unit
            if self.division == 'Sparepart' :
                self.current_limit_part = self.partner_id.credit_limit_sparepart
          
    @api.model
    def create(self,vals,context=None):
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'RP', division=False)   
        vals['date'] = datetime.today()          
        return super(dym_request_platform, self).create(vals)
        
    @api.one
    def cancel_request(self):
        self.write({'state':'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
        return True     