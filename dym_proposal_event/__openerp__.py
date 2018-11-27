{
    "name":"Proposal Event",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """        
    """,
    "depends":[
        "sale",
        "purchase", 
        "purchase_requisition", 
        "account_voucher", 
        "dealer_sale_order", 
        "dym_account_voucher",
        "dym_report_penjualan", 
        "dym_purchase_requisition",
        "dym_work_order",
        "dym_base_security",
    ],
    "data":[
        # "security/ir_rule.xml", 
        "security/ir.model.access.csv",
        "views/proposal_event.xml",
        "views/proposal_event_approval.xml",
        "wizard/report_wizard.xml",
        "report/report_qweb.xml",
        "report/proposal_report.xml",
        "data/dym_proposal_event_approval_config_data.xml",
        # "security/res_groups.xml", 
    ],
    "active":False,
    "installable":True
}
