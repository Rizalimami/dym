import time
import logging

from openerp import SUPERUSER_ID, models, fields, api, _

_logger = logging.getLogger(__name__)

class dym_account_move(models.Model):
    _inherit = 'account.move'

    @api.multi
    def write(self, values):
        res =  super(dym_account_move,self).write(values)
        if values:
            if 'name' in values:
                name = values['name']
                inv_ids = self.env['account.invoice'].search([('move_id','=',self.id)])
                for inv in inv_ids:
                    if inv.number != name:
                        print 'Menulis Nomor-----------------'
                        inv.write({'number':name})
        return res

    
class dym_account_invoice(models.Model):
    _inherit = 'account.invoice'

    number = fields.Char('Number', copy=False, default='/')
