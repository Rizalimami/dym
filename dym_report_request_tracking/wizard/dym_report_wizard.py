import time
from openerp.osv import orm, fields, osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class dym_report_request_tracking_wizard(orm.TransientModel):
    _name = 'dym.report.request.tracking.wizard'
    _description = 'Report User Request Tracking Wizard'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_report_request_tracking_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_id = [b.id for b in branch_id_user]
            
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
            
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_id)+')]')
            
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division', change_default=True, select=True),
        'start_date': fields.date(' Tgl Jtp Start Date'),
        'end_date': fields.date('Tgl Jtp End Date'),
        'trx_start_date': fields.date('Trx Start Date'),
        'trx_end_date': fields.date('Trx End Date'),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_request_tracking_branch_rel', 'dym_report_request_tracking_wizard_id',
                                        'branch_id', 'Branch', copy=False),
        'partner_ids': fields.many2many('res.partner', 'dym_report_request_tracking_partner_rel', 'dym_report_request_tracking_wizard_id',
                                        'partner_id', 'Customer', copy=False, domain=[('customer','=',True)]),
        'account_ids': fields.many2many('account.account', 'dym_report_request_tracking_account_rel', 'dym_report_request_tracking_wizard_id',
                                        'account_id', 'Account', copy=False, domain=[('type','=','receivable')]),
        'journal_ids': fields.many2many('account.journal', 'dym_report_request_tracking_journal_rel', 'dym_report_request_tracking_wizard_id',
                                        'journal_id', 'Journal', copy=False, domain=[('type','in',['purchase','purchase_refund'])]),
        # 'segmen':fields.selection([(1,'Company'),(2,'Bisnis Unit'),(3,'Branch'),(4,'Cost Center')], 'Segmen'),
        # 'branch_status' : fields.selection([('H1','H1'),('H23','H23'),('H123','H123')],string='Branch Status'),

    }

     
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        
        data = self.read(cr, uid, ids)[0]
        branch_id = data['branch_ids']
        if len(branch_id) == 0 :
            branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
            branch_id = [b.id for b in branch_id_user]
        
        account_id = data['account_ids']
        
#         if len(partner_ids) == 0 :
#             partner_ids = self.pool.get('res.partner').search(cr, uid, [('supplier','=',True)])
        
        journal_id = data['journal_ids']
        partner_ids = data['partner_ids']
#         if len(journal_ids) == 0 :
#             journal_ids = self.pool.get('account.journal').search(cr, uid, [('type','in',['purchase','sale_refund'])])
 
        start_date = data['start_date']
        end_date = data['end_date']
        trx_start_date = data['trx_start_date']
        trx_end_date = data['trx_end_date']
        division = data['division']
        # segmen = data['segmen']
        # branch_status = data['branch_status']

        data.update({
            'start_date': start_date,
            'end_date': end_date,
            'trx_start_date': trx_start_date,
            'trx_end_date': trx_end_date,
            'division': division,
            'branch_ids': branch_id,
            'account_ids': account_id,
            'journal_ids': journal_id,
            'partner_ids': partner_ids,
            # 'segmen': segmen,
            # 'branch_status': branch_status,

        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan User Request Tracking',
                    'datas': data}
        else :
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_report_request_tracking.report_request_tracking',
                data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
