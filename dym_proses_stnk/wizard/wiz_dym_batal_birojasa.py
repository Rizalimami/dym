from openerp import models, fields, api
from datetime import datetime

class dym_batal_birojasa(models.TransientModel):
    _name = "wiz.dym.batal.birojasa"
    _description = "Wizard Batal Birojasa"

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval', 'Waiting For Approval'),
        ('confirmed', 'Waiting Approval'),
        ('approved', 'Confirmed'),
        ('except_invoice', 'Invoice Exception'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ]

    APPROVAL_STATE = [
        ('b', 'Belum Request'),
        ('rf', 'Request For Approval'),
        ('a', 'Approved'),
        ('r', 'Reject')
    ]

    birojasa_id = fields.Many2one('dym.proses.birojasa', "Nomor Biro Jasa", required=True, readonly=True)
    branch_id = fields.Many2one('dym.branch', string='Branch', required=True, readonly=True)
    division = fields.Selection([('Unit', 'Showroom'), ('Sparepart', 'Workshop')], 'Division', change_default=True,
                                select=True, readonly=True)
    partner_id = fields.Many2one('res.partner', 'Biro Jasa', readonly=True)
    reason = fields.Text('Alasan Cancel', required=True)

    @api.model
    def default_get(self, fields):
        res = super(dym_batal_birojasa, self).default_get(fields)
        birojasa_id = self._context['birojasa_id']
        if birojasa_id:
            res['birojasa_id'] = birojasa_id
            res['branch_id'] = self._context['branch_id']
            res['division'] = self._context['division']
            res['partner_id'] = self._context['partner_id']
            res['state'] = 'waiting_for_approval'
            res['approval_state'] = 'rf'
        return res

    @api.multi
    def wkf_request_cancel(self):
        obj_tbj = self.env['dym.proses.birojasa']
        obj_batal_tbj = self.env['dym.batal.birojasa']
        obj_matrix_approval = self.env['dym.approval.matrixbiaya']
        tbj = obj_tbj.search([('id', '=', self.birojasa_id.id)])
        values = {}
        values['birojasa_id'] = self.birojasa_id.id
        values['request_date'] = datetime.today()
        values['branch_id'] = self.branch_id.id
        values['division'] = self.division
        values['partner_id'] = self.partner_id.id
        values['reason'] = self.reason
        values['state'] = 'draft'

        tbj.write({'state':'waiting_approval_cancel'})
        obj_batal_tbj.create(values)