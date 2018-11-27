import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
from lxml import etree
import cStringIO
import StringIO
import xlwt
import base64

class dym_report_intercompany(models.TransientModel):
    _name = 'dym.report.intercompany'

    period_id = fields.Many2one('account.period','Period', domain=[('company_id.code','=','CON')], required=True)
    journal_state = fields.Selection([('all','All State'),('posted','Posted')],'Journal State', required=True)
    name = fields.Char('File Name')
    data_file = fields.Binary('File')

    @api.multi
    def eksport_excel(self):
        data_left = [] 
        data_right = []
        uniq_list = []
        obj_consol = self.env['account.move.consol']
        obj_intercom = self.env['dym.intercompany.ref']
        book = xlwt.Workbook()
        sheet = book.add_sheet("Intercompany Report")
        now = datetime.now()
        style = xlwt.easyxf('font: bold 1;')
        style_header = xlwt.easyxf('font: bold 1, name Calibri, height 210; pattern: pattern solid, fore_colour yellow;')

        header = ['Source','Date','Transaction 1', 'Branch 1', 'Transaction 2', 'Branch 2', 'Ref Intercompany', 'Account 1', 'Debit', 'Account 2', 'Credit'] 
        account_left_list = [x.account_left_id.id for x in self.period_id.company_id.account_report_intercom_line]
        account_right_list = [x.account_right_id.id for x in self.period_id.company_id.account_report_intercom_line]
        if self.journal_state == 'posted':    
            consol_search = obj_consol.search([('period_id','=',self.period_id.id),('state','=','posted'),('journal_id','=',self.period_id.company_id.journal_consolidate_multi_company_id.id)])
        else:
            consol_search = obj_consol.search([('period_id','=',self.period_id.id),('journal_id','=',self.period_id.company_id.journal_consolidate_multi_company_id.id)])

        if consol_search:
            for consol in consol_search:
                for line in consol.line_id:
                    if line.account_id.id in account_left_list:
                        intercom = line._get_intercom_ref_id()
                        data_left.append({
                            'Origin' : line.move_id.name,
                            'Transaction 1' : line.consol_entry.ref or line.name,
                            'Ref Intercompany': intercom or line.intercom_ref or '' ,
                            'Debit': line.debit,
                            'Credit': line.credit,
                            'Date': line.date,
                            'Branch 1': line.branch_id.name,
                            'Account 1': line.account_id.code +' '+line.account_id.name,
                            'account_id': line.account_id.id,
                            'analytic_account_id': line.analytic_account_id.id,  
                            }) 

                    if line.account_id.id in account_right_list:
                        intercom = line._get_intercom_ref_id()
                        data_right.append({
                            'Origin' : line.move_id.name,
                            'Transaction 2' : line.consol_entry.ref or line.name,
                            'Ref Intercompany': intercom or line.intercom_ref or '',
                            'Debit': line.debit,
                            'Credit': line.credit,
                            'Date': line.date,
                            'Branch 2': line.branch_id.name,
                            'Account 2': line.account_id.code +' '+line.account_id.name,    
                            'account_id': line.account_id.id,
                            'analytic_account_id': line.analytic_account_id.id,  
                            }) 

        for line in data_left:
            uniq_list.append(line)

        for left in data_left:
            for right in data_right:
                if left['Ref Intercompany'] == right['Ref Intercompany']:
                    if left['Ref Intercompany'] and right['Ref Intercompany']:
                        data_left[data_left.index(left)]['Transaction 2'] = right['Transaction 2']
                        data_left[data_left.index(left)]['Branch 2'] = right['Branch 2']
                        data_left[data_left.index(left)]['Account 2'] = right['Account 2']
                        if not left['Debit']:
                            data_left[data_left.index(left)]['Debit'] = right['Debit']
                        if not left['Credit']:
                            data_left[data_left.index(left)]['Credit'] = right['Credit']             
                else:
                    if right not in uniq_list:
                        uniq_list.append(right)

        no = 0; max_len = {}
        for line in uniq_list:
            no += 1
            col = -1
            for i in header:
                col += 1
                if i in line:
                    sheet.write(no, col, line[i])
                    if col not in max_len:
                        max_len[col] = len(str(line[i]))
                    else:
                        if max_len[col] < len(str(line[i])):
                            max_len[col] = len(str(line[i]))
                    sheet.col(col).width = (max_len[col]) * 320

        colh = -1
        for x in header:
            colh += 1 
            sheet.write(0, colh, x)

        filename = 'Intercompany_Report_on_%s.xls' % (now.strftime("%Y-%m-%d %H:%M:%S"))        
        file_data = StringIO.StringIO()
        book.save(file_data)
        out = base64.encodestring(file_data.getvalue())
        self.write({'data_file':out,'name': filename})
   
        view_rec = self.env['ir.model.data'].get_object_reference('dym_journal_elimination', 'view_report_intercompany_wizard')
        view_id = view_rec[1] or False

        return {
            'view_type': 'form',
            'view_id': [view_id],
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'dym.report.intercompany',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }



