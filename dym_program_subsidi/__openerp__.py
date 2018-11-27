{
    "name":"DYM Program Subsidi",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Custom Field
    """,
    "depends":[
        "base",
        "sale",
        "dym_branch",
        "dym_approval",
        "dym_res_partner_cddb"
    ],
    "data":[
        "views/dym_program_subsidi_view.xml",
        "views/dym_subsidi_barang_view.xml",
        "views/dym_approval_program_subsidi_view.xml",
        "views/dym_approval_subsidi_barang_view.xml",
        "views/dym_hutang_komisi_view.xml",
        "views/dym_approval_hutang_komisi_view.xml",
        "security/ir.model.access.csv",
        "data/dym_approval_config_data.xml",
        # "security/res_groups.xml",
        "security/ir_rule.xml",
    ],
    "active":False,
    "installable":True
}
