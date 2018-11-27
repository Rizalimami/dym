from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import re
import openerp.addons.decimal_precision as dp
from dateutil import rrule
from datetime import datetime, date, timedelta
from dateutil.relativedelta import *
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class dym_work_days(models.Model):
    _name = "dym.work.days"
    _description = "Work Days"

    name = fields.Char('Name', required=True)

    branch_ids = fields.Many2many('dym.branch','dym_work_days_branch_rel','work_days_id','branch_id','Branchs')
    start_date = fields.Date('Starting at', required=True)
    stop_date = fields.Date('Ending at', required=True)


    @api.multi
    def get_date_diff(self, start_date, stop_date, branch_id):
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(stop_date, '%Y-%m-%d')
        delta = timedelta(days=1)
        day = start
        diff = 0
        weekend = [6]
        while day <= end:
            domain = [('start_date','<=',day),('stop_date','>=',day)]
            if branch_id:
                domain += ['|',('branch_ids','in',branch_id),('branch_ids','=',False)]
            else:
                domain += [('branch_ids','=',False)]
            search_holiday = self.search(domain)
            if day.weekday() not in weekend and not search_holiday:
                diff += 1
            day += delta
        return diff