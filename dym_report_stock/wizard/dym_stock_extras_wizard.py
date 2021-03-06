import time
from openerp.osv import orm, fields
import logging
_logger = logging.getLogger(__name__)
from lxml import etree
from openerp.osv import fields, osv

class report_stock_extras_wizard(orm.TransientModel):
    _name = 'report.stock.extras.wizard'
    _description = 'Report Stock KSU Wizard'
 
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(report_stock_extras_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,view_id,'Extras')
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='product_ids']")
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        nodes_location = doc.xpath("//field[@name='location_ids']")
        for node in nodes:
            node.set('domain', '[("categ_id", "=", '+ str(categ_ids)+')]')
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        for node in nodes_location:
            node.set('domain', '[("branch_id", "=", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
 
        'branch_ids': fields.many2many('dym.branch', 'report_stock_extras_invoice_rel', 'report_stock_extras_wizard_id',
                                        'branch_id', 'Branch', copy=False),
        'product_ids': fields.many2many('product.product', 'report_stock_extras_product_rel', 'report_stock_extras_wizard_id',
                                        'product_id', 'Product', copy=False, ),
        'location_ids': fields.many2many('stock.location', 'report_stock_extras_location_rel', 'report_stock_extras_wizard_id',
                                        'location_id', 'Location', copy=False, domain=[('usage','=','internal')]),
        'company_id': fields.many2one('res.company', 'Company', readonly=True)
    }
    
    def create(self,cr,uid,vals,context=None):
        search = []
        search_branch = []
        if vals['branch_ids'] :
            for x in vals['branch_ids'] :                
                if x[2] :
                    search_branch.append(('branch_id','in',x[2]))
        if vals['product_ids'] :
            for x in vals['product_ids'] :                
                if x[2] :
                    search.append(('product_id','in',x[2]))    
        if vals['location_ids'] :
            for x in vals['location_ids'] :                
                if x[2] :
                    search.append(('location_id','in',x[2]))
        
        
        
        if search_branch :
            search_branch_branch = self.pool.get('stock.location').search(cr,uid,search_branch)
            browse_branch=self.pool.get('stock.location').browse(cr,uid,search_branch_branch,)
            branch_ids_list=[b.id for b in browse_branch]
            search.append(('location_id','in',branch_ids_list))                                                                                           
        search_lot = self.pool.get('stock.quant').search(cr,uid,search)
        
        
        if not search_lot :
            raise osv.except_osv(('No Data Available !'), ("No records found for your selection!"))            
        res = super(report_stock_extras_wizard,self).create(cr,uid,vals,context=context)
        return res 
   
    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        data = self.read(cr, uid, ids)[0]
        branch_ids = data['branch_ids']
        cek=len(branch_ids)
        
        if cek == 0 :
            branch_ids=[b.id for b in branch_ids_user]
        else :
            branch_ids=data['branch_ids']


        product_ids = data['product_ids']
        location_ids = data['location_ids']

        data.update({
            'branch_ids': branch_ids,
            'product_ids': product_ids,
            'location_ids': location_ids,
        })
       
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'dym.stock.extras.report.xls',
                    'datas': data}
        else:
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_stock.report_stock_extras',
                data=data, context=context)

    def xls_export_extras(self, cr, uid, ids, context=None):
        
        return self.print_report(cr, uid, ids, context=context)
