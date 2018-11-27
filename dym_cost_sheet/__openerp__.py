{
    "name":"Cost Sheet",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        
    """,
    "depends":[
        "dealer_sale_order",
        "report"
    ],
    "data":[
        "report/cost_sheet_report_template.xml",
        "views/cost_sheet_report.xml",
        "views/cost_sheet.xml",
        "security/ir.model.access.csv",
        # "security/res_groups.xml", 
    ],
    "active":False,
    "installable":True
}
