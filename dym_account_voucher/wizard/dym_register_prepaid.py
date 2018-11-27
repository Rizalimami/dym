from openerp.osv import fields, osv, orm
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.tools.translate import _
from openerp import tools
from lxml import etree

class dym_register_prepaid(osv.osv_memory):
    _name = "dym.register.prepaid"
    _description = "Register Prepaid"

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_register_prepaid, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company_id),('type','=','normal'),('state','not in',('close','cancelled'))])
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='analytic_2']")
        for node in nodes_branch :
            node.set('domain', "[('segmen','=',2),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',"+str(level_1_ids)+")]")
        res['arch'] = etree.tostring(doc)
        return res
        
    _columns = {
        'name': fields.char('Prepaid Name', required=True),
        'branch_id' : fields.many2one('dym.branch', 'Branch', required=True),
        'category_id': fields.many2one('account.asset.category', 'Prepaid Category', domain="[('type','=','prepaid')]", required=True),
        'purchase_value': fields.float('Total', required=True, readonly=True),
        'purchase_date' : fields.date(string="Purchase Date", required=True),
        'payment_request_id' : fields.many2one('account.voucher', 'Voucher', required=True),
        'analytic_2' : fields.many2one('account.analytic.account', 'Account Analytic Bisnis Unit'),
        'analytic_3' : fields.many2one('account.analytic.account', 'Account Analytic Branch'),
        'analytic_4' : fields.many2one('account.analytic.account', 'Account Analytic Cost Center'),
    }    
    _defaults = {
        'payment_request_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False,
        'purchase_date': fields.date.context_today,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("You may only process one payment at a time!"))
        res = super(dym_register_prepaid, self).default_get(cr, uid, fields, context=context)
        payment_id = context and context.get('active_id', False) or False
        payment = self.pool.get('account.voucher').browse(cr, uid, payment_id, context=context)

        purchase_value = payment.amount
        branch_id = payment.branch_id.id

        if 'purchase_value' in fields:
            res.update({'purchase_value': purchase_value})
        if 'branch_id' in fields:
            res.update({'branch_id': branch_id})
        return res

    def register(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for data in self.browse(cr, uid, ids, context=context):
            prepaid_id = self.pool.get('account.asset.asset').create(cr, uid, {
                'payment_request_id': data.payment_request_id.id,
                'name': data.name,
                'branch_id': data.branch_id.id,
                'category_id': data.category_id.id,
                'purchase_date': data.purchase_date,
                'purchase_value': data.purchase_value,
                'analytic_2': data.analytic_2.id,
                'analytic_3': data.analytic_3.id,
                'analytic_4': data.analytic_4.id,
            })
            self.pool.get('account.voucher').write(cr, uid, [data.payment_request_id.id],{'prepaid_id':prepaid_id})

        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'dym_purchase_asset', 'action_account_asset_asset_form_prepaid')

        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'dym_purchase_asset', 'view_account_asset_asset_form_prepaid')
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = prepaid_id
        return result