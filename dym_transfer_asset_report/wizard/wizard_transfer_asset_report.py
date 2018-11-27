import time

import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api, models
from datetime import datetime, date
from lxml import etree


class dym_transfer_asset_report(osv.osv_memory):

    _name = 'dym.transfer.asset.report'
    _description = 'Laporan Transfer Asset'


    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_transfer_asset_report, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        
        doc = etree.XML(res['arch'])
        nodes_product = doc.xpath("//field[@name='asset_ids']")
        
        for node in nodes_product :
            node.set('domain', '[("categ_type", "=", "fixed")]')
        
        res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'branch_source': fields.many2one('dym.branch', 'Branch Source'),
        'branch_destination': fields.many2one('dym.branch', 'Branch Destination'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'asset_ids': fields.many2many('account.asset.asset', 'dym_transfer_asset_asset_rel', 'dym_transfer_asset_wizard_id',
            'asset_id', 'Assets'),
    }        

class abstract_transfer_asset_report(models.AbstractModel):
    _name = 'report.dym_transfer_asset_report.transfer_asset_report_template'

    def render_html(self, cr, uid, ids, data=None, context=None):
        registry = openerp.registry(cr.dbname)
        branch_source = False
        branch_destination = False
        start_date = False
        end_date = False
        domain = [('transfer_id.state','=','done')]
        domain_state = []
        transfers = {}
        check_wizard = registry.get('dym.transfer.asset.report').read(cr, uid, ids, context=context)
        if check_wizard:
            data_wizard = check_wizard[0]
            if data_wizard['branch_source'] != False:
                domain.append(('transfer_id.branch_id', '=', data_wizard['branch_source'][0]))
                branch_source = data_wizard['branch_source'][1]
            if data_wizard['branch_destination'] != False:
                domain.append(('transfer_id.branch_dest_id', '=', data_wizard['branch_destination'][0]))
                branch_destination = data_wizard['branch_destination'][1]
            if data_wizard['start_date'] != False:
                domain.append(('transfer_id.date', '>=', data_wizard['start_date']))
                start_date = data_wizard['start_date']
            if data_wizard['end_date'] != False:
                domain.append(('transfer_id.date', '<=', data_wizard['end_date']))
                end_date = data_wizard['end_date']
            if data_wizard['asset_ids']:
                domain.append(('asset_id', 'in', data_wizard['asset_ids']))
            transfer_ids = registry.get('dym.transfer.asset.line').search(cr, uid, domain, order='asset_id asc, id asc', context=None)
            transfers = registry.get('dym.transfer.asset.line').browse(cr, uid, transfer_ids, context=context)
            if not transfers:
                raise osv.except_osv(('Perhatian !'), ("Data Transfer Asset tidak ditemukan."))
        report_obj = self.pool['report']
        report = report_obj._get_report_from_name(cr, uid, 'dym_transfer_asset_report.transfer_asset_report_template')
        docargs = {'doc_ids': ids,'doc_model': report.model,'docs': data,'branch_source': branch_source,'branch_destination': branch_destination,'start_date': start_date,'end_date': end_date,'transfers': transfers}
        return report_obj.render(cr, uid, ids, 'dym_transfer_asset_report.transfer_asset_report_template', docargs, context=context)