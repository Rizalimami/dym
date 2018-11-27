from openerp import api, fields, models, SUPERUSER_ID
from openerp.osv import osv
from datetime import datetime, date, timedelta
import time
import pytz
from pytz import timezone
from openerp.tools.translate import _
import re
import logging

_logger = logging.getLogger(__name__)

class dym_branch(models.Model):
    _inherit = 'dym.branch'

    ahass_parent_id = fields.Many2one('dym.branch',string='AHASS Parent')
    ahass_children = fields.One2many('dym.branch','ahass_parent_id',string='AHASS Children')
