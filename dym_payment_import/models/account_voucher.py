from openerp.osv import osv, fields, orm
from openerp.addons.dym_branch.models.dym_branch import BRANCH_TYPES
 
class account_voucher(osv.osv):
    _inherit = 'account.voucher'

    _columns = {
        'payment_multi': fields.boolean('Payment Multi'),
        'branch_type': fields.related('branch_id', 'branch_type', type='selection', selection=BRANCH_TYPES, string='Branch Type'),
    }

    _defaults = {
        'payment_multi': True,
    }

    def branch_change(self, cr, uid, ids, branch, type, context=None):
        res = super(account_voucher, self).branch_change(cr, uid, ids, branch=branch, type=type, context=context)
        value = res.get('value',False)
        if not value:
            return res
        branch = self.pool.get('dym.branch').browse(cr, uid, [branch], context=context)
        branch_type = branch.branch_type
        res['value']['branch_type'] = branch_type
        return res

class dym_account_voucher_line(osv.osv):
    _inherit = "account.voucher.line"

    _columns = {
        'payment_multi': fields.related('voucher_id', 'payment_multi', type='boolean', string='Payment Multi'),
    }

    def onchange_move_line_id(self, cr, user, ids, move_line_id, amount, currency_id, journal, partner_id=False, division=False, inter_branch_id=False, due_date_payment=False, supplier_payment=False, customer_payment=False, kwitansi=False, bawah=False, branch_id=None, payment_multi=False, context=None):
        res = super(dym_account_voucher_line, self).onchange_move_line_id(cr, user, ids, move_line_id, amount, currency_id, journal, partner_id=partner_id, division=division, inter_branch_id=inter_branch_id, due_date_payment=due_date_payment, supplier_payment=supplier_payment, customer_payment=customer_payment, kwitansi=kwitansi, bawah=bawah, context=context)
        if supplier_payment==False and customer_payment==True:
            return res            
        domain = res.get('domain',False)
        if not all([branch_id,payment_multi,domain]):
            return res
        branch = self.pool.get('dym.branch').browse(cr, user, [branch_id], context=context)
        branch_type = branch.branch_type
        if branch_type != 'HO' or not 'move_line_id' in res['domain']:
            return res
        move_line_domain = []
        for dmli in res['domain']['move_line_id']:
            if tuple==type(dmli):
                k,o,v = dmli
                if k in ['branch_id','division']:
                    continue
            move_line_domain.append(dmli)
        res['domain']['move_line_id'] = move_line_domain
        return res
