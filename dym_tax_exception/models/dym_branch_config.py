from openerp import models, fields, api, _

class BranchConfig(models.Model):
    _inherit = 'dym.branch.config'

    free_tax = fields.Boolean('Free Tax Zone', help='Check if the branch is inside free tax zone')
