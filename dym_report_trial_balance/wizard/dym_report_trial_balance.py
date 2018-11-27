import time
from openerp.osv import orm, fields,osv
from openerp import api
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class report_trial_balance(orm.TransientModel):
    _name = 'dym.report.trial.balance'
    _description = 'Report Buku Besar'
 
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(report_trial_balance, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        user=self.pool.get('res.users').browse(cr,uid,uid)
        branch_ids=[b.id for b in user.branch_ids]
        company_ids=[b.id for b in user.company_ids]
        
        doc = etree.XML(res['arch'])      
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        nodes_branch = doc.xpath("//field[@name='fiscalyear_id']")
        for node in nodes_branch:
            node.set('domain', '[("company_id", "in", '+ str(company_ids)+'),("company_id.parent_id", "!=", False)]')
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'option': fields.selection([('trial_balance','Trial Balance'),('balance_sheet','Balance Sheet'),('profit_loss','Profit & Loss')], 'Option', change_default=True, select=True), 
        'konsolidasi' : fields.boolean('Konsolidasi'),
        'period_id' : fields.many2one('account.period',string='Period From', domain="[('company_id','=',company_id)]"),
        'period_to_id' : fields.many2one('account.period',string='Period To'),
        'fiscalyear_id' : fields.many2one('account.fiscalyear',string='Fiscalyear'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'status': fields.selection([('all','All Entries'),('posted','Posted')], 'Status', change_default=True, select=True), 
        'branch_ids': fields.many2many('dym.branch', 'dym_report_trial_balance_branch_rel', 'dym_report_trial_balance',
                                        'branch_id', 'Branch', copy=False),
        'account_ids': fields.many2many('account.account', 'dym_report_trial_balance_account_rel', 'dym_report_trial_balance',
                                        'account_id', 'Account', copy=False, ),
        'journal_ids': fields.many2many('account.journal', 'dym_report_trial_balance_journal_rel', 'dym_report_trial_balance',
                                        'journal_id', 'Journal', copy=False, ),                                                                            
        'segmen':fields.selection([(1,'Company'),(2,'Bisnis Unit'),(3,'Branch'),(4,'Cost Center')], 'Segmen'),
        'branch_status' : fields.selection([('H1','H1'),('H23','H23'),('H123','H123')],string='Branch Status'),
        'filters' : fields.selection([('filter_none','No Filters'),('filter_period','Periods'),('filter_date','Date')],string='Filters'),
    }

    _defaults = {
        'status':'all',
        'option':'trial_balance'
    }    
    
#     def create(self,cr,uid,vals,context=None):
#         search = []
#         if vals['period_id'] :
#             search.append(('period_id','=',vals['period_id']))
#         if vals['start_date'] :
#             search.append(('date','>=',vals['start_date']))
#         if vals['end_date'] :
#             search.append(('date_maturity','<=',vals['end_date']))
#         if vals['status'] == 'all':
#             search.append(('move_id.state','!=',False))  
#         elif vals['status'] == 'posted':
#             search.append(('move_id.state','=','posted'))                  
#         if vals['branch_ids'] :
#             for x in vals['branch_ids'] :                
#                 if x[2] :
#                     search.append(('branch_id','in',x[2]))    
#         if vals['account_ids'] :
#             for x in vals['account_ids'] :                
#                 if x[2] :
#                     search.append(('account_id','in',x[2]))                                                                                              
#         if vals['journal_ids'] :
#             for x in vals['journal_ids'] :                
#                 if x[2] :
#                     search.append(('journal_id','in',x[2]))  
#         search_move_line = self.pool.get('account.move.line').search(cr,uid,search)
#         if not search_move_line :
#             raise osv.except_osv(('No Data Available !'), ("No records found for your selection!"))            
#         
#         res = super(report_trial_balance,self).create(cr,uid,vals,context=context)
#         return res
    
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
        
        account_ids = data['account_ids']
        period_id = data['period_id']
        status = data['status']
        branch_status = data['branch_status']
        segmen = data['segmen']
        start_date = data['start_date']
        end_date = data['end_date']
        konsolidasi = data['konsolidasi']
        option = data['option']
        period_to_id = data['period_to_id']
        filters = data['filters']
        fiscalyear_id = data['fiscalyear_id']

        data.update({
            'branch_ids': branch_ids,
            'account_ids': account_ids,
            'period_id': period_id,
            'status': status,
            'branch_status': branch_status,
            'segmen': segmen,
            'start_date': start_date,
            'end_date': end_date,
            'konsolidasi': konsolidasi,
            'option': option,
            'period_to_id': period_to_id,
            'filters': filters,
            'fiscalyear_id': fiscalyear_id,
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'dym_report_trial_balance_xls',
                    'datas': data}
        else:
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_account_move.report_trial_balance',
                data=data, context=context)

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
        
        account_ids = data['account_ids']
        period_id = data['period_id']
        status = data['status']
        branch_status = data['branch_status']
        segmen = data['segmen']
        start_date = data['start_date']
        end_date = data['end_date']
        konsolidasi = data['konsolidasi']
        option = data['option']
        period_to_id = data['period_to_id']
        filters = data['filters']
        fiscalyear_id = data['fiscalyear_id']

        data.update({
            'branch_ids': branch_ids,
            'account_ids': account_ids,
            'period_id': period_id,
            'status': status,
            'branch_status': branch_status,
            'segmen': segmen,
            'start_date': start_date,
            'end_date': end_date,
            'konsolidasi': konsolidasi,
            'option': option,
            'period_to_id': period_to_id,
            'filters': filters,
            'fiscalyear_id': fiscalyear_id,
        })
        if context.get('options') in ('trial_balance','balance_sheet','profit_loss'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'dym_report_trial_balance_xls',
                    'datas': data}
            
        elif context.get('options') == 'import_sun':
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'dym_report_trial_balance_import_sun_xls',
                    'datas': data}            
        else:
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_account_move.report_trial_balance',
                data=data, context=context)
            
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context)          
    
    def konsolidasi_change(self, cr, uid, ids, konsolidasi, context=None):
        value = {}
        domain = {}
        value['fiscalyear_id'] = False
        if konsolidasi == False:
            user = self.pool.get('res.users').browse(cr,uid,uid)
            company_ids=[b.id for b in user.company_ids]
            domain['fiscalyear_id'] = [('company_id', 'in', company_ids),('company_id.parent_id', '!=', False)]
        else:
            domain['fiscalyear_id'] = [('company_id.parent_id', '=', False)]
        return {'value':value,'domain':domain}

    def period_change(self, cr, uid, ids, period_id, period_to_id, fiscalyear_id, context=None):
        value = {}
        value['start_date'] = False
        value['end_date'] = False
        if period_id and period_to_id:
            obj_period_id = self.pool.get('account.period').browse(cr, uid, period_id)
            obj_period_to_id = self.pool.get('account.period').browse(cr, uid, period_to_id)
            if obj_period_id.company_id != obj_period_to_id.company_id:
                warning = {'title':'Perhatian', 'message':'Range Period harus berasal dari company yang sama !'}
                value['period_id'] = False
                value['period_to_id'] = False
                return {'value':value, 'warning':warning}
            if obj_period_id.date_start > obj_period_to_id.date_stop :
                warning = {'title':'Perhatian', 'message':'Period To tidak boleh lebih kecil dari Period From !'}
                value['period_id'] = False
                value['period_to_id'] = False
                return {'value':value, 'warning':warning}
        return {'value':value}
    
    def onchange_filter(self, cr, uid, ids, filter, fiscalyear_id, context=None):
        value = {}
        value['start_date'] = False
        value['end_date'] = False
        value['period_id'] = False
        value['period_to_id'] = False
        return {'value':value}

    def date_change(self, cr, uid, ids, period_id, period_to_id, start_date, end_date, fiscalyear_id, context=None):
        value = {}
        Warning = {}
        obj_fiscalyear = self.pool.get('account.fiscalyear').browse(cr, uid, fiscalyear_id)
        if start_date and fiscalyear_id and start_date < obj_fiscalyear.date_start:
            warning = {'title':'Perhatian', 'message':'Start date tidak boleh diluar fiscalyear !'}
            value['start_date'] = False
            return {'value':value, 'warning':warning}
        if end_date and fiscalyear_id and end_date > obj_fiscalyear.date_stop:
            warning = {'title':'Perhatian', 'message':'End date tidak boleh diluar fiscalyear !'}
            value['end_date'] = False
            return {'value':value, 'warning':warning}
        if start_date and end_date and start_date > end_date:
            warning = {'title':'Perhatian', 'message':'End Date tidak boleh kurang dari Start Date !'}
            value['start_date'] = False
            value['end_date'] = False
            return {'value':value, 'warning':warning}
        # if period_id :
        #     obj_period_id = self.pool.get('account.period').browse(cr, uid, period_id)
        #     if start_date and (start_date < obj_period_id.date_start or start_date > obj_period_id.date_stop) :
        #         warning = {'title':'Perhatian', 'message':'Start Date dan End Date harus termasuk ke dalam Period !'}
        #         value['start_date'] = False
        #         return {'value':value, 'warning':warning}
        #     elif end_date :
        #         if not start_date :
        #             warning = {'title':'Perhatian', 'message':'Silahkan isi Start Date terlebih dahulu !'}
        #             value['end_date'] = False
        #             return {'value':value, 'warning':warning}
        #         elif end_date > obj_period_id.date_stop or end_date < obj_period_id.date_start :
        #             warning = {'title':'Perhatian', 'message':'Start Date dan End Date harus termasuk ke dalam Period !'}
        #             value['end_date'] = False
        #             return {'value':value, 'warning':warning}
            
        #     if start_date and end_date and start_date > end_date :
        #         warning = {'title':'Perhatian', 'message':'End Date tidak boleh kurang dari Start Date !'}
        #         value['start_date'] = False
        #         value['end_date'] = False
        #         return {'value':value, 'warning':warning}
        # else :
        #     value['start_date'] = False
        #     value['end_date'] = False
        return {'value':value}
    
