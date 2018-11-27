import time

from openerp.osv import fields, osv
from openerp.tools.translate import _

class invoice_merge(osv.osv_memory):
    _name = "invoice.merge"
    _description = "Invoice Merge"

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        if context is None:
            context={}
        res = super(invoice_merge, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        if context.get('active_model','') == 'account.invoice' and len(context['active_ids']) < 2:
            raise osv.except_osv(_('Warning!'),
            _('Please select multiple invoices to merge in the list view.'))
        return res

    def merge_invoices(self, cr, uid, ids, context=None):
        """
             To merge similar type of invoices.

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs
             @param context: A standard dictionary

             @return: invoice view

        """
        po_product_id_list=[];current_invoice=False
        obj_inv=self.pool.get('account.invoice')
        for inv_id in context.get('active_ids'):
            invoice=obj_inv.browse(cr,uid,inv_id)
            for line in invoice.invoice_line:
                po_list=invoice.origin.split(' ')
                for po in po_list: 
                    if current_invoice != invoice.id:
                        if str(line.product_id.id)+po in po_product_id_list:
                            raise osv.except_osv(('Perhatian !'), ("No. PO : %s \nType : %s \nWarna : %s \nTidak bisa dilakukan Merge Invoice untuk PO dan Product yang sama") % (invoice.origin,line.product_id.name,line.product_id.attribute_value_ids.name))
                        else: 
                            po_product_id_list.append(str(line.product_id.id)+po)
                            current_invoice=invoice.id
                            
        invoice_obj = self.pool.get('account.invoice')
        mod_obj =self.pool.get('ir.model.data')
        if context is None:
            context = {}
        result = mod_obj._get_id(cr, uid, 'account', 'view_account_invoice_filter')
        id = mod_obj.read(cr, uid, result, ['res_id'])

        allorders = invoice_obj.do_merge(cr, uid, context.get('active_ids',[]), context)
    
        return {
            'domain': "[('id','in', [" + ','.join(map(str, allorders.keys())) + "])]",
            'name': _('Account Invoice'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': id['res_id']
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
