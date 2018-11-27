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
            'jumlah_cetakan': self.jumlah_cetakan,
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
    
    def jumlah_cetakan(self):
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(self.cr, self.uid,[ ('model','=','stock.picking') ])[0]
        obj_ir = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid,[('report_name','=','rml.dym.internal.transfer')])
        obj_ir_id = self.pool.get('ir.actions.report.xml').browse(self.cr, self.uid,obj_ir).id
        obj_jumlah_cetak=self.pool.get('dym.jumlah.cetak').search(self.cr,self.uid,[('report_id','=',obj_ir_id),('model_id','=',obj_model_id),('transaction_id','=',self.ids[0])])
        if not obj_jumlah_cetak :
            jumlah_cetak_id = {
            'model_id':obj_model_id,
            'transaction_id': self.ids[0],
            'jumlah_cetak': 1,
            'report_id':obj_ir_id                            
            }
            jumlah_cetak=1
            move=self.pool.get('dym.jumlah.cetak').create(self.cr,self.uid,jumlah_cetak_id)
        else :
            obj_jumalah=self.pool.get('dym.jumlah.cetak').browse(self.cr,self.uid,obj_jumlah_cetak)
            jumlah_cetak=obj_jumalah.jumlah_cetak+1
            self.pool.get('dym.jumlah.cetak').write(self.cr, self.uid,obj_jumalah.id, {'jumlah_cetak': jumlah_cetak})
        return jumlah_cetak
    

    
report_sxw.report_sxw('report.rml.stock.picking.internal.transfer', 'stock.picking', 'addons/dym_stock/report/dym_internal_transfer_report.rml', parser = stock_picking, header = False)