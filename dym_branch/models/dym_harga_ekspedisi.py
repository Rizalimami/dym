import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from string import whitespace

class wiz_expedition_line(models.TransientModel):
    _name = 'wiz.expedition.line'
    _description = "Expedition Line Wizard"
        
    ekspedisi_line_id = fields.Many2one('dym.pricelist.expedition.line','Ekspedisi Line')
    cost = fields.Float('Expedition Cost')
    product_ids = fields.Many2many('product.template','wiz_ekspedisi_line_product_rel','wiz_ekspedisi_line_id','product_id','Products')

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("Data Error, please try to refresh page or contact your administrator!"))
        res = super(wiz_expedition_line, self).default_get(cr, uid, fields, context=context)
        ekspedisi_line_id = context and context.get('active_id', False) or False
        res.update(ekspedisi_line_id=ekspedisi_line_id)
        return res

    @api.onchange('product_ids')
    def product_change(self):
        domain = {}
        categ_unit = self.env['product.category'].get_child_ids('Unit')
        categ_sparepart = self.env['product.category'].get_child_ids('Sparepart')
        categ_umum = self.env['product.category'].get_child_ids('Umum')
        categ_ids = categ_unit + categ_sparepart + categ_umum        
        saved_product_ids = [line.product_template_id.id for line in self.ekspedisi_line_id.pricelist_expedition_line_detail_ids]
        domain['product_ids'] = [('categ_id','in',categ_ids),('id','not in',saved_product_ids)]
        return {'domain':domain}

    @api.one
    def save_expedition(self):
        for data in self:
            res = {}
            res['pricelist_expedition_line_id'] = data.ekspedisi_line_id.id
            res['cost'] = data.cost
            for product in data.product_ids:
                res['product_template_id'] = product.id
                data.ekspedisi_line_id.pricelist_expedition_line_detail_ids.create(res)
        return True

class dym_branch_harga_ekspedisi(models.Model):
    _inherit = 'dym.branch'
    harga_ekspedisi_ids = fields.One2many('dym.harga.ekspedisi','branch_id',string="Harga Ekspedisi")
    
class dym_harga_ekspedisi(models.Model):
    _name = "dym.harga.ekspedisi"
    _description = 'Harga Ekspedisi'

    branch_id = fields.Many2one('dym.branch',string="Branch")
    ekspedisi_id = fields.Many2one('res.partner',domain=[('forwarder','=',True)],string="Ekspedisi")
    default_ekspedisi = fields.Boolean(string="Default")
    harga_ekspedisi_id = fields.Many2one('dym.pricelist.expedition',string="Harga Ekspedisi")
    
    _sql_constraints = [
                        ('unique_ekspedisi', 'unique(branch_id,ekspedisi_id)', "'Ekspedisi' tidak boleh ada yang sama !"),  
                        ]
    
class dym_pricelist_expedition(models.Model):
    _name = "dym.pricelist.expedition"
    _description = "Pricelist Expedition"
    
    name = fields.Char('Name',required=True)
    active = fields.Boolean('Active',default=True)
    pricelist_expedition_line_ids = fields.One2many('dym.pricelist.expedition.line','pricelist_expedition_id',string="Pricelist Expedition Lines", copy=True)
    
class dym_pricelist_expedition_line(models.Model):
    _name = "dym.pricelist.expedition.line"
    _description = 'Pricelist Expedition Line'

    pricelist_expedition_id = fields.Many2one('dym.pricelist.expedition', 'Pricelist Expedition', required=True, select=True, ondelete='cascade')
    name = fields.Char('Name',required=True)
    start_date = fields.Date('Start Date',required=True)
    end_date = fields.Date('End Date',required=True)
    active = fields.Boolean('Active',default=True)
    pricelist_expedition_line_detail_ids = fields.One2many('dym.pricelist.expedition.line.detail','pricelist_expedition_line_id',string='Pricelist Expedition Line Details', required=True, copy=True)

    @api.onchange('start_date','end_date')
    def onchange_end_date(self):
        warning = {}
        if self.start_date and self.end_date :
            if self.end_date <= self.start_date :
                self.end_date = False
                warning = {
                           'title': ('Perhatian !'),
                           'message': ('End Date tidak boleh lebih kecil dari Start Date'),
                           }
        return {'warning':warning}
    
    def _check_date(self, cr, uid, ids, context=None):
        pricelist_expedition_line_id = self.browse(cr, uid, ids, context=context)
        ids_pricelist_expedition_line = self.pool.get('dym.pricelist.expedition.line').search(cr,uid,[
                                                                                                      ('pricelist_expedition_id','=',pricelist_expedition_line_id.pricelist_expedition_id.id),
                                                                                                      ('active','=',True),
                                                                                                      ('id','!=',pricelist_expedition_line_id.id),
                                                                                                      ])
        if ids_pricelist_expedition_line :
            pricelist_expedition_line_ids = self.pool.get('dym.pricelist.expedition.line').browse(cr,uid,ids_pricelist_expedition_line)
            for pricelist_expedition_line in pricelist_expedition_line_ids :
                if pricelist_expedition_line_id.start_date <= pricelist_expedition_line.end_date :
                    return False
        return True

    _constraints = [
                    (_check_date, 'You cannot have 2 pricelist versions that overlap!', ['start_date', 'end_date', 'active'])
                    ]
    
class dym_pricelist_expedition_line_detail(models.Model):
    _name = 'dym.pricelist.expedition.line.detail'
    _description = 'Pricelist Expedition Line Detail'

    pricelist_expedition_line_id = fields.Many2one('dym.pricelist.expedition.line', string='Pricelist Expedition Line', select=True, ondelete='cascade')
    product_template_id = fields.Many2one('product.template','Product',required=True)
    cost = fields.Float('Cost',required=True)

    _sql_constraints = [
                        ('unique_product', 'unique(pricelist_expedition_line_id,product_template_id)', 'Ditemukan produk duplicate, mohon cek kembali !'),
                        ]
    
    @api.onchange('product_template_id')
    def product_change(self):
        domain = {}
        categ_unit = self.env['product.category'].get_child_ids('Unit')
        categ_sparepart = self.env['product.category'].get_child_ids('Sparepart')
        categ_umum = self.env['product.category'].get_child_ids('Umum')
        categ_ids = categ_unit + categ_sparepart + categ_umum
        domain['product_template_id'] = [('categ_id','in',categ_ids)]
        return {'domain':domain}
    