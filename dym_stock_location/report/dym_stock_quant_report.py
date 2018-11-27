from openerp.osv import fields,osv
import openerp.addons.decimal_precision as dp
from openerp import tools

class dym_product_price_branch(osv.osv):
    _inherit = "product.price.branch"

    def _compute_stock_valuation(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for ppb in self.browse(cr, uid, ids, context=context):
            res[ppb.id] = {
                'current_stock': 0.0,
                'current_valuation': 0.0,
            }
            current_stock = current_valuation = 0.0
            pph_id = self.pool.get('product.price.history').search(cr, uid, [('warehouse_id','=',ppb.warehouse_id.id),('product_id','=',ppb.product_id.id)], order="date desc,warehouse_id asc", limit=1)
            pph = self.pool.get('product.price.history').browse(cr, uid, pph_id)
            res[ppb.id]['current_stock'] = pph.new_qty
            res[ppb.id]['current_valuation'] = pph.new_qty * ppb.cost
        return res

    def _get_history(self, cr, uid, ids, context=None):
        pph = self.browse(cr, uid, ids)
        ppb_ids = self.pool.get('product.price.branch').search(cr, uid, [('warehouse_id','in',pph.mapped('warehouse_id').ids),('product_id','in',pph.mapped('product_id').ids)])
        return list(set(ppb_ids))

    _columns = {
        'current_stock': fields.function(_compute_stock_valuation, digits_compute=dp.get_precision('Account'), string='Current Stock',
            store={
                    'product.price.branch': (lambda self, cr, uid, ids, c={}: ids, ['cost','warehouse_id','product_id'], 10),
                    'product.price.history': (_get_history, ['new_qty','warehouse_id','product_id'], 10),
            },
            multi='sums', help="Current Stock"),
        'current_valuation': fields.function(_compute_stock_valuation, digits_compute=dp.get_precision('Account'), string='Current Valuation',
            store={
                    'product.price.branch': (lambda self, cr, uid, ids, c={}: ids, ['cost','warehouse_id','product_id'], 10),
                    'product.price.history': (_get_history, ['new_qty','warehouse_id','product_id'], 10),
            },
            multi='sums', help="Current Valuation"),
    }
class dym_stock_quat_report(osv.osv):
    _name = "dym.stock.quant.report"
    _description = "Product Cost Report"
    _auto = False
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False 
        return branch_ids 
    
    
    _columns = {
                
        'branch_id':fields.many2one('dym.branch', 'Branch', readonly=True),
        'product_id': fields.many2one('product.product','Product',required=True),
        'categ_id': fields.many2one('product.category','Category',required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', select=True),
        'cost': fields.float('Unit Cost'),
        'current_stock': fields.float('Current Stock'),
        'current_valuation': fields.float('Current Valuation'),
    }
    _order = 'branch_id desc'
    
    _defaults = {
        'branch_id': _get_default_branch,
    }
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'dym_stock_quant_report')
        cr.execute("""
            create or replace view dym_stock_quant_report as (
                select
                    min(s.id) as id,
                    w.branch_id, 
                    s.product_id,
                    t.categ_id,
                    s.warehouse_id,
                    s.cost,         
                    s.current_stock,
                    s.current_valuation
                from product_price_branch s
                    join stock_warehouse w on (s.warehouse_id=w.id)
                    left join product_product p on (s.product_id=p.id)
                    left join product_template t on (p.product_tmpl_id=t.id)
                    left join product_category c on (t.categ_id=c.id)
                group by
                s.id,
                w.branch_id,
                s.product_id,
                t.categ_id,
                s.warehouse_id,
                s.cost,         
                s.current_stock,
                s.current_valuation
            )
        """)             
    
    
class dym_ppb_history_report(osv.osv):
    _name = "dym.ppb.history.report"
    _description = "Product Cost History Report"
    _auto = False
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False 
        return branch_ids 
    
    
    _columns = {
        'origin' : fields.char('Source Document'),
        'branch_id':fields.many2one('dym.branch', 'Branch'),
        'product_id': fields.many2one('product.product','Product'),
        'categ_id': fields.many2one('product.product','Category'),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', select=True),
        'trans_price' : fields.float('Trans Cost Price'),
        'old_cost_price' : fields.float('Beginning Cost Price'),
        'cost': fields.float('Ending Cost Price'),
        'trans_qty' : fields.float('Trans Unit qty'),
        'stock_qty' : fields.float('Beginning qty'),
        'new_qty' : fields.float('Ending qty'),
        'date' : fields.datetime('Date'),
    }
    _order = 'date desc,warehouse_id asc'
    
    _defaults = {
        'branch_id': _get_default_branch,
    }
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'dym_ppb_history_report')
        cr.execute("""
            create or replace view dym_ppb_history_report as (
                select
                    min(s.id) as id,
                    w.branch_id, 
                    s.origin,
                    s.product_id,
                    t.categ_id,
                    s.warehouse_id,
                    s.trans_price,
                    s.old_cost_price,
                    s.cost,
                    s.trans_qty,
                    s.stock_qty,
                    s.new_qty,
                    s.date
                from product_price_history s
                    join stock_warehouse w on (s.warehouse_id=w.id)
                        left join product_product p on (s.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                                left join product_category c on (t.categ_id=c.id)
                group by
                s.id,
                w.branch_id,
                s.origin,
                s.product_id,
                t.categ_id,
                s.warehouse_id,
                s.trans_price,
                s.old_cost_price,
                s.cost,
                s.trans_qty,
                s.stock_qty,
                s.new_qty,
                s.date
            )
        """)   