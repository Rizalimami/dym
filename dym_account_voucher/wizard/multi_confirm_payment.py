import time

from openerp.osv import fields, osv
from openerp.tools.translate import _

class voucher_confirm(osv.osv_memory):
    _name = "voucher.confirm"
    _description = "Confirm Voucher"

    _columns = {
        'reference': fields.char('Payment Ref', required=True)
    }
    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        if context is None:
            context={}
        res = super(voucher_confirm, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        if context.get('active_model','') == 'account.voucher' and len(context['active_ids']) < 1:
            raise osv.except_osv(_('Warning!'),
            _('Please select voucher from the list view.'))
        return res

    def confirm_voucher(self, cr, uid, ids, context=None):
        voucher_obj = self.pool.get('account.voucher')
        mod_obj =self.pool.get('ir.model.data')
        if context is None:
            context = {}
        result = mod_obj._get_id(cr, uid, 'account_voucher', 'view_voucher_filter_vendor_pay')
        id = mod_obj.read(cr, uid, result, ['res_id'])

        reference = self.browse(cr, uid, ids, context=None).reference
        voucher_obj.write(cr, uid, context.get('active_ids',[]), {'reference':reference})
        for voucher in voucher_obj.browse(cr, uid, context.get('active_ids',[])):
            if voucher.type != 'payment':
                raise osv.except_osv(_('Warning!'),
                    _('Fitur multi confirm hanya bisa digunakan di supplier payment.'))
            if voucher.state != 'approved':
                raise osv.except_osv(_('Warning!'),
                    _('Status voucher %s belum di approve.')%(voucher.number))
            voucher.signal_workflow('confirm_payment')
        return {
            'domain': "[('id','in', [" + ','.join(map(str, context.get('active_ids',[]))) + "])]",
            'name': _('Supplier Payments'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.voucher',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': id['res_id']
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
