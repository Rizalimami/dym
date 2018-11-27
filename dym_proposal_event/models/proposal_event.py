from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import re
import openerp.addons.decimal_precision as dp
from dateutil import rrule
from datetime import datetime, date, timedelta
from dateutil.relativedelta import *
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from lxml import etree

class dym_event_template(models.Model):
    _name = "dym.event.template"
    _description = "Activity Template"

    @api.one
    @api.depends('template_line','template_line_biaya')
    def _compute_budget(self):
        budget_pembelian = float(0)
        for line in self.template_line:
            budget_pembelian += line.sub_total
        budget_biaya = float(0)
        for line in self.template_line_biaya:
            budget_biaya += line.amount
        self.budget_biaya = budget_biaya
        self.budget_pembelian = budget_pembelian
        self.budget = budget_pembelian + budget_biaya


    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_event_template, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        ho = False
        for branch in self.pool.get('res.users').browse(cr, uid, uid).area_id.branch_ids:
            if branch.branch_type == 'HO':
                ho = True
        if ho == False:
            raise osv.except_osv(('Invalid action !'), ('User cabang tidak bisa membuat event template!'))
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company_id),('type','=','normal'),('state','not in',('close','cancelled'))])
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='analytic_1']")
        for node in nodes_branch :
            node.set('domain', "[('id','in',"+str(level_1_ids)+")]")
        res['arch'] = etree.tostring(doc)
        return res

    name = fields.Char('Name', required=True)
    branch_id = fields.Many2one('dym.branch', 'Branch')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division')
    budget = fields.Float('Budget Total', digits=dp.get_precision('Account'), compute='_compute_budget')
    budget_pembelian = fields.Float('Budget Capex', digits=dp.get_precision('Account'), compute='_compute_budget')
    budget_biaya = fields.Float('Budget Opex', digits=dp.get_precision('Account'), compute='_compute_budget')
    template_line = fields.One2many('dym.event.template.line', 'template_id', 'Detail Template')
    template_line_biaya = fields.One2many('dym.event.template.line.biaya', 'template_id', 'Detail Template Biaya')
    analytic_1 = fields.Many2one('account.analytic.account', 'Analytical Account Company')
    analytic_2 = fields.Many2one('account.analytic.account', 'Analytical Account Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'Analytical Account Branch')
    analytic_4 = fields.Many2one('account.analytic.account', 'Analytical Account Cost Center')
    number = fields.Char('Activity Template Ref')

    def create(self, cr, uid, vals, context=None):
        if 'branch_id' in vals and vals['branch_id'] != False:
            vals['number'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'ATE', division=False)
        else:
            vals['number'] = self.pool.get('ir.sequence').get_sequence(cr, uid, 'ATE', division=False)
        return super(dym_event_template, self).create(cr, uid, vals, context=context)

    @api.multi
    def name_get(self):
        result = []
        for template in self:
            result.append((template.id, "%s [%s]" % (template.number, template.name)))
        return result

    def change_reset(self, cr, uid, ids, field, context=None):
        res = {}
        if field == 'branch':
            res['analytic_3'] = False
            res['analytic_4'] = False
        if field == 'analytic_2':
            res['analytic_3'] = False
            res['analytic_4'] = False
        if field == 'analytic_3':
            res['analytic_4'] = False
        result = {}
        result['value'] = res
        return result

class dym_event_template_line(models.Model):
    _name = "dym.event.template.line"
    _description = "Event Template Detail"

    @api.one
    @api.depends('unit_price', 'product_qty')
    def _compute_subtotal(self):
        self.sub_total = self.product_qty * self.unit_price

    template_id = fields.Many2one('dym.event.template', 'Event Template')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    name = fields.Text('Description', required=True)
    product_qty = fields.Float('QTY', required=True)
    unit_price = fields.Float('Price', digits=dp.get_precision('Account'), required=False)
    sub_total = fields.Float('Total', digits=dp.get_precision('Account'), compute='_compute_subtotal')
    partner_id = fields.Many2one('res.partner', 'Supplier', required=True)

    @api.constrains('product_id')
    def product_constraint(self):
        if self.product_id.id:
            product_search = self.search([('product_id','=', self.product_id.id),('id','!=', self.id),('template_id','=', self.template_id.id)])
            if product_search:
                raise ValidationError("Product tidak boleh duplicate [" + self.product_id.name + "]")

    def _get_categ_ids(self, cr, uid, categ_name, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, categ_name)
        return categ_ids

    @api.onchange('product_id','partner_id','product_qty')
    def product_partner_qty_change(self):
        value = {}
        domain = {}
        categ_ids = self._get_categ_ids('Umum')
        domain['product_id'] = [('categ_id','in',categ_ids)]
        if self.product_id:
            pricelist = self.partner_id.property_product_pricelist_purchase
            acc_id = self.product_id.property_account_expense.id
            if not acc_id:
                acc_id = self.product_id.categ_id.property_account_expense_categ.id
            self.name = self.product_id.name_get().pop()[1]
            if pricelist:
                date_order_str = datetime.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
                price = pricelist.price_get(self.product_id.id, self.product_qty or 1.0, self.partner_id.id or False)[pricelist.id]
            else:
                price = self.product_id.standard_price 
            self.unit_price = price
        else:
            self.name = ''
            self.unit_price = float(0)
        return  {'value':value, 'domain':domain}

class dym_event_template_line_biaya(models.Model):
    _name = "dym.event.template.line.biaya"
    _description = "Event Template Detail Biaya"

    # @api.one
    # @api.depends('unit_price', 'qty')
    # def _compute_subtotal(self):
    #     self.sub_total = self.qty + self.unit_price

    template_id = fields.Many2one('dym.event.template', 'Event Template')
    account_id = fields.Many2one('account.account', 'Account Biaya', domain="[('type','=','other')]", required=True)
    name = fields.Text('Description', required=True)
    amount = fields.Float('Amount', digits=dp.get_precision('Account'), required=True)


    @api.constrains('account_id')
    def product_constraint(self):
        if self.account_id.id:
            account_search = self.search([('account_id','=', self.account_id.id),('id','!=', self.id),('template_id','=', self.template_id.id)])
            if account_search:
                raise ValidationError("Account payment tidak boleh duplicate [" + self.account_id.name + "]")

    @api.onchange('account_id')
    def account_change(self):
        value = {}
        domain = {}
        return  {'value':value, 'domain':domain}


class dym_proposal_event(models.Model):
    _name = "dym.proposal.event"
    _description = "Register Activity"

    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_proposal_event_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_id',\
            'division',\
            'activity',\
            'address',\
            'start_date',\
            'end_date',\
            'pic',\
            'desc_opex',\
            'bud_opex',\
            'act_opex',\
            'type_target',\
            'warna_target',\
            'qty_target',\
            'act_target',\
            'tipe_partner',\
            'partner',\
            'amount',\
        ]
 
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_arap_details_fields(self, cr, uid, context=None):
        return [
            'document', 'date', 'date_maturity', 'account', 'description',
            'rec_or_rec_part', 'debit', 'credit', 'balance',
            # 'partner_id',
        ]
 
    # Change/Add Template entries
    def _report_xls_arap_overview_template(self, cr, uid, context=None):
        """
        Template updates, e.g.
 
        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Move Line ID')],
                'lines': [1, 0, 'text', _render("p['ids_aml']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
 
    # Change/Add Template entries
    def _report_xls_arap_details_template(self, cr, uid, context=None):
        """
        Template updates, e.g.
 
        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Move Line ID')],
                'lines': [1, 0, 'text', _render("p['ids_aml']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}

    @api.model
    def _get_default_date(self):
        return self.env['dym.branch'].get_default_date_model()

    @api.one
    @api.depends('pengeluaran_ids','biaya_ids')
    def _compute_budget(self):
        budget_pembelian = float(0)
        for line in self.pengeluaran_ids:
            budget_pembelian += line.sub_total_proposal
        budget_biaya = float(0)
        for line in self.biaya_ids:
            budget_biaya += line.amount_proposal
        self.budget_biaya = budget_biaya
        self.budget_pembelian = budget_pembelian
        self.budget = budget_pembelian + budget_biaya

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_proposal_event, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company_id),('type','=','normal'),('state','not in',('close','cancelled'))])
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='analytic_1']")
        for node in nodes_branch :
            node.set('domain', "[('id','in',"+str(level_1_ids)+")]")
        res['arch'] = etree.tostring(doc)
        for field in res['fields']:
            if field == 'division':
                if 'menu' in context and context['menu'] == 'showroom':
                    res['fields'][field]['selection'] = [('Unit','Showroom'), ('Umum','General')]

                if 'menu' in context and context['menu'] == 'workshop':
                    res['fields'][field]['selection'] = [('Sparepart','Workshop'), ('Umum','General')]

                if 'menu' in context and context['menu'] == 'general_affair':
                    res['fields'][field]['selection'] = [('Unit','Showroom'), ('Sparepart','Workshop'), ('Umum','General')]
        return res
        
    budget = fields.Float('Total Proposal', digits=dp.get_precision('Account'), compute='_compute_budget', readonly=True)
    budget_pembelian = fields.Float('Proposal Capex', digits=dp.get_precision('Account'), compute='_compute_budget', readonly=True)
    budget_biaya = fields.Float('Proposal Opex', digits=dp.get_precision('Account'), compute='_compute_budget', readonly=True)
    po_ids = fields.One2many('purchase.order','proposal_id', 'Purchase Order')
    dso_ids = fields.One2many('dealer.sale.order','proposal_id', 'Dealer Sales Memo')
    wo_ids = fields.One2many('dym.work.order','proposal_id', 'Work Order')
    so_ids = fields.One2many('sale.order','proposal_id', 'Sales Memo')
    voucher_ids = fields.One2many('account.voucher','proposal_id', 'Payment Request', domain=[('type','=','purchase')])
    voucher_or_ids = fields.One2many('account.voucher','proposal_id', 'Other Receivable', domain=[('type','=','sale')])
    name = fields.Char('Nama Activity', required=True)
    state = fields.Selection([
                              ('draft','Draft'),
                              ('waiting_for_approval','Waiting For Approval'),
                              ('approved','Approved'),
                              ('done','Done'),
                              ('cancel','Cancelled'),
                              ('reject','Rejected'),
                              ], 'State', default='draft')

    branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', related="branch_id.company_id.partner_id")

    sale_status = fields.Selection([('Sales','Sales'),('Nonsales','Non Sales')], 'Jenis Activity', required=True)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division', required=True)
    budget_template = fields.Float(related='template_id.budget', string='Total Budget')
    budget_pembelian_template = fields.Float(related='template_id.budget_pembelian', string='Budget Capex')
    budget_biaya_template = fields.Float(related='template_id.budget_biaya', string='Budget Opex')
    start_date = fields.Date('Start Date', required=True)
    stop_date = fields.Date('End Date', required=True)

    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    rt = fields.Char('RT', size=3)
    rw = fields.Char('RW',size=3)
    state_id = fields.Many2one("res.country.state", 'State', ondelete='restrict')
    city_id = fields.Many2one('dym.city','City',domain="[('state_id','=',state_id)]")
    kecamatan_id = fields.Many2one('dym.kecamatan','Kecamatan', size=128,domain="[('state_id','=',state_id),('city_id','=',city_id)]")
    kecamatan = fields.Char('Kecamatan', size=100)
    zip_id = fields.Many2one('dym.kelurahan', 'ZIP Code',domain="[('kecamatan_id','=',kecamatan_id),('state_id','=',state_id),('city_id','=',city_id)]")
    kelurahan = fields.Char('Kelurahan',size=100)

    template_id = fields.Many2one('dym.event.template', 'Event Template', domain="[('branch_id','in',[branch_id,False]),('division','in',[division,False])]")
    parent_id = fields.Many2one('dym.proposal.event', 'Parent Proposal')
    child_ids = fields.One2many('dym.proposal.event', 'parent_id', 'Linked Proposal')
    pengeluaran_ids = fields.One2many('dym.proposal.event.pengeluaran', 'template_id', 'Capex')
    biaya_ids = fields.One2many('dym.proposal.event.biaya', 'template_id', 'Opex')
    target_ids = fields.One2many('dym.proposal.event.target', 'template_id', 'Sales Target')
    recurrency = fields.Boolean('Recurrent')
    rrule_type = fields.Selection([('daily', 'Day(s)'), ('weekly', 'Week(s)'), ('monthly', 'Month(s)'), ('yearly', 'Year(s)')], 'Recurrecny', default=False)
    end_type = fields.Selection([('count', 'Number of repetitions'), ('end_date', 'End date')], 'Recurrence Termination', default='count')
    interval = fields.Integer('Repeat Every', help="Repeat every (Days/Week/Month/Year)", default=1)
    count = fields.Integer('Repeat', help="Repeat x times", default=1)
    mo = fields.Boolean('Mon')
    tu = fields.Boolean('Tue')
    we = fields.Boolean('Wed')
    th = fields.Boolean('Thu')
    fr = fields.Boolean('Fri')
    sa = fields.Boolean('Sat')
    su = fields.Boolean('Sun')
    month_by = fields.Selection([('date', 'Date of month'), ('day', 'Day of month')], 'Option', oldname='select1', default='date')
    day = fields.Integer('Date of month')
    week_list = fields.Selection([('mo', 'Monday'), ('tu', 'Tuesday'), ('we', 'Wednesday'), ('th', 'Thursday'), ('fr', 'Friday'), ('sa', 'Saturday'), ('su', 'Sunday')], 'Weekday')
    byday = fields.Selection([(1, 'First'), (2, 'Second'), (3, 'Third'), (4, 'Fourth'), (5, 'Fifth'), (-1, 'Last')], 'By day')
    final_date = fields.Date('Repeat Until')
    analytic_1 = fields.Many2one('account.analytic.account', 'Analytical Account Company')
    analytic_2 = fields.Many2one('account.analytic.account', 'Analytical Account Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'Analytical Account Branch')
    analytic_4 = fields.Many2one('account.analytic.account', 'Analytical Account Cost Center')
    number = fields.Char('Nomor Activity')
    sharing_ids = fields.One2many('dym.proposal.event.sharing', 'template_id', 'Sharing Biaya')
    km = fields.Integer('Jarak Tempuh Dari Cabang (KM)')
    waktu_tempuh = fields.Integer('Waktu Tempuh Dari Cabang (Menit)')
    pic = fields.Many2one('hr.employee', 'PIC')
    pdi_basah = fields.Integer('Display Basah')
    pdi_kering = fields.Integer('Display Kering')
    marketing_executive = fields.Integer('Marketing Executive')
    marketing_trainee = fields.Integer('Marketing Trainee')
    administrasi = fields.Integer('Administrasi')

    def change_reset(self, cr, uid, ids, field, context=None):
        res = {}
        if field == 'branch':
            res['analytic_3'] = False
            res['analytic_4'] = False
        if field == 'analytic_2':
            res['analytic_3'] = False
            res['analytic_4'] = False
        if field == 'analytic_3':
            res['analytic_4'] = False
        result = {}
        result['value'] = res
        return result

    def create(self, cr, uid, vals, context=None):
        vals['number'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'RAC', division=vals['division'])
        return super(dym_proposal_event, self).create(cr, uid, vals, context=context)

    @api.multi
    def name_get(self):
        result = []
        for proposal in self:
            result.append((proposal.id, "%s [%s]" % (proposal.number, proposal.name)))
        return result

    @api.onchange('street','street2','rt','rw','state_id','city_id','kecamatan_id','kecamatan','zip_id','kelurahan')
    def onchange_address(self):
        value ={}
        warning = {}
        if self.street :
            value['street_tab'] = self.street
        if self.street2 :
            value['street2_tab'] = self.street2
        if self.rt :
            if len(self.rt) > 3 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RT tidak boleh lebih dari 3 digit ! ')),
                }
                value = {
                         'rt':False
                         }
            cek = self.rt.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RT hanya boleh angka ! ')),
                }
                value = {
                         'rt':False
                         }  
            else :
                value['rt_tab'] = self.rt
        if self.rw :
            if len(self.rw) > 3 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RW tidak boleh lebih dari 3 digit ! ')),
                }
                value = {
                         'rw':False
                         }
            cek = self.rw.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RW hanya boleh angka ! ')),
                }
                value = {
                         'rw':False
                         }   
            else :            
                value['rw_tab'] = self.rw   
        if self.state_id :
            value['state_tab_id'] = self.state_id.id
        if self.city_id :
            value['city_tab_id'] = self.city_id.id      
        if self.kecamatan_id :
            value['kecamatan_tab_id'] = self.kecamatan_id.id
            value['kecamatan_tab'] = self.kecamatan_id.name 
            value['kecamatan'] = self.kecamatan_id.name
        if self.zip_id :
            value['zip_tab_id'] = self.zip_id.id
            value['kelurahan_tab'] = self.zip_id.name   
            value['kelurahan'] = self.zip_id.name                
        return {'value':value,'warning':warning}     

    @api.onchange('template_id')
    def template_change(self):
        if self.template_id:
            self.pengeluaran_ids.unlink()
            res = []
            for x in self.template_id.template_line:
                pricelist = x.partner_id.property_product_pricelist_purchase
                if pricelist:
                    date_order_str = datetime.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
                    price = pricelist.price_get(x.product_id.id, x.product_qty or 1.0, x.partner_id.id or False)[pricelist.id]
                else:
                    price = x.product_id.standard_price 
                res.append([0,0,{
                                 'product_id':x.product_id.id,                               
                                 'name':x.name,
                                 'product_qty_proposal':x.product_qty,
                                 'unit_price_proposal':price,
                                 'partner_id':x.partner_id.id,
                }])
            self.pengeluaran_ids = res
            self.biaya_ids.unlink()
            biaya = []
            for x in self.template_id.template_line_biaya:
                biaya.append([0,0,{
                                 'account_id':x.account_id.id,
                                 'name':x.name,
                                 'amount_proposal':x.amount,
                }])
            self.biaya_ids = biaya
            self.analytic_1 = self.template_id.analytic_1.id
            self.analytic_2 = self.template_id.analytic_2.id
            self.analytic_3 = self.template_id.analytic_3.id
            self.analytic_4 = self.template_id.analytic_4.id

    @api.multi
    def wkf_action_cancel(self):
        if self.po_ids or self.voucher_ids or self.dso_ids or self.wo_ids or self.so_ids:
            raise osv.except_osv(('Invalid action !'), ('Data sudah di proses, tidak bisa mencancel data!'))
        self.write({'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
        
    @api.multi
    def close_proposal(self):
        self.write({'state': 'done'})
    
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Cannot delete a proposal which is in state \'%s\'!') % (val.state))
        return super(dym_proposal_event, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def generate_schedule(self):
        if self.child_ids:
            for child in self.child_ids:
                if child.state == 'draft':
                    child.unlink()
        res = {}
        res['name'] = self.name
        res['branch_id'] = self.branch_id.id
        res['division'] = self.division
        res['state'] = 'draft'

        res['street'] = self.street
        res['street2'] = self.street2
        res['rt'] = self.rt
        res['rw'] = self.rw
        res['state_id'] = self.state_id.id
        res['city_id'] = self.city_id.id
        res['kecamatan_id'] = self.kecamatan_id.id
        res['kecamatan'] = self.kecamatan
        res['zip_id'] = self.zip_id.id
        res['kelurahan'] = self.kelurahan

        res['template_id'] = self.template_id.id
        res['parent_id'] = self.id
        res['sale_status'] = self.sale_status
        res['analytic_1'] = self.analytic_1.id
        res['analytic_2'] = self.analytic_2.id
        res['analytic_3'] = self.analytic_3.id
        res['analytic_4'] = self.analytic_4.id
        pengeluaran = []
        for x in self.pengeluaran_ids:
            pengeluaran.append([0,0,{
                             'product_id':x.product_id.id,                               
                             'name':x.name,
                             'product_qty_proposal':x.product_qty_proposal,
                             'unit_price_proposal':x.unit_price_proposal,
                             'partner_id':x.partner_id.id,
            }])
        res['pengeluaran_ids'] = pengeluaran

        biaya = []
        for x in self.biaya_ids:
            biaya.append([0,0,{
                             'account_id':x.account_id.id,
                             'name':x.name,
                             'amount_proposal':x.amount_proposal,
            }])
        res['biaya_ids'] = biaya

        start_date = datetime.strptime(self.start_date, '%Y-%m-%d')
        stop_date = datetime.strptime(self.stop_date, '%Y-%m-%d')
        if self.end_type == 'end_date':
            final_date = datetime.strptime(self.final_date, '%Y-%m-%d')

        current_date = start_date
        date_diff = int((datetime.date(stop_date)-datetime.date(start_date)).days)
        week_to_number = {'mo': 0,'tu': 1,'we': 2,'th': 3,'fr': 4,'sa': 5,'su': 6}
        if self.rrule_type == 'daily':
            if self.end_type == 'count':
                for i in range(self.count):
                    res['start_date'] = start_date+timedelta(days=(i+1)*self.interval)
                    res['stop_date'] = stop_date+timedelta(days=(i+1)*self.interval)
                    self.create(res)
            else:
                while current_date <= final_date:
                    current_date = current_date+timedelta(days=self.interval)
                    if current_date <= final_date:
                        res['start_date'] = current_date
                        res['stop_date'] = current_date+timedelta(days=date_diff)
                        self.create(res)
        elif self.rrule_type == 'weekly':
            week_checked = []
            if self.mo == True:
                week_checked.append(week_to_number['mo'])
            if self.tu == True:
                week_checked.append(week_to_number['tu'])
            if self.we == True:
                week_checked.append(week_to_number['we'])
            if self.th == True:
                week_checked.append(week_to_number['th'])
            if self.fr == True:
                week_checked.append(week_to_number['fr'])
            if self.sa == True:
                week_checked.append(week_to_number['sa'])
            if self.su == True:
                week_checked.append(week_to_number['su'])
            if self.end_type == 'count':
                for i in range(self.count):
                    if not week_checked:
                        res['start_date'] = start_date+timedelta(days=(i+1)*7*self.interval)
                        res['stop_date'] = stop_date+timedelta(days=(i+1)*7*self.interval)
                        self.create(res)
                    else:
                        next_day = False
                        for day in week_checked:
                            if day > current_date.weekday():
                                next_day = day
                                break
                        if next_day == False:
                            next_day = week_checked[0]
                        if next_day < current_date.weekday():
                            next_interval = next_day + (7*self.interval) - current_date.weekday()
                        else:
                            next_interval = next_day - current_date.weekday()
                        current_date = current_date+timedelta(days=next_interval)
                        res['start_date'] = current_date
                        res['stop_date'] = current_date+timedelta(days=date_diff)
                        self.create(res)
            else:
                while current_date <= final_date:
                    if not week_checked:
                        current_date = current_date+timedelta(days=7*self.interval)
                        if current_date <= final_date:
                            res['start_date'] = current_date
                            res['stop_date'] = current_date+timedelta(days=date_diff)
                            self.create(res)
                    else:
                        next_day = False
                        for day in week_checked:
                            if day > current_date.weekday():
                                next_day = day
                                break
                        if next_day == False:
                            next_day = week_checked[0]
                        if next_day < current_date.weekday():
                            next_interval = next_day + (7*self.interval) - current_date.weekday()
                        else:
                            next_interval = next_day - current_date.weekday()
                        current_date = current_date+timedelta(days=next_interval)
                        if current_date <= final_date:
                            res['start_date'] = current_date
                            res['stop_date'] = current_date+timedelta(days=date_diff)
                            self.create(res)
        elif self.rrule_type == 'monthly':
            if self.end_type == 'count':
                for i in range(self.count):
                    save_start_date = start_date+relativedelta(months=(i+1)*self.interval)
                    if self.month_by == 'date':
                        next_month = date(save_start_date.year, save_start_date.month, 1).replace(day=28) + timedelta(days=4)
                        last_day_of_month = next_month - timedelta(days=next_month.day)
                        replace_date = last_day_of_month.day
                        if self.day <= last_day_of_month.day:
                            replace_date = self.day
                        res['start_date'] = save_start_date.replace(day=replace_date)
                        res['stop_date'] = save_start_date.replace(day=replace_date)+timedelta(days=date_diff)
                        self.create(res)
                    else:
                        replace_date = 1
                        if self.byday == -1:
                            replace_date = 31
                        if self.week_list == 'mo':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=MO(self.byday))
                        if self.week_list == 'tu':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=TU(self.byday))
                        if self.week_list == 'we':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=WE(self.byday))
                        if self.week_list == 'th':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=TH(self.byday))
                        if self.week_list == 'fr':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=FR(self.byday))
                        if self.week_list == 'sa':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=SA(self.byday))
                        if self.week_list == 'su':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=SU(self.byday))
                        res['start_date'] = next_day
                        res['stop_date'] = next_day+timedelta(days=date_diff)
                        self.create(res)
            else:
                while current_date <= final_date:
                    save_start_date = current_date+relativedelta(months=self.interval)
                    if self.month_by == 'date':
                        next_month = date(save_start_date.year, save_start_date.month, 1).replace(day=28) + timedelta(days=4)
                        last_day_of_month = next_month - timedelta(days=next_month.day)
                        replace_date = last_day_of_month.day
                        if self.day <= last_day_of_month.day:
                            replace_date = self.day
                        current_date = save_start_date.replace(day=replace_date)
                        if current_date <= final_date:
                            res['start_date'] = current_date
                            res['stop_date'] = current_date + timedelta(days=date_diff)
                            self.create(res)
                    else:
                        replace_date = 1
                        if self.byday == -1:
                            replace_date = 31
                        if self.week_list == 'mo':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=MO(self.byday))
                        if self.week_list == 'tu':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=TU(self.byday))
                        if self.week_list == 'we':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=WE(self.byday))
                        if self.week_list == 'th':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=TH(self.byday))
                        if self.week_list == 'fr':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=FR(self.byday))
                        if self.week_list == 'sa':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=SA(self.byday))
                        if self.week_list == 'su':
                            next_day = save_start_date + relativedelta(day=replace_date, weekday=SU(self.byday))
                        current_date = next_day
                        if current_date <= final_date:
                            res['start_date'] = current_date
                            res['stop_date'] = current_date + timedelta(days=date_diff)
                            self.create(res)
        elif self.rrule_type == 'yearly':
            if self.end_type == 'count':
                for i in range(self.count):
                    res['start_date'] = start_date+relativedelta(years=(i+1)*self.interval)
                    res['stop_date'] = stop_date+relativedelta(years=(i+1)*self.interval)
                    self.create(res)
            else:
                while current_date <= final_date:
                    current_date = current_date+relativedelta(years=self.interval)
                    if current_date <= final_date:
                        res['start_date'] = current_date
                        res['stop_date'] = current_date+timedelta(days=date_diff)
                        self.create(res)
        return True

class dym_proposal_event_pengeluaran(models.Model):
    _name = "dym.proposal.event.pengeluaran"

    @api.one
    def _compute(self):
        product_qty = 0
        sub_total = 0
        if self.product_id:
            for po in self.template_id.po_ids:
                for line in po.order_line: 
                    if line.product_id.id == self.product_id.id:
                        invoice_lines = self.env['account.invoice.line'].search([('purchase_line_id','=',line.id),('invoice_id.state','not in',['draft','cancel'])])
                        for inv_line in invoice_lines:
                            product_qty += inv_line.quantity
                            sub_total += inv_line.price_subtotal
            product_qty_template = 0
            unit_price_template = 0
            sub_total_template = 0
            if self.template_id.template_id:
                for line in self.template_id.template_id.template_line:
                    if line.product_id.id == self.product_id.id:
                        product_qty_template = line.product_qty
                        unit_price_template = line.unit_price
                        sub_total_template = line.sub_total

            self.product_qty_template = product_qty_template
            self.unit_price_template = unit_price_template
            self.sub_total_template = sub_total_template
        self.sub_total = sub_total
        self.product_qty = product_qty
        self.sub_total_proposal = self.unit_price_proposal * self.product_qty_proposal

    template_id = fields.Many2one('dym.proposal.event', 'Event Template')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    name = fields.Text('Description', required=True)
    product_qty = fields.Integer('QTY Actual', readonly=True, compute='_compute')
    sub_total = fields.Float(string='Amount Actual', digits=dp.get_precision('Account'), readonly=True, compute='_compute')
    product_qty_template = fields.Integer('QTY Budget', readonly=True, compute='_compute')
    unit_price_template = fields.Float(string='Unit Price Budget', digits=dp.get_precision('Account'), readonly=True, compute='_compute')
    sub_total_template = fields.Float(string='Budget Opex', digits=dp.get_precision('Account'), readonly=True, compute='_compute')
    product_qty_proposal = fields.Integer('QTY Proposal', required=True)
    unit_price_proposal = fields.Integer('Price Proposal', required=True)
    sub_total_proposal = fields.Integer('Total Proposal', compute='_compute')
    partner_id = fields.Many2one('res.partner', 'Supplier')

    @api.constrains('product_id')
    def product_constraint(self):
        if self.product_id.id:
            product_search = self.search([('product_id','=', self.product_id.id),('id','!=', self.id),('template_id','=', self.template_id.id)])
            if product_search:
                raise ValidationError("Product tidak boleh duplicate [" + self.product_id.name + "]")

    def _get_categ_ids(self, cr, uid, categ_name, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, categ_name)
        return categ_ids

    @api.onchange('product_id','partner_id','product_qty_proposal')
    def product_partner_qty_change(self):
        value = {}
        domain = {}
        categ_ids = self._get_categ_ids('Umum')
        domain['product_id'] = [('categ_id','in',categ_ids)]
        if self.product_id:
            pricelist = self.partner_id.property_product_pricelist_purchase
            acc_id = self.product_id.property_account_expense.id
            if not acc_id:
                acc_id = self.product_id.categ_id.property_account_expense_categ.id
            self.name = self.product_id.name_get().pop()[1]
            if pricelist:
                date_order_str = datetime.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
                price = pricelist.price_get(self.product_id.id, self.product_qty_proposal or 1.0, self.partner_id.id or False)[pricelist.id]
            else:
                price = self.product_id.standard_price 
            self.unit_price_proposal = price
        else:
            self.name = ''
            self.unit_price_proposal = float(0)
        return  {'value':value, 'domain':domain}

class dym_proposal_event_biaya(models.Model):
    _name = "dym.proposal.event.biaya"

    @api.one
    def _compute(self):
        amount = 0
        if self.account_id:
            for voucher in self.template_id.voucher_ids:
                if voucher.state == 'posted':
                    payed = self.env['account.move.line'].search([('move_id','=',voucher.move_id.id),('reconcile_id','!=',False),('credit','>',0)])
                    if payed:
                        for line in voucher.line_dr_ids:
                            if line.account_id.id == self.account_id.id:
                                amount += line.amount
            amount_template = 0
            if self.template_id.template_id:
                for line in self.template_id.template_id.template_line_biaya:
                    if line.account_id.id == self.account_id.id:
                        amount_template = line.amount

            self.amount_template = amount_template
        self.amount = amount

    template_id = fields.Many2one('dym.proposal.event', 'Event Template')
    name = fields.Text('Description')
    account_id = fields.Many2one('account.account', 'Account Biaya', domain="[('type','=','other')]")
    amount = fields.Float(string='Amount Actual', digits=dp.get_precision('Account'), readonly=True, compute='_compute')
    amount_template = fields.Float(string='Amount Budget', digits=dp.get_precision('Account'), readonly=True, compute='_compute')
    amount_proposal = fields.Float(string='Amount Proposal', digits=dp.get_precision('Account'), required=True)

    @api.constrains('account_id')
    def product_constraint(self):
        if self.account_id.id:
            account_search = self.search([('account_id','=', self.account_id.id),('id','!=', self.id),('template_id','=', self.template_id.id)])
            if account_search:
                raise ValidationError("Account payment tidak boleh duplicate [" + self.account_id.name + "]")


    @api.onchange('account_id')
    def account_change(self):
        value = {}
        domain = {}
        return  {'value':value, 'domain':domain}


class dym_proposal_event_sharing(models.Model):
    _name = "dym.proposal.event.sharing"


    template_id = fields.Many2one('dym.proposal.event', 'Event Template')
    tipe_partner = fields.Selection([('DEALER', 'DEALER'), ('LEASING', 'LEASING'), ('LAIN-LAIN', 'LAIN-LAIN')], 'Tipe Partner')
    sharing_partner = fields.Many2one('res.partner', 'Sharing Partner')
    sharing_amount = fields.Float('Sharing Amount')


class dym_proposal_event_target(models.Model):
    _name = "dym.proposal.event.target"

    @api.one
    @api.depends('unit_price', 'qty')
    def _compute_subtotal(self):
        self.sub_total = self.unit_price * self.qty
        # self.sub_total = (self.unit_price - self.discount) * self.qty

    @api.one
    def _compute(self):
        qty = 0
        amount = 0
        if self.product_id:
            invoice_ids = []
            for dso in self.template_id.dso_ids:
                invoices = self.env['account.invoice'].search([('origin','ilike',dso.name),('type','=','out_invoice'),('state','not in',['draft','cancel'])])
                invoice_ids += invoices.ids
            for wo in self.template_id.wo_ids:
                invoices = self.env['account.invoice'].search([('origin','ilike',wo.name),('type','=','out_invoice'),('state','not in',['draft','cancel'])])
                invoice_ids += invoices.ids
            for so in self.template_id.so_ids:
                invoices = self.env['account.invoice'].search([('id','in',so.invoice_ids.ids),('type','=','out_invoice'),('state','not in',['draft','cancel'])])
                invoice_ids += invoices.ids
            for inv in self.env['account.invoice'].browse(invoice_ids):
                for inv_line in inv.invoice_line:
                    if self.product_id.id == inv_line.product_id.id:
                        qty += inv_line.quantity
                        amount += inv_line.price_subtotal
        self.amount = amount
        self.qty_sold = qty

    template_id = fields.Many2one('dym.proposal.event', 'Event Template')
    prod_tmpl_id = fields.Many2one('product.template', 'Tipe')
    product_id = fields.Many2one('product.product', 'Variant', required=True)
    qty = fields.Integer('Target QTY', default=1)
    unit_price = fields.Float(string='Unit Price', digits=dp.get_precision('Account'), required=False)
    unit_price_readonly = fields.Float(string='Unit Price', digits=dp.get_precision('Account'), related="unit_price")
    # discount = fields.Float(string='Discount', digits=dp.get_precision('Account'), required=True)
    sub_total = fields.Float(string='Total', digits=dp.get_precision('Account'), readonly=True, compute='_compute_subtotal')
    qty_sold = fields.Integer('Sold QTY', readonly=True, compute='_compute')
    amount = fields.Float(string='Sold Amount', digits=dp.get_precision('Account'), readonly=True, compute='_compute')

    @api.constrains('product_id')
    def product_constraint(self):
        if self.product_id.id:
            product_search = self.search([('product_id','=', self.product_id.id),('id','!=', self.id),('template_id','=', self.template_id.id)])
            if product_search:
                raise ValidationError("Product tidak boleh duplicate [" + self.product_id.name + "]")

    def _get_categ_ids(self, cr, uid, categ_name, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, categ_name)
        return categ_ids

    @api.onchange('product_id','prod_tmpl_id')
    def product_change(self):
        value = {}
        domain = {}
        categ_ids = self._get_categ_ids(self.template_id.division)
        domain['prod_tmpl_id'] = [('categ_id','in',categ_ids)]
        if self.template_id.division != 'Unit':
            domain['product_id'] = [('categ_id','in',categ_ids)]
            domain['prod_tmpl_id'] = [('id','=',0)]
        else:
            if not self.prod_tmpl_id:
                domain['product_id'] = [('id','=',0)]
                self.product_id = False
            else:
                domain['product_id'] = [('product_tmpl_id','=',self.prod_tmpl_id.id),('categ_id','in',categ_ids)]
                if self.prod_tmpl_id and self.product_id.product_tmpl_id.id != self.prod_tmpl_id.id:
                    self.product_id = False
                if len(self.prod_tmpl_id.product_variant_ids) == 1:
                    self.product_id = self.prod_tmpl_id.product_variant_ids.id
        if self.product_id:
            pricelist_id = self.template_id.branch_id.pricelist_unit_sales_id
            price = self.product_id.standard_price
            if pricelist_id:
                date_order_str = self.template_id.start_date
                price = pricelist_id.price_get(self.product_id.id, self.qty or 1.0, False, context={'uom': self.product_id, 'date': date_order_str})[pricelist_id.id]
            self.unit_price = price
        else:
            self.unit_price = 0
        return  {'value':value, 'domain':domain}

class dym_purchase_requisition(models.Model):
    _inherit = "purchase.requisition"

    proposal_id = fields.Many2one('dym.proposal.event', 'Proposal Event Ref.', domain="[('state','=','approved'),('branch_id','=',branch_id),('division','=',division)]")

    def _prepare_purchase_order(self, cr, uid, requisition, supplier, type_id, start, end, context=None):
        res =  super(dym_purchase_requisition, self)._prepare_purchase_order(cr, uid, requisition, supplier, type_id, start, end, context=context)
        if requisition.proposal_id:
            res['proposal_id'] = requisition.proposal_id.id
        return res

    def wkf_approval(self,cr,uid,ids,context=None):
        res =  super(dym_purchase_requisition, self).wkf_approval(cr, uid, ids, context=context)
        pr = self.browse(cr, uid, ids)
        if pr.proposal_id:
            for line in pr.line_ids:
                pengeluaran_search = self.pool.get('dym.proposal.event.pengeluaran').search(cr, uid, [('template_id','=',pr.proposal_id.id),('product_id','=',line.product_id.id)])
                if not pengeluaran_search:
                    save = {
                         'product_id':line.product_id.id,                               
                         'name':line.product_id.name_get().pop()[1],
                         'template_id':pr.proposal_id.id,
                         'unit_price_proposal':0,
                         'product_qty_proposal':0,
                    }
                    self.pool.get('dym.proposal.event.pengeluaran').create(cr, uid, save)
        return res

class dym_purchase_order(models.Model):
    _inherit = "purchase.order"

    proposal_id = fields.Many2one('dym.proposal.event', 'Proposal Event Ref.')
    request_date = fields.Date(string='Request Date', related='requisition_id.date')

class dym_purchase_order(models.Model):
    _inherit = "dealer.spk"

    proposal_id = fields.Many2one('dym.proposal.event', 'Proposal Event Ref.', domain="[('state','in',['approved','done']),('branch_id','=',branch_id),('division','=',division)]")

class dym_account_voucher(models.Model):
    _inherit = "account.voucher"

    @api.one
    def _get_vouchers(self):
        voucher_text = ''
        if self.state == 'posted':
            move_lines = self.env['account.move.line'].search([('reconcile_id','!=',False),('debit','>',0),('name','=',self.number)])
            if move_lines:
                for move_line in move_lines:
                    vouchers = self.env['account.voucher'].search([('move_id','=',move_line.move_id.id)])
                    for voucher in vouchers:
                        voucher_text += voucher.number + ' '
        self.voucher_text = voucher_text

    proposal_id = fields.Many2one('dym.proposal.event', 'Proposal Event Ref.', domain="[('state','=','approved'),('branch_id','=',branch_id),('division','=',division)]")
    voucher_text = fields.Char('Payment Voucher', readonly=True, compute='_get_vouchers')

    def action_move_line_create(self, cr, uid, ids, context=None):
        res = super(dym_account_voucher,self).action_move_line_create(cr, uid, ids, context=context)
        voucher = self.browse(cr, uid, ids)
        if voucher.proposal_id:
            for line in voucher.line_dr_ids:
                pengeluaran_search = self.pool.get('dym.proposal.event.biaya').search(cr, uid, [('template_id','=',voucher.proposal_id.id),('account_id','=',line.account_id.id)])
                if not pengeluaran_search:
                    save = {                             
                         'name':line.name,
                         'account_id':line.account_id.id,
                         'template_id':voucher.proposal_id.id,
                         'amount_proposal':0,
                    }
                    self.pool.get('dym.proposal.event.biaya').create(cr, uid, save)
        return res
    
class dym_dealer_sale_order(models.Model):
    _inherit = "dealer.sale.order"

    @api.one
    def _get_invoice(self):
        invoice_text = ''
        invoices = self.env['account.invoice'].search([('origin','ilike',self.name),('type','=','out_invoice'),('state','not in',['draft','cancel'])])
        for inv in invoices:
            invoice_text += inv.number + ' '
        self.invoice_text = invoice_text

    proposal_id = fields.Many2one('dym.proposal.event', 'Proposal Event Ref.', domain="[('state','in',['approved','done']),('branch_id','=',branch_id),('division','=',division)]")
    invoice_text = fields.Char('Invoices', readonly=True, compute='_get_invoice')

    def wkf_approval(self,cr,uid,ids,context=None):
        res =  super(dym_dealer_sale_order, self).wkf_approval(cr, uid, ids, context=context)
        dso = self.browse(cr, uid, ids)
        if dso.proposal_id:
            for line in dso.dealer_sale_order_line:
                target_search = self.pool.get('dym.proposal.event.target').search(cr, uid, [('template_id','=',dso.proposal_id.id),('product_id','=',line.product_id.id)])
                if not target_search:
                    save = {
                         'product_id':line.product_id.id,                               
                         'qty':line.product_qty,
                         'unit_price':line.price_unit,
                         'template_id':dso.proposal_id.id,
                    }
                    self.pool.get('dym.proposal.event.target').create(cr, uid, save)
        return res

class dym_sale_order(models.Model):
    _inherit = "sale.order"

    proposal_id = fields.Many2one('dym.proposal.event', 'Proposal Event Ref.', domain="[('state','in',['approved','done']),('branch_id','=',branch_id),('division','=',division)]")

    def action_button_confirm(self,cr,uid,ids,context=None):
        res =  super(dym_sale_order, self).action_button_confirm(cr, uid, ids, context=context)
        so = self.browse(cr, uid, ids)
        if so.proposal_id:
            for line in so.order_line:
                target_search = self.pool.get('dym.proposal.event.target').search(cr, uid, [('template_id','=',so.proposal_id.id),('product_id','=',line.product_id.id)])
                if not target_search:
                    save = {
                         'product_id':line.product_id.id,                               
                         'qty':line.product_uom_qty,
                         'unit_price':line.price_unit,
                         'template_id':so.proposal_id.id,
                    }
                    self.pool.get('dym.proposal.event.target').create(cr, uid, save)
        return res

class dym_work_order(models.Model):
    _inherit = "dym.work.order"

    @api.one
    def _get_invoice(self):
        invoice_text = ''
        invoices = self.env['account.invoice'].search([('origin','ilike',self.name),('type','=','out_invoice'),('state','not in',['draft','cancel'])])
        for inv in invoices:
            invoice_text += inv.number + ' '
        self.invoice_text = invoice_text

    proposal_id = fields.Many2one('dym.proposal.event', 'Proposal Event Ref.', domain="[('state','in',['approved','done']),('branch_id','=',branch_id),('division','=',division)]")
    invoice_text = fields.Char('Invoices', readonly=True, compute='_get_invoice')

    def wkf_approval(self,cr,uid,ids,context=None):
        res =  super(dym_work_order, self).wkf_approval(cr, uid, ids, context=context)
        wo = self.browse(cr, uid, ids)
        if wo.proposal_id:
            for line in wo.work_lines:
                target_search = self.pool.get('dym.proposal.event.target').search(cr, uid, [('template_id','=',wo.proposal_id.id),('product_id','=',line.product_id.id)])
                if not target_search:
                    save = {
                         'product_id':line.product_id.id,                               
                         'qty':line.product_qty,
                         'unit_price':line.price_unit,
                         'template_id':wo.proposal_id.id,
                    }
                    self.pool.get('dym.proposal.event.target').create(cr, uid, save)
        return res


class dym_report_penjualan_wizard(models.TransientModel):
    _inherit = 'dym.report.penjualan.wizard'
    _description = 'Report Penjualan Wizard'
    
    proposal_id = fields.Many2one('dym.proposal.event', 'Proposal Event')
