# import itertools
# from lxml import etree
# from datetime import datetime, timedelta
# from openerp import models, fields, api, _

# class DealerSaleOrder(models.Model):
#     _inherit = "dealer.sale.order"

#     @api.model
#     def _amount_line_tax(self, line):
#         res = super(DealerSaleOrder, self)._amount_line_tax(line)
#         for detail in line:
#             if detail.tax_id.branch_exceptions:
#                 if detail.dealer_sale_order_line_id.branch_id in detail.tax_id.branch_exceptions:
#                     return 0
#         return res
