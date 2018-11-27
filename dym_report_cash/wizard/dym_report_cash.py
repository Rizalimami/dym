import time
from openerp.osv import orm, fields,osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree
from datetime import datetime

class report_cash(orm.TransientModel):
    _name = 'dym.report.cash'
    _rec_name = 'option'
    _description = 'Report Cash'
 
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(report_cash, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])      
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        nodes_journal_ids = doc.xpath("//field[@name='journal_ids']")
        nodes_journal = doc.xpath("//field[@name='journal_id']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        for node in nodes_journal:
            node.set('domain', '[("branch_id", "in", '+ str(branch_ids+[False])+'),("type","=","pettycash")]')  
        for node in nodes_journal_ids:
            node.set('domain', '[("branch_id", "in", '+ str(branch_ids+[False])+')]')                        
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'option': fields.selection([('Petty Cash','Petty Cash'),('All Non Petty Cash','All Non Petty Cash'),('Cash','Cash'),('Bank','Bank & Checks'),('EDC','EDC'),('Outstanding EDC','Outstanding EDC')], 'Option', change_default=True, select=True), 
        'status': fields.selection([('outstanding','Outstanding'),('reconcile','Reconciled')], 'Status', change_default=True, select=True),         
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_cash_branch_rel', 'dym_report_cash',
                                        'branch_id', 'Branch', copy=False),
        'journal_ids': fields.many2many('account.journal', 'dym_report_cash_journal_rel', 'dym_report_cash',
                                        'journal_id', 'Journal', copy=False, ),             
        'journal_id' : fields.many2one('account.journal',string="Journal",domain="[('type','=','pettycash')]")                                 
    }

    _defaults = {
        'start_date':fields.date.context_today,
        'end_date':fields.date.context_today,
        'option':'All Non Petty Cash'
    }    
    
    def print_report(self, cr, uid, ids, context=None):
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
        
        journal_ids = data['journal_ids']
        journal_id = data['journal_id']
        status = data['status']
        start_date = data['start_date']
        end_date = data['end_date']
        option = data['option']
        data.update({
            'branch_ids': branch_ids,
            'journal_ids': journal_ids,
            'start_date': start_date,
            'end_date': end_date,
            'option':option,
            'journal_id':journal_id
            
        })
        if context.get('options') in ('All Non Petty Cash','Cash','Bank','EDC'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'dym_report_cash_non_status_xls',
                    'datas': data}
        elif context.get('options') == 'Petty Cash':
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'dym_report_cash_pettycash_xls',
                    'datas': data}            
        else:
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_account_move.report_cash',
                data=data, context=context)

    def xls_export(self, cr, uid, ids, context=None):
        res = self.print_report(cr, uid, ids, context)
        return res
