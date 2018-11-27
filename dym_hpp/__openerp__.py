{
    "name":"Harga Pokok Penjualan",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        HPP with Serial Number.
    """,
    "depends":[
        "base",
        "stock",
        "account",
        "purchase",
        "dym_purchase_asset"
    ],
    "data":[
        "views/hpp_view.xml",
        "security/ir.model.access.csv",
        # "security/res_groups.xml",
        # "security/res_groups_button.xml",
        "report/hpp_report.xml",
    ],
    "active":False,
    "installable":True
}
