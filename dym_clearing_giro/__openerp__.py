{
    "name":"Clearing Bank",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        
    """,
    "depends":[
        "base",
        "dym_branch",
        "dym_account_voucher",
        "account",
        "dym_dealer_menu",
        "dym_account"
    ],
    "data":[
        "data/cron_data.xml",
        "views/clearing.xml",
        "views/clearing_approval.xml",
        # "views/account_voucher_view.xml",
        "data/dym_clearing_giro_approval_config_data.xml",
        "wizard/report_wizard.xml",
        "wizard/auto_clearing_view.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml", 
        # "security/res_groups.xml",                
    ],
    "active":False,
    "installable":True
}
