from openerp.osv import osv,fields
import time
from openerp import netsvc
import pdb

class dym_start_stop_wo(osv.osv):
    _name = 'dym.start.stop.wo'
    
    def _get_branch_id(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('branch_id', False)

    def _get_work_order_id(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('work_order_id', False)
    
    def _get_mekanik_id(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('mekanik_id', False)

    def _get_pit_id(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('pit_id', False)
    
    _columns = {
                'branch_id':fields.many2one('dym.branch','Branch', required="1"),
                'work_order_id':fields.many2one('dym.work.order', 'Work Order', domain="[('mekanik_id','in',[mekanik_id,False]), ('state','in',['open','approved']), ('branch_id','=',branch_id)]"),
                'mekanik_id':fields.many2one('hr.employee', 'Mekanik'),
                'start':fields.datetime('Start', readonly=True),
                'date_break':fields.datetime('Break', readonly=True),
                'end_break':fields.datetime('End Break', readonly=True),
                'finish':fields.datetime('Finish', readonly=True),
                "wo_time_line": fields.related("work_order_id", "wo_time_line", type="one2many", relation="dym.start.stop.wo.time.line"),
                'state_wo': fields.selection([('in_progress','In Progress'),('break','Break'),('finish','Finish')], 'State', readonly=True),
                'pit_id':fields.many2one('dym.pit','Pit'),
                }
    _defaults = {
        'branch_id': _get_branch_id,
        'work_order_id': _get_work_order_id,        
        'mekanik_id': _get_mekanik_id,
        'pit_id': _get_pit_id,
    }
    
    def btn_start(self, cr, uid, ids, context=None):
        tgl_start = time.strftime('%Y-%m-%d %H:%M:%S')
        a = self.browse(cr,uid,ids)
        obj_wo_a = self.pool.get('dym.work.order')
        obj_id_a = obj_wo_a.search(cr,uid,[('id','=',a.work_order_id.id)])
        obj_strt = obj_wo_a.browse(cr,uid,obj_id_a)
        inv = self.browse(cr, uid, ids[0], context=context)
        
        if obj_strt :
            obj_wo_a.write(cr, uid, obj_id_a, {'state_wo':'in_progress','start':tgl_start,'mekanik_id':inv.mekanik_id.id, 'pit_id':inv.pit_id.id}, context=context)
            self.write(cr, uid, ids, {'state_wo':'in_progress','start':tgl_start,'date_break':a.work_order_id.date_break,'end_break':a.work_order_id.end_break,'finish':a.work_order_id.finish}, context=context)
            netsvc.LocalService("workflow").trg_validate(uid, 'dym.work.order', obj_strt.id, 'start_wo', cr)

            obj_wo_time_line = self.pool.get('dym.start.stop.wo.time.line')
            time_line_values = {
                'start_stop_wo_id': obj_id_a[0],
                'state_time_line': 'start',
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            }  
            create_time_line = obj_wo_time_line.create(cr, uid, time_line_values)
            dom, warn, value = self.check_mekanik_available(cr, uid, ids, obj_strt.branch_id.id, obj_strt.mekanik_id.id, obj_strt.id)
            if warn:
                raise osv.except_osv((warn['title']), (warn['message']))
        return True
    
    def btn_break(self, cr, uid, ids, context=None):        
        tgl_break = time.strftime('%Y-%m-%d %H:%M:%S')
        b = self.browse(cr,uid,ids)
        obj_wo_b = self.pool.get('dym.work.order')
        obj_id_b = obj_wo_b.search(cr,uid,[('id','=',b.work_order_id.id)])
        obj_brk = obj_wo_b.browse(cr,uid,obj_id_b)
        cek_finish = b.work_order_id.finish
        
        if obj_brk and not cek_finish :
            obj_wo_b.write(cr, uid, obj_id_b, {'state_wo':'break','date_break':tgl_break}, context=context)
            self.write(cr, uid, ids, {'state_wo':'break','date_break':tgl_break,'start':b.work_order_id.start,'end_break':b.work_order_id.end_break,'finish':b.work_order_id.finish}, context=context)
            netsvc.LocalService("workflow").trg_validate(uid, 'dym.work.order', obj_brk.id, 'break_wo', cr)

            obj_wo_time_line = self.pool.get('dym.start.stop.wo.time.line')
            time_line_values = {
                'start_stop_wo_id': obj_id_b[0],
                'state_time_line': 'break',
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            }  
            create_time_line = obj_wo_time_line.create(cr, uid, time_line_values) 
        return True
    
    def btn_end_break(self, cr, uid, ids, context=None):
        tgl_end_break = time.strftime('%Y-%m-%d %H:%M:%S')
        c = self.browse(cr,uid,ids)
        obj_wo_c = self.pool.get('dym.work.order')
        obj_id_c = obj_wo_c.search(cr,uid,[('id','=',c.work_order_id.id)])
        obj_ebrk = obj_wo_c.browse(cr,uid,obj_id_c)
        cek_finish2 = c.work_order_id.finish
         
        if obj_ebrk and not cek_finish2 :
            obj_wo_c.write(cr, uid, obj_id_c, {'state_wo':'in_progress','end_break':tgl_end_break}, context=context)
            self.write(cr, uid, ids, {'state_wo':'in_progress','end_break':tgl_end_break,'start':c.work_order_id.start,'date_break':c.work_order_id.date_break,'finish':c.work_order_id.finish}, context=context)
            netsvc.LocalService("workflow").trg_validate(uid, 'dym.work.order', obj_ebrk.id, 'start_wo', cr)

            obj_wo_time_line = self.pool.get('dym.start.stop.wo.time.line')
            time_line_values = {
                'start_stop_wo_id': obj_id_c[0],
                'state_time_line': 'end_break',
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            }  
            create_time_line = obj_wo_time_line.create(cr, uid, time_line_values) 
            dom, warn, value = self.check_mekanik_available(cr, uid, ids, obj_ebrk.branch_id.id, obj_ebrk.mekanik_id.id, obj_ebrk.id)
            if warn:
                raise osv.except_osv((warn['title']), (warn['message']))
        return True
    
    def btn_finish(self, cr, uid, ids, context=None):
        tgl_finish = time.strftime('%Y-%m-%d %H:%M:%S')
        d = self.browse(cr,uid,ids)
        obj_wo_d = self.pool.get('dym.work.order')
        obj_id_d = obj_wo_d.search(cr,uid,[('id','=',d.work_order_id.id)])
        obj_fns = obj_wo_d.browse(cr,uid,obj_id_d)
        
        if obj_fns :
            obj_wo_d.write(cr, uid, obj_id_d, {'state_wo':'finish','finish':tgl_finish}, context=context)
            self.write(cr, uid, ids, {'state_wo':'finish','finish':tgl_finish,'start':d.work_order_id.start,'date_break':d.work_order_id.date_break,'end_break':d.work_order_id.end_break}, context=context)
            netsvc.LocalService("workflow").trg_validate(uid, 'dym.work.order', obj_fns.id, 'end_wo', cr)

            obj_wo_time_line = self.pool.get('dym.start.stop.wo.time.line')
            time_line_values = {
                'start_stop_wo_id': obj_id_d[0],
                'state_time_line': 'finish',
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            }  
            create_time_line = obj_wo_time_line.create(cr, uid, time_line_values)  
        return True
    
    def onchange_wo(self, cr, uid, ids, work_order_id):
        v = {}
        if work_order_id :
            s=self.pool.get("dym.work.order").browse(cr, uid, work_order_id)
            v['start']=s.start
            v['date_break']=s.date_break
            v['end_break']=s.end_break
            v['finish']=s.finish
            v['state_wo']=s.state_wo            
            v['wo_time_line']=s.wo_time_line            
        else :
            v['start']=False
            v['date_break']=False
            v['end_break']=False
            v['finish']=False
            v['state_wo']=False
            v['wo_time_line']=False
        return {'value':v}

    def onchange_branch_id(self, cr, uid, ids, branch_id):
        dom = {} 
        mekanik_ids = []
        value = {}   
        employee_ids = []
        employee_obj = self.pool.get('hr.employee')
        if branch_id:
            employee_ids = employee_obj.search(cr, uid, [('branch_id','=',branch_id),('active','=',1),('job_id.mekanik','=',True)])
        # value['mekanik_id'] = False
        # value['work_order_id'] = False
        dom['mekanik_id']=[('id','in',employee_ids)]
        return {'domain':dom, 'value':value}

    def onchange_mekanik_id(self, cr, uid, ids, mekanik_id, work_order_id):
        dom = {}
        if work_order_id:
            s=self.pool.get("dym.work.order").browse(cr, uid, work_order_id)
            dom, warn, value = self.check_mekanik_available(cr, uid, ids, s.branch_id.id, mekanik_id, work_order_id)
            return {'domain':dom,'warning':warn, 'value':value}
        return True

    def check_mekanik_available(self, cr, uid, ids, branch_id, mekanik_id, wo_id):
        dom = {}
        warning = ''    
        value = {}    
        employee_obj = self.pool.get('hr.employee')
        wo_obj = self.pool.get('dym.work.order')
        if mekanik_id:
            # for emp in employee_obj.browse(cr, uid, mekanik_id):
            #     if emp.state == 'absent':
            #         warning += 'Status mekanik Absent!' + '\n'
            wo_ids = wo_obj.search(cr, uid, [('id','!=',wo_id),('state_wo','=','in_progress'),('state','in',('open','approved')),('mekanik_id','=',mekanik_id)])
            if wo_ids:
                wo = wo_obj.browse(cr, uid, wo_ids)[0]
                warning += 'Mekanik sedang mengerjakan WO: ' + wo.name + '\n'
        warn = ''
        if warning:
            warn = {
               'title': 'Data Error!',
               'message': warning
            }
        return dom, warn, value

class dym_start_stop_wo_time_line(osv.osv):
    _name = 'dym.start.stop.wo.time.line'
    _columns = {
                'start_stop_wo_id':fields.many2one('dym.work.order', 'Work Order'),                
                'state_time_line': fields.selection([('start','Start'),('break','Break'),('end_break','End Break'),('finish','Finish')], 'State', readonly=True),
                'time':fields.datetime('Time', readonly=True),                            
                }

class dym_start_stop_wo(osv.osv):
    _inherit="dym.work.order"
    _columns={
              'wo_time_line': fields.one2many('dym.start.stop.wo.time.line','start_stop_wo_id','Time Line',),
              'state_wo': fields.selection([('in_progress','In Progress'),('break','Break'),('finish','Finish')], 'State', readonly=True),
              }
    
    