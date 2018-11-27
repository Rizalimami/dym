
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp.addons.dym_base import DIVISION_SELECTION
from openerp import api, fields, models, tools, _
import base64
import csv
import cStringIO

import json

class ImportBlindBonus(models.TransientModel):
    _name = 'import.bb'
    _description = 'Import BlindBonus'

    data = fields.Binary('File', required=True)
    name = fields.Char('Filename')
    delimeter = fields.Char('Delimeter', default=',', help='Default delimeter is ","')
    company_id = fields.Many2one('res.company', string='Company')

    @api.model
    def default_get(self, fields_list):
        res = super(ImportBlindBonus, self).default_get(fields_list)
        ctx = self._context
        if 'active_id' in ctx:
            bb_obj = self.env['dym.bb.batch.import']
            bb = bb_obj.browse(ctx['active_id'])
            res['company_id'] = bb.company_id.id
        return res

    @api.one
    def action_import(self):
        ctx = self._context
        active_ids = ctx.get('active_ids',False)
        active_model = ctx.get('active_model',False)
        batch_id = self.env['dym.bb.batch.import'].browse(active_ids)
        bb_obj = self.env['dym.bb.batch.import']
        
        if 'active_id' in ctx:
            bb = bb_obj.browse(ctx['active_id'])
        if not self.data:
            raise exceptions.Warning(_("You need to select a file!"))

        if not bb.company_id:
            raise exceptions.Warning(_("Please select company to continue !"))

        Branch = self.env['dym.branch']
        mds = self.env['res.partner'].search_read([('principle','=',True)],['default_code','name'])
        mdealers = dict([(c['default_code'],c['id']) for c in mds])
        md_ids = [c['id'] for c in mds]
        divisions = [d[0] for d in DIVISION_SELECTION]
        branches = self.env['dym.branch'].search_read([('company_id','=',bb.company_id.id)],['code'])
        branches = dict([(b['code'],b['id']) for b in branches])
        types = ['unit','oli','part']

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

        bbs = {}
        line_ids = []
        n = 0
        for i in range(len(reader_info)):
            n += 1

            field = reader_info[i]
            values = dict(zip(keys, field))

            if not 'COMPANY' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom COMPANY.'))
            if not 'BRANCH' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom BRANCH.'))
            if not 'DIVISION' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom DIVISION.'))
            if not 'AMOUNT' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom AMOUNT.'))
            if not 'MD' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom MD.'))
            if not 'TYPE' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom TYPE.'))

            if values['COMPANY'] != bb.company_id.code:                
                raise UserError(_('Wrong company code "%s"' % values['COMPANY']))
            if not values['BRANCH'] in branches:
                raise UserError(_('Branch code "%s" is not found in the system.' % values['BRANCH']))
            if not values['DIVISION'] in divisions:
                raise UserError(_('Division "%s" is not found in the system.' % values['DIVISION']))
            if not values['MD'] in mdealers:
                raise UserError(_('Main Dealer code "%s" is not found in the system.' % values['MD']))

            bonus_type = values['TYPE'].lower()
            if not bonus_type in types:
                raise UserError(_('Type "%s" is not found in the system.' % values['TYPE']))

            branch_id = Branch.browse([branches[values['BRANCH']]])
            name = '%s cabang %s' % (bb.memo,branch_id.name)
            try:
                values['AMOUNT'] = float(values['AMOUNT'])
            except:
                values['AMOUNT'] = float(values['AMOUNT'].replace(',',''))
            val = {
                'name': name,
                'inter_branch_id': branch_id.id,
                'inter_division': values['DIVISION'],
                'partner_id': mdealers[values['MD']],
                'amount_dpp': values['AMOUNT'],
                'type': bonus_type,
            }
            line_ids.append((0,0,val))

        bb.write({
            'line_ids': line_ids, 
        })

        # self.write({'line_ids':line_ids})

