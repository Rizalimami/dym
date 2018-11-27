# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.float_utils import float_round, float_compare
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp
from openerp.osv.orm import except_orm


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    sale_return_type = fields.Selection([
        ('none',"None"),
        ('uang',"Uang"),
        ('barang',"Barang"),
        ('admin',"Admin"),
    ], string='Sale Return Type')


    @api.multi
    def _action_move_create(self):
        account_invoice_tax = self.env['account.invoice.tax']
        account_move = self.env['account.move']
        for inv in self:
            if not inv.journal_id.sequence_id:
                raise except_orm(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise except_orm(_('No Invoice Lines!'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue
            ctx = dict(self._context, lang=inv.partner_id.lang)
            date_invoice = inv.date_invoice
            date = date_invoice
            if not inv.sale_return_type:
                company_currency = inv.company_id.currency_id
                if not inv.date_invoice:
                    if inv.currency_id != company_currency and inv.tax_line:
                        raise except_orm(
                            _('Warning!'),
                            _('No invoice date!'
                                '\nThe invoice currency is not the same than the company currency.'
                                ' An invoice date is required to determine the exchange rate to apply. Do not forget to update the taxes!'
                            )
                        )
                    inv.with_context(ctx).write({'date_invoice': openerp.fields.Date.context_today(self)})
                iml = inv._get_analytic_lines()
                compute_taxes = account_invoice_tax.compute(inv.with_context(lang=inv.partner_id.lang))
                inv.check_tax_lines(compute_taxes)

                if inv.payment_term:
                    total_fixed = total_percent = 0
                    for line in inv.payment_term.line_ids:
                        if line.value == 'fixed':
                            total_fixed += line.value_amount
                        if line.value == 'procent':
                            total_percent += line.value_amount
                    total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                    if (total_fixed + total_percent) > 100:
                        raise except_orm(_('Error!'), _("Cannot create the invoice.\nThe related payment term is probably misconfigured as it gives a computed amount greater than the total invoiced amount. In order to avoid rounding issues, the latest line of your payment term must be of type 'balance'."))
                inv._recompute_tax_amount()
                iml += account_invoice_tax.move_line_get(inv.id)
                if inv.type in ('in_invoice', 'in_refund'):
                    ref = inv.reference
                else:
                    ref = inv.number                    
                diff_currency = inv.currency_id != company_currency
                total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, ref, iml)
                name = inv.supplier_invoice_number or inv.name or '/'
                totlines = []
                if inv.payment_term:
                    totlines = inv.with_context(ctx).payment_term.compute(total, date_invoice)[0]
                if totlines:
                    res_amount_currency = total_currency
                    ctx['date'] = date_invoice
                    for i, t in enumerate(totlines):
                        if inv.currency_id != company_currency:
                            amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                        else:
                            amount_currency = False
                        res_amount_currency -= amount_currency or 0
                        if i + 1 == len(totlines):
                            amount_currency += res_amount_currency
                        iml.append({
                            'type': 'dest',
                            'name': name,
                            'price': t[1],
                            'account_id': inv.account_id.id,
                            'date_maturity': t[0],
                            'amount_currency': diff_currency and amount_currency,
                            'currency_id': diff_currency and inv.currency_id.id,
                            'ref': ref,
                        })
                else:
                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': total,
                        'account_id': inv.account_id.id,
                        'date_maturity': inv.date_due,
                        'amount_currency': diff_currency and total_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'ref': ref
                    })
                part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
                line = [(0, 0, self.line_get_convert(l, part.id, date)) for l in iml]
                line = inv.group_lines(iml, line)
                journal = inv.journal_id.with_context(ctx)
                if journal.centralisation:
                    raise except_orm(_('User Error!'),
                            _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))
                line = inv.finalize_invoice_move_lines(line)
            else:
                period_ids = self.env['account.period'].find(dt=inv.date_invoice)
                original_invoice_id = self.env['account.invoice'].search([('origin','=',inv.name)])
                if len(original_invoice_id)>1:
                    raise except_orm(_('Error!'),
                        _('Ditemukan lebih dari satu jurnal atas invoice penjualan. Silahkan hubungi system administrator untuk melanjutkan.'))

                sale_account_id = False
                for ln in inv.invoice_line:
                    if not ln.product_id:
                        continue
                    account_id = self.env['product.product']._get_account_id(ln.product_id.id)
                    if not account_id:
                        raise except_orm(_('Error!'),
                            _('Tidak ditemukan account income untuk product %s. Mohon lengkapi dulu.' % ln.product_id.name))
                    sale_account_id = account_id
                if not sale_account_id:
                    raise except_orm(_('Error!'),
                        _('Tidak ditemukan product pada return ini.'))

                line = []
                for sml in original_invoice_id.move_id.line_id:
                    if sale_account_id == sml.account_id.id:
                        account_id = inv.journal_id.default_debit_account_id
                    elif sml.account_id.type=='receivable':
                        account_id = inv.account_id
                    else:
                        account_id = sml.account_id

                        # Retur Jual PIC
                        dso=self.env['dealer.sale.order'].search([('name','=',inv.name)])
                        if dso and len(dso)==1:
                            if dso.is_pic:
                                branch_config=self.env['dym.branch.config'].search([('branch_id','=',inv.branch_id.id)])
                                if branch_config and len(branch_config)==1:
                                    if sml.account_id.id == branch_config.dealer_so_account_penjualan_pic_id.id:
                                        if not branch_config.retur_jual_dso_pic_account_id:
                                            raise except_orm(_('Error!'), _('Tidak ditemukan account retur jual pic di branch config. Mohon lengkapi dulu.'))
                                        else:
                                            account_id = branch_config.retur_jual_dso_pic_account_id

                        # Retur Jual PIC Sale Order
                        so=self.env['sale.order'].search([('name','=',inv.name)])
                        if so and len(so)==1:
                            if so.tipe_transaksi=='pic':
                                branch_config=self.env['dym.branch.config'].search([('branch_id','=',inv.branch_id.id)])
                                if branch_config and len(branch_config)==1:
                                    if sml.account_id.id == branch_config.dym_so_account_penjualan_pic_id.id:
                                        if not branch_config.retur_jual_so_pic_account_id:
                                            raise except_orm(_('Error!'),_('Tidak ditemukan account retur jual pic di branch config. Mohon lengkapi dulu.'))
                                        else:
                                            account_id = branch_config.retur_jual_so_pic_account_id
                        #JIKA BARANG SUDAH DI DELIVER KE CUSTOMER, MAKA JURNAL PERSEDIAAN TIDAK DIBUAT
                        obj_retur=self.env['dym.retur.jual'].search([('name','=',inv.origin)])
                        if account_id.user_type.code=='AT077' or  account_id.user_type.code=='AT018' :
                            if obj_retur.so_id.shipped:
                                continue

                            if obj_retur.dso_id:
                                obj_picking=self.env['stock.picking']
                                picking=obj_picking.search([('origin','=',obj_retur.dso_id.name)])
                                if picking:
                                    if picking[0].state=='done':
                                        continue
                    ml_vals = {
                        'name': sml.name or '/',
                        'ref': sml.ref or '/',
                        'account_id': account_id.id,
                        'journal_id': sml.journal_id.id,
                        'period_id': period_ids.id,
                        'date': inv.date_invoice,
                        'debit': sml.credit,
                        'credit': sml.debit,
                        'branch_id' : sml.branch_id.id,
                        'division' : sml.division,
                        'partner_id' : sml.partner_id.id,
                        'analytic_account_id' : sml.analytic_account_id.id,     
                    }
                    line.append((0,0,ml_vals))
                    account = self.env['account.account'].browse([account_id.id])[0].read(['name'])

                journal = inv.journal_id.with_context(ctx)
                if journal.centralisation:
                    raise except_orm(_('User Error!'),
                            _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            move_vals = {
                'ref': inv.reference or inv.name,
                'line_id': line,
                'journal_id': journal.id,
                'date': inv.date_invoice,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
            }
            ctx['company_id'] = inv.company_id.id
            period = inv.period_id
            if not period:
                period = period.with_context(ctx).find(date_invoice)[:1]
            if period:
                move_vals['period_id'] = period.id
                for i in line:
                    i[2]['period_id'] = period.id
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            vals = {
                'move_id': move.id,
                'period_id': period.id,
                'move_name': move.name,
            }

            inv.with_context(ctx).write(vals)

            #Menghilangkan unbalance journal dengan mengurangi nilai TAX
            debit = credit = 0
            for line in move.line_id:
                if line.debit:
                    debit+=line.debit
                elif line.credit:
                    credit+=line.credit
            
            if credit > debit :
                diff = credit - debit
                for line in move.line_id:
                    if 'PPN' in line.name:
                        line.write({'credit':line.credit - diff})
            
            if journal.entry_posted:
                move.post()
        self._log_event()
        return True
