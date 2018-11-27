from openerp.osv import fields, osv
from lxml import etree
from openerp.osv.orm import setup_modifiers
from openerp import SUPERUSER_ID
from datetime import datetime, date, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import pdb

class dym2_asset_category(osv.osv):
    _inherit = "account.asset.category"
    _columns = {
        'analisa_cost':fields.float('Cost'),
        'analisa_depreciated':fields.float('Acc. Depr. M-2'),
        'analisa_current_depre_1':fields.float('Depreciation Expense M-1'),
        'analisa_current_depre_0':fields.float('Depreciation Expense M'),
        'analisa_nbv':fields.float('NBV'),
    }
    
class dym2_analisa_penyusutan(osv.osv):
    _name = "dym2.analisa.penyusutan"
    
    def _get_branch_id(self, cr, uid, context=None):
        obj_branch = self.pool.get('dym.branch')
        ids_branch = obj_branch.search(cr, SUPERUSER_ID, [], order='name')
        branches = obj_branch.read(cr, SUPERUSER_ID, ids_branch, ['id','name'], context=context)
        res = []
        for branch in branches :
            res.append((branch['id'],branch['name']))
        return res

    def _get_asset_category(self, cr, uid, ids, field_names, arg=None, context=None):
        res={}
        for analisa in self.browse(cr, uid, ids, context):
            res[analisa.id] = []
        return res

    _columns = {
        'month':fields.selection([(1,'Januari'),(2,'Februari'),(3,'Maret'),(4,'April'),(5,'Mei'),(6,'Juni'),(7,'Juli'),(8,'Agustus'),(9,'September'),(10,'Oktober'),(11,'November'),(12,'Desember')], 'Month', required=True),
        'year': fields.selection([(num, str(num)) for num in range(2015, (datetime.now().year)+1 )], 'Year', required=True),
        'branch_id': fields.selection(_get_branch_id, 'Branch', required=True),
        'asset_category_ids': fields.function(_get_asset_category, type='one2many', relation="account.asset.category", string="Asset Categories", readonly=True),
    }

    _defaults = {
        'due_date' : 3,
    }
    
    def create(self, cr, uid, vals, context=None):
        raise osv.except_osv(('Perhatian !'), ("Tidak bisa disimpan, form ini hanya untuk Pengecekan"))
        return False
    
    def field_change(self, cr, uid, ids, branch_id, month, year, context=None):
        value = {}
        asset_category_ids = []
        if branch_id and month and year:
            next_month = date(year, month, 1).replace(day=28) + timedelta(days=4)
            last_day_of_month = (next_month - timedelta(days=next_month.day)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            first_day_of_month = date(year, month, 1).strftime(DEFAULT_SERVER_DATE_FORMAT)
            last_day_of_prev_month = (date(year, month, 1) - timedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            first_day_of_prev_month = (date(year, month, 1) - timedelta(days=1)).replace(day=1).strftime(DEFAULT_SERVER_DATE_FORMAT)
            request = ("SELECT c.id as category_id, c.name as name, (SELECT COALESCE(SUM(d1.amount),0) from account_asset_depreciation_line d1, account_asset_asset a1, account_asset_category c1 WHERE  a1.id = d1.asset_id and a1.branch_id = %s and d1.depreciation_date < %s and a1.category_id = c1.id and c1.id = c.id) as analisa_depreciated, (SELECT COALESCE(SUM(d2.amount),0) from account_asset_depreciation_line d2, account_asset_asset a2, account_asset_category c2 WHERE  a2.id = d2.asset_id and a2.branch_id = %s and d2.depreciation_date >= %s and d2.depreciation_date <= %s and a2.category_id = c2.id and c2.id = c.id) as analisa_current_depre_1, (SELECT COALESCE(SUM(d3.amount),0) from account_asset_depreciation_line d3, account_asset_asset a3, account_asset_category c3 WHERE  a3.id = d3.asset_id and a3.branch_id = %s and d3.depreciation_date >= %s and d3.depreciation_date <= %s and a3.category_id = c3.id and c3.id = c.id) as analisa_current_depre_0, (SELECT COALESCE(SUM(a4.real_purchase_value),0) - COALESCE(SUM(a4.salvage_value),0) from account_asset_asset a4, account_asset_category c4 WHERE a4.branch_id = %s and a4.id IN (SELECT d4.asset_id from account_asset_depreciation_line d4 where d4.depreciation_date <= %s) and a4.category_id = c4.id and c4.id = c.id) as analisa_cost FROM account_asset_category c  WHERE c.type = 'fixed' GROUP BY c.id ORDER BY c.name asc")
            params = (tuple([branch_id]),str(first_day_of_prev_month),tuple([branch_id]),str(first_day_of_prev_month),str(last_day_of_prev_month),tuple([branch_id]),str(first_day_of_month),str(last_day_of_month),tuple([branch_id]),str(last_day_of_month))
            cr.execute(request, params)
            rows = cr.dictfetchall()
            for row in rows:
                asset_category_ids.append([0,0,{
                    'name':row['name'],
                    'analisa_cost':row['analisa_cost'],
                    'analisa_depreciated':row['analisa_depreciated'],
                    'analisa_current_depre_1':row['analisa_current_depre_1'],
                    'analisa_current_depre_0':row['analisa_current_depre_0'],
                    'analisa_nbv':row['analisa_cost'] - row['analisa_depreciated'] - row['analisa_current_depre_1'] - row['analisa_current_depre_0'],
                }])
        value['asset_category_ids'] = asset_category_ids
        return {'value':value}

