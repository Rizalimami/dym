import time
from datetime import datetime
from openerp import models, fields, api

class dym_account_voucher(models.Model):
    _inherit = 'account.voucher'

    intercom_ref_id = fields.Many2one('dym.intercompany.ref','Intercompany Ref.', readonly=True,
                    states={'draft': [('readonly', False)]},
                    domain=[('fres_id','=',False)])

    @api.model
    def proforma_voucher(self):
        obj_ir = self.env['dym.intercompany.ref']
        res = super(dym_account_voucher,self).proforma_voucher()
        if self.intercom_ref_id:
            self.intercom_ref_id.write({
                                        'fcompany_id': self.company_id.id,
                                        'fres_id': self.id,
                                        'fmodel': self._name,
                }) 

        if self.type == 'payment' and self.payment_request_type == 'biaya' and 'TBK-' in self.number:
            ir = obj_ir.create({
                                'name': self.number,
                                'company_id': self.company_id.id,
                                'res_id': self.id,
                                'model': self._name,     
                                })
            self.intercom_ref_id = ir.id 

           

        
        return res

