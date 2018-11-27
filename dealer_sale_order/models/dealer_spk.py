# -*- coding: utf-8 -*-

import pdb
import itertools
import openerp.addons.decimal_precision as dp

from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.addons.dym_base import DIVISION_SELECTION
from openerp.osv import osv

class branch_birojasa_partner(models.Model):
    _inherit = 'res.partner'

    @api.one
    @api.depends('harga_birojasa_ids')
    def _get_branch_ids(self):
        branch_birojasa_ids = []
        for line in self.harga_birojasa_ids:
            if line.branch_id.id not in branch_birojasa_ids:
                branch_birojasa_ids.append(line.branch_id.id)
        if branch_birojasa_ids:
            self.branch_birojasa_ids = branch_birojasa_ids
   
    harga_birojasa_ids = fields.One2many('dym.harga.birojasa','birojasa_id',string="Service Bureau")
    branch_birojasa_ids = fields.Many2many('dym.branch', string='Branch', compute='_get_branch_ids', store=True)

class dealer_spk(models.Model):
    _name = "dealer.spk"
    _description = "Memo Dealer"
    _order = "name desc"

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    @api.one
    def _check_repeat(self):
        self.repeat_order = 'Tidak'
        if self.search([('state','=','done'),('partner_id','=',self.partner_id.id),('id','<',self.id),('date_order','<=',self.date_order)]):
            self.repeat_order = 'Ya'
    @api.one
    def _get_user_id(self):
        emp_id = self.employee_id.user_id.id
        emp_src = self.env['res.users'].search([('employee_id','=',self.employee_id.id)], limit=1)
        if emp_src:
            emp_id = emp_src.id
        self.employee_id = emp_id

    @api.one
    @api.depends('partner_id')
    def _get_payable_receivable(self):
        self.payable_receivable = self.partner_id.debit

    @api.model
    def _getCompanyBranch(self):
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        branch_ids = [b.id for b in self.env.user.branch_ids if b.company_id.id==company_id]
        return [('id','in',branch_ids)]

    branch_id = fields.Many2one('dym.branch', required=True, string='Branch', default=lambda self: self.env.user.branch_id, domain=_getCompanyBranch)
    origin = fields.Char(string='Source Document')
    payable_receivable = fields.Float(string='Payable Balance', compute=_get_payable_receivable, store=True)
    repeat_order = fields.Char(string='Repeat Memo', compute=_check_repeat)
    name = fields.Char(string='Memo')
    is_pic = fields.Boolean('Is PIC', help="Sale to Intercompany")
    is_asset = fields.Boolean('Is Asset', help="Sale to the company for asset")    
    division = fields.Selection([('Unit','Showroom')],required=True,string='Division',default="Unit")
    date_order = fields.Date(string='Date Memo',default=fields.Date.context_today,readonly=True)
    payment_term = fields.Many2one('account.payment.term',string='Payment Term')
    pricelist_id = fields.Many2one('product.pricelist',string='Pricelist')
    partner_id = fields.Many2one('res.partner',string='Customer',domain=[('customer','=',True)],required=True)
    partner_cabang = fields.Many2one('dym.cabang.partner',string='Customer Branch')
    finco_id = fields.Many2one('res.partner',string='Finco',domain=[('finance_company','=',True)])
    finco_cabang = fields.Many2one('dym.cabang.partner',string='Finco Branch')
    user_id = fields.Many2one('res.users',string='Responsible', compute=_get_user_id)
    employee_id = fields.Many2one('hr.employee',string='Sales Person')
    section_id = fields.Many2one('crm.case.section',string='Sales Team')
    sales_source = fields.Many2one('sales.source',string='Sales Source',required=True,)
    dealer_spk_line = fields.One2many('dealer.spk.line','dealer_spk_line_id',string='Memo Detail',)
    state = fields.Selection([
        ('draft', 'Draft'),                                
        ('progress', 'Memo'),
        ('so', 'Sales Memo'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ],string='Status',default='draft')
    cddb_id = fields.Many2many('dym.cddb', 'so_cddb_rel', 'so_id', 'cddb_id', 'CDDB', readonly=True)
    alamat_kirim = fields.Text(string='Alamat Kirim')
    distribusi_spk_id = fields.Many2one('dealer.distribusi.spk.line',string='Distribution No.')
    register_spk_id = fields.Many2one("dealer.register.spk.line",string='Register No')
    dealer_sale_order_id = fields.Many2one('dealer.sale.order')
    confirm_date = fields.Datetime('Confirmed on')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    so_create_date = fields.Date()
    user_create_so_id = fields.Many2one('res.users')
    cancel_date = fields.Datetime('Cancelled on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    no_ktp = fields.Char(related="partner_id.no_ktp",string="No KTP")
    is_mandatory_spk = fields.Boolean(related="branch_id.is_mandatory_spk",string="Mandatory Memo")
    reason_cancel = fields.Text('Reason Cancel')
    is_credit = fields.Boolean(string='Credit', default=False)
    mt_khusus = fields.Boolean(related="employee_id.mt_khusus",string="Is MT Khusus")

    @api.onchange('branch_id','pricelist_id')
    def onchange_branch_id(self):
        if not self.branch_id:
            return False
        if self.branch_id and not self.branch_id.company_id:
            return {
                'warning': {
                        'title': _('Error!'), 
                        'message': _("Branch %s is not related to any company yet. Please relate it first to continue or contact system administrator to do it." % self.branch_id.name)
                    }, 
                'value': {
                    'branch_id': []
                }
            }
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        sales_team = self.env['crm.case.section'].search([('company_id','=',company_id)])
        if not sales_team:
            return {
                'warning': {
                        'title': _('Error!'), 
                        'message': _("Branch %s does not have any sales team. Please contact system administrator." % self.branch_id.name)
                    }, 
                'value': {
                    'branch_id': []
                }
            }

        salesman = []
        for s in sales_team:
            if s.employee_id and s.employee_id.active:
                salesman.append(s.employee_id.id)
            for m in s.member_ids:
                if m.active:
                    salesman.append(m.id)

        if not salesman:
            return {
                'warning': {
                        'title': _('Error!'), 
                        'message': _("Sales Team in branch %s does not have any salesman. Please contact system administrator." % self.branch_id.name)
                    }, 
                'value': {
                    'branch_id': []
                }
            }
        self.pricelist_id = self.branch_id.pricelist_unit_sales_id
        domain = {
            'employee_id':[('id','in',salesman)],
        }
        return {'domain':domain}

    @api.onchange('is_credit')
    def onchange_credit(self):        
        if self.is_credit == False:
            self.finco_id = False

    @api.onchange('is_pic')
    def onchange_is_pic(self):
        domain = {}
        value = {}
        if self.partner_id and self.partner_id.partner_type in ['Afiliasi','Konsolidasi']:
            self.is_pic = True
            default_pic_source = self.env['sales.source'].search([('default_pic','=',True)], limit=1)
            if default_pic_source:
                self.sales_source = default_pic_source[0]
                value = {
                    'sales_source': default_pic_source[0],
                }
            domain = {
                'sales_source': [('default_pic','=',True)]
            }
        else:
            self.is_pic = False
        return {
            'domain': domain,
            'value': value,
        }

    @api.onchange('no_ktp')
    def onchange_ktp(self):
        if self.no_ktp :
            partner = self.env['res.partner'].search([('no_ktp','=',self.no_ktp)])
            if partner:
                if self.partner_id.id not in partner.ids:
                    self.partner_id = partner[0]

    @api.onchange('partner_id')
    def onchange_partner(self):
        domain = {}
        value = {}
        if self.partner_id :
            cddb = self.env['dym.cddb'].search([
                    ('customer_id','=',self.partner_id.id),
                    ], limit=1)
            if cddb :
                self.cddb_id = cddb
            else:
                self.cddb_id = False
            if self.partner_id.partner_type in ['Afiliasi','Konsolidasi']:
                self.is_pic = True
                default_pic_source = self.env['sales.source'].search([('default_pic','=',True)], limit=1)
                if default_pic_source:
                    self.sales_source = default_pic_source[0]
                    value = {
                        'sales_source': default_pic_source[0],
                    }
                domain = {
                    'sales_source': [('default_pic','=',True)]
                }
            else:
                self.is_pic = False
        else:
            self.cddb_id = False
        if self.branch_id:
            if self.branch_id.pimpinan_id:
                if self.is_pic:
                    self.employee_id=self.branch_id.pimpinan_id.id
                else:
                    self.employee_id=False
        return {
            'domain': domain,
            'value': value,
        }

    @api.onchange('distribusi_spk_id')
    def onchange_distribusi_spk_id(self):
        context = self._context or {}
        for rec in self:
            for rspk in self.env['dealer.register.spk.line'].search([('spk_id','=',rec.name)]):
                rspk.write({'state':'open','spk_id':[]})
            for dspk in self.env['dealer.distribusi.spk.line'].search([('spk_id','=',rec.name)]):
                dspk.write({'state':'open','spk_id':[]})
            rec.distribusi_spk_id.write({'state':'reserved'})
            rec.register_spk_id.write({'state':'reserved'})


    @api.onchange('register_spk_id')
    def onchange_register_spk_id(self):
        context = self._context or {}
        if self.register_spk_id:
            for x in self.env['dealer.distribusi.spk.line'].search([('dealer_register_spk_line_id','=',self.register_spk_id.id)]):
                self.distribusi_spk_id = x.id

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        dom={}        
        val={}
        self.section_id = False
        if self.employee_id :
            sales_team = self.env['crm.case.section'].search([('employee_id','=',self.employee_id.id)])
            if not sales_team:
                for team in self.env['crm.case.section'].search([]):
                    for member in team.member_ids:
                        if member.id == self.employee_id.id:
                            sales_team = team
                            break
                    if sales_team:
                        break
                team_leader = sales_team.employee_id.id
            else:
                team_leader = self.employee_id.id

            branch_id = False
            if sales_team:
                self.section_id = sales_team.id
                branch_data = sales_team.read(['branch_id'])
                branch_id = sales_team.branch_id
                team_id = sales_team.id
            register_spk_ids = []
            distribusi_spk_ids = []
            if branch_id:
                for dds in self.env['dealer.distribusi.spk'].search([('branch_id','=',branch_id.id),('sales_id','=',team_leader)]):
                    for x in dds.distribusi_spk_ids:
                        if x.state=='open' and x.state_distribusi == 'posted':
                            distribusi_spk_ids.append(x.id)
                for drsl in self.env['dealer.register.spk.line'].search([('branch_id','=',branch_id.id),('sales_id','=',team_leader),('state','=','open')]):
                    register_spk_ids.append(drsl.id)

            if not distribusi_spk_ids:
                self.employee_id = False
                self.distribusi_spk_id = False
                self.section_id = False
                return {'warning':{'title':'Attention!','message':'Distribusi Memo terlebih dahulu ke Team Leader Sales Teamnya atau Sales Personnya!'}}
            dom['distribusi_spk_id'] = [('id','in',distribusi_spk_ids)]
            dom['register_spk_id'] = [('id','in',register_spk_ids),('dealer_spk_line','=',False)]

        val['distribusi_spk_id']=False
        return {'domain':dom,'value':val}

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get_per_branch(values['branch_id'], 'DMO', division='Unit')
        values['date_order'] = datetime.today()
        dealer_spks = super(dealer_spk,self).create(values)
        if not dealer_spks:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan nomor register di dokumen!"))
        for rec in self:
            for rspk in self.env['dealer.register.spk.line'].search([('state','=','reserved'),('spk_id','=',None)]):
                rspk.write({'state':'open'})
            for dspk in self.env['dealer.distribusi.spk.line'].search([('state','=','reserved'),('spk_id','=',None)]):
                dspk.write({'state':'open'})
            for rspk in self.env['dealer.register.spk.line'].search([('spk_id','=',rec.name)]):
                rspk.write({'state':'open','spk_id':[]})
            for dspk in self.env['dealer.distribusi.spk.line'].search([('spk_id','=',rec.name)]):
                dspk.write({'state':'open','spk_id':[]})
            rec.distribusi_spk_id.write({'state':'spk','spk_id':dealer_spks})
            rec.register_spk_id.write({'state':'spk','spk_id':dealer_spks})
            if rec.partner_id.partner_type in ['Afiliasi','Konsolidasi']:
                values['is_pic'] = True
        return dealer_spks
    
    @api.multi
    def write(self, values):
        dealer_spks = super(dealer_spk,self).write(values)
        for rec in self:
            for rspk in self.env['dealer.register.spk.line'].search([('state','=','reserved'),('spk_id','=',None)]):
                rspk.write({'state':'open'})
            for dspk in self.env['dealer.distribusi.spk.line'].search([('state','=','reserved'),('spk_id','=',None)]):
                dspk.write({'state':'open'})
            for rspk in self.env['dealer.register.spk.line'].search([('spk_id','=',rec.name)]):
                rspk.write({'state':'open','spk_id':[]})
            for dspk in self.env['dealer.distribusi.spk.line'].search([('spk_id','=',rec.name)]):
                dspk.write({'state':'open','spk_id':[]})
            rec.distribusi_spk_id.write({'state':'spk','spk_id':rec.id})
            rec.register_spk_id.write({'state':'spk','spk_id':rec.id})

            if rec.partner_id.partner_type in ['Afiliasi','Konsolidasi']:
                values['is_pic'] = True
        return dealer_spks
    
    @api.multi
    def action_create_so(self):
        sale_order_line=[]
        payment_term = False
        if self.finco_id and self.partner_id:
            payment_term = self.finco_id.property_payment_term.id
        else:
            payment_term = self.partner_id.property_payment_term.id
        if self.is_pic:
            pajak_satuan=True
            pajak_gunggung=False
            pajak_gabungan=False
        else:
            # pajak_satuan=False
            if self.partner_id.npwp and not self.partner_id.tipe_faktur_pajak:
                raise Warning("Tipe Faktur Pajak di master Customer belum dilengkapi")
            elif not self.partner_id.npwp and self.partner_id.tipe_faktur_pajak != 'tanpa_fp':
                raise Warning("Nomor NPWP atau Tipe Faktur Pajak di master Customer belum dilengkapi")
            # elif self.partner_id.npwp and self.partner_id.tipe_faktur_pajak == 'tanpa_fp':
            #     raise Warning("Tipe Faktur Pajak tidak boleh diisi 'Tanpa Faktur Pajak' di master Customer jika ada NPWP")
            elif not self.partner_id.npwp and not self.partner_id.tipe_faktur_pajak:
                raise Warning("Tipe Faktur Pajak di master Customer belum dilengkapi")
                
            if self.partner_id.tipe_faktur_pajak == 'tanpa_fp':
                pajak_gunggung=True
                pajak_satuan=False
                pajak_gabungan=False
            elif self.partner_id.tipe_faktur_pajak == 'satuan':
                pajak_gunggung=False
                pajak_satuan=True
                pajak_gabungan=False
            elif self.partner_id.tipe_faktur_pajak == 'gabungan':
                pajak_gunggung=False
                pajak_satuan=False
                pajak_gabungan=True

        sale_order = {
            'branch_id': self.branch_id.id,
            'division': self.division,
            'date_order': datetime.now().strftime('%Y-%m-%d'),
            'partner_id': self.partner_id.id,
            'partner_cabang':self.partner_cabang.id, 
            'employee_id': self.employee_id.id,
            'sales_source': self.sales_source.id,
            'finco_id': self.finco_id.id if self.is_credit else False,     
            'dealer_spk_id': self.id,
            'register_spk_id': self.register_spk_id.id,
            'is_pic': self.is_pic,
            'cddb_id': False,
            'section_id':self.section_id.id,      
            'is_credit':self.is_credit, 
            'finco_cabang':self.finco_cabang.id, 
            'alamat_kirim':self.alamat_kirim,
            'payment_term': payment_term,                 
            'origin': self.origin,
            'pricelist_id': self.pricelist_id.id,
            'proposal_id': self.proposal_id.id,
            'pajak_generate': pajak_satuan,
            'pajak_gunggung': pajak_gunggung,
            'pajak_gabungan': pajak_gabungan,
        }
        so_line_cddb_ids = []
        for line in self.dealer_spk_line:
            for number in range(line.product_qty):
                plat = False
                stnk = False
                tanda_jadi = 0.0
                uang_muka = False
                biro_jasa_branch = False
                price_bbn = 0.0
                total = 0.0
                price_bbn_beli = 0.0
                price_bbn_notice = 0.0
                price_bbn_proses = 0.0
                price_bbn_jasa = 0.0
                price_bbn_jasa_area = 0.0
                price_bbn_fee_pusat = 0.0
                city = False
                if line.uang_muka:
                    uang_muka = line.uang_muka

                if self.pricelist_id.id:
                    price = self._get_price_unit(self.pricelist_id.id, line.product_id.id)
                elif self.branch_id.pricelist_unit_sales_id.id:
                    price = self._get_price_unit(self.branch_id.pricelist_unit_sales_id.id, line.product_id.id)
                else:
                    raise Warning('Pricelist jual unit Cabang "%s" belum ada, silahkan buat dulu' %(self.branch_id.name))
                
                if price <= 0:
                    raise Warning('Pricelist unit %s 0 rupiah, silahkan di set di pricelist cabang terlebih dahulu' %(line.product_id.name))
                
                if line.is_bbn == 'Y':
                    if line.partner_stnk_id.sama == True:
                        city =  line.partner_stnk_id.city_id.id
                    else:
                        city =  line.partner_stnk_id.city_tab_id.id
                    if not city:
                        raise Warning('Alamat customer STNK Belum lengkap!')
                    if self.branch_id.pricelist_bbn_hitam_id.id:
                        price_bbn = self._get_price_unit(self.branch_id.pricelist_bbn_hitam_id.id, line.product_id.id)
                    else:
                        raise Warning('Pricelist jual BBN unit Cabang "%s" belum ada, silahkan buat dulu' %(self.branch_id.name))
                    if price_bbn <= 0:
                        raise Warning('Pricelist bbn unit %s 0 rupiah, silahkan di set di pricelist cabang terlebih dahulu' %(line.product_id.name))
                    
                location_lot = self._get_location_id_branch(line.product_id.id,self.branch_id.id)
                
                if location_lot:
                    lot_id = location_lot[0].lot_id.id
                    location_id = location_lot[0].location_id.id
                    price_unit_beli = location_lot[0].lot_id.hpp
                    location_lot[0].lot_id.write({'state':'reserved'})
                else:
                    raise Warning('Tidak ditemukan stock produk')
                
                values = {
                    'categ_id': 'Unit',
                    'template_id': line.template_id.id,
                    'product_id': line.product_id.id,
                    'product_qty': 1,
                    'is_bbn': line.is_bbn,
                    'plat': plat,
                    'partner_stnk_id': line.partner_stnk_id.id,
                    'location_id': location_id,
                    'lot_id': lot_id,
                    'price_unit': price,
                    'biro_jasa_id': biro_jasa_branch or False,  
                    'price_bbn': price_bbn or 0.0,
                    'price_bbn_beli': price_bbn_beli or 0.0,
                    'tanda_jadi': line.tanda_jadi or 0.0,
                    'tanda_jadi2': self.is_credit and line.tanda_jadi or 0.0,
                    'uang_muka': uang_muka or 0.0,
                    'price_unit_beli':price_unit_beli or 0.0,
                    'price_bbn_notice': price_bbn_notice or 0.0,
                    'price_bbn_proses': price_bbn_proses or 0.0,
                    'price_bbn_jasa': price_bbn_jasa or 0.0,
                    'price_bbn_jasa_area': price_bbn_jasa_area or 0.0,
                    'price_bbn_fee_pusat': price_bbn_fee_pusat or 0.0,
                    'tax_id': [(6,0,[x.id for x in line.product_id.taxes_id])],
                    'city_id': city,
                    'discount_po': line.discount_po,
                    'diskon_dp': self.is_credit and line.discount_po or 0.0,
                }
                if line.cddb_id:
                    so_line_cddb_ids.append((4,[line.cddb_id.id]))
                sale_order_line.append([0,False,values])
        sale_order['dealer_sale_order_line'] = sale_order_line
        if so_line_cddb_ids:
            sale_order['cddb_id'] = so_line_cddb_ids

        create_so = self.env['dealer.sale.order'].create(sale_order)
        self.register_spk_id.write({'state':'so','dealer_sale_order_id':create_so.id})
        self.write({
            'state':'so',
            'dealer_sale_order_id':create_so.id,
            'user_create_so_id': self._uid,
            'so_create_date':datetime.now().strftime('%Y-%m-%d'),
        })        
        return create_so
    
    @api.multi        
    def _get_location_id_branch(self,product_id,branch_id):
        lot_id = self.env['stock.quant'].search([('lot_id.product_id','=',product_id),('lot_id.state','=','stock'),('lot_id.branch_id','=',branch_id),('location_id.usage','=','internal'),('reservation_id','=',False)], order='in_date, id', limit=1)
        return lot_id
    
    def _get_price_unit(self,cr,uid,pricelist,product_id):
        price_unit = self.pool.get('product.pricelist').price_get(cr,uid,[pricelist],product_id,1)[pricelist]
        return price_unit  
    
    def _get_harga_bbn_detail(self, cr, uid, ids, birojasa_id, plat, city_id, product_template_id,branch_id):
        if not birojasa_id:
            return False
        birojasa = self.pool.get('dym.harga.birojasa')
        harga_birojasa = birojasa.search(cr,uid,[
            ('birojasa_id','=',birojasa_id),
            ('branch_id','=',branch_id)
        ])
        if not harga_birojasa :
            return False
        harga_birojasa_browse = birojasa.browse(cr,uid,harga_birojasa)
        bbn_search = self.pool.get('dym.harga.bbn').search(cr,uid,[
            ('id','=',harga_birojasa_browse.harga_bbn_id.id)
        ])
        if not bbn_search :
            return False
        bbn_browse = self.pool.get('dym.harga.bbn').browse(cr,uid,bbn_search)
        pricelist_harga_bbn = self.pool.get('dym.harga.bbn.line').search(cr,uid,[
            ('bbn_id','=',bbn_browse.id),                                                                    
            ('tipe_plat','=',plat),
            ('active','=',True),
            ('start_date','<=',datetime.now().strftime('%Y-%m-%d')),
            ('end_date','>=',datetime.now().strftime('%Y-%m-%d')),
        ])
        if not pricelist_harga_bbn:
            return False
        for pricelist_bbn in pricelist_harga_bbn:
            bbn_detail = self.pool.get('dym.harga.bbn.line.detail').search(cr,uid,[
                ('harga_bbn_line_id','=',pricelist_bbn),
                ('product_template_id','=',product_template_id),
                ('city_id','=',city_id)
                ])
            
            if bbn_detail:
                return self.pool.get('dym.harga.bbn.line.detail').browse(cr,uid,bbn_detail)
            else:
                return False

        return False
    
    @api.multi
    def action_view_so(self):  
       
        return {
            'name': 'Dealer Sale Memo',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': self.dealer_sale_order_id.id
            }
    
    @api.multi
    def action_confirm_spk(self):
        if not self.dealer_spk_line:
            raise osv.except_osv(('Perhatian !'), ('Isi terlebih dahulu Dealer Memo Detailnya !'))
        if self.dealer_spk_line:
            for line in self.dealer_spk_line:
                if line.is_bbn=='Y':
                    cddb_ok = True
                    cddb_partner_stnk = []
                    if not line.cddb_id:
                        cddb_ok = False
                        if line.partner_stnk_id and line.partner_stnk_id.display_name:
                            cddb_partner_stnk.append(line.partner_stnk_id.display_name) 
                        elif line.partner_stnk_id and line.partner_stnk_id.name:
                            cddb_partner_stnk.append(line.partner_stnk_id.display_name)
                    if not cddb_ok:
                        names = ",".join(cddb_partner_stnk)
                        msg = "Harap lengkapi data CDDB partner STNK untuk nama: %s terlebih dahulu!. Check di baris Memo Detail." % names
                        raise osv.except_osv(('Perhatian !'), (msg))
                elif line.is_bbn == 'T' and self.finco_id and self.is_credit:
                    raise osv.except_osv(('Perhatian !'), ("Penjualan credit harus  menggunakan BBN!"))
        for line in self.dealer_spk_line:
            if self.pricelist_id.id:
                price = self._get_price_unit(self.pricelist_id.id, line.product_id.id)
            if self.branch_id.pricelist_unit_sales_id.id:
                price = self._get_price_unit(self.branch_id.pricelist_unit_sales_id.id, line.product_id.id)
            else:
                raise Warning('Pricelist jual unit Cabang "%s" belum ada, silahkan buat dulu' %(self.branch_id.name))
            if price <= 0:
                raise Warning('Pricelist unit %s 0 rupiah, silahkan di set di pricelist cabang terlebih dahulu' %(line.product_id.name))
                
            if line.is_bbn == 'Y':
                if self.branch_id.pricelist_bbn_hitam_id.id:
                    price_bbn = self._get_price_unit(self.branch_id.pricelist_bbn_hitam_id.id, line.product_id.id)
                else:
                    raise Warning('Pricelist jual BBN unit Cabang "%s" belum ada, silahkan buat dulu' %(self.branch_id.name))
                if price_bbn <= 0:
                    raise Warning('Pricelist bbn unit %s 0 rupiah, silahkan di set di pricelist cabang terlebih dahulu' %(line.product_id.name))
                if line.uang_muka > price + price_bbn:
                    raise Warning('Jaminan Pembelian PO lebih besar dari Unit Price + Price BBN')
            location_lot = self._get_location_id_branch(line.product_id.id,self.branch_id.id)
            
            if location_lot:
                lot_id = location_lot[0].lot_id.id
                location_id = location_lot[0].location_id.id
                price_unit_beli = location_lot[0].lot_id.hpp
            else:
                raise Warning('Tidak ditemukan stock produk')
               
        self.write({
            'confirm_date': datetime.now().strftime('%Y-%m-%d'),
            'confirm_uid': self._uid,
            'state': 'progress',
            'date_order':datetime.today()
        })
        return True
    
    @api.multi
    def action_cancel_spk(self):
        self.write({
            'cancel_date': datetime.now().strftime('%Y-%m-%d'),
            'cancel_uid': self._uid,
            'state': 'cancelled'
        })
        return True
    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Dealer Memo sudah diproses, data tidak bisa didelete !"))
        return super(dealer_spk, self).unlink(cr, uid, ids, context=context)    
    
    
class dealer_spk_line(models.Model):
    _name = "dealer.spk.line"
    _description = "Memo Line"
    _order = "id"
    
    categ_id = fields.Selection([('Unit','Unit')],string='Category',required=True,default="Unit")
    dealer_spk_line_id = fields.Many2one('dealer.spk')
    template_id = fields.Many2one('product.template', 'Tipe')
    product_id = fields.Many2one('product.product',string="Produk")
    product_qty = fields.Integer(string="Qty",default=1)
    is_bbn = fields.Selection([('Y','Y'),('T','T')],'BBN',required=True)
    plat = fields.Selection([('H','H'),('M','M')],string='Plat')
    partner_stnk_id = fields.Many2one('res.partner',string='Nama STNK',domain=[('customer','=',True)])
    cddb_id = fields.Many2one('dym.cddb',string='CDDB',required=False)    
    tanda_jadi = fields.Float(string='Tanda Jadi')
    uang_muka = fields.Float(string='Jaminan Pembelian PO')
    discount_po = fields.Float(string='Potongan Pelanggan')
    indent = fields.Boolean(string='Indent')
    
    @api.onchange('is_bbn')
    def onchange_is_bbn(self):
        if self.dealer_spk_line_id.is_pic == True:
            self.is_bbn = 'T'

    @api.onchange('partner_stnk_id')
    def onchange_partner(self):
        if self.partner_stnk_id :
            cddb = self.env['dym.cddb'].search([('customer_id','=',self.partner_stnk_id.id),], limit=1)
            if cddb :
                self.cddb_id = cddb
            else:
                self.cddb_id = False
        else:
            self.cddb_id = False

    @api.onchange('uang_muka')
    def uang_muka_change(self):
        warning = {}
        value = {}
        if  self.uang_muka != 0 and self.dealer_spk_line_id.is_credit == False:
            self.uang_muka = 0
            warning = {'title':'Perhatian !','message':"Penjualan cash tidak boleh ada uang muka!"}
        return {'warning':warning,'value':value}

    @api.onchange('categ_id','template_id')
    def category_change(self):
        dom = {}
        value = {}
        tampung = []
        self.product_id = False
        if self.categ_id:
            categ_ids = self.env['product.category'].get_child_ids(self.categ_id)
            dom['template_id']=[('categ_id','in',categ_ids),('sale_ok','=',True)]
            if self.template_id:
                dom['product_id']=[('product_tmpl_id','=',self.template_id.id),('categ_id','in',categ_ids),('sale_ok','=',True)]
                if len(self.template_id.product_variant_ids) == 1:
                    value['product_id'] = self.template_id.product_variant_ids.id
            else:
                dom['product_id']=[('id','=',0)]
        return {'domain':dom,'value':value}

    @api.onchange('partner_stnk_id','is_bbn')
    def partner_stnk_bbn_change(self):
        if not (self.partner_stnk_id.city_tab_id.id or self.partner_stnk_id.city_id.id) and self.is_bbn == 'Y' and self.partner_stnk_id:
            return {'value':{'partner_stnk_id':False},'warning':{'title':'Perhatian !','message':'Alamat customer STNK ' + self.partner_stnk_id.name + ' Belum lengkap.'}}
        return {}

    
class dealer_reason_spk_cancel(models.TransientModel):
    _name = "dealer.reason.cancel.spk"
   
    reason = fields.Text('Reason',required=True)
    
    @api.multi
    def action_post_cancel(self, context=None):
        spk_id = context.get('active_id',False)        
        spk_obj = self.env['dealer.spk'].browse(spk_id)
        spk_obj.write({
            'reason_cancel':self.reason,
            'cancel_date': datetime.now().strftime('%Y-%m-%d'),
            'cancel_uid': self._uid,
            'state': 'cancelled'
        })
        return True