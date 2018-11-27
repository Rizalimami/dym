from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class ConsolidateInvoice(models.Model):
    _inherit = "consolidate.invoice"

    show_picking_info = fields.Boolean('Show Picking Info', defult=False)
    picking_opbal = fields.Boolean('Picking Opbal')

    """
    @api.onchange('invoice_id')
    def onchange_invoice(self):
        domain = [
            ('picking_type_code','=','incoming'),
            ('branch_id','=',self.branch_id.id),
            ('division','=',self.division),
            ('state','=','done'),
            ('partner_id','=',self.partner_id.id),
            ('consolidated','=',False)
        ]
        res = self.invoice_id_change(self.invoice_id.id, self.partner_id.id, self.branch_id.id, self.division)
        if self.invoice_id and res.get('domain',False):
            if res['domain'].get('picking_id',False):
                picking_domain = res['domain']['picking_id']
                if type(picking_domain)==list and len(picking_domain[0])==3:
                    k,o,v = picking_domain[0]
                    if not v:
                        self.picking_id = False
                        self.show_picking_info = True
                    else:
                        self.show_picking_info = False
        return res
    """

    @api.onchange('invoice_id')
    def onchange_invoice(self):
        domain = [
            ('picking_type_code','=','incoming'),
            ('branch_id','=',self.branch_id.id),
            ('division','=',self.division),
            ('state','=','done'),
            ('partner_id','=',self.partner_id.id),
            ('consolidated','=',False)
        ]
        res = self.invoice_id_change(self.invoice_id.id, self.partner_id.id, self.branch_id.id, self.division)
        if self.invoice_id and res.get('domain',False):
            if res['domain'].get('picking_id',False):
                picking_domain = res['domain']['picking_id']
                if type(picking_domain)==list and len(picking_domain[0])==3:
                    k,o,v = picking_domain[0]
                    if not v:
                        self.picking_id = False
                        self.show_picking_info = True
                    else:
                        self.show_picking_info = False
        values = res.get('value',False)
        if values:
            self.receive_id = values.get('receive_id',False)
            self.picking_id = values.get('picking_id',False)
            self.asset = values.get('asset',False)
        return res

    @api.multi
    def write_invoice_line(self, id_invoice, purchase_line_id, qty):
        if self.picking_opbal:
            pass
        else:
            return super(ConsolidateInvoice,self).write_invoice_line(id_invoice, purchase_line_id, qty)

    @api.multi
    def create_move(self, branch_id, consolidate_line):
        res = False
        if self.picking_opbal:
            pass
        else:
            return super(ConsolidateInvoice,self).create_move(branch_id=branch_id, consolidate_line=consolidate_line)


    @api.multi
    def write_invoice_line(self, id_invoice, purchase_line_id, qty):
        res = False
        if self.picking_opbal:
            pass
        else:
            return super(ConsolidateInvoice,self).write_invoice_line(id_invoice=id_invoice, purchase_line_id=purchase_line_id, qty=qty)

    @api.multi
    def write_move_line(self, id_picking, purchase_line_id, qty):
        res = False
        if self.picking_opbal:
            pass
        else:
            return super(ConsolidateInvoice,self).write_move_line(id_picking=id_picking, purchase_line_id=purchase_line_id, qty=qty)
    
    @api.multi
    def get_sjdate(self, picking_id):
        res = False
        if self.picking_opbal:
            return 'N/A (OPBAL)'
        else:
            return super(ConsolidateInvoice,self).get_sjdate(picking_id=picking_id)


    @api.multi
    def get_grndate(self, picking_id):
        res = False
        if self.picking_opbal:
            return 'N/A (OPBAL)'
        else:
            return super(ConsolidateInvoice,self).get_grndate(picking_id=picking_id)

class ConsolidateInvoiceLine(models.Model):
    _inherit = "consolidate.invoice.line"

    show_picking_info = fields.Boolean('Show Picking Info', related='consolidate_id.show_picking_info')
    picking_opbal = fields.Boolean(' Picking Opbal', related='consolidate_id.picking_opbal')

    @api.model
    def default_get(self, fields):
        res = super(ConsolidateInvoiceLine, self).default_get(fields)
        default_picking_opbal = self.env.context.get('default_picking_opbal',False)
        if default_picking_opbal:
            res['picking_opbal'] = default_picking_opbal
        return res

    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.name and self.template_id and self.product_id:
            InvoiceLine = self.env['account.invoice.line']
            inv_line_id = InvoiceLine.search([
                ('invoice_id','=',self.consolidate_id.invoice_id.id),
                ('product_id','=',self.product_id.id),
            ], limit=1)
            if inv_line_id:
                price = (inv_line_id.price_unit * inv_line_id.quantity) - (inv_line_id.discount_amount + inv_line_id.discount_cash + inv_line_id.discount_lain + inv_line_id.discount_program)
                taxes = inv_line_id.invoice_line_tax_id.compute_all(price, 1, product=inv_line_id.product_id, partner=inv_line_id.invoice_id.partner_id)
                new_cost_price = taxes['total'] / inv_line_id.quantity                
                self.price_unit = new_cost_price
                self.price_subtotal = new_cost_price * inv_line_id.quantity
                self.product_id = self.product_id.id
                self.template_id = self.product_id.product_tmpl_id.id
                self.product_uom = self.product_id.uom_id.id
                self.product_qty = inv_line_id.quantity
                self.move_qty = inv_line_id.quantity
                self.move_qty_show = inv_line_id.quantity
                self.move_id = False

    @api.onchange('picking_opbal','name')
    def onchange_picking_opbal(self):
        InvoiceLine = self.env['account.invoice.line']
        domain = {}
        if self.picking_opbal:
            domain['name'] = [
                ('consolidate_id', '=', False),
                ('state', 'in', ['stock','reserved','intransit','sold','sold_offtr', 'paid_offtr','paid','returned']),
                ('opbal','=',True),
            ]
            if self.consolidate_id.invoice_id:
                product_ids = [i.product_id.id for i in self.consolidate_id.invoice_id.invoice_line]
                product_tmpl_ids = [i.product_id.product_tmpl_id.id for i in self.consolidate_id.invoice_id.invoice_line]
                if product_ids and product_tmpl_ids:
                    domain['template_id'] = [
                        ('id','in',product_tmpl_ids)
                    ]
                    domain['product_id'] = [
                        ('id','in',product_ids)
                    ]
                    
            if self.name and self.name.product_id:
                id_inv_line = InvoiceLine.search([
                    ('invoice_id','=',self.consolidate_id.invoice_id.id),
                    ('product_id','=',self.name.product_id.id),
                ])
                if not id_inv_line:
                    raise osv.except_osv(('Warning'),('Nomor mesin %s atas produk %s tidak ditemukan di invoice no %s' % (self.name.name,self.name.product_id.name,self.consolidate_id.invoice_id.number)))

                if len(id_inv_line)>1:
                    raise osv.except_osv(('Warning'),('Ditemukan lebih dari satu produk atas nomor mesin %s tidak ditemukan di invoice no %s' % (self.name.name,self.consolidate_id.invoice_id.number)))

                inv_line_id = id_inv_line
                price = (inv_line_id.price_unit * inv_line_id.quantity) - (inv_line_id.discount_amount + inv_line_id.discount_cash + inv_line_id.discount_lain + inv_line_id.discount_program)
                taxes = inv_line_id.invoice_line_tax_id.compute_all(price, 1, product=inv_line_id.product_id, partner=inv_line_id.invoice_id.partner_id)
                new_cost_price = taxes['total'] / inv_line_id.quantity                
                self.price_unit = new_cost_price
                self.price_subtotal = new_cost_price * 1
                self.product_id = self.name.product_id.id
                self.template_id = self.name.product_id.product_tmpl_id.id
                self.product_uom = self.name.product_id.uom_id.id
                self.product_qty = 1
                self.move_qty = 1
                self.move_qty_show = 1
                self.move_id = False
        else:
            if not self.consolidate_id.branch_id or not self.consolidate_id.division or not self.consolidate_id.invoice_id or not self.consolidate_id.partner_id and (not self.consolidate_id.picking_id or not self.consolidate_id.receive_id):
                raise osv.except_osv(('Warning'),('Silahkan lengkapi data header terlebih dahulu'))
            res = self.lot_change(
                self.consolidate_id.branch_id and self.consolidate_id.branch_id.id or False,
                self.consolidate_id.division,
                self.name,
                self.product_id and self.product_id.id or False,
                self.consolidate_id.invoice_id and self.consolidate_id.invoice_id.id or False,
                self.consolidate_id.partner_id and self.consolidate_id.partner_id.id or False,
                self.consolidate_id.picking_id and self.consolidate_id.picking_id.id or False,
                self.consolidate_id.receive_id and self.consolidate_id.receive_id.id or False,
                self.template_id and self.template_id.id or False)
            return res
        return {'domain':domain}
