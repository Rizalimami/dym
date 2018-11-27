# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _

class AccountTax(models.Model):
    _inherit = 'account.tax'

    type_tax_use2 = fields.Selection([('trade','Trade'),('non-trade','Non Trade'),('all','All')], 'Tax Usage', default='trade', required=True)
