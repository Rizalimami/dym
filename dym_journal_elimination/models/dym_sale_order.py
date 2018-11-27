import time
from datetime import datetime
from openerp import models, fields, api

class dym_sale_order(models.Model):
    _inherit = 'sale.order'

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

    @api.cr_uid_ids_context
    def action_button_confirm(self, cr, uid, ids, context=None):
        res = super(dym_sale_order,self).action_button_confirm(cr,uid,ids,context=context)
        val = self.browse(cr,uid,ids)
        if val.intercom_ref_id:
            val.intercom_ref_id.write({
                    'fmodel': val._name,
                    'fres_id': val.id,
                    'fcompany_id': val.branch_id.company_id.id,
                })
        return res
