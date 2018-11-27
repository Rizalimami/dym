{
    "name":"DYM Bulk Import Insurance",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        
    """,
    "depends":[
        "dym_branch",
        "dym_account_voucher",
        "account",
        "dym_dealer_menu",
        "dym_account",
        "dym_eksport_import",
        "dym_dealer_menu",
        "dym_res_partner",
    ],
    "data":[
        "security/ir.model.access.csv",
        # "security/ir_rule.xml",
        "views/res_partner_view.xml",
        "wizard/import_insurance_view.xml",
        # "views/branch_config_view.xml",
        "views/insurance_batch_import_view.xml",
        "views/insurance_batch_import_approval_view.xml",
    ],
    "active":False,
    "installable":True
}
