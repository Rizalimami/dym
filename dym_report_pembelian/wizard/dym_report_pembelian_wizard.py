from openerp.osv import orm, fields, osv
from lxml import etree

class dym_report_pembelian_wizard(orm.TransientModel):
    _name = 'dym.report.pembelian.wizard'
    _description = 'Report Pembelian Wizard'
    _rec_name = 'division'
    
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context:
            context = {}
        res = super(dym_report_pembelian_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids = self._get_branch_ids(cr, uid, context)
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division'),
        'state': fields.selection([('open','Open'), ('paid','Paid'), ('open_paid','Open and Paid')], 'State', required=True, change_default=True, select=True),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'product_ids': fields.many2many('product.product', 'dym_report_pembelian_product_rel', 'dym_report_pembelian_wizard_id',
            'product_id', 'Products'),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_pembelian_branch_rel', 'dym_report_pembelian_wizard_id',
            'branch_id', 'Branches', copy=False),
        'partner_ids': fields.many2many('res.partner', 'dym_report_pembelian_partner_rel', 'dym_report_pembelian_wizard_id',
            'partner_id', 'Suppliers', copy=False, domain=[('supplier','=',True)]),
        'segmen':fields.selection([(1,'Company'),(2,'Bisnis Unit'),(3,'Branch'),(4,'Cost Center')], 'Segmen'),
        'branch_status' : fields.selection([('H1','H1'),('H23','H23'),('H123','H123')],string='Branch Status'),
    }
    
    def division_change(self, cr, uid, ids, division, context=None):
        value = {}
        domain = {}
        value['product_ids'] = False
        obj_categ = self.pool.get('product.category')
        all_categ = obj_categ.search(cr,uid,[])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ, division)
        domain['product_ids'] = [('categ_id','in',categ_ids)]
        return {'value':value, 'domain':domain}
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        data = self.read(cr, uid, ids)[0]
        if len(data['branch_ids']) == 0 :
            data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})
        return {'type': 'ir.actions.report.xml', 'report_name': 'Laporan Pembelian', 'datas': data}
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
    