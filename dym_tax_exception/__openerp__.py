{
    "name":"DYM Tax Exception",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        DYM Taxation
    """,
    "depends":[
        "account",
        "dym_tax",
        "dealer_sale_order",
        "dym_purchase_order",
    ],
    "data":[  
        "views/account_tax_view.xml",
        "views/dym_branch_config_view.xml",
        "views/dym_purchase_order_view.xml",
    ],
    "active":False,
    "installable":True
}