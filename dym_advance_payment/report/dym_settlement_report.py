import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
import fungsi_terbilang

class dym_settlement(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(dym_settlement, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'terbilang':self.terbilang
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no
    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    
report_sxw.report_sxw('report.rml.settlement', 'dym.settlement', 'addons/dym_advance_payment/report/dym_settlement_report.rml', parser = dym_settlement, header = False)