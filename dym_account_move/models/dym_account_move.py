from openerp.osv import osv, fields
from datetime import datetime
import time 

class dym_account_move(osv.osv):
    _inherit = 'account.move'
    
    _columns = {
        'cancel_uid' : fields.many2one('res.users',string="Cancelled by"),
        'confirm_uid' : fields.many2one('res.users',string="Posted by"),
        'cancel_date' : fields.datetime('Cancelled on'),
        'confirm_date' : fields.datetime('Posted on'),
        'transaction_id' : fields.integer('ID Transaksi'),
        'model' : fields.char('Model'),
    }
                
    def post(self, cr, uid, ids, context=None):
        vals = self.browse(cr,uid,ids)
        total_db = 0.0
        total_cr = 0.0
        for line in vals.line_id:
            total_db += line.debit
            total_cr += line.credit
        res = super(dym_account_move, self).post(cr, uid, ids, context=context)
        vals = self.browse(cr,uid,ids)   
        user = self.pool.get('res.users').browse(cr,uid,uid)
        cr.execute('UPDATE account_move '\
                   'SET confirm_uid=%s,confirm_date=%s '\
                   'WHERE id IN %s AND state=%s',
                   (user.id,time.strftime('%Y-%m-%d %H:%M:%S'),tuple([ids] if type(ids) == int else ids),'posted'))
        return res
    
    def button_validate(self, cursor, user, ids, context=None):
        vals = super(dym_account_move,self).button_validate(cursor,user,ids,context=context)
#         self.write(cursor,user,ids,{'confirm_uid':user,'confirm_date':datetime.now()})
        for move in self.browse(cursor, user, ids, context=context):
            for line in move.line_id:
                if line.account_id.type in ['receivable','payable'] and not line.date_maturity :
                    line.date_maturity = datetime.now()
        return vals

    def button_cancel(self, cr, uid, ids, context=None):  
        vals = super(dym_account_move,self).button_cancel(cr,uid,ids,context=context)
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})
        return vals      

    def action_view_transaction(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)
        return {
            'name': 'View Transaction',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': val.model,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': val.transaction_id
            }