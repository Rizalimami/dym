from openerp import api, SUPERUSER_ID, exceptions
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.osv.orm import browse_record_list, browse_record, browse_null
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import time
from datetime import datetime
import code
# import profile

class dym_stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_stock_picking, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        for field in res['fields']:
            if field == 'division':
                if 'menu' in context and context['menu'] == 'showroom':
                    res['fields'][field]['selection'] = [('Unit','Showroom'), ('Umum','General')]

                if 'menu' in context and context['menu'] == 'workshop':
                    res['fields'][field]['selection'] = [('Sparepart','Workshop'), ('Umum','General')]
        return res
        
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            packing_id = self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id', '=', record.id),('state', '=', 'posted')], limit=1)
            packing = self.pool.get('dym.stock.packing').browse(cr, uid, packing_id)
            if packing:
                tit = "[%s] %s" % (packing.name, record.name)
            else:
                tit = "%s" % (record.name)
            res.append((record.id, tit))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []        
        if name and len(name) >= 3:
            packing_ids = self.pool.get('dym.stock.packing').search(cr, uid, [('name', operator, name),('state', '=', 'posted')])
            picking_ids = []
            for packing in self.pool.get('dym.stock.packing').browse(cr, uid, packing_ids):
                if packing.picking_id.id not in picking_ids:
                    picking_ids.append(packing.picking_id.id)
            ids = self.search(cr, uid, [('id', 'in', picking_ids)] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context or {})
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context or {})
        return self.name_get(cr, uid, ids, context or {})

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids
    
    def _get_is_effective_date(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            if not picking.start_date and not picking.end_date :
                res[picking.id] = True
            elif picking.start_date and picking.end_date and datetime.strptime(picking.start_date, "%Y-%m-%d").date() <= self._get_default_date(cr, uid, context).date() and datetime.strptime(picking.end_date, "%Y-%m-%d").date() >= datetime.today().date() :
                res[picking.id] = True
            else :
                res[picking.id] = True
        return res
    
    def _get_is_reverse(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            reverse_incoming = picking.picking_type_code == 'outgoing' and picking.location_dest_id.usage == 'supplier'
            reverse_outgoing = picking.picking_type_code == 'incoming' and picking.location_id.usage == 'customer'
            res[picking.id] = reverse_incoming or reverse_outgoing
        return res
    
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('dym.branch').get_default_date_model(cr,uid,context=None) 
        
    _columns = {
        'branch_id': fields.many2one('dym.branch', string='Branch', required=True),
        'division': fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], 'Division', change_default=True, select=True, required=True),
        'transaction_id': fields.integer('Transaction ID'),
        'model_id': fields.many2one('ir.model','Model'),
        'internal_location_id': fields.many2one('stock.location', string='Source Location'),
        'internal_location_dest_id': fields.many2one('stock.location', string='Destination Location', help='Destination Location filtered by effective date.'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'is_effective_date': fields.function(_get_is_effective_date, string='Is Effective Date', type='boolean', copy=False),
        'is_reverse': fields.function(_get_is_reverse, string='Is Reverse', type='boolean', copy=False),
        'rel_branch_type' : fields.related('branch_id', 'branch_type', string='Branch Type', type='selection', selection=[('HO','Head Office'), ('MD','Main Dealer'), ('DL','Dealer')]),
        'confirm_uid':fields.many2one('res.users', string="Transfered by", copy=False),
        'confirm_date':fields.datetime('Transfered on', copy=False),
        'retur':fields.boolean('Retur'),
    }
    
    def do_merge(self, cr, uid, ids, context=None):
        """
        To merge similar type of shipment.
        Shipment will only be merged if:
        * Purchase Orders are in draft
        * Purchase Orders belong to the same partner
        * Purchase Orders are have same stock location, same pricelist, same currency
        Lines will only be merged if:
        * Order lines are exactly the same except for the quantity and unit

         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: the ID or list of IDs
         @param context: A standard dictionary

         @return: new purchase order id

        """
        #TOFIX: merged order line should be unlink
        def make_key(br, fields):
            list_key = []
            for field in fields:
                field_val = getattr(br, field)
                if field in ('product_id', 'account_analytic_id'):
                    if not field_val:
                        field_val = False
                if isinstance(field_val, browse_record):
                    field_val = field_val.id
                elif isinstance(field_val, browse_null):
                    field_val = False
                elif isinstance(field_val, browse_record_list):
                    field_val = ((6, 0, tuple([v.id for v in field_val])),)
                list_key.append((field, field_val))
            list_key.sort()
            return tuple(list_key)
        context = dict(context or {})

        new_pickings = {}
        picking_lines_to_move = {}
        for spicking in [picking for picking in self.browse(cr, uid, ids, context=context) if picking.state == 'assigned']:
            picking_key = make_key(spicking, ('partner_id', 'branch_id', 'division', 'picking_type_id'))
            new_picking = new_pickings.setdefault(picking_key, ({}, []))
            new_picking[1].append(spicking.id)
            picking_infos = new_picking[0]
            picking_lines_to_move.setdefault(picking_key, [])

            if not picking_infos:
                picking_infos.update({
                    'branch_id': spicking.branch_id.id,
                    'division': spicking.division,
                    'origin': spicking.origin,
                    'date': spicking.date,
                    'min_date': spicking.min_date,
                    'partner_id': spicking.partner_id.id,
                    'priority': spicking.priority,
                    'picking_type_id': spicking.picking_type_id.id,
                    'start_date': spicking.start_date,
                    'end_date': spicking.end_date,
                    'backorder_id': False,
                    'date_done': False,
                    'owner_id': spicking.owner_id.id,
                    'state': 'draft',
                    'move_type': 'direct',
                    'invoice_state': 'none',
                    'move_lines': {},
                })
            else:
                if spicking.owner_id.id != False:
                    picking_infos['owner_id'] = spicking.owner_id.id
                if spicking.min_date < picking_infos['min_date']:
                    picking_infos['min_date'] = spicking.min_date
                if spicking.date < picking_infos['date']:
                    picking_infos['date'] = spicking.date
                if spicking.priority > picking_infos['priority']:
                    picking_infos['priority'] = spicking.priority
                if spicking.origin:
                    picking_infos['origin'] = (picking_infos['origin'] or '') + ' ' + spicking.origin

            picking_lines_to_move[picking_key] += [move_lines.id for move_lines in spicking.move_lines
                                               if move_lines.state != 'cancel']

        allpickings = []
        pickings_info = {}
        for picking_key, (picking_data, old_ids) in new_pickings.iteritems():
            if len(old_ids) < 2:
                allpickings += (old_ids or [])
                continue
            for key, value in picking_data['move_lines'].iteritems():
                del value['uom_factor']
                value.update(dict(key))
            picking_data['move_lines'] = [(6, 0, picking_lines_to_move[picking_key])]
            context.update({'mail_create_nolog': True})
            newpicking_id = self.create(cr, uid, picking_data)
            self.message_post(cr, uid, [newpicking_id], body=_("Shipment created"), context=context)
            pickings_info.update({newpicking_id: old_ids})
            allpickings.append(newpicking_id)
            self.unlink(cr, uid , old_ids)

        return pickings_info        

    def print_wizard(self,cr,uid,ids,context=None):
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'stock.picking.wizard.print'), ("model", "=", 'stock.picking'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Print',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
        }
    
    _defaults = {
        'picking_type_id': False,
        'name': False,
        'branch_id': _get_default_branch,
    }
    
    def create(self, cr, uid, vals, context=None):
        ptype_id = vals.get('picking_type_id', False)
        picking_type = self.pool.get('stock.picking.type').browse(cr, uid, ptype_id, context=context)
        code = picking_type.sudo().code
        if context == None:
            context = {}
        if code in ('incoming','interbranch_in') :
            if 'KSU' in context and context['KSU'] == True:
                prefix = 'OIS-KSU'
            else:
                prefix = 'OIS'
        elif code in ('outgoing','interbranch_out') :
            if 'KSU' in context and context['KSU'] == True:
                prefix = 'OOS-KSU'
            else:
                prefix = 'OOS'
        elif code == 'internal' :
            if 'KSU' in context and context['KSU'] == True:
                prefix = 'ITR-KSU'
            else:
                prefix = 'ITR'
        else :
            return super(dym_stock_picking, self).create(cr, uid, vals, context=context)
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], prefix, division=vals['division'])
        return super(dym_stock_picking, self).create(cr, uid, vals, context=context)

    def _create_backorder(self, cr, uid, picking, backorder_moves=[], context=None):
        """ Move all non-done lines into a new backorder picking. If the key 'do_only_split' is given in the context, then move all lines not in context.get('split', []) instead of all non-done lines.
        """
        if context == None:
            context = {}
        if not backorder_moves:
            backorder_moves = picking.move_lines
        backorder_move_ids = [x.id for x in backorder_moves if x.state not in ('done', 'cancel')]
        if 'do_only_split' in context and context['do_only_split']:
            backorder_move_ids = [x.id for x in backorder_moves if x.id not in context.get('split', [])]

        if backorder_move_ids:
            move_obj = self.pool.get("stock.move")
            moves = move_obj.browse(cr, uid, backorder_move_ids)
            ctx = context.copy()
            ctx['KSU'] = True
            for move in moves:
                if move.product_id.categ_id.get_root_name() != 'Extras':
                    del ctx['KSU']
                    break
            backorder_id = self.copy(cr, uid, picking.id, {
                'name': '/',
                'move_lines': [],
                'pack_operation_ids': [],
                'backorder_id': picking.id,
            }, context=ctx)
            backorder = self.browse(cr, uid, backorder_id, context=context)
            self.message_post(cr, uid, picking.id, body=_("Back order <em>%s</em> <b>created</b>.") % (backorder.name), context=context)
            move_obj.write(cr, uid, backorder_move_ids, {'picking_id': backorder_id}, context=context)

            self.write(cr, uid, [picking.id], {'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
            self.action_confirm(cr, uid, [backorder_id], context=context)
            return backorder_id
        return False

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa dihapus jika status bukan 'Draft' !"))
        return super(dym_stock_picking, self).unlink(cr, uid, ids, context=context)
    
    def renew_available(self, cr, uid, ids, context=None):
        picking_id = self.browse(cr, uid, ids, context=None)
        obj_move = self.pool.get('stock.move')
        for move in picking_id.move_lines :
            current_available = obj_move.get_stock_available(cr, uid, ids, move.product_id.id, picking_id.internal_location_id.id, context)
            move.write({'stock_available':current_available})
        return True
    
    def _check_location(self, cr, uid, ids, source_location, destination_location, context=None):
        if source_location == destination_location :
            raise osv.except_osv(('Perhatian !'), ("Source Location dan Destination Location tidak boleh sama !"))
        return True
    
    def action_confirm(self, cr, uid, ids, context=None):
        todo = []
        todo_force_assign = []
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.location_id.usage in ('supplier', 'inventory', 'production') or (picking.branch_id.branch_type == 'MD' and picking.division == 'Unit' and picking.picking_type_id.code == 'outgoing' and not picking.is_reverse) or (picking.division == 'Unit' and picking.picking_type_id.code == 'interbranch_out' and not picking.is_reverse):
                todo_force_assign.append(picking.id)
            for r in picking.move_lines:
                if r.state == 'draft':
                    todo.append(r.id)
        if len(todo):
            self.pool.get('stock.move').action_confirm(cr, uid, todo, context=context)

        if todo_force_assign:
            self.force_assign(cr, uid, todo_force_assign, context=context)
        
        #Custom
        picking_id = self.browse(cr, uid, ids, context=context)
        # if picking_id.state == 'confirmed':
        if picking_id.state in ['draft','confirmed']:
            if picking_id.picking_type_id.code == 'internal' :
                self._check_location(cr, uid, ids, picking_id.internal_location_id, picking_id.internal_location_dest_id, context)
                self.renew_available(cr, uid, ids, context)
                internal_move = {}
                for move in picking_id.move_lines :
                    internal_move[move.product_id] = internal_move.get(move.product_id,0) + move.product_uom_qty
                    if internal_move[move.product_id] > move.stock_available :
                        raise osv.except_osv(('Perhatian !'), ("Quantity product '%s' melebihi stock available" %move.product_id.name))
                self.action_assign(cr, uid, [picking_id.id])
        return True
    
    def write(self, cr, uid, ids, vals, context=None):
        vals.get('move_lines', []).sort(reverse=True)
        return super(dym_stock_picking, self).write(cr, uid, ids, vals, context=context)
    
    def internal_location_change(self, cr, uid, ids, context=None):
        value = {'move_lines': False}
        return {'value':value}
    
    @api.cr_uid_ids_context
    def dym_do_enter_transfer_details(self, cr, uid, picking, context=None):
        if not context:
            context = {}
            
        context.update({
            'active_model': self._name,
            'active_ids': picking,
            'active_id': len(picking) and picking[0] or False
        })
        
        created_id = self.pool['stock.dym_transfer_details'].create(cr, uid, {'picking_id': len(picking) and picking[0] or False}, context)
        return self.pool['stock.dym_transfer_details'].wizard_view(cr, uid, created_id, context)
    
    def type_change(self, cr, uid, ids, type, context=None):
        value = {'internal_location_id': False, 'internal_location_dest_id': False}
        if type :
            obj_type = self.pool.get('stock.picking.type').browse(cr, uid, type)
            value['internal_location_id'] = obj_type.default_location_src_id
        return {'value':value}
    
    def get_ids_move(self, cr, uid, ids, context=None):
        ids_move = []
        picking_id = self.browse(cr, uid, ids)
        for move in picking_id.move_lines :
            ids_move.append(move.id)
        return ids_move
    
    def filter_ids_move(self, cr, uid, ids, context=None):
        product_move = {}
        picking_id = self.browse(cr, uid, ids)
        for move in picking_id.move_lines :
            product_move[move.product_id.id] = []
        for move in picking_id.move_lines :
            product_move[move.product_id.id].append(move.id)
        return product_move
    
    def get_restrict_lot_ids(self, cr, uid, ids, context=None):
        ids_restrict_lot = []
        picking_id = self.browse(cr, uid, ids)
        for move in picking_id.move_lines :
            ids_restrict_lot.append(move.restrict_lot_id.id)
        return ids_restrict_lot
    
    def get_lot_ids_from_pack(self, cr, uid, ids, context=None):
        ids_lot = []
        picking_id = self.browse(cr, uid, ids)
        for pack in picking_id.pack_operation_ids :
            ids_lot.append(pack.lot_id.id)
        return ids_lot
    
    def get_reserve_lot_quant_ids(self, cr, uid, ids, context=None):
        ids_lot_quant = []
        picking_id = self.browse(cr, uid, ids)
        for move in picking_id.move_lines :
            if not move.reserved_quant_ids and move.restrict_lot_id:
                move.do_unreserve()
                move.action_assign()
            if not move.reserved_quant_ids and move.restrict_lot_id and move.location_id.usage in ['internal','kpb','nrfs'] and move.location_dest_id.usage not in ['internal','kpb','nrfs']:
                branch = move.branch_id or move.picking_id.branch_id or move.inventory_id.branch_id
                quant_id = self.pool.get('stock.quant').search(cr, uid, [('lot_id','=',move.restrict_lot_id.id),('lot_id.branch_id','=',branch.id),('location_id.usage','in',['internal','kpb','nrfs'])], limit=1)
                if quant_id:
                    quant_obj = self.pool.get('stock.quant').browse(cr, uid, quant_id)
                    quant_obj.write({'reservation_id':move.id})
            for quant in move.reserved_quant_ids :
                ids_lot_quant.append(quant.lot_id.id)
        return ids_lot_quant
    
    def filter_restrict_lot_ids(self, cr, uid, ids, context=None):
        product_restrict_lot = {}
        picking_id = self.browse(cr, uid, ids)
        for move in picking_id.move_lines :
            product_restrict_lot[move.product_id] = []
        for move in picking_id.move_lines :
            product_restrict_lot[move.product_id].append(move.restrict_lot_id.id)
        return product_restrict_lot
    
    def get_seharusnya(self, cr, uid, ids, context=None):
        qty_seharusnya = {}
        picking_id = self.browse(cr, uid, ids)
        for move in picking_id.move_lines :
            if move.state != 'cancel':
                qty_seharusnya[move.product_id] = qty_seharusnya.get(move.product_id,0) + move.product_uom_qty
        return qty_seharusnya
    
    def get_ids_move_reversed(self, cr, uid, ids, context=None):
        ids_move = self.get_ids_move(cr, uid, ids, context)
        return self.pool.get('stock.move').search(cr, uid, [('origin_returned_move_id','in',ids_move),('state','!=','cancel')])
    
    def get_origin_returned_move_id(self, cr, uid, ids, context=None):
        move_origin = {}
        picking_id = self.browse(cr, uid, ids, context=context)
        for move in picking_id.move_lines :
            move_origin[move.product_id] = []
        for move in picking_id.move_lines :
            for qty in range(int(move.product_uom_qty)):
                move_origin[move.product_id].append(move.id)
        ids_move_reversed = self.get_ids_move_reversed(cr, uid, ids, context)
        if ids_move_reversed :
            for move_reversed_id in self.pool.get('stock.move').browse(cr, uid, ids_move_reversed):
                for qty_reversed in range(int(move_reversed_id.product_uom_qty)):
                    move_origin[move_reversed_id.product_id].remove(move_reversed_id.origin_returned_move_id.id)
        return move_origin
    
    def get_product_ids(self, cr, uid, ids, context=None):
        result = []
        if isinstance(ids,(int,long)):
            ids = [ids]
        for id in ids :
            picking_obj = self.browse(cr,uid,id)
            if picking_obj.move_lines :
                for move_obj in picking_obj.move_lines :
                    result.append(move_obj.product_id.id)
        return result
    
    def get_qty(self, cr, uid, ids, picking_id, product_id, move_qty, context=None):
        qty = 0
        if product_id.categ_id.isParentName('Unit'):
            qty = 1
        elif picking_id.is_reverse or product_id.categ_id.isParentName('Extras'):
            qty = move_qty
        return qty
    
    def convert_rfs(self, cr, uid, ids, rfs, context=None):
        result = False
        if rfs == 'good' :
            result = True
        elif rfs == True :
            result = 'good'
        elif rfs == False :
            result = 'not_good'
        return result

    def _create_extras_order(self, cr, uid, picking, context=None):
        extras = {}

        move_id_unit = -1

        if not picking.move_lines:
            return False
        for move in picking.move_lines:
            if move.product_id.categ_id.isParentName('Unit') and move.state not in ['cancel','draft']:
                if move_id_unit < 0:
                    move_id_unit = move.id
                # for x in move.product_id.product_tmpl_id.extras_line:
                for x in move.product_id.extras_line:
                    if x.product_id in extras:
                        extras[x.product_id] = {'qty':extras[x.product_id]['qty']+(move.product_uom_qty*x.quantity),'line':move.id}
                    else:
                        extras[x.product_id] = {'qty':move.product_uom_qty*x.quantity,'line':move.id}
        if extras:
            """
                Create backoder for extras
            """
            if context is None:
                context = {}
            new_context = dict(context).copy()
            new_context.update({'KSU':True})
            extras_order_id = self.copy(cr, uid, picking.id, {
                    'name':'/',
                    'division':'Umum',
                    'move_lines':[],
                    'pack_operation_ids':[],
                    'backorder_id':picking.id,
                    'move_type':'direct',
                    'invoice_state':'none',
                }, context=new_context)
            extras_order = self.browse(cr, uid, extras_order_id, context=context)
            self.message_post(cr, uid, picking.id, body=_("Extras Order <em>%s</em> <b>created</b>.") % (extras_order.name), context=context)
            stock_move_obj = self.pool.get('stock.move')
            for key, value in extras.items():
                uos_id = key.uos_id and key.uos_id.id or False
                move = stock_move_obj.copy(cr, uid, move_id_unit, {
                    'picking_id':extras_order_id,
                    'categ_id': key.categ_id.id,
                    'product_id':key.id,
                    'name': key.partner_ref,
                    'product_uom': key.uom_id.id,
                    'product_uos': uos_id,
                    'product_uom_qty':value['qty'],
                    'product_uos_qty':value['qty'],
                    'price_unit': 0,
                    'undelivered_value': 0,
                    'move_line_id_extra': value['line'],
                })
            self.action_confirm(cr, uid, [extras_order_id], context=context)
            return extras_order_id
        return False
    
    def _create_interbranch_in(self, cr, uid, picking, context=None):
        if not picking.move_lines :
            return False
        
        obj_mo_id = self.pool.get('dym.mutation.order').browse(cr, uid, picking.transaction_id)
        branch_id = obj_mo_id.sudo().branch_requester_id
        warehouse_id = branch_id.warehouse_id
        picking_type_id = warehouse_id.interbranch_in_type_id
        ids_partner = self.pool.get('res.partner').search(cr, uid, [('branch_id','=',picking.branch_id.id),('default_code','=',picking.branch_id.code)])
        id_partner = False
        if ids_partner :
            id_partner = ids_partner[0]
        user = self.pool.get('res.users').browse(cr, uid, uid)
        picking_vals = {
            'branch_id': branch_id.id,
            'division': picking.division,
            'date': self._get_default_date(cr, uid, context),
            'partner_id': id_partner,
            'start_date': picking.start_date,
            'end_date': picking.end_date,
            'origin': picking.origin,
            'transaction_id': picking.transaction_id,
            'model_id': picking.model_id.id,
            'picking_type_id': picking_type_id.id,
            'company_id': user.company_id.id
        }
        mutation_order_id = self.create(cr, SUPERUSER_ID, picking_vals, context=context)
        stock_move_obj = self.pool.get('stock.move')
        todo_moves = []
        for move in picking.pack_operation_ids :
            default_location_search = self.pool.get('dym.product.location').search(cr, uid, [
                ('branch_id','=',picking.branch_id.id),
                ('product_id','=',move.product_id.id)
                ], order='id desc', limit=1)
            if default_location_search:
                default_location_brw = self.pool.get('dym.product.location').browse(cr, uid, default_location_search)
                location_dest_id = default_location_brw.location_id.id
            else:
                location_dest_id = picking_type_id.default_location_dest_id.id
            moves = {
                'branch_id': picking.branch_id.id,
                'categ_id': move.product_id.categ_id.id,
                'picking_id': mutation_order_id,
                'product_id': move.product_id.id,
                'product_uom': move.product_id.uom_id.id,
                'product_uos': move.product_id.uom_id.id,
                'name': move.product_id.partner_ref,
                'product_uom': move.product_id.uom_id.id,
                'product_uos': move.product_id.uom_id.id,
                'restrict_lot_id': move.lot_id.id,
                'date': self._get_default_date(cr, uid, context),
                'product_uom_qty': move.product_qty,
                'product_uos_qty': move.product_qty,
                'location_id': picking.picking_type_id.default_location_dest_id.id,
                'location_dest_id': location_dest_id,
                'state': 'draft',
                'picking_type_id': picking_type_id.id,
                'procurement_id': False,
                'origin': picking.origin,
                'warehouse_id': warehouse_id.id,
                'price_unit': move.linked_move_operation_ids[0].move_id.price_unit,
                'company_id': user.company_id.id,
            }
            move_create = stock_move_obj.create(cr, uid, moves, context=context)
            todo_moves.append(move_create)
            
        self.action_confirm(cr, SUPERUSER_ID, [mutation_order_id], context=context)
        self.action_assign(cr, SUPERUSER_ID, [mutation_order_id], context=context)
        return mutation_order_id

    def transfer(self, cr, uid, picking, context=None):
        self.write(cr,uid,picking.id,{'confirm_uid':uid,'confirm_date':datetime.now()})
        return True
    
    def write_serial_number(self, cr, uid, picking, context=None):
        if picking.picking_type_id.code == 'internal' and picking.division == 'Unit' :
            for move in picking.move_lines :
                self.pool.get('stock.production.lot').write(cr, uid, move.restrict_lot_id.id, {'location_id':picking.internal_location_dest_id.id, 'picking_id':picking.id})
    
    @api.cr_uid_ids_context
    def do_transfer(self, cr, uid, picking_ids, context=None):
        obj_move = self.pool.get('stock.move')
        ids_move = obj_move.search(cr, uid, [('picking_id','in',picking_ids)])
        move_ids = obj_move.browse(cr, uid, ids_move)
        move_ids.write({'date':datetime.now()})
        res = super(dym_stock_picking, self).do_transfer(cr, uid, picking_ids, context=context)
        """
            If receiving Motorcycle from supplier, do generate picking for Extras
        """
        for picking in self.browse(cr, uid, picking_ids, context=context):
            if (picking.picking_type_code in ('incoming','interbranch_out') or (picking.picking_type_code == 'outgoing' and picking.rel_branch_type == 'MD')) and picking.division == 'Unit' and not picking.is_reverse and picking.retur == False:
                self._create_extras_order(cr, uid, picking, context=context)
            if picking.picking_type_code == 'interbranch_out' :
                self._create_interbranch_in(cr, uid, picking, context=context)
            if picking.picking_type_code == 'internal' :
                picking.date_done = datetime.now()
            self.transfer(cr, uid, picking, context=context)
            self.write_serial_number(cr, uid, picking, context)

        return True

    @api.cr_uid_ids_context
    def do_unreserve(self, cr, uid, picking_ids, context=None):
        """
          Will remove all quants for picking in picking_ids
          except reservation from Dealer Sales Memo Module
        """
        moves_to_unreserve = []
        pack_line_to_unreserve = []
        for picking in self.browse(cr, uid, picking_ids, context=context):
            moves_to_unreserve += [m.id for m in picking.move_lines if m.state not in ('done', 'cancel') and not m.product_id.categ_id.isParentName('Unit') and not m.picking_id.branch_id.branch_type == 'DL']
            pack_line_to_unreserve += [p.id for p in picking.pack_operation_ids]
        if moves_to_unreserve:
            if pack_line_to_unreserve:
                self.pool.get('stock.pack.operation').unlink(cr, uid, pack_line_to_unreserve, context=context)
            self.pool.get('stock.move').do_unreserve(cr, uid, moves_to_unreserve, context=context)
            
    def branch_id_change(self, cr, uid, ids, id_branch, context=None):
        val = {}
        if id_branch :
            obj_picking_type = self.pool.get('stock.picking.type')
            id_picking_type = obj_picking_type.search(cr, uid, [
                                                                ('code','=','internal'),
                                                                ('branch_id','=',id_branch)
                                                                ])[0]
            val['picking_type_id'] = id_picking_type
        return {'value':val}
    
    def get_current_reserved(self, cr, uid, ids, id_product, id_location, ids_move, context=None):
        ids_move = tuple(ids_move)
        cr.execute("""
        SELECT
            sum(q.qty) as quantity
        FROM
            stock_quant q
        LEFT JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and q.reservation_id in %s
        """,(id_product,id_location,ids_move))
        return cr.fetchall()[0][0]
    
    def get_stock_available(self, cr, uid, ids, id_product, id_location, context=None):
        cr.execute("""
        SELECT
            sum(q.qty) as quantity
        FROM
            stock_quant q
        LEFT JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and q.reservation_id is Null 
            and (q.lot_id is Null or l.state = 'stock')
        """,(id_product,id_location))
        qty = cr.fetchall()[0][0]
        if qty < 0:
            qty = 0
        return qty
    
    def get_stock_available_extras(self, cr, uid, ids, id_product, id_location, context=None):
        cr.execute("""
        SELECT
            sum(q.qty) as quantity
        FROM
            stock_quant q
        LEFT JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and q.reservation_id is Null
            and (q.lot_id is Null or l.state = 'stock')
        """,(id_product,id_location))
        qty = cr.fetchall()[0][0]
        if qty < 0:
            qty = 0
        return qty
    
#     @profile
    def create_packing(self, cr, uid, ids, context=None):
        picking_id = self.browse(cr, uid, ids, context=context)
        if picking_id.retur == True:
            for move_line in picking_id.move_lines:
                code = False
                field = False
                retur_line_id = False
                if move_line.retur_beli_line_id.retur_id.retur_type == 'Barang':
                    code = 'outgoing'
                    field = 'retur_beli_line_id'
                    retur_line_id = move_line.retur_beli_line_id.id
                    warning1 = "Pengembalian barang ke supplier belum lengkap"
                elif move_line.retur_jual_line_id.retur_id.retur_type == 'Barang':
                    code = 'incoming'
                    field = 'retur_jual_line_id'
                    retur_line_id = move_line.retur_jual_line_id.id
                    warning1 = "Pengembalian barang dari customer belum lengkap"
                if code and field and retur_line_id:
                    move_search = move_line.search([(field,'=',retur_line_id),('picking_id.picking_type_id.code','=',code),('state','!=','done')])
                    if move_search:
                        raise osv.except_osv(('Perhatian !'), (warning1))
                    else:
                        move_search = move_line.search([('picking_id.origin','=',picking_id.origin),('picking_id.picking_type_id.code','=',code),('state','!=','done'),('retur_beli_line_id','=',False),('retur_jual_line_id','=',False)])
                        if move_search:
                            raise osv.except_osv(('Perhatian !'), (warning1))

        if picking_id.branch_id.branch_type == 'MD' and picking_id.division == 'Unit' and picking_id.picking_type_code == 'incoming' and not picking_id.is_reverse and picking_id.state != 'done' :
            raise osv.except_osv(('Perhatian !'), ("Untuk penerimaan Unit MD silahkan create di menu Showroom > Good Receipt Note MD"))
        packing_draft = self.pool.get('dym.stock.packing').search(cr, uid, [
            ('picking_id','=',picking_id.id),
            ('state','=','draft')
        ])
        if picking_id.state == 'done' or packing_draft :
            return self.view_packing(cr,uid,ids,context)
        
        obj_packing = self.pool.get('dym.stock.packing')
        obj_packing_line = self.pool.get('dym.stock.packing.line')
        branch_sender_id = False
        
        if picking_id.picking_type_code == 'interbranch_in' :
            branch_sender_id = picking_id.location_id.branch_id.id
        packing_vals = {
                        'picking_id': picking_id.id,
                        'branch_sender_id': branch_sender_id,
                        'picking_type_id': picking_id.picking_type_id.id,
                        'division':picking_id.division,
                        }
        id_packing = obj_packing.create(cr, uid, packing_vals, context=context)        
        
        if (picking_id.picking_type_code == 'outgoing' and picking_id.rel_branch_type == 'DL') or picking_id.division == 'Umum' or picking_id.is_reverse :
            ids_move = self.get_ids_move(cr, uid, ids, context)
            for move in picking_id.move_lines:
                if move.state not in ['draft','cancel']:
                    if picking_id.picking_type_code == 'incoming' and not picking_id.is_reverse :
                        current_reserved = 0
                        stock_available = self.get_seharusnya(cr, uid, ids, context)[move.product_id]
                    elif picking_id.is_reverse :
                        current_reserved = self.get_current_reserved(cr, uid, ids, move.product_id.id, move.location_id.id, ids_move, context)
                        if picking_id.picking_type_code in ('outgoing','interbranch_out'):
                            stock_available = self.get_stock_available(cr, uid, ids, move.product_id.id, move.location_id.id, context)
                        else:
                            stock_available = 0
                    elif move.product_id.categ_id.isParentName('Extras') :
                        current_reserved = self.get_current_reserved(cr, uid, ids, move.product_id.id, move.location_id.id, ids_move, context)
                        stock_available = self.get_stock_available_extras(cr, uid, ids, move.product_id.id, move.location_id.id, context)
                    else :
                        current_reserved = self.get_current_reserved(cr, uid, ids, move.product_id.id, move.location_id.id, ids_move, context)
                        stock_available = self.get_stock_available(cr, uid, ids, move.product_id.id, move.location_id.id, context)
                    packing_line_vals = {
                        'packing_id': id_packing,
                        'template_id': move.product_tmpl_id.id,
                        'product_id': move.product_id.id,
                        'quantity': self.get_qty(cr, uid, ids, picking_id, move.product_id, move.product_uom_qty, context),
                        'seharusnya': self.get_seharusnya(cr, uid, ids, context)[move.product_id],
                        'serial_number_id': move.restrict_lot_id.id,
                        'engine_number': move.restrict_lot_id.name,
                        'chassis_number': move.restrict_lot_id.chassis_no,
                        'source_location_id': move.restrict_lot_id.location_id.id if move.restrict_lot_id and move.picking_id.picking_type_code in ('outgoing','interbranch_out','internal') else move.location_id.id,
                        'destination_location_id': move.location_dest_id.id,
                        'tahun_pembuatan': move.restrict_lot_id.tahun,
                        'ready_for_sale': self.convert_rfs(cr, uid, ids, move.restrict_lot_id.ready_for_sale, context),
                        'current_reserved': current_reserved,
                        'stock_available': stock_available,
                        'purchase_line_id': move.purchase_line_id.id,
                        'move_id': move.id,
                    }
                    obj_packing_line.create(cr, uid, packing_line_vals)
        return self.view_packing(cr, uid, ids, context)

    def view_packing(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'dym_stock', 'dym_stock_packing_action'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        packing_ids = []
        picking_id = self.browse(cr, uid, ids, context=context)
        for packing in self.pool.get('dym.stock.packing').search(cr, uid, [('picking_id','=',picking_id.id)]):
            packing_ids.append(packing)
            # Here
            packing_obj = self.pool.get('dym.stock.packing').browse(cr,uid,packing)
            if picking_id.return_id:
                packing_obj.write({'is_returned':True,'return_id':picking_id.return_id.id})
        if not packing_ids :
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan Stock Packing untuk Picking '%s'" %picking_id.name))
        action['context'] = {}
        if len(packing_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, packing_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'dym_stock', 'dym_stock_packing_form_view')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = packing_ids and packing_ids[0] or False 
        return action
    
    def _get_picking_type(self,cr,uid,branch_id):
        picking_type_ids = self.pool.get('stock.picking.type').search(cr,uid,[('branch_id','=',branch_id),('code','in',['outgoing','interbranch_out'])])
        if not picking_type_ids:
            return False
        return picking_type_ids
    
    def _get_location(self,cr,uid,branch_id):
        location_ids = self.pool.get('stock.location').search(cr,uid,[('branch_id','=',branch_id),('usage','=','internal')])
        if not location_ids:
            return False
        return location_ids
    
    def _get_qty_picking(self,cr,uid,branch_id,division,product_id):
        qty_picking_product = 0
        obj_picking = self.pool.get('stock.picking')
        obj_move = self.pool.get('stock.move')
        picking_type = self._get_picking_type(cr, uid, branch_id)
        if picking_type:
            picking_ids = obj_picking.search(cr,uid,[
                ('branch_id','=',branch_id),
                ('division','=',division),
                ('picking_type_id','in',picking_type),
                ('state','not in',('draft','cancel','done'))
            ])
            if picking_ids:
                move_ids = obj_move.search(cr,uid,[('picking_id','in',picking_ids),('product_id','=',product_id)])
                if move_ids:
                    for move in obj_move.browse(cr,uid,move_ids):
                        qty_picking_product+=move.product_uom_qty
        return qty_picking_product
    
    def _get_qty_lot(self,cr,uid,branch_id,product_id):
        qty_lot_product = 0
        obj_lot = self.pool.get('stock.production.lot')
        lot_ids = obj_lot.search(cr,uid,
            [('branch_id','=',branch_id),
            ('product_id','=',product_id),
            '|',('state','in',['intransit']),
            '&',('state','in',['stock']),
            ('location_id.usage','=','internal'),
            ])
        return len(lot_ids)
    
    def _get_qty_quant(self,cr,uid,branch_id,product_id):
        qty_in_quant = 0
        obj_quant = self.pool.get('stock.quant')
        location_ids = self._get_location(cr, uid, branch_id)
        if location_ids:
            quant_ids = obj_quant.search(cr,uid,
                [('location_id','in',location_ids),
                ('product_id','=',product_id),
                ('consolidated_date','!=',False)
                ])
            if quant_ids:
                for quant in obj_quant.browse(cr,uid,quant_ids):
                    qty_in_quant+=quant.qty
        return qty_in_quant
    
    def compare_sale_stock(self,cr,uid,branch_id,division,product_id,qty):
        """ membandingkan qty per product di sale order/mutation order MD + confirmed sale order/mutation dengan stock RFS
        jika qty penjumlahan tsb melebihi stock maka tidak bisa continue
        """
        picking_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        if division=='Unit':
            qty_in_picking = self._get_qty_picking(cr,uid,branch_id,division,product_id)
            qty_in_lot = self._get_qty_lot(cr, uid, branch_id, product_id)
            # if (qty_in_picking+qty)>qty_in_lot:
            if qty>qty_in_lot:
                raise osv.except_osv(('Tidak Bisa Confirm !'), 
                 ("Stock product %s tidak mencukupi Jumlah Stock yang ada %s, Stock yang sedang dalam proses %s , Qty di SO %s" % (self.pool.get('product.product').browse(cr,uid,product_id)['name'],qty_in_lot,qty_in_picking,qty) ))
        elif division=='Sparepart':
            qty_in_picking = self._get_qty_picking(cr,uid,branch_id,division,product_id)
            qty_in_quant = self._get_qty_quant(cr, uid, branch_id, product_id)
            if (qty_in_picking+qty)>qty_in_quant:
                raise osv.except_osv(('Tidak Bisa Confirm !'), ("Stock product %s tidak mencukupi Jumlah Stock yang ada %s, Stock yang sedang dalam proses %s , Qty di SO %s" % (self.pool.get('product.product').browse(cr,uid,product_id)['name'],qty_in_quant,qty_in_picking,qty) ))
        return True

    
    def get_purchase_line_id(self, cr, uid, ids, id_product, context=None):
        picking_id = self.browse(cr, uid, ids, context=context)
        id_purchase_line = 0
        for move in picking_id.move_lines :
            if move.product_id.id == id_product :
                id_purchase_line = move.purchase_line_id.id
        return id_purchase_line
    
class dym_stock_inventory(osv.osv):
    _inherit = ['stock.inventory']
    _columns = {
        'confirm_uid':fields.many2one('res.users',string="Validated by"),
        'confirm_date':fields.datetime('Validated on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on')
    }
    
    def action_cancel_draft(self, cr, uid, ids, context=None):
        vals = super(dym_stock_inventory, self).action_cancel_draft(cr, uid, ids, context=context)
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})
        return vals
    
    def action_done(self, cr, uid, ids, context=None):
        vals = super(dym_stock_inventory, self).action_done(cr, uid, ids, context=context)
        self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now()})
        return vals
    
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Inventory adjustment yang sudah divalidasi, data tidak bisa didelete !"))
        return super(dym_stock_inventory, self).unlink(cr, uid, ids, context=context)           
