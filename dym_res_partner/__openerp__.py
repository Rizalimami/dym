{
    "name":"addons res partner",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Membuat Tambahan Master Principle, Biro Jasa, Forwarder, General Supplier, 
        Dealer, Finance Company, Customer di res_partner
    """,
    "depends":[
        "base",
        "hr",
        "dym_address",
        "dym_branch",
        "product"
    ],
    "data":[
        "views/dym_request_payment_term.xml",
        "views/dym_request_platform_view.xml",                        
        "views/dym_res_partner_view.xml",
        "views/dym_approval_rpt_view.xml",
        "views/dym_approval_platform_view.xml",
        "security/ir.model.access.csv",
        # "security/res_groups.xml",
        # "security/res_groups_button.xml",                        
        "data/dym_approval_config_data.xml",
        "security/ir_rule.xml",
    ],
    "active":False,
    "installable":True
}