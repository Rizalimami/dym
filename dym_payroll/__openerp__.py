{
    "name":"DYM Payroll",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
    """,
    "depends":[
        "dym_dealer_menu",
        "hr_contract",
        "hr_payroll_account",
        "dym_account",
    ],
    "data":[
        "report/payroll_report.xml",
        "report/dym_payroll_report_template.xml",
        "report/dym_payroll_detail_report_template.xml",
        "wizard/export_payroll_view.xml",
        "wizard/import_payroll_view.xml",
        "views/menu_view.xml",
        "views/hr_payroll_view.xml",
        "views/dym_payslip_view.xml",
        "views/dym_payslip_line_view.xml",
        "views/dym_payslip_analytic_view.xml",
        "views/res_company_view.xml",
        "views/dym_branch_view.xml",
        "views/account_account_view.xml",
        "views/account_account_partner_view.xml",
        "views/dym_payroll_duedate_view.xml",
    ],
    "active":False,
    "installable":True
}