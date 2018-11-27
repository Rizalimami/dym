from openerp.osv import orm, fields, osv
from lxml import etree

class dym_report_rjualacc_wizard(orm.TransientModel):
    _name = 'dym.report.rjualacc.wizard'
    _description = 'Laporan Jual Acc'
    
    _columns = {
        'branch_ids': fields.many2many('dym.branch', 'dym_report_rjualacc_branch_rel', 'dym_report_rjualacc_wizard_id','branch_id', 'Branches', copy=False),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
    }

    _defaults = {
        'start_date':fields.date.context_today,
        'end_date':fields.date.context_today,
    }
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        data = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'Laporan Jual Acc', 'datas': data}
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)

    