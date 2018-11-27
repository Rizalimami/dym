import time
from datetime import datetime
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools.translate import _

class dym_branch_config(models.Model):
    _name = "dym.branch.config"

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and user_browse.branch_ids[0].id or False                
        # branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    @api.one
    def _get_account_analytic_company(self):
        company = self.env['res.users'].browse(self._uid).company_id
        analytic_company = self.env['account.analytic.account'].search([('type','=','normal'),('segmen','=',1),('company_id','=',company.id), ('state','not in',('close','cancelled'))], limit=1, order='code asc')
        if not analytic_company:
            raise Warning("Tidak ditemukan account analytic untuk company " + str(company.name) + "!")
        self.analytic_company = analytic_company.id
    
    name = fields.Char(string="Name",readonly=True)
    branch_id = fields.Many2one('dym.branch',string="Branch", default=_get_default_branch)
    company_id = fields.Many2one(related="branch_id.company_id",string="Company")
    analytic_company = fields.Many2one("account.analytic.account" ,string="Company", compute="_get_account_analytic_company")
    analytic_id = fields.Many2one("account.analytic.account",string="Account Analytic Branch")

    _sql_constraints = [
    ('unique_name', 'unique(name)', 'Data Branch sudah ada. Mohon cek kembali !')]
    
    @api.model
    def create(self,vals):
        if 'branch_id' in vals and vals['branch_id'] not in ('',False):
            branch = self.env['dym.branch'].search([('id','=',vals['branch_id'])])
            vals['name'] = branch.code
        return super(dym_branch_config, self).create(vals)

    def write(self, cr, uid, ids, vals, context=None):
        if 'branch_id' in vals and vals['branch_id'] not in ('',False):
            branch = self.pool.get('dym.branch').search(cr, uid, [('id','=',vals['branch_id'])])
            vals['name'] = self.pool.get('dym.branch').browse(cr, uid, branch).code
        return super(dym_branch_config, self).write(cr, uid, ids, vals, context=context)


    def copy(self, cr, uid, id, default=None, context=None):
        default = dict(context or {})
        default.update(
            branch_id=_(False),
            name=_(""))
        return super(dym_branch_config, self).copy(cr, uid, id, default, context=context)
