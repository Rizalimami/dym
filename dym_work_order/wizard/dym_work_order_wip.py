from openerp.osv import fields, osv


class work_order_wip(osv.osv_memory):
    _name = 'work_order.wip'
    _description = 'WIP'

    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        res ={}
        datas['form'] = res
        return self.pool['report'].get_action(cr, uid, [], 'dym_work_order.dym_work_order_wip_report', data=datas, context=context)
