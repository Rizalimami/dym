from openerp.osv import fields, osv

class dym_kpb_expired(osv.osv):
    _name = 'dym.kpb.expired'
    
    _columns = {
        'name': fields.char('Engine Code', size=5),
        'description': fields.char('Description', required=True),
        'service':fields.selection([('1','1'),('2','2'),('3','3'),('4','4')],'Service',select=True,required=True),
        'hari': fields.integer('Hari', required=True,size=5),
        'km': fields.integer('Km', required=True,size=5),
        }

    
    _sql_constraints = [
        ('unique_service', 'unique(name,service)', 'Engine Sudah Terdaftar !'),
    ]
    
    