from openerp.osv import orm, fields, osv
from lxml import etree

class dym_report_stock_movement_wizard(orm.TransientModel):
    _name = 'dym.report.stock.movement.wizard'
    _description = 'Report Stock Movement Wizard'
    
    def _get_ids_branch(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_report_stock_movement_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids = self._get_ids_branch(cr, uid, context)
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'options': fields.selection([('detail_movement','Detail Movement'), ('historical_movement','Historical Movement'), ('movement_summary','Movement Summary')], 'Options', required=True, change_default=True, select=True),
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division', change_default=True, select=True),
        'hutang_piutang_ksu': fields.selection([('hutang','Hutang KSU'),('piutang','Piutang KSU')], 'Hutang / Piutang KSU', change_default=True, select=True),
        'picking_type_code': fields.selection([('all','All'),('in','In'),('out','Out'),('incoming','Receipts'),('outgoing','Delivery Orders'),('internal','Internal Transfers'),('interbranch_in','Interbranch Receipts'),('interbranch_out','Interbranch Deliveries')], 'Picking Type', change_default=True, select=True),
        'date_start_date': fields.date('Start Date'),
        'date_end_date': fields.date('End Date'),
        'min_date_start_date': fields.date('Start Date'),
        'min_date_end_date': fields.date('End Date'),
        'date_done_start_date': fields.date('Start Date'),
        'date_done_end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_stock_movement_branch_rel', 'dym_report_stock_movement_wizard_id',
            'branch_id', 'Branches', copy=False),
        'categ_ids': fields.many2many('product.category', 'dym_report_stock_movement_categ_rel', 'dym_report_stock_movement_wizard_id',
            'categ_id', 'Categories', copy=False, domain=[('type','=','normal')]),
        'product_ids': fields.many2many('product.product', 'dym_report_stock_movement_product_rel', 'dym_report_stock_movement_wizard_id',
            'product_id', 'Products'),
        'partner_ids': fields.many2many('res.partner', 'dym_report_stock_movement_partner_rel', 'dym_report_stock_movement_wizard_id',
            'partner_id', 'Partners'),
    }
    
    _defaults = {
        'options': 'detail_movement',
        'division': lambda self, cr, uid, ctx: ctx and ctx.get('division', False) or False,
        'hutang_piutang_ksu': lambda self, cr, uid, ctx: ctx and ctx.get('hutang_piutang_ksu', False) or False,
    }
    
    def categ_ids_change(self, cr, uid, ids, categ_ids, context=None):
        value = {}
        domain = {}
        value['product_ids'] = False
        if categ_ids[0][2] :
            domain['product_ids'] = [('categ_id','in',categ_ids[0][2])]
        else :
            ids_all_product = self.pool.get('product.product').search(cr, uid, [])
            domain['product_ids'] = [('categ_id','in',ids_all_product)]
        return {'value':value, 'domain':domain}
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        
        data = self.read(cr, uid, ids)[0]
        ids_branch = data['branch_ids']
        if len(ids_branch) == 0 :
            ids_branch = self._get_ids_branch(cr, uid, context)
        
        ids_categ = data['categ_ids']
        if len(ids_categ) == 0 :
            if not data['hutang_piutang_ksu']:
                ids_categ = self.pool.get('product.category').search(cr, uid, [('type','=','normal')])
            else:
                ids_categ = self.pool.get('product.category').search(cr, uid, [('parent_id','child_of','Extras')])
        
        ids_product = data['product_ids']
        ids_partner = data['partner_ids']
        division = data['division']
        hutang_piutang_ksu = data['hutang_piutang_ksu']
        picking_type_code = data['picking_type_code']
        date_start_date = data['date_start_date']
        date_end_date = data['date_end_date']
        min_date_start_date = data['min_date_start_date']
        min_date_end_date = data['min_date_end_date']
        date_done_start_date = data['date_done_start_date']
        date_done_end_date = data['date_done_end_date']
        
        data.update({
            'division': division,
            'hutang_piutang_ksu': hutang_piutang_ksu,
            'picking_type_code': picking_type_code,
            'date_start_date': date_start_date,
            'date_end_date': date_end_date,
            'min_date_start_date': min_date_start_date,
            'min_date_end_date': min_date_end_date,
            'date_done_start_date': date_done_start_date,
            'date_done_end_date': date_done_end_date,
            'branch_ids': ids_branch,
            'categ_ids': ids_categ,
            'product_ids': ids_product,
            'partner_ids': ids_partner,
        })
        
        if context.get('xls_export') == 'detail_movement' :
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'Laporan Stock Movement',
                    'datas': data}
        else :
            raise osv.except_osv(('Perhatian'), ('Report untuk options ini belum tersedia !'))
            context['landscape'] = True
            return self.pool['report'].get_action(cr, uid, [], 'dym_report_stock_movement.report_stock_movement', data=data, context=context)
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
