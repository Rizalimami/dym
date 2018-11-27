import time
from datetime import datetime
from openerp import models, fields, api, _
from openerp import workflow
from openerp.osv import expression

class account_voucher(models.Model):
    _inherit = "account.voucher"

    dso_id = fields.Many2one('dealer.sale.order.line', string='Dealer Sales Memo')

    @api.multi
    @api.depends('number', 'amount')
    def name_get_with_amount(self):
        res = []
        for voucher in self:
            name = "%s (%s)" % (voucher.number,'{:,.2f}'.format(voucher.amount))
            res += [(voucher.id, name)]
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        connector = '|'
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            connector = '&'
        recs = self.search([connector, ('number', operator, name), ('name', operator, name)] + args, limit=limit)
        if self.env.context.get('showme_amount',False):
            return recs.name_get_with_amount()
        return recs.name_get()
