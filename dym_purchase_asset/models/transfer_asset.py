from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import pdb

class dym2_transfer_asset(models.Model):
    _name = "dym2.transfer.asset"
    _description = "Transfer Asset"
    
    @api.model
    def _get_default_date(self):
        return self.env['dym.branch'].get_default_date_model()
        
    @api.model
    def _get_analytic_company(self):
        company = self.pool.get('res.users').browse(self._cr, self._uid, self._uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(self._cr, self._uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    @api.model
    def _branch_dest_get(self):
        obj_branch = self.env['dym.branch'].sudo().search([('branch_type','in',['DL','MD'])], order='name')
        return [(str(branch.code),branch.name) for branch in obj_branch]

    name = fields.Char('Transfer Asset')
    state = fields.Selection([
                              ('draft','Draft'),
                              ('waiting_for_approval','Waiting For Approval'),
                              ('approved','Approved'),
                              # ('confirm','Requested'),
                              # ('open','Open'),
                              ('done','Done'),
                              ('cancel','Cancelled'),
                              ('reject','Rejected'),
                              ], 'State', default='draft')
    date = fields.Date('Date', readonly=True)
    branch_id = fields.Many2one('dym.branch', 'Branch Source', required=True)
    branch_dest_id = fields.Selection('_branch_dest_get', 'Branch Desination', required=True)

    location_id = fields.Many2one('stock.location', 'Location Source', domain="[('branch_id','!=',False),('branch_id','=',branch_id),('usage','=','internal')]")
    location_dest_id = fields.Many2one('stock.location', 'Location Desination', domain="[('branch_id','!=',False),('branch_id','=',branch_dest_id),('usage','=','internal')]")

    user_id = fields.Many2one('res.users', 'Responsible')
    description = fields.Char('Description')
    transfer_line = fields.One2many('dym2.transfer.asset.line', 'transfer_id', 'Detail Transfer')
    division = fields.Selection([('Umum','Umum')], 'Division', readonly=True, invisible=True)
    analytic_1 = fields.Many2one('account.analytic.account', string='Account Analytic Company', default=_get_analytic_company)
    analytic_2 = fields.Many2one('account.analytic.account', 'Account Analytic Bisnis Unit')
    analytic_3 = fields.Many2one('account.analytic.account', 'Account Analytic Branch')
    analytic_4 = fields.Many2one('account.analytic.account', 'Account Analytic Cost Center')
    categ_type = fields.Selection([
                              ('fixed','Fixed Asset'),
                              ('prepaid','Prepaid'),
                              ], 'Type')
    
    _defaults={
               'user_id': lambda obj, cr, uid, context:uid,
               'categ_type': lambda self, cr, uid, ctx: ctx and ctx.get('categ_type', False) or False,
               'date' : _get_default_date,
               'division' : 'Umum',
               }

    # @api.constrains('location_id','location_dest_id')
    # def _different_location(self):
    #     if self.location_id.id == self.location_dest_id.id and self.categ_type == 'fixed':
    #         raise ValidationError("Location Source dan Location Desination tidak boleh sama !")

    def create(self, cr, uid, vals, context=None):
        if not vals['transfer_line'] :
            raise osv.except_osv(('Tidak bisa disimpan !'), ("Silahkan isi detil transfer terlebih dahulu"))
        prefix = 'TA'
        if vals['categ_type'] == 'fixed':
            prefix = 'TAS'
        elif vals['categ_type'] == 'prepaid':
            prefix = 'TPR'
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], prefix, division='Umum')
        return super(dym2_transfer_asset, self).create(cr, uid, vals, context=context)

    
    @api.onchange('branch_id')
    def branch_source_change(self):
        self.location_id = False
        self.transfer_line = False

    @api.onchange('branch_dest_id')
    def branch_dest_change(self):
        self.location_dest_id = False

    @api.onchange('location_id')
    def location_source_change(self):
        self.transfer_line = False

    @api.multi
    def wkf_action_cancel(self):
        self.write({'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
        
    @api.multi
    def do_transfer_asset(self):
        for asset in self.transfer_line:
            branch_dest = self.env['dym.branch'].sudo().search([('code','=',self.branch_dest_id)], limit=1)
            # if asset.asset_id.location_id == self.location_id:
            asset.asset_id.write({
                            'location_id': self.location_dest_id.id,
                            'branch_id': branch_dest.id,
                            'asset_user': asset.asset_user.id,
                            'responsible_id': asset.responsible_id.id,
                            'analytic_2': self.analytic_2.id,
                            'analytic_3': self.analytic_3.id,
                            'analytic_4': self.analytic_4.id,
                            })
            update_vals = {
                    'location_id':self.location_dest_id.id,
                    'branch_id': branch_dest.id,
                    'asset_user': asset.asset_user.id,
                    'responsible_id': asset.responsible_id.id,
                    'analytic_2': self.analytic_2.id,
                    'analytic_3': self.analytic_3.id,
                    'analytic_4': self.analytic_4.id,
                    }
            asset.asset_id.update_asset(asset.asset_id.child_ids, update_vals)
            # else:
                # raise osv.except_osv(('Tidak bisa diproses !'), ('Lokasi asset [%s] %s ada di branch %s : %s!') % (asset.asset_id.code, asset.asset_id.name, asset.asset_id.location_id.branch_id.name, asset.asset_id.location_id.name))
        self.write({'state': 'done'})
    
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Cannot delete a Transfer Asset which is in state \'%s\'!') % (val.state))
        return super(dym2_transfer_asset, self).unlink(cr, uid, ids, context=context)

    def view_assets(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'account_asset', 'action_account_asset_asset_form'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        asset_ids = []
        obj_transfer = self.browse(cr, uid, ids, context=context)
        for asset in obj_transfer.transfer_line:
            asset_ids.append(asset.asset_id.id)
        if not asset_ids :
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan data asset untuk transaksi '%s'" % obj_transfer.name))
        action['context'] = {}
        action['domain'] = "[('id','in',[" + ','.join(map(str, asset_ids)) + "])]"
        return action

class dym2_transfer_asset_line(models.Model):
    _name = "dym2.transfer.asset.line"
    
    @api.one
    @api.depends('unit_price', 'requested_qty')
    def _compute_price(self):
        qty = self.requested_qty
        price = self.unit_price
        self.sub_total = qty * price
    
    asset_user = fields.Many2one('hr.employee', 'User PIC')
    responsible_id = fields.Many2one('hr.employee',string="Responsible")
    transfer_id = fields.Many2one('dym2.transfer.asset', 'Transfer')
    category_id = fields.Many2one('account.asset.category', 'Asset Category')
    asset_id = fields.Many2one('account.asset.asset', 'Asset', required=True)
    rel_product_id = fields.Many2one(related='asset_id.product_id', string="Product", readonly=True)
    rel_purchase_value = fields.Float(related='asset_id.purchase_value', string="Gross Value", readonly=True)
    rel_state = fields.Selection(related='asset_id.state', string="State", readonly=True)
    description = fields.Text('Description')
    rel_transfer_state = fields.Selection(related='transfer_id.state', string="State", readonly=True)
    
    _sql_constraints = [
                        ('unique_asset_id', 'unique(transfer_id,asset_id)', 'Tidak boleh ada asset yg sama dalam satu transfer')
                        ]
    
    def asset_change(self, cr, uid, ids, asset_id, category_id, location_id, location_dest_id, categ_type, branch_id, context=None):
        value = {}
        domain = {}
        warning = {}
        if not branch_id:
            return {'warning':{'title':'Perhatian !','message':'Sebelum menambah detil,\n harap isi branch terlebih dahulu'}}
        if (not location_id or not location_dest_id) and categ_type == 'fixed':
            return {'warning':{'title':'Perhatian !','message':'Sebelum menambah detil,\n harap isi location source dan destination terlebih dahulu'}}
        domain_search = [('state', 'not in', ['sold','scrap']),('branch_id', '=', branch_id)]
        if categ_type == 'fixed':
            domain_search += [('location_id', '=', location_id)]
        if category_id:
            domain_search += [('category_id', '=', category_id)]
        # else:
        #     fixed_category_ids = self.pool.get('account.asset.category').search(cr, uid, [('type','=','fixed')])
        #     domain_search += [('category_id', 'in', fixed_category_ids)]
        asset_ids = self.pool.get('account.asset.asset').search(cr, uid, domain_search)
        domain['asset_id'] = [('id','in',asset_ids)]
        if asset_id:
            obj_asset = self.pool.get('account.asset.asset').browse(cr, uid, [asset_id])
            if obj_asset.product_id.id:
                value['description'] = obj_asset.product_id.name_get().pop()[1]
            obj_transfer_line = self.search(cr, uid, [('transfer_id.state','in',('waiting_for_approval','approved')),('asset_id','=',asset_id)])
            if obj_transfer_line:
                warning = {'title':'Perhatian !','message':'Asset [' + obj_asset.code + '] ' + obj_asset.name + ' sedang di proses oleh ' + self.browse(cr, uid, obj_transfer_line[0]).transfer_id.name}
                value['asset_id'] = False
                value['description'] = False

        return {'value':value, 'domain':domain, 'warning':warning}
