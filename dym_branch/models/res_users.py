# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp.tools.translate import _
from openerp.addons.dym_branch.models.dym_branch import BRANCH_TYPES
from lxml import etree

class res_users(models.Model):
    _inherit = 'res.users'

    branch_ids = fields.Many2many(string='Branches', related='area_id.branch_ids')
    branch_type = fields.Selection(BRANCH_TYPES, string='Default Branch Type', required=True) 
    branch_id = fields.Many2one('dym.branch',string='Default Branch')
    area_id = fields.Many2one('dym.area','Area',context={'user_preference':True},help='Area for this user.')
    dealer_id = fields.Many2one('res.partner',string='Dealer',domain="[('dealer','!=',False)]",context={'user_preference':True})
    branch_ids_show = fields.Many2many(related='area_id.branch_ids',string='Branches')
    area_id_show = fields.Many2one(related='area_id',string='Area',context={'user_preference':True},help='Area for this user.')
    dealer_id_show = fields.Many2one(related='dealer_id',string='Dealer',domain="[('dealer','!=',False)]",context={'user_preference':True})
    
    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on
        store fields. Access rights are disabled by
        default, but allowed on some specific fields defined in
        self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(res_users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.append('area_id')
        self.SELF_WRITEABLE_FIELDS.append('branch_ids')
        self.SELF_WRITEABLE_FIELDS.append('dealer_id')
        # duplicate list to avoid modifying the original reference
        self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.append('area_id')
        self.SELF_READABLE_FIELDS.append('branch_ids')
        self.SELF_READABLE_FIELDS.append('dealer_id')
        return init_res

    def get_default_branch(self, cr, uid, ids, context=None):
        user = self.browse(cr, uid, ids, context=context)
        if not user.branch_type:
            return False
        if user.branch_type != 'HO' and user.branch_id:
            return user.branch_id.id
        domain = [
            ('company_id','=',user.company_id.id),
        ]
        branch_id = False
        branch_ids = self.pool.get('dym.branch').search(cr, uid, domain, context=context)
        if branch_ids:
            branch_id = branch_ids[0]
        return branch_id

    def get_user_branches(self, cr, uid, ids, context=None):
        user = self.browse(cr, uid, ids, context=context)
        if not user.branch_type:
            return False
        if user.branch_type != 'HO' and user.branch_id:
            return user.branch_id.id
        domain = [
            ('company_id','=',user.company_id.id),
        ]
        branch_ids = self.pool.get('dym.branch').search(cr, uid, domain, context=context)
        return branch_ids

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(res_users, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        user_id = self.pool.get('res.users').browse(cr,uid,uid)
        section_obj = self.pool.get('crm.case.section').search(cr,uid,['|',
            ('user_id','=',user_id.id),
            ('member_ids','in',user_id.id)
        ])
        sec_ids=[]
        if section_obj :
            section_id = self.pool.get('crm.case.section').browse(cr,uid,section_obj)
            sec_ids=[b.id for b in section_id]  
        
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='default_section_id']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(sec_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    def create(self,cr,uid,vals,context=None):
        user_id = super(res_users, self).create(cr, uid, vals, context=context)
        user = self.browse(cr, uid, user_id, context=context)
        if not user.partner_id.email :
            user.partner_id.write({'email': user.login,'notify_email':'none'})
        return user_id            

    @api.multi
    def write(self, vals):
        if self.branch_ids and 'branch_id' in vals:
            if vals.get('branch_id') and vals.get('branch_id') not in self.branch_ids.ids:
                raise UserError(_('Default branch must be in branches'))
        return super(res_users, self).write(vals)

    # @api.onchange('area_id','branch_ids')
    # def _onchange_branch_id(self):
    #     values = {}
    #     domain = {}
    #     if self.branch_ids:
    #         domain.update({'branch_id':[('id','in',self.branch_ids.ids)]})
    #     return {'value': values, 'domain': domain}

    @api.onchange('branch_type')
    def _onchange_branch_type(self):
        values = {}
        domain = {}
        if not self.branch_type:
            self.branch_id = False
        else:
            domain.update({'branch_id':[('branch_type','=',self.branch_type)]})
            return {'value': values, 'domain': domain}
