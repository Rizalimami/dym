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


class dym_account_move_line_consol(models.Model):
    _inherit = 'account.move.line.consol'

    @api.model
    def _get_intercom_ref_id(self):
        for rec in self:
            obj_ir = self.env['dym.intercompany.ref']
            ir = False
            ref = False
            res = False

            if rec.consol_entry.ref:
                if 'POR-' in rec.consol_entry.ref:
                    ir = obj_ir.search([('name','=',rec.consol_entry.ref)])
                    if ir:
                        res = ir.name

                elif 'DSM-' in rec.consol_entry.ref:
                    ref = self.env['dealer.sale.order'].search([('name','=',rec.consol_entry.ref)])
                    if ref:
                        ir = obj_ir.search([('fres_id','=',ref.id)])
                        if ir:
                            res = ir.name

                elif 'SOR-' in rec.consol_entry.ref:
                    ref = self.env['dealer.sale.order'].search([('name','=',rec.consol_entry.ref)])
                    if ref:
                        ir = obj_ir.search([('fres_id','=',ref.id)])
                        if ir:
                            res = ir.name
            
            elif rec.consol_entry.model == 'account.voucher':
                reconcile = rec.consolidation_move_line_id.reconcile_id
                for line in reconcile.line_id:
                    if line.ref != self.consol_entry.ref:
                        if rec.consol_entry.ref:
                            if 'POR-' in rec.consol_entry.ref:
                                ir = obj_ir.search([('name','=',line.ref)])
                                if ir:
                                    res = ir.name
                                
                            elif 'DSM-' in rec.consol_entry.ref:
                                ref = self.env['dealer.sale.order'].search([('name','=',line.ref)])
                                if ref:
                                    ir = obj_ir.search([('fres_id','=',ref.id)])
                                    if ir:
                                        res = ir.name

                            elif 'SOR-' in rec.consol_entry.ref:
                                ref = self.env['sale.order'].search([('name','=',line.ref)])
                                if ref:
                                    ir = obj_ir.search([('fres_id','=',ref.id)])
                                    if ir:
                                        res = ir.name

                            elif 'LOA-' in rec.consol_entry.ref:
                                ref = self.env['dym.loan'].search([('name','=',rec.consol_entry.ref)])
                                if ref:
                                    if ref.loan_type == 'Pinjaman':
                                        rec.write({'intercom_ref': ref.name})
                                    elif ref.loan_type == 'Piutang':
                                        rec.write({'intercom_ref': ref.loan_id.name})   

                            elif 'TBK-' in rec.consol_entry.ref or 'TBM-' in rec.consol_entry.ref:
                                ref = self.env['account.voucher'].search([('name','=',rec.consol_entry.ref)])
                                if ref:
                                    if 'TBK-' in rec.consol_entry.ref:
                                        res = ref.name
                                    elif 'TBM-' in rec.consol_entry.ref:
                                        res = ref.intercom_ref_id.name   
         
            if 'LOA-' not in rec.consol_entry.ref:
                rec.write({'intercom_ref': res})     
        return res

    elimination_id = fields.Many2one('dym.journal.elimination','Journal Elimination')
    elimination_move_line_id = fields.Many2one('account.move.line.consol', string='Elimination Move Line', copy=False)
    eliminated = fields.Boolean('Eliminated', copy=False)
    eliminate_posted = fields.Boolean('Eliminate Posted', copy=False)
    elim_entry = fields.Many2one(related='elimination_move_line_id.consolidation_move_line_id.move_id', string='Journal Entry', readonly=True, store=True)
    consol_entry = fields.Many2one(related='consolidation_move_line_id.move_id', string='Journal Entry', readonly=True, store=True)
    partner_type = fields.Selection(related='partner_id.partner_type', string='Partner Type')
    is_intercom = fields.Boolean(related='account_id.is_intercom', string='Is Intercompany')
    intercom_ref = fields.Char('Intercompany Ref', readonly=True)
    # intercom_ref = fields.Many2one('dym.intercompany.ref','Intercompany Ref', readonly=True)

    @api.multi
    def view_entry(self):  
        return {
            'name': 'account.move.form',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'res_id': self.elim_entry.id or self.consol_entry.id
            }  

class dym_journal_elimination(models.Model):
    _name = 'dym.journal.elimination'
    _description = 'Journal Elimination (ALL COMPANY)'

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('confirm','Confirmed'),
        ('cancel','Cancelled')
    ]
                    
    @api.cr_uid_ids_context
    def get_group_company(self,cr,uid, ids, context=None):
        user_obj = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid)
        company = user_obj.company_id
        while company.parent_id:
            company = company.parent_id
        return company

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,SUPERUSER_ID,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
            
    branch_id = fields.Many2one('dym.branch', string='Branch Approval', required=True, default=_get_default_branch)
    division = fields.Selection([('Finance','Finance')], string='Division',default='Finance', required=True,change_default=True, select=True)
    name = fields.Char(string='No')
    date = fields.Date(string="Date",required=True,readonly=True, default=fields.Date.context_today)
    periode_id = fields.Many2one('account.period', required=True, string='Periode')
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    move_consol_ids = fields.Many2many('account.move.line.consol', 'move_consol_elim_rel', 'consol_line_id', 'elim_id', 'Journal Consolidation')
    move_id = fields.Many2one('account.move.consol', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line.consol',related='move_id.line_id',string='Journal Elimination', readonly=True)
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('dym.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    approval_state =  fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Reject')
    ],'Approval State', readonly=True,default='b')
    filename = fields.Char('Filename') 
    datafile = fields.Binary('Data File')
    move_diff_ids = fields.One2many('account.move.line.consol','elimination_id','Different Sale Journals')
    
    @api.onchange('periode_id')
    def fill_consol(self):
        domain = {}
        if self.periode_id:
            if self.periode_id.state == 'done':
                self.move_consol_ids = False
                raise osv.except_osv(('Perhatian !'), ("Period: %s sudah di close")%(self.periode_id.name))  
            company = self.get_group_company()
            period = self.periode_id
            date_start = datetime.strptime(period.date_start, DEFAULT_SERVER_DATE_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_stop = datetime.strptime(period.date_stop, DEFAULT_SERVER_DATE_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)  
            branch_period_ids = period.search([('company_id','!=',company.id),('date_start','=',period.date_start),('date_stop','=',period.date_stop)])
            branch_unconsolidated_ids = []
            if branch_period_ids:
                request = ("SELECT lx.branch_id as branch_id FROM account_move_line lx left join account_move mx on lx.move_id = mx.id left join account_period ax on mx.period_id = ax.id WHERE ax.id in %s and (lx.consolidate_posted = 'f' or  lx.consolidate_posted is null) and mx.state = 'posted' and lx.branch_id is not null group by lx.branch_id")
                params = (tuple(branch_period_ids.ids),)
                self._cr.execute(request, params)
                rows = self._cr.dictfetchall()
                branch_unconsolidated_ids = [row['branch_id'] for row in rows]

            # if branch_unconsolidated_ids:
            #     branch_unconsolidated = self.env['dym.branch'].browse(branch_unconsolidated_ids)
            #     self.move_consol_ids = False
            #     raise osv.except_osv(('Perhatian !'), ("Period: %s branch: %s belum di consolidate")%(period.name,', '.join(branch_unconsolidated.mapped('name')))) 

            # request = ("SELECT l.id as line_id FROM account_move_line_consol l left join account_move_consol m on l.move_id = m.id left join account_period a on m.period_id = a.id left join account_move_line lx on l.consolidation_move_line_id = lx.id WHERE lx.move_id in (select ly.move_id from account_move_line_consol lz left join res_partner p on p.id = lz.partner_id left join account_move_line ly on ly.id = lz.consolidation_move_line_id left join account_move_consol mz on mz.id = lz.move_id where p.partner_type = 'Konsolidasi' and lz.period_id = %s and (lz.eliminate_posted = 'f' or lz.eliminate_posted is null) and mz.state = 'posted' and lz.elimination_move_line_id is null) and a.id = %s and (l.eliminate_posted = 'f' or l.eliminate_posted is null) and m.state = 'posted' and l.elimination_move_line_id is null order by lx.move_id")
            where_account = " l.account_id in %s" % str(tuple([x.account_id.id for x in self.periode_id.company_id.account_elimination_line]))
            where_period = " l.period_id = %s" % str(self.periode_id.id)
            where_journal_type = " jx.type in ('cash','bank')"
            where_journal_jual = " jx.type in ('sale','sale_refund','purchase','purchase_refund')"
            contain = "intercompany"
            request = ("""SELECT l.id as line_id FROM account_move_line_consol l
                        left join account_move_line lx on l.consolidation_move_line_id = lx.id
                        left join account_journal jx on lx.journal_id = jx.id
                        WHERE %s  AND ((%s AND %s) OR (%s AND %s AND jx.name like '%%%%%s%%%%'))""" % (where_period,where_account,where_journal_type,where_account,where_journal_jual,contain)) 
            
            params = ((self.periode_id.id),(self.periode_id.id),)
            self._cr.execute(request, params)
            rows = self._cr.dictfetchall()
            line_ids = [row['line_id'] for row in rows]
            if not line_ids:
                self.move_consol_ids = False
                raise osv.except_osv(('Perhatian !'), ("Period: %s tidak ditemukan transaksi intercompany untuk dieliminasi")%(period.name)) 
            domain['move_consol_ids'] = [('id','in',line_ids)]
        else:
            self.move_consol_ids = False
            domain['move_consol_ids'] = [('id','=',0)]
        return {'domain':domain}

    @api.model
    def create(self,vals,context=None):
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'JEL', division=False) 
        vals['date'] = datetime.today() 
        res =  super(dym_journal_elimination, self).create(vals)  
        return res

    @api.multi
    def write(self,values,context=None):
        res =  super(dym_journal_elimination,self).write(values)
        return res

    @api.multi
    def generate_elimination(self):
        self.action_create_move_line_eliminate()
        if self.move_diff_ids:
            move = False
            for line in self.move_diff_ids:
                move = line.move_id
                line.write({'move_id':self.move_ids[0].move_id.id})
            move.unlink()

    @api.multi
    def action_create_move_line_eliminate(self):
        move_pool = self.env['account.move.consol']
        move_line_pool = self.env['account.move.line.consol']
        period_obj = self.env['account.period']
        company = self.get_group_company()
        journal_id = company.journal_eliminate_multi_company_id.id 
        if not company.journal_eliminate_multi_company_id:
            raise osv.except_osv(('Perhatian !'), ("Journal eliminasi multi company belum diisi di %s!")%(company.name)) 
        if self.periode_id.company_id != company:
            raise osv.except_osv(('Perhatian !'), ("Period yang diisi harus periode grup company")) 
        if self.periode_id.state == 'done':
            raise osv.except_osv(('Perhatian !'), ("Period: %s sudah di close")%(self.periode_id.state.name))  
        name = self.name
        date = time.strftime('%Y-%m-%d %H:%M:%S')
        partner_consol = self.move_consol_ids.mapped('partner_id').filtered(lambda r: r.partner_type != 'Konsolidasi')
        if partner_consol:
            raise osv.except_osv(_('Error!'), _('Partner %s bukan partner konsolidasi!.')%(', '.join(partner_consol.mapped('name'))))
        elim_posted = self.move_consol_ids.filtered(lambda r: r.eliminate_posted == True)
        if elim_posted:
            raise osv.except_osv(_('Error!'), _('Jurnal %s sudah di eliminasi!.')%(', '.join(elim_posted.mapped('consolidation_move_line_id.move_id.name'))))
        rows = self.move_consol_ids.read(['move_id', 'id',  'name',  'ref', 'account_id', 'credit', 'debit',  'branch_id',  'division', 'currency_id', 'product_id', 'product_uom_id', 'amount_currency', 'quantity', 'company_id', 'partner_id', 'analytic_account_id', 'tax_code_id', 'tax_amount'])
        eliminate_line = []
        eliminate_move_ids = []
        eliminate_move_line_ids = []
        for row in rows:
            row['analytic_account_id'] = row['analytic_account_id'][0] if row['analytic_account_id'] else False
            row['branch_id'] = row['branch_id'][0] if row['branch_id'] else False
            row['partner_id'] = row['partner_id'][0] if row['partner_id'] else False
            row['tax_code_id'] = row['tax_code_id'][0] if row['tax_code_id'] else False
            row['currency_id'] = row['currency_id'][0] if row['currency_id'] else False
            row['product_id'] = row['product_id'][0] if row['product_id'] else False
            row['move_id'] = row['move_id'][0] if row['move_id'] else False
            row['account_id'] = row['account_id'][0] if row['account_id'] else False
            row['product_uom_id'] = row['product_uom_id'][0] if row['product_uom_id'] else False
            row['company_id'] = row['company_id'][0] if row['company_id'] else False
            debit = row['debit']
            credit = row['credit']
            row['credit'] = debit
            row['debit'] = credit
            if row['move_id'] not in eliminate_move_ids:
                eliminate_move_ids.append(row['move_id'])
            if row['id'] not in eliminate_move_line_ids:
                eliminate_move_line_ids.append(row['id'])
            row['elimination_move_line_id'] = row['id']
            row['period_id'] = self.periode_id.id
            row['date'] = date
            move_id = row['move_id']
            row_id = row['id']
            del row['id']
            del row['move_id']
            row['eliminated'] = True

            eliminate_line.append([0,False,row])
        if not eliminate_line:
            raise osv.except_osv(('Perhatian !'), ("Period: %s, tidak ditemukan jurnal entry yang akan dieliminasi")%(self.periode_id.name))
        move = {
            'name': name,
            'ref': name,
            'journal_id': journal_id,
            'date': date,
            'period_id':self.periode_id.id,
            'line_id':eliminate_line,
        }
        move_id = move_pool.create(move)
        move_line_pool.browse(eliminate_move_line_ids).with_context(bypass_check=True).write({'eliminated':True})
        if company.journal_eliminate_multi_company_id.entry_posted:
            posted = move_id.post()
        self.write({'state': 'confirm', 'move_id': move_id.id})
        return True

    @api.multi
    def wkf_request_approval(self):
        if not self.move_consol_ids:
            raise osv.except_osv(('Perhatian !'), ("Period: %s, tidak ditemukan jurnal entry yang akan dieliminasi")%(self.periode_id.name))
        total_debit = sum(line.credit for line in self.move_consol_ids)  
        total_credit = sum(line.debit for line in self.move_consol_ids) 
        if total_debit != total_credit:
            raise osv.except_osv(('Perhatian !'), ("Hasil eliminasi tidak balance! mohon di cek kembali"))
        obj_matrix = self.env["dym.approval.matrixbiaya"]
        obj_matrix.request_by_value(self, 0)

        self.state =  'waiting_for_approval'
        self.approval_state = 'rf'
        company = self.get_group_company()
        if not company.journal_eliminate_multi_company_id:
            raise osv.except_osv(('Perhatian !'), ("Journal eliminasi multi company belum diisi di %s!")%(company.name)) 
                
    @api.multi      
    def wkf_approval(self):       
        approval_sts = self.env['dym.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'date':datetime.today(),'approval_state':'a','confirm_uid':self._uid,'confirm_date':datetime.now()})
            self.action_create_move_line_eliminate()
        elif approval_sts == 0:
                raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group Approval"))    
            
    @api.multi
    def has_approved(self):
        if self.approval_state == 'a':
            return True
        return False
    
    @api.multi
    def has_rejected(self):
        if self.approval_state == 'r':
            self.write({'state':'draft'})
            return True
        return False
    
    @api.one
    def wkf_set_to_draft(self):
        self.write({'state':'draft','approval_state':'r'})
                            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Journal Eliminasi tidak bisa didelete !"))
        return super(dym_journal_elimination, self).unlink(cr, uid, ids, context=context) 

    @api.multi
    def eksport_excel(self):
        data = []
        book = xlwt.Workbook()
        sheet = book.add_sheet("Selisih Penjualan")
        sheet2 = book.add_sheet("Total Selisih Penjualan")
        now = datetime.now()
        style = xlwt.easyxf('font: bold 1;')
        style_header = xlwt.easyxf('font: bold 1, name Calibri, height 210; pattern: pattern solid, fore_colour yellow;')

        debit_credit = {}
        header = ['Transaction', 'Ref Intercompany', 'Date','Branch'] 
        account_ids = [x for x in self.periode_id.company_id.account_fields_report_line]
        for account in account_ids:
            header.append(account.account_id.name)
            debit_credit[account.account_id.name] = account.credit
        header.append('Diff Amount')
        header.append('Bisnis Unit')
        data_dict = {}
        no = 0
        branch = {}
        for line in self.move_consol_ids:
            if line.account_id.name in header:
                data_dict[line.account_id.name] = line.debit or line.credit
                # no += 1
                intercom_ref = line._get_intercom_ref_id()
                bu = str(line.analytic_2.code)+' '+str(line.analytic_2.name)
                data.append({
                        # 'No': no,
                        'Transaction': line.consol_entry.name,
                        'Ref Intercompany': intercom_ref or self.intercom_ref or '',
                        'Date': line.consol_entry.date,
                        'Branch': line.branch_id.name,
                        line.account_id.name: data_dict[line.account_id.name],
                        'Diff Amount': (data_dict[line.account_id.name] * -1) if debit_credit[line.account_id.name] == True else data_dict[line.account_id.name],
                        'Bisnis Unit': bu,
                        'branch_id': line.branch_id.id,
                        'division': line.division,
                        'account_id': line.account_id.id,
                        'journal_id': line.company_id.journal_eliminate_multi_company_id.id,
                        'company_id': line.company_id.id,
                        'analytic_account_id': line.analytic_account_id.id,
                        'period_id': line.period_id.id,
                        })

                if line.branch_id.name+'#'+str(bu) not in branch:
                    branch[line.branch_id.name+'#'+str(bu)] = (data_dict[line.account_id.name] * -1) if debit_credit[line.account_id.name] == True else data_dict[line.account_id.name]
                else:
                    branch[line.branch_id.name+'#'+str(bu)] += (data_dict[line.account_id.name] * -1) if debit_credit[line.account_id.name] == True else data_dict[line.account_id.name]
                    
                
        trans_list = []
        uniq_list = []
        debit = 0
        credit = 0
        for d in data:
            if d['Transaction'] not in trans_list:   
                uniq_list.append(d)
                trans_list.append(d['Transaction'])
            else:
                for a in account_ids:
                    for datas in uniq_list:
                        if datas['Transaction'] == d['Transaction']:
                            if a.account_id.name in d:
                                if a.account_id.name not in datas:
                                    uniq_list[uniq_list.index(datas)][a.account_id.name] = d[a.account_id.name]
                                else:
                                    uniq_list[uniq_list.index(datas)][a.account_id.name] += d[a.account_id.name]
                                    
                                if debit_credit[a.account_id.name] == True:
                                    uniq_list[uniq_list.index(datas)]['Diff Amount'] -= d[a.account_id.name]                                      
                                else:
                                    uniq_list[uniq_list.index(datas)]['Diff Amount'] += d[a.account_id.name]

        obj_amlc = self.env['account.move.line.consol']
        obj_amc = self.env['account.move.consol']

        if not self.move_diff_ids:
            amc = obj_amc.create({
                        'journal_id':uniq_list[0]['journal_id'],
                        'period_id':uniq_list[0]['period_id'],
                        })
            for line in uniq_list:
                if line['Diff Amount'] != 0:
                    if not self.periode_id.company_id.account_elimination_diff_id:
                        raise osv.except_osv(('Perhatian !'), ("Account Elimination Diff. belum dilengkapi di Company"))       
                    else:
                        acc_elim_diff = self.periode_id.company_id.account_elimination_diff_id.id
                        obj_amlc.create({
                        'move_id': amc.id,
                        'analytic_account_id': line['analytic_account_id'],
                        'branch_id': line['branch_id'],
                        'division': line['division'],
                        'name': line['Transaction'],
                        'journal_id': line['journal_id'],                
                        'account_id': acc_elim_diff,
                        'company_id': line['company_id'],
                        'debit': line['Diff Amount'] * -1 if line['Diff Amount'] < 0 else 0,
                        'credit': line['Diff Amount'] if line['Diff Amount'] > 0 else 0,
                        'elimination_id': self.id,
                        'period_id': self.periode_id.id,
                        'date': self.create_date,                

                            }) 

        branch_list = []
        for b,x in branch.items():
            branch_list.append({
                    'Branch': b.split('#')[0],
                    'Amount': x,
                    'Bisnis Unit': b.split('#')[1]
            })


        uniq_list=sorted(uniq_list,key=lambda x: (x['Ref Intercompany'],x['Transaction']))

        no = 0; 
        for line in uniq_list:
            no += 1
            col = -1
            for i in header:
                col += 1
                if i in line:
                    sheet.write(no, col, line[i])

        colh = -1
        for x in header:
            colh += 1 
            sheet.write(0, colh, x)

        no = 0; 
        for line in branch_list:
            no += 1
            col = -1
            for i in ['Branch','Amount','Bisnis Unit']:
                col += 1
                if i in line:
                    sheet2.write(no, col, line[i])

        colh = -1
        for x in ['Branch','Amount','Bisnis Unit']:
            colh += 1 
            sheet2.write(0, colh, x)



        filename = 'Elimination_Report_on_%s.xls' % (now.strftime("%Y-%m-%d %H:%M:%S"))        
        file_data = StringIO.StringIO()
        book.save(file_data)
        out = base64.encodestring(file_data.getvalue())
        self.write({'datafile':out,'filename': filename})

        return True

# class dym_account_move_line_consol_diff(models.Model):
#     _name = 'account.move.line.consol.diff'


