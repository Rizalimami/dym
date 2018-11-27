# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api, _

class res_company(models.Model):
    _inherit = "res.company"

    max_tax_amount_diff = fields.Float(string="Max Tax Diff Acount", default="10.0", help="This amount is a limit of different tax amount between tax amount calculated based on formula (tax based * tax rate) and tax amount supplied by vendor where thoese amount may be different.")
