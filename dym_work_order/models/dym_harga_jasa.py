import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _


class dym_work_order(models.Model):
    _inherit = "dym.work.order"
    
    @api.one
    def _amount_all(self):
        val = val1 = 0.0
        for line in self.work_lines:
            if self.type=='WAR':
                if line.job_redo and line.categ_id=="Sparepart":
                    raise osv.except_osv(_('Error!'),_('Job Return Category Sparepart tidak diperkenankan !'))
                if not line.job_redo:
                    continue
            val1 += line.price_subtotal
            val += self._amount_line_tax(line)
        self.amount_tax = val
        self.amount_untaxed = val1
        self.amount_total = self.amount_untaxed + self.amount_tax

    amount_untaxed = fields.Float(string='Tax Base', compute='_amount_all')
    amount_tax = fields.Float(string='Taxes', compute='_amount_all')
    amount_total = fields.Float(string='Total', compute='_amount_all')

class dym_harga_jasa_version(models.Model):
    _name="dym.harga.jasa.version"
    _description="Harga Jasa Version"
    
    name=fields.Char(string="Version Name",required=True)
    active=fields.Boolean(string="Active")
    date_start=fields.Date(string="Start Date",required=True)
    date_end=fields.Date(string="End Date",required=True)
    
    @api.onchange('date_start','date_end')
    def onchange_date(self):
        warning = {}
        if self.date_start and self.date_end :
            if self.date_end < self.date_start :
                warning = {'title': ('Warning !'), 'message': (('End Date tidak boleh kurang dari Start Date ! ')),} 
                self.end_date = False                  
        return {'warning':warning}
    

    
    @api.model
    def create(self,values,context=None):
        # obj_version=self.env['dym.harga.jasa.version'].search([('active','=',True)])
        # if obj_version :
        #      for x in obj_version :
        #          if values['date_start'] <= x.date_end and values['date_end'] >= x.date_start :
        #              raise osv.except_osv(('Perhatian !'), ("Terdapat tanggal version harga jasa yang sama !"))
        version_harga_jasa = super(dym_harga_jasa_version,self).create(values)
        return version_harga_jasa
            




class dym_harga_jasa(models.Model):
    _name = 'dym.harga.jasa'

    
    harga_jasa_version_id=fields.Many2one("dym.harga.jasa.version",string="Version",required=True)
    product_id_jasa = fields.Many2one('product.product', 'Jasa',required=True)
    category_product_id = fields.Many2one('dym.category.product', 'Category Service',required=True)
    price = fields.Float(string='Price')
    workshop_category = fields.Many2one('dym.workshop.category', 'Workshop Category',required=True)
    
    _sql_constraints = [
    ('unique_harga_jasa', 'unique(product_id_jasa,category_product_id,workshop_category)', 'Master Jasa sudah pernah dibuat !'),
    ] 
    
    
    @api.onchange('product_id_jasa')
    def _get_domain_product_type(self):
        domain = {} 
        #categ_ids = self.env['product.category'].get_child_ids('Unit')
        categ_product_ids = self.env['product.category'].get_child_ids('Service') 
        #domain['product_id_unit'] = [('type','!=','view'),('categ_id','in',categ_ids)]
        domain['product_id_jasa'] = [('type','!=','view'),('categ_id','in',categ_product_ids)]  
        return {'domain':domain}  
    
    
    @api.onchange('harga_jasa_version_id')
    def _get_version_harga_jasa(self):
        domain = {} 
        obj_periode=self.env['dym.harga.jasa.version'].search([('date_start','<=',datetime.today()),('date_end','>=',datetime.today()),('active','=',True)])
        periode_ids=[b.id for b in obj_periode]
        domain['harga_jasa_version_id'] = [('id','in',periode_ids)]
        return {'domain':domain}  
     
    
   