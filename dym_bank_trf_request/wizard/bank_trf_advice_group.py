from openerp import api, models, fields
from openerp.tools.translate import _
from openerp.exceptions import Warning as UserError, RedirectWarning, ValidationError

class BankTrfRequestGroup(models.TransientModel):
    _name = "bank.trf.request.group"
    _description = "Bank Transfer Request Grup"

    @api.model
    def _get_branch(self):
        user = self.env.user
        company_id = user.company_id.id
        branch_user = user.branch_ids
        branch_ids = [x.id for x in branch_user]
        branch_total = self.env['dym.branch'].sudo().search([
            ('company_id','=',company_id),
            ],order='name')
        return [(branch.code,branch.name) for branch in branch_total]

    @api.model
    def _get_default_branch_ho(self):
        user = self.env.user
        branch_ids = self.env['dym.branch'].search([('company_id','=',user.company_id.id),('branch_type','=','HO')])
        for branch in user.branch_ids:
            if branch.id in branch_ids.ids and branch.branch_type=='HO':
                return branch.id

    @api.model
    def _get_default_branch(self):
        user = self.env.user
        branch_ids = self.env['dym.branch'].search([('company_id','=',user.company_id.id),('branch_type','!=','HO')])
        for branch in user.branch_ids:
            if branch.id in branch_ids.ids and branch.branch_type!='HO':
                return branch.code

    name = fields.Char('Name', default='/')    
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")
    branch_id = fields.Many2one('dym.branch', string='From Branch', required=True, domain="[('company_id','=',company_id)]", default=_get_default_branch_ho)
    payment_from_id = fields.Many2one('account.journal', string="From Bank", required=True, domain="[('branch_id','in',[branch_id,False]),('type','=','bank')]")
    branch_destination_id = fields.Selection('_get_branch', string='To Branch', required=True, default=_get_default_branch)   
    bank_dest_type = fields.Selection([('in','Bank In'),('out','Bank Out')], default='out', required=True)
    payment_to_id = fields.Many2one('account.journal', string="To Bank", required=True, domain="['|',('branch_id.code','=',branch_destination_id),('branch_id','=',False),('type','=','bank')]")
    amount = fields.Float(string='Amount', required=True)
    bank_trf_request_ids = fields.Many2many('bank.trf.request')
    merge_mode = fields.Selection([('new','New Advice'),('existing','Merge with existing')], string='Mode', default='new')
    advice_id = fields.Many2one('bank.trf.advice', domain="[\
        ('state','=','draft'),\
        ('branch_id','=',branch_id),\
        ('branch_destination_id','=',branch_destination_id)\
    ]", string='Transfer Advice')
    transfer_date = fields.Date(string='Transfer Date', required=True)


    @api.onchange('branch_id')
    def onchange_branch_id(self):
        dom = {}
        val = {}
        if self.branch_id:
            user = self.env.user
            if user.branch_type!='HO':
                raise ValidationError(_('Maaf user %s tidak diperbolehkan untuk melakukan merge transfer request!' % user.login))
            else:
                company_id = self._context.get('company_id', self.env.user.company_id.id)
                branch_destination_ids = [b.id for b in self.env.user.branch_ids if b.company_id.id==company_id and b.branch_type != 'HO']
        return {'value':val,'domain':dom}

    @api.onchange('branch_destination_id','bank_dest_type')
    def onchange_branch_destination_id(self):
        dom = {}
        val = {}
        if self.branch_destination_id:
            branch = self.env['dym.branch'].search([('code','=',self.branch_destination_id)])
            bank_dest_ids = self.env['account.journal'].search([('type','=','bank'),('transaction_type','=',self.bank_dest_type),('branch_id','=',branch.id)])
            dom['payment_to_id'] = [('id','in',bank_dest_ids.ids)]
            if bank_dest_ids:
                val['payment_to_id'] = bank_dest_ids.ids[0]
            # else:
            #     raise ValidationError(_('Cabang %s tidak memiliki rek bank masuk' % branch.name))
        return {'value':val,'domain':dom}

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(BankTrfRequestGroup, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self.env.context.get('active_model','') == 'bank.trf.request' and len(self.env.context['active_ids']) < 1:
            raise ValidationError(_('Please select multiple order to merge in the list view.'))

        active_model = self.env.context.get('active_model',False)
        active_ids = self.env.context.get('active_ids',[])

        data = self.env[active_model].browse(active_ids)
        for dt in data:
            if dt.advice_id:
                raise UserError(_('The bank transfer request %s are already in Transfer Advice.' % dt.name))
            if dt.state == 'rejected':
                raise UserError(_('The bank transfer request %s had been rejected' % dt.name))
            if dt.state != 'confirmed':
                raise UserError(_('The bank transfer request %s has not yet been confirmed' % dt.name))
        return res

    @api.model
    def default_get(self, fields):
        res = super(BankTrfRequestGroup, self).default_get(fields)
        active_model = self.env.context.get('active_model',False)
        active_ids = self.env.context.get('active_ids',[])
        if not active_ids:
            raise UserError(_('Silahkan pilih satu atau lebih Transfer Request untuk digabungkan!'))
        data = self.env[active_model].browse(active_ids)
        branches = list(set([d.branch_id.name for d in data]))
        if len(branches)>1:
            raise UserError(_('Jangan menggabungkan transfer request untuk lebih dari 1 cabang (%s)' % ','.join(branches)))
        total_amount = sum([r.amount for r in data])
        res['bank_trf_request_ids'] = active_ids
        res['amount'] = total_amount
        res['branch_destination_id'] = data[0].branch_id.code

        return res        

    @api.multi
    def merge_trf_requests(self):
        name = self.env['ir.sequence'].next_by_code('bank.trf.advice')
        branch_config = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])
        supplier_payment_limit = branch_config.supplier_payment_limit

        values = {
            'name': name,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id,
            'payment_from_id': self.payment_from_id.id,
            'payment_to_id': self.payment_to_id.id,
            'branch_destination_id': self.branch_destination_id,
            'bank_trf_request_ids': [(6,0,self.bank_trf_request_ids.ids)],
            'amount': self.amount,
            'state': 'draft',
            'transfer_date': self.transfer_date,
        }
        if self.merge_mode=='new':
            advice_id = self.env['bank.trf.advice'].create(values)
        if self.merge_mode=='existing':
            advice_id = self.advice_id
            for trf_req in self.bank_trf_request_ids:
                trf_req.write({'advice_id':advice_id.id})

        view_id = self.env.ref('dym_bank_trf_request.bank_trf_advice_form_view').id
        return {
            'name' : _('Bank Transfer Advice'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': advice_id.id,
            'res_model': 'bank.trf.advice',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': False,
            'context': self.env.context
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
