{
    "name":"DYM Account Move",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module DYMS",
    "description":"Payments",
    "depends":[
        "base",
        "dym_branch",
        "account_voucher",
        "dym_account_journal",
        "dym_account_filter",
        "account_asset",
        "account",
    ],
    "data":[
        "views/dym_account_move_view.xml",
        "views/dym_account_move_line_view.xml",
        # "security/res_groups.xml",
    ],
    "active":False,
    "installable":True
}
