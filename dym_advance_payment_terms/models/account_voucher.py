from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp import api, _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF

class dym_account_voucher_custom(osv.osv):
    _inherit = 'account.voucher'

    def onchange_date_due(self, cr, uid, ids, partner_id, date_due, context=None):
        value = {}
        warning = {}
        holiday_name = False
        new_date = False
        Holiday = self.pool.get('hr.holiday.year')
        Partner = self.pool.get('res.partner')

        if not all([partner_id,date_due]):
            return {}

        for partner in Partner.browse(cr, uid, [partner_id], context=context):
            if not partner.advanced_payment_terms:
                return {}

        due_date = datetime.strptime(date_due,DSDF)
        is_holiday = False
        if due_date.weekday()==5:
            is_holiday = True
            holiday_name = 'Sabtu'
        if due_date.weekday()==6:
            is_holiday = True
            holiday_name = 'Minggu'
        holiday_ids = Holiday.search(cr, uid, [('date_start','<=',date_due),('date_stop','>=',date_due)])
        if holiday_ids:
            is_holiday = True
            for holiday in Holiday.browse(cr, uid, holiday_ids, context=context):
                holiday_name = 'libur %s' % holiday.name
        while True:
            due_date_str = due_date.strftime(DSDF)
            holiday_ids = Holiday.search(cr, uid, [('date_start','<=',due_date_str),('date_stop','>=',due_date_str)])
            if due_date.weekday() in (5,6) or holiday_ids:
                due_date = due_date - timedelta(days=1)
            else:
                break
        if is_holiday:
            if due_date.weekday()==0:
                new_duedate_dayname = 'Senin'
            if due_date.weekday()==1:
                new_duedate_dayname = 'Selasa'
            if due_date.weekday()==2:
                new_duedate_dayname = 'Rabu'
            if due_date.weekday()==3:
                new_duedate_dayname = 'Kamis'
            if due_date.weekday()==4:
                new_duedate_dayname = 'Jumat'
            warning = {
                'title': ('Perhatian !'),
                'message': (_('Supplier %s minta agar setiap pembayaran yang jatuh tempo di hari libur pembayarannya dimajukan ke hari kerja. Sedangkan tanggal jatuh tempo %s jatuh di hari %s. Maka dari itu, tanggal jatuh tempo dimajukan ke hari %s yaitu tanggal %s.' % (partner.name, date_due, holiday_name, new_duedate_dayname, due_date_str))),
            }
        value['date_due'] = due_date
        return {'value': value,'warning':warning}


class dym_account_voucher_line(osv.osv):
    _inherit = "account.voucher.line"


    def onchange_move_line_id(self, cr, user, ids, move_line_id, amount, currency_id, journal, partner_id=False, division=False, inter_branch_id=False, due_date_payment=False, supplier_payment=False, customer_payment=False, kwitansi=False, bawah=False, context=None):
        res = super(dym_account_voucher_line, self).onchange_move_line_id(cr, user, ids, move_line_id, amount, currency_id, journal, partner_id=partner_id, division=division, inter_branch_id=inter_branch_id, due_date_payment=due_date_payment, supplier_payment=supplier_payment, customer_payment=customer_payment, kwitansi=kwitansi, bawah=bawah, context=context)
        move_line_pool = self.pool.get('account.move.line')
        currency_pool = self.pool.get('res.currency')
        account_journal = self.pool.get('account.journal')
        purchase_order = self.pool.get('purchase.order')
        stock_picking = self.pool.get('stock.picking')
        serial_number = self.pool.get('stock.production.lot')
        Warning = {}
        if move_line_id :
            remaining_amount = amount
            journal_brw = account_journal.browse(cr,user,journal)
            currency_id = currency_id or journal_brw.company_id.currency_id.id
            company_currency = journal_brw.company_id.currency_id.id
            move_line_brw = move_line_pool.browse(cr,user,move_line_id)
            if move_line_brw.settlement_id:
                Warning = {
                    'title': ('Perhatian !'),
                    'message': ("Settlement untuk advance payment %s sudah dibuat dengan nomor %s!")%(move_line_brw.avp_id.name, move_line_brw.settlement_id.name),
                }
                res['warning'] = Warning
                res['value'] = {}
                res['value']['move_line_id'] = False
                return res
            if move_line_brw.currency_id and currency_id == move_line_brw.currency_id.id:
                amount_original = abs(move_line_brw.amount_currency)
                amount_unreconciled = abs(move_line_brw.fake_balance)
            else:
                #always use the amount booked in the company currency as the basis of the conversion into the voucher currency
                amount_original = currency_pool.compute(cr, user, company_currency, currency_id, move_line_brw.credit or move_line_brw.debit or 0.0, context=context)
                amount_unreconciled = currency_pool.compute(cr, user, company_currency, currency_id, abs(move_line_brw.fake_balance), context=context)

            res['value'].update({
                'name':move_line_brw.move_id.name,
                'move_line_id':move_line_brw.id,                
                'amount_original': amount_original,
                'amount': move_line_id and min(abs(remaining_amount), amount_unreconciled) or 0.0,
                'date_original':move_line_brw.date,
                'date_due':move_line_brw.date_maturity,
                'amount_unreconciled': amount_unreconciled,
            })
            
            if move_line_brw.invoice.type == 'in_invoice' and move_line_brw.invoice.tipe == 'purchase' and not move_line_brw.invoice.consolidated :
                if all(line.quantity == line.consolidated_qty or line.product_id.type == 'service' for line in move_line_brw.invoice.invoice_line):
                    move_line_brw.invoice.write({'consolidated': True})
                else:
                    Warning = {
                        'title': ('Perhatian !'),
                        'message': ("Penerimaan atas Invoice '%s' belum lengkap, mohon lakukan consolidate invoice !")%(move_line_brw.invoice.number),
                    }
                    res['warning'] = Warning
                    res['value'] = {}
                    res['value']['move_line_id'] = False
            if move_line_brw.invoice.origin:
                if move_line_brw.invoice.type == 'in_invoice' and move_line_brw.invoice.tipe == False and len(move_line_brw.invoice.origin) > 4 and (move_line_brw.invoice.origin[:4] == 'PRBJ' or move_line_brw.invoice.origin[:3] == 'TBJ'):
                    obj_pr_birojasa = self.pool.get('dym.proses.birojasa')
                    obj_tr_stnk_line = self.pool.get('dym.penerimaan.stnk.line')
                    pr_birojasa_ids = obj_pr_birojasa.search(cr, user, [('name','=',move_line_brw.invoice.origin.split(' ') or ''),('type','=','reg')], limit=1)
                    if pr_birojasa_ids:
                        pr_birojasa = obj_pr_birojasa.browse(cr, user, pr_birojasa_ids)
                        for line in pr_birojasa.proses_birojasa_line:
                            if not line.name.penerimaan_notice_id.id or not line.name.tgl_terima_notice:
                                Warning = {
                                    'title': ('Perhatian !'),
                                    'message': ("Pembayaran tagihan birojasa %s tidak bisa diproses, karena notice belum diterima!")%(move_line_brw.invoice.origin),
                                }
                                res['warning'] = Warning
                                res['value'] = {}
                                res['value']['move_line_id'] = False

        if supplier_payment == True:
            if 'domain' not in res:
                res['domain'] = {}
            if bawah == False:
                partner = self.pool.get('res.partner').browse(cr, user, [partner_id], context=context)
                move_line_domain = [('account_id.type','=','payable'),('credit','!=',0), ('reconcile_id','=', False), ('partner_id','=',partner_id),('division','=',division),('dym_loan_id','=',False)]
                if not partner.advanced_payment_terms:
                    move_line_domain += ['|',('date_maturity','<=',due_date_payment),('date_maturity','=',False)]
            else:
                move_line_domain = [('account_id.type','=','receivable'),('debit','!=',0), ('reconcile_id','=', False),('partner_id','=',partner_id),('division','=',division),('dym_loan_id','=',False)]

            if inter_branch_id:
                move_line_domain += [('branch_id','=',inter_branch_id)]
            else:
                user_obj = self.pool.get('res.users').browse(cr, user, user)
                move_line_domain += [('branch_id','in',user_obj.area_id.branch_ids.ids)]
            move_line_search = self.pool.get('account.move.line').search(cr, user, move_line_domain)
            not_consolidated_line = []
            for move_line in self.pool.get('account.move.line').browse(cr, user, move_line_search):
                if move_line.invoice.type == 'in_invoice' and move_line.invoice.tipe == 'purchase' and not move_line.invoice.consolidated:
                    if all(line.quantity == line.consolidated_qty or line.product_id.type == 'service' or move_line.invoice.is_cip == True for line in move_line.invoice.invoice_line):
                        move_line.invoice.write({'consolidated': True})
                    else:
                        not_consolidated_line.append(move_line.id)
            if not_consolidated_line:
                move_line_domain += [('id','not in',not_consolidated_line)]
            res['domain']['move_line_id'] = move_line_domain
        if customer_payment == True:
            if 'domain' not in res:
                res['domain'] = {}
            if bawah == False:
                move_line_domain = [('kwitansi','=',kwitansi),('account_id.type','=','receivable'),('debit','!=',0), ('reconcile_id','=', False), ('partner_id','=',partner_id),('division','=',division),('dym_loan_id','=',False)]
            else:
                move_line_domain = [('account_id.type','=','payable'),('credit','!=',0), ('reconcile_id','=', False), ('partner_id','=',partner_id),('division','=',division),('dym_loan_id','=',False)]
                edi_doc_list = ['&', ('active','=',True), ('type','!=','view')]
                dicta = self.pool.get('dym.account.filter').get_domain_account(cr, user, ids,'exclude_customer_payment',context=None)
                edi_doc_list.extend(dicta)
                if dicta:
                    account_ids = self.pool.get('account.account').search(cr, user, edi_doc_list)
                    if account_ids:
                        move_line_domain += [('account_id','not in',account_ids)]
            if inter_branch_id:
                move_line_domain += [('branch_id','=',inter_branch_id)]
            else:
                user_obj = self.pool.get('res.users').browse(cr, user, user)
                move_line_domain += [('branch_id','in',user_obj.area_id.branch_ids.ids)]            
            res['domain']['move_line_id'] = move_line_domain
        if context == None:
            context = {}
        if 'line_ids' in context and context['line_ids'] and 'domain' in res and 'move_line_id' in res['domain'] and res['domain']['move_line_id']:
            voucher_line = self.pool.get('account.voucher').resolve_2many_commands(cr, user, 'line_ids', context['line_ids'], ['move_line_id'], context)
            line_ids = []
            for l in voucher_line:
                if isinstance(l, dict) and l['move_line_id'][0]:
                    line_ids += [l['move_line_id'][0]]
            if line_ids:
                res['domain']['move_line_id'] += [('id','not in',line_ids)]
        return res
