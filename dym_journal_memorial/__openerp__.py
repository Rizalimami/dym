{
    "name":"Journal Memorial",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description":"Journals",
    "depends":[
        "base",
        "account",
        "dym_branch",
        "dym_account_move",
        "dym_eksport_import",
        "dym_approval"
    ],
    "data":[                               
        "views/dym_branch_config_view.xml",
        "views/dym_journal_memorial_view.xml",
        "views/dym_approval_journal_memorial_view.xml",
        "security/ir_rule.xml",
        "security/ir.model.access.csv",
        "data/dym_approval_config_data.xml",
        "data/ir_sequence.xml",                 
        # "security/res_groups.xml",
        # "security/res_groups_button.xml", 
    ],
    "active":False,
    "installable":True
}
