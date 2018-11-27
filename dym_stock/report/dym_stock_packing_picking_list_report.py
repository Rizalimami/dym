import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class stock_picking(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(stock_picking, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'waktu_local': self.waktu_local,
            'qty': self.qty,
            'mutation_order':self.mutation_order,
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
    
    
    def mutation_order(self):
        obj_picking = self.pool.get('stock.picking').browse(self.cr, self.uid, self.ids)
        nama_dealer=False
        if obj_picking.origin[0:3] == 'MOR' :
            obj_mo=self.pool.get('dym.mutation.order').search(self.cr,self.uid,[('name','=',obj_picking.origin)])
            obj_mo_browse=self.pool.get('dym.mutation.order').browse(self.cr,self.uid,obj_mo)
            nama_dealer=obj_mo_browse.branch_requester_id
        elif obj_picking.origin[0:3] in ['SOR','WOR'] :
            nama_dealer=obj_picking.partner_id
        elif obj_picking.origin[0:3] == 'DSM' :
            dsl_obj= self.pool.get('dealer.sale.order').search(self.cr, self.uid,[('name','=',obj_picking.origin)])
            dsl=self.pool.get('dealer.sale.order').browse(self.cr, self.uid,dsl_obj)
            nama_dealer=dsl.partner_id
        return nama_dealer
    
    def qty(self):
        order = self.pool.get('stock.move').search(self.cr, self.uid,[("picking_id", "in", self.ids)])
        valbbn=0
        for line in self.pool.get('stock.move').browse(self.cr, self.uid, order) :
            valbbn += line.product_uom_qty
        return valbbn

    def invoice(self):
        no_invoice=False
        obj_picking = self.pool.get('stock.picking').browse(self.cr, self.uid, self.ids)
        obj_inv=self.pool.get('account.invoice').search(self.cr, self.uid,[('origin','ilike',obj_picking.origin),('state','in',['paid','open'])])
        inv=self.pool.get('account.invoice').browse(self.cr, self.uid,obj_inv)
        no_invoice= ', '.join(inv.mapped('number'))
        return no_invoice
    
report_sxw.report_sxw('report.rml.dym.stock.packing', 'stock.picking', 'addons/dym_stock/report/dym_stock_packing_picking_list_report.rml', parser = stock_picking, header = False)