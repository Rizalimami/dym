import time
from openerp.osv import osv, fields, orm
from lxml import etree
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import datetime, date, timedelta
from openerp import models, api, _, SUPERUSER_ID
from openerp.tools import float_compare
from openerp import workflow
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import Warning as UserError, RedirectWarning
from ..report import fungsi_terbilang
from openerp.addons.dym_base import DIVISION_SELECTION

class AccountFilterExcludeCP(models.Model):
    _inherit = "dym.account.filter"

    def _register_hook(self, cr):
        selection = self._columns['name'].selection
        if ('exclude_customer_payment','Exclude Customer Payment - Debit') not in selection: 
            self._columns['name'].selection.append(
                ('exclude_customer_payment', 'Exclude Customer Payment - Debit')
                )
        return super(AccountFilterExcludeCP, self)._register_hook(cr)  

class res_bank_internet_banking_custom(osv.osv):
    _inherit = 'res.bank'    

    _columns = {
        'internet_banking': fields.boolean('Use Interent Banking'),
        'bank':fields.selection([(' ','NON BCA'),('is_bca','BCA')], 'BANK'),
        'internet_banking_code': fields.char('Kode Internet Banking'),
        'company_code': fields.char('Kode Perusahaan'),
        'bank_indonesia_code': fields.char('Kode Bank Indonesia'),
        }

    def _is_numeric(self, cr, uid, ids, context=None):
        lines = self.browse(cr, uid, ids, context=context)
        for l in lines:
            if l.bank_indonesia_code and not l.bank_indonesia_code.isdigit():
                return False
        return True

    _constraints = [
        (_is_numeric, 'Kode Bank Indonesia harus berupa angka.', ['bank_indonesia_code']),
        ]
        

class res_partner_bank_custom(osv.osv):
    _inherit = 'res.partner.bank'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(res_partner_bank_custom, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'branch_ids': fields.many2many('dym.branch','dym_bank_account_cabang_rel','bank_account_id','branch_id', 'Branchs'),
        'division':fields.selection(DIVISION_SELECTION, 'Division'),
        'company_code': fields.char('Kode Perusahaan'),
    }

class dym_account_voucher_custom(osv.osv):
    _inherit = 'account.voucher'

    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil

    def desc_spa_par(self,cr,uid,voucher_name,voucher_desc,context=None):
        if voucher_name.name[:3] != 'PAR':
            return voucher_desc
        elif voucher_name.name[:3] == 'PAR':
            par_ids = self.pool.get('account.voucher').search(cr,uid,[('number','=',voucher_name.name)])
            par_id = self.pool.get('account.voucher').browse(cr,uid,par_ids)
            par_line_ids = self.pool.get('account.voucher.line').search(cr,uid,[('voucher_id','=',par_id.id)])
            par_line_id = self.pool.get('account.voucher.line').browse(cr,uid,par_line_ids)
            if par_line_id:
                check_desc = []
                for x in par_line_id:
                    if not x.name in check_desc:
                        check_desc.append(x.name)
                return ', '.join(check_desc)

    def desc_cetakan_spa(self,cr,uid,voucher_name,context=None):
        if 'SIN-' in voucher_name.name:
            return voucher_name.name
        else:
            spa_ids = self.pool.get('account.voucher').search(cr,uid,[('number','=',voucher_name.name)])
            spa_browse = self.pool.get('account.voucher').browse(cr,uid,spa_ids)
            if not spa_browse.line_dr_ids:
                return 'N/A'
            return spa_browse.line_dr_ids[0].name

    def ubah_tanggal(self,tanggal):
        if not tanggal:
            return 'N/A'
        tanggal = tanggal[:10]
        try:
            conv = datetime.strptime(tanggal, '%d-%m-%Y')
        except:
            conv = datetime.strptime(tanggal, '%Y-%m-%d')

        return conv.strftime('%d/%m/%Y')

    @api.onchange('amount','net_amount','line_dr_ids','current_balance')
    def payment_amount_current_balance(self):
        if self.type=='payment' and self.amount > self.current_balance:
            warning = {
                'title': ('Perhatian !'),
                'message': (_('Total transaksi tidak boleh melebihi saldo.')),
            }
            value = {
                'current_balance':0.0,
                'amount': 0.0,
                'net_amount': 0.0,
            }     
            return {'warning':warning,'value':value} 

    def update_data(self,cr,uid,ids,voucher,context=None):
        vals = self.pool.get('account.voucher').browse(cr,uid,ids)
        move_line = self.pool.get('account.move.line').search(cr,uid,[
            ('move_id','=',vals.move_id.id),
            ('debit','!=',False)
        ])
        move_line_brw = self.pool.get('account.move.line').browse(cr,uid,move_line)
        for x in move_line_brw :
            self.pool.get('account.move.line').write(cr, uid,x.id, {'kwitansi': 1,'kwitansi_id':vals.kwitansi_id.id})
        kwitansi = self.pool.get('dym.register.kwitansi.line').search(cr,uid,[
            ('payment_id','=',vals.id),
            ('state','=','printed'),
            ('reason','=',False)
        ])
        if kwitansi :
            prev_kwitansi = self.pool.get('dym.register.kwitansi.line').browse(cr,uid,kwitansi)
            for x in prev_kwitansi :        
                self.pool.get('dym.register.kwitansi.line').write(cr,uid,x.id,{'state':'cancel','reason':str(vals.reason_cancel_kwitansi)})
        self.pool.get('dym.register.kwitansi.line').write(cr, uid,vals.kwitansi_id.id, {
            'payment_id':vals.id,                                                                                                 
            'state':'printed'
        })
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr, uid,[ ('model','=','account.voucher') ])[0]
        obj_ir = self.pool.get('ir.actions.report.xml').search(cr, uid,[('report_name','=','rml.other.receivable')])
        obj_ir_id = self.pool.get('ir.actions.report.xml').browse(cr, uid,obj_ir).id                 
        obj_jumlah_cetak=self.pool.get('dym.jumlah.cetak').search(cr,uid,[('report_id','=',obj_ir_id),('model_id','=',obj_model_id),('transaction_id','=',ids[0])])
        if not obj_jumlah_cetak :
            vals.write({'cetak_ke':1,'reason_cancel_kwitansi':False})
            jumlah_cetak_id = {
                'model_id':obj_model_id,
                'transaction_id': ids[0],
                'jumlah_cetak': 1,
                'report_id':obj_ir_id                            
            }
            jumlah_cetak=1
            move=self.pool.get('dym.jumlah.cetak').create(cr,uid,jumlah_cetak_id)
        else :
            cetakke = vals.cetak_ke+1
            vals.write({'cetak_ke':cetakke,'reason_cancel_kwitansi':False})
            obj_jumalah = self.pool.get('dym.jumlah.cetak').browse(cr,uid,obj_jumlah_cetak)
            jumlah_cetak = obj_jumalah.jumlah_cetak+1
            self.pool.get('dym.jumlah.cetak').write(cr, uid,obj_jumalah.id, {'jumlah_cetak': jumlah_cetak})  
        cetak = ''
        return cetak  

    def get_tempo(self,cr,uid,ids,voucher,context=None):
        start = datetime.strptime(voucher.date, '%Y-%m-%d')
        date_due = voucher.date
        if voucher.date_due:
            date_due = voucher.date_due
        end = datetime.strptime(date_due, '%Y-%m-%d')
        delta = timedelta(days=1)
        day = start
        diff = 0
        weekend = [6]
        while day < end:
            diff += 1
            day += delta
        return diff

    def get_list_number(self,cr, uid, ids, voucher):
        numb = []
        invoices = voucher.line_ids.mapped('move_line_id').filtered(lambda r: r.invoice).mapped('invoice')
        for inv in invoices:
            if inv.number not in numb:
                numb.append(inv.number)
            if inv.name not in numb:
                numb.append(inv.name)
        return numb

    def get_list_engine(self,cr, uid, ids, voucher):
        lots = []
        invoices = voucher.line_ids.mapped('move_line_id').filtered(lambda r: r.invoice).mapped('invoice')
        for inv in invoices:
            dso_id = self.pool.get('dealer.sale.order').search(cr, uid, [('name','in',inv.origin.split(' ') or '')], limit=1)
            dso = self.pool.get('dealer.sale.order').browse(cr, uid, dso_id)
            if dso:
                for line in dso.dealer_sale_order_line:
                    if line.lot_id not in lots:
                        lots.append(line.lot_id)
        return lots

    def get_terbilang(self,cr, uid, ids, amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')         
        user = user_obj.browse(cr,uid,uid)
        return user.get_default_branch()
       
    def _get_division(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('division', False)
    
    def _get_partner_type(self, cr, uid, context=None):
        type_id = self.pool.get('dym.partner.type').search(cr, uid, [('name','=','supplier')])
        # name = 'supplier'
        if context is None: context = {}        
        if context.get('type') == 'receipt' :
            type_id = self.pool.get('dym.partner.type').search(cr, uid, [('name','=','customer')])
            # name = 'customer'
        return type_id[0]

    def _get_analytic_company(self,cr,uid,context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_account_voucher-1] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]
        
    def _get_qq_id(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            res[voucher.id] = False
            for line in voucher.line_ids:
                if line.move_line_id.sudo().invoice.qq_id:
                    res[voucher.id] = line.move_line_id.sudo().invoice.qq_id.id
                    break
        return res

    def _get_default_backdate(self,cr,uid,context=None):
        flag = False
        if self.pool.get('res.users').has_group(cr, uid, 'dym_account_voucher.group_dym_account_voucher_allow_backdate'):
            flag = True
        return flag
        
    def _get_uang_muka(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            res[voucher.id] = {
                'wo_total': 0.0,
                'so_total': 0.0,
            }
            wo_total = so_total = 0.0
            for wo_line in voucher.wo_ids:
                wo_total += wo_line.amount_total
            for so_line in voucher.so_ids:
                so_total += so_line.amount_total
            res[voucher.id]['wo_total'] = wo_total * voucher.wo_percentage / 100
            res[voucher.id]['so_total'] = so_total * voucher.so_percentage / 100
        return res

    def _get_current_balance(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            res[voucher.id] = {
                'current_balance': 110.0,
            }
            if voucher.journal_id:
                res[voucher.id]['current_balance'] = voucher.journal_id.default_debit_account_id.balance
        return res

    def _get_payable_receivable(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            payable_receivable = 0
            if voucher.type == 'payment':
                payable_receivable = voucher.partner_id.credit
            elif voucher.type == 'receipt' and voucher.is_hutang_lain == False:
                payable_receivable = voucher.partner_id.debit
            res[voucher.id] = payable_receivable
        return res

    _columns = {
        'payable_receivable': fields.function(_get_payable_receivable, digits_compute=dp.get_precision('Account'), string='Total Titipan',
            store={
                'account.voucher': (lambda self, cr, uid, ids, c={}: ids, ['partner_id'], 10),
            }, help="Total Titipan", track_visibility='always'),
        'bank_account': fields.many2one('res.partner.bank', string='Supplier Bank A/C'),
        'bank_account_name': fields.related(
            'bank_account', 'owner_name', type='char',
            relation='res.partner.bank', string='Owner Name', readonly=True),
        'unidentified_payment':fields.boolean('Unidentified Payment',readonly=True, states={'draft': [('readonly', False)]}),   
        'payment_request_type':fields.selection([('biaya','Biaya'),('prepaid','Prepaid'),('cip','CIP')], 'Payment Request Type'),
        'branch_id': fields.many2one('dym.branch', string='Branch'),
        'division':fields.selection(DIVISION_SELECTION, 'Division', change_default=True, select=True),
        'inter_branch_id': fields.many2one('dym.branch'),
        'inter_branch_division': fields.selection(DIVISION_SELECTION, 'Division', change_default=True, select=True),
        'kwitansi_id': fields.many2one('dym.register.kwitansi.line', string='Kwitansi'),
        'partner_cabang': fields.many2one('dym.cabang.partner','Cabang Supplier'),
        'reason_cancel_kwitansi':fields.char('Reason'),
        'confirm_uid':fields.many2one('res.users',string="Validated by"),
        'confirm_date':fields.datetime('Validated on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),   
        'date':fields.date('Date'),
        'due_date_payment':fields.date('Due Date'),
        'cetak_ke':fields.integer('Cetak Kwitansi Ke'),
        'pajak_gunggung':fields.boolean('Tanpa Faktur Pajak',copy=False),   
        'pajak_gabungan':fields.boolean('Faktur Pajak Gabungan',copy=False),   
        'faktur_pajak_id':fields.many2one('dym.faktur.pajak.out',string='Faktur Pajak Satuan',copy=False),    
        'no_faktur_pajak' : fields.char('No Faktur Pajak',copy=False),   
        'tgl_faktur_pajak' : fields.date('Tgl Faktur Pajak',copy=False),
        'value_date' : fields.date('Transaction Date',copy=False),
        'is_hutang_lain' : fields.boolean('Is Customer Deposit ?',copy=False),   
        'partner_type':fields.many2one('dym.partner.type',string="Partner Type",domain="[('division','like',division)]"),
        'user_id' : fields.many2one('res.users', string='Responsible', change_default=True,readonly=True, states={'draft': [('readonly', False)]},track_visibility='always'),
        'kwitansi' : fields.boolean('Yg Sudah Print Kwitansi'),
        'transaksi' : fields.selection([
                ('rutin','Rutin'),
                ('tidak_rutin','Tidak Rutin'),
            ], string='Transaksi',  index=True, change_default=True),
        'jenis_transaksi_id' : fields.many2one('dym.payments.request.type', string='Tipe Transaksi', change_default=True,
            readonly=True, states={'draft': [('readonly', False)]},
            track_visibility='always'),
        'no_document' : fields.char(string='No Document', index=True),
        'tgl_document' : fields.date(string='Tgl Document',
            readonly=True, states={'draft': [('readonly', False)]}, index=True,
            help="Keep empty to use the current date", copy=False),
        'payments_request_ids' : fields.one2many('account.voucher.line', 'voucher_id',
             readonly=True, copy=True),
        'paid_amount' : fields.float(string='Paid Amount'),
        'is_pedagang_eceran': fields.related('branch_id', 'is_pedagang_eceran', relation='dym.branch',type='boolean',string='Pedagang Eceran',store=False),
        'analytic_1': fields.many2one('account.analytic.account','Account Analytic Company'),
        'analytic_2': fields.many2one('account.analytic.account','Account Analytic Bisnis Unit'),
        'analytic_3': fields.many2one('account.analytic.account','Account Analytic Branch'),
        'analytic_4': fields.many2one('account.analytic.account','Account Analytic Cost Center'),
        'wo_ids': fields.many2many('dym.work.order','voucher_wo_rel','voucher_id','wo_id', 'Work Order Reference'),
        'so_ids': fields.many2many('sale.order','voucher_so_rel','voucher_id','so_id', 'Sales Memo Reference'),
        'qq_id': fields.function(_get_qq_id, string='QQ', type='many2one', relation='res.partner'),
        'allow_backdate':fields.boolean('Backdate'),   
        'wo_percentage' : fields.float(string='WO Percentage'),
        'so_percentage' : fields.float(string='SO Percentage'),
        'wo_total': fields.function(_get_uang_muka, string='Uang Muka WO', type='float', multi='sums'),
        'so_total': fields.function(_get_uang_muka, string='Uang Muka SO', type='float', multi='sums'),
        'current_balance': fields.function(_get_current_balance, string='Current Balance', type='float', multi='sums'),
        'move_reclass_id':fields.many2one('account.move', 'Account Reclass Entry', copy=False),
        'move_reclass_ids': fields.related('move_reclass_id','line_id', type='one2many', relation='account.move.line', string='Journal Reclass Items', readonly=True),
        'nota_kredit': fields.boolean('Nota Kredit')
    }

    _defaults = {
        'branch_id': _get_default_branch,
        'division': _get_division,
        'journal_id': False,
        'date':fields.date.context_today,
        'due_date_payment':fields.date.context_today,
        'value_date':fields.date.context_today,
        'cetak_ke':0,
        'partner_type':_get_partner_type,
        'analytic_1':_get_analytic_company,
        'allow_backdate':_get_default_backdate,
        'payment_request_type':'biaya',
        'wo_percentage':60,
        'so_percentage':60,
    }

    @api.onchange('account_id')
    def change_account_id(self):
        dom={}
        if self.nota_kredit and self.account_id:
            dom['tax_id'] = [('id','in',self.account_id.tax_ids.ids)]
            return {'domain':dom}

    def onchange_analytic(self, cr, uid, ids, branch_id, division, account_id, aa1, aa2, aa3, aa4, context=None):
        dom = {}

        # if branch_id and division and aa2:
        #     level_3_ids = aa_obj.search(cr, uid, [('segmen','=',3),('branch_id','=',branch_id),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',aa2)])
        #     level_4_ids = aa_obj.search(cr, uid, [('segmen','=',4),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',level_3_ids)])
        #     dom['analytic_3'] = [('id','in',level_3_ids)]
        #     if aa4_ids:
        #         dom['account_analytic_id'] = [('id','in',[a for a in level_4_ids if a in aa4_ids])]
        #     else:
        #         dom['account_analytic_id'] = [('id','in',level_4_ids)]

        # this = self.browse(cr, uid, ids, context=context)
        # aa1_ids, aa2_ids, aa3_ids, aa4_ids, df1, df2, df3, df4 = self.pool.get('analytic.account.filter').get_analytics(cr, uid, ids, branch_id, division, account_id, context=context)
        # aa_obj = self.pool.get('account.analytic.account')
        # if branch_id and aa2:
        #     level_3_ids = aa_obj.search(cr, uid, [('segmen','=',3),('branch_id','=',branch_id),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',aa2)])
        #     level_4_ids = aa_obj.search(cr, uid, [('segmen','=',4),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',level_3_ids)])
        #     dom['analytic_3'] = [('id','in',level_3_ids)]
        #     if aa4_ids:
        #         dom['account_analytic_id'] = [('id','in',[a for a in level_4_ids if a in aa4_ids])]
        #     else:
        #         dom['account_analytic_id'] = [('id','in',level_4_ids)]
        return {'domain':dom}

    def onchange_gabungan_gunggung(self,cr,uid,ids,gabungan_gunggung,pajak_gabungan,pajak_gunggung,context=None):
        value = {}
        if gabungan_gunggung == 'pajak_gabungan' and pajak_gabungan == True:
            value['pajak_gunggung'] = False
        if gabungan_gunggung == 'pajak_gunggung' and pajak_gunggung == True:
            value['pajak_gabungan'] = False
        return {'value':value}

    def branch_id_other_payable(self,cr,uid,ids,branch_id,context=None):
        value = {}
        domain = {}
        if branch_id :
            domain['journal_id'] = [('branch_id','in',[branch_id,False]),('type','in',['bank','cash','edc'])]
            branch_search = self.pool.get('dym.branch').browse(cr,uid,branch_id)
            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_search, 'Umum',False, 4, 'General')
            value['analytic_1'] = analytic_1
            value['analytic_2'] = analytic_2
            value['analytic_3'] = analytic_3
            value['analytic_4'] = analytic_4
        return {'domain':domain,'value':value}
      
    def journal_id_change_other_payable(self,cr,uid,ids,journal_id, context=None):
        val = {}
        account = False
        if journal_id :
            journal = self.pool.get('account.journal').browse(cr,uid,journal_id)
            if journal :
                account = journal.default_debit_account_id.id
                if not account :
                        raise except_orm(_('Warning!'), _('Konfigurasi jurnal account belum dibuat, silahkan setting dulu !'))
        val['account_id'] = account
        return {'value':val}
    
    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
        res = super(dym_account_voucher_custom,self).onchange_partner_id(cr,uid,ids,partner_id,journal_id,amount,currency_id,ttype,date,context=context)
        # if ttype == 'purchase':
        if journal_id :
            journal = self.pool.get('account.journal').browse(cr,uid,journal_id)
            res['value']['account_id'] = journal.default_credit_account_id.id
        if ttype in ('receipt','payment') and res.get('value'):
            res['value']['line_ids'] = []
            res['value']['line_dr_ids'] = []
            res['value']['line_cr_ids'] = []  
        payable_receivable = 0
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
        if not res.get('value'):
            res['value'] = {}
        if ttype == 'payment':
            payable_receivable = partner.credit
        elif ttype == 'receipt':
            payable_receivable = partner.debit
        res['value']['payable_receivable'] = payable_receivable
        return res

    def transaksi_change(self,cr,uid,ids,transaksi,context=None):
        val = {}
        if transaksi :
            val['jenis_transaksi_id'] = False
        return {'value':val}
      
    def change_kwitansi(self,cr,uid,ids,kwitansi,context=None):
        vals = {}
        if kwitansi :
            vals['line_cr_ids'] = False
            vals['line_dr_ids'] = False
        return {'value':vals}
    
    def jenis_transaksi_change(self, cr, uid, ids, jenis_transaksi_id,branch_id):
        payments_request_histrory=[]
        if jenis_transaksi_id : 
            pr_pool = self.pool.get('account.voucher')
            pr_search = pr_pool.search(cr,uid,[('jenis_transaksi_id','=',jenis_transaksi_id),('branch_id','=',branch_id),])
            pr_pool2 = self.pool.get('account.voucher.line')
            pr_search2 = pr_pool2.search(cr,uid,[('voucher_id','=',pr_search),])
            payments_request_histrory = []
            if not pr_search2 :
                payments_request_histrory = []
            elif pr_search2 :
                pr_browse = pr_pool2.browse(cr,uid,pr_search2)           
                for x in pr_browse :
                    payments_request_histrory.append([0,0,{
                        'account_id':x.account_id.id,
                        'name':x.name,
                        'amount':x.amount,
                        'analytic_2':x.analytic_2.id,
                        'analytic_3':x.analytic_3.id,
                        'account_analytic_id':x.account_analytic_id.id,
                    }])
        return {'value':{'payments_request_ids': payments_request_histrory}}
        
    def branch_id_onchange(self,cr,uid,ids,branch_id,context=None):
        dom={}
        val = {}
        edi_doc_list = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.pool.get('dym.account.filter').get_domain_account(cr,uid,ids,'other_receivable_header',context=None)
        edi_doc_list.extend(dict)      
        dom['account_id'] = edi_doc_list
        if branch_id :
            branch_search = self.pool.get('dym.branch').browse(cr,uid,branch_id)
            branch_config = self.pool.get('dym.branch.config').search(cr,uid,[
                ('branch_id','=',branch_id)
            ])
            if not branch_config :
                raise osv.except_osv(('Perhatian !'), ("Belum ada branch config atas branch %s !")%(branch_search.code))
            else :
                branch_config_browse = self.pool.get('dym.branch.config').browse(cr,uid,branch_config)
                if context.get('other_receivable',False) == 'other_receivable':
                    journal_other_receivable =  branch_config_browse.dym_other_receivable_account_id.id
                    if not journal_other_receivable :
                        raise osv.except_osv(('Perhatian !'), ("Journal Payment Request belum diisi dalam branch %s !")%(branch_search.code))
                    val['journal_id'] = journal_other_receivable

            user_obj = self.pool.get('res.users')         
            user = user_obj.browse(cr,uid,uid)
            if user.branch_type!='HO':
                if not user.branch_id:
                    raise except_orm(_('Warning!'), _('User %s tidak memiliki default branch !' % user.login))
                dom['branch_id'] = [('id','=',branch_id)]
                dom['inter_branch_id'] = [('id','=',branch_id)]
                val['division'] = 'Umum'
                #val['division'] = 'Unit'
                #val['inter_branch_division'] = 'Unit'
            else:
                dom['branch_id'] = [('branch_type','=','HO'),('id','in',user.branch_ids.ids),('company_id','=',branch_search.company_id.id)]
                branch_ids = [b.id for b in user.branch_ids if b.company_id.id==branch_search.company_id.id]
                dom['inter_branch_id'] = [('id','in',branch_ids)]
                val['division'] = 'Umum'

            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_search, 'Umum',False, 4, 'General')
            val['analytic_1'] = analytic_1
            val['analytic_2'] = analytic_2
            val['analytic_3'] = analytic_3
            val['analytic_4'] = analytic_4
        return {'domain':dom,'value': val} 
        
    def faktur_pajak_change(self,cr,uid,ids,no_faktur_pajak,context=None):   
        value = {}
        warning = {}
        if no_faktur_pajak :
            cek = no_faktur_pajak.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Nomor Faktur Pajak Hanya Boleh Angka ! ')),
                }
                value = {
                    'no_faktur_pajak':False
                }     
        return {'warning':warning,'value':value} 
       
    def create(self,cr,uid,vals,context=None):
        context = {} if context == None else context
        if context.get('hutang_lain') :
            vals['is_hutang_lain'] = True  
        amount = 0.0 
        amount_cr = 0.0
        amount_dr = 0.0
        # if not vals.get('line_cr_ids') and not vals.get('line_dr_ids') and (not context.get('is_hutang_lain') and context.get('type') == 'receipt'):
        #     raise osv.except_osv(('Perhatian !'), ("Payment Information harap diisi baik bagian Credit atau Debit!"))
        if vals.get('line_cr_ids') :
            for x in vals['line_cr_ids'] :
                amount += x[2]['amount']
                amount_cr += x[2]['amount']
        if vals.get('line_dr_ids') :
            for x in vals['line_dr_ids'] :
                amount += x[2]['amount']
                amount_dr += x[2]['amount']
        if vals.get('amount') < 0.0 and vals.get('type') in  ('payment','receipt') and not context.get('hutang_lain'):
            if not (vals['line_cr_ids'] and vals.get('type') == 'payment') and not (vals['line_dr_ids'] and vals.get('type') == 'receipt'):
                raise osv.except_osv(('Perhatian !'), ("Paid Amount tidak boleh minus"))
        if vals.get('type') in ('payment','receipt') and not context.get('hutang_lain') :
            if vals.get('writeoff_amount',0.0) < 0.0 and vals.get('payment_option') == 'without_writeoff' :
                if not (vals['line_cr_ids'] and vals.get('type') == 'payment') and not (vals['line_dr_ids'] and vals.get('type') == 'receipt'):
                    raise osv.except_osv(('Perhatian !'), ("Nilai difference amount tidak boleh kurang dari nol !"))   
            elif vals.get('type') == 'receipt' and vals.get('line_cr_ids') and  vals.get('payment_option') == 'without_writeoff' and vals.get('writeoff_amount',0.0) > 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Nilai difference amount tidak boleh lebih dari nol !"))   
            elif vals.get('type') == 'payment' and vals.get('line_dr_ids') and vals.get('payment_option') == 'without_writeoff' and vals.get('writeoff_amount',0.0) > 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Nilai difference amount tidak boleh lebih dari nol !"))   
            elif vals.get('type') == 'receipt' and vals.get('line_cr_ids') and not vals.get('line_dr_ids') and vals.get('amount') == 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa memotong AR, mohon periksa kembali data anda !"))   
            elif vals.get('type') == 'payment' and vals.get('line_dr_ids') and not vals.get('line_cr_ids') and vals.get('amount') == 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa memotong AP, mohon periksa kembali data anda !"))
            if not (vals['line_cr_ids'] and vals.get('type') == 'payment') and not (vals['line_dr_ids'] and vals.get('type') == 'receipt'):
                if vals.get('type') == 'receipt' and amount_dr != 0.0 :
                    if amount_cr > amount_dr :
                        raise osv.except_osv(('Perhatian !'), ("Nilai Difference Amount tidak boleh minus !"))              
                elif vals.get('type') == 'payment' and amount_cr != 0.0 :
                    if amount_cr < amount_dr :
                        raise osv.except_osv(('Perhatian !'), ("Nilai Difference Amount tidak boleh minus !"))              
                                      
        vals['number'] = self.generate_sequence(cr, uid, vals, context=context)
        res = super(dym_account_voucher_custom,self).create(cr,uid,vals,context=context)
        value = self.browse(cr,uid,res)
        if value.type in ('sale','purchase') or value.type == 'receipt' and value.is_hutang_lain :
            self.compute_tax(cr,uid,value.id,context)
            if value.payment_option == 'without_writeoff' :
                self.cek_amount_total_per_detail(cr, uid, value.id, value, amount, context=context)         
        if value.is_hutang_lain :
            diff_total = sum(value.line_cr_ids.mapped('amount')) - value.paid_amount
            if diff_total != 0 :
                raise osv.except_osv(('Perhatian !'), ("Amount total harus sama dengan total detail"))            
        return res
    
    def cek_amount_total_per_detail(self,cr,uid,ids,value,amount,context=None):
        amount_value = round(value.amount,2)
        amount_and_tax = round(amount,2)+round(value.tax_amount,2) if not value.tax_id.price_include else amount_value
        diff_total = amount_value - amount_and_tax
        if value.type in ('sale','purchase') :
            if diff_total != 0 :
                raise osv.except_osv(('Perhatian !'), ("Amount total harus sama dengan total detail Rp.%s")%(amount))                               
        elif value.type == 'receipt' and value.is_hutang_lain :
            if diff_total != 0 :
                raise osv.except_osv(('Perhatian !'), ("Amount total harus sama dengan total detail Rp.%s")%(amount))            
        return True
                
    def write(self,cr,uid,ids,vals,context=None):
        res = super(dym_account_voucher_custom,self).write(cr,uid,ids,vals)
        value = self.browse(cr,uid,ids)
        # if value.number and value.division:
        #     if value.number[:5] == 'CPA-S' and value.division != 'Unit':
        #         raise osv.except_osv(('Perhatian !'), ("Nomor CPA sudah terbentuk dan tidak bisa mengganti divisi!"))
        #     elif value.number[:5] == 'CPA-W' and value.division != 'Sparepart':
        #         raise osv.except_osv(('Perhatian !'), ("Nomor CPA sudah terbentuk dan tidak bisa mengganti divisi!"))
        # if value.number:
        #     if not vals.get('line_cr_ids') and not vals.get('line_dr_ids') and (not context.get('is_hutang_lain') and context.get('type') == 'receipt'):
        #         raise osv.except_osv(('Perhatian !'), ("Payment Information harap diisi baik bagian Credit atau Debit!"))
        if vals.get('type') or vals.get('line_cr_ids') or vals.get('line_dr_ids') or vals.get('amount') or vals.get('writeoff_amount') or vals.get('payment_option') :
            if value.type in ('sale','purchase') or (value.type =='receipt' and value.is_hutang_lain) :
                if vals.get('tax_id') or vals.get('line_cr_ids') or vals.get('line_dr_ids'):
                    self.compute_tax(cr,uid,ids,context) 
            else :             
                self.check_amount_with_or_not_writeoff(cr, uid, ids, context=context)
        for voucher in value:
            if voucher.is_hutang_lain :
                diff_total = sum(voucher.line_cr_ids.mapped('amount')) - voucher.paid_amount
                if diff_total != 0 :
                    raise osv.except_osv(('Perhatian !'), ("Amount total harus sama dengan total detail"))   
        return res       
        
    def account_move_get(self, cr, uid, voucher_id, context=None):
        res = super(dym_account_voucher_custom,self).account_move_get(cr,uid,voucher_id,context=context)
        res['transaction_id'] = voucher_id
        res['model'] = self.browse(cr, uid, voucher_id).__class__.__name__
        return res
    
    def first_move_line_get(self, cr, uid, voucher_id, move_id, company_currency, current_currency, context=None):
        res = super(dym_account_voucher_custom,self).first_move_line_get(cr, uid, voucher_id, move_id, company_currency, current_currency, context=context)
        voucher = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        res['analytic_account_id'] = voucher.analytic_4.id
        return res
        
    def check_amount_with_or_not_writeoff(self,cr,uid,ids,context=None):
        voucher = self.browse(cr,uid,ids)
        amount = 0.0 
        amount_cr = 0.0
        amount_dr = 0.0      
        if voucher.line_cr_ids :
            for x in voucher.line_cr_ids :
                amount += x.amount
                amount_cr += x.amount
                
        if voucher.line_dr_ids :
            for x in voucher.line_dr_ids :
                amount += x.amount
                amount_dr += x.amount

        amount += voucher.tax_amount              
        if voucher.amount < 0.0 and voucher.type in ('payment','receipt') and not voucher.is_hutang_lain:
            if not (voucher.line_cr_ids and voucher.type == 'payment') and not (voucher.line_dr_ids and voucher.type == 'receipt'):
                raise osv.except_osv(('Perhatian !'), ("Paid Amount tidak boleh minus")) 
        if voucher.type in ('payment','receipt') and not voucher.is_hutang_lain :    
            amount_writeoff = voucher.writeoff_amount or 0.0      
            amount2 = self._compute_writeoff_amount(cr, uid, voucher.line_dr_ids, voucher.line_cr_ids, voucher.amount, voucher.type)
            if amount2 < 0.0 and voucher.payment_option == 'without_writeoff' :
                if not (voucher.line_cr_ids and voucher.type == 'payment') and not (voucher.line_dr_ids and voucher.type == 'receipt'):
                    raise osv.except_osv(('Perhatian !'), ("Nilai difference amount tidak boleh kurang dari nol !"))   
            elif voucher.type == 'receipt' and voucher.line_cr_ids and voucher.payment_option == 'without_writeoff' and voucher.writeoff_amount > 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Nilai difference amount tidak boleh lebih dari nol !"))   
            elif voucher.type == 'payment' and voucher.line_dr_ids and voucher.payment_option == 'without_writeoff' and voucher.writeoff_amount > 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Nilai difference amount tidak boleh lebih dari nol !"))   
            elif voucher.type == 'receipt' and voucher.line_cr_ids and not voucher.line_dr_ids and voucher.amount == 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa memotong AR, mohon periksa kembali data anda !"))   
            elif voucher.type == 'payment' and voucher.line_dr_ids and not voucher.line_cr_ids and voucher.amount == 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa memotong AP, mohon periksa kembali data anda !"))                
            if not (voucher.line_cr_ids and voucher.type == 'payment') and not (voucher.line_dr_ids and voucher.type == 'receipt'):
                if voucher.type  == 'receipt' and amount_dr != 0.0 :
                    if amount_cr > amount_dr :
                        raise osv.except_osv(('Perhatian !'), ("Nilai Difference Amount tidak boleh minus !"))              
                elif voucher.type == 'payment' and amount_cr != 0.0   :
                    if amount_cr < amount_dr :
                        raise osv.except_osv(('Perhatian !'), ("Nilai Difference Amount tidak boleh minus !"))              
                              
        if voucher.type in ('sale','purchase') or voucher.type == 'receipt' and voucher.is_hutang_lain :
            if voucher.payment_option == 'without_writeoff' :
                self.cek_amount_total_per_detail(cr, uid, ids, voucher, amount, context=context) 
        return True
    
    def generate_sequence(self,cr,uid,vals,context=None):
        name = '/'
        if vals.get('is_hutang_lain') == True and vals.get('type') == 'receipt' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'CDE', division='Umum') 
        elif not vals.get('is_hutang_lain') and vals.get('type') == 'receipt' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'CPA', division=vals['division']) 
        elif vals.get('type') == 'payment' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'SPA', division=vals['division']) 
        elif vals.get('type') == 'sale' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'NDE', division='Umum')
        elif vals.get('type') == 'purchase' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'PAR', division='Umum')
        return name   
             
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_account_voucher_custom, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        obj_active = self.browse(cr,uid,context.get('active_id',[]))
        if not context.get('portal'):
            if 'branch_id' in context:
                branch_id = context['branch_id']
            else:
                if not ('active_model' in context and context['active_model'] != 'account.voucher'):
                    branch_id = obj_active.branch_id.id
                    kwitansi=obj_active.kwitansi_id.id
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='kwitansi_id']")
            for node in nodes:
                    node.set('domain', '[("payment_id","=",False),("branch_id", "=", '+ str(branch_id)+'),("state","=","open")]')
            res['arch'] = etree.tostring(doc)
        for field in res['fields']:
            if field == 'division':
                if 'menu' in context and context['menu'] == 'showroom':
                    res['fields'][field]['selection'] = [('Unit','Showroom'), ('Umum','General')]

                if 'menu' in context and context['menu'] == 'workshop':
                    res['fields'][field]['selection'] = [('Sparepart','Workshop'), ('Umum','General')]

                if 'menu' in context and context['menu'] == 'general_affair':
                    res['fields'][field]['selection'] = [('Unit','Showroom'), ('Sparepart','Workshop'), ('Umum','General')]
        return res

    def onchange_price(self, cr, uid, ids, line_ids, tax_id, partner_id=False, context=None):
        context = context or {}
        tax_pool = self.pool.get('account.tax')
        partner_pool = self.pool.get('res.partner')
        position_pool = self.pool.get('account.fiscal.position')
        if not line_ids:
            line_ids = []
        res = {
            'tax_amount': False,
            'amount': False,
        }
        voucher_total = 0.0
        line_ids = self.resolve_2many_commands(cr, uid, 'line_ids', line_ids, ['amount'], context)
        total_tax = 0.0
        for line in line_ids:
            line_amount = 0.0
            line_amount = line.get('amount',0.0)
            if tax_id:
                tax = [tax_pool.browse(cr, uid, tax_id, context=context)]
                if partner_id:
                    partner = partner_pool.browse(cr, uid, partner_id, context=context) or False
                    taxes = position_pool.map_tax(cr, uid, partner and partner.property_account_position or False, tax)
                    tax = tax_pool.browse(cr, uid, taxes, context=context)
 
                if not tax[0].price_include:
                    for tax_line in tax_pool.compute_all(cr, uid, tax, line_amount, 1).get('taxes', []):
                        total_tax += tax_line.get('amount')
 
            voucher_total += line_amount
        total = voucher_total + total_tax
 
        res.update({
            'amount': total or voucher_total,
            'tax_amount': total_tax
        })
        if tax_id == False :
            res.update({
                'pajak_gabungan':False,
                'pajak_gunggung':False,
                'no_faktur_pajak': False,
                'tgl_faktur_pajak':False,
            })            
        return {
            'value': res
        }
            
    def branch_onchange_payment_request(self,cr,uid,ids,branch_id,context=None):
        account_id=False
        journal_id=False
        val = {}
        dom = {}
        sel = {}
        if branch_id:
            branch_config =self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
            branch_config_browse = self.pool.get('dym.branch.config').browse(cr,uid,branch_config)
            journal_id=branch_config_browse.dym_payment_request_account_id.id
            account_id=branch_config_browse.dym_payment_request_account_id.default_credit_account_id.id
            if not journal_id :
                    raise except_orm(_('Warning!'), _('Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu !'))
            if not account_id :
                    raise except_orm(_('Warning!'), _('Konfigurasi jurnal account cabang belum dibuat, silahkan setting dulu !'))
            if branch_config_browse.branch_id.is_pedagang_eceran == True:
                val['is_pedagang_eceran'] = True
            else:
                val['is_pedagang_eceran'] = False
            branch_obj =  self.pool.get('dym.branch').browse(cr, uid, branch_id)
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            if user.branch_type!='HO':
                if not user.branch_id:
                    raise except_orm(_('Warning!'), _('User %s tidak memiliki default branch !' % user.login))
                dom['branch_id'] = [('id','=',user.branch_id.id)]
            else:
                dom['branch_id'] = [('id','in',user.branch_ids.ids),('company_id','=',branch_obj.company_id.id)]
            sel['division'] = [('Unit','Showroom'),('Sparepart','Workshop')]
            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_obj, 'Umum',False, 4, 'General')
            val['analytic_1'] = analytic_1
            val['analytic_2'] = analytic_2
            val['analytic_3'] = analytic_3
            val['analytic_4'] = analytic_4
        else:
            val['is_pedagang_eceran'] = False
        val['account_id'] = account_id
        val['journal_id'] = journal_id
        return {'value':val,'domain':dom,'selection':sel}
                    
    def onchange_payment_req_type(self, cr, uid, ids, context=None):
        value = {}
        value['line_dr_ids'] = []
        return {'value':value}

    def branch_change(self, cr, uid, ids, branch, type, context=None):
        value = {}
        domain = {}
        user_obj = self.pool.get('res.users')         
        user = user_obj.browse(cr,uid,uid)
        if branch:
            if context.get('type',False)=='receipt':
                domain['journal_id'] = [('branch_id','in',[branch,False]),('type','in',['bank','cash','edc'])]
            else:              
                domain['journal_id'] = [('branch_id','in',[branch,False]),('type','in',['pettycash','bank','cash','edc'])]

            branch_obj =  self.pool.get('dym.branch').browse(cr, uid, branch)
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            if user.branch_type!='HO':
                if not user.branch_id:
                    raise except_orm(_('Warning!'), _('User %s tidak memiliki default branch !' % user.login))
                domain['branch_id'] = [('id','=',user.branch_id.id)]
            else:
                domain['branch_id'] = [('branch_type','=','HO'),('id','in',user.branch_ids.ids),('company_id','=',branch_obj.company_id.id)]

            if user.branch_type!='HO':
                value['division'] = 'Unit'
            else:
                value['division'] = 'Finance'
            value['line_ids'] = []
            value['line_cr_ids'] = []
            value['line_dr_ids'] = []
            branch_obj =  self.pool.get('dym.branch').browse(cr, uid, branch)
            analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_obj, 'Umum',False, 4, 'General')
            value['analytic_1'] = analytic_1
            value['analytic_2'] = analytic_2
            value['analytic_3'] = analytic_3
            value['analytic_4'] = analytic_4
        return {'value':value, 'domain':domain}
        
    def inter_branch_receipt_change(self, cr, uid, ids, branch_id, inter_branch, inter_branch_division, account_id, context=None):
        value = {}
        dom = {}
        analytic_filter_obj = self.pool.get('analytic.account.filter')
        account_analytic_obj = self.pool.get('account.analytic.account')
        user_obj = self.pool.get('res.users')         
        user = user_obj.browse(cr,uid,uid)
        if branch_id:
            # dom['partner_id'] = [('customer','=',True),('credit','>',0)]
            dom['partner_id'] = [('customer','=',True)]
            branch_src = self.pool.get('dym.branch').browse(cr, uid, branch_id)
            if user.branch_type!='HO':
                dom['inter_branch_id'] = [('id','=',branch_id)]
                value['inter_branch_id'] = branch_id
            else:
                branch_ids = [b.id for b in user.branch_ids if b.company_id.id==branch_src.company_id.id]
                dom['inter_branch_id'] = [('id','in',branch_ids)]
        if inter_branch and inter_branch_division and account_id:
            aa1_ids, aa2_ids, aa3_ids, aa4_ids, df1, df2, df3, df4, aa_dict = analytic_filter_obj.get_analytics(cr, uid, ids, inter_branch, inter_branch_division, account_id, context=context)
            value['analytic_1'] = df1
            value['analytic_2'] = df2
            value['analytic_3'] = df3
            value['analytic_4'] = df4
            value['account_analytic_id'] = df4
            dom['analytic_1'] = [('id','in',aa1_ids)]
            dom['analytic_2'] = [('id','in',aa2_ids)]
            dom['analytic_3'] = [('id','in',aa3_ids)]
            dom['analytic_4'] = [('id','in',aa4_ids)]

        if inter_branch:
            inter_branch_id = self.pool.get('dym.branch').browse(cr, uid, inter_branch)
            analytic_filter = ""
            if account_id: 
                analytic_filter_id = analytic_filter_obj.search(cr, uid, [('account_id','=',account_id),('branch_type','=',inter_branch_id.branch_type)])
                analytic_filter = analytic_filter_obj.browse(cr, uid, analytic_filter_id)
            if analytic_filter:
                analytic_1, analytic_2, analytic_3, analytic_4 = account_analytic_obj.get_analytical(cr, uid, inter_branch, analytic_filter.bisnis_unit.name, False, 4, analytic_filter.cost_center)
            elif inter_branch_division:
                analytic_1, analytic_2, analytic_3, analytic_4 = account_analytic_obj.get_analytical(cr, uid, inter_branch, inter_branch_division, False, 4, 'General')
            else:
                analytic_1, analytic_2, analytic_3, analytic_4 = account_analytic_obj.get_analytical(cr, uid, inter_branch, 'Umum', False, 4, 'General')
            value['analytic_1'] = analytic_1
            value['analytic_2'] = analytic_2
            value['analytic_3'] = analytic_3      
            value['analytic_4'] = analytic_4

        value['line_cr_ids'] = []
        value['line_ids'] = []
        value['line_cr_ids'] = []
        value['line_dr_ids'] = []
        return {'value':value,'domain':dom}

    def inter_branch_payment_change(self, cr, uid, ids, branch_id, inter_branch, context=None):
        value = {}
        dom = {}
        user_obj = self.pool.get('res.users')         
        user = user_obj.browse(cr,uid,uid)
        if branch_id:
            dom['partner_id'] = [('supplier','=',True),('debit','>',0)]
            if not inter_branch:
                value['inter_branch_id'] = branch_id
            branch_src = self.pool.get('dym.branch').browse(cr, uid, branch_id)
            if user.branch_type!='HO':
                dom['inter_branch_id'] = [('id','=',branch_id)]
                value['inter_branch_id'] = branch_id
            else:
                branch_ids = [b.id for b in user.branch_ids if b.company_id.id==branch_src.company_id.id]
                dom['inter_branch_id'] = [('id','in',branch_ids)]
        value['line_cr_ids'] = []
        value['line_ids'] = []
        value['line_cr_ids'] = []
        value['line_dr_ids'] = []
        return {'value':value,'domain':dom}
    
    def action_move_line_create(self, cr, uid, ids, context=None):
        res = super(dym_account_voucher_custom,self).action_move_line_create(cr, uid, ids, context=context)
        for voucher_data in self.browse(cr,uid,ids) :
            for voucher_line in voucher_data.line_ids:
                if voucher_line.move_line_id.date and voucher_line.move_line_id.date > voucher_data.date:
                    raise osv.except_osv(('Perhatian !'), ("Tidak bisa confirm voucher! Tanggal efektif jurnal item %s adalah %s, tanggal efektif voucher: %s!")%(voucher_line.move_line_id.name, voucher_line.move_line_id.date, voucher_data.date))
                if voucher_line.move_line_id.avp_id :
                    source_settlement = voucher_data.number
                    if voucher_line.move_line_id.avp_id.source_settlement not in [False, '']:
                        source_settlement = voucher_line.move_line_id.avp_id.source_settlement + ' ' + voucher_data.number
                    voucher_line.move_line_id.avp_id.write({'source_settlement': source_settlement})
                    if voucher_line.move_line_id.reconcile_id:
                        workflow.trg_validate(uid, 'dym.advance.payment', voucher_line.move_line_id.avp_id.id, 'avp_done', cr)
            if voucher_data.move_ids :
                for line in voucher_data.move_ids :
                    if not line.branch_id :
                        line.write({'branch_id':voucher_data.branch_id.id,'division':voucher_data.division,'date_maturity':voucher_data.date_due})
                    if not line.division :
                        line.write({'division':voucher_data.division,'date_maturity':voucher_data.date_due})
        return res
        
    def onchange_division(self,cr,uid,ids,division,context=None):
        value = {}
        if division :
            value['line_cr_ids'] = []
            value['line_ids'] = []
            value['line_cr_ids'] = []
            value['line_dr_ids'] = []
            val = self.browse(cr,uid,ids)
            user = self.pool.get('res.users').browse(cr,uid,uid)
            if user.branch_type == 'DL':
               value['inter_branch_id'] = val.branch_id.id
               value['inter_branch_division'] = division
        return {'value':value}
                        
    def onchange_journal_account_voucher(self, cr, uid, ids, branch_id, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=None):
        if context is None:
            context = {}
        if not journal_id:
            return False
        journal_pool = self.pool.get('account.journal')
        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        vals = {'value':{} }
        current_balance = 0.0
        if ttype in ('payment', 'purchase') and journal.type in ['bank','edc']: 
            vals['value'].update({
                'clearing_bank':True,
            })
        if journal.type in ['bank','edc']: 
            #current_balance = journal.default_debit_account_id.balance
            current_balance = self.get_journal_balance(cr, uid, ids, branch_id, journal_id, context=context)

        if journal.type in ['cash','pettycash']: 
            current_balance = self.get_journal_balance(cr, uid, ids, branch_id, journal_id, context=context)
        vals['value'].update({
            'current_balance': current_balance,
        })
        account_id = journal.default_credit_account_id or journal.default_debit_account_id
        tax_id = False
        if account_id and account_id.tax_ids:
            tax_id = account_id.tax_ids[0].id
        if ttype in ('sale', 'purchase'):
            vals['value'].update({'tax_id':tax_id,'amount': amount})
        currency_id = False
        if journal.currency:
            currency_id = journal.currency.id
        else:
            currency_id = journal.company_id.currency_id.id

        period_id = self.pool.get('account.period').find(cr, uid, context=dict(context, company_id=company_id))
        vals['value'].update({
            'currency_id': currency_id,
            'payment_rate_currency_id': currency_id,
            'period_id' : period_id and period_id[0],
            'account_id':account_id
        })
        return vals
                            
    def interco_move_line_create(self,cr,uid,ids,move_lines,voucher_data,context=None):
        #Make journal intercompany
        branch_rekap = {}    
        branch_pool = self.pool.get('dym.branch')        
        if voucher_data.inter_branch_id :      
            move_line = self.pool.get('account.move.line')          
            #Merge Credit and Debit by Branch                          
            for x in move_lines :
                if x.branch_id not in branch_rekap :
                    branch_rekap[x.branch_id] = {}
                    branch_rekap[x.branch_id]['debit'] = x.debit
                    branch_rekap[x.branch_id]['credit'] = x.credit
                else :
                    branch_rekap[x.branch_id]['debit'] += x.debit
                    branch_rekap[x.branch_id]['credit'] += x.credit    
                                                
            config = branch_pool.search(cr,uid,[('id','=',voucher_data.branch_id.id)])
            config_destination = branch_pool.search(cr,uid,[('id','=',voucher_data.inter_branch_id.id)])
            
            if config :
                config_browse = branch_pool.browse(cr,uid,config)
                inter_branch_account_id = config_browse.inter_company_account_id.id
                if not inter_branch_account_id :
                    raise osv.except_osv(('Perhatian !'), ("Account Inter Company belum diisi dalam Master branch %s !")%(voucher_data.branch_id.name))
            elif not config :
                    raise osv.except_osv(('Perhatian !'), ("Account Inter Company belum diisi dalam Master branch %s !")%(voucher_data.branch_id.name))
            
            if config_destination :
                config_browse_destination = branch_pool.browse(cr,uid,config_destination)
                inter_branch_terima_account_id = config_browse_destination.inter_company_account_id.id
                if not inter_branch_terima_account_id :
                    raise osv.except_osv(('Perhatian !'), ("Account Inter Company belum diisi dalam Master branch %s !")%(voucher_data.inter_branch_terima_account_id.name))   
            for key,value in branch_rekap.items() :
                if key != voucher_data.branch_id :
                    balance = value['debit']-value['credit']
                    debit = abs(balance) if balance < 0 else 0
                    credit = balance if balance > 0 else 0
                    if balance != 0:
                        move_line_create = {
                            'name': _('Interco Account Voucher %s')%(key.name),
                            'ref':_('Interco Account Voucher %s')%(key.name),
                            'account_id': inter_branch_account_id,
                            'move_id': voucher_data.move_id.id,
                            'journal_id': voucher_data.journal_id.id,
                            'period_id': voucher_data.period_id.id,
                            'date': voucher_data.date,
                            'debit': debit,
                            'credit': credit,
                            'branch_id' : key.id,
                            'division' : voucher_data.division,
                            'partner_id' : voucher_data.partner_id.id                    
                        }    
                        inter_first_move = move_line.create(cr, uid, move_line_create, context)                                 
                        move_line2_create = {
                            'name': _('Interco Account Voucher %s')%(voucher_data.branch_id.name),
                            'ref':_('Interco Account Voucher %s')%(voucher_data.branch_id.name),
                            'account_id': inter_branch_terima_account_id,
                            'move_id': voucher_data.move_id.id,
                            'journal_id': voucher_data.journal_id.id,
                            'period_id': voucher_data.period_id.id,
                            'date': voucher_data.date,
                            'debit': credit,
                            'credit': debit,
                            'branch_id' : voucher_data.branch_id.id,
                            'division' : voucher_data.division,
                            'partner_id' : voucher_data.partner_id.id                       
                        }    
                        inter_second_move = move_line.create(cr, uid, move_line2_create, context) 
        return True

    def voucher_move_line_create(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency, context=None):
        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        tot_line = line_total
        rec_lst_ids = []

        date = self.read(cr, uid, [voucher_id], ['date'], context=context)[0]['date']
        ctx = context.copy()
        ctx.update({'date': date})
        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=ctx)
        voucher_currency = voucher.journal_id.currency or voucher.company_id.currency_id
        ctx.update({
            'voucher_special_currency_rate': voucher_currency.rate * voucher.payment_rate ,
            'voucher_special_currency': voucher.payment_rate_currency_id and voucher.payment_rate_currency_id.id or False,})
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        obj_branch_config_search = self.pool.get('dym.branch.config').search(cr, uid, [('branch_id','=',voucher.branch_id.id)])
        obj_branch_config = self.pool.get('dym.branch.config').browse(cr, uid, obj_branch_config_search)
        date_maturity = voucher.due_date_payment if voucher.type == 'payment' else False
        if not voucher.is_hutang_lain and voucher.type == 'receipt':
            date_maturity = voucher.date
        for line in voucher.line_ids:
            #create one move line per voucher line where amount is not 0.0
            # AND (second part of the clause) only if the original move line was not having debit = credit = 0 (which is a legal value)
            if not line.amount and not (line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit, precision_digits=prec) and not float_compare(line.move_line_id.debit, 0.0, precision_digits=prec)):
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_curreny.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            amount = self._convert_amount(cr, uid, line.untax_amount or line.amount, voucher.id, context=ctx)
            # if the amount encoded in voucher is equal to the amount unreconciled, we need to compute the
            # currency rate difference
            if line.amount == line.amount_unreconciled:
                if not line.move_line_id:
                    raise osv.except_osv(_('Wrong voucher line'),_("The invoice you are willing to pay is not valid anymore."))
                sign = line.type =='dr' and -1 or 1
                currency_rate_difference = sign * (line.move_line_id.amount_residual - amount)
            else:
                currency_rate_difference = 0.0
            
            analytic_account_id = line.account_analytic_id
            if line.move_line_id and line.move_line_id.analytic_account_id and (voucher.type in ('payment','receipt') and voucher.is_hutang_lain == False):
                analytic_account_id = line.move_line_id.analytic_account_id

            move_line = {
                'unidentified_payment': voucher.unidentified_payment,
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'currency_id': line.move_line_id and (company_currency <> line.move_line_id.currency_id.id and line.move_line_id.currency_id.id) or False,
                'analytic_account_id' : analytic_account_id.id,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': voucher.date,
                'date_maturity': date_maturity,
            }
            if amount < 0:
                amount = -amount
                if line.type == 'dr':
                    line.type = 'cr'
                else:
                    line.type = 'dr'

            if (line.type=='dr'):
                tot_line += amount
                move_line['debit'] = amount
            else:
                tot_line -= amount
                move_line['credit'] = amount

            if voucher.tax_id and voucher.type in ('sale', 'purchase'):
                move_line.update({
                    'account_tax_id': voucher.tax_id.id,
                })

            # compute the amount in foreign currency
            foreign_currency_diff = 0.0
            amount_currency = False
            if line.move_line_id:
                # We want to set it on the account move line as soon as the original line had a foreign currency
                if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency:
                    # we compute the amount in that foreign currency.
                    if line.move_line_id.currency_id.id == current_currency:
                        # if the voucher and the voucher line share the same currency, there is no computation to do
                        sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                        amount_currency = sign * (line.amount)
                    else:
                        # if the rate is specified on the voucher, it will be used thanks to the special keys in the context
                        # otherwise we use the rates of the system
                        amount_currency = currency_obj.compute(cr, uid, company_currency, line.move_line_id.currency_id.id, move_line['debit']-move_line['credit'], context=ctx)
                if line.amount == line.amount_unreconciled:
                    foreign_currency_diff = line.move_line_id.amount_residual_currency - abs(amount_currency)

            move_line['amount_currency'] = amount_currency
            voucher_line = move_line_obj.create(cr, uid, move_line)
            rec_ids = [voucher_line, line.move_line_id.id]

            if line.move_line_id and line.move_line_id.currency_id and not currency_obj.is_zero(cr, uid, line.move_line_id.currency_id, foreign_currency_diff):
                # Change difference entry in voucher currency
                move_line_foreign_currency = {
                    'journal_id': line.voucher_id.journal_id.id,
                    'period_id': line.voucher_id.period_id.id,
                    'name': _('change')+': '+(line.name or '/'),
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': line.voucher_id.partner_id.id,
                    'currency_id': line.move_line_id.currency_id.id,
                    'amount_currency': -1 * foreign_currency_diff,
                    'quantity': 1,
                    'credit': 0.0,
                    'debit': 0.0,
                    'date': line.voucher_id.date,
                }
                new_id = move_line_obj.create(cr, uid, move_line_foreign_currency, context=context)
                rec_ids.append(new_id)
            if line.move_line_id.id:
                rec_lst_ids.append(rec_ids)
        voucher = (tot_line, rec_lst_ids)
        vals = self.browse(cr,uid,voucher_id)
        move_line = self.pool.get('account.move.line')
        move_obj = self.pool.get('account.move.line')
        if vals.type in ('receipt', 'payment') :
            if vals.inter_branch_id :
                inter_branch = vals.inter_branch_id.id
            else :
                inter_branch = vals.branch_id.id          
            move_ids = []
            for x in voucher[1] :
                move_ids += x
            move_browse = move_obj.browse(cr,uid,move_ids)
            for value in move_browse :
                if value.move_id.id != move_id :
                    continue
                if vals.type == 'receipt':
                    if value.account_id.type == 'payable' :
                        value.write({'branch_id':vals.branch_id.id,'division':vals.division})
                    elif not inter_branch:
                        value.write({'branch_id':move_browse.branch_id.id,'division':vals.division})
                    else:
                        value.write({'branch_id':inter_branch,'division':vals.division})
                elif vals.type == 'payment' :
                    if value.account_id.type == 'receivable' :
                        value.write({'branch_id':vals.branch_id.id,'division':vals.division})
                    elif not inter_branch:
                        value.write({'branch_id':move_browse.branch_id.id,'division':vals.division})
                    else :
                        value.write({'branch_id':inter_branch,'division':vals.division})
        
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
              
        move_obj=self.pool.get('account.move')
        move_line_obj=self.pool.get('account.move.line')
        move=move_obj.browse(cr,uid,move_id)

        ppn_x = 0
        for line in move.line_id:
            #Analytic Branch untuk Bank
            if vouc.journal_id.type=='bank':
                if vouc.journal_id:
                    if vouc.journal_id.branch_id:
                        aa_bank_1, aa_bank_2, aa_bank_3, aa_bank_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, vouc.journal_id.branch_id.id, 'Umum', False, 4, 'General')
                        if line.account_id.id == vouc.journal_id.default_debit_account_id.id or line.account_id.id == vouc.journal_id.clearing_account_id.id:
                            line.write({'analytic_account_id':aa_bank_4})
                    else:
                        raise osv.except_osv  (('Error!'), ('Branch dalam journal %s belum diset.' % vouc.journal_id.name))
            #Analytic Bisnis Unit untuk PPN di PAR
            if "PAR-G" in vouc.number:
                if 'PPN' in line.name:
                    payments_request_ids = sorted(vouc.payments_request_ids, key=lambda x: x.id)
                    if vouc.payments_request_ids:
                        analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, payments_request_ids[ppn_x].analytic_3.branch_id.id, payments_request_ids[ppn_x].analytic_2.bisnis_unit.name, False, 4, 'General')
                        line.write({'analytic_account_id':analytic_4})
                        ppn_x += 1
            #Analytic Bisnis Unit untuk PPh dan PPN
            elif "NDE-G" not in vouc.number:
                if 'PPh' in line.name:
                    if vouc.withholding_ids:
                        for wt in vouc.withholding_ids:
                            if wt.amount == line.tax_amount:
                                if wt.analytic_2:
                                    if wt.analytic_2.id != line.analytic_2.id:
                                        line.write({'analytic_2':wt.analytic_2.id})
                                        break
                                else:
                                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch.id, 'Service', False, 4, 'General')
                                    line.write({'analytic_account_id':analytic_4})
        
                elif 'PPN' in line.name:
                    if vouc.withholding_ids:
                        for wt in vouc.withholding_ids:
                            if wt.amount == line.tax_amount:
                                if wt.analytic_2:
                                    if wt.analytic_2.id != line.analytic_2.id:
                                        line.write({'analytic_2':wt.analytic_2.id})
                                        break
                                else:
                                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch.id, 'Service', False, 4, 'General')
                                    line.write({'analytic_account_id':analytic_4})
            else:
                if vouc.line_cr_ids:
                    if line.analytic_4.id != vouc.line_cr_ids[0].account_analytic_id.id:
                        line.write({'analytic_account_id':analytic_4})
                    else:
                        analytic__1, analytic__2, analytic__3, analytic__4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch.id, division, False, 4, vouc.line_cr_ids[0].account_analytic_id.cost_center)                
                        line.write({'analytic_account_id':analytic__4})
                else:
                    line.write({'analytic_account_id':analytic_4})

            # Untuk menambah line PPN dari Account Selisih STNK dan mengurangi nilai selisih STNK
            obj_tax=self.pool.get('account.tax')
            obj_branch_conf=self.pool.get('dym.branch.config')

            ppn_ids=obj_tax.search(cr,uid,[('type_tax_use2','=','non-trade'),('type_tax_use','=','sale'),('company_id','=',branch.company_id.id)])
            if ppn_ids:
                ppn=obj_tax.browse(cr,uid,ppn_ids[0])
                branch_config_ids=obj_branch_conf.search(cr,uid,[('branch_id','=',branch.id)])
                if branch_config_ids:
                    branch_config=obj_branch_conf.browse(cr,uid,branch_config_ids[0])           
                    acc=branch_config.tagihan_birojasa_bbn_account_id
                    if line.account_id.id==acc.id:
                        if line.credit>0:
                            base_amount=line.credit/1.1
                            ppn_amount=base_amount * ppn.amount
                            line.move_id.button_cancel() 
                            line.write({'credit':line.credit - ppn_amount, 'analytic_account_id':analytic__4})
                            aml_ppn=move_line_obj.create(cr,uid,{
                                'name': ppn.description or '/',
                                'ref': vouc.number or '/',
                                'account_id': ppn.account_collected_id.id,
                                'journal_id': vouc.journal_id.id,
                                'period_id': vouc.period_id.id,
                                'date': vouc.create_date,
                                'date_maturity':vouc.date_due,
                                'debit': 0,
                                'credit': ppn_amount,
                                'branch_id' : branch.id,
                                'division' : division,
                                'partner_id' : vouc.partner_id.id,
                                'move_id': line.move_id.id,
                                'analytic_account_id' : analytic_4,
                                'tax_code_id':ppn.tax_code_id.id,
                                'tax_amount':base_amount,
                                })
                            line.move_id.post()
                            aml = move_line_obj.browse(cr,uid,aml_ppn)
                            aml.write({'analytic_account_id':analytic_4})
                            line.move_id.post()
        return voucher   
    
    def onchange_partner_type(self,cr,uid,ids,partner_type,context=None):
        dom={}        
        val={}
        if partner_type:
            domain_search = []
            obj_partner_type = self.pool.get('dym.partner.type').browse(cr, uid, [partner_type])
            if obj_partner_type.field_type == 'boolean':
                domain_search += [(obj_partner_type.name,'!=',False)]
            elif obj_partner_type.field_type == 'selection':
                domain_search += [(obj_partner_type.selection_name,'=',obj_partner_type.name)]
            dom['partner_id'] = domain_search
            val['partner_id'] = False                             
        return {'domain':dom,'value':val} 
            
    def print_wizard_kwitansi(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'kwitansi.wizard.customer.payment'), ("model", "=", 'account.voucher'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Kwitansi',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'target': 'new',
            'nodestroy': True,
            'res_id': obj_claim_kpb.id,
            'context': context
            }
        
    def reg_kwitansi(self, cr, uid, ids, vals, context=None):
        res = super(dym_account_voucher_custom, self).write(cr, uid, ids, vals, context=context)
        return res

    def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
        vals = super(dym_account_voucher_custom, self).recompute_voucher_lines(cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=context)
        if vals :
            if 'line_cr_ids' in vals['value'] :      
                del(vals['value']['line_cr_ids'])    
                                    
            if 'line_dr_ids' in vals['value'] :  
                del(vals['value']['line_dr_ids'])
                
        return vals

    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('dym.branch').get_default_date(cr,uid,ids,context=context)

    def proforma_voucher(self, cr, uid, ids, context=None):
        value = self.browse(cr,uid,ids)
        if not context:
            context = {}
        context['company_id'] = value.company_id.id
        total_dr = sum([x.amount for x in value.line_dr_ids])
        total_cr = sum([x.amount for x in value.line_cr_ids])
        if total_dr==0.0 and total_cr==0.0:
            raise osv.except_osv(('Perhatian !'), ("'Total Line Amount' tidak boleh Nol !!"))

        if value.allow_backdate == True and value.type in ('sale','purchase','receipt','payment'):
            periods = self.pool.get('account.period').find(cr, uid,dt=value.date, context=context)
            self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now(),'period_id':periods and periods[0]})
        else:
            periods = self.pool.get('account.period').find(cr, uid,dt=self._get_default_date(cr, uid, ids, context), context=context)
            self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now(),'date':self._get_default_date(cr, uid, ids, context=context),'period_id':periods and periods[0]})
        vals = super(dym_account_voucher_custom,self).proforma_voucher(cr, uid, ids, context=context)
        if not value.amount and value.journal_id.type == 'edc':
            raise osv.except_osv(('Perhatian !'), ("'Paid Amount' harus diisi untuk pembayaran menggunakan EDC"))
        if value.tax_id and not value.pajak_gabungan and not value.pajak_gunggung and value.type == 'sale' :
            no_pajak = self.pool.get('dym.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'account.voucher',context=context)
        if value.tax_id and value.pajak_gunggung == True and value.type == 'sale':   
            self.pool.get('dym.faktur.pajak.out').create_pajak_gunggung(cr,uid,ids,'account.voucher',context=context) 
        return vals
    
    def create_new_move(self, cr, uid, ids, id_old_move, context=None):
        move_pool = self.pool.get('account.move')
        new_move_line_id = False
        new_id_move = move_pool.copy(cr, uid, id_old_move)
        new_move_id = move_pool.browse(cr, uid, new_id_move)
        for line in new_move_id.line_id :
            if line.account_id.type in ('payable','receivable') :
                new_move_line_id = line.id
            credit = line.debit
            debit = line.credit
            line.write({'debit':debit,'credit':credit})            
        return new_move_line_id

    def cancel_voucher(self, cr, uid, ids, context=None):
        if context == None :
            context = {}        
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})
        reconcile_pool = self.pool.get('account.move.reconcile')
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        clearing_pool = self.pool.get('dym.clearing.giro')
        for voucher in self.browse(cr, uid, ids, context=context):
            voucher.refresh()                    
            if voucher.move_id:
                if voucher.clearing_bank:
                    move_line_id = move_line_pool.search(cr,uid,[('move_id','=',voucher.move_id.id)])
                    move_line = move_line_pool.browse(cr,uid,move_line_id)
                    for line in move_line:
                        if line.clear_state in ['open','cleared']:
                            clearing_id = clearing_pool.search(cr,uid,[('move_line_ids','=',line.id)])
                            if clearing_id:
                                clearing = clearing_pool.browse(cr,uid,clearing_id)
                                raise RedirectWarning(('Data %s sudah diproses, mohon cancel CBA terlebih dahulu!') % (clearing.name))
                voucher.move_id.action_reverse_journal()
        
        res = {
            'state':'cancel',
            'move_id':False,
        }
        self.write(cr, uid, ids, res)
        return True

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




    """ 
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

            # if voucher.type == 'receipt':
            #     account_id = voucher.partner_id.property_account_payable.id
            # elif voucher.type == 'payment':
            #     account_id = voucher.partner_id.property_account_receivable.id
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
                raise osv.except_osv(('Perhatian !'), ("Mohon lengkapi account rounding partner %s !")%(voucher.partner_id.name))  
            res.update({'account_id':account_id})    
            res.update({'analytic_account_id':voucher.analytic_4.id})    
            #Analytic Branch untuk Write Off
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
    """

    def onchange_line_ids(self, cr, uid, ids, line_dr_ids, line_cr_ids, amount, voucher_currency, type, context=None):
        res = super(dym_account_voucher_custom,self).onchange_line_ids(cr, uid, ids, line_dr_ids, line_cr_ids, amount, voucher_currency, type, context=context)
        line_dr_ids = self.resolve_2many_commands(cr, uid, 'line_dr_ids', line_dr_ids, ['amount'], context)
        line_cr_ids = self.resolve_2many_commands(cr, uid, 'line_cr_ids', line_cr_ids, ['amount'], context)
        writeoff_amount = self._compute_writeoff_amount(cr, uid, line_dr_ids, line_cr_ids, 0, type)
        res['value']['net_amount'] = writeoff_amount*-1
        res['value']['payment_option'] = 'without_writeoff'
        return res

    def onchange_wo_so(self, cr, uid, ids, wo_ids, wo_percentage, so_ids, so_percentage, paid_amount, context=None):
        value = {}
        wo_ids = self.resolve_2many_commands(cr, uid, 'wo_ids', wo_ids, ['amount_total'], context)
        so_ids = self.resolve_2many_commands(cr, uid, 'so_ids', so_ids, ['amount_total'], context)
        if not wo_ids and not so_ids:
            value['paid_amount'] = paid_amount
            return {'value' : value}
        wo_total = so_total = 0.0
        for l in wo_ids:
            if isinstance(l, dict):
                wo_total += l['amount_total']
        for l in so_ids:
            if isinstance(l, dict):
                so_total += l['amount_total']
        if wo_percentage < 60 or wo_percentage > 100:
            wo_percentage = 60
        if so_percentage < 60 or so_percentage > 100:
            so_percentage = 60
        wo_total = wo_total * wo_percentage / 100
        so_total = so_total * so_percentage  / 100
        if paid_amount < wo_total + so_total:
            paid_amount = wo_total + so_total
        value['wo_percentage'] = wo_percentage
        value['so_percentage'] = so_percentage
        value['wo_total'] = wo_total
        value['so_total'] = so_total
        value['paid_amount'] = paid_amount
        line_cr_ids = [[0,0,{'amount':paid_amount}]]
        value['line_cr_ids'] = line_cr_ids
        return {'value' : value}

    def writeoff_amount_change(self, cr, uid, ids, line_dr_ids, line_cr_ids, amount, type, context=None):
        res = {}
        line_dr_ids = self.resolve_2many_commands(cr, uid, 'line_dr_ids', line_dr_ids, ['amount'], context)
        line_cr_ids = self.resolve_2many_commands(cr, uid, 'line_cr_ids', line_cr_ids, ['amount'], context)
        writeoff_amount = self._compute_writeoff_amount(cr, uid, line_dr_ids, line_cr_ids, amount, type)
        if writeoff_amount == 0:
            res['payment_option'] = 'without_writeoff'
            # res['writeoff_amount'] = writeoff_amount
        else:
            res['payment_option'] = 'with_writeoff'
            # res['writeoff_amount'] = writeoff_amount
        return {'value':res}

class dym_account_voucher_line(osv.osv):
    _inherit = "account.voucher.line"

    def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled, context=None):
        vals = {}
        warning = {}
        if amount > amount_unreconciled:
            vals['amount'] = amount_unreconciled
            warning = {
                'title': _('Error!'), 
                'message': _("Nilai Alokasi tidak boleh lebih besar dari Open Balance (sisa A/R)")
            }
        if amount:
            vals['reconcile'] = (amount == amount_unreconciled)
        return {'value': vals, 'warning':warning}

    def _get_analytic_company(self,cr,uid,context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_account_vouche-2] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    def _get_analytic_2(self,cr,uid,context=None):
        return False

    # If the payment is in the same currency than the invoice, we keep the same amount
    # Otherwise, we compute from invoice currency to payment currency
    def _compute_balance(self, cr, uid, ids, name, args, context=None):
        print 
        currency_pool = self.pool.get('res.currency')
        rs_data = {}
        for line in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            ctx.update({'date': line.voucher_id.date})
            voucher_rate = self.pool.get('res.currency').read(cr, uid, line.voucher_id.currency_id.id, ['rate'], context=ctx)['rate']
            ctx.update({
                'voucher_special_currency': line.voucher_id.payment_rate_currency_id and line.voucher_id.payment_rate_currency_id.id or False,
                'voucher_special_currency_rate': line.voucher_id.payment_rate * voucher_rate})
            res = {}
            company_currency = line.voucher_id.journal_id.company_id.currency_id.id
            voucher_currency = line.voucher_id.currency_id and line.voucher_id.currency_id.id or company_currency
            move_line = line.move_line_id or False

            if not move_line:
                res['amount_original'] = 0.0
                res['amount_unreconciled'] = 0.0
            elif move_line.currency_id and voucher_currency==move_line.currency_id.id:
                res['amount_original'] = abs(move_line.amount_currency)
                res['amount_unreconciled'] = abs(move_line.fake_balance) + line.amount
            else:
                res['amount_original'] = currency_pool.compute(cr, uid, company_currency, voucher_currency, move_line.credit or move_line.debit or 0.0, context=ctx)
                res['amount_unreconciled'] = currency_pool.compute(cr, uid, company_currency, voucher_currency, move_line.fake_balance, context=ctx) + line.amount

            rs_data[line.id] = res
        return rs_data
        
    _columns = {
        'branch_dest_id': fields.many2one('dym.branch', string='For Branch'),
        'division_dest_id':fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')],'Division', change_default=True, select=True),
        'prepaid_id': fields.many2one('account.asset.asset', string='Prepaid/Asset'),
        'kwitansi' : fields.boolean(related='voucher_id.kwitansi',string='Yg Sudah Print Kwitansi'),
        'name' : fields.text(string='Description'),
        'analytic_1':  fields.many2one('account.analytic.account', 'Account Analytic Company'),
        'analytic_2':  fields.many2one('account.analytic.account', 'Account Analytic Bisnis Unit'),
        'analytic_3':  fields.many2one('account.analytic.account', 'Account Analytic Branch'),
        'account_analytic_id':  fields.many2one('account.analytic.account', 'Account Analytic Cost Center'),
        'amount_original': fields.function(_compute_balance, multi='dc', type='float', string='Original Amount', store=True, digits_compute=dp.get_precision('Account')),
        'amount_unreconciled': fields.function(_compute_balance, multi='dc', type='float', string='Open Balance', store=True, digits_compute=dp.get_precision('Account')),
    }

    _defaults = {
        # 'analytic_1':_get_analytic_company,
        # 'analytic_2':_get_analytic_2,
    }

    _sql_constraints = [
        ('unique_journal_item', 'unique(voucher_id,move_line_id)', 'Tidak boleh ada journal item yg sama didalam satu voucher !'),
    ]
        
    def name_payable_onchange(self,cr,uid,ids,account_id,branch_id,division,context=None):
        if not branch_id or not division:
            raise except_orm(_('No Branch Defined!'), _('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        dom2={}
        vals={}
        edi_doc_list2 = ['&', ('active','=',True), ('type','=','payable')]
        dict=self.pool.get('dym.account.filter').get_domain_account(cr,uid,ids,'other_payable',context=None)
        edi_doc_list2.extend(dict)      
        dom2['account_id'] = edi_doc_list2
        account_ids = self.pool.get('account.account').search(cr, uid, edi_doc_list2)
        if account_id and account_id not in account_ids:
            vals['account_id'] = False

        if account_id:
            account = self.pool.get('account.account').browse(cr, uid, [account_id])
            vals['name'] = account.name
            aa2_ids = self.pool.get('analytic.account.filter').get_analytics_2(cr, uid, ids, branch_id, division, account_id)
            dom2['analytic_2'] = [('id','in',[a2.id for a2 in aa2_ids])]
            if aa2_ids:
                vals['analytic_2'] = aa2_ids[0]


            # aa3_ids = self.pool.get('analytic.account.filter').get_analytics_3(cr, uid, ids, branch_id, division, account_id, self.analytic_2.code, self.analytic_2.id)
            # dom['analytic_3'] = [('id','in',[a3.id for a3 in aa3_ids])]
            # self.analytic_3 = aa3_ids[0]


        # if division != 'Sparepart':
        #     category = 'Unit'
        #     if division != 'Unit':
        #         category = 'Umum'
        #     branch_obj =  self.pool.get('dym.branch').browse(cr, uid, branch_id)
        #     analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_obj, category, False, 4, 'General')
        #     vals['analytic_1'] = analytic_1
        #     vals['analytic_2'] = analytic_2
        #     vals['analytic_3'] = analytic_3
        #     vals['account_analytic_id'] = analytic_4
        return {'domain':dom2,'value':vals}

    # def onchange_analytic_3(self,cr,uid,ids,account_id,branch_id,division,context=None):
    #     dom = {}
    #     if self.analytic_2 and self.analytic_3:
    #         branch_id = self._context.get('branch_id',[])
    #         division = self._context.get('division',False)
    #         aa4_ids = self.env['analytic.account.filter'].get_analytics_4(branch_id, division, self.account_id.id, self.analytic_2.code, self.analytic_2.id, self.analytic_3.id)
    #         if aa4_ids:
    #             dom['analytic_4'] = [('id','in',[a2.id for a2 in aa4_ids])]
    #             self.analytic_4 = aa4_ids[0]
    #     return {'domain':dom}

    def name_onchange(self,cr,uid,ids,name,branch_id,division,account_id,context=None):
        if not branch_id or not division:
            raise except_orm(_('No Branch Defined!'), _('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        dom={}
        val={}
        return {'domain':dom,'value':val}

    def account_id_onchange(self,cr,uid,ids,account_id,branch_id,division,context=None):
        if not branch_id or not division:
            raise except_orm(_('No Branch Defined!'), _('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        dom2={}
        vals={}
        edi_doc_list2 = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.pool.get('dym.account.filter').get_domain_account(cr,uid,ids,'other_receivable_detail',context=context)
        edi_doc_list2.extend(dict)      
        dom2['account_id'] = edi_doc_list2
        account_ids = self.pool.get('account.account').search(cr, uid, edi_doc_list2)
        if account_id and account_id not in account_ids:
            vals['account_id'] = False
        return {'domain':dom2,'value':vals}  

    def onchange_account_pr(self, cr, uid, ids, payment_request_type, branch_id, branch_dest_id, division_dst, account_id, division, context=None):
        value = {}
        dom = {}

        aa_obj = self.pool.get('account.analytic.account')
        user_obj = self.pool.get('res.users')         
        user = user_obj.browse(cr,uid,uid)

        branch_config_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
        if not branch_config_id:
            raise osv.except_osv(
                _('Perhatian'),
                _('Config Branch, silahkan setting dulu.'))
        branch_config = self.pool.get('dym.branch.config').browse(cr,uid,branch_config_id[0])
        if payment_request_type == 'prepaid':
            if not(branch_config.journal_register_prepaid and branch_config.journal_register_prepaid.default_debit_account_id):
                raise osv.except_osv(
                    _('Perhatian'),
                    _('Jurnal register prepaid cabang belum lengkap, silahkan setting dulu.'))
            debit_account = branch_config.journal_register_prepaid.default_debit_account_id.id
            value['account_id'] = debit_account
        elif payment_request_type == 'cip':
            if not(branch_config.journal_register_asset and branch_config.journal_register_asset.default_debit_account_id):
                raise osv.except_osv(
                    _('Perhatian'),
                    _('Jurnal register asset cabang belum lengkap, silahkan setting dulu.'))
            debit_account = branch_config.journal_register_asset.default_debit_account_id.id
            value['account_id'] = debit_account

        if branch_id:
            branch_src =  self.pool.get('dym.branch').browse(cr, uid, branch_id)
            if user.branch_type!='HO':
                dom['branch_dest_id'] = [('id','=',branch_id)]
                dom['division_dest_id'] = [('id','=',['Unit','Sparepart'])]
                value['branch_dest_id'] = branch_id
                value['division_dest_id'] = division_dst
            else:
                branch_ids = [b.id for b in user.branch_ids if b.company_id.id==branch_src.company_id.id]
                dom['branch_dest_id'] = [('id','in',branch_ids)]

            if branch_dest_id:
                if division_dst:
                    edi_doc_list = ['&', ('active','=',True), ('type','!=','view')]
                    accts = self.pool.get('analytic.account.filter').get_accounts(cr, uid, ids, branch_dest_id, division_dst, context=context)
                    dom['account_id'] = [('id','in',accts)]
                    if context.get('account_filter'):
                        dict = self.pool.get('dym.account.filter').get_domain_account(cr,uid,ids,context.get('account_filter'),context=None)
                        edi_doc_list.extend(dict)
                        if dict:
                            account_ids = self.pool.get('account.account').search(cr, uid, edi_doc_list)
                            dom['account_id'] = [('id','in',account_ids)]
                    if account_id:
                        analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_dest_id, division_dst, False, 4, 'General')
                        aa1_ids, aa2_ids, aa3_ids, aa4_ids, df1, df2, df3, df4, aa_dict = self.pool.get('analytic.account.filter').get_analytics(cr, uid, ids, branch_dest_id, division_dst, account_id, context=context)
                        if not all([df1,df2,df3,df4]):
                            account =  self.pool.get('account.account').browse(cr, uid, account_id)
                            return {
                                'value': {
                                    'account_id': False,
                                    'analytic_2': False,
                                    'analytic_3': False,
                                    'account_analytic_id': False,
                                }
                            }
                        value['analytic_2'] = analytic_2
                        value['analytic_3'] = analytic_3
                        value['account_analytic_id'] = False
                        dom = {
                            'analytic_1': [('id','in',aa1_ids)],
                            'analytic_2': [('id','in',aa2_ids)],
                            'analytic_3': [('id','in',aa3_ids)],
                            'account_analytic_id': [('id','in',aa4_ids)],
                        }
        return {'value':value,'domain':dom}

    def onchange_analytic(self, cr, uid, ids, branch_id, division, account_id, aa1, aa2, aa3, aa4, context=None):
        dom = {}

        # this = self.browse(cr, uid, ids, context=context)
        # aa1_ids, aa2_ids, aa3_ids, aa4_ids, df1, df2, df3, df4 = self.pool.get('analytic.account.filter').get_analytics(cr, uid, ids, branch_id, division, account_id, context=context)
        # aa_obj = self.pool.get('account.analytic.account')
        # if branch_id and aa2:
        #     level_3_ids = aa_obj.search(cr, uid, [('segmen','=',3),('branch_id','=',branch_id),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',aa2)])
        #     level_4_ids = aa_obj.search(cr, uid, [('segmen','=',4),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',level_3_ids)])
        #     dom['analytic_3'] = [('id','in',level_3_ids)]
        #     if aa4_ids:
        #         dom['account_analytic_id'] = [('id','in',[a for a in level_4_ids if a in aa4_ids])]
        #     else:
        #         dom['account_analytic_id'] = [('id','in',level_4_ids)]
        return {'domain':dom}

    def onchange_move_line_id(self, cr, user, ids, move_line_id, amount, currency_id, journal, partner_id=False, division=False, inter_branch_id=False, due_date_payment=False, supplier_payment=False, customer_payment=False, kwitansi=False, bawah=False, context=None):
        res = super(dym_account_voucher_line, self).onchange_move_line_id(cr, user, ids, move_line_id, context=context)
        move_line_pool = self.pool.get('account.move.line')
        currency_pool = self.pool.get('res.currency')
        account_journal = self.pool.get('account.journal')
        purchase_order = self.pool.get('purchase.order')
        stock_picking = self.pool.get('stock.picking')
        serial_number = self.pool.get('stock.production.lot')
        Warning = {}
        if move_line_id :
            remaining_amount = amount
            journal_brw = account_journal.browse(cr,user,journal)
            currency_id = currency_id or journal_brw.company_id.currency_id.id
            company_currency = journal_brw.company_id.currency_id.id
            move_line_brw = move_line_pool.browse(cr,user,move_line_id)
            if move_line_brw.settlement_id:
                Warning = {
                    'title': ('Perhatian !'),
                    'message': ("Settlement untuk advance payment %s sudah dibuat dengan nomor %s!")%(move_line_brw.avp_id.name, move_line_brw.settlement_id.name),
                }
                res['warning'] = Warning
                res['value'] = {}
                res['value']['move_line_id'] = False
                return res
            if move_line_brw.currency_id and currency_id == move_line_brw.currency_id.id:
                amount_original = abs(move_line_brw.amount_currency)
                amount_unreconciled = abs(move_line_brw.fake_balance)
            else:
                #always use the amount booked in the company currency as the basis of the conversion into the voucher currency
                amount_original = currency_pool.compute(cr, user, company_currency, currency_id, move_line_brw.credit or move_line_brw.debit or 0.0, context=context)
                amount_unreconciled = currency_pool.compute(cr, user, company_currency, currency_id, abs(move_line_brw.fake_balance), context=context)

            res['value'].update({
                'name':move_line_brw.move_id.name,
                'move_line_id':move_line_brw.id,                
                'amount_original': amount_original,
                'amount': move_line_id and min(abs(remaining_amount), amount_unreconciled) or 0.0,
                'date_original':move_line_brw.date,
                'date_due':move_line_brw.date_maturity,
                'amount_unreconciled': amount_unreconciled,
            })
            
            if move_line_brw.invoice.type == 'in_invoice' and move_line_brw.invoice.tipe == 'purchase' and not move_line_brw.invoice.consolidated :
                if all(line.quantity == line.consolidated_qty or line.product_id.type == 'service' for line in move_line_brw.invoice.invoice_line):
                    move_line_brw.invoice.write({'consolidated': True})
                else:
                    Warning = {
                        'title': ('Perhatian !'),
                        'message': ("Penerimaan atas Invoice '%s' belum lengkap, mohon lakukan consolidate invoice !")%(move_line_brw.invoice.number),
                    }
                    res['warning'] = Warning
                    res['value'] = {}
                    res['value']['move_line_id'] = False
            if move_line_brw.invoice.origin:
                if move_line_brw.invoice.type == 'in_invoice' and move_line_brw.invoice.tipe == False and len(move_line_brw.invoice.origin) > 4 and (move_line_brw.invoice.origin[:4] == 'PRBJ' or move_line_brw.invoice.origin[:3] == 'TBJ'):
                    obj_pr_birojasa = self.pool.get('dym.proses.birojasa')
                    obj_tr_stnk_line = self.pool.get('dym.penerimaan.stnk.line')
                    pr_birojasa_ids = obj_pr_birojasa.search(cr, user, [('name','=',move_line_brw.invoice.origin.split(' ') or ''),('type','=','reg')], limit=1)
                    if pr_birojasa_ids:
                        pr_birojasa = obj_pr_birojasa.browse(cr, user, pr_birojasa_ids)
                        for line in pr_birojasa.proses_birojasa_line:
                            if not line.name.penerimaan_notice_id.id or not line.name.tgl_terima_notice:
                                Warning = {
                                    'title': ('Perhatian !'),
                                    'message': ("Pembayaran tagihan birojasa %s tidak bisa diproses, karena notice belum diterima!")%(move_line_brw.invoice.origin),
                                }
                                res['warning'] = Warning
                                res['value'] = {}
                                res['value']['move_line_id'] = False

        if supplier_payment == True:
            if 'domain' not in res:
                res['domain'] = {}
            if bawah == False:
                move_line_domain = [('account_id.type','=','payable'),('credit','!=',0), ('reconcile_id','=', False), ('partner_id','=',partner_id),('division','=',division),'|',('date_maturity','<=',due_date_payment),('date_maturity','=',False),('dym_loan_id','=',False)]
            else:
                move_line_domain = [('account_id.type','=','receivable'),('debit','!=',0), ('reconcile_id','=', False),('partner_id','=',partner_id),('division','=',division),('dym_loan_id','=',False)]
            if inter_branch_id:
                move_line_domain += [('branch_id','=',inter_branch_id)]
            else:
                user_obj = self.pool.get('res.users').browse(cr, user, user)
                move_line_domain += [('branch_id','in',user_obj.area_id.branch_ids.ids)]
            move_line_search = self.pool.get('account.move.line').search(cr, user, move_line_domain)
            not_consolidated_line = []
            for move_line in self.pool.get('account.move.line').browse(cr, user, move_line_search):
                if move_line.invoice.type == 'in_invoice' and move_line.invoice.tipe == 'purchase' and not move_line.invoice.consolidated:
                    if all(line.quantity == line.consolidated_qty or line.product_id.type == 'service' or move_line.invoice.is_cip == True for line in move_line.invoice.invoice_line):
                        move_line.invoice.write({'consolidated': True})
                    else:
                        not_consolidated_line.append(move_line.id)
            if not_consolidated_line:
                move_line_domain += [('id','not in',not_consolidated_line)]
            res['domain']['move_line_id'] = move_line_domain
        if customer_payment == True:
            if 'domain' not in res:
                res['domain'] = {}
            if bawah == False:
                move_line_domain = [('kwitansi','=',kwitansi),('account_id.type','=','receivable'),('debit','!=',0), ('reconcile_id','=', False), ('partner_id','=',partner_id),('division','=',division),('dym_loan_id','=',False)]
            else:
                move_line_domain = [('account_id.type','=','payable'),('credit','!=',0), ('reconcile_id','=', False), ('partner_id','=',partner_id),('division','=',division),('dym_loan_id','=',False)]
                edi_doc_list = ['&', ('active','=',True), ('type','!=','view')]
                dicta = self.pool.get('dym.account.filter').get_domain_account(cr, user, ids,'exclude_customer_payment',context=None)
                edi_doc_list.extend(dicta)
                if dicta:
                    account_ids = self.pool.get('account.account').search(cr, user, edi_doc_list)
                    if account_ids:
                        move_line_domain += [('account_id','not in',account_ids)]
            if inter_branch_id:
                move_line_domain += [('branch_id','=',inter_branch_id)]
            else:
                user_obj = self.pool.get('res.users').browse(cr, user, user)
                move_line_domain += [('branch_id','in',user_obj.area_id.branch_ids.ids)]            
            res['domain']['move_line_id'] = move_line_domain
        if context == None:
            context = {}
        if 'line_ids' in context and context['line_ids'] and 'domain' in res and 'move_line_id' in res['domain'] and res['domain']['move_line_id']:
            voucher_line = self.pool.get('account.voucher').resolve_2many_commands(cr, user, 'line_ids', context['line_ids'], ['move_line_id'], context)
            line_ids = []
            for l in voucher_line:
                if isinstance(l, dict) and l['move_line_id'][0]:
                    line_ids += [l['move_line_id'][0]]
            if line_ids:
                res['domain']['move_line_id'] += [('id','not in',line_ids)]
        return res
        
class invoice(osv.osv):
    _inherit = 'account.invoice'
    
    def invoice_pay_customer(self, cr, uid, ids, context=None):
        if not ids: return []
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_dialog_form')
        inv = self.browse(cr, uid, ids[0], context=context)
        return {
            'name':("Pay Invoice"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'payment_expected_currency': inv.currency_id.id,
                'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(inv.partner_id).id,
                'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
                'branch_id': inv.branch_id.id,
                'division': inv.division,
                'close_after_process': True,
                'invoice_type': inv.type,
                'invoice_id': inv.id,
                'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
            }
        }
        
class dym_register_kwitansi_payments(osv.osv):
    _inherit = 'dym.register.kwitansi.line'   
    
    _columns = {
        'amount':fields.float('Amount')
    }
    
class dym_payments_request_type(osv.osv):
    _name = "dym.payments.request.type" 
    _description = 'Payment Request Type'
    
    _columns ={
        'name' : fields.text(string='Description'),
        'account_id': fields.many2one('account.account', string='Account'),
    } 
   
