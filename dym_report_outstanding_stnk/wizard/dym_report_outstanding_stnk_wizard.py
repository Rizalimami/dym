import time
from openerp.osv import orm, fields, osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class dym_report_outstanding_stnk_wizard(orm.TransientModel):
    _name = 'dym.report.outstanding.stnk.wizard'
    _description = 'Report Outstanding STNK Wizard'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_report_outstanding_stnk_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_id = [b.id for b in branch_id_user]
            
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
            
        for node in nodes_branch:
            node.set('domain', '[("id", "=", '+ str(branch_id)+')]')
            
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'trx_start_date': fields.date('Trx Start Date'),
        'trx_end_date': fields.date('Trx End Date'),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_outstanding_stnk_branch_rel', 'dym_report_outstanding_stnk_wizard_id',
                                        'branch_id', 'Branch', copy=False),
        'partner_ids': fields.many2many('res.partner', 'dym_report_outstanding_stnk_partner_rel', 'dym_report_outstanding_stnk_wizard_id', 'partner_id', 'Birojasa', copy=False, domain=[('biro_jasa','=',True)]),

    }
     
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        
        data = self.read(cr, uid, ids)[0]
        branch_id = data['branch_ids']
        if len(branch_id) == 0 :
            branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
            branch_id = [b.id for b in branch_id_user]
        
        partner_ids = data['partner_ids']
 
        trx_start_date = data['trx_start_date']
        trx_end_date = data['trx_end_date']
        
        data.update({
            'trx_start_date': trx_start_date,
            'trx_end_date': trx_end_date,
            'branch_ids': branch_id,
            'partner_ids': partner_ids,

        })

        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan Outstanding STNK',
                    'datas': data}
        else :
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_report_outstanding_stnk.report_outstanding_stnk',
                data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
