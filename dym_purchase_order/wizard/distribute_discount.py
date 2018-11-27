
from openerp import models, fields, api, _, workflow, SUPERUSER_ID
import openerp.addons.decimal_precision as dp

class PurchaseDiscountDistribute(models.TransientModel):

    _name = "purchase.discount.distribute"

    discount_amount = fields.Float(string='Discount Amount', digits=dp.get_precision('Account'))
    discount_type = fields.Selection([
	('discount','Discount'),
        ('discount_program','Discount Program'),
        ('discount_cash','Discount Cash'),
        ('discount_lain','Discount Lain'),
        ], string="Discount Type", default="discount_program")
    invoice_id = fields.Many2one('account.invoice', string='Invoice Reference')
    invoice_line = fields.One2many("purchase.discount.distribute.invoice","distribute_id")

    @api.model
    def default_get(self, fields):
        res = super(PurchaseDiscountDistribute, self).default_get(fields)
        active_id = self._context.get('active_id', None)
        if not active_id:
            return res

        res['invoice_id'] = active_id
        invoice = self.env['account.invoice'].browse([active_id])
        lines = []
        for line in invoice.invoice_line:
            print line.product_id.name
            lines.append((0,0,{
                'product_id':line.product_id.id,
                'selected': True,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'sequence': line.sequence,
                'quantity': line.quantity,
                'invoice_line_id':line.id,
            }))
        res['invoice_line'] = lines
        return res

    @api.onchange('discount_amount')
    def _onchange_discount_amount(self):
        total_invoice = sum([line.price_subtotal for line in self.invoice_line])
        total_qty = sum([line.quantity for line in self.invoice_line])
        for line in self.invoice_line:
            line.discount = line.price_subtotal / total_invoice * self.discount_amount

    @api.multi
    def distribute_it(self):
        for line in self.invoice_line:
            if self.discount_type=='discount_program':
                line.invoice_line_id.discount_program = line.discount
            if self.discount_type=='discount_cash':
                line.invoice_line_id.discount_cash = line.discount
            if self.discount_type=='discount_lain':
                line.invoice_line_id.discount_lain = line.discount
	    if self.discount_type=='discount':
                line.invoice_line_id.discount_amount = line.discount

class PurchaseDiscountDistributeInvoice(models.TransientModel):

    _name = "purchase.discount.distribute.invoice"
    _order = 'sequence'

    distribute_id = fields.Many2one("purchase.discount.distribute", string="Distribute")
    sequence = fields.Integer(string='Sequence', default=10,
        help="Gives the sequence of this line when displaying the invoice.")
    invoice_id = fields.Many2one('account.invoice', string='Invoice Reference',
        ondelete='cascade', index=True)
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice Line',
        ondelete='cascade', index=True)
    uos_id = fields.Many2one('product.uom', string='Unit of Measure',
        ondelete='set null', index=True)
    product_id = fields.Many2one('product.product', string='Product',
        ondelete='restrict', index=True)
    price_unit = fields.Float(string='Unit Price', required=True,
        digits= dp.get_precision('Product Price'))
    price_subtotal = fields.Float(string='Amount', digits= dp.get_precision('Account'),
        store=True, readonly=True)
    quantity = fields.Float(string='Quantity', digits= dp.get_precision('Product Unit of Measure'),
        required=True, default=1)
    discount = fields.Float(string='Discount', digits= dp.get_precision('Discount'),
        default=0.0)
