{
    "name":"Journal Memorial Consolidation",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description":"Journals",
    "depends":[
        "base",
        "account",
        "dym_journal_consolidation",
        "dym_branch",
        "dym_account_move"
    ],
    "data":[
        "views/dym_branch_config.xml",
        "views/dym_journal_memorial_consol_view.xml",
        "views/dym_approval_journal_memorial_consol_view.xml",
        "security/ir_rule.xml",
        "security/ir.model.access.csv",
        "data/dym_approval_config_data.xml",
        # "security/res_groups.xml",
    ],
    "active":False,
    "installable":True
}
