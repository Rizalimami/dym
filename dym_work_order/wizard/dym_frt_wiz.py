from openerp.osv import fields, osv, orm
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.tools.translate import _
from openerp import tools
import pdb

class dym_frt_price_adjust(osv.osv_memory):
    _name = "dym.frt.price.adjust"
    _description = "Adjust FRT Price"
    _columns = {
        'branch_id' : fields.many2one('dym.branch', 'Branch', required=True),
        'new_price': fields.float('New FRT Price', required=True),
        'frt_id' : fields.many2one('dym.frt', 'Flat Rate Time', required=True),
    }    
    _defaults = {
        'frt_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False
    }

    def adjust_price(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for data in self.browse(cr, uid, ids, context=context):
            if data.new_price <= 0:
                raise osv.except_osv(_('Warning!'), _('Price harus lebih dari 0.'))
            self.pool.get('dym.frt.history').create(cr, uid, {
                'frt_id': data.frt_id.id,
                'time': 0,
                'branch_id': data.branch_id.id,
                'rate': 0,
                'date': datetime.today(),
                'price': data.new_price,
            })
        return {}

    def onchange_branch_id(self, cr, uid, ids, branch_id, frt_id, context=None):
        obj_frt_history_adjust_ids = self.pool.get('dym.frt.history').search(cr,uid,[('frt_id','=',frt_id),('branch_id','=',branch_id),('price','>',0)], order="date desc, id desc", limit=1)
        obj_frt_history_adjust = self.pool.get('dym.frt.history').browse(cr, uid, obj_frt_history_adjust_ids)
        
        obj_frt_lastest_change_ids = self.pool.get('dym.frt.history').search(cr,uid,['|','&',('frt_id','=',frt_id),('time','>',0),'&',('branch_id','=',branch_id),('rate','>',0)], order="date desc, id desc", limit=1)        
        obj_frt_lastest_change = self.pool.get('dym.frt.history').browse(cr, uid, obj_frt_lastest_change_ids)

        if obj_frt_history_adjust and obj_frt_lastest_change and obj_frt_history_adjust.date >= obj_frt_lastest_change.date and obj_frt_history_adjust.id >= obj_frt_lastest_change.id:
            return { 'value': { 'new_price': obj_frt_history_adjust.price } }
            
        obj_frt = self.pool.get('dym.frt').browse(cr, uid, frt_id)
        rate = self.pool.get('dym.branch').browse(cr,uid,branch_id).rate
        harga_frt = obj_frt.time * rate
        return { 'value': { 'new_price': harga_frt } }