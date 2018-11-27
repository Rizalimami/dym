from openerp.osv import orm, fields, osv
from lxml import etree

class dym_report_penjualan_md_wizard(orm.TransientModel):
    _name = 'dym.report.penjualan.md.wizard'
    _description = 'Report Penjualan MD Wizard'
    
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def _get_categ_ids(self, cr, uid, division, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, division)
        return categ_ids
    
#     def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
#         if not context: context = {}
#         res = super(dym_report_penjualan_md_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
# #         branch_ids = self._get_branch_ids(cr, uid, context)
#         categ_ids = self._get_categ_ids(cr, uid, context)
#         
#         doc = etree.XML(res['arch'])
# #         nodes_branch = doc.xpath("//field[@name='branch_ids']")
#         nodes_product = doc.xpath("//field[@name='product_ids']")
#         
# #         for node in nodes_branch :
# #             node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
#         for node in nodes_product :
#             node.set('domain', '[("categ_id", "in", '+ str(categ_ids)+')]')
#         
#         res['arch'] = etree.tostring(doc)
#         return res
    
    _columns = {
        'options': fields.selection([('detail_per_type_warna','Detail Per Type Warna')], 'Options', required=True, change_default=True, select=True),
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division'),
        'product_ids': fields.many2many('product.product', 'dym_report_penjualan_md_product_rel', 'dym_report_penjualan_md_wizard_id',
            'product_id', 'Products'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'state': fields.selection([('progress','Outstanding'), ('done','Paid'), ('progress_done','Outstanding & Paid')], 'Customer AR State', required=True, change_default=True, select=True),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_penjualan_md_branch_rel', 'dym_report_penjualan_md_wizard_id',
            'branch_id', 'Branches', copy=False, domain=[('branch_type','=','MD')]),
        'dealer_ids': fields.many2many('res.partner', 'dym_report_penjualan_md_dealer_rel', 'dym_report_penjualan_md_wizard_id',
            'dealer_id', 'Dealer', copy=False, domain=['|',('dealer','=',True),('ahass','=',True)]),
    }
    
    _defaults = {
        'options': 'detail_per_type_warna',
    }
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        
        data = self.read(cr, uid, ids)[0]
        product_ids = data['product_ids']
        division = data['division']
        
        branch_ids = data['branch_ids']
        if len(branch_ids) == 0 :
            branch_ids = self._get_branch_ids(cr, uid, context)
        
        dealer_ids = data['dealer_ids']
        
        start_date = data['start_date']
        end_date = data['end_date']
        state = data['state']
        
        data.update({
            'product_ids': product_ids,
            'division': division,
            'start_date': start_date,
            'end_date': end_date,
            'state': state,
            'branch_ids': branch_ids,
            'dealer_ids': dealer_ids
        })
        
        if context.get('xls_export') == 'detail_per_type_warna' :
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan Penjualan MD',
                    'datas': data}
        else :
            raise osv.except_osv(('Perhatian'), ('Report untuk options ini belum tersedia !'))
            context['landscape'] = True
            return self.pool['report'].get_action(cr, uid, [], 'dym_report_penjualan_md.report_penjualan_md', data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
