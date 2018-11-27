# -*- coding: utf-8 -*-
from openerp import fields, api, models, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv
import time

class dym_stock_packing(models.Model):
    _inherit = 'dym.stock.packing'

    import_sj = fields.Boolean("Import Surat Jalan")
    sj_id = fields.Many2one('po.sj.import', 'Nomor Surat Jalan')
    no_faktur = fields.Char(string="Supplier Invoice Number", compute="_get_no_supplier_invoice")

    @api.onchange('import_sj')
    def onchange_import_sj(self):
        if not self.import_sj:
            self.sj_id = False
            self.sj_no = False
            self.no_faktur = False

    def _get_no_supplier_invoice(self):
        if self.sj_id:
            self.no_faktur = self.sj_id.no_faktur

    @api.multi
    def post(self):
        res = super(dym_stock_packing,self).post()
        if self.import_sj and self.sj_id:
            if self.rel_code == "incoming" and self.rel_division == "Unit":
                # Change status receive
                imp_sj_lines = self.env['po.sj.import.line']
                for pack in self.packing_line:
                    sj_line = imp_sj_lines.search([('import_id','=',self.sj_id.id),('nomor_mesin','=',pack.engine_number), ('nomor_rangka','=',pack.chassis_number)])
                    sj_line.sts_receive = True

                item_line = self.sj_id.unit_lines
            elif self.rel_code == "incoming" and self.rel_division == "Sparepart":
                # Change status receive
                imp_sj_lines = self.env['po.sj.import.line']
                for pack in self.packing_line3:
                    sj_line = imp_sj_lines.search([('import_id','=',self.sj_id.id),('kode_product','=',pack.product_id.name_template)])
                    if sj_line.qty_receive:
                        sj_line.qty_receive += pack.quantity
                    else:
                        sj_line.qty_receive = pack.quantity

                    if sj_line.quantity == sj_line.qty_receive:
                        sj_line.sts_receive = True

                item_line = self.sj_id.part_lines

            # Update state Surat Jalan
            if self.sj_id:
                status = 0
                for line in item_line:
                    if line.sts_receive == False:
                        status += 1
                if status == 0:
                    self.sj_id.write({'state': 'done'})
        return res

    @api.onchange('sj_id')
    def onchange_sj(self):
        if self.sj_id:
            vals = []
            list_product = []
            unit_qty = {}
            self.sj_no = self.sj_id.name
            self.sj_date = self.sj_id.shipping_date
            self.no_faktur = self.sj_id.no_faktur
            for sj in self.env['po.sj.import.line'].search([('sts_receive', '=', False), ('import_id','=',self.sj_id.id)]):
                if self.rel_division == "Unit":
                    attr_warna = self.env['product.attribute.value'].search([('code','=',sj.kode_warna)], limit=1)
                    if len(attr_warna) > 1:
                        for warna in attr_warna:
                            p_product = self.env['product.product'].search([('name_template', '=', sj.kode_product), ('attribute_value_ids','=',warna.id),('active','=',True)])
                            if p_product:
                                break
                    else:
                        p_product = self.env['product.product'].search([('name_template', '=', sj.kode_product), ('attribute_value_ids','=',attr_warna.id),('active','=',True)])

                    stock_move = self.env['stock.move'].search([('product_id','=',p_product.id),('picking_id','=',self.picking_id.id)])

                    if stock_move:
                        if p_product.id not in list_product:
                            list_product.append(p_product.id)
                            unit_qty[p_product.id] = 1
                        else:
                            unit_qty[p_product.id] += 1

                        if unit_qty[p_product.id] <= stock_move.product_qty:
                            vals.append({
                                'packing_id': self.id,
                                'engine_number': sj.nomor_mesin,
                                'chassis_number': sj.nomor_rangka,
                                'template_id': p_product.product_tmpl_id.id,
                                'product_id': p_product.id,
                                'quantity': 1,
                                'tahun_pembuatan': sj.tahun_perakitan,
                                'no_faktur': sj.no_faktur,
                                # 'move_id': stock_move.id,
                            })
                elif self.rel_division == "Sparepart":
                    p_product = self.env['product.product'].search([('name_template', '=', sj.kode_product),('active','=',True)])
                    stock_move = self.env['stock.move'].search([('product_id','=',p_product.id),('picking_id','=',self.picking_id.id)])
                    if stock_move:
                        if sj.quantity-sj.qty_receive > stock_move.product_uom_qty:
                            qty = stock_move.product_uom_qty
                        else:
                            qty = sj.quantity-sj.qty_receive
                        vals.append({
                            'packing_id': self.id,
                            'template_id': p_product.product_tmpl_id.id,
                            'product_id': p_product.id,
                            'quantity': qty,
                            'no_faktur': sj.no_faktur,
                        })

            if not vals:
                warning = {
                            'title':'Perhatian !',
                            'message':"Maaf item di Surat Jalan tidak sesuai dengan PO!!"
                        }
                return {'warning': warning}
            else:
                if self.rel_division == "Unit":
                    self.packing_line = vals
                elif self.rel_division == "Sparepart":
                    self.packing_line3 = vals

    @api.onchange('packing_line', 'packing_line3')
    def _change_packing_line(self):
        if self.sj_id:
            if self.rel_division == "Unit":
                packing_line = self.packing_line
            elif self.rel_division == "Sparepart":
                packing_line = self.packing_line3

            for line in packing_line:
                line.change_engine_number()
                line.change_chassis_number()
                line.change_product_id()
                # line.change_template()
                line.change_current_reserved()
                line.change_performance_hpp()
                # line.change_quantity()
                line.change_seharusnya()
                line.change_serial_number_id()
                line.change_serial_number_id2()
                line.change_stock_available()
                line.freight_cost_change()
                # line.change_tahun_pembuatan()
                # line.change_purchase_line_id_ship_list()
                line.change_rel_source_location_id()
                line.change_rel_destination_location_id()
                line.change_source_location_id()
                line.change_default()
                line.change_rfs()

class po_sj_import(models.Model):
    _name = 'po.sj.import'

    name = fields.Char(string="Nomor Surat Jalan")
    shipping_date = fields.Date(string="Tanggal Surat Jalan")
    branch_id = fields.Many2one("dym.branch", string="Branch")
    nopol = fields.Char(string="Nopol Ekspedisi")
    no_faktur = fields.Char(string="Supplier Invoice Number")
    faktur_date = fields.Date(string="Supplier Invoice Date")
    no_nd = fields.Char(string="No. ND")
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop')], string='Division', select=True)
    user_id = fields.Many2one('res.users', string='PDI')
    unit_lines = fields.One2many('po.sj.import.line','import_id')
    part_lines = fields.One2many('po.sj.import.line','import_id')
    sj_ids = fields.One2many('dym.stock.packing', 'sj_id')
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('confirmed','Confirmed'),
        ('done','Done'),
        ('cancel','Cancelled'),
        ], 'State', default='draft')

    @api.one
    @api.constrains('name')
    def _check_no_sj(self):
        if len(self.search([('name', '=', self.name)])) > 1:
            raise Warning(_('Maaf nomor surat jalan sudah pernah di import.'))

    @api.multi
    def act_validate(self):
        self.write({'state': 'confirmed'})

    @api.multi
    def unlink(self):
        for sj in self:
            status = 0
            if sj.state != 'draft':
                status += 1
            if status == 0:
                for line in sj.unit_lines:
                    if status > 0:
                        break
                    elif line.sts_receive == True:
                        status += 1
            if status > 0:
                raise Warning(_('Maaf data tidak dapat di delete.'))
        return super(po_sj_import, self).unlink()

class po_sj_import_line(models.Model):
    _name = 'po.sj.import.line'

    import_id = fields.Many2one('po.sj.import', string='No SJ', ondelete='cascade')
    nomor_surat_jalan = fields.Char("Nomor Surat Jalan")
    tanggal_shipping = fields.Date("Tanggal Surat Jalan")
    rel_division = fields.Selection(related='import_id.division', string='Division')
    kode_dealer = fields.Char("Kode Dealer")
    kode_cabang_dealer = fields.Char("Kode Cabang Dealer")
    kode_warna = fields.Char("Kode Warna")
    nomor_mesin = fields.Char("Nomor Mesin")
    nomor_rangka = fields.Char("Nomor Rangka")
    tahun_perakitan = fields.Char("Tahun Perakitan")
    kode_product = fields.Char("Kode Product")
    nama_product = fields.Char("Nama Product")
    kode_warna = fields.Char("Kode Warna")
    kode_tipe_product = fields.Char("Kode Tipe Product")
    quantity = fields.Float("Quantity")
    qty_receive = fields.Float("Quantity Receive", default=0)
    qty_residual = fields.Float("Quantity Residual")
    no_faktur = fields.Char("No Faktur")
    sts_receive = fields.Boolean("Status Receive")

    @api.multi
    @api.constrains('nomor_mesin','nomor_rangka')
    def _check_no_sj(self):
        if len(self.search([('nomor_mesin', '=', self.nomor_mesin)])) > 1:
            raise Warning(_('Maaf engine number {} sudah pernah di import.'.format(self.nomor_mesin)))
        if len(self.search([('nomor_rangka', '=', self.nomor_rangka)])) > 1:
            raise Warning(_('Maaf chassis number {} sudah pernah di import.'.format(self.nomor_rangka)))

    @api.constrains('quantity','qty_receive')
    def _summary_qty_residual(self):
        if self.rel_division == 'Sparepart' and self.quantity:
            self.write({'qty_residual': self.quantity-self.qty_receive})


class dym_stock_packing_line(models.Model):
    _inherit = "dym.stock.packing.line"

    @api.onchange('engine_number','serial_number_id')
    def change_engine_number(self):
        template_id = self.template_id
        res = super(dym_stock_packing_line, self).change_engine_number()
        if self.packing_id.import_sj:
            self.template_id = template_id