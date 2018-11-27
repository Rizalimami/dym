from openerp.osv import fields, osv

class dym_res_users(osv.osv):
    _inherit = 'res.users'

    def create(self, cr, uid, vals, context=None):
        # if vals.get('login') and not vals.get('default_code') :
        #     vals['default_code'] = vals.get('login')
        user_id = super(dym_res_users, self).create(cr, uid, vals, context=context)
        return user_id