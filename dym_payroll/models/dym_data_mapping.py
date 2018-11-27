# -*- coding: utf-8 -*-
import time
from datetime import datetime
from dateutil import relativedelta

from openerp import api, fields, models, tools, _
from openerp.addons.dym_base import DIVISION_SELECTION
import openerp.addons.decimal_precision as dp

class ResCompany(models.Model):
    _inherit = 'res.company'

    payroll_company = fields.Char('Payroll Company')

class DymBranch(models.Model):
    _inherit = 'dym.branch'

    payroll_branch = fields.Char('Payroll Branch')
