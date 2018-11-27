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

import time
from openerp import models, fields, api
from openerp.osv import osv
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime

class dym_checkgyro_generate_line(models.TransientModel):
    _name = 'dym.checkgyro.generate.line'

    number_start = fields.Integer("Start")
    number_end = fields.Integer('End')
    checkgyro_id = fields.Many2one('dym.checkgyro', 'Check/Giro')
    journal_id = fields.Many2one('account.journal', string="Bank Account", related="checkgyro_id.journal_id", readonly=True)
    pages = fields.Integer('Pages', readonly=True)
    prefix = fields.Char('Prefix', default='CC')
    padding = fields.Integer('Padding', default=6)

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(dym_checkgyro_generate_line, self).default_get(cr, uid, fields, context=context)
        checkgyro_id = context.get('active_ids', [])
        active_model = context.get('active_model')
        if not checkgyro_id or len(checkgyro_id) != 1:
            return res
        checkgyro_id = self.pool.get('dym.checkgyro').browse(cr, uid, checkgyro_id, context=context)
        res.update({'checkgyro_id':checkgyro_id[0].id,'pages':int(checkgyro_id[0].pages)})
        return res

    @api.onchange('prefix','number_start','number_end')
    def change_numbers(self):
        if self.number_start and self.pages:
            self.number_end = self.number_start + self.pages - 1
        if self.number_end and self.number_start:
            if self.number_end < self.number_start:
                values = {'number_end':self.number_start+25}
                warning = {'title':'Attention !','message':_('Start number must be smaller than end number.')}
                return {'warning':warning,'value':values}
            if self.number_end - self.number_start > 50:
                raise UserError(_('Warning!'), _('You can not generate more than 50 numbers.'))
            if (self.number_end - self.number_start + 1) not in [25,50]:
                raise UserError(_('Warning!'), _('Checkbook or Giro can only contain 25 pages or 50 pages.'))
    
    @api.multi
    def generate_numbers(self):
        lines = []
        start = self.number_start
        end = start + self.pages
        for x in self.checkgyro_id.line_ids:
            x.unlink()
        for n in range(start,end):
            negative_padding = self.padding * -1
            number = (str('0'*self.padding)+str(n))[negative_padding:]
            name = '%s-%s' % (self.prefix,number)
            if self.env['dym.checkgyro.line'].search([
                ('journal_id','=',self.journal_id.id),
                ('name','=',name),
                ]):
                raise UserError(_('Cheque / Giro for bank account %s number %s is already exist.' % (self.journal_id.name,name)))
            values = {'name':name}
            lines.append((0,0,values))
        vals = {
            'number_start': self.number_start,
            'number_end': self.number_end,
            'prefix': self.prefix,
            'line_ids':lines
        }
        self.checkgyro_id.write(vals)

