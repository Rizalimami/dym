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

import time
from openerp.osv import osv
from openerp.report import report_sxw


class dym_work_order_wip(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(dym_work_order_wip, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_pricelist': self._get_pricelist,
            'lines_a': self._lines_a,
            'no_urut': self.no_urut,
            
        })

        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no

    def _get_pricelist(self, pricelist_id):
        pricelist = self.pool.get('product.pricelist').read(self.cr, self.uid, [pricelist_id], ['name'], context=self.localcontext)[0]
        return pricelist['name']
    
    def _lines_a(self, accounts):
        self.cr.execute("SELECT wo.name as name, wo.date as date, wo.no_pol as no_pol, wo.type as type, wo.state as state, wo.state_wo as state_wo, emp.name_related as mekanik_name from dym_work_order wo left join hr_employee emp on wo.mekanik_id = emp.id where state !='draft' and state !='done'")
        res = self.cr.dictfetchall()
        return res
        
class report_dym_work_order_wip(osv.AbstractModel):
    _name = 'report.dym_work_order.dym_work_order_wip_report'
    _inherit = 'report.abstract_report'
    _template = 'dym_work_order.dym_work_order_wip_report'
    _wrapped_report_class = dym_work_order_wip

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
