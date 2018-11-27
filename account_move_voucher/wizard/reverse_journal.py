import time

from openerp.osv import fields, osv
from openerp.tools.translate import _

class reverse_journal(osv.osv_memory):
    _name = "reverse.journal"
    _description = "Reverse Entries"

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        if context is None:
            context={}
        res = super(reverse_journal, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        if context.get('active_model','') == 'account.move' and len(context['active_ids']) < 1:
            raise osv.except_osv(_('Warning!'),
            _('Please select entries from the list view.'))
        return res

    def reverse(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('account.move')
        if context is None:
            context = {}
        tree_view = move_obj.action_reverse_journal(cr, uid, context.get('active_ids',[]))
        return tree_view


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
