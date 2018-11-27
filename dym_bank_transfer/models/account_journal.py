from openerp import models, fields, api

class account_journal(models.Model):
    _inherit = 'account.journal'
    _description = 'Account Journal'

    transaction_type = fields.Selection([('in','Bank In'),('out','Bank Out')], string='Transaction Type')
    ats_from_branch_ids = fields.Many2many('dym.branch', 'branch_src_id', 'branch_dst_id', string='ATS From Branch')   
