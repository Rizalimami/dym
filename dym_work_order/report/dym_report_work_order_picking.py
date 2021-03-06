import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
#import fungsi_terbilang
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class dym_work_order(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(dym_work_order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'invoice_id': self.invoice_id,
            'type_wo': self.type_wo,
            'waktu_local': self.waktu_local,
            
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no
    
    def time_date(self):
        tangal=time.strftime('%Y-%m-%d %H:%M:%S')
        return tangal
    
    def type_wo(self):
        wo = self.pool.get('dym.work.order').browse(self.cr, self.uid, self.ids).type_wo
        return wo
    
    def waktu_local(self):
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date
    

    
    def invoice_id(self):
        invoice = self.pool.get('dym.work.order').browse(self.cr, self.uid, self.ids).name
        invoice2 = self.pool.get('account.invoice').search(self.cr, self.uid,[ ('origin','ilike',invoice) ])
        no_invoice = self.pool.get('account.invoice').browse(self.cr, self.uid,invoice2).number
        return no_invoice
    
report_sxw.report_sxw('report.rml.work.order.picking', 'dym.work.order', 'addons/dym_work_order/report/dym_report_work_order_picking.rml', parser = dym_work_order, header = False)