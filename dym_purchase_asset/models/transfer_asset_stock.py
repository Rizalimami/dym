import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv

class dym_branch_config(models.Model):
    _inherit = 'dym.branch.config'

    account_register_asset_persediaan = fields.Many2one('account.account',string='Account Register Asset Persediaan',domain="[('type','!=','view')]",help='Account Register Asset Persediaan')
    account_register_asset_ppn_keluaran = fields.Many2one('account.account',string='Account Register Asset PPN Keluaran',domain="[('type','!=','view')]",help='Account Register Asset PPN Keluaran')
    account_register_discount_subsidi_external = fields.Many2one('account.account',string='Account Register Discount Subsidi External',domain="[('type','!=','view')]",help='Account Register Discount Subsidi External')

class dym_transfer_asset(models.Model):
	_inherit = 'dym.transfer.asset'

	@api.multi
	def cetak_register_asset_stock(self):
		return self.env['report'].get_action(self, 'dym_purchase_asset.document_register_asset_stock')

class dym_transfer_asset_line(models.Model):
	_inherit = 'dym.transfer.asset.line'

	@api.depends('price_unit','discount')
	def compute_dpp(self):
		for line in self:
			line.dpp = line.price_unit - line.discount

	discount = fields.Float('Discount')
	dpp = fields.Float('DPP',compute=compute_dpp,readonly=1,store=1)

	@api.onchange('asset_owner')
	def onchange_asset_owner(self):
		if self.transfer_id.register_type == 'stock' and self.asset_owner:
			analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.env['account.analytic.account'].get_analytical(self.asset_owner, 'Umum', False, 3, 'General')
			self.analytic_1 = analytic_1_general
			self.analytic_2 = analytic_2_general
			self.analytic_3 = analytic_3_general
			self.analytic_4 = analytic_4_general