import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp


class dym_account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    def _register_hook(self, cr):
        selection = self._columns['tipe'].selection
        if ('md_sale_unit', 'md_sale_unit') and ('md_sale_sparepart', 'md_sale_sparepart') not in selection:
            self._columns['tipe'].selection.append(
                ('md_sale_unit', 'md_sale_unit'))
            self._columns['tipe'].selection.append(
                ('md_sale_sparepart', 'md_sale_sparepart'))
            
        return super(dym_account_invoice, self)._register_hook(cr)
    
    def _get_branch_journal_config_so(self,branch_id):
        result = {}
        obj_branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if not obj_branch_config:
            raise Warning( ("Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu"))
        else:
            if not(obj_branch_config.dym_so_account_discount_cash_id and obj_branch_config.dym_so_account_discount_program_id and obj_branch_config.dym_so_account_discount_lainnya_id):
                raise Warning( ("Konfigurasi cabang jurnal Diskon belum dibuat, silahkan setting dulu"))
        result.update({
                  'dym_so_account_discount_cash_id':obj_branch_config.dym_so_account_discount_cash_id,
                  'dym_so_account_discount_program_id':obj_branch_config.dym_so_account_discount_program_id,
                  'dym_so_account_discount_lainnya_id':obj_branch_config.dym_so_account_discount_lainnya_id,
                  })
        
        return result
    
    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        move_lines = super(dym_account_invoice,self).finalize_invoice_move_lines(move_lines)
        # if self.type=='out_invoice' and self.tipe in ('md_sale_unit', 'md_sale_sparepart'):
            
        #     if self.discount_cash>0 or self.discount_lain>0 or self.discount_program>0:
        #         move_lines.pop()
        #         journal_config = self._get_branch_journal_config_so(self.branch_id.id)
        #         period_ids = self.env['account.period'].find()
        #         move_obj = self.env['account.move']
                
        #         move_lines.append((0,0,{
        #                        'name': self.name,
        #                         'partner_id': self.partner_id.id,
        #                         'account_id': self.account_id.id,
        #                         'period_id': period_ids.id,
        #                         'date': datetime.now().strftime('%Y-%m-%d'),
        #                         'debit': self.amount_total,
        #                         'credit': 0.0,
        #                         'branch_id': self.branch_id.id,
        #                         'division': self.division,
        #                         'analytic_account_id':self.analytic_4,  
        #                 }))
                
        #         if self.discount_cash>0:
                    
        #             move_lines.append((0,0,{
        #                        'name': 'Diskon Cash '+ self.name,
        #                        'ref' : 'Diskon Cash '+ self.name, 
        #                         'partner_id': self.partner_id.id,
        #                         'account_id': journal_config['dym_so_account_discount_cash_id'].id,
        #                         'period_id': period_ids.id,
        #                         'date': datetime.now().strftime('%Y-%m-%d'),
        #                         'debit': self.discount_cash,
        #                         'credit': 0.0,                                
        #                         'branch_id': self.branch_id.id,
        #                         'division': self.division,
        #                         'analytic_account_id':self.analytic_4,  
        #                 }))
                    
        #         if self.discount_program>0:
        #             move_lines.append((0,0,{
        #                         'name': 'Diskon Program '+ self.name,
        #                         'ref' : 'Diskon Program '+ self.name,
        #                         'partner_id': self.partner_id.id,
        #                         'account_id': journal_config['dym_so_account_discount_program_id'].id,
        #                         'period_id': period_ids.id,
        #                         'date': datetime.now().strftime('%Y-%m-%d'),
        #                         'debit': self.discount_program,
        #                         'credit': 0.0,
        #                         'branch_id': self.branch_id.id,
        #                         'division': self.division,
        #                         'analytic_account_id':self.analytic_4,  
        #                 }))
    
                    
        #         if self.discount_lain>0:
        #             move_lines.append((0,0,{
        #                        'name': 'Diskon Cash '+ self.name,
        #                        'ref': 'Diskon Cash '+ self.name,
        #                         'partner_id': self.partner_id.id,
        #                         'account_id': journal_config['dym_so_account_discount_lainnya_id'].id,
        #                         'period_id': period_ids.id,
        #                         'date': datetime.now().strftime('%Y-%m-%d'),
        #                         'debit': self.discount_lain,
        #                         'credit': 0.0,
        #                         'branch_id': self.branch_id.id,
        #                         'division': self.division,
        #                         'analytic_account_id':self.analytic_4,  
        #                 }))
               
        return move_lines