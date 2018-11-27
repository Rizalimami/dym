import time
import calendar

from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
from datetime import date, datetime, timedelta
from lxml import etree
from openerp.osv.orm import setup_modifiers
from dateutil.relativedelta import relativedelta
from openerp import tools
from openerp import api
from openerp.tools import float_is_zero

import openerp
import openerp.addons.decimal_precision as dp

class dym2_asset_tambah_value(osv.osv_memory):
    _name = "dym2.split.amortisasi.line"
    _description = "Split Amortisasi Asset"

    def _get_analytic_company(self, cr, uid, context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    _columns = {
        'amortisasi_id' : fields.many2one('dym2.split.amortisasi', 'Amortisasi'),
        'branch_id' : fields.many2one('dym.branch', 'Branch', required=True),
        'analytic_1' : fields.many2one('account.analytic.account', 'Account Analytic Company'),
        'analytic_2' : fields.many2one('account.analytic.account', 'Account Analytic Bisnis Unit'),
        'analytic_3' : fields.many2one('account.analytic.account', 'Account Analytic Branch'),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Account Analytic Cost Center'),
        'amount' : fields.float('Value', required=True),
    }    
    _defaults = {
        'first_day_of_month':True,
        'analytic_1':_get_analytic_company,
    }

    def change_reset(self, cr, uid, ids, field, context=None):
        res = {}
        if field in ('analytic_2','branch'):
            res['analytic_3'] = False
            res['account_analytic_id'] = False
        if field == 'analytic_3':
            res['account_analytic_id'] = False
        result = {}
        result['value'] = res
        return result

class dym2_split_amortisasi(osv.osv_memory):
    _name = "dym2.split.amortisasi"
    _description = "Split Amortisasi"
    _columns = {
        'depre_line_id' : fields.many2one('account.asset.depreciation.line', 'Depreciation Line ID'),
        'total_amortisasi' : fields.float('Total Amortisasi'),
        'amortisation_lines': fields.one2many('dym2.split.amortisasi.line', 'amortisasi_id')
    }    
    _defaults = {
        'depre_line_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("Data Error, please try to refresh page or contact your administrator!"))
        res = super(dym2_split_amortisasi, self).default_get(cr, uid, fields, context=context)
        depre_line_id = context and context.get('active_id', False) or False
        depreciation_line = self.pool.get('account.asset.depreciation.line').browse(cr, uid, depre_line_id, context=context)
        analytic_1 = depreciation_line.asset_id.category_id.analytic_1.id
        analytic_2 = depreciation_line.asset_id.category_id.analytic_2.id
        analytic_3 = depreciation_line.asset_id.category_id.analytic_3.id
        account_analytic_id = depreciation_line.asset_id.category_id.account_analytic_id.id
        if not analytic_1 or not analytic_2 or not analytic_3 or not account_analytic_id:
            analytic_2 = analytic_3 = account_analytic_id = False
            company = self.pool.get('res.users').browse(cr, uid, uid).company_id
            level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
            if not level_1_ids:
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan data analytic untuk company %s")%(company.name))
            analytic_1 = level_1_ids[0]
        amortisation_lines = [[0,0,{'branch_id': depreciation_line.asset_id.branch_id.id, 'analytic_1': analytic_1, 'analytic_2': analytic_2, 'analytic_3': analytic_3, 'account_analytic_id': account_analytic_id, 'amount': depreciation_line.amount}]]
        res['amortisation_lines'] = amortisation_lines
        res['total_amortisasi'] = depreciation_line.amount
        return res

    def create_move(self, cr, uid, ids, context=None):
        for data in self.browse(cr, uid, ids, context=context):
            akumulasi_amortisasi = 0
            branch_ids = []
            for y in data.amortisation_lines:
                if y.branch_id.id in branch_ids:
                    raise osv.except_osv(_('Warning!'), _('Detail branch %s duplicate, mohon dicek kembali!')%(y.branch_id.name))
                branch_ids.append(y.branch_id.id)
                if y.amount <= 0:
                    raise osv.except_osv(_('Warning!'), _('nilai amount untuk branch %s harus lebih dari 0')%(y.branch_id.name))
                akumulasi_amortisasi += y.amount
            if akumulasi_amortisasi != data.total_amortisasi:
                raise osv.except_osv(_('Warning!'), _('Total amortisasi yang di split (%s) tidak sama dengan total amortisasi seharusnya (%s) \n Perbedaan nilai amortisasi = %s')%(akumulasi_amortisasi, data.total_amortisasi, (data.total_amortisasi-akumulasi_amortisasi)))
            context = dict(context or {})
            can_close = False
            asset_obj = self.pool.get('account.asset.asset')
            period_obj = self.pool.get('account.period')
            move_obj = self.pool.get('account.move')
            move_line_obj = self.pool.get('account.move.line')
            currency_obj = self.pool.get('res.currency')
            created_move_ids = []
            asset_ids = []
            for line in data.depre_line_id:
                depreciation_date = context.get('depreciation_date') or line.depreciation_date or time.strftime('%Y-%m-%d')
                period_ids = period_obj.find(cr, uid, depreciation_date, context=context)
                company_currency = line.asset_id.company_id.currency_id.id
                current_currency = line.asset_id.currency_id.id
                context.update({'date': depreciation_date})
                sign = (line.asset_id.category_id.journal_id.type == 'purchase' and 1) or -1
                asset_name = "/"
                reference = line.asset_id.name
                move_vals = {
                    'name': asset_name,
                    'date': depreciation_date,
                    'ref': reference,
                    'period_id': period_ids and period_ids[0] or False,
                    'journal_id': line.asset_id.category_id.journal_id.id,
                    'transaction_id':line.asset_id.id,
                    'model':line.asset_id.__class__.__name__,
                    }
                move_id = move_obj.create(cr, uid, move_vals, context=context)
                journal_id = line.asset_id.category_id.journal_id.id
                partner_id = line.asset_id.partner_id.id
                move_line_obj.create(cr, uid, {
                    'name': asset_name,
                    'ref': reference,
                    'move_id': move_id,
                    'account_id': line.asset_id.category_id.account_depreciation_id.id,
                    'debit': 0.0,
                    'credit': data.total_amortisasi,
                    'period_id': period_ids and period_ids[0] or False,
                    'journal_id': journal_id,
                    'currency_id': company_currency != current_currency and  current_currency or False,
                    'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
                    'date': depreciation_date,
                    'branch_id': line.asset_id.analytic_3.branch_id.id or line.asset_id.branch_id.id,
                    'division': 'Umum',
                    'analytic_account_id' : line.asset_id.analytic_4.id,
                })
                for x in data.amortisation_lines:
                    amount = currency_obj.compute(cr, uid, current_currency, company_currency, x.amount, context=context)
                    analytic = line.asset_id.analytic_4
                    categ_id = False
                    if analytic.type == 'normal':
                        if analytic.segmen == 2 and not categ_id:
                            categ_id = analytic.bisnis_unit
                    while (analytic.parent_id and not categ_id):
                        analytic = analytic.parent_id
                        if analytic.type == 'normal':
                            if analytic.segmen == 2 and not categ_id:
                                categ_id = analytic.bisnis_unit
                    analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, x.branch_id, '', categ_id, 4, line.asset_id.analytic_4.cost_center)
                    move_line_obj.create(cr, uid, {
                        'name': asset_name,
                        'ref': reference,
                        'move_id': move_id,
                        'account_id': line.asset_id.category_id.account_expense_depreciation_id.id,
                        'credit': 0.0,
                        'debit': amount,
                        'period_id': period_ids and period_ids[0] or False,
                        'journal_id': journal_id,
                        'currency_id': company_currency != current_currency and  current_currency or False,
                        'amount_currency': company_currency != current_currency and sign * line.amount or 0.0,
                        'date': depreciation_date,
                        'asset_id': line.asset_id.id,
                        'branch_id': x.branch_id.id,
                        'division': 'Umum',
                        'analytic_account_id': analytic_4,
                    })
                self.pool.get('account.asset.depreciation.line').write(cr, uid, line.id, {'move_id': move_id}, context=context)
                created_move_ids.append(move_id)
                asset_ids.append(line.asset_id.id)
            # we re-evaluate the assets to determine whether we can close them
            for asset in asset_obj.browse(cr, uid, list(set(asset_ids)), context=context):
                if currency_obj.is_zero(cr, uid, asset.currency_id, asset.value_residual):
                    asset.write({'state': 'close'})
            move_lines = self.pool.get('account.move').browse(cr,uid,created_move_ids)
            periods = self.pool.get('account.period').find(cr, uid, context=context)
            for move_line in move_lines :
                get_name = self.pool.get('ir.sequence').get_per_branch(cr,uid,[data.depre_line_id.asset_id.branch_id.id], move_line.journal_id.code) 
                move_line.write({'name':get_name})
        return {}

class dym2_asset_tambah_value_history(osv.osv):
    _name="dym2.tambah.value.history"

    _columns = {
        'asset_id' : fields.many2one('account.asset.asset', 'Asset ID'),
        'date': fields.date('Date'),
        'value' : fields.float('Value'),
        }

class dym2_asset_tambah_value(osv.osv_memory):
    _name = "dym2.asset.tambah.value"
    _description = "Penambahan Value Asset"
    _columns = {
        'value' : fields.float('Value', required=True),
        'asset_id' : fields.many2one('account.asset.asset', 'Asset ID', required=True),
    }    
    _defaults = {
        'asset_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False
    }

    def tambah_value(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for data in self.browse(cr, uid, ids, context=context):
            self.pool.get('dym2.tambah.value.history').create(cr, uid, {
                'asset_id': data.asset_id.id,
                'value': data.value,
                'date': datetime.today(),
            })
        return {}

class dym2_asset_transfer_beban_history(osv.osv):
    _name="dym2.transfer.beban.history"

    _columns = {
        'asset_id' : fields.many2one('account.asset.asset', 'Asset ID'),
        'date': fields.date('Date'),
        'branch_from' : fields.many2one('dym.branch', 'From'),
        'branch_to' : fields.many2one('dym.branch', 'To'),
    }

class dym2_asset_transfer_beban(osv.osv_memory):
    _name = "dym2.asset.transfer.beban"
    _description = "Transfer Pembebanan Asset"
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym2_asset_transfer_beban, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company_id),('type','=','normal'),('state','not in',('close','cancelled'))])
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='analytic_2']")
        for node in nodes_branch :
            node.set('domain', "[('segmen','=',2),('type','=','normal'),('state','not in',('close','cancelled')),('parent_id','child_of',"+str(level_1_ids)+")]")
        res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'branch_id' : fields.many2one('dym.branch', 'Branch', required=True),
        'asset_id' : fields.many2one('account.asset.asset', 'Asset ID', required=True),
        'analytic_2' : fields.many2one('account.analytic.account', 'Account Analytic Bisnis Unit'),
        'analytic_3' : fields.many2one('account.analytic.account', 'Account Analytic Branch'),
        'analytic_4' : fields.many2one('account.analytic.account', 'Account Analytic Cost Center'),
    }

    _defaults = {
        'asset_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False
    }

    def change_reset(self, cr, uid, ids, field, context=None):
        res = {}
        if field == 'branch':
            res['analytic_2'] = False
            res['analytic_3'] = False
            res['analytic_4'] = False
        if field == 'analytic_2':
            res['analytic_3'] = False
            res['analytic_4'] = False
        if field == 'analytic_3':
            res['analytic_4'] = False
        result = {}
        result['value'] = res
        return result

    def transfer_child(self, cr, uid, child_ids, data, context=None):
        for asset in child_ids:            
            self.pool.get('dym2.transfer.beban.history').create(cr, uid, {
                'asset_id': asset.id,
                'branch_from': asset.branch_id.id,
                'branch_to': data.branch_id.id,
                'date': datetime.today(),
            })
            self.pool.get('account.asset.asset').write(cr, uid, [asset.id], {
                'branch_id':data.branch_id.id,
                'analytic_2':data.analytic_2.id,
                'analytic_3':data.analytic_3.id,
                'analytic_4':data.analytic_4.id,
            }, context)
            self.transfer_child(cr, uid, asset.child_ids, data, context=context)
        return True

    def transfer_beban(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for data in self.browse(cr, uid, ids, context=context):
            if data.branch_id.id == data.asset_id.branch_id.id:
                raise osv.except_osv(_('Warning!'), _('Beban asset telah terdaftar di branch %s sebelumnya')%(data.branch_id.name))

            self.pool.get('dym2.transfer.beban.history').create(cr, uid, {
                'asset_id': data.asset_id.id,
                'branch_from': data.asset_id.branch_id.id,
                'branch_to': data.branch_id.id,
                'date': datetime.today(),
            })
            self.pool.get('account.asset.asset').write(cr, uid, [data.asset_id.id], {
                'branch_id':data.branch_id.id,
                'analytic_2':data.analytic_2.id,
                'analytic_3':data.analytic_3.id,
                'analytic_4':data.analytic_4.id,
            }, context)
            # self.transfer_child(cr, uid, data.asset_id.child_ids, data, context=context)
        return {}

class account_period_close(osv.osv_memory):
    _inherit = "account.period.close"
    
    def data_save(self, cr, uid, ids, context=None):
        journal_period_pool = self.pool.get('account.journal.period')
        period_pool = self.pool.get('account.period')
        account_move_obj = self.pool.get('account.move')
        obj_depreciation_line = self.pool.get('account.asset.depreciation.line')

        for pad in period_pool.browse(cr, uid, context['active_ids']).sorted(key=lambda r: r.date_start):
            open_period_ids = period_pool.search(cr, uid, [('company_id','=',pad.company_id.id),('date_stop','<',pad.date_start),('state','=','draft'),('id','not in',context['active_ids'])])
            if open_period_ids:
                raise osv.except_osv(_('Invalid Action!'), _('In order to close a period, you must first close earlier period.'))
            did = obj_depreciation_line.search(cr, uid, [('depreciation_date', '>=', pad.date_start), ('depreciation_date', '<=', pad.date_stop), ('asset_id.company_id', '=', pad.company_id.id), ('move_check', '=', False)])
            if did :
                dad = obj_depreciation_line.browse(cr, uid, did)
                obj_depreciation_line.create_move(cr, uid, [x.id for x in dad])

            mid = account_move_obj.search(cr, uid, [('period_id', '=', pad.id), ('state', '=', "draft")], context=context)
            if mid :
                account_move_obj.button_validate(cr, uid, mid)
        
        mode = 'done'
        for form in self.read(cr, uid, ids, context=context):
            if form['sure']:
                for id in context['active_ids']:
                    account_move_ids = account_move_obj.search(cr, uid, [('period_id', '=', id), ('state', '=', "draft")], context=context)
                    if account_move_ids:
                        raise osv.except_osv(_('Invalid Action!'), _('In order to close a period, you must first post related journal entries.'))

                    cr.execute('update account_journal_period set state=%s where period_id=%s', (mode, id))
                    cr.execute('update account_period set state=%s where id=%s', (mode, id))
                    self.invalidate_cache(cr, uid, context=context)

        return {'type': 'ir.actions.act_window_close'}


class dym3_asset_category(osv.osv):
    _inherit = "account.asset.category"

    _columns = {
        'yearly_prorate': fields.boolean(string="Yearly Prorate", help="If this option checked and asset depreciation calculated yearly then amount depreciated will be prorated pe month. e.g Monthly Depreciation = Yearly depreciation / 12 * (12 - purchase month)"),
        'journal_acq_id': fields.many2one('account.journal', 'Acquisition Journal', required=False, help='Acquisition Journal'),
    }

    def onchange_method_number(self, cr, uid, ids, method_number, yearly_prorate, context=None):
        res = {'value':{}}
        if yearly_prorate == True:
            for categ in self.browse(cr, uid, ids, context=context):
                if categ.method_number > max_year_asset:
                    res['value'].update({
                        'method_number':max_year_asset,
                    })
            res['value'].update({
                'method_period':12,
            })
        return res

class dym_asset(osv.osv):
    _inherit = "account.asset.asset"
                
    def change_reset(self, cr, uid, ids, field, context=None):
        res = {}
        if field == 'branch':
            res['location_id'] = False
            res['analytic_2'] = False
            res['analytic_3'] = False
            res['analytic_4'] = False
        if field == 'analytic_2':
            res['analytic_3'] = False
            res['analytic_4'] = False
        if field == 'analytic_3':
            res['analytic_4'] = False
        result = {}
        result['value'] = res
        return result

    def update_asset(self, cr, uid, child_ids, vals, context=None):
        for asset in child_ids:    
            if asset.state not in ['sold','scrap']:
                asset.write(vals) 
            self.update_asset(cr, uid, asset.child_ids, vals, context=context)
        return True
        
    def _real_value_residual(self, cr, uid, ids, name, args, context=None):
        cr.execute("""SELECT
                l.asset_id as id, SUM(abs(l.debit-l.credit)) AS amount
            FROM
                account_move_line l
            WHERE
                l.asset_id IN %s GROUP BY l.asset_id """, (tuple(ids),))
        res=dict(cr.fetchall())
        for asset in self.browse(cr, uid, ids, context):
            company_currency = asset.company_id.currency_id.id
            current_currency = asset.currency_id.id
            amount = self.pool['res.currency'].compute(cr, uid, company_currency, current_currency, res.get(asset.id, 0.0), context=context)
            res[asset.id] = asset.real_purchase_value - amount - asset.salvage_value
        for id in ids:
            res.setdefault(id, 0.0)
        return res

    def get_child_residual(self, cr, uid, child_ids, total_child_residual, context=None):
        for asset in child_ids:
            total_child_residual += asset.real_value_residual
            for tambah in asset.tambah_value_history_ids:
                total_child_residual += tambah.value
            total_child_residual += self.get_child_residual(cr, uid, asset.child_ids, 0)
        return total_child_residual

    def _amount_residual(self, cr, uid, ids, name, args, context=None):
        res={}
        for asset in self.browse(cr, uid, ids, context):
            total_child_residual = 0
            total_child_residual += self.get_child_residual(cr, uid, asset.child_ids, total_child_residual)
            total_penambahan_value = 0
            for tambah in asset.tambah_value_history_ids:
                total_penambahan_value += tambah.value
            amount_residual = total_child_residual + asset.real_value_residual + total_penambahan_value
            res[asset.id] = amount_residual
        return res

    def get_child_purchase(self, cr, uid, child_ids, total_child_purchase, context=None):
        for asset in child_ids:
            total_child_purchase += asset.real_purchase_value
            total_child_purchase += self.get_child_purchase(cr, uid, asset.child_ids, 0)
        return total_child_purchase

    def _get_purchase_value(self, cr, uid, ids, name, args, context=None):
        res={}
        for asset in self.browse(cr, uid, ids, context):
            total_child_purchase = 0
            total_child_purchase += self.get_child_purchase(cr, uid, asset.child_ids, total_child_purchase)
            res[asset.id] = asset.real_purchase_value + total_child_purchase
        return res

    def get_child_depre(self, cr, uid, child_ids, child_depre_ids, context=None):
        for asset in child_ids:
            depreciation_line_ids = self.pool.get('account.asset.depreciation.line').search(cr, uid, [('asset_id', '=', asset.id)],order='depreciation_date asc')
            child_depre_ids += depreciation_line_ids
            child_depre_ids += self.get_child_depre(cr, uid, asset.child_ids, [])
        return child_depre_ids

    def _get_depre_lines(self, cr, uid, ids, field_names, arg=None, context=None):
        res={}
        for asset in self.browse(cr, uid, ids, context):
            child_depre_ids = []
            child_depre_ids += self.get_child_depre(cr, uid, asset.child_ids, child_depre_ids)
            depreciation_line_ids = self.pool.get('account.asset.depreciation.line').search(cr, uid, ['|',('asset_id', '=', asset.id),('id', 'in', child_depre_ids)],order='depreciation_date asc')
            res[asset.id] = depreciation_line_ids
        return res

    def get_child_count(self, cr, uid, child_ids, child_line_count, context=None):
        for asset in child_ids:
            move_line_count = self.pool.get('account.move.line').search_count(cr, uid, [('asset_id', '=', asset.id)], context=context)
            child_line_count += move_line_count
            child_line_count += self.get_child_count(cr, uid, asset.child_ids, 0)
        return child_line_count

    def _entry_count(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for asset in self.browse(cr, uid, ids, context):
            child_line_count = 0
            child_line_count += self.get_child_count(cr, uid, asset.child_ids, child_line_count)
            move_line_count = self.pool.get('account.move.line').search_count(cr, uid, [('asset_id', '=', asset.id)], context=context)
            res[asset.id] = move_line_count + child_line_count
        return res
    
    def get_child_asset(self, cr, uid, child_ids, asset_ids, context=None):
        for asset in child_ids:
            asset_ids += [asset.id]
            asset_ids += self.get_child_asset(cr, uid, asset.child_ids, [])
        return asset_ids

    def open_entries(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        asset_ids = []
        for asset in self.browse(cr, uid, ids, context):
            asset_ids += [asset.id]
            asset_ids += self.get_child_asset(cr, uid, asset.child_ids, [])
        move_line_ids = self.pool.get('account.move.line').search(cr, uid, [('asset_id', 'in', asset_ids)], context=context)
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'dym_account_move', 'dym_journal_items_action'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        action['context'] = {}
        action['domain'] = "[('id','in',[" + ','.join(map(str, move_line_ids)) + "])]"
        return action

    _columns = {
        'entry_count': fields.function(_entry_count, string='# Asset Entries', type='integer'),
        'confirm_uid':fields.many2one('res.users',string="Validated by"),
        'confirm_date':fields.datetime('Validated on'),
        'gl_date':fields.date('GL Date', help="GL Date is an acquisition date where an asset will be cofirmed started to be depreciated."),
        'acq_move_id': fields.many2one('account.move', string='Acquisition Move'),
        'branch_id': fields.many2one('dym.branch', string='User Branch'),
        'division':fields.selection([('Umum','Umum')], 'Division', select=True),   
        'product_id' : fields.many2one('product.product',string="Product"),
        'purchase_id' : fields.many2one('purchase.order',string="Purchase No"),
        'invoice_id' : fields.many2one('account.invoice',string="Invoice No"), 
        'category_id': fields.many2one('account.asset.category', 'Asset Category',required=True, change_default=True, readonly=True, states={'draft':[('readonly',False)]}),
        'categ_type' : fields.related('category_id','type',type='char',string="Type"),
        'received' : fields.boolean(string="Received"),
        'receive_id' : fields.many2one('dym.transfer.asset',string="Receipt No"),
        'register_prepaid_id' : fields.many2one('dym2.register.prepaid',string="Register Prepaid No"),
        'responsible_id' : fields.many2one('hr.employee',string="Responsible"),
        'cost_centre_id' : fields.related('branch_id','profit_centre',relation="stock.warehouse",type="char",string="Cost Centre"),
        'asset_classification_id' : fields.related('category_id','asset_classification_id',relation='dym.asset.classification',type='many2one',readonly=True,string="Asset Classification"),
        'code': fields.char('Asset Code', readonly=True,copy=False),
        'account_asset_id' : fields.related('category_id','account_asset_id',relation='account.account',type='many2one',readonly=True,string="Asset Account"),
        'account_depreciation_id' : fields.related('category_id','account_depreciation_id',relation='account.account',type='many2one',readonly=True,string="Depreciation Account"),
        'account_expense_depreciation_id' : fields.related('category_id','account_expense_depreciation_id',relation='account.account',type='many2one',readonly=True,string="Depr. Expense Account"),
        'real_purchase_value' : fields.float(string="Purchase Value"),
        'real_purchase_date' : fields.date(string="Purchase Date"),
        'asset_owner': fields.many2one('dym.branch', string='Asset Owner'),
        'asset_user': fields.many2one('hr.employee', string='User PIC'),
        'location_id': fields.many2one('stock.location', string='Location', domain="[('usage','=','internal')]"),
        'beban_history_ids': fields.one2many('dym2.transfer.beban.history', 'asset_id', string='Transfer Pembebanan History'),
        'value_residual': fields.function(_amount_residual, method=True, digits_compute=dp.get_precision('Account'), string='NBV / Residual Value'),
        'real_value_residual': fields.function(_real_value_residual, method=True, digits_compute=dp.get_precision('Account'), string='Real Residual Value'),
        'tambah_value_history_ids': fields.one2many('dym2.tambah.value.history', 'asset_id', string='Penambahan Value History'),
        'purchase_value': fields.function(_get_purchase_value, method=True, digits_compute=dp.get_precision('Account'), string='Gross Value', readonly=True),
        'depreciation_line_ids': fields.function(_get_depre_lines, type='one2many', relation="account.asset.depreciation.line", string="Depreciation Lines", readonly=True),
        'method_number': fields.integer('Number of Depreciations', readonly=True, states={'draft':[('readonly',False)]}, help="The number of depreciations needed to depreciate your asset"),
        'method_period': fields.integer('Number of Months in a Period', required=True, readonly=True, states={'draft':[('readonly',False)]}, help="The amount of time between two depreciations, in months"),
        'method_end': fields.date('Ending Date', readonly=True, states={'draft':[('readonly',False)]}),
        'method_progress_factor': fields.related('category_id','method_progress_factor', string='Degressive Factor', type='float',  digits_compute=dp.get_precision('Degressive')),
        'method_time': fields.selection([('number','Number of Depreciations'),('end','Ending Date')], 'Time Method', required=True, readonly=True, states={'draft':[('readonly',False)]},
                          help="Choose the method to use to compute the dates and number of depreciation lines.\n"\
                               "  * Number of Depreciations: Fix the number of depreciation lines and the time between 2 depreciations.\n" \
                               "  * Ending Date: Choose the time between 2 depreciations and the date the depreciations won't go beyond."),
        'prorata':fields.boolean('Prorata Temporis', readonly=True, states={'draft':[('readonly',False)]}, help='Indicates that the first depreciation entry for this asset have to be done from the purchase date instead of the first January'),
        'first_day_of_month': fields.related('category_id', 'first_day_of_month', type='boolean', string='First day of Month', store=False, readonly=True),
        'yearly_prorate': fields.related('category_id', 'yearly_prorate', type='boolean', string='Yearly Prorate', store=False, readonly=True),
    }

    _defaults = {
        'division' : 'Umum',
    }
    
    _sql_constraints = [
        ('unique_name_asset_code', 'unique(code)', 'Code/Reference Asset duplicate mohon periksa kembali data anda !'),
    ]        
    def write(self, cr, uid, ids, val, context=None):
        if context is None:
            context = {}
        if 'category_id' in val:
            categ = self.pool.get('account.asset.category').browse(cr, uid, val['category_id'])
            if 'method' not in val:
                val['method'] = categ.method
            if 'method_number' not in val:
                val['method_number'] = categ.method_number
            if 'method_period' not in val:
                val['method_period'] = categ.method_period
            if 'method_end' not in val:
                val['method_end'] = categ.method_end
            if 'method_progress_factor' not in val:
                val['method_progress_factor'] = categ.method_progress_factor
            if 'method_time' not in val:
                val['method_time'] = categ.method_time
            if 'prorata' not in val:
                val['prorata'] = categ.prorata
            if 'first_day_of_month' not in val:
                val['first_day_of_month'] = categ.first_day_of_month
        res = super(dym_asset, self).write(cr, uid, ids, val, context=context)
        return res

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            tit = "[%s] %s" % (str(record.code), record.name)
            res.append((record.id, tit))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []        
        if name and len(name) >= 3:
            ids = self.search(cr, uid, [('code', operator, name)] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context or {})
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context or {})
        return self.name_get(cr, uid, ids, context or {})
        
    def onchange_yearly_prorate(self, cr, uid, ids, yearly_prorate, context=None):
        res = {'value':{}}
        if yearly_prorate == True:
            res['value'].update({
                'method_period':1,
            })
        return res

    def onchange_category_id(self, cr, uid, ids, category_id, context=None):
        res = {}
        res = super(dym_asset,self).onchange_category_id(cr, uid, ids, category_id, context=context)
        asset_categ_obj = self.pool.get('account.asset.category')
        if category_id:
            category_obj = asset_categ_obj.browse(cr, uid, category_id, context=context)
            res['value'].update({'first_day_of_month': category_obj.first_day_of_month})
            asset = self.browse(cr, uid, ids)
        return res

    def create_move_acquisition_old(self, cr, uid, ids, context=None):
        context = dict(context or {})
        can_close = False
        asset_obj = self.pool.get('account.asset.asset')
        period_obj = self.pool.get('account.period')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        created_move_ids = []
        asset_ids = self.search(cr, uid, [('state','=','draft')])
        self.compute_depreciation_board(cr, uid, asset_ids, context=None)
        for line in self.browse(cr, uid, asset_ids, context=context):
            company_currency = line.company_id.currency_id.id
            current_currency = line.currency_id.id
            context.update({'date': '2016-02-29'})
            acquisition_date = '2016-02-29'
            amount = currency_obj.compute(cr, uid, current_currency, company_currency, line.purchase_value, context=context)
            asset_name = "/"
            reference = line.name
            if line.company_id.id == 8:
                period_id = 60
                ap_suspense = 19118
            else:
                period_id = 46
                ap_suspense = 19804

            move_vals = {
                'name': asset_name,
                'date': acquisition_date,
                'ref': reference,
                'period_id': period_id,
                'journal_id': line.category_id.journal_id.id,
                'company_id': line.company_id.id,
                'transaction_id':line.id,
                'model':line.__class__.__name__,
                }
            move_id = move_obj.create(cr, uid, move_vals, context=context)
            journal_id = line.category_id.journal_id.id
            move_line_obj.create(cr, uid, {
                'name': asset_name,
                'ref': reference,
                'move_id': move_id,
                'account_id': ap_suspense,
                'debit': 0.0,
                'credit': amount,
                'period_id': period_id,
                'journal_id': journal_id,
                'analytic_4': line.analytic_4.id,
                'date': acquisition_date,
                # 'asset_id': line.id,
                'analytic_account_id' : line.analytic_4.id,
                'branch_id': line.analytic_3.branch_id.id or line.branch_id.id,
                'division': 'Umum',
            })
            move_line_obj.create(cr, uid, {
                'name': asset_name,
                'ref': reference,
                'move_id': move_id,
                'account_id': line.account_asset_id.id,
                'credit': 0.0,
                'debit': amount,
                'period_id': period_id,
                'journal_id': journal_id,
                'analytic_4': line.analytic_4.id,
                'date': acquisition_date,
                'analytic_account_id' : line.analytic_4.id,
                'branch_id': line.analytic_3.branch_id.id or line.branch_id.id,
                'division': 'Umum',
        })
            created_move_ids.append(move_id)
        return created_move_ids


    def _create_move_acquisition(self, cr, uid, ids, asset, context=None):

        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        period_obj = self.pool.get('account.period')
        trf_asset_obj = self.pool.get('dym.transfer.asset')
        branch_config_obj = self.pool.get('dym.branch.config')
        gl_date = asset.gl_date
        period_id = period_obj.find(cr, uid, gl_date, context=context)
        if not period_id:
            raise osv.except_osv(
                'Configuration Error', '''There is no Open Period for the GL Date of %s''' % asset.gl_date)

        reference = '%s' % asset.code
        asset_name = asset.name

        if not asset.category_id.journal_acq_id:
            raise osv.except_osv(
                'Configuration Error', '''Journal Acquisition is not set at Asset Category''')

        if not asset.category_id.journal_acq_id.default_debit_account_id:
            raise osv.except_osv(
                'Configuration Error', '''Journal Acquisition does not have "Default Debit Account".''')

        if not asset.category_id.journal_acq_id.default_credit_account_id:
            raise osv.except_osv(
                'Configuration Error', '''Journal Acquisition does not have "Default Credit Account".''')

        journal_id = asset.category_id.journal_acq_id
        account_debit = asset.category_id.account_asset_id
        account_credit = asset.category_id.journal_acq_id.default_credit_account_id
        amount = asset.purchase_value
        register_type = asset.receive_id.register_type
        branch_config_ids = branch_config_obj.search(cr,uid,[('branch_id','=',asset.branch_id.id)])
        branch_config = branch_config_obj.browse(cr,uid,asset.branch_id.id)

        move_vals = {
            'name': asset_name,
            'date': asset.gl_date,
            'ref': reference,
            'period_id': period_id[0],
            'journal_id': journal_id.id,
            'company_id': asset.company_id.id,
            'model':asset.__class__.__name__,
        }
        move_id = move_obj.create(cr, uid, move_vals, context=context)
        if register_type == 'stock':
            discount = asset.receive_id.transfer_ids2[0].discount
            price_unit = amount - discount
            analytic_4 = asset.receive_id.transfer_ids2[0].analytic_4

            analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, asset.branch_id.id, 'Unit',False, 4, 'General')
            analytic_1_sales, analytic_2_sales, analytic_3_sales, analytic_4_sales = self.pool.get('account.analytic.account').get_analytical(cr, uid, asset.branch_id.id, 'Unit',False, 4, 'Sales')

            if not branch_config.account_register_asset_ppn_keluaran:
                raise osv.except_osv(
                    'Configuration Error', '''Please set Account Register Asset Persediaan di Branch Configuration.''')

            if not branch_config.account_register_discount_subsidi_external:
                raise osv.except_osv(
                    'Configuration Error', '''Please set Account Register Discount Subsidi External di Branch Configuration.''')

            if not branch_config.account_register_asset_persediaan:
                raise osv.except_osv(
                    'Configuration Error', '''Please set Account Register Asset Persediaan di Branch Configuration.''')

            # discount
            move_disc = {
                'name': asset_name,
                'ref': reference,
                'move_id': move_id,
                'account_id': branch_config.account_register_discount_subsidi_external.id,
                'credit': 0.0,
                'debit': discount,
                'period_id': period_id[0],
                'journal_id': journal_id.id,
                'analytic_4': analytic_4_sales,
                'date': gl_date,
                'analytic_account_id' : analytic_4_sales,
                'branch_id': asset.analytic_3.branch_id.id or asset.branch_id.id,
                'division': asset.division,
            }
            move_line_obj.create(cr, uid, move_disc)

        credit_vals = {
            'name': asset_name,
            'ref': reference,
            'move_id': move_id,
            'account_id': account_credit.id if register_type != 'stock' else branch_config.account_register_asset_persediaan.id,
            'debit': 0.0,
            'credit': amount,
            'period_id': period_id[0],
            'journal_id': journal_id.id,
            'analytic_4': asset.analytic_4.id if register_type != 'stock' else analytic_4_general,
            'date': gl_date,
            # 'asset_id': line.id,
            'analytic_account_id' : asset.analytic_4.id if register_type != 'stock' else analytic_4_general,
            'branch_id': asset.analytic_3.branch_id.id or asset.branch_id.id,
            'division': asset.division,
        }

        debit_vals = {
            'name': asset_name,
            'ref': reference,
            'move_id': move_id,
            'account_id': account_debit.id,
            'credit': 0.0,
            'debit': amount if register_type != 'stock' else price_unit,
            'period_id': period_id[0],
            'journal_id': journal_id.id,
            'analytic_4': asset.analytic_4.id if register_type != 'stock' else analytic_4.id,
            'date': gl_date,
            'analytic_account_id' : asset.analytic_4.id if register_type != 'stock' else analytic_4.id,
            'branch_id': asset.analytic_3.branch_id.id or asset.branch_id.id,
            'division': asset.division,
        }

        move_line_obj.create(cr, uid, credit_vals)
        move_line_obj.create(cr, uid, debit_vals)
        return move_id
            
    def validate(self, cr, uid, ids, context=None):
        for asset in self.browse(cr, uid, ids, context=context):
            journal_acq_id = asset.category_id.journal_acq_id
            if not journal_acq_id:
                raise osv.except_osv(
                    'Configuration Error', '''Please set Journal Acquisiton at Asset Category to continue''')
            if not asset.gl_date:
                raise osv.except_osv(
                    'Configuration Error', '''Please set GL Date to continue''')

            if asset.acq_move_id:
                raise osv.except_osv(
                    'Configuration Error', '''Acquisition move already exist, please remove it first to continue''')

            move_id = self._create_move_acquisition(cr, uid, ids, asset, context=None)
            asset.acq_move_id = move_id

        vals = super(dym_asset,self).validate(cr,uid,ids,context=context)
        for asset in self.browse(cr, uid, ids, context=context):
            # if asset.category_id.cip == True: 
            #     raise osv.except_osv(_('Error!'), _('You cannot validate an asset with category CIP.'))
            if asset.state == 'draft':
                self.write(cr, uid, [asset.id], {
                    'confirm_uid':uid,'confirm_date':datetime.now()
                }, context)
        return vals
    
    def unlink(self, cr, uid, ids, context=None):
        for asset in self.browse(cr, uid, ids, context=context):
            if asset.account_move_line_ids: 
                raise osv.except_osv(_('Error!'), _('You cannot delete an asset that contains posted depreciation lines.'))
        return super(dym_asset, self).unlink(cr, uid, ids, context=context)

    def set_to_close(self, cr, uid, ids, context=None):
        for asset in self.browse(cr, uid, ids, context=context):
            if asset.state in ['open','approved']:
                self.write(cr, uid, asset.id, {'state': 'close'}, context=context)
            # asset.child_ids.set_to_close()
        return True
        
    def set_to_draft(self, cr, uid, ids, context=None):
        asset_ids = self.search(cr, uid, [('state','=','open')])

        self.compute_depreciation_board(cr, uid, asset_ids, context=None)
        #     if asset.state == 'open':
        #         self.write(cr, uid, asset.id, {'state': 'draft'}, context=context)
            # asset.child_ids.set_to_draft()
        return True

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_asset, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
         
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_id']")
        nodes_categ = doc.xpath("//field[@name='category_id']")        
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        if context.get('type') == 'prepaid' :
            for node in nodes_categ:
                node.set('domain', '[("type","=","prepaid")]') 
        else  :       
            for node in nodes_categ:
                node.set('domain', '[("type","=","fixed")]')                 
        res['arch'] = etree.tostring(doc)           
        return res
    
    def create(self,cr,uid,vals,context=None):
        categori = self.pool.get('account.asset.category')
        sequence = self.pool.get('ir.sequence')
        if vals.get('purchase_value') :
            vals['real_purchase_value'] = vals.get('purchase_value')
        if vals.get('purchase_date') :
            vals['real_purchase_date'] = vals.get('purchase_date')
        if vals.get('category_id') :
            categ_id = categori.browse(cr,uid,[vals['category_id']])
            if not vals.get('method'):
                vals['method'] = categ_id.method
            if not vals.get('method_number'):
                vals['method_number'] = categ_id.method_number
            if not vals.get('method_period'):
                vals['method_period'] = categ_id.method_period
            if not vals.get('code'):
                trf_asset_obj = self.pool.get('dym.transfer.asset')
                trf_asset = trf_asset_obj.browse(cr, uid, vals['receive_id'])
                if trf_asset.register_type == 'stock':
                    vals['code'] = trf_asset.name
        res = super(dym_asset,self).create(cr,uid,vals,context=context)
        return res 

    def _compute_board_amount(self, cr, uid, asset, i, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date, context=None):
        #by default amount = 0
        amount = 0
        if i == undone_dotation_number:
            amount = residual_amount
        else:
            if asset.method == 'linear':
                amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
                if asset.prorata:
                    amount = amount_to_depr / asset.method_number
                    if i == 1:
                        purchase_date = datetime.strptime(asset.purchase_date, '%Y-%m-%d')
                        if asset.method_period % 12 != 0:
                            # Calculate depreciation for remaining days in the month
                            # Example: asset value of 120, monthly depreciation, 12 depreciations
                            #    (120 (Asset value)/ (12 (Number of Depreciations) * 1 (Period Length))) /  31 (days of month) * 12 (days to depreciate in purchase month)
                            month_days = calendar.monthrange(purchase_date.year, purchase_date.month)[1]
                            days = month_days - purchase_date.day + 1
                            amount = (amount_to_depr / (asset.method_number * asset.method_period)) / month_days * days
                        else:
                            # Calculate depreciation for remaining days in the year
                            # Example: asset value of 120, yearly depreciation, 12 depreciations
                            #    (120 (Asset value)/ (12 (Number of Depreciations) * 1 (Period Length, in years))) /  365 (days of year) * 75 (days to depreciate in purchase year)
                            year_days = 366 if purchase_date.year % 4 == 0 else 365
                            days = year_days - float(depreciation_date.strftime('%j')) + 1
                            amount = (amount_to_depr / (asset.method_number * (asset.method_period / 12))) / year_days * days
            elif asset.method == 'degressive':
                amount = residual_amount * asset.method_progress_factor
                if asset.prorata:
                    if i == 1:
                        purchase_date = datetime.strptime(asset.purchase_date, '%Y-%m-%d')
                        if asset.method_period % 12 != 0:
                            month_days = calendar.monthrange(purchase_date.year, purchase_date.month)[1]
                            days = month_days - purchase_date.day + 1
                            amount = (residual_amount * asset.method_progress_factor) / month_days * days
                        else:
                            year_days = 366 if purchase_date.year % 4 == 0 else 365
                            days = year_days - float(depreciation_date.strftime('%j')) + 1
                            amount = (residual_amount * asset.method_progress_factor * (asset.method_period / 12)) / year_days * days
        return amount

    def _compute_board_undone_dotation_nb(self, cr, uid, asset, depreciation_date, total_days, context=None):
        undone_dotation_number = asset.method_number
        if asset.method_time == 'end':
            end_date = datetime.strptime(asset.method_end, '%Y-%m-%d')
            undone_dotation_number = 0
            while depreciation_date <= end_date:
                depreciation_date = (datetime(depreciation_date.year, depreciation_date.month, depreciation_date.day) + relativedelta(months=+asset.method_period))
                undone_dotation_number += 1
        if asset.prorata:
            undone_dotation_number += 1
        return undone_dotation_number

    def compute_depreciation_board(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        depreciation_lin_obj = self.pool.get('account.asset.depreciation.line')
        currency_obj = self.pool.get('res.currency')
        
        for asset in self.browse(cr, uid, ids, context=context):
            if asset.value_residual == 0.0:
                continue
            if asset.category_id.cip:
                continue
            posted_depreciation_line_ids = depreciation_lin_obj.search(cr, uid, [('asset_id', '=', asset.id), ('move_check', '=', True)],order='depreciation_date desc')
            old_depreciation_line_ids = depreciation_lin_obj.search(cr, uid, [('asset_id', '=', asset.id), ('move_id', '=', False)])
            if old_depreciation_line_ids:
                depreciation_lin_obj.unlink(cr, uid, old_depreciation_line_ids, context=context)

            amount_to_depr = residual_amount = asset.value_residual

            if asset.prorata:
                depreciation_date = datetime.strptime(self._get_last_depreciation_date(cr, uid, [asset.id], context)[asset.id], '%Y-%m-%d')
            else:
                purchase_date = datetime.strptime(asset.purchase_date, '%Y-%m-%d')
                if (len(posted_depreciation_line_ids)>0):
                    last_depreciation_date = datetime.strptime(depreciation_lin_obj.browse(cr,uid,posted_depreciation_line_ids[0],context=context).depreciation_date, '%Y-%m-%d')
                    depreciation_date = (last_depreciation_date+relativedelta(months=+asset.method_period))
                else:
                    depreciation_date = datetime(purchase_date.year, purchase_date.month, 1) + relativedelta(months=+1)
                    depreciation_date = (datetime(depreciation_date.year, depreciation_date.month, 1) + relativedelta(days=-1))

            day = depreciation_date.day
            month = depreciation_date.month
            year = depreciation_date.year
            total_days = (year % 4) and 365 or 366

            precision_digits = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
            undone_dotation_number = self._compute_board_undone_dotation_nb(cr, uid, asset, depreciation_date, total_days, context=context)
            
            # YEARLY PRORATE
            if asset.yearly_prorate:
                if asset.method_period != 12:
                    raise osv.except_osv(
                        'Configuration Error', '''You have set depreciation calculation based on Yearly Prorate.
                            But the "Number of Months in a Period" is not set to 12 months.''')

                residual_amount2 = residual_amount 
                purchase_date = datetime.strptime(asset.purchase_date, '%Y-%m-%d')
                purchasedate = purchase_date + relativedelta(months=+1)
                depreciation_date = datetime(purchasedate.year,purchasedate.month,1) - timedelta(days=1)

                day = depreciation_date.day
                month = depreciation_date.month
                year = depreciation_date.year

                periods = 12 * undone_dotation_number
                amount_each = round(residual_amount / periods, precision_digits)
                if purchase_date.month != 1:
                    undone_dotation_number += 1

                counter = 0
                sum_amount = 0

                for x in range(len(posted_depreciation_line_ids), undone_dotation_number):
                    i = x + 1
                    undone_dotation_number2 = undone_dotation_number
                    if asset.method != 'degressive' and purchase_date.month != 1:
                        undone_dotation_number2 -= 1

                    amount = self._compute_board_amount(cr, uid, asset, i, residual_amount, amount_to_depr, undone_dotation_number2, posted_depreciation_line_ids, total_days, depreciation_date, context=context)
                    if float_is_zero(amount, precision_digits=precision_digits):
                        continue

                    monthes = 12
                    if i==1 and purchase_date.month != 1:
                        
                        monthes = 12 - purchase_date.month + 1
                        if asset.method == 'degressive':
                            amount = amount / 12 * monthes

                    if i==undone_dotation_number:
                        if purchase_date.month != 1:
                            monthes = purchase_date.month - 1
                        else:
                            monthes = 12
                    residual_amount -= amount
                    if asset.method == 'degressive' and monthes!=0:
                        amount_each = round(amount / monthes, precision_digits)
                    for m in range(monthes):
                        counter += 1
                        if counter == periods:
                            amount_each = amount_to_depr - sum_amount
                        sum_amount += amount_each
                        residual_amount2 -= amount_each
                        vals = {
                             'amount': amount_each,
                             'asset_id': asset.id,
                             'sequence': i,
                             'name': str(asset.id) +'/' + str(i),
                             'remaining_value': residual_amount2,
                             'depreciated_value': (asset.purchase_value - asset.salvage_value) - (residual_amount2 + amount_each),
                             'depreciation_date': depreciation_date.strftime('%Y-%m-%d'),
                        }
                        depreciation_lin_obj.create(cr, uid, vals, context=context)
                        depreciation_date = (datetime(year, month, day) + relativedelta(months=+2)) 
                        depreciation_date = (datetime(depreciation_date.year, depreciation_date.month, 1) + relativedelta(days=-1)) 
                        day = depreciation_date.day
                        month = depreciation_date.month
                        year = depreciation_date.year

            # NON YEARLY PRORATE
            else:
                for x in range(len(posted_depreciation_line_ids), undone_dotation_number):
                    i = x + 1
                    amount = self._compute_board_amount(cr, uid, asset, i, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date, context=context)
                    if float_is_zero(amount, precision_digits=precision_digits):
                        continue
                    residual_amount -= amount
                    vals = {
                         'amount': amount,
                         'asset_id': asset.id,
                         'sequence': i,
                         'name': str(asset.id) +'/' + str(i),
                         'remaining_value': residual_amount,
                         'depreciated_value': (asset.purchase_value - asset.salvage_value) - (residual_amount + amount),
                         'depreciation_date': depreciation_date.strftime('%Y-%m-%d'),
                    }
                    depreciation_lin_obj.create(cr, uid, vals, context=context)
                    # depreciation_date = (datetime(year, month, day) + relativedelta(months=+asset.method_period))

                    depreciation_date = (datetime(year, month, day) + relativedelta(months=+2)) 
                    depreciation_date = (datetime(depreciation_date.year, depreciation_date.month, 1) + relativedelta(days=-1)) 

                    day = depreciation_date.day
                    month = depreciation_date.month
                    year = depreciation_date.year
        return True

class dym_asset_category(osv.osv):
    _inherit = "account.asset.category"
    
    def _get_degressive_factor(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.method_number != 0:
                degressive = (float(1.0) / float(line.method_number)) * float(2)
            else:
                degressive = 0
            res[line.id] = degressive
        return res

    def _get_analytic_company(self,cr,uid,context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    _columns = {
        'type':fields.selection([('prepaid','Prepaid'),('fixed','Fixed Asset')],string="Type"),
        'code' : fields.char(string="Asset Code"),
        'first_day_of_month' : fields.boolean(string="First day of Month"),
        'method_progress_factor' : fields.function(_get_degressive_factor, type='float', digits=dp.get_precision('Degressive'), string="Degressive Factor"),
        'asset_classification_id' : fields.many2one('dym.asset.classification',string="Asset Classification"),
        'cip' : fields.boolean(string="CIP"),
        'analytic_1' : fields.many2one('account.analytic.account', 'Account Analytic Company'),
        'analytic_2' : fields.many2one('account.analytic.account', 'Account Analytic Bisnis Unit'),
        'analytic_3' : fields.many2one('account.analytic.account', 'Account Analytic Branch'),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Account Analytic Cost Center'),
    }

    _defaults = {
        'first_day_of_month':True,
        'analytic_1':_get_analytic_company,
    }
      
    _sql_constraints = [
        ('unique_name_asset_category_name', 'unique(name)', 'Nama duplicate mohon periksa kembali data anda !'),
    ]   

    def change_reset(self, cr, uid, ids, field, context=None):
        res = {}
        if field == 'company':
            res['analytic_1'] = False
            res['analytic_2'] = False
            res['analytic_3'] = False
            res['account_analytic_id'] = False
        if field == 'analytic_1':
            res['analytic_2'] = False
            res['analytic_3'] = False
            res['account_analytic_id'] = False
        if field == 'analytic_2':
            res['analytic_3'] = False
            res['account_analytic_id'] = False
        if field == 'analytic_3':
            res['account_analytic_id'] = False
        result = {}
        result['value'] = res
        return result

    def copy(self, cr, uid, id, default=None, context=None):
        default = dict(context or {})
        categ = self.browse(cr, uid, id, context=context)
        default.update(
            code=_(""),
            name=_("%s (copy)") % (categ['name'] or ''))
        return super(dym_asset_category, self).copy(cr, uid, id, default, context=context)

    def create(self,cr,uid,vals,context=None):
        if '__copy_data_seen' not in context:
            code = vals.get('code',vals['name'])
        res = super(dym_asset_category,self).create(cr,uid,vals,context=None)
        return res
    
class dym_asset_depreciation_line(osv.osv):
    _inherit = "account.asset.depreciation.line"
    
    def create_move(self, cr, uid, ids, context=None):
        context = dict(context or {})
        can_close = False
        asset_obj = self.pool.get('account.asset.asset')
        period_obj = self.pool.get('account.period')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        created_move_ids = []
        asset_ids = []
        for line in self.browse(cr, uid, ids, context=context):
            depreciation_date = context.get('depreciation_date') or line.depreciation_date or time.strftime('%Y-%m-%d')
            period_ids = period_obj.find(cr, uid, depreciation_date, context=context)
            company_currency = line.asset_id.company_id.currency_id.id
            current_currency = line.asset_id.currency_id.id
            context.update({'date': depreciation_date})
            amount = currency_obj.compute(cr, uid, current_currency, company_currency, line.amount, context=context)
            sign = (line.asset_id.category_id.journal_id.type == 'purchase' and 1) or -1
            asset_name = "/"
            reference = line.asset_id.name
            move_vals = {
                'name': asset_name,
                'date': depreciation_date,
                'ref': reference,
                'period_id': period_ids and period_ids[0] or False,
                'journal_id': line.asset_id.category_id.journal_id.id,
                'transaction_id':line.asset_id.id,
                'model':line.asset_id.__class__.__name__,
                }
            move_id = move_obj.create(cr, uid, move_vals, context=context)
            journal_id = line.asset_id.category_id.journal_id.id
            partner_id = line.asset_id.partner_id.id
            move_line_obj.create(cr, uid, {
                'name': asset_name,
                'ref': reference,
                'move_id': move_id,
                'account_id': line.asset_id.category_id.account_depreciation_id.id,
                'debit': 0.0,
                'credit': amount,
                'period_id': period_ids and period_ids[0] or False,
                'journal_id': journal_id,
                'branch_id': line.asset_id.analytic_3.branch_id.id or line.asset_id.branch_id.id,
                'division': 'Umum',
                'currency_id': company_currency != current_currency and  current_currency or False,
                'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
                'date': depreciation_date,
                'analytic_account_id' : line.asset_id.analytic_4.id,
            })
            analytic = line.asset_id.category_id.account_analytic_id
            analytic_4 = analytic.id
            branch_id = False
            if analytic.type == 'normal' and analytic.segmen == 3 and not branch_id:
                branch_id = analytic.branch_id.id
            while (analytic.parent_id and not branch_id):
                analytic = analytic.parent_id
                if analytic.type == 'normal' and analytic.segmen == 3:
                        branch_id = analytic.branch_id.id
            move_line_obj.create(cr, uid, {
                'name': asset_name,
                'ref': reference,
                'move_id': move_id,
                'account_id': line.asset_id.category_id.account_expense_depreciation_id.id,
                'credit': 0.0,
                'debit': amount,
                'period_id': period_ids and period_ids[0] or False,
                'journal_id': journal_id,
                'branch_id': branch_id or line.asset_id.category_id.analytic_3.branch_id.id,
                'division': 'Umum',
                'currency_id': company_currency != current_currency and  current_currency or False,
                'amount_currency': company_currency != current_currency and sign * line.amount or 0.0,
                'date': depreciation_date,
                'asset_id': line.asset_id.id,
                'analytic_account_id': analytic_4,
            })
            self.write(cr, uid, line.id, {'move_id': move_id}, context=context)
            created_move_ids.append(move_id)
            asset_ids.append(line.asset_id.id)
        # we re-evaluate the assets to determine whether we can close them
        for asset in asset_obj.browse(cr, uid, list(set(asset_ids)), context=context):
            if currency_obj.is_zero(cr, uid, asset.currency_id, asset.value_residual):
                asset.write({'state': 'close'})
        move_lines = self.pool.get('account.move').browse(cr,uid,created_move_ids)
        periods = self.pool.get('account.period').find(cr, uid, context=context)
        for move_line in move_lines :
            branch_id = False
            for x in move_line.line_id :
                if not branch_id :
                    if not x.asset_id.branch_id:
                        raise osv.except_osv('Configuration Error', '''Asset dengan ID %s dan nama = "%s" tidak memiliki cabang, mohon setting dulu sebelum close period ini.''' % (x.asset_id.id,x.asset_id.name))
                    branch_id = x.asset_id.branch_id.id
                x.write({'branch_id':branch_id,'division':'Umum'})
            if branch_id:
                get_name = self.pool.get('ir.sequence').get_per_branch(cr,uid,[branch_id], move_line.journal_id.code) 
                move_line.write({'name':get_name})
            else:
                raise osv.except_osv('Configuration Error', '''Baris jurnal dengan ID %s tidak memiliki cabang, mohon setting dulu sebelum close period ini.''' % (move_line.id))

        return created_move_ids
    
class dym_asset_classification(osv.osv):
    _name = "dym.asset.classification"
    _description = "Asset Classification"
    
    _columns = {
                'name' : fields.char(string="Name"),
                'code' : fields.char(string='Code'),
                'categ_id' : fields.one2many('account.asset.category','asset_classification_id',string="Asset Category")
                }
    
    _sql_constraints = [
    ('unique_name_asset_classification', 'unique(code)', 'Code duplicate mohon periksa kembali data anda !'),
]            