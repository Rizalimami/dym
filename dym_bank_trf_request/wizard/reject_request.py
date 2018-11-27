# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api, models, fields
from openerp.tools.translate import _
from openerp.exceptions import Warning as UserError, RedirectWarning

class TrfRequestRejectReason(models.TransientModel):
    _name = 'trf.request.reject.reason'

    request_id = fields.Many2one('bank.trf.request', string='Request ID')
    reason = fields.Char('Reason', required=True)
    rejection_rpc_line = fields.One2many('trf.request.reject.reason.rpc.line', 'rejection_id', string='Lines')
    rejection_rpc_line2 = fields.Char(string='Lines2')

    @api.multi
    def action_reject(self):
        for rec in self:
            if not rec.rejection_rpc_line:
                raise UserError(_('Tidak ada PCO yang di-reject.'))
            for line in rec.rejection_rpc_line:
                line.reimbursed_line_id.reimbursed_id.state = "horejected"            
                line.pettycash_id.state = "horejected"
            not_rejected = [l for l in eval(rec.rejection_rpc_line2) if l not in [i.pettycash_id.id for i in rec.rejection_rpc_line]]
            for pco_id in self.env['dym.pettycash'].browse(not_rejected):
                for pco_line in pco_id.line_ids:
                    pco_line.amount_reimbursed = 0.0
                if pco_id.state != 'posted':
                    pco_id.state = 'posted'
            rec.request_id.state = 'rejected'

    @api.model
    def default_get(self, fields):
        res = super(TrfRequestRejectReason, self).default_get(fields)
        active_model = self.env.context.get('active_model',False)
        active_ids = self.env.context.get('active_ids',[])
        if not active_model or not active_ids:
            return res
        for trq in self.env['bank.trf.request'].browse(active_ids):
            rejection_rpc_lines = []
            pcos = []
            if trq.obj == 'dym.reimbursed':
                rejection_rpc_line2_ids = []
                for drmb_line in self.env['dym.reimbursed'].browse(trq.res_id)[0].line_ids:
                    if drmb_line.pettycash_id.id not in pcos:
                        pcos.append(drmb_line.pettycash_id.id)
                    else:
                        continue
                    rejection_rpc_lines.append((0,0,{
                        'reimbursed_line_id':drmb_line.id,
                        'pettycash_id': drmb_line.pettycash_id.id,
                        'date': drmb_line.pettycash_id.date,
                        'name': drmb_line.pettycash_id.name,
                        'amount': drmb_line.pettycash_id.amount,
                    }))
                    rejection_rpc_line2_ids.append(drmb_line.pettycash_id.id)
                res['rejection_rpc_line'] = rejection_rpc_lines
                res['rejection_rpc_line2'] = str(rejection_rpc_line2_ids)
        return res

class TrfRequestRejectReasonRPCLine(models.TransientModel):
    _name = 'trf.request.reject.reason.rpc.line'

    rejection_id = fields.Many2one('trf.request.reject.reason', string='Rejection ID')
    reimbursed_line_id = fields.Many2one('dym.reimbursed.line', string='Line')
    pettycash_id = fields.Many2one('dym.pettycash', string='Petty Cash')
    date = fields.Date(string="Date")
    name = fields.Char(string="Description", required=True)
    amount = fields.Float(string="Amount")
