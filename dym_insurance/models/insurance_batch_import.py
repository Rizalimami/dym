# -*- coding: utf-8 -*-
import time
from datetime import datetime, date, timedelta
from dateutil import relativedelta

from openerp import api, fields, models, tools, _, exceptions
from openerp.addons.dym_base import DIVISION_SELECTION
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp.exceptions import Warning as UserError, RedirectWarning


BB_STATE_SELECTIONS = [
    ('draft','Draft'),
    ('waiting_for_approval','Waiting For Approval'),
    ('approved','Approved'),
    ('done','Posted'),
    ('cancel','Cancelled'),
    ('reject','Rejected'),
]

DIVISION_SELECTIONS = [
    ('Unit','Showroom'),
    # ('Sparepart','Workshop'),
    ('Umum','General'),
    # ('Finance','Finance'),
    # ('Service','Service'),
]

INSURANCE_TYPES = [
    ('Biaya dibayar dimuka - Asuransi Barang Dalam Perjalanan','Biaya dibayar dimuka - Asuransi Barang Dalam Perjalanan'),
    ('Biaya dibayar dimuka - Asuransi Kas','Biaya dibayar dimuka - Asuransi Kas'),
    ('Biaya dibayar dimuka - Asuransi Kebakaran Bangunan','Biaya dibayar dimuka - Asuransi Kebakaran Bangunan'),
    ('Biaya dibayar dimuka - Asuransi Kebakaran Peralatan Kantor & Bengkel','Biaya dibayar dimuka - Asuransi Kebakaran Peralatan Kantor & Bengkel'),
    ('Biaya dibayar dimuka - Asuransi Kendaraan','Biaya dibayar dimuka - Asuransi Kendaraan'),
    ('Biaya dibayar dimuka - Asuransi Kesehatan','Biaya dibayar dimuka - Asuransi Kesehatan'),
    ('Biaya dibayar dimuka - Asuransi Persediaan','Biaya dibayar dimuka - Asuransi Persediaan'),
]

class InsuranceBatchImport(models.Model):
    _name = 'dym.insurance.batch.import'
    _description = 'DYM Insurance Batch Import'

    @api.one
    @api.depends('line_ids.price_unit')
    def _compute_total_amount(self):
        self.total_amount = sum(inc.price_unit for inc in self.line_ids)

    name = fields.Char(required=True, readonly=True, states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=True)
    
    # journal_id = fields.Many2one('account.journal', 'Journal', required=True)
    # account_id = fields.Many2one('account.account', related='journal_id.default_debit_account_id')

    partner_id = fields.Many2one('res.partner', string='Insurance Company', domain=[('insurance_company','=',True)], required=True)    
    type = fields.Selection(INSURANCE_TYPES, 'Insurance Type', required=True)

    line_ids = fields.One2many('dym.insurance.batch.import.line', 'batch_id', string='Line', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(BB_STATE_SELECTIONS, string='Status', index=True, readonly=True, copy=False, default='draft')
    value_date = fields.Date(string='Transaction Date', required=True, readonly=True, states={'draft': [('readonly', False)]})    
    date = fields.Date(string='Date', required=True, readonly=True, states={'draft': [('readonly', False)]})

    date_start = fields.Date(string='Date Start', required=True, readonly=True, states={'draft': [('readonly', False)]})
    date_end = fields.Date(string='Date End', required=True, readonly=True, states={'draft': [('readonly', False)]})
    duration = fields.Char(string='Duration')

    total_amount = fields.Float(string='Total Amount', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_amount')
    memo = fields.Char('Memo')

    po_ids = fields.Many2many('purchase.order','insurance_batch_po_rel','batch_id','po_id','Purchase Orders')


    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'INS', division='Umum')
        return super(InsuranceBatchImport, self).create(vals)


    @api.model
    def default_get(self, fields_list):
        res = super(InsuranceBatchImport, self).default_get(fields_list)
        context = dict(self.env.context or {})
        company_id = self.env.user.company_id
        branch_id = self.env['dym.branch'].search([('company_id','=',company_id.id),('branch_type','=','HO')], limit=1)
        if branch_id:
            res['branch_id'] = branch_id.id
        res['division'] = 'Umum'
        res['value_date'] = date.today().strftime(DATE_FORMAT)
        res['date'] = date.today().strftime(DATE_FORMAT)
        res['name'] = '/' 
        return res

    @api.one
    @api.onchange('type')
    def onchange_type(self):
        if self.type:
            self.memo = 'Biaya asuransi %s' % self.type

    @api.one
    @api.onchange('branch_id')
    def onchange_branch_id(self):
        if self.branch_id:
            config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
            if config.dym_bb_journal:
                self.journal_id = config.dym_bb_journal.id

    @api.multi
    def view_purchase_order(self):
        po_ids = self.po_ids.ids
        mod_obj = self.env['ir.model.data']
        result = mod_obj._get_id('purchase', 'view_purchase_order_filter')
        id = mod_obj.browse(result).read(['res_id'])[0]
        return {
            'domain': "[('id','in', [" + ','.join(map(str, po_ids)) + "])]",
            'name': _('Purchase Order'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': id['res_id']
        }


class InsuranceBatchImportLine(models.Model):
    _name = 'dym.insurance.batch.import.line'
    _description = 'DYM Insurance Batch Import Line'

    name = fields.Char(required=True, readonly=True)
    batch_id = fields.Many2one('dym.insurance.batch.import', 'Batch', required=True)
    inter_branch_id = fields.Many2one('dym.branch', 'Branch', required=True)
    inter_division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', required=True)
    type = fields.Selection(INSURANCE_TYPES, 'Insurance Type', required=True)
    price_unit = fields.Float(string='Price Unit', digits=dp.get_precision('Account'), readonly=True)

    categ_id = fields.Many2one('product.category',string='Category of Product', readonly=True)
    template_id = fields.Many2one("product.template", string="Type", required=True)
    product_id = fields.Many2one('product.product', string='Variant')
    product_uom = fields.Many2one('product.uom', 'Product Unit of Measure', readonly=True)


