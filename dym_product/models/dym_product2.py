import re
import string
from openerp.osv import osv, fields, expression
from openerp import models, api, _, SUPERUSER_ID

class dym_product_location(osv.osv):
    _name = "dym.product.location"
    _columns = {
        'product_id':fields.many2one('product.product', 'Product', required=True),
        'branch_id': fields.many2one('dym.branch', 'Branch', required=True),
        'location_id' : fields.many2one('stock.location','Location', required=True, domain="[('branch_id','!=',False),('branch_id','=',branch_id),('usage','=','internal')]"),
    }
    _sql_constraints = [
        ('unique_product_branch', 'unique(product_id,branch_id)', 'Data branch tidak boleh duplicate!'),
    ]
    
    '''
    def get_location_id(self, cr, uid, product_id, branch_id, picking_type_id, location_src_id, location_dest_id, move, product_uom_qty=0, usage=['internal'], context=None):
        location_id = self.search(cr, uid, [
            ('branch_id','=',branch_id),
            ('product_id','=',product_id)
            ], order='id desc', limit=1)
        
        location = False
        picking_type = False
        picking_src = False
        picking_dest = False
        location_source = location_src_id
        location_destination = location_dest_id
        if location_id:
            location = self.browse(cr, uid, location_id)
        if picking_type_id:
            picking_type = self.pool.get('stock.picking.type').browse(cr, uid, picking_type_id)
            if picking_type.code in ['incoming','interbranch_in']:
                picking_dest = picking_type.default_location_dest_id
            elif picking_type.code in ['outgoing','interbranch_out']:
                picking_src = picking_type.default_location_src_id
            elif picking_type.code in ['internal']:
                picking_src = picking_type.default_location_src_id
                picking_dest = picking_type.default_location_dest_id

        # START - Modified by Iman 2017/08/30

        # if location and picking_dest:
        #     if location_dest_id == picking_dest.id:
        #         location_destination = location.location_id.id
        #     elif location_dest_id != picking_dest.id:
        #         location_destination = location_dest_id

        # New line
        if location and location.location_id:
            location_destination = location.location_id.id
        else:
            if picking_dest:
                if location_dest_id == picking_dest.id:
                    location_destination = picking_dest.id
                elif location_dest_id != picking_dest.id:
                    location_destination = location_dest_id

        # END - Modified by Iman 2017/08/30

        if location and picking_src:
            if location_src_id == picking_src.id:
                location_source = location.location_id.id
            elif location_src_id != picking_src.id:
                location_source = location_src_id
        return location_source, location_destination


    ORIGINAL SCRIPT
    '''

    def get_location_id(self, cr, uid, product_id, branch_id, picking_type_id, location_src_id, location_dest_id, move, product_uom_qty=0, usage=['internal'], context=None):
        location_id = self.search(cr, uid, [
                            ('branch_id','=',branch_id),
                            ('product_id','=',product_id)
                            ], order='id desc', limit=1)
        location = False
        picking_type = False
        picking_src = False
        picking_dest = False
        location_source = location_src_id
        location_destination = location_dest_id
        if location_id:
            location = self.browse(cr, uid, location_id)
        if picking_type_id:
            picking_type = self.pool.get('stock.picking.type').browse(cr, uid, picking_type_id)
            if picking_type.code in ['incoming','interbranch_in']:
                picking_dest = picking_type.default_location_dest_id
            elif picking_type.code in ['outgoing','interbranch_out']:
                picking_src = picking_type.default_location_src_id
            elif picking_type.code in ['internal']:
                picking_src = picking_type.default_location_src_id
                picking_dest = picking_type.default_location_dest_id
        if location and picking_dest:
            if location_dest_id == picking_dest.id:
                location_destination = location.location_id.id
            elif location_dest_id != picking_dest.id:
                location_destination = location_dest_id
        if location and picking_src:
            if location_src_id == picking_src.id:
                location_source = location.location_id.id
            elif location_src_id != picking_src.id:
                location_source = location_src_id
        return location_source, location_destination

class dym_product_product(osv.osv):
    _inherit = 'product.product'
    
    def get_location_ids(self,cr,uid,ids,context=None):
        quants_ids = self.pool.get('stock.quant').search(cr,uid,['&',('product_id','in',ids),('qty','>',0.0),('reservation_id','=',False)])
        loc_ids = self.pool.get('stock.quant').read(cr, uid, quants_ids, ['location_id'])
        return [x['location_id'][0] for x in loc_ids]

    MODELS = []


    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []

        def _name_get(d):
            name = d.get('name','')
            product = d.get('product','')
            description = d.get('description','')
            code = context.get('display_default_code', True) and d.get('default_code',False) or False            
            if code:
                name = '%s' % (name)
            if 'attribute_only' in context and context['attribute_only'] and product.categ_id.get_root_name() =='Unit':
                name = d.get('variant')
            if description and name and (description not in name) and 'attribute_only' not in context:
                name = name + ' [' + description + ']'
            # if product.categ_id.get_root_name() =='Unit':
            #     name = d.get('variant')
            return (d['id'], name)


        partner_id = context.get('partner_id', False)
        if partner_id:
            partner_ids = [partner_id, self.pool['res.partner'].browse(cr, user, partner_id, context=context).commercial_partner_id.id]
        else:
            partner_ids = []

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights(cr, user, "read")
        self.check_access_rule(cr, user, ids, "read", context=context)

        result = []
      
        for product in self.browse(cr, SUPERUSER_ID, ids, context=context):
            variant = ", ".join([v.name for v in product.attribute_value_ids])
            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = []
            if partner_ids:
                sellers = filter(lambda x: x.name.id in partner_ids, product.seller_ids)
            if sellers:
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    mydict = {
                              'id': product.id,
                              'name': seller_variant or name,
                              'default_code': s.product_code or product.default_code,
                              'product': product,
                              'variant': variant,
                              'description': product.description or '',
                              }
                    result.append(_name_get(mydict))
            else:
                mydict = {
                          'id': product.id,
                          'name': name,
                          'default_code': product.default_code,
                          'product': product,
                          'variant': variant,
                          'description': product.description or '',
                          }
                result.append(_name_get(mydict))
        return result

    '''
    def name_get(self, cr, uid, ids, context=None):
        res = []
        for product in self.browse(cr, uid, ids, context=context):
            res.append((product.id, (product.name or '') + ' [' + (product.description or product.default_code or '') + ']'))
        return res
    '''

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name and len(name) >= 3:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            ids = []
            if operator in positive_operators:
                ids = self.search(cr, user, ['|',('product_tmpl_id.name','=',name),('default_code','=',name)]+ args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user, [('ean13','=',name)]+ args, limit=limit, context=context)
            if not ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                ids = self.search(cr, user, args + [('default_code', operator, name)], limit=limit, context=context)
                if not limit or len(ids) < limit:
                    limit2 = (limit - len(ids)) if limit else False
                    ids += self.search(cr, user, args + [('name', operator, name), ('id', 'not in', ids)], limit=limit2, context=context)
            elif not ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                ids = self.search(cr, user, args + ['&', ('default_code', operator, name), ('name', operator, name)], limit=limit, context=context)
            if not ids and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, user, [('default_code','=', res.group(2))] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result

    _columns = {
        'extras_line': fields.one2many('dym.barang.extras', 'barang_extras_id', 'Barang Extras'),
        'default_location': fields.one2many('dym.product.location', 'product_id', 'Default Location'),
    }
    
    _defaults = {
             'lst_price': 0,
             'cost_method': 'average',
             'valuation': 'real_time',
    }

    def _get_account_id(self, cr, uid, ids, product_id,context=None):
        obj_account = self.pool.get('product.product').browse(cr,uid,product_id)
        if obj_account:
            account_line= obj_account.property_account_income.id
            if not account_line :
                account_line= obj_account .categ_id.property_account_income_categ.id
                if not account_line :
                    account_line= obj_account.categ_id.parent_id.property_account_income_categ.id
                return account_line
    
    def create(self,cr,uid,vals,context=None):
        res = super(dym_product_product,self).create(cr,uid,vals,context=context)
        return res

class dym_product_attribute_value(osv.osv):
    _inherit = 'product.attribute.value'
    _columns = {
        'code': fields.char('Code'),
    }
    
class dym_barang_extras(osv.osv):
    _name = 'dym.barang.extras'
    _columns = {
        'barang_extras_id':fields.many2one('product.product', 'Barang Extras'),
        'product_id':fields.many2one('product.product', 'Product', domain=[('categ_id','child_of','Extras')], required=True),
        'quantity':fields.float('Quantity', required=True)
    }
    
    def product_change(self, cr, uid, ids, product, categ_id):
        value = {}
        value['quantity'] = 1
        root_name = self.pool.get('product.category').get_root_name(cr, uid, categ_id)
        if root_name <> "Unit" :
            raise osv.except_osv(('Perhatian !'), ("Tidak bisa menambahkan Extras, Category bukan Unit"))
        return {'value': value}
    
class dym_product_template(osv.osv):
    _inherit = 'product.template'
    _columns = {
        'kd_mesin':fields.char('Kode Mesin'),
        'category_product_id':fields.many2one('dym.category.product', 'Category Service (Unit)'),
        'series':fields.char('Series'),
        'is_asset': fields.boolean('Is Asset', help="Specify if the product is an asset."),
        'is_prepaid': fields.boolean('Is Prepaid', help="Specify if the product is prepaid asset."),
        'is_oli': fields.boolean('Is Oli', help="Specify if the product is an Oli."),
        'default_code': fields.related('product_variant_ids', 'default_code', type='char', string='Internal Reference'),
    }
    
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Ditemukan nama produk duplicate, silahkan cek kembali !'),
    ]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []        
        if name and len(name) >= 3:
            ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('description', operator, name)] + args, limit=limit, context=context or {})
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context or {})
        return self.name_get(cr, uid, ids, context or {})

    def kd_mesin_change(self, cr, uid, ids, kd_mesin, context=None):
        value = {}
        warning = {}
        if kd_mesin:
            kd_mesin = kd_mesin.replace(' ','')
            kd_mesin = kd_mesin.upper()
            value['kd_mesin'] = kd_mesin
            pjg = len(kd_mesin)
            for x in range(pjg):
                if kd_mesin[x] in string.punctuation:
                    value['kd_mesin'] = False
                    warning = {
                               'title': 'Perhatian !',
                               'message': 'Kode mesin hanya boleh huruf dan angka !'
                               }
                    return {'warning':warning, 'value':value}
            if pjg > 5 :
                value['kd_mesin'] = kd_mesin[:5]
                warning = {
                           'title': 'Perhatian !',
                           'message': 'Kode mesin maksimal 5 karakter !'
                           }
        return {'warning':warning, 'value':value}
    
    _defaults = {
        'list_price': 0
    }

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for product in self.browse(cr, uid, ids, context=context):
            res.append((product.id, (product.name or '') + ' [' + (product.description or product.default_code or '') + ']'))
        return res

class dym_product_category(osv.osv):
    _inherit = 'product.category'
    
    def _get_child_ids(self, cr, uid, categ_id):
        res=[]
        child_ids = self.pool.get('product.category').search(cr, uid, [('parent_id','=',categ_id)])
        if child_ids :
            res += child_ids
            for child in child_ids :
                grand_child = self._get_child_ids(cr,uid,child)
                if grand_child :
                    res += grand_child
        return res
    
    def get_child_ids(self, cr, uid, ids, parent_categ_name):
        tampung=[]
        obj_pc = self.pool.get('product.category')
        obj_pc_ids = obj_pc.search(cr, uid, [('name','=',parent_categ_name)])
        tampung += obj_pc_ids
        for obj_pc_id in obj_pc_ids :
            tampung += self._get_child_ids(cr,uid,obj_pc_id)
        return tampung
    
    def get_child_by_ids(self, cr, uid, ids):
        tampung=[]
        if isinstance(ids, (int, long)) :
            ids = [ids]
        obj_pc = self.pool.get('product.category')
        obj_pc_ids = obj_pc.search(cr, uid, [('id','in',ids)])
        tampung += obj_pc_ids
        for obj_pc_id in obj_pc_ids :
            tampung += self._get_child_ids(cr,uid,obj_pc_id)
        return tampung

    def get_root_name(self, cr, uid, ids):
        root_name = ""
        if isinstance(ids, (int, long)):
            ids = [ids]
        for obj_pc in self.browse(cr, uid, ids):
            while (obj_pc.parent_id):
                obj_pc = obj_pc.parent_id
            if root_name == "":
                root_name = obj_pc.name
            elif root_name != obj_pc.name :
                return False
        return root_name
    
    def isParentName(self,cr,uid,ids,parent_name):
        if len(ids)>1:
            return False
        pc_obj=self.pool.get('product.category').browse(cr,uid,ids)
        while (pc_obj.name != parent_name):
            if pc_obj.parent_id:
                pc_obj = pc_obj.parent_id
            else:
                return False
        return True
    
