from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp

class dym_ahass_deposit(models.Model):
    _name = 'dym.ahass.deposit'

    name = fields.Char('Number')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    branch_parent_id = fields.Many2one('dym.branch',string='AHASS Parent')
    branch_ahass_id = fields.Many2one('dym.branch',string='AHASS Child')
    amount = fields.Float(string="Amount", digits_compute=dp.get_precision('Account'))
    withdrawal_ids = fields.One2many('dym.bank.transfer.ahass.deposit','deposit_ahass_id',string='Withdrawals')
