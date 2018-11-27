from datetime import datetime, timedelta
from openerp import models, exceptions, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp

class dym_settlement(models.Model):
    _inherit = "dym.settlement"

    withholding_ids = fields.One2many(
        'dym.transaction.withholding',
        'settle_id',
        string='Withholdings',
        required=False,
        readonly=True,
        states={'draft': [('readonly', False)]}
        )
    withholdings_amount = fields.Float(
        'PPh',
        # digits=dp.get_precision('Account'),
        # waiting for a PR 9081 to fix computed fields translations
        # _('Withholdings Amount'),
        help=_('Amount Paid With Withholdings'),
        compute='_compute_amount',
        # compute='_get_withholdings_amount',
        digits=dp.get_precision('Account'),
    )
    total_net = fields.Float(
        'Total Tagihan (Net)',
        # waiting for a PR 9081 to fix computed fields translations
        # _('Withholdings Amount'),
        help='Importe a ser Pagado con Retenciones',
        # help=_('Amount Paid With Withholdings'),
        compute='_get_total_net',
        digits=dp.get_precision('Account'),
    )

    amountview = fields.Float('Total',
        help='Total amount view',
        digits=dp.get_precision('Account'),
    )

    @api.one
    @api.depends('withholding_ids')
    def _get_withholdings_amount(self):
        self.withholdings_amount = self.get_withholdings_amount()[self.id]
   
    @api.multi
    def get_withholdings_amount(self):
        res = {}
        for settle in self:
            withholdings_amount = sum(
                x.amount for x in settle.withholding_ids)
            res[settle.id] = withholdings_amount
        return res

    @api.one
    @api.depends('withholdings_amount')
    def _get_total_net(self):
        self.total_net = self.get_total_net()[self.id]
  
    @api.multi
    def get_total_net(self):
        res = {}
        for settle in self:
            total_net = settle.amount_total - settle.withholdings_amount
            res[settle.id] = total_net
        return res

    @api.one
    @api.depends('settlement_line.amount','withholding_ids.amount')
    def _compute_amount(self):
        self.amount_total = sum(line.amount for line in self.settlement_line)
        # for wh in self.withholding_ids:
        #     wh.tax_base = self.amount_total
        #     wh.get_tax_amount()
        self.withholdings_amount = sum(line.amount for line in self.withholding_ids)
        if self.type:
            if self.type=='kembali':
                self.amount_gap = self.amount_avp - self.amount_total + (self.withholdings_amount or 0)
                # self.amount_gap = self.amount_avp - self.amount_total
            else:
                self.amount_gap = self.amount_total - self.amount_avp - (self.withholdings_amount or 0)
        else:
            # self.amount_gap = 0 + (self.withholdings_amount or 0)
            self.amount_gap = 0