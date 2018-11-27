# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import itertools
import math
from lxml import etree

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools import float_compare
import openerp.addons.decimal_precision as dp

class account_invoice_tax(models.Model):
    _inherit = "account.invoice.tax"

    @api.multi
    def amount_change(self, amount, currency_id=False, company_id=False, date_invoice=False):
        amount_tax = sum(line.amount for line in self.invoice_id.tax_line)
        company = self.env['res.company'].browse(company_id)
        diff_amount = abs(amount_tax - amount)
        if diff_amount > company.max_tax_amount_diff:
            raise Warning(_('Perbedaan nilai pajak antara perhitungan (dpp x tarif pajak) melebihi batas yang diijinkan yaitu: Nilai perhitungan sebesar Rp. %s sedangkan nilai pajak yang dimasukkan sebesar Rp. %s sehingga selisihnya adalah Rp. %s, padahal yang diijinkan hanya sebesar Rp. %s. Silahkan hubungi bagian pajak untuk membahas masalah ini.' % ("{:,}".format(amount_tax),"{:,}".format(amount),"{:,}".format(diff_amount),"{:,}".format(company.max_tax_amount_diff))))
        if currency_id and company.currency_id:
            currency = self.env['res.currency'].browse(currency_id)
            currency = currency.with_context(date=date_invoice or fields.Date.context_today(self))
            amount = currency.compute(amount, company.currency_id, round=False)
        tax_sign = math.copysign(1, (self.tax_amount * self.amount))
        
        return {'value': {'tax_amount': amount * tax_sign}}