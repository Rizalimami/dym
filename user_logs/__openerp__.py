# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004 OpenERP SA (<http://www.openerp.com>)
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

{
    'name' : 'User Log and Session Management',
    'version' : '1.0.0',
    'author' : 'Geo Technosoft',
    'website': 'www.geotechnosoft.com',
    'category' : 'User Log and Session Management',
    'description' : """
        This modules records sign-in sign-out for every users.
        It will also record multi session and multi session out.
        It will also print report for User Logs.
    """,
    'website': '',
    'depends' : ['base'],
    'data': [
             'security/log_group_view.xml',
             'views/users_view.xml',
             'views/user_logs_view.xml',
             'views/ir_config_data.xml',
             'report/user_log_report_view.xml',
             'views/report_view.xml',

             ],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
