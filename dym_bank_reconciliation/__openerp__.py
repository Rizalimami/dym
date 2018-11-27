{
    "name":"DYM Bank Reconciliation",
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
        "dym_account"
    ],
    "data":[
        "views/bank_reconciliation.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml", 
        # "security/res_groups.xml",                
    ],
    "active":False,
    "installable":True
}
