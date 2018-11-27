import datetime
from openerp.osv import fields, osv
from openerp import SUPERUSER_ID

tgl = datetime.datetime.now()
thn = tgl.year

class serial_number(osv.osv):
    _inherit ='stock.production.lot'
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    def _get_original_sales_ahm_code(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        pic = False
        pac = False
        nots = False

        for rec in self.browse(cr, SUPERUSER_ID, ids, context=context):
            lot_pool = self.pool.get('stock.production.lot')
            lot_search = lot_pool.search(cr,SUPERUSER_ID,[('name','=',rec.name)])
            if lot_search:
                if len(lot_search) == 2:
                    pic = True
                if pic == True:
                    lot_browse = lot_pool.browse(cr,SUPERUSER_ID,lot_search)
                    if pic == True:
                        for lot_1 in lot_browse:
                            pic_lot_search = lot_pool.search(cr,SUPERUSER_ID,[('id','=',lot_1.id),('customer_stnk','=',False)])
                            if pic_lot_search:
                                pic_lot_browse = lot_pool.browse(cr,SUPERUSER_ID,pic_lot_search)
                                for lot_pic in pic_lot_browse:
                                    result[rec.id] = {
                                            'pelanggaran_branch_ahm_code_test': lot_pic.branch_id.ahm_code,
                                            'pelanggaran_branch_ahm_sales_code_test': lot_pic.branch_id.pimpinan_id.sales_ahm,
                                            'pelanggaran_branch_name_test': lot_pic.branch_id.name,
                                            'pelanggaran_branch_id_test': lot_pic.branch_id.id,
                                            'pelanggaran_company_id_test': lot_pic.branch_id.company_id.id,
                                        }
                elif pic == False:
                    lot_browse = lot_pool.browse(cr,SUPERUSER_ID,lot_search)
                    for lot_2 in lot_browse:
                        if lot_browse.sudo().pelanggaran_branch_id.id == lot_2.branch_id.id:
                            result[rec.id] = {
                                    'pelanggaran_branch_ahm_code_test': lot_2.branch_id.ahm_code,
                                    'pelanggaran_branch_ahm_sales_code_test': lot_2.dealer_sale_order_id.employee_id.sales_ahm,
                                    'pelanggaran_branch_name_test': lot_2.branch_id.name,
                                    'pelanggaran_branch_id_test': lot_2.branch_id.id,
                                    'pelanggaran_company_id_test': lot_2.branch_id.company_id.id,
                                }
                        else:
                            result[rec.id] = {
                                    'pelanggaran_branch_ahm_code_test': lot_browse.sudo().pelanggaran_branch_id.ahm_code,
                                    'pelanggaran_branch_ahm_sales_code_test': lot_browse.sudo().pelanggaran_branch_id.pimpinan_id.sales_ahm,
                                    'pelanggaran_branch_name_test': lot_browse.sudo().pelanggaran_branch_id.name,
                                    'pelanggaran_branch_id_test': lot_browse.sudo().pelanggaran_branch_id.id,
                                    'pelanggaran_company_id_test': lot_browse.sudo().pelanggaran_branch_id.company_id.id,
                                }
        return result

    def _get_original_location(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for rec in self.browse(cr, SUPERUSER_ID, ids, context=context):
            quant_obj = self.pool.get("stock.quant")
            quants = quant_obj.search(cr, SUPERUSER_ID, [('lot_id', 'in', [rec.id])], context=context)
            moves = []
            for quant in quant_obj.browse(cr, SUPERUSER_ID, quants, context=context):
                for move in quant.history_ids:
                    moves.append(move.id)
            if moves:
                obj_move_ids = self.pool.get('stock.move').search(cr, SUPERUSER_ID, [('id', 'in', moves)], order='date asc, id asc', context=context)
                obj_move = self.pool.get('stock.move').browse(cr, SUPERUSER_ID, obj_move_ids, context=context)
                for stock_move in obj_move:
                    if stock_move.location_id.id and stock_move.location_id.usage == 'internal':
                        # result[rec.id] = stock_move.location_id.id
                        result[rec.id] = {
                            'original_location_id': stock_move.location_id.id,
                            'pelanggaran_wilayah': True if rec.branch_id != stock_move.location_id.branch_id else False,
                            'pelanggaran_branch_ahm_code': stock_move.location_id.branch_id.ahm_code,
                            'pelanggaran_supplier_ahm_code': stock_move.location_id.branch_id.default_supplier_id.ahm_code,
                            'pelanggaran_supplier_id': stock_move.location_id.branch_id.default_supplier_id.id,
                            'pelanggaran_branch_id': stock_move.location_id.branch_id.id,
                            'pelanggaran_branch_name': stock_move.location_id.branch_id.name_get().pop()[1] if stock_move.location_id.branch_id else '',
                        }
                        return result
                    elif stock_move.location_dest_id.id and stock_move.location_dest_id.usage == 'internal':
                        # result[rec.id] = stock_move.location_dest_id.id
                        result[rec.id] = {
                            'original_location_id': stock_move.location_dest_id.id,
                            'pelanggaran_wilayah': True if rec.branch_id != stock_move.location_dest_id.branch_id else False,
                            'pelanggaran_branch_ahm_code': stock_move.location_dest_id.branch_id.ahm_code,
                            'pelanggaran_supplier_ahm_code': stock_move.location_dest_id.branch_id.default_supplier_id.ahm_code,
                            'pelanggaran_supplier_id': stock_move.location_dest_id.branch_id.default_supplier_id.id,
                            'pelanggaran_branch_id': stock_move.location_dest_id.branch_id.id,
                            'pelanggaran_branch_name': stock_move.location_dest_id.branch_id.name_get().pop()[1] if stock_move.location_dest_id.branch_id else '',
                        }
                        return result
            else:
                # result[rec.id] = rec.location_id.id     
                result[rec.id] = {
                    'original_location_id': rec.location_id.id,
                    'pelanggaran_wilayah': True if rec.branch_id != rec.location_id.branch_id else False,
                    'pelanggaran_branch_ahm_code': rec.location_id.branch_id.ahm_code,
                    'pelanggaran_supplier_ahm_code': rec.location_id.branch_id.default_supplier_id.ahm_code,
                    'pelanggaran_supplier_id': rec.location_id.branch_id.default_supplier_id.id,
                    'pelanggaran_branch_id': rec.location_id.branch_id.id,
                    'pelanggaran_branch_name': rec.location_id.branch_id.name_get().pop()[1] if rec.location_id.branch_id else '',
                }       
                return result
            # result[rec.id] = False
            result[rec.id] = {
                'original_location_id': False,
                'pelanggaran_wilayah': False,
                'pelanggaran_branch_ahm_code': '',
                'pelanggaran_supplier_ahm_code': '',
                'pelanggaran_supplier_id': False,
                'pelanggaran_branch_id': False,
                'pelanggaran_branch_name': '',
            }       
        return result

    def get_location_before(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for rec in self.browse(cr, uid, ids, context=context):
            quant_obj = self.pool.get("stock.quant")
            quants = quant_obj.search(cr, uid, [('lot_id', 'in', [rec.id])], context=context)
            moves = []
            for quant in quant_obj.browse(cr, uid, quants, context=context):
                for move in quant.history_ids:
                    moves.append(move.id)
            if moves:
                obj_move_ids = self.pool.get('stock.move').search(cr, uid, [('id', 'in', moves)], order='date desc, id desc', context=context)
                obj_move = self.pool.get('stock.move').browse(cr, uid, obj_move_ids, context=context)
                flag = False
                branch_id = rec.branch_id.id
                for stock_move in obj_move:
                    if flag == True:
                        if stock_move.location_dest_id.id and stock_move.location_dest_id.usage == 'internal' and stock_move.location_dest_id.branch_id.id != branch_id:
                            result[rec.id] = stock_move.location_dest_id.id
                            return result                        
                    if stock_move.location_id.id and stock_move.location_id.usage == 'internal' and stock_move.location_id.branch_id.id != branch_id:
                        result[rec.id] = stock_move.location_id.id
                        return result
                    flag = True
            else:
                result[rec.id] = False
                return result
            result[rec.id] = False
        return result

    _columns={
        'name': fields.char('Serial Number', required=True, help="Unique Serial Number", size=12),
        'location_before': fields.function(get_location_before, string='Location Before', type='many2one', relation="stock.location"),
        'original_location_id': fields.function(_get_original_location, string='Original Location', type='many2one', relation="stock.location", multi="pelanggaran_wil"),
        'pelanggaran_wilayah': fields.function(_get_original_location, string='Pelanggaran Wilayah', type='boolean', multi="pelanggaran_wil"),
        'pelanggaran_branch_ahm_code': fields.function(_get_original_location, string='AHM Code Branch', type='char', multi="pelanggaran_wil"),
        'pelanggaran_supplier_ahm_code': fields.function(_get_original_location, string='AHM Code Supplier', type='char', multi="pelanggaran_wil"),
        'pelanggaran_supplier_id': fields.function(_get_original_location, string='Supplier', type='many2one', relation="res.partner", multi="pelanggaran_wil"),
        'pelanggaran_branch_id': fields.function(_get_original_location, string='Branch', type='many2one', relation="dym.branch", multi="pelanggaran_wil"),
        'pelanggaran_branch_id': fields.function(_get_original_location, string='Branch', type='many2one', relation="dym.branch", multi="pelanggaran_wil"),
        'pelanggaran_branch_name': fields.function(_get_original_location, string='Branch', type='char', multi="pelanggaran_wil"),
        'chassis_no':fields.char('Chassis Number',required=True, size=14),
        'chassis_code':fields.char('Chassis Code', size=3),
        'branch_id': fields.many2one('dym.branch','Branch'),
        'division':fields.selection([('Unit','Showroom')], 'Division'),
        'state': fields.selection([('intransit', 'Intransit'),('titipan','Titipan'),('stock', 'Stock'), ('reserved','Reserved'),('sold','Sold OTR'), ('paid', 'Paid OTR'),('sold_offtr','Sold OFFTR'),('paid_offtr','Paid OFFTR'),('workshop','Workshop'),('returned','Purchase Return'),('asset','Asset'),('loss','Loss')], 'State'),
        'state_stnk': fields.selection([('mohon_faktur', 'Mohon Faktur'),('terima_faktur','Terima Faktur'),('proses_stnk','Proses STNK')], 'State STNK', track_visibility='always'),
        'tahun': fields.char('Tahun Pembuatan', size=4),
        'sale_order_id': fields.many2one('sale.order', string='Sales Memo',readonly=True),
        'customer_invoice_id': fields.many2one('account.invoice',string='Customer Invoice',readonly=True),
        'receipt_id': fields.many2one('stock.picking', 'Receipt'),
        'picking_id': fields.many2one('stock.picking', 'Picking'),
        'location_id': fields.many2one('stock.location','Location'),
        'ready_for_sale': fields.selection([('good','Good'),('not_good','Not Good')], 'Ready For Sale'),

        #PURCHASE
        'purchase_order_id': fields.many2one('purchase.order','PO Number'),
        'po_date': fields.date('PO Date'),
        'supplier_id':fields.many2one('res.partner','Supplier'),
        'expedisi_id':fields.many2one('res.partner','Supplier Expedisi'),
        'receive_date':fields.date('Receive Date'),
        'freight_cost':fields.float('Freight Cost'),

        # SALES MD
        'dealer_id':fields.many2one('res.partner','Dealer'),
        'sales_md_date': fields.date('Sales MD Date'),
        'do_md_date':fields.date('DO MD Date'),
        'tgl_cetak_faktur':fields.date('Tanggal Cetak Faktur'),
        'tgl_mohon_faktur':fields.date('Tanggal Mohon Faktur'),
        # SALES DEALER
        'invoice_date':fields.date('Invoice Date'),
        'do_date':fields.date('DO Date'),
        'tgl_faktur':fields.date('Tanggal Mohon Faktur'),
        'faktur_stnk':fields.char('No Faktur STNK', size=128),
        'tgl_terima':fields.date('Tanggal Terima'),
        'customer_id':fields.many2one('res.partner','Customer',domain=[('customer','=',True)]),
        'finco_id':fields.many2one('res.partner','Code Finance Company',domain=[('finance_company','=',True)]),
        'finco_cabang': fields.many2one('dym.cabang.partner','Cabang Finco'),
        'reserved': fields.boolean('Reserved'),
        'customer_reserved': fields.many2one('res.partner','Customer Reserved'),
        'customer_stnk': fields.many2one('res.partner','Customer STNK',domain=[('customer','=',True)]),
        'jenis_penjualan':fields.selection([('1','Cash'),('2','Credit')],'Jenis Penjualan'),
        'dp':fields.float('JP'),
        'tenor':fields.float('Tenor'),
        'cicilan':fields.float('Cicilan'),
        #STNK & BPKB
        'biro_jasa_id':fields.many2one('res.partner','Biro Jasa',domain=[('biro_jasa','=',True)]),
        'no_polisi':fields.char('No Polisi',size=128),
        'tgl_notice':fields.date('Tgl JTP Notice'),
        'no_notice':fields.char('No Notice', size=128),
        'tgl_stnk':fields.date('Tgl JTP STNK'),
        'no_stnk':fields.char('No STNK',size=128),
        'tgl_bpkb':fields.date('Tgl Jadi BPKB'),
        'no_bpkb':fields.char('No BPKB',size=128),
        #WORKSHOP
        'kode_buku':fields.char('Kode Buku Service'),
        'nama_buku':fields.char('Nomor Buku Service'), 
        'no_sipb':fields.char('No SIPB'),
        'no_ship_list':fields.char('No Ship List'),
        'tgl_ship_list':fields.date("Tgl Ship List"),
        'no_faktur':fields.char('No Faktur'),

        'pelanggaran_company_id_test': fields.function(_get_original_sales_ahm_code, string='Company ID', type='char', multi="pelanggaran_wil_test"),
        'pelanggaran_branch_id_test': fields.function(_get_original_sales_ahm_code, string='Branch ID', type='char', multi="pelanggaran_wil_test"),
        'pelanggaran_branch_name_test': fields.function(_get_original_sales_ahm_code, string='Branch', type='char', multi="pelanggaran_wil_test"),
        'pelanggaran_branch_ahm_code_test': fields.function(_get_original_sales_ahm_code, string='AHM Code Branch', type='char', multi="pelanggaran_wil_test"),
        'pelanggaran_branch_ahm_sales_code_test': fields.function(_get_original_sales_ahm_code, string='AHM Code Sales', type='char', multi="pelanggaran_wil_test"),
    }
    
    def _check_unique_name(self, cr, uid, ids, context=None):
        lines = self.browse(cr, SUPERUSER_ID, ids, context=context)
        for l in lines:
            if l.sudo().branch_id and l.name:
                lot = self.search(cr, uid, [('branch_id.company_id','=',l.sudo().branch_id.company_id.id),('name','=',l.name),('id','!=',l.id)])
                if lot:
                    return False
        return True

    def _check_unique_chassis(self, cr, uid, ids, context=None):
        lines = self.browse(cr, SUPERUSER_ID, ids, context=context)
        for l in lines:
            if l.sudo().branch_id and l.chassis_no:
                lot = self.search(cr, SUPERUSER_ID, [('branch_id.company_id','=',l.sudo().branch_id.company_id.id),('chassis_no','=',l.chassis_no),('id','!=',l.id)])
                if lot:
                    return False
        return True

    _constraints = [
        (_check_unique_name, 'Ditemukan Serial Number duplicate.', ['name','branch_id']),
        (_check_unique_chassis, 'Ditemukan Chassis Number duplicate.', ['chassis_no','branch_id']),
    ]
        
    _defaults={
        'tahun': thn,
        'branch_id': _get_default_branch,
    }   

    def unlink(self,cr,uid,ids,retur=False,context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if retur == False:
                raise osv.except_osv(('Perhatian !'), ("Tidak boleh menghapus lot"))
        return False
                         
    def tahun_change(self, cr, uid, ids, tahun, context=None):
        val = {}
        war = {}
        if tahun and not tahun.isdigit():
            val['tahun'] = False
            war = {'title':'Perhatian !', 'message':'Tahun Perakitan hanya boleh angka'}
            
        return {'value':val, 'warning':war}