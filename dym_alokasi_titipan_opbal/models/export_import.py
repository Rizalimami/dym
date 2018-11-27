from openerp import models, fields, api, _, SUPERUSER_ID, workflow
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class EksportImport(osv.osv_memory):
    _inherit = "eksport.import"

    def dym_alokasi_titipan_line(self, cr, uid, data, col,separator,context=None):
        vals = []
        Partner = self.pool.get('res.partner')
        Lot = self.pool.get('stock.production.lot')
        Branch = self.pool.get('dym.branch')

        id_alokasi = context.get('alokasi_id',False)
        if not id_alokasi:
            raise osv.except_osv(('Perhatian !'), ("ID Alokasi tidak ditemukan di context, mohon dicoba lagi!"))

        alokasi = self.pool.get('dym.alokasi.titipan').browse(cr, uid, id_alokasi)
        titipan_line = alokasi.titipan_move.line_id.filtered(lambda r: not r.reconcile_id and r.fake_balance > 0 and r.account_id.type in ['payable','receivable'])
        if not titipan_line:
            raise osv.except_osv(('Perhatian !'), ("Baris hutang tidak ditemukan di system!"))

        res_titipan_line = []
        
        for line in titipan_line:
            res_titipan_line.append({'line':line,'amount':line.fake_balance})
        
        for row in data:
            
            if len(row) not in [2,3]:
                raise osv.except_osv(('Perhatian !'), ("Format data import salah! Jika data opbal, perlu 3 kolom yaitu: 'code_customer', 'amount', 'branch'. Jika bukan data opbal perlu 2 kolom yaitu: 'NOSIN','NOMINAL'."))
            
            id_customer = False
            amount = 0
            branch_id = False
            nosin = False
            lot_id = False
            partner_id = False
            if len(row)==3:
                try:
                    id_customer = int(row[0])
                except ValueError, e:
                    raise osv.except_osv(('Perhatian !'), ("Kolom code_customer harus diisi dengan angka saja, tidak boleh aja huruf!"))

                partner_id = Partner.browse(cr, uid, [id_customer], context=context)
                if not partner_id:
                    raise osv.except_osv(('Perhatian !'), ("Customer dengan kode %s tidak ditemukan di system, mohon dicek kembali!" % id_customer))
                try:
                    amount = int(row[1])
                except ValueError, e:
                    raise osv.except_osv(('Perhatian !'), ("Kolom amount harus diisi dengan angka saja, tidak boleh aja huruf!"))
                branch_code = row[2]
                if not branch_code:
                    raise osv.except_osv(('Perhatian !'), ("Mohon lengkapi kolom Branch !"))
                id_branch = Branch.search(cr, uid, [('code','=',branch_code)])
                if not id_branch:
                    raise osv.except_osv(('Perhatian !'), ("Kode cabang %s tidak ditemukan di system !" % branch_code))
                branch_id = Branch.browse(cr, uid, id_branch, context=context)
            else:
                nosin = row[0]
                noka = False
                if '/' in nosin:
                    splitted_nosin = nosin.split('/')
                    if len(splitted_nosin) != 2:
                        raise osv.except_osv(('Perhatian !'), ("Format penulisan nosin salah, seharusnya 12 digit nosin saja atau bisa juga digabung dengan no rangka dipisah dengan satu tanda garis miring!"))
                    nosin, noka = splitted_nosin
                id_lot_search_domain = [('name','=',nosin),('state','not in',['workshop'])]
                if noka:
                    id_lot_search_domain += [('chassis_no','=',noka)]
                id_lot = Lot.search(cr, uid, id_lot_search_domain)
                if len(id_lot)>1:
                    id_lot = Lot.search(cr, uid, [('id','in',id_lot),('branch_id','!=',False)])
                if len(id_lot)>1:
                    id_lot = Lot.search(cr, uid, [('id','in',id_lot),('customer_reserved','!=',False)])

                valid_lot_id = []
                if len(id_lot)>1:
                    for lot_num in self.pool.get('stock.production.lot').browse(cr, uid, id_lot, context=context):
                        customer_reserved = lot_num.customer_reserved
                        if customer_reserved and customer_reserved.partner_type in ['Konsolidasi','Afiliasi']:
                            continue
                        valid_lot_id.append(lot_num.id)
                if valid_lot_id:
                    id_lot = valid_lot_id
                if len(id_lot)>1:
                    raise osv.except_osv(('Perhatian !'), ("Ditemukan lebih dari 1 nosin dengan kode %s, mohon dicek kembali !" % nosin))                    

                if not id_lot:
                    raise osv.except_osv(('Perhatian !'), ("Nosin dengan kode %s tidak ditemukan di system, mohon dicek kembali!" % nosin))

                lot_id = Lot.browse(cr, uid, id_lot, context=context)
                branch_id = lot_id.branch_id
                if not lot_id.customer_reserved:
                    raise osv.except_osv(('Perhatian !'), ("Nosin dengan kode %s tidak terhubung dengan customer manapun, mohon dicek kembali!" % nosin))
                partner_id = lot_id.customer_reserved
                try:
                    amount = int(row[1])
                except ValueError, e:
                    raise osv.except_osv(('Perhatian !'), ("Kolom amount harus diisi dengan angka saja, tidak boleh aja huruf!"))

            if not amount or amount <= 0:
                raise osv.except_osv(('Perhatian !'), ("Kolom amount tidak boleh kosong dan harus lebih besar dari nol!"))

            move_line_id = False
            for move_line in res_titipan_line:
                if move_line['amount'] >= amount:
                    move_line_id = move_line['line']
                    move_line['amount'] -= amount
                    break
            if not move_line_id:
                raise osv.except_osv(('Perhatian !'), ("Saldo customer deposit tidak cukup, mohon cek kembali amount di file csv anda!"))
            val = {
                'lot_id': lot_id and lot_id.id or False,
                'amount': amount,
                'alokasi_id': id_alokasi,
                'partner_id': partner_id.id,
                'branch_id': branch_id.id,
                'division': 'Unit',
                'titipan_line_id': move_line_id.id,
                'open_balance': move_line_id.fake_balance,
                'open_balance_show': move_line_id.fake_balance,
                'description': partner_id.name,
            }
            vals.append(val)
            
        for val in vals :    
            alokasi_line_id = self.pool.get("dym.alokasi.titipan.line").create(cr, uid, val)    
            alokasi_line = self.pool.get("dym.alokasi.titipan.line").browse(cr, uid, alokasi_line_id)
            amount = alokasi_line.amount
            branch_config_id = self.pool.get('dym.branch.config').search(cr,uid,[('branch_id','=',alokasi_line.branch_id.id)], limit =1)
            branch_config = self.pool.get('dym.branch.config').browse(cr,uid,branch_config_id)
            domain = [('account_id','=', branch_config.dealer_so_journal_pelunasan_id.default_debit_account_id.id),('partner_id','=',alokasi_line.partner_id.id),('reconcile_id','=', False),('debit','!=',0),'|',('ref','ilike','NDE-'),('ref','ilike','DSM-')]
            move_line_ar_id = self.pool.get('account.move.line').search(cr,uid,domain)
            amount_ar = 0
            for move_line_ar in self.pool.get('account.move.line').browse(cr,uid,move_line_ar_id,context=context):
                amount_ar = move_line_ar.debit if move_line_ar.fake_balance >= move_line_ar.debit else move_line_ar.fake_balance
                break
            if amount_ar != amount:
                if not alokasi_line.alokasi_id.force_alocate:
                    if alokasi_line.alokasi_id.log_import:
                        alokasi_line.alokasi_id.write({'log_import':str(alokasi_line.alokasi_id.log_import) + "\n" +"Customer %s nominal tidak sesuai (AR: %s, AMOUNT CSV: %s)"%(alokasi_line.partner_id.name_get()[0][1], amount_ar, amount)})             
                        continue
                    else:
                        alokasi_line.alokasi_id.write({'log_import': "Customer %s nominal tidak sesuai (AR: %s, AMOUNT CSV: %s)"%(alokasi_line.partner_id.name_get()[0][1], amount_ar, amount)})             
                        continue   