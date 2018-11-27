{
    "name":"Net Off",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description":"Net Off",
    "depends":[
        "base",
        "account",
        "dym_branch",
        "dym_account_move",
        "dym_eksport_import"
    ],
    "data":[
        "views/dym_net_off_view.xml",
        # "security/res_groups.xml",
        # "security/res_groups_button.xml",   
        "views/dym_approval_net_off_view.xml",                             
        "security/ir_rule.xml",
        "security/ir.model.access.csv",
        "data/dym_approval_config_data.xml",
    ],
    "active":False,
    "installable":True
}
