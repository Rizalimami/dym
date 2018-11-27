import time
from datetime import datetime
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from openerp import workflow, api

class wiz_proses_stnk_line(orm.TransientModel):
    _name = 'wiz.proses.stnk.line'
    _description = "Proses STNK Wizard"
    _columns = {
        'wizard_proses_stnk_id': fields.many2one('wiz.proses.stnk', 'Wizard ID'),
        'name': fields.many2one('stock.production.lot', 'Engine No'),
        'chassis_no': fields.related('name', 'chassis_no', type='char', string='Chassis Number'),
        'customer_stnk': fields.related('name', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
        'faktur_stnk': fields.related('name', 'faktur_stnk', type='char', string='No Faktur STNK'),
        'biro_jasa_id': fields.many2one('res.partner', 'Biro Jasa', domain=[('biro_jasa','=',True)]),
        'tgl_faktur': fields.related('name', 'tgl_faktur', type='date', string='Tanggal Mohon Faktur'),
        'tgl_terima': fields.related('name', 'tgl_terima', type='date', string='Tanggal Terima'),
        'check_process':fields.boolean('Process?'),
    }

    def onchange_biro_jasa(self, cr, uid, ids, birojasa_id, branch_id, context=None):
        domain = {}
        value = {}
        warning = {}
        birojasa = []
        birojasa_srch = self.pool.get('dym.harga.birojasa').search(cr,uid,[
            ('branch_id','=',branch_id)
        ])
        if birojasa_srch :
            birojasa_brw = self.pool.get('dym.harga.birojasa').browse(cr,uid,birojasa_srch)
            for x in birojasa_brw :
                birojasa.append(x.birojasa_id.id)
        domain['biro_jasa_id'] = [('id','in',birojasa)]
        if birojasa_id and birojasa_id not in birojasa:
            warning = {
                'title': ('Perhatian !'),
                'message': (('Biro jasa yang anda pilih tidak terdaftar di dalam branch')),
            }
            value['biro_jasa_id'] = False
            return {'warning':warning,'domain':domain,'value':value}
        return {'domain':domain}

class wiz_proses_stnk(orm.TransientModel):
    _name = 'wiz.proses.stnk'
    _description = "Proses STNK Wizard"
    _columns = {
        'proses_stnk_id' : fields.many2one('dym.proses.stnk', 'Proses STNK'),
        'branch_id' : fields.many2one('dym.branch', 'Branch', required=True),
        'line_ids': fields.one2many('wiz.proses.stnk.line', 'wizard_proses_stnk_id'),
    }
    _defaults = {
        'proses_stnk_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False,
        'branch_id': lambda self, cr, uid, ctx: ctx and ctx.get('branch_id', False) or False,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("Data Error, please try to refresh page or contact your administrator!"))
        res = super(wiz_proses_stnk, self).default_get(cr, uid, fields, context=context)
        proses_id = context and context.get('active_id', False) or False
        proses = self.pool.get('dym.proses.stnk').browse(cr, uid, proses_id, context=context)
        branch_id = proses.branch_id.id
        line = self.pool.get('stock.production.lot')
        if branch_id:
            lot_pool = self.pool.get('stock.production.lot')
            lot_search = lot_pool.search(cr,uid,[
                ('branch_id','=',branch_id),
                # ('biro_jasa_id','=',partner_id),
                ('state_stnk','=','terima_faktur'),
                ('tgl_terima','!=',False),
                ('tgl_proses_stnk','=',False),
                ('proses_stnk_id','=',False),
                '|',('state','=','paid'),
                '&',('state','=','sold'),
                ('customer_id.is_group_customer','!=',False),
                # '|',('inv_pengurusan_birojasa_id','=',False),
                # '&',('inv_pengurusan_birojasa_id','!=',False),
                # ('state_pengurusan_birojasa','=','paid'),
            ])
            lot = []
            if not lot_search :
                lot = []
            elif lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)           
                for x in lot_browse :
                    lot.append([0,0,{
                        'check_process':False,
                        'name':x.id,                               
                        'chassis_no':x.chassis_no,
                        'customer_stnk':x.customer_stnk.id,
                        'faktur_stnk':x.faktur_stnk,
                        'tgl_faktur':x.tgl_faktur,
                        'tgl_terima':x.tgl_terima,
                        'biro_jasa_id':x.biro_jasa_id.id
                    }])   
            res['line_ids']= lot
        return res

    def add_new(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for data in self.browse(cr, uid, ids, context=context):
            for line in data.line_ids:
                if line.check_process:
                    line.name.write({'proses_stnk_id':data.proses_stnk_id.id,'biro_jasa_id':line.biro_jasa_id.id})
        return {}

class dym_proses_stnk(osv.osv):
    _name = 'dym.proses.stnk'
    _inherit = ['mail.thread']
    _description = "Proses STNK"

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    def _get_invoice_count(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for proses in self.browse(cr, uid, ids):
            obj_inv = self.pool.get('account.invoice')
            obj = obj_inv.search(cr,uid,[
                ('origin','ilike',proses.name),
                ('type','=','in_invoice'),
                ('tipe','=','bbn')
            ])
            res[proses.id] = int(len(obj))
        return res

    def _get_birojasa_ids(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            birojasa_ids = []
            for lot in record.serial_number_ids:
                if lot.biro_jasa_id.id not in birojasa_ids:
                    birojasa_ids.append(lot.biro_jasa_id.id)
            result[record.id] = birojasa_ids
        return result
    
    @api.depends('serial_number_ids.name')
    def _amount_all(self):
        for ib in self:
            amount_total = 0.0
            for line in ib.serial_number_ids:
                ib.update({
                    'total_record': len(ib.serial_number_ids),
                })

    _columns = {
        # 'dso_ids': fields.related('serial_number_ids', 'dealer_sale_order_id', type='many2one', relation='dealer.sale.order', string='Dealer Sales Memo'),
        'birojasa_ids': fields.function(_get_birojasa_ids, type='many2many', relation="res.partner", string="Birojasa"),
        'branch_id': fields.many2one('dym.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Showroom')], 'Division', change_default=True, select=True),
        'name': fields.char('No Reference', readonly=True),
        'tgl_proses_stnk': fields.date('Tanggal'),
        'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
        'serial_number_ids': fields.one2many('stock.production.lot','proses_stnk_id',string="Table Proses STNK"), 
        'engine_no': fields.related('serial_number_ids', 'name', type='char',string='No Engine'),
        'customer_stnk': fields.related('serial_number_ids', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
        'confirm_uid':fields.many2one('res.users',string="Posted by"),
        'confirm_date':fields.datetime('Posted on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),     
        'invoice_count': fields.function(_get_invoice_count,string='Invoice Count', type='integer'),
        'total_record' : fields.integer(string='Total Engine', store=True, readonly=True, compute='_amount_all'),
    }
    _defaults = {
        'name': '/',
        'tgl_proses_stnk': fields.date.context_today,
        'state':'draft',
        'division' : 'Unit',
        'branch_id': _get_default_branch,
     }    
    
    def cancel_proses(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        for x in val.serial_number_ids :
            lot_search = lot_pool.search(cr,uid,[
                ('branch_id','=',val.branch_id.id),
                ('proses_stnk_id','=',val.id),
                ('name','=',x.name),
            ])
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                if lot_browse.penerimaan_stnk_id.id or lot_browse.penerimaan_notice_id.id or lot_browse.penerimaan_bpkb_id.id or lot_browse.proses_biro_jasa_id.id :
                    raise osv.except_osv(('Perhatian !'), ("No faktur engine \'%s\' telah diproses, data tidak bisa di cancel !")%(lot_browse.name))                    
                else : 
                    lot_browse.write({'state_stnk': 'terima_faktur','tgl_proses_stnk':False,'proses_stnk_id':False})
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penerimaan. Data tidak bisa di save."))
        self.write(cr, uid, ids, {
            'state': 'cancel',
            'cancel_uid':uid,
            'cancel_date':datetime.now()
        })
        self.message_post(cr, uid, val.id, body=_("Proses STNK canceled "), context=context) 
        return True
    
    def _get_branch_journal_config(self,cr,uid,branch_id):
        result = {}
        obj_branch_config_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
        if not obj_branch_config_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak Ditemukan konfigurasi jurnal Cabang, Silahkan konfigurasi dulu"))
        else:
            obj_branch_config = self.pool.get('dym.branch.config').browse(cr,uid,obj_branch_config_id[0])
            # if not(obj_branch_config.proses_stnk_journal_bbnbeli_id.id):
            #     raise osv.except_osv(('Perhatian !'), ("Konfigurasi jurnal proses stnk cabang belum lengkap, silahkan setting dulu"))
        return obj_branch_config

    def get_move_line_bbn(self,cr,uid,ids,move_line_bbn_ids,line_ids,context=None):
        for x in line_ids :
            if x.credit > 0.0 :
                move_line_bbn_ids = x.id                              
        return move_line_bbn_ids
        
    def post_proses(self,cr,uid,ids,context=None):                                
        val = self.browse(cr,uid,ids)  
        if not val.serial_number_ids:
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail proses STNK. Data tidak bisa di post."))

        lot_pool = self.pool.get('stock.production.lot') 
        engine = ''
        tanggal = datetime.today()
        self.write(cr, uid, ids, {
            'state': 'posted',
            'tgl_proses_stnk': tanggal,
            'confirm_uid': uid,
            'confirm_date': datetime.now()
        })
        obj_branch_config = self._get_branch_journal_config(cr,uid,val.branch_id.id)
        line_errors = []
        for x in val.serial_number_ids:
            lot_search = lot_pool.search(cr,uid,[
                ('branch_id','=',val.branch_id.id),
                ('state_stnk','=','terima_faktur'),
                ('tgl_terima','!=',False),
                ('tgl_proses_stnk','=',False),
                ('name','=',x.name)
            ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penerimaan. Data tidak bisa di save."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                lot_browse.write({
                    'state_stnk':'proses_stnk',
                    'tgl_proses_stnk': val.tgl_proses_stnk,
                })
            engine += ('- '+str(x.name)+'<br/>')
            if x.biro_jasa_id:
                dso_search = self.pool.get('dealer.sale.order.line').search(cr, uid, [('lot_id','=',x.id),('dealer_sale_order_line_id','=',x.dealer_sale_order_id.id)])
                line = self.pool.get('dealer.sale.order.line').browse(cr, uid, dso_search)
                if line.is_bbn == 'Y':                    
                    total_jasa = 0
                    city = line.lot_id.cddb_id.city_id.id
                    if not city:
                        raise osv.except_osv(_('Error!'),_('Mohon lengkapi data kota untuk customer CDDB %s')%(lot_browse.customer_stnk.name)) 
                    biro_line = self.pool.get('dealer.spk')._get_harga_bbn_detail(cr, uid, ids, x.biro_jasa_id.id, line.plat, city, x.product_id.product_tmpl_id.id,val.branch_id.id)
                    total = 0
                    if not biro_line:
                        if line.price_bbn_beli > 0:
                            total = line.price_bbn_beli
                        else:
                            msg = '%s type %s alamat %s' % (line.lot_id.name,line.template_id.name,line.lot_id.cddb_id.city_id.name)
                            line_errors.append(msg)
                    else:
                        total = biro_line.total
                        line.write({
                            'price_bbn_beli': biro_line.total,
                            'price_bbn_notice': biro_line.notice,
                            'price_bbn_proses': biro_line.proses,
                            'price_bbn_jasa': biro_line.jasa,
                            'price_bbn_jasa_area': biro_line.jasa_area,
                            'price_bbn_fee_pusat': biro_line.fee_pusat,
                        })
                    if not line_errors:
                        total_jasa = line.price_bbn_jasa+line.price_bbn_jasa_area
                        x.write({
                            'total_jasa':total_jasa,
                        })
        if line_errors:
            line_error_msg = ','.join(line_errors)
            raise osv.except_osv(('Perhatian !'), ("Harga BBN untuk nomor mesin %s tidak ditemukan, mohon cek master harga bbn yang tersedia!" % line_error_msg))
        self.message_post(cr, uid, val.id, body=_("Proses STNK posted <br/> No Engine : <br/>  %s ")%(engine), context=context)                             
        if val.name == '/':
            values = {
                'name' : self.pool.get('ir.sequence').get_per_branch(cr, uid, val.branch_id.id, 'PST', division='Unit')
            }
            self.write(cr, uid, ids, values, context=context)            
        return True
    
    def action_view_invoice_bbn(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')        
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'dym_purchase_order', 'action_invoice_tree2_showroom')        
        id = result and result[1] or False        
        result = act_obj.read(cr, uid, [id], context=context)[0]
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        obj = obj_inv.search(cr,uid,[
            ('origin','ilike',val.name),
            ('type','=','in_invoice'),
            ('tipe','=','bbn')
        ])        
        if len(obj)>0:
            result['domain'] = "[('id','in',["+','.join(map(str, obj))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = obj[0] 
        return result

    def onchange_engine_line(self, cr, uid, ids, branch_id,context=None):
        line = self.pool.get('stock.production.lot')
        value = {}
        if ids :
            obj = self.browse(cr,uid,ids)
            if obj.serial_number_ids.name :
                for x in obj.serial_number_ids :
                    line_search = line.search(cr,uid,[
                        ('proses_stnk_id','=',obj.id)
                    ])
                    if line_search :
                        line_browse = line.browse(cr,uid,line_search)
                        line_browse.write({'proses_stnk_id':False})
        domain = {}
        return {'value':value,'domain':domain}
    
    def create(self, cr, uid, vals, context=None):
        lot_collect = []
        for x in vals['serial_number_ids']:
            lot_collect.append(x.pop(2))
        del[vals['serial_number_ids']]
        lot_pool = self.pool.get('stock.production.lot')
        vals['tgl_proses_stnk'] = time.strftime('%Y-%m-%d'),
        try :
            proses_stnk_id = super(dym_proses_stnk, self).create(cr, uid, vals, context=context) 
            if proses_stnk_id : 
                for x in lot_collect :
                    lot_search = lot_pool.search(cr,uid,[
                        ('branch_id','=',vals['branch_id']),
                        # ('biro_jasa_id','=',x['partner_id']),
                        ('state_stnk','=','terima_faktur'),
                        ('tgl_terima','!=',False),
                        ('tgl_proses_stnk','=',False),
                        ('name','=',x['name'])
                    ])
                    if lot_search :
                        lot_browse = lot_pool.browse(cr,uid,lot_search)
                        lot_browse.write({
                            'proses_stnk_id':proses_stnk_id,
                            'biro_jasa_id':x['biro_jasa_id'],
                        })  
            else :
                return False
            cr.commit()
        except Exception:
            cr.rollback()
            raise osv.except_osv(('Perhatian !'), ("Data telah diproses user lain. Periksa kembali data Anda."))
        return proses_stnk_id  

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        collect = self.browse(cr,uid,ids)
        lot = vals.get('serial_number_ids', False)
        if lot :
            del[vals['serial_number_ids']]
            for x,item in enumerate(lot) :
                lot_pool = self.pool.get('stock.production.lot')
                lot_id = item[1]
                if item[0] == 2 :
                    lot_search = lot_pool.search(cr,uid,[
                        ('id','=',lot_id)
                    ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar"))
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                        'proses_stnk_id':False,
                        'tgl_proses_stnk':False,
                    })
                    self.message_post(cr, uid, collect.id, body=_("Delete Engine No \'%s\'")%(lot_browse.name), context=context)                                                                           
                elif item[0] == 0 :
                    values = item[2]
                    lot_search = lot_pool.search(cr,uid,[
                        ('name','=',values['name'])
                    ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                        'proses_stnk_id':collect.id,
                        'biro_jasa_id':values['biro_jasa_id'],
                    })
                elif item[0] == 1:
                    values = item[2]
                    lot_search = lot_pool.search(cr,uid,[
                       ('id','=',lot_id)
                       ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar"))
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                        'biro_jasa_id':values['biro_jasa_id'],
                    })
        return super(dym_proses_stnk, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Permohonan Faktur sudah di validate ! tidak bisa didelete !"))
        lot_pool = self.pool.get('stock.production.lot')
        lot_search = lot_pool.search(cr,uid,[
            ('proses_stnk_id','=',ids)
        ])
        lot_browse = lot_pool.browse(cr,uid,lot_search)
        for x in lot_browse :
            x.write({'tgl_proses_stnk':False})
        return super(dym_proses_stnk, self).unlink(cr, uid, ids, context=context)

class dym_stock_production_lot_proses_stnk(osv.osv):
    _inherit = 'stock.production.lot'

    def onchange_biro_jasa(self, cr, uid, ids, birojasa_id, branch_id,context=None):
        domain = {}
        value = {}
        warning = {}
        birojasa = []
        birojasa_srch = self.pool.get('dym.harga.birojasa').search(cr,uid,[
            ('branch_id','=',branch_id)
        ])
        if birojasa_srch :
            birojasa_brw = self.pool.get('dym.harga.birojasa').browse(cr,uid,birojasa_srch)
            for x in birojasa_brw :
                birojasa.append(x.birojasa_id.id)
        domain['biro_jasa_id'] = [('id','in',birojasa)]
        if birojasa_id and birojasa_id not in birojasa:
            warning = {
                'title': ('Perhatian !'),
                'message': (('Biro jasa yang anda pilih tidak terdaftar di dalam branch')),
            }
            value['biro_jasa_id'] = False
            return {'warning':warning,'domain':domain,'value':value}
        return {'domain':domain}