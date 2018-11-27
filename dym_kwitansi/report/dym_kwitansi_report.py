import time
from openerp.report import report_sxw
import time
import fungsi_terbilang

class dym_kwitansi(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(dym_kwitansi, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'terbilang':self.terbilang
        })
    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    
report_sxw.report_sxw('report.print.kwitansi', 'account.voucher', 'addons/WTC/dym_kwitansi/report/dym_kwitansi_report.rml', parser = dym_kwitansi, header = False)