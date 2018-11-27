from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import datetime
from openerp import workflow
from openerp.tools.translate import _
from openerp import SUPERUSER_ID

class dym_approval_discount_line(models.Model):
    _name= "dym.approval.line"
    
    @api.one
    @api.depends('form_id','transaction_id')
    def _get_transaction_no(self):
        try:
            if self.form_id.model == 'account.voucher' :
                self.transaction_no = self.env[self.form_id.model].browse(self.transaction_id).sudo().number
            else :
                self.transaction_no = self.env[self.form_id.model].browse(self.transaction_id).sudo().name
        except:
            self.transaction_no = ''
        
    @api.one
    def _get_groups(self):
        x = self.env['res.users'].browse(self._uid)['groups_id']
        self.is_mygroup = self.group_id in x 
    
    @api.multi
    def _cek_groups(self,operator,value):
        group_ids = self.env['res.users'].browse(self._uid)['groups_id']
        if operator == '=' and value :
            where = [('group_id', 'in', [x.id for x in group_ids])]
        else :
            where = [('group_id', 'not in', [x.id for x in group_ids])]
        return where
    
    @api.multi
    def _cek_no_trans(self,operator,value):
        ids = []
        try:
            groups = self.env['res.users'].browse(self._uid)['groups_id']
            line_ids = self.search([('group_id', 'in', groups.ids),('sts', '=', 1)])
            for line in line_ids:
                if line.form_id.model == 'account.voucher' :
                    transaction_no = self.env[line.form_id.model].browse(line.transaction_id).sudo().number
                else :
                    transaction_no = self.env[line.form_id.model].browse(line.transaction_id).sudo().name
                if value.upper() in transaction_no.upper():
                    ids.append(line.id)
            where = [('id', 'in', ids)]
            return where
        except:
            where = [('id', 'in', ids)]
            return where
    

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    @api.one
    def _get_partner(self):
        self.partner_id = False
        trans = self.env[self.form_id.model].browse(self.transaction_id)
        if 'partner_id' in trans:
            self.partner_id = trans.sudo().partner_id.id
        elif 'customer_id' in trans:
            self.partner_id = trans.sudo().customer_id.id
        elif 'supplier_id' in trans:
            self.partner_id = trans.sudo().supplier_id.id
        elif 'user_id' in trans:
            self.partner_id = trans.sudo().user_id.id

    @api.multi
    def _cek_partner(self,operator,value):
        ids = []
        try:
            groups = self.env['res.users'].browse(self._uid)['groups_id']
            line_ids = self.search([('group_id', 'in', groups.ids),('sts', '=', 1)])
            for line in line_ids:
                approval_id = False
                trans = self.env[line.form_id.model].browse(line.transaction_id)
                if 'partner_id' in trans and (value.upper() in trans.sudo().partner_id.name.upper() or value.upper() in trans.sudo().partner_id.default_code.upper()):
                    approval_id = line.id
                elif 'customer_id' in trans and (value.upper() in trans.sudo().customer_id.name.upper() or value.upper() in trans.sudo().customer_id.default_code.upper()):
                    approval_id = line.id
                elif 'supplier_id' in trans and (value.upper() in trans.sudo().supplier_id.name.upper() or value.upper() in trans.sudo().supplier_id.default_code.upper()):
                    approval_id = line.id
                elif 'user_id' in trans and (value.upper() in trans.sudo().user_id.name.upper() or value.upper() in trans.sudo().user_id.default_code.upper()):
                    approval_id = line.id
                if approval_id:
                    ids.append(approval_id)
            where = [('id', 'in', ids)]
            return where
        except:
            where = [('id', 'in', ids)]
            return where

    transaction_id = fields.Integer('Transaction ID')
    value = fields.Float('Value',digits=(12,2))
    form_id = fields.Many2one('ir.model','Form')
    group_id = fields.Many2one('res.groups','Group', select=True)
    branch_id = fields.Many2one('dym.branch','Branch',select=True, default=_get_default_branch)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', change_default=True, select=True)
    limit = fields.Float('Limit', digits=(12,2))
    sts = fields.Selection([('1','Belum Approve'),('2','Approved'),('3','Revised'),('4','Cancelled')],'Status')
    pelaksana_id = fields.Many2one('res.users','Pelaksana', size=128)
    tanggal = fields.Datetime('Tanggal Approve')
    product_template_id = fields.Many2one('product.template',string='Product Template')
    reason = fields.Text('Reason')
    transaction_no = fields.Char(compute='_get_transaction_no', string="Transaction No", method=True, search='_cek_no_trans')
    is_mygroup = fields.Boolean(compute='_get_groups', string="is_mygroup", method=True, search='_cek_groups')
    view_name = fields.Char('View Name')
    approval_config_id = fields.Many2one('dym.approval.config', 'Form')
    partner_id = fields.Many2one('res.partner', 'Partner', compute='_get_partner', search='_cek_partner')
    
    @api.constrains('branch_id','sts','pelaksana_id')
    def _constraint_move_line(self):
        user = self.env['res.users'].browse(self._uid)
        if user.company_id != self.branch_id.company_id:
            raise Warning(('Perhatian !'), ("Branch Company %s tidak sama dengan user company %s! sesuaikan user company preference terlebih dahulu") % (self.branch_id.company_id.name, user.company_id.name))

    @api.multi
    def dym_get_transaction(self):  
        if self.view_name == False :
            values = {
                'name': self.form_id.name,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': self.form_id.model,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'res_id': self.transaction_id
            }
            if self.form_id.name=='Work Order':
                obj_ir_view_search = self.env["ir.ui.view"].search([("name", "=", 'work.order.form1'), ("model", "=", 'dym.work.order'),])
                if obj_ir_view_search:
                    values['view_id'] = obj_ir_view_search.id
            return values  
        else :
            obj_ir_view = self.env["ir.ui.view"]
            obj_ir_view_browse= obj_ir_view.search([("name", "=", self.view_name), ("model", "=", self.form_id.model)])
            return {
                'name': self.form_id.name,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': self.form_id.model,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'res_id': self.transaction_id,
                'view_id':obj_ir_view_browse.id
            }
