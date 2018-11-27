# -*- coding: utf-8 -*-

from openerp import fields, models, api, _

class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    is_opbal = fields.Boolean('Is Opbal', help='Check if this inventory adjustment is due to opening balance procedure.')


