from openerp.osv import fields,osv
from openerp import tools

class dym_stock_unit_report(osv.osv):
    _name = "dym.stock.unit.report"
    _description = "Stock Unit Report"
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
        'branch_id':fields.many2one('dym.branch','Branch'),
        'category':fields.char('Category', readonly=True),
        'product_kode': fields.many2one('product.template', 'Kode Barang', readonly=True),
        'product_default_code': fields.char('Internal Reference', readonly=True),
        'product_warna': fields.many2one('product.attribute.value', 'Warna', readonly=True),
        'location': fields.many2one('stock.location','Lokasi', readonly=True),
        'mesin': fields.many2one('stock.production.lot','Mesin ', readonly=True),
        'rangka': fields.char('Rangka ', readonly=True),
        'jumlah': fields.float('Jumlah ', readonly=True),
        'posisi_stock': fields.char('Posisi Stock ', readonly=True),
        'source': fields.char('Source ', readonly=True),
    }

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'dym_stock_unit_report')
        cr.execute("""
            create or replace view dym_stock_unit_report as (                    
                select
                    min(a.id) as id,
                    c.id as branch_id,
                    a.product_category as category,
                    x.id as product_kode,
                    e.default_code as product_default_code,
                    g.id as product_warna,
                    b.id as location,
                    d.id as mesin,
                    d.chassis_no as rangka,
                    sum(a.qty) as jumlah,
                    CASE 
                        WHEN (d.state = 'intransit' or (a.consolidated_date is null and a.lot_id is null)) and b.usage in ('internal','nrfs','kpb') and a.product_category != 'Extras' THEN 'Intransit'
                        WHEN (d.state = 'stock' or (a.consolidated_date is not null and a.lot_id is null) or a.product_category = 'Extras') and b.usage = 'internal' and a.reservation_id is null THEN 'Ready for Sale'
                        WHEN (d.state = 'stock' or (a.consolidated_date is not null and a.lot_id is null) or a.product_category = 'Extras') and b.usage in ('nrfs','kpb') and a.reservation_id is null THEN 'Not Ready for Sale'
                        WHEN (d.state in ('sold','sold_offtr','paid','paid_offtr') or (a.reservation_id is not null and a.lot_id is null)) and b.usage in ('internal','nrfs','kpb') THEN 'Undelivered'
                        WHEN (d.state in ('sold','sold_offtr','paid','paid_offtr') or (a.reservation_id is not null and a.lot_id is null)) and b.usage = 'customer' THEN 'Transferred'
                        WHEN (d.state = 'reserved' or a.reservation_id is not null) and b.usage in ('internal','nrfs','kpb') THEN 'Reserved'
                        WHEN d.state = 'returned' and b.usage in ('internal','nrfs','kpb','supplier') THEN 'Purchase Return'
                        WHEN b.usage = 'asset_clearing' THEN 'Asset'
                        ELSE '' 
                    END as posisi_stock,
                    r.origin as source

                from
                    stock_quant a
                    LEFT JOIN stock_location b ON b.id = a.location_id
                    LEFT JOIN dym_branch c ON c.id = b.branch_id
                    LEFT JOIN stock_production_lot d ON d.id = a.lot_id
                    LEFT JOIN product_product e ON e.id = a.product_id
                    LEFT JOIN product_template x ON x.id = e.product_tmpl_id
                    LEFT JOIN product_attribute_value_product_product_rel f ON f.prod_id = a.product_id
                    LEFT JOIN product_attribute_value g ON g.id = f.att_id
                    LEFT JOIN product_category h ON h.id = x.categ_id
                    LEFT JOIN stock_warehouse w ON b.warehouse_id = w.id
                    LEFT JOIN stock_picking r ON r.id = d.picking_id

                where
                    b.usage in ('internal','nrfs','kpb')

                group by
                    c.id,
                    a.product_category,
                    x.id,
                    e.default_code,
                    g.id,
                    b.id,
                    d.id,
                    d.chassis_no,
                    posisi_stock,
                    source
               
            )
        """)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
