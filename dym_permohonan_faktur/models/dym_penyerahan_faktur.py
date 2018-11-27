import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import api

class dym_penyerahan_faktur(osv.osv):
    _name = "dym.penyerahan.faktur"
    
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

    _columns = {
                'name': fields.char('No Reference', readonly=True),
                'branch_id': fields.many2one('dym.branch', string='Branch', required=True),
                'division':fields.selection([('Unit','Showroom')], 'Division', change_default=True, select=True),
                'penerima':fields.char('Penerima'),
                'partner_id':fields.many2one('res.partner','Customer',domain=[('customer','=',True)]),
                'keterangan':fields.char('Keterangan'),
                'tanggal':fields.date('Tanggal'),
                'penyerahan_line' : fields.one2many('dym.penyerahan.faktur.line','penyerahan_id',string="Penyerahan STNK"),  
                'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
                'engine_no': fields.related('penyerahan_line', 'name', type='char', string='No Engine'),
                'customer_stnk': fields.related('penyerahan_line', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
                'confirm_uid':fields.many2one('res.users',string="Posted by"),
                'confirm_date':fields.datetime('Posted on'),
                'total_record' : fields.integer(string='Total Engine', store=True, readonly=True, compute='_amount_all'),
                }
 
    _defaults = {
        'name': '/',
        'state':'draft',
        'division' : 'Unit',
        'tanggal': fields.date.context_today,
        'branch_id': _get_default_branch,
     } 

    def onchange_partner(self,cr,uid,ids,partner):
        value = {}
        if partner :
            res_partner = self.pool.get('res.partner').search(cr,uid,[
                                                                      ('id','=',partner)
                                                                      ])
            res_partner_browse = self.pool.get('res.partner').browse(cr,uid,res_partner)            
            value = {'penerima':res_partner_browse.name}          
        return {'value':value}    
    
    def post_penyerahan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = datetime.today()
        self.write(cr, uid, ids, {'state': 'posted','tanggal':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})       
 
        for x in val.penyerahan_line :
            lot_search = lot_pool.search(cr,uid,[
                        ('id','=',x.name.id)
                        ])
            lot_browse = lot_pool.browse(cr,uid,lot_search)   
 
            lot_browse.write({
                    'tgl_penyerahan_faktur':x.tgl_ambil_faktur,
                     }) 

        if val.name=='/':
            values = {
                'name': self.pool.get('ir.sequence').get_per_branch(cr, uid, val.branch_id.id, 'PFO', division='Unit')
            }     
            self.write(cr, uid, ids, values, context=context)
                           
        return True
    
    def create(self, cr, uid, vals, context=None):
        if not vals['penyerahan_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penyerahan. Data tidak bisa di save."))
        lot_penyerahan = []
        for x in vals['penyerahan_line']:
            lot_penyerahan.append(x.pop(2))
        lot_pool = self.pool.get('stock.production.lot')
        # vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PFO', division='Unit')
        vals['tanggal'] = time.strftime('%Y-%m-%d'),
        del[vals['penyerahan_line']]        
        penyerahan_id = super(dym_penyerahan_faktur, self).create(cr, uid, vals, context=context) 
        if penyerahan_id :         
            for x in lot_penyerahan :
                
                lot_search = lot_pool.search(cr,uid,[
                            ('id','=',x['name'])
                            ])
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                penyerahan_pool = self.pool.get('dym.penyerahan.faktur.line')
                penyerahan_pool.create(cr, uid, {
                                                    'name':lot_browse.id,
                                                    'penyerahan_id':penyerahan_id,
                                                    'customer_stnk':13,
                                                    'tgl_cetak_faktur':lot_browse.tgl_cetak_faktur,
                                                    'faktur_stnk':lot_browse.faktur_stnk,
                                                    'tgl_ambil_faktur':x['tgl_ambil_faktur'],
                                                    })  
                lot_browse.write({
                       'penyerahan_faktur_id':penyerahan_id,
                                  })
        else :
            return False
        return penyerahan_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        val = self.browse(cr,uid,ids)    
        vals.get('penyerahan_line',[]).sort(reverse=True)        
        penyerahan_pool = self.pool.get('dym.penyerahan.faktur.line')
        lot_pool = self.pool.get('stock.production.lot')
        lot = vals.get('penyerahan_line', False)
        if lot :
            del[vals['penyerahan_line']]
            for x,item in enumerate(lot) :
                lot_id = item[1]

                if item[0] == 2 :
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
                                       'penyerahan_faktur_id':False,
                                     })
                    penyerahan_pool.unlink(cr,uid,lot_id, context=context)
                elif item[0] == 0 :
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
                                    'tgl_cetak_faktur':lot_browse.tgl_cetak_faktur,
                                    'faktur_stnk':lot_browse.faktur_stnk,
                                    'tgl_ambil_faktur':values['tgl_ambil_faktur'],
                                    })
                    
                    lot_browse.write({
                           'penyerahan_faktur_id':val.id,  
                                                       }) 
                elif item[0] == 1 :
                    data = item[2]
                    penyerahan_search = penyerahan_pool.search(cr,uid,[
                                                                       ('id','=',lot_id)
                                                                       ])
                    penyerahan_browse = penyerahan_pool.browse(cr,uid,penyerahan_search)
                    if penyerahan_search :
                        if 'tgl_ambil_faktur' in data :
                            penyerahan_browse.write({
                                                     'tgl_ambil_faktur':data['tgl_ambil_faktur']
                                                     })
                                                        
        return super(dym_penyerahan_faktur, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Penyerahan Faktur sudah di validate ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')

        for x in self.browse(cr, uid, ids, context=context):
            for y in x.penyerahan_line :
                lot_search = lot_pool.search(cr,uid,[
                                                     ('id','=',y.name.id)
                                                     ])
                if lot_search :
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                                      'tgl_penyerahan_faktur':False,})     
                       

        return super(dym_penyerahan_faktur, self).unlink(cr, uid, ids, context=context)    
    
class dym_penyerahan_faktur_line(osv.osv):
    _name = "dym.penyerahan.faktur.line"

    def _check_no_faktur(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if l.faktur_stnk:
                lot_ids = self.pool.get('stock.production.lot').search(cr, uid, [('faktur_stnk','=',l.faktur_stnk),('id','!=',l.name.id)])
                if lot_ids:
                    lot = self.pool.get('stock.production.lot').browse(cr, uid, lot_ids)
                    raise osv.except_osv(('Perhatian !'), ("Faktur STNK No. %s sudah ada di nomor engine %s!")%(l.faktur_stnk, lot.name))
                    return False
                else:
                    line_ids = self.search(cr, uid, [('faktur_stnk','=',l.faktur_stnk),('id','!=',l.id)])
                    if line_ids:
                        raise osv.except_osv(('Perhatian !'), ("Faktur STNK No. %s duplicate!")%(l.faktur_stnk))
                        return False
        return True
        
    _columns = {
        'name' : fields.many2one('stock.production.lot','No Engine',change_default=True,),                
        'penyerahan_id' : fields.many2one('dym.penyerahan.faktur','Penyerahan Faktur'),
        'customer_id':fields.related('name','customer_id',type='many2one',relation='res.partner',readonly=True,string='Customer'),
        'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
        'tgl_cetak_faktur' : fields.related('name','tgl_cetak_faktur',type="date",readonly=True,string='Tgl Cetak Faktur'),
        'faktur_stnk' : fields.related('name','faktur_stnk',type="char",readonly=True,string='No Faktur STNK'),
        'tgl_ambil_faktur' :fields.date('Tgl Ambil Faktur')
    }

    _sql_constraints = [
        ('unique_name_penyerahan_id', 'unique(name,penyerahan_id)', 'Detail Engine duplicate, mohon cek kembali !'),
    ]

    _constraints = [
        (_check_no_faktur, 'ditemukan faktur STNK duplicate.', ['faktur_stnk','name']),
    ]

    _defaults = {
      'tgl_ambil_faktur': fields.date.context_today,

     } 
        
    def onchange_engine(self, cr, uid, ids, name,branch_id,division,customer,penerima_stnk):
        if not branch_id or not division or not penerima_stnk:
            raise osv.except_osv(('Perhatian !'), ('Sebelum menambah detil transaksi,\n harap isi branch, division, peneriman STNK terlebih dahulu.'))
        value = {}
        domain = {}
        result = {}
        if customer :
            domain['name'] ="[('penerimaan_faktur_id','!=',False),('faktur_stnk','!=',False),('state_stnk','=','terima_faktur'),('branch_id','=',parent.branch_id),('customer_id','=',parent.partner_id),('tgl_penyerahan_faktur','=',False),'|',('state','=','paid_offtr'),'&',('state','=','sold_offtr'),('customer_id.is_group_customer','!=',False)]"
        elif not customer :
            domain['name'] ="[('penerimaan_faktur_id','!=',False),('faktur_stnk','!=',False),('state_stnk','=','terima_faktur'),('branch_id','=',parent.branch_id),('tgl_penyerahan_faktur','=',False),'|',('state','=','paid_offtr'),'&',('state','=','sold_offtr'),('customer_id.is_group_customer','!=',False)]"
        if name :
            lot_obj = self.pool.get('stock.production.lot')
            lot_search = lot_obj.search(cr,uid,[('id','=',name)])
            if lot_search :
                lot_browse = lot_obj.browse(cr,uid,lot_search)          
                value = {                
                    'dealer_sale_order_id': lot_browse.dealer_sale_order_id.id,
                    'customer_id': lot_browse.customer_id.id,
                    'customer_stnk':lot_browse.customer_stnk.id,
                    'tgl_cetak_faktur':lot_browse.tgl_cetak_faktur,
                    'faktur_stnk':lot_browse.faktur_stnk,
                }
        return {'domain':domain,'value':value}