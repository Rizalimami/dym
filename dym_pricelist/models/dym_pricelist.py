from openerp.osv import fields, osv
from lxml import etree
from openerp.osv.orm import setup_modifiers
from openerp import SUPERUSER_ID

class dym_product_pricelist_item (osv.osv):
    _inherit = "product.pricelist.item"
    
    def product_id_change(self, cr, uid, ids, product_id, product_tmpl_id, categ_id, context=None):
        value = {}
        value['name'] = False
        if product_id :
            prod = self.pool.get('product.product').browse(cr, uid, product_id)
            value['name'] = prod.name_get().pop()[1]
            value['product_tmpl_id'] = False
            value['categ_id'] = False
        elif product_tmpl_id :
            prod_tmpl = self.pool.get('product.template').browse(cr, uid, product_tmpl_id)
            value['name'] = prod_tmpl.name_get().pop()[1]
            value['product_id'] = False
            value['categ_id'] = False
        elif categ_id :
            categ = self.pool.get('product.category').browse(cr, uid, categ_id)
            value['name'] = categ.name_get().pop()[1]
            value['product_id'] = False
            value['product_tmpl_id'] = False
        return {'value':value}
    
class dym_pricelist (osv.osv):
    _name = "dym.pricelist"
    
    def _get_branch_id(self, cr, uid, context=None):
        obj_branch = self.pool.get('dym.branch')
        ids_branch = obj_branch.search(cr, SUPERUSER_ID, [], order='name')
        branches = obj_branch.read(cr, SUPERUSER_ID, ids_branch, ['id','name'], context=context)
        res = []
        for branch in branches :
            res.append((branch['id'],branch['name']))
        return res
    
    _columns = {
                'product_id': fields.many2one('product.product', 'Product'),
                'branch_id': fields.selection(_get_branch_id, 'Branch'),
                'name': fields.char('Name'),
                'categ_id': fields.many2one('product.category','Category'),
                'pricelist_unit_purchase_id' : fields.many2one('product.pricelist', string='Price List Beli Unit', domain=[('type','=','purchase')]),
                'pricelist_unit_sales_id' : fields.many2one('product.pricelist', string='Price List Jual Unit', domain=[('type','=','sale')]),
                'pricelist_part_purchase_id' : fields.many2one('product.pricelist', string='Price List Beli Sparepart', domain=[('type','=','purchase')]),
                'pricelist_part_sales_id' : fields.many2one('product.pricelist', string='Price List Jual Sparepart', domain=[('type','=','sale')]),
                'pricelist_bbn_hitam_id' : fields.many2one('product.pricelist', string='Price List Jual BBN Plat Hitam', domain=[('type','=','sale_bbn_hitam')]),
                'pricelist_bbn_merah_id' : fields.many2one('product.pricelist', string='Price List Jual BBN Plat Merah', domain=[('type','=','sale_bbn_merah')]),
                'harga_beli': fields.float('Harga Beli'),
                'harga_jual': fields.float('Harga Jual Off'),
                'harga_jual_bbn_hitam': fields.float('Harga Jual BBN Hitam'),
                'harga_jual_bbn_merah': fields.float('Harga Jual BBN Merah'),
                'total_stock': fields.float('Total Stock'),
                'stock_intransit': fields.float('Stock Intransit'),
                'stock_available': fields.float('Stock Available'),
                'stock_reserved': fields.float('Stock Reserved'),
                'location_id': fields.char('Location')
                }
    
    
    def pricelist_change(self, cr, uid, ids, product_id, branch_id, context=None):
        value = {}
        warning = {}
        
        value['name'] = False
        value['categ_id'] = False
        value['pricelist_unit_sales_id'] = False
        value['pricelist_unit_purchase_id'] = False
        value['pricelist_bbn_hitam_id'] = False
        value['pricelist_bbn_merah_id'] = False
        value['harga_beli'] = False
        value['harga_jual'] = False
        value['harga_jual_bbn_hitam'] = False
        value['harga_jual_bbn_merah'] = False
        value['total_stock'] = False
        value['stock_available'] = False
        value['location_id'] = ''
        value['stock_reserved'] = False
        value['order_qty'] = 0
        value['lost_order_qty'] = 0
        
        if product_id and branch_id :
            prod = self.pool.get('product.product').browse(cr, SUPERUSER_ID, product_id)
            branch = self.pool.get('dym.branch').browse(cr, SUPERUSER_ID, branch_id)
            
            value['name'] = prod.description
            value['categ_id'] = prod.categ_id
            value['pricelist_unit_purchase_id'] = branch.pricelist_unit_purchase_id
            value['pricelist_unit_sales_id'] = branch.pricelist_unit_sales_id
            value['pricelist_part_purchase_id'] = branch.pricelist_part_purchase_id
            value['pricelist_part_sales_id'] = branch.pricelist_part_sales_id
            value['pricelist_bbn_hitam_id'] = branch.pricelist_bbn_hitam_id
            value['pricelist_bbn_merah_id'] = branch.pricelist_bbn_merah_id
            
            if prod.categ_id.isParentName('Unit') :
                # pricelist beli unit
                if branch.pricelist_unit_purchase_id :
                    value['harga_beli'] = self.pool.get('product.pricelist').price_get(cr, uid, [branch.pricelist_unit_purchase_id.id], product_id, 1,0)[branch.pricelist_unit_purchase_id.id]
                
                # pricelist jual unit
                if branch.pricelist_unit_sales_id :
                    value['harga_jual'] = self.pool.get('product.pricelist').price_get(cr, uid, [branch.pricelist_unit_sales_id.id], product_id, 1,0)[branch.pricelist_unit_sales_id.id]
                
                # pricelist jual bbn hitam
                if branch.pricelist_bbn_hitam_id :
                    value['harga_jual_bbn_hitam'] = self.pool.get('product.pricelist').price_get(cr, uid, [branch.pricelist_bbn_hitam_id.id], product_id, 1,0)[branch.pricelist_bbn_hitam_id.id]
                    
                # pricelist jual bbn merah
                if branch.pricelist_bbn_merah_id :
                    value['harga_jual_bbn_merah'] = self.pool.get('product.pricelist').price_get(cr, uid, [branch.pricelist_bbn_merah_id.id], product_id, 1,0)[branch.pricelist_bbn_merah_id.id]
                
                cr.execute("""SELECT
                    q.product_id, l.branch_id, q.reservation_id, q.consolidated_date, s.state, sum(q.qty)
                FROM
                    stock_quant q
                JOIN
                    stock_location l on q.location_id = l.id
                JOIN
                    stock_production_lot s on q.lot_id = s.id
                WHERE
                    q.product_id = %s and l.branch_id = %s and l.usage in ('internal','transit')
                GROUP BY
                    q.product_id, l.branch_id, q.reservation_id, q.consolidated_date, s.state
                """,(product_id,branch_id))

                unit_intransit = 0
                unit_available = 0
                unit_reserved = 0
                
                for x in cr.fetchall() :
                    if x[2] == None and (x[4] == 'intransit' or x[3] == None) :
                        unit_intransit += x[5]
                    elif x[2] == None and x[4] == 'stock' :
                        unit_available += x[5]
                    elif x[2] <> None or x[4] == 'reserved' :
                        unit_reserved += x[5]
                
                unit_tot_qty = unit_intransit + unit_available + unit_reserved
                
                value['stock_intransit'] = unit_intransit
                value['stock_available'] = unit_available
                value['stock_reserved'] = unit_reserved
                value['total_stock'] = unit_tot_qty

            else :
                # pricelist beli sparepart
                if branch.pricelist_part_purchase_id :
                    value['harga_beli'] = self.pool.get('product.pricelist').price_get(cr, uid, [branch.pricelist_part_purchase_id.id], product_id, 1,0)[branch.pricelist_part_purchase_id.id]
                
                # pricelist jual sparepart
                if branch.pricelist_part_sales_id :
                    value['harga_jual'] = self.pool.get('product.pricelist').price_get(cr, uid, [branch.pricelist_part_sales_id.id], product_id, 1,0)[branch.pricelist_part_sales_id.id]
                
                cr.execute("""SELECT
                    q.product_id, l.branch_id, q.reservation_id, q.consolidated_date, sum(q.qty), l.name
                FROM
                    stock_quant q
                JOIN
                    stock_location l on q.location_id = l.id
                WHERE
                    q.product_id = %s and l.branch_id = %s and l.usage in ('internal','transit')
                GROUP BY
                    q.product_id, l.branch_id, q.reservation_id, q.consolidated_date, l.name
                """,(product_id,branch_id))

                part_intransit = 0
                part_available = 0
                part_reserved = 0
                location_part = ''
                
                for x in cr.fetchall() :
                    if x[2] <> None and x[3] <> None :
                        part_reserved += x[4]
                        location_part = x[5]
                    elif x[2] == None and x[3] <> None :
                        part_available += x[4]
                    elif x[3] == None :
                        part_intransit += x[4]
                
                part_tot_qty = part_intransit + part_available + part_reserved
                
                value['stock_intransit'] = part_intransit
                value['stock_available'] = part_available
                value['stock_reserved'] = part_reserved
                value['total_stock'] = part_tot_qty
                value['location_id'] = location_part
        
        return {'value':value}
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:context = {}
        res = super(dym_pricelist, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='product_id']")   
        parent_categ_id = str(context.get('default_categ_id'))

        for node in nodes:
            domain ="[('type','!=','view'),('categ_id','child_of','"+parent_categ_id+"')]"
            if parent_categ_id == 'Sparepart':
                domain ="[('type','!=','view'),('categ_id','child_of','"+parent_categ_id+"')]"
            node.set('domain', domain)
            setup_modifiers(node, res['fields']['product_id'])
        res['arch'] = etree.tostring(doc)            
        return res
    