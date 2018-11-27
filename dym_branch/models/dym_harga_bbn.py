from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _

class dym_harga_bbn(models.Model):
    _name = "dym.harga.bbn"
    _description = "Harga Beli BBN"
    
    name = fields.Char('Name',required=True)
    active = fields.Boolean('Active',default=True)
    harga_bbn_line_ids = fields.One2many('dym.harga.bbn.line','bbn_id',string="Line")
    
    def copy(self, cr, uid, id, default=None, context=None):
        default = dict(context or {})
        harga_bbn = self.browse(cr, uid, id, context=context)
        default.update(
            name=_("%s (copy)") % (harga_bbn['name'] or ''),
            harga_bbn_line_ids=_([]))
        new_harga_id = super(dym_harga_bbn, self).copy(cr, uid, id, default, context=context)
        for harga_line in harga_bbn.harga_bbn_line_ids:
            new_harga_line_id = harga_line.copy({'bbn_id':new_harga_id, 'harga_bbn_line_detail_ids':[]})
            for harga_line_detail in harga_line.harga_bbn_line_detail_ids:
                new_harga_line_detail_id = harga_line_detail.copy({'harga_bbn_line_id':new_harga_line_id.id})
        return new_harga_id

    def unlink(self, cr, uid, ids, context=None):
        for harga_bbn in self.browse(cr, uid, ids, context=context):
            for harga_line in harga_bbn.harga_bbn_line_ids:
                harga_line.harga_bbn_line_detail_ids.unlink()
        return super(dym_harga_bbn, self).unlink(cr, uid, ids, context=context)

class dym_harga_bbn_line(models.Model):
    _name = 'dym.harga.bbn.line'
    _description = 'Harga Beli BBN Line'

    bbn_id = fields.Many2one('dym.harga.bbn','Harga Beli BBN',required=True,ondelete="cascade")
    name = fields.Char('Name',required=True)
    tipe_plat = fields.Selection([('H','Hitam'),('M','Merah')],'Tipe Plat',required=True)
    start_date = fields.Date('Start Date',required=True)
    end_date = fields.Date('End Date',required=True)
    active = fields.Boolean('Active',default=True)
    harga_bbn_line_detail_ids = fields.One2many('dym.harga.bbn.line.detail','harga_bbn_line_id',string='Details')

        
    @api.onchange('end_date')
    def onchange_end_date(self):
        warn = {}
        if self.end_date :
            if self.end_date <= self.start_date :
                self.end_date = False
                warn = {
                    'title': ('Perhatian !'),
                    'message': ('End Date tidak boleh lebih kecil dari Start Date'),
                } 
        return {'warning':warn}
    
    @api.v7            
    def _check_date(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context=context)
        bbn = self.pool.get('dym.harga.bbn.line').search(cr,uid,[
                                                                 ('bbn_id','=',val.bbn_id.id),
                                                                 ('active','=',True),
                                                                 ('id','!=',val.id),
                                                                 ('tipe_plat','=',val.tipe_plat)
                                                                 ])
        if bbn :
            bbn_browse = self.pool.get('dym.harga.bbn.line').browse(cr,uid,bbn)
            for x in bbn_browse :
                if val.start_date <= x.end_date and val.end_date >= x.start_date :
                    return False
        return True
    
    @api.multi
    def _check_start_end_date(self):
        if self.start_date > self.end_date:
            return False
        return True

    # _constraints = [
    #     (_check_date, 'You cannot have 2 pricelist versions that overlap!',
    #         ['start_date', 'end_date', 'active']),
    #     (_check_start_end_date, 'start date tidak boleh melebihi end date!',['start_date','end_date'])
    # ]
    
class dym_harga_bbn_line_detail(models.Model):
    _name = 'dym.harga.bbn.line.detail'
    _description = 'Harga BBN Detail'

    harga_bbn_line_id = fields.Many2one('dym.harga.bbn.line',string='Harga Beli BBN Line',required=True)
    product_template_id = fields.Many2one('product.template','Product',required=True)
    city_id = fields.Many2one('dym.city','City',required=True)
    notice = fields.Float('Notice',required=True)
    proses = fields.Float('Plat,Buku BPKB dll',required=True)
    jasa = fields.Float('Jasa',required=True)
    jasa_area = fields.Float('Jasa Area')
    fee_pusat = fields.Float('Fee Pusat')
    total = fields.Float('Total',required=True)

    @api.onchange('notice','proses','jasa','jasa_area','fee_pusat','total')
    def total_change(self):
        self.total = self.notice+self.proses+self.jasa+self.jasa_area+self.fee_pusat

    _sql_constraints = [
    ('unique_bbn', 'unique(harga_bbn_line_id,product_template_id,city_id)', 'Detail BBN duplicate, mohon cek kembali !'),
]   
    
    @api.onchange('product_template_id')
    def _get_domain_product_type(self):
        domain = {} 
        categ_ids = self.env['product.category'].get_child_ids('Unit')
        domain['product_template_id'] = [('type','!=','view'),('categ_id','in',categ_ids)]
        return {'domain':domain}  