import time
import base64
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID, api
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
import sys

class stock_production_lot(osv.osv):
    _inherit = 'stock.production.lot'

    def _get_branches(self, cr, uid, ids, name, args, context, where =''):
        branch_ids = self.pool.get('res.users').browse(cr, uid, uid).branch_ids.ids
        result = {}
        for val in self.browse(cr, uid, ids):
            result[val.id] = True if val.branch_id.id in branch_ids else False
        return result

    def _cek_branches(self, cr, uid, obj, name, args, context):
        branch_ids = self.pool.get('res.users').browse(cr, uid, uid).branch_ids.ids
        return [('branch_id', 'in', branch_ids)]

    _columns = {
        'is_mybranch': fields.function(_get_branches, string='Is My Branches', type='boolean', fnct_search=_cek_branches),
        # 'sales_ahm_code':fields.related('serial_number_ids','sales_ahm_code',type='char',readonly=True,string='AHM Code Sales'),
    }

class dym_permohonan_faktur_reject(osv.osv):
    _name = "dym.permohonan.faktur.reject"
    _columns = {
        'permohonan_faktur_id' : fields.many2one('dym.permohonan.faktur','Permohonan Faktur'),
        'name' : fields.many2one('stock.production.lot','Engine No'),
        'chassis_no':fields.char('Chassis Number'),
        'product_id': fields.many2one('product.product', 'Product'),
        'customer_id': fields.many2one('res.partner', 'Customer'),
        'customer_stnk': fields.many2one('res.partner', 'Customer STNK'),
        'state': fields.selection([('intransit', 'Intransit'),('titipan','Titipan'),('stock', 'Stock'), ('reserved','Reserved'),('sold','Sold'), ('paid', 'Paid'),('sold_offtr','Sold.offtr'),('paid_offtr','Paid.offtr'),('workshop','Workshop')], 'State'),
        'date':fields.date('Date'),
    }

class dym_reject_faktur_line(osv.osv_memory):
    _name = "dym.reject.faktur.line"

    _columns = {
        'reject_faktur_id': fields.many2one('dym.reject.faktur', 'Reject ID'),
        'serial_id': fields.many2one('stock.production.lot', 'Engine No'),
        'chassis_no':fields.char('Chassis Number'),
        'product_id': fields.many2one('product.product', 'Product'),
        'customer_id': fields.many2one('res.partner', 'Customer'),
        'customer_stnk': fields.many2one('res.partner', 'Customer STNK'),
        'state': fields.selection([('intransit', 'Intransit'),('titipan','Titipan'),('stock', 'Stock'), ('reserved','Reserved'),('sold','Sold'), ('paid', 'Paid'),('sold_offtr','Sold.offtr'),('paid_offtr','Paid.offtr'),('workshop','Workshop')], 'State'),
    }

class dym_reject_faktur(osv.osv_memory):
    _name = "dym.reject.faktur"
    _columns = {
                'permohonan_faktur_id': fields.many2one('dym.permohonan.faktur', string='Request Faktur', required=True),
                'serial_number_ids': fields.one2many('dym.reject.faktur.line','reject_faktur_id',string="Table Permohonan Faktur"), 
                }   
    _defaults = {
                'permohonan_faktur_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("You may only process one request at a time!"))
        res = super(dym_reject_faktur, self).default_get(cr, uid, fields, context=context)
        request_id = context and context.get('active_id', False) or False
        request = self.pool.get('dym.permohonan.faktur').browse(cr, uid, request_id, context=context)

        serial_number_ids = []

        if 'serial_number_ids' in fields and request.serial_number_ids:
            for serial in request.serial_number_ids:
                serial_number_ids.append({'serial_id': serial.id,'name': serial.name,'chassis_no': serial.chassis_no,'product_id': serial.product_id.id,'customer_id': serial.customer_id.id,'customer_stnk': serial.customer_stnk.id,'state': serial.state})
            res.update({'serial_number_ids': serial_number_ids})
        return res

    def do_reject_faktur(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for data in self.browse(cr, uid, ids, context=context):
            for reject_line in data.serial_number_ids:
                if (reject_line.serial_id.penerimaan_faktur_id and reject_line.serial_id.penerimaan_faktur_id.state == 'posted')or reject_line.serial_id.penerimaan_notice_id or reject_line.serial_id.proses_stnk_id or reject_line.serial_id.penerimaan_stnk_id or reject_line.serial_id.penerimaan_bpkb_id or reject_line.serial_id.proses_biro_jasa_id :
                    raise osv.except_osv(('Perhatian !'), ("No faktur engine \'%s\' telah diproses, data tidak bisa di reject!")%(reject_line.serial_id.name))                    
                else:
                    self.pool.get('dym.permohonan.faktur.reject').create(cr, uid, {
                                 'name':reject_line.serial_id.id,
                                 'chassis_no':reject_line.serial_id.chassis_no,
                                 'customer_stnk':reject_line.serial_id.customer_stnk.id,
                                 'customer_id':reject_line.serial_id.customer_id.id,
                                 'product_id':reject_line.serial_id.product_id.id,
                                 'state':reject_line.serial_id.state,
                                 'permohonan_faktur_id':data.permohonan_faktur_id.id,
                                 'date': datetime.today()
                                })
                    if reject_line.serial_id.penerimaan_faktur_id:
                        line_pool = self.pool.get('dym.penerimaan.faktur.line')
                        line_search = line_pool.search(cr,uid,[('name','=',reject_line.serial_id.id),('penerimaan_faktur_id','=',reject_line.serial_id.penerimaan_faktur_id.id)])                        
                        line_pool.unlink(cr,uid,line_search, context=context)
                    reject_line.serial_id.write({'state_stnk': False,'tgl_faktur':False,'permohonan_faktur_id':False,'tgl_terima':False,'penerimaan_faktur_id':False,'faktur_stnk':False,'tgl_cetak_faktur':False})
        return {}

class Eksport_cddb(osv.osv_memory):
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids

    _name = "eksport.cddb"
    _columns = {
                'type': fields.selection((('cddb','CDDB'), ('udstk','UDSTK'), ('udsls','UDSLS')), 'File'),
                'name': fields.char('File Name', 35),
                'data_file': fields.binary('File'),
                }   
    _defaults = {
                'type' :'cddb',
                'branch_id': _get_default_branch,
                }
    
    def export_file(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        trx_id = context.get('active_id',False) 
        trx_obj = self.pool.get('dym.permohonan.faktur').browse(cr,uid,trx_id,context=context)
 
        if val.type == 'cddb' :
            result = self.eksport_cddb(cr, uid, ids, trx_obj,context)
        elif val.type == 'udstk' :
            result = self.eksport_udstk(cr, uid, ids, trx_obj,context)
        elif val.type == 'udsls' :
            result = self.eksport_udsls(cr, uid, ids, trx_obj,context)
        
        
        form_id  = 'view.wizard.eksport.cddb'
 
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                                                             ("name", "=", form_id), 
                                                             ("model", "=", 'eksport.cddb'),
                                                             ])
     
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'eksport.cddb',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }
        
    def eksport_cddb(self, cr, uid, ids,trx_obj, context=None):
        result = ''
        kodeMD = ''
        kodeDealer = ''
        for x in trx_obj.serial_number_ids :
            if not x.cddb_id :
                raise osv.except_osv(('Perhatian !'), ("Customer CDDB belum diisi dalam nomor mesin %s")%(x.name))                
            date = x.cddb_id.birtdate
            if not date :
                raise osv.except_osv(('Perhatian !'), ("Tanggal lahir belum diisi untuk CDDB %s")%(x.cddb_id.customer_id.name))
            if x.dealer_sale_order_id :
                lot_pool = self.pool.get('stock.production.lot') 
                
                original_domain_pic = [
                        ('name','=',x.name),
                        ('branch_id','!=',x.dealer_sale_order_id.branch_id.id)
                        ]
                original_lot_search_pic = lot_pool.search(cr,uid,original_domain_pic)

                #if pic
                if original_lot_search_pic:
                    original_lot_browse_pic = lot_pool.browse(cr,uid,original_lot_search_pic)
                    if original_lot_browse_pic.sudo().branch_id.pimpinan_id.sales_ahm:
                        sales_ahm = original_lot_browse_pic.sudo().branch_id.pimpinan_id.sales_ahm
                        kodeDealer = original_lot_browse_pic.sudo().branch_id.ahm_code
                    else:    
                        sales_ahm = 'TA'
                        kodeDealer = original_lot_browse_pic.sudo().branch_id.ahm_code
                else:
                    sales_ahm = self.flp_id(cr, uid, ids, x.dealer_sale_order_id, context)
                    kodeDealer = x.sudo().pelanggaran_branch_ahm_code_test
                # sales_ahm = self.flp_id(cr, uid, ids, x.dealer_sale_order_id, context)
            elif not x.dealer_sale_order_id :
                sales_ahm = 'TA'
            bulan = str(date[5:7])
            tanggal = str(date[8:10])
            tahun = str(date[:4])
            new_date = tanggal+bulan+tahun
            no_telp = x.cddb_id.no_telp
            kecamatan = x.cddb_id.kecamatan
            if not x.cddb_id.kecamatan :
                kecamatan = x.cddb_id.kecamatan_id.name
            if not x.cddb_id.no_telp :
                no_telp = 01234
            
            alamat = str(x.cddb_id.street) + ' RT/RW.' + str(x.cddb_id.rt) + '/' + str(x.cddb_id.rw)
            ro_bd_id = ''
            ref_id = ''
            if x.cddb_id.ro_bd_id:
                ro_bd_id = x.cddb_id.ro_bd_id
            if x.cddb_id.ref_id:
                ref_id = x.cddb_id.ref_id

            if x.cddb_id.pekerjaan_id and x.cddb_id.pekerjaan_id2:
                result += x.name[:5] +' ;'+ x.name[5:12] +';'+ x.cddb_id.no_ktp +';'+ x.cddb_id.kode_customer +';'+ str(x.cddb_id.jenis_kelamin_id.value) +';'+ new_date+';'+ alamat+';'+ str(x.cddb_id.zip_id.code or '??') +';'+ str(kecamatan)+';'+ str(x.cddb_id.city_id.code)+';'+ str(x.cddb_id.zip_id.zip)+';'+ str(x.cddb_id.state_id.code)+';'+ str(x.cddb_id.agama_id.value)+';'+ str(x.cddb_id.pekerjaan_id2.value) +';'+ str(x.cddb_id.pengeluaran_id.value)+';'+ str(x.cddb_id.pendidikan_id.value)+';'+ str(x.cddb_id.penanggung_jawab)+';'+ str(x.cddb_id.no_hp)+';'+ str(no_telp)+';'+ str(x.cddb_id.dpt_dihubungi)+';'+ str(x.cddb_id.merkmotor_id.value)+';'+ str(x.cddb_id.jenismotor_id.value)+';'+ str(x.cddb_id.penggunaan_id.value)+';'+ str(x.cddb_id.pengguna_id.value)+';'+sales_ahm+';'+ str(x.cddb_id.status_rumah_id.value)+';'+ str(x.cddb_id.status_hp_id.value)+';'+ str(x.cddb_id.facebook or 'N')+';'+ str(x.cddb_id.twitter or 'N')+';'+ str(x.cddb_id.instagram or 'N')+';'+ str(x.cddb_id.youtube or 'N')+';'+str(x.cddb_id.hobi_id.value)+';'+ str(x.cddb_id.karakteristik or 'N')+';'+str(x.cddb_id.no_kk)+';'+str(x.cddb_id.wni_wna)+';'+str(ro_bd_id)+';'+str(ref_id)+';'
            elif x.cddb_id.pekerjaan_id and not x.cddb_id.pekerjaan_id2:
                result += x.name[:5] +' ;'+ x.name[5:12] +';'+ x.cddb_id.no_ktp +';'+ x.cddb_id.kode_customer +';'+ str(x.cddb_id.jenis_kelamin_id.value) +';'+ new_date+';'+ alamat+';'+ str(x.cddb_id.zip_id.code or '??') +';'+ str(kecamatan)+';'+ str(x.cddb_id.city_id.code)+';'+ str(x.cddb_id.zip_id.zip)+';'+ str(x.cddb_id.state_id.code)+';'+ str(x.cddb_id.agama_id.value)+';'+ str(x.cddb_id.pekerjaan_id.value) +';'+ str(x.cddb_id.pengeluaran_id.value)+';'+ str(x.cddb_id.pendidikan_id.value)+';'+ str(x.cddb_id.penanggung_jawab)+';'+ str(x.cddb_id.no_hp)+';'+ str(no_telp)+';'+ str(x.cddb_id.dpt_dihubungi)+';'+ str(x.cddb_id.merkmotor_id.value)+';'+ str(x.cddb_id.jenismotor_id.value)+';'+ str(x.cddb_id.penggunaan_id.value)+';'+ str(x.cddb_id.pengguna_id.value)+';'+sales_ahm+';'+ str(x.cddb_id.status_rumah_id.value)+';'+ str(x.cddb_id.status_hp_id.value)+';'+ str(x.cddb_id.facebook or 'N')+';'+ str(x.cddb_id.twitter or 'N')+';'+ str(x.cddb_id.instagram or 'N')+';'+ str(x.cddb_id.youtube or 'N')+';'+str(x.cddb_id.hobi_id.value)+';'+ str(x.cddb_id.karakteristik or 'N')+';'+str(x.cddb_id.no_kk)+';'+str(x.cddb_id.wni_wna)+';'+str(ro_bd_id)+';'+str(ref_id)+';'
            result += '\r\n'  
            # kodeDealer = x.sudo().pelanggaran_branch_ahm_code
        kodeMD = trx_obj.partner_id.ahm_code
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        if not kodeMD :
            raise osv.except_osv(('Perhatian !'), ("AHM kode Principle belum diisi di Data Customer."))
        if not kodeDealer :
            raise osv.except_osv(('Perhatian !'), ("AHM kode belum diisi di Master Branch."))
        user = self.pool.get('res.users').browse(cr, uid, uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)     
        start_date = start.strftime("%y%m%d%H%M")
        kode = str(kodeMD[:3]) +'-'+ str(kodeDealer) + '-'+str(tanggal) +'-'+ str(start_date)
        nama = kode + '.CDDB'
        out = base64.encodestring(result)
        cddb = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)
        
        return cddb
    
    def flp_id (self,cr,uid,ids,so,context=None):
        employeee_pool = self.pool.get('hr.employee')

        sales_ahm = False

        lot_pool = self.pool.get('stock.production.lot') 
                
        original_domain_pac = [
                ('sale_order_reserved','=',so.id)
                ]
        
        original_lot_search_pac = lot_pool.search(cr,uid,original_domain_pac)
        original_lot_browse_pac = lot_pool.browse(cr,uid,original_lot_search_pac)

        branch_id = original_lot_browse_pac.branch_id.id
        branch_id_pac = original_lot_browse_pac.original_location_id.branch_id.id

        dsol_branch_id = so.branch_id.id

        if dsol_branch_id == branch_id_pac:

            employee_search = so.employee_id.ids
            sales_ahm = False
            
            if employee_search :
                for x in employeee_pool.browse(cr,uid,employee_search) :
                    sales_ahm = x.sales_ahm
                    if sales_ahm :
                        break
            section_id = so.section_id
            while not sales_ahm :
                user_id = section_id.user_id and section_id.user_id.id or False
                if user_id :
                    search = section_id.user_id.ids
                    if search :
                        for x in employeee_pool.browse(cr,uid,employee_search) :
                            sales_ahm = x.sales_ahm
                            if sales_ahm :
                                break
                section_id = section_id.parent_id
                if not section_id and not sales_ahm:
                    sales_ahm = 'TA'

        else:
            if original_lot_browse_pac.sudo().original_location_id.branch_id.pimpinan_id.sales_ahm:
                sales_ahm = original_lot_browse_pac.sudo().original_location_id.branch_id.pimpinan_id.sales_ahm
            else:
                sales_ahm = 'TA'
                         
        return sales_ahm

    def eksport_udstk(self, cr, uid, ids,trx_obj, context=None):
        result = ''
        kodeMD = ''
        kodeDealer = ''
        sys.setrecursionlimit(10000)
        for x in trx_obj.serial_number_ids :
            alamat = str(x.customer_stnk.street_tab) + ' RT/RW.' + str(x.customer_stnk.rt_tab) + '/' + str(x.customer_stnk.rw_tab)
            kecamatan = x.cddb_id.kecamatan
            if not x.cddb_id.kecamatan :
                kecamatan = x.cddb_id.kecamatan_id.name

            lot_pool = self.pool.get('stock.production.lot') 
                
            original_domain_pic = [
                    ('name','=',x.name),
                    ('branch_id','!=',x.dealer_sale_order_id.branch_id.id)
                    ]
            original_lot_search_pic = lot_pool.search(cr,uid,original_domain_pic)

            #if pic
            if original_lot_search_pic:
                original_lot_browse_pic = lot_pool.browse(cr,uid,original_lot_search_pic)
                if original_lot_browse_pic:
                    kodeDealer = original_lot_browse_pic.sudo().branch_id.ahm_code
                else:    
                    kodeDealer = original_lot_browse_pic.sudo().branch_id.ahm_code
            else:
                sales_ahm = self.flp_id(cr, uid, ids, x.dealer_sale_order_id, context)
                kodeDealer = x.sudo().pelanggaran_branch_ahm_code_test
                
            result += x.chassis_no +';'+ x.name[:5] +' ;'+ x.name[5:12] +';'+ x.customer_stnk.name +';'+ alamat+';'+ str(x.cddb_id.zip_id.code or '??') +';'+ str(kecamatan)+';'+ str(x.cddb_id.city_id.code)+';'+ str(x.cddb_id.zip_id.zip)+';'+ str(x.cddb_id.state_id.code)+';'+str(x.jenis_penjualan)+';'+str(x.sudo().pelanggaran_branch_ahm_code)+';'
            result += '\r\n'  
            # kodeDealer = x.sudo().pelanggaran_branch_ahm_code
        kodeMD = trx_obj.partner_id.ahm_code
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        if not kodeMD :
            raise osv.except_osv(('Perhatian !'), ("AHM kode Principle belum diisi di Data Customer."))
        if not kodeDealer :
            raise osv.except_osv(('Perhatian !'), ("AHM kode belum diisi di Master Branch."))
        user = self.pool.get('res.users').browse(cr, uid, uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)    
        start_date = start.strftime("%y%m%d%H%M")
        kode = str(kodeMD[:3]) +'-'+ str(kodeDealer) + '-'+str(tanggal) +'-'+ str(start_date)
        nama = kode + '.UDSTK'
        out = base64.encodestring(result)
        udstk = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)
        
        return udstk
    
    def eksport_udsls(self, cr, uid, ids,trx_obj, context=None):
        result = ''
        kodeMD = ''
        kodeDealer = ''
        for x in trx_obj.serial_number_ids :
            # alamat = str(x.customer_stnk.street_tab) + ' RT/RW.' + str(x.customer_stnk.rt_tab) + '/' + str(x.customer_stnk.rw_tab)
            # kecamatan = x.cddb_id.kecamatan
            # if not x.cddb_id.kecamatan :
                # kecamatan = x.cddb_id.kecamatan_id.name
            if not x.invoice_date:
                raise osv.except_osv(('Perhatian !'), ("Tanggal invoice tidak ditemukan pada tabel Nomor Mesin, mungkin data penjualan diambil dari hasil import opbal. Silahkan hubungi sistem admin untuk melanjutkan."))

            date = x.invoice_date
            bulan = str(date[5:7])
            tanggal = str(date[8:10])
            tahun = str(date[:4])

            new_date = tanggal+bulan+tahun
            if not x.dealer_sale_order_id:
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan ID sale memo untuk Nomor Mesin %s, mungkin data penjualan diambil dari hasil import opbal. Silahkan hubungi sistem admin untuk melanjutkan." % x.name))

            dso = x.dealer_sale_order_id

            lot_pool = self.pool.get('stock.production.lot') 
                
            original_domain_pic = [
                    ('name','=',x.name),
                    ('branch_id','!=',x.dealer_sale_order_id.branch_id.id)
                    ]
            original_lot_search_pic = lot_pool.search(cr,uid,original_domain_pic)

            #if pic
            if original_lot_search_pic:
                original_lot_browse_pic = lot_pool.browse(cr,uid,original_lot_search_pic)
                if original_lot_browse_pic:
                    kodeDealer = original_lot_browse_pic.sudo().branch_id.ahm_code
                else:    
                    kodeDealer = original_lot_browse_pic.sudo().branch_id.ahm_code
            else:
                sales_ahm = self.flp_id(cr, uid, ids, x.dealer_sale_order_id, context)
                kodeDealer = x.sudo().pelanggaran_branch_ahm_code_test

            if not x.finco_id.ahm_code and x.finco_id:
                raise osv.except_osv(('Perhatian !'), ("AHM kode Finance Company belum diisi."))
            result += x.name[:5]+' '+x.name[5:12]+';'+ x.chassis_no +';'+ (x.finco_id.ahm_code or '') +';'+ x.cddb_id.kecamatan_id.code+';'+ str(x.tenor).split('.')[0]+';'+ str(x.dp).split('.')[0]+';'+ new_date+';'+ (dso.sales_source.code or '') +';'+ str(x.cddb_id.zip_id.zip)+';'+str(x.customer_stnk.name)+';'+str(x.cddb_id.jenis_kartu_id.value or 'N')+';'+str(x.cddb_id.sms_broadcast)+';'+str(x.cddb_id.no_hp)+';'+str(x.cddb_id.email or 'N')+';'+str(x.cicilan).split('.')[0]+';'+';'+';'+';'+';'
            result += '\r\n'
            # kodeDealer = x.sudo().pelanggaran_branch_ahm_code
        kodeMD = trx_obj.partner_id.ahm_code
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        if not kodeMD :
            raise osv.except_osv(('Perhatian !'), ("AHM kode Principle belum diisi di Data Customer."))
        if not kodeDealer :
            raise osv.except_osv(('Perhatian !'), ("AHM kode belum diisi di Master Branch."))
        user = self.pool.get('res.users').browse(cr, uid, uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)    
        start_date = start.strftime("%y%m%d%H%M")
        kode = str(kodeMD[:3]) +'-'+ str(kodeDealer) + '-'+str(tanggal) +'-'+ str(start_date)
        nama = kode + '.UDSLS'
        out = base64.encodestring(result)
        udsls = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)
        
        return udsls

class dym_permohonan_faktur(osv.osv):
    _name = 'dym.permohonan.faktur'
    _inherit = ['mail.thread']
    _description = "Permohonan Faktur"
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids    

    @api.depends('serial_number_ids.name')
    def _amount_all(self):
        for ib in self:
            amount_total = 0.0
            for line in ib.serial_number_ids:
                ib.update({
                    'total_record': len(ib.serial_number_ids),
                })
    
    _columns = {
        'branch_id': fields.many2one('dym.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Showroom')], 'Division', change_default=True, select=True),
        'name': fields.char('No Reference', readonly=True),
        'tgl_mohon_faktur': fields.date('Tanggal'),
        'state': fields.selection([('draft', 'Draft'),('waiting_for_approval','Waiting For Approval'), ('approved','Posted'),('confirmed', 'Waiting Approval'),('cancel','Canceled')], 'State', readonly=True),
        'serial_number_ids': fields.one2many('stock.production.lot','permohonan_faktur_id',string="Table Permohonan Faktur"), 
        'partner_id':fields.many2one('res.partner', string='Supplier', domain="[('principle','=',True)]"),
        'partner_md':fields.related('partner_id', type='many2one', relation='res.partner', string='Supplier', readonly=True),
        'ahm_code':fields.related('partner_id','ahm_code',type='char',readonly=True,string='AHM Code MD'),
        'engine_no': fields.related('serial_number_ids', 'name', type='char', string='No Engine'),
        'customer_stnk': fields.related('serial_number_ids', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),  
        'exception_faktur' : fields.boolean('Faktur Off The Road'),
        'pelwil' : fields.boolean('Unit Hasil Mutation Order'),
        'is_pic': fields.boolean('Unit Hasil PIC'),
        'confirm_uid':fields.many2one('res.users',string="Posted by"),
        'confirm_date':fields.datetime('Posted on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),          
        'reject_ids': fields.one2many('dym.permohonan.faktur.reject','permohonan_faktur_id',string="Reject Faktur History"), 
        'total_record' : fields.integer(string='Total Engine', store=True, readonly=True, compute='_amount_all'),
    }

    _defaults = {
        'name': '/',
        'branch_id': _get_default_branch,
        'tgl_mohon_faktur': fields.date.context_today,
        'state':'draft',
        'division' : 'Unit',
     }    
            
    def cancel_permohonan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        for x in val.serial_number_ids :
            lot_search = lot_pool.search(cr,uid,[
                        ('branch_id','=',val.branch_id.id),
                        ('permohonan_faktur_id','=',val.id),
                        ('name','=',x.name)
                        ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                if lot_browse.penerimaan_faktur_id or lot_browse.penerimaan_notice_id or lot_browse.proses_stnk_id or lot_browse.penerimaan_stnk_id or lot_browse.penerimaan_bpkb_id or lot_browse.proses_biro_jasa_id :
                    raise osv.except_osv(('Perhatian !'), ("No faktur engine \'%s\' telah diproses, data tidak bisa di cancel !")%(lot_browse.name))                    
                else : 
                    lot_browse.write({'state_stnk': False,'tgl_faktur':False,'permohonan_faktur_id':False})
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        self.message_post(cr, uid, val.id, body=_("Permohononan Faktur canceled "), context=context) 

        return True
    
    def reject_faktur(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        for x in val.serial_number_ids :
            lot_search = lot_pool.search(cr,uid,[
                        ('branch_id','=',val.branch_id.id),
                        ('permohonan_faktur_id','=',val.id),
                        ('name','=',x.name)
                        ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                if lot_browse.penerimaan_faktur_id or lot_browse.penerimaan_notice_id or lot_browse.proses_stnk_id or lot_browse.penerimaan_stnk_id or lot_browse.penerimaan_bpkb_id or lot_browse.proses_biro_jasa_id :
                    raise osv.except_osv(('Perhatian !'), ("No faktur engine \'%s\' telah diproses, data tidak bisa di cancel !")%(lot_browse.name))                    
                else : 
                    lot_browse.write({'state_stnk': False,'tgl_faktur':False,'permohonan_faktur_id':False})
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        self.message_post(cr, uid, val.id, body=_("Permohononan Faktur canceled "), context=context) 

        return True

    def post_permohonan(self,cr,uid,ids,context=None):                                
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        engine = ''
        tanggal = datetime.today()
        self.write(cr, uid, ids, {'state': 'approved','tgl_mohon_faktur':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})         
        for x in val.serial_number_ids :
            lot_search = lot_pool.search(cr,uid,[
                        ('branch_id','=',val.branch_id.id),
                        ('tgl_faktur','=',False),
                        ('state','!=',''),
                        ('name','=',x.name)
                        
                        ])
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                lot_browse.write({
                       'state_stnk':'mohon_faktur',
                       'tgl_faktur': val.tgl_mohon_faktur,
                       })
            engine += ('- '+str(x.name)+'<br/>')
        self.message_post(cr, uid, val.id, body=_("Permohononan Faktur posted <br/> No Engine : <br/>  %s ")%(engine), context=context)                 
        if val.name == '/':
            self.write(cr, uid, ids, {
                'name': self.pool.get('ir.sequence').get_per_branch(cr, uid, val.branch_id.id, 'PFA', division='Unit'),
            }, context=context)
        return True
    
    def onchange_exception(self,cr,uid,ids,exception_faktur,serial_number_ids,branch_id,partner_id,pelwil,is_pic,context=None):
        res = self.onchange_branch_permohonan_faktur(cr, uid, ids, branch_id=branch_id, exception=exception_faktur, pelwil=pelwil, partner_id=partner_id,is_pic=is_pic,context=context)
        value = {}
        if not exception_faktur:
            value = {
                'serial_number_ids' : False,
                # 'branch_id' : False,
                'partner_id' : False,
                'partner_md' : False,
                'ahm_code' : False,
                'sales_ahm' : False
            }
        res['value'].update(value)
        return res

    def onchange_branch_permohonan_faktur(self, cr, uid, ids, branch_id,exception,pelwil, partner_id,is_pic,context=None):
        line = self.pool.get('stock.production.lot')
        sales_ahm_id = 0
        sys.setrecursionlimit(10000)
        if ids :
            obj = self.browse(cr,uid,ids)
            for x in obj.serial_number_ids :
                line_search = line.search(cr,uid,[
                                      ('permohonan_faktur_id','=',obj.id)
                                      ])
                if line_search :
                    line_browse = line.browse(cr,uid,line_search)
                    line_browse.write({
                                       'permohonan_faktur_id':False
                                       })
            
            
        if context is None:
            context = {}
        lot = []
        if branch_id and partner_id:
            lot_pool = self.pool.get('stock.production.lot')
            if not exception:
                if is_pic:
                    domain = [
                        ('branch_id','=',branch_id),
                        ('tgl_faktur','=',False),
                        ('permohonan_faktur_id','=',False),
                        ('lot_status_cddb','=','ok'),
                        '|',
                        ('state','=','paid'),
                        ('dealer_sale_order_id.mt_khusus','=',True)
                        ]
                    lot_search = lot_pool.search(cr,uid,domain)
                    
                    if not lot_search :
                        lot = []
                    elif lot_search :
                        lot_browse = lot_pool.browse(cr,uid,lot_search)
                        for x in lot_browse :
                            original_domain = [
                                        ('name','=',x.name),
                                        ('branch_id','!=',branch_id)
                                        ]
                            original_lot_search = lot_pool.search(cr,uid,original_domain)
                            if not original_lot_search :
                                lot = []
                            elif original_lot_search :
                                original_lot_browse = lot_pool.browse(cr,uid,original_lot_search)
                                for org in original_lot_browse :
                                    # pic
                                    lot.append([0,0,{
                                        'name':x.name,
                                        'chassis_no':x.chassis_no,
                                        'product_id':x.product_id.id,
                                        'dealer_sale_order_id' : x.dealer_sale_order_id,
                                        'customer_id':x.customer_id.id,
                                        'customer_stnk':x.customer_stnk.id,
                                        'state':x.state,
                                        # 'pelanggaran_branch_name':org.sudo().branch_id.name,
                                        # 'pelanggaran_branch_ahm_code':org.sudo().branch_id.ahm_code,
                                        # 'pelanggaran_branch_ahm_sales_code': org.sudo().branch_id.pimpinan_id.sales_ahm,
                                        'pelanggaran_branch_name_test':org.sudo().branch_id.name,
                                        'pelanggaran_branch_ahm_code_test':org.sudo().branch_id.ahm_code,
                                        'pelanggaran_branch_ahm_sales_code_test': org.sudo().branch_id.pimpinan_id.sales_ahm,
                                    }])
                else:
                    domain = [
                        ('branch_id','=',branch_id),
                        ('tgl_faktur','=',False),
                        ('permohonan_faktur_id','=',False),
                        ('lot_status_cddb','=','ok'),
                        '|',
                        ('state','=','paid'),
                        ('dealer_sale_order_id.mt_khusus','=',True)
                        ]
                    lot_search = lot_pool.search(cr,uid,domain)
                    
                    if not lot_search :
                        lot = []
                    elif lot_search :
                        lot_browse = lot_pool.browse(cr,uid,lot_search)
                        for x in lot_browse :
                            original_domain = [
                                        ('name','=',x.name)
                                        ]
                            original_lot_search = lot_pool.search(cr,uid,original_domain)
                            if not original_lot_search :
                                lot = []
                            elif original_lot_search :
                                original_lot_browse = lot_pool.browse(cr,uid,original_lot_search)
                                if len(original_lot_browse) == 1:
                                    if x.sudo().pelanggaran_supplier_id.id == partner_id and ((x.sudo().pelanggaran_branch_id.id != branch_id and pelwil) or (x.sudo().pelanggaran_branch_id.id == branch_id and not pelwil)):
                                        if pelwil :
                                            # pac
                                            lot.append([0, 0, {
                                                'name': x.name,
                                                'chassis_no': x.chassis_no,
                                                'product_id': x.product_id.id,
                                                'dealer_sale_order_id' : x.dealer_sale_order_id,
                                                'customer_id': x.customer_id.id,
                                                'customer_stnk': x.customer_stnk.id,
                                                'state': x.state,
                                                # 'pelanggaran_branch_name': x.sudo().pelanggaran_branch_name,
                                                # 'pelanggaran_branch_ahm_code': x.sudo().pelanggaran_branch_ahm_code,
                                                # 'pelanggaran_branch_ahm_sales_code': x.sudo().pelanggaran_branch_id.pimpinan_id.sales_ahm,
                                                'pelanggaran_branch_name_test': x.sudo().pelanggaran_branch_name,
                                                'pelanggaran_branch_ahm_code_test': x.sudo().pelanggaran_branch_ahm_code,
                                                'pelanggaran_branch_ahm_sales_code_test': x.sudo().pelanggaran_branch_id.pimpinan_id.sales_ahm,
                                            }])
                                        else:
                                            # not pac
                                            lot.append([0,0,{
                                                'name':x.name,
                                                'chassis_no':x.chassis_no,
                                                'product_id':x.product_id.id,
                                                'dealer_sale_order_id' : x.dealer_sale_order_id,
                                                'customer_id':x.customer_id.id,
                                                'customer_stnk':x.customer_stnk.id,
                                                'state':x.state,
                                                # 'pelanggaran_branch_name':x.sudo().pelanggaran_branch_name,
                                                # 'pelanggaran_branch_ahm_code':x.sudo().pelanggaran_branch_ahm_code,
                                                # 'pelanggaran_branch_ahm_sales_code': x.dealer_sale_order_id.employee_id.sales_ahm,
                                                'pelanggaran_branch_name_test':x.sudo().pelanggaran_branch_name,
                                                'pelanggaran_branch_ahm_code_test':x.sudo().pelanggaran_branch_ahm_code,
                                                'pelanggaran_branch_ahm_sales_code_test': x.dealer_sale_order_id.employee_id.sales_ahm,
                                            }])
            if exception :
                lot_search = lot_pool.search(cr,uid,[
                                            ('branch_id','=',branch_id),
                                            ('tgl_faktur','=',False),
                                            ('permohonan_faktur_id','=',False),
                                            ('lot_status_cddb','=','ok'),
                                            '|',('state','=','paid_offtr'),
                                            '&',('customer_id.is_group_customer','!=',False),
                                            '|',('state','=','sold'),
                                            ('state','=','sold_offtr')
                                            ])
                
                if not lot_search :
                    lot = []
                elif lot_search :
                    lot_browse = lot_pool.browse(cr,uid,lot_search)           
                    for x in lot_browse :
                        if x.sudo().pelanggaran_supplier_id.id == partner_id and ((x.sudo().pelanggaran_branch_id.id != branch_id and pelwil) or (x.sudo().pelanggaran_branch_id.id == branch_id and not pelwil)):
                            lot.append([0,0,{
                                             'name':x.name,                               
                                             'chassis_no':x.chassis_no,
                                             'product_id':x.product_id.id,
                                             'dealer_sale_order_id' : x.dealer_sale_order_id,
                                             'customer_id':x.customer_id.id,
                                             'customer_stnk':x.customer_stnk.id,
                                             'state':x.state,
                                             'pelanggaran_branch_name_test':x.sudo().pelanggaran_branch_name,
                                             'pelanggaran_branch_ahm_code_test':x.sudo().pelanggaran_branch_ahm_code,
                                             'pelanggaran_branch_ahm_sales_code_test': x.dealer_sale_order_id.employee_id.sales_ahm,
                            }])
        branch_search = self.pool.get('dym.branch').search(cr,uid,[('id','=',branch_id)])
        branch_browse = self.pool.get('dym.branch').browse(cr,uid,branch_search)

        partner_md = branch_browse.default_supplier_id.id
        if pelwil or is_pic:
            partner_md = partner_id
        partner = self.pool.get('res.partner').browse(cr, uid, partner_md)
        return {'value':{'serial_number_ids': lot,'partner_id':partner_md,'partner_md':partner_md,'ahm_code':partner.ahm_code}}


    '''    
    def onchange_branch_permohonan_faktur(self, cr, uid, ids, branch_id, exception, pelwil, partner_id, context=None):
        line = self.pool.get('stock.production.lot')
        
        print "######=======> ids=", ids, " branch_id=",branch_id, " exception=", exception, " pelwil=",pelwil, " partner_id=",partner_id

        sys.setrecursionlimit(10000)
        if ids :
            obj = self.browse(cr,uid,ids)
            for x in obj.serial_number_ids:
                line_search = line.search(cr,uid,[
                    ('permohonan_faktur_id','=',obj.id)
                ])
                if line_search :
                    line_browse = line.browse(cr,uid,line_search)
                    line_browse.write({
                        'permohonan_faktur_id':False
                    })
            
            
        if context is None:
            context = {}
        lot = []
        if branch_id and partner_id:
            print "---9999900000------"
            lot_pool = self.pool.get('stock.production.lot')
            if not exception:
                lot_search = lot_pool.search(cr,uid,[
                    ('branch_id','=',branch_id),
                    ('tgl_faktur','=',False),
                    ('permohonan_faktur_id','=',False),
                    ('lot_status_cddb','=','ok'),
                    ('state','=','paid')
                ])
                
                if not lot_search :
                    lot = []
                elif lot_search :
                    lot_browse = lot_pool.browse(cr,uid,lot_search)           
                    for x in lot_browse :
                        if x.sudo().pelanggaran_supplier_id.id == partner_id and ((x.sudo().pelanggaran_branch_id.id != branch_id and pelwil) or (x.sudo().pelanggaran_branch_id.id == branch_id and not pelwil)):

                            lot.append({
                                'name':x.name,                               
                                'chassis_no':x.chassis_no,
                                'product_id':x.product_id.id,
                                'dealer_sale_order_id':x.dealer_sale_order_id.id,
                                'customer_id':x.customer_id.id,
                                'customer_stnk':x.customer_stnk.id,
                                'state':x.state,
                                'pelanggaran_branch_name':x.sudo().pelanggaran_branch_name,
                                'pelanggaran_branch_ahm_code':x.sudo().pelanggaran_branch_ahm_code,
                            })

                            # lot.append([0,0,{
                            #     'name':x.name,                               
                            #     'chassis_no':x.chassis_no,
                            #     'product_id':x.product_id.id,
                            #     'dealer_sale_order_id':x.dealer_sale_order_id.id,
                            #     'customer_id':x.customer_id.id,
                            #     'customer_stnk':x.customer_stnk.id,
                            #     'state':x.state,
                            #     'pelanggaran_branch_name':x.sudo().pelanggaran_branch_name,
                            #     'pelanggaran_branch_ahm_code':x.sudo().pelanggaran_branch_ahm_code,
                            # }])
            if exception :
                lot_search = lot_pool.search(cr,uid,[
                    ('branch_id','=',branch_id),
                    ('tgl_faktur','=',False),
                    ('permohonan_faktur_id','=',False),
                    ('lot_status_cddb','=','ok'),
                    '|',('state','=','paid_offtr'),
                    '&',('customer_id.is_group_customer','!=',False),
                    '|',('state','=','sold'),
                    ('state','=','sold_offtr')
                ])
                
                if not lot_search :
                    lot = []
                elif lot_search :
                    lot_browse = lot_pool.browse(cr,uid,lot_search)           
                    for x in lot_browse :
                        if x.sudo().pelanggaran_supplier_id.id == partner_id and ((x.sudo().pelanggaran_branch_id.id != branch_id and pelwil) or (x.sudo().pelanggaran_branch_id.id == branch_id and not pelwil)):
                            # lot.append([0,0,{
                            #     'name':x.name,                               
                            #     'chassis_no':x.chassis_no,
                            #     'product_id':x.product_id.id,
                            #     'dealer_sale_order_id':x.dealer_sale_order_id.id,
                            #     'customer_id':x.customer_id.id,
                            #     'customer_stnk':x.customer_stnk.id,
                            #     'state':x.state,
                            #     'pelanggaran_branch_name':x.sudo().pelanggaran_branch_name,
                            #     'pelanggaran_branch_ahm_code':x.sudo().pelanggaran_branch_ahm_code,
                            # }])

                            lot.append({
                                'name':x.name,                               
                                'chassis_no':x.chassis_no,
                                'product_id':x.product_id.id,
                                'dealer_sale_order_id':x.dealer_sale_order_id.id,
                                'customer_id':x.customer_id.id,
                                'customer_stnk':x.customer_stnk.id,
                                'state':x.state,
                                'pelanggaran_branch_name':x.sudo().pelanggaran_branch_name,
                                'pelanggaran_branch_ahm_code':x.sudo().pelanggaran_branch_ahm_code,
                            })

        print "-------3333-------"
        branch_search = self.pool.get('dym.branch').search(cr,uid,[('id','=',branch_id)])
        branch_browse = self.pool.get('dym.branch').browse(cr,uid,branch_search)
        partner_md = branch_browse.default_supplier_id.id
        if pelwil:
            partner_md = partner_id
        partner = self.pool.get('res.partner').browse(cr, uid, partner_md)

        lot_ids = []
        for l in lot:
            lot_id = lot_pool.search(cr, uid, [('name','=',l['name'])])
            if not lot_id:
                lot_id = lot_pool.create(l)
            else:
                lot_id = lot_id[0]
            lot_ids.append(lot_id)            

        res = {'value':{'serial_number_ids':[(6,0,lot_ids)],'partner_id':partner_md,'partner_md':partner_md,'ahm_code':partner.ahm_code}}
        # res = {'value':{'serial_number_ids': lot,'partner_id':partner_md,'partner_md':partner_md,'ahm_code':partner.ahm_code}}

        print "-------555-------", res
        return res
    '''

    '''    
    def create(self, cr, uid, vals, context=None):
        lot_pool = self.pool.get('stock.production.lot')
        if not vals['serial_number_ids'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail permohonan. Data tidak bisa di save."))


        lot_collect = []
        for sn in vals['serial_number_ids']:
            v1, v2, v3 = sn
            lot_collect.append(v2)

        print "====lot_collect==",lot_collect


        # lot_collect = []
        # for x in vals['serial_number_ids']:
        #     lot_collect.append(x.pop(2))

        # print "----lot_collect----",lot_collect

        del[vals['serial_number_ids']]

        # lot_pool = self.pool.get('stock.production.lot')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PFA', division='Unit')
        vals['tgl_mohon_faktur'] = time.strftime('%Y-%m-%d'),

        print "===vals===>",vals

        permohonan_id = super(dym_permohonan_faktur, self).create(cr, uid, vals, context=context) 

        for lc in lot_collect:
            lot_pool.write(cr, uid, [lc], {'permohonan_faktur_id':permohonan_id})

        #VALS = {'branch_id': 351, 'pelwil': False, 'exception_faktur': False, 'division': 'Unit', 'tgl_mohon_faktur': ('2017-09-14',), 'approval_ids': [], 'message_follower_ids': False, 'partner_id': 24985, 'message_ids': False, 'name': u'PFA-S/LTI01/1709/00001'}


        # if permohonan_id:
        #     for x in lot_collect :
        #         lot_search = lot_pool.search(cr,uid,[
        #             ('branch_id','=',vals['branch_id']),
        #             ('tgl_faktur','=',False),
        #             ('name','=',x['name'])
        #             ])
        #         lot_browse = lot_pool.browse(cr,uid,lot_search)
        #         lot_browse.write({
        #            'permohonan_faktur_id':permohonan_id,
        #         })  
        # else :
        #     return False

        # try :
        #     permohonan_id = super(dym_permohonan_faktur, self).create(cr, uid, vals, context=context) 
        #     if permohonan_id :         
        #             for x in lot_collect :
        #                 lot_search = lot_pool.search(cr,uid,[
        #                             ('branch_id','=',vals['branch_id']),
        #                             ('tgl_faktur','=',False),
        #                             ('name','=',x['name'])
        #                             ])
        #                 lot_browse = lot_pool.browse(cr,uid,lot_search)
        #                 lot_browse.write({
        #                        'permohonan_faktur_id':permohonan_id,
        #                        })  
        #     else :
        #         return False
        #     cr.commit()
        # except Exception:
        #     cr.rollback()
        #     raise osv.except_osv(('Perhatian !'), ("Data telah diproses user lain. Periksa kembali data Anda."))
        # sys.setrecursionlimit(10000)



        permohonan = self.browse(cr, uid, permohonan_id)
        # if len(permohonan.serial_number_ids.sudo().mapped('pelanggaran_branch_id')) > 1:
        #     raise osv.except_osv(('Perhatian !'), ("Permohonan Faktur STNK ke Main Dealer yang pelanggaran wilayah harus memiliki asal cabang motor yang sama."))
        return permohonan_id  
    '''


    def create(self, cr, uid, vals, context=None):
        if not vals['serial_number_ids'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail permohonan. Data tidak bisa di save."))
        lot_collect = []
        for x in vals['serial_number_ids']:
            lot_collect.append(x.pop(2))

        del[vals['serial_number_ids']]
        lot_pool = self.pool.get('stock.production.lot')
        # vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PFA', division='Unit')
        vals['tgl_mohon_faktur'] = time.strftime('%Y-%m-%d'),
        try :
            permohonan_id = super(dym_permohonan_faktur, self).create(cr, uid, vals, context=context) 
            if permohonan_id :         
                    for x in lot_collect :
                        lot_search = lot_pool.search(cr,uid,[
                            ('branch_id','=',vals['branch_id']),
                            ('tgl_faktur','=',False),
                            ('name','=',x['name'])
                        ])
                        lot_browse = lot_pool.browse(cr,uid,lot_search)
                        lot_browse.write({
                           'permohonan_faktur_id':permohonan_id,
                        })  
            else :
                return False
            cr.commit()
        except Exception:
            cr.rollback()
            raise osv.except_osv(('Perhatian !'), ("Data telah diproses user lain. Periksa kembali data Anda."))
        sys.setrecursionlimit(10000)
        permohonan = self.browse(cr, uid, permohonan_id)
        # for sn in permohonan.serial_number_ids:
        #     print "--->",sn.pelanggaran_branch_id
        branch_id = []
        pic_pac = 0
        for x in permohonan.serial_number_ids.sudo().mapped('pelanggaran_branch_id_test'):
            if not x in branch_id:
                branch_id.append(x)
                # print "branch_idbranch_idbranch_id", branch_id
                pic_pac = 1
            else:
                pic_pac = 0
        # print "branch_idbranch_idbranch_id", branch_id
        # print "testtesttesttest", pic_pac
        # if len(permohonan.serial_number_ids.sudo().mapped('pelanggaran_branch_id')) > 1:
        if len(permohonan.serial_number_ids) > 1:
            if pic_pac == 1:
                raise osv.except_osv(('Perhatian !'), ("Permohonan Faktur STNK ke Main Dealer yang pelanggaran wilayah harus memiliki asal cabang motor yang sama."))

        # if len(permohonan.serial_number_ids.sudo().mapped('pelanggaran_branch_id')) > 1:
        #     raise osv.except_osv(('Perhatian !'), ("Permohonan Faktur STNK ke Main Dealer yang pelanggaran wilayah harus memiliki asal cabang motor yang sama."))
        return permohonan_id
    
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        collect = self.browse(cr,uid,ids)
        lot = vals.get('serial_number_ids', False)
        dellot = ''
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
                        'state_stnk':False,
                        'permohonan_faktur_id':False,
                        'tgl_faktur':False,
                    })
                    dellot += ('- '+str(lot_browse.name)+'<br/>')
                elif item[0] == 0 :
                    values = item[2]
                    lot_search = lot_pool.search(cr,uid,[
                        ('name','=',values['name'])
                    ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                        'permohonan_faktur_id':collect.id
                    })
            if dellot :
                self.message_post(cr, uid, collect.id, body=_("Delete Engine No <br/> %s")%(dellot), context=context)
        sys.setrecursionlimit(10000)
        for permohonan_id in ids:         
            permohonan = self.browse(cr, uid, permohonan_id)
            branch_id = []
            pic_pac = 0
            for x in permohonan.serial_number_ids.sudo().mapped('pelanggaran_branch_id_test'):
                if not x in branch_id:
                    branch_id.append(x)
                    # print "branch_idbranch_idbranch_id", branch_id
                    pic_pac = 1
                else:
                    pic_pac = 0
            # if len(permohonan.serial_number_ids.sudo().mapped('pelanggaran_branch_id')) > 1:
            if len(permohonan.serial_number_ids) > 1:
                if pic_pac == 1:
                    raise osv.except_osv(('Perhatian !'), ("Permohonan Faktur STNK ke Main Dealer yang pelanggaran wilayah harus memiliki asal cabang motor yang sama."))
        return super(dym_permohonan_faktur, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Permohonan Faktur sudah di post ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')
        lot_search = lot_pool.search(cr,uid,[
                                           ('permohonan_faktur_id','=',ids)
                                           ])
        lot_browse = lot_pool.browse(cr,uid,lot_search)
        for x in lot_browse :
            x.write({'state_stnk': False,'tgl_faktur':False})
        return super(dym_permohonan_faktur, self).unlink(cr, uid, ids, context=context)
    
    def action_button_permohonan(self,cr,uid,ids,context=None):
        lot = self.pool.get('stock.production.lot')
        form_id  = 'permohonan.faktur.form'
        view_pool = self.pool.get("ir.ui.view")
        vit = view_pool.search(cr,uid, [
                                     ("name", "=", form_id), 
                                     ("model", "=", 'dym.permohonan.faktur'), 
                                    ])
        form_browse = view_pool.browse(cr,uid,vit)
        return {
            'name': 'Permohonan Faktur',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dym.permohonan.faktur',
            'type': 'ir.actions.act_window',
            'view_id' : form_browse.id,
            'nodestroy': True,
            'target': 'new',
        } 