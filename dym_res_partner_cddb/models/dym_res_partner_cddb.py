import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import string  

class dym_cddb(osv.osv):
    _name = "dym.cddb"

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            tit = "%s" % (record.cddb_code,)
            res.append((record.id, tit))
        return res
    
    def _get_code(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('kode_customer', False)
    
             
    _columns = {
        "kartukeluarga_ids": fields.related("customer_id", "kartukeluarga_ids", type="one2many", relation="dym.kartu.keluarga"),
        'customer_id' : fields.many2one('res.partner','customer_id'),
        'name' :fields.char('Name'),
        'status_hp_id' : fields.many2one('dym.questionnaire','Status HP',domain=[('type','=','Status HP')]),
        'status_rumah_id' : fields.many2one('dym.questionnaire','Status Rumah',domain=[('type','=','Status Rumah')]),
        'kode_customer' : fields.selection([('G','Group Customer'),('I','Individual Customer(Regular)'),('J','Individual Customer (Joint Promo)'),('C','Individual Customer (Kolektif)')], string="Kode Customer", change_default=True),
        'penanggung_jawab' : fields.char('Penanggung Jawab'),
        'jenis_kelamin_id' : fields.many2one('dym.questionnaire','Jenis Kelamin',domain=[('type','=','JenisKelamin')]),
        'dpt_dihubungi' : fields.selection([('Y','Ya'),('N','Tidak')],string="Dapat Dihubungi"),
        'agama_id' : fields.many2one('dym.questionnaire','Agama',domain=[('type','=','Agama')]),
        'pendidikan_id' : fields.many2one('dym.questionnaire','Pendidikan',domain=[('type','=','Pendidikan')]),
        'pekerjaan_id' : fields.many2one('dym.questionnaire','Pekerjaan',domain=[('type','=','Pekerjaan')]),
		
		#Yordan
		'pekerjaan_id2' : fields.many2one('dym.questionnaire','Pekerjaan Detail',domain=[('type','=','PekerjaanDetail')]),
		'pkj_detail': fields.boolean('PekerjaanDtl'),
		
        'pengeluaran_id' : fields.many2one('dym.questionnaire','Pengeluaran',domain=[('type','=','Pengeluaran')]),
        'merkmotor_id' : fields.many2one('dym.questionnaire','Merk Motor',domain=[('type','=','MerkMotor')]),
        'jenismotor_id' : fields.many2one('dym.questionnaire','Jenis Motor',domain=[('type','=','JenisMotor')]),
        'penggunaan_id' : fields.many2one('dym.questionnaire','Penggunaan',domain=[('type','=','Penggunaan')]),
        'pengguna_id' : fields.many2one('dym.questionnaire','Pengguna',domain=[('type','=','Pengguna')]),
        'hobi_id' : fields.many2one('dym.questionnaire','Hobi',domain=[('type','=','Hobi')]),
        'jenis_kartu_id' : fields.many2one('dym.questionnaire','Jenis Kartu',domain=[('type','=','JenisKartu')]),
        'sms_broadcast' : fields.selection([('Y','Ya'),('N','Tidak')],string="SMS Broadcast"),
        'program' : fields.selection([('1','Loyality Member Card'),('2','Community Program')],string="Program"),
        'id_program' : fields.char('ID'),
        'email':fields.char(string="Email"),
        'facebook':fields.char(string="Facebook"),
        'twitter':fields.char(string="Twitter"),
        'instagram':fields.char(string="Instagram"),
        'youtube':fields.char(string="Youtube"),
        'karakteristik':fields.char(string="Karakteristik Konsumen"),
        #'no_ktp':fields.char('No KTP'),
		
		#Kiki
		'no_ktp':fields.char('No KTP / KITAS', size=16),
        
		'cddb_code':fields.char(string="CDDB Code"),
        'birtdate':fields.date('Day of Birth'),
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
        'default_code':fields.char(string="Default Code"),
		'pkj_detail': fields.boolean('PekerjaanDtl'),
		
		# Aris
        'wni_wna': fields.selection([('1', ' WNI'), ('2', ' WNA')], string="WNI/WNA"),
        'no_kk':fields.char('No KK'),

        # Alih
        'ro_bd_id':fields.char(string="RO BD ID", size=10),
        'ref_id':fields.char(string="REF ID", size=10),
    }

    _defaults = {
        'kode_customer':_get_code,
    }

    _sql_constraints = [
        ('unique_name_code', 'unique(customer_id,cddb_code)', 'Data CDDB sudah ada, silahkan cek kembali Nama Konsumen dan Code CDDB !'),
    ] 
	
	#Aris
    def change_nokk(self,cr,uid,ids,no_kk,context=None):
        value = {}
        warning = {}
        if no_kk :
            cek = no_kk.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No KK hanya boleh angka ! ')),
                }
                value = {
                            'no_kk':False
                        }
        return {'warning':warning,'value':value}

	
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
            if len(nohp) > 13 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No HP tidak boleh lebih dari 13 digit ! ')),
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
           
    def create(self,cr,uid,vals,context=None):          
        partner = self.pool.get('res.partner').browse(cr,uid,vals['customer_id'])
        cddb = super(dym_cddb, self).create(cr, uid, vals, context=context) 
        data = self.browse(cr,uid,cddb)
        cddb_code = self.get_cddb_code(cr, uid, data.id, partner.name,data.customer_id,context)
  
        if data.kode_customer == 'I' or data.kode_customer == 'C' :
            data.write({'penanggung_jawab':'N'})
            if data.no_hp == False :
                data.write({'no_hp':'01234'})
        
        data.write({'cddb_code':cddb_code})
        return cddb

    def get_cddb_code(self,cr,uid,ids,name,customer_id,context=None):
        cddb_code = name.replace(' ','')
        cddb_code = cddb_code[:10]
        cddb = self.pool.get('dym.cddb').search(cr,uid,[
                                                        ('customer_id','=',customer_id.id),
                                                        ])
        split_code = []
        cddb_brw = self.pool.get('dym.cddb').browse(cr,uid,cddb)
            
        if len(cddb) == 1 :
            
            a = '001'
            cddb_code = cddb_code + a
                    
        elif cddb_brw :
            for x in cddb_brw :
                if x.cddb_code :
                    split = int(x.cddb_code[10:13])
                    split_code.append(split)
            split = max(split_code)
            code = split + 1
            code = str(code)
            
            if len(code) == 1 :
                cddb_code = cddb_code + '00' + code
            elif len(code) == 2 :
                cddb_code = cddb_code + '0' + code
            else :
                cddb_code = cddb_code + code

        return cddb_code
                    
    def write(self,cr,uid,ids,vals,context=None):
        lot = self.pool.get('stock.production.lot')
        lot_search = lot.search(cr,uid,[
                                        ('cddb_id','in',ids),
                                        ('lot_status_cddb','!=','ok')
                                        ])
        if lot_search :
            lot_browse = lot.browse(cr,uid,lot_search)
            for x in lot_browse :
                if x.lot_status_cddb == 'udstk' :
                    lot_browse.write({'lot_status_cddb':'ok'})
                if x.lot_status_cddb == 'ok' :
                    lot_browse.write({'lot_status_cddb':'ok'})
                if x.lot_status_cddb == 'not' :
                    lot_browse.write({'lot_status_cddb':'cddb'})                    
            
        return super(dym_cddb, self).write(cr, uid, ids, vals, context=context) 
    
    def unlink(self,cr,uid,ids,context=None):
        lot = self.pool.get('stock.production.lot')
        lot_search = lot.search(cr,uid,[
                                        ('cddb_id','in',ids)
                                        ])
        if lot_search :
            lot_browse = lot.browse(cr,uid,lot_search)
            lot_browse.write({'lot_status_cddb':'not'})
            
        return super(dym_cddb, self).unlink(cr, uid, ids, context=context) 
    
	#Yordan
    def get_pkj_id(self, cr, uid, ids, pekerjaan_id, context=None):
        dom = {}
        pekerjaandetail_ids = []
        pekerjaan_ids = []
        
        if not pekerjaan_id:
            dom['pekerjaan_id2'] = []
        else:
            pkj_src = self.pool.get('dym.questionnaire').search(cr,uid,[('id','=',pekerjaan_id)])
            pkj_brw = self.pool.get('dym.questionnaire').browse(cr,uid,pkj_src)

            pkj_src_2 = self.pool.get('dym.questionnaire').search(cr,uid,[('position','=',pkj_brw.position),('type','in',['Pekerjaan'])])
            pkj_brw_2 = self.pool.get('dym.questionnaire').browse(cr,uid,pkj_src_2)

            pkj_dtl_src_2 = self.pool.get('dym.questionnaire').search(cr,uid,[('position','=',pkj_brw.position),('type','in',['PekerjaanDetail'])])
            pkj_dtl_brw_2 = self.pool.get('dym.questionnaire').browse(cr,uid,pkj_dtl_src_2)
            
            count = 0
            for xx in pkj_brw_2:
                print "---------------------------------------------------------------------------", xx.value, xx.position, xx.name
                pekerjaan_ids.append(xx.id)

            for xx_dtl in pkj_dtl_brw_2:
                print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;", xx_dtl.value, xx_dtl.position, xx_dtl.name
                count = count + 1
                pekerjaandetail_ids.append(xx_dtl.id)

            if count > 1:
                pkj_detail = True
                dom['pkj_detail']=True
                print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", count, pkj_detail
                dom['pekerjaan_id2']=[('id','in',pekerjaandetail_ids)]
            else:
                pkj_detail = False
                dom['pkj_detail']=False
                print "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", count, pkj_detail
                dom['pekerjaan_id2']=[('id','in',pekerjaan_ids)]

            print "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC", count, pkj_detail

            # dom['pekerjaan_id2']=[('id','in',pekerjaandetail_ids)]

        print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", dom
        
        # return pkj_detail
        return {'domain': dom}
	
    def get_domain(self,cr,uid,ids,val,no_hp,name,context=None):
        if name == False:
            raise osv.except_osv(_('Warning!'), _('Isi data nama terlebih dahulu!'))
        domain = {}
        value = {}
        warning = {}
        obj = self.pool.get('dym.questionnaire')
        cekname = name.upper()
        
        if val :
            if cekname[:2] == "PT" or cekname[:2] == "CV" :
                if val not in ['G','J']:
                    warning = {
                                'title': ('Perhatian !'),
                                'message': (('PT atau CV hanya boleh memilih Group Customer / Joint Promo ! ')),                       
                               }
                    value = {
                             'kode_customer':False,
                             }
                    return {'warning':warning,'value':value}  
                 
            elif 'KOPERASI' in cekname or 'KOPRASI' in cekname or 'DINAS' in cekname:
                if val not in ['G','J']:
                    warning = {
                                'title': ('Perhatian !'),
                                'message': (('Koperasi atau Dinas hanya boleh memilih Group Customer / Joint Promo ! ')),                       
                               }
                    value = {
                             'kode_customer':False,
                             }
                    return {'warning':warning,'value':value}                             
        
        #JenisKelamin
        if name :
            search_jk = obj.search(cr,uid,[
                                           ('type','=','JenisKelamin'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_jk = obj.browse(cr,uid,search_jk)
            
            #Agama
            search_agm = obj.search(cr,uid,[
                                           ('type','=','Agama'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_agm = obj.browse(cr,uid,search_agm)
            
            #Pendidikan
            search_pdd = obj.search(cr,uid,[
                                           ('type','=','Pendidikan'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_pdd = obj.browse(cr,uid,search_pdd)   
            
            #Pekerjaan
            search_pkj = obj.search(cr,uid,[
                                           ('type','=','Pekerjaan'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_pkj = obj.browse(cr,uid,search_pkj)
            
            search_pkj2 = obj.search(cr,uid,[
                                           ('type','=','PekerjaanDetail'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_pkj2 = obj.browse(cr,uid,search_pkj2)     
            
            #Pengeluaran        
            search_png = obj.search(cr,uid,[
                                           ('type','=','Pengeluaran'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_png = obj.browse(cr,uid,search_png) 
            
            #MerkMotor        
            search_mmt = obj.search(cr,uid,[
                                           ('type','=','MerkMotor'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_mmt = obj.browse(cr,uid,search_mmt)
    
            #JenisMotor        
            search_jmt = obj.search(cr,uid,[
                                           ('type','=','JenisMotor'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_jmt = obj.browse(cr,uid,search_jmt)
    
            #Penggunaan      
            search_penggunaan = obj.search(cr,uid,[
                                           ('type','=','Penggunaan'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_penggunaan = obj.browse(cr,uid,search_penggunaan)
            
            #Pengguna     
            search_pengguna = obj.search(cr,uid,[
                                           ('type','=','Pengguna'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_pengguna = obj.browse(cr,uid,search_pengguna)
            
            #Hobi     
            search_hobi = obj.search(cr,uid,[
                                           ('type','=','Hobi'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_hobi = obj.browse(cr,uid,search_hobi)
            
            #StatusRumah     
            search_str = obj.search(cr,uid,[
                                           ('type','=','Status Rumah'),
                                           ('name','=','GROUP CUSTOMER')
                                           ])
            browse_str = obj.browse(cr,uid,search_str)
    
            #StatusHP   
            search_hp = obj.search(cr,uid,[
                                           ('type','=','Status HP'),
                                           ('name','=','Tidak Memiliki')
                                           ])
            browse_hp = obj.browse(cr,uid,search_hp)
            
            if no_hp :
                #Status HP
                domain['status_hp_id']=[('type','=','Status HP'),('name','!=','Tidak Memiliki')]
                
            if no_hp == False :
                #Value HP
                domain['status_hp_id']=[('type','=','Status HP'),('name','=','Tidak Memiliki')]
                value['status_hp_id']=browse_hp.id 
                    
            if val == 'G' :
                #StatusRumah
                domain['status_rumah_id']=[('type','=','Status Rumah'),('name','=','GROUP CUSTOMER')]
                value['status_rumah_id']=browse_str.id
                
            if val == 'G' or val == 'J' :
                #JenisKelamin
                domain['jenis_kelamin_id']=[('type','=','JenisKelamin'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['jenis_kelamin_id']=browse_jk.id
                
                #Agama
                domain['agama_id']=[('type','=','Agama'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['agama_id']=browse_agm.id
                
                #Pendidikan            
                domain['pendidikan_id']=[('type','=','Pendidikan'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['pendidikan_id']=browse_pdd.id
                
                #Pekerjaan
                domain['pekerjaan_id']=[('type','=','Pekerjaan'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['pekerjaan_id']=browse_pkj.id
				
				#Yordan
                domain['pekerjaan_id2']=[('type','=','PekerjaanDetail'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['pekerjaan_id2']=browse_pkj2.id
                
                #Pengeluaran
                domain['pengeluaran_id']=[('type','=','Pengeluaran'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['pengeluaran_id']=browse_png.id            
                
                #MerkMotor
                domain['merkmotor_id']=[('type','=','MerkMotor'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['merkmotor_id']=browse_mmt.id            
                
                #JenisMotor
                domain['jenismotor_id']=[('type','=','JenisMotor'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['jenismotor_id']=browse_jmt.id 
                
                #Penggunaan
                domain['penggunaan_id']=[('type','=','Penggunaan'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['penggunaan_id']=browse_penggunaan.id
                
                #Pengguna
                domain['pengguna_id']=[('type','=','Pengguna'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['pengguna_id']=browse_pengguna.id
                
                #Hobi
                domain['hobi_id']=[('type','=','Hobi'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['hobi_id']=browse_hobi.id
            else :
                domain['status_rumah_id']=[('type','=','Status Rumah'),('name','!=','GROUP CUSTOMER')]
                value['status_rumah_id']=False
                domain['jenis_kelamin_id']=[('type','=','JenisKelamin'),('name','!=','GROUP CUSTOMER/JOINT PROMO')] 
                value['jenis_kelamin_id']=False  
                domain['agama_id']=[('type','=','Agama'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['agama_id']=False
                domain['pendidikan_id']=[('type','=','Pendidikan'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['pendidikan_id']=False
                domain['pekerjaan_id']=[('type','=','Pekerjaan'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['pekerjaan_id']=False
                domain['pekerjaan_id2']=[('type','=','PekerjaanDetail'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['pekerjaan_id2']=False
                domain['pengeluaran_id']=[('type','=','Pengeluaran'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['pengeluaran_id']=False
                domain['merkmotor_id']=[('type','=','MerkMotor'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['merkmotor_id']=False
                domain['jenismotor_id']=[('type','=','JenisMotor'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['jenismotor_id']=False
                domain['penggunaan_id']=[('type','=','Penggunaan'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['penggunaan_id']=False
                domain['pengguna_id']=[('type','=','Pengguna'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]   
                value['pengguna_id']=False          
                domain['hobi_id']=[('type','=','Hobi'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]   
                value['hobi_id']=False          
            return {'domain':domain,'value':value}
        
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
        
    def get_customer(self, cr, uid, ids, name,default_code,no_ktp,birthday,street,street2,rt,rw,state,city,kecamatan_id,kecamatan,zip,kelurahan,phone,mobile):
        result = {}     
        if name :
           result.update({'name': name,'no_ktp':no_ktp,'birtdate':birthday,'street':street,'street2':street2,'rt':rt,'rw':rw,'state_id':state,'city_id':city,'kecamatan_id':kecamatan_id,'kecamatan':kecamatan,'zip_id':zip,'kelurahan':kelurahan,'no_hp':mobile,'no_telp':phone})
        return { 'value' : result}
           
    def onchange_jenis(self,cr,uid,ids,jenis,kode,context=None):
        domain = {}
        value = {}
        if jenis :
            search = self.pool.get('dym.questionnaire').search(cr,uid,[
                                         ('id','=',jenis)
                                         ])
            browse = self.pool.get('dym.questionnaire').browse(cr,uid,search)
            search_mmt = self.pool.get('dym.questionnaire').search(cr,uid,[
                                       ('type','=','MerkMotor'),
                                       ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                       ])
            browse_mmt = self.pool.get('dym.questionnaire').browse(cr,uid,search_mmt)
            if search :
                value['merkmotor_id']=False
                if browse.name == 'Belum pernah memiliki' :
                    domain['merkmotor_id']=[('type','=','MerkMotor'),('value','=','6')]
                if browse.name != 'Belum pernah memiliki' :
                    if kode == 'G' or kode == 'J' :
                        value['merkmotor_id']=browse_mmt.id
                        domain['merkmotor_id']=[('type','=','MerkMotor'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                        
                    else :
                        domain['merkmotor_id']=[('type','=','MerkMotor'),('name','!=','GROUP CUSTOMER/JOINT PROMO'),('value','!=','6')]

        
        return {'domain':domain,'value':value}   

	#Kiki
    def onchange_punctuation(self,cr,uid,ids,no_ktp,penanggung_jawab,context=None):    
        value = {}
        warning = {}

        if no_ktp :
            if no_ktp != '0' and len(no_ktp) == 16:
                no_ktp = "".join(l for l in no_ktp if l not in string.punctuation)  
                value = {
                    'no_ktp':no_ktp
                    }  
            elif no_ktp != '0' and len(no_ktp) != '16':
                warning = {
                            'title': ('Perhatian !'),
                            'message': (('No KTP / KITAS harus 16 digit ! ')),
                        }    
                value = {
                         'no_ktp':False
                         }

        if penanggung_jawab :
            penanggung_jawab = "".join(l for l in penanggung_jawab if l not in string.punctuation)  
            value = {
                     'penanggung_jawab':penanggung_jawab
                     }                                  
        return {'value':value,'warning':warning}
            
class dym_kartu_keluarga(osv.osv):
    _name = "dym.kartu.keluarga"
    _columns = {
        'customer_id' : fields.many2one('res.partner','Customer'),
        'name' : fields.char('Nama'),
        'nik' : fields.char('Nik'),
        'tgl_lahir' : fields.date('Tgl Lahir'),
        'hub' : fields.selection([('1','Suami'),('2','Istri'),('3','Anak'),('4','Saudara'),('5','Ayah'),('6','Ibu')],string="Hubungan")
    }
    
           
           
           
           
           
           
           
