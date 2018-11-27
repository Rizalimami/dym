from openerp.osv import fields, osv

class dym_branch_config(osv.osv):
    _inherit = 'dym.branch.config'
    _columns = {
                
        'cost_adjustment_journal_id': fields.many2one('account.journal','Journal Cost Adjustment', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi cost adjustment",),
    }