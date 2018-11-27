{
    "name":"DYM Account",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Custom field account.
    """,
    "depends":[
        "base", 
        "account",
        "dym_branch",
        "analytic",
        "account_payment",
        "procurement",
        "product",
        "dym_faktur_pajak",
        "purchase",
        "account_asset"
    ],
    "data":[
        "report/report_invoice_inherit.xml",
        "data/dym.partner.type.xml",
        "views/account_analytic_filter_view.xml",
        "views/account_view.xml",
        "views/dym_procurement_view.xml",
        "views/dym_payment_order_view.xml",
        "views/journal_view.xml",
        "views/account_tax_view.xml",
        "security/ir.model.access.csv",
        # "security/res_groups.xml",
        # "security/res_groups_button.xml",
        "views/supplier_invoice_view.xml",
        "wizard/dym_invoice_merge.xml",
        "report/invoice_report.xml",
    ],
    "active":False,
    "installable":True
}
