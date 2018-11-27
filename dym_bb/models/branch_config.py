# -*- coding: utf-8 -*-
import time
from datetime import datetime, date, timedelta
from dateutil import relativedelta

from openerp import api, fields, models, tools, _, exceptions
from openerp.addons.dym_base import DIVISION_SELECTION
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp.exceptions import Warning as UserError, RedirectWarning

class DymBranchConfig(models.Model):
    _inherit = "dym.branch.config"
    
    dym_bb_journal = fields.Many2one('account.journal',string="Blind Bonus Journal")
    dym_bb_income_account_unit = fields.Many2one('account.account',string="Blind Bonus Income Unit")
    dym_bb_income_account_oli = fields.Many2one('account.account',string="Blind Bonus Income Oli")
    dym_bb_income_account_part = fields.Many2one('account.account',string="Blind Bonus Income Part")

