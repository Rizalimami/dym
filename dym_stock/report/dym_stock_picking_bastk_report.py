import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class dym_stock_packing(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(dym_stock_packing, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'waktu_local': self.waktu_local,
            'nama_konsumen': self.nama_konsumen,
            'alamat_kirim': self.alamat_kirim,
            'invoice':self.invoice
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no

    
    def waktu_local(self):
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date
    
    def invoice(self):
        no_invoice=False
        a=self.pool.get('dym.stock.packing').browse(self.cr, self.uid, self.ids).picking_id.id
        obj_picking = self.pool.get('stock.picking').browse(self.cr, self.uid, a)
        obj_inv=self.pool.get('account.invoice').search(self.cr, self.uid,[('origin','ilike',obj_picking.origin),('state','in',['paid','open'])])
        inv=self.pool.get('account.invoice').browse(self.cr, self.uid,obj_inv)
        no_invoice= ', '.join(inv.mapped('number'))
        return no_invoice
        
    def nama_konsumen(self):
        obj_packing = self.pool.get('dym.stock.packing').browse(self.cr, self.uid, self.ids).rel_origin
        model = 'dealer.sale.order'
        invoice2 = self.pool.get('dealer.sale.order').search(self.cr, self.uid,[ ('name','=',obj_packing) ])
        name_nya = self.pool.get(model).browse(self.cr, self.uid, invoice2).partner_id
        if not invoice2:
            model = 'dym.work.order'
            invoice2 = self.pool.get(model).search(self.cr, self.uid,[ ('name','=',obj_packing) ])
            name_nya = self.pool.get(model).browse(self.cr, self.uid, invoice2).customer_id
        if not invoice2:
            model = 'sale.order'
            invoice2 = self.pool.get(model).search(self.cr, self.uid,[ ('name','=',obj_packing) ])
            name_nya = self.pool.get(model).browse(self.cr, self.uid, invoice2).partner_id
        return name_nya

    def alamat_kirim(self):
        obj_packing = self.pool.get('dym.stock.packing').browse(self.cr, self.uid, self.ids).rel_origin
        model = 'dealer.sale.order'
        invoice2 = self.pool.get('dealer.sale.order').search(self.cr, self.uid,[ ('name','=',obj_packing) ])
        name_nya = self.pool.get(model).browse(self.cr, self.uid, invoice2)
        return name_nya

    
report_sxw.report_sxw('report.rml.dym.stock.picking.bastk', 'dym.stock.packing', 'addons/dym_stock/report/dym_stock_picking_bastk_report.rml', parser = dym_stock_packing, header = False)