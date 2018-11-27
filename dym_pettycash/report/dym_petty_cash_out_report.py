import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
import fungsi_terbilang
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class dym_pettycash(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(dym_pettycash, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'terbilang': self.terbilang,
            'waktu_local': self.waktu_local,
            
        })        
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no
    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    
    def waktu_local(self):
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y")
        return start_date


    
report_sxw.report_sxw('report.rml.dym.pettycash', 'dym.pettycash', 'addons/dym_pettycash/report/dym_petty_cash_out_report.rml', parser = dym_pettycash, header = False)