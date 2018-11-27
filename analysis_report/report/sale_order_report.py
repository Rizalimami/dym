from openerp.osv import fields,osv
from openerp import tools

class sale_order_report(osv.osv):
    _name = "sale.order.report"
    _description = "Sale Order Report"
    _auto = False

    def _get_branches(self, cr, uid, ids, name, args, context, where =''):
        branch_ids = self.pool.get('res.users').browse(cr, uid, uid).branch_ids.ids
        result = {}
        for val in self.browse(cr, uid, ids):
            result[val.id] = True if val.branch_id.id in branch_ids else False
        return result

    def _cek_branches(self, cr, uid, obj, name, args, context):
        branch_ids = self.pool.get('res.users').browse(cr, uid, uid).branch_ids.ids
        return [('branch_id', 'in', branch_ids)]
        
    _columns = {
        'is_mybranch': fields.function(_get_branches, string='Is My Branches', type='boolean', fnct_search=_cek_branches),
        'date_order': fields.datetime('Order Date', readonly=True, help="Date on which this document has been created"),  # TDE FIXME master: rename into date_order
        'state': fields.selection([('draft', 'Draft'),
                                     ('waiting_for_approval', 'Waiting For Approval'),
                                      ('approved', 'Approved'),
                                      ('confirmed', 'Confirmed'),
                                      ('finished', 'Finished'),
                                      ('open', 'Open'),
                                      ('except_picking', 'Shipping Exception'),
                                      ('except_invoice', 'Invoice Exception'),
                                      ('done', 'Done'),
                                      ('cancel', 'Cancelled')],'State', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'partner_id':fields.many2one('res.partner','Customer'),
        'type':fields.selection([('KPB','KPB'),('REG','Regular'),('WAR','Job Return'),('CLA','Claim'),('SLS','Part Sales')],'Type', change_default=True, select=True, readonly=True, required=True),
        # 'kpb_ke':fields.selection([('1','1'),('2','2'),('3','3'),('4','4')],'KPB Ke',change_default=True,select=True),
#         'price_average': fields.float('Average Price', readonly=True, group_operator="avg"),
        'quantity': fields.integer('Service/Sparepart Quantity', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'user_id':fields.many2one('res.users', 'Responsible', readonly=True),
        'branch_id':fields.many2one('dym.branch','Branch',required=True),
        'categ_id':fields.selection([('Sparepart','Workshop'),('Service','Service')],'Category',required=True),
        'employee_id':fields.many2one('hr.employee', 'Mekanik', readonly=True),
        # 'sa_id':fields.many2one('hr.employee', 'Sales Advisor', readonly=True),
        'so_name':fields.char('Sales Order'),
        # 'lot_id':fields.many2one('stock.production.lot', 'Nomor Mesin', readonly=True),
        # 'categ_id_2':fields.char('Category 2'),
        'category_prod':fields.char('Category Product'),
        'category_product_id': fields.many2one('dym.category.product', 'Category Service Unit'),
        'product_unit_id': fields.many2one('product.product', 'Product Unit'),
        # 'total_unit_entry': fields.integer('Total Unit Entry', readonly=True),
        # 'no_pol':fields.char('No Polisi',size=12,select=True),
    }
    _order = 'date_order desc ,price_total desc'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'sale_order_report')
        cr.execute("""
            create or replace view sale_order_report as (
                select
                    min(l.id) as id,
                    l.date_order,
                    l.state,
                    s.product_id,
                    l.partner_id,
                    l.tipe_transaksi,
                    l.create_uid as user_id,
                    sum(s.product_uom_qty) as quantity ,
                    sum(s.price_unit*s.product_uom_qty-s.discount-s.discount_program) as price_total,
                    --sum(s.count_wo) as total_unit_entry,
                    l.branch_id,
                    s.categ_id,
                    --l.mekanik_id,
                    --l.lot_id,
                    l.employee_id,
                    c.name as category_prod,
                    s.product_id as product_unit_id,
                    l.name as so_name,
                    t.category_product_id
                from sale_order_line s
                    join sale_order l on (s.order_id=l.id)
                    left join product_product p on (s.product_id=p.id)
                    left join product_template t on (p.product_tmpl_id=t.id)
                    left join product_category c on (s.categ_id=c.id)
                    --left join (select db.wo_line_id, sum(db.diskon) as discount_bundle from sale_order_bundle db group by db.wo_line_id) s_db ON s_db.wo_line_id = s.id 
                    --where l.state in ('done')
                group by
                    l.state,
                    s.product_id,
                    s.categ_id,
                    l.partner_id,
                    --l.no_pol,
                    l.tipe_transaksi,
                    --l.kpb_ke,
                    --l.lot_id,
                    l.create_uid,
                    l.date_order,
                    l.branch_id,
                    --l.mekanik_id,
                    l.employee_id,
                    l.name,
                    c.name,
                    s.product_id,
                    t.category_product_id
            )
        """)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
