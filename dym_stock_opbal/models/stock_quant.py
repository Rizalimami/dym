from openerp.osv import osv, fields
from openerp.tools.float_utils import float_round as round

class stock_quant(osv.osv):
    _inherit = "stock.quant"
        
    def _prepare_account_move_line(self, cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=None):
        move_date = fields.date.context_today(self, cr, uid, context=context)
        stock_inventory = context.get('inventory',False)
        if stock_inventory:
            move_date = stock_inventory.date

        res = super(stock_quant,self)._prepare_account_move_line(cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=context)
        if not res:
            return res
        for n,r in enumerate(res):
            data = res[n][2]
            if not data.get('date',False):
                continue
            res[n][2]['date'] = move_date
            res[n][2]['date_maturity'] = move_date
        return res


    def _create_account_move_line(self, cr, uid, quants, move, credit_account_id, debit_account_id, journal_id, context=None):
        move_date = fields.date.context_today(self, cr, uid, context=context)
        stock_inventory = context.get('inventory',False)
        if stock_inventory:
            move_date = stock_inventory.date

        #group quants by cost
        quant_cost_qty = {}
        for quant in quants:
            if quant_cost_qty.get(quant.cost):
                quant_cost_qty[quant.cost] += quant.qty
            else:
                quant_cost_qty[quant.cost] = quant.qty
        move_obj = self.pool.get('account.move')
        for cost, qty in quant_cost_qty.items():
            move_lines = self._prepare_account_move_line(cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=context)
            period_id = context.get('force_period', self.pool.get('account.period').find(cr, uid, context=context)[0])
            move_obj.create(cr, uid, {'journal_id': journal_id,
                                      'line_id': move_lines,
                                      'period_id': period_id,
                                      'date': move_date,
                                      'ref': move.picking_id.name,
                                      'transaction_id': move.picking_id.id if move.picking_id else move.inventory_id.id if move.inventory_id else 0,
                                      'model': move.picking_id.__class__.__name__ if move.picking_id else move.inventory_id.__class__.__name__ if move.inventory_id else ''}, context=context)


