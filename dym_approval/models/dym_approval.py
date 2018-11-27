import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc
from openerp.tools.translate import _

class dym_approval_matrixbiaya_header(osv.osv):
    _name = "dym.approval.matrixbiaya.header"
    _inherit = ['mail.thread']
    _columns = {
        'branch_id':fields.many2one('dym.branch',string='Branch',required=True),
        'division':fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', change_default=True, select=True, required=True),
        'approval_line': fields.one2many('dym.approval.matrixbiaya', 'header_id', 'Approval lines'),
        'form_id':fields.many2one('dym.approval.config',string='Form',required=True,domain="[('type','=','biaya')]"),
    }
    
    def create(self, cr, uid, values, context=None):
        if 'approval_line' not in values:
            return False
        form_id = self.pool.get('dym.approval.config').browse(cr,uid,values['form_id'])       
        for lines in values['approval_line']:
            lines[2].update({'code':form_id.code,'branch_id':values['branch_id'],'division':values['division'],'form_id':form_id.form_id.id})
        approval = super(dym_approval_matrixbiaya_header,self).create(cr, uid, values, context=context)
        val = self.browse(cr,uid,approval)
        self.message_post(cr, uid, val.id, body=_("Approval created "), context=context) 
        return approval
    
    def write(self, cr, uid,ids,values,context=None):
        app=self.browse(cr,uid,ids)
        # if values.get('form_id',False):
        #     config = self.pool.get('dym.approval.config').search(cr,uid,[
        #                                                      ('id','=',values['form_id']),
        #                                                      ])   
        #     form_id = self.pool.get('dym.approval.config').browse(cr,uid,config)               
        #     new_reg = self.pool.get('dym.approval.matrixbiaya').search(cr,uid,[('header_id','=',app.id)])
        #     self.pool.get('dym.approval.matrixbiaya').write(cr, uid, new_reg,{'form_id':form_id.form_id.id,'code':form_id.code},context=context)
        # if values.get('branch_id',False):
        #     new_reg = self.pool.get('dym.approval.matrixbiaya').search(cr,uid,[('header_id','=',app.id)])
        #     self.pool.get('dym.approval.matrixbiaya').write(cr, uid, new_reg,{'branch_id':values['branch_id']},context=context)
            
        # if values.get('division',False):
        #     new_reg = self.pool.get('dym.approval.matrixbiaya').search(cr,uid,[('header_id','=',app.id)])
        #     self.pool.get('dym.approval.matrixbiaya').write(cr, uid, new_reg,{'division':values['division']},context=context)
        
        # if values.get('approval_line',False):
        #     for lines in values['approval_line']:
        #         app=self.browse(cr,uid,ids)
        #         if lines[1]==False:
        #             lines[2].update({
        #                              'form_id':app.form_id.form_id.id,
        #                              'branch_id':app.branch_id.id,
        #                              'division':app.division,
        #                              'code':app.form_id.code,
        #                              })
        approval = super(dym_approval_matrixbiaya_header,self).write(cr, uid,ids,values)
        self.message_post(cr, uid, app.id, body=_("Approval updated "), context=context) 
        return approval

class dym_approval_matrixbiaya(osv.osv):
    _name="dym.approval.matrixbiaya"
        
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')                
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                                
        return branch_ids 

    def _check_limit(self, cr, uid, ids, context=None):
        matrix = self.browse(cr, uid, ids, context=context)[0]
        if matrix.limit > 0:
            return True
        return False

    _columns = {
        'header_id': fields.many2one('dym.approval.matrixbiaya.header', 'Header', ondelete='cascade'),
        'branch_id': fields.related('header_id', 'branch_id', relation='dym.branch', type='many2one', string='Branch'),
        'division' : fields.related('header_id', 'division', string='Division', type='selection', selection=[('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')]),
        'form_header': fields.related('header_id', 'form_id', relation='dym.approval.config', type='many2one', string='Form Header'),
        'form_id': fields.related('form_header', 'form_id', relation='ir.model', type='many2one', string='Form'),
        'code' : fields.related('form_header', 'code', string='Code', type='selection', selection=[(' ',' '),('fix','PO - Fix'),('additional','PO - Additional'),('administratif','PO - Administratif'),('waiting_list','PO - Waiting List'),('hotline','PO - Hotline'),('local_purchase','PO - Local Purchase'),('regular','PO - Regular'),('toko_lain-lain','PO - Toko Lain-lain'),('jp3','PO - JP3'),('payment','Supplier Payment'),('receipt','Customer Payment'),('purchase','Payment Request'),('sale','Other Receivable'),('cancel','Cancel Journal Memorial'),('offtr','Penjualan Off The Road'),('pic','Penjualan Off The Road PIC'),('cod','Penjualan COD')]),
        'group_id':fields.many2one('res.groups',string='Group',required=True,domain=[('category_id.name','=','Daya Motor')]),
        'limit': fields.float(digits=(8,2), string="Limit",required=True),
    }

    _constraints = [
        (_check_limit, 'Limit harus lebih besar dari 0!', ['limit']),
    ]


    _defaults = {
        'code':' ',
        'branch_id': _get_default_branch,
    }
        
    def request(self, cr, uid, ids, trx, subject_to_approval,code=' ',view_name=None):
        try:
            field_test = trx[subject_to_approval]
        except:
            raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki field %s. Cek kembali Matrix Approval.")%(subject_to_approval))
        return self.request_by_value(cr,uid,ids,trx,trx[subject_to_approval],code,view_name)

    def request_by_value(self,cr,uid,ids,trx,value,code=' ',view_name=None):
        config = self.pool.get('dym.approval.config').search(cr,uid,[('form_id','=',trx.__class__.__name__),('code','=',code),('type','=','biaya')])        
        if not config :
            raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki Approval Configuration !"))
        config_brw = self.pool.get('dym.approval.config').browse(cr,uid,config)     
        
        if trx.branch_id :
            matrix = self.search(cr, uid, [
                ('branch_id','=',trx.branch_id.id),
                ('division','=',trx.division),
                ('form_id','=',config_brw[0].form_id.id),
                ('code','=',config_brw.code)
            ])
        else :
            matrix = self.search(cr, uid, [
                ('branch_id','=',trx.branch_destination_id.id),
                ('division','=',trx.division),
                ('form_id','=',config_brw[0].form_id.id),
                ('code','=',config_brw.code)
            ])
        if not matrix:
            raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki matrix approval. Cek kembali data Cabang & Divisi"))

        data = self.browse(cr, uid, matrix)
        user_limit = 0
        
        if view_name is None :
            for x in data :
                self.pool.get('dym.approval.line').create(cr, uid, {
                    'value':value,
                    'group_id':x.group_id.id,
                    'transaction_id':trx.id,
                    'branch_id':x.branch_id.id,
                    'division':x.division,
                    'form_id':x.form_id.id,
                    'limit':x.limit,
                    'sts':'1',
                    'approval_config_id':config_brw[0].id,
                })
                if user_limit < x.limit:
                    user_limit = x.limit
        else :
            for x in data :
                self.pool.get('dym.approval.line').create(cr, uid, {
                    'value':value,
                    'group_id':x.group_id.id,
                    'transaction_id':trx.id,
                    'branch_id':x.branch_id.id,
                    'division':x.division,
                    'form_id':x.form_id.id,
                    'limit':x.limit,
                    'sts':'1',
                    'view_name':view_name,
                    'approval_config_id':config_brw[0].id,
                })
                if user_limit < x.limit:
                    user_limit = x.limit
                        
        if user_limit < value:
            raise osv.except_osv(('Perhatian !'), ("Nilai transaksi %d. Nilai terbesar di matrix approval: %d. Cek kembali Matrix Approval.") % (value, user_limit))
        return True

    def request_by_value_branch_destination(self,cr,uid,ids,trx,value,code=' ',view_name=None):
        config = self.pool.get('dym.approval.config').search(cr,uid,[
            ('form_id','=',trx.__class__.__name__),
            ('code','=',code),('type','=','biaya')
            ])
        if not config :
            raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))     
        config_brw = self.pool.get('dym.approval.config').browse(cr,uid,config)             
        matrix = self.search(cr, uid, [
            ('branch_id','=',trx.branch_destination_id.id),
            ('division','=',trx.division),
            ('form_id','=',config_brw[0].form_id.id),
            ('code','=',config_brw.code)
        ])            
        if not matrix:
            raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki matrix approval. Cek kembali data Cabang & Divisi"))

        data = self.browse(cr, uid, matrix)

        user_limit = 0
        
        if view_name is None :
            for x in data :
                self.pool.get('dym.approval.line').create(cr, uid, {
                    'value':value,
                    'group_id':x.group_id.id,
                    'transaction_id':trx.id,
                    'branch_id':x.branch_id.id,
                    'division':x.division,
                    'form_id':x.form_id.id,
                    'limit':x.limit,
                    'sts':'1',
                    'approval_config_id':config_brw[0].id,
                })
                if user_limit < x.limit:
                    user_limit = x.limit
        else :
            for x in data :
                self.pool.get('dym.approval.line').create(cr, uid, {
                    'value':value,
                    'group_id':x.group_id.id,
                    'transaction_id':trx.id,
                    'branch_id':x.branch_id.id,
                    'division':x.division,
                    'form_id':x.form_id.id,
                    'limit':x.limit,
                    'sts':'1',
                    'view_name':view_name,
                    'approval_config_id':config_brw[0].id,
                })
                if user_limit < x.limit:
                    user_limit = x.limit
                        
        if user_limit < value:
            raise osv.except_osv(('Perhatian !'), ("Nilai transaksi %d. Nilai terbersar di matrix approval: %d. Cek kembali Matrix Approval.") % (value, user_limit))

        return True

    def approve(self, cr, uid, ids, trx, code=False):
        user_groups = self.pool.get('res.users').browse(cr, uid, uid)['groups_id']
                                                                                                         
        config = self.pool.get('dym.approval.config').search(cr,uid,[('form_id','=',trx.__class__.__name__),('type','=','biaya')])
        if not config :
            raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))     
        config_brw = self.pool.get('dym.approval.config').browse(cr,uid,config)        
        domain_src = [('division','=',trx.division),('form_id','=',config_brw[0].form_id.id),('transaction_id','=',trx.id)]
        if trx.branch_id:
            domain_src += [('branch_id','=',trx.branch_id.id)]
        else :
            domain_src += [('branch_id','=',trx.branch_destination_id.id)]
        if code:
            domain_src += [('approval_config_id.code','=',code)]

        approval_lines_ids = self.pool.get('dym.approval.line').search(cr, uid, domain_src)                
        if not approval_lines_ids:
            raise osv.except_osv(('Perhatian x!'), ("Transaksi ini tidak memiliki detail approval. Cek kembali Matrix Approval."))
        approve_all = False
        user_limit = 0

        approval_lines = self.pool.get('dym.approval.line').browse(cr, uid, approval_lines_ids)
        for approval_line in approval_lines:
            if approval_line.sts == '1':
                if approval_line.group_id in user_groups:
                    if approval_line.limit > user_limit:
                        user_limit = approval_line.limit
                        approve_all = approval_line.value <= user_limit
                    approval_line.write({
                        'sts':'2',
                        'pelaksana_id':uid,
                        'tanggal':datetime.today(),
                    })

        if user_limit:
            for approval_line in approval_lines:
                if approval_line.sts == '1':
                    if approve_all:
                        approval_line.write({
                            'sts':'2',
                            'pelaksana_id':uid,
                            'tanggal':datetime.today(),
                        })
                    elif approval_line.limit <= user_limit:
                        approval_line.write({
                            'sts':'2',
                            'pelaksana_id':uid,
                            'tanggal':datetime.today(),
                        })
        if approve_all:
            return 1
        elif user_limit:
            return 2
        return 0

    def reject(self, cr, uid, ids, trx, reason):
        user_groups = self.pool.get('res.users').browse(cr, uid, uid)['groups_id']
        config = self.pool.get('dym.approval.config').search(cr,uid,[
                                                                                                         ('form_id','=',trx.__class__.__name__),('type','=','biaya'),
                                                                                                         ])
        if not config :
                raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))     
        config_brw = self.pool.get('dym.approval.config').browse(cr,uid,config)        
        if trx.branch_id :
            approval_lines_ids = self.pool.get('dym.approval.line').search(cr, uid, [
                ('branch_id','=',trx.branch_id.id),
                ('division','=',trx.division),
                ('form_id','=',config_brw[0].form_id.id),
                ('transaction_id','=',trx.id),
            ])
        else :
            approval_lines_ids = self.pool.get('dym.approval.line').search(cr, uid, [
                ('branch_id','=',trx.branch_destination_id.id),
                ('division','=',trx.division),
                ('form_id','=',config_brw[0].form_id.id),
                ('transaction_id','=',trx.id),
            ])                
        if not approval_lines_ids:
            raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki detail approval. Cek kembali Matrix Approval."))
        approval_lines = self.pool.get('dym.approval.line').browse(cr, uid, approval_lines_ids)
        reject_all = False
        for approval_line in approval_lines:
            if approval_line.sts == '1':
                if approval_line.group_id in user_groups:
                    reject_all = True
                    approval_line.write({
                        'sts':'3',
                        'reason':reason,
                        'pelaksana_id':uid,
                        'tanggal':datetime.today(),
                    })
                    break
        if reject_all:
            for approval_line in approval_lines:
                if approval_line.sts == '1':
                    approval_line.write({
                        'sts':'3',
                        'pelaksana_id':uid,
                        'reason':reason,
                        'tanggal':datetime.today(),
                    })
            return 1
        return 0

    def cancel_approval(self, cr, uid, ids, trx, reason):
        config = self.pool.get('dym.approval.config').search(cr,uid,[
            ('form_id','=',trx.__class__.__name__),('type','=','biaya'),
        ])
        if not config :
            raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))     
        config_brw = self.pool.get('dym.approval.config').browse(cr,uid,config)            
        if trx.branch_id :
            approval_lines_ids = self.pool.get('dym.approval.line').search(cr, uid, [
                ('branch_id','=',trx.branch_id.id),
                ('division','=',trx.division),
                ('form_id','=',config_brw[0].form_id.id),
                ('transaction_id','=',trx.id),
            ])
        else :
            approval_lines_ids = self.pool.get('dym.approval.line').search(cr, uid, [
                ('branch_id','=',trx.branch_destination_id.id),
                ('division','=',trx.division),
                ('form_id','=',config_brw[0].form_id.id),
                ('transaction_id','=',trx.id),
            ])                
        if not approval_lines_ids:
            raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki detail approval. Cek kembali Matrix Approval."))
        approval_lines = self.pool.get('dym.approval.line').browse(cr, uid, approval_lines_ids)
        cancel_all = False
        for approval_line in approval_lines:
            if approval_line.sts == '1':
                cancel_all = True
                approval_line.write({
                    'sts':'4',
                    'reason':reason,
                    'pelaksana_id':uid,
                    'tanggal':datetime.today(),
                })
                break
        if cancel_all:
            for approval_line in approval_lines:
                if approval_line.sts == '1':
                    approval_line.write({
                        'sts':'4',
                        'pelaksana_id':uid,
                        'reason':reason,
                        'tanggal':datetime.today(),
                    })
            return 1
        return 0    
 
class dym_approval_reject(osv.osv_memory):
    _name = "dym.approval.reject"
    _columns = {
        'reason':fields.text('Reason')
    }
    
    def dym_approval_reject(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context=context)
        trx_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
        model_name = context.get('model_name',False)
        next_workflow = context.get('next_workflow',False)
        update_value = context.get('update_value',False)
        
        if not trx_id and not model_name:
            raise osv.except_osv(('Perhatian !'), ("Context di button belum lengkap."))

        trx_obj = self.pool.get(model_name).browse(cr,uid,trx_id,context=context)
        if self.pool.get('dym.approval.matrixbiaya').reject(cr, uid, ids, trx_obj, val.reason):
            if next_workflow:
                netsvc.LocalService("workflow").trg_validate(uid, model_name, trx_id, next_workflow, cr) 
            elif update_value :
                self.pool.get(model_name).write(cr,uid,trx_id,update_value)
        else :
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))                                                        
        return True

class dym_reception_reject(osv.osv_memory):
    _name = "dym.reception.reject"
    _columns = {
        'reason':fields.text('Reason')
    }
    
    def dym_reception_reject(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context=context)
        
        trx_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
        model_name = context.get('model_name',False)
        next_workflow = context.get('next_workflow',False)
        update_value = context.get('update_value',False)
        
        if not trx_id and not model_name:
            raise osv.except_osv(('Perhatian !'), ("Context di button belum lengkap."))

        trx_obj = self.pool.get(model_name).browse(cr,uid,trx_id,context=context)
        if self.pool.get('dym.approval.matrixbiaya').reject(cr, uid, ids, trx_obj, val.reason):
            if next_workflow:
                netsvc.LocalService("workflow").trg_validate(uid, model_name, trx_id, next_workflow, cr) 
            elif update_value :
                self.pool.get(model_name).write(cr,uid,trx_id,update_value)
        else :
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))                                                        
        return True
    
class dym_approval_cancel(osv.osv_memory):
    _name = "dym.approval.cancel"
    _columns = {
        'reason':fields.text('Reason')
    }
    
    def dym_approval_cancel(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context=context)
        
        trx_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
        model_name = context.get('model_name',False)
        next_workflow = context.get('next_workflow',False)
        update_value = context.get('update_value',False)
        if not trx_id and not model_name:
            raise osv.except_osv(('Perhatian !'), ("Context di button belum lengkap."))

        trx_obj = self.pool.get(model_name).browse(cr,uid,trx_id,context=context)
        if self.pool.get('dym.approval.matrixbiaya').cancel_approval(cr, uid, ids, trx_obj, val.reason):
            if next_workflow:
                netsvc.LocalService("workflow").trg_validate(uid, model_name, trx_id, next_workflow, cr) 
            elif update_value :
                self.pool.get(model_name).write(cr,uid,trx_id,update_value)
        else :
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))                                                        
        return True