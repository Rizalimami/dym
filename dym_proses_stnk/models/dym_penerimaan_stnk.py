import time
from datetime import datetime
from openerp.osv import fields, osv, orm
from openerp import api
from string import whitespace
import re

class wiz_penerimaan_stnk_line(orm.TransientModel):
    _name = 'wiz.penerimaan.stnk.line'
    _description = "Penerimaan STNK Line Wizard"
        
    _columns = {
        'penerimaan_stnk_id': fields.many2one('dym.penerimaan.stnk', string='Penerimaan STNK'),
        'lot_ids': fields.many2many('stock.production.lot','wiz_penerimaan_stnk_line_lot_rel','wiz_penerimaan_stnk_id','lot_id','Engine Number'),
    }

    _defaults = {
        'penerimaan_stnk_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("Data Error, please try to refresh page or contact your administrator!"))
        res = super(wiz_penerimaan_stnk_line, self).default_get(cr, uid, fields, context=context)
        return res

    def lot_change(self, cr, uid, ids, penerimaan_stnk_id, context=None):
        domain = {}
        penerimaan = self.pool.get('dym.penerimaan.stnk').browse(cr, uid, penerimaan_stnk_id)
        saved_lot_ids = penerimaan.penerimaan_line.mapped('name').ids
        domain['lot_ids'] = [('tgl_proses_stnk','!=',False),('state_stnk','=','proses_stnk'),('branch_id','=',penerimaan.branch_id.id),('biro_jasa_id','=',penerimaan.partner_id.id),'|',('tgl_terima_stnk','=',False),'|',('tgl_terima_no_polisi','=',False),('tgl_terima_notice','=',False),('id','not in',saved_lot_ids)]
        return {'domain':domain}

    def save_lot_ids(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for data in self.browse(cr, uid, ids, context=context):
            for lot in data.lot_ids:
                lot_change_vals = self.pool.get('dym.penerimaan.stnk.line').onchange_engine(cr, uid, ids, lot.id, data.penerimaan_stnk_id.branch_id.id, data.penerimaan_stnk_id.division)
                if 'warning' in lot_change_vals and lot_change_vals['warning']:
                    raise osv.except_osv((lot_change_vals['warning']['title']), (lot_change_vals['warning']['message']))
                lot_change_vals['value']['penerimaan_notice_id'] = data.penerimaan_stnk_id.id
                lot_change_vals['value']['name'] = lot.id
                res = {
                    'penerimaan_line': [[0, data.penerimaan_stnk_id.id, lot_change_vals['value']]]
                }
                data.penerimaan_stnk_id.write(res)
        return True

class dym_penerimaan_stnk(osv.osv):
    _name = "dym.penerimaan.stnk"

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    def _cek_lengkap(self, cr, uid, ids, field_name, arg, context=None):
        res ={}
        for penerimaan in self.browse(cr, uid, ids, context=context):
            if penerimaan.penerimaan_line:
              res[penerimaan.id] ={'lengkap': 'Lengkap'}
            else:
              res[penerimaan.id] ={'lengkap': 'Belum Lengkap'}
            for line in penerimaan.penerimaan_line:
                conditions = [
                  line.tgl_notice,
                  line.no_notice,
                  line.tgl_stnk,
                  line.no_stnk,
                  line.no_polisi,
                  line.tgl_terima_notice,
                  line.tgl_terima_no_polisi,
                  line.tgl_terima_stnk
                ]
                if not all(conditions):
                  res[penerimaan.id] ={'lengkap': 'Belum Lengkap'}
                # if not line.no_notice or not line.no_polisi or not line.no_stnk:
        return res

    @api.depends('penerimaan_line.name')
    def _amount_all(self):
        for ib in self:
            amount_total = 0.0
            for line in ib.penerimaan_line:
                ib.update({
                    'total_record': len(ib.penerimaan_line),
                })

    def _get_order(self, cr, uid, ids, context=None):
        penerimaan_line_ids = self.pool.get('dym.penerimaan.stnk.line').search(cr, uid, [('name','in',ids)])
        penerimaan = self.pool.get('dym.penerimaan.stnk.line').browse(cr, uid, penerimaan_line_ids).mapped('penerimaan_notice_id')
        return list(set(penerimaan.ids))

    _columns = {
        'lengkap':fields.function(_cek_lengkap,string='Kelengkapan', type='char',
            store={
                'stock.production.lot': (_get_order, ['no_stnk', 'no_polisi', 'no_notice'], 10),
            },
             multi='sums', help="Kelengkapan"),
        'branch_id': fields.many2one('dym.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Showroom')], 'Division', change_default=True, select=True),
        'name': fields.char('No Reference', readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
        'penerimaan_line': fields.one2many('dym.penerimaan.stnk.line','penerimaan_notice_id',string="Table Penerimaan STNk"), 
        'partner_id':fields.many2one('res.partner','Biro Jasa',domain=[('biro_jasa','=',True)]),
        'tgl_terima' : fields.date('Tanggal'),
        'lokasi_stnk_id' : fields.many2one('dym.lokasi.stnk',string="Lokasi",domain="[('branch_id','=',branch_id),('type','=','internal')]"),
        'engine_no': fields.related('penerimaan_line', 'name', type='char', string='No Engine'),
        'customer_stnk': fields.related('penerimaan_line', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
        'confirm_uid':fields.many2one('res.users',string="Posted by"),
        'confirm_date':fields.datetime('Posted on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),         
        'total_record' : fields.integer(string='Total Engine', store=True, readonly=True, compute='_amount_all'),
    }
    _defaults = {
        'name': '/',
        'state':'draft',
        'division' : 'Unit',
        'tgl_terima': fields.date.context_today,
        'branch_id': _get_default_branch,
    }   

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
     
    def cancel_penerimaan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        for x in val.penerimaan_line :
            x.write({'state':'cancel'})
            lot_search = lot_pool.search(cr,uid,[
                ('branch_id','=',val.branch_id.id),
                ('biro_jasa_id','=',val.partner_id.id),
                ('id','=',x.name.id),
                ('lokasi_stnk_id','=',val.lokasi_stnk_id.id),
            ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                if lot_browse.penerimaan_notice_id.id == val.id :
                    lot_browse.write({
                        'penerimaan_notice_id':False,
                        'no_notice':False,
                        'tgl_notice':False,
                        'tgl_terima_notice':False
                    })
                if lot_browse.penerimaan_stnk_id.id == val.id :
                    lot_browse.write({
                        'penerimaan_stnk_id':False,
                        'no_stnk':False,
                        'tgl_stnk':False,
                        'tgl_terima_stnk':False
                    })  
                if lot_browse.penerimaan_no_polisi_id.id == val.id  :            
                    lot_browse.write({
                        'penerimaan_no_polisi_id':False,
                        'no_polisi':False,
                        'tgl_terima_no_polisi':False
                    })
                lot_browse.write({
                    'lokasi_stnk_id':False,
                    'penerimaan_stnk_line_id': False
                })
            
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        return True
    
    def post_penerimaan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = datetime.today()
        self.write(cr, uid, ids, {'state': 'posted','tgl_terima':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})  
        for x in val.penerimaan_line :
            x.write({'state':'posted'})
            lot_search = lot_pool.search(cr,uid,[
                ('id','=',x.name.id)
            ])
            lot_browse = lot_pool.browse(cr,uid,lot_search)
            if x.no_notice :
                lot_browse.write({
                    'tgl_notice': x.tgl_notice,
                    'no_notice':x.no_notice,
                    'tgl_terima_notice':x.tgl_terima_notice,
                })   
            else:
                raise osv.except_osv(('Perhatian !'), ("Nomor notice harus diisi!"))
            if x.no_stnk :
                lot_browse.write({
                    'tgl_stnk':x.tgl_stnk,
                    'no_stnk':x.no_stnk,
                    'tgl_terima_stnk':x.tgl_terima_stnk,
                })
            if x.no_polisi :
                lot_browse.write({
                    'no_polisi':x.no_polisi,
                    'tgl_terima_no_polisi':x.tgl_terima_no_polisi,
                })
            lot_browse.write({'lokasi_stnk_id':val.lokasi_stnk_id.id})

        if val.name == '/':
            values = {
                'name': self.pool.get('ir.sequence').get_per_branch(cr, uid, val.branch_id.id, 'PES', division='Unit')
            }
            self.write(cr, uid, ids, values, context=context)
        return True
    
    def create(self, cr, uid, vals, context=None):
        # if not vals['penerimaan_line'] :
        #     raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penerimaan. Data tidak bisa di save."))
        lot_penerimaan = []
        for x in vals['penerimaan_line']:
            lot_penerimaan.append(x.pop(2))
        lot_pool = self.pool.get('stock.production.lot')
        # vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PES', division='Unit')
        vals['tgl_terima'] = time.strftime('%Y-%m-%d'),
        del[vals['penerimaan_line']]
        penerimaan_id = super(dym_penerimaan_stnk, self).create(cr, uid, vals, context=context) 
        if penerimaan_id :         
            for x in lot_penerimaan :
                lot_search = lot_pool.search(cr,uid,[
                            ('id','=',x['name'])
                            ])
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                penerimaan_pool = self.pool.get('dym.penerimaan.stnk.line')
                if 'no_notice' in x:
                    no_notice = x['no_notice']
                    tgl_notice = x['tgl_notice']
                elif lot_browse.no_notice_copy:
                    no_notice = lot_browse.no_notice_copy
                    tgl_notice = lot_browse.tgl_notice_copy
                else:
                    no_notice = lot_browse.no_notice
                    tgl_notice = lot_browse.tgl_notice
                penerimaan_pool.create(cr, uid, {
                    'name':lot_browse.id,
                    'penerimaan_notice_id':penerimaan_id,
                    'customer_id':lot_browse.customer_id.id,
                    'customer_stnk':lot_browse.customer_stnk.id,
                    'tgl_notice':tgl_notice,
                    'no_notice':no_notice,
                    'tgl_stnk':x['tgl_stnk'],
                    'no_stnk':x['no_stnk'],
                    'no_polisi':x['no_polisi'],
                    'lokasi_stnk_id':vals['lokasi_stnk_id'],
                    'tgl_terima_notice':x['tgl_terima_notice'],
                    'tgl_terima_stnk':x['tgl_terima_stnk'],
                    'tgl_terima_no_polisi':x['tgl_terima_no_polisi'],
                })
                if not lot_browse.no_notice :
                    if no_notice:
                        lot_browse.write({
                               'penerimaan_notice_id':penerimaan_id,
                               })   
                
                if not lot_browse.no_stnk :
                    if x['no_stnk'] :
                        lot_browse.write({
                               'penerimaan_stnk_id':penerimaan_id,
                               }) 
                
                if not lot_browse.no_polisi :
                    if x['no_polisi'] :
                        lot_browse.write({
                               'penerimaan_no_polisi_id':penerimaan_id,
                                          })
                           
        else :
            return False
        return penerimaan_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        val = self.browse(cr,uid,ids)    
        penerimaan_pool = self.pool.get('dym.penerimaan.stnk.line')
        lot_pool = self.pool.get('stock.production.lot')
        vals.get('penerimaan_line',[]).sort(reverse=True)
        lot = vals.get('penerimaan_line', False)
        if lot :
            del[vals['penerimaan_line']]
            for x,item in enumerate(lot) :
                lot_id = item[1]
                if item[0] == 2 :
                    if val.state != 'draft':
                        raise osv.except_osv(('Perhatian !'), ("Tidak bisa menghapus nomor engine!"))
                    id_lot = item[2]
                    search = penerimaan_pool.search(cr,uid,[
                                                            ('id','=',lot_id)
                                                            ])
                    if not search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar"))
                    browse = penerimaan_pool.browse(cr,uid,search)
                     
                    lot_search = lot_pool.search(cr,uid,[
                       ('id','=',browse.name.id)
                       ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar"))
                    lot_browse = lot_pool.browse(cr,uid,lot_search)

                    lot_browse.write({
                                       'penerimaan_notice_id':False,
                                       'penerimaan_stnk_id':False,
                                       'penerimaan_no_polisi_id':False,
                                       'tgl_notice': False,
                                       'no_notice':False,
                                       'tgl_stnk':False,
                                       'no_stnk':False,
                                       'no_polisi':False,
                                       'state_stnk':'proses_stnk',
                                       'tgl_terima_notice':False,
                                       'tgl_terima_stnk':False,
                                       'tgl_terima_no_polisi':False,
                                       'lokasi_stnk_id':False,
                                     })
                    penerimaan_pool.unlink(cr,uid,lot_id, context=context)
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
                    
                    if 'no_notice' in values:
                        no_notice = values['no_notice']
                        tgl_notice = values['tgl_notice']
                    elif lot_browse.no_notice_copy:
                        no_notice = lot_browse.no_notice_copy
                        tgl_notice = lot_browse.tgl_notice_copy
                    else:
                        no_notice = lot_browse.no_notice
                        tgl_notice = lot_browse.tgl_notice

                    penerimaan_pool.create(cr, uid, {
                                'name':lot_browse.id,
                                'penerimaan_notice_id':val.id,
                                'customer_id': lot_browse.customer_id.id,
                                'customer_stnk':lot_browse.customer_stnk.id,
                                'tgl_notice':tgl_notice,
                                'no_notice':no_notice,
                                'tgl_stnk':values['tgl_stnk'],
                                'no_stnk':values['no_stnk'],
                                'no_polisi':values['no_polisi'],
                                'tgl_terima_notice':values['tgl_terima_notice'],
                                'tgl_terima_stnk':values['tgl_terima_stnk'],
                                'tgl_terima_no_polisi':values['tgl_terima_no_polisi'],
                                })

                    if no_notice :
                        lot_browse.write({
                               'penerimaan_notice_id':val.id,
                               })   
                    if values['no_stnk'] :
                        lot_browse.write({
                               'penerimaan_stnk_id':val.id,  
                                                           }) 
                    if values['no_polisi'] :
                        lot_browse.write({
                               'penerimaan_no_polisi_id':val.id,
                                          })
                elif item[0] == 1 :
                    data = item[2]
                    penerimaan_search = penerimaan_pool.search(cr,uid,[
                                                                       ('id','=',lot_id)
                                                                       ])
                    penerimaan_browse = penerimaan_pool.browse(cr,uid,penerimaan_search)
                    if penerimaan_search :
                        if 'no_polisi' in data or 'tgl_terima_no_polisi' in data:
                            penerimaan_browse.write({
                                                     'tgl_terima_no_polisi': data['tgl_terima_no_polisi'] if 'tgl_terima_no_polisi' in data else penerimaan_browse.tgl_terima_no_polisi,
                                                     'no_polisi':data['no_polisi'] if 'no_polisi' in data else penerimaan_browse.no_polisi,
                                                     })
                            if ('no_polisi' in data and data['no_polisi']) or ('tgl_terima_no_polisi' in data and data['tgl_terima_no_polisi']):
                                penerimaan_browse.name.write({
                                    'penerimaan_no_polisi_id':penerimaan_browse.penerimaan_notice_id.id,
                                    'no_polisi':penerimaan_browse.no_polisi,
                                    'tgl_terima_no_polisi':penerimaan_browse.tgl_terima_no_polisi,
                                })
                            else:
                                penerimaan_browse.name.write({
                                    'penerimaan_no_polisi_id':False,
                                    'no_polisi':'',
                                    'tgl_terima_no_polisi':False,
                                })                         
                        if 'no_stnk' in data  or 'tgl_stnk' in data or 'tgl_terima_stnk' in data:
                            penerimaan_browse.write({
                                                     'tgl_stnk':data['tgl_stnk'] if 'tgl_stnk' in data else penerimaan_browse.tgl_stnk,
                                                     'no_stnk':data['no_stnk'] if 'no_stnk' in data else penerimaan_browse.no_stnk,
                                                     'tgl_terima_stnk':data['tgl_terima_stnk'] if 'tgl_terima_stnk' in data else penerimaan_browse.tgl_terima_stnk,
                                                     })
                            if ('no_stnk' in data and data['no_stnk']) or ('tgl_stnk' in data and data['tgl_stnk']) or ('tgl_terima_stnk' in data and data['tgl_terima_stnk']):
                                penerimaan_browse.name.write({
                                    'penerimaan_stnk_id':penerimaan_browse.penerimaan_notice_id.id,  
                                    'no_stnk':penerimaan_browse.no_stnk,
                                    'tgl_stnk':penerimaan_browse.tgl_stnk,
                                    'tgl_terima_stnk':penerimaan_browse.tgl_terima_stnk,
                                })                             
                            else:
                                penerimaan_browse.name.write({
                                    'penerimaan_stnk_id':False,
                                    'no_stnk':'',
                                    'tgl_stnk':False,
                                    'tgl_terima_stnk':False,
                                })                         
                        if 'no_notice' in data or 'tgl_notice' in data or 'tgl_terima_notice' in data:
                            penerimaan_browse.write({
                                                     'tgl_notice':data['tgl_notice'] if 'tgl_notice' in data else penerimaan_browse.tgl_notice,
                                                     'no_notice':data['no_notice'] if 'no_notice' in data else penerimaan_browse.no_notice,
                                                     'tgl_terima_notice':data['tgl_terima_notice'] if 'tgl_terima_notice' in data else penerimaan_browse.tgl_terima_notice,
                                                     })
                            if ('no_notice' in data and data['no_notice']) or ('tgl_notice' in data and data['tgl_notice'])  or ('tgl_terima_notice' in data and data['tgl_terima_notice']):
                                penerimaan_browse.name.write({
                                    'penerimaan_notice_id':penerimaan_browse.penerimaan_notice_id.id,
                                    'no_notice':penerimaan_browse.no_notice,
                                    'tgl_notice':penerimaan_browse.tgl_notice,
                                    'tgl_terima_notice':penerimaan_browse.tgl_terima_notice,
                                })                                                           
                            else:
                                penerimaan_browse.name.write({
                                    'penerimaan_notice_id':False,
                                    'no_notice':'',
                                    'tgl_notice':False,
                                    'tgl_terima_notice':False,
                                })                                                           
        return super(dym_penerimaan_stnk, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Penerimaan Faktur sudah di validate ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')

        for x in self.browse(cr, uid, ids, context=context):
            for y in x.penerimaan_line :
                lot_search = lot_pool.search(cr,uid,[
                                                     ('id','=',y.name.id)
                                                     ])
                if lot_search :
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    if y.no_notice :
                        lot_browse.write({                 
                                          'no_notice':False,
                                          'tgl_notice':False,
                                          'tgl_terima_notice':False})
                    if y.no_stnk :
                        lot_browse.write({
                                          'no_stnk':False,
                                          'tgl_stnk':False,
                                          'tgl_terima_stnk':False})     
                    if y.no_polisi :
                        lot_browse.write({
                                          'no_polisi':False,
                                          'tgl_terima_no_polisi':False})                        
                    lot_browse.write({
                                      'lokasi_stnk_id':False,
                                      })
        return super(dym_penerimaan_stnk, self).unlink(cr, uid, ids, context=context)

        
class dym_penerimaan_stnk_line(osv.osv):
    _name = "dym.penerimaan.stnk.line"


    # 'name' : fields.many2one('stock.production.lot','No Engine',domain="[\
    #     ('tgl_proses_stnk','!=',False),\
    #     ('state_stnk','=','proses_stnk'),\
    #     ('branch_id','=',parent.branch_id),\
    #     ('biro_jasa_id','=',parent.partner_id),\
    #     '|',\
    #     ('tgl_terima_stnk','=',False),\
    #     '|',\
    #     ('tgl_terima_no_polisi','=',False),\
    #     ('tgl_terima_notice','=',False)\
    #     ]",change_default=True,),


    _columns = {
        'name' : fields.many2one('stock.production.lot','No Engine',domain="[\
            ('penerimaan_stnk_line_id','=',False),\
            ('tgl_proses_stnk','!=',False),\
            ('state_stnk','=','proses_stnk'),\
            ('branch_id','=',parent.branch_id),\
            ('biro_jasa_id','=',parent.partner_id),\
            '|',\
            ('tgl_terima_stnk','=',False),\
            '|',\
            ('tgl_terima_no_polisi','=',False),\
            ('tgl_terima_notice','=',False)\
            ]",change_default=True),
        'penerimaan_notice_id' : fields.many2one('dym.penerimaan.stnk','Penerimaan Notice'),
        'customer_id': fields.related('name', 'customer_id', type='many2one', relation='res.partner', string='Customer', readonly=True),
        'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
        'tgl_notice' : fields.date('Tgl JTP Notice'),
        'no_notice' : fields.char('No Notice'),
        'tgl_stnk' : fields.date('Tgl JTP STNK'),
        'no_stnk' : fields.char('No STNK'),
        'no_polisi' : fields.char('No Polisi'),
        'no_notice_rel':fields.related('name','no_notice',type='char',readonly=True,string='No Notice REL'),
        'tgl_notice_rel':fields.related('name','tgl_notice',type='date',readonly=True,string='Tgl JTP Notice REL'),
        'tgl_terima_notice_rel':fields.related('name','tgl_terima_notice',type='date',readonly=True,string='Tgl Terima Notice REL'),
        'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
        'tgl_terima_notice' : fields.date('Tgl Terima Notice'),
        'tgl_terima_no_polisi' : fields.date('Tgl Terima Plat No Polisi'),
        'tgl_terima_stnk' : fields.date('Tgl Terima STNK'),
    }

    _defaults = {
        'state':'draft',
    }   

    _sql_constraints = [
        ('unique_name_penerimaan_notice_id', 'unique(name,penerimaan_notice_id)', 'Detail Engine duplicate, mohon cek kembali !'),
    ]    

    def create(self, cr, uid, vals, context=None):
        spl_obj = self.pool.get('stock.production.lot')
        penerimaan_stnk_line_id = super(dym_penerimaan_stnk_line, self).create(cr, uid, vals, context=context)

        lot_id = vals.get('name',False)
        if lot_id:
            spl_obj.write(cr, uid, [lot_id], {'penerimaan_stnk_line_id': penerimaan_stnk_line_id}, context=context)
        return penerimaan_stnk_line_id

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.name:
                lot_obj = self.pool.get('stock.production.lot')
                lot_search_id = lot_obj.search(cr,uid,[('id','=',item.name.id)])
                if lot_search_id:
                    lot_lot_it = lot_obj.write(cr,uid,lot_search_id,{'penerimaan_stnk_line_id':item.id},context=context)
        return super(dym_penerimaan_stnk_line, self).unlink(cr, uid, ids, context=context)

    def onchange_no_polisi(self,cr,uid,ids,no_polisi,context=None):
        warning = {}
        value = {}
        result = {}
        if no_polisi:
            formatted_no_polisi = ''
            no_polisi_normalize = no_polisi.replace(' ', '').upper()
            splitted_no_polisi = re.findall(r'[A-Za-z]+|\d+', no_polisi_normalize)
            if len(splitted_no_polisi) == 3:
              if splitted_no_polisi[0].isalpha() == True and splitted_no_polisi[1].isdigit() == True and splitted_no_polisi[2].isalpha() == True:
                for word in splitted_no_polisi:
                  formatted_no_polisi += word + ' '
                formatted_no_polisi = formatted_no_polisi[:-1]
                return {'value':{'no_polisi':formatted_no_polisi}}              
            warning = {
                'title': ('Perhatian !'),
                'message': (('Format nomor polisi salah, mohon isi nomor polisi dengan format yang benar! (ex. A 1234 BB)')),
            }
            value['no_polisi'] = self.browse(cr, uid, ids).no_polisi
            result['warning'] = warning
            result['value'] = value
            return result

    def onchange_no_notice(self,cr,uid,ids,no_notice,context=None):
        if no_notice :
            no_notice = no_notice.replace(' ', '').upper()
            return {'value' : {'no_notice':no_notice}}
            
    def onchange_no_stnk(self,cr,uid,ids,no_stnk,context=None):
        if no_stnk :
            no_stnk = no_stnk.replace(' ', '').upper().strip()
            return {'value' : {'no_stnk':no_stnk}}
            
    def onchange_engine(self, cr, uid, ids, name,branch_id,division,context=None):
        if not branch_id or not division:
            raise osv.except_osv(('No Branch Defined!'), ('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
       
        result = {}
        warning = {}
        value = {}
        val = self.browse(cr,uid,ids)
        lot_obj = self.pool.get('stock.production.lot')
        lot_search = lot_obj.search(cr,uid,[('id','=',name)])
        lot_browse = lot_obj.browse(cr,uid,lot_search)
        
        if name : 
            if lot_browse.penerimaan_notice_id.id != False and lot_browse.tgl_notice == False:
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No Engine \'%s\' telah diproses dengan no penerimaan \'%s\' mohon post atau cancel terlebih dahulu, atau hapus dari detail penerimaan ! ') % (lot_browse.name,lot_browse.penerimaan_notice_id.name)),
                }
                value = {
                    'name':False,
                }
                    
            elif lot_browse.penerimaan_stnk_id.id != False and lot_browse.tgl_stnk == False :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No STNK Engine \'%s\' telah diproses dengan no penerimaan \'%s\' mohon post atau cancel terlebih dahulu, atau hapus dari detail penerimaan ! ') % (lot_browse.name,lot_browse.penerimaan_stnk_id.name)),
                }
                value = {
                    'name':False,
                }  
            elif lot_browse.penerimaan_no_polisi_id.id != False and lot_browse.tgl_terima_no_polisi == False :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No Polisi Engine \'%s\' telah diproses dengan no penerimaan \'%s\' mohon post atau cancel terlebih dahulu, atau hapus dari detail penerimaan ! ') % (lot_browse.name,lot_browse.penerimaan_no_polisi_id.name)),
                }
                value = {
                    'name':False,
                } 
   
            if not warning :
                if lot_browse.no_notice_copy == False :
                    value = {
                        'customer_id': lot_browse.customer_id.id,
                        'customer_stnk':lot_browse.customer_stnk.id,
                        'tgl_notice':lot_browse.tgl_notice,
                        'no_notice':lot_browse.no_notice,
                        'tgl_stnk':lot_browse.tgl_stnk,
                        'no_stnk':lot_browse.no_stnk,
                        'no_polisi':lot_browse.no_polisi,
                        'tgl_notice_rel':lot_browse.tgl_notice,
                        'no_notice_rel':lot_browse.no_notice,
                        'tgl_terima_notice_rel':lot_browse.tgl_terima_notice,
                        'tgl_terima_notice':lot_browse.tgl_terima_notice,
                        'tgl_terima_stnk':lot_browse.tgl_terima_stnk,
                        'tgl_terima_no_polisi':lot_browse.tgl_terima_no_polisi,
                    }
        
                elif lot_browse.no_notice_copy :
                    value = {
                        'customer_id': lot_browse.customer_id.id,
                        'customer_stnk':lot_browse.customer_stnk.id,
                        'tgl_notice':lot_browse.tgl_notice_copy,
                        'no_notice':lot_browse.no_notice_copy,
                        'tgl_stnk':lot_browse.tgl_stnk,
                        'no_stnk':lot_browse.no_stnk,
                        'no_polisi':lot_browse.no_polisi,
                        'tgl_notice_rel':lot_browse.tgl_notice_copy,
                        'no_notice_rel':lot_browse.no_notice_copy,
                        'tgl_terima_notice_rel':lot_browse.tgl_terima_notice,
                        'tgl_terima_notice':lot_browse.tgl_terima_notice,
                        'tgl_terima_stnk':lot_browse.tgl_terima_stnk,
                        'tgl_terima_no_polisi':lot_browse.tgl_terima_no_polisi,
                    }

            result['value'] = value
            result['warning'] = warning 
        return result
