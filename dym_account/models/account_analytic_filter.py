from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools.translate import _
from openerp.addons.dym_branch.models.dym_branch import BRANCH_TYPES
from openerp.addons.dym_account.models.account import CC_SELECTION

class AnalyticAccountFilter(models.Model):
    _name = "analytic.account.filter"

    account_id = fields.Many2one('account.account', string='Account')
    branch_type = fields.Selection(BRANCH_TYPES, string='Branch Type', required=True)
    bisnis_unit = fields.Many2one('product.category', 'Bisnis Unit', domain=[('bisnis_unit','=',True)])
    cost_center = fields.Selection(CC_SELECTION, 'Cost Center')

    @api.multi
    def get_accounts(self, branch_id, division):
        res = []
        if not all([branch_id, division]):
            return res
        branch = self.env['dym.branch'].browse(branch_id)
        if division=='Sparepart':
            categories = ['Accessories','Service','Sparepart']
        elif division=='Finance':
            categories = ['Umum']
        else:
            categories = [division]

        bisnis_units = self.env['product.category'].search([('name','in',categories)])
        company = branch.company_id
        accts = []
        domain = [('branch_type','=',branch.branch_type),('bisnis_unit','in',bisnis_units.ids)]
        for fltr in self.sudo().search(domain):
            if fltr.account_id.id not in accts:
                accts.append(fltr.account_id.id)
        return accts

    @api.multi
    def get_analytics(self, branch_id, division, account_id):

        aa1_ids = aa2_ids = aa3_ids = aa4_ids = False
        df1 = df2 = df3 = df4 = False
        aa_dict = {}

        if not all([branch_id, division, account_id]):
            return (aa1_ids, aa2_ids, aa3_ids, aa4_ids, df1, df2, df3, df4, aa_dict)

        branch = self.env['dym.branch'].browse(branch_id)
        if division=='Sparepart':
            categories = ['Accessories','Service','Sparepart']
        elif division=='Finance':
            categories = ['Umum']
        else:
            categories = [division]
        bisnis_units = self.env['product.category'].search([('name','in',categories)])
        company = branch.company_id
        bu_ids = []
        ccs = []
        domain = [('account_id','=',account_id),('branch_type','=',branch.branch_type),('bisnis_unit','in',bisnis_units.ids)]
        for fltr in self.sudo().search(domain):
            if fltr.bisnis_unit.id not in bu_ids:
                bu_ids.append(fltr.bisnis_unit.id)
            if fltr.cost_center not in ccs:
                ccs.append(fltr.cost_center)

        aa_obj = self.env['account.analytic.account']

        level_1_ids = aa_obj.search([('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        level_2_ids = aa_obj.search([('segmen','=',2),('bisnis_unit','in',bu_ids),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',level_1_ids.ids)])
        level_3_ids = aa_obj.search([('segmen','=',3),('branch_id','=',branch.id),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',level_2_ids.ids)])
        level_4_ids = aa_obj.search([('segmen','=',4),('cost_center','in',ccs),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',level_3_ids.ids)])

        if level_1_ids:
            aa1_ids = level_1_ids.ids
            df1 = level_1_ids.ids[0]
        if level_2_ids:
            aa2_ids = level_2_ids.ids
            df2 = level_2_ids.ids[0]
        if level_3_ids:
            aa3_ids = level_3_ids.ids
            df3 = level_3_ids.ids[0]
        if level_4_ids:
            aa4_ids = level_4_ids.ids
            df4 = level_4_ids.ids[0]

        level_1_ids = aa_obj.search([('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        for lvl_1 in level_1_ids.ids:
            aa_dict[lvl_1] = {}
            level_2_ids = aa_obj.search([('segmen','=',2),('bisnis_unit','in',bu_ids),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',[lvl_1])])
            for lvl_2 in level_2_ids.ids:
                aa_dict[lvl_1][lvl_2] = {}
                level_3_ids = aa_obj.search([('segmen','=',3),('branch_id','=',branch.id),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',[lvl_2])])
                for lvl_3 in level_3_ids.ids:
                    level_4_ids = aa_obj.search([('segmen','=',4),('cost_center','in',ccs),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',[lvl_3])])
                    aa_dict[lvl_1][lvl_2][lvl_3] = level_4_ids.ids

        res = (aa1_ids, aa2_ids, aa3_ids, aa4_ids, df1, df2, df3, df4, aa_dict)
        return res

    @api.multi
    def get_analytics_2(self, branch_id, division, account_id):
        branch = self.env['dym.branch'].browse(branch_id)
        if division=='Sparepart':
            categories = ['Accessories','Service','Sparepart']
        elif division=='Finance':
            categories = ['Umum']
        else:
            categories = [division]
        bisnis_units = self.env['product.category'].search([('name','in',categories)])
        company = branch.company_id
        bu_ids = []
        ccs = []
        domain = [('account_id','=',account_id),('branch_type','=',branch.branch_type),('bisnis_unit','in',bisnis_units.ids)]
        for fltr in self.sudo().search(domain):
            if fltr.bisnis_unit.id not in bu_ids:
                bu_ids.append(fltr.bisnis_unit.id)
            if fltr.cost_center not in ccs:
                ccs.append(fltr.cost_center)
        aa_obj = self.env['account.analytic.account']
        level_1_ids = aa_obj.search([('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        level_2_ids = aa_obj.search([('segmen','=',2),('bisnis_unit','in',bu_ids),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',level_1_ids.ids)])
        return level_2_ids

    @api.multi
    def get_categories(self, analytic_2_code):
        if analytic_2_code=='000':
            categories = 'Umum'
        elif analytic_2_code=='100':
            categories = 'Unit'
        elif analytic_2_code=='210':
            categories = 'Service'
        elif analytic_2_code=='220':
            categories = 'Sparepart'
        elif analytic_2_code=='230':
            categories = 'ACCESSORIES'
        else:
            categories = False
        return categories

    @api.multi
    def get_analytics_3(self, branch_id, division, account_id, analytic_2_code, analytic_2):
        aa_obj = self.env['account.analytic.account']
        if not analytic_2_code:
            return (False,False)
        categories = self.get_categories(analytic_2_code)
        branch = self.env['dym.branch'].browse(branch_id)
        bisnis_units = self.env['product.category'].search([('name','=',categories)])
        bu_ids = []
        ccs = []
        domain = [('account_id','=',account_id),('branch_type','=',branch.branch_type),('bisnis_unit','in',bisnis_units.ids)]
        for fltr in self.sudo().search(domain):
            if fltr.bisnis_unit.id not in bu_ids:
                bu_ids.append(fltr.bisnis_unit.id)
            if fltr.cost_center not in ccs:
                ccs.append(fltr.cost_center)
        level_3_ids = aa_obj.search([('segmen','=',3),('branch_id','=',branch.id),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',analytic_2)])
        return level_3_ids

    @api.multi
    def get_analytics_4(self, branch_id, division, account_id, analytic_2_code, analytic_2, analytic_3):
        aa_obj = self.env['account.analytic.account']
        if not analytic_2_code and not analytic_3:
            return (False,False)
        categories = self.get_categories(analytic_2_code)
        branch = self.env['dym.branch'].browse(branch_id)
        bisnis_units = self.env['product.category'].search([('name','=',categories)])
        bu_ids = []
        ccs = []
        domain = [('account_id','=',account_id),('branch_type','=',branch.branch_type),('bisnis_unit','in',bisnis_units.ids)]
        for fltr in self.sudo().search(domain):
            if fltr.bisnis_unit.id not in bu_ids:
                bu_ids.append(fltr.bisnis_unit.id)
            if fltr.cost_center not in ccs:
                ccs.append(fltr.cost_center)
        level_3_ids = aa_obj.search([('segmen','=',3),('branch_id','=',branch.id),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',analytic_2)])
        level_4_ids = aa_obj.search([('segmen','=',4),('cost_center','in',ccs),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',level_3_ids.ids)])
        return level_4_ids
