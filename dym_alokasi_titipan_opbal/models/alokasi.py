from openerp import models, fields, api, _, SUPERUSER_ID, workflow
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class dym_alokasi_titipan(models.Model):
    _inherit = "dym.alokasi.titipan"

    @api.one
    @api.depends('line_ids.amount')
    def _compute_total_alokasi(self):
        if not self.force_alocate:
            total_amount_alokasi = 0.0
            for line in self.line_ids:
                if not line.partner_id.default_code:
                    raise osv.except_osv(('Perhatian!'), ('Partner "%s" [%s, %s] tidak memiliki kode, mohon lengkapi dulu untuk melanjutkan.' % (line.partner_id.name, line.amount, line.lot_id)))
                if line.partner_id.default_code not in str(line.alokasi_id.log_import):
                    total_amount_alokasi += line.amount
            self.total_alokasi = total_amount_alokasi
        else:
            self.total_alokasi = sum(line.amount for line in self.line_ids)
            
    total_alokasi = fields.Float(string='Total Alokasi', digits=dp.get_precision('Account'), readonly=True, compute='_compute_total_alokasi')
    line_ids = fields.One2many('dym.alokasi.titipan.line', 'alokasi_id', 'Detail Alokasi Customer Deposit')

    @api.multi
    def confirm_alokasi(self):
        if len(self.line_ids.filtered(lambda s:s.voucher_id))>0:
            for line in self.line_ids.filtered(lambda s:not s.voucher_id):
                line.create_voucher()
                self.env.cr.commit()
            if len(self.line_ids) == len(self.line_ids.filtered(lambda s:s.voucher_id)):
                self.write({'state':'done'})
            return
        if not self.force_alocate:
            total_amount_alokasi = sum(line.amount for line in self.line_ids if line.partner_id.default_code not in str(line.alokasi_id.log_import))
        else:
            total_amount_alokasi = sum(line.amount for line in self.line_ids)
        
        if total_amount_alokasi <= 0 :
            raise osv.except_osv(('Tidak bisa confirm!'), ('Amount alokasi harus lebih besar dari 0'))
        if not self.line_ids:
            raise osv.except_osv(('Tidak bisa confirm!'), ('Detail Alokasi Customer Deposit harus diisi'))
        if self.total_titipan < total_amount_alokasi:
            raise osv.except_osv(('Tidak bisa confirm!'), ('Total titipan [%s] lebih kecil dari total amount yang dialokasikan [%s]!')%(self.total_titipan, total_amount_alokasi))

        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        period_ids = self.env['account.period'].find()        
        branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if not branch_config :
            raise osv.except_osv(('Perhatian !'), ("Belum ada branch config atas branch %s !")%(branch_config.branch_id.code))
        journal_alokasi =  branch_config.dym_journal_alokasi_customer_deposit
        if not journal_alokasi:
            raise osv.except_osv(('Perhatian !'), ("Journal alokasi customer deposit belum lengkap dalam branch %s !")%(branch_config.branch_id.name))
        move_journal = {
            'name': self.name,
            'ref': self.memo,
            'journal_id': journal_alokasi.id,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'period_id':period_ids.id,
            'transaction_id':self.id,
            'model':self.__class__.__name__,
        }
        create_journal = move_obj.create(move_journal)
        titipan_line_list = []
        titipan_line_dict = {}
        for line in self.line_ids:
            if line.partner_id.default_code not in str(self.log_import) or self.force_alocate:
                if line.titipan_line_id not in titipan_line_list:
                    titipan_line_list.append(line.titipan_line_id)
                    titipan_line_dict[line.titipan_line_id] = {'amount':0}
                titipan_line_dict[line.titipan_line_id]['amount'] += line.amount
                created_move_line = move_line_obj.create({
                    'name': _('Alokasi Customer Deposit ' + self.name),
                    'ref': _(line.description),
                    'partner_id': line.partner_id.id,
                    'account_id': line.titipan_line_id.account_id.id,
                    'period_id':period_ids.id,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'debit': 0.0,
                    'credit': line.amount,
                    'branch_id': line.branch_id.id,
                    'division': line.division,
                    'analytic_account_id' : line.titipan_line_id.analytic_account_id.id ,
                    'move_id': create_journal.id
                })
                line.write({'move_line_id':created_move_line.id})
            
        titipan_line_ids = []
        for titipan_line in titipan_line_list:
            allocated_amount = titipan_line_dict[titipan_line]['amount']
            if allocated_amount > titipan_line.fake_balance:
                raise osv.except_osv(('Tidak bisa confirm!'), ("Total Customer Deposit [%s] untuk titipan %s lebih besar dari balance yang bisa dialokasikan [%s]")%(allocated_amount, titipan_line.name, titipan_line.fake_balance))
            created_move_line = move_line_obj.create({
                'name': _('Customer Deposit ' + titipan_line.name),
                'ref': _(self.name),
                'partner_id': titipan_line.partner_id.id,
                'account_id': titipan_line.account_id.id,
                'period_id':period_ids.id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'debit': allocated_amount,
                'credit': 0.0,
                'branch_id': titipan_line.branch_id.id,
                'division': titipan_line.division,
                'analytic_account_id' : titipan_line.analytic_account_id.id,
                'move_id': create_journal.id
            })
            if titipan_line.id not in titipan_line_ids:
                titipan_line_ids.append(titipan_line.id)
            titipan_line_ids.append(created_move_line.id)
        if titipan_line_ids:
            titipan_lines = move_line_obj.browse(titipan_line_ids)
            reconcile_id = titipan_lines.reconcile_partial('auto')
        
        if create_journal.journal_id.entry_posted:
            post_journal = create_journal.post()
        self.write({'move_id':create_journal.id,'confirm_uid':self._uid,'confirm_date':datetime.now()})

        for line in self.line_ids:
            line.create_voucher()
            self.env.cr.commit()

        if len(self.line_ids) == len(self.line_ids.filtered(lambda s:s.voucher_id)):
            self.write({'state':'done'})
        return True

class dym_alokasi_titipan_line(models.Model):
    _inherit = "dym.alokasi.titipan.line"

    @api.multi
    def create_voucher(self):
        move_line_id = self.move_line_id
        if not self.move_line_id:
            move_line_id = self.env['account.move.line'].search([('move_id','=', self.alokasi_id.move_id.id),('partner_id','=', self.partner_id.id),('account_id','=', self.titipan_line_id.account_id.id),('credit','=', self.amount),('reconcile_id','=', False)], limit=1)
            self.write({'move_line_id':move_line_id.id})
        if not move_line_id:
            if not self.alokasi_id.force_alocate:
                if self.partner_id.default_code in self.alokasi_id.log_import:
                    return True
            else:
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan journal entries untuk transaksi %s %s, titipan!")%(self.alokasi_id.name, self.description))
        amount = self.amount if move_line_id.fake_balance >= self.amount else move_line_id.fake_balance
        move_line_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_id.id, amount, False, False)
        voucher_line = [[0,0,{
            'move_line_id': move_line_vals['value']['move_line_id'], 
            'account_id': move_line_vals['value']['account_id'], 
            'date_original': move_line_vals['value']['date_original'], 
            'date_due': move_line_vals['value']['date_due'], 
            'amount_original': move_line_vals['value']['amount_original'], 
            'amount_unreconciled': move_line_vals['value']['amount_unreconciled'],
            'amount': amount, 
            'currency_id': move_line_vals['value']['currency_id'], 
            'type': 'dr', 
            'name': move_line_vals['value']['name'],
            'reconcile': True,
        }]]

        branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)], limit =1)
        move_line_ar = self.env['account.move.line'].search([('account_id','=', branch_config.dealer_so_journal_pelunasan_id.default_debit_account_id.id),('partner_id','=',self.partner_id.id),('reconcile_id','=', False),('debit','!=',0),'|',('ref','ilike','NDE-'),('ref','ilike','DSM-')])
        if len(move_line_ar)>1:
            if self.lot_id.dealer_sale_order_id:
                for mla in move_line_ar:
                    if self.lot_id.dealer_sale_order_id.name == mla.ref:
                        move_line_ar = mla
                        break
        if len(move_line_ar)>1:
            raise osv.except_osv(('Perhatian !'), ("Ditemukan lebih dari satu AR untuk partner %s dan nosin %s di cabang %s !")%(self.partner_id.name,self.lot_id.name,branch_config.branch_id.name))
        if move_line_ar:
            amount_ar = move_line_ar.debit if move_line_ar.fake_balance >= move_line_ar.debit else move_line_ar.fake_balance
            move_line_ar_vals = self.env['account.voucher.line'].onchange_move_line_id(move_line_ar.id, amount_ar, False, False)
        else:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan AR untuk partner '%s' dengan nosin %s di cabang '%s' !")%(self.partner_id.name,self.lot_id.name,branch_config.branch_id.name, ))

        if move_line_ar:
            if amount_ar == amount:
                voucher_cr_line = [[0,0,{
                    'move_line_id': move_line_ar_vals['value']['move_line_id'], 
                    'account_id': move_line_ar_vals['value']['account_id'], 
                    'date_original': move_line_ar_vals['value']['date_original'], 
                    'date_due': move_line_ar_vals['value']['date_due'], 
                    'amount_original':move_line_ar.debit, 
                    'amount_unreconciled': amount_ar,
                    'amount': amount, 
                    'currency_id': move_line_ar_vals['value']['currency_id'], 
                    'type': 'cr', 
                    'name': move_line_ar_vals['value']['name'],
                    'reconcile': True if amount == amount_ar else (False if amount < amount_ar else True),
                       }]]
            else:
                if not self.alokasi_id.force_alocate:
                    errorrrr
                    return True
                else:
                    vals = {
                        'move_line_id': move_line_ar_vals['value']['move_line_id'], 
                        'account_id': move_line_ar_vals['value']['account_id'], 
                        'date_original': move_line_ar_vals['value']['date_original'], 
                        'date_due': move_line_ar_vals['value']['date_due'], 
                        'amount_original':move_line_ar.debit, 
                        'amount_unreconciled':move_line_ar.debit,
                        'amount': move_line_ar.debit, 
                        'currency_id': move_line_ar_vals['value']['currency_id'], 
                        'type': 'cr', 
                        'name': move_line_ar_vals['value']['name'],
                        'reconcile': True if amount == amount_ar else (False if amount < amount_ar else True),
                    }
                    if amount > amount_ar:
                        vals.update({
                            'amount': amount_ar,
                            'reconcile': True,
                        })
                    elif amount < amount_ar:
                        vals.update({
                            'amount': amount,
                            'reconcile': True,
                        })
                    voucher_cr_line = [(0,0,vals)]
        else:
            raise osv.except_osv(('Perhatian!'), ('AR tidak ditemukan'))
        journal_alokasi = branch_config.dym_journal_alokasi_customer_deposit
        if not journal_alokasi:
            raise osv.except_osv(('Perhatian !'), ("Journal alokasi customer deposit belum lengkap dalam branch %s !")%(branch_config.branch_id.name))
        analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.branch_id, 'Umum',False, 4, 'General')
        voucher = {
            'branch_id':self.branch_id.id, 
            'division': self.division, 
            'inter_branch_id':self.branch_id.id, 
            'inter_branch_division': self.division, 
            'partner_id': self.partner_id.id, 
            'date':datetime.now().strftime('%Y-%m-%d'), 
            'amount': 0, 
            'reference': self.alokasi_id.name, 
            'name': self.alokasi_id.memo, 
            'user_id': self._uid,
            'type': 'receipt',
            'line_dr_ids': voucher_line,
            'line_cr_ids': voucher_cr_line,
            'analytic_1': analytic_1,
            'analytic_2': analytic_2,
            'analytic_3': analytic_3,
            'analytic_4': analytic_4,
            'journal_id': journal_alokasi.id,
            'account_id': journal_alokasi.default_debit_account_id.id,
            'alokasi_cd': True,
        }        
        
        voucher_obj = self.env['account.voucher']
        voucher_id = voucher_obj.create(voucher)
        self.write({'voucher_id': voucher_id.id})

        voucher_id.validate_or_rfa_credit()
        voucher_id.signal_workflow('approval_approve')

        if amount > amount_ar :
            analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(self.alokasi_id.branch_id, 'Umum',False, 4, 'General')
            if not branch_config.dym_journal_selisih_alokasi_cde:
                raise osv.except_osv(('Perhatian !'), ("Mohon lengkapi Journal selisih alokasi customer deposit branch %s !")%(branch_config.branch_id.name))  
            else:
                diff = amount - amount_ar 
                new_cde_line = [[0,0,{
                    'account_id': branch_config.dym_journal_selisih_alokasi_cde.default_credit_account_id.id, 
                    'name': 'Selisih kelebihan bayar transaksi %s' % voucher_id.name, 
                    'analytic_2': analytic_2, 
                    'analytic_3': analytic_3,
                    'account_analytic_id': analytic_4,
                    'amount': diff, 
                }]]
                new_cde = {
                    'company_id':self.alokasi_id.voucher_id.company_id.id,
                    'branch_id':self.alokasi_id.voucher_id.branch_id.id, 
                    'division': self.alokasi_id.voucher_id.division, 
                    'partner_id': self.alokasi_id.voucher_id.partner_id.id, 
                    'date':datetime.now().strftime('%Y-%m-%d'), 
                    'amount': diff, 
                    'reference': self.alokasi_id.name, 
                    'name': self.alokasi_id.voucher_id.name, 
                    'user_id': self._uid,
                    'type': self.alokasi_id.voucher_id.type,
                    'line_dr_ids': False,
                    'line_cr_ids': new_cde_line,
                    'analytic_1': self.alokasi_id.voucher_id.analytic_1.id,
                    'analytic_2': self.alokasi_id.voucher_id.analytic_2.id,
                    'analytic_3': self.alokasi_id.voucher_id.analytic_3.id,
                    'analytic_4': self.alokasi_id.voucher_id.analytic_4.id,
                    'journal_id': journal_alokasi.id,
                    'account_id': branch_config.dym_journal_selisih_alokasi_cde.default_debit_account_id.id,
                    'alokasi_id': self.alokasi_id.id,
                    'voucher_ref_id': self.alokasi_id.voucher_id.id,
                    'is_hutang_lain': True,
                    'paid_amount': diff,
                }  
                voucher_obj = self.env['account.voucher']
                new_cde_id = voucher_obj.create(new_cde)
                self.write({'voucher_cde_id': new_cde_id.id})
                new_cde_id.validate_or_rfa_credit()
                new_cde_id.signal_workflow('approval_approve')
        return True

