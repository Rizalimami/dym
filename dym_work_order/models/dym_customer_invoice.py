import time
from datetime import datetime
from openerp.osv import fields, osv

class dym_pengajuan_birojasa(osv.osv):
    _inherit = "account.invoice"     
    _columns = {
        'workorder_id': fields.many2one('dym.work.order', string='No. WO'),
        'merge_inv': fields.selection([('not', 'Not Paid'), ('paid','paid')], 'Merge Invoice', readonly=True),
    }
    
    _defaults = {
        'merge_inv':'not'
    }
