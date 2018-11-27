from openerp import models, api, _, workflow, SUPERUSER_ID
from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.exceptions import Warning as UserError, RedirectWarning

class dym_proses_birojasa(models.Model):
    _inherit = "dym.proses.birojasa"
    
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
            amount_real = 0.0
            if estimasi or progressive:
                amount_real = engine.amount_real
            else:
                engine.amount_real = 0.0

            koreksi = (estimasi + progressive) - amount_real
            res[engine.id]['total_approval_koreksi'] = koreksi
            res[engine.id]['amount_tax'] = tax
            res[engine.id]['amount_untaxed'] = tagihan
            res[engine.id]['total_koreksi'] = koreksi
            res[engine.id]['total_estimasi'] = estimasi
            res[engine.id]['total_progressive'] = progressive
            res[engine.id]['amount_total'] = estimasi + progressive
            res[engine.id]['tax_base'] = tax_base
            # self.browse(cr, uid, ids, context=context)._recalculate_withholding()
        return res
    
    def _get_engine(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('dym.proses.birojasa.line').browse(cr, uid, ids, context=context):
            result[line.proses_biro_jasa_id.id] = True
        return result.keys()

    _columns = {
        'amount_real': fields.float(string='Real Tagihan', digits_compute=dp.get_precision('Account')),
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
            # store={
            #     'dym.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
            #     'dym.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            # },
            multi='sums', help="The total amount."),
        'total_koreksi': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Koreksi',
            # store={
            #     'dym.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
            #     'dym.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            # },
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
        'tax_base': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tax Base',
            store={
                'dym.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'dym.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."),
    }
    
    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_bj = self.browse(cr, uid, ids, context=context)
        if obj_bj.total_approval_koreksi!=0:
            raise osv.except_osv(('Perhatian !'), ("Total koreksi harus sama dengan nol!"))
        if obj_bj.name == '/':
            values = {
                'name': self.pool.get('ir.sequence').get_per_branch(cr, uid, obj_bj.branch_id.id, 'TBJ', division='Unit')        
            }
            self.write(cr, uid, ids, values, context=context)

        obj_matrix = self.pool.get("dym.approval.matrixbiaya")
        if not obj_bj.proses_birojasa_line:
            raise osv.except_osv(('Perhatian !'), ("Engine belum diisi"))
        obj_matrix.request(cr, uid, ids, obj_bj, 'total_approval_koreksi')
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True

    @api.cr_uid_ids_context
    def onchange_total_amount_real(self, cr, uid, ids, amount_real, amount_total, context=None):
        obj_bj = self.browse(cr, uid, ids)
        total_koreksi = 0.0
        result = {}

        total_koreksi = amount_total - amount_real
        result['value'] = {
            'total_koreksi': total_koreksi,
            'total_approval_koreksi': total_koreksi
        }
        return result

    @api.multi
    def button_dummy(self):
        self.check_price_bbn()
        return True

    @api.multi
    def check_price_bbn(self):
        for x in self.proses_birojasa_line:
            result = {}
            value = {}
            lot_obj = self.env['stock.production.lot']
            lot = lot_obj.search([('id','=',x.name.id)]) 
            type_selection = str(self.type)
            so = self.env['dealer.sale.order']
            so_search = so.search([
                ('id','=',lot.dealer_sale_order_id.id)
            ])
            pajak = self.env['dym.branch'].browse(self.branch_id.id).pajak_progressive
            if lot : 
                total_jasa = 0
                total_notice = 0
                total_estimasi = 0
                total_tagihan = 0
                # total_koreksi = 0
                city = lot.cddb_id.city_id.id
                if not city :
                    raise osv.except_osv(_('Error!'),
                        _('Mohon lengkapi data kota untuk customer CDDB %s')%(lot.customer_stnk.name)) 
                if not lot.plat :
                    raise osv.except_osv(_('Error!'),
                        _('Tipe plat untuk %s belum diset, mohon diset di Master Serial Number!')%(lot.name)) 
                    
                biro_line = self.env['dealer.spk']._get_harga_bbn_detail(self.partner_id.id, lot.plat, city, lot.product_id.product_tmpl_id.id, self.branch_id.id)
                if not biro_line :
                    raise osv.except_osv(_('Error!'),
                        _('Harga BBN untuk nomor mesin %s type %s alamat %s tidak ditemukan, mohon cek master harga bbn yang tersedia!' % (lot.name, lot.product_id.product_tmpl_id.name,lot.cddb_id.city_id.name) ))
                x.total_estimasi = biro_line.total
                x.total_tagihan = biro_line.total + x.pajak_progressive
                x.total_jasa = biro_line.jasa
                x.total_notice = biro_line.notice

    @api.multi
    def wkf_request_approval(self):
        res = super(dym_proses_birojasa, self).wkf_request_approval()
        text_warning = ""
        for line in self.proses_birojasa_line:
            if not line.titipan:
                text_warning += ("\n - %s" % line.name.name)
        if text_warning:
            raise osv.except_osv(('Perhatian !'), ("Titipan untuk engine dibawah ini tidak boleh kosong! %s") % text_warning)
        if self.total_koreksi != 0:
            raise osv.except_osv(('Perhatian !'), ("Total koreksi harus sama dengan nol!"))
        return res

class dym_proses_birojasa_line(models.Model):
    _inherit = "dym.proses.birojasa.line"

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {
                'koreksi': 0.0,
                'titipan': 0.0,
                'margin': 0.0,
            }
            koreksi = (line.total_tagihan or 0.0) -  (line.total_estimasi or 0.0) -  (line.pajak_progressive or 0.0)
            if line.is_opbal:
                opbal_obj = self.pool.get('opbal.customer.deposit')
                titipan_stnk_id = opbal_obj.search(cr, uid, [('engine_id','=',line.name.id)], context=context)
                if not titipan_stnk_id:
                    return res
                titipan_stnk = opbal_obj.browse(cr, uid, titipan_stnk_id, context=context)
                titipan = titipan_stnk.amount or 0.0
                if not titipan:
                    return res
            else:
                model = 'dealer.sale.order.line'
                obj_ids = self.pool.get(model).search(cr, uid, [('dealer_sale_order_line_id','=',line.name.dealer_sale_order_id.id),('lot_id','=',line.name.id)], limit=1)
                if not obj_ids:
                    model = 'dym.retur.jual.line'
                    obj_ids = self.pool.get(model).search(cr, uid, [('dso_line_id.dealer_sale_order_line_id','=',line.name.dealer_sale_order_id.id),('retur_lot_id','=',line.name.id),('retur_id.state','not in',['draft','cancel'])], limit=1)
                obj = self.pool.get(model).browse(cr, uid, obj_ids)
                titipan = obj.price_bbn or 0.0
                if not titipan:
                    return res
            margin = titipan - (line.total_tagihan or 0.0) + (line.pajak_progressive or 0.0) + (line.total_jasa or 0.0)
            # print "margin = titipan - total_estimasi + pajak_progressive + total_jasa", margin,titipan,line.total_estimasi,line.pajak_progressive,line.total_jasa
            res[line.id]['koreksi'] = koreksi
            res[line.id]['titipan'] = titipan
            res[line.id]['margin'] = margin
        return res

    _columns = {
        # 'proses_stnk_id': fields.many2one('dym.proses.stnk', string='No Proses STNK'),
        'proses_stnk_id': fields.related('name', 'proses_stnk_id', relation='dym.proses.stnk', type='many2one', string='No Proses STNK',readonly=True),
        'total_tagihan_show': fields.related('total_tagihan', type='float', string='Total Tagihan',digits_compute=dp.get_precision('Account')),
        'is_opbal': fields.related(
                'proses_biro_jasa_id', 'is_opbal', type='boolean',
                relation='dym.proses.birojasa', string='OBL', readonly=False),
        'koreksi': fields.function(_amount_line, digits_compute=dp.get_precision('Account'), string='Koreksi', multi='sums', help="Koreksi.", track_visibility='always'),
        'margin': fields.function(_amount_line, digits_compute=dp.get_precision('Account'), string='Margin', multi='sums', help="Margin."),
        'titipan': fields.function(_amount_line, digits_compute=dp.get_precision('Account'), string='Titipan', multi='sums', help="Titipan."),
    }

    @api.cr_uid_ids_context
    def onchange_engine(self, cr, uid, ids, name,branch_id,partner_id,type):
        if not branch_id or not partner_id or not type:
            raise osv.except_osv(('No Branch Defined!'), ('Sebelum menambah detil transaksi,\n harap isi branch , type dan Biro Jasa terlebih dahulu.'))
        result = {}
        value = {}
        dom = {}
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
            total_tagihan = 0
            # total_koreksi = 0
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
            total_tagihan = total_estimasi
            total_jasa = biro_line.jasa + biro_line.jasa_area
            total_notice = biro_line.notice

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
                    'total_tagihan':total_tagihan,
                    'total_jasa':total_jasa,
                    'total_notice':total_notice,
                    'type':type_selection,
                    'no_notice_copy':lot_browse.no_notice,
                    'tgl_notice_copy':lot_browse.tgl_notice,
                    'pajak_progressive_branch':pajak,
                    'tgl_notice_rel':lot_browse.tgl_notice,
                    'no_notice_rel':lot_browse.no_notice,
                    'proses_stnk_id': lot_browse.proses_stnk_id.id,
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
                    'total_tagihan':total_tagihan,
                    'type':type_selection,
                    'total_jasa':total_jasa,
                    'total_notice':total_notice,
                    'pajak_progressive_branch':pajak,
                    'no_notice_copy':lot_browse.no_notice_copy,
                    'tgl_notice_copy':lot_browse.tgl_notice_copy,
                    'tgl_notice_rel':lot_browse.tgl_notice_copy,
                    'no_notice_rel':lot_browse.no_notice_copy,
                    'proses_stnk_id': lot_browse.proses_stnk_id.id,
                }
            dom['proses_stnk_id'] = [('id','=',lot_browse.proses_stnk_id.id)]

        result['domain'] = dom
        result['value'] = value
        return result
        
    def onchange_total_tagihan(self, cr, uid, ids, name, total_tagihan, total_estimasi, pajak_progressive, is_opbal, context=None):
        if not all([name,total_tagihan]):
            return False
        value = {
            'total_tagihan': 0.0,
            'koreksi': 0.0,
            'titipan': 0.0,
            'margin': 0.0,
        }
        engine_id = self.pool.get('stock.production.lot').browse(cr, uid, name, context=context)
        # city = engine_id.cddb_id.city_id.id
        # biro_line = self.pool.get('dealer.spk')._get_harga_bbn_detail(cr, uid, ids, partner_id, engine_id.plat, city, engine_id.product_id.product_tmpl_id.id, branch_id)
        koreksi = (total_tagihan or 0.0) -  (total_estimasi or 0.0) -  (pajak_progressive or 0.0)
        if is_opbal:
            opbal_obj = self.pool.get('opbal.customer.deposit')
            titipan_stnk_id = opbal_obj.search(cr, uid, [('engine_id','=',engine_id.id)], context=context)
            if not titipan_stnk_id:
                return {
                    'warning': {
                            'title': _('Error!'), 
                            'message': _('Nomor mesin %s tidak ditemukan di tabel opbal titipan stnk. Mohon isi di Advance Setting > Opbal Setting > Titipan STNK' % engine_id.name)
                        }, 
                    'value': {
                        'total_tagihan': 0.0
                    }
                }
            titipan_stnk = opbal_obj.browse(cr, uid, titipan_stnk_id, context=context)
            titipan = titipan_stnk.amount or 0.0
            if not titipan:
                return {
                    'warning': {
                            'title': _('Error!'), 
                            'message': _('Titipan STNK untuk nomor mesin %s sebesar nol. Mohon isi di Advance Setting > Opbal Setting > Titipan STNK' % engine_id.name)
                        }, 
                    'value': {
                        'total_tagihan': 0.0
                    }
                }
        else:
            titipan = 0.0
            model = 'dealer.sale.order.line'
            obj_ids = self.pool.get(model).search(cr, uid, [('dealer_sale_order_line_id','=',engine_id.dealer_sale_order_id.id),('lot_id','=',engine_id.id)], limit=1)
            if not obj_ids:
                model = 'dym.retur.jual.line'
                obj_ids = self.pool.get(model).search(cr, uid, [('dso_line_id.dealer_sale_order_line_id','=',engine_id.dealer_sale_order_id.id),('retur_lot_id','=',engine_id.id),('retur_id.state','not in',['draft','cancel'])], limit=1)
            obj = self.pool.get(model).browse(cr, uid, obj_ids)
            titipan = obj.price_bbn or 0.0
            if not titipan:
                return {
                    'warning': {
                            'title': _('Error!'), 
                            'message': _('Titipan STNK untuk nomor mesin %s sebesar nol. Mungkin ini data dari Opbal, coba centang field OBL, kemudian tekan update!' % engine_id.name)
                        }, 
                    'value': {
                        'total_tagihan': 0.0
                    }
                }
        tagihan = (total_estimasi or 0.0) + (pajak_progressive or 0.0)
        # margin = titipan - tagihan + (pajak_progressive or 0.0) + (tbj_line.total_jasa or 0.0)
        margin = titipan - tagihan + (pajak_progressive or 0.0)
        value['total_tagihan'] = tagihan
        value['total_tagihan_show'] = tagihan
        value['koreksi'] = koreksi
        value['titipan'] = titipan
        value['margin'] = margin
        return {
            'value': value,
        }

    @api.one
    @api.onchange('is_opbal')
    def onchange_is_opbal(self):
        engine_id = self.env['stock.production.lot'].browse(self.name.id)
        koreksi = (self.total_tagihan or 0.0) -  (self.total_estimasi or 0.0) - (self.pajak_progressive or 0.0)
        titipan = 0.0
        if self.is_opbal:
            opbal_obj = self.env['opbal.customer.deposit']
            titipan_stnk_id = opbal_obj.search([('engine_id','=',engine_id.id)])
            if not titipan_stnk_id:
                self.total_tagihan = 0.0
                raise osv.except_osv(('Perhatian !'), ('Nomor mesin %s tidak ditemukan di tabel opbal titipan stnk. Mohon isi di Advance Setting > Opbal Setting > Titipan STNK' % engine_id.name))
            titipan_stnk = opbal_obj.browse(titipan_stnk_id.id)
            titipan = titipan_stnk.amount or 0.0
            if not titipan:
                self.total_tagihan = 0.0
                raise osv.except_osv(('Perhatian !'), ('Titipan STNK untuk nomor mesin %s sebesar nol. Mohon isi di Advance Setting > Opbal Setting > Titipan STNK' % engine_id.name))
        tagihan = (self.total_estimasi or 0.0) + (self.pajak_progressive or 0.0)
        margin = titipan - tagihan + (self.pajak_progressive or 0.0)
        self.total_tagihan = tagihan
        self.total_tagihan_show = tagihan
        self.koreksi = koreksi
        self.titipan = titipan
        self.margin = margin

