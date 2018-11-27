import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import string  

class dym_res_partner(osv.osv):
    _inherit = "res.partner"
             
    _columns = {
        'cabang_partner_line' : fields.one2many('dym.cabang.partner','partner_id','Cabang Partner'),
        'nama_pt':fields.char('Nama Perusahaan'),
        'street_pt': fields.char('Address'),
        'street2_pt': fields.char(),
        'rt_pt':fields.char('RT', size=3),
        'rw_pt':fields.char('RW',size=3),
        'zip_pt_id':fields.many2one('dym.kelurahan', 'ZIP Code',domain="[('kecamatan_id','=',kecamatan_pt_id),('state_id','=',state_pt_id),('city_id','=',city_pt_id)]"),
        'kelurahan_pt':fields.char('Kelurahan',size=100), 
        'kecamatan_pt_id':fields.many2one('dym.kecamatan','Kecamatan', size=128,domain="[('state_id','=',state_pt_id),('city_id','=',city_pt_id)]"),
        'kecamatan_pt':fields.char('Kecamatan', size=100),
        'city_pt_id':fields.many2one('dym.city','City',domain="[('state_id','=',state_pt_id)]"),
        'state_pt_id':fields.many2one('res.country.state', 'Province'),
        'bidang_usaha_id' : fields.many2one('dym.questionnaire','Bidang Usaha',domain=[('type','=','Bidang Usaha')]),
        'employee_id': fields.many2one('hr.employee','Sales Person'),
    }

class dym_cabang_partner(osv.osv):
    _name = "dym.cabang.partner"
             
    _columns = {
        'partner_id' : fields.many2one('res.partner','Partner'),
        'name' :fields.char('Name'),
        'no_hp':fields.char('Mobile'),
        'no_telp' : fields.char('Phone'),
        'street': fields.char('Address'),
        'street2': fields.char(),
        'rt':fields.char('RT', size=3),
        'rw':fields.char('RW',size=3),
        'zip_id':fields.many2one('dym.kelurahan', 'ZIP Code',domain="[('kecamatan_id','=',kecamatan_id),('state_id','=',state_id),('city_id','=',city_id)]"),
        'kelurahan':fields.char('Kelurahan',size=100), 
        'kecamatan_id':fields.many2one('dym.kecamatan','Kecamatan', size=128,domain="[('state_id','=',state_id),('city_id','=',city_id)]"),
        'kecamatan':fields.char('Kecamatan', size=100),
        'city_id':fields.many2one('dym.city','City',domain="[('state_id','=',state_id)]"),
        'state_id':fields.many2one('res.country.state', 'Province'),
    }

    def change_rtrw(self,cr,uid,ids,rt,rw,context=None):   
        value = {}
        warning = {}
        if rt :
            if len(rt) > 3 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RT tidak boleh lebih dari 3 digit ! ')),
                }
                value = {
                         'rt':False
                         }
            else :
                cek = rt.isdigit()
                if not cek :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('RT hanya boleh angka ! ')),
                    }
                    value = {
                             'rt':False
                             }
        if rw :
            if len(rw) > 3 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RW tidak boleh lebih dari 3 digit ! ')),
                }
                value = {
                         'rw':False
                         }
            else :            
                cek = rw.isdigit()
                if not cek :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('RW hanya boleh angka ! ')),
                    }
                    value = {
                             'rw':False
                             }       
        return {'warning':warning,'value':value} 
             
    def change_nomor(self,cr,uid,ids,nohp,notelp,context=None):
        value = {}
        warning = {}
        if nohp :
            if len(nohp) > 12 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No HP tidak boleh lebih dari 12 digit ! ')),
                }
                value = {
                         'no_hp':False
                         }
            else :
                cek = nohp.isdigit()
                if not cek :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('No HP hanya boleh angka ! ')),
                    }
                    value = {
                             'no_hp':False
                             }
        if notelp :
            if len(notelp) > 11 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No Telepon tidak boleh lebih dari 11 digit ! ')),
                }
                value = {
                         'no_telp':False
                         }
            else :            
                cek = notelp.isdigit()
                if not cek :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('No Telepon hanya boleh angka ! ')),
                    }
                    value = {
                             'no_telp':False
                             }       
        return {'warning':warning,'value':value} 
    
    def _onchange_kecamatan(self, cr, uid, ids, kecamatan_id):
        if kecamatan_id:
            kec = self.pool.get("dym.kecamatan").browse(cr, uid, kecamatan_id)
            return {
                    'value' : {'kecamatan':kec.name}
                    }
        else:
            return {
                    'value' : {'kecamatan':False}}
        return True
    
    def _onchange_zip(self, cr, uid, ids, zip_id):
        if zip_id:
            kel = self.pool.get("dym.kelurahan").browse(cr, uid, zip_id)
            return {'value' : {'kelurahan':kel.name,}}
        else:
            return {'value' : {'kelurahan':False,}}
        return True
