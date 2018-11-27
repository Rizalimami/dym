import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class dealer_distribusi_spk(models.Model):
    
    _name = "dealer.distribusi.spk"
    _description = "Distribusi Memo Dealer"
    _order = "id asc"

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    @api.model
    def _getCompanyBranch(self):
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        branch_ids = [b.id for b in self.env.user.branch_ids if b.company_id.id==company_id]
        return [('id','in',branch_ids)]

    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, domain=_getCompanyBranch)
    sales_id = fields.Many2one('hr.employee', string='Salesman', required=True)
    date = fields.Date(string='Date',required=True,default=fields.Date.context_today)
    distribusi_spk_ids = fields.One2many('dealer.distribusi.spk.line','distribusi_spk_id',ondelete='cascade')
    state = fields.Selection([
                              ('draft','Draft'),
                              ('cancel','Cancel'),
                              ('posted','Posted'),
                              ],default='draft')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    
    @api.model
    def create(self,values,context=None):
        vals = {}
        values['date'] = datetime.today()
        create_dealer_distribusi_spks = super(dealer_distribusi_spk,self).create(values)
                
        return create_dealer_distribusi_spks
    
    @api.multi
    def action_post(self):
        for distribusi in self.distribusi_spk_ids:
            distribusi.dealer_register_spk_line_id.write({'sales_id':self.sales_id.id,'tanggal_distribusi':datetime.now().strftime('%Y-%m-%d')})
        self.state = 'posted'
        self.confirm_date = datetime.now()
        self.confirm_uid = self._uid
        self.date = datetime.today()        
        return True
    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Dealer Distribusi Memo sudah diproses, data tidak bisa didelete !"))
            for dist in item.distribusi_spk_ids:
                if dist.state != 'draft':
                    raise osv.except_osv(('Perhatian..!'), ("Dealer Distribusi Memo ini mengandung nomor register yang sudah diproses, data tidak bisa didelete !"))

    @api.onchange('branch_id')
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
            if s.employee_id:
                salesman.append(s.employee_id.id)
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
        return {'domain':{'sales_id':[('id','in',salesman)]}}


    @api.one
    def action_cancel(self):
        self.state = 'cancel'

    @api.one
    def action_draft(self):
        self.state = 'draft'
    
class dealer_distribusi_spk_line(models.Model):
    _name = 'dealer.distribusi.spk.line'
    _rec_name = 'dealer_register_spk_line_id'    

    distribusi_spk_id = fields.Many2one('dealer.distribusi.spk')
    dealer_register_spk_line_id = fields.Many2one('dealer.register.spk.line', string='No. Register')
    branch_id = fields.Many2one(related='distribusi_spk_id.branch_id', string='Branch', readonly=True)
    sales_id = fields.Many2one(related='distribusi_spk_id.sales_id', string='Salesman', readonly=True)
    state_distribusi = fields.Selection(related='distribusi_spk_id.state', string='Dist.State', readonly=True)
    state = fields.Selection(related='dealer_register_spk_line_id.state', string='Reg.State', readonly=True)
    tanggal_distribusi= fields.Date(related='dealer_register_spk_line_id.tanggal_distribusi', string='Tanggal Distribusi', readonly=True)
    tanggal_kembali = fields.Date(related='dealer_register_spk_line_id.tanggal_kembali', string='Tanggal Kembali', readonly=True)
    spk_id = fields.Many2one(related='dealer_register_spk_line_id.spk_id', string ='Memo', readonly=True)
    dealer_sale_order_id = fields.Many2one(related='dealer_register_spk_line_id.dealer_sale_order_id', string='Dealer Sales Memo', readonly=True)

    _sql_constraints = [
        ('unique_dealer_register_spk_line', 'unique(dealer_register_spk_line_id,distribusi_spk_id)', 'Nomor register duplicate !'),
    ]
    
    @api.multi
    def onchange_register_spk(self,branch_id):
        dom = {}
        tampung = []
        if branch_id:
            register_ids = self.env['dealer.register.spk'].search([('branch_id','=',branch_id)])
            dom['dealer_register_spk_line_id']=[('register_spk_id','in',[x['id'] for x in register_ids]),('state','=','open'),('sales_id','=',False)]
        return {'domain':dom}
    
    