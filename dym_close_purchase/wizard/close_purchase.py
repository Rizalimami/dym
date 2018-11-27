# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

#
# Order Point Method:
#    - Order if the virtual stock of today is bellow the min of the defined order point
#

from datetime import date, datetime
import threading
from openerp.osv import fields,osv
from openerp.api import Environment
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

class close_purchase_wizard(osv.osv_memory):
    _name = 'close.purchase.wizard'
    _description = 'Close purchase wizard'

    def close_purchase_order(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        purchase_obj = self.pool.get('purchase.order')
        today = date.today().strftime(DATE_FORMAT)
        domain = [
            ('state','in',['draft','bid','confirmed','sent','approved']),
            ('end_date','<',today),
        ]
        po_ids = purchase_obj.search(cr, uid, domain, context=context)
        for purchase in purchase_obj.browse(cr, uid, po_ids, context=context):
            purchase.action_close()
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
