import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc

class dym_bank_transfer_approval(osv.osv):
    _inherit = "dym.bank.transfer"
      
    _columns = {
        'approval_ids': fields.one2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
        'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),
        'is_internal': fields.boolean(string='Is Internal'),
    }
    
    _defaults ={
        'approval_state':'b'
    }
    
    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_bj = self.browse(cr, uid, ids, context=context)
        obj_matrix = self.pool.get("dym.approval.matrixbiaya")
        if all([not obj_bj.line_ids,not obj_bj.voucher_line_ids,not obj_bj.deposit_ahass_ids,not obj_bj.invoice_line_ids]):
            raise osv.except_osv(('Perhatian !'), ("Line belum diisi 11"))        
        config = self.pool.get('dym.branch.config').search(cr,uid,[
           ('branch_id','=',obj_bj.branch_id.id)
        ])   
        if config :
            config_browse = self.pool.get('dym.branch.config').browse(cr,uid,config)
            flag_mit = False
            for x in config_browse :
                if not x.bank_transfer_fee_account_id and obj_bj.bank_fee:
                    raise osv.except_osv(('Perhatian !'), ("Account Bank Transfer Fee belum diisi di Master Branch Config untuk %s")%(obj_bj.branch_id.name))
                if not x.bank_transfer_mit_account_id and x.banktransfer_mit == True :
                    raise osv.except_osv(('Perhatian !'), ("Account Bank Transfer MIT belum diisi di Master Branch Config untuk %s")%(obj_bj.branch_id.name))
                if x.banktransfer_mit == True:
                    flag_mit = True
            if flag_mit == True:
                if obj_bj.payment_from_id.type == 'cash' :
                    analytic_branch_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',3),('branch_id','=',obj_bj.branch_id.id),('type','=','normal'),('state','not in',('close','cancelled'))])
                    analytic_cc_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',4),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',analytic_branch_ids)])
                    sql_query = ' AND l.analytic_account_id in %s' % str(tuple(analytic_cc_ids))
                    if obj_bj.amount > obj_bj.payment_from_id.default_debit_account_id.with_context(sql_query=sql_query).balance or obj_bj.amount_show > obj_bj.payment_from_id.default_debit_account_id.with_context(sql_query=sql_query).balance :
                        raise osv.except_osv(('Perhatian !'), ("Saldo kas tidak mencukupi !"))
                # self.action_move_line_create(cr, uid, ids, mit=True, context=context)
        obj_matrix.request_by_value(cr, uid, ids, obj_bj, obj_bj.amount)
        values = {
            'state': 'waiting_for_approval',
            'approval_state':'rf'
        }
        if obj_bj.name == '/':
            values['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, obj_bj.branch_id.id, 'BTR', division='Umum', context=context) 
        self.write(cr, uid, ids, values)
        return True
           
    def wkf_approval(self, cr, uid, ids, context=None):
        obj_bj = self.browse(cr, uid, ids, context=context)
        approval_sts = self.pool.get("dym.approval.matrixbiaya").approve(cr, uid, ids, obj_bj)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))  
        self.action_move_line_create(cr, uid, ids, mit=True, context=context) 
        for line2 in obj_bj.line_ids2:
            if line2.reimbursement_id:
                line2.reimbursement_id.state='done'
        return True

    def has_cancelled2(self, cr, uid, ids, *args):
        print "has_cancelled2"
        self.write(cr, uid, ids, {'state':'cancel'})
        return True
        # obj_bj = self.browse(cr, uid, ids)
        # return obj_bj.approval_state == 'a' and not obj_bj.is_internal

    def has_approved_ext(self, cr, uid, ids, *args):
        obj_bj = self.browse(cr, uid, ids)
        return obj_bj.approval_state == 'a' and not obj_bj.is_internal

    def has_approved_int(self, cr, uid, ids, *args):
        obj_bj = self.browse(cr, uid, ids)
        return obj_bj.approval_state == 'a' and obj_bj.is_internal

    def has_rejected(self, cr, uid, ids, *args):
        obj_bj = self.browse(cr, uid, ids)
        if obj_bj.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False

    def act_waiting_for_confirm_received(self, cr, uid, ids, *args):
        obj_bj = self.browse(cr, uid, ids)
        for line in obj_bj.bank_trf_request_ids:
            if line.obj == 'dym.reimbursed':
                for reimb in self.pool.get('dym.reimbursed').browse(cr, uid, [line.res_id]):
                    reimb.state = 'paid'
            if line.obj == 'dym.reimbursed.bank':
                for reimb in self.pool.get('dym.reimbursed.bank').browse(cr, uid, [line.res_id]):
                    reimb.state = 'paid'

        self.write(cr, uid, ids, {'state':'waiting_for_confirm_received'})
        return True

    def has_received(self, cr, uid, ids, *args):
        this = self.browse(cr, uid, ids)

        config_id = self.pool.get('dym.branch.config').search(cr,uid,[
           ('branch_id','=',this.branch_id.id)
        ])
        if not config_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan konfigurasi untuk cabang '%s', hubungi system administrator." % this.branch_id.name))  

        config = self.pool.get('dym.branch.config').browse(cr, uid, config_id)

        if this.state in ['waiting_for_confirm_received']:
            if this.receive_date < this.date: 
                raise osv.except_osv(('Perhatian !'), ("Tanggal terima harus sama atau lebih besar dari tanggal transaksi"))

        if config.banktransfer_mit:
            if this.transaction_type=='deposit':
                if not config.bank_deposit_mit_account_id:
                    raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan konfigurasi akun perantara untuk transaksi Setoran (biasanya akun Setoran Tunai Perantara) pada cabang '%s', hubungi system administrator." % this.branch_id.name))  
                for line in this.line_ids:
                    if line.payment_to_id.type != 'bank':
                        raise osv.except_osv(('Perhatian !'), ("Jurnal %s tidak termasuk jurnal bank tapi jurnal %s. Transaksi Deposit / penyetoran kas ke bank hanya boleh dari jurnal Kas ke jurnal Bank saja. Silahkan hubungi system administrator untuk melanjutkan." % (line.payment_to_id.name,line.payment_to_id.type)))  

            elif this.transaction_type=='withdraw':
                if not config.bank_withdrawal_mit_account_id:
                    raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan konfigurasi akun perantara untuk transaksi Penarikan (biasanya akun Penggantian Kas) pada cabang '%s', hubungi system administrator." % this.branch_id.name))  
                for line in this.line_ids:
                    if line.payment_to_id.type not in ['pettycash','cash']:
                        raise osv.except_osv(('Perhatian !'), ("Jurnal %s tidak termasuk jurnal Cash tapi jurnal %s. Transaksi Withdrawal / pengambilan bank hanya boleh dari jurnal bank ke jurnal cash saja. Silahkan hubungi system administrator untuk melanjutkan." % (line.payment_to_id.name,line.payment_to_id.type)))  

            elif this.transaction_type in ['ats','ho2branch','inhouse']:
                if not config.bank_transfer_mit_account_id:
                    raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan konfigurasi akun perantara untuk transaksi ATS, Ho2Branch dan Inhouse Transfer (biasanya akun Pindahan Antar bank) pada cabang '%s', hubungi system administrator." % this.branch_id.name))  
                for line in this.line_ids:
                    if line.payment_to_id.type != 'bank':
                        raise osv.except_osv(('Perhatian !'), ("Jurnal %s tidak termasuk jurnal bank tapi jurnal %s. Transaksi ini hanya boleh dari jurnal bank ke jurnal bank saja. Silahkan hubungi system administrator untuk melanjutkan." % (line.payment_to_id.name,line.payment_to_id.type)))  
            else:
                raise osv.except_osv(('Perhatian !'), ("System tidak mengenal transaksi ini, system hanya mengenal transaksi deposit, witdrawal, ats, ho2branch dan inhouse saja."))  

        # self.env.context.get('transaction_type',False)
        if this.approval_state == 'a':
            self.write(cr, uid, ids, {'state':'app_received'})
            return True
        return False

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        for banktransfer in self.browse(cr, uid, ids, context=context):       
            if banktransfer.move_mit_id:
                banktransfer.move_mit_id.button_cancel()
                banktransfer.move_mit_id.unlink()
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r','move_mit_id': False})

    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        for banktransfer in self.browse(cr, uid, ids, context=context):       
            if banktransfer.move_mit_id:
                banktransfer.move_mit_id.button_cancel()
                banktransfer.move_mit_id.unlink()
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b','move_mit_id': False})
