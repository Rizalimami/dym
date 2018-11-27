import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
import fungsi_terbilang

class dym_advance_payment(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(dym_advance_payment, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'terbilang':self.terbilang,
            'get_my_date': self.get_my_date,
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no
    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    
    def get_my_date(self, date):
        return time.strftime('%d') + '-' + datetime.strptime(date, '%d-%m-%Y').strftime('%b').upper() + '-' + time.strftime('%Y')
    
report_sxw.report_sxw('report.rml.advance.payment', 'dym.advance.payment', 'addons/dym_advance_payment/report/dym_advance_payment_report.xml', parser = dym_advance_payment, header = False)