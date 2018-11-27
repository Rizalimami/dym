import time
from datetime import datetime
from openerp import fields, models, api

class StockPicking(models.Model):
    _inherit = "stock.picking"

    move_reason = fields.Selection([('normal','Normal'),('sale_return','Retur Beli')], default='normal')
    invoice_partner = fields.Many2one('res.partner', string='Supplier', domain=[('supplier','=',True),'|',('principle','=',True),('partner_type','=','Konsolidasi')])
    invoice_id = fields.Many2one('account.invoice', string='Supplier Invoice', domain="[('branch_id','=',branch_id),('state','=','open'),('consolidated','=',True),('division','=',division),('type','=','in_invoice'),('partner_id','=',invoice_partner)]" )

    @api.onchange('branch_id')
    def onchange_branch_id100(self):
        ctx = dict(self.env.context or {})
        menu = ctx.get('menu',False)
        if menu=='showroom':
            self.division = 'Unit'
        params = ctx.get('params',False)
        action_id = params.get('action',False)
        if action_id:
            action = self.env['ir.actions.act_window'].browse(action_id)
            if 'Internal Transfer' in action.name and self.branch_id:
                picking_id = self.env['stock.picking.type'].search([
                    ('name','=','Internal Transfers'),
                    ('branch_id','=',self.branch_id.id)
                ])
                if picking_id:
                    self.picking_type_id = picking_id.id

    @api.onchange('move_reason')
    def onchange_move_reason(self):
        if self.move_reason == 'sale_return' and self.branch_id:
            src_loc_id = self.env['stock.location'].search([
                ('branch_id','=',self.branch_id.id),
                ('name','=','SHW')])
            if src_loc_id:
                self.internal_location_id = src_loc_id.id

            dst_loc_id = self.env['stock.location'].search([
                ('branch_id','=',self.branch_id.id),
                ('name','=','NRFS')])
            if dst_loc_id:
                self.internal_location_dest_id = dst_loc_id.id

    @api.onchange('invoice_id')
    def onchange_invoice_id(self):
        if self.invoice_id:
            move_lines = []
            for ci in self.env['consolidate.invoice'].search([('invoice_id','=',self.invoice_id.id)]):
                for line in ci.consolidate_line:
                    move_lines.append((0,0,{
                        'branch_id': self.branch_id.id,
                        'division': self.division,
                        'name': line.product_id.name_get().pop()[1] or '',
                        'product_tmpl_id': line.product_id.product_tmpl_id.id,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_id.uom_id.id,
                        'product_uom_qty': line.product_qty,
                        'location_id': self.internal_location_id.id,
                        'location_dest_id': self.internal_location_dest_id.id,
                        'picking_id': self.picking_type_id.id,
                        'price_unit': line.price_unit,
                        'invoice_state': 'none',
                        'restrict_lot_id': line.name.id,
                    }))
            self.move_lines = move_lines
