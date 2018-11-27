from openerp import models, fields, api, _
from openerp.osv import orm

        
class AccountFilter(orm.Model):
    _inherit = "dym.account.filter"

    def _register_hook(self, cr):
        selection = self._columns['name'].selection
        if ('other_receivable_header','Other Receivable Header') not in selection: 
            self._columns['name'].selection.append(
                ('other_receivable_header', 'Other Receivable Header'))
        if ('payments_request','Payments Request') not in selection:         
            self._columns['name'].selection.append(
                ('payments_request', 'Payments Request'))       
        if ('other_payable','Other Payable') not in selection: 
            self._columns['name'].selection.append(
                ('other_payable', 'Other Payable'))                 
        return super(AccountFilter, self)._register_hook(cr)  
     
    
    
