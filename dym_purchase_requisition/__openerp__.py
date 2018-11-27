{
    "name":"Purchase Request",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Purchase Request & Report Purchase Requisition
    """,
    "depends":[
        "purchase",
        "purchase_requisition",
        "product",
        "hr",
        "dym_branch",
        "dym_approval",
        "dym_sequence",
        "dym_purchase_order"
    ],
    "data":[
        "views/dym_purchase_requisition_report.xml",
        "views/dym_approval_pr_workflow.xml",
        "views/dym_purchase_requisition_view.xml",
        "views/dym_approval_pr_view.xml",
        "security/ir_rule.xml",
        # "security/res_groups.xml",
        # "data/dym_approval_config_data.xml",
    ],
    "active":False,
    "installable":True
}
