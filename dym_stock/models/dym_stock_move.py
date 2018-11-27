from openerp.osv import fields, osv
from openerp import SUPERUSER_ID
from datetime import datetime

class dym_stock_move(osv.osv):
    _inherit = 'stock.move'
    
    def _get_division(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for x in self.browse(cr, uid, ids, context=context) :
            result[x.id] = self.pool.get('product.category').get_root_name(cr, uid, x.categ_id.id)
        return result

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids

    def create(self, cr, uid, vals, context=None):
        move_id = super(dym_stock_move, self).create(cr, uid, vals, context=context)
        move = self.pool.get('stock.move').browse(cr, SUPERUSER_ID, move_id)
        if move.sudo().picking_id.branch_id and move.sudo().picking_id.picking_type_id:
            location_source, location_destination = self.pool.get('dym.product.location').get_location_id(cr, SUPERUSER_ID, move.sudo().product_id.id, move.sudo().picking_id.branch_id.id, move.sudo().picking_id.picking_type_id.id, move.sudo().location_id.id, move.sudo().location_dest_id.id, move, product_uom_qty=move.product_uom_qty, context=context)
            if move.sudo().restrict_lot_id and move.sudo().picking_id.picking_type_code in ('outgoing','interbranch_out','internal'):
                location_source = move.sudo().restrict_lot_id.location_id.id
            move.sudo().write({'location_id':location_source, 'location_dest_id':location_destination})
        return move_id

    def _get_warehouse(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for move in self.browse(cr, uid, ids, context=context):
            res[move.id] = {
                'warehouse_location': False,
            }
            res[move.id]['warehouse_location'] = move.location_id.warehouse_id.id if move.location_id.usage in ['nrfs','internal','kpb'] and move.location_id.warehouse_id.id else move.location_dest_id.warehouse_id.id
        return res

    def _get_stock_location(self, cr, uid, ids, context=None):
        move_ids = self.pool.get('stock.move').search(cr, uid, ['|',('location_id', 'in', ids),('location_dest_id', 'in', ids)])
        return list(set(move_ids))


    def _get_branches(self, cr, uid, ids, name, args, context, where =''):
        branch_ids = self.pool.get('res.users').browse(cr, uid, uid).branch_ids.ids
        result = {}
        for val in self.browse(cr, uid, ids):
            result[val.id] = True if val.warehouse_location.branch_id.id in branch_ids else False
        return result

    def _cek_branches(self, cr, uid, obj, name, args, context):
        branch_ids = self.pool.get('res.users').browse(cr, uid, uid).branch_ids.ids
        return [('warehouse_location.branch_id', 'in', branch_ids)]

    _columns = {
        'is_mybranch': fields.function(_get_branches, string='Is My Branches', type='boolean', fnct_search=_cek_branches),
        'warehouse_location': fields.function(_get_warehouse, string='Warehouse',
            store={
                'stock.move': (lambda self, cr, uid, ids, c={}: ids, ['location_id','location_dest_id'], 10),
                'stock.location': (_get_stock_location, ['warehouse_id'], 10),
            },relation='stock.warehouse',type='many2one', 
            multi='sums', help="Warehouse", track_visibility='always'),
        'name': fields.char('Description', required=False, select=True),
        'branch_id': fields.many2one('dym.branch', string='Branch'),
        'categ_id': fields.many2one('product.category', 'Category'),
        'func_division': fields.function(_get_division, string="Division", type="char"),
        'stock_available': fields.float('Stock Available', digits=(10,0)),
        'rel_stock_available': fields.related('stock_available', string='Stock Available', digits=(10,0)),
        'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
        'confirm_date':fields.datetime('Confirmed on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),
        'undelivered_value': fields.float('Undelivered Value'),
        'real_hpp': fields.float('Real HPP'),
        'product_tmpl_id': fields.related('product_id', 'product_tmpl_id', relation='product.template', type='many2one', string='Tipe'),
        'move_line_id_extra':fields.many2one('stock.move',string="Move ID Extra"),
    }
    
    _sql_constraints = [
        ('unique_lot', 'unique(picking_id,restrict_lot_id)', 'Ditemukan Lot duplicate, Silahkan cek kembali !'),
    ]
    
    _defaults = {
         'branch_id': _get_default_branch,
    }
    
    def lot_qty_change(self, cr, uid, ids, product_uom_qty, product_uom, restrict_lot_id, context=None) :
        value = {}
        value['product_uos'] = product_uom
        if restrict_lot_id :
            value['product_uom_qty'] = 1
            value['product_uos_qty'] = 1
        else :
            value['product_uos_qty'] = product_uom_qty
        return {'value':value}
    
    def get_stock_available(self, cr, uid, ids, id_product, id_location, context=None):
        cr.execute("""
        SELECT
            sum(q.qty) as quantity
        FROM
            stock_quant q
        LEFT JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and q.reservation_id is Null and q.consolidated_date is not Null
            and (q.lot_id is Null or l.state = 'stock')
        """,(id_product,id_location))
        return cr.fetchall()[0][0]
    
    def get_lot_available(self, cr, uid, ids, id_product, id_location, context=None):
        ids_lot_available = []
        cr.execute("""
        SELECT
            l.id
        FROM
            stock_quant q
        JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and l.state = 'stock' and q.reservation_id is Null and q.consolidated_date is not Null
        """,(id_product,id_location))
        for id_lot in cr.fetchall() :
            ids_lot_available.append(id_lot[0])
        return ids_lot_available
    
    def categ_id_change(self, cr, uid, ids, branch_id, division, categ_id, source, context=None):
        val = {}
        dom = {}
        war = {}
        obj_categ = self.pool.get('product.category')
        val['product_id'] = False
        val['restrict_lot_id'] = False
        
        if categ_id and not source :
            val['categ_id'] = False
            war = {'title':'Perhatian !', 'message':'Silahkan isi Source Location terlebih dahulu'}
            return {'warning':war, 'value':val}
        elif categ_id and not branch_id :
            val['categ_id'] = False
            war = {'title':'Perhatian !', 'message':'Silahkan isi Branch terlebih dahulu'}
            return {'warning':war, 'value':val}
        elif categ_id and source :
            val['func_division'] = obj_categ.get_root_name(cr, uid, categ_id)
            
            cr.execute("""SELECT
                q.product_id
            FROM
                stock_quant q
            LEFT JOIN
                product_product p on (p.id=q.product_id)
            LEFT JOIN
                stock_location l on (l.id=q.location_id)
            LEFT JOIN
                dym_branch b on (b.id=l.branch_id)
            WHERE
                q.location_id=%s and l.branch_id=%s""",(source,branch_id))
            result = cr.fetchall()
            dom['product_id'] = [('categ_id','=',categ_id),('id','in',result)]
            
        return {'domain':dom, 'value':val, 'warning':war}
    
    def picking_branch_id_change(self, cr, uid, ids, categ_id, branch_id, division, type, source, destination, context=None):
        if not type :
            raise osv.except_osv(('Data header belum lengkap !'), ('Sebelum menambah detil harap isi data header terlebih dahulu'))
        elif not branch_id or not division :
            raise osv.except_osv(('Data header belum lengkap !'), ('Sebelum menambah detil harap isi data header terlebih dahulu'))
        val = {}
        dom = {}
        obj_categ = self.pool.get('product.category')
        picking_type_id = self.pool.get('stock.picking.type').browse(cr, uid, type)
        if picking_type_id.default_location_src_id.usage == 'internal':
            cr.execute("""SELECT
                q.product_id
            FROM
                stock_quant q
            LEFT JOIN
                product_product p on (p.id=q.product_id)
            LEFT JOIN
                stock_location l on (l.id=q.location_id)
            LEFT JOIN
                dym_branch b on (b.id=l.branch_id)
            WHERE
                q.location_id=%s and l.branch_id=%s""",(picking_type_id.default_location_src_id.id,branch_id))
            result = cr.fetchall()
            
            categ_ids = obj_categ.get_child_ids(cr, uid, ids, division)

            dom['product_id'] = [('categ_id','in',categ_ids),('id','in',result)]
        else:
            categ_ids = obj_categ.get_child_ids(cr, uid, ids, division)

            dom['product_id'] = [('categ_id','in',categ_ids)]
        
        val['branch_id'] = branch_id
        val['restrict_lot_id'] = False
        val['func_division'] = division
        val['location_id'] = picking_type_id.default_location_src_id.id
        val['location_dest_id'] = picking_type_id.default_location_dest_id.id
        return {'domain':dom, 'value':val}
    
    def internal_stock_available_change(self, cr, uid, ids, stock_available, context=None):
        value = {}
        value['rel_stock_available'] = stock_available
        return {'value':value}
    
    def internal_product_qty_change(self, cr, uid, ids, stock_available, id_branch, division, id_product, qty, id_picking_type, source, destination, restrict_lot_id,template_id=False, context=None):
        if not id_branch or not division or not id_picking_type or not source or not destination :
            raise osv.except_osv(('Data header belum lengkap !'), ('Sebelum menambah detil harap isi data header terlebih dahulu'))
        val = {}
        war = {}
        dom = {}
        obj_categ = self.pool.get('product.category')
        product_id = self.pool.get('product.product').browse(cr, uid, id_product)
        obj_pu = self.pool.get('product.uom')
        if id_product :
            if restrict_lot_id not in self.get_lot_available(cr, uid, ids, id_product, source, context) :
                val['restrict_lot_id'] = False
            dom['restrict_lot_id'] = [('id','in',self.get_lot_available(cr, uid, ids, id_product, source, context))]
            val['stock_available'] = self.get_stock_available(cr, uid, ids, id_product, source, context)
        
        cr.execute("""
        SELECT
            q.product_id
        FROM
            stock_quant q
        LEFT JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.location_id = %s and q.reservation_id is Null and q.consolidated_date is not Null
            and (q.lot_id is Null or l.state = 'stock')
        """,(source,))
        result = cr.fetchall()
        categ_ids = obj_categ.get_child_ids(cr, uid, ids, division)
        dom['product_tmpl_id']=[('categ_id','in',categ_ids),('purchase_ok','=',True)]
        if template_id:
            dom['product_id']=[('product_tmpl_id','=',template_id),('categ_id','in',categ_ids),('purchase_ok','=',True)]
            template = self.pool.get('product.template').browse(cr, uid, [template_id])
            if id_product and id_product not in template.product_variant_ids.ids:
                val['product_id'] = False
            if len(template.product_variant_ids) == 1:
                val['product_id'] = template.product_variant_ids.id
        else:
            val['product_id'] = False
            dom['product_id']=[('id','=',0)]
        #dom['product_id'] = [('categ_id','in',categ_ids),('id','in',result)]

        val['branch_id'] = id_branch
        val['func_division'] = division
        
        id_pu = obj_pu.search(cr, uid, [('name','like','Unit')])
        val['product_uom'] = id_pu[0]
        val['product_uos'] = id_pu[0]
        val['picking_type_id'] = id_picking_type
        val['location_id'] = source
        val['location_dest_id'] = destination
        if product_id :
            val['name'] = product_id.description
            val['categ_id'] = product_id.categ_id.id
        val['product_uos_qty'] = qty
        if qty : 
            if qty < 0 :
                val['product_uom_qty'] = stock_available
                val['product_uos_qty'] = stock_available
                war = {'title':'Perhatian !', 'message':'Quantity tidak boleh kurang dari nol'}
            elif division <> 'Unit' and qty > stock_available and id_product:
                val['product_uom_qty'] = stock_available
                val['product_uos_qty'] = stock_available
                war = {'title':'Perhatian !', 'message':'Quantity tidak boleh lebih dari stock available'}
        
        if division == 'Unit' :
            val['product_uom_qty'] = 1
            val['product_uos_qty'] = 1        
        return {'value':val, 'warning':war, 'domain':dom}
    
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False, template_id=False, division=False):
        result = super(dym_stock_move,self).onchange_product_id(cr, uid, ids, prod_id=prod_id, loc_id=loc_id, loc_dest_id=loc_dest_id, partner_id=partner_id)
        if prod_id :
            id_categ = self.pool.get('product.product').browse(cr, uid, prod_id).categ_id.id
            result['value'].update({'categ_id': id_categ})
            result['value'].update({'restrict_lot_id': False})

        obj_categ = self.pool.get('product.category')
        domain_add = []
        dom = {}
        if 'domain' not in result:
            result['domain'] = {}
        if 'value' not in result:
            result['value'] = {}
        categ_ids = obj_categ.get_child_ids(cr, uid, ids, division)
        domain_add = [('categ_id','in',categ_ids)]
        dom['product_tmpl_id'] = domain_add
        if template_id:
            dom['product_id']=[('product_tmpl_id','=',template_id)] + domain_add
            template = self.pool.get('product.template').browse(cr, uid, [template_id])
            if prod_id and prod_id not in template.product_variant_ids.ids:
                result['value'].update({'product_id': False})
            if len(template.product_variant_ids) == 1:
                result['value'].update({'product_id': template.product_variant_ids.id})
        else:
            result['value'].update({'product_id': False})
            dom['product_id']=[('id','=',0)]
        result['domain'] = dom
        return result
    
    def action_done(self, cr, uid, ids, context=None):  
        self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now()})        
        vals = super(dym_stock_move,self).action_done(cr,uid,ids,context=context)  
        return vals
    
    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})        
        vals = super(dym_stock_move,self).action_cancel(cr,uid,ids,context=context)  
        return vals
    
    def action_assign(self, cr, uid, ids, context=None):
        """ Checks the product type and accordingly writes the state.
        """
        context = context or {}
        quant_obj = self.pool.get("stock.quant")
        to_assign_moves = []
        main_domain = {}
        todo_moves = []
        operations = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.state not in ('confirmed', 'waiting', 'assigned'):
                continue
            if move.location_id.usage in ('supplier', 'inventory', 'production') or (move.sudo().branch_id.branch_type == 'MD' and move.picking_id.division == 'Unit' and move.picking_id.picking_type_id.code == 'outgoing' and not move.picking_id.is_reverse) or (move.picking_id.division == 'Unit' and move.picking_id.picking_type_id.code == 'interbranch_out' and not move.picking_id.is_reverse):
                to_assign_moves.append(move.id)
                if not move.origin_returned_move_id:
                    continue
            if move.product_id.type == 'consu':
                to_assign_moves.append(move.id)
                continue
            else:
                todo_moves.append(move)
                main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]
                ancestors = self.find_move_ancestors(cr, uid, move, context=context)
                if move.state == 'waiting' and not ancestors:
                    main_domain[move.id] += [('id', '=', False)]
                elif ancestors:
                    main_domain[move.id] += [('history_ids', 'in', ancestors)]

                if move.origin_returned_move_id:
                    main_domain[move.id] += [('history_ids', 'in', move.origin_returned_move_id.id)]
                for link in move.linked_move_operation_ids:
                    operations.add(link.operation_id)
        operations = list(operations)
        operations.sort(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.lot_id and -1 or 0))
        for ops in operations:
            for record in ops.linked_move_operation_ids:
                move = record.move_id
                if move.id in main_domain:
                    domain = main_domain[move.id] + self.pool.get('stock.move.operation.link').get_specific_domain(cr, uid, record, context=context)
                    qty = record.qty
                    if qty:
                        quants = quant_obj.quants_get_prefered_domain(cr, uid, ops.location_id, move.product_id, qty, domain=domain, prefered_domain_list=[], restrict_lot_id=move.restrict_lot_id.id, restrict_partner_id=move.restrict_partner_id.id, context=context)
                        quant_obj.quants_reserve(cr, uid, quants, move, record, context=context)
        for move in todo_moves:
            if move.linked_move_operation_ids:
                continue
            move.refresh()
            if move.state != 'assigned':
                qty_already_assigned = move.reserved_availability
                qty = move.product_qty - qty_already_assigned
                if move.origin_returned_move_id and not move.retur_beli_line_id and move.location_dest_id.usage == 'supplier':
                    context['bypass_consolidate'] = True
                quants = quant_obj.quants_get_prefered_domain(cr, uid, move.location_id, move.product_id, qty, domain=main_domain[move.id], prefered_domain_list=[], restrict_lot_id=move.restrict_lot_id.id, restrict_partner_id=move.restrict_partner_id.id, context=context)
                quant_obj.quants_reserve(cr, uid, quants, move, context=context)
        
        if to_assign_moves:
            self.force_assign(cr, uid, to_assign_moves, context=context)
    
class dym_stock_move_operation_link(osv.osv):
    _inherit = "stock.move.operation.link"

    def get_specific_domain(self, cr, uid, record, context=None):
        domain = super(dym_stock_move_operation_link, self).get_specific_domain(cr, uid, record, context)
        reverse_incoming = record.move_id.picking_id.picking_type_id.code == 'outgoing' and record.move_id.location_dest_id.usage == 'supplier'
        reverse_outgoing = record.move_id.picking_id.picking_type_id.code == 'incoming' and record.move_id.location_id.usage == 'customer'
        if not (reverse_incoming or reverse_outgoing):
            domain.append(('consolidated_date', '!=', False))
        return domain
