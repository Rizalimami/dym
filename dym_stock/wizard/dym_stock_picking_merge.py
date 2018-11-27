import time

from openerp.osv import fields, osv
from openerp.tools.translate import _

class stock_picking_merge(osv.osv_memory):
    _name = "stock.picking.merge"
    _description = "Stock Picking Merge"

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        """
         Changes the view dynamically
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return: New arch of view.
        """
        if context is None:
            context={}
        res = super(stock_picking_merge, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        if context.get('active_model','') == 'stock.picking' and len(context['active_ids']) < 2:
            raise osv.except_osv(_('Warning!'),
            _('Please select multiple shipments to merge in the list view.'))
        return res

    def merge_shipments(self, cr, uid, ids, context=None):
        """
             To merge similar type of shipments.

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs
             @param context: A standard dictionary

             @return: stock picking view

        """
        picking_obj = self.pool.get('stock.picking')
        mod_obj =self.pool.get('ir.model.data')
        if context is None:
            context = {}
        result = mod_obj._get_id(cr, uid, 'stock', 'view_picking_internal_search')
        id = mod_obj.read(cr, uid, result, ['res_id'])

        allorders = picking_obj.do_merge(cr, uid, context.get('active_ids',[]), context)
    
        return {
            'domain': "[('id','in', [" + ','.join(map(str, allorders.keys())) + "])]",
            'name': _('Stock Picking'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': id['res_id']
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
