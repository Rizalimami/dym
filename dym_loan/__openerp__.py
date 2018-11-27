{
    "name":"Loan",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        
    """,
    "depends":[
        "base",
        "account",
        "dym_branch",
        "dym_account_voucher",
        "dym_dealer_menu",
        "dym_account",
        "dym_account_filter"
    ],
    "data":[
        "report/report_loan.xml",
        "report/report_loan_pinjaman.xml",
        "report/report_loan_piutang.xml",
        "report/report_view.xml",
        "views/loan.xml",
        "views/loan_approval.xml",
        "data/dym_loan_approval_config_data.xml",
        "views/dym_branch_config_view.xml", 
        "security/ir.model.access.csv",
        "security/ir_rule.xml", 
    ],
    "active":False,
    "installable":True
}
