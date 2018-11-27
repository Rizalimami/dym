import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _, workflow
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
import time
from openerp.osv import osv
from openerp.tools.translate import _
import pdb

class dym2_account_voucher_prepaid_state(models.Model):
    _inherit = 'account.voucher'

    @api.depends('line_dr_ids.prepaid_id')
    def _check_prepaid(self):
        for voucher in self:
            prepaid_state = True
            if voucher.payment_request_type in ['prepaid','cip']:
                for line in voucher.line_dr_ids:
                    if not line.prepaid_id:
                        prepaid_state = False
                    break
            voucher.prepaid_state = prepaid_state                    
    prepaid_state = fields.Boolean(string='Prepaid State', compute='_check_prepaid', readonly=True, store=True)

class dym_account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'
    
    cip_count = fields.Float(string='CIP Count')

class dym_account_invoice(models.Model):
    _inherit = 'account.invoice'

    @api.one
    def _check_po_asset_prepaid(self):
        po_obj = self.env['purchase.order'].search([('invoice_ids','in',self.id)])[0]
        self.po_asset_prepaid = False
        if po_obj.asset == True:
            self.po_asset_prepaid = 'asset'
            other_type = self.env['purchase.order'].search([('invoice_ids','in',self.id),('asset','=',False)])
            if other_type:
                self.po_asset_prepaid = False
        elif po_obj.prepaid == True:
            self.po_asset_prepaid = 'prepaid'
            other_type = self.env['purchase.order'].search([('invoice_ids','in',self.id),('prepaid','=',False)])
            if other_type:
                self.po_asset_prepaid = False
        elif po_obj.prepaid == False and po_obj.asset == False:
            self.po_asset_prepaid = 'normal'
            other_type = self.env['purchase.order'].search([('invoice_ids','in',self.id),'|',('prepaid','=',True),('asset','=',True)])
            if other_type:
                self.po_asset_prepaid = False

    @api.depends('invoice_line.cip_count','is_cip')
    def _check_cip(self):
        for invoice in self:
            cip_state = True
            if invoice.is_cip == True:
                for line in invoice.invoice_line:
                    if line.quantity > line.cip_count:
                        cip_state = False
                    break
            invoice.cip_state = cip_state                
    
    is_cip = fields.Boolean(string='Is CIP')
    cip_state = fields.Boolean(string='CIP State', compute='_check_cip', readonly=True, store=True)
    po_asset_prepaid = fields.Selection([('normal','Normal'),('asset','Asset'),('prepaid','Prepaid')], string='Asset / Prepaid PO', compute='_check_po_asset_prepaid')

    def _get_product_return_moves(self, pick):
        result1 = []
        uom_obj = self.env['product.uom']
        pick_obj = self.env['stock.picking']
        quant_obj = self.env["stock.quant"]
        chained_move_exist = False
        if pick:
            if pick.state != 'done':
                raise osv.except_osv(_('Warning!'), _("You may only return pickings that are Done!"))

            for move in pick.move_lines:
                if move.move_dest_id:
                    chained_move_exist = True
                #Sum the quants in that location that can be returned (they should have been moved by the moves that were included in the returned picking)
                qty = 0
                quant_search = quant_obj.search([('history_ids', 'in', move.id), ('qty', '>', 0.0), ('location_id', 'child_of', move.location_dest_id.id)])
                for quant in quant_search:
                    if not quant.reservation_id or quant.reservation_id.origin_returned_move_id.id != move.id:
                        qty += quant.qty
                qty = uom_obj._compute_qty(move.product_id.uom_id.id, qty, move.product_uom.id)
                result1.append({'product_id': move.product_id.id, 'quantity': qty, 'move_id': move.id})

            if len(result1) == 0:
                raise osv.except_osv(_('Warning!'), _("No products to return (only lines in Done state and not fully returned yet can be returned)!"))
        return result1

    @api.multi
    def _create_returns(self, pick):
        move_obj = self.env['stock.move']
        pick_obj = self.env['stock.picking']
        uom_obj = self.env['product.uom']
        data_obj = self.env['stock.return.picking.line']
        product_return_moves = self._get_product_return_moves(pick)
        returned_lines = 0

        # Cancel assignment of existing chained assigned moves
        moves_to_unreserve = []
        for move in pick.move_lines:
            to_check_moves = [move.move_dest_id] if move.move_dest_id.id else []
            while to_check_moves:
                current_move = to_check_moves.pop()
                if current_move.state not in ('done', 'cancel') and current_move.reserved_quant_ids:
                    moves_to_unreserve.append(current_move.id)
                split_move_ids = move_obj.search([('split_from', '=', current_move.id)])
                if split_move_ids:
                    to_check_moves += split_move_ids

        if moves_to_unreserve:
            move_to_unreserve_obj = move_obj.search([('id', 'in', moves_to_unreserve)])
            move_to_unreserve_obj.do_unreserve()
            #break the link between moves in order to be able to fix them later if needed
            move_to_unreserve_obj.write({'move_orig_ids': False})

        #Create new picking for returned products
        pick_type_id = pick.picking_type_id.return_picking_type_id and pick.picking_type_id.return_picking_type_id.id or pick.picking_type_id.id
        new_picking = pick.copy({
            'move_lines': [],
            'picking_type_id': pick_type_id,
            'state': 'draft',
            'origin': pick.name,
        })
        for data_get in product_return_moves:
            move = move_obj.search([('id','=',data_get['move_id'])])
            if not move:
                raise osv.except_osv(_('Warning !'), _("You have manually created product lines, please delete them to proceed"))
            new_qty = data_get['quantity']
            if new_qty:
                # The return of a return should be linked with the original's destination move if it was not cancelled
                if move.origin_returned_move_id.move_dest_id.id and move.origin_returned_move_id.move_dest_id.state != 'cancel':
                    move_dest_id = move.origin_returned_move_id.move_dest_id.id
                else:
                    move_dest_id = False

                returned_lines += 1
                move.copy({
                    'product_id': data_get['product_id'],
                    'product_uom_qty': new_qty,
                    'product_uos_qty': new_qty * move.product_uos_qty / move.product_uom_qty,
                    'picking_id': new_picking.id,
                    'state': 'draft',
                    'location_id': move.location_dest_id.id,
                    'location_dest_id': move.location_id.id,
                    'picking_type_id': pick_type_id,
                    'origin_returned_move_id': move.id,
                    'restrict_lot_id': move.restrict_lot_id.id,
                    'move_dest_id': move_dest_id,
                })

        if not returned_lines:
            raise osv.except_osv(_('Warning!'), _("Please specify at least one non-zero quantity."))
        new_picking.action_confirm()
        new_picking.do_transfer()
        return new_picking, pick_type_id

    @api.multi
    def invoice_change_asset(self) :
        if self.state in ('paid','cancel'):
            raise osv.except_osv(('Perhatian !'), ("Invoice %s sudah diproses!")%(self.number))
        if (self.asset == True and (self.po_asset_prepaid in ['asset','prepaid'])) or self.tipe != 'purchase':
            return True
        po_obj = self.env['purchase.order'].search([('invoice_ids','in',self.id)])
        for picking in po_obj.picking_ids:
            for move in picking.move_lines :
                if move.consolidated_qty > 0 or picking.consolidated == True:
                    raise osv.except_osv(('Perhatian !'), ("Shipment %s sudah di consolidate!")%(picking.name))
            if picking.returned_for_asset_change == True or picking.state == 'cancel':
                continue
            elif picking.state == 'done':
                new_picking_id, pick_type_id = self._create_returns(picking)
                picking.write({'returned_for_asset_change':True})
            elif picking.state not in ('cancel','done'):
                picking.move_lines.action_cancel()

        receive_asset_obj = self.env['dym2.receive.asset']
        for inv_line in self.invoice_line:
            if inv_line.consolidated_qty > 0 or self.consolidated == True:
                raise osv.except_osv(('Perhatian !'), ("Invoice %s sudah di consolidate!")%(self.number))
            receive_line = []
            receive_line.append([0,False,{
                    'purchase_line_id': inv_line.purchase_line_id.id,
                    'product_id': inv_line.product_id.id,
                    'price_unit': inv_line.price_subtotal / inv_line.quantity,
                    'quantity': inv_line.quantity,
                    'description': inv_line.name,             
                }])
            if po_obj.asset == True:
                asset_prepaid = 'asset'
                po_obj.write({'asset':True,'asset_receive':False,'asset_receive_qty':0})
            if po_obj.prepaid == True:
                asset_prepaid = 'prepaid'
                po_obj.write({'asset':True,'asset_receive':False,'asset_receive_qty':0})
            receive_id = receive_asset_obj.create({
                           'purchase_id' : po_obj.id,
                           'asset_prepaid' : asset_prepaid,
                           'receive_line_ids':receive_line}) 
        self.write({'asset':True})
        po_obj.write({'asset_receive':False,'asset_receive_qty':0})
        for order_line in po_obj.order_line:
            order_line.write({'asset_receive':False,'asset_receive_qty':0,'received':0})
        return True


    @api.multi
    def invoice_change_normal(self) :
        if self.state in ('paid','cancel'):
            raise osv.except_osv(('Perhatian !'), ("Invoice %s sudah diproses!")%(self.number))
        if self.asset == False or self.tipe != 'purchase':
            return True
        po_obj = self.env['purchase.order'].search([('invoice_ids','=',self.id)])
        for receiving in self.env['dym2.receive.asset'].search([('purchase_id','=',po_obj.id)]):
            if receiving.state == 'cancel':
                continue
            for line in receiving.receive_line_ids :
                if line.consolidated_qty > 0 or receiving.consolidated == True:
                    raise osv.except_osv(('Perhatian !'), ("Asset %s sudah di consolidate!")%(receiving.name))
                elif receiving.state != 'cancel':
                    receiving.write({'state':'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})

        picking_vals = {
            'picking_type_id': po_obj.picking_type_id.id,
            'partner_id': po_obj.dest_address_id.id or po_obj.partner_id.id,
            'date': po_obj.date_order,
            'start_date': po_obj.start_date,
            'end_date': po_obj.end_date,
            'origin': po_obj.name,
            'branch_id': po_obj.branch_id.id,
            'division': po_obj.division,
            'transaction_id': po_obj.id,
            'model_id': self.env['ir.model'].search([('model','=',po_obj.__class__.__name__)])[0].id,
        }
        picking_id = self.env['stock.picking'].create(picking_vals)
        self.env['purchase.order']._create_stock_moves(po_obj, po_obj.order_line, picking_id.id)

        self.write({'asset':False})
        po_obj.write({'asset':False,'asset_receive':False,'asset_receive_qty':0})
        for order_line in po_obj.order_line:
            order_line.write({'asset_receive':False,'asset_receive_qty':0,'received':0})
        return True

class dym2_stock_picking(models.Model):
    _inherit = 'stock.picking'

    returned_for_asset_change = fields.Boolean('Returned for asset change')