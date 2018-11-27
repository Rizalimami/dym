import time
import datetime
from openerp.tools.translate import _
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from lxml import etree
import re

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
                'employee_id': fields.many2one('hr.employee', 'Employee'),
                }

class dym_employee (osv.osv):
    _inherit = 'hr.employee'
    
    def name_get(self, cr, uid, ids, context=None):
        result = []
        for employee in self.browse(cr, uid , ids):
            result.append((employee.id, "[%s] %s" % (employee.nip, employee.name or '')))
        return result
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []        
        if name and len(name) >= 3:
            ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('nip', operator, name)] + args, limit=limit, context=context or {})
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context or {})
        return self.name_get(cr, uid, ids, context or {})


    def _onchange_province(self, cr, uid, ids, state_id):
        if state_id:
            return {'domain' : {'city_id':[('state_id','=',state_id)]},
                    'value' : {'city_id':False}}
        else:
            return {'domain' : {'city_id':[('state_id','=',False)]},
                    'value' : {'city_id':False}}
        return True
    
    def _onchange_city(self, cr, uid, ids, city_id):
        if city_id:
            return {'domain' : {'kecamatan_id':[('city_id','=',city_id)]},
                    'value' : {'kecamatan_id':False}}
        else:
            return {'domain' : {'kecamatan_id':[('city_id','=',False)]},
                    'value' : {'kecamatan_id':False}}
        return True
            
    def _onchange_kecamatan(self, cr, uid, ids, kecamatan_id):
        if kecamatan_id:
            kec = self.pool.get("dym.kecamatan").browse(cr, uid, kecamatan_id)
            return {'domain' : {'zip_id':[('kecamatan_id','=',kecamatan_id)]},
                    'value' : {'kecamatan':kec.name,'zip_id':False}
                    }
        else:
            return {'domain' : {'zip_id':[('kecamatan_id','=',False)]},
                    'value' : {'kecamatan':False,'zip_id':False}}
        return True
    
    def _onchange_zip(self, cr, uid, ids, zip_id):
        if zip_id:
            kel = self.pool.get("dym.kelurahan").browse(cr, uid, zip_id)
            return {'value' : {'kelurahan':kel.name,}}
        else:
            return {'value' : {'kelurahan':False,}}
        return True

    def _onchange_branch(self, cr, uid, ids, branch_id):
        if branch_id :
            return {'value' : {'area_id':False}}
        return True
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids    
    
    _columns = { 
                 'partner_id':fields.many2one('res.partner',string = 'Partner'),
                 'branch_id':fields.many2one('dym.branch',string = 'Branch'),
                 'division':fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')],'Division', change_default=True,select=True),
                 'npwp' : fields.char('No NPWP'),            
                 'shift':fields.selection([('WIB','WIB'),('WIT','WIT'),('WITA','WITA')],'Shift', change_default=True,select=True),
                 'area_id':fields.many2one('dym.area',string = 'Area',domain="[('branch_ids.id','=',branch_id)]"),
                 'sales_ahm':fields.char('Sales Ahm'),
                 'no_kontrak':fields.char('No Kontrak'),
                 'tgl_masuk':fields.date('Tgl Masuk'),
                 'tgl_keluar':fields.date('Tgl Keluar'),
                 'nip':fields.char('NIP'),
                 'street':fields.char('Address'),
                 'street2': fields.char(),
                 'rt':fields.char('rt',size = 3),
                 'rw':fields.char('rw',size = 3),
                 'kelurahan':fields.char('Kelurahan',size = 100),
                 'kecamatan_id':fields.many2one('dym.kecamatan','Kecamatan'),
                 'kecamatan':fields.char('Kecamatan', size=100),
                 'city_id':fields.many2one('dym.city','City'),
                 'state_id':fields.many2one('res.country.state','Province'),
                 'zip_id':fields.many2one('dym.kelurahan','ZIP Code'),
                 'phone':fields.char('No Telp'),
                 'mobile':fields.char('No.Handphone'),
                 'fax':fields.char('Fax'),
                 'email':fields.char('Email'),
                 'pmt_ke':fields.selection([('0','0'),('1','1'),('2','2'),('3','3')],'PMT ke', change_default=True,select=True),
                 'job_id': fields.many2one('hr.job', 'Job Title',domain="['|',('department_id','=',department_id),('department_id','=',False)]"),
                 'branch_control' : fields.related('job_id','branch_control',type='boolean',string='Branch Control'),
                 'wo_target': fields.float('Target'),
                 'mt_khusus': fields.boolean('Is MT Khusus'),
                }
                
    _defaults={
                'tgl_masuk':fields.date.context_today,
                'branch_id': _get_default_branch,
               
               }
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_employee, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        if context.get('branch_control') :          
            doc = etree.XML(res['arch'])
            nodes_branch = doc.xpath("//field[@name='job_id']")
            for node in nodes_branch:
                node.set('domain', '[("salesman", "=", True)]')
            res['arch'] = etree.tostring(doc)
        return res
        
    def create(self,cr,uid,vals,context=None):
        if not vals.get('nip') :
            vals['nip'] = self.pool.get('ir.sequence').get_nik_per_branch(cr, uid, vals['branch_id'])
        if not vals.get('work_email') :
            vals['work_email'] = vals['nip']
        employee =  super(dym_employee, self).create(cr, uid, vals, context=context) 
        
        ###### Make user based on employee #######
        val = self.browse(cr,uid,employee)
        # if not val.job_id.group_id  :
        #     raise osv.except_osv(('Perhatian !'), ("User Group belum diisi di Master 'Job' !"))
        obj_res_partner = self.pool.get('res.partner')
        res_partner_id = {
            'name': vals['name'],
            'default_code': vals['nip'],
            'street': vals['street']  ,
            'street2': vals['street2'],
            'rt': vals['rt'],
            'rw': vals['rw'],
            'state_id': vals['state_id'],
            'city_id': vals['city_id'],  
            'kecamatan_id': vals['kecamatan_id'],
            'kecamatan': vals['kecamatan'],
            'zip_id': vals['zip_id'],
            'kelurahan': vals['kelurahan'],
            'phone': vals['phone'],
            'mobile': vals['mobile'],
            'email': vals['work_email'] ,                               
            }
        res_partner=obj_res_partner.create(cr,uid,res_partner_id,context=context)
        self.write(cr, uid, employee, {'partner_id' : res_partner})
        update_partner = obj_res_partner.write(cr,uid,res_partner,{'employee_id': employee,'customer': False})
        
        ######## Cek Tanggal Keluar ########
        if val.tgl_keluar :
            self.write(cr,uid,employee,{'active':False})
        return employee
    
    def npwp_onchange(self,cr,uid,ids,npwp,context=None):
        warning = {}
        value = {}
        result = {}
        if npwp:
            formatted_npwp = ''
            npwp_normalize = npwp.replace(' ', '').upper()
            splitted_npwp = re.findall(r'\d+', npwp_normalize)
            if len(splitted_npwp) == 6:
              if len(splitted_npwp[0]) == 2 and len(splitted_npwp[1]) == 3 and len(splitted_npwp[2]) == 3 and len(splitted_npwp[3]) == 1 and len(splitted_npwp[4]) == 3 and len(splitted_npwp[5]) == 3:                
                formatted_npwp = splitted_npwp[0] + '.' + splitted_npwp[1] + '.' + splitted_npwp[2] + '.' + splitted_npwp[3] + '-' + splitted_npwp[4] + '.' + splitted_npwp[5]
                return {'value':{'npwp':formatted_npwp}}
            elif len(splitted_npwp) == 1 and len(splitted_npwp[0]) == 15:
                formatted_npwp = splitted_npwp[0][:2] + '.' + splitted_npwp[0][2:-10] + '.' + splitted_npwp[0][5:-7] + '.' + splitted_npwp[0][8:-6] + '-' + splitted_npwp[0][9:-3] + '.' + splitted_npwp[0][-3:]
                return {'value':{'npwp':formatted_npwp}}
            warning = {
                'title': ('Perhatian !'),
                'message': (('Format nomor npwp salah, mohon isi nomor npwp dengan format yang benar! (ex. 99.999.999.9-999.999)')),
            }
            value['npwp'] = self.browse(cr, uid, ids).npwp
            result['warning'] = warning
            result['value'] = value
            return result
    
    def onchange_department(self,cr,uid,ids,job_id,context=None):
        if job_id :
            department = self.pool.get('hr.job').browse(cr,uid,job_id).department_id.id
            return {'value':{'department_id':department}}
        return True
            
    def write(self,cr,uid,ids,vals,context=None):
        user_pool = self.pool.get('res.partner')  
        job_pool = self.pool.get('hr.job')
        user_vals = {}
        user = self.browse(cr,uid,ids)
        # if vals.get('tgl_keluar') :
        #     vals['active'] = False 
        #     user_vals['active'] = False
        # if vals.get('shift') :
        #     if vals.get('shift') == 'WIB' :
        #         user_vals['tz'] = 'Asia/Jakarta'
        #     elif vals.get('shift') == 'WITA' :
        #         user_vals['tz'] = 'Asia/Pontianak'
        #     elif vals.get('shift') == 'WIT' :
        #         user_vals['tz'] = 'Asia/Jayapura'          
        # if vals.get('job_id') :
        #     job_id = job_pool.browse(cr,uid,vals['job_id'])
        #     user_vals['groups_id'] =[(6,0,[job_id.group_id.id])]
        # if vals.get('area_id') :
        #     user_vals['area_id'] = vals['area_id'] 
        # if vals.get('nip') :
        #     user_vals['login'] = vals['nip']  
        if vals.get('work_email'):
            user_vals['email'] = vals['work_email']
        if vals.get('name'):
            user_vals['name'] = vals['name']  
        if user_vals and user.partner_id:
            user_pool.write(cr,uid,user.partner_id.id,user_vals)
        res = super(dym_employee, self).write(cr, uid, ids, vals, context=context) 

        return res
            
            
            
