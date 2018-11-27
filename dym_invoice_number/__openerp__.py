# -*- coding: utf-8 -*-
#################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 Julius Network Solutions SARL <contact@julius.fr>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

{
    "name": "DYM Invoice Number",
    "version": "1.0",
    "author": "ADSOFT",
    "description": """This module change the invoice numbering behaviour, where 
    numbering will be triggered by OnChange move_id.name instead of related to move_id.name
    by default.
""",
    "website": "http://adsoft.co.id",
    "license": "GPL-3 or any later version",
    "depends": [
        "dym_work_order",
    ],
    "category": "Custom Module",
    "data": [
    ],
    'installable': True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
