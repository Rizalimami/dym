# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
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
    "name": "Other Receivabble Withholding",
    "version": "8.0.0.0.0",
    "author":  "ADSOFT",
    "website": "adsoft.co.id",
    "license": "AGPL-3",
    "category": "Accounting & Finance",
    "demo": [],
    "depends": [
        "account_voucher_withholding",
        "dym_account_voucher",
        "dym_account_move",
        "account_voucher_payline",
    ],
    "description": """
Other Receivabble Withholding
=============================
Add withholding management on other receivable vouchers
""",
    "data":[
        "views/account_voucher_view.xml",
        "views/account_withholding_view.xml",
        "views/account_tax_withholding_view.xml",
    ],
    "test": [],
    "installable": True,
    "active":False,
 }
