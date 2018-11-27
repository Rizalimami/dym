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

import openerp.addons.decimal_precision as dp
from openerp import models, fields, api, exceptions, _
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
import openerp
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

class iBankingDone(models.TransientModel):
    _name = 'dym.ibanking.done'

    ibanking_id = fields.Many2one('dym.ibanking', string='iBanking')
    line_ids = fields.One2many('dym.ibanking.done.line', 'ibanking_done_id', string='Lines')
    date = fields.Date(string='Date', required=True)

    @api.model
    def default_get(self, fields):
        res = super(iBankingDone, self).default_get(fields)
        active_model = self.env.context.get('active_model',False)
        active_ids = self.env.context.get('active_ids',[])
        if not active_model or not active_ids:
            return res
        res['ibanking_id'] = active_ids[0]
        lines = []
        ibanking = self.env['dym.ibanking'].browse(active_ids)
        for line in ibanking.transfer_ids:
            values = {
                'name': line.name,
                'obj': 'dym.bank.transfer',
                'res_id': line.id,
                'amount': line.amount,
            }
            lines.append((0,0,values))

        for line in ibanking.voucher_ids:
            values = {
                'name': line.number,
                'obj': 'account.voucher',
                'res_id': line.id,
                'amount': line.amount,
            }
            lines.append((0,0,values))
        res['line_ids'] = lines
        today = date.today().strftime(DATE_FORMAT)
        res['date'] = (datetime.strptime(today,DATE_FORMAT) + relativedelta(days=-1)).strftime(DATE_FORMAT)
        return res

    @api.multi
    def action_done(self):
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        for line in self.line_ids:
            obj_browse = self.env[line.obj].browse([line.res_id])
            if line.success:
                if line.obj == 'account.voucher':
                    obj_browse.write({'reference':self.ibanking_id.file_name})
                    obj_browse.signal_workflow('confirm_payment')
                    move_id = move_obj.search([('model','=',obj_browse._name),('transaction_id','=',obj_browse.id)])
                    move_lines = move_id.mapped('line_id').filtered(lambda r: r.clear_state=='open')
                    if move_lines:
                        period_ids = self.env['account.period'].find(dt=self.date)
                        move_journal = {
                            'name': self.ibanking_id.name,
                            'ref': obj_browse.number,
                            'journal_id': obj_browse.journal_id.id,
                            'date': self.date,
                            'period_id':period_ids.id,
                            'transaction_id':obj_browse.id,
                            'model':obj_browse.__class__.__name__,
                        }
                        vals1 = {
                            'name': _('Clearing Bank ' + self.ibanking_id.name),
                            'ref': obj_browse.number,
                            'partner_id': obj_browse.partner_id.id,
                            'account_id': obj_browse.journal_id.clearing_account_id.id,
                            'period_id':period_ids.id,
                            'date': self.date,
                            'debit': obj_browse.net_amount,
                            'credit': 0.0,
                            'branch_id': obj_browse.branch_id.id,
                            'division': obj_browse.division,
                            'analytic_account_id' : obj_browse.analytic_4.id 
                        }
                        move_line = [[0,False,vals1]]
                        move_journal['line_id'] = move_line
                        create_journal = move_obj.create(move_journal)
                        for line in move_lines:
                            vals2 = {
                                'name': _('Bank ' + (line.ref or line.name)),
                                'ref': obj_browse.name,
                                'partner_id': line.partner_id.id,
                                'account_id': obj_browse.journal_id.default_credit_account_id.id,
                                'period_id':period_ids.id,
                                'date': self.date,
                                'debit': 0.0,
                                'credit': line.credit,
                                'branch_id': line.branch_id.id,
                                'division': line.division,
                                'analytic_account_id' : line.analytic_account_id.id,
                                'move_id': create_journal.id,
                            }
                            created_move_line = move_line_obj.create(vals2)
                        move_lines.write({'clear_state':'cleared'})
                elif line.obj == 'dym.bank.transfer':
                    obj_browse.signal_workflow('approval_approve')
            else:
                obj_browse.write({'ibanking_id':False, 'total_record':self.ibanking_id.total_record-1})
        self.ibanking_id.state = 'done'

class iBankingDoneLine(models.TransientModel):
    _name = 'dym.ibanking.done.line'

    ibanking_done_id = fields.Many2one('dym.ibanking.done', string='iBanking Done')
    name = fields.Char()
    obj = fields.Char()
    res_id = fields.Integer('ID')
    success = fields.Boolean(string='Success')
    amount = fields.Float(string="Total Amount", digits_compute=dp.get_precision('Account'))
    reason = fields.Selection([
        ('00','Success'),
        ('10','Wrong Destination Account'),
        ('11','Insufficient Balance'),
        ('99','Other'),
    ], default='00')

