{
    "name":"CDDB",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module",
    "description": """
        CDDB
    """,
    "depends":[
        "base",
        "account",
        "dym_res_partner",
        "sales_team",
    ],
    "data":[
        "views/dym_questionnaire_view.xml",
        "views/dym_res_partner_cddb_view.xml",
        "views/dym_res_partner_wizard_view.xml",
        "views/dym_res_partner_data.xml",
        "views/dym_cabang_partner.xml",
        "security/ir.model.access.csv",
        "views/dym_sales_team.xml",
        "views/dym_partner_customer_view.xml",
        "views/dym_partner_finco_view.xml",
        # "security/res_groups.xml",
        ],
    "active":False,
    "installable":True
}