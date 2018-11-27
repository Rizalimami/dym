from openerp import models, fields, api, _, SUPERUSER_ID, workflow
from openerp.osv import osv
import time
import logging
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
_logger = logging.getLogger(__name__)

class dym_alokasi_titipan(osv.osv):
    _inherit = "dym.alokasi.titipan"

    def check_confirm_alokasi(self, cr, uid, context=None):
        alokasi_ids = self.search(cr, uid, [('state','=','approved')], context=context)
        for dat in self.browse(cr, uid, alokasi_ids, context=context):
            _logger.info(_('Comfirn Alokasi Titipan %s' % dat.name))
            try:
                dat.confirm_alokasi()
            except:
                _logger.info(_("Confirm Alokasi Titipan %s ....... ERROR" % dat.name))
                pass
            
 