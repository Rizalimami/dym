# from openerp import models, fields, api, SUPERUSER_ID
# from openerp.osv import osv
# from openerp.tools.translate import _

# class dym_account_move_line(models.Model):
#     _inherit = 'account.move.line'

#     def create(self, cr, uid, vals, context=None):
#         # print "==========vals GGGGGGGG=====",context
#         if 'tax_amount' in vals and 'move_id' in vals:
#             move = self.pool.get('account.move').browse(cr, uid, [vals['move_id']], context=context)
#             # print "======move=========",move.name
#             voucher_obj = self.pool.get('account.voucher')
#             voucher_id = voucher_obj.search(cr, uid, [('number','=',move.name)], context=context)
#             if voucher_id:
#                 voucher = voucher_obj.browse(cr, uid, voucher_id, context=context)
#                 if 'NDE-G' in voucher.number and voucher.tax_id and 'tax_amount' in vals and 'credit' in vals and vals['credit']>0 and 'debit' in vals and vals['debit']==0.0:
#                     # res = voucher_obj.round_tax_amount(vals['tax_amount'])
#                     # vals['tax_amount'] = voucher.tax_amount
#                     # vals['credit'] = voucher_obj.round_tax_amount(vals['credit'])

#                     vals['tax_amount'] = voucher_obj.round_tax_amount(vals['tax_amount'])
#                     vals['credit'] = voucher_obj.round_tax_amount(vals['credit'])

                    

#                     # print "tax_amount==",vals['tax_amount'], " | credit==", vals['credit']
#                     print "========voucher.tax_amount=====>>>>",vals


#         # print vals
#         return super(dym_account_move_line, self).create(cr, uid, vals, context=context)


            
#         #     dddd
#         # if 'analytic_account_id' not in vals and 'tax_code_id' in vals and 'move_id' in vals:
#         #     last_line_id = self.search(cr, uid, [
#         #         ('move_id','=',vals['move_id']),
#         #         ('analytic_account_id','!=',False),
#         #         '|',('account_tax_id.tax_code_id','=',vals['tax_code_id']),
#         #         ('account_tax_id.ref_tax_code_id','=',vals['tax_code_id'])], limit=1, order='id desc')
#         #     if last_line_id:
#         #         last_line = self.browse(cr, uid, last_line_id)
#         #         vals['analytic_account_id'] = last_line.analytic_account_id.id

#         # line_id = super(dym_account_move_line, self).create(cr, uid, vals, context=context)
#         # line = self.browse(cr, uid, line_id)
#         # taxes = self.pool.get('account.tax').search(cr, uid, ['|',('account_paid_id','=', line.account_id.id),('account_collected_id','=', line.account_id.id)])
#         # if taxes:
#         #     if not line.period_id.company_id.partner_tax_id:
#         #         raise osv.except_osv(_('Warning!'),_("Mohon isi partner pajak di master company!."))
#         #     line.write({'partner_id':line.period_id.company_id.partner_tax_id.id})
#         # if not line.branch_id and line.analytic_account_id:
#         #     branch_id = False
#         #     if line.analytic_account_id.branch_id:
#         #         branch_id = line.analytic_account_id.branch_id.id
#         #     else:
#         #         analytic = line.analytic_account_id
#         #         while (analytic.parent_id and branch_id == False):
#         #             analytic = analytic.parent_id
#         #             if analytic.branch_id:
#         #                 branch_id = analytic.branch_id.id
#         #     if branch_id:
#         #         line.write({'branch_id':branch_id})
#         # if not line.branch_id and not line.analytic_account_id:
#         #     if line.move_id.model and line.move_id.transaction_id:
#         #         obj = self.pool.get(line.move_id.model).browse(cr, uid, line.move_id.transaction_id)
#         #         if 'branch_id' in obj and obj.sudo().branch_id:
#         #             line.write({'branch_id':obj.sudo().branch_id.id})
#         # if not line.analytic_account_id and line.invoice.account_id == line.account_id and line.invoice.analytic_4.id:
#         #     line.write({'analytic_account_id':line.invoice.analytic_4.id})
#         # return line_id