{
    "name":"DYM Approval Bertingkat",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
    """,
    "depends":[
        "base",
        "dym_branch",
        "mail",
        "dym_dealer_menu",
    ],
    "data":[
        "views/dym_approval_view.xml",
        "views/dym_approval_config_view.xml",
        "views/dym_so_approval_view.xml",
        "views/dym_copy_approval_view.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        # "security/res_groups.xml",
    ],
    "active":False,
    "installable":True
}