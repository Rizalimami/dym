import time
from datetime import datetime
from openerp.osv import fields, osv, orm
from openerp import api
import sys

class wiz_penerimaan_faktur_line(orm.TransientModel):
    _name = 'wiz.penerimaan.faktur.line'
    _description = "penerimaan faktur Line Wizard"
        
    _columns = {
        'penerimaan_faktur_id': fields.many2one('dym.penerimaan.faktur', string='penerimaan faktur'),
        'lot_ids': fields.many2many('stock.production.lot','wiz_penerimaan_faktur_line_lot_rel','wiz_penerimaan_faktur_id','lot_id','Engine Number', domain="[('id','=',0)]"),
    }

    _defaults = {
        'penerimaan_faktur_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("Data Error, please try to refresh page or contact your administrator!"))
        res = super(wiz_penerimaan_faktur_line, self).default_get(cr, uid, fields, context=context)
        return res
        
    def lot_change(self, cr, uid, ids, penerimaan_faktur_id, context=None):
        domain = {}
        penerimaan = self.pool.get('dym.penerimaan.faktur').browse(cr, uid, penerimaan_faktur_id)
        saved_lot_ids = penerimaan.penerimaan_line.mapped('name').ids

        pic_lot_ids = []
        pic_lot_id = []
        pic_lot_id = []
        non_pic_lot_id = []

        domain['lot_ids'] = [('id','=',0)]
        if penerimaan.partner_id:
            lot_obj = self.pool.get('stock.production.lot')
            all_lot_src = lot_obj.search(cr, uid,  [('penerimaan_faktur_id','=',False),('tgl_faktur','!=',False),('state_stnk','=','mohon_faktur'),('branch_id','=',penerimaan.branch_id.id),('id','not in',saved_lot_ids)])
            # all_lot_brw = lot_obj.browse(cr,uid,all_lot_src)
            sys.setrecursionlimit(10000)

            for all_lot_src_id in all_lot_src:
                # print "all_lot_src_idall_lot_src_idall_lot_src_id", all_lot_src_id
                all_lot_brw_id = lot_obj.browse(cr,uid,all_lot_src_id)
                # print "all_lot_brw_idall_lot_brw_id", all_lot_brw_id
                # print "all_lot_brw_idall_lot_brw_id", all_lot_brw_id.id
                # print "all_lot_brw_idall_lot_brw_id", all_lot_brw_id.name
                all_lot_pic_src = lot_obj.search(cr,uid,[('name','=',all_lot_brw_id.name)])
                if len(all_lot_pic_src) == 2:
                    all_lot_pic_brw = lot_obj.browse(cr,uid,all_lot_pic_src)
                    for x in all_lot_pic_brw:
                        all_lot_pic_src_same_branch = lot_obj.search(cr,uid,[('name','=',x.name),('branch_id','=',penerimaan.branch_id.id)])
                        all_lot_pic_brw_same_branch = lot_obj.browse(cr,uid,all_lot_pic_src_same_branch)
                        if all_lot_pic_brw_same_branch:
                            pic_lot_ids.append(x.id)
            for a in all_lot_src:
                if a in pic_lot_ids:
                    pic_lot_id.append(a)
                else:
                    non_pic_lot_id.append(a)

            if not penerimaan.is_pic and not penerimaan.pelwil:
                # print "non_pic_lot_id", non_pic_lot_id
                non_pic_lot_id_brw = lot_obj.browse(cr,uid,non_pic_lot_id)
                non_pic_lot_id_src = non_pic_lot_id_brw.filtered(lambda r: r.sudo().pelanggaran_supplier_id.id == penerimaan.partner_id.id and ((r.sudo().pelanggaran_branch_id.id != penerimaan.branch_id.id and penerimaan.pelwil) or (r.sudo().pelanggaran_branch_id.id == penerimaan.branch_id.id and not penerimaan.pelwil)) ).ids
                all_lot_ids = non_pic_lot_id_src
            elif penerimaan.pelwil:
                # print "non_pic_lot_id", non_pic_lot_id
                non_pic_lot_id_brw = lot_obj.browse(cr,uid,non_pic_lot_id)
                non_pic_lot_id_src = non_pic_lot_id_brw.filtered(lambda r: r.sudo().pelanggaran_supplier_id.id == penerimaan.partner_id.id and ((r.sudo().pelanggaran_branch_id.id != penerimaan.branch_id.id and penerimaan.pelwil) or (r.sudo().pelanggaran_branch_id.id == penerimaan.branch_id.id and not penerimaan.pelwil)) ).ids
                all_lot_ids = non_pic_lot_id_src
            elif penerimaan.is_pic:
                all_lot_ids = pic_lot_id
            # all_lot_ids = all_lot_brw.filtered(lambda r: r.sudo().pelanggaran_supplier_id.id == penerimaan.partner_id.id and ((r.sudo().pelanggaran_branch_id.id != penerimaan.branch_id.id and penerimaan.pelwil) or (r.sudo().pelanggaran_branch_id.id == penerimaan.branch_id.id and not penerimaan.pelwil)) ).ids
            domain['lot_ids'] = [('id','in',all_lot_ids)]
        return {'domain':domain}

    def save_lot_ids(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for data in self.browse(cr, uid, ids, context=context):
            for lot in data.lot_ids:
                lot_change_vals = self.pool.get('dym.penerimaan.faktur.line').onchange_engine(cr, uid, ids, lot.id,data.penerimaan_faktur_id.partner_id.id, data.penerimaan_faktur_id.branch_id.id,data.penerimaan_faktur_id.pelwil,data.penerimaan_faktur_id.is_pic)
                if 'warning' in lot_change_vals and lot_change_vals['warning']:
                    raise osv.except_osv((lot_change_vals['warning']['title']), (lot_change_vals['warning']['message']))
                lot_change_vals['value']['penerimaan_faktur_id'] = data.penerimaan_faktur_id.id
                lot_change_vals['value']['name'] = lot.id
                res = {
                    'penerimaan_line': [[0, data.penerimaan_faktur_id.id, lot_change_vals['value']]]
                }
                data.penerimaan_faktur_id.write(res)
        return True

class dym_penerimaan_faktur(osv.osv):
    _name = "dym.penerimaan.faktur"


    def get_customer_invoice(self,cr,uid,ids,dso,context=None):
        obj_inv = self.pool.get('account.invoice')
        if dso.finco_id:
            invoice_ids = obj_inv.search(cr, uid, [('origin','ilike',dso.name),('tipe','=','finco'),('partner_id','in',[dso.finco_id.id,dso.partner_id.id])])
        else:
            invoice_ids = obj_inv.search(cr, uid, [('origin','ilike',dso.name),('tipe','=','customer'),('partner_id','=',dso.partner_id.id)])
        for inv in obj_inv.browse(cr, uid, invoice_ids):
            return inv.number
        return '-'

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    @api.depends('penerimaan_line.name')
    def _amount_all(self):
        for ib in self:
            amount_total = 0.0
            for line in ib.penerimaan_line:
                ib.update({
                    'total_record': len(ib.penerimaan_line),
                })
        
    _columns = {
        'branch_id': fields.many2one('dym.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Showroom')], 'Division', change_default=True, select=True),
        'name': fields.char('No Reference', readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
        'penerimaan_line': fields.one2many('dym.penerimaan.faktur.line','penerimaan_faktur_id',string="Table Permintaan Faktur"), 
        'partner_id':fields.many2one('res.partner', string='Supplier', domain="[('principle','=',True)]"),
        'partner_md':fields.related('partner_id', type='many2one', relation='res.partner', string='Supplier', readonly=True),
        'ahm_code':fields.related('partner_id','ahm_code',type='char',readonly=True,string='AHM Code MD'),
        'tgl_terima' : fields.date('Tanggal'),
        'engine_no': fields.related('penerimaan_line', 'name', type='char', string='No Engine'),
        'customer_stnk': fields.related('penerimaan_line', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
        'confirm_uid':fields.many2one('res.users',string="Posted by"),
        'confirm_date':fields.datetime('Posted on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),                
        'pelwil' : fields.boolean('Unit Hasil Mutation Order'),
        'is_pic': fields.boolean('Unit Hasil PIC'),
        'total_record' : fields.integer(string='Total Engine', store=True, readonly=True, compute='_amount_all'),
    }
    _defaults = {
        'name': '/',
        'state':'draft',
        'division' : 'Unit',
        'tgl_terima': fields.date.context_today,
        'branch_id': _get_default_branch,
    }   

    def onchange_pelwil(self,cr,uid,ids,pelwil,branch_id,is_pic,context=None):
        value = {}
        if not pelwil or not is_pic :
            value = {
                'penerimaan_line' : False,
                'ahm_code' : False,
                'partner_id' : False,
                'partner_md' : False,
            }
        else:
            value = {
                'penerimaan_line' : False,
                'ahm_code' : False,
                'partner_id' : False,
                'partner_md' : False,
            }
        return {'value':value}

    def onchange_branch_penerimaan_faktur(self, cr, uid, ids, branch_id, pelwil, partner_id, is_pic):
        branch_obj = self.pool.get('dym.branch')
        branch_search = branch_obj.search(cr,uid,[('id','=',branch_id)])
        branch_browse = branch_obj.browse(cr,uid,branch_search)   
        partner_md = branch_browse.default_supplier_id.id
        if pelwil or is_pic:
            partner_md = partner_id
        partner = self.pool.get('res.partner').browse(cr, uid, partner_md)
        return {'value':{'partner_id':partner_md,'partner_md':partner_md,'ahm_code':partner.ahm_code}}
    
    def cancel_penerimaan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        for x in val.penerimaan_line :
            lot_search = lot_pool.search(cr,uid,[
                ('branch_id','=',val.branch_id.id),
                ('penerimaan_faktur_id','=',val.id),
                ('id','=',x.name.id)
                ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                if lot_browse.proses_stnk_id or lot_browse.penerimaan_notice_id or lot_browse.penerimaan_stnk_id or lot_browse.penerimaan_bpkb_id or lot_browse.proses_biro_jasa_id :
                    raise osv.except_osv(('Perhatian !'), ("No faktur engine \'%s\' telah diproses, data tidak bisa di cancel !")%(lot_browse.name))                    
                else : 
                    lot_browse.write({'state_stnk': 'mohon_faktur','tgl_terima':False,'penerimaan_faktur_id':False,'faktur_stnk':False,'tgl_cetak_faktur':False})
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        return True
    
    def post_penerimaan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = datetime.today()
        self.write(cr, uid, ids, {'state': 'posted','tgl_terima':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})               
        for x in val.penerimaan_line :
            lot_search = lot_pool.search(cr,uid,[
                ('id','=',x.name.id)
                ])
            lot_browse = lot_pool.browse(cr,uid,lot_search)
            lot_browse.write({
                'state_stnk':'terima_faktur',
                'tgl_cetak_faktur': x.tgl_cetak_faktur,
                'faktur_stnk':x.faktur_stnk,
                'tgl_terima':val.tgl_terima
            })   
        if val.name=='/':
            values = {
                'name': self.pool.get('ir.sequence').get_per_branch(cr, uid, val.branch_id.id, 'PEF', division='Unit')
            }
            self.write(cr, uid, ids, values, context=context)
        return True
    
    def create(self, cr, uid, vals, context=None):
        lot_penerimaan = []
        for x in vals['penerimaan_line']:
            lot_penerimaan.append(x.pop(2))
        
        lot_pool = self.pool.get('stock.production.lot')
        # vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PEF', division='Unit')
        vals['tgl_terima'] = time.strftime('%Y-%m-%d'),
        del[vals['penerimaan_line']]
        penerimaan_id = super(dym_penerimaan_faktur, self).create(cr, uid, vals, context=context) 
        sys.setrecursionlimit(10000)
        if penerimaan_id :         
            for x in lot_penerimaan :
                lot_search = lot_pool.search(cr,uid,[
                    ('id','=',x['name'])
                ])
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                lot_browse.write({
                    'penerimaan_faktur_id':penerimaan_id,
                })   
                penerimaan_pool = self.pool.get('dym.penerimaan.faktur.line')
                penerimaan_pool.create(cr, uid, {
                    'name':lot_browse.id,
                    'penerimaan_faktur_id':penerimaan_id,
                    'customer_stnk':lot_browse.customer_stnk.id,
                    'tgl_cetak_faktur':x['tgl_cetak_faktur'],
                    'faktur_stnk':x['faktur_stnk'],
                    'chassis_no':lot_browse.chassis_no,
                    'pelanggaran_branch_name_test':lot_browse.sudo().pelanggaran_branch_name_test,
                    'pelanggaran_branch_ahm_code_test':lot_browse.sudo().pelanggaran_branch_ahm_code_test,
                    'pelanggaran_branch_ahm_sales_code_test':lot_browse.sudo().pelanggaran_branch_ahm_sales_code_test,
                })           
        else :
            return False
        return penerimaan_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        vals.get('penerimaan_line',[]).sort(reverse=True)

        collect = self.browse(cr,uid,ids)
        lot_penerimaan = []
        lot_pool = self.pool.get('stock.production.lot')
        line_pool = self.pool.get('dym.penerimaan.faktur.line')

        lot = vals.get('penerimaan_line', False)
        if lot :
            for x,item in enumerate(lot) :
                lot_id = item[1]
                if item[0] == 2 :
                    line_search = line_pool.search(cr,uid,[('id','=',lot_id)])
                    line_browse = line_pool.browse(cr,uid,line_search)
                    lot_search = lot_pool.search(cr,uid,[
                                           ('id','=',line_browse.name.id)
                                           ])
                    if not line_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Penerimaan Line"))
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                        'penerimaan_faktur_id':False,
                        'tgl_cetak_faktur':False,
                        'faktur_stnk':False,
                        'tgl_terima':False
                    })                        
                elif item[0] == 0:
                    values = item[2]
                    lot_search = lot_pool.search(cr,uid,[('id','=',values['name'])])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
                    
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                           'penerimaan_faktur_id':collect.id,
                           })   
                    
            
        return super(dym_penerimaan_faktur, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Penerimaan Faktur sudah di post ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')
        lot_search = lot_pool.search(cr,uid,[
                                           ('penerimaan_faktur_id','=',ids)
                                           ])
        lot_browse = lot_pool.browse(cr,uid,lot_search)
        for x in lot_browse :
            x.write({'faktur_stnk': False,'tgl_cetak_faktur':False,'tgl_terima':False})
        return super(dym_penerimaan_faktur, self).unlink(cr, uid, ids, context=context)
    
        
class dym_penerimaan_faktur_line(osv.osv):
    _name = "dym.penerimaan.faktur.line"

    def _check_no_faktur(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if l.faktur_stnk:
                lot_ids = self.pool.get('stock.production.lot').search(cr, uid, [('faktur_stnk','=',l.faktur_stnk),('id','!=',l.name.id)], limit=1)
                if lot_ids:
                    lot = self.pool.get('stock.production.lot').browse(cr, uid, lot_ids)
                    raise osv.except_osv(('Perhatian !'), ("Faktur STNK No. %s sudah ada di nomor engine %s!")%(l.faktur_stnk, lot.name))
                    return False
                else:
                    line_ids = self.search(cr, uid, [('faktur_stnk','=',l.faktur_stnk),('id','!=',l.id),('penerimaan_faktur_id.state','in',['draft','posted'])])
                    if line_ids:
                        raise osv.except_osv(('Perhatian !'), ("Faktur STNK No. %s duplicate!")%(l.faktur_stnk))
                        return False
        return True

    _columns = {
        'name' : fields.many2one('stock.production.lot','No Engine',domain="[('id','=',0)]"),
        'dealer_sale_order_id': fields.related('name', 'dealer_sale_order_id', type='many2one', relation='dealer.sale.order', readonly='1', string='DSM'),
        'penerimaan_faktur_id' : fields.many2one('dym.penerimaan.faktur','Penerimaan Faktur'),
        'customer_id': fields.related('name', 'customer_id', type='many2one', relation='res.partner', string='Customer', readonly=True),
        'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
        'tgl_cetak_faktur' : fields.date('Tanggal Cetak'),
        'faktur_stnk' : fields.char('No Faktur STNK'),
        'chassis_no':fields.related('name','chassis_no',type='char',readonly=True,string='No Chassis'),
        'pelanggaran_branch_name_test':fields.related('name','pelanggaran_branch_name_test',type='char',readonly=True,string='Branch'),
        'pelanggaran_branch_ahm_code_test':fields.related('name','pelanggaran_branch_ahm_code_test',type='char',readonly=True,string='AHM Code Branch'),
        'pelanggaran_branch_ahm_sales_code_test':fields.related('name','pelanggaran_branch_ahm_sales_code_test',type='char',readonly=True,string='AHM Code Sales'),
    }

    _sql_constraints = [
        ('unique_name_penerimaan_faktur_id', 'unique(name,penerimaan_faktur_id)', 'Detail Engine duplicate, mohon cek kembali !'),
    ]      

    _constraints = [
        (_check_no_faktur, 'ditemukan faktur STNK duplicate.', ['faktur_stnk','name']),
    ]

    def onchange_engine(self, cr, uid, ids, name, partner_id, branch_id, pelwil, is_pic):
        lot_obj = self.pool.get('stock.production.lot')
        lot_search = lot_obj.search(cr,uid,[('id','=',name)])
        lot_browse = lot_obj.browse(cr,uid,lot_search)           
        sys.setrecursionlimit(10000)

        branch = self.pool.get('dym.branch')
        branch_src = branch.search(cr,uid,[('id','=',branch_id)])
        branch_brw = branch.browse(cr,uid,branch_src)

        company_id = branch_brw.company_id.id
        
        value = {
            'chassis_no':lot_browse.chassis_no,
            'dealer_sale_order_id':lot_browse.dealer_sale_order_id.id,
            'customer_id':lot_browse.customer_id.id,
            'customer_stnk':lot_browse.customer_stnk.id,
            'tgl_cetak_faktur':lot_browse.tgl_cetak_faktur,
            'faktur_stnk':lot_browse.faktur_stnk,
            'pelanggaran_branch_name_test':lot_browse.pelanggaran_branch_name_test,
            'pelanggaran_branch_ahm_code_test':lot_browse.pelanggaran_branch_ahm_code_test,
            'pelanggaran_branch_ahm_sales_code_test':lot_browse.pelanggaran_branch_ahm_sales_code_test
        }
        
        domain = {'name':[('id','=',0)]}
        pic_lot_ids = []
        pic_lot_id = []
        pic_lot_id = []
        non_pic_lot_id = []
        if partner_id:
            all_lot_src = lot_obj.search(cr, uid, [('penerimaan_faktur_id','=',False),('tgl_faktur','!=',False),('state_stnk','=','mohon_faktur'),('branch_id','=',branch_id)])
            for all_lot_src_id in all_lot_src:
                all_lot_brw_id = lot_obj.browse(cr,uid,all_lot_src_id)
                all_lot_pic_src = lot_obj.search(cr,uid,[('name','=',all_lot_brw_id.name)])
                if len(all_lot_pic_src) == 2:
                    all_lot_pic_brw = lot_obj.browse(cr,uid,all_lot_pic_src)
                    for x in all_lot_pic_brw:
                        all_lot_pic_src_same_branch = lot_obj.search(cr,uid,[('name','=',x.name),('branch_id','=',branch_id)])
                        all_lot_pic_brw_same_branch = lot_obj.browse(cr,uid,all_lot_pic_src_same_branch)
                        if all_lot_pic_brw_same_branch:
                            pic_lot_ids.append(x.id)
            # all_lot_brw = lot_obj.browse(cr,uid,all_lot_src)
            # all_lot_ids = all_lot_brw.filtered(lambda r: r.sudo().pelanggaran_supplier_id.id == partner_id and ((r.sudo().pelanggaran_branch_id.id != branch_id and pelwil) or (r.sudo().pelanggaran_branch_id.id == branch_id and not pelwil))
            #     ).ids
            for a in all_lot_src:
                if a in pic_lot_ids:
                    pic_lot_id.append(a)
                else:
                    non_pic_lot_id.append(a)

            if not is_pic and not pelwil:
                non_pic_lot_id_brw = lot_obj.browse(cr,uid,non_pic_lot_id)
                non_pic_lot_id_src = non_pic_lot_id_brw.filtered(lambda r: r.sudo().pelanggaran_supplier_id.id == partner_id and ((r.sudo().pelanggaran_branch_id.id != branch_id and pelwil) or (r.sudo().pelanggaran_branch_id.id == branch_id and not pelwil))
                    ).ids
                all_lot_ids = non_pic_lot_id_src
            elif pelwil:
                non_pic_lot_id_brw = lot_obj.browse(cr,uid,non_pic_lot_id)
                non_pic_lot_id_src = non_pic_lot_id_brw.filtered(lambda r: r.sudo().pelanggaran_supplier_id.id == partner_id and ((r.sudo().pelanggaran_branch_id.id != branch_id and pelwil) or (r.sudo().pelanggaran_branch_id.id == branch_id and not pelwil))
                    ).ids
                all_lot_ids = non_pic_lot_id_src
            elif is_pic:
                all_lot_ids = pic_lot_id
            domain = {'name':[('id','in',all_lot_ids)]}
        
        return {
            'value':value,
            'domain':domain,
        }
    
    def onchange_faktur_stnk(self,cr,uid,ids,faktur_stnk,context=None):
        if faktur_stnk :
            faktur_stnk = faktur_stnk.replace(' ', '').upper()
            return {
                'value' : {'faktur_stnk':faktur_stnk}
            }  
    
    
    