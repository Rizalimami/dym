{
    "name":"Master Branch",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Master Branch
    """,
    "depends":[
        "base",
        "product",
        "hr",
        "stock",
        "account",
        "dym_address",
        "dym_dealer_menu"
    ],
    "data":[
        "views/dym_branch_view.xml",
        "views/dym_harga_birojasa_view.xml",
        "views/dym_harga_bbn_view.xml",
        "views/dym_branch_data.xml",
        "views/dym_branch_category_view.xml",
        "views/dym_area_view.xml",
        "views/res_users_view.xml",
        "security/ir.model.access.csv",
        "views/dym_branch_config_view.xml",
        "views/dym_harga_ekspedisi_view.xml",
        # "data/res_groups.xml",
        # "data/res_groups_audit.xml",
        # "data/dym.branch.xml",
        # "data/account.journal.xml",
        # "data/dym.branch.config.xml",
        # "data/dym.area.xml",
        # "data/dym.branch.csv",
        # "data/dym.area.csv",
        # "data/dym.branch.config.csv",
        # "data/account.account",
        # "security/res_groups.xml",
    ],
    "active":False,
    "installable":True
}