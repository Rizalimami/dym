{
    "name":"Advance Payment Terms",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description":"This module aim to make an advance payment terms",
    "depends":[
        "l10n_id_hr_holiday",
        "dym_account",
        "dym_account_voucher",
        "dym_branch"
    ],
    "data":[
        "views/res_partner_view.xml",
        "views/account_voucher_view.xml",
        "views/account_invoice_view.xml",
    ],
    "active":False,
    "installable":True
}