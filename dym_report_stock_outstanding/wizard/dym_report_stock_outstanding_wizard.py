from openerp.osv import orm, fields, osv
from lxml import etree

class dym_report_stock_outstanding_wizard(orm.TransientModel):
    _name = 'dym.report.stock.outstanding.wizard'
    _description = 'Report Stock Outstanding Wizard'
    
    def _get_ids_branch(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_report_stock_outstanding_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids = self._get_ids_branch(cr, uid, context)
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division', change_default=True, select=True),
        'date_start_date': fields.date('Start Date'),
        'date_end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_stock_outstanding_branch_rel', 'dym_report_stock_outstanding_wizard_id',
            'branch_id', 'Branches', copy=False),
        'product_ids': fields.many2many('product.product', 'dym_report_stock_outstanding_product_rel', 'dym_report_stock_outstanding_wizard_id',
            'product_id', 'Products'),
    }
    
    _defaults = {
        'division': lambda self, cr, uid, ctx: ctx and ctx.get('division', False) or False,
    }


    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        
        data = self.read(cr, uid, ids)[0]
        branch_ids = data['branch_ids']
        if len(branch_ids) == 0 :
            branch_ids = self._get_ids_branch(cr, uid, context)
        product_ids = data['product_ids']
        division = data['division']
        date_start_date = data['date_start_date']
        date_end_date = data['date_end_date']
        
        data.update({
            'division': division,
            'date_start_date': date_start_date,
            'date_end_date': date_end_date,
            'branch_ids': branch_ids,
            'product_ids': product_ids,
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan Stock Outstanding',
                    'datas': data}
        else :
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_report_stock_outstanding.report_stock_outstanding',
                data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
