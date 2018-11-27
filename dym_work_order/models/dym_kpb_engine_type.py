import time
from datetime import datetime
from openerp.osv import fields, osv

class dym_kategori_nilai_mesin(osv.osv):
    _name = "dym.kpb.engine.type"     
    _columns = {
                'engine_no' :fields.char('Engine Number'),
                'name':fields.char('Kategori'),
                'workshop_id': fields.many2one('dym.workshop.category', string='Workshop Category'),
                'kategori_line': fields.one2many('dym.kpb.engine.price','kategori_id', string='Kategori Nilai Mesin'),
    }
    _sql_constraints = [
    ('unique_name_engine_no', 'unique(name,engine_no,workshop_id)', 'Nomor Engine, Nama dan Workshop Kategori harus unik !'),
]    
class dym_kategori_nilai_mesin_line(osv.osv):
    _name = "dym.kpb.engine.price"
    _rec_name = "kpb_ke"
    _columns = {
                
                'kategori_id' : fields.many2one('dym.kpb.engine.type',string="Kategori Nilai Mesin"),
                'kpb_ke' :fields.integer('KPB Ke'),
                'jasa':fields.float('Jasa'),
                'oli':fields.float('Oli'),
                'kompensasi_oli':fields.float('Kompensasi Oli'),

                } 
    