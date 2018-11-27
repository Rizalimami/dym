import time
from openerp.osv import orm, fields, osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class dym_report_lost_order_wizard(orm.TransientModel):
    _name = 'dym.report.lost.order.wizard'
    _description = 'Report Lost Order Wizard'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_report_lost_order_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_id = [b.id for b in branch_id_user]
            
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
            
        for node in nodes_branch:
            node.set('domain', '[("id", "=", '+ str(branch_id)+')]')
            
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division', change_default=True, select=True),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_lost_order_branch_rel', 'dym_report_lost_order_wizard_id',
                                        'branch_id', 'Branch', copy=False),
        'product_ids': fields.many2many('product.product', 'dym_report_lost_order_product_rel', 'dym_report_lost_order_wizard_id',
                                        'product_id', 'Product', copy=False),

    }

     
    def _get_categ_ids(self, cr, uid, categ_name, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, categ_name)
        return categ_ids

    def onchange_division(self, cr, uid, ids, division, context=None):
        value = {}
        domain = {}
        warning = {}
        value['product_ids'] = False
        domain['product_ids'] = [('id','=',0)]
        if division:
            categ_ids = self._get_categ_ids(cr, uid, division, context)
            domain['product_ids'] = [('categ_id','in',categ_ids)]
        return  {'value':value, 'domain':domain, 'warning':warning}

    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        
        data = self.read(cr, uid, ids)[0]
        
        start_date = data['start_date']
        end_date = data['end_date']
        division = data['division']

        branch_id = data['branch_ids']
        if len(branch_id) == 0 :
            branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
            branch_id = [b.id for b in branch_id_user]
        
        # product_id = data['product_ids']
        # if len(product_id) == 0 :
        #     categ_ids = self._get_categ_ids(cr, uid, division, context)
        #     product_ids = self.pool.get('product.product').search(cr, uid, [('categ_id','in',categ_ids)], order='name asc')
        
        data.update({
            'start_date': start_date,
            'end_date': end_date,
            'division': division,
            'branch_ids': branch_id,
            # 'product_ids': product_ids,

        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan Lost Order',
                    'datas': data}
        else :
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_report_lost_order.report_lost_order',
                data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
