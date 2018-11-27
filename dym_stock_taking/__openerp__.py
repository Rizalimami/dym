{
    "name":"Stock Taking",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        
    """,
    "depends":[
        "base", 
        "stock", 
        "dym_approval", 
        "dym_branch",
        "account",
        "dym_serial_number",
        "dym_account_filter"
    ],
    "data":[
        "security/ir.model.access.csv",
        "report/report_inventory_tag_report.xml",
        "views/stock_taking_report.xml",
        "views/stock_taking.xml",
        "views/stock_taking_approval.xml",
        "views/stock_inventory_view.xml",
        "data/dym_stock_taking_approval_config_data.xml",                 
    ],
    "active":False,
    "installable":True
}
