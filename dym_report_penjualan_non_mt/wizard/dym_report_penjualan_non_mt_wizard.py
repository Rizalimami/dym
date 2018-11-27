from openerp.osv import orm, fields, osv
from lxml import etree

class dym_report_penjualan_non_mt_wizard(orm.TransientModel):
    _name = 'dym.report.penjualan.non.mt.wizard'
    _description = 'Report Penjualan Non MT Wizard'

    _columns = {
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_penjualan_non_mt_branch_rel', 'dym_report_penjualan_non_mt_wizard_id',
            'branch_id', 'Branches', copy=False),
    }

    
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        data = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'Laporan Penjualan Non MT', 'datas': data}
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
