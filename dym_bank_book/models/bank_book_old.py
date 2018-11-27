from openerp import models, fields, api, _, SUPERUSER_ID
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp.osv import orm, fields, osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class dym_account_move_line(models.Model):
    _inherit = 'account.move.line'

    def _report_xls_bank_book_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_name',\
            'date',\
            'value_date',\
            'partner_name',\
            'finance_company',\
            'account_code2',\
            'account_name2',\
            'name',\
            'giro',\
            'ref',\
            'debit',\
            'credit',\
            'analytic_combination',\
            'analytic_1',\
            'analytic_2',\
            'analytic_3',\
            'analytic_4',\
        ]

class report_bank_book(orm.TransientModel):
    _name = 'dym.bank.book'
    _description = 'Report Bank Book'
 
    _columns = {
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'start_value_date': fields.date('Start Value Date'),
        'end_value_date': fields.date('End Value Date'),
        'branch_id': fields.many2one('dym.branch', 'Branch'),
        'journal_id': fields.many2one('account.journal', 'Journal', domain="[('type','in',['bank','cash','pettycash']),('branch_id','in',[False,branch_id])]"),
    }


    def branch_id_onchange(self,cr,uid,ids,branch_id,context=None):
        dom={}
        val = {}
        # edi_doc_list = ['&', ('active','=',True), ('type','!=','view')]
        # dict=self.pool.get('dym.account.filter').get_domain_account(cr,uid,ids,'other_receivable_header',context=None)
        # edi_doc_list.extend(dict)      
        # dom['account_id'] = edi_doc_list
        # if branch_id :
        #     branch_search = self.pool.get('dym.branch').browse(cr,uid,branch_id)
        #     branch_config = self.pool.get('dym.branch.config').search(cr,uid,[
        #         ('branch_id','=',branch_id)
        #     ])
        #     if not branch_config :
        #         raise osv.except_osv(('Perhatian !'), ("Belum ada branch config atas branch %s !")%(branch_search.code))
        #     else :
        #         branch_config_browse = self.pool.get('dym.branch.config').browse(cr,uid,branch_config)
        #         journal_other_receivable =  branch_config_browse.dym_other_receivable_account_id.id
        #         if not journal_other_receivable :
        #             raise osv.except_osv(('Perhatian !'), ("Journal Payment Request belum diisi dalam branch %s !")%(branch_search.code))
        #         val['journal_id'] = journal_other_receivable

        #     analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch_search, 'Umum',False, 4, 'General')
        #     val['analytic_1'] = analytic_1
        #     val['analytic_2'] = analytic_2
        #     val['analytic_3'] = analytic_3
        #     val['analytic_4'] = analytic_4
        return {'domain':dom,'value': val} 
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        journal_id = data['journal_id']
        start_date = data['start_date']
        end_date = data['end_date']
        start_value_date = data['start_value_date']
        end_value_date = data['end_value_date']
        branch_id = data['branch_id']

        data.update({
            'branch_id': branch_id,
            'journal_id': journal_id,
            'start_date': start_date,
            'end_date': end_date,
            'start_value_date': start_value_date,
            'end_value_date': end_value_date,
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'dym_report_bank_book_xls',
                    'datas': data}
        else:
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_bank_book.report_bank_book',
                data=data, context=context)

    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context)