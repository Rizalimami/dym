import time
from openerp.osv import orm, fields, osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class dym_report_clearing_bank_wizard(orm.TransientModel):
    _name = 'dym.report.clearing.bank.wizard'
    _description = 'Report Clearing Bank Wizard'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_report_clearing_bank_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
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
        'start_due_date': fields.date('Start Due Date'),
        'end_due_date': fields.date('End Due Date'),
        'state': fields.selection([('open','Open'),('cleared','Cleared'),('open_cleared','Open & Cleared')], 'Status', change_default=True, select=True),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_clearing_bank_branch_rel', 'dym_report_clearing_bank_wizard_id', 'branch_id', 'Branch', copy=False),
        'journal_ids': fields.many2many('account.journal', 'dym_report_clearing_bank_journal_rel', 'dym_report_clearing_bank_wizard_id', 'journal_id', 'Journal', copy=False),
        'account_ids': fields.many2many('account.account', 'dym_report_clearing_bank_account_rel', 'dym_report_clearing_bank_wizard_id', 'account_id', 'Account', copy=False),
        'partner_ids': fields.many2many('res.partner', 'dym_report_clearing_bank_partner_rel', 'dym_report_clearing_bank_wizard_id', 'partner_id', 'Partner', copy=False),
    }

    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        
        data = self.read(cr, uid, ids)[0]
        start_date = data['start_date']
        end_date = data['end_date']
        start_due_date = data['start_due_date']
        end_due_date = data['end_due_date']
        division = data['division']
        state = data['state']

        branch_id = data['branch_ids']
        if len(branch_id) == 0 :
            branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
            branch_id = [b.id for b in branch_id_user]
        
        journal_ids = data['journal_ids']
        account_ids = data['account_ids']
        partner_ids = data['partner_ids']
        
        data.update({
            'start_date': start_date,
            'end_date': end_date,
            'start_due_date': start_due_date,
            'end_due_date': end_due_date,
            'division': division,
            'state': state,
            'branch_ids': branch_id,
            'journal_ids': journal_ids,
            'account_ids': account_ids,
            'partner_ids': partner_ids,
        })
        
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan Clearing Bank',
                    'datas': data}
        else :
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_clearing_giro.report_clearing_bank',
                data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
