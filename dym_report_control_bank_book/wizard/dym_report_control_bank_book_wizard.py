from openerp.osv import orm, fields, osv
from lxml import etree

class dym_report_control_bank_book_wizard(orm.TransientModel):
    _name = 'dym.report.control.bank.book.wizard'
    _description = 'Report Kontrol Kas dan Bank Wizard'

    def _get_period(self, cr, uid, context=None):
        ctx = dict(context or {})
        period_ids = self.pool.get('account.period').find(cr, uid, context=ctx)
        return period_ids[0]

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'period_id': fields.many2one('account.period', 'Period', required=True),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_control_bank_book_branch_rel', 'dym_report_control_bank_book_wizard_id',
            'branch_id', 'Branches', copy=False),
    }

    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'period_id': _get_period,
    }
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        data = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'Laporan Kontrol Kas dan Bank', 'datas': data}
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
