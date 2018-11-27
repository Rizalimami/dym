{
    "name":"DYM Incentive",
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
        "dym_eksport_import",
        "dym_alokasi_titipan",
        "dym_dealer_menu",
        "dym_res_partner",
    ],
    "data":[
        "wizard/import_incentive_view.xml",
        "views/res_partner_view.xml",
        "views/incentive_allocation_view.xml",
        "views/incentive_allocation_approval_view.xml",
        "views/incentive_batch_import_view.xml",
        "views/incentive_batch_import_approval_view.xml",
        "data/dym_incentive_allocation_approval_config_data.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
    ],
    "active":False,
    "installable":True
}
