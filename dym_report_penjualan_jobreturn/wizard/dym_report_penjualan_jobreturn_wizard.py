from openerp.osv import orm, fields, osv
from lxml import etree

class dym_report_penjualan_jobreturn_wizard(orm.TransientModel):
    _name = 'dym.report.penjualan.jobreturn.wizard'
    _description = 'Report Penjualan WO Job Return Wizard'
    
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    _columns = {
        'category': fields.selection([('Sparepart','Sparepart'), ('ACCESSORIES','Aksesoris'), ('Service','Service')], 'Category', change_default=True, select=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'user_id': fields.many2one('hr.employee', 'Sales Person'),
        'product_ids': fields.many2many('product.product', 'dym_report_penjualan_wo_product_rel', 'dym_report_penjualan_wo_wizard_id','product_id', 'Products'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'state': fields.selection([('open','Outstanding'), ('done','Paid'), ('progress_done','Outstanding & Paid')], 'Customer AR State', required=True, change_default=True, select=True),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_penjualan_wo_branch_rel', 'dym_report_penjualan_wo_wizard_id','branch_id', 'Branches', copy=False),
    }
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        data = self.read(cr, uid, ids)[0]
        product_ids = data['product_ids']
        
        branch_ids = data['branch_ids']
        if len(branch_ids) == 0 :
            branch_ids = self._get_branch_ids(cr, uid, context)
        
        section_id = data['section_id'][0] if data['section_id'] != False else False
        user_id = data['user_id'][0] if data['user_id'] != False else False
        start_date = data['start_date']
        end_date = data['end_date']
        state = data['state']
        category = data['category']
        
        data.update({
            'section_id': section_id,
            'user_id': user_id,
            'product_ids': product_ids,
            'start_date': start_date,
            'end_date': end_date,
            'state': state,
            'category': category,
            'branch_ids': branch_ids,
        })
        
        if context.get('xls_export') :
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan Penjualan WO Job Return',
                    'datas': data}
        else :
            context['landscape'] = True
            return self.pool['report'].get_action(cr, uid, [], 'dym_report_penjualan_jobreturn.report_penjualan_jobreturn', data=data, context=context)
        
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
