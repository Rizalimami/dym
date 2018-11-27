import time

import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api, models
from datetime import datetime, date

class dealer_distribusi_spk_line(osv.osv):
    _inherit = 'dealer.distribusi.spk.line'

    def get_aging_date(self, cr, uid, ids, register_date, context=None):
        # aging_date = int((date.today()-datetime.date(datetime.strptime(register_date, '%Y-%m-%d'))).days)
        val = self.browse(cr, uid, ids)[0]
        aging_date = self.pool.get('dym.work.days').get_date_diff(cr, uid, ids, register_date, str(date.today()), val.distribusi_spk_id.branch_id.id)
        return aging_date

class dym_aging_spk_report(osv.osv_memory):

    _name = 'dym.aging.spk.report'
    _description = 'Laporan Aging Memo'
    _columns = {
        'branch_id': fields.many2one('dym.branch', 'Branch', required=True),
        'sales_id': fields.many2one('hr.employee', 'Salesman'),
        # 'date': fields.date('Date'),
    }        

    _defaults = {
        # 'date':datetime.today()
    }


class aging_spk_report(models.AbstractModel):
    _name = 'report.dym_aging_spk_report.aging_spk_report_template'

    def render_html(self, cr, uid, ids, data=None, context=None):
        registry = openerp.registry(cr.dbname)
        branch_id = False
        sales_id = False
        # date = False
        domain = [('state', '=', 'posted')]
        distributions = {}
        check_wizard = registry.get('dym.aging.spk.report').read(cr, uid, ids, context=context)
        if check_wizard:
            data_wizard = check_wizard[0]
            if data_wizard['branch_id'] != False:
                domain.append(('branch_id', '=', data_wizard['branch_id'][0]))
                branch_id = data_wizard['branch_id'][1]
            if data_wizard['sales_id'] != False:
                domain.append(('sales_id', '=', data_wizard['sales_id'][0]))
                sales_id = data_wizard['sales_id'][1]
            # if data_wizard['date'] != False:
                # domain.append(('date', '<=', data_wizard['date']))
                # date = data_wizard['date']
            distribution_ids = registry.get('dealer.distribusi.spk').search(cr, uid, domain, order='sales_id asc, date asc', context=None)
            distributions = registry.get('dealer.distribusi.spk').browse(cr, uid, distribution_ids, context=context)
            if not distributions:
                raise osv.except_osv(('Perhatian !'), ("Data Aging Memo tidak ditemukan."))
        report_obj = self.pool['report']
        report = report_obj._get_report_from_name(cr, uid, 'dym_aging_spk_report.aging_spk_report_template')
        docargs = {'doc_ids': ids,'doc_model': report.model,'docs': data,'distributions': distributions,'branch_id': branch_id,'sales_id': sales_id}
        return report_obj.render(cr, uid, ids, 'dym_aging_spk_report.aging_spk_report_template', docargs, context=context)