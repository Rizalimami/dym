from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import datetime
from openerp import workflow
from openerp.tools.translate import _
from openerp import SUPERUSER_ID

class dym_approval_config(models.Model):
    _name ="dym.approval.config"

    name = fields.Char(string="Name")
    form_id = fields.Many2one('ir.model',string="Form")
    code = fields.Selection([
        (' ',' '),
        ('fix','PO - Fix'),
        ('additional','PO - Additional'),
        ('administratif','PO - Administratif'),
        ('waiting_list','PO - Waiting List'),
        ('hotline','PO - Hotline'),
        ('local_purchase','PO - Local Purchase'),
        ('regular','PO - Regular'),
        ('toko_lain-lain','PO - Toko Lain-lain'),
        ('jp3','PO - JP3'),
        ('payment','Supplier Payment'),
        ('receipt','Customer Payment'),
        ('purchase','Payment Request'),
        ('sale','Other Receivable'),
        ('cancel','Cancel Journal Memorial'),
        ('offtr','Penjualan Off The Road'),
        ('pic','Penjualan PIC'),
        ('cod','Penjualan COD')], string="Code", default=' ')
    type = fields.Selection([('biaya','Biaya'),('discount','Discount')])
    
    _sql_constraints = [
        ('unique_name_form_id', 'unique(form_id,code,type)', 'Master sudah ada !'),
    ]   
    
    @api.onchange('type')
    def change_form_id(self):
        domain ={}
        if self.type == 'discount' :
            domain['form_id'] = [('model','=','dealer.sale.order')]
            form = self.env['ir.model'].search([('model','=','dealer.sale.order')])
            self.form_id = form.id
        elif self.type == 'biaya' :
            domain['form_id'] = [('model','!=','dealer.sale.order')]
            self.form_id = False
        elif not self.type :
            self.form_id = False
        return {'domain':domain}