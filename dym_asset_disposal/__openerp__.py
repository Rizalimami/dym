{
    "name":"DYM Asset Disposal",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Permohonan Faktur
    """,
    "depends":[
        "base",
        "dym_faktur_pajak",
        "account",
        "dym_branch",
        "stock",
        "dym_dealer_menu",
        "dym_serial_number",
        "dym_approval",
        "dym_purchase_asset"
    ],
    "data":[            
        "data/dym_approval_config_data.xml", 
        "security/ir.model.access.csv",     
        "views/dym_asset_disposal_workflow.xml",                              
        "views/dym_approval_asset_disposal_workflow.xml",
        "views/dym_asset_disposal_view.xml",
        "views/dym_approval_asset_disposal_view.xml",
        "views/dym_asset.xml",
        "views/dym_branch_config_view.xml", 
        "views/dym_asset_delivery.xml", 
    ],
    "active":False,
    "installable":True
}