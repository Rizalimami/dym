from openerp import models, fields, api
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import netsvc
from openerp.osv import osv

class dym_account_voucher_custom(osv.osv):
    _inherit = 'account.voucher'

    def writeoff_move_line_get(self, cr, uid, voucher_id, line_total, move_id, name, company_currency, current_currency, context=None):
        res = super(dym_account_voucher_custom,self).writeoff_move_line_get(cr,uid,voucher_id,line_total,move_id,name,company_currency,current_currency,context=context)
        currency_obj = self.pool.get('res.currency')
        move_line = {}
        voucher = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        current_currency_obj = voucher.currency_id or voucher.journal_id.company_id.currency_id
        if not currency_obj.is_zero(cr, uid, current_currency_obj, line_total):
            diff = line_total
            account_id = res.get('account_id')
            if voucher.type == 'receipt' or voucher.type == 'payment':
                if voucher.writeoff_amount <= -10:
                    if voucher.partner_id.property_account_rounding and voucher.partner_id.property_account_rounding.id != voucher.writeoff_acc_id.id:
                        raise osv.except_osv(('Perhatian !'), ("Write off account harus sama dengan account rounding di partner! (%s)")%(voucher.partner_id.property_account_rounding.name))
            if voucher.type == 'receipt':
                account_id = voucher.partner_id.property_account_rounding.id
            elif voucher.type == 'payment':
                account_id = voucher.partner_id.property_account_rounding.id
            elif voucher.type == 'sale':
                account_id = voucher.partner_id.property_account_rounding.id
            elif voucher.type == 'purchase':
                account_id = voucher.partner_id.property_account_rounding.id
            if not account_id and voucher.writeoff_acc_id:
                account_id = voucher.writeoff_acc_id.id
            if not account_id:
                acc_rp_id = self.pool.get('account.account').search(cr, uid, [('code','=','7200008'),('company_id','=',voucher.company_id.id)])
                if acc_rp_id:
                    account_id = acc_rp_id[0]
            if voucher.alokasi_cd:
                acc_rp_id = self.pool.get('account.account').search(cr, uid, [('code','=','2105020'),('company_id','=',voucher.company_id.id)])
                if acc_rp_id:
                    account_id = acc_rp_id[0]
            if not account_id:
                raise osv.except_osv(('Perhatian !'), ("Mohon lengkapi account rounding partner xx %s !")%(voucher.partner_id.name))  
            res.update({'account_id':account_id})    
            res.update({'analytic_account_id':voucher.analytic_4.id})    
            vouc=self.pool.get('account.voucher').browse(cr,uid,voucher_id)
            if vouc.inter_branch_id:
                branch=vouc.inter_branch_id
                if vouc.inter_branch_division:
                    division=vouc.inter_branch_division
                else:
                    division=vouc.division
            else:
                branch=vouc.branch_id
                division=vouc.division
            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch.id, division, False, 4, 'General')        
            res.update({'analytic_account_id':analytic_4})
        return res
