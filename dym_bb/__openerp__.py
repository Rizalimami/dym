{
    "name":"DYM Blind Bonus",
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
        
        #"data/dym_bb_import_approval_config_data.xml",
        "wizard/import_bb_view.xml",
        "views/branch_config_view.xml",
        "views/bb_batch_import_view.xml",
        "views/bb_batch_import_approval_view.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
    ],
    "active":False,
    "installable":True
}
