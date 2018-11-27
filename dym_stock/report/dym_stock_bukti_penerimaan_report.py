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
            'qty': self.qty,
            'product_name': self._product_name,
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
    
    
    def qty(self):
        order = self.pool.get('dym.stock.packing.line').search(self.cr, self.uid,[("packing_id", "in", self.ids)])
        valbbn=0
        for line in self.pool.get('dym.stock.packing.line').browse(self.cr, self.uid, order) :
            valbbn += line.quantity
        return valbbn

report_sxw.report_sxw('report.rml.dym.stock.packing.penerimaan', 'dym.stock.packing', 'addons/dym_stock/report/dym_stock_bukti_penerimaan_report.xml', parser = dym_stock_packing, header = False)
# report_sxw.report_sxw('report.rml.dym.stock.packing.penerimaan', 'dym.stock.packing', 'addons/dym_stock/report/dym_stock_bukti_penerimaan_report.rml', parser = dym_stock_packing, header = False)