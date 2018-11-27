import time
from openerp.osv import orm, fields,osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree
from datetime import datetime

class report_journal(orm.TransientModel):
    _name = 'dym.report.journal'
    _rec_name = 'option'
    _description = 'Report Journal'
 
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(report_journal, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])      
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'option': fields.selection([('account','Detail per Account')], 'Option', change_default=True, select=True), 
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division', change_default=True, select=True),         
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'period_id' : fields.many2one('account.period',string='Period'),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_journal_branch_rel', 'dym_report_journal',
                                        'branch_id', 'Branch', copy=False),
        'account_ids': fields.many2many('account.account', 'dym_report_journal_account_rel', 'dym_report_journal',
                                        'account_id', 'Account', copy=False, ), 
        'journal_ids': fields.many2many('account.journal', 'dym_report_journal_journal_rel', 'dym_report_journal',
                                        'journal_id', 'Journal', copy=False, ),
        'partner_ids': fields.many2many('res.partner', 'dym_report_journal_partner_rel', 'dym_report_journal',
                                        'partner_id', 'Partner', copy=False),                                           
        'segmen':fields.selection([(1,'Company'),(2,'Bisnis Unit'),(3,'Branch'),(4,'Cost Center')], 'Segmen'),
        'branch_status' : fields.selection([('H1','H1'),('H23','H23'),('H123','H123')],string='Branch Status'),
    }

    _defaults = {
                 'start_date':fields.date.context_today,
                 'end_date':fields.date.context_today,
                 'option':'account'
                 }    
    
    def report_detail_account(self, cr, uid, ids, context=None):
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
        account_ids = data['account_ids']
        journal_ids = data['journal_ids']
        partner_ids = data['partner_ids']
        division = data['division']
        period_id = data['period_id']
        start_date = data['start_date']
        end_date = data['end_date']
        segmen = data['segmen']
        branch_status = data['branch_status']

        data.update({
            'branch_ids': branch_ids,
            'account_ids': account_ids,
            'journal_ids': journal_ids,
            'start_date': start_date,
            'end_date': end_date,
            'period_id': period_id,
            'segmen': segmen,
            'branch_status': branch_status,
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'dym_report_journal_detail_account_xls',
                    'datas': data}
        else:
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_account_move.report_journal',
                data=data, context=context)

    def xls_export(self, cr, uid, ids, context=None):
        res = True
        if context.get('options') == 'account' :
            res = self.report_detail_account(cr, uid, ids, context)
        return res
