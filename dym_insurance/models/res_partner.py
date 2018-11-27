# -*- coding: utf-8 -*-
from openerp import api, fields, models, tools, _, exceptions
from openerp.exceptions import Warning as UserError, RedirectWarning

class ResPartner(models.Model):
    _inherit = "res.partner"

    insurance_company = fields.Boolean('Insurance Company')
 