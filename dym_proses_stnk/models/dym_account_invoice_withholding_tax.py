# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning


class account_invoice(models.Model):

    _inherit = "account.invoice"


    withholding_ids = fields.One2many(
        'dym.account.invoice.withholding',
        'invoice_id',
        string='Withholdings',
        required=False,
        readonly=True,
        states={'draft': [('readonly', False)]}
        )
    withholdings_amount = fields.Float(
        'PPh',
        # waiting for a PR 9081 to fix computed fields translations
        # _('Withholdings Amount'),
        help='Importe a ser Pagado con Retenciones',
        # help=_('Amount Paid With Withholdings'),
        compute='_get_withholdings_amount',
        digits=dp.get_precision('Account'),
    )
    total_net = fields.Float(
        'Total Tagihan (Net)',
        # waiting for a PR 9081 to fix computed fields translations
        # _('Withholdings Amount'),
        help='Importe a ser Pagado con Retenciones',
        # help=_('Amount Paid With Withholdings'),
        compute='_get_total_net',
        digits=dp.get_precision('Account'),
    )

    amountview = fields.Float('Total',
        help='Total amount view',
        digits=dp.get_precision('Account'),
    )

    @api.onchange('net_amount')
    def onchange_amount_total_view(self):
        self.amountview = self.net_amount

    @api.one
    @api.depends(
        'withholding_ids',
        )
    def _get_withholdings_amount(self):
        self.withholdings_amount = self.get_withholdings_amount()[self.id]
   
    @api.multi
    def get_withholdings_amount(self):
        res = {}
        for invoice in self:
            withholdings_amount = sum(
                x.amount for x in invoice.withholding_ids)
            res[invoice.id] = withholdings_amount
        return res

    @api.one
    @api.depends(
        'withholdings_amount',
        )
    def _get_total_net(self):
        self.total_net = self.get_total_net()[self.id]
  
    @api.multi
    def get_total_net(self):
        res = {}
        for invoice in self:
            total_net = invoice.amount_total - invoice.withholdings_amount
            res[invoice.id] = total_net
        return res

    @api.multi
    def get_paylines_amount(self):
        res = super(account_invoice, self).get_paylines_amount()
        for invoice in self:
            withholdings_amount = invoice.get_withholdings_amount()[birojasa.id]
            res[invoice.id] = res[invoice.id] + withholdings_amount
        return res

    @api.model
    def paylines_moves_create(
            self, invoice, move_id, company_currency, current_currency):
        paylines_total = super(account_invoice, self).paylines_moves_create(
            invoice, move_id, company_currency, current_currency)
        withholding_total = self.create_withholding_lines(
            invoice, move_id, company_currency, current_currency)
        return paylines_total + withholding_total

    #Untuk meng-copy paste isi record Pemotongan PPh di Birojasa ke Invoice
    def update_pph_invoice_birojasa(self,birojasa_id,invoice_id):
        birojasa_obj=self.env['dym.proses.birojasa']
        inv_obj=self.env['account.invoice']
        inv_wh_tax=self.env['dym.account.invoice.withholding']
        birojasa=birojasa_obj.browse(birojasa_id)

        pph_list=[]
        for pph in birojasa.withholding_ids:
            pph_list.append({
                # 'name':pph.name,
                'tax_withholding_id':pph.tax_withholding_id.id,
                'tax_base':pph.tax_base,
                'amount':pph.amount,
                'move_line_id':pph.move_line_id.id,
                'partner_id':pph.partner_id.id,
                'date':pph.date,
                # 'internal_number':pph.internal_number,
                'company_id':pph.company_id.id,
                'invoice_id':invoice_id.id,
                # 'date':pph.date,
                })

        for wh_tax in pph_list:
            inv_wh_tax.create(wh_tax)

        return True

    #Untuk meng-copy paste isi record Pemotongan PPh di Birojasa ke Invoice
    def update_pph_invoice_dso(self,dso_id,invoice_id):
        dso_obj=self.env['dealer.sale.order']
        inv_obj=self.env['account.invoice']
        inv_wh_tax=self.env['dym.account.invoice.withholding']
        wh_tax_obj=self.env['account.tax.withholding']
        dso=dso_obj.browse(dso_id)

        pph_line={}
        amount_komisi=0
        if dso.partner_komisi_id:
            if dso.partner_komisi_id.npwp:
                wh_tax=wh_tax_obj.search([('company_id','=',invoice_id.branch_id.company_id.id),('tax_code_id.code','=','02102'),('amount','=',0.025)])
            else:
                wh_tax=wh_tax_obj.search([('company_id','=',invoice_id.branch_id.company_id.id),('tax_code_id.code','=','02102'),('amount','=',0.03)])
    
            if wh_tax:            
                for line in dso.dealer_sale_order_line:
                    amount_komisi+=line.amount_hutang_komisi

                    # pph_line['name']=wh_tax.name
                    pph_line['tax_withholding_id']=wh_tax.id
                    pph_line['tax_base']=line.amount_hutang_komisi
                    # 'move_line_id':pph.move_line_id.id,
                    pph_line['partner_id']=dso.partner_komisi_id.id
                    pph_line['date']=invoice_id.date_invoice
                    # 'internal_number':pph.internal_number,
                    pph_line['company_id']=invoice_id.branch_id.company_id.id
                    pph_line['invoice_id']=invoice_id.id
                    # pph_line['date']=pph.date
                pph_line['amount']=amount_komisi*wh_tax.amount
       
                inv_wh_tax.create(pph_line)

        return True

    @api.model
    def create(self,vals):
        # origin=vals.get('origin', False)
        invoice_id = super(account_invoice, self).create(vals)
        birojasa=self.env['dym.proses.birojasa'].search([('name','=',invoice_id.origin)])
        dso=self.env['dealer.sale.order'].search([('name','=',invoice_id.origin)])
        if birojasa:
            self.update_pph_invoice_birojasa(birojasa.id,invoice_id)
        elif dso:
            self.update_pph_invoice_dso(dso.id,invoice_id)
            
        return invoice_id

    @api.multi
    def action_move_create(self):
        res = super(account_invoice, self).action_move_create()
        obj_move=self.env['account.move']
        obj_move_line=self.env['account.move.line']
        obj_branch_conf=self.env['dym.branch.config']
        obj_birojasa=self.env['dym.proses.birojasa']
        obj_po=self.env['purchase.order']
        obj_dso=self.env['dealer.sale.order']
        obj_tax=self.env['account.tax']
        kas_negara_id = self.env['res.partner'].search([('kas_negara','=',True)])
        for line in self.move_id.line_id:
            #line.move_id.journal_id.write({'update_posted':True})
            line.move_id.button_cancel()
            if self.branch_id:
                branch_config=obj_branch_conf.search([('branch_id','=',self.branch_id.id)])
                if branch_config:      
                    if self.withholdings_amount>0:
                       if self.origin:
                            origin=self.origin.split(' ')[0]
                            if obj_birojasa.search([('name','=',origin)]):# Jika dari Tagihan Birojasa
                                journal=branch_config[0].tagihan_birojasa_bbn_journal_id
                            elif obj_po.search([('name','=',origin)]):# Jika dari Tagihan Sewa
                                journal=branch_config[0].dym_po_journal_prepaid_id
                            elif obj_dso.search([('name','=',origin)]):# Jika dari Tagihan Broker / Komisi
                                journal=branch_config[0].dealer_so_journal_hc_id
                            if journal:
                                acc=journal.default_credit_account_id
                                if line.account_id.id == acc.id:
                                    line.write({'credit':line.credit - self.withholdings_amount})
                                    for pph in self.withholding_ids:
                                        dom_inv_line = [('invoice_id','=',self.id),('price_subtotal','=',pph.tax_base)]
                                        invoice_line = self.env['account.invoice.line'].search(dom_inv_line)
                                        invoice_line_name = invoice_line.name if len(invoice_line)==1 else {}
                                        description = pph.comment or invoice_line_name or pph.tax_withholding_id.description
                                        name = '%s: %s' % (description, pph.internal_number)
                                        if pph.name:
                                            name += ' (%s)' % pph.name
                                        obj_move_line.create({
                                                'name': description or '/',
                                                'ref': self.origin or '/',
                                                'account_id': pph.tax_withholding_id.account_id.id,
                                                'journal_id': self.journal_id.id,
                                                'period_id': self.period_id.id,
                                                'date': self.create_date,
                                                'date_maturity':self.date_due,
                                                'debit': 0,
                                                'credit': pph.amount,
                                                'branch_id' : self.branch_id.id,
                                                'division' : self.division,
                                                'partner_id' : kas_negara_id.id,
                                                'move_id': self.move_id.id,
                                                'analytic_account_id' : line.analytic_account_id.id,
                                                'tax_code_id':pph.tax_withholding_id.tax_code_id.id,
                                                'tax_amount':pph.tax_base,
                                                'analytic_4':self.analytic_4.id,
                                                })

                # Tambah PPN jika ada selisih STNK untuk transaksi birojasa
                # if obj_birojasa.search([('name','=',origin)]):
                ppn=obj_tax.search([('type_tax_use2','=','non-trade'),('type_tax_use','=','sale'),('company_id','=',self.branch_id.company_id.id)])
                if ppn:
                    acc=branch_config[0].tagihan_birojasa_bbn_account_id
                    if line.account_id.id==acc.id:
                        if line.credit>0:
                            base_amount=line.credit/1.1
                            ppn_amount=base_amount * ppn.amount    
                            line.write({'credit':line.credit - ppn_amount })
                            obj_move_line.create({
                                'name': ppn.description or '/',
                                'ref': self.origin or '/',
                                'account_id': ppn.account_collected_id.id,
                                'journal_id': self.journal_id.id,
                                'period_id': self.period_id.id,
                                'date': self.create_date,
                                'date_maturity':self.date_due,
                                'debit': 0,
                                'credit': ppn_amount,
                                'branch_id' : self.branch_id.id,
                                'division' : self.division,
                                'partner_id' : self.partner_id.id,
                                'move_id': self.move_id.id,
                                'analytic_account_id' : self.analytic_4.id,
                                'tax_code_id':ppn.tax_code_id.id,
                                'tax_amount':base_amount,
                                # 'analytic_4':self.analytic_4.id,
                                })
      
            line.move_id.post()

        # for i in self.move_id.line_id:
        #     print i.name,i.debit,i.credit,'################'


class dym_account_invoice_withholding(models.Model):
    _name = "dym.account.invoice.withholding"
    _rec_name = "display_name"
    _description = "Account Invoice Withholding"

    invoice_id = fields.Many2one(
        'account.invoice',
        'Invoice',
        required=True,
        ondelete='cascade',
        )
    display_name = fields.Char(
        compute='get_display_name'
        )
    name = fields.Char(
        'Nomor Bukti Potong',
        )
    internal_number = fields.Char(
        'Internal Number',
        required=True,
        default='/',
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    date = fields.Date(
        'Date',
        required=True,
        default=fields.Date.context_today,
        )
    state = fields.Selection(
        related='invoice_id.state',
        default='draft',
        )
    tax_withholding_id = fields.Many2one(
        'account.tax.withholding',
        string='Jenis PPh',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    comment = fields.Text(
        'Additional Information',
        )
    amount = fields.Float(
        'Jumlah PPh',
        required=True,
        digits=dp.get_precision('Account'),
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    tax_base = fields.Float(
        'Tax Base',
        required=True,
        digits=dp.get_precision('Account'),
        states={'draft': [('readonly', False)]},
        )
    move_line_id = fields.Many2one(
        'account.move.line',
        'Journal Item',
        readonly=True,
        )
    # Related fields
    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        store=True, readonly=True,
        )
    company_id = fields.Many2one(
        'res.company',
        related='invoice_id.branch_id.company_id',
        string='Company', store=True, readonly=True
        )
    type = fields.Selection(
        related='invoice_id.type',
        string='Tipe',
        # string='Type',
        # waiting for a PR 9081 to fix computed fields translations
        readonly=True,
        )

    # Ini di-comment sementara
    # _sql_constraints = [
    #     ('internal_number_uniq', 'unique(internal_number, tax_withholding_id)',
    #         'Internal Number must be unique per Tax Withholding!'),
    # ]

    # @api.one
    # @api.depends('invoice_id')
    # def get_tax_base(self):
    #     self.tax_base = self.invoice_id.amount_untaxed

    def _unit_compute_inv(self, cr, uid, taxes, price_unit):
        res = []
        cur_price_unit = price_unit

        tax_parent_tot = 0.0
        for tax in taxes:
            if tax.type=='percent':
                tax_parent_tot += tax.amount

        for tax in taxes:
            if tax.type=='fixed':
                cur_price_unit -= tax.amount

        for tax in taxes:
            if tax.type=='percent':
                amount = (cur_price_unit / (1 + tax_parent_tot)) * tax.amount

            elif tax.type=='fixed':
                amount = tax.amount

            todo = 1
            values = {
                'id': tax.id,
                'todo': todo,
                'name': tax.name,
                'amount': amount,
                'account_collected_id': tax.account_id.id,
                'account_paid_id': tax.ref_account_id.id,
                'account_analytic_collected_id': tax.account_analytic_id.id,
                'account_analytic_paid_id': tax.ref_account_analytic_id.id,
                'base_code_id': tax.base_code_id.id,
                'ref_base_code_id': tax.ref_base_code_id.id,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'price_unit': cur_price_unit,
                'tax_code_id': tax.tax_code_id.id,
                'ref_tax_code_id': tax.ref_tax_code_id.id,
            }
            res.append(values)

        total = 0.0
        for r in res:
            if r['todo']:
                total += r['amount']
        for r in res:
            r['price_unit'] -= total
            r['todo'] = 0
        return res

    def compute_inv(self, cr, uid, taxes, price_unit, precision=None):
        if not precision:
            precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        res = self._unit_compute_inv(cr, uid, taxes, price_unit)
        total = 0.0
        for r in res:
            if r.get('balance',False):
                r['amount'] = round(r['balance'], precision) - total
            else:
                r['amount'] = round(r['amount'], precision)
                total += r['amount']
        return res

    def _unit_compute(self, cr, uid, taxes, price_unit):
        res = []
        cur_price_unit=price_unit
        for tax in taxes:
            # we compute the amount for the current tax object and append it to the result
            if tax.type=='percent':
                amount = cur_price_unit * tax.amount

            elif tax.type=='fixed':
                amount = tax.amount

            data = {
                'id':tax.id,
                'name': tax.name,
                'amount': amount,
                'account_collected_id':tax.account_id.id,
                'account_paid_id':tax.ref_account_id.id,
                'account_analytic_collected_id': tax.account_analytic_id.id,
                'account_analytic_paid_id': tax.ref_account_analytic_id.id,
                'base_code_id': tax.base_code_id.id,
                'ref_base_code_id': tax.ref_base_code_id.id,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'price_unit': cur_price_unit,
                'tax_code_id': tax.tax_code_id.id,
                'ref_tax_code_id': tax.ref_tax_code_id.id,
            }
            res.append(data)
        return res

    def _compute(self, cr, uid, taxes, price_unit, precision=None):
        if not precision:
            precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        res = self._unit_compute(cr, uid, taxes, price_unit)
        total = 0.0
        for r in res:
            if r.get('balance',False):
                r['amount'] = round(r.get('balance', 0.0), precision) - total
            else:
                r['amount'] = round(r.get('amount', 0.0), precision)
                total += r['amount']
        return res

    @api.onchange('tax_base','tax_withholding_id')
    def get_tax_amount(self):
        amount = 0
        # if self.tax_base == 0:
        #     self.tax_base = self.birojasa_id.net_amount        
        # for x in self.birojasa_id.line_dr_ids:
        #     if x.move_line_id.move_id:
        #         model = x.move_line_id.move_id.model
        #         res_id = x.move_line_id.move_id.transaction_id
        #         # if model == 'dym.proses.birojasa':
        #         #     for vou in self.env[model].browse([res_id]):
        #         #         for y in vou.line_dr_ids:
        #         #             self.tax_base = y.amount
        #         # elif model == 'account.invoice':
        #         #     for inv in self.env[model].browse([res_id]):
        #         #         self.tax_base = inv.amount_untaxed

        #     else:
        #         self.tax_base = x.amount

        if self.tax_base and self.tax_withholding_id and self.tax_withholding_id.type != 'none':
            precision = self.env['decimal.precision'].precision_get('Account')
            tax_compute_precision = precision
            if self.tax_withholding_id.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_compute_precision += 5
            totalin = totalex = round(self.tax_base, precision)
            tin = []
            tex = []
            if not self.tax_withholding_id.price_include:
                tex.append(self.tax_withholding_id)
            else:
                tin.append(self.tax_withholding_id)
            tin = self.compute_inv(tin, self.tax_base, precision=tax_compute_precision)
            for r in tin:
                totalex -= r.get('amount', 0.0)
            totlex_qty = 0.0
            try:
                totlex_qty = totalex
            except:
                pass
            tex = self._compute(tex, totlex_qty, precision=tax_compute_precision)
            for r in tex:
                totalin += r.get('amount', 0.0)
            res = {
                'total': totalex,
                'total_included': totalin,
                'taxes': tin + tex
            }
            amount = sum(t['amount'] for t in res['taxes'])            
        self.amount = amount

    @api.one
    @api.depends('name', 'internal_number')
    def get_display_name(self):
        display_name = self.internal_number
        if self.name:
            display_name += ' (%s)' % self.name
        self.display_name = display_name

    @api.one
    @api.constrains('tax_withholding_id', 'invoice_id')
    def check_tax_withholding(self):
        if self.invoice_id.branch_id.company_id != self.tax_withholding_id.company_id:
            raise Warning(_(
                'Voucher and Tax Withholding must belong to the same company'))

    @api.model
    def create(self, vals):
        if vals.get('internal_number', '/') == '/':
            tax_withholding = self.tax_withholding_id.browse(
                vals.get('tax_withholding_id'))
            if not tax_withholding:
                raise Warning(_('Tax Withholding is Required!'))
            sequence = tax_withholding.sequence_id
            vals['internal_number'] = sequence.next_by_id(sequence.id) or '/'
        kas_negara_id = self.env['res.partner'].search([('kas_negara','=',True)])
        if not kas_negara_id:
            raise Warning(_(
                'Kas Negara belum ditentukan, silahkan centang Kas Negara di form Partner'))
        vals['partner_id'] = kas_negara_id.id
        return super(dym_account_invoice_withholding, self).create(vals)


# class dym_harga_bbn(models.Model):
#     _inherit="dym.harga.bbn"

#     partner_id = fields.Many2one('res.partner','Biro Jasa',domain="[('partner_type','=','Pihak_ke_3')]")



