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
    "name": "DYM Invoice SQL Insert",
    "version": "1.0",
    "author": "ADSOFT",
    "description": """This module change the way model account.invoice insert data. 
It will directly insert data to the table via SQL Query INSERT instead of normal ORM create procedure. 
""",
    "website": "http://adsoft.co.id",
    "license": "GPL-3 or any later version",
    "depends": [
        # "account",
        "dealer_sale_order",
        "opening_balance_procedure",
        "dym_account",
        "dym_account_voucher",
        "dym_advance_payment_terms",
        "dym_bank_transfer",
        "dym_bank_trf_request",
        "dym_hpp",
        # "dym_invoice_number",
        "dym_payment_import",
        "dym_proses_stnk",
        "dym_purchase_asset",
        "dym_purchase_order",
        "dym_retur_jual",
        "dym_sale_order",
        "dym_work_order",
    ],
    "category": "Custom Module",
    "data": [
    ],
    'installable': True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
