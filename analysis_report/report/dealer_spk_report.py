from openerp.osv import fields,osv
from openerp import tools

class dealer_spk_report(osv.osv):
    _name = "dealer.spk.report"
    _description = "Dealer Memo Report"
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
        'branch_id':fields.many2one('dym.branch', 'Branch', readonly=True),
        'division':fields.selection([('Sparepart','Workshop')],'Division', change_default=True,select=True,required=True),
        'partner_id':fields.many2one('res.partner', 'Customer', readonly=True),
        'finco_id':fields.many2one('res.partner', 'Finco', readonly=True),
        'employee_id':fields.many2one('hr.employee', 'Sales Person', readonly=True),
        'date': fields.date('Order Date', readonly=True, help="Date on which this document has been created"),  # TDE FIXME master: rename into date_order
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'name': fields.char('Memo', size=64, required=True),
        'state': fields.selection([
                                ('draft', 'Draft'),                                
                                ('progress', 'Memo'),
                                ('so', 'Sales Memo'),
                                ('done', 'Done'),
                                ('cancelled', 'Cancelled'),
                                ],string='Status',default='draft')
    
    }
    _order = 'date desc'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'dealer_spk_report')
        cr.execute("""
            create or replace view dealer_spk_report as (
                select
                    min(l.id) as id,
                    l.date_order as date,
                    l.branch_id, 
                    l.division,
                    l.partner_id,
                    l.finco_id,
                    l.employee_id,
                    s.product_id,
                    l.name,
                    l.state
                    
                    
                from dealer_spk_line s
                    join dealer_spk l on (s.dealer_spk_line_id=l.id)
                        left join product_product p on (s.product_id=p.id)
                
                group by
                l.branch_id,
                l.date_order,
                l.division,
                l.partner_id,
                l.finco_id,
                l.employee_id,
                s.product_id,
                l.name,
                l.state
                      
            )
        """)
    
    
    
    
    
    
    def list_branchs(self, cr, uid, context=None):
        ids = self.pool.get('res.users').browse(cr, uid, uid).branch_ids.ids
        return self.pool.get('dym.branch').name_get(cr, uid, ids, context=context)


    def list_products(self, cr, uid, context=None):
        idss = self.pool.get('product.category').search(cr,uid,[])
        product_ids = self.pool.get('product.category').get_child_ids(cr,uid,idss,'Unit')
        ids = self.pool.get('product.product').search(cr,uid,[("categ_id", "in", product_ids)],limit=90)
        #ids = self.pool.get('product.product').search(cr,uid,[], limit=1)
        return self.pool.get('product.product').name_get(cr, uid, ids, context=context)
#         idss = self.pool.get('product.category').search(cr,uid,[])
#         product_ids = self.pool.get('product.category').get_child_ids(cr,uid,idss,'Unit',)
#         ids = self.pool.get('product.product').search(cr,uid,[("categ_id", "in", product_ids)])
#         return self.pool.get('product.product').name_get(cr, uid, ids, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
