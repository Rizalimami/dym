from openerp.osv import fields, osv
from lxml import etree
from openerp.osv.orm import setup_modifiers
from openerp import SUPERUSER_ID
from datetime import datetime, date, timedelta
import pdb

class dym_check_service(osv.osv):
    _name = "dym.check.service"
    
    def _get_branch_id(self, cr, uid, context=None):
        obj_branch = self.pool.get('dym.branch')
        ids_branch = obj_branch.search(cr, SUPERUSER_ID, [], order='name')
        branches = obj_branch.read(cr, SUPERUSER_ID, ids_branch, ['id','name'], context=context)
        res = []
        for branch in branches :
            res.append((branch['id'],branch['name']))
        return res

    _columns = {
                'branch_id': fields.selection(_get_branch_id, 'Branch'),
                'service_type':fields.selection([('KPB','KPB'),('REG','Regular'),('WAR','Job Return')],'Type WO', change_default=True, select=True),
                'lot_id':fields.many2one('stock.production.lot','Nopol / Engine No'),
                'due_date':fields.integer('Re-visit (Days)'),
                'customer_id':fields.many2one('res.partner','Nomor Member / Customer'),
                'work_order_ids': fields.one2many('dym.work.order', 'check_service_id', 'Work Order', readonly=True),
                }

    _defaults = {
                 'due_date' : 3,
                 }
    
    def create(self, cr, uid, vals, context=None):
        raise osv.except_osv(('Perhatian !'), ("Tidak bisa disimpan, form ini hanya untuk Pengecekan"))
        return False
    
    def field_change(self, cr, uid, ids, service_type, branch_id, lot_id, due_date, customer_id, context=None):
        value = {}
        warning = {}
        work_order_obj = self.pool.get('dym.work.order')
        value['work_order_ids'] = False
        domain = {}
        domain_search = [('state', 'in', ['done','open'])]
        
        if customer_id or lot_id:
            if service_type:
                domain_search.append(('type', '=', service_type))
            else:
                domain_search.append(('type', 'in', ('KPB', 'REG', 'WAR')))
            if lot_id:
                domain_search.append(('lot_id', '=', lot_id))
            if branch_id:
                domain_search.append(('branch_id', '=', branch_id))
            if customer_id:
                domain_search.append(('customer_id', '=', customer_id))
     
            work_order_ids = work_order_obj.search(cr, SUPERUSER_ID, domain_search, order='date desc, id desc')
            work_order = work_order_obj.browse(cr, SUPERUSER_ID, work_order_ids)

            lot_ids = []
            show_wo_ids = []
            for x in work_order:
                if str(x.lot_id.id) + ' - ' + x.type in lot_ids or x.service_date_remaining > due_date:
                    continue
                lot_ids.append(str(x.lot_id.id) + ' - ' + x.type)
                show_wo_ids.append(x.id)

            value['work_order_ids'] = show_wo_ids
        return {'value':value}
    
class config_days_revisit(osv.osv):
    _name = "dym.days.revisit"

    _columns = {
        'name': fields.char('Name', readonly=True),
        'due_date': fields.integer('Due Date (days)', required=True),
        }

class dym_work_order(osv.osv):
    _inherit = "dym.work.order"

    def _compute_revisit_date(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for wo in self.browse(cr, uid, ids, context=None):
            res[wo.id] = {
                'tgl_service_kembali': False,
                'service_date_remaining': 0,
            }
            revisit_date = False
            if wo.type in ('KPB', 'REG', 'WAR') and wo.date:
                days_revisit_id = self.pool.get('dym.days.revisit').search(cr, SUPERUSER_ID, [('name', '=', wo.type)], limit=1)
                days_revisit = self.pool.get('dym.days.revisit').browse(cr, SUPERUSER_ID, days_revisit_id).due_date
                revisit_date = datetime.strptime(wo.date, '%Y-%m-%d %H:%M:%S') + timedelta(days=days_revisit)
            res[wo.id]['tgl_service_kembali'] = revisit_date.strftime('%Y-%m-%d')
            if int((datetime.date(revisit_date)-date.today()).days) < 0:
                res[wo.id]['service_date_remaining'] = 0
            else:
                res[wo.id]['service_date_remaining'] = int((datetime.date(revisit_date)-date.today()).days)
        return res

    _columns = {
        'tgl_service_kembali': fields.function(_compute_revisit_date, type="date", string='Tgl Service Kembali', multi='sums', readonly=True),
        'service_date_remaining': fields.function(_compute_revisit_date, type="integer", string='Due Date', multi='sums', readonly=True),
        'engine_number':fields.related('lot_id','name',type='char',string='Engine Number'),
        }