# # -*- coding: utf-8 -*-
# ##############################################################################
# # For copyright and license notices, see __openerp__.py file in module root
# # directory
# ##############################################################################
# from openerp import models, fields, api, _
# import openerp.addons.decimal_precision as dp


# class account_voucher(models.Model):

#     _inherit = "account.voucher"

#     def round_tax_amount(self, amount):
#         tax_amount = float(int(amount))
#         tax_decimal = amount % 1
#         if tax_decimal >= 0.6:
#             tax_decimal = 1.0
#         else:
#             tax_decimal = 0.0
#         res = tax_amount + tax_decimal
#         return res

#     @api.onchange('tax_amount')
#     def onchange_tax_amount(self):
#         if self.tax_amount:
#             result = self.round_tax_amount(self.tax_amount)
#             self.tax_amount = result

#     def onchange_price(self, cr, uid, ids, line_ids, tax_id, partner_id=False, context=None):
#         res = super(account_voucher, self).onchange_price(cr, uid, ids, line_ids, tax_id, partner_id=partner_id, context=context)
#         this = self.browse(cr, uid, ids, context=context)
#         if this and res and 'NDE-G' in this.number and 'value' in res:
#             if 'tax_amount' in res['value']:
#                 result = self.round_tax_amount(res['value']['tax_amount'])
#                 res['value']['tax_amount'] = result
#         return res

#     def write(self, cr, uid, ids, vals, context=None):
#         if isinstance(ids,(int,long)):
#             ids = [ids]
#         this = self.browse(cr, uid, ids, context=context)
#         if 'NDE-G' in this.number and this.tax_id:
#             tax_total = 0.0
#             for line in this.line_cr_ids:
#                 xx = this.tax_id.compute_all(line.amount, 1)['taxes'][0]
#                 print "======xx====>>",xx
#                 # tax_total += 

#                 # for tax in line.tax_id.compute_all(price, 1, product=line.product_id, partner=val.partner_id)['taxes']:
#                 #     ppn += tax['amount']

#                 # harga_satuan = line.tax_id.compute_all(harga_satuan, 1, product=line.product_id, partner=val.partner_id)['total']

#             if 'tax_amount' in vals:
#                 tax_amount = self.round_tax_amount(vals['tax_amount'])
#                 vals['tax_amount'] = tax_amount
#                 total = 0.0
#                 for line in this.line_cr_ids:
#                     total += line.amount
#                 vals['amount'] = total + tax_amount
#         print "================================================",vals
#         res_id = super(account_voucher, self).write(cr, uid, ids, vals, context=context)
#         return res_id

#     # def compute_tax(self, cr, uid, ids, context=None):
#     #     print "====this is compute_tax ------.>"
#     #     tax_pool = self.pool.get('account.tax')
#     #     partner_pool = self.pool.get('res.partner')
#     #     position_pool = self.pool.get('account.fiscal.position')
#     #     voucher_line_pool = self.pool.get('account.voucher.line')
#     #     voucher_pool = self.pool.get('account.voucher')
#     #     if context is None: context = {}

#     #     for voucher in voucher_pool.browse(cr, uid, ids, context=context):
#     #         voucher_amount = 0.0
#     #         for line in voucher.line_ids:
#     #             voucher_amount += line.untax_amount or line.amount
#     #             line.amount = line.untax_amount or line.amount
#     #             voucher_line_pool.write(cr, uid, [line.id], {'amount':line.amount, 'untax_amount':line.untax_amount})

#     #         if not voucher.tax_id:
#     #             self.write(cr, uid, [voucher.id], {'amount':voucher_amount, 'tax_amount':0.0})
#     #             continue

#     #         tax = [tax_pool.browse(cr, uid, voucher.tax_id.id, context=context)]
#     #         partner = partner_pool.browse(cr, uid, voucher.partner_id.id, context=context) or False
#     #         taxes = position_pool.map_tax(cr, uid, partner and partner.property_account_position or False, tax, context=context)
#     #         tax = tax_pool.browse(cr, uid, taxes, context=context)

#     #         total = voucher_amount
#     #         total_tax = 0.0

#     #         if not tax[0].price_include:
#     #             for line in voucher.line_ids:
#     #                 for tax_line in tax_pool.compute_all(cr, uid, tax, line.amount, 1).get('taxes', []):
#     #                     total_tax += tax_line.get('amount', 0.0)
#     #             total += total_tax
#     #         else:
#     #             for line in voucher.line_ids:
#     #                 line_total = 0.0
#     #                 line_tax = 0.0

#     #                 for tax_line in tax_pool.compute_all(cr, uid, tax, line.untax_amount or line.amount, 1).get('taxes', []):
#     #                     line_tax += tax_line.get('amount', 0.0)
#     #                     line_total += tax_line.get('price_unit')
#     #                 total_tax += line_tax
#     #                 untax_amount = line.untax_amount or line.amount
#     #                 voucher_line_pool.write(cr, uid, [line.id], {'amount':line_total, 'untax_amount':untax_amount})

#     #         self.write(cr, uid, [voucher.id], {'amount':total, 'tax_amount':total_tax})
#     #     return True


#     # def write(self,cr,uid,ids,vals,context=None):
#     #     res = super(dym_account_voucher_custom,self).write(cr,uid,ids,vals)
#     #     value = self.browse(cr,uid,ids)
#     #     if vals.get('type') or vals.get('line_cr_ids') or vals.get('line_dr_ids') or vals.get('amount') or vals.get('writeoff_amount') or vals.get('payment_option') :
#     #         if value.type in ('sale','purchase') or (value.type =='receipt' and value.is_hutang_lain) :
#     #             if vals.get('tax_id') or vals.get('line_cr_ids') or vals.get('line_dr_ids'):
#     #                 self.compute_tax(cr,uid,ids,context) 
#     #         else :             
#     #             self.check_amount_with_or_not_writeoff(cr, uid, ids, context=context)
#     #     for voucher in value:
#     #         if voucher.is_hutang_lain :
#     #             diff_total = sum(voucher.line_cr_ids.mapped('amount')) - voucher.paid_amount
#     #             if diff_total != 0 :
#     #                 raise osv.except_osv(('Perhatian !'), ("Amount total harus sama dengan total detail"))   
#     #     return res       


#     # def voucher_move_line_create(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency, context=None):
#     #     if context is None:
#     #         context = {}
#     #     move_line_obj = self.pool.get('account.move.line')
#     #     currency_obj = self.pool.get('res.currency')
#     #     tax_obj = self.pool.get('account.tax')
#     #     tot_line = line_total
#     #     rec_lst_ids = []
#     #     date = self.read(cr, uid, [voucher_id], ['date'], context=context)[0]['date']
#     #     ctx = context.copy()
#     #     ctx.update({'date': date})
#     #     voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=ctx)
#     #     voucher_currency = voucher.journal_id.currency or voucher.company_id.currency_id
#     #     ctx.update({
#     #         'voucher_special_currency_rate': voucher_currency.rate * voucher.payment_rate ,
#     #         'voucher_special_currency': voucher.payment_rate_currency_id and voucher.payment_rate_currency_id.id or False,})
#     #     prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
#     #     obj_branch_config_search = self.pool.get('dym.branch.config').search(cr, uid, [('branch_id','=',voucher.branch_id.id)])
#     #     obj_branch_config = self.pool.get('dym.branch.config').browse(cr, uid, obj_branch_config_search)
#     #     for line in voucher.line_ids:
#     #         if not line.amount and not (line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit, precision_digits=prec) and not float_compare(line.move_line_id.debit, 0.0, precision_digits=prec)):
#     #             continue
#     #         amount = self._convert_amount(cr, uid, line.untax_amount or line.amount, voucher.id, context=ctx)
#     #         if line.amount == line.amount_unreconciled:
#     #             if not line.move_line_id:
#     #                 raise osv.except_osv(_('Wrong voucher line'),_("The invoice you are willing to pay is not valid anymore."))
#     #             sign = line.type =='dr' and -1 or 1
#     #             currency_rate_difference = sign * (line.move_line_id.amount_residual - amount)
#     #         else:
#     #             currency_rate_difference = 0.0
            
#     #         analytic_account_id = line.account_analytic_id
#     #         if line.move_line_id and line.move_line_id.analytic_account_id and (voucher.type in ('payment','receipt') and voucher.is_hutang_lain == False):
#     #             analytic_account_id = line.move_line_id.analytic_account_id

#     #         print "fasdfasdfasd====================",voucher.number

#     #         move_line = {
#     #             'unidentified_payment': voucher.unidentified_payment,
#     #             'journal_id': voucher.journal_id.id,
#     #             'period_id': voucher.period_id.id,
#     #             'name': line.name or '/',
#     #             'account_id': line.account_id.id,
#     #             'move_id': move_id,
#     #             'partner_id': voucher.partner_id.id,
#     #             'currency_id': line.move_line_id and (company_currency <> line.move_line_id.currency_id.id and line.move_line_id.currency_id.id) or False,
#     #             'analytic_account_id' : analytic_account_id.id,
#     #             'quantity': 1,
#     #             'credit': 0.0,
#     #             'debit': 0.0,
#     #             'date': voucher.date
#     #         }
#     #         if amount < 0:
#     #             amount = -amount
#     #             if line.type == 'dr':
#     #                 line.type = 'cr'
#     #             else:
#     #                 line.type = 'dr'

#     #         if (line.type=='dr'):
#     #             tot_line += amount
#     #             move_line['debit'] = amount
#     #         else:
#     #             tot_line -= amount
#     #             move_line['credit'] = amount

#     #         if 'NDE-G' in voucher.number and voucher.tax_id:
#     #             print "xxxxxxx~~~~~~>",voucher.tax_amount
#     #             move_line['credit'] = voucher.tax_amount
#     #             print "============>",voucher.tax_amount

#     #         if voucher.tax_id and voucher.type in ('sale', 'purchase'):
#     #             move_line.update({
#     #                 'account_tax_id': voucher.tax_id.id,
#     #             })




#     #         foreign_currency_diff = 0.0
#     #         amount_currency = False
#     #         if line.move_line_id:
#     #             if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency:
#     #                 if line.move_line_id.currency_id.id == current_currency:
#     #                     sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
#     #                     amount_currency = sign * (line.amount)
#     #                 else:
#     #                     amount_currency = currency_obj.compute(cr, uid, company_currency, line.move_line_id.currency_id.id, move_line['debit']-move_line['credit'], context=ctx)
#     #             if line.amount == line.amount_unreconciled:
#     #                 foreign_currency_diff = line.move_line_id.amount_residual_currency - abs(amount_currency)

#     #         move_line['amount_currency'] = amount_currency
#     #         print "--------move_line--",move_line
#     #         voucher_line = move_line_obj.create(cr, uid, move_line)
#     #         rec_ids = [voucher_line, line.move_line_id.id]

#     #         if line.move_line_id and line.move_line_id.currency_id and not currency_obj.is_zero(cr, uid, line.move_line_id.currency_id, foreign_currency_diff):
#     #             move_line_foreign_currency = {
#     #                 'journal_id': line.voucher_id.journal_id.id,
#     #                 'period_id': line.voucher_id.period_id.id,
#     #                 'name': _('change')+': '+(line.name or '/'),
#     #                 'account_id': line.account_id.id,
#     #                 'move_id': move_id,
#     #                 'partner_id': line.voucher_id.partner_id.id,
#     #                 'currency_id': line.move_line_id.currency_id.id,
#     #                 'amount_currency': -1 * foreign_currency_diff,
#     #                 'quantity': 1,
#     #                 'credit': 0.0,
#     #                 'debit': 0.0,
#     #                 'date': line.voucher_id.date,
#     #             }
#     #             new_id = move_line_obj.create(cr, uid, move_line_foreign_currency, context=context)
#     #             rec_ids.append(new_id)
#     #         if line.move_line_id.id:
#     #             rec_lst_ids.append(rec_ids)
#     #     voucher = (tot_line, rec_lst_ids)
#     #     vals = self.browse(cr,uid,voucher_id)
#     #     move_line = self.pool.get('account.move.line')
#     #     move_obj = self.pool.get('account.move.line')
#     #     if vals.type in ('receipt', 'payment') :
#     #         if vals.inter_branch_id :
#     #             inter_branch = vals.inter_branch_id.id
#     #         else :
#     #             inter_branch = vals.branch_id.id          
#     #         move_ids = []
#     #         for x in voucher[1] :
#     #             move_ids += x
#     #         move_browse = move_obj.browse(cr,uid,move_ids)
#     #         for value in move_browse :
#     #             if value.move_id.id != move_id :
#     #                 continue
#     #             if vals.type == 'receipt' :
#     #                 if value.account_id.type == 'payable' :
#     #                     value.write({'branch_id':vals.branch_id.id,'division':vals.division})
#     #                 elif not inter_branch:
#     #                     value.write({'branch_id':move_browse.branch_id.id,'division':vals.division})
#     #                 else:
#     #                     value.write({'branch_id':inter_branch,'division':vals.division})
#     #             elif vals.type == 'payment' :
#     #                 if value.account_id.type == 'receivable' :
#     #                     value.write({'branch_id':vals.branch_id.id,'division':vals.division})
#     #                 elif not inter_branch:
#     #                     value.write({'branch_id':move_browse.branch_id.id,'division':vals.division})
#     #                 else :
#     #                     value.write({'branch_id':inter_branch,'division':vals.division})
#     #     return voucher   
    

#     # def action_move_line_create(self, cr, uid, ids, context=None):

#     #     if context is None:
#     #         context = {}
#     #     move_pool = self.pool.get('account.move')
#     #     move_line_pool = self.pool.get('account.move.line')
#     #     for voucher in self.browse(cr, uid, ids, context=context):
#     #         local_context = dict(
#     #             context, force_company=voucher.journal_id.company_id.id)
#     #         if voucher.move_id:
#     #             continue
#     #         company_currency = self._get_company_currency(
#     #             cr, uid, voucher.id, context)
#     #         current_currency = self._get_current_currency(
#     #             cr, uid, voucher.id, context)
#     #         context = self._sel_context(cr, uid, voucher.id, context)
#     #         ctx = context.copy()
#     #         ctx.update({'date': voucher.value_date})
#     #         move_id = move_pool.create(cr, uid, self.account_move_get(
#     #             cr, uid, voucher.id, context=context), context=context)
#     #         name = move_pool.browse(cr, uid, move_id, context=context).name
#     #         line_total = self.paylines_moves_create(
#     #             cr, uid, voucher, move_id, company_currency,
#     #             current_currency, context)
#     #         rec_list_ids = []
#     #         if voucher.type == 'sale':
#     #             line_total = line_total - \
#     #                 self._convert_amount(
#     #                     cr, uid, voucher.tax_amount, voucher.id, context=ctx)
#     #         elif voucher.type == 'purchase':
#     #             line_total = line_total + \
#     #                 self._convert_amount(
#     #                     cr, uid, voucher.tax_amount, voucher.id, context=ctx)
#     #         line_total, rec_list_ids = self.voucher_move_line_create(
#     #             cr, uid, voucher.id, line_total, move_id, company_currency, current_currency, context)
#     #         ml_writeoff = self.writeoff_move_line_get(
#     #             cr, uid, voucher.id, line_total, move_id, name, company_currency, current_currency, local_context)
#     #         if ml_writeoff:
#     #             move_line_pool.create(cr, uid, ml_writeoff, local_context)
#     #         self.write(cr, uid, [voucher.id], {
#     #             'move_id': move_id,
#     #             'state': 'posted',
#     #             'number': name,
#     #         })
#     #         # the_move = move_pool.browse(cr, uid, move_id, context=context)
#     #         # if 'NDE-G' in voucher.number and voucher.tax_id:
#     #         #     for lin in the_move.line_id:
#     #         #         if voucher.tax_id.account_collected_id.id == lin.account_id.id and lin.credit > 0.0 and lin.debit==0.0:
#     #         #             if lin.credit != voucher.tax_amount:
#     #         #                 move_line_pool.write(cr, uid, [lin.id], {'credit':voucher.tax_amount})
#     #         if voucher.journal_id.entry_posted:
#     #             move_pool.post(cr, uid, [move_id], context={})
            
#     #         # We automatically reconcile the account move lines.
#     #         reconcile = False
#     #         for rec_ids in rec_list_ids:
#     #             if len(rec_ids) >= 2:
#     #                 reconcile = move_line_pool.reconcile_partial(
#     #                     cr, uid, rec_ids, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id)
#     #     return True

