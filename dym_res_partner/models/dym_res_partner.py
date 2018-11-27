import time
from datetime import datetime
import string 
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api
from openerp.osv.expression import get_unaccent_wrapper
import re

import phonenumbers
from phonenumbers import carrier
from phonenumbers.phonenumberutil import number_type


class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    def _get_payment_term(self, cr, uid, context=None):
        obj_payment_term = self.pool.get('account.payment.term')
        id_payment_term = obj_payment_term.search(cr, uid, [('name','=','Immediate Payment')])
        if id_payment_term :
            return id_payment_term[0]
        return False

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    _columns = {
        'parent_name': fields.related('parent_id', 'name', type='char', readonly=True, string='Parent name'),
        'default_code': fields.char('Partner Code'),
        'principle': fields.boolean('Principle'),
        'biro_jasa': fields.boolean('Biro Jasa'),
        'kas_negara': fields.boolean('Kas Negara'),
        'forwarder': fields.boolean('Forwarder'),
        'supplier': fields.boolean('General Supplier', help="Check this box if this contact is a supplier. If it's not checked, purchase people will not see it when encoding a purchase order."),
        'showroom': fields.boolean('Showroom'),
        'ahass': fields.boolean('Ahass'),
        'dealer': fields.boolean('Dealer'),
        'finance_company': fields.boolean('Finance Company'),
        'vat': fields.related('npwp', string="TIN", type="char", help="Tax Identification Number. Check the box if this contact is subjected to taxes. Used by the some of the legal statements.", store=True),
        'ahm_code': fields.char('AHM Code'),
        'dealer_code': fields.char('Dealer Code'),
        'kode_pajak_id':fields.selection([('1','010'),('2','020'),('3','030'),('4','040'),('5','050'),('6','060'),('7','070'),('8','080'),('9','090')],'Kode Transaksi FP'),
        'tipe_faktur_pajak' : fields.selection([('tanpa_fp','Tanpa Faktur Pajak'),('satuan','Satuan'),('gabungan','Gabungan')],'Tipe Faktur Pajak'),
        'pkp' : fields.boolean('PKP'),
        'npwp': fields.char('No.NPWP'),
        'tgl_kukuh': fields.date('Tgl Kukuh'),
        'mobile_provider': fields.char('Mobile Provider'),
        
        #Alamat di Header
        'rt':fields.char('RT', size=3),
        'rw':fields.char('RW',size=3),
        'zip_id':fields.many2one('dym.kelurahan', 'ZIP Code',domain="[('kecamatan_id','=',kecamatan_id),('state_id','=',state_id),('city_id','=',city_id)]"),
        'kelurahan':fields.char('Kelurahan',size=100), 
        'kecamatan_id':fields.many2one('dym.kecamatan','Kecamatan', size=128,domain="[('state_id','=',state_id),('city_id','=',city_id)]"),
        'kecamatan':fields.char('Kecamatan', size=100),
        'city_id':fields.many2one('dym.city','City',domain="[('state_id','=',state_id)]"),
                        
        #Alamat di Tab Customer Info
        'sama':fields.boolean(''), #diberi required True
        'street_tab': fields.char('Address'),
        'street2_tab': fields.char(),
        'rt_tab':fields.char('RT', size=3),
        'rw_tab':fields.char('RW',size=3),
        'zip_tab_id':fields.many2one('dym.kelurahan', 'ZIP Code',domain="[('kecamatan_id','=',kecamatan_tab_id),('state_id','=',state_tab_id),('city_id','=',city_tab_id)]"),
        'kelurahan_tab':fields.char('Kelurahan',size=100), 
        'kecamatan_tab_id':fields.many2one('dym.kecamatan','Kecamatan', size=128,domain="[('state_id','=',state_tab_id),('city_id','=',city_tab_id)]"),
        'kecamatan_tab':fields.char('Kecamatan', size=100),
        'city_tab_id':fields.many2one('dym.city','City',domain="[('state_id','=',state_tab_id)]"),
        'state_tab_id':fields.many2one('res.country.state', 'Province'),
        
        #Field yang ada di Tab Customer Info
        'birthday':fields.date('Date of Birth'),
        'hp_status':fields.selection([('aktif','Aktif'),('TidakAktif','Tidak Aktif')],'HP Status'),
        'gender':fields.selection([('lakilaki', 'Laki-laki'),('perempuan', 'Perempuan')],'Jenis Kelamin'),
        'no_kk':fields.char('No. KK',50),
        'religion':fields.selection([('Islam', 'Islam'),('Kristen', 'Kristen'),('Katholik', 'Katholik'),('Hindu', 'Hindu'),('Budha', 'Budha')],'Religion'),
        'no_ktp':fields.char('No.KTP',50),
        'property_account_payable': fields.property(
            type='many2one',
            relation='account.account',
            string="Account Payable",
            domain="[('type', '=', 'payable')]",
            help="This account will be used instead of the default one as the payable account for the current partner",
            required=False),
        'property_account_receivable': fields.property(
            type='many2one',
            relation='account.account',
            string="Account Receivable",
            domain="[('type', '=', 'receivable')]",
            help="This account will be used instead of the default one as the receivable account for the current partner",
            required=False),      
        'property_account_rounding': fields.property(
            type='many2one',
            relation='account.account',
            string="Account Rounding",
            required=False),                    
        'pendidikan':fields.selection([('noSD', 'Tidak Tamat SD'),('sd', 'SD'),('sltp', 'SLTP/SMP'),('slta', 'SLTA/SMA'),('akademik', 'Akademi/Diploma'),('sarjana', 'Sarjana(S1)'),('pascasarjana', 'Pasca Sarjana')],'Pendidikan'),
        'pekerjaan':fields.selection([('pNegeri', 'Pegawai Negeri'),('pSwasta', 'Pegawai Swasta'),('ojek', 'Ojek'),('pedagang', 'Pedagang/Wiraswasta'),('pelajar', 'Pelajar/Mahasiswa'),('guru', 'Guru/Dosen'),('tni', 'TNI/Polri'),('irt', 'Ibu Rumah Tangga'),('petani/nelayan', 'Petani/Nelayan'),('pro', 'Profesional(Contoh : Dokter)'),('lain', 'Lainnya')],'Pekerjaan'),
        'pengeluaran':fields.selection([('<900', '< Rp.900.000,-'),('900125', 'Rp.900.001,- s/d Rp.1.250.000,-'),('125175', 'Rp.1.250.001,- s/d Rp.1.750.000,-'),('175250', 'Rp.1.750.001,- s/d Rp.2.500.000,-'),('250400', 'Rp.2.500.001,- s/d Rp.4.000.000,-'),('400600', 'Rp.4.000.001,- s/d Rp.6.000.000,-'),('600000', '> Rp.6.000.000,-')],'Pengeluaran /Bulan'),
        'rel_code': fields.related('default_code', string='Partner Code', type="char", readonly="True"),
        'branch_id':fields.many2one('dym.branch',string='Branch'),
        'direct_customer': fields.boolean(string='Direct Customer'),
        'branch': fields.boolean(string='Branch (Boolean)'),
        'is_customer_depo':fields.boolean('Customer Depo'),
        'is_group_customer':fields.boolean('Group Customer'),
        'member':fields.char('Member Number'),
        'creditur_debitur':fields.boolean('Creditur / Debitur'),
        
        #Forwarder
        'driver_lines': fields.one2many('dym.driver.line','partner_id','Driver'),
        'plat_number_lines': fields.one2many('dym.plat.number.line','partner_id','Plat Number'),
    }

    _defaults = {
        'tz': api.model(lambda self: self.env.context.get('tz', 'Asia/Jakarta')),
        'sama': True,
        'default_code': 'BPA/',
        'branch_id':_get_default_branch,        
    }
         
    _sql_constraints = [
        ('unique_member', 'unique(member)', 'Nomor Member sudah terdaftar!'),
    ]

    # def _unique_no_ktp(self, cr, uid, ids, context=None):
    #     for l in self.browse(cr, uid, ids, context=context):
    #         if l.no_ktp:
    #             if self.search(cr,uid,[('no_ktp','=',l.no_ktp),('id','!=',l.id)]):
    #                 return False
    #     return True
    
    # _constraints = [
    #     (_unique_no_ktp, 'No KTP Duplicate!', ['no_ktp']),
    # ]

    def default_get(self, cr, uid, fields, context=None):
         context = context or {}
         res = super(res_partner, self).default_get(cr, uid, fields, context=context)
         if 'property_payment_term' in fields:
             res.update({'property_payment_term': self._get_payment_term(cr, uid)})
         return res

    def _display_address(self, cr, uid, address, without_company=False, context=None):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''


        '''
        <xpath expr="//field[@name='city']" position="before">
            <group>
                <div>
                    <field name="street" placeholder="Street..." on_change="onchange_address(street,street2,rt,rw,state_id,city_id,kecamatan_id,kecamatan,zip_id,kelurahan)" />
                    <div>
                        <field name="street2" placeholder="Street" style="width: 50%%" on_change="onchange_address(street,street2,rt,rw,state_id,city_id,kecamatan_id,kecamatan,zip_id,kelurahan)" />
                        <field name="rt" placeholder="RT" style="width: 25%%" on_change="onchange_address(street,street2,rt,rw,state_id,city_id,kecamatan_id,kecamatan,zip_id,kelurahan)" />
                        <field name="rw" placeholder="RW" style="width: 25%%" on_change="onchange_address(street,street2,rt,rw,state_id,city_id,kecamatan_id,kecamatan,zip_id,kelurahan)" />
                        <field name="state_id" on_change="onchange_address(street,street2,rt,rw,state_id,city_id,kecamatan_id,kecamatan,zip_id,kelurahan)" class="oe_no_button" placeholder="Province" style="width: 50%%" options='{"no_open": True}' />
                        <field name="city_id" on_change="onchange_address(street,street2,rt,rw,state_id,city_id,kecamatan_id,kecamatan,zip_id,kelurahan)" placeholder="City" style="width: 50%%" attrs="{'required': ['|','|',('direct_customer','=',True),('is_group_customer','=',True),('customer','=',True)]}" />
                        <field name="kecamatan_id" on_change="onchange_address(street,street2,rt,rw,state_id,city_id,kecamatan_id,kecamatan,zip_id,kelurahan)" placeholder="Kecamatan" style="width: 50%%" />
                        <field name="kecamatan" on_change="onchange_address(street,street2,rt,rw,state_id,city_id,kecamatan_id,kecamatan,zip_id,kelurahan)" placeholder="Kecamatan" style="width: 50%%" />
                        <field name="zip_id" on_change="onchange_address(street,street2,rt,rw,state_id,city_id,kecamatan_id,kecamatan,zip_id,kelurahan)" placeholder="ZIP" style="width: 50%%" options='{"no_open": True}' />
                        <field name="kelurahan" on_change="onchange_address(street,street2,rt,rw,state_id,city_id,kecamatan_id,kecamatan,zip_id,kelurahan)" class="oe_no_button" placeholder="Kelurahan" style="width: 50%%" />
                    </div>
                </div>
            </group>
        </xpath>
        '''


        # get the information that will be injected into the display format
        # get the address format
        # address_format = address.country_id.address_format or \
        #       "%(street)s\n%(street2)s\nRT: %(rt)s RW: %(rw)s Desa/Kel:%(kelurahan)s Kec:%(kecamatan)s\nKab/Kota:%(city)s Prov:%(state_code)s %(zip)s\n%(country_name)s"

        address_format = "%(street)s\n%(street2)s\nRT: %(rt)s RW: %(rw)s Desa/Kel:%(kelurahan)s Kec:%(kecamatan)s\nKab/Kota:%(city_name)s Prov: %(state_name)s Kode Pos: %(kode_pos)s\n%(country_name)s"
        args = {
            'state_code': address.state_id.code or '',
            'state_name': address.state_id.name or '',
            'country_code': address.country_id.code or '',
            'country_name': address.country_id.name or '',
            'company_name': address.parent_name or '',
            'rt': address.rt or '-',
            'rw': address.rw or '-',
            'kelurahan': address.kelurahan or '-',
            'kecamatan': address.kecamatan or '-',
            'city_name': address.city_id and address.city_id.name or '-',
            'kode_pos': address.zip_id and address.zip_id.zip or '-',
        }
        for field in self._address_fields(cr, uid, context=context):
            args[field] = getattr(address, field) or ''
        if without_company:
            args['company_name'] = ''
        elif address.parent_id:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args

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

    def onchange_mobile(self, cr, uid, ids, mobile, context=None):
        value = {}
        warning = {}

        if mobile:
            id_number = phonenumbers.parse(mobile,"ID")
            if not carrier._is_mobile(number_type(id_number)):
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Masukkan nomor handphone dengan benar, misal: 0817989800')),
                }
                value['mobile'] = ''
            else:
                formatted_mobile = phonenumbers.format_number(id_number, phonenumbers.PhoneNumberFormat.E164)
                provider_mobile = eval(repr(carrier.name_for_number(id_number, "en")))
                value['mobile'] = formatted_mobile
                value['mobile_provider'] = provider_mobile

        return {
            'warning': warning,
            'value': value,
        }


    def onchange_customer(self, cr, uid, ids, customer):
        if not customer:
            return {
                'value':{
                    'no_ktp':False,
                    'birthday':False,
                    'gender':False,
                    'religion':False,
                    'no_kk':False,
                    'pendidikan':False,
                    'pekerjaan':False,
                    'pengeluaran':False,
                    'sama':'',
                    }
                }
        return True

    def onchange_dealer(self, cr, uid, ids, dealer, finance_company, principle, ahm_code, dealer_code):
        def_ahm_code = False
        def_dealer_code = False
        
        if dealer:
            def_ahm_code = True
            def_dealer_code = True
        if finance_company:
            def_ahm_code = True
        if principle:
            def_ahm_code = True
        
        return {
                'value':{
                         'ahm_code':ahm_code if def_ahm_code else False,
                         'dealer_code': dealer_code if def_dealer_code else False,
                         }
                }
    
    def showroom_ahass_change(self, cr, uid, ids, showroom, ahass, dealer, context=None):
        value = {}
        value['dealer'] = False
        if showroom or ahass :
            value['dealer'] = True
        return {'value':value}
    
    def onchange_pkp(self, cr, uid, ids, pkp, context=None):
        if not pkp==False:
            return {
                'value':{
                       'npwp':'',
                       'tgl_kukuh':False,
                    }
            }
       
        return True
    
    def onchange_forwarder(self, cr, uid, ids, forwarder, context=None):
        if not forwarder :
            return {'value' : {'plat_number_lines':False, 'driver_lines':False}}
        return True
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.parent_id and not record.is_company:
                name = "%s, %s" % (record.parent_name, name)
            if context.get('show_address_only'):
                name = self._display_address(cr, uid, record, without_company=True, context=context)
            if context.get('show_address'):
                name = name + "\n" + self._display_address(cr, uid, record, without_company=True, context=context)
            name = name.replace('\n\n','\n')
            name = name.replace('\n\n','\n')
            if context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            if record.default_code:
                name = "[%s] %s %s" % (record.default_code, name, '(' + record.member + ')' if record.member else '')
            res.append((record.id, name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like') and len(name) >= 3:
            self.check_access_rights(cr, uid, 'read')
            where_query = self._where_calc(cr, uid, args, context=context)
            self._apply_ir_rules(cr, uid, where_query, 'read', context=context)
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

            # search on the name of the contacts and of its company
            search_name = name
            operator = 'like'
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]
            unaccent = get_unaccent_wrapper(cr)
            where_str = where_str.replace('"res_partner"','p')
            query = """SELECT p.id
                         FROM res_partner p
                      {where} (upper(p.{display_name}) {operator} {percent}
                           OR upper(p.{default_code}) {operator} {percent}
                           OR upper(p.{member}) {operator} {percent})
                     ORDER BY p.{display_name}, p.{default_code}
                    """.format(where=where_str, operator=operator,
                               display_name=unaccent('display_name'),
                               default_code=unaccent('default_code'),
                               member=unaccent('member'),
                               percent=unaccent('%s'))
            where_clause_params += [search_name.upper(), search_name.upper(), search_name.upper()]
            if limit:
                query += ' limit %s'
                where_clause_params.append(limit)
            cr.execute(query, where_clause_params)
            ids = map(lambda x: x[0], cr.fetchall())

            if ids:
                return self.name_get(cr, uid, ids, context)
            else:
                return []
        return []
        

    # def name_search(self, cr, uid, name, args=None, operator='=', context=None, limit=100):
    #     if not args:
    #         args = []
    #     operator = '='
    #     if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
    #         self.check_access_rights(cr, uid, 'read')
    #         where_query = self._where_calc(cr, uid, args, context=context)
    #         self._apply_ir_rules(cr, uid, where_query, 'read', context=context)
    #         from_clause, where_clause, where_clause_params = where_query.get_sql()
    #         where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '
    #         if '*' in name or '%' in name:
    #             operator = 'like'
    #         if '*' in name:
    #             name = name.replace('*','%')
    #         search_name = name
    #         if operator in ('=ilike', '=like'):
    #             operator = operator[1:]
    #         unaccent = get_unaccent_wrapper(cr)
    #         where_str = where_str.replace('"res_partner"','p')
    #         query = """SELECT p.id
    #                      FROM res_partner p
    #                   {where} (upper(p.{display_name}) {operator} {percent}
    #                        OR upper(p.{default_code}) {operator} {percent}
    #                        OR upper(p.{member}) {operator} {percent})
    #                  ORDER BY p.{display_name}, p.{default_code}
    #                 """.format(where=where_str, operator=operator,
    #                            display_name=unaccent('display_name'),
    #                            default_code=unaccent('default_code'),
    #                            member=unaccent('member'),
    #                            percent=unaccent('%s'))
    #         where_clause_params += [search_name.upper(), search_name.upper(), search_name.upper()]
    #         if limit:
    #             query += ' limit %s'
    #             where_clause_params.append(limit)
    #         cr.execute(query, where_clause_params)
    #         ids = map(lambda x: x[0], cr.fetchall())
    #         if ids:
    #             return self.name_get(cr, uid, ids, context)
    #         else:
    #             return []
    #     return []
        
    def create(self, cr, uid, vals, context=None):
        if vals.get('default_code','BPA/') == 'BPA/' :
            vals['default_code'] = self.pool.get('ir.sequence').get_sequence(cr, uid, 'BPA', division=False, padding=6)
        partner_id = super(res_partner, self).create(cr, uid, vals, context=context)
        self.write(cr, uid, partner_id, {'company_id':False})
        return partner_id
    
    def onchange_letter(self,cr,uid,ids,sama,street=None,street2=None,rt=None,rw=None,state_id=None,city_id=None,kecamatan_id=None,kecamatan=None,zip_id=None,kelurahan=None,context=None):
        value ={}
        if not sama :
            value = {
                'street_tab':False,
                'street2_tab':False,
                'rt_tab':False,
                'rw_tab':False,
                'state_tab_id':False,
                'city_tab_id':False,
                'kecamatan_tab_id':False,
                'kecamatan_tab':False,
                'zip_tab_id':False,
                'kelurahan_tab':False,                         
            }
        if sama :
            value = {
                'street_tab':street,
                'street2_tab':street2,
                'rt_tab':rt,
                'rw_tab':rw,
                'state_tab_id':state_id,
                'city_tab_id':city_id,
                'kecamatan_tab_id':kecamatan_id,
                'kecamatan_tab':kecamatan,
                'zip_tab_id':zip_id,
                'kelurahan_tab':kelurahan,                         
            }            
        return {'value':value}

    def _onchange_kecamatan_tab(self, cr, uid, ids, kecamatan_id):
        if kecamatan_id:
            kec = self.pool.get("dym.kecamatan").browse(cr, uid, kecamatan_id)
            return {'value' : {'kecamatan_tab':kec.name}}
        else:
            return {'value' : {'kecamatan_tab':False}}
        return True
    
    def _onchange_zip_tab(self, cr, uid, ids, zip_id):
        if zip_id:
            kel = self.pool.get("dym.kelurahan").browse(cr, uid, zip_id)
            return {'value' : {'kelurahan_tab':kel.name,}}
        else:
            return {'value' : {'kelurahan_tab':False,}}
        return True
        
    def onchange_address(self,cr,uid,ids,street=None,street2=None,rt=None,rw=None,state_id=None,city_id=None,kecamatan_id=None,kecamatan=None,zip_id=None,kelurahan=None,context=None):
        value ={}
        warning = {}
        if street :
            value['street_tab'] = street
        if street2 :
            value['street2_tab'] = street2
        if rt :
            if len(rt) > 3 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RT tidak boleh lebih dari 3 digit ! ')),
                }
                value = {
                         'rt':False
                         }
            cek = rt.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RT hanya boleh angka ! ')),
                }
                value = {
                         'rt':False
                         }  
            else :
                value['rt_tab'] = rt
        if rw :
            if len(rw) > 3 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RW tidak boleh lebih dari 3 digit ! ')),
                }
                value = {
                         'rw':False
                         }
            cek = rw.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RW hanya boleh angka ! ')),
                }
                value = {
                         'rw':False
                         }   
            else :            
                value['rw_tab'] = rw   
        if state_id :
            value['state_tab_id'] = state_id
        if city_id :
            value['city_tab_id'] = city_id              
        if kecamatan_id :
            kec = self.pool.get("dym.kecamatan").browse(cr, uid, kecamatan_id)         
            value['kecamatan_tab_id'] = kecamatan_id
            value['kecamatan_tab'] = kec.name 
            value['kecamatan'] = kec.name
        if zip_id :
            kel = self.pool.get("dym.kelurahan").browse(cr, uid, zip_id)
            value['zip_tab_id'] = zip_id
            value['kelurahan_tab'] = kel.name   
            value['kelurahan'] = kel.name                
        return {'value':value,'warning':warning}     
             
    def change_nomor(self,cr,uid,ids,nohp,notelp,context=None):
        value = {}
        warning = {}
        # if nohp :
        #     if len(nohp) > 13 :
        #         warning = {
        #             'title': ('Perhatian !'),
        #             'message': (('No HP tidak boleh lebih dari 13 digit ! ')),
        #         }
        #         value = {
        #                  'no_hp':False
        #                  }
        #     else :
        #         cek = nohp.isdigit()
        #         if not cek :
        #             warning = {
        #                 'title': ('Perhatian !'),
        #                 'message': (('No HP hanya boleh angka ! ')),
        #             }
        #             value = {
        #                      'no_hp':False
        #                      }
        # if notelp :
        #     if len(notelp) > 11 :
        #         warning = {
        #             'title': ('Perhatian !'),
        #             'message': (('No Telepon tidak boleh lebih dari 11 digit ! ')),
        #         }
        #         value = {
        #                  'no_telp':False
        #                  }
        #     else :            
        #         cek = notelp.isdigit()
        #         if not cek :
        #             warning = {
        #                 'title': ('Perhatian !'),
        #                 'message': (('No Telepon hanya boleh angka ! ')),
        #             }
        #             value = {
        #                      'no_telp':False
        #                      }       
        return {'warning':warning,'value':value} 
    
    def onchange_punctuation(self,cr,uid,ids,no_ktp,context=None):    
        value = {}
        warning = {}
        if no_ktp:
            if no_ktp == '0':
                value = {
                             'no_ktp':no_ktp
                             }
            elif no_ktp != '0' and len(no_ktp) == 16:
            # if no_ktp :
                ktp = self.search(cr,uid,[('no_ktp','=',no_ktp)])
                if ktp :
                        warning = {
                            'title': ('Perhatian !'),
                            'message': (('No KTP %s sudah pernah dibuat ! ')%(no_ktp)),
                        }    
                        value = {
                                 'no_ktp':False
                                 }
                if not warning :            
                    no_ktp = "".join(l for l in no_ktp if l not in string.punctuation)  
                    value = {
                             'no_ktp':no_ktp
                             }                                 
            elif no_ktp != '0' and len(no_ktp) != '16':
                warning = {
                            'title': ('Perhatian !'),
                            'message': (('No KTP harus 16 digit ! ')),
                        }    
                value = {
                         'no_ktp':False
                         }
        return {'value':value,'warning':warning}
    
class dym_driver_line(osv.osv):
    _name = "dym.driver.line"
    _rec_name = 'driver'
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Forwarder'),
        'driver': fields.char('Driver'),
        }
    
    def driver_change(self, cr, uid, ids, driver, context=None):
        value = {}
        if driver :
            driver = driver.upper()
            value['driver'] = driver
        return {'value':value}
    
class dym_plat_number_line(osv.osv):
    _name = "dym.plat.number.line"
    _rec_name = 'plat_number'
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Forwarder'),
        'plat_number': fields.char('Plat Number'),
        }
    
    def plat_number_change(self, cr, uid, ids, plat_number, context=None):
        value = {}
        warning = {}
        if plat_number :
            plat_number = plat_number.upper()
            plat_number = plat_number.replace(' ','')
            value['plat_number'] = plat_number
            
            for x in plat_number :
                if x in string.punctuation :
                    warning = {'title': 'Perhatian', 'message': 'Plat Number hanya boleh huruf dan angka !'}
                    value['plat_number'] = False
        return {'value':value, 'warning':warning}
    
