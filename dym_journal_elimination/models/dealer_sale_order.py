import time
from datetime import datetime
from openerp import models, fields, api

class dealer_spk(models.Model):
    _inherit = 'dealer.spk'

    intercom_ref_id = fields.Many2one('dym.intercompany.ref','Intercompany Ref.')

    @api.onchange('partner_id','partner_cabang')
    def customer_change(self):
        dom = {}
        dom_list=[]
        po_ids = []
        if self.partner_id and self.partner_cabang:
            dom_list.append(('partner_type.name','=','Konsolidasi'))
            dom_list.append(('branch_id.company_id.partner_id','=',self.partner_id.id))
            branch = self.env['dym.branch'].sudo().search([('company_id.partner_id','=',self.partner_id.id),('name','ilike',self.partner_cabang.name)])
            branch_ids=[x.id for x in branch]
            dom_list.append(('branch_id','in',branch_ids))
            po_ids = self.env['purchase.order'].sudo().search(dom_list)
            intercom_ref_ids = self.env['dym.intercompany.ref'].sudo().search([('model','=','purchase.order'),('res_id','in',[x.id for x in po_ids])])
            dom['intercom_ref_id']=[('id','in',[x.id for x in intercom_ref_ids]),('fres_id','=',False)]
        return {'domain':dom}

    @api.multi
    def action_create_so(self):
        res = super(dealer_spk,self).action_create_so()

        if self.intercom_ref_id:
            self.intercom_ref_id.write({
                    'fmodel': res._name,
                    'fres_id': res.id,
                    'fcompany_id': res.branch_id.company_id.id,
                })
            res.write({
                        'intercom_ref_id': self.intercom_ref_id.id
                })
        return res
        

class dealer_sale_order(models.Model):
    _inherit = 'dealer.sale.order'

    intercom_ref_id = fields.Many2one('dym.intercompany.ref','Intercompany Ref.')
