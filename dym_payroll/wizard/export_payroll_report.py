from openerp.exceptions import Warning as UserError, RedirectWarning
from openerp import api, fields, models, tools, _
import openerp
import base64
import csv
import cStringIO
import time
from datetime import datetime, date

import json

class ExportPayrollReport(models.TransientModel):
    _name = 'export.payroll.report'
    _description = 'Export Payroll Report'

    @api.multi
    def _get_account_ids(self):
        ctx = self._context
        account_ids = []
        if 'active_id' in ctx:
            payroll_obj = self.env['dym.payslip.run']
            payroll = payroll_obj.browse(ctx['active_id'])
            for slip in payroll.slip_ids:
                account_ids.extend([line.account_id.id for line in slip.line_ids if line.account_id.type == 'payable'])
            account_ids = list(set(account_ids))
        return [('id','in',account_ids)]

    @api.multi
    def _get_partner_ids(self):
        ctx = self._context
        partner_ids = []
        if 'active_id' in ctx:
            payroll_obj = self.env['dym.payslip.run']
            payroll = payroll_obj.browse(ctx['active_id'])
            for slip in payroll.slip_ids:
                partner_ids.extend([line.partner_id.id for line in slip.line_ids])
            partner_ids = list(set(partner_ids))
        return [('id','in',partner_ids)]

    payslip_run_id = fields.Many2one('dym.payslip.run', string='Payslip Batches', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date_start = fields.Date(string='Date From', readonly=True)
    date_end = fields.Date(string='Date To', readonly=True)
    account_id = fields.Many2one('account.account','Account', domain=_get_account_ids)
    partner_id = fields.Many2one('res.partner', 'Partner', domain=_get_partner_ids)
    line_ids = fields.One2many('export.payroll.line.report', 'export_id', string="Export Line")
    print_detail = fields.Boolean('Print Detail')

    @api.model
    def default_get(self, fields):
        ctx = self._context
        if ctx is None: ctx = {}
        res = super(ExportPayrollReport, self).default_get(fields)
        transfer_ids = ctx.get('active_ids', [])
        active_model = ctx.get('active_model')

        payslip = self.env['dym.payslip.run'].search([('id','=',ctx['active_id'])])
        res.update({
            'payslip_run_id': payslip.id,
            'company_id': payslip.company_id.id,
            'date_start': payslip.date_start,
            'date_end': payslip.date_end,
        })
        return res

    @api.onchange('account_id')
    def onchange_account(self):
        dom = {}
        ctx = self._context
        payslip = self.env['dym.payslip.run'].search([('id','=',ctx['active_id'])])
        slip_line_obj = self.env['dym.payslip.line']
        slip_line = slip_line_obj.search([('slip_id','=',payslip.slip_ids.id),('account_id','=',self.account_id.id)])
        partner_ids = [x.partner_id.id for x in slip_line]
        dom['partner_id'] = [('id','in',partner_ids)]
        if partner_ids:
            self.partner_id = partner_ids[0]
        return {'domain':dom}

    @api.multi
    def print_report(self):
        ctx = self._context
        if 'active_id' in ctx:
            payslip = self.env['dym.payslip.run'].search([('id','=',ctx['active_id'])])
            datas = {
                'ids': [payslip.id],
                'model': ctx['active_model'],
                'form': payslip.id,
                'context': ctx,
            }
            account_ids = []
            # partner_ids = []
            for ln in self.line_ids:
                account_ids.append(ln.account_id.id)
                # partner_ids.append(ln.partner_id.id)

            datas['account_ids'] = account_ids
            datas['partner_id'] = self.partner_id.id
            datas['print_detail'] = self.print_detail
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'dym_payroll.report_payroll_template',
            'datas': datas,
        }

class ExportPayrollLineReport(models.TransientModel):
    _name = 'export.payroll.line.report'
    _description = 'Export Payroll Line Report'

    # @api.multi
    # def _get_account_ids(self):
    #     ctx = self._context
    #     account_ids = []
    #     if 'active_id' in ctx:
    #         payroll_obj = self.env['dym.payslip.run']
    #         payroll = payroll_obj.browse(ctx['active_id'])
    #         for slip in payroll.slip_ids:
    #             account_ids.extend([line.account_id.id for line in slip.line_ids if line.account_id.type == 'payable'])
    #         account_ids = list(set(account_ids))
    #     return [('id','in',account_ids)]

    # @api.multi
    # def _get_account_ids(self):
    #     ctx = self._context
    #     account_ids = []
    #     if 'active_id' in ctx:
    #         payroll_obj = self.env['dym.payslip.run']
    #         payslip_line_obj = self.env['dym.payslip.line']
    #         payroll = payroll_obj.browse(ctx['active_id'])
    #         for slip in payroll.slip_ids:
    #             # account_ids.extend([line.account_id.id for line in slip.line_ids if line.account_id.type == 'payable' and line.partner_id.id == self.export_id.partner_id.id])
    #             account_ids.extend([line.account_id.id for line in payslip_line_obj.search([('slip_id','=',slip.id),('partner_id','=',self.export_id.partner_id.id)]) if line.account_id.type == 'payable'])
    #         account_ids = list(set(account_ids))
    #     return [('id','in',account_ids)]

    export_id = fields.Many2one('export.payroll.report')
    account_id = fields.Many2one('account.account','Account')
    partner_id = fields.Many2one('res.partner', 'Partner')

    # @api.onchange('account_id')
    # def onchange_account(self):
    #     dom = {}
    #     ctx = self._context
    #     payslip = self.env['dym.payslip.run'].search([('id','=',ctx['payslip_run_id'])])
    #     slip_line_obj = self.env['dym.payslip.line']
    #     slip_line = slip_line_obj.search([('slip_id','=',payslip.slip_ids.id),('account_id','=',self.account_id.id)])
    #     partner_ids = [x.partner_id.id for x in slip_line]
    #     dom['partner_id'] = [('id','in',partner_ids)]
    #     if partner_ids:
    #         self.partner_id = partner_ids[0]
    #     return {'domain':dom}

    @api.onchange('account_id')
    def onchange_account(self):
        dom = {}
        ctx = self._context
        account_ids = []
        payroll_obj = self.env['dym.payslip.run']
        payslip_line_obj = self.env['dym.payslip.line']
        payroll = payroll_obj.browse(ctx['payslip_run_id'])
        for slip in payroll.slip_ids:
            account_ids.extend([line.account_id.id for line in payslip_line_obj.search([('slip_id','=',slip.id),('partner_id','=',self.export_id.partner_id.id)]) if line.account_id.type == 'payable'])
        account_ids = list(set(account_ids))
        dom['account_id'] = [('id','in',account_ids)]
        return {'domain':dom}
        
class payroll_report(models.AbstractModel):
    _name = 'report.dym_payroll.report_payroll_template'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        AccountAccount = self.env['account.account']
        AccountPeriod = self.env['account.period']
        PayrollDueDate = self.env['dym.payroll.duedate']
        PayrollDueDateLine = self.env['dym.payroll.duedate.line']

        report = report_obj._get_report_from_name('dym_payroll.report_payroll_template')
        data_obj = self.env[report.model]
        data_tran = data_obj.browse(docids)
        account_ids = AccountAccount.browse(list(set(data['account_ids'])))

        period_id = AccountPeriod.search([('company_id','=',data_tran.company_id.id),('date_start','<=',data_tran.date_start),('date_stop','>=',data_tran.date_end)])
        payroll_date_id = PayrollDueDate.search([('company_id','=',data_tran.company_id.id),('period_id','=',period_id.id)])
        payroll_date_line_id = PayrollDueDateLine.search([('payroll_date_id','=',payroll_date_id.id),('partner_id','=',data['partner_id'])])

        docargs = {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': data_tran,
            'payroll_date': payroll_date_line_id,
            'partner_id': data['partner_id'],
            'account_ids': account_ids,
        }
        if data['print_detail']:
            return report_obj.render('dym_payroll.report_payroll_detail_template', docargs)
        else:
            return report_obj.render('dym_payroll.report_payroll_template', docargs)