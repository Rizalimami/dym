{
    "name":" Addons Eff Date and Max Qty",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Addons Eff Date and Max Qty
    """,
    "depends":[
        "base",
        "stock",
        "dym_branch",
        "dym_stock_account",
        "dym_warehouse"
    ],
    "data":[
        "views/dym_stock_location_view.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
    ],
    "active":False,
    "installable":True
}