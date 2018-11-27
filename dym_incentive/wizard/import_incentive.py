
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp.addons.dym_base import DIVISION_SELECTION
from openerp import api, fields, models, tools, _
import base64
import csv
import cStringIO

import json

class ImportIncentive(models.TransientModel):
    _name = 'import.incentive'
    _description = 'Import Incentive'

    data = fields.Binary('File', required=True)
    name = fields.Char('Filename')
    delimeter = fields.Char('Delimeter', default=',', help='Default delimeter is ","')
    company_id = fields.Many2one('res.company', string='Company')

    @api.model
    def default_get(self, fields_list):
        res = super(ImportIncentive, self).default_get(fields_list)
        ctx = self._context        
        if 'active_id' in ctx:
            incentive_obj = self.env['dym.incentive.batch.import']
            incentive = incentive_obj.browse(ctx['active_id'])
            res['company_id'] = incentive.company_id.id
        return res

    @api.one
    def action_import(self):
        ctx = self._context
        active_ids = ctx.get('active_ids',False)
        active_model = ctx.get('active_model',False)
        batch_id = self.env['dym.incentive.batch.import'].browse(active_ids)
        incentive_obj = self.env['dym.incentive.batch.import']
        
        if 'active_id' in ctx:
            incentive = incentive_obj.browse(ctx['active_id'])
        if not self.data:
            raise exceptions.Warning(_("You need to select a file!"))

        IncentiveAllocation = self.env['dym.incentive.allocation']
        IncentiveAllocationLine = self.env['dym.incentive.allocation.line']
        Lot = self.env['stock.production.lot']
        Move = self.env['account.move']

        finance_companies = self.env['res.partner'].search_read([('finance_company','=',True)],['default_code','name'])
        finances = dict([(c['default_code'],c['id']) for c in finance_companies])
        finance_ids = [c['id'] for c in finance_companies]

        divisions = [d[0] for d in DIVISION_SELECTION]

        companies = self.env['res.company'].search_read([],['code'])
        companies = dict([(c['code'],c['id']) for c in companies])

        branches = self.env['dym.branch'].search_read([],['code'])
        branches = dict([(b['code'],b['id']) for b in branches])

        accounts = self.env['account.account'].search_read([],['code'])
        accounts = dict([(a['code'],a['id']) for a in accounts])

        data = base64.b64decode(self.data)
        file_input = cStringIO.StringIO(data)
        file_input.seek(0)
        reader_info = []
        if self.delimeter:
            delimeter = str(self.delimeter)
        else:
            delimeter = ','

        reader = csv.reader(file_input, delimiter=delimeter,
                            lineterminator='\r\n')
        try:
            reader_info.extend(reader)
        except Exception:
            raise exceptions.Warning(_("Not a valid file!"))

        if len(reader_info[0])==1:
            raise UserError(_("Periksa kembali delimiter yang digunakan pada file yang Anda import, mungkin bukan ( %s )!" % (delimeter)))

        keys = reader_info[0]
        del reader_info[0]
        values = {}

        incentives = {}
        n = 0
        for i in range(len(reader_info)):
            n += 1

            field = reader_info[i]
            values = dict(zip(keys, field))

            if not 'COMPANY' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom COMPANY.'))
            if not 'FBRANCH' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom FBRANCH.'))
            if not 'TBRANCH' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom TBRANCH.'))
            if not 'FDIVISION' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom FDIVISION.'))
            if not 'TDIVISION' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom TDIVISION.'))
            if not 'FINANCE' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom FINANCE.'))
            # if not 'PPN' in values:
            #     raise UserError(_('Data yang Anda import tidak memiliki kolom PPN.'))
            if not 'CDE' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom CDE.'))

            if not values['COMPANY'] in companies:                
                raise UserError(_('Company code "%s" is not found in the system.' % values['COMPANY']))
            if not values['FBRANCH'] in branches:
                raise UserError(_('Branch code "%s" is not found in the system.' % values['FBRANCH']))
            if not values['TBRANCH'] in branches:
                raise UserError(_('Branch code "%s" is not found in the system.' % values['TBRANCH']))
            if not values['FDIVISION'] in divisions:
                raise UserError(_('Division "%s" is not found in the system.' % values['FDIVISION']))
            if not values['TDIVISION'] in divisions:
                raise UserError(_('Division "%s" is not found in the system.' % values['TDIVISION']))
            if not values['FINANCE'] in finances:
                raise UserError(_('Finance code "%s" is not found in the system.' % values['FINANCE']))

            company_id = companies[values['COMPANY']]
            branch_id = branches[values['FBRANCH']]
            company = self.env['res.company'].browse([(company_id)])
            branch_fcode = '%s|%s' % (values['FBRANCH'],values['TBRANCH'])

            if not branch_fcode in incentives:
                incentives[branch_fcode] = []
            if values not in incentives[branch_fcode]:
                incentives[branch_fcode].append(values)

        for k,v in incentives.items():
            fbcode, tbcode = k.split('|')
            data = v[0]
            if not data['AMOUNT']:
                raise UserError(_('Amount pada baris data tidak boleh ada yang nilainya nol'))
            if not data['DPP']:
                raise UserError(_('DPP pada baris data tidak boleh ada yang nilainya nol'))
            if not 'FDIVISION' in data:
                raise UserError(_('Kolom FDIVISION pada baris data tidak boleh kosong'))
            if not 'TDIVISION' in data:
                raise UserError(_('Kolom TDIVISION pada baris data tidak boleh kosong'))

            try:
                data['AMOUNT'] = float(data['AMOUNT'])
            except:
                data['AMOUNT'] = float(data['AMOUNT'].replace(',',''))

            fbranch_id = branches[fbcode]
            tbranch_id = branches[tbcode]
            branch_config = self.env['dym.branch.config'].search([('branch_id','=',fbranch_id)])
            journal_id = branch_config.dym_incentive_allocation_journal
            if not journal_id:
                raise UserError(_('Jurnal insentif di cabang %s tidak ditemukan, silahkan atur di menu Branch Config, isi kolom: "Journal Incentive Allocation" dengan jurnal yang sesuai' % branch_config.branch_id.name))

            line_ids = []

            for line in v:
                lot_id = Lot.search([('name','=',line['NOSIN']),('branch_id','=',tbranch_id)])
                move_line_id = False
                if line['CDE']!='TOCREATE':
                    move_id = Move.search([('name','=',line['CDE'])])
                    if not move_id:
                        raise UserError(_('Journal %s tidak ditemukan, mohon periksa kembali data yang Anda import!' % (line['CDE'])))
                    move_line_id = move_id.line_id.filtered(lambda r:r.fake_balance>0 and r.account_id.type=='payable')
                    if not move_line_id:
                        raise UserError(_('Baris journal %s dengan tipe akun "payable" dan yang saldonya cukup tidak ditemukan, mohon periksa kembali data yang Anda import!' % (line['CDE'])))
                val = {
                    'amount':line['AMOUNT'],
                    'tax_base':line['DPP'],
                    'partner_id':finances[line['FINANCE']],
                    'branch_id':branch_id,
                    'division':'Finance',
                    'description': batch_id.name,
                }
                if lot_id:
                    val.update({
                        'lot_id':lot_id.id,
                    })                    
                if move_line_id:
                    val.update({
                        'titipan_line_id':move_line_id.id,
                        'open_balance':move_line_id.fake_balance,
                        'open_balance_show':move_line_id.fake_balance,
                    })
                line_ids.append((0,0,val))
            incentive_alloc = {
                'batch_id': batch_id.id,
                'branch_id': fbranch_id,
                'division': data['FDIVISION'],
                'inter_branch_id': tbranch_id,
                'inter_division': data['TDIVISION'],
                'partner_id': finances[data['FINANCE']],
                'journal_id': journal_id.id,
                'date': batch_id.date,
                'value_date': batch_id.value_date,
                'approval_state': 'b',
                'account_id': journal_id.default_credit_account_id.id,
                'memo': k,
                'line_ids': line_ids,
            }
            incentive_alloc_id = IncentiveAllocation.search([('memo','=',k),('batch_id','=',batch_id.id),('date','=',batch_id.value_date)])
            if not incentive_alloc_id:
                IncentiveAllocation.create(incentive_alloc)

