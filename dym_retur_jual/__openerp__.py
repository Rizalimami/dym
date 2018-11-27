{
    "name":"DYM Retur Penjualan",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module",
    "description": """
        Retur Penjualan
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
        "dym_retur_beli",
        "dealer_sale_order",
    ],
    "data":[            
        # "security/ir_rule.xml", 
        "data/dym_approval_config_data.xml",      
        "views/dym_retur_workflow.xml",                              
        "views/dym_approval_retur_workflow.xml",
        "wizard/report_wizard_xls.xml", 
        "wizard/back_to_rfs_info.xml",
        "report/report_retur.xml", 
        "report/report.xml", 
        "views/dym_retur_view.xml",
        "views/dym_approval_retur_view.xml",
        "views/dym_branch_config_view.xml", 
        "views/account_invoice_view.xml", 
        "views/dealer_sale_order_view.xml", 
        "views/stock_picking_view.xml",      
        "views/stock_packing_view.xml",      
        # "security/res_groups.xml", 
    ],
    "active":False,
    "installable":True
}