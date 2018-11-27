
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp.addons.dym_base import DIVISION_SELECTION
from openerp import api, fields, models, tools, _
import base64
import csv
import cStringIO

import json

class ImportMBD(models.TransientModel):
    _name = 'import.mbd'
    _description = 'Import MBD'

    data = fields.Binary('File', required=True)
    name = fields.Char('Filename')
    delimeter = fields.Char('Delimeter', default=',', help='Default delimeter is ","')
    company_id = fields.Many2one('res.company', string='Company')

    @api.model
    def default_get(self, fields_list):
        res = super(ImportMBD, self).default_get(fields_list)
        ctx = self._context        
        if 'active_id' in ctx:
            mbd_obj = self.env['dym.mbd.batch.import']
            mbd = mbd_obj.browse(ctx['active_id'])
            res['company_id'] = mbd.company_id.id
        return res

    @api.one
    def action_import(self):
        ctx = self._context
        active_ids = ctx.get('active_ids',False)
        active_model = ctx.get('active_model',False)
        batch_id = self.env['dym.mbd.batch.import'].browse(active_ids)
        mbd_obj = self.env['dym.mbd.batch.import']
        
        if 'active_id' in ctx:
            mbd = mbd_obj.browse(ctx['active_id'])
        if not self.data:
            raise exceptions.Warning(_("You need to select a file!"))

        MBDAllocation = self.env['dym.mbd.allocation']
        MBDAllocationLine = self.env['dym.mbd.allocation.line']
        Lot = self.env['stock.production.lot']
        Move = self.env['account.move']

        finance_companies = self.env['res.partner'].search_read([('finance_company','=',True)],['default_code','name'])
        finances = dict([(c['default_code'],c['id']) for c in finance_companies])
        finance_ids = [c['id'] for c in finance_companies]

        fbranches = self.env['dym.cabang.partner'].search_read([('partner_id','in',finance_ids)],['code','partner_id'])

        fbranches = dict([(c['code'],c['id']) for c in fbranches])

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

        mbds = {}
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
            if not 'FCODE' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom FCODE.'))
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
            if not values['FCODE'] in fbranches:
                raise UserError(_('Finance Branch "%s" is not found in the system.' % values['FCODE']))

            company_id = companies[values['COMPANY']]
            branch_id = branches[values['FBRANCH']]
            company = self.env['res.company'].browse([(company_id)])
            # ho_branch_id = self.env['dym.branch'].search([('company_id','=',company.id),('code','=',company.code)])
            branch_fcode = '%s|%s|%s' % (values['FCODE'],values['FBRANCH'],values['TBRANCH'])

            if not branch_fcode in mbds:
                mbds[branch_fcode] = []
            if values not in mbds[branch_fcode]:
                mbds[branch_fcode].append(values)

        internal_partners = self.env['res.partner'].search([('partner_type','in',['Afiliasi','Konsolidasi'])])
        for k,v in mbds.items():
            fcode, fbcode, tbcode = k.split('|')
            data = v[0]
            if not data['AMOUNT']:
                raise UserError(_('Amount pada baris data tidak boleh ada yang nilainya nol'))
            if not data['DPP']:
                raise UserError(_('DPP pada baris data tidak boleh ada yang nilainya nol'))
            if not 'FDIVISION' in data:
                raise UserError(_('Kolom FDIVISION pada baris data tidak boleh kosong'))
            if not 'TDIVISION' in data:
                raise UserError(_('Kolom TDIVISION pada baris data tidak boleh kosong'))
            fbranch_id = branches[fbcode]
            tbranch_id = branches[tbcode]
            branch_config = self.env['dym.branch.config'].search([('branch_id','=',fbranch_id)])
            journal_id = branch_config.dym_mbd_allocation_journal
            line_ids = []
            for line in v:
                lot_id = Lot.search([('state','!=','workshop'),('name','=',line['NOSIN']),'|',('customer_reserved','=',False),('customer_reserved','not in',internal_partners.ids)])
                move_id = Move.search([('name','=',line['CDE'])])
                if not move_id:
                    raise UserError(_('Journal %s tidak ditemukan, mohon periksa kembali data yang Anda import!' % (line['CDE'])))
                move_line_id = move_id.line_id.filtered(lambda r:r.fake_balance>0 and r.account_id.type=='payable')
                if not move_line_id:
                    raise UserError(_('Baris journal %s dengan tipe akun "payable" dan yang saldonya cukup tidak ditemukan, mohon periksa kembali data yang Anda import!' % (line['CDE'])))
                if len(lot_id)>1 and "NOKA" in line and line["NOKA"]:
                    lot_id = Lot.search([("name","=",line["NOSIN"]),("chassis_no","=",line["NOKA"])])
                val = {
                    'lot_id':lot_id.id,
                    'amount':line['AMOUNT'],
                    'tax_base':line['DPP'],
                    'partner_id':finances[line['FINANCE']],
                    'branch_id':branch_id,
                    'division':'Finance',
                    'titipan_line_id':move_line_id.id,
                    'open_balance':move_line_id.fake_balance,
                    'open_balance_show':move_line_id.fake_balance,
                    'description': batch_id.name,
                }
                line_ids.append((0,0,val))
            mbd_alloc = {
                'batch_id': batch_id.id,
                'branch_id': fbranch_id,
                'division': data['FDIVISION'],
                'inter_branch_id': tbranch_id,
                'inter_division': data['TDIVISION'],
                'partner_id': finances[data['FINANCE']],
                'partner_cabang_id': fbranches[data['FCODE']],
                'journal_id': journal_id.id,
                'date': batch_id.date_end,
                'value_date': batch_id.date_end,
                'approval_state': 'b',
                'account_id': journal_id.default_credit_account_id.id,
                'memo': k,
                'line_ids': line_ids,
            }
            mbd_alloc_id = MBDAllocation.search([('memo','=',k),('batch_id','=',batch_id.id),('date','=',batch_id.date_end)])
            if not mbd_alloc_id:
                MBDAllocation.create(mbd_alloc)

