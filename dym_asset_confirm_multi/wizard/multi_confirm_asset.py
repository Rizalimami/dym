import time

from openerp.osv import fields, osv
from openerp.tools.translate import _

class asset_confirm(osv.osv_memory):
    _name = "asset.confirm"
    _description = "Confirm Asset"

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        if context is None:
            context={}
        res = super(asset_confirm, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        if context.get('active_model','') == 'account.asset.asset' and len(context['active_ids']) < 1:
            raise osv.except_osv(_('Warning!'),
            _('Please select asset from the list view.'))
        return res

    def confirm_asset(self, cr, uid, ids, context=None):
        asset_obj = self.pool.get('account.asset.asset')
        mod_obj =self.pool.get('ir.model.data')
        if context is None:
            context = {}
        result = mod_obj._get_id(cr, uid, 'account_asset', 'view_account_asset_search')
        id = mod_obj.read(cr, uid, result, ['res_id'])
        asset_ids = asset_obj.search(cr, uid, [('state','=','draft'),('id','in',context.get('active_ids',[]))], context=context)
        result = asset_obj.validate(cr, uid, asset_ids, context=context)
        return {
            'domain': "[('id','in', [" + ','.join(map(str, asset_ids)) + "])]",
            'name': _('Account Assets'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.asset.asset',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': id['res_id']
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
