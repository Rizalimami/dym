import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _

class AccountTax(models.Model):
    _inherit = "account.tax"

    branch_exceptions = fields.Many2many('dym.branch', 'dym_tax_exception_branch_rel','tax_id','branch_id', string='Branch Exception', help='Company branch(es) where this tax would not be applied!')
