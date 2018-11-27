from openerp import tools
from openerp.osv import osv,fields
from datetime import date
from datetime import datetime
import time

class holiday_year(osv.osv):
    _name = "hr.holiday.year"
    _order = "date_start"
    
    def get_month(self, cr, uid, ids, field_names, arg, context=None):
        result={}
        for holiday in self.browse(cr,uid,ids):
            date = datetime.strptime(holiday.date_start, "%Y-%m-%d")
            result[holiday.id] = date.strftime("%m %b")
        return result
    
    def get_year(self, cr, uid, ids, field_names, arg, context=None):
        result={}
        for holiday in self.browse(cr,uid,ids):
            date = datetime.strptime(holiday.date_start, "%Y-%m-%d")
            result[holiday.id] = date.strftime("%Y")
        return result
    
    _columns    = {
        'name'       : fields.char('Holiday Name', size=128, required=True),
        'date_start' : fields.date('Date Start', required=True),
        'date_stop'  : fields.date('Date Stop', required=True),
        'month'      : fields.function(get_month, type="char", string='Month', size=250,
            store = {
                'hr.holiday.year': (lambda self, cr, uid, ids, c={}: ids, ['date_start','date_stop'], 10),
            },),
        'year'       : fields.function(get_year, type="char", string='Year', size=250,
            store = {
                'hr.holiday.year': (lambda self, cr, uid, ids, c={}: ids, ['date_start','date_stop'], 10),
            },),
        'note'       : fields.text('Description'),
        'delay'      : fields.integer('Duration'),
    }
