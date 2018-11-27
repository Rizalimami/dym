from openerp import api, fields, models, SUPERUSER_ID
import re


class dym_production_stock_lot(models.Model):
    _inherit = 'stock.production.lot'
     

    @api.multi
    def name_onchange(self,product_id,name):
        dom = {}
        # product_ids = self.env['product.category'].get_child_ids('Unit')
        # dom['product_id']=[('categ_id','in',product_ids)]
        product_ids = []
        if name:
            kd_mesin = name[:5]
            name = name.replace(' ', '').upper()
            kd_mesin = kd_mesin.replace(' ', '').upper()
            prod_tmpl_src = self.env["product.template"].search([("kd_mesin","=",kd_mesin)])
            if prod_tmpl_src:
                for x in prod_tmpl_src:
                    prod_prod_src = self.env["product.product"].search([("product_tmpl_id","=",x.id)])
                    if prod_prod_src:
                        for y in prod_prod_src:
                            product_ids.append(y.id)
        dom['product_id']=[('id','in',product_ids)]
        return {'value' : {'name':name,'state':'workshop'},'domain':dom }
        
    @api.multi
    def chassis_onchange(self,chassis_no):
        if chassis_no :
            chassis_no = chassis_no.replace(' ', '').upper()
            return {'value' : {'chassis_no':chassis_no}}

    @api.multi
    def nosin_onchange(self,name):
        dom = {}
        product_ids = []
        if name:
            kd_mesin = name[:5]
            name = name.replace(' ', '').upper()
            kd_mesin = kd_mesin.replace(' ', '').upper()
            prod_tmpl_src = self.env["product.template"].search([("kd_mesin","=",kd_mesin)])
            if prod_tmpl_src:
                for x in prod_tmpl_src:
                    prod_prod_src = self.env["product.product"].search([("product_tmpl_id","=",x.id)])
                    if prod_prod_src:
                        for y in prod_prod_src:
                            product_ids.append(y.id)
        dom['product_id']=[('id','in',product_ids)]
        return {'domain': dom}
        
    @api.multi
    def no_pol_onchange(self,no_polisi):
        warning = {}
        value = {}
        result = {}
        if no_polisi:
            formatted_no_polisi = ''
            no_polisi_normalize = no_polisi.replace(' ', '').upper()
            splitted_no_polisi = re.findall(r'[A-Za-z]+|\d+', no_polisi_normalize)
            if len(splitted_no_polisi) == 3:
              if splitted_no_polisi[0].isalpha() == True and splitted_no_polisi[1].isdigit() == True and splitted_no_polisi[2].isalpha() == True:
                for word in splitted_no_polisi:
                  formatted_no_polisi += word + ' '
                formatted_no_polisi = formatted_no_polisi[:-1]
                return {'value':{'no_polisi':formatted_no_polisi}}              
            warning = {
                'title': ('Perhatian !'),
                'message': (('Format nomor polisi salah, mohon isi nomor polisi dengan format yang benar! (ex. A 1234 BB)')),
            }
            value['no_polisi'] = self.no_polisi
            result['warning'] = warning
            result['value'] = value
            return result
    
    @api.multi
    def kode_buku_onchange(self,kode_buku):
        if kode_buku :
            kode_buku = kode_buku.replace(' ', '').upper()
            return {'value' : {'kode_buku':kode_buku}}
        
    @api.multi
    def nama_buku_onchange(self,nama_buku):
        if nama_buku :
            nama_buku = nama_buku.replace(' ', '').upper()
            return {'value' : {'nama_buku':nama_buku}}
    
    
    work_order_ids = fields.One2many('dym.work.order','lot_id',string="Work Orders",readonly=True)

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.no_polisi:
                name = "%s - %s" % (record.no_polisi, name)
            res.append((record.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name and len(name) >= 3:
            args = ['|',('name', operator, name),('no_polisi', operator, name)] + args
        categories = self.search(args, limit=limit)
        return categories.name_get()

    @api.model
    def create(self, vals):
        if not vals.get('product_id'):
            return False
        res = super(dym_production_stock_lot, self).create(vals)
        return res
    
    
class dym_res_partner_wo(models.Model):
    _inherit = 'res.partner'
    
    @api.multi
    def name_wo_onchange(self,name):
        if name :
            name = name.replace(' ', '').upper()
            return {'value' : {'name':name} }
         