import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc
import openerp.addons.decimal_precision as dp

class dealer_sale_order_approval_diskon(osv.osv):
    _name = "dealer.sale.order.summary.diskon"   
    
    def _amount_average(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for approval in self.browse(cr, uid, ids, context=context):
            total_average = approval.beban_ps + approval.beban_bb + approval.beban_bb + approval.beban_po + approval.beban_hc
            
            res[approval.id]['amount_average']=total_average
        return res

    _columns = {
        'dealer_sale_order_id': fields.many2one('dealer.sale.order'),
        'product_id': fields.many2one('product.product','Product'),
        'product_qty': fields.integer('Qty'),
        'beban_ps': fields.float('Subsidi Dealer'),
        'beban_bb' : fields.float('Barang Bonus'),
        'beban_po': fields.float('Potongan'),
        'beban_hc': fields.float('Hutang Komisi'),
        'amount_average': fields.float('Amount Average'),
    }

class dealer_sale_order(osv.osv):
    _inherit = "dealer.sale.order"      

    def _is_offtheroad(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            offtr = False
            for line in order.dealer_sale_order_line:
                if line.is_bbn == 'T':
                    offtr = True
                    break
            res[order.id] = offtr
        return res

    def _cek_approval_line(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'approval_line_diskon' : False,
                'approval_line_offtr' : False,
                'approval_line_cod' : False,
                'approval_line_pic': False,
            }
            offtr = False
            pic = False
            cod = False
            diskon = False
            if order.approval_ids.filtered(lambda s: s.sts == '1').mapped('approval_config_id').filtered(lambda r: r.code == 'offtr' and r.type == 'biaya'):
                offtr = True
            if order.approval_ids.filtered(lambda s: s.sts == '1').mapped('approval_config_id').filtered(lambda r: r.code == 'pic' and r.type == 'biaya'):
                pic = True
            if order.approval_ids.filtered(lambda s: s.sts == '1').mapped('approval_config_id').filtered(lambda r: r.code == 'cod' and r.type == 'biaya'):
                cod = True
            if order.approval_ids.filtered(lambda s: s.sts == '1').mapped('approval_config_id').filtered(lambda r: r.code == ' ' and r.type == 'discount'):
                diskon = True
            res[order.id] = {
                'approval_line_diskon' : diskon,
                'approval_line_offtr' : offtr,
                'approval_line_pic' : pic,
                'approval_line_cod' : cod,
            }
        return res

    _columns = {
        'approve_diskon': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Diskon Approved'),
        'approve_offtr': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Off The Road Approved'),
        'approve_cod': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'COD Approved'),
        'approve_pic': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'PIC Approved'),
        'offtr': fields.function(_is_offtheroad, type="boolean", string='Off The Road'),
        'approval_line_diskon': fields.function(_cek_approval_line, type="boolean", string='Diskon', multi='sumsa'),
        'approval_line_offtr': fields.function(_cek_approval_line, type="boolean", string='Off The Road', multi='sumsa'),
        'approval_line_pic': fields.function(_cek_approval_line, type="boolean", string='PIC', multi='sumsa'),
        'approval_line_cod': fields.function(_cek_approval_line, type="boolean", string='COD', multi='sumsa'),
        'approval_ids': fields.one2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
        'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),  
    }
    
    _defaults ={
        'approve_diskon':'b',
        'approve_offtr':'b',
        'approve_cod':'b',
        'approve_pic':'b',
        'approval_state':'b',
    }
    
    def _check_sale_order(self,cr,uid,ids,sale_order):
        for order_line in sale_order.dealer_sale_order_line:
            if sale_order.finco_id:
                if not order_line.finco_tgl_po:
                    raise osv.except_osv(('Perhatian !'), ("Tanggal PO belum diisi!"))
                elif not order_line.finco_no_po:
                    raise osv.except_osv(('Perhatian !'), ("No. PO Belum diisi!"))
                elif order_line.finco_tenor <= 0:
                    raise osv.except_osv(('Perhatian !'), ("Ttenor Harus lebih dari 0!"))
                elif order_line.cicilan <=0:
                    raise osv.except_osv(('Perhatian !'), ("Cicilan harus lebih dari 0!"))
                elif order_line.is_bbn =='T':
                    raise osv.except_osv(('Perhatian !'), ("Penjualan credit harus pilih BBN!"))
                elif order_line.uang_muka <=0:
                    raise osv.except_osv(('Perhatian !'), ("Penjualan credit jaminan pembelian harus diisi"))
                
            branch_config_obj = self.pool.get('dym.branch.config')
            branch_config_search = branch_config_obj.search(cr, uid, [('branch_id','=',order_line.branch_dummy)])
            branch_config = branch_config_obj.browse(cr, uid, branch_config_search)

            if not order_line.tax_id and not branch_config.free_tax:
                raise osv.except_osv(('Perhatian !'), ("Pajak harus diisi!"))
            if sale_order.partner_komisi_id:
                if not order_line.hutang_komisi_id:
                    raise osv.except_osv(('Perhatian !'), ("Hutang Komisi Belum diisi!"))
            if order_line.is_bbn=='Y':
                if order_line.price_bbn<=0:
                    raise osv.except_osv(('Perhatian !'), ("Harga BBN tidak boleh 0!"))
                if not order_line.plat:
                    raise osv.except_osv(('Perhatian !'), ("Plat Belum Diisi!"))
            if not sale_order.finco_id:
                if order_line.uang_muka >0:
                    raise osv.except_osv(('Perhatian !'), ("Penjualan cash jaminan pembelian harus 0!"))
            
        return True
   
    def wkf_request_approval(self, cr, uid, ids, context=None):
        sale_order = self.browse(cr, uid, ids, context=context)
        total_diskon_dp = 0.0
        for line in sale_order.dealer_sale_order_line:
            total_diskon_dp += line.discount_total

        if sale_order.is_credit and total_diskon_dp != sale_order.diskon_dp:
        	raise osv.except_osv(('Perhatian !'), ("Nilai Disc Total harus sama dengan nilai Diskon JP 1 (%s vs %s)" % ('{:20,.2f}'.format(total_diskon_dp), '{:20,.2f}'.format(sale_order.diskon_dp))))


        obj_matrix = self.pool.get("dym.approval.matrixdiscount")
        if not sale_order.dealer_sale_order_line:
            raise osv.except_osv(('Perhatian !'), ("Produk belum diisi"))
        
        cek_order = self._check_sale_order(cr, uid, ids, sale_order)
        hasil = []
        
        summary_diskon = self._set_diskon_summary(cr,uid,ids,sale_order.dealer_sale_order_line)
        
        res_write = {'state': 'waiting_for_approval','approval_state':'rf','approve_diskon':'a','approve_cod':'a','approve_offtr':'a','approve_pic':'a'}
        for key, value in summary_diskon.items():
            product = self.pool.get('product.product').browse(cr,uid,key)
            average = (value.get('beban_po',0)+value.get('beban_hc',0)+value.get('beban_ps',0)+value.get('beban_bb',0))/value.get('product_qty',0)
            if average > 0:
                obj_matrix.request_by_value(cr, uid, ids, sale_order, sale_order['summary_diskon_ids'], average, product)
                res_write['approve_diskon'] = 'rf'

        obj_matrix_biaya = self.pool.get("dym.approval.matrixbiaya")
        if sale_order.is_cod == True:
            obj_matrix_biaya.request_by_value(cr, uid, ids, sale_order, 0, code='cod')
            res_write['approve_cod'] = 'rf'
        if sale_order.offtr == True:
            obj_matrix_biaya.request_by_value(cr, uid, ids, sale_order, 0, code='offtr')
            res_write['approve_offtr'] = 'rf'
        if sale_order.is_pic == True:
            obj_matrix_biaya.request_by_value(cr, uid, ids, sale_order, 0, code='pic')
            res_write['approve_pic'] = 'rf'
        self.write(cr, uid, ids, res_write)
        return True
           
    def wkf_approval(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        obj_so = self.browse(cr, uid, ids, context=context)
        if not obj_so.summary_diskon_ids:
            raise osv.except_osv(('Perhatian !'), ("produk belum diisi"))
        approval_diskon_sts = False
        for summary in obj_so.summary_diskon_ids:
            if obj_so.approval_line_diskon == True:
                if approval_diskon_sts != 2:
                    approval_diskon_sts = self.pool.get("dym.approval.matrixdiscount").approve(cr, uid, ids, obj_so, summary.product_id)
                    if approval_diskon_sts == 0:
                        raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval diskon"))
        if approval_diskon_sts == 1:
            self.write(cr, uid, ids, {'approve_diskon':'a'})        
        if (obj_so.approve_cod == 'a' or not obj_so.approval_line_cod) and (obj_so.approve_diskon == 'a' or not obj_so.approval_line_diskon) and (obj_so.approve_offtr == 'a' or not obj_so.approval_line_offtr) and (obj_so.approve_pic == 'a' or not obj_so.approval_line_pic):
            self.write(cr, uid, ids, {'approval_state':'a','state':'approved'})
        return True

    def wkf_approval_cod(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        obj_so = self.browse(cr, uid, ids, context=context)
        approval_cod_sts = self.pool.get("dym.approval.matrixbiaya").approve(cr, uid, ids, obj_so, code='cod')
        if approval_cod_sts == 0:             
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval cod"))
        elif approval_cod_sts == 1:
            self.write(cr, uid, ids, {'approve_cod':'a'})
        if (obj_so.approve_cod == 'a' or not obj_so.approval_line_cod) and (obj_so.approve_diskon == 'a' or not obj_so.approval_line_diskon) and (obj_so.approve_offtr == 'a' or not obj_so.approval_line_offtr) and (obj_so.approve_pic == 'a' or not obj_so.approval_line_pic):
            if obj_so.is_credit == False and not(obj_so.payment_term and len(obj_so.payment_term.line_ids.ids) == 1 and obj_so.payment_term.line_ids.days == 1 and obj_so.payment_term.line_ids.days2 == 0 and obj_so.payment_term.line_ids.value == 'balance'):
                term_search = self.pool.get('account.payment.term.line').search(cr, uid, [('value','=','balance'),('days','=',1),('days2','=',0),('payment_id.active','=',True)])
                term_browse = self.pool.get('account.payment.term.line').browse(cr, uid, term_search).mapped('payment_id').filtered(lambda r: len(r.line_ids.ids) == 1)
                if not term_browse:
                    raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan payment term COD (1 Day). Mohon ditambahkan terlebih dahulu"))
                else:
                    self.write(cr, uid, ids, {'payment_term':term_browse[0].id})
            self.write(cr, uid, ids, {'approval_state':'a','state':'approved'})
        return True 

    def wkf_approval_offtr(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        obj_so = self.browse(cr, uid, ids, context=context)
        approval_offtr_sts = self.pool.get("dym.approval.matrixbiaya").approve(cr, uid, ids, obj_so, code='offtr')        
        if approval_offtr_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval off the road"))
        elif approval_offtr_sts == 1:
            self.write(cr, uid, ids, {'approve_offtr':'a'})
        if (obj_so.approve_cod == 'a' or not obj_so.approval_line_cod) and (obj_so.approve_diskon == 'a' or not obj_so.approval_line_diskon) and (obj_so.approve_offtr == 'a' or not obj_so.approval_line_offtr) and (obj_so.approve_pic == 'a' or not obj_so.approval_line_pic):
            self.write(cr, uid, ids, {'approval_state':'a','state':'approved'})
        return True

    def wkf_approval_pic(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        obj_so = self.browse(cr, uid, ids, context=context)
        approval_pic_sts = self.pool.get("dym.approval.matrixbiaya").approve(cr, uid, ids, obj_so, code='pic')
        if approval_pic_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval PIC"))
        elif approval_pic_sts == 1:
            self.write(cr, uid, ids, {'approve_pic':'a','approve_offtr':'a'})
        if (obj_so.approve_cod == 'a' or not obj_so.approval_line_cod) and (obj_so.approve_diskon == 'a' or not obj_so.approval_line_diskon) and (obj_so.approve_pic == 'a' or not obj_so.approval_line_pic):
            self.write(cr, uid, ids, {'approval_state':'a','state':'approved'})
        return True

    def has_approved(self, cr, uid, ids, *args):
        obj_po = self.browse(cr, uid, ids)
        return obj_po.approval_state == 'a'

    def bypassrfa(self, cr, uid, ids, *args):
        dso = self.browse(cr, uid, ids)
        total_diskon = 0
        for summary in dso.summary_diskon_ids:
            total_diskon += summary.amount_average
        if dso.is_cod == False and dso.offtr == False and total_diskon <= 0:
            return True
        return False

    def has_rejected(self, cr, uid, ids, *args):
        obj_po = self.browse(cr, uid, ids)
        if obj_po.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r','approve_cod':'r','approve_diskon':'r','approve_offtr':'r','approve_pic':'r'})
    
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b','approve_cod':'b','approve_diskon':'b','approve_offtr':'b','approve_pic':'b'})   
        
class dealer_sale_order_reason_reject_approval(osv.osv_memory):
    _name = "dealer.sale.order.reason.reject.approval.so"
    
    _columns = {
        'reason':fields.text('Reason')
    }
    
    def dym_reject_approval(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context=context)
        user = self.pool.get("res.users").browse(cr, uid, uid)['groups_id']
        po_id = context.get('active_id',False)
        line = self.pool.get("dym.work.order").browse(cr,uid,po_id,context=context)
        objek = False
        for x in line.approval_ids :
            for y in user:
                    if y == x.group_id :
                        objek = True
                        for z in line.approval_ids :
                            if z.reason == False :
                                z.write({
                                    'reason':val.reason,
                                    'value':line.amount_total,
                                    'sts':'3',
                                    'pelaksana_id':uid,
                                    'tanggal':datetime.today()
                                })
                                self.pool.get("dym.work.order").write(cr, uid, po_id, {'state':'draft','approval_state':'r'})
        if objek == False :
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
                                                      
        return True    
