{
    "name":"DYM Retur Pembelian",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Retur Pembelian
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
        "dym_hpp"
    ],
    "data":[
        "security/ir.model.access.csv", 
        # "security/ir_rule.xml", 
        "data/dym_approval_config_data.xml",      
        "views/dym_retur_workflow.xml",                              
        "views/dym_approval_retur_workflow.xml",
        "wizard/report_wizard_xls.xml", 
        "report/report_retur.xml", 
        "report/report.xml", 
        "views/dym_retur_view.xml",
        "views/dym_approval_retur_view.xml",
        "views/dym_branch_config_view.xml", 
        # "security/res_groups.xml", 
    ],
    "active":False,
    "installable":True
}