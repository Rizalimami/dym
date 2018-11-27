from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from lxml import etree

class AccountFilter(models.Model):
    _inherit = "dym.account.filter"

    def _register_hook(self, cr):
        selection = self._columns['name'].selection
        key = ('settlement_advance_payment','Settlement Advance Payment')
        if key not in selection: 
            self._columns['name'].selection.append(key)
        return super(AccountFilter, self)._register_hook(cr)  
