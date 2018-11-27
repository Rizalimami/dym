import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

import json

class account_tax(models.Model):
    
    _inherit = "account.tax"

    def round_tax_amount(self, amount):
        tax_amount = float(int(amount))
        tax_decimal = round(amount % 1,2)
        if tax_decimal >= 0.6:
            tax_decimal = 1.0
        else:
            tax_decimal = 0.0
        res = tax_amount + tax_decimal
        return res

    '''
    @api.v7
    def compute_all(self, cr, uid, taxes, price_unit, quantity, product=None, partner=None, force_excluded=False):

        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        tax_compute_precision = precision
        if taxes and taxes[0].company_id.tax_calculation_rounding_method == 'round_globally':
            tax_compute_precision += 5
        totalin = totalex = round(price_unit * quantity, precision)
        tin = []
        tex = []
        for tax in taxes:
            if not tax.price_include or force_excluded:
                tex.append(tax)
            else:
                tin.append(tax)
        tin = self.compute_inv(cr, uid, tin, price_unit, quantity, product=product, partner=partner, precision=tax_compute_precision)
        if tin:
        	tin[0]['amount'] = self.round_tax_amount(tin[0]['amount'])
        for r in tin:
            totalex -= r.get('amount', 0.0)
        totlex_qty = 0.0
        try:
            totlex_qty = totalex/quantity
        except:
            pass
        tex = self._compute(cr, uid, tex, totlex_qty, quantity, product=product, partner=partner, precision=tax_compute_precision)
        if tex:
        	tex[0]['amount'] = self.round_tax_amount(tex[0]['amount'])
        for r in tex:
            totalin += r.get('amount', 0.0)
        values = {
            'total': totalex,
            'total_included': totalin,
            'taxes': tin + tex
        }
        return values
    '''
    