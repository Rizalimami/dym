import time
from openerp.osv import orm, fields, osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class dym_retur_jual_wizard(orm.TransientModel):
    _name = 'dym.retur.jual.wizard'
    _description = 'Report Retur Penjualan Wizard'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_retur_jual_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_id = [b.id for b in branch_id_user]
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "=", '+ str(branch_id)+')]')
        res['arch'] = etree.tostring(doc)
        for field in res['fields']:
            if field == 'division':
                if 'menu' in context and context['menu'] == 'showroom':
                    res['fields'][field]['selection'] = [('Unit','Showroom')]
                if 'menu' in context and context['menu'] == 'workshop':
                    res['fields'][field]['selection'] = [('Sparepart','Workshop')]
        return res
    
    _columns = {
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division', change_default=True, select=True),
        'retur_type':fields.selection([('Uang','Uang'),('Barang','Barang')], 'Tipe Retur', change_default=True, select=True),
        'trx_start_date': fields.date('Trx Start Date'),
        'trx_end_date': fields.date('Trx End Date'),
        'branch_ids': fields.many2many('dym.branch', 'dym_retur_jual_wizard_branch_rel', 'dym_retur_jual_wizard_id', 'branch_id', 'Branch', copy=False),
        'customer_ids': fields.many2many('res.partner', 'dym_retur_jual_wizard_customer_rel', 'dym_retur_jual_wizard_id', 'customer_id', 'Supplier', copy=False),
        'product_ids': fields.many2many('product.product', 'dym_retur_jual_wizard_product_rel', 'dym_retur_jual_wizard_id', 'product_id', 'Product', copy=False),

    }

     
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        
        data = self.read(cr, uid, ids)[0]
        branch_id = data['branch_ids']
        if len(branch_id) == 0 :
            branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
            branch_id = [b.id for b in branch_id_user]
        
        trx_start_date = data['trx_start_date']
        trx_end_date = data['trx_end_date']
        division = data['division']
        retur_type = data['retur_type']
        product_ids = data['product_ids']
        customer_ids = data['customer_ids']
        
        data.update({
            'trx_start_date': trx_start_date,
            'trx_end_date': trx_end_date,
            'division': division,
            'branch_ids': branch_id,
            'product_ids': product_ids,
            'retur_type': retur_type,
            'customer_ids': customer_ids,

        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan Retur Penjualan',
                    'datas': data}
        else :
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_retur_jual.report_retur_penjualan',
                data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
