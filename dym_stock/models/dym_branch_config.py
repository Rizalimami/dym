from openerp import models, fields, api, _

class dym_branch_config(models.Model):
    _inherit = 'dym.branch.config'
    freight_cost_journal_id = fields.Many2one('account.journal', string='Jurnal Hutang Ekspedisi', help='Jurnal hutang ekspedisi untuk pembelian main dealer')
    