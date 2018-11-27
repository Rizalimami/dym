# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Eficent (<http://www.eficent.com/>)
#              <contact@eficent.com>
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

{
    "name": "Purchase Order SJ Import",
    "author": "ADSOFT",
    "version": "8.0.1.0.0",
    "contributors": [
        'Iman Sulaiman',
    ],
    "category": "Purchase Order SJ Import",
    "depends": [
        "dym_dealer_menu",
        "dym_purchase_order",
        "dym_stock",
        "dym_branch",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/import_sj_view.xml",
        "views/po_sj_import_view.xml",
        "security/ir_rule.xml",
    ],
    'demo': [
    ],
    "license": 'AGPL-3',
    "installable": True
}
