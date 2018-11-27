# -*- coding: utf-8 -*-
import time
from datetime import datetime
from dateutil import relativedelta

from openerp import api, fields, models, tools, _
from openerp.addons.dym_base import DIVISION_SELECTION
import openerp.addons.decimal_precision as dp

class AccountAccount(models.Model):
    _inherit = 'account.account'

    account_default_partner_ids = fields.One2many('account.account.partner','account_id', string='Default Account Partner')


class AccountAccountPartner(models.Model):
    _name = 'account.account.partner'

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, default=_get_default_branch)
    account_id = fields.Many2one('account.account', string='Account')
    partner_id = fields.Many2one('res.partner', string='Partner')
    city = fields.Char(related='partner_id.city', string='City')
    state_id = fields.Many2one('res.country.state', string='Province', related='partner_id.state_id')