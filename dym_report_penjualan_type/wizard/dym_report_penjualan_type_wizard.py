from openerp.osv import orm, fields, osv
from lxml import etree

class dym_report_penjualan_type_wizard(orm.TransientModel):
    _name = 'dym.report.penjualan.type.wizard'
    _description = 'Report Penjualan Pertype Wizard'
    
    _columns = {
        'product_ids': fields.many2many('product.product', 'dym_report_penjualan_type_product_rel', 'dym_report_penjualan_type_wizard_id',
            'product_id', 'Products'),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_penjualan_type_branch_rel', 'dym_report_penjualan_type_wizard_id',
            'branch_id', 'Branches', copy=False),
    }
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        data = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'Laporan Penjualan Pertype', 'datas': data}
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
