import time
from datetime import datetime
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
from openerp import api

class wiz_penyerahan_stnk_line(orm.TransientModel):
    _name = 'wiz.penyerahan.stnk.line'
    _description = "penyerahan stnk Line Wizard"
        
    _columns = {
        'penyerahan_stnk_id': fields.many2one('dym.penyerahan.stnk', string='penyerahan stnk'),
        'lot_ids': fields.many2many('stock.production.lot','wiz_penyerahan_stnk_line_lot_rel','wiz_penyerahan_stnk_id','lot_id','Engine Number'),
    }

    _defaults = {
        'penyerahan_stnk_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("Data Error, please try to refresh page or contact your administrator!"))
        res = super(wiz_penyerahan_stnk_line, self).default_get(cr, uid, fields, context=context)
        return res
        
    def lot_change(self, cr, uid, ids, penyerahan_stnk_id, context=None):
        domain = {}
        penyerahan = self.pool.get('dym.penyerahan.stnk').browse(cr, uid, penyerahan_stnk_id)
        saved_lot_ids = penyerahan.penyerahan_line.mapped('name').ids
        if penyerahan.partner_id:
            domain['lot_ids'] = [('tgl_proses_birojasa','!=',False),('tgl_terima_notice','!=',False),('state_stnk','=','proses_stnk'),('branch_id','=',penyerahan.branch_id.id),('customer_id','=',penyerahan.partner_id.id),'|',('tgl_penyerahan_stnk','=',False),('tgl_penyerahan_plat','=',False),'|',('inv_pajak_progressive_id','=',False),('state_pajak_progressive','=','paid'),'|',('inv_pengurusan_stnk_bpkb_id','=',False),('state_pengurusan_stnk','=','paid'),('id','not in',saved_lot_ids)]
        elif not penyerahan.partner_id:
            domain['lot_ids'] = [('tgl_proses_birojasa','!=',False),('tgl_terima_notice','!=',False),('state_stnk','=','proses_stnk'),('branch_id','=',penyerahan.branch_id.id),'|',('tgl_penyerahan_stnk','=',False),('tgl_penyerahan_plat','=',False),'|',('inv_pajak_progressive_id','=',False),('state_pajak_progressive','=','paid'),'|',('inv_pengurusan_stnk_bpkb_id','=',False),('state_pengurusan_stnk','=','paid'),('id','not in',saved_lot_ids)]
        return {'domain':domain}

    def save_lot_ids(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for data in self.browse(cr, uid, ids, context=context):
            for lot in data.lot_ids:
                lot_change_vals = self.pool.get('dym.penyerahan.stnk.line').onchange_engine(cr, uid, ids, lot.id, data.penyerahan_stnk_id.branch_id.id, data.penyerahan_stnk_id.division, data.penyerahan_stnk_id.partner_id.id, data.penyerahan_stnk_id.penerima)
                if 'warning' in lot_change_vals and lot_change_vals['warning']:
                    raise osv.except_osv((lot_change_vals['warning']['title']), (lot_change_vals['warning']['message']))
                lot_change_vals['value']['penyerahan_id'] = data.penyerahan_stnk_id.id
                lot_change_vals['value']['name'] = lot.id
                res = {
                    'penyerahan_line': [[0, data.penyerahan_stnk_id.id, lot_change_vals['value']]]
                }
                data.penyerahan_stnk_id.write(res)
        return True

class dym_penyerahan_stnk(osv.osv):
    _name = "dym.penyerahan.stnk"
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    @api.depends('penyerahan_line.name')
    def _amount_all(self):
        for ib in self:
            amount_total = 0.0
            for line in ib.penyerahan_line:
                ib.update({
                    'total_record': len(ib.penyerahan_line),
                })

    def _cek_lengkap(self, cr, uid, ids, field_name, arg, context=None):
        res ={}
        for penyerahan in self.browse(cr, uid, ids, context=context):
            if penyerahan.penyerahan_line:
              res[penyerahan.id] ={'lengkap': 'Lengkap'}
            else:
              res[penyerahan.id] ={'lengkap': 'Belum Lengkap'}
            for line in penyerahan.penyerahan_line:
                if not line.tgl_ambil_stnk or not line.tgl_ambil_polisi or not line.tgl_ambil_notice:
                    res[penyerahan.id] ={'lengkap': 'Belum Lengkap'}
        return res

    def _get_order(self, cr, uid, ids, context=None):
        penyerahan_line_ids = self.pool.get('dym.penyerahan.stnk.line').search(cr, uid, [('name','in',ids)])
        penyerahan = self.pool.get('dym.penyerahan.stnk.line').browse(cr, uid, penyerahan_line_ids).mapped('penyerahan_id')
        return list(set(penyerahan.ids))
        
    _columns = {
        'lengkap':fields.function(_cek_lengkap,string='Kelengkapan', type='char',
            store={
                'stock.production.lot': (_get_order, ['tgl_penyerahan_stnk', 'tgl_penyerahan_plat', 'tgl_penyerahan_notice'], 10),
            },
            multi='sums', help="Kelengkapan"),
        'name': fields.char('No Reference', readonly=True),
        'branch_id': fields.many2one('dym.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Showroom')], 'Division', change_default=True, select=True),
        'penerima':fields.char('Penerima'),
        'partner_id':fields.many2one('res.partner','Customer',domain=[('customer','=',True)]),
        'keterangan':fields.char('Keterangan'),
        'tanggal':fields.date('Tanggal'),
        'penyerahan_line' : fields.one2many('dym.penyerahan.stnk.line','penyerahan_id',string="Penyerahan STNK"),  
        'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
        'engine_no': fields.related('penyerahan_line', 'name', type='char', string='No Engine'),
        'customer_stnk': fields.related('penyerahan_line', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
        'no_stnk': fields.related('penyerahan_line', 'no_stnk', type='char', string='No STNK'),
        'confirm_uid':fields.many2one('res.users',string="Posted by"),
        'confirm_date':fields.datetime('Posted on'),                      
        'total_record' : fields.integer(string='Total Engine', store=True, readonly=True, compute='_amount_all'),                    
    }
 
    _defaults = {
      'state':'draft',
      'division' : 'Unit',
      'tanggal': fields.date.context_today,
      'branch_id': _get_default_branch,

    }
    
    def onchange_partner(self,cr,uid,ids,partner):
        value = {}
        if partner :
            res_partner = self.pool.get('res.partner').search(cr,uid,[('id','=',partner)])
            res_partner_browse = self.pool.get('res.partner').browse(cr,uid,res_partner)            
            value = {'penerima':res_partner_browse.name}
        return {'value':value}    
    
    def post_penyerahan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = datetime.now()
        self.write(cr, uid, ids, {'state': 'posted','tanggal':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})        
        for x in val.penyerahan_line :
            x.write({'state':'posted'})
            lot_search = lot_pool.search(cr,uid,[
                        ('id','=',x.name.id)
                        ])
            lot_browse = lot_pool.browse(cr,uid,lot_search)   
            if not x.tgl_ambil_stnk and not x.tgl_ambil_polisi and not x.tgl_ambil_notice:
              raise osv.except_osv(('Perhatian !'), ("Mohon lengkapi data terlebih dahulu!"))
            if not lot_browse.tgl_penyerahan_stnk :
                if x.tgl_ambil_stnk :
                    lot_browse.write({
                           'tgl_penyerahan_stnk':x.tgl_ambil_stnk,
                           })                 
            if not lot_browse.tgl_penyerahan_plat :
                if x.tgl_ambil_polisi :
                    lot_browse.write({
                           'tgl_penyerahan_plat':x.tgl_ambil_polisi,
                           })
            if not lot_browse.tgl_penyerahan_notice :
                if x.tgl_ambil_notice :
                    lot_browse.write({
                           'tgl_penyerahan_notice':x.tgl_ambil_notice,
                           })
            lot_browse.write({
                     'lokasi_stnk_id':False
                     })                     
        return True
    
    def create(self, cr, uid, vals, context=None):
        # if not vals['penyerahan_line'] :
        #     raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penyerahan. Data tidak bisa di save."))
        lot_penyerahan = []
        for x in vals['penyerahan_line']:
            lot_penyerahan.append(x.pop(2))
        lot_pool = self.pool.get('stock.production.lot')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PSN', division='Unit')
        vals['tanggal'] = time.strftime('%Y-%m-%d'),

        for y in lot_penyerahan :
            id = y['name']
            engine = self.pool.get('stock.production.lot').browse(cr,uid,[id])
            if y['tgl_ambil_stnk']:       
                if not engine.no_stnk :     
                    raise osv.except_osv(('Perhatian !'), ("No STNK belum diterima, tidak bisa input tanggal ambil STNK"))
            if y['tgl_ambil_polisi']:
                if not engine.no_polisi :
                    raise osv.except_osv(('Perhatian !'), ("No Polisi belum diterima, tidak bisa input tanggal ambil Plat"))                
                
        del[vals['penyerahan_line']]        
        penyerahan_id = super(dym_penyerahan_stnk, self).create(cr, uid, vals, context=context) 

        if penyerahan_id :         
            for x in lot_penyerahan :
                lot_search = lot_pool.search(cr,uid,[('id','=',x['name'])])
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                penyerahan_pool = self.pool.get('dym.penyerahan.stnk.line')
                penyerahan_pool.create(cr, uid, {
                    'name':lot_browse.id,
                    'penyerahan_id':penyerahan_id,
                    'customer_stnk':lot_browse.customer_stnk.id,
                    'no_stnk':lot_browse.no_stnk,
                    'no_polisi':lot_browse.no_polisi,
                    'no_notice':lot_browse.no_notice,
                    'tgl_ambil_stnk':x['tgl_ambil_stnk'],
                    'tgl_ambil_polisi':x['tgl_ambil_polisi'],
                    'tgl_ambil_notice':x['tgl_ambil_notice']
                })
                if not lot_browse.tgl_penyerahan_stnk :
                    if x['tgl_ambil_stnk'] :
                        lot_browse.write({'penyerahan_stnk_id':penyerahan_id,}) 
                if not lot_browse.tgl_penyerahan_plat :
                    if x['tgl_ambil_polisi'] :
                        lot_browse.write({'penyerahan_polisi_id':penyerahan_id,})
                if not lot_browse.tgl_penyerahan_notice :
                    if x['tgl_ambil_notice'] :
                        lot_browse.write({'penyerahan_notice_id':penyerahan_id,})                        
        else :
            return False
        return penyerahan_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        vals.get('penyerahan_line',[]).sort(reverse=True)            
        val = self.browse(cr,uid,ids)    
        penyerahan_pool = self.pool.get('dym.penyerahan.stnk.line')
        lot_pool = self.pool.get('stock.production.lot')
        lot = vals.get('penyerahan_line', False)
        if lot :
            del[vals['penyerahan_line']]
            for x,item in enumerate(lot) :
                lot_id = item[1]

                if item[0] == 2 :
                    if val.state != 'draft':
                        raise osv.except_osv(('Perhatian !'), ("Tidak bisa menghapus nomor engine!"))
                    id_lot = item[2]
                    search = penyerahan_pool.search(cr,uid,[
                                                            ('id','=',lot_id)
                                                            ])
                    if not search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar"))
                    browse = penyerahan_pool.browse(cr,uid,search)
                     
                    lot_search = lot_pool.search(cr,uid,[
                       ('id','=',browse.name.id)
                       ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar"))
                    lot_browse = lot_pool.browse(cr,uid,lot_search)

                    lot_browse.write({
                                       'penyerahan_stnk_id':False,
                                       'penyerahan_polisi_id':False,
                                       'penyerahan_notice_id':False,
                                     })
                    penyerahan_pool.unlink(cr,uid,lot_id, context=context)
                    
                elif item[0] == 0 :
                    if val.state != 'draft':
                        raise osv.except_osv(('Perhatian !'), ("Tidak bisa menambah nomor engine!"))
                    values = item[2]
                    lot_search = lot_pool.search(cr,uid,[
                                                        ('id','=',values['name'])
                                                        ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
            
                
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    
                    penyerahan_pool.create(cr, uid, {
                                    'name':lot_browse.id,
                                    'penyerahan_id':val.id,
                                    'customer_stnk':lot_browse.customer_stnk.id,
                                    'no_stnk':lot_browse.no_stnk,
                                    'no_polisi':lot_browse.no_polisi,
                                    'no_notice':lot_browse.no_notice,
                                    'tgl_ambil_stnk':values['tgl_ambil_stnk'],
                                    'tgl_ambil_polisi':values['tgl_ambil_polisi'],
                                    'tgl_ambil_notice':values['tgl_ambil_notice']
                                    })
                     
                    if values['tgl_ambil_stnk'] :
                        lot_browse.write({
                               'penyerahan_stnk_id':val.id,  
                                                           }) 
                    if values['tgl_ambil_polisi'] :
                        lot_browse.write({
                               'penyerahan_polisi_id':val.id,
                                          })
                    if values['tgl_ambil_notice'] :
                        lot_browse.write({
                               'penyerahan_notice_id':val.id,
                                          })                        
                elif item[0] == 1 :
                    data = item[2]
                    penyerahan_search = penyerahan_pool.search(cr,uid,[
                                                                       ('id','=',lot_id)
                                                                       ])
                    penyerahan_browse = penyerahan_pool.browse(cr,uid,penyerahan_search)
                    if penyerahan_search :
                        if 'tgl_ambil_stnk' in data or 'no_stnk' in data:
                            penyerahan_browse.write({
                                                     'tgl_ambil_stnk': data['tgl_ambil_stnk'] if 'tgl_ambil_stnk' in data else penyerahan_browse.tgl_ambil_stnk,
                                                     'no_stnk':data['no_stnk'] if 'no_stnk' in data else penyerahan_browse.no_stnk,
                                                     })
                            if ('tgl_ambil_stnk' in data and data['tgl_ambil_stnk']) or ('no_stnk' in data and data['no_stnk']):
                                penyerahan_browse.name.write({
                                            'penyerahan_stnk_id':penyerahan_browse.penyerahan_id.id,
                                            'tgl_ambil_stnk':penyerahan_browse.tgl_ambil_stnk,
                                            'no_stnk':penyerahan_browse.no_stnk,
                                              })                            
                            else:
                                penyerahan_browse.name.write({
                                   'penyerahan_stnk_id':False,
                                   'tgl_ambil_stnk':False,
                                   'no_stnk':False,
                                   })                     
                        elif 'tgl_ambil_polisi' in data or 'no_polisi' in data:
                            penyerahan_browse.write({
                                                     'tgl_ambil_polisi': data['tgl_ambil_polisi'] if 'tgl_ambil_polisi' in data else penyerahan_browse.tgl_ambil_polisi,
                                                     'no_polisi':data['no_polisi'] if 'no_polisi' in data else penyerahan_browse.no_polisi,
                                                     })
                            if ('tgl_ambil_polisi' in data and data['tgl_ambil_polisi']) or ('no_polisi' in data and data['no_polisi']):
                                penyerahan_browse.name.write({
                                            'penyerahan_polisi_id':penyerahan_browse.penyerahan_id.id,
                                            'tgl_ambil_polisi':penyerahan_browse.tgl_ambil_polisi,
                                            'no_polisi':penyerahan_browse.no_polisi,
                                              })                            
                            else:
                                penyerahan_browse.name.write({
                                   'penyerahan_polisi_id':False,
                                   'tgl_ambil_polisi':False,
                                   'no_polisi':False,
                                   })             
                        elif 'tgl_ambil_notice' in data or 'no_notice' in data :
                            penyerahan_browse.write({
                                                     'tgl_ambil_notice': data['tgl_ambil_notice'] if 'tgl_ambil_notice' in data else penyerahan_browse.tgl_ambil_notice,
                                                     'no_notice':data['no_notice'] if 'no_notice' in data else penyerahan_browse.no_notice,
                                                     })
                            if ('tgl_ambil_notice' in data and data['tgl_ambil_notice']) or ('no_notice' in data and data['no_notice']):
                                penyerahan_browse.name.write({
                                            'penyerahan_notice_id':penyerahan_browse.penyerahan_id.id,
                                            'tgl_ambil_notice':penyerahan_browse.tgl_ambil_notice,
                                            'no_notice':penyerahan_browse.no_notice,
                                              })                            
                            else:
                                penyerahan_browse.name.write({
                                   'penyerahan_notice_id':False,
                                   'tgl_ambil_notice':False,
                                   'no_notice':False,
                                   })                              
                                                        
        return super(dym_penyerahan_stnk, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Penyerahan STNK/No Polisi sudah di validate ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')

        for x in self.browse(cr, uid, ids, context=context):
            for y in x.penyerahan_line :
                lot_search = lot_pool.search(cr,uid,[
                                                     ('id','=',y.name.id)
                                                     ])
                if lot_search :
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    if y.no_stnk :
                        lot_browse.write({
                                          'penyerahan_stnk_id':False,
                                          'tgl_penyerahan_stnk':False,})     
                    if y.no_polisi :
                        lot_browse.write({
                                          'penyerahan_polisi_id':False,
                                          'tgl_penyerahan_plat':False})                        

        return super(dym_penyerahan_stnk, self).unlink(cr, uid, ids, context=context)    
    
      
class dym_penyerahan_stnk_line(osv.osv):
    _name = "dym.penyerahan.stnk.line"

    _columns = {
        'name' : fields.many2one('stock.production.lot','No Engine',change_default=True, help="AR tagihan harus sudah lunas"),                
        'penyerahan_id' : fields.many2one('dym.penyerahan.stnk','Penyerahan STNK'),
        'customer_id':fields.related('name','customer_id',type='many2one',relation='res.partner',readonly=True,string='Customer'),
        'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
        'no_stnk' : fields.related('name','no_stnk',type="char",readonly=True,string='No STNK'),
        'no_polisi' : fields.related('name','no_polisi',type="char",readonly=True,string='No Polisi'),
        'tgl_ambil_stnk' : fields.date('Tgl Ambil STNK'),
        'tgl_ambil_polisi' : fields.date('Tgl Ambil Plat No Polisi'),
        'no_notice' : fields.related('name','no_notice',type="char",readonly=True,string='No Notice'),
        'tgl_ambil_notice' : fields.date('Tgl Ambil Notice'),
        'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
    }

    _defaults = {
        'state':'draft',
    }

    _sql_constraints = [
        ('unique_name_penyerahan_id', 'unique(name,penyerahan_id)', 'Detail Engine duplicate, mohon cek kembali !'),
    ]

    def onchenge_tgl_ambil_polisi(self, cr, uid, ids, name, tgl_ambil_polisi, tgl_ambil_stnk, context=None):
        res = {}
        penerima_stnk_id = self.pool.get('dym.penerimaan.stnk.line').search(cr, uid, [('name','=',name)])
        penerima_stnk = self.pool.get('dym.penerimaan.stnk.line').browse(cr, uid, penerima_stnk_id, context=context)

        if tgl_ambil_stnk and not penerima_stnk.tgl_terima_stnk:
            return {
                'warning': {
                    'title': _('Warning'),'message': _('STNK belum diterima.')
                },
                'value': {
                    'tgl_ambil_stnk': False,
                }
            }

        if tgl_ambil_polisi and not penerima_stnk.tgl_terima_no_polisi:
            return {
                'warning': {
                    'title': _('Warning'),'message': _('Plat Nomor Polisi belum diterima.')
                },
                'value': {
                    'tgl_ambil_polisi': False,
                }
            }
    
    def onchange_engine(self, cr, uid, ids, name, branch_id, division, customer, penerima_stnk):
        if not branch_id or not division or not penerima_stnk:
            raise osv.except_osv(('Perhatian !'), ('Sebelum menambah detil transaksi,\n harap isi branch, division, peneriman STNK terlebih dahulu.'))
    
        value = {}
        domain = {}
        result = {}
        
        if customer :
            domain['name'] ="[('tgl_proses_birojasa','!=',False),('tgl_terima_notice','!=',False),('state_stnk','=','proses_stnk'),('branch_id','=',parent.branch_id),('customer_id','=',parent.partner_id),'|',('tgl_penyerahan_stnk','=',False),('tgl_penyerahan_plat','=',False),'|',('inv_pajak_progressive_id','=',False),('state_pajak_progressive','=','paid'),'|',('inv_pengurusan_stnk_bpkb_id','=',False),('state_pengurusan_stnk','=','paid')]"
        elif not customer :
            domain['name'] ="[('tgl_proses_birojasa','!=',False),('tgl_terima_notice','!=',False),('state_stnk','=','proses_stnk'),('branch_id','=',parent.branch_id),'|',('tgl_penyerahan_stnk','=',False),('tgl_penyerahan_plat','=',False),'|',('inv_pajak_progressive_id','=',False),('state_pajak_progressive','=','paid'),'|',('inv_pengurusan_stnk_bpkb_id','=',False),('state_pengurusan_stnk','=','paid')]"
                
        if name :
            lot_obj = self.pool.get('stock.production.lot')
            lot_search = lot_obj.search(cr,uid,[('id','=',name)])
            if lot_search :
                lot_browse = lot_obj.browse(cr,uid,lot_search)          
                value = {
                    'customer_id':lot_browse.customer_id.id,
                    'customer_stnk':lot_browse.customer_stnk.id,
                    'no_stnk':lot_browse.no_stnk,
                    'no_polisi':lot_browse.no_polisi,
                    'tgl_ambil_stnk':lot_browse.tgl_penyerahan_stnk,
                    'tgl_ambil_polisi':lot_browse.tgl_penyerahan_plat,
                    'no_notice':lot_browse.no_notice,
                    'tgl_ambil_notice':lot_browse.tgl_penyerahan_notice,
                } 

        return {
            'domain':domain,
            'value':value
        }