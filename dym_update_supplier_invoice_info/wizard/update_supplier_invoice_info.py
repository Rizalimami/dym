from openerp import fields, api, models

class update_supplier_invoice_info(models.TransientModel):

    _name = 'update.supplier.invoice.info'

    invoice_id = fields.Many2one('account.invoice', 'Invoice')
    new_number = fields.Char('Supplier Invoice Number')
    new_date = fields.Date('Supplier Invoice Date')

    @api.multi
    def action_update_info(self):
        if self.new_number:
            invoice_id = self.env['account.invoice'].browse(self._context.get('active_id', False))
            if invoice_id.move_id:
                for move_line in invoice_id.move_id.line_id:
                    if move_line.name == self.invoice_id.supplier_invoice_number:
                        move_line.write({'name': self.new_number})
            self.invoice_id.supplier_invoice_number = self.new_number

        if self.new_date:
            self.invoice_id.document_date = self.new_date