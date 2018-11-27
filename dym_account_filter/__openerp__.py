{
    "name":"DYM Account Filter",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Account Filter
    """,
    "depends":[
        "base",
        "account",
        "dym_branch",
        "dym_dealer_menu"
    ],
    "data":[
        "views/dym_account_filter_view.xml",
        "security/ir.model.access.csv",
        # "security/res_groups.xml",
    ],
    "active":False,
    "installable":True
}
