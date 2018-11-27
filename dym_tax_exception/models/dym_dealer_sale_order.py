import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _

class DealerSaleOrder(models.Model):
    _inherit = "dealer.sale.order"

    def _check_sale_order(self,cr,uid,ids,sale_order):
    	BranchConfig = self.pool.get('dym.branch.config')
        branch_config_id = BranchConfig.search(cr, uid, [('branch_id','=',sale_order.branch_id.id)])
        branch_config = BranchConfig.browse(cr, uid, branch_config_id, {}) 
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
                
            if not branch_config.free_tax and not order_line.tax_id:
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
