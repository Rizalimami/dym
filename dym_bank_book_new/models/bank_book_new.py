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

class dym_account_move_line_new(models.Model):
    _inherit = 'account.move.line'

    def _report_xls_bank_book_new_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_name',\
            'date',\
            # 'value_date',\
            'partner_code', \
            'partner_name', \
            'cabang', \
            'finance_company',\
            'account_code2',\
            'account_name2',\
            'name',\
            'jurnal_item',\
            'giro',\
            'ref', \
            'kas_bon', \
            'debit',\
            'credit',\
            'cur_balance',\
            'analytic_combination',\
            'analytic_1',\
            'analytic_2',\
            'analytic_3',\
            'analytic_4',\
            'state',\
			'btr_type',\
            'source_of_fund',\
        ]

class report_bank_book_new(orm.TransientModel):
    _name = 'dym.bank.book.new'
    _description = 'Report Bank Book New'
 
    _columns = {
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'start_value_date': fields.date('Start Value Date'),
        'end_value_date': fields.date('End Value Date'),
        'branch_id': fields.many2one('dym.branch', 'Branch'),
        'journal_id': fields.many2one('account.journal', 'Journal', domain="[('type','in',['bank','cash','pettycash']),('branch_id','in',[False,branch_id])]"),
        'projection': fields.boolean(string='Projection'),
    }

    def branch_id_onchange(self,cr,uid,ids,branch_id,context=None):
        dom={}
        val = {}
        return {'domain':dom,'value': val} 

    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        journal_id = data['journal_id']
        # start_date = data['start_date']
        # end_date = data['end_date']
        start_value_date = data['start_value_date']
        end_value_date = data['end_value_date']
        branch_id = data['branch_id']

        data.update({
            'branch_id': branch_id,
            'journal_id': journal_id,
            # 'start_date': start_value_date,
            # 'end_date': end_value_date,
            'start_value_date': start_value_date,
            'end_value_date': end_value_date,
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'dym_report_bank_book_new_xls',
                    'datas': data}
        else:
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_bank_book_new.report_bank_book_new',
                data=data, context=context)

    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context)