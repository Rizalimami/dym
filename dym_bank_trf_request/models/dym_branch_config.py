from openerp import models, fields, api, _

class dym_branch_config(models.Model):
    _inherit = 'dym.branch.config'
   
    supplier_payment_limit = fields.Float('Supplier Payment Limit', default="10000000", help="Batas maksimum nominal pembayaran ke supplier yang boleh dibayarkang langsung oleh cabang. Semua tagihan yang melebihi batas maksimum akan langsung dibayarkan oleh HO ke supplier.")
