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

class dealer_sale_order(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(dealer_sale_order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'terbilang': self.terbilang,
            'invoice_id': self.invoice_id,
            'waktu_local': self.waktu_local,
            'ps_finco_nya': self.ps_finco_nya,
            
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
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date
    
    
    def ps_finco_nya(self):
        val = self.pool.get('dealer.sale.order').browse(self.cr, self.uid, self.ids)
        total_ps_finco=0
        for line in val.dealer_sale_order_line:
            for disc in line.discount_line:
                total_ps_finco += disc.ps_finco
        if val.print_subsidi_tax == True:
            total_ps_finco = (total_ps_finco/0.98) + ((total_ps_finco/0.98) * 0.1)
        return total_ps_finco
    
    def invoice_id(self):
        invoice = self.pool.get('dealer.sale.order').browse(self.cr, self.uid, self.ids).name
        invoice2 = self.pool.get('account.invoice').search(self.cr, self.uid,[ ('origin','ilike',invoice),('tipe','=','customer') ])
        no_invoice = self.pool.get('account.invoice').browse(self.cr, self.uid,invoice2).number
        return no_invoice
    
report_sxw.report_sxw('report.rml.dealer.sale.order.subsidi.leasing', 'dealer.sale.order', 'addons/dealer_sale_order/report/dealer_sale_order_subsidi_leasing_report.rml', parser = dealer_sale_order, header = False)