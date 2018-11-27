import time
from datetime import datetime
from openerp import workflow
from openerp.osv import fields, osv, orm
import openerp.addons.decimal_precision as dp
from openerp import netsvc, api, SUPERUSER_ID
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
from lxml import etree
from openerp.osv.orm import setup_modifiers

class wiz_proses_birojasa_line(orm.TransientModel):
    _name = 'wiz.proses.birojasa.line'
    _description = "Proses Birojasa Line Wizard"
        
    _columns = {
        'proses_birojasa_id': fields.many2one('dym.proses.birojasa', string='Proses Birojasa'),
        'lot_ids': fields.many2many('stock.production.lot','wiz_proses_birojasa_line_lot_rel','wiz_proses_birojasa_id','lot_id','Engine Number'),
    }

    _defaults = {
        'proses_birojasa_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("Data Error, please try to refresh page or contact your administrator!"))
        res = super(wiz_proses_birojasa_line, self).default_get(cr, uid, fields, context=context)
        return res

    def lot_change(self, cr, uid, ids, proses_birojasa_id, context=None):
        domain = {}
        proses = self.pool.get('dym.proses.birojasa').browse(cr, uid, proses_birojasa_id)
        saved_lot_ids = proses.proses_birojasa_line.mapped('name').ids
        domain['lot_ids'] = [('no_notice','!=',False),('tgl_proses_stnk','!=',False),('proses_biro_jasa_id','=',False),('state_stnk','=','proses_stnk'),('branch_id','=',proses.branch_id.id),('biro_jasa_id','=',proses.partner_id.id),('id','not in',saved_lot_ids)]
        return {'domain':domain}

    def save_lot_ids(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for data in self.browse(cr, uid, ids, context=context):
            for lot in data.lot_ids:
                lot_change_vals = self.pool.get('dym.proses.birojasa.line').onchange_engine(cr, uid, ids, lot.id, data.proses_birojasa_id.branch_id.id, data.proses_birojasa_id.partner_id.id, data.proses_birojasa_id.type)
                if 'warning' in lot_change_vals and lot_change_vals['warning']:
                    raise osv.except_osv((lot_change_vals['warning']['title']), (lot_change_vals['warning']['message']))
                lot_change_vals['value']['proses_biro_jasa_id'] = data.proses_birojasa_id.id
                lot_change_vals['value']['name'] = lot.id
                res = {
                    'proses_birojasa_line': [[0, data.proses_birojasa_id.id, lot_change_vals['value']]]
                }
                data.proses_birojasa_id.write(res)
        return True

class dym_proses_birojasa(osv.osv):
    _name = "dym.proses.birojasa"
    _description = "Tagihan Biro Jasa"
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('confirmed', 'Waiting Approval'),
        ('approved','Process Confirmed'),
        ('except_invoice', 'Invoice Exception'),
        ('done','Done'),
        ('cancel','Cancelled')
    ] 

    def get_sin_spa_tbj(self,cr,uid,ids,field_name, arg, context=None):
        user_brw = self.pool.get('res.users').browse(cr, uid, uid)
        user_branch_type = user_brw.branch_type

        res = {}

        if user_branch_type == 'HO':
            uid = SUPERUSER_ID
        else:
            uid = uid
        for item in self.browse(cr, uid, ids):
            spa_test = False
            if item.state != 'draft':
                for y in item:
                    sin_id = self.pool.get('account.invoice').search(cr, uid,[('name', '=', y.name),('number','like','SIN%')])
                    sin = self.pool.get('account.invoice').browse(cr, uid, sin_id)
                    if sin.state in ('open','paid'):
                        for spa_ids in sin.payment_ids:
                            if spa_ids:
                                spa_id = self.pool.get('account.voucher').search(cr, uid,[('number', '=', spa_ids.move_id.name)])
                                spa = self.pool.get('account.voucher').browse(cr, uid, spa_id)
                                if spa:
                                    spa_test = spa.id
            res[item.id] = spa_test
        return res

    def get_sin(self,cr,uid,origin,context=None):
        sin_id = self.pool.get('account.invoice').search(cr, uid,[('origin', '=', origin),('number','like','SIN%')])
        sin = self.pool.get('account.invoice').browse(cr, uid, sin_id)
        return sin.number

    def get_paymentstatus(self,cr,uid,origin,context=None):
         if not origin:
            return ''
         invoice_ids = self.pool.get('account.invoice').search(cr,uid,[('origin','=',origin)])
         invoice = self.pool.get('account.invoice').browse(cr,uid,invoice_ids[0])
         if invoice.state == 'paid':
            return 'Paid'
            
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

    @api.model
    def _recalculate_withholding(self):
        if self.withholding_ids:
            tax_base = sum([x.total_jasa for x in self.proses_birojasa_line])    
            for line in self.withholding_ids:
                line.write({
                            'tax_base': tax_base,
                            'amount': line.get_tax_amount(), 
                            })
        return True

    def _amount_line_tax(self,cr , uid, line, context=None):
        val=0.0
        for c in self.pool.get('account.tax').compute_all(cr,uid, line.tax_id, line.total_jasa+line.total_notice,1)['taxes']:
            val +=c.get('amount',0.0)
        return val
    
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for engine in self.browse(cr, uid, ids, context=context):
            res[engine.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'total_approval_koreksi': 0.0,
                'total_koreksi':0.0,
                'total_estimasi':0.0,
                'total_progressive':0.0,
                'tax_base':0.0
            }
            koreksi = nilai = nilai_2 = estimasi = tagihan = progressive =  tax = tax_base = 0.0
           
            for line in engine.proses_birojasa_line:
                koreksi += line.koreksi  
                nilai = abs(line.koreksi)
                nilai_2 += nilai
                estimasi += line.total_estimasi
                tagihan += line.total_tagihan
                progressive += line.pajak_progressive
                tax += self._amount_line_tax(cr, uid, line, context=context)
                tax_base += line.total_jasa
            res[engine.id]['total_approval_koreksi'] = nilai_2
            res[engine.id]['amount_tax'] = tax
            res[engine.id]['amount_untaxed'] =tagihan
            res[engine.id]['total_koreksi'] =koreksi
            res[engine.id]['total_estimasi'] =estimasi
            res[engine.id]['total_progressive'] = progressive
            res[engine.id]['amount_total'] = koreksi + estimasi + progressive
            res[engine.id]['tax_base'] = tax_base
            self.browse(cr, uid, engine.id, context=context)._recalculate_withholding()
        return res
    
    def _get_engine(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('dym.proses.birojasa.line').browse(cr, uid, ids, context=context):
            result[line.proses_biro_jasa_id.id] = True
        return result.keys()

    @api.depends('proses_birojasa_line.name')
    def _amount_engine_all(self):
        for ib in self:
            amount_total = 0.0
            for line in ib.proses_birojasa_line:
                ib.update({
                    'total_record': len(ib.proses_birojasa_line),
                })

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    _columns = {
        'branch_id': fields.many2one('dym.branch', string='Branch', required=True),
        'no_spa':fields.function(get_sin_spa_tbj, type="many2one", relation="account.voucher", string='SPA Reff'),
        'division':fields.selection([('Unit','Showroom')], 'Division', change_default=True, select=True),
        'name': fields.char('No Reference', readonly=True),
        'tanggal': fields.date('Tanggal'),
        'state': fields.selection(STATE_SELECTION, 'State', readonly=True),
        'proses_birojasa_line': fields.one2many('dym.proses.birojasa.line','proses_biro_jasa_id',string="Table Permohonan Faktur"), 
        'partner_id':fields.many2one('res.partner','Biro Jasa'),
        'tgl_dok':fields.date('Supplier Invoice Date'),
        'no_dok' : fields.char('Supplier Invoice Number'),
        'description' : fields.char('Description'),
        'type' : fields.selection([('reg', 'REG'),('adv', 'ADV')], 'Type'),
        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'dym.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'dym.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'dym.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'dym.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Tagihan',
            store={
                'dym.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'dym.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."),
        'total_approval_koreksi': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Approval Koreksi',
            store={
                'dym.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'dym.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."),
        'total_koreksi': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Koreksi',
            store={
                'dym.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'dym.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."),
        'total_estimasi': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Estimasi',
            store={
                'dym.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'dym.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."),  
        'total_progressive': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Progresif',
            store={
                'dym.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'dym.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."),                               
        'note' : fields.text('Note..'),
        'invoiced': fields.boolean('Invoiced', readonly=True, copy=False),
        'invoice_method': fields.selection([('order','Based on generated draft invoice')], 'Invoicing Control', required=True,
            readonly=True),
        'document_copy':fields.boolean('Document Copy'),
        'engine_no': fields.related('proses_birojasa_line', 'name', type='char', string='No Engine'),
        'customer_stnk': fields.related('proses_birojasa_line', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
        'tax_id': fields.many2one('account.tax', string='Taxes'),
        'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
        'confirm_date':fields.datetime('Confirmed on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),  
        'tax_base': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tax Base',
            store={
                'dym.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'dym.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."), 
        'total_record' : fields.integer(string='Total Engine', store=True, readonly=True, compute='_amount_engine_all'),
    }

    _defaults = {
        'name': '/',
        'tanggal': fields.date.context_today,
        'tgl_dok': fields.date.context_today,
        'type':'reg',
        'state':'draft',
        'division' : 'Unit',
        'invoice_method':'order',
        'invoiced': 0,
        'document_copy':True,
        'branch_id': _get_default_branch,
     }

    def get_harga_cetakan(self, cr, uid, nosin, context=None):
        hargabirojasa_obj = self.pool.get('dym.harga.birojasa')
        hargabirojasa_ids = hargabirojasa_obj.search(cr,uid,[
                            ('branch_id','=',nosin.branch_id.id),
                            ('birojasa_id','=',nosin.biro_jasa_id.id)
                            ])
        hargabirojasa_browse = hargabirojasa_obj.browse(cr,uid,hargabirojasa_ids[0])

        bbnline_obj = self.pool.get('dym.harga.bbn.line')
        bbnline_ids = bbnline_obj.search(cr,uid,[
                            ('bbn_id','=',hargabirojasa_browse.harga_bbn_id.id)
                            ])

        bbnlinedetail_obj = self.pool.get('dym.harga.bbn.line.detail')
        bbnlinedetail_ids = bbnlinedetail_obj.search(cr,uid,[
                            ('harga_bbn_line_id','=',bbnline_ids),
                            ('city_id','=',nosin.cddb_id.city_id.id),
                            ('product_template_id','=',nosin.product_id.product_tmpl_id.id),
                            ])
        bbnlinedetail_browse = bbnlinedetail_obj.browse(cr,uid,bbnlinedetail_ids)
        return bbnlinedetail_browse
    
    def create(self, cr, uid, vals, context=None):
        # Cek Total Tagihan & Koreksi Create
        lot_pool = self.pool.get('stock.production.lot')
        line_pool = self.pool.get('dym.proses.birojasa.line')
        if 'proses_birojasa_line' in vals:
            tagihan_nol = []
            koreksi = []
            for item in vals['proses_birojasa_line']:
                lot_obj = lot_pool.browse(cr, uid, item[2]['name'])
                cek_koreksi = (item[2]['total_tagihan'] or 0.0) -  (item[2]['total_estimasi'] or 0.0) -  (item[2]['pajak_progressive'] or 0.0)
                if item[2]['total_tagihan'] == 0:
                    tagihan_nol.append(lot_obj.name)
                if cek_koreksi != 0:
                    koreksi.append(lot_obj.name)
            wrn_tagihan = ""
            wrn_koreksi = ""
            if tagihan_nol:
                wrn_tagihan = "\n- Total Tagihan tidak boleh nol pada nomor mesin: \n%s" % '\n '.join(tagihan_nol)
            if koreksi:
                wrn_koreksi = "\n- Koreksi harus nol pada nomor mesin: \n%s" % '\n '.join(koreksi)
            if koreksi or tagihan_nol:
                raise osv.except_osv(('Perhatian !'), (wrn_tagihan+wrn_koreksi))

        lot_proses = []
        for x in vals['proses_birojasa_line']:
            lot_proses.append(x.pop(2))
        lot_pool = self.pool.get('stock.production.lot')
        proses_pool = self.pool.get('dym.proses.birojasa.line')
        # vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'TBJ', division='Unit')        
        vals['tanggal'] = time.strftime('%Y-%m-%d'),
        del[vals['proses_birojasa_line']]
        proses_id = super(dym_proses_birojasa, self).create(cr, uid, vals, context=context) 
        if proses_id :         
            for x in lot_proses :
                lot_search = lot_pool.search(cr,uid,[
                            ('id','=',x['name'])
                            ])
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                lot_browse.write({
                       'proses_biro_jasa_id':proses_id,
                       })   
                if 'no_notice_copy' in x:
                    no_notice = x['no_notice_copy']
                    tgl_notice = x['tgl_notice_copy']
                elif lot_browse.no_notice_copy:
                    no_notice = lot_browse.no_notice_copy
                    tgl_notice = lot_browse.tgl_notice_copy
                else:
                    no_notice = lot_browse.no_notice
                    tgl_notice = lot_browse.tgl_notice
                if 'pajak_progressive' not in x:
                    x['pajak_progressive'] = 0
                proses_pool.create(cr, uid, {
                    'name':lot_browse.id,
                    'proses_biro_jasa_id':proses_id,
                    'customer_stnk':lot_browse.customer_stnk.id,
                    'tgl_notice':x['tgl_notice'],
                    'no_notice':x['no_notice'],
                    'tgl_notice_copy':tgl_notice,
                    'no_notice_copy':no_notice,                                            
                    'total_estimasi':x['total_estimasi'],
                    'total_jasa':x['total_jasa'],
                    'total_notice':x['total_notice'],
                    'pajak_progressive':x['pajak_progressive'],
                    'total_tagihan':x['total_tagihan'],
                    'pajak_progressive_branch':x['pajak_progressive_branch'],
                })
        return proses_id
    
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Proses Biro Jasa sudah di post ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')
        lot_search = lot_pool.search(cr,uid,[
                                           ('proses_biro_jasa_id','=',ids)
                                           ])
        lot_browse = lot_pool.browse(cr,uid,lot_search)
        for x in lot_browse :
            x.write({
                'tgl_proses_birojasa': False,
                'no_notice_copy': False,
                'tgl_notice_copy':False,
                'total_jasa':False,
                'total_notice':False,
            })

        return super(dym_proses_birojasa, self).unlink(cr, uid, ids, context=context)
    
    
    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def wkf_confirm_birojasa(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = datetime.today()
        self.write(cr, uid, ids, {'state': 'approved','tanggal':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})
        for x in val.proses_birojasa_line :
            lot_search = lot_pool.search(cr,uid,[
                ('id','=',x.name.id)
                ])
            lot_browse = lot_pool.browse(cr,uid,lot_search)
            lot_browse.write({
                'tgl_proses_birojasa':val.tanggal,
                'no_notice_copy': x.no_notice_copy,
                'tgl_notice_copy':x.tgl_notice_copy,
                'total_jasa':x.total_jasa,
                'total_notice':x.total_notice,
                })   
          
        return True
   
    def wkf_action_cancel(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        for x in val.proses_birojasa_line :
            lot_search = lot_pool.search(cr,uid,[
                        ('id','=',x.name.id)
                        ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                lot_browse.write({
                                  'proses_biro_jasa_id': False,
                                  'tgl_proses_birojasa':False,
                                  'no_notice_copy':False,
                                  'tgl_notice_copy':False,
                                  'total_jasa':False,
                                  'total_notice':False,
                                })
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        return True

    def wkf_approve_order(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'approved' })
        return True
    
    def write(self, cr, uid, ids, vals, context=None):
        # Cek Total Tagihan & Koreksi Write
        lot_pool = self.pool.get('stock.production.lot')
        line_pool = self.pool.get('dym.proses.birojasa.line')
        if 'proses_birojasa_line' in vals:
            tagihan_nol = []
            koreksi = []
            for item in vals['proses_birojasa_line']:
                item_obj = line_pool.browse(cr, uid, item[1])

                lot_id = item_obj.name.id
                total_tagihan = item_obj.total_tagihan
                total_estimasi = item_obj.total_estimasi
                pajak_progressive = item_obj.pajak_progressive

                if item[2]:
                    lot_id = item[2]['name'] if 'name' in item[2] else item_obj.name.id
                    total_tagihan = item[2]['total_tagihan'] if 'total_tagihan' in item[2] else item_obj.total_tagihan
                    total_estimasi = item[2]['total_estimasi'] if 'total_estimasi' in item[2] else item_obj.total_estimasi
                    pajak_progressive = item[2]['pajak_progressive'] if 'pajak_progressive' in item[2] else item_obj.pajak_progressive
                
                lot_obj = lot_pool.browse(cr, uid, lot_id)
                cek_koreksi = (total_tagihan or 0.0) -  (total_estimasi or 0.0) -  (pajak_progressive or 0.0)
                
                if total_tagihan == 0:
                    tagihan_nol.append(lot_obj.name)
                if cek_koreksi != 0:
                    koreksi.append(lot_obj.name)
            wrn_tagihan = ""
            wrn_koreksi = ""
            if tagihan_nol:
                wrn_tagihan = "\n- Total Tagihan tidak boleh nol pada nomor mesin: \n%s" % '\n '.join(tagihan_nol)
            if koreksi:
                wrn_koreksi = "\n- Koreksi harus nol pada nomor mesin: \n%s" % '\n '.join(koreksi)
            if koreksi or tagihan_nol:
                raise osv.except_osv(('Perhatian !'), (wrn_tagihan+wrn_koreksi))

        if context is None:
            context = {}
        vals.get('proses_birojasa_line',[]).sort(reverse=True)

        collect = self.browse(cr,uid,ids)
        lot_penerimaan = []
        lot_pool = self.pool.get('stock.production.lot')
        line_pool = self.pool.get('dym.proses.birojasa.line')
        lot = vals.get('proses_birojasa_line', False)
        
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
                    lot_browse.write({
                        'proses_biro_jasa_id': False,
                        'tgl_proses_birojasa':False,
                        'no_notice_copy':False,
                        'tgl_notice_copy':False,
                        'total_jasa':False,
                        'total_notice':False,
                    })
                        
                elif item[0] == 0 :
                    values = item[2]
                    lot_search = lot_pool.search(cr,uid,[
                                                        ('id','=',values['name'])
                                                        ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
                    
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                           'proses_biro_jasa_id':collect.id,
                           }) 

                    if 'no_notice_copy' in values:
                        no_notice = values['no_notice_copy']
                        tgl_notice = values['tgl_notice_copy']
                    elif lot_browse.no_notice_copy:
                        no_notice = lot_browse.no_notice_copy
                        tgl_notice = lot_browse.tgl_notice_copy
                    else:
                        no_notice = lot_browse.no_notice
                        tgl_notice = lot_browse.tgl_notice

                    values['no_notice_copy'] = no_notice
                    values['tgl_notice_copy'] = tgl_notice
                    
        return super(dym_proses_birojasa, self).write(cr, uid, ids, vals, context=context)
    
    def wkf_set_to_draft(self,cr,uid,ids):
        return self.write({'state':'draft'})       
     
    def action_invoice_create(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        engine_obj = self.pool.get('stock.production.lot')
        obj_inv = self.pool.get('account.invoice')
        total_jasa = 0.00
        total_notice = 0.00
        estimasi = 0.00
        invoice_id = {}
        move_line_obj = self.pool.get('account.move.line')
        #ACCOUNT 
        config = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',val.branch_id.id),
                                                                ])
        invoice_bbn = {}

        if config :
            config_browse = self.pool.get('dym.branch.config').browse(cr,uid,config)
            progressive_debit_account = config_browse.tagihan_birojasa_progressive_journal_id.default_debit_account_id.id  
            progressive_credit_account = config_browse.tagihan_birojasa_progressive_account_id.id
            bbn_debit_account_id = config_browse.tagihan_birojasa_bbn_account_id.id 
            bbn_credit_account_id = config_browse.tagihan_birojasa_bbn_journal_id.default_credit_account_id.id  
            bbn_jual_id = config_browse.dealer_so_account_bbn_jual_id.id  
            journal_birojasa = config_browse.tagihan_birojasa_bbn_journal_id.id
            journal_progressive = config_browse.tagihan_birojasa_progressive_journal_id.id,
            if not journal_birojasa or not journal_progressive or not progressive_credit_account or not progressive_debit_account or not bbn_debit_account_id or not bbn_credit_account_id  or not bbn_jual_id:
                raise osv.except_osv(_('Attention!'),
                    _('Jurnal Pajak Progressive atau Jurnal BBN Beli belum lengkap, harap isi terlebih dahulu didalam branch config'))   
                             
        elif not config :
            raise osv.except_osv(_('Error!'),
                _('Please define Journal in Setup Division for this branch: "%s".') % \
                (val.branch_id.name))
                              
        move_list = []
        if val.amount_total < 1: 
            raise osv.except_osv(_('Attention!'),
                _('Mohon periksa kembali detail tagihan birojasa.')) 
        analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, 'Unit', False, 4, 'Sales')
        analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, val.branch_id, 'Unit', False, 4, 'General')
        birojasa_id = obj_inv.create(cr,uid, {
            'name':val.name,
            'origin': val.name,
            'branch_id':val.branch_id.id,
            'division':val.division,
            'partner_id':val.partner_id.id,
            'date_invoice':val.tanggal,
            'reference_type':'none',
            'account_id':bbn_credit_account_id,
            'comment':val.note,
            'type': 'in_invoice',
            'supplier_invoice_number' : val.no_dok,
            'journal_id' : journal_birojasa,
            'document_date' : val.tgl_dok,
            'analytic_1': analytic_1_general,
            'analytic_2': analytic_2_general,
            'analytic_3': analytic_3_general,
            'analytic_4': analytic_4_general,
        })   
        obj_line = self.pool.get('account.invoice.line') 
        invoice_bbn_ids = []
        total_titipan = 0
        move_bbn_partner = {}
        move_bbn_ids = []
        move_ids = []
        for x in val.proses_birojasa_line :
            pajak_progressive_id = False
            if x.pajak_progressive > 0.00 :
                customer_name = str(x.name.customer_id.name)       
                engine_no = str(x.name.name)                     
                string = "Pajak Progresif a/n \'%s\', No Engine \'%s\' !" % (customer_name,engine_no)
                inv_pajak_progressive_id = obj_inv.create(cr,uid, {
                    'name':string,
                    'qq_id':x.name.customer_stnk.id,
                    'origin': val.name,
                    'branch_id':val.branch_id.id,
                    'division':val.division,
                    'partner_id':x.name.customer_id.id,
                    'date_invoice':val.tanggal,
                    'reference_type':'none',
                    'account_id':progressive_debit_account,
                    'type': 'out_invoice',
                    'supplier_invoice_number' : val.no_dok,
                    'journal_id':journal_progressive,
                    'document_date' : val.tgl_dok,
                    'analytic_1': analytic_1_general,
                    'analytic_2': analytic_2_general,
                    'analytic_3': analytic_3_general,
                    'analytic_4': analytic_4_general,
                    'invoice_line':[[0,False,{
                        'account_id':progressive_credit_account,
                        'partner_id':x.name.customer_id.id,
                        'name': string,
                        'quantity': 1,
                        'origin': val.name,
                        'price_unit':x.pajak_progressive  or 0.00,
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id': analytic_4,
                    }]]
                })       
                obj_inv.signal_workflow(cr, uid, [inv_pajak_progressive_id], 'invoice_open' ) 
                pajak_progressive_id = inv_pajak_progressive_id
                
            engine_obj.write(cr,uid,[x.name.id],{'inv_pajak_progressive_id':pajak_progressive_id,'inv_proses_birojasa':birojasa_id})

            inv_line_id = False
            if x.name.dealer_sale_order_id.finco_id and x.name.dealer_sale_order_id.is_credit == True:
                inv_line_id = obj_line.search(cr,uid,[
                    ('invoice_id.origin', 'ilike', x.name.dealer_sale_order_id.name),
                    ('invoice_id.partner_id', 'in', [x.name.dealer_sale_order_id.partner_id.id,x.name.dealer_sale_order_id.finco_id.id]),
                    ('invoice_id.tipe','=','finco'),
                    '|',('account_id', '=', bbn_jual_id),('invoice_id.account_bbn', '=', bbn_jual_id),
                    ], limit=1)
            else:
                inv_line_id = obj_line.search(cr,uid,[
                    ('invoice_id.origin', 'ilike', x.name.dealer_sale_order_id.name),
                    ('invoice_id.partner_id', '=', x.name.dealer_sale_order_id.partner_id.id),
                    ('invoice_id.tipe','=','customer'),
                    '|',('account_id', '=', bbn_jual_id),('invoice_id.account_bbn', '=', bbn_jual_id),
                    ], limit=1)
            invoice_line = obj_line.browse(cr, uid, inv_line_id)
            if invoice_line:
                obj_line.create(cr,uid, {
                    'invoice_id':birojasa_id,
                    'account_id':bbn_jual_id,
                    'partner_id':x.name.customer_id.id,
                    'name': 'Total Titipan ' + x.name.customer_id.name + ' ' + x.name.name,
                    'quantity': 1,
                    'origin': val.name,
                    'price_unit': x.titipan,
                    'analytic_1': analytic_1_general,
                    'analytic_2': analytic_2_general,
                    'analytic_3': analytic_3_general,
                    'account_analytic_id': analytic_4_general,
                    'tagihan_birojasa': x.total_tagihan,
                    'force_partner_id': x.name.customer_id.id,
                    })
                if invoice_line.invoice_id.move_id.id not in move_ids:
                    move_bbn_id = self.pool.get('account.move.line').search(cr, uid, [('account_id','=',bbn_jual_id),('move_id','=',invoice_line.invoice_id.move_id.id),('credit','>',0)])
                    self.pool.get('account.move.line').write(cr, uid, move_bbn_id, {'partner_id':x.name.customer_id.id})
                    move_ids.append(invoice_line.invoice_id.move_id.id)
                    if x.name.customer_id not in move_bbn_partner:
                        move_bbn_partner[x.name.customer_id] = []
                    move_bbn_partner[x.name.customer_id] += move_bbn_id
                bbn_res = {}
                bbn_res['lot_id'] = x.name
                bbn_res['partner_id'] = x.name.customer_id
                bbn_res['amount'] = x.titipan
                invoice_bbn_ids.append(bbn_res)
                total_titipan += x.titipan
        obj_line.create(cr,uid, {
            'invoice_id':birojasa_id,
            'account_id':bbn_debit_account_id,
            'partner_id':val.partner_id.id,
            'name': 'Total Pendapatan STNK',
            'quantity': 1,
            'origin': val.name,
            'price_unit': (val.amount_total - total_titipan) or 0.00,
            'analytic_1': analytic_1,
            'analytic_2': analytic_2,
            'analytic_3': analytic_3,
            'account_analytic_id': analytic_4,
            }) 
           
        obj_inv.signal_workflow(cr, uid, [birojasa_id], 'invoice_open' ) 
        birojasa_inv = obj_inv.browse(cr, uid, [birojasa_id])
        move_line_ids = []
        for bbn in invoice_bbn_ids:
            move_line_ids = move_line_obj.search(cr,uid,[
                ('name','=','Total Titipan ' + bbn['partner_id'].name + ' ' + bbn['lot_id'].name),
                ('invoice','=',birojasa_id),
                ('account_id','=',bbn_jual_id),
                ('move_id','=',birojasa_inv.move_id.id),
                ('partner_id','=',bbn['partner_id'].id),
                ('debit','=',bbn['amount']),
                ], limit=1)
            move_line_obj.write(cr, uid, move_line_ids, {'partner_id':bbn['partner_id'].id})
            if move_line_ids and bbn['partner_id'] in move_bbn_partner:
                reconcile_id = move_line_obj.reconcile_partial(cr, uid, move_line_ids + move_bbn_partner[bbn['partner_id']], 'auto')

        return birojasa_id 
        
    def invoice_done(self, cr, uid, ids, context=None):
        for birojasa in self.pool.get('dym.proses.birojasa').browse(cr,uid,ids):
            birojasa.write({'invoiced':True})
            for x in birojasa.proses_birojasa_line :
                tanggal = datetime.now()
                x.name.write({'tgl_bayar_birojasa':tanggal})
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return True
    
    def view_invoice(self,cr,uid,ids,context=None):  
        val = self.browse(cr, uid, ids, context={})[0]
        obj_inv = self.pool.get('account.invoice')
        
        obj = obj_inv.search(cr,uid,[
                                     ('origin','ilike',val.name),
                                     ('type','=','in_invoice')
                                     ])
        obj_hai = obj_inv.browse(cr,uid,obj).id
        return {
            'name': 'Supplier Invoice',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': obj_hai
        }
    
    
class dym_proses_birojasa_line(osv.osv):
    _name = "dym.proses.birojasa.line"

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {
                'koreksi': 0.0,
                'titipan': 0.0,
                'margin': 0.0,
            }
            koreksi = (line.total_tagihan or 0.0) -  (line.total_estimasi or 0.0) -  (line.pajak_progressive or 0.0)
            mod_obj = self.pool.get('dealer.sale.order.line')
            if mod_obj:
                obj_ids = mod_obj.search(cr, uid, [('dealer_sale_order_line_id','=',line.name.dealer_sale_order_id.id),('lot_id','=',line.name.id)], limit=1)
                if not obj_ids:
                    mod_obj = self.pool.get('dym.retur.jual.line')
                    obj_ids = mod_obj.search(cr, uid, [('dso_line_id.dealer_sale_order_line_id','=',line.name.dealer_sale_order_id.id),('retur_lot_id','=',line.name.id),('retur_id.state','not in',['draft','cancel'])], limit=1)
                obj = mod_obj.browse(cr, uid, obj_ids)
                titipan = obj.price_bbn or 0.0
                margin = titipan - (line.total_tagihan or 0.0) + (line.pajak_progressive or 0.0)
                res[line.id]['koreksi'] = koreksi
                res[line.id]['titipan'] = titipan
                res[line.id]['margin'] = margin
        return res

    def onchange_price(self,cr,uid,ids,price_unit):
        value = {'total_estimasi_fake':0}
        if price_unit:
            value.update({'total_estimasi_fake':price_unit})  
        return {'value':value}
    
    def _get_estimasi(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.read(cr, uid, ids, ['total_estimasi']):
            price_unit_show = price['total_estimasi']
            res[price['id']] = price_unit_show
        return res
    
    def _pajak_progressive(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.read(cr, uid, ids, ['total_estimasi']):
            price_unit_show = price['total_estimasi']
            res[price['id']] = price_unit_show   
        return res    

    def print_invoice_pajak_progressive(self, cr, uid, ids, context=None):
        invoice_obj = self.pool.get('account.invoice')
        for data in self.browse(cr, uid, ids, context=context):
            nosin = data.name.name
            if not data.pajak_progressive_branch:            
                raise osv.except_osv(_('Attention!'),
                    _('Baris ini tidak memiliki pajak progressive.')) 
            if not data.pajak_progressive:            
                raise osv.except_osv(_('Attention!'),
                    _('Baris ini tidak memiliki nilai pajak progressive.')) 
            cr.execute("select id from account_invoice where type='out_invoice' and origin='"+data.proses_biro_jasa_id.name+"' and name ilike '%%"+nosin+"%%'")
            res = cr.fetchone()
            if res:
                invoices = invoice_obj.browse(cr, uid, res, context=context)
            else:
                raise osv.except_osv(_('Attention!'),
                    _('Tidak ditemukan Invoice atas pajak progressive ini.')) 
            return invoices.invoice_print()

    _columns = {
        'name' : fields.many2one('stock.production.lot','No Engine',domain="[('no_notice','!=',False),('tgl_proses_stnk','!=',False),('proses_biro_jasa_id','=',False),('state_stnk','=','proses_stnk'),('branch_id','=',parent.branch_id),('biro_jasa_id','=',parent.partner_id),('exclude_proses_birojasa','=',False)]",change_default=True,),
        'proses_biro_jasa_id' : fields.many2one('dym.proses.birojasa','Proses Biro Jasa'),
        'customer_id':fields.related('name','customer_id',type='many2one',relation='res.partner',readonly=True,string='Customer'),
        'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
        'tgl_notice' : fields.date('Tgl JTP Notice'),
        'no_notice' : fields.char('No Notice'),
        'tgl_notice_copy' : fields.date('Tgl JTP Notice'),
        'no_notice_copy' : fields.char('No Notice'),
        'total_estimasi' : fields.float('Total Estimasi',digits_compute=dp.get_precision('Account')),
        'total_estimasi_fake' : fields.function(_get_estimasi,string='Total Estimasi',digits_compute=dp.get_precision('Account')),
        'total_jasa' : fields.float('Jasa',digits_compute=dp.get_precision('Account')),
        'total_notice' : fields.float('Notice',digits_compute=dp.get_precision('Account')),
        'pajak_progressive' : fields.float('Pajak Progresif',digits_compute=dp.get_precision('Account')),
        'total_tagihan' : fields.float('Total Tagihan',digits_compute=dp.get_precision('Account')),
        'tax_id': fields.many2many('account.tax', 'prose_birojasa_tax', 'proses_birojasa_line', 'tax_id', 'Taxes'),
        'type' : fields.selection([('reg', 'REG'),('adv', 'ADV')], 'Type',readonly=True),
        'pajak_progressive_branch' : fields.boolean(string="Pajak Progressive"),
        'no_notice_rel':fields.related('name','no_notice',type='char',readonly=True,string='No Notice REL'),
        'tgl_notice_rel':fields.related('name','tgl_notice',type='date',readonly=True,string='Tgl JTP Notice REL'),
        'koreksi': fields.function(_amount_line, digits_compute=dp.get_precision('Account'), string='Koreksi', multi='sums', help="Koreksi.", track_visibility='always'),
        'margin': fields.function(_amount_line, digits_compute=dp.get_precision('Account'), string='Margin', multi='sums', help="Margin."),
        'titipan': fields.function(_amount_line, digits_compute=dp.get_precision('Account'), string='Titipan', multi='sums', help="Titipan."),
    }

    _sql_constraints = [
    ('unique_name_proses_biro_jasa_id', 'unique(name,proses_biro_jasa_id)', 'Detail Engine duplicate, mohon cek kembali !'),
]    
    def onchange_notice(self,cr,uid,ids,notice,tgl,doc):
        value = {}
        if notice :
            notice = notice.replace(' ', '').upper()
            value = {
                'no_notice_copy':notice,
            }            
        if not doc :
            if notice :
                value = {
                    'no_notice_copy':notice,
                    'no_notice':notice,
                }
            if tgl :
                value = {'tgl_notice':tgl}
        return {'value':value} 
    
    def onchange_total_tagihan(self, cr, uid, ids, name, total_tagihan, total_estimasi, pajak_progressive, context=None):
        if not all([name,total_tagihan]):
            return False
        value = {
            'koreksi': 0.0,
            'titipan': 0.0,
            'margin': 0.0,
        }
        koreksi = (total_tagihan or 0.0) -  (total_estimasi or 0.0) -  (pajak_progressive or 0.0)
        this = self.browse(cr, uid, ids, context=context)

        # For opbal only
        titipan = 0.0
        model = 'dealer.sale.order.line'
        engine_id = self.pool.get('stock.production.lot').browse(cr, uid, [name], context=context)
        obj_ids = self.pool.get(model).search(cr, uid, [('dealer_sale_order_line_id','=',engine_id.dealer_sale_order_id.id),('lot_id','=',engine_id.id)], limit=1)
        if not obj_ids:
            model = 'dym.retur.jual.line'
            obj_ids = self.pool.get(model).search(cr, uid, [('dso_line_id.dealer_sale_order_line_id','=',engine_id.dealer_sale_order_id.id),('retur_lot_id','=',engine_id.id),('retur_id.state','not in',['draft','cancel'])], limit=1)
        obj = self.pool.get(model).browse(cr, uid, obj_ids)
        titipan = obj.price_bbn or 0.0

        margin = titipan - (total_tagihan or 0.0) + (pajak_progressive or 0.0)
        value['koreksi'] = koreksi
        value['titipan'] = titipan
        value['margin'] = margin
        return {
            'value': value,
        }

    def onchange_engine(self, cr, uid, ids, name,branch_id,partner_id,type):
        if not branch_id or not partner_id or not type:
            raise osv.except_osv(('No Branch Defined!'), ('Sebelum menambah detil transaksi,\n harap isi branch , type dan Biro Jasa terlebih dahulu.'))
        result = {}
        value = {}
        val = self.browse(cr,uid,ids)
        lot_obj = self.pool.get('stock.production.lot')
        lot_search = lot_obj.search(cr,uid,[('id','=',name)])
        lot_browse = lot_obj.browse(cr,uid,lot_search)  
        type_selection = str(type)
        so = self.pool.get('dealer.sale.order')
        so_search = so.search(cr,uid,[
            ('id','=',lot_browse.dealer_sale_order_id.id)
        ])
        so_browse = so.browse(cr,uid,so_search)
        pajak = self.pool.get('dym.branch').browse(cr,uid,branch_id).pajak_progressive
        if name : 
            total_jasa = 0
            total_notice = 0
            total_estimasi = 0
            city = lot_browse.cddb_id.city_id.id
            if not city :
                raise osv.except_osv(_('Error!'),
                    _('Mohon lengkapi data kota untuk customer CDDB %s')%(lot_browse.customer_stnk.name)) 
            if not lot_browse.plat :
                raise osv.except_osv(_('Error!'),
                    _('Tipe plat untuk %s belum diset, mohon diset di Master Serial Number!')%(lot_browse.name)) 
                
            biro_line = self.pool.get('dealer.spk')._get_harga_bbn_detail(cr, uid, ids, partner_id, lot_browse.plat, city, lot_browse.product_id.product_tmpl_id.id,branch_id)
            if not biro_line :
                raise osv.except_osv(_('Error!'),
                    _('Harga BBN untuk nomor mesin %s type %s alamat %s tidak ditemukan, mohon cek master harga bbn yang tersedia!' % (lot_browse.name, lot_browse.product_id.product_tmpl_id.name,lot_browse.cddb_id.city_id.name) ))                 
            total_estimasi = biro_line.total
            total_jasa = biro_line.jasa + biro_line.jasa_area
            total_notice = biro_line.notice
            
            print "====onchange_engine====>",biro_line.jasa, biro_line.jasa_area, total_jasa

            if lot_browse.no_notice_copy == False :
                value = {
                    'customer_id':lot_browse.customer_id.id,
                    'customer_stnk':lot_browse.customer_stnk.id,
                    'tgl_notice':lot_browse.tgl_notice,
                    'no_notice':lot_browse.no_notice,
                    'tgl_stnk':lot_browse.tgl_stnk,
                    'no_stnk':lot_browse.no_stnk,
                    'no_polisi':lot_browse.no_polisi,
                    'total_estimasi':total_estimasi,
                    'total_jasa':total_jasa,
                    'total_notice':total_notice,
                    'type':type_selection,
                    'no_notice_copy':lot_browse.no_notice,
                    'tgl_notice_copy':lot_browse.tgl_notice,
                    'pajak_progressive_branch':pajak,
                    'tgl_notice_rel':lot_browse.tgl_notice,
                    'no_notice_rel':lot_browse.no_notice,
                }
            elif lot_browse.no_notice_copy :
                value = {
                    'customer_id':lot_browse.customer_id.id,
                    'customer_stnk':lot_browse.customer_stnk.id,
                    'tgl_notice':lot_browse.tgl_notice_copy,
                    'no_notice':lot_browse.no_notice_copy,
                    'tgl_stnk':lot_browse.tgl_stnk,
                    'no_stnk':lot_browse.no_stnk,
                    'no_polisi':lot_browse.no_polisi,
                    'total_estimasi':total_estimasi,
                    'type':type_selection,
                    'total_jasa':total_jasa,
                    'total_notice':total_notice,
                    'pajak_progressive_branch':pajak,
                    'no_notice_copy':lot_browse.no_notice_copy,
                    'tgl_notice_copy':lot_browse.tgl_notice_copy,
                    'tgl_notice_rel':lot_browse.tgl_notice_copy,
                    'no_notice_rel':lot_browse.no_notice_copy,
                }
            
        result['value'] = value
        return result

class invoice_line_birojasa(osv.osv):
    _inherit = 'account.invoice.line'

    _columns = {
        'tagihan_birojasa':fields.float('Tagihan Birojasa',digits_compute=dp.get_precision('Account')),
    }

class invoice_birojasa(osv.osv):
    _inherit = 'account.invoice'

    def invoice_pay_customer(self, cr, uid, ids, context=None):
        if not ids: return []
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_dialog_form')
   
        inv = self.browse(cr, uid, ids[0], context=context)    
        tanggal = datetime.now()

        if inv.type == "in_invoice" :
            birojasa = self.pool.get('dym.proses.birojasa')
            birojasa_search = birojasa.search(cr,uid,[
                ('name','=',inv.origin.split(' ') or '')
            ], limit=1)
            birojasa_browse = birojasa.browse(cr,uid,birojasa_search)
            if birojasa_search :
                birojasa_browse.write({'invoiced':True})
                for x in birojasa_browse.proses_birojasa_line :
                    lot = self.pool.get('stock.production.lot')
                    lot_search = lot.search(cr,uid,[('id','=',x.name.id)])
                    if lot_search :
                        lot_browse = lot.browse(cr,uid,lot_search)
                        lot_browse.write({'tgl_bayar_birojasa':tanggal})          
        return {
            'name':_("Pay Invoice"),
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
                'default_reference': inv.name,
                'close_after_process': True,
                'invoice_type': inv.type,
                'invoice_id': inv.id,
                'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
            }
        }        