from openerp import models, fields, api
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp import netsvc
from openerp.osv import osv

class InsuranceBatchImport(models.Model):
    _inherit = 'dym.insurance.batch.import'
    
    approval_ids = fields.One2many('dym.approval.line', 'transaction_id', string="Table Approval", domain=[('form_id','=',_inherit)])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Reject')
    ], 'Approval State', readonly=True, default='b')
    approve_uid = fields.Many2one('res.users',string="Approved by")
    approve_date = fields.Datetime('Approved on')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')    
        
    @api.multi
    def wkf_request_approval(self):
        # Config = self.env['dym.branch.config']
        # config_id = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)], limit =1)

        # if not config_id.dym_bb_journal:
        #     raise exceptions.ValidationError(("Cabang %s tidak memiliki journal piutang blind bonus. Silahkan setting di Branch Config" % (self.branch_id.name)))

        # if not config_id.dym_bb_income_account_unit:
        #     raise exceptions.ValidationError(("Cabang %s tidak memiliki akun pendapatan blind bonus unit. Silahkan setting di Branch Config" % (self.branch_id.name)))

        # if not config_id.dym_bb_income_account_oli:
        #     raise exceptions.ValidationError(("Cabang %s tidak memiliki akun pendapatan blind bonus oli. Silahkan setting di Branch Config" % (self.branch_id.name)))

        # if not config_id.dym_bb_income_account_part:
        #     raise exceptions.ValidationError(("Cabang %s tidak memiliki akun pendapatan blind bonus part. Silahkan setting di Branch Config" % (self.branch_id.name)))

        # if not self.line_ids:
        #     raise osv.except_osv(('Perhatian !'), ("Mohon lengkapi data untuk melanjutkan !")) 

        obj_matrix = self.env['dym.approval.matrixbiaya']
        obj_matrix.request_by_value(self,self.total_amount)
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
        return True

    @api.multi
    def wkf_approval(self):
        titipan_line_list = []
        titipan_line_dict = {}
        approval_sts = self.env['dym.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'approval_state':'a', 'state':'approved','approve_uid':self._uid,'approve_date':datetime.now()})
        elif approval_sts == 0 :
            raise exceptions.ValidationError( ("User tidak termasuk group approval"))
        self.action_create_other_receivable_voucher()
        return True

    @api.model
    def action_create_other_receivable_voucher(self):
        return self._action_create_other_receivable_voucher()

    @api.model
    def _get_picking_type_ids(self, branch_id=None):        
        picking_type_id = self.env['stock.picking.type'].search([('branch_id','=',branch_id.id),('code','=','incoming')])
        if not picking_type_id:
            raise UserError(('Error'), ("Tidak ditemukan picking type untuk branch %s")%(branch_id.name))
        return picking_type_id

    @api.model
    def _prepare_purchase_order_data(self, branch_id=None, division=None):
        branch_config = self.env['dym.branch.config'].search([('branch_id','=',branch_id.id)])
        if not branch_config:
            raise UserError(
                _('Perhatian'),
                _('Konfigurasi Cabang ini tidak ditemukan di Branch Config, silahkan setting dulu.'))

        if not branch_config.dym_po_journal_prepaid_id:
            raise UserError(
                _('Perhatian'),
                _('Cabang "%s" tidak memiliki jurnal asset prepaid, silahkan setting dulu.' % branch_id.name))

        analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(branch_id, division, False, 4, 'General')
        return {
            'asset': False,
            'branch_id': branch_id.id,
            'division': division,
            'journal_id': branch_config.dym_po_journal_prepaid_id.id,
            'analytic_1': analytic_1,
            'analytic_2': analytic_2,
            'analytic_3': analytic_3,
            'analytic_4': analytic_4,
            'order_line': []
        }

    @api.multi
    def _action_create_other_receivable_voucher(self):
        Config = self.env['dym.branch.config']
        Fiscal = self.env['account.fiscal.position']
        PO_Type = self.env['dym.purchase.order.type']

        purchase_order_type_id = PO_Type.search([('name','=','Regular')])
        if not purchase_order_type_id:
            raise UserError(_('PO Type "Regular" Tidak ditemukan di system. Mohon lengkapi dulu !'))

        partner_type = self.env['dym.partner.type'].search([('name','=','supplier')])
        if not partner_type:
            raise UserError(_('Tipe partner "General Supplier" tidak ditemukan di system. Mohon lengkapi dulu untuk melanjutkan !'))
        if not self.partner_id.property_supplier_payment_term:
            raise UserError(_('Partner "%s" tidak memiliki "Supplier Payment Term". Mohon lengkapi dulu di form partner !'))

        purchase_orders = {}
        branches = []
        for line in self.line_ids:
            if not line.inter_branch_id.id in branches:
                branches.append(line.inter_branch_id.id)
                purchase_orders[line.inter_branch_id.id] = self._prepare_purchase_order_data(branch_id=line.inter_branch_id,division=line.inter_division)
                picking_type_id = self._get_picking_type_ids(branch_id=line.inter_branch_id)
                purchase_orders[line.inter_branch_id.id].update({
                    'partner_type': partner_type.id,
                    'partner_id': self.partner_id.id,
                    'payment_term_id': self.partner_id.property_supplier_payment_term.id,
                    'picking_type_id': picking_type_id.id,
                    'location_id': picking_type_id.default_location_dest_id.id,
                    'set2draft': True,
                    'prepaid': True,
                    'purchase_order_type_id': purchase_order_type_id.id,
                })

            values = {
                'categ_id': line.categ_id.id,
                'template_id': line.template_id.id,
                'product_id': line.product_id.id,
                'name': line.name,
                'product_qty': 1,
                'product_uom': line.product_uom.id,
                'price_unit': line.price_unit,
                'price_unit_show': line.price_unit,
            }
            purchase_orders[line.inter_branch_id.id]['order_line'].append((0,0,values))

        po_ids = []
        for branch in branches:
            po_id = self.env['purchase.order'].create(purchase_orders[branch])
            po_id.signal_workflow('approval_request')
            po_id.signal_workflow('approval_approve')
            po_ids.append(po_id.id)

        self.write({'po_ids':[(6, 0, po_ids)]})

        return True


