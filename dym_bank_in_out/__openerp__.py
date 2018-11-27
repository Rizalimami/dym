{
    "name":"DYM Bank In/Out",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        
    """,
    "depends":[
        "base",
        "dym_branch",
        "dym_account_voucher",
        "account",
        "dym_dealer_menu",
        "dym_account",
        "dym_bank_trf_request",
        "dym_base_security",
    ],
    "data":[
        "security/ir.model.access.csv",
        "views/menu.xml",
        "views/cash_bank_in.xml",
        "views/cash_bank_out.xml",
        "views/dym_reimburse_bank_view.xml",
        "wizard/transfer_request_wizard_view.xml",
    ],
    "active":False,
    "installable":True
}
