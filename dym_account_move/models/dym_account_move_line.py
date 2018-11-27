from openerp import models, fields, api, SUPERUSER_ID
from openerp.osv import osv
from openerp.tools.translate import _

class res_company(models.Model):
    _inherit = "res.company"
    
    partner_tax_id = fields.Many2one('res.partner',string="Partner Pajak")

class dym_account_move_line(models.Model):
    _inherit = 'account.move.line'

    @api.cr_uid_ids_context
    def _check_company_id(self, cr, uid, ids, context=None):
        lines = self.browse(cr, SUPERUSER_ID, ids, context=context)
        for l in lines:
            if l.period_id.company_id != l.account_id.company_id:
                return False
        return True

    _constraints = [
        (_check_company_id, 'Account and Period must belong to the same company.', ['company_id']),
    ]

    def get_residual_date_based(self, cr, uid, move_line_id, intiial_date=False, context=None):
        move_line = self.pool.get('account.move.line').browse(cr, uid, move_line_id)[0]
        sign = (move_line.debit - move_line.credit) < 0 and -1 or 1
        residual = (move_line.debit - move_line.credit) * sign
        line_total_in_company_currency =  move_line.debit - move_line.credit
        if move_line.reconcile_id:
            for payment_line in move_line.reconcile_id.line_id:
                if payment_line.id == move_line.id:
                    continue
                if intiial_date and payment_line.date > intiial_date:
                    continue
                line_total_in_company_currency += (payment_line.debit - payment_line.credit)
        elif move_line.reconcile_partial_id:
            for payment_line in move_line.reconcile_partial_id.line_partial_ids:
                if payment_line.id == move_line.id:
                    continue
                if intiial_date and payment_line.date > intiial_date:
                    continue
                line_total_in_company_currency += (payment_line.debit - payment_line.credit)
        residual = line_total_in_company_currency * sign
        return residual

    def _get_context_analytic_code(self, cr, uid, ctx=None):
        for k,v in ctx.items():
            if k not in ['analytic_co_dari','analytic_co_sampai','analytic_bb_dari','analytic_bb_sampai','analytic_br_dari','analytic_br_sampai','analytic_cc_dari','analytic_cc_sampai']:
                continue
            ctx.update({
                k: self.pool.get('account.analytic.account').browse(cr, uid, [v], {})[0].code
            })
        return ctx

    def _query_get(self, cr, uid, obj='l', context=None):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalperiod_obj = self.pool.get('account.period')
        account_obj = self.pool.get('account.account')
        fiscalyear_ids = []
        context = self._get_context_analytic_code(cr, uid, dict(context or {}))
        initial_bal = context.get('initial_bal', False)
        company_clause = " "
        query = ''
        query_params = {}
        if context.get('company_id'):
            company_clause = " AND " +obj+".company_id = %(company_id)s"
            query_params['company_id'] = context['company_id']
        if not context.get('fiscalyear'):
            if context.get('all_fiscalyear'):
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [])
            else:
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [('state', '=', 'draft')])
        else:
            fiscalyear_ids = context['fiscalyear']
            if isinstance(context['fiscalyear'], (int, long)):
                fiscalyear_ids = [fiscalyear_ids]

        query_params['fiscalyear_ids'] = tuple(fiscalyear_ids) or (0,)
        state = context.get('state', False)
        where_move_state = ''
        where_move_lines_by_date = ''

        table_account_move = 'account_move'
        if 'konsolidasi' in context and context['konsolidasi'] == True:
            table_account_move = 'account_move_consol'

        if context.get('date_from') and context.get('date_to'):
            query_params['date_from'] = context['date_from']
            query_params['date_to'] = context['date_to']
            if initial_bal:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM "+table_account_move+" WHERE date < %(date_from)s)"
            else:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM "+table_account_move+" WHERE date >= %(date_from)s AND date <= %(date_to)s)"

        if state:
            if state.lower() not in ['all']:
                query_params['state'] = state
                where_move_state= " AND "+obj+".move_id IN (SELECT id FROM "+table_account_move+" WHERE "+table_account_move+".state = %(state)s)"
        if context.get('period_from') and context.get('period_to') and not context.get('periods'):
            if initial_bal:
                period_company_id = fiscalperiod_obj.browse(cr, uid, context['period_from'], context=context).company_id.id
                first_period = fiscalperiod_obj.search(cr, uid, [('company_id', '=', period_company_id)], order='date_start', limit=1)[0]
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, first_period, context['period_from'])
            else:
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, context['period_from'], context['period_to'])
        if context.get('periods'):
            query_params['period_ids'] = tuple(context['periods'])
            if initial_bal:
                query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s)" + where_move_state + where_move_lines_by_date
                period_ids = fiscalperiod_obj.search(cr, uid, [('id', 'in', context['periods'])], order='date_start', limit=1)
                if period_ids and period_ids[0]:
                    first_period = fiscalperiod_obj.browse(cr, uid, period_ids[0], context=context)
                    query_params['date_start'] = first_period.date_start
                    query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s AND date_start <= %(date_start)s AND id NOT IN %(period_ids)s)" + where_move_state + where_move_lines_by_date
            else:
                query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s AND id IN %(period_ids)s)" + where_move_state + where_move_lines_by_date
        else:
            query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s)" + where_move_state + where_move_lines_by_date

        if initial_bal and not context.get('periods') and not where_move_lines_by_date:
            raise osv.except_osv(_('Warning!'),_("You have not supplied enough arguments to compute the initial balance, please select a period and a journal in the context."))

        if context.get('journal_ids'):
            query_params['journal_ids'] = tuple(context['journal_ids'])
            query += ' AND '+obj+'.journal_id IN %(journal_ids)s'

        if context.get('account_ids'):
            query_params['account_ids'] = tuple(context['account_ids'])
            query += ' AND '+obj+'.account_id IN %(account_ids)s'

        if context.get('analytic_ids'):
            query_params['analytic_ids'] = tuple(context['analytic_ids'])
            query += ' AND '+obj+'.analytic_account_id IN %(analytic_ids)s'

        if context.get('chart_account_id'):
            child_ids = account_obj._get_children_and_consol(cr, uid, [context['chart_account_id']], context=context)
            # query_params['child_ids'] = tuple(child_ids)
            # query += ' AND '+obj+'.account_id IN %(child_ids)s'

        if context.get('sql_query'):
            query += context['sql_query']

        if context.get('analytic_co_dari'):
            if context.get('analytic_co_dari').isdigit():
                query_params['analytic_co_dari'] = int(context['analytic_co_dari'])
                query += " AND cast(coalesce(a1.code, '-1') as integer) >= %(analytic_co_dari)s"

        if context.get('analytic_co_sampai'):
            if context.get('analytic_co_sampai').isdigit():
                query_params['analytic_co_sampai'] = int(context['analytic_co_sampai'])
                query += " AND cast(coalesce(a1.code, '9999999999') as integer) <= %(analytic_co_sampai)s"

        if context.get('analytic_bb_dari'):
            if context.get('analytic_bb_dari').isdigit():
                query_params['analytic_bb_dari'] = int(context['analytic_bb_dari'])
                query += " AND cast(coalesce(a2.code, '-1') as integer) >= %(analytic_bb_dari)s"

        if context.get('analytic_bb_sampai'):
            if context.get('analytic_bb_sampai').isdigit():
                query_params['analytic_bb_sampai'] = int(context['analytic_bb_sampai'])
                query += " AND cast(coalesce(a2.code, '9999999999') as integer) <= %(analytic_bb_sampai)s"

        if context.get('analytic_br_dari'):
            if context.get('analytic_br_dari').isdigit():
                query_params['analytic_br_dari'] = int(context['analytic_br_dari'])
                query += " AND cast(coalesce(a3.code, '-1') as integer) >= %(analytic_br_dari)s"

        if context.get('analytic_br_sampai'):
            if context.get('analytic_br_sampai').isdigit():
                query_params['analytic_br_sampai'] = int(context['analytic_br_sampai'])
                query += " AND cast(coalesce(a3.code, '9999999999') as integer) <= %(analytic_br_sampai)s"

        if context.get('analytic_cc_dari'):
            if context.get('analytic_cc_dari').isdigit():
                query_params['analytic_cc_dari'] = int(context['analytic_cc_dari'])
                query += " AND cast(coalesce(a4.code, '-1') as integer) >= %(analytic_cc_dari)s"

        if context.get('analytic_cc_sampai'):
            if context.get('analytic_cc_sampai').isdigit():
                query_params['analytic_cc_sampai'] = int(context['analytic_cc_sampai'])
                query += " AND cast(coalesce(a4.code, '9999999999') as integer) <= %(analytic_cc_sampai)s"

        query += company_clause
        return cr.mogrify(query, query_params)

    @api.cr_uid_ids_context
    def _query_get_consolidate(self, cr, uid, obj='l1', obj2='l2', context=None):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalperiod_obj = self.pool.get('account.period')
        account_obj = self.pool.get('account.account')
        fiscalyear_ids = []
        context = dict(context or {})
        initial_bal = context.get('initial_bal', False)
        company_clause = " "
        query = ''
        query_params = {}
        if context.get('company_id'):
            company_clause = " AND " +obj+".company_id = %(company_id)s"
            query_params['company_id'] = context['company_id']
        if not context.get('fiscalyear'):
            if context.get('all_fiscalyear'):
                #this option is needed by the aged balance report because otherwise, if we search only the draft ones, an open invoice of a closed fiscalyear won't be displayed
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [])
            else:
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [('state', '=', 'draft')])
        else:
            #for initial balance as well as for normal query, we check only the selected FY because the best practice is to generate the FY opening entries
            fiscalyear_ids = context['fiscalyear']
            if isinstance(context['fiscalyear'], (int, long)):
                fiscalyear_ids = [fiscalyear_ids]

        query_params['fiscalyear_ids'] = tuple(fiscalyear_ids) or (0,)
        state = context.get('state', False)
        where_move_state = ''
        where_move_lines_by_date = ''

        if context.get('date_from') and context.get('date_to'):
            query_params['date_from'] = context['date_from']
            query_params['date_to'] = context['date_to']
            if initial_bal:
                where_move_lines_by_date = " AND " +obj2+".move_id IN (SELECT id FROM account_move WHERE date < %(date_from)s and id = l2.move_id)"
            else:
                where_move_lines_by_date = " AND " +obj2+".move_id IN (SELECT id FROM account_move WHERE date >= %(date_from)s AND date <= %(date_to)s and id = l2.move_id)"

        if state:
            if state.lower() not in ['all']:
                query_params['state'] = state
                where_move_state= " AND "+obj2+".move_id IN (SELECT id FROM account_move WHERE account_move.state = %(state)s  and id = l2.move_id)"
        if context.get('period_from') and context.get('period_to') and not context.get('periods'):
            if initial_bal:
                period_company_id = fiscalperiod_obj.browse(cr, uid, context['period_from'], context=context).company_id.id
                first_period = fiscalperiod_obj.search(cr, uid, [('company_id', '=', period_company_id)], order='date_start', limit=1)[0]
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, first_period, context['period_from'])
            else:
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, context['period_from'], context['period_to'])
        if context.get('periods'):
            query_params['period_ids'] = tuple(context['periods'])
            if initial_bal:
                query = obj2+".state <> 'draft' AND "+obj2+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s and id = l2.period_id)" + where_move_state + where_move_lines_by_date
                period_ids = fiscalperiod_obj.search(cr, uid, [('id', 'in', context['periods'])], order='date_start', limit=1)
                if period_ids and period_ids[0]:
                    first_period = fiscalperiod_obj.browse(cr, uid, period_ids[0], context=context)
                    query_params['date_start'] = first_period.date_start
                    query = obj2+".state <> 'draft' AND "+obj2+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s AND date_start <= %(date_start)s AND id NOT IN %(period_ids)s and id = l2.period_id)" + where_move_state + where_move_lines_by_date
            else:
                query = obj2+".state <> 'draft' AND "+obj2+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s AND id IN %(period_ids)s and id = l2.period_id)" + where_move_state + where_move_lines_by_date
        else:
            query = obj2+".state <> 'draft' AND "+obj2+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s and id = l2.period_id)" + where_move_state + where_move_lines_by_date

        if initial_bal and not context.get('periods') and not where_move_lines_by_date:
            raise osv.except_osv(_('Warning!'),_("You have not supplied enough arguments to compute the initial balance, please select a period and a journal in the context."))

        if context.get('journal_ids'):
            query_params['journal_ids'] = tuple(context['journal_ids'])
            query += ' AND '+obj+'.journal_id IN %(journal_ids)s'

        if context.get('chart_account_id'):
            child_ids = account_obj._get_children_and_consol(cr, uid, [context['chart_account_id']], context=context)
            query_params['child_ids'] = tuple(child_ids)
            query += ' AND '+obj+'.account_id IN %(child_ids)s'

        query += company_clause
        return cr.mogrify(query, query_params)

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False
        return branch_ids 


    @api.model
    def get_analytic2(self, ids=None):
        res = {}
        import json
        for this in self.browse(ids):
            analytic = this.analytic_account_id
            if analytic.type == 'normal':
                if analytic.segmen == 1:
                    this.analytic_1 = analytic
                if analytic.segmen == 2:
                    this.analytic_2 = analytic
                if analytic.segmen == 3:
                    this.analytic_3 = analytic
                    if not this.branch_id and analytic.branch_id:
                        this.branch_id = analytic.branch_id
                if analytic.segmen == 4:
                    this.analytic_4 = analytic

            while (analytic.parent_id):
                analytic = analytic.parent_id
                if analytic.type == 'normal':
                    if analytic.segmen == 1 and not this.analytic_1:
                        this.analytic_1 = analytic
                    if analytic.segmen == 2 and not this.analytic_2:
                        this.analytic_2 = analytic
                    if analytic.segmen == 3 and not this.analytic_3:
                        this.analytic_3 = analytic
                        if not this.branch_id and analytic.branch_id:
                            this.branch_id = analytic.branch_id
                    if analytic.segmen == 4 and not this.analytic_4:
                        this.analytic_4 = analytic
        return json.dumps(res)

    @api.one
    @api.depends('analytic_account_id','analytic_1','analytic_2','analytic_3','analytic_4',)
    def get_analytic(self):
        analytic = self.analytic_account_id
        if analytic.type == 'normal':
            if analytic.segmen == 1 and not self.analytic_1:
                self.analytic_1 = analytic
            if analytic.segmen == 2 and not self.analytic_2:
                self.analytic_2 = analytic
            if analytic.segmen == 3 and not self.analytic_3:
                self.analytic_3 = analytic
                if not self.branch_id and analytic.branch_id:
                    self.branch_id = analytic.branch_id
            if analytic.segmen == 4 and not self.analytic_4:
                self.analytic_4 = analytic
        while (analytic.parent_id):
            analytic = analytic.parent_id
            if analytic.type == 'normal':
                if analytic.segmen == 1 and not self.analytic_1:
                    self.analytic_1 = analytic
                if analytic.segmen == 2 and not self.analytic_2:
                    self.analytic_2 = analytic
                if analytic.segmen == 3 and not self.analytic_3:
                    self.analytic_3 = analytic
                    if not self.branch_id and analytic.branch_id:
                        self.branch_id = analytic.branch_id
                if analytic.segmen == 4 and not self.analytic_4:
                    self.analytic_4 = analytic
        if self.analytic_1:
            self.analytic1 = self.analytic_1
        if self.analytic_2:
            self.analytic2 = self.analytic_2
        if self.analytic_3:
            self.analytic3 = self.analytic_3
        if self.analytic_4:
            self.analytic4 = self.analytic_4

    @api.one
    def get_fake_balance(self):
        if self.currency_id:
            amount = abs(self.amount_residual_currency)
        else:
            amount = abs(self.amount_residual)
        active_model = self._context.get('active_model', False)
        voucher_id = False
        if active_model == 'account.voucher':
            voucher_id = self._context.get('active_id',False)
        SQL = """
            SELECT 
                vl.amount
            FROM 
                account_voucher_line vl 
            INNER JOIN
                account_voucher vc ON vc.id=vl.voucher_id
            WHERE 
                vl.move_line_id=%s AND 
                vc.state NOT IN ('posted','cancel')"""
        if voucher_id:
            SQL += " AND vc.id <> " + str(voucher_id)
        self.env.cr.execute(SQL,(self.id,))
        for vo in self.env.cr.fetchall():
            amount -= vo[0]
        self.fake_balance = amount


    @api.one
    @api.depends('invoice')
    def get_finco(self):
        finco_id = False
        engine_number = ''
        dso_name = self.invoice.origin or ''
        dso = self.env['dealer.sale.order'].search([('name','in',dso_name.split(' '))], limit=1)
        if dso and dso.is_credit == True:
            finco_id = dso.finco_id.id
            engine_number = ', '.join(dso.dealer_sale_order_line.mapped('lot_id.name'))
        self.finco_id = finco_id
        self.engine_number = engine_number

    finco_id = fields.Many2one('res.partner', string='Finco', compute="get_finco")
    engine_number = fields.Char(string='Engine Number', compute="get_finco")
    branch_id = fields.Many2one('dym.branch', string='Branch')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', change_default=True, select=False)
    kwitansi = fields.Boolean('kwitansi')
    analytic_1 = fields.Many2one('account.analytic.account', string='Account Analytic Company', compute="get_analytic", store=True)
    analytic_2 = fields.Many2one('account.analytic.account', string='Account Analytic Bisnis Unit', compute="get_analytic", store=True)
    analytic_3 = fields.Many2one('account.analytic.account', string='Account Analytic Branch', compute="get_analytic", store=True)
    analytic_4 = fields.Many2one('account.analytic.account', string='Account Analytic Cost Center', compute="get_analytic", store=True)
    unidentified_payment = fields.Boolean(string='Unidentified Payment',readonly=True, states={'draft': [('readonly', False)]})   
    fake_balance = fields.Float('Fake Balance', compute="get_fake_balance")

    @api.onchange('analytic_1','analytic_2','analytic_3','analytic_4')
    def payment_account_analytic_accounts(self):
        if self.analytic_1:
            self.analytic1 = self.analytic_1
        if self.analytic_2:
            self.analytic2 = self.analytic_2
        if self.analytic_3:
            self.analytic3 = self.analytic_3
        if self.analytic_4:
            self.analytic4 = self.analytic_4

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = args
        if name:
            move_ids = self.env['account.move'].search([('name',operator,name)])
            move_ids = [x.id for x in move_ids]
            domain += ['|','|',('name', operator, name),('move_id', 'in', move_ids),('ref', operator, name)]
        recs = self.search(domain, limit=limit)
        # recs = self.search(['|','|',('name', operator, name),('move_id.name', operator, name),('ref', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.cr_uid_ids_context
    def create_analytic_lines(self, cr, uid, ids, context=None):
        return True      

    @api.cr_uid_ids_context
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        result = []

        for line in self.browse(cr, uid, ids, context=context):
            if line.name != '/':  
                if line.invoice.qq_id :
                    result.append((line.id, (line.move_id.name or '')+' ('+line.name+')'+'-'+line.invoice.qq_id.name))
                else :
                    result.append((line.id, (line.move_id.name or '')+' ('+line.name+')'))
            else:
                if line.invoice.qq_id :
                    result.append((line.id, line.move_id.name+'-'+line.invoice.qq_id.name))
                else :
                    result.append((line.id, line.move_id.name))
        return result
    
    def create(self, cr, uid, vals, context=None):
        if 'move_id' in vals:
            move = self.pool.get('account.move').browse(cr, uid, [vals['move_id']], context=context)[0]
        if 'date' in vals:
            vals['date'] = move.date
        if 'analytic_account_id' not in vals and 'tax_code_id' in vals and 'move_id' in vals:
            last_line_id = self.search(cr, uid, [
                ('move_id','=',vals['move_id']),
                ('analytic_account_id','!=',False),
                '|',('account_tax_id.tax_code_id','=',vals['tax_code_id']),
                ('account_tax_id.ref_tax_code_id','=',vals['tax_code_id'])], limit=1, order='id desc')
            if last_line_id:
                last_line = self.browse(cr, uid, last_line_id)
                vals['analytic_account_id'] = last_line.analytic_account_id.id

        line_id = super(dym_account_move_line, self).create(cr, uid, vals, context=context)
        line = self.browse(cr, uid, line_id)
        taxes = self.pool.get('account.tax').search(cr, uid, ['|',('account_paid_id','=', line.account_id.id),('account_collected_id','=', line.account_id.id)])
        if taxes:
            if not line.period_id.company_id.partner_tax_id:
                raise osv.except_osv(_('Warning!'),_("Mohon isi partner pajak di master company!."))
            line.write({'partner_id':line.period_id.company_id.partner_tax_id.id})
            if line.move_id and line.move_id.model and line.move_id.transaction_id:
                if line.move_id.model == 'account.voucher':
                    voucher = self.pool.get(line.move_id.model).browse(cr, uid, [line.move_id.transaction_id], context=context)
                    line.write({'analytic_account_id':voucher.analytic_4.id})
        if not line.branch_id and line.analytic_account_id:
            branch_id = False
            if line.analytic_account_id.branch_id:
                branch_id = line.analytic_account_id.branch_id.id
            else:
                analytic = line.analytic_account_id
                while (analytic.parent_id and branch_id == False):
                    analytic = analytic.parent_id
                    if analytic.branch_id:
                        branch_id = analytic.branch_id.id
            if branch_id:
                line.write({'branch_id':branch_id})
        if not line.branch_id and not line.analytic_account_id:
            if line.move_id.model and line.move_id.transaction_id:
                obj = self.pool.get(line.move_id.model).browse(cr, uid, line.move_id.transaction_id)
                if 'branch_id' in obj and obj.sudo().branch_id:
                    line.write({'branch_id':obj.sudo().branch_id.id})
        if not line.analytic_account_id and line.invoice.account_id == line.account_id and line.invoice.analytic_4.id:
            line.write({'analytic_account_id':line.invoice.analytic_4.id})
        return line_id

    def _check_moves(self, cr, uid, context=None):
        # use the first move ever created for this journal and period
        if context is None:
            context = {}
        cr.execute('SELECT id, state, name FROM account_move WHERE journal_id = %s AND period_id = %s ORDER BY id limit 1', (context['journal_id'],context['period_id']))
        res = cr.fetchone()
        # if res:
        #     if res[1] != 'draft':
        #         raise osv.except_osv(_('User Error!'),
        #                _('The account move (%s) for centralisation ' \
        #                         'has been confirmed.') % res[2])
        return res

