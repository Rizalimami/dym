
from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp import api, fields, models, tools, _
import base64
import csv
import cStringIO

import json

class ImportPayroll(models.TransientModel):
    _name = 'import.payroll'
    _description = 'Import Payroll'

    data = fields.Binary('File', required=True)
    name = fields.Char('Filename')
    delimeter = fields.Char('Delimeter', default=',',
                            help='Default delimeter is ","')
    company_id = fields.Many2one('res.company', string='Company')

    @api.model
    def default_get(self, fields_list):
        res = super(ImportPayroll, self).default_get(fields_list)
        ctx = self._context        
        if 'active_id' in ctx:
            payroll_obj = self.env['dym.payslip.run']
            payroll = payroll_obj.browse(ctx['active_id'])
            res['company_id'] = payroll.company_id.id
        return res

    @api.one
    def action_import(self):
        ctx = self._context
        payroll_obj = self.env['dym.payslip.run']
        branch_obj = self.env['dym.branch']
        if 'active_id' in ctx:
            payroll = payroll_obj.browse(ctx['active_id'])
        if not self.data:
            raise Warning(_("You need to select a file!"))

        Payslip = self.env['dym.payslip']
        PayrollDate = self.env['dym.payroll.duedate']
        PayslipLine = self.env['dym.payslip.line']
        PayslipAnalytic = self.env['dym.payslip.analytic']

        # Get master data
        companies = self.env['res.company'].search_read([],['payroll_company'])
        companies = dict([(c['payroll_company'],c['id']) for c in companies])

        branches = self.env['dym.branch'].search_read([],['payroll_branch'])
        branches = dict([(b['payroll_branch'],b['id']) for b in branches])

        accounts = self.env['account.account'].search_read([],['code'])
        accounts = dict([(a['code'],a['id']) for a in accounts])

        business_units = {}
        for bu in self.env['account.analytic.account'].search_read([('segmen','=',2),('type','=','normal')],['code','bisnis_unit']):
            if bu['code'] not in business_units and bu['bisnis_unit']:
                business_units[bu['code']] = bu['bisnis_unit'][1]

        cost_centers = {}
        for cc in self.env['account.analytic.account'].search_read([('segmen','=',4),('type','=','normal')],['code','cost_center']):
            if cc['code'] not in cost_centers and cc['cost_center']:
                cost_centers[cc['code']] = cc['cost_center']

        # Decode the file data
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
            raise UserError(_("Not a valid file!"))
        keys = reader_info[0]
        # check if keys exist
        # if not isinstance(keys, list) or ('code' not in keys or
        #                                   'quantity' not in keys):
        #     raise exceptions.Warning(
        #         _("Not 'code' or 'quantity' keys found"))
        del reader_info[0]
        values = {}

        actual_date = fields.Date.today()
        payroll_name = self.name + ' - ' + actual_date
        
        slip_seq = 0
        line_seq = 0
        analytic_seq = 0
        n = 0

        PayrollDateLine = self.env['dym.payroll.duedate.line']
        period_id = self.env['account.period'].search([('company_id','=',payroll.company_id.id),('date_start','<=',payroll.date_start),('date_stop','>=',payroll.date_end)])
        payroll_date_id = PayrollDate.search([('company_id','=',payroll.company_id.id),('period_id','=',period_id.id)])

        if not payroll_date_id:
            payroll_date_id = PayrollDate.create({
                'company_id': payroll.company_id.id,
                'period_id': period_id.id
            })

        for i in range(len(reader_info)):
            n += 1

            field = reader_info[i]
            values = dict(zip(keys, field))
            set_field = list(set(field))

            if len(set_field) > 1:

                if not values['COMPANY'] in companies:                
                    raise UserError(_('Company code "%s" is not found in the system.' % values['COMPANY']))
                if not values['ACCOUNT'] in accounts:
                    raise UserError(_('Account code "%s" is not found in the system.' % values['ACCOUNT']))
                if not values['BRANCH'] in branches:
                    raise UserError(_('Branch code "%s" is not found in the system.' % values['BRANCH']))
                if not values['UNIT_BISNIS']:
                    values['UNIT_BISNIS'] = '000'
                if values['UNIT_BISNIS'] and not values['UNIT_BISNIS'] in business_units:
                    raise UserError(_('Business Unit code "%s" is not found in the system.' % values['UNIT_BISNIS']))
                if not values['COST_CENTER']:
                    values['COST_CENTER'] = '00'
                if values['COST_CENTER'] and not values['COST_CENTER'] in cost_centers:
                    raise UserError(_('Cost Center code "%s" is not found in the system.' % values['COST_CENTER']))

                company_id = companies[values['COMPANY']]
                branch_id = branches[values['BRANCH']]
                business_unit = business_units[values['UNIT_BISNIS']]
                cost_center = cost_centers[values['COST_CENTER']]
                division = values['DIVISION']
                
                company = self.env['res.company'].browse([(company_id)])
                ho_branch_id = branch_obj.search([('company_id','=',company.id),('code','=',company.code)])
                branch_id = branch_obj.search([('company_id','=',company.id),('payroll_branch','=',values['BRANCH'])])
                if not branch_id:
                    raise UserError(_('Branch code "%s" is not found in the system.' % values['BRANCH']))

                account_id = self.env['account.account'].search([('company_id','=',company_id),('code','=',values['ACCOUNT'])])
                journal_id = self.env['account.journal'].search([('company_id','=',company_id),('name','ilike','Jurnal Pengakuan Biaya')])

                # if 'PARTNER' in values and values['PARTNER']:
                #     partner_id = self.env['res.partner'].search([('default_code','=',values['PARTNER'])])
                #     if not partner_id:
                #         raise UserError(_('Partner code "%s" is not found in the system.' % values['PARTNER']))
                # else:
                #     partner_id = self.env['res.company'].browse([company_id]).partner_id
                
                partner_id = self.env['res.company'].browse([company_id]).partner_id
                acc_partner_id = self.env['account.account.partner'].search([('account_id','=',account_id.id),('branch_id','=',branch_id.id)])
                if acc_partner_id:
                    partner_id = acc_partner_id.partner_id
                analytic_1, analytic_2, analytic_3, analytic_4 = self.env['account.analytic.account'].get_analytical(branch_id.id,business_unit,False,4,cost_center)
                
                db_amount = float(values['DEBIT'])
                cr_amount = float(values['CREDIT'])

                amount = 0
                if db_amount>0:
                    amount = db_amount
                else:
                    amount = -1 * cr_amount

                if account_id.type == 'payable':
                    payroll_date_line_id = PayrollDateLine.search([('payroll_date_id','=',payroll_date_id.id),('partner_id','=',partner_id.id)])
                    if not payroll_date_line_id:
                        payroll_date_line_id = PayrollDateLine.create({
                            'payroll_date_id': payroll_date_id.id,
                            'partner_id': partner_id.id
                        })

                slip_id = Payslip.search([
                    ('payslip_run_id','=',payroll.id),
                    ('company_id','=',company_id),
                    ('branch_id','=',ho_branch_id.id),
                    ('division','=',division),
                    ('date_from','=',payroll.date_start),
                    ('date_to','=',payroll.date_end),
                ])
                if not slip_id:
                    slip_seq += 1
                    number = self.env['ir.sequence'].get_per_branch(ho_branch_id.id,'PRL', division=division)
                    description = values['KETERANGAN'] or '-'
                    dps_vals = {
                        'sequence': slip_seq,
                        'payslip_run_id': payroll.id,
                        'number': payroll.name,
                        'name': description,
                        'company_id': company_id,
                        'branch_id': ho_branch_id.id,
                        'partner_id': partner_id.id,
                        'division': division,
                        'journal_id': journal_id.id,
                        'date_from': payroll.date_start,
                        'date_to': payroll.date_end,
                        'state': payroll.state,
                    }
                    slip_id = Payslip.create(dps_vals)

                line_id = PayslipLine.search([
                    ('slip_id','=',slip_id.id),
                    ('company_id','=',company_id),
                    ('branch_id','=',branch_id.id),
                    ('division','=',division),
                    ('date_from','=',payroll.date_start),
                    ('date_to','=',payroll.date_end),
                    ('account_id','=',account_id.id),
                ])
                if not line_id:
                    line_seq += 1
                    dpl_vals = {
                        'sequence': line_seq,
                        'slip_id': slip_id.id,
                        'company_id': company_id,
                        'branch_id': branch_id.id,
                        'partner_id': partner_id.id,
                        'division': division,
                        'account_id': account_id.id,
                        'date_from': payroll.date_start,
                        'date_to': payroll.date_end,
                        'state': payroll.state,
                    }
                    line_id = PayslipLine.create(dpl_vals)

                analytic_seq += 1
                dpa_vals = {
                    'line_id': line_id.id,
                    'sequence': analytic_seq,
                    'company_id': company_id,
                    'branch_id': branch_id.id,
                    'division': division,
                    'account_id': account_id.id,
                    'analytic_id': analytic_4,
                    'amount': amount,
                    'date_from': payroll.date_start,
                    'date_to': payroll.date_end,
                    'state': payroll.state,
                }
                PayslipAnalytic.create(dpa_vals)

