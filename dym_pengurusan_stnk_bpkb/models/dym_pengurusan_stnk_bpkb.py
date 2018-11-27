import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from string import whitespace
from openerp.tools.translate import _

class dym_pengurusan_stnk_bpkb(models.Model):
    _name = "dym.pengurusan.stnk.bpkb"
    _description ="Pengurusan STNK BPKB"

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    @api.depends('pengurusan_line.name')
    def _amount_all(self):
        for ib in self:
            amount_total = 0.0
            for line in ib.pengurusan_line:
                ib.update({
                    'total_record': len(ib.pengurusan_line),
                })
        
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, default=_get_default_branch)
    division=fields.Selection([('Unit','Showroom')], 'Division', change_default=True, default='Unit',select=True)
    name= fields.Char('No Reference', readonly=True)
    state= fields.Selection([('draft', 'Draft'), ('approved', 'Approved'),('except_invoice', 'Invoice Exception'),('confirm','Confirmed'),('cancel','Canceled'),('done','Done')], 'State', readonly=True,default='draft')
    pengurusan_line= fields.One2many('dym.pengurusan.stnk.bpkb.line','pengurusan_id',string="Table Penerimaan STNk")
    partner_id=fields.Many2one('res.partner','Biro Jasa',domain=[('biro_jasa','=',True)])
    tgl_pengurusan = fields.Date('Tanggal',default=fields.Date.context_today)
    customer_id = fields.Many2one('res.partner','Customer',domain=[('customer','=',True)])
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    total_record = fields.Integer(string='Total Engine', store=True, readonly=True, compute='_amount_all')
        
    @api.multi  
    def cancel_pengurusan(self):
        lot_pool = self.env['stock.production.lot'] 
        for x in self.pengurusan_line :
            lot_browse = lot_pool.search([
                        ('branch_id','=',self.branch_id.id),
                        ('id','=',x.name.id),
                        ])
            if not lot_browse :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_browse :
                if lot_browse.proses_stnk_id or lot_browse.penerimaan_notice_id or lot_browse.penerimaan_stnk_id or lot_browse.penerimaan_bpkb_id or lot_browse.proses_biro_jasa_id :
                    raise osv.except_osv(('Perhatian !'), ("No engine \'%s\' telah diproses, data tidak bisa di cancel !")%(lot_browse.name))                    
                else :                
                    lot_browse.write({
                                      'pengurusan_stnk_bpkb_id':False,
                                      'state_stnk':'terima_faktur',
                                      'biro_jasa_id':False,
                                      'tgl_pengurusan_stnk_bpkb' : False,
                                      'plat' : False
                                      }
                                     )
                     
                    if lot_browse.state == 'sold' :
                        lot_browse.write({'state':'sold_offtr'})
                    if lot_browse.state == 'paid' :
                        lot_browse.write({'state':'paid_offtr'})
         
        self.cek_invoice_state(self.name)                
        self.write({'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})                  
        return True
    
    @api.cr_uid_ids_context
    def cek_invoice_state(self,cr,uid,ids,name,context=None):
        obj_inv = self.pool.get('account.invoice')
        invoice = obj_inv.search(cr,uid,[('origin','ilike',name)])    
        invoice_browse = obj_inv.browse(cr,uid,invoice)    
        for x in invoice_browse :
            if x.state == 'paid' :
                raise osv.except_osv(('Perhatian !'), ("Invoice No \'%s\' telah dibayar, Pengurusan STNK dan BPKB tidak bisa dicancel  !")%(x.name))
            else :
                obj_inv.signal_workflow(cr, uid, [x.id], 'invoice_cancel' ) 
        
        return True
        
    @api.one 
    def confirm_pengurusan(self):
        lot_pool = self.env['stock.production.lot'] 
        tanggal = datetime.today()
        self.write({'state': 'confirm','tgl_pengurusan':tanggal,'confirm_uid':self._uid,'confirm_date':datetime.now()})       
  
        for x in self.pengurusan_line :
            lot_browse = lot_pool.search([
                        ('id','=',x.name.id)
                        ])             
            if lot_browse :               
                lot_browse.write({
                                  'biro_jasa_id':self.partner_id.id,                                  
                                  'plat':x.plat,                                  
                                  })
                if lot_browse.state == 'paid_offtr' :
                    lot_browse.write({'state':'paid'})
                if lot_browse.state == 'sold_offtr' :
                    lot_browse.write({'state':'sold'})
        return True

    @api.model
    def action_create_invoice(self):
        self.action_create_invoice_supplier()
        return self.action_create_invoice_customer()


    @api.model
    def wkf_approve(self) :
        self.write({'state': 'confirm'})     
            
    @api.cr_uid_ids_context
    def action_create_invoice_customer(self,cr,uid,ids,context=None):        
        invoice_bbn = {}
        invoice_bbn_line = []
        total_bbn = 0
        val = self.browse(cr,uid,ids)
        lot = self.pool.get('stock.production.lot')
        for x in val.pengurusan_line :    
            if x.plat == 'H' :
                if not val.branch_id.pricelist_bbn_hitam_id:
                    raise osv.except_osv(('Perhatian !'), ("Price List BBN hitam belum diisi di Master Branch")) 
                else :
                    pricelist = val.branch_id.pricelist_bbn_hitam_id.id
            elif x.plat == 'M' :
                if not val.branch_id.pricelist_bbn_merah_id:
                    raise osv.except_osv(('Perhatian !'), ("Price List BBN Merah belum diisi di Master Branch")) 
                else :
                    pricelist = val.branch_id.pricelist_bbn_merah_id.id
            price = self.pool.get('product.pricelist').price_get(cr,uid,[pricelist], x.name.product_id.id, 1,0)[pricelist]
            if price is False:
                return {
                        'warning':
                        {'title':'Perhatian !',
                         'message':('Data Pricelist BBN tidak ditemukan untuk produk engine %s, silahkan konfigurasi data cabang dulu.')%(x.name.name)
                        }}
            else:
                total_bbn += price
                model = 'dealer.sale.order.line'
                obj_ids = self.pool.get(model).search(cr, uid, [('dealer_sale_order_line_id','=',x.name.dealer_sale_order_id.id),('lot_id','=',x.name.id)], limit=1)
                if not obj_ids:
                    model = 'dym.retur.jual.line'
                    obj_ids = self.pool.get(model).search(cr, uid, [('dso_line_id.dealer_sale_order_line_id','=',x.name.dealer_sale_order_id.id),('retur_lot_id','=',x.name.id),('retur_id.state','not in',['draft','cancel'])], limit=1)
                if obj_ids:
                    obj = self.pool.get(model).browse(cr, uid, obj_ids)
                    obj.write({'price_bbn':price})
                
        config = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',val.branch_id.id),
                                                                ])
  
        if config :
            config_browse = self.pool.get('dym.branch.config').browse(cr,uid,config)
            debit_account_id = config_browse.offtr_to_ontr_bbn_jual_journal_id.default_debit_account_id.id   
            credit_account_id = config_browse.offtr_to_ontr_bbn_jual_account_id.id   
            if not config_browse.offtr_to_ontr_bbn_jual_journal_id or not debit_account_id or not credit_account_id:
                raise osv.except_osv(_('Error!'),
                    _('Data Jurnal BBN Jual Off the Road untuk branch %s belum lengkap!') % \
                    (val.branch_id.name))                 
        elif not config :
            raise osv.except_osv(_('Error!'),
                _('Please define Journal in Setup Division for this branch: "%s".') % \
                (val.branch_id.name))                              
              
        obj_inv = self.pool.get('account.invoice')
        analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, 'Unit', False, 4, 'Sales')
        invoice_bbn = {
                        'name':val.name,
                        'origin': val.name,
                        'branch_id':val.branch_id.id,
                        'division':val.division,
                        'partner_id':val.customer_id.id,
                        'date_invoice':val.tgl_pengurusan,
                        'reference_type':'none',
                        'account_id':debit_account_id,
                        'type': 'out_invoice',                                    
                        'tipe': 'customer',
                        'journal_id' : config_browse.offtr_to_ontr_bbn_jual_journal_id.id,
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'analytic_4': analytic_4,
                        }
        invoice_bbn_line.append([0,False,{
                        'account_id':credit_account_id,
                        'name': 'BBN ' + str(val.name),
                        'quantity': 1,
                        'origin': val.name,
                        'price_unit':total_bbn,
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id': analytic_4,
                        }])
        invoice_bbn['invoice_line'] = invoice_bbn_line
        invoice_bbn_create = obj_inv.create(cr,uid,invoice_bbn)
        obj_inv.signal_workflow(cr, uid, [invoice_bbn_create], 'invoice_open' )
        
        #add customer invoice pengurusan stnk dan bpkb di lot
        for x in val.pengurusan_line :
            lot_search = lot.search(cr,uid,[
                                            ('id','=',x.name.id)
                                            ])
            if not lot_search :
                raise osv.except_osv(_('Error!'),
                    _('No engine: "%s" tidak ditemukan.') % \
                    (x.name))   
            lot.write(cr,uid,[x.name.id],{'tgl_pengurusan_stnk_bpkb':val.tgl_pengurusan,'inv_pengurusan_stnk_bpkb_id':invoice_bbn_create})  
                  
        return invoice_bbn_create

    @api.cr_uid_ids_context
    def action_create_invoice_supplier(self,cr,uid,ids,context=None):
        # invoice_bbn = {}
        # invoice_bbn_line = []
        # total = 0
        # obj_inv = self.pool.get('account.invoice')
        # val = self.browse(cr,uid,ids)
        # lot = self.pool.get('stock.production.lot')
        
        
        # config = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',val.branch_id.id),
        #                                                         ])
  
        # if config :
        #     config_browse = self.pool.get('dym.branch.config').browse(cr,uid,config)
        #     debit_account_id = config_browse.offtr_to_ontr_bbn_beli_journal_id.default_debit_account_id.id 
        #     credit_account_id = config_browse.offtr_to_ontr_bbn_beli_journal_id.default_credit_account_id.id  
        #     if not debit_account_id or not credit_account_id :
        #         raise osv.except_osv(_('Error!'),
        #             _('Please define Journal Off the road to on the road in Setup Division for this branch: "%s".') % \
        #             (val.branch_id.name))        
        # elif not config :
        #     raise osv.except_osv(_('Error!'),
        #         _('Please define Journal Setup Division for this branch: "%s".') % \
        #         (val.branch_id.name)) 
        
        # for x in val.pengurusan_line :   
        #     city = x.customer_stnk.city_id.id
        #     if not x.customer_stnk.city_id.id :
        #         city = x.customer_stnk.city_tab_id.id 
                
        #     biro_line = self.pool.get('dym.pengurusan.stnk.bpkb.line')._get_harga_bbn_detail(cr, uid, ids, val.partner_id.id, x.plat, city, x.name.product_id.product_tmpl_id.id,val.branch_id.id) 
        #     if not biro_line :
        #         raise osv.except_osv(_('Error!'),
        #             _('Harga BBN tidak ditemukan, masukan setting configurasi birojasa dalam master branch !'))                 
        #     total = biro_line.total
        #     total_jasa = biro_line.jasa + biro_line.jasa_area
        #     invoice_bbn = {
        #         'name':val.name,
        #         'origin':val.name,
        #         'branch_id':val.branch_id.id,
        #         'division':val.division,
        #         'partner_id':val.partner_id.id,
        #         'date_invoice':val.tgl_pengurusan,
        #         'reference_type':'none',
        #         'account_id':credit_account_id,
        #         'type':'in_invoice', 
        #         'tipe':'bbn',
        #         'qq_id':x.customer_stnk.id, 
        #         'lot_id':x.name.id,
        #         'journal_id':config_browse.offtr_to_ontr_bbn_beli_journal_id.id
        #     }
        #     analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, 'Unit', False, 4, 'Sales')
        #     invoice_bbn_line  = [[0,False,{
        #         'account_id':debit_account_id,
        #         'partner_id':val.partner_id.id,
        #         'name': 'BBN '+x.name.product_id.name,
        #         'quantity': 1,
        #         'origin': val.name,
        #         'price_unit':total,
        #         'price_subtotal':total,
        #         'analytic_2': analytic_2,
        #         'analytic_3': analytic_3,
        #         'account_analytic_id':analytic_4,
        #     }]]
        #     invoice_bbn['invoice_line']=invoice_bbn_line
        #     invoice_bbn_create = obj_inv.create(cr,uid,invoice_bbn)
        #     obj_inv.signal_workflow(cr, uid, [invoice_bbn_create], 'invoice_open' )
        #     lot.write(cr,uid,[x.name.id],{'invoice_bbn':invoice_bbn_create,'total_jasa':total_jasa})
        return True

    @api.model
    def create(self,vals,context=None):
        if not vals['pengurusan_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail pengurusan. Data tidak bisa di save."))
        lot_penerimaan = []
        for x in vals['pengurusan_line']:
            lot_penerimaan.append(x.pop(2))
        lot_pool = self.env['stock.production.lot']
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'PSB', division=vals['division'])       
        vals['tgl_pengurusan'] = time.strftime('%Y-%m-%d')
        del[vals['pengurusan_line']]
         
        pengurusan_id = super(dym_pengurusan_stnk_bpkb, self).create(vals)
     
        if pengurusan_id :         
            for x in lot_penerimaan :
                
                lot_browse = lot_pool.search([('id','=',x['name'])])
                # city = lot_browse.customer_stnk.city_id.id
                # if not lot_browse.customer_stnk.city_id.id :
                #     city = lot_browse.customer_stnk.city_tab_id.id 
                # biro_line = self.env['dym.pengurusan.stnk.bpkb.line']._get_harga_bbn_detail(vals['partner_id'], x['plat'], city, lot_browse.product_id.product_tmpl_id.id,vals['branch_id']) 
                # if not biro_line :
                #     raise osv.except_osv(_('Error!'),
                #         _('Data Pricelist BBN tidak ditemukan untuk produk engine %s, silahkan konfigurasi data cabang dulu. ! ') % (lot_browse.name))
                                   
                pengurusan_pool = self.env['dym.pengurusan.stnk.bpkb.line']
                pengurusan_pool.create({
                                                    'name':lot_browse.id,
                                                    'pengurusan_id':pengurusan_id.id,
                                                    'customer_stnk':lot_browse.customer_stnk.id,
                                                    'plat':x['plat'],
 
                                                    })
                lot_browse.write({
                       'pengurusan_stnk_bpkb_id':pengurusan_id.id,
                       })   
                            
        else :
            return False
        return pengurusan_id    

    @api.cr_uid_ids_context
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
        obj = obj_inv.search(cr,uid,[('origin','ilike',val.name)])
        result['res_id'] = obj[0] 
        return result
 
    @api.model
    def wkf_pengurusan_done(self):
        self.write({'state': 'done'})

    @api.cr_uid_ids_context
    def birojasa_change(self,cr,uid,ids,branch_id,birojasa_id,context=None):
        domain = {}
        birojasa = []
        birojasa_srch = self.pool.get('dym.harga.birojasa').search(cr,uid,[
                                                                      ('branch_id','=',branch_id)
                                                                      ])
        if birojasa_srch :
            birojasa_brw = self.pool.get('dym.harga.birojasa').browse(cr,uid,birojasa_srch)
            for x in birojasa_brw :
                birojasa.append(x.birojasa_id.id)
        domain['partner_id'] = [('id','in',birojasa)]
        return {'domain':domain} 
                            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Pengurusan STNK BPKB sudah diproses, data tidak bisa didelete !"))
        return super(dym_pengurusan_stnk_bpkb, self).unlink(cr, uid, ids, context=context)  

    @api.multi
    def write(self,values,context=None):
        values.get('pengurusan_line',[]).sort(reverse=True)
        return super(dym_pengurusan_stnk_bpkb,self).write(values)
        
class dym_pengurusan_stnk_bpkb_line(models.Model):
    _name = "dym.pengurusan.stnk.bpkb.line"

    pengurusan_id = fields.Many2one('dym.pengurusan.stnk.bpkb',string='Penerimaan Notice')
    name = fields.Many2one('stock.production.lot',string='No Engine',domain="[('branch_id','=',parent.branch_id),('tgl_terima','!=',False),('tgl_pengurusan_stnk_bpkb','=',False),('state_stnk','=','terima_faktur'),'|',('state','=','sold_offtr'),('state','=','paid_offtr'),'|',('customer_id','=',parent.customer_id),('customer_stnk','=',parent.customer_id)]",change_default=True)
    customer_id = fields.Many2one('res.partner',related="name.customer_id",string="Customer",readonly=True)
    customer_stnk = fields.Many2one('res.partner',related="name.customer_stnk",string="Customer STNK",readonly=True)
    plat = fields.Selection([('H','H'),('M','M')],'Plat',default='H')

    _sql_constraints = [
    ('unique_name_pengurusan_id', 'unique(name,pengurusan_id)', 'Detail Engine duplicate, mohon cek kembali !'),
]   
    @api.cr_uid_ids_context
    def onchange_engine(self,cr,uid,ids,name,partner_id,plat,branch_id):
        warning = {}
        lot_obj = self.pool.get('stock.production.lot')
        lot_search = lot_obj.search(cr,uid,[('id','=',name)])
        lot_browse = lot_obj.browse(cr,uid,lot_search)  
        return {
            'value':{
                'customer_id':lot_browse.customer_id.id,
                'customer_stnk':lot_browse.customer_stnk.id,
                'plat':lot_browse.plat,
            },
            'warning':warning
        }        

    @api.cr_uid_ids_context
    def onchange_plat(self,cr,uid,ids,name,partner_id,plat,branch_id):
        warning = {}       
        return {'warning':warning}
        
    @api.cr_uid_ids_context    
    def _get_harga_bbn_detail(self, cr, uid, ids, birojasa_id, plat, city_id, product_template_id,branch_id,context=None):
        if not birojasa_id:
            return False
        birojasa = self.pool.get('dym.harga.birojasa')
        harga_birojasa = birojasa.search(cr,uid,[
                                                 ('birojasa_id','=',birojasa_id),
                                                 ('branch_id','=',branch_id),
                                                 ('default_birojasa','=',True)
                                                 ])
        if not harga_birojasa :
            raise osv.except_osv(_('Attention!'),
                _('Default Birojasa tidak ditemukan silahkan buat terlebih dahulu'))
            
        harga_birojasa_browse = birojasa.browse(cr,uid,harga_birojasa)
        
        bbn_search = self.pool.get('dym.harga.bbn').search(cr,uid,[
                                                                   ('id','=',harga_birojasa_browse.harga_bbn_id.id)
                                                                   ])
        if not bbn_search :
            raise osv.except_osv(_('Attention!'),
                _('Harga BBN tidak ditemukan'))
        
        bbn_browse = self.pool.get('dym.harga.bbn').browse(cr,uid,bbn_search)
                     
        pricelist_harga_bbn = self.pool.get('dym.harga.bbn.line').search(cr,uid,[
                ('bbn_id','=',bbn_browse.id),                                                                    
                ('tipe_plat','=',plat),
                ('active','=',True),
                ('start_date','<=',datetime.now().strftime('%Y-%m-%d')),
                ('end_date','>=',datetime.now().strftime('%Y-%m-%d')),
            ])

        if not pricelist_harga_bbn:
            raise osv.except_osv(_('Attention!'),
                _('Pricelist tidak ditemukan, silahkan setting terlebih dahulu dalam master branch'))

        for pricelist_bbn in pricelist_harga_bbn:
            bbn_detail = self.pool.get('dym.harga.bbn.line.detail').search(cr,uid,[
                    ('harga_bbn_line_id','=',pricelist_bbn),
                    ('product_template_id','=',product_template_id),
                    ('city_id','=',city_id)
                ])
            if bbn_detail:
                return self.pool.get('dym.harga.bbn.line.detail').browse(cr,uid,bbn_detail)
 