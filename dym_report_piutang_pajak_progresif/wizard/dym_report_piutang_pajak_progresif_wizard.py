import time
from openerp.osv import orm, fields, osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree
from datetime import datetime

class AccountFilter(orm.Model):
    _inherit = "dym.account.filter"

    def _register_hook(self, cr):
        selection = self._columns['name'].selection
        if ('trade','Account Trade') not in selection:         
            self._columns['name'].selection.append(
                ('trade','Account Trade'))
        if ('non_trade', 'Account Non-Trade') not in selection:         
            self._columns['name'].selection.append(
                ('non_trade', 'Account Non-Trade'))
        return super(AccountFilter, self)._register_hook(cr)    

class dym_report_piutang_pajak_progresif_wizard(orm.TransientModel):
    _name = 'dym.report.piutang.pajak.progresif.wizard'
    _description = 'Report Piutang Pajak Progresif Wizard'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_report_piutang_pajak_progresif_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
            
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
            
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'per_tgl': fields.date('Saldo Per Tanggal'),
        'detail_pembayaran': fields.boolean('Detail Pembayaran'),
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', change_default=True, select=True),
        'trade_non_trade': fields.selection([('trade','Trade'),('non_trade','Non-Trade')], 'Trade / Non-Trade', change_default=True, select=True),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'status': fields.selection([('reconciled','Reconciled'),('outstanding','Outstanding'), ('outstanding_reconciled','Outstanding & Reconciled')], 'Status', change_default=True, select=True),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_piutang_pajak_progresif_branch_rel', 'dym_report_piutang_pajak_progresif_wizard_id',
                                        'branch_id', 'Branch', copy=False),
        'partner_ids': fields.many2many('res.partner', 'dym_report_piutang_pajak_progresif_partner_rel', 'dym_report_piutang_pajak_progresif_wizard_id',
                                        'partner_id', 'Customer', copy=False, domain=[('customer','=',True)]),
        'account_ids': fields.many2many('account.account', 'dym_report_piutang_pajak_progresif_account_rel', 'dym_report_piutang_pajak_progresif_wizard_id',
                                        'account_id', 'Account', copy=False, domain=[('type','=','receivable')]),
        'journal_ids': fields.many2many('account.journal', 'dym_report_piutang_pajak_progresif_journal_rel', 'dym_report_piutang_pajak_progresif_wizard_id',
                                        'journal_id', 'Journal', copy=False, domain=[('type','in',['sale','purchase_refund'])]), 
        'segmen':fields.selection([(1,'Company'),(2,'Bisnis Unit'),(3,'Branch'),(4,'Cost Center')], 'Segmen'),
        'branch_status' : fields.selection([('H1','H1'),('H23','H23'),('H123','H123')],string='Branch Status'),
    }
    
    _defaults = {
        'per_tgl': fields.date.context_today,
        'end_date': fields.date.context_today,
        'division': 'Unit',
        'status': 'outstanding_reconciled',
        'detail_pembayaran': True,        
        'trade_non_trade': 'trade',
    }
    
#     def create(self, cr, uid, vals, context=None):
#         search = []
#         if vals['division'] :
#             search.append(('division','=',vals['division']))
#         if vals['start_date'] :
#             search.append(('date','>=',vals['start_date']))
#         if vals['end_date'] :
#             search.append(('date','<=',vals['end_date']))
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
#                 partner_ids = self.pool.get('res.partner').search(cr, uid, [('customer','=',True)])
#                 search.append(('partner_id','in',partner_ids))
#         for x in vals['account_ids'] :
#             if x[2] :
#                 search.append(('account_id','in',x[2]))
#             else :
#                 account_ids = self.pool.get('account.account').search(cr, uid, [('type','=','receivable')])
#                 search.append(('account_id','in',account_ids))
#         for x in vals['journal_ids'] :
#             if x[2] :
#                 search.append(('journal_id','in',x[2]))
#             else :
#                 journal_ids = self.pool.get('account.journal').search(cr, uid, [('type','in',['sale','purchase_refund'])])
#                 search.append(('journal_id','in',journal_ids))
#     
#         ids_move_line = self.pool.get('account.move.line').search(cr, uid, search)
#         if not ids_move_line :
#             raise osv.except_osv(('No Data Available'),('No records found for your selection!'))            
#         res = super(dym_report_piutang_wizard, self).create(cr, uid, vals, context=context)
#         return res

    def trade_non_trade_change(self,cr,uid,ids,trade_non_trade,context=None):
        domain = {}
        value = {}
        account_domain = ['&', ('active','=',True), ('type','=','receivable')]
        if trade_non_trade:
            dict = self.pool.get('dym.account.filter').get_domain_account(cr,uid,ids,trade_non_trade,context=None)
            account_domain.extend(dict)
        domain['account_ids'] = account_domain
        value['account_ids'] = False
        return {'domain':domain,'value':value}

    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        
        data = self.read(cr, uid, ids)[0]
        branch_ids = data['branch_ids']
        if len(branch_ids) == 0 :
            branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
            branch_ids = [b.id for b in branch_ids_user]
        
        account_ids = data['account_ids']
        if len(account_ids) == 0 :
            account_domain = ['&', ('active','=',True), ('type','=','receivable')]
            if data['trade_non_trade']:
                dict = self.pool.get('dym.account.filter').get_domain_account(cr,uid,ids,data['trade_non_trade'],context=None)
                account_domain.extend(dict)
            account_ids = self.pool.get('account.account').search(cr, uid, account_domain)
            
        partner_ids = data['partner_ids']
#         if len(partner_ids) == 0 :
#             partner_ids = self.pool.get('res.partner').search(cr, uid, [('customer','=',True)])
            
        journal_ids = data['journal_ids']
#         if len(journal_ids) == 0 :
#             journal_ids = self.pool.get('account.journal').search(cr, uid, [('type','in',['sale','purchase_refund'])])
 
        division = data['division']
        start_date = data['start_date']
        end_date = data['end_date']
        status = data['status']
        segmen = data['segmen']
        branch_status = data['branch_status']
        detail_pembayaran = data['detail_pembayaran']
        per_tgl = data['per_tgl']
        
        data.update({
            'division': division,
            'start_date': start_date,
            'end_date': end_date,
            'status': status,
            'branch_ids': branch_ids,
            'partner_ids': partner_ids,
            'account_ids': account_ids,
            'journal_ids': journal_ids,
            'segmen': segmen,
            'branch_status': branch_status,
            'detail_pembayaran': detail_pembayaran,
            'per_tgl': per_tgl,
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan Piutang',
                    'datas': data}
        else :
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_report_piutang.report_piutang',
                data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
