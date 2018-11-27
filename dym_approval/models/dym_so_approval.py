from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import datetime
from openerp import workflow
from openerp.tools.translate import _


class dym_approval_matrixdiscount_header(models.Model):
    _name ="dym.approval.matrixdiscount.header"
    _inherit = ['mail.thread']
    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    @api.cr_uid_ids_context
    def _get_default_form(self,cr,uid,ids,context=None):
        form = self.pool.get('dym.approval.config').search(cr,uid,[
                                                       ('type','=','discount')
                                                       ]) 
        form_id = False
        if form :
            form_id =  self.pool.get('dym.approval.config').browse(cr,uid,form)
        return form_id
        
    form_id = fields.Many2one('dym.approval.config',string='Form',domain="[('type','=','discount')]", default=_get_default_form)
    branch_id = fields.Many2one('dym.branch',string='Branch', default=_get_default_branch)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division', change_default=True, select=True)
    product_template_id = fields.Many2one('product.template',string='Product Template')
    dym_approval_md_ids = fields.One2many('dym.approval.matrixdiscount','dym_approval_md_id')
    
    @api.model
    def create(self,values):
        config = self.env['dym.approval.config'].search([
                                                         ('id','=',values['form_id']),('type','=','discount'),
                                                         ])   
        for lines in values['dym_approval_md_ids']:
            lines[2].update({'product_template_id':values['product_template_id'],'branch_id':values['branch_id'],'division':values['division'],'form_id':config.form_id.id})
        
        approval = super(dym_approval_matrixdiscount_header,self).create(values)
        val = self.browse(approval)
        val.id.message_post(body=_("Approval created ")) 

        return approval
    
    @api.multi
    def write(self,values,context=None):
        approval = super(dym_approval_matrixdiscount_header,self).write(values)
        val = self.browse([self.id])
        val.message_post(body=_("Approval updated "))
        return approval
    
    @api.onchange('division')
    def category_change(self):
        dom = {}
        tampung = []
        if self.division:
            categ_ids = self.env['product.category'].get_child_ids(self.division)
            dom['product_template_id']=[('categ_id','in',categ_ids)]
        return {'domain':dom}
    
class dym_approval_matrixdiscount(models.Model):
    _name = "dym.approval.matrixdiscount"
    _description = "Approval Sales Memo"
    _order = "id asc"
    
    @api.multi
    def _check_limit(self):
        if self.limit > 0:
          return True
        return False

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    dym_approval_md_id = fields.Many2one('dym.approval.matrixdiscount.header',ondelete='cascade')
    form_id = fields.Many2one(related='dym_approval_md_id.form_id.form_id')
    branch_id = fields.Many2one(related='dym_approval_md_id.branch_id')
    division = fields.Selection(related='dym_approval_md_id.division')
    product_template_id = fields.Many2one(related='dym_approval_md_id.product_template_id')
    group_id = fields.Many2one('res.groups',string='Group')
    limit =  fields.Float(digits=(8,2), string="Limit")

    _constraints = [
      (_check_limit, 'Limit harus lebih besar dari 0!', ['limit']),
    ]
    
    _sql_constraints = [
    ('unique_approval_diskon', 'unique(group_id,dym_approval_md_id)', 'Tidak boleh ada duplicate group approval!'),
    ]
    
    
    @api.multi
    def request(self, object, object_line, subject_to_approval,product_id):
        for obj_line in object_line:
            try:
                field_test = obj_line[subject_to_approval] and obj_line[product_id]
            except:
                raise Warning(('Perhatian !'), ("Transaksi ini tidak memiliki field " + subject_to_approval + ". Cek kembali Matrix Approval."))
            self.request_by_value(object,obj_line,obj_line[subject_to_approval],obj_line.product_id)
        return True
    
    @api.multi
    def request_by_value(self,object,object_line,value,product_id):
        product_template_id = product_id.product_tmpl_id.id
        config = self.env['dym.approval.config'].search([
                                                         ('form_id','=',object.__class__.__name__),('type','=','discount')
                                                         ])
        if not config :
            raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))
        matrix = self.search([
            ('branch_id','=',object.branch_id.id),
            ('division','=',object.division),
            ('form_id','=',config.form_id.id),
            ('product_template_id','=',product_template_id)
          ])
        if not matrix:
            raise Warning(('Perhatian !'), ("Transaksi ini tidak memiliki matrix approval. Cek kembali data Cabang & Divisi"))
    
        user_limit = 0
        
        for data in matrix :
            create_approval = self.env['dym.approval.line'].create({
              'value':value,
              'group_id':data.group_id.id,
              'transaction_id':object.id,
              'product_template_id': product_template_id,
              'branch_id':data.branch_id.id,
              'division':data.division,
              'form_id':data.form_id.id,
              'limit':data.limit,
              'sts':'1',
              'approval_config_id':config.id,
            })
            
            if user_limit < data.limit:
                user_limit = data.limit
    
        if user_limit < value:
            raise Warning(('Perhatian !'), ("Nilai transaksi %d. Nilai terbersar di matrix approval: %d. Cek kembali Matrix Approval.") % (value, user_limit))
    
        return True
    
    @api.multi
    def approve(self, trx, product_id):
        user_groups = self.env['res.users'].browse(self._uid)['groups_id']
        config = self.env['dym.approval.config'].search([
                                                         ('form_id','=',trx.__class__.__name__),('type','=','discount'),
                                                         ])
        if not config :
            raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))        
        approval_lines_ids = self.env['dym.approval.line'].search([
                                                            ('branch_id','=',trx.branch_id.id),
                                                            ('division','=',trx.division),
                                                            ('form_id','=',config.form_id.id),
                                                            ('transaction_id','=',trx.id),
                                                            ('product_template_id','=',product_id.product_tmpl_id.id),
                                                          ])
        if not approval_lines_ids:
            raise Warning('Perhatian ! Transaksi ini tidak memiliki detail approval1. Cek kembali Matrix Approval.')
        approve_all = False
        user_limit = 0
        for approval_line in approval_lines_ids:
            if approval_line.sts == '1':
                if approval_line.group_id in user_groups:
                    approval_line.write({
                                  'sts':'2',
                                  'pelaksana_id':self._uid,
                                  'tanggal':datetime.today(),
                                })
                    if approval_line.limit > user_limit:
                        user_limit = approval_line.limit
                        approve_all = approval_line.value <= user_limit
	            elif approval_line.sts=='2':
            		user_limit = approval_line.limit
            		approve_all = approval_line.value <= user_limit
	    
        if user_limit:
            for approval_line in approval_lines_ids:
                if approval_line.sts == '1':
                    if approve_all:
                        approval_line.write({
                        'sts':'2',
                        'pelaksana_id':self._uid,
                        'tanggal':datetime.today(),
                      })
                    elif approval_line.limit <= user_limit:
                        approval_line.write({
                        'sts':'2',
                        'pelaksana_id':self._uid,
                        'tanggal':datetime.today(),
                      })
	
        if approve_all:
            return 1
        elif user_limit:
            return 2
	return 0
    
    @api.multi
    def reject(self, trx, reason):
        user_groups = self.env['res.users'].browse(self._uid)['groups_id']
        config = self.env['dym.approval.config'].search([
                                                         ('form_id','=',trx.__class__.__name__),('type','=','discount'),
                                                         ])
        if not config :
            raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))        
        approval_lines_ids = self.env['dym.approval.line'].search([
                                                            ('branch_id','=',trx.branch_id.id),
                                                            ('division','=',trx.division),
                                                            ('form_id','=',config.id),
                                                            ('transaction_id','=',trx.id),
                                                            ('product_template_id','=',trx.id),
                                                          ])
        if not approval_lines_ids:
            raise exceptions(('Perhatian !'), ("Transaksi ini tidak memiliki detail approval2. Cek kembali Matrix Approval."))
        
        reject_all = False
        for approval_line in approval_lines_ids:
            if approval_line.sts == '1':
                if approval_line.group_id in user_groups:
                    reject_all = True
                    approval_line.write({
                      'sts':'3',
                      'reason':reason,
                      'pelaksana_id':uid,
                      'tanggal':datetime.today(),
                    })
                    break
        if reject_all:
            for approval_line in approval_lines:
                if approval_line.sts == '1':
                    approval_line.write({
                  'sts':'3',
                  'pelaksana_id':uid,
                  'tanggal':datetime.today(),
                })
            return 1
        return 0

