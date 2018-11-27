import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from lxml import etree
  
class dym_account_account_asset(osv.osv):
    _inherit = 'account.asset.asset'

    def _get_analytic_company(self,cr,uid,context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        level_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('segmen','=',1),('company_id','=',company.id),('type','=','normal'),('state','not in',('close','cancelled'))])
        if not level_1_ids:
            raise osv.except_osv(('Perhatian !'), ("[dym_asset_disposal-1] Tidak ditemukan data analytic untuk company %s")%(company.name))
        return level_1_ids[0]

    _columns = {
        'dispose_asset_id': fields.many2one('dym.asset.disposal',string="No Asset Disposal"), 
        'dispose_asset_id': fields.many2one('dym.asset.disposal',string="No Asset Disposal"), 
        'tgl_bayar_disposal' : fields.date('Tanggal Dispose Asset'),
        'tgl_asset_disposal' : fields.date('Tanggal Dispose Asset'),
        'inv_dispose_asset':fields.many2one('account.invoice','Invoice Asset Disposal'),
        'analytic_1' : fields.many2one('account.analytic.account', 'Account Analytic Company'),
        'analytic_2' : fields.many2one('account.analytic.account', 'Account Analytic Bisnis Unit'),
	    'analytic_3' : fields.many2one('account.analytic.account', 'Account Analytic Branch'),
	    'analytic_4' : fields.many2one('account.analytic.account', 'Account Analytic Cost Center'),
        'state': fields.selection([('draft','Draft'),('open','Running'),('close','Close'),('sold','Sold'),('scrap','Scrapped'),('waiting_for_approval', 'Waiting for Approval'), ('approved','Approved')], 'Status', required=True, copy=False,
                  help="When an asset is created, the status is 'Draft'.\n" \
                       "If the asset is confirmed, the status goes in 'Running' and the depreciation lines can be posted in the accounting.\n" \
                       "You can manually close an asset when the depreciation is over. If the last line of depreciation is posted, the asset automatically goes in that status."),
    }

    _defaults = {
        'analytic_1': _get_analytic_company,
    }