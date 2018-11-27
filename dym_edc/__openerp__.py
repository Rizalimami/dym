{
    "name":"Payment Method EDC",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        EDC
    """,
    "depends":[
        "base",
        "account_voucher",
        "account"
    ],
    "data":[  
        # "data/dym_branch_config.xml",
        "views/dym_edc_view.xml",
        "views/dym_branch_config_view.xml",
        "views/dym_disbursement_view.xml",
        # "security/res_groups.xml",            
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        # "security/res_groups_button.xml", 
        # "data/res_partner_bank.xml",   
        # "data/edc.xml",
    ],
    "active":False,
    "installable":True
}