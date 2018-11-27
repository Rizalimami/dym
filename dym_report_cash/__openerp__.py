{
    "name":"Report Cash",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description":"Payments",
    "depends":[
        "base",
        "dym_branch",
        "dym_account_move",
        "dym_account_journal"
    ],
    "data":[
        "wizard/dym_report_cash.xml",
        # "security/res_groups.xml",       
    ],
    "active":False,
    "installable":True
}
