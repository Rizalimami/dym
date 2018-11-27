from openerp import models, fields, api

class dym_welcome_page(models.Model):
    _name = 'dym.welcome.page'
    
    description = fields.Text()