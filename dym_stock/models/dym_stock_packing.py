from openerp import models, fields, api, _, SUPERUSER_ID
import time
from datetime import datetime
from openerp.osv import osv
import string
import openerp.addons.decimal_precision as dp

class dym_stock_location(models.Model):
    _inherit = "stock.location"
    
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], string='Division')

class dym_stock_packing(models.Model):
    _name = "dym.stock.packing"
    _description = "Stock Packing"
    
    def _is_reverse(self):
        # print "aaaaaaaaaaaaaaaaaaaaaaaaaaaa", self.rel_origin[:3]
        reverse_incoming = self.rel_code == 'outgoing' and self.rel_destination_location_id.usage == 'supplier'
        reverse_outgoing = self.rel_code == 'incoming' and self.rel_source_location_id.usage == 'customer'
        self.is_reverse = reverse_incoming or reverse_outgoing
        # if self.rel_origin[:3] == 'WOR':
        #     self.is_wor = self.rel_origin
    
    @api.model
    def check_split(self):
        extra = False
        not_extra = False
        check_split = 0
        for line in self.packing_line:
            if line.product_id.categ_id.isParentName('Extras'):
                extra = True
            else:
                not_extra = True
        if extra == True and not_extra == True:
            return 1
        return 0

    @api.model
    def get_faktur_no(self):
        return self.env['account.invoice'].search([('name','ilike',self.picking_id.origin)], order='id asc', limit=1).supplier_invoice_number

    @api.model
    def get_approval_po(self):
        return self.env['purchase.order'].search([('name','ilike',self.picking_id.origin)], order='id asc', limit=1).confirm_uid.name or '(_________________)'

    @api.model
    def get_product_name(self, name=None):
        try:
            list_1 = name.split("[")
            list_2 = [(x.replace("]", "")).strip(" ") for x in list_1]
            if (list_2[1]==""):
                return list_2[0]
            else:
                return list_2[1]
        except Exception as e:
            return name

    @api.model
    def _get_default_date(self):
        return self.env['dym.branch'].get_default_date_model()
    
    name = fields.Char('Packing Ref.')
    state = fields.Selection([
        ('draft','Draft'),
        ('reserved','Reserved'),
        ('posted','Posted'),
        ('cancelled','Cancelled'),
        ], 'State', default='draft')
    picking_id = fields.Many2one('stock.picking', 'Picking Ref.')
    branch_id = fields.Many2one('dym.branch', 'Branch')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General')], string='Division')
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type')
    source_location_id = fields.Many2one('stock.location', 'Source Location')
    destination_location_id = fields.Many2one('stock.location', 'Destination Location')
    rel_picking_type_id = fields.Many2one(related='picking_id.picking_type_id', string='Picking Type')
    rel_branch_id = fields.Many2one(related='picking_id.picking_type_id.branch_id', string='Branch')
    rel_source_location_id = fields.Many2one(related='picking_id.location_id', string='Source Location')
    rel_destination_location_id = fields.Many2one(related='picking_id.location_dest_id', string='Destination Location')
    nrfs_location = fields.Many2one('stock.location', 'NRFS Location')
    rel_origin = fields.Char(related='picking_id.origin', string='Source Document')
    rel_partner_id = fields.Many2one(related='picking_id.partner_id', string='Partner')
    branch_sender_id = fields.Many2one('dym.branch', 'Branch Sender')
    expedition_id = fields.Many2one('res.partner','Ekspedisi')
    plat_number_id = fields.Many2one('dym.plat.number.line','Nopol Ekspedisi')
    driver_id = fields.Many2one('dym.driver.line','Sopir Ekspedisi')
    date = fields.Date('Date')
    rel_division = fields.Selection(related='picking_id.division', string='Jenis Barang')
    rel_code = fields.Selection(related='picking_id.picking_type_id.code', string='Code')
    rel_branch_type = fields.Selection(related='picking_id.branch_id.branch_type', string='Branch Type')
    is_reverse = fields.Boolean(compute='_is_reverse', string="Is Reverse", method=True)
    is_wor = fields.Boolean(compute='_is_reverse', string="Is WOR", method=True)
    packing_line = fields.One2many('dym.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line2 = fields.One2many('dym.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line3 = fields.One2many('dym.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line4 = fields.One2many('dym.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line5 = fields.One2many('dym.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line6 = fields.One2many('dym.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line7 = fields.One2many('dym.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line8 = fields.One2many('dym.stock.packing.line', 'packing_id', 'Packing Line')
    rel_serial_number_id = fields.Char(related='packing_line.serial_number_id.name', string='Serial Number')
    invoice_id = fields.Many2one('account.invoice', 'Invoice')
    move_id = fields.Many2one(related='invoice_id.move_id', string='Journal Item')
    sj_date = fields.Date('Tanggal Surat Jalan')
    sj_no = fields.Char('Nomor Surat Jalan')
    # import_sj = fields.Boolean("Import Surat Jalan")
    # sj_id = fields.Many2one('po.sj.import', 'Nomor Surat Jalan')
    # no_faktur = fields.Char(string="Supplier Invoice Number", compute="_get_no_supplier_invoice")

    @api.onchange('import_sj')
    def onchange_import_sj(self):
        if not self.import_sj:
            self.sj_id = False
            self.sj_no = False
            self.no_faktur = False

    def _get_no_supplier_invoice(self):
        if self.sj_id:
            self.no_faktur = self.sj_id.no_faktur
    
    def print_wizard(self,cr,uid,ids,context=None):
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dym.stock.packing.wizard.print'), ("model", "=", 'dym.stock.packing'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Print',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dym.stock.packing',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
            }
    
    def write(self, cr, uid, ids, vals, context=None):
        packing_id = self.browse(cr, uid, ids, context=context)
        #<!-- 1 incoming-unit-dealer, incoming-unit-maindealer-new -->
        if (packing_id.rel_code == 'incoming' and packing_id.rel_division == 'Unit' and packing_id.rel_branch_type == 'DL' and not packing_id.is_reverse) or not packing_id.picking_id :
            vals.get('packing_line', []).sort(reverse=True)
            vals.pop('packing_line2',None)
            vals.pop('packing_line3',None)
            vals.pop('packing_line4',None)
            vals.pop('packing_line5',None)
            vals.pop('packing_line6',None)
            vals.pop('packing_line7',None)
            vals.pop('packing_line8',None)
        #<!-- 2 outgoing-unit-dealer, interbranch_out-unit-dealer, interbranch_in-unit-dealer -->
        elif packing_id.rel_code in ('outgoing','interbranch_out','interbranch_in') and packing_id.rel_division == 'Unit' and packing_id.rel_branch_type == 'DL' and not packing_id.is_reverse :
            vals.get('packing_line2', []).sort(reverse=True)
            vals.pop('packing_line',None)
            vals.pop('packing_line3',None)
            vals.pop('packing_line4',None)
            vals.pop('packing_line5',None)
            vals.pop('packing_line6',None)
            vals.pop('packing_line7',None)
            vals.pop('packing_line8',None)
        #<!-- 3 incoming-sparepart-dealer, incoming-umum-dealer, incoming-sparepart-maindealer, incoming-umum-maindealer -->
        elif packing_id.rel_code == 'incoming' and packing_id.rel_division in ('Sparepart','Umum') and not packing_id.is_reverse :
            vals.get('packing_line3', []).sort(reverse=True)
            vals.pop('packing_line',None)
            vals.pop('packing_line2',None)
            vals.pop('packing_line4',None)
            vals.pop('packing_line5',None)
            vals.pop('packing_line6',None)
            vals.pop('packing_line7',None)
            vals.pop('packing_line8',None)
        #<!-- 4 outgoing-sparepart-dealer, outgoing-umum-dealer, interbranch_out-sparepart-dealer, interbranch_out-umum-dealer, interbranch_in-sparepart-dealer, interbranch_in-umum-dealer,
        #outgoing-sparepart-maindealer, outgoing-umum-maindealer, interbranch_out-sparepart-maindealer, interbranch_out-umum-maindealer, interbranch_in-sparepart-maindealer, interbranch_in-umum-maindealer -->
        elif packing_id.rel_code in ('outgoing','interbranch_out','interbranch_in') and packing_id.rel_division in ('Sparepart','Umum') and not packing_id.is_reverse :
            vals.get('packing_line4', []).sort(reverse=True)
            vals.pop('packing_line',None)
            vals.pop('packing_line2',None)
            vals.pop('packing_line3',None)
            vals.pop('packing_line5',None)
            vals.pop('packing_line6',None)
            vals.pop('packing_line7',None)
            vals.pop('packing_line8',None)
        #<!-- 5 reverse-incoming-unit-dealer, reverse-outgoing-unit-dealer, reverse-incoming-unit-maindealer, reverse-outgoing-unit-maindealer -->
        elif ((packing_id.rel_code in ('incoming','outgoing') and packing_id.rel_branch_type == 'DL') or (packing_id.rel_code in ('incoming','outgoing') and packing_id.rel_branch_type == 'MD')) and packing_id.rel_division == 'Unit' and packing_id.is_reverse :
            vals.get('packing_line5', []).sort(reverse=True)
            vals.pop('packing_line',None)
            vals.pop('packing_line2',None)
            vals.pop('packing_line3',None)
            vals.pop('packing_line4',None)
            vals.pop('packing_line6',None)
            vals.pop('packing_line7',None)
            vals.pop('packing_line8',None)
        #<!-- 6 reverse-incoming-sparepart-dealer, reverse-incoming-umum-dealer, reverse-outgoing-sparepart-dealer, reverse-outgoing-umum-dealer, reverse-outgoing-sparepart-maindealer, reverse-outgoing-umum-maindealer -->
        elif ((packing_id.rel_code in ('incoming','outgoing') and packing_id.rel_division in ('Sparepart','Umum') and packing_id.rel_branch_type == 'DL') or (packing_id.rel_code in ('incoming','outgoing') and packing_id.rel_division in ('Sparepart','Umum') and packing_id.rel_branch_type == 'MD')) and packing_id.is_reverse :
            vals.get('packing_line6', []).sort(reverse=True)
            vals.pop('packing_line',None)
            vals.pop('packing_line2',None)
            vals.pop('packing_line3',None)
            vals.pop('packing_line4',None)
            vals.pop('packing_line5',None)
            vals.pop('packing_line7',None)
            vals.pop('packing_line8',None)
        #<!-- 7 incoming-unit-maindealer -->
        elif packing_id.rel_code == 'incoming' and packing_id.rel_division == 'Unit' and packing_id.rel_branch_type == 'MD' and not packing_id.is_reverse :
            vals.get('packing_line7', []).sort(reverse=True)
            vals.pop('packing_line',None)
            vals.pop('packing_line2',None)
            vals.pop('packing_line3',None)
            vals.pop('packing_line4',None)
            vals.pop('packing_line5',None)
            vals.pop('packing_line6',None)
            vals.pop('packing_line8',None)
        #<!-- 8 outgoing-unit-maindealer, interbranch_out-unit-maindealer, interbranch_in-unit-maindealer -->
        elif packing_id.rel_code in ('outgoing','interbranch_out','interbranch_in') and packing_id.rel_division == 'Unit' and packing_id.rel_branch_type == 'MD' and not packing_id.is_reverse :
            vals.get('packing_line8', []).sort(reverse=True)
            vals.pop('packing_line',None)
            vals.pop('packing_line2',None)
            vals.pop('packing_line3',None)
            vals.pop('packing_line4',None)
            vals.pop('packing_line5',None)
            vals.pop('packing_line6',None)
            vals.pop('packing_line7',None)
        
        if packing_id.rel_code == 'interbranch_out' and packing_id.rel_division == 'Unit' and packing_id.rel_branch_type == 'DL' and not packing_id.is_reverse :
            filter_ids_move = packing_id.picking_id.filter_ids_move()
            obj_quant = self.pool.get('stock.quant')
            obj_packing_line = self.pool.get('dym.stock.packing.line')
            for line in vals.get('packing_line2', []) :
                if line[0] == 1 and line[2].get('serial_number_id') or line[0] == 2 :
                    packing_line = obj_packing_line.browse(cr, uid, line[1])
                    id_quant = obj_quant.search(cr, SUPERUSER_ID, [('lot_id','=',packing_line.serial_number_id.id)])
                    obj_quant.write(cr, SUPERUSER_ID, id_quant, {'reservation_id':False})
                if line[0] == 1 and line[2].get('serial_number_id') or line[0] == 0 :
                    id_quant = obj_quant.search(cr, SUPERUSER_ID, [('lot_id','=',line[2].get('serial_number_id'))])
                    prod_id = line[2].get('product_id')
                    if not prod_id :
                        prod_id = obj_packing_line.browse(cr, SUPERUSER_ID, line[1]).product_id.id
                    obj_quant.write(cr, SUPERUSER_ID, id_quant, {'reservation_id':filter_ids_move[prod_id][0]})
                    
        elif packing_id.rel_code in ('outgoing','interbranch_out') and packing_id.rel_branch_type == 'MD' and packing_id.rel_division == 'Unit' and not packing_id.is_reverse :
            filter_ids_move = packing_id.picking_id.filter_ids_move()
            obj_quant = self.pool.get('stock.quant')
            obj_packing_line = self.pool.get('dym.stock.packing.line')
            
            for line in vals.get('packing_line8', []) :
                if line[0] == 1 and line[2].get('serial_number_id') or line[0] == 2 :
                    packing_line = obj_packing_line.browse(cr, uid, line[1])
                    id_quant = obj_quant.search(cr, SUPERUSER_ID, [('lot_id','=',packing_line.serial_number_id.id)])
                    obj_quant.write(cr, SUPERUSER_ID, id_quant, {'reservation_id':False})
                if line[0] == 1 and line[2].get('serial_number_id') or line[0] == 0 :
                    id_quant = obj_quant.search(cr, SUPERUSER_ID, [('lot_id','=',line[2].get('serial_number_id'))])
                    prod_id = line[2].get('product_id')
                    if not prod_id :
                        prod_id = obj_packing_line.browse(cr, SUPERUSER_ID, line[1]).product_id.id
                    obj_quant.write(cr, SUPERUSER_ID, id_quant, {'reservation_id':filter_ids_move[prod_id][0]})
                    
        if packing_id.rel_code in ('outgoing','interbranch_out') or packing_id.is_reverse :
            self.renew_available_and_reserved(cr, uid, ids, context)
        return super(dym_stock_packing, self).write(cr, uid, ids, vals, context=context)
    
    @api.one
    def renew_available_and_reserved(self):
        ids_move = self.picking_id.get_ids_move()
        for packing_line in self.packing_line :
            if self.is_reverse :
                if self.rel_code in ('outgoing','interbranch_out'):
                    stock_available = self.picking_id.get_stock_available(packing_line.product_id.id, packing_line.source_location_id.id)
                else:
                    stock_available = 0
                current_reserved = self.picking_id.get_current_reserved(packing_line.product_id.id,packing_line.source_location_id.id,ids_move)
            elif packing_line.product_id.categ_id.isParentName('Extras') :
                stock_available = self.picking_id.get_stock_available_extras(packing_line.product_id.id, packing_line.source_location_id.id)
                current_reserved = self.picking_id.get_current_reserved(packing_line.product_id.id,packing_line.source_location_id.id,ids_move)
            else :
                stock_available = self.picking_id.get_stock_available(packing_line.product_id.id, packing_line.source_location_id.id)
                stock_moves = self.env['stock.move'].browse(ids_move)
                current_reserved = self.picking_id.get_current_reserved(packing_line.product_id.id,packing_line.source_location_id.id,ids_move)
            packing_line.write({'stock_available':stock_available, 'current_reserved':current_reserved})
    
    @api.multi
    def _is_over_qty(self):
        todo_move = {}
        qty = {}
        for packing_line in self.packing_line :
            if packing_line.quantity <= 0 :
                raise osv.except_osv(('Perhatian !'), ("Quantity tidak boleh nol atau kurang dari 1 !"))
            qty[packing_line.product_id] = qty.get(packing_line.product_id,0) + packing_line.quantity
            if qty[packing_line.product_id] > packing_line.seharusnya :
                raise osv.except_osv(('Perhatian !'), ("Quantity product '%s' melebihi qty seharusnya\nsilahkan cek kembali !" %packing_line.product_id.name))
            if packing_line.product_id not in todo_move :
                todo_move[packing_line.product_id] = {packing_line.source_location_id : 0}
            else :
                todo_move[packing_line.product_id].update({packing_line.source_location_id : 0})

        if self.rel_code in ('outgoing','interbranch_out','interbranch_in') or self.rel_code in ('outgoing') and self.is_reverse:
            for packing_line in self.packing_line :
                todo_move[packing_line.product_id][packing_line.source_location_id] += packing_line.quantity
                if todo_move[packing_line.product_id][packing_line.source_location_id] > (packing_line.stock_available + packing_line.current_reserved) :
                    raise osv.except_osv(('Perhatian !'), ("Quantity product '%s' melebihi current reserve dan stock available\nsilahkan cek kembali !" %packing_line.product_id.name))
    
    @api.multi
    def _check_serial_number(self):
        for packing_line in self.packing_line :
            if self.is_reverse or (self.rel_code in ('outgoing','interbranch_out','interbranch_in') and self.rel_division == 'Unit') or (self.rel_code == 'incoming' and self.rel_branch_type == 'MD') :
                if packing_line.product_id.categ_id.isParentName('Unit') and not packing_line.serial_number_id :
                    raise osv.except_osv(('Perhatian !'), ("Silahkan isi Serial Number untuk produk '%s'" %packing_line.product_id.name))
        return True
    
    @api.multi
    def _update_lot(self, picking_id):
        if self.rel_division == "Unit" or not self.picking_id :
            if self.rel_code == "interbranch_out" and not self.is_reverse :
                for packing_line in self.packing_line :
                    packing_line.serial_number_id.write({'location_id':packing_line.destination_location_id.id,'picking_id':self.picking_id.id,'branch_id':self.rel_branch_id.id,'ready_for_sale':packing_line.convert_rfs(packing_line.rel_ready_for_sale) or packing_line.convert_rfs(packing_line.ready_for_sale),'performance_hpp':packing_line.performance_hpp,'expedisi_id':self.expedition_id.id,'freight_cost':packing_line.freight_cost})
            elif self.rel_code in ("outgoing","interbranch_in") and not self.is_reverse :
                for packing_line in self.packing_line :
                    if self.rel_code == 'outgoing' and self.rel_branch_type == 'MD' :
                        packing_line.serial_number_id.write({'location_id':packing_line.destination_location_id.id,'picking_id':self.picking_id.id,'branch_id':self.rel_branch_id.id,'ready_for_sale':packing_line.convert_rfs(packing_line.rel_ready_for_sale) or packing_line.convert_rfs(packing_line.ready_for_sale),'state':'sold','dealer_id':packing_line.packing_id.rel_partner_id.id,'sales_md_date':packing_line.packing_id.picking_id.date,'do_md_date':self._get_default_date(),'expedisi_id':self.expedition_id.id,'freight_cost':packing_line.freight_cost})
                    else :
                        packing_line.serial_number_id.write({'location_id':self.get_destination_location(packing_line.ready_for_sale, packing_line.rel_ready_for_sale, packing_line.destination_location_id.id),'picking_id':self.picking_id.id,'branch_id':self.rel_branch_id.id,'ready_for_sale':packing_line.convert_rfs(packing_line.rel_ready_for_sale) or packing_line.convert_rfs(packing_line.ready_for_sale),'expedisi_id':self.expedition_id.id,'freight_cost':packing_line.freight_cost})
            elif self.rel_code == 'incoming' and self.rel_branch_type == 'DL' and self.is_reverse :
                for packing_line in self.packing_line :
                    packing_line.serial_number_id.write({'location_id':self.get_destination_location(packing_line.ready_for_sale, packing_line.rel_ready_for_sale, packing_line.destination_location_id.id),'picking_id':self.picking_id.id,'branch_id':self.rel_branch_id.id,'ready_for_sale':packing_line.convert_rfs(packing_line.rel_ready_for_sale) or packing_line.convert_rfs(packing_line.ready_for_sale),'state':'stock','expedisi_id':self.expedition_id.id,'freight_cost':packing_line.freight_cost})
            elif self.branch_id.branch_type == 'MD' and not self.picking_id :
                for packing_line in self.packing_line :
                    packing_line.serial_number_id.write({
                        'location_id':self.get_destination_location(packing_line.ready_for_sale, packing_line.rel_ready_for_sale, packing_line.destination_location_id.id),
                        'picking_id':picking_id.id,
                        'ready_for_sale':packing_line.convert_rfs(packing_line.ready_for_sale),
                        'state':'stock',
                        'po_date':picking_id.date,
                        'supplier_id':picking_id.partner_id.id,
                        'expedisi_id':self.expedition_id.id,
                        'freight_cost':packing_line.freight_cost,
                    })
    
    @api.multi
    def _delete_lot(self):
        if self.rel_code == 'outgoing' and self.is_reverse :
            for packing_line in self.packing_line :
                packing_line.serial_number_id.unlink()
    
    @api.multi
    def _update_packing(self):
        prefix = False
        if self.rel_code == 'incoming':
            prefix = 'GRN'
        elif self.rel_code == 'outgoing':
            prefix = 'DNO'
        if prefix:
            sequence = self.env['ir.sequence'].get_per_branch(self.rel_branch_id.id or self.branch_id.id or self.picking_id.branch_id.id, prefix, division=self.rel_division or self.division)
        else:
            sequence = self.env['ir.sequence'].get_id(self.rel_picking_type_id.sequence_id.id or self.picking_type_id.sequence_id.id)

        self.write({'name':sequence, 'state':'posted', 'date':self._get_default_date()})
    
    @api.multi
    def _write_quants(self):
        if (self.rel_code == 'incoming' and self.rel_branch_type == 'MD' and not self.is_reverse) or (self.picking_type_id.code == 'incoming' and self.branch_id.branch_type == 'MD') or ((self.rel_code == 'incoming' or self.picking_type_id.code == 'incoming') and self.rel_origin and (self.rel_origin[:3] == 'RB/' or self.rel_origin[:3] == 'RBE') and not self.is_reverse) or ((self.rel_code == 'incoming' or self.picking_type_id.code == 'incoming') and self.is_reverse):
            for packing_line in self.packing_line :
                if packing_line.product_id.categ_id.isParentName('Unit'):
                    quant_id = self.env['stock.quant'].sudo().search([('location_id','=',packing_line.destination_location_id.id),('lot_id','=',packing_line.serial_number_id.id),('qty','=',packing_line.quantity),
                        ('consolidated_date','=',False)], order='id desc',limit=1)
                    move_id = self.env['stock.move'].search([('picking_id','=',packing_line.packing_id.picking_id.id),('product_id','=',packing_line.product_id.id)])
                    if len(move_id) > 1:
                        move_id = move_id.filtered(lambda r: r.restrict_lot_id.id == packing_line.serial_number_id.id)
                    unit_cost = move_id.price_unit or quant_id.cost
                    quant_id.sudo().write({'consolidated_date':self._get_default_date(), 'cost':unit_cost + packing_line.serial_number_id.freight_cost})
                elif packing_line.product_id.categ_id.isParentName('Sparepart'):
                    quant_ids = self.env['stock.quant'].sudo().search([
                        ('product_id','=',packing_line.product_id.id),
                        ('qty','=',packing_line.quantity),
                        ('location_id','=',packing_line.destination_location_id.id),
                        ('consolidated_date','=',False)
                        ])
                    move_id = self.env['stock.move'].search([('picking_id','=',packing_line.packing_id.picking_id.id),('product_id','=',packing_line.product_id.id)])
                    for quant_id in quant_ids :
                        quant_id.sudo().write({'consolidated_date':self._get_default_date(), 'cost':move_id.price_unit*quant_id.qty})
    
    @api.multi
    def _check_freight_cost(self):
        # if (self.branch_id.branch_type == 'MD' and not self.picking_id) or (self.rel_branch_id and self.rel_branch_id.branch_type != 'MD' and self.expedition_id):
        if self.expedition_id:
            for packing_line in self.packing_line :
                if packing_line.freight_cost == 0 :
                    branch = self.branch_id or self.rel_branch_id
                    freight_cost = branch.get_freight_cost(self.expedition_id.id,packing_line.product_id.id)
                    if freight_cost != 0 :
                        packing_line.write({'freight_cost':freight_cost})
                    else :
                        raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan harga Ekspedisi untuk Product '%s' !" %packing_line.product_id.name))
    
    @api.multi
    def _prepare_account_invoice_line(self, id_journal, picking_id):
        branch = self.branch_id or self.rel_branch_id
        jurnal_hutang_ekspedisi_id = self.env['account.journal'].search([('id','=',id_journal)])
        if not jurnal_hutang_ekspedisi_id.default_debit_account_id :
            raise osv.except_osv(('Perhatian !'), ("Silahkan isi Default Debit Account utk Jurnal Hutang Ekspedisi '%s' !" %branch.name))
        id_valuation_account = False
        id_uom = False
        qty = 0
        freight_cost = 0
        invoice_line = []
        for packing_line in self.packing_line :
            analytic_1 = False
            analytic_2 = False
            analytic_3 = False
            analytic_4 = False
            if branch and (self.division or self.rel_division):
                cost_center = ''
                if packing_line.product_id.categ_id.get_root_name() in ('Unit','Extras'):
                    cost_center = 'Sales'
                elif packing_line.product_id.categ_id.get_root_name() == 'Sparepart':
                    cost_center = 'Sparepart_Accesories'
                elif packing_line.product_id.categ_id.get_root_name() =='Umum':
                    cost_center = 'General'
                elif packing_line.product_id.categ_id.get_root_name() =='Service':
                    cost_center = 'Service'
                if cost_center:
                    categ_obj = packing_line.product_id.categ_id
                    category = ''
                    if packing_line.product_id.categ_id.get_root_name() == 'Extras':
                        categ_obj = False
                        category = 'Unit'
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, category, categ_obj, 4, cost_center)
            invoice_line.append([0,False,{
                    'name': 'Hutang Ekspedisi '+ str(packing_line.serial_number_id.name) or str(packing_line.engine_number),
                    'quantity': 1,
                    'origin': self.name,
                    'price_unit':packing_line.freight_cost,
                    'account_id': jurnal_hutang_ekspedisi_id.default_debit_account_id.id,
                    'analytic_1': analytic_1,
                    'analytic_2': analytic_2,
                    'analytic_3': analytic_3,
                    'account_analytic_id':analytic_4,
                }])
        return invoice_line
    
    @api.multi
    def _create_journal_freight_cost(self, picking_id):
        if self.expedition_id:
            branch = self.branch_id or self.rel_branch_id
            branch_config_id = self.env['dym.branch.config'].search([('branch_id','=',branch.id)])
            id_journal = branch_config_id.freight_cost_journal_id.id
            if not id_journal :
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan Jurnal Hutang Ekspedisi untuk '%s'\nsilahkan isi di Branch Config !" %branch.name))
            invoice_line_vals = self._prepare_account_invoice_line(id_journal, picking_id)
            analytic_1 = False
            analytic_2 = False
            analytic_3 = False
            analytic_4 = False
            if branch and (self.division or self.rel_division):
                cost_center = ''
                if self.division == 'Unit' or self.rel_division == 'Unit':
                    cost_center = 'Sales'
                elif self.division == 'Sparepart' or self.rel_division == 'Sparepart':
                    cost_center = 'Sparepart_Accesories'
                elif self.division == 'Umum' or self.rel_division =='Umum':
                    cost_center = 'General'
                if cost_center:
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, branch, self.division or self.rel_division, False, 4, cost_center)
                
            invoice_vals = {
                'name':picking_id.name,
                'origin': self.name,
                'branch_id':branch.id,
                'division':self.division or self.rel_division,
                'partner_id':self.expedition_id.id,
                'date_invoice':self._get_default_date(),
                'reference_type':'none',
                'type': 'in_invoice', 
                'journal_id': id_journal,
                'account_id': self.expedition_id.property_account_payable.id,
                'invoice_line': invoice_line_vals,
                'analytic_1': analytic_1,
                'analytic_2': analytic_2,
                'analytic_3': analytic_3,
                'analytic_4': analytic_4,   
            }
            return self.env['account.invoice'].create(invoice_vals)
    
    @api.multi
    def _create_stock_move(self, picking_id, packing_lines):
        todo_moves = []
        for packing_line in packing_lines :
            if not packing_line.purchase_line_id :
                if not packing_line.serial_number_id.purchase_order_id :
                    raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan No PO utk Serial Number '%s' !"%packing_line.serial_number_id.name))
                for order_line in packing_line.serial_number_id.purchase_order_id.order_line :
                    if packing_line.product_id == order_line.product_id :
                        packing_line.purchase_line_id = order_line.id
                        break
            move_vals = {
                'branch_id': packing_line.purchase_line_id.order_id.branch_id.id,
                'categ_id': packing_line.purchase_line_id.product_id.categ_id.id,
                'name': packing_line.purchase_line_id.name or '',
                'product_id': packing_line.purchase_line_id.product_id.id,
                'product_uom': packing_line.purchase_line_id.product_uom.id,
                'product_uos': packing_line.purchase_line_id.product_uom.id,
                'product_uom_qty': packing_line.quantity,
                'product_uos_qty': packing_line.quantity,
                'date': packing_line.purchase_line_id.order_id.date_order,
                'date_expected': packing_line.purchase_line_id.order_id.end_date,
                'location_id': packing_line.purchase_line_id.order_id.picking_type_id.default_location_src_id.id,
                'location_dest_id': packing_line.purchase_line_id.order_id.location_id.id,
                'picking_id': picking_id.id,
                'partner_id': packing_line.purchase_line_id.order_id.dest_address_id.id or packing_line.purchase_line_id.order_id.partner_id.id,
                'move_dest_id': False,
                'state': 'draft',
                'purchase_line_id': packing_line.purchase_line_id.id,
                'company_id': packing_line.purchase_line_id.order_id.company_id.id,
                'price_unit': packing_line.serial_number_id.hpp*1.1,
                'picking_type_id': packing_line.purchase_line_id.order_id.picking_type_id.id,
                'procurement_id': False,
                'origin': packing_line.purchase_line_id.order_id.name,
                'route_ids': packing_line.purchase_line_id.order_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in packing_line.purchase_line_id.order_id.picking_type_id.warehouse_id.route_ids])] or [],
                'warehouse_id':packing_line.purchase_line_id.order_id.picking_type_id.warehouse_id.id,
                'invoice_state': packing_line.purchase_line_id.order_id.invoice_method == 'picking' and '2binvoiced' or 'none',
                }
            stock_move_id = self.env['stock.move'].create(move_vals)
            todo_moves.append(stock_move_id.id)
        todo_moves = self.env['stock.move'].search([('id','in',todo_moves)]).action_confirm()
        self.env['stock.move'].search([('id','in',todo_moves)]).force_assign()
    
    @api.multi
    def _create_picking(self):
        order = self.packing_line[0].serial_number_id.purchase_order_id
        picking_vals = {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': order.dest_address_id.id or order.partner_id.id,
            'date': order.date_order,
            'start_date': order.start_date,
            'end_date': order.end_date,
            'origin': False,
            'branch_id': self.branch_id.id,
            'division': self.division,
        }
        picking_id = self.env['stock.picking'].create(picking_vals)
        self._create_stock_move(picking_id, self.packing_line)
        return picking_id
    
    @api.multi
    def _check_lot_state(self, serial_number_id):
        if serial_number_id.state != 'intransit' :
            raise osv.except_osv(('Perhatian !'), ("Serial Number '%s' statusnya bukan intransit\nSerial Number mungkin sudah diterima sebelumnya dengan Packing yg berbeda !" %serial_number_id.name))
    
    @api.multi
    def _write_account_move(self, picking_id):
        move_ids = self.env['account.move'].search([('ref','=',picking_id.name)])
        if move_ids :
            move_ids.write({'name':self.name})
    
    @api.multi
    def get_destination_location(self, rfs, rel_rfs, id_dest_location):
        if (self.picking_type_id.code in ('incoming','interbranch_in') and self.division == 'Unit') or (self.rel_code in ('incoming','interbranch_in') and self.rel_division == 'Unit'):
            if self.rel_branch_type == 'DL' and ((self.rel_code == 'interbranch_in' and not self.is_reverse) or (self.rel_code == 'incoming' and self.is_reverse)):
                if not rel_rfs :
                    if not self.nrfs_location :
                        raise osv.except_osv(('Perhatian !'), ("Silahkan isi NRFS Location terlebih dahulu !"))
                    return self.nrfs_location.id
            else :
                if not rfs :
                    if not self.nrfs_location :
                        raise osv.except_osv(('Perhatian !'), ("Silahkan isi NRFS Location terlebih dahulu !"))
                    return self.nrfs_location.id
        return id_dest_location
    
    @api.one
    def post_md(self):
        if not self.packing_line :
            raise osv.except_osv(('Perhatian !'), ("Tidak bisa di Post, silahkan tambahkan produk !"))
        if self.state == 'draft' and self.branch_id.branch_type == 'MD' and self.picking_type_id.code == 'incoming' and self.division == 'Unit' and not self.picking_id and not self.is_reverse :
           
            for packing_line in self.packing_line :
                self._check_lot_state(packing_line.serial_number_id)
            
            self._check_freight_cost()
            picking_id = self._create_picking()
            self._update_lot(picking_id)
            
            processed_ids = []
            # Create new and update existing pack operations
            for prod in self.packing_line :
                pack_datas = {
                    'product_id': prod.product_id.id,
                    'product_uom_id': prod.product_id.uom_id.id,
                    'product_qty': prod.quantity,
                    'lot_id': prod.serial_number_id.id,
                    'location_id': prod.source_location_id.id,
                    'location_dest_id': self.get_destination_location(prod.ready_for_sale, prod.rel_ready_for_sale, prod.destination_location_id.id),
                    'date': self._get_default_date(),
                    'owner_id': picking_id.owner_id.id,
                }
                if prod.packop_id :
                    prod.packop_id.write(pack_datas)
                    processed_ids.append(prod.packop_id.id)
                else:
                    pack_datas['picking_id'] = picking_id.id
                    packop_id = self.env['stock.pack.operation'].create(pack_datas)
                    processed_ids.append(packop_id.id)
            # Delete the others
            packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', picking_id.id), '!', ('id', 'in', processed_ids)])
            for packop in packops :
                packop.unlink()
            
            # Execute the transfer of the picking
            period_id = self.env['account.period'].find(dt=self._get_default_date().date())
            picking_id.with_context(force_period=period_id.id).do_transfer()
            
            self._update_packing()
            if self.expedition_id:
                invoice_id = self._create_journal_freight_cost(picking_id)
                self.write({'invoice_id':invoice_id.id, 'picking_id':picking_id.id})
            self._write_account_move(picking_id)
            self._write_quants()
        return True

    @api.multi
    def reserve(self):
        self._is_over_qty()
        wo = self.env['dym.work.order'].search([('name','=',self.rel_origin)])[0]
        self.write({'state': 'reserved'})
        # wo.end_wo()
        # wo.finished()
        wo.picking_done()
        todo_move_ids = []
        for move in self.picking_id.move_lines:
            todo_move_ids.append(move.id)
            self.env['stock.move'].search([('id','in',todo_move_ids)]).write({'state': 'done'})
            # self.env['stock.move'].search([('id','in',todo_move_ids)]).action_done()
        # print wo.id,'WO ID --------------------------\n'
        # self.env['dym.work.order.line'].search([('work_order_id','=',wo.id),('categ_id','=','Sparepart')]).create_supply_qty()
        # wo.create_supply_qty()
        woline = self.env['dym.work.order.line'].search([('work_order_id','=',wo.id),('categ_id','=','Sparepart')])
        for packing_line in self.packing_line :
            woline.write({'supply_qty': packing_line.quantity})
    
    @api.multi
    def post(self):
	
	# Cek Status Invoice SO
        if self.rel_division == 'Sparepart' and self.rel_code == 'outgoing' and 'SOR-W' in self.rel_origin:
            dso = self.env['sale.order'].search([('name','=',self.rel_origin)])[0]
            if not dso.invoiced and (dso.partner_id.property_payment_term.id == 1 or not dso.partner_id.property_payment_term) and dso.tipe_transaksi!='pic' :
                raise osv.except_osv(('Perhatian !'), ("Lakukan pembayarannya terlebih dahulu Atau Ajukan Customer Payment Term ke Accounting! "))

	# Check Destination Location If Stock
        if self.rel_code == 'incoming' or self.rel_code == 'interbranch_in':
            check_product = []
            for item in self.packing_line3:
                if item.destination_location_id.name == 'Stock':
                    check_product.append(item.product_id.name)
            if check_product:
                raise osv.except_osv(('Perhatian !'), ("Silahkan pilih Destination Location yang seharusnya untuk product: \n%s" % ', '.join(check_product) ))

        returned_id = False
        if self.picking_id.return_id:
            returned_id = self.picking_id.return_id

        if not returned_id and self.rel_origin.startswith('DSM-'):
            dso = self.env['dealer.sale.order'].search([('name','=',self.rel_origin)])[0]
            if dso.return_id:
                returned_id = self.dso.return_id

        if returned_id:
            for rl in returned_id.retur_jual_line:
                for dl in self.packing_line2:
                    if dl.serial_number_id.id == rl.lot_id.id:
                        raise osv.except_osv(('Perhatian !'), ("Nomor mesin %s telah diretur dengan nomor retur %s pada tanggal %s. Pastikan proses retur penjualan selesai sampai dengan Validate Invoice Retur Penjualan !" % (rl.lot_id.name,returned_id.name,returned_id.date)))

        okey = self._context.get('okey',False)
        sjdate = self.sj_date and datetime.strftime(datetime.strptime(self.sj_date, '%Y-%m-%d'), "%Y-%m") or None
        exdate = self.picking_id.end_date and datetime.strftime(datetime.strptime(self.picking_id.end_date, '%Y-%m-%d'), "%Y-%m") or None
        if not okey and sjdate and exdate and sjdate != exdate:
            context = dict(self.env.context or {})
            context['active_id'] = self.id
            context['message'] = "Tanggal Surat Jalan yaitu '%s' tidak sama dengan rentang tanggal PO (%s s/d %s), yakin mau diposting?" % (self.sj_date,self.picking_id.start_date,self.picking_id.end_date)
            view_id = self.env.ref('dym_stock.account_stock_picking_post_button_view').id
            return {
                'name': _('Post Picking'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.picking.post.button',
                'view_id': view_id,
                'domain': "[]",
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': context,
            }

        if not self.packing_line :
            raise osv.except_osv(('Perhatian !'), ("Tidak bisa di Post, silahkan tambahkan produk !"))
        
        if self.state == 'draft':
            if self.rel_code in ('outgoing','interbranch_out') or self.is_reverse :
                self.renew_available_and_reserved()
            
            ids_product = self.picking_id.get_product_ids()
            for packing_line in self.packing_line :
                if packing_line.product_id.id not in ids_product :
                    raise osv.except_osv(('Perhatian !'), ("Product '%s' tidak ada di daftar transfer !" %packing_line.product_id.name))
            
            self._check_serial_number()
            ids_reserve_lot = self.picking_id.get_reserve_lot_quant_ids()
            if self.rel_division == 'Unit' and ((self.is_reverse and self.rel_code == 'outgoing') or (self.rel_code == 'interbranch_in' or (self.rel_code == 'outgoing' and self.rel_branch_type == 'DL'))):
                # if self.rel_division == 'Unit' and (self.rel_code == 'interbranch_in' or (self.rel_code == 'outgoing' and self.rel_branch_type == 'DL') and self.picking_id.retur == False):
                for packing_line in self.packing_line :
                    if packing_line.product_id.categ_id.isParentName('Unit') and packing_line.serial_number_id.id not in ids_reserve_lot :
                        raise osv.except_osv(('Perhatian !'), ("Serial Number '%s' tidak ada di daftar transfer yg sudah dibooking !" %packing_line.serial_number_id.name))
            elif self.rel_division == 'Unit' and self.rel_code == 'interbranch_out' and self.rel_branch_type == 'DL' :
                for packing_line in self.packing_line :
                    if packing_line.serial_number_id.id not in packing_line.get_lot_available_dealer(packing_line.product_id.id,packing_line.source_location_id.id) and packing_line.serial_number_id.id not in ids_reserve_lot :
                        raise osv.except_osv(('Perhatian !'), ("Serial Number '%s' tidak ditemukan di daftar Serial Number available !" %packing_line.serial_number_id.name))
            elif self.rel_division == 'Unit' and self.rel_code in ('outgoing','interbranch_out') and self.rel_branch_type == 'MD' :
                for packing_line in self.packing_line :
                    if packing_line.serial_number_id.id not in self.get_lot_available_md() and packing_line.serial_number_id.id not in ids_reserve_lot :
                        raise osv.except_osv(('Perhatian !'), ("Serial Number '%s' tidak ditemukan di daftar Serial Number available !" %packing_line.serial_number_id.name))
            
            force_valuation_amount = 0
            if self.rel_division in ('Unit', 'Sparepart') and self.rel_code == 'incoming' and not self.is_reverse :
                if self.rel_branch_type == 'DL' :
                    force_valuation_amount = 0.01
            
            self._is_over_qty()
            self._update_lot(self.picking_id)
            
            processed_ids = []
            # Create new and update existing pack operations
            for lstits in [self.packing_line]:
                for prod in lstits :
                    if prod.chassis_number :
                        if len(prod.chassis_number) == 14:
                            chassis_number = prod.chassis_number
                            chassis_code = False
                        elif len(prod.chassis_number) == 17:
                            chassis_number = prod.chassis_number[3:18]
                            chassis_code = prod.chassis_number[:3]
                    
                    if self.rel_code == "incoming" and self.rel_division == "Unit" and self.rel_branch_type == 'DL' and not self.is_reverse  :
                        engine_exist = self.env['stock.production.lot'].search([('name','=',prod.engine_number),('branch_id.company_id','=',self.picking_id.branch_id.company_id.id)])
                        if engine_exist:
                            if engine_exist.state in ['returned','loss']:
                                prod.serial_number_id = engine_exist
                                state = 'intransit'
                                if self.picking_id.retur == True:
                                    state = 'stock'
                                prod.serial_number_id.write({
                                    'name':prod.engine_number,
                                    'chassis_no':chassis_number,
                                    'chassis_code':chassis_code,
                                    'product_id':prod.product_id.id,
                                    'branch_id':self.picking_id.branch_id.id,
                                    'division':self.picking_id.division,
                                    'purchase_order_id':self.picking_id.transaction_id,
                                    'po_date':self.picking_id.date,
                                    'receive_date':self._get_default_date(),
                                    'supplier_id':self.picking_id.partner_id.id,
                                    'expedisi_id':self.expedition_id.id,
                                    'receipt_id':self.picking_id.id,
                                    'picking_id':self.picking_id.id,
                                    'state':state,
                                    'location_id': self.get_destination_location(prod.ready_for_sale, prod.rel_ready_for_sale, prod.destination_location_id.id),
                                    'tahun': prod.tahun_pembuatan,
                                    'ready_for_sale': prod.convert_rfs(prod.ready_for_sale),
                                    'no_faktur':prod.no_faktur,
                                    'consolidate_id':False,
                                })
                            else:
                                raise osv.except_osv(('Perhatian !'), ("Serial Number '%s' sudah terdaftar dan sedang dalam status %s!") % (prod.serial_number_id.name,prod.serial_number_id.name))
                        else:
                            state = 'intransit'
                            if self.is_reverse or self.picking_id.retur == True:
                                state = 'stock'
                            prod.serial_number_id = self.env['stock.production.lot'].create({
                                'name':prod.engine_number,
                                'chassis_no':chassis_number,
                                'chassis_code':chassis_code,
                                'product_id':prod.product_id.id,
                                'branch_id':self.picking_id.branch_id.id,
                                'division':self.picking_id.division,
                                'purchase_order_id':self.picking_id.transaction_id,
                                'po_date':self.picking_id.date,
                                'receive_date':self._get_default_date(),
                                'supplier_id':self.picking_id.partner_id.id,
                                'expedisi_id':self.expedition_id.id,
                                'receipt_id':self.picking_id.id,
                                'picking_id':self.picking_id.id,
                                'state':state,
                                'location_id': self.get_destination_location(prod.ready_for_sale, prod.rel_ready_for_sale, prod.destination_location_id.id),
                                'tahun': prod.tahun_pembuatan,
                                'ready_for_sale': prod.convert_rfs(prod.ready_for_sale),
                                'no_faktur':prod.no_faktur,
                            })
                    elif self.rel_code == "incoming" and self.is_reverse and prod.serial_number_id and self.rel_division == "Unit":
                        prod.serial_number_id.write({
                            'state':'stock',
                            'sale_order_reserved':False,
                            'customer_reserved':False,
                            'customer_reserved':False,
                            'dealer_sale_order_id': False,
                            'invoice_date': False,
                            'customer_id': False,
                            'customer_stnk': False,
                            'dp': 0,
                            'tenor': 0,
                            'cicilan': 0,
                            'jenis_penjualan':'',
                            'finco_id':False,
                            'biro_jasa_id': False,
                            'invoice_bbn': False,
                            'total_jasa':0,
                            'cddb_id':False,
                            'move_lines_invoice_bbn_id':False,
                            'pengurusan_stnk_bpkb_id':False,
                            'state_stnk':False,
                            'tgl_pengurusan_stnk_bpkb' : False,
                            'inv_pengurusan_stnk_bpkb_id': False,
                            'invoice_bbn':False,
                            'total_jasa':0,
                            'pengurusan_stnk_bpkb_id':False,
                            'tgl_faktur':False,
                            'permohonan_faktur_id':False,
                            'tgl_terima':False,
                            'penerimaan_faktur_id':False,
                            'faktur_stnk':False,
                            'tgl_cetak_faktur':False,
                            'tgl_penyerahan_faktur':False,
                            'penyerahan_faktur_id':False,
                            'lot_status_cddb':'not',
                            'proses_biro_jasa_id': False,
                            'tgl_proses_birojasa':False,
                            'no_notice_copy':False,
                            'tgl_notice_copy':False,
                            'proses_stnk_id':False,
                            'tgl_proses_stnk':False,
                            'no_faktur':'',
                        })
                    elif self.rel_code == "outgoing" and self.is_reverse and prod.serial_number_id and self.rel_division == "Unit" :
                        prod.serial_number_id.write({'state':'returned'})
                    elif self.rel_code == "outgoing" and prod.serial_number_id.state in ['reserved','stock'] and prod.serial_number_id and self.rel_division == "Unit" and not self.is_reverse and self.picking_id.retur == True:
                        retur_line = prod.move_id.retur_jual_line_id
                        if retur_line:                            
                            obj_inv = self.env['account.invoice']
                            dso = retur_line.retur_id.dso_id
                            if dso.is_credit:
                                jenis_penjualan = '2'
                                inv_id = obj_inv.search([
                                    ('origin','ilike',dso.name),
                                    ('partner_id','in',[dso.partner_id.id,dso.finco_id.id]),
                                    ('tipe','=','finco'),
                                    ('customer_payment','=',True)
                                ])
                            else:
                                jenis_penjualan = '1'
                                inv_id = obj_inv.search([
                                    ('origin','ilike',dso.name),
                                    ('partner_id','=',dso.partner_id.id),
                                    ('tipe','=','customer'),
                                    ('customer_payment','=',True)
                                ])
                            if retur_line.dso_line_id.is_bbn == 'Y':
                                if not inv_id:
                                    state = 'sold'
                                else:
                                    state = 'paid'
                            else:
                                if not inv_id:
                                    state = 'sold_offtr'
                                else:
                                    state = 'paid_offtr'
                            prod.serial_number_id.write({
                                'state':state,
                                'dealer_sale_order_id': dso.id,
                                'invoice_date': inv_id.date_invoice,
                                'customer_id': dso.partner_id.id,
                                'customer_stnk': retur_line.dso_line_id.partner_stnk_id.id,
                                'dp': retur_line.dso_line_id.uang_muka,
                                'tenor': retur_line.dso_line_id.finco_tenor,
                                'cicilan': retur_line.dso_line_id.cicilan,
                                'jenis_penjualan': jenis_penjualan,
                                'finco_id': retur_line.dso_line_id.dealer_sale_order_line_id.finco_id.id,
                                'biro_jasa_id': retur_line.dso_line_id.biro_jasa_id.id,
                                'cddb_id':retur_line.dso_line_id.dealer_sale_order_line_id.cddb_id.id,
                            })
                    pack_datas = {
                        'product_id': prod.product_id.id,
                        'product_uom_id': prod.product_id.uom_id.id,
                        'product_qty': prod.quantity,
                        'lot_id': prod.serial_number_id.id,
                        'location_id': prod.source_location_id.id,
                        'location_dest_id': self.get_destination_location(prod.ready_for_sale, prod.rel_ready_for_sale, prod.destination_location_id.id),
                        'date': prod.packing_id.date if prod.packing_id.date else self._get_default_date(),
                        'owner_id': prod.packing_id.picking_id.owner_id.id,
                    }
                    if prod.packop_id:
                        prod.packop_id.write(pack_datas)
                        if prod.packop_id.linked_move_operation_ids[0]:
                            prod.write({'move_id':prod.packop_id.linked_move_operation_ids[0].move_id.id})
                        prod.move_id.write({
                            'location_id':prod.source_location_id.id,
                            'location_dest_id':self.get_destination_location(prod.ready_for_sale, prod.rel_ready_for_sale, prod.destination_location_id.id)
                        })
                        processed_ids.append(prod.packop_id.id)
                    else:
                        pack_datas['picking_id'] = self.picking_id.id
                        packop_id = self.env['stock.pack.operation'].create(pack_datas)
                        if packop_id.linked_move_operation_ids and packop_id.linked_move_operation_ids[0]:
                            prod.write({'move_id':packop_id.linked_move_operation_ids[0].move_id.id})
                        prod.move_id.write({
                            'location_id':prod.source_location_id.id,
                            'location_dest_id':self.get_destination_location(prod.ready_for_sale, prod.rel_ready_for_sale, prod.destination_location_id.id)
                        })
                        processed_ids.append(packop_id.id)
            
            packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', self.picking_id.id), '!', ('id', 'in', processed_ids)])
            for packop in packops:
                packop.unlink()
            period_id = self.env['account.period'].find(dt=self._get_default_date().date())
            # if (self.picking_id.origin[:5] not in ('SOR-W')):
                # print 'WOR Transfer-------------------------\n'
            self.picking_id.with_context(force_period=period_id.id).do_transfer()
            # else:
            #     self.picking_id.write({'state': 'done'})
            #     for move in self.picking_id.move_lines:
            #         move.write({'state': 'done'})
            self._update_packing()
            self._check_freight_cost()
            if self.expedition_id:
                invoice_id = self._create_journal_freight_cost(self.picking_id)
                self.write({'invoice_id':invoice_id.id})            
            self._write_account_move(self.picking_id)
            self._write_quants()
            return True
        elif self.state == 'reserved':
            print 'if reserve****************'
            if self.rel_code in ('outgoing','interbranch_out') or self.is_reverse :
                self.renew_available_and_reserved()
            
            ids_product = self.picking_id.get_product_ids()
            for packing_line in self.packing_line :
                if packing_line.product_id.id not in ids_product :
                    raise osv.except_osv(('Perhatian !'), ("Product '%s' tidak ada di daftar transfer !" %packing_line.product_id.name))
            
            self._check_serial_number()
            ids_reserve_lot = self.picking_id.get_reserve_lot_quant_ids()
            if self.rel_division == 'Unit' and ((self.is_reverse and self.rel_code == 'outgoing') or (self.rel_code == 'interbranch_in' or (self.rel_code == 'outgoing' and self.rel_branch_type == 'DL'))):
                # if self.rel_division == 'Unit' and (self.rel_code == 'interbranch_in' or (self.rel_code == 'outgoing' and self.rel_branch_type == 'DL') and self.picking_id.retur == False):
                for packing_line in self.packing_line :
                    if packing_line.product_id.categ_id.isParentName('Unit') and packing_line.serial_number_id.id not in ids_reserve_lot :
                        raise osv.except_osv(('Perhatian !'), ("Serial Number '%s' tidak ada di daftar transfer yg sudah dibooking !" %packing_line.serial_number_id.name))
            elif self.rel_division == 'Unit' and self.rel_code == 'interbranch_out' and self.rel_branch_type == 'DL' :
                for packing_line in self.packing_line :
                    if packing_line.serial_number_id.id not in packing_line.get_lot_available_dealer(packing_line.product_id.id,packing_line.source_location_id.id) and packing_line.serial_number_id.id not in ids_reserve_lot :
                        raise osv.except_osv(('Perhatian !'), ("Serial Number '%s' tidak ditemukan di daftar Serial Number available !" %packing_line.serial_number_id.name))
            elif self.rel_division == 'Unit' and self.rel_code in ('outgoing','interbranch_out') and self.rel_branch_type == 'MD' :
                for packing_line in self.packing_line :
                    if packing_line.serial_number_id.id not in self.get_lot_available_md() and packing_line.serial_number_id.id not in ids_reserve_lot :
                        raise osv.except_osv(('Perhatian !'), ("Serial Number '%s' tidak ditemukan di daftar Serial Number available !" %packing_line.serial_number_id.name))
            
            force_valuation_amount = 0
            if self.rel_division in ('Unit', 'Sparepart') and self.rel_code == 'incoming' and not self.is_reverse :
                if self.rel_branch_type == 'DL' :
                    force_valuation_amount = 0.01
            if not (self.rel_division == 'Sparepart' and self.rel_code == 'outgoing' and 'WOR-W' in self.rel_origin):
                self._is_over_qty()
            self._update_lot(self.picking_id)
            
            processed_ids = []
            # Create new and update existing pack operations
            print 'test packing*********\n'
            for lstits in [self.packing_line]:
                for prod in lstits :
                    if prod.chassis_number :
                        if len(prod.chassis_number) == 14:
                            chassis_number = prod.chassis_number
                            chassis_code = False
                        elif len(prod.chassis_number) == 17:
                            chassis_number = prod.chassis_number[3:18]
                            chassis_code = prod.chassis_number[:3]
                    elif self.rel_code == "incoming" and self.is_reverse and prod.serial_number_id and self.rel_division == "Unit":
                        prod.serial_number_id.write({
                            'state':'stock',
                            'sale_order_reserved':False,
                            'customer_reserved':False,
                            'customer_reserved':False,
                            'dealer_sale_order_id': False,
                            'invoice_date': False,
                            'customer_id': False,
                            'customer_stnk': False,
                            'dp': 0,
                            'tenor': 0,
                            'cicilan': 0,
                            'jenis_penjualan':'',
                            'finco_id':False,
                            'biro_jasa_id': False,
                            'invoice_bbn': False,
                            'total_jasa':0,
                            'cddb_id':False,
                            'move_lines_invoice_bbn_id':False,
                            'pengurusan_stnk_bpkb_id':False,
                            'state_stnk':False,
                            'tgl_pengurusan_stnk_bpkb' : False,
                            'inv_pengurusan_stnk_bpkb_id': False,
                            'invoice_bbn':False,
                            'total_jasa':0,
                            'pengurusan_stnk_bpkb_id':False,
                            'tgl_faktur':False,
                            'permohonan_faktur_id':False,
                            'tgl_terima':False,
                            'penerimaan_faktur_id':False,
                            'faktur_stnk':False,
                            'tgl_cetak_faktur':False,
                            'tgl_penyerahan_faktur':False,
                            'penyerahan_faktur_id':False,
                            'lot_status_cddb':'not',
                            'proses_biro_jasa_id': False,
                            'tgl_proses_birojasa':False,
                            'no_notice_copy':False,
                            'tgl_notice_copy':False,
                            'proses_stnk_id':False,
                            'tgl_proses_stnk':False,
                            'no_faktur':'',
                        })
                    elif self.rel_code == "outgoing" and self.is_reverse and prod.serial_number_id and self.rel_division == "Unit" :
                        prod.serial_number_id.write({'state':'returned'})
                    elif self.rel_code == "outgoing" and prod.serial_number_id.state in ['reserved','stock'] and prod.serial_number_id and self.rel_division == "Unit" and not self.is_reverse and self.picking_id.retur == True:
                        retur_line = prod.move_id.retur_jual_line_id
                        if retur_line:                            
                            obj_inv = self.env['account.invoice']
                            dso = retur_line.retur_id.dso_id
                            if dso.is_credit:
                                jenis_penjualan = '2'
                                inv_id = obj_inv.search([
                                    ('origin','ilike',dso.name),
                                    ('partner_id','in',[dso.partner_id.id,dso.finco_id.id]),
                                    ('tipe','=','finco'),
                                    ('customer_payment','=',True)
                                ])
                            else:
                                jenis_penjualan = '1'
                                inv_id = obj_inv.search([
                                    ('origin','ilike',dso.name),
                                    ('partner_id','=',dso.partner_id.id),
                                    ('tipe','=','customer'),
                                    ('customer_payment','=',True)
                                ])
                            if retur_line.dso_line_id.is_bbn == 'Y':
                                if not inv_id:
                                    state = 'sold'
                                else:
                                    state = 'paid'
                            else:
                                if not inv_id:
                                    state = 'sold_offtr'
                                else:
                                    state = 'paid_offtr'
                            prod.serial_number_id.write({
                                'state':state,
                                'dealer_sale_order_id': dso.id,
                                'invoice_date': inv_id.date_invoice,
                                'customer_id': dso.partner_id.id,
                                'customer_stnk': retur_line.dso_line_id.partner_stnk_id.id,
                                'dp': retur_line.dso_line_id.uang_muka,
                                'tenor': retur_line.dso_line_id.finco_tenor,
                                'cicilan': retur_line.dso_line_id.cicilan,
                                'jenis_penjualan': jenis_penjualan,
                                'finco_id': retur_line.dso_line_id.dealer_sale_order_line_id.finco_id.id,
                                'biro_jasa_id': retur_line.dso_line_id.biro_jasa_id.id,
                                'cddb_id':retur_line.dso_line_id.dealer_sale_order_line_id.cddb_id.id,
                            })
                    pack_datas = {
                        'product_id': prod.product_id.id,
                        'product_uom_id': prod.product_id.uom_id.id,
                        'product_qty': prod.quantity,
                        'lot_id': prod.serial_number_id.id,
                        'location_id': prod.source_location_id.id,
                        'location_dest_id': self.get_destination_location(prod.ready_for_sale, prod.rel_ready_for_sale, prod.destination_location_id.id),
                        'date': prod.packing_id.date if prod.packing_id.date else self._get_default_date(),
                        'owner_id': prod.packing_id.picking_id.owner_id.id,
                    }
                    # if prod.packop_id:
                    #     prod.packop_id.write(pack_datas)
                    #     if prod.packop_id.linked_move_operation_ids[0]:
                    #         prod.write({'move_id':prod.packop_id.linked_move_operation_ids[0].move_id.id})
                    #     prod.move_id.write({
                    #         'location_id':prod.source_location_id.id,
                    #         'location_dest_id':self.get_destination_location(prod.ready_for_sale, prod.rel_ready_for_sale, prod.destination_location_id.id)
                    #     })
                    #     processed_ids.append(prod.packop_id.id)
                    # else:
                    #     pack_datas['picking_id'] = self.picking_id.id
                    #     packop_id = self.env['stock.pack.operation'].create(pack_datas)
                    #     if packop_id.linked_move_operation_ids and packop_id.linked_move_operation_ids[0]:
                    #         prod.write({'move_id':packop_id.linked_move_operation_ids[0].move_id.id})
                    #     prod.move_id.write({
                    #         'location_id':prod.source_location_id.id,
                    #         'location_dest_id':self.get_destination_location(prod.ready_for_sale, prod.rel_ready_for_sale, prod.destination_location_id.id)
                    #     })
                    #     processed_ids.append(packop_id.id)
            
            packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', self.picking_id.id), '!', ('id', 'in', processed_ids)])
            for packop in packops:
                packop.unlink()
            period_id = self.env['account.period'].find(dt=self._get_default_date().date())
            self.picking_id.with_context(force_period=period_id.id).do_transfer()
            test = self._update_packing()
            print test, '----------\n'
            self._check_freight_cost()
            if self.expedition_id:
                invoice_id = self._create_journal_freight_cost(self.picking_id)
                self.write({'invoice_id':invoice_id.id})            
            self._write_account_move(self.picking_id)
            self._write_quants()
            return True
    
    @api.multi
    def action_cancel(self):
        if self.state=='posted':
            return True
        self.write({'state':'cancelled'})
    
    @api.onchange('rel_source_location_id','rel_destination_location_id')
    def packing_line_change(self):
        self.packing_line = self.packing_line2 = self.packing_line3 = self.packing_line4 = False
    
    @api.onchange('expedition_id','branch_id')
    def expedition_id_change(self):
        domain = {}
        domain['expedition_id'] = [('id','in',self.branch_id.get_ids_expedition())]
        self.plat_number_id = False
        self.driver_id = False
        return {'domain':domain}
    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa dihapus jika status bukan 'Draft' !"))
        return super(dym_stock_packing, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def get_lot_available_md(self):
        location_ids = self.env['stock.location'].search([('id','child_of',self.rel_source_location_id.id)])
        ids_location = []
        for location in location_ids :
            ids_location.append(location.id)
        ids_product = self.picking_id.get_product_ids()
        ids_lot_available = []
        self._cr.execute("""
        SELECT
            l.id
        FROM
            stock_quant q
        JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id in %s and q.location_id in %s and l.state = 'stock' and q.reservation_id is Null and q.consolidated_date is not Null
        ORDER BY
            q.in_date asc
        """,(tuple(ids_product,),tuple(ids_location,)))
        for id_lot in self._cr.fetchall() :
            ids_lot_available.append(id_lot[0])
        return ids_lot_available
    
    @api.onchange('picking_type_id')
    def picking_type_id_change(self):
        if self.picking_type_id :
            self.source_location_id = self.picking_type_id.default_location_src_id.id
            self.destination_location_id = self.picking_type_id.default_location_dest_id.id

    @api.onchange('destination_location_id')
    def change_line_destination_location(self):
        if self.destination_location_id:
            if self.rel_division == "Unit":
                packing_line = self.packing_line
            elif self.rel_division == "Sparepart":
                packing_line = self.packing_line3
            for line in self.packing_line:
                line.destination_location_id = self.destination_location_id.id

    
class dym_stock_packing_line(models.Model):
    _name = "dym.stock.packing.line"
    _description = "Stock Packing Line"
    _rec_name = "product_id"
    
    @api.model
    def _get_default_date(self):
        # return datetime.now()
        return self.env['dym.branch'].get_default_date_model()
    
    def default_get(self, cr, uid, fields, context=None):
        data = {}
        if 'params' in context and 'id' in context['params'] and 'model' in context['params'] and context['params']['model'] == 'dym.stock.packing':
            packing_id = self.pool.get('dym.stock.packing').browse(cr, uid, [context['params']['id']])
            data['rel_division'] = packing_id.rel_division
            data['rel_code'] = packing_id.rel_code
            data['rel_source_location_id'] = packing_id.rel_source_location_id.id
            data['rel_destination_location_id'] = packing_id.rel_destination_location_id.id
            data['rel_branch_type'] = packing_id.rel_branch_type
            return data
        if 'active_id' in context and (('active_model' in context and context['active_model'] == 'dym.stock.packing') or 'active_model' not in context):
            packing_id = self.pool.get('dym.stock.packing').browse(cr, uid, [context['active_id']])
            data['rel_division'] = packing_id.rel_division
            data['rel_code'] = packing_id.rel_code
            data['rel_source_location_id'] = packing_id.rel_source_location_id.id
            data['rel_destination_location_id'] = packing_id.rel_destination_location_id.id
            data['rel_branch_type'] = packing_id.rel_branch_type
            return data
        return data
    
    @api.one
    @api.depends('source_location_id','destination_location_id')
    def _get_usage(self):
        source_location_usage = self.source_location_id.usage
        destination_location_usage = self.destination_location_id.usage
        if self.source_location_id.usage == 'view':
            source_location_usage = 'internal'
        if self.destination_location_id.usage == 'view':
            destination_location_usage = 'internal'
        self.source_location_usage = source_location_usage
        self.destination_location_usage = destination_location_usage

    @api.one
    @api.depends('packing_id.rel_code','product_id','packing_id.rel_branch_id','packing_id.branch_id')
    def _get_src_lct_domain(self):
        location_ids = []
        if self.packing_id.rel_code in ('outgoing','interbranch_out'):
            if self.product_id.id and (self.packing_id.rel_branch_id.id or self.packing_id.branch_id.id):
                ids_move = self.packing_id.picking_id.get_ids_move()
                location_ids = self.get_stock_location(self.product_id.id, self.packing_id.rel_branch_id.id or self.packing_id.branch_id.id, ids_move)
        self.src_loc_domain = location_ids
        if location_ids:
            if len(location_ids)>1:
                for location in self.env['stock.location'].browse(location_ids):
                    if len(location_ids)>1 and location.name != 'Stock':
                        self.source_location_id = location.id
                        break
            else:
                self.source_location_id = location_ids[0]

    src_loc_domain = fields.Many2many('stock.location', compute='_get_src_lct_domain', string='Source Location Domain')
    packing_id = fields.Many2one('dym.stock.packing', 'Packing')
    template_id = fields.Many2one('product.template', 'Tipe')
    product_id = fields.Many2one('product.product', 'Product')
    rel_division = fields.Selection(related='packing_id.rel_division', string='Division')
    rel_code = fields.Selection(related='packing_id.rel_code', string='Code')
    rel_is_reverse = fields.Boolean(related='packing_id.is_reverse', string='Is Reverse')
    rel_source_location_id = fields.Many2one(related='packing_id.rel_source_location_id', string='Source Location')
    rel_destination_location_id = fields.Many2one(related='packing_id.rel_destination_location_id', string='Destination Location')
    source_location_id = fields.Many2one('stock.location', 'Source Location')
    destination_location_id = fields.Many2one('stock.location', 'Destinaton Location')
    current_reserved = fields.Float('Current Reserved', digits_compute=dp.get_precision('Product Unit of Measure'))
    rel_current_reserved = fields.Float(related='current_reserved', string='Current Reserved')
    stock_available = fields.Float('Stock Available', digits_compute=dp.get_precision('Product Unit of Measure'))
    rel_stock_available = fields.Float(related='stock_available', string='Stock Available')
    packop_id = fields.Many2one('stock.pack.operation', 'Operation')
    quantity = fields.Float('Qty', digits_compute=dp.get_precision('Product Unit of Measure'))
    seharusnya = fields.Float('Seharusnya', digits_compute=dp.get_precision('Product Unit of Measure'))
    rel_seharusnya = fields.Float(related='seharusnya', string='Seharusnya')
    serial_number_id = fields.Many2one('stock.production.lot', 'Serial Number')
    engine_number = fields.Char('Engine Number')
    chassis_number = fields.Char('Chassis Number')
    tahun_pembuatan = fields.Char('Tahun Pembuatan', size=4)
    rel_tahun_pembuatan = fields.Char(related='serial_number_id.tahun', string='Tahun Pembuatan')
    ready_for_sale = fields.Boolean('Ready For Sale')
    rel_ready_for_sale = fields.Boolean(related='ready_for_sale', string='Ready For Sale')
    performance_hpp = fields.Float('Performance HPP', digits_compute=dp.get_precision('Product Price'))
    freight_cost = fields.Float('Freight Cost', digits_compute=dp.get_precision('Product Price'))
    rel_branch_type = fields.Selection(related='packing_id.rel_branch_type', string='Branch Type')
    no_ship_list = fields.Char('No Ship List')
    no_faktur = fields.Char('No Faktur')
    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Line')
    move_id = fields.Many2one('stock.move', 'Stock Move')
    source_location_usage = fields.Char(compute='_get_usage', string='Source Location Usage', store=True)
    destination_location_usage = fields.Char(compute='_get_usage', string='Destination Location Usage', store=True)
    
    _sql_constraints = [
        ('unique_engine_number', 'unique(packing_id,engine_number)', 'Ditemukan engine number duplicate, silahkan cek kembali !'),
        ('unique_chassis_number', 'unique(packing_id,chassis_number)', 'Ditemukan chassis number duplicate, silahkan cek kembali !'),
    ]
    
    @api.multi
    def convert_rfs(self, rfs):
        result = False
        if rfs == 'good' :
            result = True
        elif rfs == True :
            result = 'good'
        elif rfs == False :
            result = 'not_good'
        return result
    
    @api.multi
    def get_lot_available_dealer(self, id_product, id_location):
        ids_lot_available = []
        self._cr.execute("""
        SELECT
            l.id
        FROM
            stock_quant q
        JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and l.state = 'stock' and q.reservation_id is Null and q.consolidated_date is not Null
        ORDER BY
            q.in_date desc
        """,(id_product,id_location))
        for id_lot in self._cr.fetchall() :
            ids_lot_available.append(id_lot[0])
        return ids_lot_available
    
    @api.multi
    def _get_lot_intransit(self):
        ids_lot_intransit = []
        branch_id = self.env['dym.branch'].search([('branch_type','=','MD')])
        serial_number_ids = self.env['stock.production.lot'].search([
            ('branch_id','=',branch_id.id),
            ('state','=','intransit'),
            ])
        for lot in serial_number_ids :
            ids_lot_intransit.append(lot.id)
        return ids_lot_intransit
    
    @api.multi
    def get_qty_max(self, seharusnya, available, reserved):
        qty_max = seharusnya
        if self.rel_code <> 'incoming' and seharusnya != reserved:
            if (available + reserved) < seharusnya :
                qty_max = available + reserved
        return qty_max
    
    @api.multi
    def is_punctuation(self, words):
        for n in range(len(words)) :
            if words[n] in string.punctuation :
                return True
        return False
    
    @api.multi
    def _get_suggested_location(self, id_product_tmpl, id_attribute_value, id_destination_location):
        id_location = id_destination_location
        return id_location
    
    @api.onchange('seharusnya')
    def change_default(self):
        self.ready_for_sale = True
        
    @api.onchange('template_id')
    def change_template(self):
        self.product_id = False
        
    @api.onchange('product_id','serial_number_id','template_id')
    def change_product_id(self):
        domain = {}
        warning = {}
        product_ids = self.packing_id.picking_id.get_product_ids()
        template_ids = []
        for product in self.env['product.product'].browse(product_ids):
            if product.product_tmpl_id.id not in template_ids:
                template_ids.append(product.product_tmpl_id.id)
        if self.engine_number and len(self.engine_number) > 4:
            tipe_search = self.template_id.search([('kd_mesin','ilike',self.engine_number[:4]),('id','in',template_ids)])
            domain['template_id'] = [('id','in',tipe_search.ids)]
        else:
            domain['template_id'] = [('id','in',template_ids)]
        if self.template_id:
            domain['product_id'] = [('product_tmpl_id','=',self.template_id.id),('id','in',product_ids)]
        else:
            domain['product_id'] = [('id','in',product_ids)]
        if self.serial_number_id :
            self.product_id = self.serial_number_id.product_id.id
            self.template_id = self.serial_number_id.product_id.product_tmpl_id.id
        elif not self.serial_number_id and self.rel_division == 'Unit' and self.rel_code in ['incoming','outgoing','interbranch_out','interbranch_in'] and self.packing_id.rel_branch_type == 'MD' and not self.rel_is_reverse :
            self.product_id = False
            self.template_id = False
        return {'domain':domain, 'warning':warning}

    @api.onchange('engine_number','serial_number_id')
    def change_engine_number(self):
        domain = {}
        warning={}
        picking_id = self.packing_id.picking_id
 
        if self.rel_code == 'incoming' and self.rel_branch_type == 'DL' and not self.rel_is_reverse :
            if self.engine_number :
                self.engine_number = self.engine_number.replace(" ", "")
                self.engine_number = self.engine_number.upper()
                if len(self.engine_number) != 12 :
                    self.engine_number = False
                    warning = {'title':'Engine Number Salah !','message':"Nomor mesin wajib 12 digit. Silahkan periksa kembali Engine Number yang Anda input (2)"}
                    return {'warning':warning}
                
                if self.is_punctuation(self.engine_number) :
                    warning = {'title':'Perhatian !','message':"Engine Number hanya boleh huruf dan angka"}
                    return {'warning':warning}
                
                if self.packing_id.rel_branch_type == 'DL' :
                    if self.product_id :
                        product_id = self.env['product.template'].search([('name','=',self.product_id.name)])
                        if product_id.kd_mesin :
                            pjg = len(product_id.kd_mesin)
                            if product_id.kd_mesin != self.engine_number[:pjg] :
                                self.engine_number = False
                                warning = {'title':'Perhatian !','message':"Engine Number tidak sama dengan kode mesin di Produk"}
                                return {'warning':warning}
                            
                        else :
                            self.engine_number = False
                            warning = {'title':'Perhatian !','message':"Silahkan isi kode mesin '%s' di master product terlebih dahulu" %self.product_id.description}
                            return {'warning':warning}
                        
                        engine_exist = self.env['stock.production.lot'].search([('branch_id.company_id','=',self.packing_id.rel_branch_id.company_id.id),('name','=',self.engine_number),('state','not in',['returned','loss'])])
                        if engine_exist:
                            self.engine_number=False
                            warning = {'title':'Perhatian !','message':"Engine Number sudah pernah ada"}
                            return {'warning':warning}
        else :
            if self.serial_number_id :
                self.engine_number = self.serial_number_id.name
            else :
                self.engine_number = False
        if self.engine_number and len(self.engine_number) > 4:
            warning = {}
            product_ids = self.packing_id.picking_id.get_product_ids()
            template_ids = []
            for product in self.env['product.product'].browse(product_ids):
                if product.product_tmpl_id.id not in template_ids:
                    template_ids.append(product.product_tmpl_id.id)
            tipe_search = self.template_id.search([('kd_mesin','ilike',self.engine_number[:4]),('id','in',template_ids)])
            domain['template_id'] = [('id','in',tipe_search.ids)]
            if not tipe_search:
                warning = {'title':'Engine Number Salah !','message':"Kd mesin " + self.engine_number[:4] + " tidak terdaftar di product"}
                self.engine_number = False
            for tipe in tipe_search:
                if tipe.id in template_ids:
                    self.template_id = tipe.id
                    # self.product_id = False
                    break
        return {'domain':domain, 'warning':warning}
    
    @api.onchange('ready_for_sale')
    def change_rfs(self):
        warning = {}
        if self.ready_for_sale == False and 'selected' in self._context and self._context['selected']:
            if not self.packing_id.nrfs_location:
                self.ready_for_sale = True
                self.destination_location_id = self.packing_id.destination_location_id.id or self.move_id.location_dest_id.id or self.rel_destination_location_id.id
                warning = {'title':'Data belum lengkap!','message':"Mohon isi NRFS Location di header"}
                return {'warning':warning}
            self.destination_location_id = self.packing_id.nrfs_location.id
        else:
            self.destination_location_id = self.packing_id.destination_location_id.id or self.move_id.location_dest_id.id or self.rel_destination_location_id.id

    @api.onchange('chassis_number','serial_number_id')
    def change_chassis_number(self):
        warning = {}
        picking_id = self.packing_id.picking_id
        if self.rel_code == 'incoming' and self.packing_id.rel_branch_type == 'DL' and not self.rel_is_reverse :
            if self.chassis_number :
                self.chassis_number = self.chassis_number.replace(" ", "")
                self.chassis_number = self.chassis_number.upper()
                if len(self.chassis_number) == 14 or (len(self.chassis_number) == 17 and self.chassis_number[:2] == 'MH') :
                    self.chassis_number = self.chassis_number
                else :
                    self.chassis_number = False
                    warning = {'title':'Chassis Number Salah !','message':"Silahkan periksa kembali Chassis Number yang Anda input"}
                    return {'warning':warning}
                
                if self.is_punctuation(self.chassis_number) :
                    self.chassis_number = False
                    warning = {'title':'Perhatian','message':"Chassis Number hanya boleh huruf dan angka"}
                    return {'warning':warning}
                
                chassis_exist = self.env['stock.production.lot'].search([('branch_id.company_id','=',self.packing_id.rel_branch_id.company_id.id),('chassis_no','=',self.chassis_number),('state','not in',['returned','loss'])])
                if chassis_exist:
                    self.chassis_number = False
                    warning = {'title':'Perhatian','message':"Chassis Number sudah pernah ada"}
                    return {'warning':warning}
        else :
            if self.serial_number_id :
                self.chassis_number = self.serial_number_id.chassis_no
            else :
                self.chassis_number = False
    
    @api.onchange('serial_number_id','product_id','source_location_id')
    def change_serial_number_id(self):
        domain = {}
        ids_serial_number = []
        if self.rel_code == 'interbranch_out' and self.rel_branch_type == 'DL' and not self.rel_is_reverse :
            if self.product_id and self.source_location_id :
                ids_serial_number = self.get_lot_available_dealer(self.product_id.id, self.source_location_id.id)
        elif self.rel_code == 'outgoing' and self.rel_branch_type == 'DL' and not self.rel_is_reverse and self.packing_id.picking_id.retur == True:
            ids_serial_number = self.get_lot_available_dealer(self.product_id.id, self.source_location_id.id)
        elif (self.rel_code in ('interbranch_in','outgoing') and self.rel_branch_type == 'DL') or self.rel_is_reverse :
            product_serial_number = self.packing_id.picking_id.filter_restrict_lot_ids()
            if self.product_id in product_serial_number :
                ids_serial_number = product_serial_number[self.product_id]
#         elif self.rel_code == 'incoming' and self.packing_id.rel_branch_type == 'MD' and not self.rel_is_reverse :
        elif self.packing_id.branch_id.branch_type == 'MD' and self.packing_id.division == 'Unit' and self.packing_id.picking_type_id.code == 'incoming' and not self.packing_id.picking_id :
            ids_serial_number = self._get_lot_intransit()
        elif self.rel_code in ('outgoing','interbranch_out') and self.rel_branch_type == 'MD' and not self.rel_is_reverse :
            ids_serial_number = self.packing_id.get_lot_available_md()
        elif self.rel_code == 'interbranch_in' and self.rel_branch_type == 'MD' and not self.rel_is_reverse :
            ids_serial_number = self.packing_id.picking_id.get_reserve_lot_quant_ids()
        domain['serial_number_id'] = [('id','in',ids_serial_number)]
        return {'domain':domain}
    
    @api.onchange('product_id','source_location_id')
    def change_serial_number_id2(self):
        if self.rel_code == 'interbranch_out' and self.rel_branch_type == 'DL' and self.serial_number_id.product_id.id != self.product_id.id:
            self.serial_number_id = False
    
    @api.onchange('source_location_id')
    def change_source_location_id(self):
        if not self.source_location_id or self.packing_id.is_reverse and self.rel_code in ('incoming','interbranch_in') or not self.packing_id.picking_id :
            self.source_location_id = self.rel_source_location_id.id or self.packing_id.source_location_id.id
        if self.rel_code in ('outgoing','interbranch_out') and self.rel_division == 'Unit' and self.rel_branch_type == 'MD' and not self.rel_is_reverse :
            if self.serial_number_id :
                self.source_location_id = self.serial_number_id.location_id.id
        self.source_location_usage = self.source_location_id.usage
    
    @api.onchange('destination_location_id','product_id')
    def change_destination_location_id(self):
        if not self.destination_location_id or self.packing_id.is_reverse and self.rel_code in ('outgoing','interbranch_out') :
            self.destination_location_id = self.rel_destination_location_id.id or self.packing_id.destination_location_id.id
        elif (self.rel_code == 'incoming' and self.rel_branch_type == 'MD') or not self.packing_id.picking_id :
            self.destination_location_id = self._get_suggested_location(self.product_id.product_tmpl_id.id, self.product_id.attribute_value_ids.id, self.rel_destination_location_id.id)
        self.destination_location_usage = self.destination_location_id.usage

    @api.onchange('rel_source_location_id')
    def change_rel_source_location_id(self):
        if not self.rel_source_location_id and not self.packing_id.picking_id :
            self.rel_source_location_id = self.packing_id.source_location_id.id
    
    @api.onchange('rel_destination_location_id')
    def change_rel_destination_location_id(self):
        if not self.rel_destination_location_id and not self.packing_id.picking_id :
            self.rel_destination_location_id = self.packing_id.destination_location_id.id
    
    @api.onchange('quantity','product_id')
    def change_quantity(self):
        if self.product_id.categ_id.isParentName('Unit'):
            self.quantity = 1
        else :
            qty_max = self.get_qty_max(self.seharusnya, self.stock_available, self.current_reserved)
            if self.quantity > qty_max :
                self.quantity = qty_max
                warning = {'title':'Perhatian','message':"Quantity melebihi jumlah maksimal '%d'" %qty_max}
                return {'warning':warning}
            elif self.quantity < 0 :
                self.quantity = qty_max
                warning = {'title':'Perhatian','message':'Quantity tidak boleh kurang dari nol'}
                return {'warning':warning}
    
    @api.onchange('tahun_pembuatan','serial_number_id')
    def change_tahun_pembuatan(self):
        warning = {}
        if self.tahun_pembuatan and not self.tahun_pembuatan.isdigit() :
            self.tahun_pembuatan = False
            warning = {'title':'Perhatian', 'message':'Tahun Pembuatan hanya boleh angka'}
            return {'warning':warning}
        
        if self.rel_code == 'incoming' and not self.tahun_pembuatan :
            self.tahun_pembuatan = self._get_default_date().strftime('%Y')
        if self.serial_number_id :
            self.tahun_pembuatan = self.serial_number_id.tahun
    
    @api.onchange('serial_number_id')
    def change_ready_for_sale(self):
        if self.serial_number_id :
            self.ready_for_sale = self.convert_rfs(self.serial_number_id.ready_for_sale)
    
    @api.onchange('product_id')
    def change_seharusnya(self):
        seharusnya = self.packing_id.picking_id.get_seharusnya()
        if self.product_id in seharusnya :
            self.seharusnya = seharusnya[self.product_id]
        else :
            self.seharusnya = 0
        if self.packing_id.picking_id and not self.move_id:
            self.write({'move_id':self.env['stock.move'].search([('product_id','=',self.product_id.id),('picking_id','=',self.packing_id.picking_id.id)], limit=1).id})

    @api.onchange('product_id','source_location_id')
    def change_current_reserved(self):
        if self.rel_code in ('outgoing','interbranch_out','interbranch_in') or self.packing_id.is_reverse :
            ids_move = self.packing_id.picking_id.get_ids_move()
            if self.product_id and self.source_location_id :
                self.current_reserved = self.packing_id.picking_id.get_current_reserved(self.product_id.id, self.source_location_id.id, ids_move)
    
    @api.multi
    def get_stock_location(self, product_id, branch_id, move_id, usage=['internal'], where_query="", warn_kosong=False, lot_state=['stock']):
        if 'usage' in self._context:
            usage = self._context['usage']
        if 'lot_state' in self._context:
            lot_state = self._context['lot_state']
        move_query = ""
        if move_id:
            move_query = ("or q.reservation_id in %s") % (str(
                tuple(move_id)).replace(',)', ')'),)
        ids_location = []
        self._cr.execute("""
        SELECT
            q.location_id,
            l.name
        FROM
            stock_location l, stock_quant q
        LEFT JOIN
            stock_production_lot lot on lot.id = q.lot_id
        WHERE
            q.product_id = %s and l.branch_id = %s and (q.reservation_id is Null """ + move_query + """)
            and (q.lot_id is Null or lot.state in %s) and q.location_id = l.id and l.usage in %s """ + where_query + """
        GROUP BY
            q.location_id, l.name
        """,(product_id, branch_id, tuple(lot_state), tuple(usage)))
        for location in self._cr.fetchall():
            ids_location.append(location[0])
        if warn_kosong == True and len(ids_location) == 0:
            product = self.env['product.product'].browse(product_id)
            branch = self.env['dym.branch'].browse(branch_id)
            raise osv.except_osv(('Perhatian !'), ("Produk %s %s tidak ditemukan di branch %s, Mohon periksa stock!")%(product.name, product.description or product.default_code, branch.name))
        return ids_location

    @api.onchange('product_id','source_location_id')
    def change_stock_available(self):
        domain = {}
        if self.packing_id.is_reverse :
            if self.packing_id.rel_code in ('outgoing','interbranch_out'):
                if self.product_id.id and (self.packing_id.rel_branch_id.id or self.packing_id.branch_id.id):
                    ids_move = self.packing_id.picking_id.get_ids_move()
                    location_ids = self.get_stock_location(self.product_id.id, self.packing_id.rel_branch_id.id or self.packing_id.branch_id.id, ids_move)
                    domain['source_location_id'] = [('id','in',location_ids)]
                    if self.serial_number_id:
                        self.source_location_id = self.serial_number_id.location_id.id
                    else:
                        if location_ids:
                            move = self.move_id.search([('id','in',ids_move),('product_id','=',self.product_id.id),('location_id','in',location_ids)], limit=1)
                            if move:
                                self.source_location_id = move.location_id.id
                            elif self.source_location_id.id in location_ids:
                                self.source_location_id = self.source_location_id.id
                            else:
                                self.source_location_id = location_ids[0]
                self.stock_available = self.packing_id.picking_id.get_stock_available(self.product_id.id, self.source_location_id.id)
            else:
                self.stock_available = 0
        elif self.rel_code == 'incoming' :
            self.stock_available = self.seharusnya
        else :
            if self.product_id.id and (self.packing_id.rel_branch_id.id or self.packing_id.branch_id.id):
                ids_move = self.packing_id.picking_id.get_ids_move()
                location_ids = self.get_stock_location(self.product_id.id, self.packing_id.rel_branch_id.id or self.packing_id.branch_id.id, ids_move)
                domain['source_location_id'] = [('id','in',location_ids)]
                if self.packing_id.rel_code in ('outgoing','interbranch_out'):
                    if self.serial_number_id:
                        self.source_location_id = self.serial_number_id.location_id.id
                    else:
                        if location_ids:
                            move = self.move_id.search([('id','in',ids_move),('product_id','=',self.product_id.id),('location_id','in',location_ids)], limit=1)
                            if move:
                                self.source_location_id = move.location_id.id
                            elif self.source_location_id.id in location_ids:
                                self.source_location_id = self.source_location_id.id
                            else:
                                self.source_location_id = location_ids[0]
            if self.product_id and self.source_location_id :
                ids_move = self.packing_id.picking_id.get_ids_move()
                if self.product_id.categ_id.isParentName('Extras') :
                    self.stock_available = self.packing_id.picking_id.get_stock_available_extras(self.product_id.id, self.source_location_id.id)
                else :
                    self.stock_available = self.packing_id.picking_id.get_stock_available(self.product_id.id, self.source_location_id.id)
        return {'domain':domain}

    
    @api.onchange('product_id')
    def change_performance_hpp(self):
        if self.rel_code == 'interbranch_out' and self.rel_division == 'Unit' and self.packing_id.rel_branch_id.branch_type == 'MD' :
            mutation_order_id = self.env['dym.mutation.order'].search([('id','=',self.packing_id.picking_id.transaction_id)])
            self.performance_hpp = 0
            for mo_line in mutation_order_id.order_line :
                if self.product_id == mo_line.product_id :
                    self.performance_hpp = mo_line.performance_hpp
                    break
                
    @api.onchange('product_id')
    def freight_cost_change(self):
        if self.packing_id.expedition_id:
            if not self.packing_id.picking_id:
                if not self.packing_id.expedition_id :
                    raise osv.except_osv(('Perhatian !'), ("Silahkan pilih Ekspedisi terlebih dahulu !"))
                if not self.packing_id.branch_id :
                    raise osv.except_osv(('Perhatian !'), ("Silahkan input Branch terlebih dahulu !"))
                if not self.packing_id.division :
                    raise osv.except_osv(('Perhatian !'), ("Silahkan pilih Division terlebih dahulu !"))
                if not self.packing_id.picking_type_id :
                    raise osv.except_osv(('Perhatian !'), ("Silahkan pilih Picking Type terlebih dahulu !"))
            branch = self.packing_id.branch_id or self.packing_id.rel_branch_id
            self.freight_cost = branch.get_freight_cost(self.packing_id.expedition_id.id,self.product_id.id)
            
    @api.onchange('purchase_line_id','no_ship_list','serial_number_id')
    def change_purchase_line_id_ship_list(self):
        if self.serial_number_id :
            self.no_ship_list = self.serial_number_id.no_ship_list
            self.no_faktur = self.serial_number_id.no_faktur
            for order_line in self.serial_number_id.sudo().purchase_order_id.order_line :
                if order_line.product_id == self.serial_number_id.product_id :
                    self.purchase_line_id = order_line.id
                    break
        else :
            self.purchase_line_id = False
            self.no_ship_list = False
            self.no_faktur = False
        