# -*- coding: utf-8 -*-

from openerp import fields, models

class OpbalCustomerDeposit(models.Model):
    _name = 'opbal.customer.deposit'

    date = fields.Date(string='Date')
    amount = fields.Float(string='Amount')
    engine_id = fields.Many2one('stock.production.lot', string='Engine Number')
    partner_id = fields.Many2one('res.partner', string='Partner')

