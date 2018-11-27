from openerp import models, fields, api, _

class dym_branch_config(models.Model):
    _inherit = 'dym.branch.config'

    # Default Journal
    dym_po_journal_unit_id = fields.Many2one('account.journal', string='Jurnal Purchase Unit',help='Journal pembentukan invoice pembelian unit')
    dym_po_journal_sparepart_id = fields.Many2one('account.journal', string='Jurnal Purchase Sparepart',help='Journal pembentukan invoice pembelian sparepart')
    dym_po_journal_umum_id = fields.Many2one('account.journal', string='Jurnal Purchase Umum',help='Journal pembentukan invoice pembelian umum')
    dym_po_journal_blind_bonus_beli_id = fields.Many2one('account.journal', string='Journal Blind Bonus Beli',help='Journal blind bonus beli unit')
    dym_po_journal_asset_id = fields.Many2one('account.journal', string='Jurnal Purchase Asset',help='Journal pembentukan invoice pada pembelian asset')
    dym_po_journal_prepaid_id = fields.Many2one('account.journal', string='Jurnal Purchase Prepaid',help='Journal pembentukan invoice pada pembelian prepaid')
    dym_po_journal_intercompany_id = fields.Many2one('account.journal', string='Jurnal Purchase InterCompany',help='Journal pembentukan invoice pembelian intercompany')
    dym_po_type_journal_ids = fields.One2many('dym.branch.config.po_type','config_id',string='Journal PO Type')

    # Default Account
    dym_po_account_discount_cash_id = fields.Many2one('account.account',string='Account Discount Cash Supplier')
    dym_po_account_discount_program_id = fields.Many2one('account.account',string='Account Discount Program Supplier')
    dym_po_account_discount_lainnya_id = fields.Many2one('account.account',string='Account Discount lainnya Supplier')
    dym_po_account_blind_bonus_beli_dr_id = fields.Many2one('account.account', string='Account Blind Bonus Beli (Dr)',help='Account blind bonus beli unit (Dr)')
    dym_po_account_blind_bonus_beli_cr_id = fields.Many2one('account.account', string='Account Blind Bonus Beli (Cr)',help='Account blind bonus beli unit (Cr)')

    # dym_po_account_analytic_cost_center = fields.Many2one('account.analytic.account', string='Account Analytic Cost Center',help='Account Analytic Cost Center')
    # dym_po_account_analytic_bu_unit = fields.Many2one('account.analytic.account', string='Account Analytic BU (Unit)',help='Account Analytic BU (Unit)')
    # dym_po_account_analytic_bu_sparepart = fields.Many2one('account.analytic.account', string='Account Analytic BU (Sparepart)',help='Account Analytic BU (Sparepart)')
    # dym_po_account_analytic_bu_aksesoris = fields.Many2one('account.analytic.account', string='Account Analytic BU (Aksesoris)',help='Account Analytic BU (Aksesoris)')
    # dym_po_account_analytic_bu_umum = fields.Many2one('account.analytic.account', string='Account Analytic BU (Umum)',help='Account Analytic BU (Umum)')

    @api.multi
    def get_all_po_types(self):
        ConfigPOType = self.env['dym.branch.config.po_type']
        po_types = self.env['dym.purchase.order.type'].search([], order='category,name')
        for rec in self:
            po_type_ids = []
            for pt in po_types:
                config_po_type = ConfigPOType.search([('config_id','=',rec.id),('po_type_id','=',pt.id)])
                if not config_po_type:
                    ConfigPOType.create({
                        'config_id': rec.id,
                        'category': pt.category,
                        'po_type_id': pt.id,
                        'account_id': False
                    })
                else:
                    config_po_type.write({
                        'category': pt.category,
                    })

class dym_branch_config_po_type(models.Model):
    _name = 'dym.branch.config.po_type'
    _order = 'category,po_type_id'

    config_id = fields.Many2one('dym.branch.config', string='Config ID')
    category = fields.Selection([
            ('Unit','Showroom'),
            ('Sparepart','Workshop'),
            ('Umum','General'),
        ], string='Type')
    po_type_id = fields.Many2one('dym.purchase.order.type', string='PO Type')
    journal_id = fields.Many2one('account.journal', string='Default Journal', domain="[('type','=','purchase')]")

    _sql_constraints = [
        ('config_categ_potype_uniq', 'unique(po_type_id, category, config_id)',
            'Configuration PO Type must be unique per branch!'),
    ]
