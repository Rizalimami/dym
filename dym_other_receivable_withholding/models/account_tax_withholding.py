# -*- coding: utf-8 -*-
from openerp import models, fields, api, SUPERUSER_ID
import openerp.addons.decimal_precision as dp
import openerp

class account_tax_withholding(models.Model):
    _inherit = "account.tax.withholding"

    is_other_receivable = fields.Boolean('Is Other Receivable')