# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _

class asset_many_depreciation_confirmation_wizard(osv.osv_memory):
    _name = "asset.many.depreciation.confirmation.wizard"

    _columns = {
        'total_assets': fields.integer(string='Total Assets')
    }

    def asset_accum_compute(self, cr, uid, ids, context):
        period_id = context.get('period_id',False)
        asset_ids = context.get('asset_ids',False)
        if not period_id or not asset_ids:
            return {}
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        ass_obj = self.pool.get('account.asset.asset')
        period_obj = self.pool.get('account.period')
        depreciation_obj = self.pool.get('account.asset.depreciation.line')
        period = period_obj.browse(cr, uid, period_id, context=context)

        for asset in ass_obj.browse(cr, uid, asset_ids, context=context):
            depreciation_ids = depreciation_obj.search(cr, uid, [
                ('asset_id', '=', asset.id), 
                ('depreciation_date', '<=', period.date_stop), 
                ('move_check', '=', False)
                ], context=context)
            ass_obj.create_asset_accum_move(cr, uid, asset.id, depreciation_ids, period_id, period.date_stop, context=context)

    def asset_compute_per_period(self, cr, uid, ids, context):

        period_id = context.get('period_id',False)
        asset_ids = context.get('asset_ids',False)

        if not period_id or not asset_ids:
            return {}

        context_copy = context.copy()
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        ass_obj = self.pool.get('account.asset.asset')
        period_obj = self.pool.get('account.period')
        depreciation_obj = self.pool.get('account.asset.depreciation.line')
        period = period_obj.browse(cr, uid, period_id, context=context)
        oldest_depreciation_id = depreciation_obj.search(cr, uid, [
            ('asset_id', 'in', asset_ids), 
            ('depreciation_date', '<=', period.date_stop), 
            ('depreciation_date', '<=', period.date_start), 
            ('move_check', '=', False)
            ], context=context, order='depreciation_date', limit=1)

        depreciation_date = depreciation_obj.browse(cr, uid, oldest_depreciation_id, context=context)[0].depreciation_date
        # period_id = period_obj.search(cr, uid, [('date_start','>=',depreciation_date),('date_stop','<=',depreciation_date)], context=context)
        period_id = period_obj.search(cr, uid, [('company_id','=',company_id.id),('special','=',False)], context=context, order="date_start", limit=1)
        period_oldest = period_obj.browse(cr, uid, period_id, context=context)
        if period_oldest:
            context_copy.update({
                'period_id': period_oldest[0].id,
                'depreciation_date': period_oldest[0].date_stop,
            })


        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
            ("name", "=", "asset.depreciation.confirmation.wizard"), 
            ("model", "=", 'asset.depreciation.confirmation.wizard'),
        ])

        return {
            'name': _('Compute Assets Per Period'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'asset.depreciation.confirmation.wizard',
            'view_id': view_id,
            'domain': "[]",
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': context_copy,
        }


class asset_depreciation_confirmation_wizard(osv.osv_memory):
    _inherit = "asset.depreciation.confirmation.wizard"
    _description = "asset.depreciation.confirmation.wizard"


    def asset_compute(self, cr, uid, ids, context):
        ass_obj = self.pool.get('account.asset.asset')
        asset_ids = ass_obj.search(cr, uid, [('state','=','open')], context=context)
        data = self.browse(cr, uid, ids, context=context)
        period_id = data[0].period_id.id

        period_obj = self.pool.get('account.period')
        depreciation_obj = self.pool.get('account.asset.depreciation.line')
        period = period_obj.browse(cr, uid, period_id, context=context)
        depreciation_ids = depreciation_obj.search(cr, uid, [
            ('asset_id', 'in', asset_ids), 
            ('depreciation_date', '<=', period.date_stop), 
            ('depreciation_date', '<=', period.date_start), 
            ('move_check', '=', False)
            ], context=context)

        context = dict(context or {}, depreciation_date=period.date_stop)
        if asset_ids:
            context['total_assets'] = len(asset_ids)
        if period_id:
            context['period_id'] = period_id
        if asset_ids:
            context['asset_ids'] = asset_ids

        if len(depreciation_ids)==1:
            return depreciation_obj.create_move(cr, uid, depreciation_ids, context=context)
        else:
            view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                            ("name", "=", "asset.many.depreciation.confirmation.wizard"), 
                            ("model", "=", 'asset.many.depreciation.confirmation.wizard'),
                        ])
            return {
                'name': _('Compute Assets Confirmation'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'asset.many.depreciation.confirmation.wizard',
                'view_id': view_id,
                'domain': "[]",
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': context,
            }

        created_move_ids = ass_obj._compute_entries(cr, uid, asset_ids, period_id, context=context)
        res = super(asset_depreciation_confirmation_wizard, self).asset_compute(cr, uid, ids, context=context)
        return res
    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
