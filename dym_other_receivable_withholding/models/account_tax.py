# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp

class account_tax(models.Model):
    _inherit = "account.tax"

    # def _compute(self, cr, uid, taxes, price_unit, quantity, product=None, partner=None, precision=None):
    #     print "==========compute----tax------"
    #     """
    #     Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.

    #     RETURN:
    #         [ tax ]
    #         tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
    #         one tax for each tax id in IDS and their children
    #     """
    #     if not precision:
    #         precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
    #     res = self._unit_compute(cr, uid, taxes, price_unit, product, partner, quantity)
    #     total = 0.0
    #     for r in res:
    #         if r.get('balance',False):
    #             r['amount'] = round(r.get('balance', 0.0) * quantity, precision) - total
    #         else:
    #             r['amount'] = round(r.get('amount', 0.0) * quantity, precision)
    #             total += r['amount']
    #     return res
