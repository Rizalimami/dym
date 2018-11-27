
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp.addons.dym_base import DIVISION_SELECTION
from openerp.addons.dym_insurance.models.insurance_batch_import import INSURANCE_TYPES
from openerp import api, fields, models, tools, _
import base64
import csv
import cStringIO
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

import json

class ImportInsurance(models.TransientModel):
    _name = 'import.insurance'
    _description = 'Import Insurance'

    data = fields.Binary('File', required=True)
    name = fields.Char('Filename')
    delimeter = fields.Char('Delimeter', default=',', help='Default delimeter is ","')
    company_id = fields.Many2one('res.company', string='Company')

    @api.model
    def default_get(self, fields_list):
        res = super(ImportInsurance, self).default_get(fields_list)
        ctx = self._context
        ii_obj = False
        if 'active_id' in ctx:
            import_insurance_obj = self.env['dym.insurance.batch.import']
            ii_obj = import_insurance_obj.browse(ctx['active_id'])
            res['company_id'] = ii_obj.company_id.id

        if ii_obj and not all([ii_obj.date_start,ii_obj.date_end]):
            UserError(_('Mohon Lengkapi data sebelum import !'))

        print "ii_obj=============",ii_obj


        a = datetime.strptime(ii_obj.date_start, DEFAULT_SERVER_DATE_FORMAT)
        b = datetime.strptime(ii_obj.date_end, DEFAULT_SERVER_DATE_FORMAT)
        delta = b - a
        print "##############-",delta.days # that's it

        return res

    @api.one
    def action_import(self):
        ctx = self._context
        active_ids = ctx.get('active_ids',False)
        active_model = ctx.get('active_model',False)
        batch_id = self.env['dym.insurance.batch.import'].browse(active_ids)
        import_insurance_obj = self.env['dym.insurance.batch.import']
        
        if 'active_id' in ctx:
            ii_obj = import_insurance_obj.browse(ctx['active_id'])
        if not self.data:
            raise exceptions.Warning(_("You need to select a file!"))

        if not ii_obj.company_id:
            raise exceptions.Warning(_("Please select company to continue !"))

        Branch = self.env['dym.branch']
        insurances = self.env['res.partner'].search_read([('insurance_company','=',True)],['default_code','name'])
        insurance_companies = dict([(c['default_code'],c['id']) for c in insurances])
        insurance_ids = [c['id'] for c in insurances]
        divisions = [d[0] for d in DIVISION_SELECTION]
        branches = self.env['dym.branch'].search_read([('company_id','=',ii_obj.company_id.id)],['code'])
        branches = dict([(b['code'],b['id']) for b in branches])
        types = [i[1] for i in INSURANCE_TYPES]

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

        ii_objs = {}
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
            if not 'PARTNER' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom PARTNER.'))
            if not 'TYPE' in values:
                raise UserError(_('Data yang Anda import tidak memiliki kolom TYPE.'))

            if values['COMPANY'] != ii_obj.company_id.code:                
                raise UserError(_('Wrong company code "%s"' % values['COMPANY']))
            if not values['BRANCH'] in branches:
                raise UserError(_('Branch code "%s" is not found in the system.' % values['BRANCH']))
            if not values['DIVISION'] in divisions:
                raise UserError(_('Division "%s" is not found in the system.' % values['DIVISION']))
            if not values['PARTNER'] in insurance_companies:
                raise UserError(_('Main Dealer code "%s" is not found in the system.' % values['PARTNER']))

            insurance_type = values['TYPE']
            print "------------>",types
            if not insurance_type in types:
                raise UserError(_('Type "%s" is not found in the system.' % values['TYPE']))

            branch_id = Branch.browse([branches[values['BRANCH']]])
            name = '%s cabang %s' % (ii_obj.memo,branch_id.name)
            try:
                values['AMOUNT'] = float(values['AMOUNT'])
            except:
                values['AMOUNT'] = float(values['AMOUNT'].replace(',',''))

            categ_id = self.env['product.category'].search([('name','=',values['DIVISION'])])
            if not categ_id:
                raise UserError(_('Product category "%s" is not found in the system.' % values['DIVISION']))

            template_id = self.env['product.template'].search([('name','ilike',values['TYPE'])])
            if not template_id:
                raise UserError(_('Product template "%s" is not found in the system.' % values['TYPE']))

            template_id = self.env['product.template'].search([('name','ilike',values['TYPE'])])
            if not template_id:
                raise UserError(_('Product template "%s" is not found in the system.' % values['TYPE']))

            product_id = self.env['product.product'].search([('product_tmpl_id','=',template_id.id),('name','ilike',values['TYPE'])])
            if not product_id:
                raise UserError(_('Product variant "%s" is not found in the system.' % values['TYPE']))

            val = {
                'name': product_id.name,
                'inter_branch_id': branch_id.id,
                'inter_division': values['DIVISION'],
                'price_unit': values['AMOUNT'],
                'type': insurance_type,
                'categ_id': categ_id.id,
                'template_id': template_id.id,
                'product_id': product_id.id,
                'product_uom': product_id.uom_id.id,
            }
            line_ids.append((0,0,val))

        ii_obj.write({
            'line_ids': line_ids, 
        })

        # self.write({'line_ids':line_ids})

