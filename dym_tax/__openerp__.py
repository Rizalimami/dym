{
    "name":"DYM Tax",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        DYM Taxation
    """,
    "depends":[
        "dym_faktur_pajak",
        "dym_purchase_order",
        "dym_asset_disposal",
    ],
    "data":[  
        "views/res_company_view.xml",
        "views/faktur_pajak_view.xml",
        "views/asset_dispossal_view.xml",
    ],
    "active":False,
    "installable":True
}