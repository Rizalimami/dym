import time
from datetime import datetime
from openerp.osv import fields, osv
  
class dym_questionnaire(osv.osv):
    _name = 'dym.questionnaire'
    
    SELECTION_TYPE = [
        ('Bidang Usaha','Bidang Usaha'),
        ('Status HP','Status HP'),
        ('Status Rumah','Status Rumah'),
        ('JenisKelamin','Jenis Kelamin'),
        ('Agama','Agama'),
        ('Pendidikan','Pendidikan'),
        ('Pekerjaan','Pekerjaan'),
		('PekerjaanDetail','PekerjaanDetail'),
        ('Pengeluaran','Pengeluaran'),
        ('MerkMotor','Merk Motor'),
        ('JenisMotor','Jenis Motor'),
        ('Penggunaan','Penggunaan'),
        ('Pengguna','Pengguna'),
        ('Hobi','Hobi'),
        ('JenisKartu','Jenis Kartu'),
        ('JenisPenjualan','Jenis Penjualan'),
        ('KodeCustomer','Kode Customer'),
    ]
    _columns = {
                'type' : fields.selection(SELECTION_TYPE, string="Kode Customer", change_default=True),
                # 'type' : fields.char('Type'),
                'name' : fields.char('Question'),
                'value' : fields.char('Value'),
                'position' : fields.integer('Position'),

    }
        
    def unlink(self, cr, uid, ids, context=None):
        if ids :
                raise osv.except_osv(('Perhatian !'), ("Master Questionnaire tidak bisa didelete !"))
        return super(dym_questionnaire, self).unlink(cr, uid, ids, context=context)