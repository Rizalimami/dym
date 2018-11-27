import time
from datetime import datetime
from openerp import models, fields, api

class dym_purchase_order(models.Model):
    _inherit = 'purchase.order'

    intercom_ref_id = fields.Many2one('dym.intercompany.ref','Intercompany Ref.', readonly=True)

    @api.model
    def wkf_confirm_order(self):
        res = super(dym_purchase_order,self).wkf_confirm_order()
        obj_ir = self.env['dym.intercompany.ref']
        ir = obj_ir.create({
                            'name': self.name,
                            'company_id': self.company_id.id,
                            'res_id': self.id,
                            'model': self._name,     
                            })
        self.intercom_ref_id = ir.id    
        return res

 