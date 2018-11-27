# -*- coding: utf-8 -*-
from openerp import fields, api, models, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv
import time

class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    payment_multi = fields.Boolean('Payment Multi', default=False)
    branch_type = fields.Selection(related='branch_id.branch_type')

class AccountVoucherLine(models.Model):
    _inherit = 'account.voucher.line'

    payment_multi = fields.Boolean(related='voucher_id.payment_multi', string="Multi Payment",readonly=1)

    @api.one
    @api.onchange('move_line_id')
    def onchange_move_line_id(self, ids, move_line_id, amount, currency_id, journal, partner_id=False, division=False, inter_branch_id=False, due_date_payment=False, supplier_payment=False, customer_payment=False, kwitansi=False, bawah=False):


        # print "onchange_move_line_id=============", self.env.user.branch_type, "amount==",amount, "currency_id==",currency_id, "division==",division, "inter_branch_id--",inter_branch_id,"due_date_payment=",due_date_payment,"supplier_payment=",supplier_payment,"customer_payment=",customer_payment,"kwitansi=",kwitansi,"bawah=",bawah

        res = super(AccountVoucherLine,self).onchange_move_line_id(move_line_id, amount, currency_id, journal, partner_id=partner_id, division=division, inter_branch_id=inter_branch_id, due_date_payment=due_date_payment, supplier_payment=supplier_payment, customer_payment=customer_payment, kwitansi=kwitansi, bawah=bawah)
        payment_multi = self.env.context.get('payment_multi',False)

        print "@@@@@@@@@@@@------------",self.voucher_id.payment_multi
        # print "---------payment_multi----->",payment_multi, " ========= ",self.env.user.branch_type

        if not payment_multi or self.env.user.branch_type != 'HO':
            return res
        if all([payment_multi,supplier_payment]):
            move_line_domain = []
            for dmli in res['domain']['move_line_id']:
                if tuple==type(dmli):
                    k,o,v = dmli
                    if k in ['branch_id','division']:
                        continue
                move_line_domain.append(dmli)
            res['domain']['move_line_id'] = move_line_domain
        # print "--------------",res['domain']['move_line_id']
        return res
