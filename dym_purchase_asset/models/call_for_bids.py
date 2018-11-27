import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import date, datetime, timedelta
from lxml import etree
from openerp.osv.orm import setup_modifiers
from dateutil.relativedelta import relativedelta

class dym_purchase_requisition(osv.osv):
    _inherit = 'purchase.requisition'
    _columns = {
        'asset': fields.boolean('Asset', readonly=True, states={'draft': [('readonly', False)]}),
        'prepaid': fields.boolean('Prepaid', readonly=True, states={'draft': [('readonly', False)]}),
    }
    
    def onchange_asset_prepaid(self,cr,uid,ids,asset_prepaid,asset,prepaid,context=None):
        value = {}
    	if asset_prepaid == 'asset' and asset == True:
        	value['prepaid'] = False
    	if asset_prepaid == 'prepaid' and prepaid == True:
        	value['asset'] = False
        return {'value':value}