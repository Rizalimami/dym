from openerp import api, models, fields
from openerp.tools.translate import _
from openerp.exceptions import Warning as UserError, RedirectWarning, ValidationError

class BankTrfRequestGroup(models.TransientModel):
    _inherit = "bank.trf.request.group"
    _description = "Bank Transfer Request Grup"

    branch_via_id = fields.Many2one('dym.branch', string='AHASS Parent')

    @api.onchange('branch_destination_id','bank_dest_type')
    def onchange_branch_destination_id(self):
        dom = {}
        val = {}
        if self.branch_destination_id:
            branch = self.env['dym.branch'].search([('code','=',self.branch_destination_id)])
            if branch.ahass_parent_id:
                self.branch_via_id = branch.ahass_parent_id.id
                bank_dest_ids = self.env['account.journal'].search([('type','=','bank'),('transaction_type','=',self.bank_dest_type),('branch_id','=',branch.ahass_parent_id.id)])
            else:
                bank_dest_ids = self.env['account.journal'].search([('type','=','bank'),('transaction_type','=',self.bank_dest_type),('branch_id','=',branch.id)])
            dom['payment_to_id'] = [('id','in',bank_dest_ids.ids)]
            if bank_dest_ids:
                val['payment_to_id'] = bank_dest_ids.ids[0]
        return {'value':val,'domain':dom}

    @api.multi
    def merge_trf_requests(self):
        name = self.env['ir.sequence'].next_by_code('bank.trf.advice')
        branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
        supplier_payment_limit = branch_config.supplier_payment_limit

        values = {
            'name': name,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id,
            'payment_from_id': self.payment_from_id.id,
            'payment_to_id': self.payment_to_id.id,
            'branch_destination_id': self.branch_destination_id,
            'branch_via_id': self.branch_via_id.id,
            'bank_trf_request_ids': [(6,0,self.bank_trf_request_ids.ids)],
            'amount': self.amount,
            'state': 'draft',
            'transfer_date': self.transfer_date,
        }
        if self.merge_mode=='new':
            advice_id = self.env['bank.trf.advice'].create(values)
        if self.merge_mode=='existing':
            advice_id = self.advice_id
            for trf_req in self.bank_trf_request_ids:
                trf_req.write({'advice_id':advice_id.id})

        view_id = self.env.ref('dym_bank_trf_request.bank_trf_advice_form_view').id
        return {
            'name' : _('Bank Transfer Advice'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': advice_id.id,
            'res_model': 'bank.trf.advice',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': False,
            'context': self.env.context
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
