from openerp.osv import osv, fields
from openerp.tools.translate import _

class dym_account_journal(osv.osv):
    _inherit = 'account.journal'

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    _columns = {
        'code': fields.char('Code', size=512, required=True, help="The code will be displayed on reports."),
	    'branch_id':fields.many2one('dym.branch', string='Branch'),
    }

    _defaults = {
        'branch_id': _get_default_branch,
    }

    def _auto_init(self, cr, context=None):
    	self._sql_constraints = [
	        ('code_company_uniq', 'unique (code, branch_id, company_id)', 'The code of the journal must be unique per branch !'),
	        ('name_company_uniq', 'unique (name, company_id, branch_id)', 'The name of the journal must be unique per company !'),
    	]
    	super(dym_account_journal,self)._auto_init(cr, context)


    def copy(self, cr, uid, id, default=None, context=None):
        default = dict(context or {})
        journal = self.browse(cr, uid, id, context=context)
        default.update(
            sequence_id=_(False),
            code=_("%s (copy)") % (journal['code'] or ''),
            name=_("%s (copy)") % (journal['name'] or ''))
        return super(dym_account_journal, self).copy(cr, uid, id, default, context=context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        index  = -1
        final_args = []
        for arg in args:
            index += 1
            if type(arg) in [type(()),type([])] and len(arg) == 3:
                field, operator, value = arg
                if field == 'branch_id':
                    branch_id = False
                    flag = False
                    if type(value) == type(0):
                        branch_id = value
                        flag = True
                    elif type(value) in [type(()),type([])] and len(value) > 0:
                        flag = True
                        for val in value:
                            if type(branch_id) == type(0) and type(val) == type(0):
                                flag = False
                                break
                            if type(val) == type(False):
                                continue
                            branch_id = val
                    if branch_id != False and flag == True:
                        branch = self.pool.get('dym.branch').browse(cr, uid, branch_id)
                        if branch.branch_type == 'HO':
                            branch_index = index
                            continue
            final_args.append(arg)
        args = final_args
        return super(dym_account_journal, self).search(cr, uid, args, offset, limit, order, context, count)