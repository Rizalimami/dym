import time
from openerp.osv import orm, fields, osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class dym_report_monitoring_wizard(orm.TransientModel):
    _name = 'dym.report.purchase.order.wizard'
    _description = 'Report Monitoring Wizard'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_report_monitoring_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_id = [b.id for b in branch_id_user]
            
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "=", '+ str(branch_id)+')]')            
            
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'detail_tipe': fields.boolean('Track Produk'),
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division', change_default=True, select=True),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_monitoring_branch_rel', 'dym_report_monitoring_wizard_id', 'branch_id', 'Branch', copy=False),
        'start_date_pr': fields.date('PR Start Date'),
        'end_date_pr': fields.date('PR End Date'),
        'pr_ids': fields.many2many('purchase.requisition', 'dym_report_monitoring_pr_rel', 'dym_report_monitoring_wizard_id', 'pr_id', 'Purchase Request', copy=False, domain="[('division','=',division)]"),
        'start_date_po': fields.date('PO Start Date'),
        'end_date_po': fields.date('PO End Date'),
        'po_ids': fields.many2many('purchase.order', 'dym_report_monitoring_po_rel', 'dym_report_monitoring_wizard_id', 'po_id', 'Purchase Order', copy=False, domain="[('division','=',division)]"),
    }

    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        
        data = self.read(cr, uid, ids)[0]
        
        division = data['division']
        detail_tipe = data['detail_tipe']

        branch_ids = data['branch_ids']
        if len(branch_ids) == 0 :
            branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
            branch_ids = [b.id for b in branch_id_user]
        
        start_date_pr = data['start_date_pr']
        end_date_pr = data['end_date_pr']
        pr_ids = data['pr_ids']

        start_date_po = data['start_date_po']
        end_date_po = data['end_date_po']
        po_ids = data['po_ids']

        
        data.update({
            'division': division,
            'branch_ids': branch_ids,
            'start_date_pr': start_date_pr,
            'end_date_pr': end_date_pr,
            'pr_ids': pr_ids,
            'start_date_po': start_date_po,
            'end_date_po': end_date_po,
            'po_ids': po_ids,
            'detail_tipe': detail_tipe,
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan Monitoring',
                    'datas': data}
        else :
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_report_monitoring.report_monitoring',
                data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
