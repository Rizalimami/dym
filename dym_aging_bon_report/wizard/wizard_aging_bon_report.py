import time

import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api, models
from datetime import datetime, date

class dym_advance_patment(osv.osv):
    _inherit = 'dym.advance.payment'

    def get_settlement(self, cr, uid, ids, avp_id, context=None):
        settlement_ids = self.pool.get('dym.settlement').search(cr, uid, [('advance_payment_id','=',avp_id)])
        string = ''
        for settle in self.pool.get('dym.settlement').browse(cr, uid, settlement_ids):
            string += settle.name + ' '
        return string

    def get_aging_date(self, cr, uid, ids, register_date, context=None):
        # aging_date = int((date.today()-datetime.date(datetime.strptime(register_date, '%Y-%m-%d'))).days)
        val = self.browse(cr, uid, ids)[0]
        aging_date = self.pool.get('dym.work.days').get_date_diff(cr, uid, ids, register_date, str(date.today()), val.branch_id.id)
        return aging_date

class dym_aging_bon_report(osv.osv_memory):

    _name = 'dym.aging.bon.report'
    _description = 'Laporan Aging Bon'
    _columns = {
        'branch_id': fields.many2one('dym.branch', 'Branch', required=True),
        'user_id': fields.many2one('res.users', 'Employee'),
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division'),
        'due': fields.boolean('Due'),
        'waiting_for_approval': fields.boolean('Waiting for Approval'),
        'approved': fields.boolean('Approved'),
        'confirmed': fields.boolean('Confirmed'),
        'done': fields.boolean('Done'),
        'payment_method': fields.many2many('account.journal', 'aging_bs_journal_rel', 'aging_bs_id',
            'journal_id', 'Payment Method'),
    }        

    _defaults = {
    }


class aging_bon_report(models.AbstractModel):
    _name = 'report.dym_aging_bon_report.aging_bon_report_template'

    def render_html(self, cr, uid, ids, data=None, context=None):
        registry = openerp.registry(cr.dbname)
        branch_id = False
        user_id = False
        company = False
        division = 'Unit, Sparepart, Umum'
        state = ''
        due = 'T'
        domain = []
        bons = {}
        check_wizard = registry.get('dym.aging.bon.report').read(cr, uid, ids, context=context)
        if check_wizard:
            data_wizard = check_wizard[0]
            if data_wizard['branch_id'] != False:
                domain.append(('branch_id', '=', data_wizard['branch_id'][0]))
                branch_id = data_wizard['branch_id'][1]
                company = registry.get('dym.branch').browse(cr, uid, [data_wizard['branch_id'][0]]).company_id.name
            if data_wizard['division'] != False:
                domain.append(('division', '=', data_wizard['division']))
                division = data_wizard['division']
            if data_wizard['user_id'] != False:
                domain.append(('user_id', '=', data_wizard['user_id'][0]))
                user_id = data_wizard['user_id'][1]
            if data_wizard['payment_method']:
                domain.append(('payment_method', 'in', data_wizard['payment_method']))
            state_domain = []
            if data_wizard['due'] != False:
                domain.append(('date_due', '<', date.today()))
                due = "Y"
                state_domain = ['waiting_for_approval','approved','confirmed']
                state = 'Waiting for Approval, Approved, Confirmed'
            else:
                if data_wizard['waiting_for_approval'] != False:
                    state_domain.append('waiting_for_approval')
                if data_wizard['approved'] != False:
                    state_domain.append('approved')
                if data_wizard['confirmed'] != False:
                    state_domain.append('confirmed')
                if data_wizard['done'] != False:
                    state_domain.append('done')
                if not state_domain:
                    state_domain = ['waiting_for_approval','approved','confirmed','done']
                state = 'Waiting for Approval, Approved, Confirmed, Done'
            domain.append(('state', 'in', state_domain))
            bon_ids = registry.get('dym.advance.payment').search(cr, uid, domain, order='user_id asc, division asc, date asc', context=None)
            bons = registry.get('dym.advance.payment').browse(cr, uid, bon_ids, context=context)
            if not bons:
                raise osv.except_osv(('Perhatian !'), ("Data Aging Bon tidak ditemukan."))
        report_obj = self.pool['report']
        report = report_obj._get_report_from_name(cr, uid, 'dym_aging_bon_report.aging_bon_report_template')
        docargs = {'doc_ids': ids,'doc_model': report.model,'docs': data,
                    'bons': bons,
                    'branch_id': branch_id,
                    'company': company,
                    'division': division,
                    'state': state,
                    'user_id': user_id,
                    'due': due,
                    'branch_id': branch_id,
                    'branch_id': branch_id,
                    'branch_id': branch_id,
                    'company': company}
        return report_obj.render(cr, uid, ids, 'dym_aging_bon_report.aging_bon_report_template', docargs, context=context)