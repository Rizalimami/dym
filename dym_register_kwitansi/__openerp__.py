{
    "name":"Registrasi Kwitansi",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Register Kwitansi
    """,
    "depends":[
        "base",
        "dym_branch",
        "dym_sequence"
    ],
    "data":[
        "views/dym_register_kwitansi_view.xml",
        "views/dym_generate_register_kwitansi_view.xml",
        "security/ir.model.access.csv",
        # "security/res_groups.xml"
    ],
    "active":False,
    "installable":True
}
