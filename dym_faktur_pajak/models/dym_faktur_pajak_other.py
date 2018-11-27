from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.osv import osv

class dym_faktur_pajak_other(models.Model):
    
    _name = "dym.faktur.pajak.other"
    _description = "Faktur Pajak Other"
    _order = "id asc"
         
    name = fields.Char(string='Faktur Pajak Other')
    description = fields.Char(string='Description')
    date = fields.Date(string='Date',required=True,default=fields.Date.context_today)
    company_id = fields.Many2one('res.company',string="Company")
    faktur_pajak_id = fields.Many2one('dym.faktur.pajak.out',string='No Faktur Pajak', domain="[('state','=','open'),('company_id','=',company_id)]")
    partner_id = fields.Many2one('res.partner',string='Partner')
    tgl_terbit = fields.Date(string='Tgl Terbit')
    thn_penggunaan = fields.Integer('Tahun Penggunaan')
    pajak_gabungan = fields.Boolean('Pajak Gabungan')
    untaxed_amount = fields.Float(string='Untaxed Amount')
    tax_amount = fields.Float(string='Tax Amount')
    total_amount = fields.Float(string='Total Amount')
    state = fields.Selection([
                              ('draft','Draft'),
                              ('posted','Posted'),
                              ],default='draft')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')   
    kwitansi_no = fields.Char(string='No Kwitansi')
    in_out = fields.Selection([
                              ('in','In'),
                              ('out','Out'),
                              ], default='out', required=True, string='Faktur Type')
    no_faktur_pajak = fields.Char(string="No Faktur Pajak")
    move_line_ids = fields.Many2many('account.move.line','fp_other_move_line_rel','fp_other_id','move_line_id','Move Line', domain="[('id','=',0)]")
    
    def faktur_pajak_change(self,cr,uid,ids,no_faktur_pajak,context=None):   
        value = {}
        warning = {}
        if no_faktur_pajak :
            cek = no_faktur_pajak.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Nomor Faktur Pajak Hanya Boleh Angka ! ')),
                }
                value = {
                         'no_faktur_pajak':False
                         }     
        return {'warning':warning,'value':value} 

    @api.model
    def create(self,values,context=None):
        vals = []
        values['name'] = self.env['ir.sequence'].get_sequence('FPO', division='Umum')     
        values['date'] = datetime.today()
        if len(str(values.get('thn_penggunaan','1'))) < 4 or len(str(values.get('thn_penggunaan','1'))) > 4 :
            raise osv.except_osv(('Perhatian !'), ("Tahun Pembuatan harus 4 digit !"))
        faktur_pajak = super(dym_faktur_pajak_other,self).create(values)       
        return faktur_pajak
    
    @api.onchange('thn_penggunaan')
    def onchange_tahun_penggunaan(self):
        warning = {}        
        if self.thn_penggunaan :
            tahun = len(str(self.thn_penggunaan))
            if tahun > 4 or tahun < 4 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Tahun hanya boleh 4 digit ! ')),
                }
                self.thn_penggunaan = False                
        return {'warning':warning} 
    
    @api.onchange('in_out')
    def onchange_in_out(self):
        if self.in_out == 'in':
            self.faktur_pajak_id = False
        if self.in_out == 'out':
            self.no_faktur_pajak = False


    @api.onchange('in_out','partner_id','company_id')
    def fill_move(self):
        self.move_line_ids = False
        dom=[('id','=',0)]
        if self.partner_id and self.company_id:
            if self.in_out == 'in':
                dom=[('partner_id','=',self.partner_id.id),('company_id','=',self.company_id.id),('account_id.type','=','payable'),('credit','>',0)]
            if self.in_out == 'out':
                dom=[('partner_id','=',self.partner_id.id),('company_id','=',self.company_id.id),('account_id.type','=','receivable'),('debit','>',0)]
        domain = {'move_line_ids':dom}
        return {'domain': domain}

    @api.onchange('move_line_ids')
    def onchange_move(self):
        if self.move_line_ids:
            final_tax_amount = 0
            final_untaxed_amount = 0
            final_total_amount = 0
            for line in self.move_line_ids:
                tax_amount = 0
                untaxed_amount = 0
                total_amount = 0
                tax = ['tax_amount','amount_tax']
                untaxed = ['untaxed_amount','amount_untaxed']
                total = ['amount_total','total_amount','amount']
                if line.move_id.transaction_id and line.move_id.model:
                    trans = self.env[line.move_id.model].sudo().browse(line.move_id.transaction_id)
                    for i in tax:
                        if i in trans:
                            tax_amount = trans[i]
                            break
                    for j in untaxed:
                        if j in trans:
                            untaxed_amount = trans[j]
                            break
                    for k in total:
                        if k in trans:
                            total_amount = trans[k]
                            break
                if untaxed_amount == 0:
                    untaxed_amount = total_amount - tax_amount
                final_untaxed_amount += untaxed_amount
                final_tax_amount += tax_amount
                final_total_amount += total_amount
            self.untaxed_amount = final_untaxed_amount
            self.tax_amount = final_tax_amount
            self.total_amount = final_total_amount

    @api.multi
    def action_post(self):
        if self.untaxed_amount and self.tax_amount :
            self.total_amount = self.untaxed_amount + self.tax_amount
        elif self.untaxed_amount :
            self.total_amount = self.untaxed_amount
        elif self.tax_amount :
            self.total_amount = self.tax_amount
        else :
            self.total_amount = 0.0
        model_id = self.env['ir.model'].search([
                                ('model','=','dym.faktur.pajak.other')
                                ])
        if self.in_out == 'out' and self.faktur_pajak_id.id:
            if self.faktur_pajak_id.state != 'open':
                raise osv.except_osv(('Perhatian !'), ("Faktur pajak %s sudah digunakan!")%(self.faktur_pajak_id.name))
            faktur_pajak = self.env['dym.faktur.pajak.out'].browse(self.faktur_pajak_id.id)
            faktur_pajak.write({
                            'model_id':model_id.id,
                            'pajak_gabungan' :self.pajak_gabungan,
                            'partner_id':self.partner_id.id,
                            'untaxed_amount':self.untaxed_amount,
                            'amount_total':self.total_amount,
                            'tgl_terbit':self.tgl_terbit,
                            'transaction_id':self.id,
                            'date':self.date,
                            'tax_amount':self.tax_amount,
                            'thn_penggunaan':self.thn_penggunaan,
                            'state':'close',
                            'in_out':'out',
                            })
        elif self.in_out == 'in':
            faktur_pajak_id = self.env['dym.faktur.pajak.out'].create({
                'name': self.no_faktur_pajak,
                'state': 'close',
                'thn_penggunaan' : self.thn_penggunaan,
                'tgl_terbit' : self.tgl_terbit,
                'model_id':model_id.id,
                'amount_total':self.total_amount,
                'untaxed_amount':self.untaxed_amount,
                'tax_amount':self.tax_amount,
                'transaction_id':self.id,
                'date':self.date,
                'partner_id':self.partner_id.id,
                'in_out':'in',
                'pajak_gabungan' :self.pajak_gabungan,
                'company_id' :self.company_id.id,
            })
            self.write({'faktur_pajak_id':faktur_pajak_id.id})

        self.confirm_date = datetime.now()
        self.confirm_uid = self._uid
        self.state = 'posted'
        self.date = datetime.today()
        return True
          
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Faktur Pajak Others tidak bisa didelete !"))
        return super(dym_faktur_pajak_other, self).unlink(cr, uid, ids, context=context) 
             