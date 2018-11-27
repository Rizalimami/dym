import time
from datetime import datetime
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import pdb


class dym_check_frt_history(models.Model):
    _name="dym.check.frt.history"

    # frt_id = fields.Many2one("dym.frt")
    # branch_id = fields.Many2one('dym.branch', 'Branch')
    time = fields.Integer(string='Menit')
    rate = fields.Float(string='Rate')
    date = fields.Date(string="Date")
    price = fields.Float(string="Price")
    adjust = fields.Boolean(string='Adjustment Price', default=False)
    check_frt_id = fields.Many2one("dym.check.frt", readonly=True, invisible=True)

class dym_check_frt(models.Model):
    _name="dym.check.frt"

    branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    frt_id = fields.Many2one("dym.frt", string='Flat Rate Time', required=True)
    date_start = fields.Date(string="Date Start")
    date_end = fields.Date(string="Date End")
    frt_history_line_dummy = fields.One2many('dym.check.frt.history', 'check_frt_id', string='FRT History',readonly=True)
    
    @api.model
    def create(self,values,context=None):
        raise ValidationError("Tidak bisa disimpan, form ini hanya untuk Pengecekan!")
        return False
    
    @api.onchange('branch_id','frt_id','date_start','date_end')
    def field_change(self):
        value = {}
        warning = {}
        dym_frt_history_obj = self.env['dym.frt.history']
        value['frt_history_line_dummy'] = False
        domain = {}
        domain_search = []
        
        if self.branch_id and self.frt_id:
            domain_search += ['|','&',('branch_id', '=', self.branch_id.id),('rate', '>', 0)]
            domain_search += ['|','&',('frt_id', '=', self.frt_id.id),('time', '>', 0)]
            domain_search += ['&','&',('branch_id', '=', self.branch_id.id),('frt_id', '=', self.frt_id.id),('price', '>', 0)]
                 
            frt_history = dym_frt_history_obj.search(domain_search, order='date asc, id asc')
            show_check_history_id = []
            if frt_history:
                check_frt_history_obj = self.env['dym.check.frt.history']
                check_frt_history_ids = []

                rate = 0
                time = 0
                no = 0
                for data in frt_history:
                    price = 0
                    date = False
                    if data.time > 0:
                        time = data.time
                    if data.rate > 0:
                        rate = data.rate
                    if (self.date_start and data.date < self.date_start) or (self.date_end and data.date > self.date_end):
                        continue
                    price = rate * time
                    adjust = False
                    if data.price > 0:
                        price = data.price
                        adjust = True
                    date = data.date        
                    if price > 0:
                        show_check_history_id.append({no:[0,0,{
                            'date': date,
                            'time': time,
                            'rate': rate,
                            'price': price,
                            'adjust': adjust,
                        }]})
                        no += 1
            res = []
            for x in sorted(show_check_history_id, reverse=True):
                no -= 1
                res.append(x[no])
            self.frt_history_line_dummy = res


class dym_frt_history(models.Model):
    _name="dym.frt.history"
    _description="Flat Rate Time Line"
    _order="date desc, id desc"
    
    frt_id = fields.Many2one("dym.frt")
    time = fields.Integer(string='Menit')
    branch_id = fields.Many2one('dym.branch', 'Branch')
    rate = fields.Float(string='Jasa')
    date = fields.Date(string="Date", default=fields.Date.context_today)
    price = fields.Float(string="Price")

class dym_frt_history_dummy(models.Model):
    _name="dym.frt.history.dummy"

    branch_id = fields.Many2one('dym.branch', 'Branch')
    time = fields.Integer(string='Menit')
    rate = fields.Float(string='Rate')
    date = fields.Date(string="Date")
    price = fields.Float(string="Price")
    adjust = fields.Boolean(string='Adjustment Price', default=False)
    frt_id = fields.Many2one("dym.frt", readonly=True, invisible=True)

class dym_frt(models.Model):
    _name = 'dym.frt'

    @api.multi
    def name_get(self):
        result = []
        for inv in self:
            result.append((inv.id, "%s [%s]" % (inv.product_id_jasa.name, inv.category_product_id.name)))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name and len(name) >= 3:
            recs = [('product_id_jasa', operator, name)] + args
        recs = self.search(args, limit=limit)
        return recs.name_get()

    @api.one
    def _check_history(self):
        obj_frt_history = self.env['dym.frt.history'].search([('frt_id','=',self.id)])
        if obj_frt_history:
            self.frt_history_exist = True
        else:
            self.frt_history_exist = False


    @api.one
    def _check_frt_per_branch(self):
        dym_frt_history_obj = self.env['dym.frt.history']
        branch_obj = self.env['dym.branch']
        if self.frt_history_exist:
            self.env['dym.frt.history.dummy'].unlink()
            show_check_history_ids = []
            for branch in branch_obj.search([('rate','>',0)]):
                domain_search = []
                domain_search += ['|','&',('branch_id', '=', branch.id),('rate', '>', 0)]
                domain_search += ['|','&',('frt_id', '=', self.id),('time', '>', 0)]
                domain_search += ['&','&',('branch_id', '=', branch.id),('frt_id', '=', self.id),('price', '>', 0)]
                    
                frt_history = dym_frt_history_obj.search(domain_search, order='date asc, id asc')
                if frt_history:
                    res = {}

                    rate = 0
                    time = 0
                    for data in frt_history:
                        price = 0
                        date = False
                        if data.time > 0:
                            time = data.time
                        if data.rate > 0:
                            rate = data.rate
                        price = rate * time
                        adjust = False
                        if data.price > 0:
                            price = data.price
                            adjust = True
                        date = data.date        
                        if price > 0:
                            res = {
                                'frt_id': self.id,
                                'branch_id': branch.id,
                                'date': date,
                                'time': time,
                                'rate': rate,
                                'price': price,
                                'adjust': adjust,
                            }
                    if res:
                        show_check_history_ids.append(self.env['dym.frt.history.dummy'].create(res).id)
            self.frt_history_line_dummy = self.env['dym.frt.history.dummy'].search([('id','in',show_check_history_ids)])

    product_id_jasa = fields.Many2one('product.template', 'Jasa',required=True)
    category_product_id = fields.Many2one('dym.category.product', 'Category Service',required=True)
    time = fields.Integer(string='Menit', required=True)
    frt_history_exist = fields.Boolean(string='FRT History', readonly=True, compute='_check_history')
    frt_history_line_dummy = fields.One2many('dym.frt.history.dummy', 'frt_id', string='FRT History',readonly=True, compute='_check_frt_per_branch')
    
    @api.constrains('product_id_jasa','category_product_id')
    def _constrain_frt(self):
        obj_frt = self.search([('product_id_jasa','=',self.product_id_jasa.id),('category_product_id','=',self.category_product_id.id),('id','!=',self.id)])
        if obj_frt:
            raise ValidationError("Master FRT sudah pernah dibuat!")

    @api.constrains('time')
    def _constrain_time(self):
        if self.time <= 0:
            raise ValidationError("Menit harus lebih dari 0!")
        self.env['dym.frt.history'].create({
            'frt_id': self.id,
            'time': self.time,
            'branch_id': False,
            'rate': 0,
            'date': datetime.today(),
            'price': 0,
        })

    @api.onchange('product_id_jasa')
    def _get_domain_product_type(self):
        domain = {}
        categ_product_ids = self.env['product.category'].get_child_ids('Service')
        domain['product_id_jasa'] = [('type','!=','view'),('categ_id','in',categ_product_ids),('use_frt','=',True)]
        return {'domain':domain}

    @api.multi
    def reset_price(self):
        self.env['dym.frt.history'].create({
            'frt_id': self.id,
            'time': self.time,
            'branch_id': False,
            'rate': 0,
            'date': datetime.today(),
            'price': 0,
        })

class dym_branch(models.Model):
    _inherit = 'dym.branch'

    rate = fields.Float(string='Jasa',required=True)
    
    @api.constrains('rate')
    def _constrain_rate(self):
        self.env['dym.frt.history'].create({
            'frt_id': False,
            'time': 0,
            'branch_id': self.id,
            'rate': self.rate,
            'date': datetime.today(),
            'price': 0,
        })

class dym_product_template(models.Model):
    _inherit = 'product.template'

    use_frt = fields.Boolean(string='Use FRT Price', help="Specify if the product use FRT price.")

