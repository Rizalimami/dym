import time
from datetime import datetime
from openerp.osv import fields, osv, orm
from openerp import api

class wiz_penyerahan_bpkb_line(orm.TransientModel):
    _name = 'wiz.penyerahan.bpkb.line'
    _description = "penyerahan bpkb Line Wizard"
        
    _columns = {
        'penyerahan_bpkb_id': fields.many2one('dym.penyerahan.bpkb', string='penyerahan bpkb'),
        'lot_ids': fields.many2many('stock.production.lot','wiz_penyerahan_bpkb_line_lot_rel','wiz_penyerahan_bpkb_id','lot_id','Engine Number'),
    }

    _defaults = {
        'penyerahan_bpkb_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("Data Error, please try to refresh page or contact your administrator!"))
        res = super(wiz_penyerahan_bpkb_line, self).default_get(cr, uid, fields, context=context)
        return res

    def lot_change(self, cr, uid, ids, penyerahan_bpkb_id, context=None):
        domain = {}
        penyerahan = self.pool.get('dym.penyerahan.bpkb').browse(cr, uid, penyerahan_bpkb_id)
        saved_lot_ids = penyerahan.penyerahan_line.mapped('name').ids
        domain['lot_ids'] = ['&','&','&','&',('tgl_proses_birojasa','!=',False),('tgl_terima_bpkb','!=',False),('state_stnk','=','proses_stnk'),('branch_id','=',penyerahan.branch_id.id),('tgl_penyerahan_bpkb','=',False),'|',('finco_id','=',penyerahan.partner_id.id),'&',('customer_id','=',penyerahan.partner_id.id),('finco_id','=',False),('id','not in',saved_lot_ids)]
        return {'domain':domain}

    def save_lot_ids(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for data in self.browse(cr, uid, ids, context=context):
            for lot in data.lot_ids:
                lot_change_vals = self.pool.get('dym.penyerahan.bpkb.line').onchange_engine(cr, uid, ids, lot.id, data.penyerahan_bpkb_id.branch_id.id, data.penyerahan_bpkb_id.division, data.penyerahan_bpkb_id.partner_id.id, data.penyerahan_bpkb_id.penerima)
                if 'warning' in lot_change_vals and lot_change_vals['warning']:
                    raise osv.except_osv((lot_change_vals['warning']['title']), (lot_change_vals['warning']['message']))
                lot_change_vals['value']['penyerahan_id'] = data.penyerahan_bpkb_id.id
                lot_change_vals['value']['name'] = lot.id
                res = {
                    'penyerahan_line': [[0, data.penyerahan_bpkb_id.id, lot_change_vals['value']]]
                }
                data.penyerahan_bpkb_id.write(res)
        return True

class dym_penyerahan_bpkb(osv.osv):
    _name = "dym.penyerahan.bpkb"

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user = user_obj.browse(cr,uid,uid)
        if user.branch_type!='HO':
            if not user.branch_id:
                return False
            return user.branch_id.id
        else:
            return False

    @api.depends('penyerahan_line.name')
    def _amount_all(self):
        for ib in self:
            amount_total = 0.0
            for line in ib.penyerahan_line:
                ib.update({
                    'total_record': len(ib.penyerahan_line),
                })
    
    _columns = {
        'name': fields.char('No Reference', readonly=True),
        'branch_id': fields.many2one('dym.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Showroom')], 'Division', change_default=True, select=True),
        'penerima':fields.char('Penerima'),
        'partner_id':fields.many2one('res.partner','Customer'),
        'partner_cabang': fields.many2one('dym.cabang.partner',string='Customer Branch'),
        'keterangan':fields.char('Keterangan'),
        'tanggal':fields.date('Tanggal'),
        'penyerahan_line' : fields.one2many('dym.penyerahan.bpkb.line','penyerahan_id',string="Penyerahan STNK"),  
        'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
        'engine_no': fields.related('penyerahan_line', 'name', type='char', string='No Engine'),
        'customer_stnk': fields.related('penyerahan_line', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK', help=' Syarat Penyerahan BKPB: \
                                    \n* Semua tagihan harus sudah lunas (termasuk pajak progresif). \
                                    \n* Sudah proses STNK. \
                                    \n* Sudah terima BPKB'),
        'no_bpkb': fields.related('penyerahan_line', 'no_bpkb', type='char', string='No BPKB'),
        'tgl_penyerahan_bpkb' :fields.date('Tgl Penyerahan BPKB'),
        'cetak_ke' : fields.integer('Cetak Ke'),     
        'confirm_uid':fields.many2one('res.users',string="Posted by"),
        'confirm_date':fields.datetime('Posted on'),        
        'total_record' : fields.integer(string='Total Engine', store=True, readonly=True, compute='_amount_all'),
    }
 
    _defaults = {
        'state':'draft',
        'division' : 'Unit',
        'tanggal': fields.date.context_today,
        'tgl_penyerahan_bpkb': fields.date.context_today,
        'cetak_ke' : 0,
        'branch_id': _get_default_branch,
    } 
    
    def post_penyerahan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = datetime.now()
        for x in val.penyerahan_line :
            lot_search = lot_pool.search(cr,uid,[
                ('id','=',x.name.id)
                ])
            lot_browse = lot_pool.browse(cr,uid,lot_search)
            lot_browse.write({
                   'tgl_penyerahan_bpkb':x.tgl_ambil_bpkb,
                   'lokasi_bpkb_id':False,
                   })   
        self.write(cr, uid, ids, {'state': 'posted','tanggal':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})       
        return True
    
    def create(self, cr, uid, vals, context=None):
        # if not vals['penyerahan_line'] :
        #     raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penyerahan. Data tidak bisa di save."))
        lot_penyerahan = []
        for x in vals['penyerahan_line']:
            lot_penyerahan.append(x.pop(2))
        lot_pool = self.pool.get('stock.production.lot')
        penyerahan_pool = self.pool.get('dym.penyerahan.bpkb.line')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PBK', division='Unit')
        
        vals['tanggal'] = time.strftime('%Y-%m-%d'),
        del[vals['penyerahan_line']]

        
        penyerahan_id = super(dym_penyerahan_bpkb, self).create(cr, uid, vals, context=context) 

        if penyerahan_id :         
            for x in lot_penyerahan :
                lot_search = lot_pool.search(cr,uid,[
                            ('id','=',x['name'])
                            ])
                if not lot_search :
                    raise osv.except_osv(('Perhatian !'), ("No Engine tidak ditemukan !"))
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                lot_browse.write({
                       'penyerahan_bpkb_id':penyerahan_id,
                       })   
                penyerahan_pool.create(cr, uid, {
                    'name':lot_browse.id,
                    'penyerahan_id':penyerahan_id,
                    'customer_stnk':lot_browse.customer_stnk.id,
                    'no_bpkb':lot_browse.no_bpkb,
                    'no_urut':lot_browse.no_urut_bpkb,
                    'tgl_ambil_bpkb':x['tgl_ambil_bpkb']
                })
                           
        else :
            return False
        return penyerahan_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        vals.get('penyerahan_line',[]).sort(reverse=True)

        collect = self.browse(cr,uid,ids)
        lot_penyerahan = []
        lot_pool = self.pool.get('stock.production.lot')
        line_pool = self.pool.get('dym.penyerahan.bpkb.line')
        lot = vals.get('penyerahan_line', False)
        if lot :
            for x,item in enumerate(lot) :
                lot_id = item[1]
                if item[0] == 2 :               
                    line_search = line_pool.search(cr,uid,[
                                                           ('id','=',lot_id)
                                                           ])
                    line_browse = line_pool.browse(cr,uid,line_search)
                    lot_search = lot_pool.search(cr,uid,[
                                           ('id','=',line_browse.name.id)
                                           ])
                    if not line_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Penerimaan Line"))
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    # del[vals['penyerahan_line']]
                    lot_browse.write({
                                   'penyerahan_bpkb_id':False,
                                   'tgl_penyerahan_bpkb':False
                                     })
                    # line_pool.unlink(cr,uid,lot_id, context=context)
                        
                elif item[0] == 0 :
                    values = item[2]
                    lot_search = lot_pool.search(cr,uid,[
                                                        ('id','=',values['name'])
                                                        ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
                    
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                           'penyerahan_bpkb_id':collect.id,
                           }) 
                    
        return super(dym_penyerahan_bpkb, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Penyerahan BPKB sudah di post ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')
        lot_search = lot_pool.search(cr,uid,[
                                           ('penyerahan_bpkb_id','=',ids)
                                           ])
        lot_browse = lot_pool.browse(cr,uid,lot_search)
        for x in lot_browse :
            x.write({
                     'tgl_penyerahan_bpkb':False,
                     })
        return super(dym_penyerahan_bpkb, self).unlink(cr, uid, ids, context=context)   
    
    def onchange_partner(self,cr,uid,ids,partner,penerima,context=None):
        warning = {}  
        value = {}  
        result = {}

        obj_browse = self.pool.get('res.partner').browse(cr,uid,[partner]) 


        if partner:
            res_partner = self.pool.get('res.partner').search(cr,uid,[
                                                                      ('id','=',partner)
                                                                      ])
            res_partner_browse = self.pool.get('res.partner').browse(cr,uid,res_partner)            
            if obj_browse.finance_company :
                value = {'penerima':res_partner_browse.name}
        if partner and penerima :
            if obj_browse.finance_company and penerima != obj_browse.name:
                warning = {
                        'title': ('Perhatian !'),
                        'message': ('A/N BPKB adalah Finance Company, Nama Penerima harus sama'),
                    } 
                if warning :
                    value = {'penerima':False}

        result['value'] = value         
        result['warning'] = warning
        return result

    def onchange_branch(self, cr, uid, ids, branch_id, context=None):
        warning = {}  
        domain = {}  
        value = {}  
        result = {}  
        if branch_id:
            branch = self.pool.get('dym.branch').browse(cr,uid,[branch_id])
            domain_lot = ['&','&','&','&',('tgl_proses_birojasa','!=',False),('tgl_terima_bpkb','!=',False),('state_stnk','=','proses_stnk'),('branch_id','=',branch_id),('tgl_penyerahan_bpkb','=',False),'|',('finco_id','!=',False),'&',('customer_id','!=',False),('finco_id','=',False)]
            lot_ids = self.pool.get('stock.production.lot').search(cr, uid, domain_lot)
            lot = self.pool.get('stock.production.lot').browse(cr, uid, lot_ids)
            finco = lot.mapped('finco_id')
            partner = lot.filtered(lambda r: not r.finco_id).mapped('customer_id')
            domain['partner_id'] = ['|',('id','in',finco.ids),('id','in',partner.ids)]
        result['domain'] = domain       
        result['value'] = value         
        result['warning'] = warning
        return result
    
class dym_penyerahan_bpkb_line(osv.osv):
    _name = "dym.penyerahan.bpkb.line"
    _columns = {
        'name' : fields.many2one('stock.production.lot','No Engine',domain="['&','&','&','&',('tgl_proses_birojasa','!=',False),('tgl_terima_bpkb','!=',False),('state_stnk','=','proses_stnk'),('branch_id','=',parent.branch_id),('tgl_penyerahan_bpkb','=',False),'|',('finco_id','=',parent.partner_id),'&',('customer_id','=',parent.partner_id),('finco_id','=',False),'|',('inv_pajak_progressive_id','=',False),('state_pajak_progressive','=','paid'),'|',('inv_pengurusan_stnk_bpkb_id','=',False),('state_pengurusan_stnk','=','paid')]",change_default=True, help="AR tagihan harus sudah lunas"),        
        'penyerahan_id' : fields.many2one('dym.penyerahan.bpkb','Penyerahan STNK'),
        'customer_id':fields.related('name','customer_id',type='many2one',relation='res.partner',readonly=True,string='Customer'),
        'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
        'no_bpkb' : fields.related('name','no_bpkb',type="char",readonly=True,string='No BPKB'),
        'tgl_ambil_bpkb' : fields.date('Tgl Ambil BPKB'),
        'no_urut':fields.related('name','no_urut_bpkb',type='char',readonly=True,string='No Urut'),
    }

    _defaults = {
        'tgl_ambil_bpkb': fields.date.context_today,
    }
    
    _sql_constraints = [
        ('unique_name_penyerahan_id', 'unique(name,penyerahan_id)', 'Detail Engine duplicate, mohon cek kembali !'),
    ]    

    def onchange_engine(self, cr, uid, ids, name,branch_id,division,birojasa,penerima_bpkb, context=None):
        if not branch_id or not division or not birojasa or not penerima_bpkb:
            raise osv.except_osv(('Perhatian !'), ('Sebelum menambah detil transaksi,\n harap isi branch, division, peneriman STNK dan Customer STNK terlebih dahulu.'))
    
        warning = {}
        value = {}
        domain = {}

        finco_domain = [
            ('branch_id','=',branch_id),
            ('division','=',division),
        ]
        partner_id = context.get('partner_id',False)
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, [partner_id], context=context)
            if partner.finance_company:
                finco_domain += [('finco_id','in',(partner_id,False))]
                partner_cabang = context.get('partner_cabang',False)
                if partner_cabang:
                    finco_domain += [('finco_cabang','=',partner_cabang)]
            else:
                finco_domain += [('customer_id','=',partner_id)]


        if finco_domain:
            domain['name'] = finco_domain

        if name :
            lot_obj = self.pool.get('stock.production.lot')
            lot_search = lot_obj.search(cr,uid,[
                ('id','=',name)
            ])
            lot_browse = lot_obj.browse(cr,uid,lot_search)          
            if lot_browse.dealer_sale_order_id:
                obj_inv = self.pool.get('account.invoice')
                obj_ids = obj_inv.search(cr,uid,[
                    ('origin','ilike',lot_browse.dealer_sale_order_id.name),
                    ('type','=','out_invoice'),
                    ('state','not in',['paid','cancel']),
                ], limit=1)
                if obj_ids:
                    obj = obj_inv.browse(cr,uid,obj_ids)
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('Invoice \'%s\' untuk nomor engine \'%s\' belum lunas ! ') % (obj.number or obj.name,lot_browse.name)),
                    }
                    value = {
                        'name':False,
                    }
                    return {'warning':warning,'value':value}
            if lot_browse.penyerahan_bpkb_id.id != False and lot_browse.tgl_penyerahan_bpkb == False:
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No Engine \'%s\' telah diproses dengan no penyerahan BPKB \'%s\' mohon post atau cancel terlebih dahulu, atau hapus dari detail penerimaan ! ') % (lot_browse.name,lot_browse.penyerahan_bpkb_id.name)),
                }
                value = {
                    'name':False,
                }
            else:
                if lot_search :
                    value = {
                        'customer_id':lot_browse.customer_id.id,
                        'customer_stnk':lot_browse.customer_stnk.id,
                        'no_bpkb':lot_browse.no_bpkb,
                        'no_urut':lot_browse.no_urut_bpkb
                    }
        return {'warning':warning,'value':value}