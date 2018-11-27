import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _

class WorkOrderLine(models.Model):
    _inherit = "dym.work.order.line"

    @api.multi
    @api.onchange('product_id')
    def product_change(self, product_id, categ_id, branch_id, product_unit_id, kpb_ke, type, division, customer_id):
        res = super(WorkOrderLine, self).product_change(product_id, categ_id, branch_id, product_unit_id, kpb_ke, type, division, customer_id)
        branch_config_id = self.env['dym.branch.config'].search([('branch_id','=',branch_id)])

        if branch_config_id.free_tax:
            res['value']['tax_id'] = False
            res['value']['tax_id_show'] = False
        return res

class WorkOrder(models.Model):
    _inherit = "dym.work.order"

    @api.multi
    def button_dummy(self):
        for line in self.work_lines:
            branch_config_id = self.env['dym.branch.config'].search([('branch_id','=',line.branch_dummy)])

            if branch_config_id.free_tax:
                line.tax_id = False
        res = super(WorkOrder, self).button_dummy()
        return res