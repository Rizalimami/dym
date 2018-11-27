from openerp import models, fields, api

class res_partner_bank(models.Model):
    _inherit = 'res.partner.bank'

    transaction_type = fields.Selection([('in','Bank In'),('out','Bank Out')], string='Transaction Type')
    code_supplier = fields.Char('Code Supplier')

    @api.onchange('journal_id','transaction_type')
    def onchange_journal_transaction_type(self):
        if self.journal_id and self.transaction_type:
            self.journal_id.write({'transaction_type':self.transaction_type})
