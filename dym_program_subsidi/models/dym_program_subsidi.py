import time
import pytz
from openerp import SUPERUSER_ID
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from openerp.osv import fields, osv
from openerp import netsvc
from openerp import pooler
from openerp import tools
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.osv.orm import browse_record, browse_null
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

class dym_program_subsidi(osv.osv):
    _name = 'dym.program.subsidi'
    _description = "Program Subsidi"
    _inherit = ['mail.thread']
    
    def _get_max(self, cr, uid, ids, field_name, arg, context=None):
        res ={}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] ={
                            'nilai_promo': 0.0
                            }
            nilai_max =0.0
            for line in order.program_subsidi_line :
                if nilai_max < line.total_diskon :
                    nilai_max = line.total_diskon
                res[order.id]['nilai_promo']=nilai_max
        return res
    
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('dym.program.subsidi.line').browse(cr, uid, ids, context=context):
            result[line.program_subsidi_id.id] = True
        return result.keys()

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    def _get_tenor(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for obj in self.browse(cr, uid, ids, context=context):
            res[obj.id]= {
                'tenor': 0,
                'tenor_start': 0,
                'tenor_end': 0,
            }
            for line in obj.program_subsidi_line:
                if line.tenor_start != 0 or line.tenor_start != 0 or line.tenor_end != 0:
                    res[obj.id]['tenor'] = line.tenor_start
                    res[obj.id]['tenor_start'] = line.tenor_start
                    res[obj.id]['tenor_end'] = line.tenor_end
        return res

    _columns = { 
        'branch_id':fields.many2one('dym.branch','Branch', required=True),
        'division':fields.selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division', change_default=True, select=True,required=True),                     
        'area_id':fields.many2one('dym.area',string='Area',required=True),
        'name':fields.char("Name",required=True),
        'date_start':fields.date("Date Start",required=True),
        'date_end':fields.date("Date End",required=True),
        'keterangan':fields.text("Keterangan"),                
        'nilai_promo':fields.function(_get_max, string='Nilai Promo', store=True, multi='sums', help="Subtotal Diskon."),
        'instansi_id': fields.many2many('res.partner', 'program_subsidi_partner_rel', 'program_subsidi_id', 'partner_id', 'Instansi', domain=[('finance_company','=',True)]),
        'tipe_subsidi':fields.selection([('fix','Fix'),('non','Non Fix')], "Tipe Subsidi", change_default=True, select=True,required=True),                     
        'state': fields.selection([('draft', 'Draft'),('waiting_for_approval','Waiting For Approval'), ('approved', 'Approved'),('rejected','Rejected'),('editable','Editable'),('on_revision','On Revision')], 'State', readonly=True),
        'program_subsidi_line':fields.one2many('dym.program.subsidi.line','program_subsidi_id',"Program Subsidi",copy=True),
        'partner_ref':fields.char('Kode Program MD / Finco',required=True),
        'active':fields.boolean('Active'),
        'confirm_uid':fields.many2one('res.users',string="Approved by"),
        'confirm_date':fields.datetime('Approved on'),
        'is_exclusive':fields.boolean('Exclusive'),
        'is_program_depo':fields.boolean('Program Depo'),
        'is_member_only':fields.boolean('Member Only'),
        'tenor':fields.function(_get_tenor, string='Tenor', type='integer', 
            store={
                'dym.program.subsidi': (lambda self, cr, uid, ids, c={}: ids, ['program_subsidi_line'], 10),
                'dym.program.subsidi.line': (_get_order, ['diskon_ahm', 'diskon_md', 'diskon_dealer', 'diskon_finco', 'diskon_others'], 10),
            },
             multi='sums', help="Tenor"),
        'tenor_start':fields.function(_get_tenor, string='Tenor Start', type='integer', 
            store={
                'dym.program.subsidi': (lambda self, cr, uid, ids, c={}: ids, ['program_subsidi_line'], 10),
                'dym.program.subsidi.line': (_get_order, ['diskon_ahm', 'diskon_md', 'diskon_dealer', 'diskon_finco', 'diskon_others'], 10),
            },
             multi='sums', help="Tenor"),
        'tenor_end':fields.function(_get_tenor, string='Tenor End', type='integer', 
            store={
                'dym.program.subsidi': (lambda self, cr, uid, ids, c={}: ids, ['program_subsidi_line'], 10),
                'dym.program.subsidi.line': (_get_order, ['diskon_ahm', 'diskon_md', 'diskon_dealer', 'diskon_finco', 'diskon_others'], 10),
            },
             multi='sums', help="Tenor"),
        'include_invoice': fields.boolean('Discount include di invoice', help="jika dicentang maka diskon subsidi akan dimasukkan ke invoice dan di jurnal sebagai diskon quotation"),
    }
    _defaults ={
        'state': 'draft',
        'branch_id': _get_default_branch,
        'active': True,
        'include_invoice': True,
    }

    def _check_dates(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        obj_task = self.browse(cr, uid, ids[0], context=context)
        start = obj_task.date_start or False
        end = obj_task.date_end or False
        if start and end :
            if start > end:
                return False
        return True
    
    _constraints = [
      (_check_dates, 'Perhatian !, Date end harus lebih besar dari',['date_start']),
    ]
            
    def button_dummy(self, cr, uid, ids, context=None):
        return True
    
    def create(self,cr,uid,vals,context=None):
        if not vals['program_subsidi_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail Program Subsidi. Data tidak bisa di save."))
        return super(dym_program_subsidi, self).create(cr, uid, vals, context=context)

         
    def unlink(self, cr, uid, ids, context=None):
         for item in self.browse(cr, uid, ids, context=context):
             if item.state != 'draft':
                 raise osv.except_osv(('Perhatian !'), ("Program Subsidi tidak bisa didelete !"))
         return super(dym_program_subsidi, self).unlink(cr, uid, ids, context=context)
    
    def copy(self, cr, uid, id, default=None, context=None):
        subsidi_line = []
        if default is None:
            default = {}
            
        for program_subsidi in self.browse(cr,uid,id):
            #end_date = parse(program_subsidi.date_end) + timedelta(days=2)
            #start_date = datetime.strptime(program_subsidi.date_start,'%Y-%m-%d') + timedelta(days=1)
            #end_date = datetime.strptime(program_subsidi.date_start,'%Y-%m-%d') + timedelta(days=2)
            default.update({
                'branch_id': program_subsidi.branch_id.id,
                'division': program_subsidi.division,
                'area_id': program_subsidi.area_id.id,
                'name': program_subsidi.name,
                'date_start': program_subsidi.date_start,
                'date_end': program_subsidi.date_end,
                'keterangan': program_subsidi.keterangan,
                'tipe_subsidi': program_subsidi.tipe_subsidi,                     
                'state': 'draft',
                'partner_ref': program_subsidi.partner_ref,
                'active': True,
                'approval_state': 'b',
                'is_exclusive': program_subsidi.is_exclusive,
                'is_program_depo': program_subsidi.is_program_depo,
                'is_member_only': program_subsidi.is_member_only,
                'include_invoice': program_subsidi.include_invoice,
		'nilai_promo': program_subsidi.nilai_promo,
            })
            for lines in program_subsidi.program_subsidi_line:
                subsidi_line.append([0,False,{
                    'product_template_id':lines.product_template_id.id,
                    'tipe_dp': lines.tipe_dp,
                    'amount_dp': lines.amount_dp,
                    'diskon_ahm':lines.diskon_ahm,
                    'diskon_md':lines.diskon_md,
                    'diskon_dealer':lines.diskon_dealer,
                    'diskon_finco':lines.diskon_finco,
                    'diskon_others':lines.diskon_others,
                    'tipe_diskon':lines.tipe_diskon,
                    'diskon_persen':lines.diskon_persen,                                       
                }])
            default.update({'program_subsidi_line':subsidi_line})
                
        return super(dym_program_subsidi, self).copy(cr, uid, id, default=default, context=context)
        
    def write(self,cr,uid,ids,vals,context=None):
        val = self.browse(cr,uid,ids)
        date_start = val.date_start
        date_end = val.date_end
        new_start = vals.get('date_start',date_start)
        new_end = vals.get('date_end',date_end)
        user = self.pool.get('res.users').browse(cr,uid,uid)
        if date_start != new_start or date_end != new_end :
            if val.state == 'on_revision' and not vals.get('state') and not vals.get('approval_state'):
                self.message_post(cr, uid, val.id, body=_("Previous Date : %s - %s <br/> Effective Date : %s - %s <br/> Revised by %s ")%(date_start,date_end,new_start,new_end,user.name), context=context) 
            elif val.state == 'editable' and not vals.get('state') and not vals.get('approval_state'):
                self.message_post(cr, uid, val.id, body=_("Previous Date : %s - %s <br/> Effective Date : %s - %s <br/> Edited by %s ")%(date_start,date_end,new_start,new_end,user.name), context=context) 
        return super(dym_program_subsidi, self).write(cr, uid, ids, vals, context=context)       
    
class dym_program_subsidi_line(osv.osv):
    _name = 'dym.program.subsidi.line'
    
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            if line.tipe_diskon == 'percentage':
                price = (line.diskon_persen or 0.0)
            else:
                price = (line.diskon_ahm or 0.0) + (line.diskon_md or 0.0)+ (line.diskon_dealer or 0.0)+(line.diskon_finco or 0.0) + (line.diskon_others or 0.0)
            res[line.id]=price
        return res
    
    _columns = { 
        'program_subsidi_id':fields.many2one('dym.program.subsidi',"Program Subsidi" ,ondelete='cascade'),
        'product_template_id': fields.many2one('product.template', 'Product'),
        'tipe_dp': fields.selection([('min','Min'),('max','Max')], 'Tipe JP', change_default=True, select=True),
        'amount_dp':fields.float("JP Min/Max"),

        'diskon_ahm':fields.float("Diskon AHM"),
        'diskon_md':fields.float("Diskon MD"),
        'diskon_dealer':fields.float("Diskon Dealer"),
        'diskon_finco':fields.float("Diskon Finco"),
        'diskon_others':fields.float("Diskon Others"),

        # 'diskon_ahm_12':fields.float("Diskon AHM"),
        # 'diskon_md_12':fields.float("Diskon MD"),
        # 'diskon_dealer_12':fields.float("Diskon Dealer"),
        # 'diskon_finco_12':fields.float("Diskon Finco"),
        # 'diskon_others_12':fields.float("Diskon Others"),

        # 'diskon_ahm_16':fields.float("Diskon AHM"),
        # 'diskon_md_16':fields.float("Diskon MD"),
        # 'diskon_dealer_16':fields.float("Diskon Dealer"),
        # 'diskon_finco_16':fields.float("Diskon Finco"),
        # 'diskon_others_16':fields.float("Diskon Others"),

        # 'diskon_ahm_24':fields.float("Diskon AHM"),
        # 'diskon_md_24':fields.float("Diskon MD"),
        # 'diskon_dealer_24':fields.float("Diskon Dealer"),
        # 'diskon_finco_24':fields.float("Diskon Finco"),
        # 'diskon_others_24':fields.float("Diskon Others"),

        # 'diskon_ahm_28':fields.float("Diskon AHM"),
        # 'diskon_md_28':fields.float("Diskon MD"),
        # 'diskon_dealer_28':fields.float("Diskon Dealer"),
        # 'diskon_finco_28':fields.float("Diskon Finco"),
        # 'diskon_others_28':fields.float("Diskon Others"),


        'total_diskon':fields.function(_amount_line, string='Total Diskon',store=True),
        'tipe_diskon':fields.selection([('amount','Amount'),('percentage','Percentage')], 'Tipe Diskon', change_default=True, select=True, required=True),                     
        'diskon_persen':fields.float("Diskon Persen"),
        'tenor':fields.integer('Tenor'),
        'tenor_start':fields.integer('Tenor Start'),
        'tenor_end':fields.integer('Tenor End'),
        'tenor_range':fields.char('Tenor Range'),
    }

    _defaults = {
        'amount_dp': 0.0,
        'diskon_ahm': 0.0,
        'diskon_md': 0.0,
        'diskon_dealer': 0.0,
        'diskon_finco': 0.0,
        'diskon_others': 0.0,
        'tipe_diskon': 'amount',
        'diskon_persen': 0.0,
    }

    _sql_constraints = [
        ('unique_product_ps', 'unique(program_subsidi_id,product_template_id)', 'Tidak boleh ada produk yg sama didalam satu master program subsidi !'),
    ]

    def create(self,cr,uid,vals,context=None):
        tenor_start = False
        tenor_end = False
        try:
            if vals['tenor_range']:
                tenor_range = vals['tenor_range']
                if '-' in tenor_range:
                    tenor_range = tenor_range.split('-')
                    tenor_start = int(tenor_range[0])
                    tenor_end = int(tenor_range[1])
                else:
                    tenor_start = int(tenor_range)
                    tenor_end = int(tenor_range)
                vals['tenor_start']= tenor_start
                vals['tenor_end']= tenor_end
        except:
            pass
        return super(dym_program_subsidi_line, self).create(cr, uid, vals, context=context)
    
    def _get_domain_program_subsidi(self,cr,uid,ids,division,context=None):
        domain = {} 
        if division:
            categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,division)
            if division == 'Sparepart':
                categ_ids += self.pool.get('product.category').get_child_ids(cr,uid,ids,'Service')
            domain['product_template_id'] = [('type','!=','view'),('categ_id','in',categ_ids)]
        else:
            raise osv.except_osv(('Perhatian !'), ("Mohon isi division terlebih dahulu."))
        return {'domain':domain}        

    def onchange_tenor_range(self, cr, uid, ids, tenor_range, context=None):
        tenor_start = False
        tenor_end = False
        valid = True

        if not tenor_range:
            return {}
        if '-' in tenor_range:
            tenor_range = tenor_range.split('-')
            try:
                tenor_start = int(tenor_range[0])
            except:
                valid = False
            try:
                tenor_end = int(tenor_range[1])
            except:
                valid = False
            if tenor_start>=tenor_end:
                valid = False                    
        else:
            try:
                tenor_start = int(tenor_range)
                tenor_end = int(tenor_range)
            except:
                valid = False
        if not valid:
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _('Data tenor salah, seharusnya angka saja misal: 11 atau range misal: 11-16')
                },
                'value': {
                    'tenor': False,
                    'tenor_range': False,
                }
            }
        ts = context.get('tenor_start',False)
        te = context.get('tenor_end',False)
        if ts and te and (ts != tenor_start or te != tenor_end):
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _('Tenor range harus sama dengan tenor range lainnya pada form ini. Jika memang beda, silahkan buat program yang baru.')
                },
                'value': {
                    'tenor': ts,
                    'tenor_start': ts,
                    'tenor_end': te,
                    'tenor_range': '%s-%s' % (ts,te),
                }
            }
        return {
            'value': {
                'tenor': tenor_start,
                'tenor_start': tenor_start,
                'tenor_end': tenor_end,
            }
        }


    def onchange_tipe_diskon(self,cr,uid,ids,tipe_diskon):
        value = {}
        if tipe_diskon == 'percentage':
            value['diskon_ahm'] = 0
            value['diskon_md'] = 0
            value['diskon_dealer'] = 0
            value['diskon_finco'] = 0
            value['diskon_others'] = 0
            if ids:
                self.write(cr, uid, ids, value)
        elif tipe_diskon == 'amount':
            value['diskon_persen'] = 0
            if ids:
                self.write(cr, uid, ids, value)
        return {'value':value}
