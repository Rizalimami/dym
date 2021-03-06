# -*- encoding: utf-8 -*-
###########################################################################
#    Copyright (C) OpenERP Venezuela (<http://openerp.com.ve>).
#    All Rights Reserved
# Credits######################################################
#    Coded by:   Humberto Arocha humberto@openerp.com.ve
#                Angelica Barrios angelicaisabelb@gmail.com
#               Jordi Esteve <jesteve@zikzakmedia.com>
#    Planified by: Humberto Arocha
#    Finance by: LUBCAN COL S.A.S http://www.lubcancol.com
#    Audited by: Humberto Arocha humberto@openerp.com.ve
#############################################################################
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
##############################################################################
{
    "name": "DYM Financial Reports",
    "version": "2.0",
    "author": "ADSOFT",
    "website": "https://adsoft.co.id",
    'depends': [
        'account',
        'report_xls', 
        'dym_account_move',
        'dym_account',
        # 'account_financial_report_webkit',
    ],
    "category": "Accounting",
    "description":
    """
Account Financial Reports.
==========================

From the wizard you will be asked to provide information needed to create your
report.

Not only you can set the option within the wizard you can create your own
Customized Account Financial Reports, in here, you will be able to create
Templates for generating Two types of Reports: Balance Sheets and Income
Statements, incluiding Analytic Ledgers. Besides, you can select within a set
of choices to get better detailed report, be it that you ask it by one or
several periods, by months (12 Months + YTD), or by quarters (4QRT's + YTD).
Even you can get your reports in currencies other than the one set on your
company.

In the [ Account's Sign on Reports ] Section in the Company will be able to
set the sign conventions for the Accounts, so that you will be able to see in
positives Values in your reports for those accounts with Accreditable nature
where appropriate
    """,
    "data": [
        # 'views/accounting_report_view.xml',
        'views/account_financial_report_view.xml',
        # 'views/account_balance_report_view.xml',
        # 'views/account_general_ledger_report_view.xml',
        'views/report_financial.xml',
    ],
    "active": False,
    "installable": True
}
