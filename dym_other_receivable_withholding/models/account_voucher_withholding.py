# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning


class account_voucher_withholding(models.Model):
    _inherit = "account.voucher.withholding"

    type_tax_use = fields.Selection(
        [('receipt', 'Receipt'), ('payment', 'Payment'), ('all', 'All')],
        'Tax Application',
        related="tax_withholding_id.type_tax_use",
        required=True
        )
