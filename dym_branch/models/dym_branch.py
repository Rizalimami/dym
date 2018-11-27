from openerp import api, fields, models, SUPERUSER_ID
from openerp.osv import osv
from datetime import datetime, date, timedelta
import time
import pytz
from pytz import timezone
from openerp.tools.translate import _
import re
import logging

_logger = logging.getLogger(__name__)

BRANCH_TYPES = [
    ('HO','Head Office'),
    ('DL','Dealership')
]

class dym_branch(models.Model):
    _name = 'dym.branch'
    _description = 'Branches'
    
    @api.multi
    def get_customer_invoice(self,dso):
        obj_inv = self.env['account.invoice']
        if dso.finco_id and dso.is_credit == True:
            invoice_ids = obj_inv.search([('origin','ilike',dso.name),('tipe','=','finco'),('partner_id','in',[dso.partner_id.id,dso.finco_id.id])])
        else:            
            invoice_ids = obj_inv.search([('origin','ilike',dso.name),('tipe','=','customer'),('partner_id','=',dso.partner_id.id)])
        for inv in invoice_ids:
            return inv.number
        return '-'

    @api.multi
    def get_attribute_name(self,product):
        attr_name = ''
        if product.attribute_value_ids:
            for attr in product.attribute_value_ids:
                attr_name += attr.name + ', '
            attr_name = attr_name[:-2]
        return attr_name

    @api.multi
    def get_waktu_local(self, date_format=False):
        month_array = {
            1:'Januari',
            2:'Februari',
            3:'Maret',
            4:'April',
            5:'Mei',
            6:'Juni',
            7:'Juli',
            8:'Agustus',
            9:'September',
            10:'Oktober',
            11:'November',
            12:'Desember',
        }
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.env['res.users'].browse(self._uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        if date_format:
            month_number = "%02d" % (start.month,)
            month_string = month_array[start.month]
            start_date = start.strftime("%d %m %Y")
            start_date = re.sub("\s[^]]*\s", lambda x:x.group(0).replace(month_number,month_string), start_date)
        else:
            start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date

    @api.multi
    def formatted_date(self, date):

        if not date:
            return "NO INVOICE DATE"

        month_array = {
            1:'Januari',
            2:'Februari',
            3:'Maret',
            4:'April',
            5:'Mei',
            6:'Juni',
            7:'Juli',
            8:'Agustus',
            9:'September',
            10:'Oktober',
            11:'November',
            12:'Desember',
        }
        if date != 'Multiple':
            date = datetime.strptime(date, '%Y-%m-%d')
            month_number = "%02d" % (date.month,)
            month_string = month_array[date.month]
            date = date.strftime("%d %m %Y")
            date = re.sub("\s[^]]*\s", lambda x:x.group(0).replace(month_number,month_string), date)
        return date


    @api.multi
    def get_cetakan_no(self, model, report_name, obj):
        obj_model = self.env['ir.model'].search([('model','=',model)])[0]
        obj_model_id = obj_model.id
        obj_ir = self.env['ir.actions.report.xml'].search([('report_name','=',report_name)])
        obj_ir_id = obj_ir.id
        obj_jumlah_cetak=self.env['dym.jumlah.cetak'].search([('report_id','=',obj_ir_id),('model_id','=',obj_model_id),('transaction_id','=',obj.ids[0])])
        if not obj_jumlah_cetak :
            jumlah_cetak_id = {
            'model_id':obj_model_id,
            'transaction_id': obj.ids[0],
            'jumlah_cetak': 1,
            'report_id':obj_ir_id                            
            }
            jumlah_cetak=1
            move=self.env['dym.jumlah.cetak'].create(jumlah_cetak_id)
        else :
            jumlah_cetak=obj_jumlah_cetak.jumlah_cetak+1
            obj_jumlah_cetak.write({'jumlah_cetak': jumlah_cetak})
        return jumlah_cetak

    @api.onchange('state_id')
    def _onchange_province(self):
        self.city_id = False
        return {'domain' : {'city_id':[('state_id','=',self.state_id.id)],},}

    @api.onchange('city_id')    
    def _onchange_city(self):
        self.kecamatan_id = False
        return {'domain' : {'kecamatan_id':[('city_id','=',self.city_id.id)],},}

    @api.onchange('kecamatan_id')            
    def _onchange_kecamatan(self):
        self.zip_code_id = False
        self.kecamatan = self.kecamatan_id.name
        return {'domain' : {'zip_code_id':[('kecamatan_id','=',self.kecamatan_id.id)],},}

    @api.onchange('zip_code_id')    
    def _onchange_zip(self):
        self.kelurahan = self.zip_code_id.name
    
    @api.multi
    def npwp_onchange(self,npwp):
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
            value['npwp'] = self.npwp
            result['warning'] = warning
            result['value'] = value
            return result

    code = fields.Char(string='Code',required=True)
    name = fields.Char(string='Name',required=True)
    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env['res.company']._company_default_get('dym.branch'))
    doc_code = fields.Char(related='code',readonly=True)
    branch_type = fields.Selection(BRANCH_TYPES, string='Branch Type', required=True)
    ahm_code = fields.Char(string='AHM Code Showroom')
    default_supplier_id = fields.Many2one('res.partner',string='Principle Showroom',domain=[('principle','=',True)])
    street = fields.Char(string='Address')
    street2 = fields.Char()
    rt = fields.Char(string='RT',size=3)
    rw = fields.Char(string='RW',size=3)
    zip_code_id = fields.Many2one('dym.kelurahan',string='ZIP Code')
    kelurahan = fields.Char(string='Kelurahan',size=100)
    kecamatan_id = fields.Many2one('dym.kecamatan',string='Kecamatan')
    kecamatan = fields.Char(string='Kecamatan',size=100)
    city_id = fields.Many2one('dym.city',string='City')
    state_id = fields.Many2one('res.country.state',string='Province')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    fax = fields.Char(string='Fax')
    email = fields.Char(string='e-mail')
    npwp = fields.Char(string='No NPWP')
    no_pkp = fields.Char(string='No PKP', related="npwp")
    tgl_kukuh = fields.Date(string='Tgl Kukuh')

    npwp_street = fields.Char(string='Address')
    npwp_street2 = fields.Char()
    npwp_rt = fields.Char(string='RT',size=3)
    npwp_rw = fields.Char(string='RW',size=3)
    npwp_zip_code_id = fields.Many2one('dym.kelurahan',string='ZIP Code')
    npwp_kelurahan = fields.Char(string='Kelurahan',size=100)
    npwp_kecamatan_id = fields.Many2one('dym.kecamatan',string='Kecamatan')
    npwp_kecamatan = fields.Char(string='Kecamatan',size=100)
    npwp_city_id = fields.Many2one('dym.city',string='City')
    npwp_state_id = fields.Many2one('res.country.state',string='Province')


    pimpinan_id = fields.Many2one('hr.employee',string='Pimpinan')
    manager_id = fields.Many2one('hr.employee',string='AM')
    general_manager_id = fields.Many2one('hr.employee',string='GM')
    warehouse_id = fields.Many2one('stock.warehouse',string='Warehouse')
    property_account_payable_id = fields.Many2one('account.account',string='Payable Account Showroom')
    property_account_receivable_id = fields.Many2one('account.account',string='Receivable Account Showroom')
    property_account_payable_analytic_id = fields.Many2one('account.analytic.account',string='Payable Analytic Account')
    property_account_receivable_analytic_id = fields.Many2one('account.analytic.account',string='Receivable Analytic Account')

    pricelist_unit_sales_id = fields.Many2one('product.pricelist',string='Price List Jual Unit',domain=[('type','=','sale')])
    pricelist_unit_purchase_id = fields.Many2one('product.pricelist',string='Price List Beli Unit',domain=[('type','=','purchase')])
    pricelist_bbn_hitam_id = fields.Many2one('product.pricelist',string='Price List Jual BBN Plat Hitam',domain=[('type','=','sale_bbn_hitam')])
    pricelist_bbn_merah_id = fields.Many2one('product.pricelist',string='Price List Jual BBN Plat Merah',domain=[('type','=','sale_bbn_merah')])

    pricelist_part_sales_id = fields.Many2one('product.pricelist',string='Price List Jual Spare Part',domain=[('type','=','sale')])
    pricelist_part_purchase_id = fields.Many2one('product.pricelist',string='Price List Beli Spare Part',domain=[('type','=','purchase')])

    default_customer_location = fields.Many2one('stock.location',string='Default Customer Location')
    area_ids = fields.Many2many('dym.area','dym_area_cabang_rel','branch_id','area_id','Areas')
    user_ids = fields.Many2many('res.users', 'dym_branch_users_rel', 'branch_id', 'user_id', 'Users')
    blind_bonus_beli = fields.Float(string='Blind Bonus Beli')
    blind_bonus_jual = fields.Float(string='Blind Bonus Jual')
    profit_centre = fields.Char(string='Profit Centre',help='please contact your Accounting Manager to get Profit Center.')
    inter_company_account_id = fields.Many2one('account.account',string='Inter Company Account',domain="[('type','!=','view'),'|',('code','ilike',str('1685'+'%')),('code','ilike',str('1696'+'%'))]") 
    pajak_progressive = fields.Boolean('Pajak Progressive',default=True)
    is_mandatory_spk = fields.Boolean('Is Mandatory SPK')
    partner_id = fields.Many2one('res.partner',string='Partner', copy=False)
    branch_status = fields.Selection([('HO','HO'),('H1','H1'),('H23','H23'),('H123','H123')],string='Branch Status')
    default_supplier_workshop_id = fields.Many2one('res.partner',string='Principle Workshop',domain=[('principle','=',True)])
    property_account_payable_workshop_id = fields.Many2one('account.account',string='Payable Account Workshop')
    property_account_receivable_workshop_id = fields.Many2one('account.account',string='Receivable Account Workshop')
    ahm_code_workshop = fields.Char(string='AHM Code Workshop')

    # afiliasi_ids = fields.Many2many('res.partner', 'dym_branch_partner_afiliasi_rel', 'branch_id', 'afiliasi_id', 'Afiliasi')
    # afiliasi_ids = fields.Many2many('res.partner', 'dym_branch_partner_afiliasi_rel', 'branch_id', 'afiliasi_id', 'Afiliasi')
    
    _sql_constraints = [
       ('code_unique', 'unique(code)', '`Code` tidak boleh ada yang sama.'),  
    ]

    def write(self, cr, uid, ids, val, context=None):
        if context is None:
            context = {}
        res = super(dym_branch, self).write(cr, uid, ids, val, context=context)
        if 'name' in val or 'code' in val:
            context=dict(context)
            for branch in self.browse(cr, uid, ids):
                search_partner = self.pool.get('res.partner').search(cr, uid, [('branch_id','=',branch.id)], context=context)
                if not search_partner:
                    context.update({
                        'form_name': 'Branch'
                    })
                    partner_vals = {
                        'name': branch.name,
                        'default_code': branch.code,
                        'street': branch.street,
                        'street2': branch.street2,
                        'rt': branch.rt,
                        'rw': branch.rw,
                        'state_id': branch.state_id.id,
                        'city_id': branch.city_id.id,
                        'kecamatan_id': branch.kecamatan_id.id,
                        'kecamatan': branch.kecamatan,
                        'zip_code_id': branch.zip_code_id.id,
                        'kelurahan': branch.kelurahan,
                        'phone': branch.phone,
                        'mobile': branch.mobile,
                        'fax': branch.fax,
                        'email': branch.email,
                        }
                    partner = self.pool.get('res.partner').create(cr, uid, partner_vals, context=context)
                    self.write(cr, uid, branch.id, {'partner_id' : partner})
                    self.pool.get('res.partner').write(cr, uid, partner, {'branch_id': branch.id,'customer': False})
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        default = dict(context or {})
        branch = self.browse(cr, uid, id, context=context)
        default.update(
            code=_("%s (copy)") % (branch['code'] or ''),
            name=_("%s (copy)") % (branch['name'] or ''))
        return super(dym_branch, self).copy(cr, uid, id, default, context=context)
    
    def create(self,cr,uid,val,context=None):
        if context is None:
            context = {}  
        dym_branch_id = super(dym_branch, self).create(cr, uid, val, context=context)
        if '__copy_data_seen' not in context:
            context.update({
                'form_name': 'Branch'
            })
            obj_res_partner = self.pool.get('res.partner')
            res_partner_id = {
                'name': val['name'],
                'default_code': val['code'],
                'street': val['street']  ,
                'street2': val['street2'],
                'rt': val['rt'],
                'rw': val['rw'],
                'state_id': val['state_id'],
                'city_id': val['city_id'],  
                'kecamatan_id': val['kecamatan_id'],
                'kecamatan': val['kecamatan'],
                'zip_code_id': val['zip_code_id'],
                'kelurahan': val['zip_code_id'],
                'phone': val['phone'],
                'mobile': val['mobile'],
                'fax': val['fax'],
                'email': val['email'] ,                               
                }
            res_partner=obj_res_partner.create(cr,uid,res_partner_id,context=context)
            self.write(cr, uid, dym_branch_id, {'partner_id' : res_partner})
            update_partner = obj_res_partner.write(cr,uid,res_partner,{'branch_id': dym_branch_id,'customer': False})
        return dym_branch_id
        
        
    def change_profit_centre(self,cr,uid,ids,profit_centre,context=None):   
        value = {}
        warning = {}
        if profit_centre :
            if len(profit_centre) != 5 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Profit Branch harus 5 digit ! ')),
                }
                value = {
                         'profit_centre':False
                         }
            else :
                cek = profit_centre.isdigit()
                if not cek :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('Profit Centre hanya boleh numeric ! ')),
                    }
                    value = {
                             'profit_centre':False
                             }      
        return {'warning':warning,'value':value} 
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.code:
                name = "[%s] %s" % (record.code, name)
            res.append((record.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            # Be sure name_search is symetric to name_get
            args = ['|',('name', operator, name),('code', operator, name)] + args
        categories = self.search(args, limit=limit)
        return categories.name_get()
    
    @api.multi
    def get_ids_expedition(self):
        expedition_ids = []
        for expedition in self.harga_ekspedisi_ids :
            expedition_ids.append(expedition.ekspedisi_id.id)
        return expedition_ids
    
    @api.multi
    def get_freight_cost(self, expedition_id, product_id):
        freight_cost = 0
        date = self.get_default_date().strftime('%Y-%m-%d')
        if expedition_id not in self.get_ids_expedition() :
            raise osv.except_osv(('Perhatian !'), ("Ekspedisi tidak ditemukan di Master Branch '%s' !" %self.name))
        for ekspedition in self.harga_ekspedisi_ids :
            if ekspedition.ekspedisi_id.id == expedition_id :
                effective_pricelist = []
                for line in ekspedition.harga_ekspedisi_id.pricelist_expedition_line_ids :
                    if line.start_date <= date and line.end_date >= date :
                        effective_pricelist.append(line.id)
                        for detail in line.pricelist_expedition_line_detail_ids :
                            if detail.product_template_id.id == self.env['product.product'].search([('id','=',product_id)]).product_tmpl_id.id :
                                freight_cost = detail.cost
                                break
                if not effective_pricelist :
                    raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan Pricelist aktif utk ekspedisi '%s' di '%s' !" %(ekspedition.ekspedisi_id.name,self.name)))
        return freight_cost
    
    @api.multi
    def get_default_date(self):
        return pytz.UTC.localize(datetime.now()).astimezone(timezone('Asia/Jakarta'))    
    
    @api.model
    def get_default_date_model(self):
        return pytz.UTC.localize(datetime.now()).astimezone(timezone('Asia/Jakarta'))      

