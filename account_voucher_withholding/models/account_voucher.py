# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp


class account_voucher(models.Model):

    _inherit = "account.voucher"

    withholding_ids = fields.One2many(
        'account.voucher.withholding',
        'voucher_id',
        string='Withholdings',
        required=False,
        readonly=True,
        states={'draft': [('readonly', False)]}
        )
    withholdings_amount = fields.Float(
        'PPh',
        # waiting for a PR 9081 to fix computed fields translations
        # _('Withholdings Amount'),
        help='Importe a ser Pagado con Retenciones',
        # help=_('Amount Paid With Withholdings'),
        compute='_get_withholdings_amount',
        digits=dp.get_precision('Account'),
    )
    amountview = fields.Float('Total',
        help='Total amount view',
        digits=dp.get_precision('Account'),
    )

    is_group_customer = fields.Boolean('Group Customer', related='partner_id.is_group_customer')

    @api.onchange('net_amount')
    def onchange_amount_total_view(self):
        self.amountview = self.net_amount

    @api.one
    @api.depends(
        'withholding_ids',
        )
    def _get_withholdings_amount(self):
        self.withholdings_amount = self.get_withholdings_amount()[self.id]
        # We force the update of paylines and amount
        self._get_paylines_amount()
        self._get_amount(inverse=True)

    @api.multi
    def get_withholdings_amount(self):
        res = {}
        for voucher in self:
            withholdings_amount = sum(
                x.amount for x in voucher.withholding_ids)
            res[voucher.id] = withholdings_amount
        return res

    @api.multi
    def get_paylines_amount(self):
        res = super(account_voucher, self).get_paylines_amount()
        for voucher in self:
            withholdings_amount = voucher.get_withholdings_amount()[voucher.id]
            res[voucher.id] = res[voucher.id] + withholdings_amount
        return res

    @api.model
    def paylines_moves_create(
            self, voucher, move_id, company_currency, current_currency):
        paylines_total = super(account_voucher, self).paylines_moves_create(
            voucher, move_id, company_currency, current_currency)
        withholding_total = self.create_withholding_lines(
            voucher, move_id, company_currency, current_currency)
        return paylines_total + withholding_total

    # TODO ver si en vez de usar api.model usamos self y no pasamos el voucher
    # TODO ver que todo esto solo funcione en payment y receipts y no en sale y purchase
    @api.model
    def create_withholding_lines(
            self, voucher, move_id, company_currency, current_currency):
        move_lines = self.env['account.move.line']
        withholding_total = 0.0
        for line in voucher.withholding_ids:
            dom_vcr_line = [('voucher_id','=',voucher.id),('amount','=',line.tax_base)]
            if line.branch_id:
                dom_vcr_line.append(('branch_dest_id','=',line.branch_id.id))
            voucher_line = self.env['account.voucher.line'].search(dom_vcr_line)
            voucher_line = voucher_line if len(voucher_line)==1 else {}
                
            description = line.comment or voucher_line.name if voucher_line else False or line.tax_withholding_id.description
            name = '%s: %s' % (description, line.internal_number)
            if line.name:
                name += ' (%s)' % line.name
            payment_date = False
            amount = line.amount
            if amount >= 0:
                account = line.tax_withholding_id.account_id
            else:
                account = line.tax_withholding_id.ref_account_id
            # partner = voucher.partner_id
            partner = self.env['res.partner'].search([('kas_negara','=',True)])
            move_line = move_lines.create(
                self.prepare_move_line(
                    voucher, amount, move_id, name, company_currency,
                    current_currency, payment_date, account, partner)
                    )
            line.move_line_id = move_line.id
            if voucher.line_dr_ids and voucher.type == 'payment':
                move_line.update({
                    'analytic_account_id':voucher.line_dr_ids[0].move_line_id.analytic_account_id.id,
                    'branch_id':voucher.line_dr_ids[0].move_line_id.branch_id.id,
                    'division':voucher.line_dr_ids[0].move_line_id.division,
                    })
            elif voucher.line_dr_ids and voucher.type == 'purchase':
                if voucher_line:
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(voucher_line.analytic_3.branch_id.id, voucher_line.analytic_2.bisnis_unit.name, False, 4, 'General')
                move_line.update({
                    'analytic_account_id':analytic_4 if voucher_line else voucher.analytic_4.id,
                    'branch_id':line.branch_id.id or voucher.branch_id.id,
                    'division':voucher_line.division_dest_id if voucher_line else voucher.division,
                    })
            elif voucher.line_cr_ids and voucher.type == 'receipt':
                move_line.update({
                    'analytic_account_id':voucher.line_cr_ids[0].move_line_id.analytic_account_id.id,
                    'branch_id':voucher.line_cr_ids[0].move_line_id.branch_id.id,
                    'division':voucher.line_cr_ids[0].move_line_id.division,
                    })
            move_line.update({
                'tax_code_id': line.tax_withholding_id.tax_code_id.id,
                'tax_amount': amount,
                })
            dom_vcr_line = [('voucher_id','=',voucher.id),('amount','=',line.tax_base)]
            if line.branch_id:
                dom_vcr_line.append(('branch_dest_id','=',line.branch_id.id))
            voucher_line = self.env['account.voucher.line'].search(dom_vcr_line)
            voucher_line = voucher_line if len(voucher_line)==1 else {}
                
            description = line.comment or voucher_line.name if voucher_line else False or line.tax_withholding_id.description
            name = '%s: %s' % (description, line.internal_number)
            if line.name:
                name += ' (%s)' % line.name
            withholding_total += move_line.debit - move_line.credit
        return withholding_total

    # def get_discount_amount(self,cr,uid,ids,wor_ref,sor_ref,dso_ref):
    #     obj_wor=self.pool.get('dym.work.order')
    #     obj_sor=self.pool.get('sale.order')
    #     obj_dso=self.pool.get('dealer.sale.order')
    #     res = {
    #             'discount_service':0,
    #             'discount_part':0,
    #             'discount_acc':0,
    #             'discount_unit':0,
    #         }
    #     if wor_ref:
    #         wor_ids = obj_wor.search(cr,uid,[('name','=',wor_ref)])
    #         if wor_ids and len(wor_ids)==1:
    #             wor=obj_wor.browse(cr,uid,wor_ids)
    #             for line in wor.work_lines:
    #                 summary_discount = line.discount + line.discount_program + line.discount_bundle
    #                 if summary_discount > 0: 
    #                     if line.categ_id == 'Service':
    #                         res['discount_service'] += summary_discount /1.1 #Untaxed Discount Service
    #                     elif line.categ_id == 'Sparepart':
    #                         if line.categ_id_2.bisnis_unit:
    #                             res['discount_acc'] += summary_discount /1.1 #Untaxed Discount Acc
    #                         else:
    #                             res['discount_part'] += summary_discount /1.1 #Untaxed Discount Part
        
    #     if sor_ref:
    #         sor_ids = obj_sor.search(cr,uid,[('name','=',sor_ref)])
    #         if sor_ids and len(sor_ids)==1:
    #             sor=obj_sor.browse(cr,uid,sor_ids)
    #             for line in sor.order_line:
    #                 summary_discount = line.discount + line.discount_lain + line.discount_program + line.discount_bundle
    #                 if summary_discount > 0: 
    #                     if line.categ_id.bisnis_unit:
    #                         res['discount_acc'] += summary_discount /1.1 #Untaxed Discount Acc
    #                     else:
    #                         res['discount_part'] += summary_discount /1.1 #Untaxed Discount Part

    #     if dso_ref:
    #         dso_ids = obj_dso.search(cr,uid,[('name','=',dso_ref)])
    #         if dso_ids and len(dso_ids)==1:
    #             dso=obj_dso.browse(cr,uid,dso_ids)
    #             for line in dso.dealer_sale_order_line:
    #                 summary_discount = line.discount_total
    #                 if summary_discount > 0: 
    #                     res['discount_unit'] += summary_discount /1.1 #Untaxed Discount Unit

    #     return res
 
    def generate_withholding_tax(self,cr,uid,ids,context=None):
        val=self.browse(cr,uid,ids)
        obj_branch_conf=self.pool.get('dym.branch.config')
        obj_tax=self.pool.get('account.tax')
        obj_wh_tax=self.pool.get('account.tax.withholding')
        obj_voucher_wh_tax=self.pool.get('account.voucher.withholding')
        withholding=0

        if val.withholding_ids:
            for wh in val.withholding_ids:
                wh.unlink()
                
        if val.inter_branch_id:
            branch=val.inter_branch_id
        else:
            branch=val.branch_id

        if val.type=='receipt':
            type_wh_tax='receipt'
            type_tax='purhcase'
        elif val.type=='sale':
            type_wh_tax='payment'
            type_tax='sale'

        pph23=False;pph22=False;ppn=False;limit=0
        tax_base_jasa=0;tax_base_part=0;tax_base_acc=0;tax_base_unit=0;
        analytic_jasa=0;analytic_part=0;analytic_acc=0;analytic_unit=0
        if val.partner_id.kode_pajak_id:
            if val.partner_id.is_group_customer:
                if val.partner_id.npwp:
                    pph23=obj_wh_tax.search(cr,uid,[('company_id','=',branch.company_id.id),('type_tax_use','=',type_wh_tax),('amount','=',0.02),'|',('tax_code_id.code','=','03102'),('tax_code_id.code','=','02104')])
                else:
                    pph23=obj_wh_tax.search(cr,uid,[('company_id','=',branch.company_id.id),('type_tax_use','=',type_wh_tax),('amount','=',0.04),'|',('tax_code_id.code','=','03102'),('tax_code_id.code','=','02104')])
        
                if val.partner_id.kode_pajak_id=='2' or val.partner_id.kode_pajak_id=='3':
                    pph22=obj_wh_tax.search(cr,uid,[('company_id','=',branch.company_id.id),('type_tax_use','=',type_wh_tax),('tax_code_id.code','=','03101'),('amount','=',0.015)])
                    ppn=obj_wh_tax.search(cr,uid,[('company_id','=',branch.company_id.id),('type_tax_use','=',type_wh_tax),('tax_code_id.code','=','04111'),('amount','=',0.1)])
        
        if val.line_cr_ids:
            wh_list=[]
            for line in val.line_cr_ids:
                if line.move_line_id.analytic_2.code == '210':
                    analytic_jasa = line.move_line_id.analytic_2.id
                    tax_base_jasa+=line.move_line_id.debit or line.move_line_id.credit
                elif line.move_line_id.analytic_2.code=='220':
                    analytic_part = line.move_line_id.analytic_2.id
                    tax_base_part+= line.move_line_id.debit or line.move_line_id.credit
                elif line.move_line_id.analytic_2.code=='230':
                    analytic_acc = line.move_line_id.analytic_2.id   
                    tax_base_acc+=line.move_line_id.debit or line.move_line_id.credit 
                elif line.move_line_id.analytic_2.code=='100':
                    analytic_unit = line.move_line_id.analytic_2.id
                    tax_base_unit+=line.move_line_id.debit or line.move_line_id.credit

            if tax_base_jasa:
                tax_base_jasa/=1.1
            if tax_base_unit:
                tax_base_unit/=1.1
            if tax_base_part:
                tax_base_part/=1.1
            if tax_base_acc:
                tax_base_acc/=1.1

            if pph23 and len(pph23)==1 and tax_base_jasa:
                pph = obj_wh_tax.browse(cr,uid,pph23[0])
                tax_base_jasa/=1.1
                wh_list.append({
                                'tax_withholding_id':pph.id,
                                'partner_id':val.partner_id.id,
                                'date':val.date,
                                'company_id':branch.company_id.id,
                                'voucher_id':val.id,
                                'tax_base':tax_base_jasa,
                                'amount':tax_base_jasa * pph.amount,
                                'analytic_2':analytic_jasa,     
                               })
              
            if pph22 and len(pph22)==1:
                pph = obj_wh_tax.browse(cr,uid,pph22[0])
                if val.partner_id.kode_pajak_id=='2':
                    limit=pph.limit_instansi
                elif val.partner_id.kode_pajak_id=='3':
                    limit=pph.limit_bumn
                if tax_base_part and (tax_base_part + tax_base_acc) > limit and val.partner_id.kode_pajak_id=='2' :
                    wh_list.append({
                                    'tax_withholding_id':pph.id,
                                    'partner_id':val.partner_id.id,
                                    'date':val.date,
                                    'company_id':branch.company_id.id,
                                    'voucher_id':val.id,
                                    'tax_base':tax_base_part,
                                    'amount':tax_base_part * pph.amount,
                                    'analytic_2':analytic_part,     
                                   })
                   
                if tax_base_acc and (tax_base_part + tax_base_acc) > limit and val.partner_id.kode_pajak_id=='2':
                    wh_list.append({
                                    'tax_withholding_id':pph.id,
                                    'partner_id':val.partner_id.id,
                                    'date':val.date,
                                    'company_id':branch.company_id.id,
                                    'voucher_id':val.id,
                                    'tax_base':tax_base_acc,
                                    'amount':tax_base_acc * pph.amount,
                                    'analytic_2':analytic_acc,     
                                   })
                    
                if tax_base_unit and tax_base_unit > limit and val.partner_id.kode_pajak_id=='2':
                    wh_list.append({
                                    'tax_withholding_id':pph.id,
                                    'partner_id':val.partner_id.id,
                                    'date':val.date,
                                    'company_id':branch.company_id.id,
                                    'voucher_id':val.id,
                                    'tax_base':tax_base_unit,
                                    'amount':tax_base_unit * pph.amount,
                                    'analytic_2':analytic_unit,     
                                   })
                    
            if ppn and len(ppn)==1:
                ppn = obj_wh_tax.browse(cr,uid,ppn[0])
                if val.partner_id.kode_pajak_id=='2':
                    limit=ppn.limit_instansi
                elif val.partner_id.kode_pajak_id=='3':
                    limit=ppn.limit_bumn
                if tax_base_jasa and (tax_base_jasa + tax_base_part + tax_base_acc) > limit:
                    wh_list.append({
                                'tax_withholding_id':ppn.id,
                                'partner_id':val.partner_id.id,
                                'date':val.date,
                                'company_id':branch.company_id.id,
                                'voucher_id':val.id,
                                'tax_base':tax_base_jasa,
                                'amount':tax_base_jasa * ppn.amount,
                                'analytic_2':analytic_jasa,     
                               })
            
                if tax_base_part and (tax_base_jasa + tax_base_part + tax_base_acc) > limit:
                    wh_list.append({
                                'tax_withholding_id':ppn.id,
                                'partner_id':val.partner_id.id,
                                'date':val.date,
                                'company_id':branch.company_id.id,
                                'voucher_id':val.id,
                                'tax_base':tax_base_part,
                                'amount':tax_base_part * ppn.amount,
                                'analytic_2':analytic_part,     
                               })
                    
                if tax_base_acc and (tax_base_jasa + tax_base_part + tax_base_acc) > limit:
                    wh_list.append({
                                'tax_withholding_id':ppn.id,
                                'partner_id':val.partner_id.id,
                                'date':val.date,
                                'company_id':branch.company_id.id,
                                'voucher_id':val.id,
                                'tax_base':tax_base_acc,
                                'amount':tax_base_acc * ppn.amount,
                                'analytic_2':analytic_acc,     
                               })
                    
                if tax_base_unit and tax_base_unit > limit:
                    wh_list.append({
                                'tax_withholding_id':ppn.id,
                                'partner_id':val.partner_id.id,
                                'date':val.date,
                                'company_id':branch.company_id.id,
                                'voucher_id':val.id,
                                'tax_base':tax_base_unit,
                                'amount':tax_base_unit * ppn.amount,
                                'analytic_2':analytic_unit,     
                               })
                    
            if wh_list:
                for wh in wh_list:
                    obj_voucher_wh_tax.create(cr,uid,wh)
                    withholding+=wh['amount']

        val.net_amount = sum([x.amount for x in val.line_cr_ids]) - withholding
        
        return True


