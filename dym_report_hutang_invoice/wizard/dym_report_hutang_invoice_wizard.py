import time
from openerp.osv import orm, fields, osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class dym_report_hutang_invoice_wizard(orm.TransientModel):
    _name = 'dym.report.hutang.invoice.wizard'
    _description = 'Report Hutang Invoice Wizard'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_report_hutang_invoice_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_id = [b.id for b in branch_id_user]
            
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
            
        for node in nodes_branch:
            node.set('domain', '[("id", "=", '+ str(branch_id)+')]')
            
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division', change_default=True, select=True),
        'start_date': fields.date(' Tgl Jtp Start Date'),
        'end_date': fields.date('Tgl Jtp End Date'),
        'trx_start_date': fields.date('Trx Start Date'),
        'trx_end_date': fields.date('Trx End Date'),
        'status': fields.selection([('reconciled','Reconciled'),('outstanding','Outstanding')], 'Status', change_default=True, select=True),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_hutang_invoice_branch_rel', 'dym_report_hutang_invoice_wizard_id',
                                        'branch_id', 'Branch', copy=False),
        'partner_ids': fields.many2many('res.partner', 'dym_report_hutang_invoice_partner_rel', 'dym_report_hutang_invoice_wizard_id',
                                        'partner_id', 'Supplier', copy=False, domain=[('supplier','=',True)]),
        'account_ids': fields.many2many('account.account', 'dym_report_hutang_invoice_account_rel', 'dym_report_hutang_invoice_wizard_id',
                                        'account_id', 'Account', copy=False, domain=[('type','=','payable')]),
        'journal_ids': fields.many2many('account.journal', 'dym_report_hutang_invoice_journal_rel', 'dym_report_hutang_invoice_wizard_id',
                                        'journal_id', 'Journal', copy=False, domain=[('type','in',['purchase','sale_refund'])]),
        # 'segmen':fields.selection([(1,'Company'),(2,'Bisnis Unit'),(3,'Branch'),(4,'Cost Center')], 'Segmen'),
        # 'branch_status' : fields.selection([('H1','H1'),('H23','H23'),('H123','H123')],string='Branch Status'),

    }

#     def create(self, cr, uid, vals, context=None):
#         search = []
#         if vals['division'] :
#             search.append(('division','=',vals['division']))
#         if vals['start_date'] :
#             search.append(('date_maturity','>=',vals['start_date']))
#         if vals['end_date'] :
#             search.append(('date_maturity','<=',vals['end_date']))
#         if vals['status'] :
#             if vals['status'] == 'reconciled' :
#                 search.append(('reconcile_id','!=',False))
#             else :
#                 search.append(('reconcile_id','=',False))
#         for x in vals['branch_ids'] :
#             if x[2] :
#                 search.append(('branch_id','in',x[2]))
#             else :
#                 branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
#                 branch_ids = [b.id for b in branch_ids_user]
#                 search.append(('branch_id','in',branch_ids))
#         for x in vals['partner_ids'] :
#             if x[2] :
#                 search.append(('partner_id','in',x[2]))
#             else :
#                 partner_ids = self.pool.get('res.partner').search(cr, uid, [('supplier','=',True)])
#                 search.append(('partner_id','in',partner_ids))
#         for x in vals['account_ids'] :
#             if x[2] :
#                 search.append(('account_id','in',x[2]))
#             else :
#                 account_ids = self.pool.get('account.account').search(cr, uid, [('type','=','payable')])
#                 search.append(('account_id','in',account_ids))
#         for x in vals['journal_ids'] :
#             if x[2] :
#                 search.append(('journal_id','in',x[2]))
#             else :
#                 journal_ids = self.pool.get('account.journal').search(cr, uid, [('type','in',['purchase','sale_refund'])])
#                 search.append(('journal_id','in',journal_ids))
#     
#         ids_move_line = self.pool.get('account.move.line').search(cr, uid, search)
#         if not ids_move_line :
#             raise osv.except_osv(('No Data Available'),('No records found for your selection!'))            
#         res = super(dym_report_hutang_wizard, self).create(cr, uid, vals, context=context)
#         return res
     
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        
        data = self.read(cr, uid, ids)[0]
        branch_id = data['branch_ids']
        if len(branch_id) == 0 :
            branch_id_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
            branch_id = [b.id for b in branch_id_user]
        
        account_id = data['account_ids']
        
        # if len(partner_ids) == 0 :
        #     partner_ids = self.pool.get('res.partner').search(cr, uid, [('supplier','=',True)])
        
        journal_id = data['journal_ids']
        partner_ids = data['partner_ids']
#         if len(journal_ids) == 0 :
#             journal_ids = self.pool.get('account.journal').search(cr, uid, [('type','in',['purchase','sale_refund'])])
 
        start_date = data['start_date']
        end_date = data['end_date']
        trx_start_date = data['trx_start_date']
        trx_end_date = data['trx_end_date']
        status = data['status']
        division = data['division']
        # segmen = data['segmen']
        # branch_status = data['branch_status']
        
        data.update({
            'start_date': start_date,
            'end_date': end_date,
            'trx_start_date': trx_start_date,
            'trx_end_date': trx_end_date,
            'status': status,
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
                    'report_name': 'Laporan Hutang Invoice',
                    'datas': data}
        else :
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_report_hutang_invoice.report_hutang_invoice',
                data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
