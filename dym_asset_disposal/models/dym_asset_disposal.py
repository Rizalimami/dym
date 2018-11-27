import time
from datetime import datetime,timedelta
from openerp import workflow
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
from lxml import etree
from openerp.osv.orm import setup_modifiers

class dym_asset_disposal(osv.osv):
    _name = "dym.asset.disposal"
    _description = "Asset Disposal"
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('confirmed', 'Waiting Approval'),
        ('approved','Process Confirmed'),
        ('except_invoice', 'Invoice Exception'),
        ('done','Done'),
        ('cancel','Cancelled')
    ] 
      
    def dispose_change(self,cr,uid,ids,branch_id,birojasa_id,context=None):
        domain = {}
        value = {}
        if branch_id:
            branch = self.pool.get('dym.branch').browse(cr, uid, branch_id)
            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, 'Umum', False, 4, 'General')
            value['analytic_1'] = analytic_1_general
            value['analytic_2'] = analytic_2_general
            value['analytic_3'] = analytic_3_general
            value['analytic_4'] = analytic_4_general

        # birojasa = []
        # birojasa_srch = self.pool.get('dym.harga.birojasa').search(cr,uid,[
        #                                                               ('branch_id','=',branch_id)
        #                                                               ])
        # if birojasa_srch :
        #     birojasa_brw = self.pool.get('dym.harga.birojasa').browse(cr,uid,birojasa_srch)
        #     for x in birojasa_brw :
        #         birojasa.append(x.birojasa_id.id)
        # domain['partner_id'] = [('id','in',birojasa)]
        return {'domain':domain,'value':value}
    
    # def change_type(self,cr,uid,ids,type,context=None):
    #     value = {}
    #     if type == 'Cash':
    #         value['days_pay'] = 1
    #     else:
    #         value['days_pay'] = False
    #     return {'value':value}

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for asset in self.browse(cr, uid, ids, context=context):
            res[asset.id] = {
                'amount_untaxed': 0.0,
                'amount_net_price': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            amount_untaxed = amount_tax = amount_net_price = amount_total = amount_tax = 0.0
           
            for line in asset.asset_disposal_line:
                amount_untaxed += line.amount
            for tax_id in asset.taxes_ids:
                for c in self.pool.get('account.tax').compute_all(cr,uid, tax_id, (amount_untaxed-asset.discount),1)['taxes']:
                    amount_tax +=c.get('amount',0.0)
            res[asset.id]['amount_untaxed'] = amount_untaxed
            res[asset.id]['amount_net_price'] = amount_untaxed - asset.discount
            res[asset.id]['amount_tax'] = amount_tax
            res[asset.id]['amount_total'] = amount_untaxed - asset.discount + amount_tax
        return res
    
    def _get_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('dym.asset.disposal.line').browse(cr, uid, ids, context=context):
            result[line.dispose_id.id] = True
        return result.keys()

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    # def _get_date_due(self, cr, uid, ids, field_names, args, context=None):        
    #     res = {}
    #     for dispose in self.browse(cr, uid, ids, context=context):
    #         date_due = False
    #         res[dispose.id] = datetime.strptime(dispose.date,'%Y-%m-%d') + timedelta(days=dispose.days_pay)                
    #     return res

    def _get_analytic_company(self,cr,uid,context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_asset_disposal-2] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    _columns = {
        'branch_id': fields.many2one('dym.branch', string='Branch', required=True),
        'division':fields.selection([('Umum','General')], 'Division', change_default=True, select=True),
        'name': fields.char('Name', readonly=True),
        'date': fields.date('Transaction Date'),
        'state': fields.selection(STATE_SELECTION, 'State', readonly=True),
        'asset_disposal_line': fields.one2many('dym.asset.disposal.line','dispose_id',string="Table disposal asset"), 
        'partner_id':fields.many2one('res.partner','Partner'),
        'reference' : fields.char('Reference #'),
        'memo' : fields.char('Memo'),
        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'dym.asset.disposal': (lambda self, cr, uid, ids, c={}: ids, ['asset_disposal_line'], 10),
                'dym.asset.disposal.line': (_get_line, ['amount'], 10),
            },
            multi='sums', help="The amount without tax and discount.", track_visibility='always'),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'dym.asset.disposal': (lambda self, cr, uid, ids, c={}: ids, ['asset_disposal_line','discount','taxes_ids'], 10),
                'dym.asset.disposal.line': (_get_line, ['amount'], 10),
            },
            multi='sums', help="Grand Total."),
        'amount_net_price': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Net Price',
            store={
                'dym.asset.disposal': (lambda self, cr, uid, ids, c={}: ids, ['asset_disposal_line','discount'], 10),
                'dym.asset.disposal.line': (_get_line, ['amount'], 10),
            },
            multi='sums', help="The total amount without tax."),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tax Amount',
            store={
                'dym.asset.disposal': (lambda self, cr, uid, ids, c={}: ids, ['asset_disposal_line','taxes_ids', 'discount'], 10),
                'dym.asset.disposal.line': (_get_line, ['amount'], 10),
            },
            multi='sums', help="The tax amount."),
        'discount' : fields.float('Discount',digits_compute=dp.get_precision('Account')),
        'invoiced': fields.boolean('Invoiced', readonly=True, copy=False),
        'invoice_method': fields.selection([('order','Based on generated draft invoice')], 'Invoicing Control', required=True,
            readonly=True),
        'taxes_ids': fields.many2many('account.tax', 'dym_asset_disposal_tax_rel', 'dym_asset_disposal_id',
            'tax_id', 'Taxes'),
        'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
        'confirm_date':fields.datetime('Confirmed on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),  
        'payment_term':fields.many2one('account.payment.term',string="Payment Terms"),
        'pajak_gunggung':fields.boolean('Tanpa Faktur Pajak',copy=False),   
        'pajak_gabungan':fields.boolean('Faktur Pajak Gabungan',copy=False),   
        'faktur_pajak_id':fields.many2one('dym.faktur.pajak.out',string='No Faktur Pajak',copy=False),
        'is_pedagang_eceran': fields.related('branch_id', 'is_pedagang_eceran', relation='dym.branch',type='boolean',string='Pedagang Eceran',store=False),
        'analytic_1': fields.many2one('account.analytic.account','Account Analytic Company'),
        'analytic_2': fields.many2one('account.analytic.account','Account Analytic Bisnis Unit'),
        'analytic_3': fields.many2one('account.analytic.account','Account Analytic Branch'),
        'analytic_4': fields.many2one('account.analytic.account','Account Analytic Cost Center'),
    }
    _defaults = {
      'analytic_1':_get_analytic_company,
      'date': fields.date.context_today,
      # 'type':'reg',
      'state':'draft',
      'division' : 'Umum',
      'invoice_method':'order',
      'invoiced': 0,
      'branch_id': _get_default_branch,
     }

    def onchange_gabungan_gunggung(self,cr,uid,ids,gabungan_gunggung,pajak_gabungan,pajak_gunggung,context=None):
        value = {}
        if gabungan_gunggung == 'pajak_gabungan' and pajak_gabungan == True:
            value['pajak_gunggung'] = False
        if gabungan_gunggung == 'pajak_gunggung' and pajak_gunggung == True:
            value['pajak_gabungan'] = False
        return {'value':value}

    def create_child_ids(self, cr, uid, dispose_id, child_ids, context=None):
        dispose = self.browse(cr, uid, dispose_id)
        for asset in child_ids:
            if asset.branch_id.id == dispose.branch_id.id and not asset.dispose_asset_id and asset.state not in ('sold','scrap') and asset.categ_type == 'fixed':
                description = ''
                if asset.product_id.id:
                    description = asset.product_id.name_get().pop()[1]
                vals = {
                     'dispose_id':dispose_id,
                     'asset_id':asset.id,
                     'description':description,
                     'amount':0,
                }
                self.pool.get('dym.asset.disposal.line').create(cr, uid, vals)
            self.create_child_ids(cr, uid, dispose_id, asset.child_ids)
        return True

    def create(self, cr, uid, vals, context=None):
        if not vals['asset_disposal_line']:
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail Asset Disposal. Data tidak bisa di save."))
        dispose_asset = []
        for x in vals['asset_disposal_line']:
            dispose_asset.append(x.pop(2))
        asset_pool = self.pool.get('account.asset.asset')
        proses_pool = self.pool.get('dym.asset.disposal.line')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'ADI', division='Umum')
        vals['date'] = time.strftime('%Y-%m-%d'),
        del[vals['asset_disposal_line']]
        proses_id = super(dym_asset_disposal, self).create(cr, uid, vals, context=context) 

        if proses_id :         
            for x in dispose_asset:
                asset_search = asset_pool.search(cr,uid,[
                            ('id','=',x['asset_id'])
                            ])
                asset_browse = asset_pool.browse(cr,uid,asset_search)
                asset_browse.write({
                       'dispose_asset_id':proses_id,
                       })
                proses_pool.create(cr, uid, {
                                     'dispose_id':proses_id,
                                     'responsible_id':x['responsible_id'],
                                     'asset_id':asset_browse.id,
                                     'description':x['description'],
                                     'amount':x['amount'],
                                    })
                update_vals = {'dispose_asset_id':proses_id}
                # asset_pool.update_asset(cr, uid, asset_browse.child_ids, update_vals, context=context)
                self.create_child_ids(cr, uid, proses_id, asset_browse.child_ids)
        return proses_id
    
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Asset Disposal sudah di post ! tidak bisa didelete !"))

        asset_pool = self.pool.get('account.asset.asset')
        asset_search = asset_pool.search(cr,uid,[
                                           ('dispose_asset_id','in',ids)
                                           ])
        asset_browse = asset_pool.browse(cr,uid,asset_search)
        for x in asset_browse:
            x.write({
                     'tgl_asset_disposal': False,
                     })
            update_vals = {'tgl_asset_disposal': False,}
            # asset_pool.update_asset(cr, uid, asset_browse.child_ids, update_vals, context=context)
        return super(dym_asset_disposal, self).unlink(cr, uid, ids, context=context)
    
    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def wkf_confirm_dispose(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)
        asset_pool = self.pool.get('account.asset.asset')
        date = datetime.today()
        self.write(cr, uid, ids, {'state': 'approved','confirm_uid':uid,'confirm_date':datetime.now()})
        for x in val.asset_disposal_line :
            asset_search = asset_pool.search(cr,uid,[
                ('id','=',x.asset_id.id)
                ])
            asset_browse = asset_pool.browse(cr,uid,asset_search)
            asset_browse.write({
                   'tgl_asset_disposal':val.date,
                   })
            update_vals = {'tgl_asset_disposal': val.date,}
            # asset_pool.update_asset(cr, uid, asset_browse.child_ids, update_vals, context=context)
        return True
   
    def wkf_action_cancel(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)  
        asset_pool = self.pool.get('account.asset.asset')
        for x in val.asset_disposal_line :
            asset_search = asset_pool.search(cr,uid,[
                        ('id','=',x.asset_id.id)
                        ])
            if not asset_search :
                raise osv.except_osv(('Perhatian !'), ("Asset Tidak Ditemukan."))
            if asset_search :
                asset_browse = asset_pool.browse(cr,uid,asset_search)
                asset_browse.write({
                                  'dispose_asset_id': False,
                                  'tgl_asset_disposal':False,
                                })
                update_vals = {'dispose_asset_id': False,'tgl_asset_disposal':False,}
                # asset_pool.update_asset(cr, uid, asset_browse.child_ids, update_vals, context=context)
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        return True

    def wkf_approve_order(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'approved'})
        return True
    
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        vals.get('asset_disposal_line',[]).sort(reverse=True)

        collect = self.browse(cr,uid,ids)
        asset_pool = self.pool.get('account.asset.asset')
        line_pool = self.pool.get('dym.asset.disposal.line')
        asset = vals.get('asset_disposal_line', False)
        if asset :
            for x,item in enumerate(asset) :
                line_id = item[1]
                if item[0] == 2 :    
                    line_search = line_pool.search(cr,uid,[
                                                           ('id','=',line_id)
                                                           ])
                    line_browse = line_pool.browse(cr,uid,line_search)
                    asset_search = asset_pool.search(cr,uid,[
                                           ('id','=',line_browse.asset_id.id)
                                           ])
                    if not line_search :
                        raise osv.except_osv(('Perhatian !'), ("Asset tidak ada didalam disposal line"))
                    if not asset_search :
                        raise osv.except_osv(('Perhatian !'), ("Asset tidak ada di dalam daftar asset"))
                    asset_browse = asset_pool.browse(cr,uid,asset_search)
                    asset_browse.write({
                                  'dispose_asset_id': False,
                                  'tgl_asset_disposal':False,
                                     })
                    update_vals = {'dispose_asset_id': False,'tgl_asset_disposal':False,}
                    # asset_pool.update_asset(cr, uid, asset_browse.child_ids, update_vals, context=context)
                elif item[0] == 0 :
                    values = item[2]
                    asset_search = asset_pool.search(cr,uid,[
                                                        ('id','=',values['asset_id'])
                                                        ])
                    if not asset_search :
                        raise osv.except_osv(('Perhatian !'), ("Asset tidak ada di dalam daftar asset"))
                    
                    asset_browse = asset_pool.browse(cr,uid,asset_search)
                    asset_browse.write({
                           'dispose_asset_id':collect.id,
                           })
                    update_vals = {'dispose_asset_id': collect.id,}
                    # asset_pool.update_asset(cr, uid, asset_browse.child_ids, update_vals, context=context)
                    self.create_child_ids(cr, uid, collect.id, asset_browse.child_ids)

                elif item[0] == 1 :
                    values = item[2]
                    if 'asset_id' in values:
                        asset_before_id = line_pool.browse(cr, uid, [item[1]]).asset_id
                        asset_before_id.write({
                                              'dispose_asset_id': False,
                                              'tgl_asset_disposal':False,
                                           })
                        update_vals = {'dispose_asset_id': False,'tgl_asset_disposal':False,}
                        # asset_pool.update_asset(cr, uid, asset_before_id.child_ids, update_vals, context=context)

                        asset_search = asset_pool.search(cr,uid,[
                                                            ('id','=',values['asset_id'])
                                                            ])
                        if not asset_search :
                            raise osv.except_osv(('Perhatian !'), ("Asset tidak ada di dalam daftar asset"))
                        
                        asset_browse = asset_pool.browse(cr,uid,asset_search)
                        asset_browse.write({
                               'dispose_asset_id':collect.id,
                               })
                        update_vals = {'dispose_asset_id': collect.id,}
                        # asset_pool.update_asset(cr, uid, asset_browse.child_ids, update_vals, context=context)
                        self.create_child_ids(cr, uid, collect.id, asset_browse.child_ids)
        return super(dym_asset_disposal, self).write(cr, uid, ids, vals, context=context)
    
    def wkf_set_to_draft(self,cr,uid,ids):
        return self.write({'state':'draft'})       
     
    def action_invoice_create(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        asset_obj = self.pool.get('account.asset.asset')
        obj_inv = self.pool.get('account.invoice')
        invoice_line = []
        move_line_obj = self.pool.get('account.move.line')
        #ACCOUNT 
        config = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',val.branch_id.id)])
        config_browse = self.pool.get('dym.branch.config').browse(cr,uid,config)
        if config :
            disposal_debit_account_id = config_browse.asset_disposal_journal_id.default_debit_account_id.id 
            disposal_credit_account_id = config_browse.asset_disposal_journal_id.default_credit_account_id.id  
            journal_asset_disposal = config_browse.asset_disposal_journal_id.id
            if not journal_asset_disposal or not disposal_debit_account_id or not disposal_credit_account_id:
                raise osv.except_osv(_('Attention!'),
                    _('Jurnal Asset Disposal belum diisi, harap isi terlebih dahulu didalam branch config'))   
                             
        elif not config :
            raise osv.except_osv(_('Error!'),
                _('Please define Journal in Setup Division for this branch: "%s".') % \
                (val.branch_id.name))
                              
        if val.amount_total < 1: 
            raise osv.except_osv(_('Attention!'),
                _('Mohon periksa kembali detail asset disposal.')) 
        for x in val.asset_disposal_line:
            if not x.asset_id.analytic_4.id:
                raise osv.except_osv(_('Attention!'),
                    _('data analytic untuk asset %s belum lengkap') % \
                    (x.asset_id.name))
            # analytic_1 = self.search(cr, uid, [('segmen','=',1),('company_id','=',x.asset_id.analytic_2.branch_id.company_id.id),('type','=','normal'),('state','not in',('close','cancelled'))])
            # if not analytic_1:
                # raise osv.except_osv(_('Attention!'),
                    # _('data analytic company untuk branch %s belum lengkap') % \
                    # (x.asset_id.analytic_2.branch_id.name))
            if not x.asset_id.account_depreciation_id or not x.asset_id.account_asset_id:
                raise osv.except_osv(_('Attention!'),
                    _('Data Account di kategori asset %s belum lengkap')%(x.asset_id.category_id.name))   
            invoice_line.append([0,False,{
                    'account_id':x.asset_id.account_depreciation_id.id,
                    'partner_id':val.partner_id.id,
                    # 'name': 'Asset Disposal [' + x.asset_id.code + '] ' + x.asset_id.name,
                    'name': 'Accumulated Depreciation ' + x.asset_id.name,
                    'quantity': 1,
                    'origin': val.name,
                    'price_unit':(x.depreciated*-1) or 0.00,
                    # 'analytic_1': analytic_1,
                    'analytic_2': x.asset_id.analytic_2.id,
                    'analytic_3': x.asset_id.analytic_3.id,
                    'account_analytic_id':x.asset_id.analytic_4.id,
                }])
            invoice_line.append([0,False,{
                    'account_id':x.asset_id.account_asset_id.id,
                    'partner_id':val.partner_id.id,
                    # 'name': 'Asset Disposal [' + x.asset_id.code + '] ' + x.asset_id.name,
                    'name': 'Cost ' + x.asset_id.name,
                    'quantity': 1,
                    'origin': val.name,
                    'price_unit':x.purchase_value  or 0.00,
                    # 'analytic_1': analytic_1,
                    'analytic_2': x.asset_id.analytic_2.id,
                    'analytic_3': x.asset_id.analytic_3.id,
                    'account_analytic_id':x.asset_id.analytic_4.id,
                }])
            invoice_line.append([0,False,{
                    'account_id':disposal_credit_account_id,
                    'partner_id':val.partner_id.id,
                    # 'name': 'Asset Disposal [' + x.asset_id.code + '] ' + x.asset_id.name,
                    'name': 'Laba / Rugi ' + x.asset_id.name,
                    'quantity': 1,
                    'origin': val.name,
                    'price_unit':x.gain_loss  or 0.00,
                    # 'analytic_1': analytic_1,
                    'analytic_2': x.asset_id.analytic_2.id,
                    'analytic_3': x.asset_id.analytic_3.id,
                    'account_analytic_id':x.asset_id.analytic_4.id,
                }])
        tax_line =[]
        for tax_id in val.taxes_ids:
            amount_tax = float(0)
            for c in self.pool.get('account.tax').compute_all(cr,uid, tax_id, (val.amount_untaxed-val.discount),1)['taxes']:
                amount_tax +=c.get('amount',0.0)
            tax_line.append([0,False,{
                    'name':tax_id.name,
                    'account_id':tax_id.account_collected_id.id,
                    'base':(val.amount_untaxed-val.discount),               
                    'amount':amount_tax,               
                }])
        # pdb.set_trace()
        if val.discount != 0:
            invoice_line.append([0,False,{
                    'account_id':disposal_credit_account_id,
                    'partner_id':val.partner_id.id,
                    # 'name': 'Asset Disposal [' + x.asset_id.code + '] ' + x.asset_id.name,
                    'name': 'Diskon ' + val.name,
                    'quantity': 1,
                    'origin': val.name,
                    'price_unit': (val.discount*-1) or 0.00,
                    # 'analytic_1': analytic_1,
                    'analytic_2': x.asset_id.analytic_2.id,
                    'analytic_3': x.asset_id.analytic_3.id,
                    'account_analytic_id':x.asset_id.analytic_4.id,
                }])
        inv_dispose_asset_id = obj_inv.create(cr,uid, {
                                    'name':val.name,
                                    'origin': val.name,
                                    'branch_id':val.branch_id.id,
                                    'division':val.division,
                                    'partner_id':val.partner_id.id,
                                    'date_invoice':val.date,
                                    'reference_type':'none',
                                    'account_id':disposal_debit_account_id,
                                    'comment':val.memo,
                                    'type': 'out_invoice',
                                    'journal_id' : journal_asset_disposal,
                                    'discount_lain' : val.discount,                        
                                    'tipe': 'customer',                
                                    'payment_term': val.payment_term.id,
                                    'tax_line':tax_line,
                                    'invoice_line':invoice_line,
                                    'analytic_1': val.analytic_1.id,
                                    'analytic_2': val.analytic_2.id,
                                    'analytic_3': val.analytic_3.id,
                                    'analytic_4': val.analytic_4.id,
                                })   
        obj_line = self.pool.get('account.invoice.line') 
        for dispose_line in val.asset_disposal_line :
            asset_obj.write(cr,uid,[dispose_line.asset_id.id],{'inv_dispose_asset':inv_dispose_asset_id})
            update_vals = {'inv_dispose_asset':inv_dispose_asset_id,}
            # asset_obj.update_asset(cr, uid, dispose_line.asset_id.child_ids, update_vals, context=context)
        obj_inv.signal_workflow(cr, uid, [inv_dispose_asset_id], 'invoice_open' )
        if val.amount_tax and not val.pajak_gabungan and not val.pajak_gunggung :
            self.pool.get('dym.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'dym.asset.disposal',context=context)   
        if val.amount_tax and val.pajak_gunggung == True :   
            self.pool.get('dym.faktur.pajak.out').create_pajak_gunggung(cr,uid,ids,'dym.asset.disposal',context=context)  
        return inv_dispose_asset_id 
        
    def invoice_done(self, cr, uid, ids, context=None):
        asset_obj = self.pool.get('account.asset.asset')
        for dispose in self.pool.get('dym.asset.disposal').browse(cr,uid,ids):
            if dispose.invoiced == False:
                dispose.write({'invoiced':True})
                if dispose.asset_receive == True:
                    self.write(cr, uid, [dispose.id], {'state': 'done'}, context=context)
                    for x in dispose.asset_disposal_line:
                        date = datetime.now()
                        if dispose.amount_total > 0:
                            x.asset_id.write({'tgl_bayar_disposal':date,'state':'sold'})
                            update_vals = {'tgl_bayar_disposal':date,'state':'sold'}
                        else:
                            x.asset_id.write({'state':'scrap'})
                            update_vals = {'state':'scrap'}
                        # asset_obj.update_asset(cr, uid, x.asset_id.child_ids, update_vals, context=context)
                else:
                    self.write(cr, uid, [dispose.id], {'state': 'approved'}, context=context)
                    for x in dispose.asset_disposal_line:
                        date = datetime.now()
                        if dispose.amount_total > 0:
                            x.asset_id.write({'tgl_bayar_disposal':date})
                            update_vals = {'tgl_bayar_disposal':date}
                            # asset_obj.update_asset(cr, uid, x.asset_id.child_ids, update_vals, context=context)
        return True
    
    def view_invoice(self,cr,uid,ids,context=None):  

        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        result['views'] = [(res and res[1] or False, 'form')]
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        obj = obj_inv.search(cr,uid,[('origin','ilike',val.name),
                                     ('type','=','out_invoice')
                                    ])
        result['res_id'] = obj[0] 
        return result

class dym_asset_disposal_line(osv.osv):
    _name = "dym.asset.disposal.line"

    def get_child_nbv(self, cr, uid, child_ids, nbv, context=None):
        for asset in child_ids:
            nbv += asset.salvage_value + asset.real_value_residual
            nbv += self.get_child_nbv(cr, uid, asset.child_ids, 0)
        return nbv

    def _amount_nbv(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            nbv = 0
            # nbv += self.get_child_nbv(cr, uid, line.asset_id.child_ids, nbv)
            res[line.id] = line.asset_id.salvage_value + line.asset_id.real_value_residual + nbv
        return res

    def _amount_depreciated(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id]= line.purchase_value - line.nbv
        return res

    def _amount_purchase_value(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id]= line.asset_id.real_purchase_value
        return res

    def _amount_gain_loss(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id]= line.amount - line.nbv
        return res

    _columns = {
                'dispose_id' : fields.many2one('dym.asset.disposal','Asset Disposal'),
                'responsible_id':fields.many2one('hr.employee','Responsible of'),
                'asset_id' : fields.many2one('account.asset.asset','Asset',domain="[('dispose_asset_id','=',False),('analytic_3.branch_id','=',parent.branch_id),('state','not in',['sold','scrap']),('categ_type','=','fixed'),('parent_id','=',False)]",change_default=True,),
                'description': fields.text('Description'),
                'amount' : fields.float('Amount',digits_compute=dp.get_precision('Account')),
                'nbv': fields.function(_amount_nbv, string='NBV', digits_compute=dp.get_precision('Account')),
                'depreciated': fields.function(_amount_depreciated, string='Depreciated', digits_compute=dp.get_precision('Account')),
                'purchase_value': fields.function(_amount_purchase_value, string='Cost', digits_compute=dp.get_precision('Account')),
                'gain_loss': fields.function(_amount_gain_loss, string='Gain (Loss)', digits_compute=dp.get_precision('Account')),
                'delivered' : fields.boolean('Delivered'),
                }

    _sql_constraints = [
    ('unique_asset_id_disposal_id', 'unique(asset_id,dispose_id)', 'Detail Asset duplicate, mohon cek kembali !'),
]    
                    
    def onchange_asset(self, cr, uid, ids, asset_id, branch_id, responsible_id):
        if not branch_id:
            raise osv.except_osv(('No Branch Defined!'), ('Sebelum menambah detil transaksi,\n harap isi branch dan partner terlebih dahulu.'))
        value = {}
        domain = {}
        warning = {}
        domain_search = [('analytic_3.branch_id', '=', branch_id),('dispose_asset_id','=',False),('state','not in',['sold','scrap']),('categ_type','=','fixed')]
        if responsible_id:
            domain_search += [('responsible_id', '=', responsible_id)]
        asset_ids = self.pool.get('account.asset.asset').search(cr, uid, domain_search)
        domain['asset_id'] = [('id','in',asset_ids)]
        if asset_id:
            obj_asset = self.pool.get('account.asset.asset').browse(cr, uid, [asset_id])
            if obj_asset.product_id.id:
                value['description'] = obj_asset.product_id.name_get().pop()[1]
            value['nbv'] = obj_asset.salvage_value + obj_asset.value_residual
            nbv = 0
            # nbv += self.get_child_nbv(cr, uid, obj_asset.child_ids, nbv)
            value['nbv'] = obj_asset.salvage_value + obj_asset.real_value_residual + nbv
            purchase_value = obj_asset.real_purchase_value
            value['purchase_value'] = purchase_value
            depreciated = purchase_value - (obj_asset.salvage_value + obj_asset.real_value_residual + nbv)
            value['depreciated'] = depreciated
            obj_dispose_line = self.search(cr, uid, [('dispose_id.state','not in',('draft','cancel')),('asset_id','=',asset_id)])
            if obj_dispose_line:
                warning = {'title':'Perhatian !','message':'Asset ' + obj_asset.name + ' sedang di proses oleh ' + self.browse(cr, uid, obj_dispose_line[0]).dispose_id.name}
                value['asset_id'] = False
                value['description'] = False
                value['amount'] = False
                value['nbv'] = False
                value['depreciated'] = False
                value['purchase_value'] = False
                value['gain_loss'] = False
        return  {'value':value, 'domain':domain, 'warning':warning}
