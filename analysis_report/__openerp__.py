{
    "name":"Analysis Reports",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Analysis Reports
    """,
    "depends":[
        "stock",
        "dealer_sale_order",
        "dym_work_order",
        "dym_purchase_order"
    ],
    "data":[       
        "report/dealer_sale_order_analysis_view.xml",            
        "report/work_order_report_view.xml",
        "report/sale_order_report_view.xml",
        "report/dym_stock_unit_report.xml",
        "dealer_spk_view.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        # "security/res_groups.xml",
    ],
    "active":False,
    "installable":True
}