import json
from datetime import datetime
from openerp.osv import fields, osv

import logging
_logger = logging.getLogger(__name__)

class dym_work_order(osv.osv):
    _inherit = "dym.work.order"

    def create_cpa(self, cr, uid, ids, ar_ids, analytic_1, analytic_2, analytic_3, analytic_4, context=None):
        AccountMoveLine = self.pool.get('account.move.line')
        AccountJournal = self.pool.get('account.journal')
        Voucher = self.pool.get('account.voucher')
        PartnerType = self.pool.get('dym.partner.type')
        this = self.browse(cr, uid, ids, context=context)
        new_cpa_line = []
        total_amount = 0.0
        for ar_id in ar_ids:
            aml_id = AccountMoveLine.browse(cr, uid, ar_id, context=context)
            new_cpa_line.append([0,0,{
                'account_id': aml_id.account_id.id, 
                'move_line_id': ar_id,
                'name': aml_id.ref, 
                'analytic_2': aml_id.analytic_2.id, 
                'analytic_3': aml_id.analytic_3.id,
                'account_analytic_id': aml_id.analytic_4.id,
                'amount': aml_id.debit, 
            }])
            total_amount += aml_id.debit

        domain = [('company_id','=',this.branch_id.company_id.id),('type','=','cash'),('name','ilike','Kas Besar')]
        journal_id = AccountJournal.search(cr, uid, domain, limit=1)
        if not journal_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan jurnal Kas Besar untuk company_id %s" % this.branch_id.company_id.name ))
        journal = AccountJournal.browse(cr, uid, journal_id, context=context)[0]
        
        partner_type_id = PartnerType.search(cr, uid, [('name','=','customer')])
        if not partner_type_id:
            raise osv.except_osv(('Perhatian !'), ("Tipe Partner 'customer' tidak ditemukan di database, mohon hubungi Divisi IT."))
        new_cpa = {
            'company_id':this.branch_id.company_id.id,
            'branch_id':this.branch_id.id, 
            'division': this.division, 
            'inter_branch_id':this.branch_id.id, 
            'inter_branch_division': this.division, 
            'partner_type': partner_type_id[0],
            'partner_id': this.customer_id.id, 
            'date':datetime.now().strftime('%Y-%m-%d'), 
            'amount': total_amount, 
            'reference': this.name, 
            'name': this.name, 
            'user_id': uid,
            'type': 'receipt',
            'line_dr_ids': False,
            'line_cr_ids': new_cpa_line,
            'analytic_1': analytic_1.id,
            'analytic_2': analytic_2.id,
            'analytic_3': analytic_3.id,
            'analytic_4': analytic_4.id,
            'journal_id': journal.id,
            'account_id': journal.default_debit_account_id.id,
            'is_hutang_lain': False,
            'paid_amount': total_amount,
        } 
        new_cpa_id = Voucher.create(cr, uid, new_cpa, context=context)
        return new_cpa_id

    def view_cpa(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')        
        result = mod_obj.get_object_reference(cr, uid, 'dealer_sale_order', 'action_vendor_receipt_workshop')
        
        id = result and result[1] or False        
        result = act_obj.read(cr, uid, [id], context=context)[0]
        
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        Voucher = self.pool.get('account.voucher')
        VoucherLine = self.pool.get('account.voucher.line')
        inv_ids = obj_inv.search(cr,uid,[
            ('origin','ilike',val.name),
            ('type','=','out_invoice')
        ])

        if not inv_ids:
            raise osv.except_osv(('Perhatian !'), ("Belum ada invoice"))

        ar_ids = []

        analytic_1 = False
        analytic_2 = False
        analytic_3 = False
        analytic_4 = False
        for inv in obj_inv.browse(cr, uid, inv_ids, context=context):
            analytic_1 = inv.analytic_1
            analytic_2 = inv.analytic_2
            analytic_3 = inv.analytic_3
            analytic_4 = inv.analytic_4
            if inv.move_id:
                move_line_ar = inv.move_id.line_id.filtered(lambda x:x.account_id.type=='receivable') or False
                if move_line_ar:
                    for ml_ar in move_line_ar:
                        ar_ids.append(ml_ar.id)
                else:
                    raise osv.except_osv(('Perhatian !'), ("Invoice belum divalidasi... (1)"))
            else:
                raise osv.except_osv(('Perhatian !'), ("Invoice belum divalidasi... (2)"))

        cpa_ids = []
        if ar_ids:
            voucher_line_ids = VoucherLine.search(cr, uid, [('move_line_id','in',ar_ids)], context=context)
            if voucher_line_ids:
                for voucher_line_id in VoucherLine.browse(cr, uid, voucher_line_ids, context=context):
                    if not voucher_line_id.voucher_id.id in cpa_ids:
                        cpa_ids.append(voucher_line_id.voucher_id.id)

        if not cpa_ids:
            if ar_ids:
                cpa_id = self.create_cpa(cr, uid, ids, ar_ids, analytic_1, analytic_2, analytic_3, analytic_4, context=context)
                cpa_ids.append(cpa_id)
            else:
                raise osv.except_osv(('Perhatian !'), ("Invoice belum divalidasi sehingga belum bisa dibuatkan voucher pembayaran ... (2)"))
        
        if len(cpa_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, cpa_ids))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
            print "res---------->",res
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = cpa_ids[0] 
        
        return result
