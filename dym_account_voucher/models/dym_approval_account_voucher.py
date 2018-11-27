import time
from datetime import datetime
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.osv import orm
from openerp.tools.translate import _


class dym_account_voucher_approval(osv.osv):
    _inherit = "account.voucher"
    STATE_SELECTION = [
        ('draft','Draft'),
        ('waiting_for_approval','Waiting Approval'),
        ('confirmed', 'Waiting Approval'),
        ('request_approval','RFA'), 
        ('approved','Approve'), 
        ('cancel','Cancelled'),
        ('proforma','Pro-forma'),
        ('posted','Posted')
    ]
    
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.voucher.line').browse(cr, uid, ids, context=context):
            result[line.voucher_id.id] = True
        return result.keys()
    
    def _total_debit(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            res[voucher.id] = {
                'total_debit': 0.0,
                'total_credit': 0.0,
            }
            value =  0.0
            for line in voucher.line_dr_ids:
                value += line.amount
            res[voucher.id]['total_debit'] = value

            value =  0.0
            for line in voucher.line_cr_ids:
                value += line.amount
            res[voucher.id]['total_credit'] = value

        return res
    
    # def _get_payment_option(self, cr, uid, ids, name, args, context=None):
    #     if not ids: return {}
    #     res = {}
    #     for voucher in self.browse(cr, uid, ids, context=context):
    #         if voucher.writeoff_amount == 0:
    #             res[voucher.id] = 'without_writeoff'
    #         else:
    #             res[voucher.id] = 'with_writeoff'              
    #     return res

    _columns = {
        'approval_ids': fields.one2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)],),
        'state':fields.selection(STATE_SELECTION, 'Status', readonly=True, track_visibility='onchange', copy=False,
            help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed Voucher. \
                        \n* The \'Pro-forma\' when voucher is in Pro-forma status,voucher does not have an voucher number. \
                        \n* The \'Posted\' status is used when user create voucher,a voucher number is generated and voucher entries are created in account \
                        \n* The \'Cancelled\' status is used when user cancel voucher.'),
        'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),
        'type':fields.selection([
            ('sale','Sale'),
            ('purchase','Purchase'),
            ('payment','Payment'),
            ('receipt','Receipt'),
        ],'Default Type', readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'name':fields.char('Memo', readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'date':fields.date('Date', readonly=True, select=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]},
                           help="Effective date for accounting entries", copy=False),
        'journal_id':fields.many2one('account.journal', 'Journal', readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'account_id':fields.many2one('account.account', 'Account', readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'line_ids':fields.one2many('account.voucher.line', 'voucher_id', 'Voucher Lines',
                                   readonly=True, copy=True,
                                   states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'line_cr_ids':fields.one2many('account.voucher.line','voucher_id','Credits',
            domain=[('type','=','cr')], context={'default_type':'cr'}, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'line_dr_ids':fields.one2many('account.voucher.line','voucher_id','Debits',
            domain=[('type','=','dr')], context={'default_type':'dr'}, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'narration':fields.text('Notes', readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'amount': fields.float('Total', digits_compute=dp.get_precision('Account'), required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'reference': fields.char('Ref #', readonly=False, states={'posted':[('readonly',True)]},
                                 help="Transaction reference number.", copy=False),
        'partner_id':fields.many2one('res.partner', 'Partner', change_default=1, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'pay_now':fields.selection([
            ('pay_now','Pay Directly'),
            ('pay_later','Pay Later or Group Funds'),
        ],'Payment', select=True, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'tax_id': fields.many2one('account.tax', 'Tax', readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}, domain=[('price_include','=', False)], help="Only for tax excluded from price"),
        'date_due': fields.date('Due Date', readonly=True, select=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
        'payment_option': fields.selection([
            ('without_writeoff', 'Keep Open'),
            ('with_writeoff', 'Reconcile Payment Balance'),
        ], 'Payment Difference', required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft': [('readonly', False)]}, help="This field helps you to choose what you want to do with the eventual difference between the paid amount and the sum of allocated amounts. You can either choose to keep open this difference on the partner's account, or reconcile it with the payment(s)"),

        # 'payment_option': fields.function(_get_payment_option, string='Payment Difference', type='selection', selection=[
        #                                    ('without_writeoff', 'Keep Open'),
        #                                    ('with_writeoff', 'Reconcile Payment Balance'),
        #                                    ], required=True, help="This field helps you to choose what you want to do with the eventual difference between the paid amount and the sum of allocated amounts. You can either choose to keep open this difference on the partner's account, or reconcile it with the payment(s)"),

        'writeoff_acc_id': fields.many2one('account.account', 'Counterpart Account', readonly=True, states={'request_approval':[('readonly',True)],'draft': [('readonly', False)]}),
        'comment': fields.char('Counterpart Comment', required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft': [('readonly', False)]}),
        'analytic_id': fields.many2one('account.analytic.account','Write-Off Analytic Account', readonly=True, states={'request_approval':[('readonly',True)],'draft': [('readonly', False)]}),
        'payment_rate_currency_id': fields.many2one('res.currency', 'Payment Rate Currency', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'payment_rate': fields.float('Exchange Rate', digits=(12,6), required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft': [('readonly', False)]},
            help='The specific rate that will be used, in this voucher, between the selected currency (in \'Payment Rate Currency\' field)  and the voucher currency.'),
        'total_debit': fields.function(_total_debit, digits_compute=dp.get_precision('Account'), string='Total Debit',
            multi='sums', help="Line Debit"),
        'total_credit': fields.function(_total_debit, digits_compute=dp.get_precision('Account'), string='Total Credit',
            multi='sums', help="Line Credit"),
        'faktur_pajak_id':fields.many2one('dym.faktur.pajak.out',string='No Faktur Pajak'),
        'faktur_pajak_tgl': fields.related('faktur_pajak_id', 'date', relation='dym.faktur_pajak_out',type='date',string='Tgl Faktur Pajak',store=False),    
    }
    
    _defaults ={
        'approval_state':'b'
    }
    
    def validate_or_rfa(self,cr,uid,ids,context=None):
        obj_av = self.browse(cr, uid, ids, context=context)
        if obj_av.total_debit > 0 :
            self.signal_workflow(cr, uid, ids, 'approval_request')
        else :
            self.signal_workflow(cr, uid, ids, 'proforma_voucher')
        return True

    def validate_or_rfa_credit(self,cr,uid,ids,context=None):
        obj_av = self.browse(cr, uid, ids, context=context)
        if obj_av.total_credit > 0 :
            self.signal_workflow(cr, uid, ids, 'approval_request')
        else :
            self.signal_workflow(cr, uid, ids, 'proforma_voucher')
        obj_av._set_net_amount()
        return True

    def _get_writeoff_amount2(self, cr, uid, ids, context=None):
        if not ids: return {}
        currency_obj = self.pool.get('res.currency')
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            debit = credit = 0.0
            sign = voucher.type == 'payment' and -1 or 1
            for l in voucher.line_dr_ids:
                debit += l.amount
            for l in voucher.line_cr_ids:
                credit += l.amount
            currency = voucher.currency_id or voucher.company_id.currency_id
            res[voucher.id] = (voucher.payment_option, currency_obj.round(cr, uid, currency, voucher.amount - sign * (credit - debit)))
        return res

    def wkf_request_approval(self, cr, uid, ids, context=None):
        writeoff_option = self._get_writeoff_amount2(cr, uid, ids, context=context)
        obj_av = self.browse(cr, uid, ids, context=context)
        # obj_av.check_open_balance()
        if writeoff_option:
            for k,v in writeoff_option.items():
                Config = self.pool.get('dym.branch.config')
                branch_config_id = Config.search(cr,uid,[('branch_id','=',obj_av.branch_id.id)])
                branch_config = Config.browse(cr,uid,branch_config_id,context=context)
                payment_option, difference = v
                if difference:
                    if obj_av.type=='payment':
                        if not branch_config.max_writeoff_payable:
                            raise osv.except_osv(('Perhatian !'), ("Terdapat selisih pembayaran dengan hutang sebesar %s, tapi nilai maximum payable writeoff belum ditentukan pada branch config. Silahkan lengkapi dulu untuk melanjutkan." % difference)) 
                        if difference <= branch_config.max_writeoff_payable and obj_av.payment_option == 'without_writeoff':
                            if not branch_config.writeoff_payable_account_id:
                                raise osv.except_osv(('Perhatian !'), ("Terdapat selisih pembayaran dengan piutang sebesar %s, tapi akun writeoff payable belum ditentukan pada branch config. Silahkan lengkapi dulu untuk melanjutkan." % difference)) 
                            self.write(cr, uid, ids, {
                                'payment_option': 'with_writeoff',
                                'writeoff_acc_id': branch_config.writeoff_payable_account_id.id,
                            })

                    if obj_av.type=='receipt':
                        if not branch_config.max_writeoff_receivable:
                            raise osv.except_osv(('Perhatian !'), ("Terdapat selisih penerimaan dengan piutang sebesar %s, tapi nilai maximum payable writeoff belum ditentukan pada branch config. Silahkan lengkapi dulu untuk melanjutkan." % difference)) 
                        if difference <= branch_config.max_writeoff_receivable and obj_av.payment_option == 'without_writeoff':
                            if not branch_config.writeoff_receivable_account_id:
                                raise osv.except_osv(('Perhatian !'), ("Terdapat selisih penerimaan dengan piutang sebesar %s, tapi akun writeoff receivable belum ditentukan pada branch config. Silahkan lengkapi dulu untuk melanjutkan." % difference)) 
                            self.write(cr, uid, ids, {
                                'payment_option': 'with_writeoff',
                                'writeoff_acc_id': branch_config.writeoff_receivable_account_id.id,
                            })

        obj_matrix = self.pool.get("dym.approval.matrixbiaya")
        total = 0.0
        for x in obj_av.line_dr_ids :
            total += x.amount
        type = obj_av.type
        if type == 'payment' :
            view_name = 'account.voucher.payment.form'
        elif type == 'purchase' :
            view_name = 'account.voucher.purchase.form'
        elif type == 'receipt' :
            view_name = 'account.voucher.receipt.form'
        elif type == 'sale' :
            view_name = 'account.voucher.sale.form'
            for x in obj_av.line_cr_ids :
                total += x.amount
        obj_matrix.request_by_value(cr, uid, ids, obj_av, total, type,view_name)
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True        
    
    def wkf_approval(self, cr, uid, ids, context=None):
        context = context.copy()
        context['other_receivable'] = 'OR'
        val = self.browse(cr, uid, ids, context=context) 
        approval_sts = self.pool.get("dym.approval.matrixbiaya").approve(cr, uid, ids, val)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
        
        try:
            total = 0.0
            for x in val.line_dr_ids :
                total += x.amount
            tax = val.amount - total

            if tax and not val.pajak_gabungan and val.type == 'purchase':
                model = self.pool.get('ir.model').search(cr,uid,[
                                                             ('model','=',val.__class__.__name__)
                                                             ])
                faktur_pajak_id = self.pool.get('dym.faktur.pajak.out').create(cr, uid, {
                    'name': val.no_faktur_pajak,
                    'state': 'close',
                    'thn_penggunaan' : int(val.tgl_faktur_pajak[:4]),
                    'tgl_terbit' : val.tgl_faktur_pajak,
                    'model_id':model[0],
                    'amount_total':val.amount,
                    'untaxed_amount':total,
                    'tax_amount':tax,                                                    
                    'state':'close',
                    'transaction_id':val.id,
                    'date':val.date,
                    'partner_id':val.partner_id.id,
                    'company_id':val.branch_id.company_id.id,
                    'in_out':'in',
                }, context=context)
                self.write(cr, uid, ids, {'faktur_pajak_id':faktur_pajak_id}, context=context)

        except:
            return True
        partner_id = val.partner_id.id
        # UPDATE PARTNER SESUAI PENGALOKASIAN TITIP JIKA ADA TRANSAKSI TITIPAN DIMANA PARTNER TIDAK DIKETAHUI
        for line in val.line_cr_ids:
            if not line.move_line_id.partner_id:
                self.pool.get('account.move').write(cr, uid, line.move_line_id.move_id.id, {'partner_id':partner_id})
                for move_line in line.move_line_id.move_id.line_id:
                    self.pool.get('account.move.line').write(cr, uid, move_line.id, {'partner_id':partner_id})

        for line in val.line_dr_ids:
            if not line.move_line_id.partner_id:
                self.pool.get('account.move').write(cr, uid, line.move_line_id.move_id.id, {'partner_id':partner_id})
                for move_line in line.move_line_id.move_id.line_id:
                    self.pool.get('account.move.line').write(cr, uid, move_line.id, {'partner_id':partner_id})            
        return True

    def has_approved(self, cr, uid, ids, *args):
        obj_av = self.browse(cr, uid, ids)
        return obj_av.approval_state == 'a'

    def is_payment(self, cr, uid, ids, *args):
        obj_av = self.browse(cr, uid, ids)
        if obj_av.type != 'payment' :
            return False
        return True
    
    def is_not_payment(self, cr, uid, ids, *args):
        obj_av = self.browse(cr, uid, ids)
        if obj_av.type == 'payment' :
            return False
        return True
        
    def has_rejected(self, cr, uid, ids, *args):
        obj_av = self.browse(cr, uid, ids)
        if obj_av.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'}) 

    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})
   
    def onchange_partner_id(self, cr,uid,ids,partner_id,journal_id,amount,currency_id,ttype,date, context=None):
        res = super(dym_account_voucher_approval,self).onchange_partner_id(cr,uid,ids,partner_id,journal_id,amount,currency_id,ttype,date,context=context)
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if ttype in ('receipt','payment'):
                if res.get('value'):
                    res['value']['writeoff_acc_id'] = partner.sudo().property_account_rounding.id
                else:
                    res['value'] = {}                    
                    res['value']['writeoff_acc_id'] = partner.sudo().property_account_rounding.id
        return res

    # def check_open_balance(self, cr, uid, ids, context=None):
    #     voucher_id = self.browse(cr, uid, ids)
    #     for line in voucher_id.line_dr_ids:
    #         if line.amount > line.amount_unreconciled:
    #             raise osv.except_osv(('Perhatian !'), ("Nilai Alokasi %s tidak boleh lebih besar dari Open Balance (sisa A/R)") % line.move_line_id)
    #         elif not line.amount_unreconciled:
    #             raise osv.except_osv(('Perhatian !'), ("Open Balance (sisa A/R) %s tidak boleh sama dengan nol.") % line.move_line_id)
    #     return True