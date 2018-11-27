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

class dym_proses_birojasa(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(dym_proses_birojasa, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'waktu_local': self.waktu_local,
            'waktu_local': self.waktu_local,
            'koreksi': self.koreksi,
            'prog': self.prog,
            'total': self.total,
            'total_bbn': self.total_bbn,
            'jumlah_cetakan': self.jumlah_cetakan,
            'total_jasa_ap' : self.total_jasa_ap,
            'total_estimasi_ap' : self.total_estimasi_ap,
            'total_margin_ap' : self.total_margin_ap,
            
            
        })
        
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
        obj_model_id = obj_model.search(self.cr, self.uid,[ ('model','=','dym.proses.birojasa') ])[0]
        obj_ir = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid,[('report_name','=','rml.proses.birojasa')])
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
    
    def koreksi(self):
        order = self.pool.get('dym.proses.birojasa.line').search(self.cr, self.uid,[("proses_biro_jasa_id", "in", self.ids)])
        tot_koreksi=0
        for line in self.pool.get('dym.proses.birojasa.line').browse(self.cr, self.uid, order) :
            tot_koreksi += line.koreksi
        return tot_koreksi
    
    def prog(self):
        order = self.pool.get('dym.proses.birojasa.line').search(self.cr, self.uid,[("proses_biro_jasa_id", "in", self.ids)])
        tot_prog=0
        for line in self.pool.get('dym.proses.birojasa.line').browse(self.cr, self.uid, order) :
            tot_prog += line.pajak_progressive
        return tot_prog
    
    def total(self):
        order = self.pool.get('dym.proses.birojasa.line').search(self.cr, self.uid,[("proses_biro_jasa_id", "in", self.ids)])
        tot_tagihan=0
        for line in self.pool.get('dym.proses.birojasa.line').browse(self.cr, self.uid, order) :
            tot_tagihan += line.total_tagihan
        return tot_tagihan

    
    def total_bbn(self):
        order = self.pool.get('dym.proses.birojasa.line').search(self.cr, self.uid,[("proses_biro_jasa_id", "in", self.ids)])
        tot_bbn=0
        for x in self.pool.get('dym.proses.birojasa.line').browse(self.cr, self.uid, order) :
           tot_bbn +=  x.total_estimasi
        return tot_bbn

    def total_jasa_ap(self):
        order = self.pool.get('dym.proses.birojasa.line').search(self.cr, self.uid,[("proses_biro_jasa_id", "in", self.ids)])
        tot_jasa_ap=0
        for x in self.pool.get('dym.proses.birojasa.line').browse(self.cr, self.uid, order) :
           tot_jasa_ap +=  x.total_jasa
        return tot_jasa_ap

    def total_estimasi_ap(self):
        order = self.pool.get('dym.proses.birojasa.line').search(self.cr, self.uid,[("proses_biro_jasa_id", "in", self.ids)])
        tot_estimasi_ap=0
        for x in self.pool.get('dym.proses.birojasa.line').browse(self.cr, self.uid, order) :
           tot_estimasi_ap +=  x.total_estimasi
        return tot_estimasi_ap

    def total_margin_ap(self):
        order = self.pool.get('dym.proses.birojasa.line').search(self.cr, self.uid,[("proses_biro_jasa_id", "in", self.ids)])
        tot_margin_ap=0
        for x in self.pool.get('dym.proses.birojasa.line').browse(self.cr, self.uid, order) :
           tot_margin_ap +=  x.margin
        return tot_margin_ap
 
report_sxw.report_sxw('report.rml.proses.birojasa', 'dym.proses.birojasa', 'addons/dym_proses_stnk/report/dym_proses_birojasa_report.rml', parser = dym_proses_birojasa, header = False)