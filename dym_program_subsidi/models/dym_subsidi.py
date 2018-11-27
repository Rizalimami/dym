import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
from lxml import etree

class wiz_program_subsidi(models.TransientModel):
    _name = 'wiz.program.subsidi'
    _description = "Program Subsidi Wizard"
        
    program_subsidi_id = fields.Many2one('dym.program.subsidi',"Program Subsidi" , ondelete='cascade')
    hutang_komisi_id = fields.Many2one('dym.hutang.komisi',"Hutang Komisi" , ondelete='cascade')
    subsidi_barang_id = fields.Many2one('dym.subsidi.barang',"Subsidi Barang" , ondelete='cascade')
    product_ids = fields.Many2many('product.template','wiz_program_subsidi_product_rel','wiz_program_subsidi_id','product_id','Products')
    tipe_dp = fields.Selection([('min','Min'),('max','Max')], 'Tipe JP')
    amount_dp = fields.Float("JP Min/Max")
    diskon_ahm = fields.Float("Diskon AHM")
    diskon_md = fields.Float("Diskon MD")
    diskon_dealer = fields.Float("Diskon Dealer")
    diskon_finco = fields.Float("Diskon Finco")
    diskon_others = fields.Float("Diskon Others")
    tipe_diskon = fields.Selection([('amount','Amount'),('percentage','Percentage')], 'Tipe Diskon')
    diskon_persen = fields.Float("Diskon Persen")
    qty = fields.Integer("Qty")
    tenor = fields.Char('Tenor (Misal:11 atau 11-16)', placeholder="Misal: 11 atau 11-16", help="Isi dengan tenor/bulan misal: 23 jika tenor 23 bulan atau dengan range misal: 23-28 untuk tenor 23 bulan hingga 28 bulan.")
    amount = fields.Float('Amount')

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("Data Error, please try to refresh page or contact your administrator!"))
        res = super(wiz_program_subsidi, self).default_get(cr, uid, fields, context=context)
        program_subsidi_id = context and context.get('program_subsidi_id', False) or False
        hutang_komisi_id = context and context.get('hutang_komisi_id', False) or False
        subsidi_barang_id = context and context.get('subsidi_barang_id', False) or False
        res.update(program_subsidi_id=program_subsidi_id)
        res.update(hutang_komisi_id=hutang_komisi_id)
        res.update(subsidi_barang_id=subsidi_barang_id)
        return res

    @api.onchange('product_ids')
    def product_change(self):
        domain = {}
        division = self.program_subsidi_id.division or self.hutang_komisi_id.division or self.subsidi_barang_id.division
        categ_ids = self.env['product.category'].get_child_ids(division)
        if division == 'Sparepart':
            categ_ids += self.env['product.category'].get_child_ids('Service')
        if self.program_subsidi_id:
            saved_product_ids = [line.product_template_id.id for line in self.program_subsidi_id.program_subsidi_line]
        elif self.hutang_komisi_id:
            saved_product_ids = [line.product_template_id.id for line in self.hutang_komisi_id.hutang_komisi_line]
        elif self.subsidi_barang_id:
            saved_product_ids = [line.product_id.id for line in self.subsidi_barang_id.subsidi_barang_line]
        domain['product_ids'] = [('type','!=','view'),('categ_id','in',categ_ids),('id','not in',saved_product_ids)]
        return {'domain':domain}
    
    @api.onchange('tipe_diskon')
    def onchange_tipe_diskon(self):
        value = {}
        if self.tipe_diskon == 'percentage':
            self.diskon_ahm = 0
            self.diskon_md = 0
            self.diskon_dealer = 0
            self.diskon_finco = 0
            self.diskon_others = 0
        elif self.tipe_diskon == 'amount':
            self.diskon_persen = 0
        return {'value':value}

    @api.onchange('tenor')
    def onchange_tenor(self):
        valid = True
        if self.tenor:
            if '-' in self.tenor:
                tenor_range = self.tenor.split('-')
                try:
                    tenor_start = int(tenor_range[0])
                except:
                    valid = False
                try:
                    tenor_end = int(tenor_range[1])
                except:
                    valid = False
                if tenor_start>=tenor_end:
                    valid = False                    
            else:
                try:
                    tenor = int(self.tenor)
                except:
                    valid = False
        if not valid:
            raise osv.except_osv(_('Warning!'), _("Data tenor salah, seharusnya angka saja misal: 11 atau range misal: 11-16"))


    @api.one
    def save_program(self):
        tenors = []
        for data in self:
            if not data:
                continue
            if data.tenor and '-' in data.tenor:
                tenor_range = self.tenor.split('-')
                tenor_start = int(tenor_range[0])
                tenor_end = int(tenor_range[1])
                tenors = range(tenor_start,tenor_end+1)
            else:
                tenors = [int(data.tenor)]

            tenor = min(tenors)
            tenor_range = data.tenor 
            res = {}
            res['program_subsidi_id'] = data.program_subsidi_id.id
            res['hutang_komisi_id'] = data.hutang_komisi_id.id
            res['subsidi_barang_id'] = data.subsidi_barang_id.id
            res['tipe_dp'] = data.tipe_dp
            res['amount_dp'] = data.amount_dp
            res['diskon_ahm'] = data.diskon_ahm
            res['diskon_md'] = data.diskon_md
            res['diskon_dealer'] = data.diskon_dealer
            res['diskon_finco'] = data.diskon_finco
            res['diskon_others'] = data.diskon_others
            res['tipe_diskon'] = data.tipe_diskon
            res['diskon_persen'] = data.diskon_persen
            res['tenor'] = tenor
            res['tenor_range'] = tenor_range            
            res['qty'] = data.qty
            res['amount'] = data.amount
            for product in data.product_ids:
                if data.program_subsidi_id:
                    res['product_template_id'] = product.id
                    create_id = data.program_subsidi_id.program_subsidi_line.create(res)
                elif data.hutang_komisi_id:
                    res['product_template_id'] = product.id
                    create_id = data.hutang_komisi_id.hutang_komisi_line.create(res)
                elif data.subsidi_barang_id:
                    res['product_id'] = product.id
                    create_id = data.subsidi_barang_id.subsidi_barang_line.create(res)
        return True

class dym_program_subsidi(models.Model):
    _inherit = 'dym.program.subsidi'

    @api.one
    @api.depends('program_subsidi_line.product_template_id','program_subsidi_line.product_template_id.product_variant_ids')
    def _get_product_ids(self):
        product_ids = []
        for line in self.program_subsidi_line:
            product_ids += line.product_template_id.product_variant_ids.ids
        self.product_ids = product_ids
   
    product_ids = fields.Many2many('product.product', string='Products', compute='_get_product_ids', store=True)