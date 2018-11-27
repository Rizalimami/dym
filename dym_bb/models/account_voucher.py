from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class AccountVoucher(models.Model):
    _inherit = "account.voucher"
    
    bb_batch_id = fields.Many2one('dym.bb.batch.import', 'BB Batch ID')

    @api.model
    def voucher_move_line_create(self, voucher_id, line_total, move_id, company_currency, current_currency, context=None):
        res = super(AccountVoucher, self).voucher_move_line_create(voucher_id, line_total, move_id, company_currency, current_currency)
        obj_move = self.env['account.move']
        obj_voucher = self.env['account.voucher']
        
        move = obj_move.browse(move_id)
        voucher = obj_voucher.browse(voucher_id)

        if voucher.bb_batch_id:    
            for line in move.line_id:
                # line.move_id.button_cancel()   
                if line.branch_id and line.credit and 'PPN' not in line.name and 'PPh' not in line.name:
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(line.branch_id, 'Unit', False, 4, 'Sales')           
                    line.write({'analytic_account_id': analytic_4})
            
                if voucher.branch_id.id == line.branch_id.id:
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(line.branch_id, 'Finance', False, 4, 'General')           
                    line.write({'analytic_account_id': analytic_4})        
        return res
    
