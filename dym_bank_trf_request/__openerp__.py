{
    "name":"Bank Transfer Request",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Bank Transfer Request",
    "description": """
        
    """,
    "depends":[
        "base",
        "account",
        "account_voucher",
        "dym_branch",
        "dym_account_move",
        "dym_pettycash",
        "dym_account_voucher",
        "dym_clearing_giro",
        "dym_bank_transfer",
    ],
    'qweb':[
        "static/src/xml/bank_trf_request_quickadd.xml",
    ],
    "data":[
        "data/cron.xml",
        "data/ir_sequence.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/assets.xml",
        "views/account_voucher_view.xml",
        "views/dym_bank_transfer_view.xml",
        "wizard/manual_transfer_request_view.xml",
        "wizard/bank_trf_advice_group_view.xml",
        "wizard/reject_request_view.xml",
        "views/menu_view.xml",
        "views/dym_bank_trf_advice_view.xml",
        "views/dym_bank_trf_request_view.xml",
        "views/dym_branch_config_view.xml",
        "views/dym_checkgyro_view.xml",
    ],
    "active":False,
    "installable":True
}
