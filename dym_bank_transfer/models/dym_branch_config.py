from openerp import models, fields, api

class dym_branch_config(models.Model):
    _inherit = "dym.branch.config"
    
    bank_transfer_fee_account_id = fields.Many2one('account.account',string="Account Bank Transfer Fee",domain=[('type','=','other')],help="Account ini.(prefix:8121)")
    bank_transfer_mit_account_id = fields.Many2one('account.account',string="Account Bank Transfer MIT")
    bank_withdrawal_mit_account_id = fields.Many2one('account.account',string="Account Bank Withdrawal MIT")
    bank_deposit_mit_account_id = fields.Many2one('account.account',string="Account Bank Deposit MIT")
    banktransfer_mit = fields.Boolean(string="Apply Money Intransit")
    bank_account_in_default = fields.Many2one('res.partner.bank', string="Defaut Bank Account IN ", help="This account will automatically selected on bank tranfer")
    bank_account_out_default = fields.Many2one('res.partner.bank', string="Defaut Bank Account OUT", help="This account will automatically selected on bank tranfer")  