from openerp.osv import orm, fields, osv
from lxml import etree

class dym_report_penjualandwh_wizard(orm.TransientModel):
    _name = 'dym.report.penjualandwh.wizard'
    _description = 'Report penjualandwh Wizard'
    
    _columns = {
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_penjualandwh_branch_rel', 'dym_report_penjualandwh_wizard_id',
            'branch_id', 'Branches', copy=False),
    }
    
    _defaults = {
        'options': '1',
    }
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        
        data = self.read(cr, uid, ids)[0]
        branch_ids = data['branch_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        
        data.update({
            'start_date': start_date,
            'end_date': end_date,
            'branch_ids': branch_ids,
        })
        
        # atas perintah report generate
        if context.get('xls_export') == '1' :
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan DWH New',
                    'datas': data}
        else :
            # bawah perintah report generate
            raise osv.except_osv(('Perhatian'), ('Report untuk options ini belum tersedia !'))
            context['landscape'] = True
            return self.pool['report'].get_action(cr, uid, [], 'dym_report_penjualandwh.report_penjualandwh', data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
