# -*- coding: utf-8 -*-
import time
from datetime import datetime, date, timedelta
from dateutil import relativedelta

from openerp import api, fields, models, tools, _
from openerp.addons.dym_base import DIVISION_SELECTION
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp.exceptions import Warning as UserError, RedirectWarning


MBD_STATE_SELECTIONS = [
    ('draft', 'Draft'),
    ('close', 'Closed'),
]

DIVISION_SELECTIONS = [
    ('Unit','Showroom'),
    ('Sparepart','Workshop'),
    ('Umum','General'),
    ('Finance','Finance'),
    ('Service','Service'),
]

class MBDBatchImport(models.Model):
    _name = 'dym.mbd.batch.import'
    _description = 'DYM MBD Batch Import'

    name = fields.Char(required=True, readonly=True, states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    mbd_ids = fields.One2many('dym.mbd.allocation', 'batch_id', string='MBD Allocations', readonly=True,
        states={'draft': [('readonly', False)]})
    state = fields.Selection(MBD_STATE_SELECTIONS, string='Status', index=True, readonly=True, copy=False, default='draft')
    date_start = fields.Date(string='Date From', required=True, readonly=True,
        states={'draft': [('readonly', False)]})
    date_end = fields.Date(string='Date To', required=True, readonly=True,
        states={'draft': [('readonly', False)]})

    # def create(self, cr, uid, vals, context=None):
    #     name_exist = self.search(cr, uid, [('name','=',vals['name'])])
    #     if name_exist:
    #         raise UserError(_('Batch import dengan nama "%s" sudah ada !' % (vals['name'])))

    #     date_range_exist = self.search(cr, uid, [('date_start','>=',vals['date_start']),('date_end','<=',vals['date_end'])])
    #     if date_range_exist:
    #         raise UserError(_('Batch import dengan date start "%s" dan date end "%s" sudah ada !' % (vals['date_start'],vals['date_end'])))
    #     # vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'MBD', division='Umum')
    #     return super(MBDBatchImport, self).create(cr, uid, vals, context=context)


    @api.model
    def default_get(self, fields_list):
        res = super(MBDBatchImport, self).default_get(fields_list)
        context = dict(self.env.context or {})

        date_end = date.today().replace(day=1) - timedelta(days=1)
        date_start = date_end.replace(day=1)
        date_end = date_end
        period_name = '%s - %s' % (date_start.strftime('%d'),date_end.strftime('%d %b %Y'))
        res['date_end'] = date_end.strftime(DATE_FORMAT)
        res['date_start'] = date_start.strftime(DATE_FORMAT)
        res['name'] = 'Batch Import MBD period: %s' % (period_name)

        return res

    @api.multi
    def validate_mbd_batch_import(self):
        print "-- validate_mbd_batch_import --"

