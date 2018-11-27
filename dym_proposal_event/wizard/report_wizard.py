import time
from openerp.osv import orm, fields, osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class dym_report_proposal_event_wizard(orm.TransientModel):
    _name = 'dym.report.proposal.event.wizard'
    _description = 'Report Register Activity Wizard'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_report_proposal_event_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
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
        'branch_ids': fields.many2many('dym.branch', 'dym_report_proposal_event_branch_rel', 'dym_report_proposal_event_wizard_id', 'branch_id', 'Branch', copy=False),
    }

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
        
        data.update({
            'start_date': start_date,
            'end_date': end_date,
            'division': division,
            'branch_ids': branch_id,
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan Register Activity',
                    'datas': data}
        else :
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_proposal_event.report_proposal_event',
                data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)



class dym_report_penjualan_wizard(orm.TransientModel):
    _inherit = 'dym.report.penjualan.wizard'
    _description = 'Report Penjualan Wizard'
    
    _columns = {
        'proposal_id': fields.many2one('dym.proposal.event', 'Proposal Event'),
    }