import time
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from datetime import datetime
import pdb

class dym_work_order(osv.osv):
    _inherit = "dym.work.order"
    
    _columns = {
        'collected_ok_not':fields.selection([('ok','OK'), ('not','Not Ok')], 'Status KPB'),
        'tipe_motor':fields.related('product_id','category_product_id',type='many2one',relation='dym.category.product',readonly=True, string='Type Motor'),
    }

class dym_collecting_kpb(osv.osv):
    _name = "dym.collecting.kpb"
    _description = "Collecting KPB"
    
    def _get_branch(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('branch_id', False)

    def _get_adh(self, cr, uid, ids, branch_id, context=None):
        hr_obj = self.pool.get('hr.employee')
        hr_ids = hr_obj.search(cr, uid, [('branch_id','=',branch_id),('job_id','=',125)])
        hrs = hr_obj.browse(cr,uid,hr_ids)
        return hrs[0].name

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    def _amount_total(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        result = {}
        for collect in self.browse(cr, uid, ids, context=context):
            res[collect.id] = {
                'amount_total': 0.0,
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_jasa': 0.0,
                'amount_oli': 0.0,
                'amount_wo': 0.0,
                'amount_outstanding': 0.0,
            }
            amount_kompensasi_oli = amount_jasa = amount_oli = amount_total = amount_untaxed = amount_tax = 0.0

            for wo in collect.work_order_ids:
                tipe_motor = wo.tipe_motor.name
                result[tipe_motor]={'amount_jasa':0.0,'amount_oli':0.0}
                for woline in wo.work_lines:
                    if woline.categ_id=='Service':
                        amount_jasa += woline.price_subtotal
                        result[tipe_motor]['amount_jasa'] += woline.price_subtotal
                    if woline.categ_id=='Sparepart':
                        amount_oli += woline.price_subtotal
                        result[tipe_motor]['amount_oli'] += woline.price_subtotal

            for line in collect.collecting_line:
                self.pool.get('dym.collecting.kpb.line').write(cr, uid, line.id, {
                    'total_jasa':line.categ and line.categ in result and result[line.categ]['amount_jasa'] or 0.0,
                    'total_oli':line.categ and line.categ in result and result[line.categ]['amount_oli'] or 0.0,
                }, context=context)
                if collect.use_kompensasi == True:
                    amount_kompensasi_oli += line.total_kompensasi
                if collect.use_oli == True:
                    amount_oli += line.total_oli
                amount_jasa += line.total_jasa

            taxes = self.pool.get('account.tax').compute_all(cr, uid, collect.taxes_ids, (amount_kompensasi_oli),1)
            amount_untaxed += taxes['total']
            for c in taxes['taxes']:
                amount_tax += c.get('amount',0.0)
            res[collect.id]['amount_untaxed'] = amount_untaxed
            res[collect.id]['amount_tax'] = amount_tax
            res[collect.id]['amount_jasa'] = amount_jasa
            res[collect.id]['amount_oli'] = amount_oli
            amount_total = amount_untaxed + amount_tax + amount_jasa + amount_oli
            res[collect.id]['amount_total'] = amount_total
            amount_wo = 0
            for x in collect.collecting_line.mapped('wo_ids') :
                inv_obj_search=self.pool.get('account.invoice').search(cr,uid,[('origin','ilike',x.name)])
                for inv_obj in self.pool.get('account.invoice').browse(cr,uid,inv_obj_search):
                    amount_wo += inv_obj.amount_total
            res[collect.id]['amount_wo'] = amount_wo
            res[collect.id]['amount_outstanding'] = amount_wo - amount_total
        return res

    def _get_collect(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('dym.collecting.kpb.line').browse(cr, uid, ids, context=context):
            result[line.collecting_id.id] = True
        return result.keys()
        
    _columns = {
        'use_kompensasi': fields.boolean('Kompensasi Oli'),
        'use_oli': fields.boolean('Oli'),
        'use_sparepart': fields.related('use_oli', type='boolean', string='Oli'),
        'type': fields.selection([('KPB','KPB'),('CLA','Claim')], string='Type'),
        'name': fields.char('Collecting KPB', readonly=True),
        'branch_id':fields.many2one('dym.branch','Branch',required=True, change_default=1), 
        'division':fields.selection([('Sparepart','Workshop')],'Division', change_default=True,select=True,required=True),
        'work_order_ids': fields.one2many('dym.work.order','collecting_id',string="Table Collecting KPB"), 
        'work_order_ids2': fields.related('work_order_ids', type='one2many', relation='dym.work.order', string="Table Collecting KPB"), 
        'state': fields.selection([('draft', 'Draft'), ('open','Open'), ('done', 'Done')], 'State', readonly=True),
        'supplier_id':fields.related('branch_id','default_supplier_workshop_id',type='many2one',relation='res.partner',readonly=True,string='Supplier'),
        'collecting_line':fields.one2many('dym.collecting.kpb.line','collecting_id',string="Table Collecting Line"),
        'collecting_line1':fields.one2many('dym.collecting.kpb.line','collecting_id',string="Table Collecting Line"),
        'collecting_line2':fields.one2many('dym.collecting.kpb.line','collecting_id',string="Table Collecting Line"),
        'collecting_line3':fields.one2many('dym.collecting.kpb.line','collecting_id',string="Table Collecting Line"),
        'collecting_line4':fields.one2many('dym.collecting.kpb.line','collecting_id',string="Table Collecting Line"),
        'supplier_ref':fields.char(string='No. Claim MD',size=64),
        'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
        'confirm_date':fields.datetime('Confirmed on'),
        'date' : fields.date('Date'),
        'amount_untaxed': fields.function(_amount_total, digits_compute=dp.get_precision('Account'), string='Tax Base (Kompensasi Oli)',
            store={
                'dym.collecting.kpb': (lambda self, cr, uid, ids, c={}: ids, ['collecting_line','collecting_line1','collecting_line2','collecting_line3','collecting_line4','taxes_ids','use_oli','use_kompensasi'], 10),
                'dym.collecting.kpb.line': (_get_collect, ['qty','oli','jasa','kompensasi'], 10),
            },
            multi='sums', help="The amount without tax (Kompensasi Oli).", track_visibility='always'),
        
        'taxes_ids': fields.many2many('account.tax', 'collect_kpb_tax_rel', 'collect_kpb_id','tax_id', 'Taxes (Kompensasi Oli)'),
        'amount_tax': fields.function(_amount_total, digits_compute=dp.get_precision('Account'), string='Tax Amount (Kompensasi Oli)',
            store={
                'dym.collecting.kpb': (lambda self, cr, uid, ids, c={}: ids, ['collecting_line','collecting_line1','collecting_line2','collecting_line3','collecting_line4','taxes_ids','use_oli','use_kompensasi'], 10),
                'dym.collecting.kpb.line': (_get_collect, ['qty','oli','jasa','kompensasi'], 10),
            },
            multi='sums', help="Tax Amount (Kompensasi Oli)."),
        'amount_jasa': fields.function(_amount_total, digits_compute=dp.get_precision('Account'), string='Total Jasa',
            store={
                'dym.collecting.kpb': (lambda self, cr, uid, ids, c={}: ids, ['collecting_line','collecting_line1','collecting_line2','collecting_line3','collecting_line4','taxes_ids','use_oli','use_kompensasi'], 10),
                'dym.collecting.kpb.line': (_get_collect, ['qty','oli','jasa','kompensasi'], 10),
            },
            multi='sums', help="Total Jasa"),
        'amount_oli': fields.function(_amount_total, digits_compute=dp.get_precision('Account'), string='Total Oli',
            store={
                'dym.collecting.kpb': (lambda self, cr, uid, ids, c={}: ids, ['collecting_line','collecting_line1','collecting_line2','collecting_line3','collecting_line4','taxes_ids','use_oli','use_kompensasi'], 10),
                'dym.collecting.kpb.line': (_get_collect, ['qty','oli','jasa','kompensasi'], 10),
            },
            multi='sums', help="Total Oli"),
        'amount_sparepart': fields.related('amount_oli', type='float', string='Amount Sparepart'),
        'amount_total': fields.function(_amount_total, string='Total Collecting KPB', digits_compute= dp.get_precision('Account'),
            store={
                'dym.collecting.kpb': (lambda self, cr, uid, ids, c={}: ids, ['collecting_line','collecting_line1','collecting_line2','collecting_line3','collecting_line4','taxes_ids','use_oli','use_kompensasi'], 10),
                'dym.collecting.kpb.line': (_get_collect, ['qty','oli','jasa','kompensasi'], 10),
            },multi='sums', help="Total."),  
        'amount_wo': fields.function(_amount_total, string='Total Work Order', digits_compute= dp.get_precision('Account'),
            store={
                'dym.collecting.kpb': (lambda self, cr, uid, ids, c={}: ids, ['work_order_ids','collecting_line','collecting_line1','collecting_line2','collecting_line3','collecting_line4','taxes_ids','use_oli','use_kompensasi'], 10),
                'dym.collecting.kpb.line': (_get_collect, ['qty','oli','jasa','kompensasi'], 10),
            },multi='sums', help="Total Work Order."),  
        'amount_outstanding': fields.function(_amount_total, string='Total WO O/S', digits_compute= dp.get_precision('Account'),
            store={
                'dym.collecting.kpb': (lambda self, cr, uid, ids, c={}: ids, ['work_order_ids','collecting_line','collecting_line1','collecting_line2','collecting_line3','collecting_line4','taxes_ids','use_oli','use_kompensasi'], 10),
                'dym.collecting.kpb.line': (_get_collect, ['qty','oli','jasa','kompensasi'], 10),
            },multi='sums', help="Total WO O/S."),  
        'date_kirim_md' : fields.date('Tanggal Kirim Ke MD'),
    }
    
    _defaults = {
        'name': '/',
        'division':'Sparepart',
        'branch_id':_get_branch,
        'state':'draft',
        'branch_id': _get_default_branch,
        'date':fields.date.context_today
    }
     
    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def onchange_branch_collecting(self, cr, uid, ids, branch_id, type):
        wo_pool = self.pool.get('dym.work.order')
        wo_search = wo_pool.search(cr,uid,[
            ('branch_id','=',branch_id),
            ('kpb_collected','=','ok'),
            ('state','=','open'),
            ('type','=',type),
            ('collecting_id','=',False)
        ])
        workorder = []
        if not wo_search :
            workorder = []
        elif wo_search :
            wo_browse = wo_pool.browse(cr,uid,wo_search)           
            for x in wo_browse:
                workorder.append([0,0,{
                    'name':x.name,
                    'lot_id':x.lot_id.id,                                 
                    'chassis_no':x.chassis_no,
                    'date':x.date,
                    'type':x.type,
                    'kpb_ke':x.kpb_ke,
                    'km':x.km,
                    'state':x.state,
                    'kpb_collected':x.kpb_collected,
                    'kpb_collected_date':x.kpb_collected_date,
                }])
        branch_obj = self.pool.get('dym.branch')
        branch_search = branch_obj.search(cr,uid,[
            ('id','=',branch_id)
        ])

        branch_browse = branch_obj.browse(cr,uid,branch_search)
        use_kompensasi = type=='KPB' and branch_browse.kpb_ganti_oli_barang or False
        use_oli = type=='CLA' or False
        taxes_ids = [(6, 0, branch_browse.kpb_ganti_oli_barang_tax.ids)]
        if branch_browse:
            if branch_browse.kpb_ganti_oli_barang:
                use_oli = False
                use_kompensasi = True
            else:
                use_oli = True
                use_kompensasi = False

        vals = {
            'work_order_ids': workorder,
            'work_order_ids2': workorder,
            'supplier_id':branch_browse.default_supplier_workshop_id.id, 
            'use_kompensasi':use_kompensasi,
            'use_oli':use_oli,
            'taxes_ids':taxes_ids
        }
        return {'value':vals}   
    
    def get_sequence(self,cr,uid,branch_id,context=None):
        doc_code = self.pool.get('dym.branch').browse(cr, uid, branch_id).doc_code
        seq_name = 'CKP-W/{0}'.format(doc_code)
        if context and context.get('default_type')=='KPB':
            seq_name = 'CKP-W/{0}'.format(doc_code)
        if context and context.get('default_type')=='CLA':
            seq_name = 'CCL-W/{0}'.format(doc_code)            
        seq = self.pool.get('ir.sequence')
        ids = seq.search(cr, uid, [('name','=',seq_name)])
        if not ids:
            prefix = '/%(y)s%(month)s/'
            prefix = seq_name + prefix
            ids = seq.create(cr, uid, {'name':seq_name,
                'implementation':'no_gap',
                'prefix':prefix,
                'padding':5
            })
        return seq.get_id(cr, uid, ids)
    
    def get_rekap_collecting_line(self,cr,uid,wo_collect,branch) :
        rekap = {}
        collecting = []
        wo_pool = self.pool.get('dym.work.order')

        for x in wo_collect :
            wo_search = wo_pool.search(cr,uid,[
                ('branch_id','=',branch),
                ('kpb_collected','=','ok'),
                ('state','=','open'),
                ('collecting_id','=',False),
                ('name','=',x['name'])
            ])

            wo_browse = wo_pool.browse(cr,uid,wo_search)
            tax_obj = self.pool.get('account.tax')
            nilai_obj = self.pool.get('dym.kpb.engine.type')
            nilai_obj_line = self.pool.get('dym.kpb.engine.price')
            engine_obj = self.pool.get('stock.production.lot')
            engine_search = engine_obj.search(cr,uid,[('id','=',x['lot_id'])])
            engine_browse = engine_obj.browse(cr,uid,engine_search)
            nilai_search = nilai_obj.search(cr,uid,[('engine_no','=',engine_browse.name[:5]),('workshop_id','=',wo_browse.branch_id.workshop_category.id)])
            if not nilai_search :
                nilai_search = nilai_obj.search(cr,uid,[('engine_no','=',engine_browse.name[:4]),('workshop_id','=',wo_browse.branch_id.workshop_category.id)])
            if not nilai_search :
                raise osv.except_osv(('Perhatian !'), ("Nomor engine tidak ada dalam daftar Kategori Nilai Mesin"))
            
            nilai_browse = nilai_obj.browse(cr,uid,nilai_search)

            a = str(nilai_browse.engine_no)
            b = a + str(x['kpb_ke'])

            j = 0.0
            s = 0.0

            for i in wo_browse.work_lines:
                if i.categ_id=='Sparepart':
                    price_total = (i.supply_qty_show * i.price_unit_show) - (i.discount_pcs*i.supply_qty_show+i.discount_bundle+i.discount_program) 
                    taxes = tax_obj.compute_all(cr, uid, i.tax_id, price_total, 1, i.product_id)
                    s += taxes['total_included']
                if i.categ_id=='Service':
                    price_total = (i.price_unit_show) - (i.discount+i.discount_bundle+i.discount_program) 
                    taxes = tax_obj.compute_all(cr, uid, i.tax_id, price_total, 1, i.product_id)
                    j += taxes['total_included']

            if b in rekap:
                qty = rekap[b]['qty'] + 1
                rekap[b].update({'qty':qty}) 

                if x['type']=='CLA':
                    rekap[b].update({
                        'oli': s,
                        'jasa': j,
                    })
                wo_ids = rekap[b]['wo_ids'][0][2] + wo_browse.ids
                rekap[b].update({'wo_ids':[(6, 0, wo_ids)]}) 
            else :
                nilai_search_jasa = nilai_obj_line.search(cr,uid,[
                    ('kpb_ke','=',x['kpb_ke']),
                    ('kategori_id','=',nilai_browse.id)
                ])
                nilai_browse_jasa = nilai_obj_line.browse(cr,uid,nilai_search_jasa)
                if wo_browse.type=='KPB' and not nilai_browse_jasa.kpb_ke :
                    raise osv.except_osv(('Perhatian !'), ("KPB Ke %s tidak ditemukan")%(wo_browse.kpb_ke))
                c = nilai_browse.name
                d = nilai_browse_jasa.kpb_ke

                if x['type'] == 'KPB':
                    e = nilai_browse_jasa.oli
                    f = nilai_browse_jasa.jasa
                else:
                    e = s
                    f = j

                g = nilai_browse_jasa.kompensasi_oli
                h = [(6, 0, wo_browse.ids)]
            
                rekap[b] = {'categ':c,'kpb_ke':d,'oli':e,'jasa':f,'qty':1,'kompensasi':g,'wo_ids':h}

        for value in rekap :
            rekap[value]['total_jasa'] = rekap[value]['jasa']*rekap[value]['qty']
            rekap[value]['total_oli'] = rekap[value]['oli']*rekap[value]['qty']
            rekap[value]['total_kompensasi'] = rekap[value]['kompensasi']*rekap[value]['qty']
            collecting.append([0,False,rekap[value]])
                   
        return collecting
    
    def invoice_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return True
                
    def create(self,cr,uid,vals,context=None):
        if not vals['work_order_ids'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail collecting. Data tidak bisa di save."))

        #Work Order
        wo_collect = []
        for x in vals['work_order_ids']:
            wo_collect.append(x.pop(2))
        
        del[vals['work_order_ids']]
        wo_pool = self.pool.get('dym.work.order')
        vals['name'] = self.get_sequence(cr,uid,vals['branch_id'],context)
        vals['date'] = datetime.today()
        nilai_obj = self.pool.get('dym.kpb.engine.type')
        engine_obj = self.pool.get('stock.production.lot')
        for x in wo_collect :
            wo_branch_search = wo_pool.search(cr, uid,[('name','=',x['name'])])
            wo_branch_browse = wo_pool.browse(cr,uid,wo_branch_search)
            engine_search = engine_obj.search(cr,uid,[('id','=',x['lot_id'])])
            engine_browse = engine_obj.browse(cr,uid,engine_search)
            nilai_search = nilai_obj.search(cr,uid,[('engine_no','=',engine_browse.name[:5]),('workshop_id','=',wo_branch_browse.branch_id.workshop_category.id)])
            if not nilai_search :
                nilai_search = nilai_obj.search(cr,uid,[('engine_no','=',engine_browse.name[:4]),('workshop_id','=',wo_branch_browse.branch_id.workshop_category.id)])
            if not nilai_search :
                raise osv.except_osv(('Perhatian !'), ("Nomor engine tidak ada dalam daftar Kategori Nilai Mesin"))
        # try :
        collecting_line_vals = self.get_rekap_collecting_line(cr,uid,wo_collect,vals['branch_id'])
        vals["collecting_line"] = collecting_line_vals

        collecting_id = super(dym_collecting_kpb, self).create(cr, uid, vals, context=context)
        if collecting_id :         
                for x in wo_collect :
                    wo_search = wo_pool.search(cr,uid,[
                                ('branch_id','=',vals['branch_id']),
                                ('kpb_collected','=','ok'),
                                ('state','=','open'),
                                ('collecting_id','=',False),
                                ('name','=',x['name'])
                                ])
                    wo_browse = wo_pool.browse(cr,uid,wo_search)
                    wo_browse.write({
                           'kpb_collected':'collected',
                           'collecting_id':collecting_id,
                           })              
        else :
            return False
        return collecting_id 
    
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

    def get_update_rekap_collecting_line(self,cr,uid,ids,a) :
        rekap = {} 
        collecting = []
        for x,item in enumerate(a) :
            wo_pool = self.pool.get('dym.work.order')
            wo_id = item[1]
            wo_search = wo_pool.search(cr,uid,[
                                   ('id','=',wo_id)
                                   ])
            if not wo_search :
                raise osv.except_osv(('Perhatian !'), ("Nomor WO tidak ada di work order"))
            wo_browse = wo_pool.browse(cr,uid,wo_search)
            if item[0] == 2 :
                wo_browse.write({
                               'kpb_collected':'ok',
                               'collecting_id':False,
                                 })
            else :
                nilai_obj = self.pool.get('dym.kpb.engine.type')
                nilai_obj_line = self.pool.get('dym.kpb.engine.price')
                engine_obj = self.pool.get('stock.production.lot')
                engine_search = engine_obj.search(cr,uid,[
                                                          ('id','=',wo_browse.lot_id.id)
                                                          ])
                if not engine_search :
                    raise osv.except_osv(('Perhatian !'), ("Nomor engine tidak ada"))

                engine_browse = engine_obj.browse(cr,uid,engine_search)
                nilai_search = nilai_obj.search(cr,uid,[
                                        ('engine_no','=',engine_browse.name[:5]),
                                        ('workshop_id','=',wo_browse.branch_id.workshop_category.id)
                                        ])
                if not nilai_search :
                    nilai_search = nilai_obj.search(cr,uid,[
                                        ('engine_no','=',engine_browse.name[:4]),
                                        ('workshop_id','=',wo_browse.branch_id.workshop_category.id)
                                        ])
                if not nilai_search :
                    raise osv.except_osv(('Perhatian !'), ("Nomor engine tidak ada"))

                nilai_browse = nilai_obj.browse(cr,uid,nilai_search)
               
                a = str(nilai_browse.engine_no)
                b = a + str(wo_browse.kpb_ke)
                if b in rekap:
                    qty = rekap[b]['qty'] + 1
                    rekap[b].update({'qty':qty}) 
                    wo_ids = rekap[b]['wo_ids'][0][2] + wo_browse.ids
                    rekap[b].update({'wo_ids':[(6, 0, wo_ids)]}) 
                else :
                    nilai_search_jasa = nilai_obj_line.search(cr,uid,[
                        ('kpb_ke','=',wo_browse.kpb_ke),
                        ('kategori_id','=',nilai_browse.id)
                    ])
                    nilai_browse_jasa = nilai_obj_line.browse(cr,uid,nilai_search_jasa)
                    # if not nilai_browse_jasa.kpb_ke :
                    #     raise osv.except_osv(('Perhatian !'), ("KPB Ke %s tidak ditemukan")%(wo_browse.kpb_ke))
                    c = nilai_browse.name
                    d = nilai_browse_jasa.kpb_ke
                    e = nilai_browse_jasa.oli
                    f = nilai_browse_jasa.jasa                
                    g = nilai_browse_jasa.kompensasi_oli                
                    h = [(6, 0, wo_browse.ids)]
                    rekap[b] = {'categ':c,'kpb_ke':d,'oli':e,'jasa':f,'qty':1,'kompensasi':g,'wo_ids':h}
                    
        for value in rekap :
            rekap[value]['total_jasa'] = rekap[value]['jasa']*rekap[value]['qty']            
            rekap[value]['total_oli'] = rekap[value]['oli']*rekap[value]['qty']
            rekap[value]['total_kompensasi'] = rekap[value]['kompensasi']*rekap[value]['qty']
            collecting.append([0,0,rekap[value]])
        
        line = self.pool.get('dym.collecting.kpb.line')
        line_search = line.search(cr,uid,[
                                          ('collecting_id','=',ids)
                                          ]) 
        line.unlink(cr,uid,line_search)
            
        return collecting
        
        
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
            
        collect = self.browse(cr,uid,ids)

        a = vals.get('work_order_ids', False)
        
        if a :
            del[vals['work_order_ids']]
            collecting_line_vals = self.get_update_rekap_collecting_line(cr,uid,ids,a)
            vals["collecting_line"] = collecting_line_vals
        return super(dym_collecting_kpb, self).write(cr, uid, ids, vals, context=context)             
 
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Collecting KPB sudah di validate ! tidak bisa didelete !"))

        wo_pool = self.pool.get('dym.work.order')
        wo_search = wo_pool.search(cr,uid,[
                                           ('collecting_id','=',ids)
                                           ])
        wo_browse = wo_pool.browse(cr,uid,wo_search)
        for x in wo_browse :
            x.write({'kpb_collected': 'ok'})
        return super(dym_collecting_kpb, self).unlink(cr, uid, ids, context=context)
          
           
    def invoice_create(self,cr,uid,ids,context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        invoice_wo = {}
        invoice_categ = {}
        invoice_id = {}
        invoice_bbn = {}
        curr_invoice_id=[]
         
         
        move_ids = []
        move_line_obj = self.pool.get('account.move.line')
        obj_inv = self.pool.get('account.invoice')
        obj_line = self.pool.get('account.invoice.line') 
         
        obj =  self.pool.get('dym.branch.config').search(cr,uid,[ ('branch_id','=',val.branch_id.id) ])
        journal = self.pool.get('dym.branch.config').browse(cr,uid,obj)
        if not journal.wo_collecting_kpb_journal_id.id :
            raise osv.except_osv(('Warning !'), ("Journal Collecting KPB Belum di Setting"))
        if not journal.wo_collecting_kpb_journal_id.default_debit_account_id.id :
            raise osv.except_osv(('Warning !'), ("Journal Account Collecting KPB Belum di Setting"))

        if not journal.wo_collecting_claim_journal_id.id :
            raise osv.except_osv(('Warning !'), ("Journal Collecting Claim Belum di Setting"))
        if not journal.wo_collecting_claim_journal_id.default_debit_account_id.id :
            raise osv.except_osv(('Warning !'), ("Journal Account Collecting Claim Belum di Setting"))

        if val.type=='KPB':
            journal_id=journal.wo_collecting_kpb_journal_id.id
            account_id=journal.wo_collecting_kpb_journal_id.default_debit_account_id.id
        else:
            journal_id=journal.wo_collecting_claim_journal_id.id
            account_id=journal.wo_collecting_claim_journal_id.default_debit_account_id.id
                     
        obj_inv = self.pool.get('account.invoice')
        move_list = []
        total = 0
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr,uid,[ ('model','=',self.__class__.__name__) ])
        analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, 'Service', False, 4, 'General')
        analytic_1_part, analytic_2_part, analytic_3_part, analytic_4_part = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, 'Sparepart', False, 4, 'Sparepart_Accesories')
        analytic_1_part_general, analytic_2_part_general, analytic_3_part_general, analytic_4_part_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, 'Sparepart', False, 4, 'General')
        work_id = obj_inv.create(cr,uid, {
            'name':val.name,
            'origin': val.name,
            'branch_id':val.branch_id.id,
            'division':val.division,
            'journal_id':journal_id,
            'account_id':account_id,
            'transaction_id':val.id,
            'model_id':obj_model_id[0],
            'partner_id':val.supplier_id.id,
            'date_invoice':val.create_date,
            'reference_type':'none',
            'analytic_1': analytic_1,
            'analytic_2': analytic_2,
            'analytic_3': analytic_3,
            'analytic_4': analytic_4,
        })
        outstanding_oli_sparepart = 0
        for line in val.collecting_line:
            # if line.categ not in invoice_categ:
            #     invoice_categ['Category: ' + line.categ + ' KPB Ke: ' + line.kpb_ke] = {}
            if val.use_oli:
                total_oli_sparepart = line.oli + line.jasa
            else:
                total_oli_sparepart = line.jasa
            for x in line.wo_ids:
                total_residual = 0
                inv_obj_search=self.pool.get('account.invoice').search(cr,uid,[('origin','ilike',x.name),('type','=','out_invoice'),('state','=','open')])
                for inv_obj in self.pool.get('account.invoice').browse(cr,uid,inv_obj_search):
                    total_residual += inv_obj.residual

                    name = inv_obj.supplier_invoice_number or inv_obj.name or '/'
                    move_line = move_line_obj.search(cr,uid,[
                                        ('name','=', name[:64]),
                                        ('invoice','=',inv_obj.id),
                                        ('account_id','=',inv_obj.account_id.id),
                                        ('debit','>',0)
                                        ])
                    move_brw = move_line_obj.browse(cr, uid, move_line)
                    
                    if inv_obj.account_id not in invoice_bbn:
                        invoice_bbn[inv_obj.account_id] = {'Service':0, 'Sparepart':0, 'ar_line_service_ids': [], 'ar_line_sparepart_ids': []}
                    if inv_obj.analytic_4.cost_center == 'Sparepart_Accesories':
                        invoice_bbn[inv_obj.account_id]['Sparepart'] += inv_obj.residual
                    else:
                        if move_brw.analytic_2.name == 'Part':
                            invoice_bbn[inv_obj.account_id]['Sparepart'] += inv_obj.residual
                        else:
                            invoice_bbn[inv_obj.account_id]['Service'] += inv_obj.residual

                    if inv_obj.analytic_4.cost_center == 'Sparepart_Accesories':
                        invoice_bbn[inv_obj.account_id]['ar_line_sparepart_ids'] += move_line
                    else:
                        if move_brw.analytic_2.name == 'Part':
                            invoice_bbn[inv_obj.account_id]['ar_line_sparepart_ids'] += move_line
                        else:
                            invoice_bbn[inv_obj.account_id]['ar_line_service_ids'] += move_line
                        # move_brw = move_line_obj.browse(cr, uid, move_line)
                if total_oli_sparepart != total_residual:
                    outstanding_oli_sparepart += total_oli_sparepart - total_residual
        # if val.type=='CLA':
        #     for wor in val.work_order_ids2:
        #         inv_ids=obj_inv.search(cr,uid,[('origin','=',wor.name)])
        #         if inv_ids:
        #             for inv_id in inv_ids:
        #                 inv=obj_inv.browse(cr,uid,inv_id)
        #                 if inv.analytic_2.code=='210':
        #                     invoice_bbn[inv.account_id]['Service']=inv.amount_total
        #                 elif inv.analytic_2.code=='220':
        #                     invoice_bbn[inv.account_id]['Sparepart']=inv.amount_total
        for key,value in invoice_bbn.items() :
            if value['Service'] > 0:
                obj_line.create(cr,uid, {
                                    'invoice_id':work_id,
                                    'account_id':key.id,
                                    'partner_id':val.supplier_id.id,
                                    'name': 'Jasa [' + key.name + ']',
                                    'quantity': 1,
                                    'origin': val.name,
                                    'price_unit':value['Service'],
                                    'type': 'out_invoice',
                                    'analytic_1': analytic_1,
                                    'analytic_2': analytic_2,
                                    'analytic_3': analytic_3,
                                    'account_analytic_id': analytic_4,       
                                    })
            if value['Sparepart'] > 0:
                obj_line.create(cr,uid, {
                                    'invoice_id':work_id,
                                    'account_id':key.id,
                                    'partner_id':val.supplier_id.id,
                                    'name': 'Oli [' + key.name + ']',
                                    'quantity': 1,
                                    'origin': val.name,
                                    'price_unit':value['Sparepart'],
                                    'type': 'out_invoice',
                                    'analytic_1': analytic_1_part_general,
                                    'analytic_2': analytic_2_part_general,
                                    'analytic_3': analytic_3_part_general,
                                    'account_analytic_id': analytic_4_part_general,
                                    })
        total_kompensasi = sum(line.total_kompensasi for line in val.collecting_line) if val.use_kompensasi == True else 0
        if total_kompensasi > 0:
            if not journal.wo_collecting_kpb_kompensasi_account_id.id:
                raise osv.except_osv(('Warning !'), ("Journal Account Kompensasi Oli Belum di Setting"))
            kompensasi_account_id = journal.wo_collecting_kpb_kompensasi_account_id.id
            obj_line.create(cr,uid, {
                                    'invoice_id':work_id,
                                    'account_id':kompensasi_account_id,
                                    'partner_id':val.supplier_id.id,
                                    'name': val.name + ' [Kompensasi Oli]',
                                    'quantity': 1,
                                    'origin': val.name,
                                    'price_unit': total_kompensasi,
                                    'type': 'out_invoice',
                                    'analytic_1': analytic_1,
                                    'analytic_2': analytic_2,
                                    'analytic_3': analytic_3,
                                    'account_analytic_id': analytic_4,
                                    'invoice_line_tax_id': [(6,0,val.taxes_ids.ids)],
                                    })
        if outstanding_oli_sparepart != 0:
            if not journal.wo_collecting_kpb_selisih_account_id.id:
                raise osv.except_osv(('Warning !'), ("Journal Account Selisih Collecting KPB Belum di Setting"))
            selisih_account_id = journal.wo_collecting_kpb_selisih_account_id.id
            obj_line.create(cr,uid, {
                                'invoice_id':work_id,
                                'account_id':selisih_account_id,
                                'partner_id':val.supplier_id.id,
                                'name': 'Selisih Collecting KPB',
                                'quantity': 1,
                                'origin': val.name,
                                'price_unit':outstanding_oli_sparepart,
                                'type': 'out_invoice',
                                'analytic_1': analytic_1_part,
                                'analytic_2': analytic_2_part,
                                'analytic_3': analytic_3_part,
                                'account_analytic_id': analytic_4_part,
                                })
        obj_inv.signal_workflow(cr, uid, [work_id], 'invoice_open' )
        self.write(cr, uid, ids, {'date':datetime.today(),'state': 'open','confirm_uid':uid,'confirm_date':datetime.now()})
        # for key_categ,value_categ in invoice_categ.items() :
        for key,value in invoice_bbn.items():
            if value['Service'] > 0 and value['ar_line_service_ids']:
                mv_line_name = 'Jasa [' + key.name + ']'
                move = move_line_obj.search(cr,uid,[
                                                    ('name','=', mv_line_name),
                                                    ('invoice','=',work_id),
                                                    ('account_id','=',key.id),
                                                    ('credit','>',0)
                                                    ])
                if move :
                    account_move = move_line_obj.browse(cr,uid, value['ar_line_service_ids']).sorted(key=lambda r: r.date).ids
                    reconcile_id = self.pool.get('account.move.line').reconcile_partial(cr, uid, account_move + move, 'auto')
            if value['Sparepart'] > 0 and value['ar_line_sparepart_ids']:
                mv_line_name = 'Oli [' + key.name + ']'
                move = move_line_obj.search(cr,uid,[
                                                    ('name','=', mv_line_name),
                                                    ('invoice','=',work_id),
                                                    ('account_id','=',key.id),
                                                    ('credit','>',0)
                                                    ])
                if move :
                    account_move = move_line_obj.browse(cr,uid, value['ar_line_sparepart_ids']).sorted(key=lambda r: r.date).ids
                    reconcile_id = self.pool.get('account.move.line').reconcile_partial(cr, uid, account_move + move, 'auto')
        acc_move_line=self.pool.get('account.move.line').browse(cr,uid,move[0])
        acc_move=self.pool.get('account.move').browse(cr,uid,acc_move_line.move_id.id)
        
        wh_tax_obj=self.pool.get('account.tax.withholding')
        wh_tax_ids=wh_tax_obj.search(cr,uid,[('type_tax_use','=','receipt'),('company_id','=',val.branch_id.company_id.id),('name','like','PPh-23 IN (2%) Jasa')])
        if wh_tax_ids:
            wh_tax=wh_tax_obj.browse(cr,uid,wh_tax_ids)

        #self.pool.get('account.journal').write(cr,uid,acc_move.journal_id.id,{'update_posted':True})
        acc_move.button_cancel()
         
        for i in acc_move.line_id:
            if i.account_id.user_type.code=='AT011' and i.analytic_2.code=='210':
                base_amount=i.credit/1.1
                pph=base_amount*wh_tax.amount
                
        for i in acc_move.line_id:
            if i.account_id.user_type.code=='AT014':
                move_line_obj.write(cr,uid,i.id,{'debit':i.debit-pph})
                move_line_obj.create(cr,uid,{
                    'name': wh_tax.description or '/',
                    'ref': i.ref or '/',
                    'account_id': wh_tax.account_id.id,
                    'journal_id': i.journal_id.id,
                    'period_id': i.period_id.id,
                    'date': i.create_date,
                    'date_maturity':i.date_maturity,
                    'debit': pph,
                    'credit': 0,
                    'branch_id' : i.branch_id.id,
                    'division' : i.division,
                    'partner_id' : i.partner_id.id,
                    'move_id': i.move_id.id,
                    'analytic_account_id' : i.analytic_account_id.id,
                    'analytic_1':analytic_1,
                    'analytic_2':analytic_2,
                    'analytic_3':analytic_3,
                    'analytic_4':analytic_4,
                    'tax_code_id':wh_tax.tax_code_id.id,
                    'tax_amount':base_amount,
                    })

        acc_move.post()
        return work_id
    
class dym_collecting_line(osv.osv):
    _name = "dym.collecting.kpb.line"

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {
                'total_jasa':0.0,
                'total_oli':0.0,
                'total_kompensasi':0.0,
                'amount':0.0,
            }
            total_jasa = line.qty * line.jasa
            total_oli = line.qty * line.oli
            total_kompensasi = line.qty * line.kompensasi
            res[line.id]['total_jasa'] = total_jasa
            res[line.id]['total_oli'] = total_oli
            res[line.id]['total_kompensasi'] = total_kompensasi
            res[line.id]['amount'] = total_kompensasi + total_oli + total_jasa
        return res

    _columns = {
        'collecting_id':fields.many2one('dym.collecting.kpb'),
        'categ':fields.char('Category'),
        'kpb_ke':fields.char('KPB Ke'),
        'qty':fields.integer('Qty'),
        'type': fields.related('collecting_id', 'type', type='char', string='Type'),
        'jasa':fields.float('Jasa'),
        'oli':fields.float('Oli'),
        'kompensasi':fields.float('Kompensasi Oli'),
        'total_jasa': fields.function(_amount_line, string='Total Jasa', digits_compute= dp.get_precision('Account'), store = {
           'dym.collecting.kpb.line': (lambda self, cr, uid, ids, c={}: ids, ['qty','oli','jasa','kompensasi'], 10),
           }, multi='sums'), 
        'total_oli': fields.function(_amount_line, string='Total Oli', digits_compute= dp.get_precision('Account'), store = {
           'dym.collecting.kpb.line': (lambda self, cr, uid, ids, c={}: ids, ['qty','oli','jasa','kompensasi'], 10),
           }, multi='sums'), 
        'total_kompensasi': fields.function(_amount_line, string='Total Kompensasi Oli', digits_compute= dp.get_precision('Account'), store = {
           'dym.collecting.kpb.line': (lambda self, cr, uid, ids, c={}: ids, ['qty','oli','jasa','kompensasi'], 10),
           }, multi='sums'), 
        'amount': fields.function(_amount_line, string='Amount', digits_compute= dp.get_precision('Account'), store = {
           'dym.collecting.kpb.line': (lambda self, cr, uid, ids, c={}: ids, ['qty','oli','jasa','kompensasi'], 10),
           }, multi='sums'), 
        'wo_ids': fields.many2many('dym.work.order','collect_line_wo_rel','collect_line_id','wo_id', 'Work Order Reference'),
    }    

