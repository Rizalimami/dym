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

    def _report_xls_kas_besar_fields(self, cr, uid, context=None):
        return [
            'no',\
            'hari',\
            'date',\
            'saldo_awal',\
            'debit',\
            'credit',\
            'saldo_akhir',\
            'lebih_setor',\
            'kurang_setor',\
  
        ]

class report_kas_besar(orm.TransientModel):
    _name = 'dym.kas.besar'
    _description = 'Report Kas Besar'
 
    _columns = {
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_id': fields.many2one('dym.branch', 'Branch'),
        'journal_id': fields.many2one('account.journal', 'Journal', domain="[('type','in',['cash']),('branch_id','in',[False,branch_id])]"),

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
        start_date = data['start_date']
        end_date = data['end_date']
        #start_value_date = data['start_value_date']
        #end_value_date = data['end_value_date']
        branch_id = data['branch_id']

        data.update({
            'branch_id': branch_id,
            'journal_id': journal_id,
            'start_date': start_date,
            'end_date': end_date,
            #'start_value_date': start_value_date,
            #'end_value_date': end_value_date,
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'dym_report_kas_besar_xls',
                    'datas': data}
        else:
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_kas_besar.report_kas_besar',
                data=data, context=context)

    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context)