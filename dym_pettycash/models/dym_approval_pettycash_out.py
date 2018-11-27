import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc

class dym_pettycash_approval(osv.osv):
    _inherit = "dym.pettycash"
      
    _columns = {
        'approval_ids': fields.one2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
        'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),
    }
    
    _defaults ={
        'approval_state':'b'
    }
    
    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_bj = self.browse(cr, uid, ids, context=context)
        obj_matrix = self.pool.get("dym.approval.matrixbiaya")
        if not obj_bj.line_ids:
            raise osv.except_osv(('Perhatian !'), ("Engine belum diisi"))
        jml_line = 0
        for x in obj_bj.line_ids :
            jml_line += 1
        if jml_line > 1 and obj_bj.kas_bon == True:
            raise osv.except_osv(('Perhatian !'), ("PCO Kas Bon hanya boleh memiliki 1 row payment information"))
        obj_matrix.request_by_value(cr, uid, ids, obj_bj, obj_bj.amount)
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True
           
    def wkf_to_confirm(self, cr, uid, ids, context=None):
        return False

    def wkf_approval(self, cr, uid, ids, context=None):
        obj_bj = self.browse(cr, uid, ids, context=context)
        if not obj_bj.line_ids:
            raise osv.except_osv(('Perhatian !'), ("Engine belum diisi"))

        approval_sts = self.pool.get("dym.approval.matrixbiaya").approve(cr, uid, ids, obj_bj)
        if approval_sts == 1:
            if obj_bj.pay_supplier_invoice:
                invoice_id = [l.invoice_id for l in obj_bj.line_ids2 if l.invoice_id][0]
                account_id = invoice_id.account_id
                move_line_id = self.pool.get('account.move.line').search(cr, uid, [('invoice','=',invoice_id.id),('account_id','=',account_id.id)], context={})
                voucher_data = {
                    'company_id': invoice_id.company_id.id,
                    'branch_id': invoice_id.branch_id.id,
                    'partner_id': invoice_id.partner_id.id,
                    'journal_id': obj_bj.journal_id.id,
                    'division': obj_bj.division,
                    'amount': invoice_id.amount_total,
                    'net_amount': invoice_id.amount_total,
                    'account_id': account_id.id,
                    'state': 'draft',
                    'type': 'payment',
                    'analytic_2': invoice_id.analytic_2.id,
                    'analytic_3': invoice_id.analytic_3.id,
                    'analytic_4': invoice_id.analytic_4.id,
                    'line_dr_ids': [(0,0,{
                        'move_line_id': move_line_id and move_line_id[0] or False,
                        'account_id': invoice_id.account_id.id,
                        'reconcile': True,
                        'amount': invoice_id.amount_total,
                        'date_due': invoice_id.date_due,
                    })],
                    'line_cr_ids': [],
                }
                voucher_id = self.pool.get('account.voucher').create(cr, uid, voucher_data, context={})
                domain = [('pettycash_id','=',obj_bj.id)]
                voucher_line_id = self.pool.get('dym.pettycash.line').search(cr, uid, domain, context={})
                self.pool.get('dym.pettycash.line').write(cr, uid, voucher_line_id,  {'voucher_id':voucher_id}, context={})
            
            self.write(cr, uid, ids, {'approval_state':'a'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
        return True

    def has_approved(self, cr, uid, ids, *args):
        obj_bj = self.browse(cr, uid, ids)
        return obj_bj.approval_state == 'a'

    def has_rejected(self, cr, uid, ids, *args):
        obj_bj = self.browse(cr, uid, ids)
        if obj_bj.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False  

    def is_branch(self, cr, uid, ids, *args):
        obj_bj = self.browse(cr, uid, ids)
        return obj_bj.branch_id.branch_type!='HO'

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
        
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})
