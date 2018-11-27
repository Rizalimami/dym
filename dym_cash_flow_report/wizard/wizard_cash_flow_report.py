import time

import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api, models
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from lxml import etree

class dym_cash_flow_report(osv.osv_memory):

    _name = 'dym.cash.flow.report'
    _description = 'Laporan Cash Flow'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_cash_flow_report, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
            
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
            
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'per_tgl': fields.date('Per Tanggal', readonly=True),
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division', change_default=True, select=True),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'status': fields.selection([('reconciled','Review'),('outstanding','Forecast')], 'Status', change_default=True, select=True, required=True),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_cash_flow_branch_rel', 'dym_report_cash_flow_wizard_id',
                                        'branch_id', 'Branch', copy=False),
        'partner_ids': fields.many2many('res.partner', 'dym_report_cash_flow_partner_rel', 'dym_report_cash_flow_wizard_id',
                                        'partner_id', 'Customer', copy=False),
        'account_ids': fields.many2many('account.account', 'dym_report_cash_flow_account_rel', 'dym_report_cash_flow_wizard_id',
                                        'account_id', 'Account', copy=False, domain=[('type','in',['receivable','payable'])]),
        'bank_ids': fields.many2many('account.account', 'dym_report_cash_flow_bank_rel', 'dym_report_cash_flow_wizard_id',
                                        'account_id', 'Account', copy=False, domain=[('user_type.code','in',['bank','cash'])]),
        'journal_ids': fields.many2many('account.journal', 'dym_report_cash_flow_journal_rel', 'dym_report_cash_flow_wizard_id',
                                        'journal_id', 'Journal', copy=False, domain=[('type','in',['sale','purchase_refund','purchase','sale_refund'])]),
    }
    
    _defaults = {
        'per_tgl': fields.date.context_today,
        'end_date': fields.date.context_today,
        'status': 'outstanding',
    }
     
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}

        data = self.read(cr, uid, ids)[0]
        branch_ids = data['branch_ids']
        if len(branch_ids) == 0 :
            branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
            branch_ids = [b.id for b in branch_ids_user]
        
        bank_ids = data['bank_ids']
        if len(bank_ids) == 0 :
            bank_ids = self.pool.get('account.account').search(cr, uid, [('user_type.code','in',['bank','cash'])])

        account_ids = data['account_ids']
        if len(account_ids) == 0 :
            account_ids = self.pool.get('account.account').search(cr, uid, [('type','in',['receivable','payable'])])
            

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
        
        data.update({
            'division': division,
            'start_date': start_date,
            'end_date': end_date,
            'status': status,
            'branch_ids': branch_ids,
            'partner_ids': partner_ids,
            'bank_ids': bank_ids,
            'account_ids': account_ids,
            'journal_ids': journal_ids,
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                        'report_name': 'Laporan Cash Flow',
                        'datas': data}
        else :
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_cash_flow_report.report_cash_flow',
                data=data, context=context)

    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)

#     def _get_branch_ids(self, cr, uid, context=None):
#         branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
#         branch_ids = [b.id for b in branch_ids_user]
#         return branch_ids
    
#     def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
#         if not context:
#             context = {}
#         res = super(dym_cash_flow_report, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
#         branch_ids = self._get_branch_ids(cr, uid, context)
#         doc = etree.XML(res['arch'])
#         nodes_branch = doc.xpath("//field[@name='branch_ids']")
#         for node in nodes_branch :
#             node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
#         res['arch'] = etree.tostring(doc)
#         return res

#     _columns = {
#         'branch_ids': fields.many2many('dym.branch', 'dym_report_cash_flow_branch_rel', 'dym_report_cash_flow_wizard_id',
#             'branch_id', 'Branches', copy=False),
#         'division':fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=True),
#         'period':fields.selection([('minggu','1 Minggu'),('bulan','1 Bulan')], 'Period', required=True),
#     }        

# class cash_flow_report(models.AbstractModel):
#     _name = 'report.dym_cash_flow_report.cash_flow_report_template'

#     def get_balance(self, cr, uid, ids, date_query, date_query_params, context=None):
#         mapping = {
#             'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
#             'debit': "COALESCE(SUM(l.debit), 0) as debit",
#             'credit': "COALESCE(SUM(l.credit), 0) as credit",
#             'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
#         }
#         children_and_consolidated = self.pool.get('account.account')._get_children_and_consol(cr, uid, ids, context=context)
#         accounts = {}
#         res = {}
#         if children_and_consolidated:
#             aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)

#             wheres = [""]
#             if date_query.strip():
#                 wheres.append(date_query.strip())
#             if aml_query.strip():
#                 wheres.append(aml_query.strip())
#             filters = " AND ".join(wheres)
#             request = ("SELECT l.account_id as id, " +\
#                        ', '.join(mapping.values()) +
#                        " FROM account_move_line l" \
#                        " WHERE l.account_id IN %s " \
#                             + filters +
#                        " GROUP BY l.account_id")
#             params = (tuple(children_and_consolidated),) + date_query_params
#             cr.execute(request, params)

#             for row in cr.dictfetchall():
#                 accounts[row['id']] = row

#             children_and_consolidated.reverse()
#             brs = list(self.pool.get('account.account').browse(cr, uid, children_and_consolidated, context=context))
#             sums = {}
#             currency_obj = self.pool.get('res.currency')
#             while brs:
#                 current = brs.pop(0)
#                 if accounts.get(current.id, {}).get('balance', 0.0) != 0:
#                     sums[current] = accounts.get(current.id, {}).get('balance', 0.0)
#                     for child in current.child_id:
#                         if child.company_id.currency_id.id == current.company_id.currency_id.id:
#                             sums[current] += sums[child]
#                         else:
#                             sums[current] += currency_obj.compute(cr, uid, child.company_id.currency_id.id, current.company_id.currency_id.id, sums[child], context=context)
#                     if current.currency_id and current.exchange_rate and \
#                                 ('adjusted_balance' in ['balance'] or 'unrealized_gain_loss' in ['balance']):
#                         adj_bal = sums[current].get('foreign_balance', 0.0) / current.exchange_rate
#                         sums[current].update({'adjusted_balance': adj_bal, 'unrealized_gain_loss': adj_bal - sums[current].get('balance', 0.0)})
#         return sums

#     def render_html(self, cr, uid, ids, data=None, context=None):
#         registry = openerp.registry(cr.dbname)
#         branch = ''
#         division = ''
#         next_date = False
#         period = ''
#         domain = ['|','&',('debit','>',0),('account_id.type','=','receivable'),'&',('credit','>',0),('account_id.type','=','payable'),('date_maturity','!=',False),('reconcile_id','=',False)]
#         ar = {}
#         ap = {}
#         check_wizard = registry.get('dym.cash.flow.report').read(cr, uid, ids, context=context)
#         if check_wizard:
#             data_wizard = check_wizard[0]
#             if data_wizard['period'] == 'minggu':
#                 next_date = date.today() + timedelta(days=7)
#             elif data_wizard['period'] == 'bulan':
#                 next_date = date.today() + relativedelta(months=1)
#             domain += [('date_maturity','>=', date.today()),('date_maturity','<=', next_date)]

#             if data_wizard['division'] != False:
#                 domain.append(('division','=',data_wizard['division']))
#                 division = data_wizard['division']

#             if data_wizard['branch_ids']:
#                 branch_ids = data_wizard['branch_ids']
#             else:
#                 branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
#                 branch_ids = [b.id for b in branch_ids_user]
#             domain.append(('branch_id', 'in', branch_ids))
#             for branch_obj in self.pool.get('dym.branch').browse(cr, uid, branch_ids):
#                 branch += '[' + branch_obj.code + ']' + branch_obj.name + ', '
#             if branch != '':
#                 branch = branch[:-2]
#             move_ids = registry.get('account.move.line').search(cr, uid, domain, order=" account_id asc, date_maturity asc, id asc", context=None)
#             moves_brw = registry.get('account.move.line').browse(cr, uid, move_ids, context=context)
#             if not moves_brw:
#                 raise osv.except_osv(('Perhatian !'), ("Data Cash Flow tidak ditemukan."))
#             # ar_ids = []
#             # ap_ids = []
#             trans = {}
#             for move in moves_brw:
#                 key = move.date_maturity
#                 if key not in trans:
#                     per_account = {}
#                     per_account['ar'] = {}
#                     per_account['ap'] = {}
#                     trans[key] = per_account
#                 if move.account_id.type == 'receivable':
#                     if move.account_id not in trans[key]['ar']:
#                         trans[key]['ar'][move.account_id] = move.debit
#                     else:
#                         trans[key]['ar'][move.account_id] += move.debit
#                 elif move.account_id.type == 'payable':
#                     if move.account_id not in trans[key]['ap']:
#                         trans[key]['ap'][move.account_id] = move.credit
#                     else:
#                         trans[key]['ap'][move.account_id] += move.credit
#             # ar = self.get_balance(cr, uid, ar_ids, 'date_maturity >= %s and date_maturity <= %s', (date.today().strftime('%Y-%m-%d'), next_date.strftime('%Y-%m-%d')))
#             # ap = self.get_balance(cr, uid, ap_ids, 'date_maturity >= %s and date_maturity <= %s', (date.today().strftime('%Y-%m-%d'), next_date.strftime('%Y-%m-%d')))
#         report_obj = self.pool['report']
#         report = report_obj._get_report_from_name(cr, uid, 'dym_cash_flow_report.cash_flow_report_template')
#         docargs = {'doc_ids': ids,'doc_model': report.model,'docs': data,
#                     'branch': branch,
#                     'division': division,
#                     'date': date.today().strftime('%Y-%m-%d'),
#                     'next_date': next_date.strftime('%Y-%m-%d'),
#                     'period': data_wizard['period'],
#                     'trans': trans}
#         pdb.set_trace()
#         return report_obj.render(cr, uid, ids, 'dym_cash_flow_report.cash_flow_report_template', docargs, context=context)