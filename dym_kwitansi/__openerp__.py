{
    "name":"Kwitansi",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description":"Kwitansi",
    "depends":[
        "base",
        "account_voucher",
        "account",
        "dym_branch",
        "dym_account_voucher"
    ],
    "data":[
        "views/dym_kwitansi_report.xml",
        "views/dym_kwitansi_view.xml",
        "views/dym_cancel_kwitansi_view.xml",
        "security/ir_rule.xml",
        "security/ir.model.access.csv",
        # "security/res_groups.xml",
    ],
    "active":False,
    "installable":True
}