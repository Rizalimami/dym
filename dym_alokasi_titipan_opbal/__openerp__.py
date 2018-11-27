{
    "name":"DYM Alokasi Customer Deposit - Opbal",
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
        "dym_eksport_import"
    ],
    "data":[
        "views/alokasi.xml",
        "views/alokasi_approval.xml",
        "data/dym_alokasi_titipan_approval_config_data.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml", 
        # "security/res_groups.xml",                
    ],
    "active":False,
    "installable":True
}
